"""실제 OpenAI 호출 검증 — 명세 §1·§2.

규칙 기반 fallback 결과는 최종 AI 검증으로 치지 않는다. 이 스크립트는
**실제 GPT 응답일 때만 PASS** 를 준다(`answer_source == "openai"`).

키가 없으면 아무것도 호출하지 않고, 무엇을 설정해야 하는지만 알린다.
키를 코드에 넣지 않는다 — 환경 변수 또는 backend/.env 로만 받는다.

    # 1) backend/.env 에 OPENAI_API_KEY=sk-... 를 넣거나 환경 변수로 export
    # 2) DEBUG=true 로 백엔드를 띄운다 (주입 컨텍스트 확인용)
    python tests/verify_openai.py

과금 주의: 질문 7개 × 1회 호출. gpt-4o-mini · max_tokens 800 기준
대략 1회당 1,000~1,500 토큰이다.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

BASE = os.getenv("API_BASE", "http://127.0.0.1:8000")
PROJECT = Path(__file__).resolve().parents[1]

QUESTIONS = [
    ("Q1", "오늘 제작할 후보 3개 추천해줘."),
    ("Q2", "MAKE 후보만 보여줘."),
    ("Q3", "WATCH 후보 중 점수가 높은 것을 알려줘."),
    ("Q4", "최근 점수가 높은 주제는 무엇이야?"),
    ("Q5", "money_retirement 채널 후보가 있다면 알려줘."),
    ("Q6", "왜 이 후보를 MAKE로 추천했어?"),
    ("Q7", "비트코인 시세 급등 관련 후보 있어?"),
]

# 저장된 데이터에 존재하지 않는 것들. 답변에 사실처럼 나오면 hallucination 이다.
ABSENT_TERMS = ["money_retirement", "비트코인", "bitcoin"]


def call(method: str, path: str, body: dict | None = None, timeout: float = 90.0):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(
        BASE + path, data=data, method=method,
        headers={"Content-Type": "application/json"} if data else {},
    )

    def parse(text: str):
        try:
            return json.loads(text or "null")
        except json.JSONDecodeError:
            return text

    try:
        with urllib.request.urlopen(req, timeout=timeout) as res:
            return res.status, parse(res.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as exc:
        return exc.code, parse(exc.read().decode("utf-8", "replace"))
    except urllib.error.URLError as exc:
        print(f"[중단] 백엔드에 연결할 수 없습니다 ({BASE}): {exc.reason}")
        print("       uvicorn app.main:app --port 8000 으로 먼저 띄우세요.")
        sys.exit(2)


def check_hallucination(reply: str, titles: set[str]) -> list[str]:
    """지어낸 정보의 흔적을 찾는다. 완전한 판정은 사람이 해야 한다."""
    problems = []
    for term in ABSENT_TERMS:
        if term.lower() in reply.lower():
            # 없다고 말하는 맥락이면 정상. 있다고 말하면 문제.
            negations = ["없습니다", "없음", "없다", "존재하지", "찾을 수 없"]
            window = reply.lower()
            if not any(neg in window for neg in negations):
                problems.append(f"'{term}' 를 부정 없이 언급")
    return problems


def main() -> int:
    print("=" * 74)
    print("실제 OpenAI 호출 검증")
    print("=" * 74)

    status, health = call("GET", "/api/health")
    if status != 200:
        print(f"[중단] /api/health 가 {status} 를 반환했습니다.")
        return 2

    if not health.get("openai_configured"):
        print("\n❌ OPENAI_API_KEY 가 설정되어 있지 않습니다. 실제 호출 검증을 건너뜁니다.")
        print("   규칙 기반 fallback 결과는 AI 검증으로 간주하지 않습니다.\n")
        print("   설정할 환경 변수:")
        print("     OPENAI_API_KEY   (필수)  발급받은 키")
        print("     OPENAI_BASE_URL  (프록시 사용 시 필수)")
        print("                              Codyssey → https://copa.codyssey.kr/v1")
        print("                              비우면 api.openai.com 으로 나가 401 이 납니다")
        print("     OPENAI_MODEL     (선택)  기본 gpt-5-mini")
        print("     OPENAI_MAX_TOKENS(선택)  기본 800 — 과금 상한")
        print("     DEBUG            (선택)  true 로 두면 주입 컨텍스트를 확인할 수 있음")
        print(f"\n   설정 위치: {PROJECT / 'backend' / '.env'}")
        print("   키는 코드에 넣지 마세요. .env 는 .gitignore 에 있습니다.")
        return 1

    print(f"모델    : {health.get('openai_model')}")
    print(f"엔드포인트: {health.get('openai_endpoint')}")
    print(f"저장소  : {health.get('store')}")

    status, rows = call("GET", "/api/data?limit=2000")
    if status != 200 or not rows:
        print("[중단] 후보 데이터가 없습니다. 표본을 먼저 적재하세요:")
        print("       POST /api/data/import?source=sample&replace=true")
        return 2
    titles = {str(r.get("title") or "") for r in rows}
    print(f"저장된 후보: {len(rows)}건\n")

    debug_on = call("POST", "/api/chat/preview", {"message": "ping"})[0] == 200
    print(f"주입 컨텍스트 확인 경로: {'사용 가능 (DEBUG=true)' if debug_on else '닫힘 (DEBUG 미설정)'}\n")

    passed = failed = 0
    for label, question in QUESTIONS:
        print("─" * 74)
        print(f"{label}. {question}")

        injected = None
        if debug_on:
            _, pv = call("POST", "/api/chat/preview", {"message": question})
            injected = pv

        status, res = call("POST", "/api/chat", {"message": question})
        if status != 200:
            print(f"   ❌ FAIL — HTTP {status}")
            failed += 1
            continue

        source = res.get("answer_source")
        reply = res.get("reply", "")
        used = res.get("candidates_used", 0)
        summary_count = (res.get("summary_used") or {}).get("count", 0)
        basis = res.get("selection_basis")
        conv_id = res.get("conversation_id")

        # 대화 저장 확인
        st_conv, conv = call("GET", f"/api/conversations/{conv_id}")
        saved = st_conv == 200 and len(conv.get("messages", [])) >= 2

        halluc = check_hallucination(reply, titles)
        is_real_ai = source == "openai"
        ok = is_real_ai and summary_count > 0 and used > 0 and saved and not halluc

        print(f"   사용 후보     : {used}건 (선별 근거: {basis})")
        print(f"   Summary 사용  : {'예' if summary_count > 0 else '아니오'} ({summary_count}건)")
        if injected:
            print(f"   주입 프롬프트 : {injected.get('system_prompt_chars')}자")
        print(f"   응답 출처     : {source}")
        print(f"   대화 저장     : {'예' if saved else '아니오'} ({conv_id})")
        print(f"   Hallucination : {'없음' if not halluc else ', '.join(halluc)}")
        print(f"   판정          : {'PASS' if ok else 'FAIL'}")
        if not is_real_ai:
            print(f"      → 실제 GPT 응답이 아닙니다 (source={source})")
        print()
        print("   응답:")
        for line in reply.splitlines()[:14]:
            print(f"     {line}")
        if len(reply.splitlines()) > 14:
            print("     …")
        print()

        passed += ok
        failed += not ok

    print("=" * 74)
    print(f"결과: PASS {passed} · FAIL {failed} / 전체 {len(QUESTIONS)}")
    print("=" * 74)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
