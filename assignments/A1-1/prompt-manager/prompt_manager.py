import json
import os
from data import CATEGORIES, prompts

# JSON 파일 경로
PROMPTS_FILE = "prompts.json"

# ================ 영속화 함수 ================

def load_prompts():
    """JSON 파일에서 프롬프트를 불러오는 함수"""
    global prompts
    if os.path.exists(PROMPTS_FILE):
        try:
            with open(PROMPTS_FILE, "r", encoding="utf-8") as f:
                prompts = json.load(f)
            print(f"✅ {len(prompts)}개의 프롬프트를 불러왔습니다.")
        except Exception as e:
            print(f"❌ 파일 불러오기 실패: {e}")
    else:
        print("저장된 파일이 없습니다. 기본 프롬프트 3개로 시작합니다.")

def save_prompts():
    """프롬프트를 JSON 파일로 저장하는 함수"""
    try:
        with open(PROMPTS_FILE, "w", encoding="utf-8") as f:
            json.dump(prompts, f, ensure_ascii=False, indent=2)
        print(f"✅ {len(prompts)}개의 프롬프트가 저장되었습니다.")
    except Exception as e:
        print(f"❌ 파일 저장 실패: {e}")

def export_to_markdown():
    """전체 프롬프트를 카테고리별 Markdown 파일로 내보내는 함수"""
    if not prompts:
        print("내보낼 프롬프트가 없습니다.")
        return

    try:
        # 카테고리별로 프롬프트를 그룹화
        category_prompts = {}
        for prompt in prompts:
            cat = prompt["category"]
            if cat not in category_prompts:
                category_prompts[cat] = []
            category_prompts[cat].append(prompt)

        # 각 카테고리별로 Markdown 파일 생성
        file_count = 0
        for category in CATEGORIES:
            if category in category_prompts:
                filename = f"prompts_{category}.md"
                with open(filename, "w", encoding="utf-8") as f:
                    f.write(f"# {category} 카테고리 프롬프트\n\n")
                    for prompt in category_prompts[category]:
                        f.write(f"## {prompt['title']}\n\n")
                        f.write(f"**조회수**: {prompt.get('view_count', 0)}\n\n")
                        f.write(f"**즐겨찾기**: {'⭐' if prompt['favorite'] else '☆'}\n\n")
                        f.write(f"{prompt['content']}\n\n")
                        f.write("---\n\n")
                file_count += 1

        print(f"✅ {file_count}개의 Markdown 파일로 내보내졌습니다.")
    except Exception as e:
        print(f"❌ 내보내기 실패: {e}")

# ================ 기본 기능 ================

def add_prompt():
    """새로운 프롬프트를 추가하는 함수"""
    print("\n" + "="*40)
    print("프롬프트 추가")
    print("="*40)

    # 제목 입력
    while True:
        title = input("제목: ").strip()
        if title:
            break
        print("제목을 입력해주세요.")

    # 내용 입력
    while True:
        content = input("내용: ").strip()
        if content:
            break
        print("내용을 입력해주세요.")

    # 카테고리 선택
    print("\n카테고리 선택:")
    for i, category in enumerate(CATEGORIES, 1):
        print(f"{i}) {category}")

    while True:
        try:
            choice = int(input("선택: "))
            if 1 <= choice <= len(CATEGORIES):
                category = CATEGORIES[choice - 1]
                break
            else:
                print("올바른 번호를 입력해주세요.")
        except ValueError:
            print("숫자를 입력해주세요.")

    # 프롬프트 추가
    new_prompt = {
        "title": title,
        "content": content,
        "category": category,
        "favorite": False,
        "view_count": 0
    }
    prompts.append(new_prompt)
    save_prompts()

    print(f"\n✅ '{title}' 프롬프트가 추가되었습니다!")

def show_list():
    """저장된 모든 프롬프트를 보는 함수"""
    print("\n" + "="*40)
    print("프롬프트 목록")
    print("="*40)

    if not prompts:
        print("저장된 프롬프트가 없습니다.")
        return

    for i, prompt in enumerate(prompts, 1):
        favorite_mark = "⭐" if prompt["favorite"] else " "
        view_count = prompt.get("view_count", 0)
        print(f"{i}. [{prompt['category']}] {prompt['title']} {favorite_mark} (조회: {view_count})")

    print(f"\n총 {len(prompts)}개의 프롬프트")

