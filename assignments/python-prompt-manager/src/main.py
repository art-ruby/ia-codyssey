import json
from pathlib import Path


DATA_FILE = Path(__file__).parent.parent / "prompts.json"

CATEGORIES = [
    "텍스트 생성",
    "이미지 생성",
    "영상 생성",
    "페르소나",
    "자동화",
    "기타",
]

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


def print_summary_list(prompt_list):
    """번호, 카테고리, 제목, 즐겨찾기 표시를 한 줄씩 출력하고 총 개수를 알립니다."""
    for number, prompt in enumerate(prompt_list, start=1):
        star = " ⭐" if prompt.get("favorite", False) else ""
        print(f"{number}. [{prompt['category']}] {prompt['title']}{star}")
    print(f"\n총 {len(prompt_list)}개의 프롬프트")


def show_list(prompts):
    print("\n=== 프롬프트 목록 ===")
    if not prompts:
        print("등록된 프롬프트가 없습니다.")
        return
    print_summary_list(prompts)


def search_prompt(prompts):
    print("\n=== 프롬프트 검색 ===")
    keyword = input("검색어: ").strip().lower()
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

    if not results:
        print("검색 결과가 없습니다.")
        return

    print("\n검색 결과:")
    print_summary_list(results)


def input_required(label):
    """빈 값이 입력되면 값이 채워질 때까지 다시 입력을 요청합니다."""
    while True:
        value = input(label).strip()
        if value:
            return value
        print("값을 입력해야 합니다. 다시 입력하세요.")


def select_category():
    """미리 정의된 카테고리를 번호로 선택하거나 직접 입력합니다."""
    print("\n카테고리 선택:")
    for number, category in enumerate(CATEGORIES, start=1):
        print(f"{number}) {category}")
    print("0) 직접 입력")

    while True:
        choice = input("선택: ").strip()
        if choice == "0":
            return input_required("카테고리 이름: ")
        if choice.isdigit() and 1 <= int(choice) <= len(CATEGORIES):
            return CATEGORIES[int(choice) - 1]
        print(f"0부터 {len(CATEGORIES)}까지 입력하세요.")


def add_prompt(prompts):
    print("\n=== 프롬프트 추가 ===")
    title = input_required("제목: ")
    content = input_required("내용: ")
    category = select_category()

    prompts.append(
        {
            "title": title,
            "content": content,
            "category": category,
            "favorite": False,
        }
    )
    save_prompts(prompts)
    print("\n프롬프트가 추가되었습니다!")


def show_by_category(prompts):
    print("\n=== 카테고리별 조회 ===")
    for number, category in enumerate(CATEGORIES, start=1):
        print(f"{number}) {category}")

    choice = input("선택: ").strip()
    if not choice.isdigit() or not 1 <= int(choice) <= len(CATEGORIES):
        print(f"1부터 {len(CATEGORIES)}까지 입력하세요.")
        return

    category = CATEGORIES[int(choice) - 1]
    results = [prompt for prompt in prompts if prompt["category"] == category]

    print(f"\n[{category}] 카테고리 프롬프트:")
    if not results:
        print("해당 카테고리에 등록된 프롬프트가 없습니다.")
        return
    print_summary_list(results)


def ask_prompt_number(prompts):
    """목록 번호를 입력받아 해당 프롬프트를 반환합니다. 잘못된 번호면 None을 반환합니다."""
    choice = input("번호 입력: ").strip()
    if not choice.isdigit() or not 1 <= int(choice) <= len(prompts):
        print(f"1부터 {len(prompts)}까지의 번호를 입력하세요.")
        return None
    return prompts[int(choice) - 1]


def show_detail(prompts):
    print("\n=== 프롬프트 상세 보기 ===")
    if not prompts:
        print("등록된 프롬프트가 없습니다.")
        return

    print_summary_list(prompts)
    prompt = ask_prompt_number(prompts)
    if prompt is None:
        return

    favorite = "⭐" if prompt.get("favorite", False) else "☆"
    print("\n" + "─" * 28)
    print(f"제목: {prompt['title']}")
    print(f"카테고리: {prompt['category']}")
    print(f"즐겨찾기: {favorite}")
    print("─" * 28)
    print("내용:")
    print(prompt["content"])
    print("─" * 28)


def toggle_favorite(prompts):
    print("\n=== 즐겨찾기 관리 ===")
    if not prompts:
        print("등록된 프롬프트가 없습니다.")
        return

    print_summary_list(prompts)
    prompt = ask_prompt_number(prompts)
    if prompt is None:
        return

    prompt["favorite"] = not prompt.get("favorite", False)
    save_prompts(prompts)
    status = "즐겨찾기에 추가" if prompt["favorite"] else "즐겨찾기에서 해제"
    print(f"'{prompt['title']}' 프롬프트를 {status}했습니다!")


def show_favorites(prompts):
    print("\n=== 즐겨찾기 목록 ===")
    favorites = [prompt for prompt in prompts if prompt.get("favorite", False)]
    if not favorites:
        print("즐겨찾기한 프롬프트가 없습니다.")
        return
    print_summary_list(favorites)


def show_menu():
    """메뉴를 출력하고 사용자가 입력한 번호를 반환합니다."""
    print("\n=== 나만의 프롬프트 관리 ===")
    print("1. 프롬프트 추가")
    print("2. 프롬프트 목록")
    print("3. 카테고리별 조회")
    print("4. 프롬프트 검색")
    print("5. 프롬프트 상세 보기")
    print("6. 즐겨찾기 관리")
    print("7. 즐겨찾기 목록")
    print("0. 종료")
    return input("선택: ").strip()


def main():
    prompts = load_prompts()

    while True:
        choice = show_menu()

        if choice == "1":
            add_prompt(prompts)
        elif choice == "2":
            show_list(prompts)
        elif choice == "3":
            show_by_category(prompts)
        elif choice == "4":
            search_prompt(prompts)
        elif choice == "5":
            show_detail(prompts)
        elif choice == "6":
            toggle_favorite(prompts)
        elif choice == "7":
            show_favorites(prompts)
        elif choice == "0":
            save_prompts(prompts)
            print("\n프로그램을 종료합니다.")
            break
        else:
            print("0부터 7까지 입력하세요.")


if __name__ == "__main__":
    main()
