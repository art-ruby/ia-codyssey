import argparse
import json
import os
from datetime import datetime

import requests
from dotenv import load_dotenv
from google import genai


# --------------------------------------------------
# 1. CLI 입력
# --------------------------------------------------
def parse_arguments():
    parser = argparse.ArgumentParser(
        description="국내 여행지 추천 프로그램"
    )

    parser.add_argument(
        "-date",
        "--date",
        required=True,
        help="여행 날짜 (YYYY-MM-DD)"
    )

    parser.add_argument(
        "--days",
        type=int,
        choices=[1, 2],
        default=1,
        help="여행 일수: 1=당일, 2=1박 2일"
    )

    return parser.parse_args()


# --------------------------------------------------
# 2. 날짜 형식 확인
# --------------------------------------------------
def validate_date(date_text):
    try:
        datetime.strptime(date_text, "%Y-%m-%d")
        return True
    except ValueError:
        return False


# --------------------------------------------------
# 3. .env에서 API 키 불러오기
# --------------------------------------------------
def load_config():
    load_dotenv()

    gemini_key = os.getenv("GEMINI_API_KEY")
    kakao_key = os.getenv("KAKAO_REST_API_KEY")

    if not gemini_key:
        print("오류: GEMINI_API_KEY가 설정되지 않았습니다.")
        print(".env 파일을 확인하세요.")
        raise SystemExit(1)

    if not kakao_key:
        print("오류: KAKAO_REST_API_KEY가 설정되지 않았습니다.")
        print(".env 파일을 확인하세요.")
        raise SystemExit(1)

    return gemini_key, kakao_key


# --------------------------------------------------
# 4. Gemini 여행지 추천
# --------------------------------------------------
def get_travel_recommendation(date, days, gemini_key, errors):
    client = genai.Client(api_key=gemini_key)

    if days == 1:
        trip_type = "당일 여행"
    else:
        trip_type = "1박 2일 여행"

    prompt = f"""
여행 날짜는 {date}입니다.
여행 기간은 {trip_type}입니다.

이 조건에 적합한 대한민국 국내 여행지 2곳을 추천하세요.

두 지역은 가능하면 서로 다른 매력을 가진 곳으로 추천하세요.

반드시 다음 JSON 형식으로만 응답하세요.

{{
  "recommended_city": "첫 번째 추천 도시",
  "weather": "첫 번째 추천 도시의 해당 시기 일반적 날씨",
  "events": ["행사 또는 축제 후보 1", "행사 또는 축제 후보 2"],
  "reason": "첫 번째 추천 도시를 추천하는 이유 2~4문장",
  "recommended_cities": [
    {{
      "city": "첫 번째 도시",
      "weather": "날씨",
      "events": ["행사 또는 축제"],
      "reason": "추천 이유",
      "highlight": "대표 여행 매력"
    }},
    {{
      "city": "두 번째 도시",
      "weather": "날씨",
      "events": ["행사 또는 축제"],
      "reason": "추천 이유",
      "highlight": "대표 여행 매력"
    }}
  ]
}}

규칙:
- recommended_cities에는 정확히 2개의 도시를 넣으세요.
- recommended_city는 recommended_cities의 첫 번째 city와 같아야 합니다.
- events는 문자열 배열이어야 합니다.
- JSON 이외의 설명은 작성하지 마세요.
- Markdown 코드블록을 사용하지 마세요.
"""

    # 최초 요청 + JSON 파싱 실패 시 1회 재요청
    for attempt in range(2):
        try:
            response = client.models.generate_content(
                model="gemini-3.5-flash",
                contents=prompt
            )

            result = json.loads(response.text.strip())

            required_keys = [
                "recommended_city",
                "weather",
                "events",
                "reason",
                "recommended_cities"
            ]

            for key in required_keys:
                if key not in result:
                    raise ValueError(
                        f"필수 키가 없습니다: {key}"
                    )

            if len(result["recommended_cities"]) != 2:
                raise ValueError(
                    "recommended_cities는 정확히 2개여야 합니다."
                )

            return result

        except (json.JSONDecodeError, ValueError) as e:
            if attempt == 0:
                print("  - JSON 파싱 실패")
                print("  - Gemini에 1회 재요청합니다.")

                prompt += """

이전 응답을 JSON으로 파싱하지 못했습니다.
설명 문장과 Markdown 코드블록을 모두 제거하고
위에서 요구한 JSON 객체 하나만 다시 출력하세요.
"""
                continue

            errors.append({
                "step": "gemini_recommendation",
                "type": "JSON_PARSE_ERROR",
                "message": str(e)
            })

            raise RuntimeError(
                "Gemini JSON 파싱에 최종 실패했습니다."
            )

        except Exception as e:
            errors.append({
                "step": "gemini_recommendation",
                "type": "API_ERROR",
                "message": str(e)
            })
            raise