def show_detail():
    """선택한 프롬프트의 상세 정보를 보는 함수"""
    print("\n" + "="*40)
    print("프롬프트 상세 보기")
    print("="*40)

    if not prompts:
        print("저장된 프롬프트가 없습니다.")
        return

    try:
        num = int(input("번호 입력: "))
        if 1 <= num <= len(prompts):
            prompt = prompts[num - 1]
            favorite_mark = "⭐" if prompt["favorite"] else " "
            view_count = prompt.get("view_count", 0)

            # 조회수 증가
            prompts[num - 1]["view_count"] = view_count + 1
            save_prompts()

            print("\n" + "-"*40)
            print(f"제목: {prompt['title']}")
            print(f"카테고리: {prompt['category']}")
            print(f"즐겨찾기: {favorite_mark}")
            print(f"조회수: {view_count + 1}")
            print("-"*40)
            print(f"내용:\n{prompt['content']}")
            print("-"*40)
        else:
            print("존재하지 않는 번호입니다.")
    except ValueError:
        print("숫자를 입력해주세요.")

def search_prompt():
    """키워드로 프롬프트를 검색하는 함수"""
    print("\n" + "="*40)
    print("프롬프트 검색")
    print("="*40)

    if not prompts:
        print("저장된 프롬프트가 없습니다.")
        return

    keyword = input("검색어: ").strip()

    if not keyword:
        print("검색어를 입력해주세요.")
        return

    results = []
    for i, prompt in enumerate(prompts):
        if keyword.lower() in prompt["title"].lower() or keyword.lower() in prompt["content"].lower():
            results.append((i + 1, prompt))

    if results:
        print(f"\n검색 결과:")
        for num, prompt in results:
            favorite_mark = "⭐" if prompt["favorite"] else " "
            view_count = prompt.get("view_count", 0)
            print(f"{num}. [{prompt['category']}] {prompt['title']} {favorite_mark} (조회: {view_count})")
        print(f"\n{len(results)}개의 프롬프트를 찾았습니다.")
    else:
        print(f"\n'{keyword}'를 포함하는 프롬프트가 없습니다.")

def show_by_category():
    """카테고리별로 프롬프트를 조회하는 함수"""
    print("\n" + "="*40)
    print("카테고리별 조회")
    print("="*40)

    if not prompts:
        print("저장된 프롬프트가 없습니다.")
        return

    print("\n카테고리 선택:")
    for i, category in enumerate(CATEGORIES, 1):
        print(f"{i}) {category}")

    try:
        choice = int(input("\n선택: "))
        if 1 <= choice <= len(CATEGORIES):
            selected_category = CATEGORIES[choice - 1]

            print(f"\n[{selected_category}] 카테고리 프롬프트:")
            results = []
            for i, prompt in enumerate(prompts):
                if prompt["category"] == selected_category:
                    results.append((i + 1, prompt))

            if results:
                for num, prompt in results:
                    favorite_mark = "⭐" if prompt["favorite"] else " "
                    view_count = prompt.get("view_count", 0)
                    print(f"{num}. {prompt['title']} {favorite_mark} (조회: {view_count})")
                print(f"\n총 {len(results)}개의 프롬프트")
            else:
                print(f"{selected_category} 카테고리에 프롬프트가 없습니다.")
        else:
            print("올바른 번호를 입력해주세요.")
    except ValueError:
        print("숫자를 입력해주세요.")

def toggle_favorite():
    """프롬프트의 즐겨찾기를 추가/해제하는 함수"""
    print("\n" + "="*40)
    print("즐겨찾기 관리")
    print("="*40)

    if not prompts:
        print("저장된 프롬프트가 없습니다.")
        return

    try:
        num = int(input("프롬프트 번호 입력: "))
        if 1 <= num <= len(prompts):
            prompt = prompts[num - 1]

            if prompt["favorite"]:
                prompt["favorite"] = False
                print(f"\n❌ '{prompt['title']}' 프롬프트를 즐겨찾기에서 제거했습니다!")
            else:
                prompt["favorite"] = True
                print(f"\n⭐ '{prompt['title']}' 프롬프트를 즐겨찾기에 추가했습니다!")
            save_prompts()
        else:
            print("존재하지 않는 번호입니다.")
    except ValueError:
        print("숫자를 입력해주세요.")

def show_favorites():
    """즐겨찾기된 프롬프트 목록을 보는 함수"""
    print("\n" + "="*40)
    print("즐겨찾기 목록")
    print("="*40)

    favorites = []
    for i, prompt in enumerate(prompts):
        if prompt["favorite"]:
            favorites.append((i + 1, prompt))

    if favorites:
        for num, prompt in favorites:
            view_count = prompt.get("view_count", 0)
            print(f"{num}. [{prompt['category']}] {prompt['title']} ⭐ (조회: {view_count})")
        print(f"\n총 {len(favorites)}개의 즐겨찾기")
    else:
        print("즐겨찾기된 프롬프트가 없습니다.")

# ================ 보너스 기능 ================

