import json
from pathlib import Path


print("Prompt Manager 시작")


DATA_FILE = Path(__file__).parent.parent / "prompts.json"

DEFAULT_PROMPTS = [
    {
        "title": "AI 최신 뉴스 콘텐츠 패키지",
        "content": "뉴스기사를 바탕으로 블로그, 이미지, 영상 콘텐츠를 제작하라.",
        "category": "자동화",
        "favorite": False,
    },
    {
        "title": "심리학 롱폼 대본 및 이미지 제작",
        "content": "심리학 주제를 2D 애니메이션 롱폼 대본과 이미지 프롬프트로 제작하라.",
        "category": "영상 생성",
        "favorite": False,
    },
    {
        "title": "맞춤형 글쓰기 프롬프트 생성",
        "content": "사용자의 요구사항을 질문하고 맞춤형 글쓰기 프롬프트를 생성하라.",
        "category": "텍스트 생성",
        "favorite": False,
    },
]


def load_prompts():
    """JSON 파일에서 프롬프트를 불러옵니다. 파일이 없으면 기본값을 사용합니다."""
    if not DATA_FILE.exists():
        save_prompts(DEFAULT_PROMPTS)
        return DEFAULT_PROMPTS.copy()

    try:
        with DATA_FILE.open("r", encoding="utf-8") as file:
            data = json.load(file)
        if isinstance(data, list):
            return data
    except (json.JSONDecodeError, OSError):
        print("저장 파일을 읽지 못해 기본 프롬프트를 사용합니다.")

    save_prompts(DEFAULT_PROMPTS)
    return DEFAULT_PROMPTS.copy()


def save_prompts(prompt_list):
    """현재 프롬프트 목록을 JSON 파일에 저장합니다."""
    with DATA_FILE.open("w", encoding="utf-8") as file:
        json.dump(prompt_list, file, ensure_ascii=False, indent=2)


prompts = load_prompts()


def print_prompt(number, prompt):
    favorite = "★" if prompt.get("favorite", False) else "☆"
    print(f"\n{number}. {prompt['title']}")
    print(f"카테고리: {prompt['category']}")
    print(f"즐겨찾기: {favorite}")
    print(f"내용: {prompt['content']}")


def show_all_prompts():
    print("\n[전체 프롬프트]")
    if not prompts:
        print("등록된 프롬프트가 없습니다.")
        return
    for number, prompt in enumerate(prompts, start=1):
        print_prompt(number, prompt)


def search_prompts():
    keyword = input("\n검색어를 입력하세요: ").strip().lower()
    if not keyword:
        print("검색어를 입력해야 합니다.")
        return

    results = [
        prompt
        for prompt in prompts
        if keyword in prompt["title"].lower()
        or keyword in prompt["content"].lower()
        or keyword in prompt["category"].lower()
    ]

    print(f"\n[검색 결과: {len(results)}개]")
    if not results:
        print("검색 결과가 없습니다.")
        return
    for number, prompt in enumerate(results, start=1):
        print_prompt(number, prompt)


def add_prompt():
    print("\n[새 프롬프트 추가]")
    title = input("프롬프트 제목: ").strip()
    content = input("프롬프트 내용: ").strip()
    category = input("카테고리: ").strip()

    if not title or not content or not category:
        print("제목, 내용, 카테고리를 모두 입력해야 합니다.")
        return

    prompts.append(
        {
            "title": title,
            "content": content,
            "category": category,
            "favorite": False,
        }
    )
    save_prompts(prompts)
    print("\n새 프롬프트가 추가되고 저장되었습니다.")


def show_favorites():
    print("\n[즐겨찾기 프롬프트]")
    favorites = [prompt for prompt in prompts if prompt.get("favorite", False)]
    if not favorites:
        print("즐겨찾기한 프롬프트가 없습니다.")
        return
    for number, prompt in enumerate(favorites, start=1):
        print_prompt(number, prompt)


def toggle_favorite():
    show_all_prompts()
    if not prompts:
        return

    try:
        number = int(input("\n즐겨찾기를 변경할 번호: "))
        prompt = prompts[number - 1]
    except (ValueError, IndexError):
        print("올바른 번호를 입력하세요.")
        return

    prompt["favorite"] = not prompt.get("favorite", False)
    save_prompts(prompts)
    status = "추가" if prompt["favorite"] else "해제"
    print(f"'{prompt['title']}' 즐겨찾기가 {status}되었습니다.")


def main():
    while True:
        print("\n========== Prompt Manager ==========")
        print("1. 전체 프롬프트 보기")
        print("2. 프롬프트 검색")
        print("3. 새 프롬프트 추가")
        print("4. 즐겨찾기 보기")
        print("5. 즐겨찾기 설정/해제")
        print("6. 종료")

        choice = input("\n메뉴를 선택하세요: ").strip()

        if choice == "1":
            show_all_prompts()
        elif choice == "2":
            search_prompts()
        elif choice == "3":
            add_prompt()
        elif choice == "4":
            show_favorites()
        elif choice == "5":
            toggle_favorite()
        elif choice == "6":
            save_prompts(prompts)
            print("\nPrompt Manager를 종료합니다.")
            break
        else:
            print("1부터 6까지 입력하세요.")


if __name__ == "__main__":
    main()