# --------------------------------------------------
# 5. Kakao Local 맛집 검색
# --------------------------------------------------
def search_kakao_restaurants(city, kakao_key, errors):
    url = "https://dapi.kakao.com/v2/local/search/keyword.json"

    headers = {
        "Authorization": f"KakaoAK {kakao_key}"
    }

    query = f"{city} 맛집"

    params = {
        "query": query,
        "category_group_code": "FD6",
        "size": 5,
        "page": 1,
        "sort": "accuracy"
    }

    try:
        response = requests.get(
            url,
            headers=headers,
            params=params,
            timeout=10
        )

        response.raise_for_status()

        data = response.json()
        documents = data.get("documents", [])

        if not documents:
            errors.append({
                "step": "place_search",
                "city": city,
                "type": "EMPTY_RESULT",
                "message": f"0 results for query={query}"
            })
            return []

        restaurants = []

        for item in documents:
            restaurant = {
                "name": item.get("place_name", ""),
                "address": (
                    item.get("road_address_name")
                    or item.get("address_name", "")
                ),
                "category": item.get("category_name", ""),
                "url": item.get("place_url", ""),
                "phone": item.get("phone", ""),
                "lng": float(item["x"]) if item.get("x") else None,
                "lat": float(item["y"]) if item.get("y") else None
            }

            restaurants.append(restaurant)

        return restaurants

    except requests.RequestException as e:
        errors.append({
            "step": "place_search",
            "city": city,
            "type": "API_ERROR",
            "message": str(e)
        })

        return []


# --------------------------------------------------
# 6. Gemini 최종 리포트 생성
# --------------------------------------------------
def generate_final_report(
    date,
    days,
    recommendation,
    restaurants_by_city,
    errors,
    gemini_key
):
    client = genai.Client(api_key=gemini_key)

    if days == 1:
        schedule_rule = """
일정 제안은 두 추천 도시를 각각 독립적인 당일 코스로 작성하세요.

### A안 — 첫 번째 도시 당일 코스
- 오전
- 오후
- 저녁

### B안 — 두 번째 도시 당일 코스
- 오전
- 오후
- 저녁
"""
    else:
        schedule_rule = """
일정 제안은 다음과 같이 작성하세요.

### DAY 1 — 첫 번째 도시
- 오전
- 오후
- 저녁

### DAY 2 — 두 번째 도시
- 오전
- 오후
- 저녁
"""

    report_prompt = f"""
다음 정보를 바탕으로 국내 여행 추천 리포트를
Markdown 형식으로 작성하세요.

여행 날짜:
{date}

여행 일수:
{days}일

여행 추천 정보:
{json.dumps(recommendation, ensure_ascii=False, indent=2)}

Kakao 맛집 검색 결과:
{json.dumps(restaurants_by_city, ensure_ascii=False, indent=2)}

오류 목록:
{json.dumps(errors, ensure_ascii=False, indent=2)}

반드시 다음 항목을 포함하세요.

# {date} 국내 여행 추천 리포트

## 추천 지역

## 추천 이유

## 날씨 요약

## 행사/축제

## 맛집 추천

## 일정 제안

{schedule_rule}

## 오류 요약

규칙:
- 맛집은 Kakao 검색 결과에 실제로 존재하는 식당만 사용하세요.
- Kakao 검색 결과에 없는 식당을 새로 만들어내지 마세요.
- 각 식당의 이름과 주소를 보기 쉽게 정리하세요.
- 맛집 결과가 없으면 '데이터 없음'이라고 작성하세요.
- 오류가 없으면 '오류 없음'이라고 작성하세요.
"""

    response = client.models.generate_content(
        model="gemini-3.5-flash",
        contents=report_prompt
    )

    return response.text