def update_prompt():
    """프롬프트를 수정하는 함수"""
    print("\n" + "="*40)
    print("프롬프트 수정")
    print("="*40)

    if not prompts:
        print("저장된 프롬프트가 없습니다.")
        return

    try:
        num = int(input("수정할 프롬프트 번호 입력: "))
        if 1 <= num <= len(prompts):
            prompt = prompts[num - 1]

            print(f"\n현재 제목: {prompt['title']}")
            print("(엔터를 누르면 기존 값 유지)")

            # 제목 수정
            new_title = input("새 제목: ").strip()
            if new_title:
                prompt["title"] = new_title

            # 내용 수정
            print(f"\n현재 내용: {prompt['content'][:50]}...")
            new_content = input("새 내용: ").strip()
            if new_content:
                prompt["content"] = new_content

            # 카테고리 수정
            print(f"\n현재 카테고리: {prompt['category']}")
            print("새 카테고리 선택 (엔터를 누르면 기존 값 유지):")
            for i, category in enumerate(CATEGORIES, 1):
                print(f"{i}) {category}")

            try:
                choice = input("선택: ").strip()
                if choice:
                    choice = int(choice)
                    if 1 <= choice <= len(CATEGORIES):
                        prompt["category"] = CATEGORIES[choice - 1]
                    else:
                        print("올바른 번호를 입력해주세요.")
            except ValueError:
                print("숫자를 입력해주세요.")

            save_prompts()
            print(f"\n✅ '{prompt['title']}' 프롬프트가 수정되었습니다!")
        else:
            print("존재하지 않는 번호입니다.")
    except ValueError:
        print("숫자를 입력해주세요.")

def delete_prompt():
    """프롬프트를 삭제하는 함수"""
    print("\n" + "="*40)
    print("프롬프트 삭제")
    print("="*40)

    if not prompts:
        print("저장된 프롬프트가 없습니다.")
        return

    try:
        num = int(input("삭제할 프롬프트 번호 입력: "))
        if 1 <= num <= len(prompts):
            prompt = prompts[num - 1]
            title = prompt["title"]

            # 확인
            confirm = input(f"'{title}' 프롬프트를 정말 삭제하시겠습니까? (y/n): ").strip().lower()
            if confirm == "y":
                prompts.pop(num - 1)
                save_prompts()
                print(f"✅ '{title}' 프롬프트가 삭제되었습니다!")
            else:
                print("삭제가 취소되었습니다.")
        else:
            print("존재하지 않는 번호입니다.")
    except ValueError:
        print("숫자를 입력해주세요.")

def show_top_prompts():
    """조회수가 높은 프롬프트 Top 목록을 보는 함수"""
    print("\n" + "="*40)
    print("인기 프롬프트 (조회수 기준)")
    print("="*40)

    if not prompts:
        print("저장된 프롬프트가 없습니다.")
        return

    # 조회수로 정렬 (내림차순)
    sorted_prompts = sorted(enumerate(prompts, 1), key=lambda x: x[1].get("view_count", 0), reverse=True)

    print("\n조회수 기준 정렬:\n")
    for rank, (num, prompt) in enumerate(sorted_prompts, 1):
        favorite_mark = "⭐" if prompt["favorite"] else " "
        view_count = prompt.get("view_count", 0)
        print(f"{rank}. {prompt['title']} {favorite_mark}")
        print(f"   카테고리: {prompt['category']} | 조회수: {view_count}")
        print()

def show_menu():
    """메뉴를 출력하는 함수"""
    print("\n" + "="*40)
    print("    나만의 프롬프트 관리")
    print("="*40)
    print("1. 프롬프트 추가")
    print("2. 프롬프트 목록")
    print("3. 카테고리별 조회")
    print("4. 프롬프트 검색")
    print("5. 프롬프트 상세 보기")
    print("6. 즐겨찾기 관리")
    print("7. 즐겨찾기 목록")
    print("8. 프롬프트 수정")
    print("9. 프롬프트 삭제")
    print("10. 인기 프롬프트 (Top)")
    print("11. Markdown으로 내보내기")
    print("12. 프롬프트 저장")
    print("0. 종료")
    print("="*40)

def main():
    """메인 루프"""
    load_prompts()  # 시작할 때 저장된 프롬프트 불러오기

    while True:
        show_menu()
        choice = input("선택: ").strip()

        if choice == "0":
            save_prompts()  # 종료 전 저장
            print("프로그램을 종료합니다.")
            break
        elif choice == "1":
            add_prompt()
        elif choice == "2":
            show_list()
        elif choice == "3":
            show_by_category()
        elif choice == "4":
            search_prompt()
        elif choice == "5":
            show_detail()
        elif choice == "6":
            toggle_favorite()
        elif choice == "7":
            show_favorites()
        elif choice == "8":
            update_prompt()
        elif choice == "9":
            delete_prompt()
        elif choice == "10":
            show_top_prompts()
        elif choice == "11":
            export_to_markdown()
        elif choice == "12":
            save_prompts()
        else:
            print("잘못된 선택입니다. 다시 입력해주세요.")

if __name__ == "__main__":
    main()
