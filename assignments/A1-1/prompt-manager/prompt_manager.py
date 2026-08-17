from data import CATEGORIES, prompts
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
        "favorite": False
    }
    prompts.append(new_prompt)
    
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
        print(f"{i}. [{prompt['category']}] {prompt['title']} {favorite_mark}")
    
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
            
            print("\n" + "-"*40)
            print(f"제목: {prompt['title']}")
            print(f"카테고리: {prompt['category']}")
            print(f"즐겨찾기: {favorite_mark}")
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
            print(f"{num}. [{prompt['category']}] {prompt['title']} {favorite_mark}")
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
                    print(f"{num}. {prompt['title']} {favorite_mark}")
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
            print(f"{num}. [{prompt['category']}] {prompt['title']} ⭐")
        print(f"\n총 {len(favorites)}개의 즐겨찾기")
    else:
        print("즐겨찾기된 프롬프트가 없습니다.") 
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
    print("0. 종료")
    print("="*40)

def main():
    """메인 루프"""
    while True:
        show_menu()
        choice = input("선택: ").strip()
        
        if choice == "0":
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
        else:
            print("잘못된 선택입니다. 다시 입력해주세요.")

if __name__ == "__main__":
    main()