# --------------------------------------------------
# 7. 결과 저장
# --------------------------------------------------
def save_results(
    date,
    days,
    recommendation,
    restaurants_by_city,
    errors,
    final_report
):
    os.makedirs("results", exist_ok=True)

    json_path = f"results/data_{date}_{days}d.json"
    md_path = f"results/report_{date}_{days}d.md"

    raw_data = {
        "date": date,
        "days": days,
        "recommendation": recommendation,
        "restaurants_by_city": restaurants_by_city,
        "errors": errors
    }

    with open(
        json_path,
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            raw_data,
            f,
            ensure_ascii=False,
            indent=2
        )

    with open(
        md_path,
        "w",
        encoding="utf-8"
    ) as f:
        f.write(final_report)

    return json_path, md_path


# --------------------------------------------------
# 8. 메인 실행
# --------------------------------------------------
def main():
    args = parse_arguments()

    # 날짜 확인
    if not validate_date(args.date):
        print("오류: 날짜 형식이 올바르지 않습니다.")
        print()
        print("사용법:")
        print(
            'python travel_planner.py '
            '-date "YYYY-MM-DD" [--days 1|2]'
        )
        return

    # API 키 확인
    gemini_key, kakao_key = load_config()

    errors = []

    if args.days == 1:
        trip_type = "당일"
    else:
        trip_type = "1박 2일"

    print()
    print("국내 여행지 추천 프로그램")
    print(f"여행 날짜: {args.date}")
    print(f"여행 일수: {args.days}일 ({trip_type})")
    print("API 키 설정 확인 완료")
    print()

    # --------------------------------------------------
    # [1/3] Gemini 여행지 추천
    # --------------------------------------------------
    print("[1/3] Gemini 여행지 추천 생성 중...")

    try:
        recommendation = get_travel_recommendation(
            args.date,
            args.days,
            gemini_key,
            errors
        )

    except Exception as e:
        print()
        print("Gemini 여행지 추천 생성에 실패했습니다.")
        print(f"오류: {e}")
        return

    print("  - JSON 응답 수신 완료")
    print(
        "  - 추천 지역 1:",
        recommendation["recommended_cities"][0]["city"]
    )
    print(
        "  - 추천 지역 2:",
        recommendation["recommended_cities"][1]["city"]
    )

    # --------------------------------------------------
    # [2/3] Kakao 맛집 검색
    # --------------------------------------------------
    print()
    print("[2/3] Kakao 맛집 검색 중...")

    restaurants_by_city = {}

    for index, city_info in enumerate(
        recommendation["recommended_cities"],
        start=1
    ):
        city = city_info["city"]

        print(
            f'  - [{index}/2] 검색어: "{city} 맛집"'
        )

        restaurants = search_kakao_restaurants(
            city,
            kakao_key,
            errors
        )

        restaurants_by_city[city] = restaurants

        if restaurants:
            print(
                f"    → {len(restaurants)}곳 검색 완료"
            )
        else:
            print(
                "    → 데이터 없음"
            )

    # --------------------------------------------------
    # [3/3] Gemini 최종 리포트
    # --------------------------------------------------
    print()
    print("[3/3] Gemini 최종 리포트 생성 중...")

    try:
        final_report = generate_final_report(
            args.date,
            args.days,
            recommendation,
            restaurants_by_city,
            errors,
            gemini_key
        )

        print("  - 최종 리포트 생성 완료")

    except Exception as e:
        errors.append({
            "step": "final_report",
            "type": "API_ERROR",
            "message": str(e)
        })

        print("최종 리포트 생성에 실패했습니다.")
        print(f"오류: {e}")
        return

    # --------------------------------------------------
    # 결과 저장
    # --------------------------------------------------
    json_path, md_path = save_results(
        args.date,
        args.days,
        recommendation,
        restaurants_by_city,
        errors,
        final_report
    )

    print()
    print("결과 저장 완료")
    print(f"  - {json_path}")
    print(f"  - {md_path}")
    print()
    print("완료!")


if __name__ == "__main__":
    main()