# 나만의 프롬프트 관리 프로그램 (Python Prompt Manager)

Python 기초 문법과 Git/GitHub 사용법을 익히기 위해 제작한 **콘솔 기반 프롬프트 관리 프로그램**입니다.
이전 미션에서 실제로 사용했던 프롬프트를 한곳에 모아 두고, 터미널에서 메뉴 번호를 입력해 목록 조회·카테고리별 조회·검색·상세 보기·즐겨찾기 관리를 수행합니다.

- GitHub 저장소: <https://github.com/art-ruby/ia-codyssey> — `assignments/A1-1/python-prompt-manager`
- 과제 제출보고서: [Python_Git_미션과제_제출보고서.md](Python_Git_미션과제_제출보고서.md)
- 수행 당시 Git 이력: [GIT_HISTORY.md](GIT_HISTORY.md)

---

## 1. 개발 환경

| 항목 | 내용 |
|---|---|
| 언어 | Python 3.11.9 (과제 요구: 3.10 이상) |
| 실행 환경 | Windows 11 / PowerShell 터미널 |
| 개발 도구 | Visual Studio Code (Python 확장) |
| 형상 관리 | Git 2.55.0 / GitHub |
| 사용 라이브러리 | `json`, `pathlib` (둘 다 표준 라이브러리) |

필수 기능은 **외부 라이브러리 없이 Python 기본 문법만으로** 구현했습니다. 별도의 설치 과정이 필요 없습니다.

---

## 2. 실행 방법

### 2.1 저장소 내려받기

```powershell
git clone https://github.com/art-ruby/ia-codyssey.git
```

```powershell
cd ia-codyssey/assignments/A1-1/python-prompt-manager
```

### 2.2 Python 버전 확인

```powershell
python --version
```

`Python 3.10` 이상이면 정상입니다. 실제 개발 환경은 `Python 3.11.9`입니다.

### 2.3 프로그램 실행

```powershell
python src/main.py
```

환경에 따라 Python 3 실행 명령이 `python3`인 경우에는 아래 명령을 사용합니다.

```powershell
python3 src/main.py
```

> `python` 대화형 입력창(`>>>`)이 아니라 **프로젝트 경로가 표시되는 터미널**에서 실행해야 합니다.
> `>>>` 상태에서 `python src/main.py`를 입력하면 `SyntaxError`가 발생합니다.

---

## 3. 메뉴와 기능

프로그램을 실행하면 아래 메뉴가 반복해서 표시되고, 각 기능을 수행한 뒤 다시 메뉴로 돌아옵니다.

```text
=== 나만의 프롬프트 관리 ===
1. 프롬프트 추가
2. 프롬프트 목록
3. 카테고리별 조회
4. 프롬프트 검색
5. 프롬프트 상세 보기
6. 즐겨찾기 관리
7. 즐겨찾기 목록
0. 종료
선택:
```

| 번호 | 메뉴 | 담당 함수 | 동작 |
|---:|---|---|---|
| 1 | 프롬프트 추가 | `add_prompt()` | 제목·내용을 입력받고 카테고리를 번호로 선택합니다. 빈 값이면 다시 입력을 요청합니다. 즐겨찾기 기본값은 `False`입니다. |
| 2 | 프롬프트 목록 | `show_list()` | 전체 프롬프트를 `번호. [카테고리] 제목 ⭐` 형식으로 출력하고 총 개수를 알려 줍니다. |
| 3 | 카테고리별 조회 | `show_by_category()` | 카테고리 6개를 보여 주고, 선택한 카테고리의 프롬프트만 출력합니다. 없으면 안내 메시지를 표시합니다. |
| 4 | 프롬프트 검색 | `search_prompt()` | 키워드가 제목·내용·카테고리에 포함된 프롬프트를 찾습니다. 영문은 대소문자를 구분하지 않습니다. |
| 5 | 프롬프트 상세 보기 | `show_detail()` | 번호를 입력받아 제목·카테고리·즐겨찾기·내용 전체를 출력합니다. 잘못된 번호는 안내 후 메뉴로 돌아갑니다. |
| 6 | 즐겨찾기 관리 | `toggle_favorite()` | 번호를 입력받아 즐겨찾기를 추가하거나 해제합니다. |
| 7 | 즐겨찾기 목록 | `show_favorites()` | `favorite`가 `True`인 프롬프트만 모아서 출력합니다. |
| 0 | 종료 | `main()` | 현재 목록을 저장한 뒤 프로그램을 종료합니다. |

`0`부터 `7` 이외의 값을 입력하면 `0부터 7까지 입력하세요.`를 출력하고 메뉴를 다시 보여 줍니다.

### 함수 구조

모든 코드를 한 함수에 몰아넣지 않고 기능별로 분리했습니다.

```text
main()                     # 메뉴 반복과 입력 분기
 ├─ show_menu()            # 메뉴 출력 및 선택값 반환
 ├─ load_prompts()         # JSON에서 프롬프트 불러오기
 ├─ save_prompts()         # JSON으로 프롬프트 저장
 ├─ print_summary_list()   # 목록 공통 출력(번호·카테고리·제목·⭐·총 개수)
 ├─ input_required()       # 빈 값이면 재입력 요청
 ├─ select_category()      # 카테고리 번호 선택 또는 직접 입력
 ├─ ask_prompt_number()    # 목록 번호 입력값 검증
 ├─ add_prompt()
 ├─ show_list()
 ├─ show_by_category()
 ├─ search_prompt()
 ├─ show_detail()
 ├─ toggle_favorite()
 └─ show_favorites()
```

---

## 4. 등록된 프롬프트 카테고리

프롬프트 추가 시 아래 6개 카테고리를 번호로 선택하거나, `0) 직접 입력`을 골라 새 카테고리를 입력할 수 있습니다.

| 번호 | 카테고리 | 기본 데이터 등록 여부 |
|---:|---|---|
| 1 | 텍스트 생성 | 등록 (맞춤형 글쓰기 프롬프트 생성) |
| 2 | 이미지 생성 | 미등록 |
| 3 | 영상 생성 | 등록 (심리학 롱폼 대본 및 이미지 제작) |
| 4 | 페르소나 | 미등록 |
| 5 | 자동화 | 등록 (AI 최신 뉴스 콘텐츠 패키지) |
| 6 | 기타 | 등록 (캐릭터 시트 생성기) |

이전 미션에서 작성한 프롬프트가 **기본 데이터로 4개** 등록되어 있어 과제 기준(최소 3개)을 충족합니다.

---

## 5. 데이터 구조와 저장 방식

프롬프트는 **리스트 안에 딕셔너리**를 담는 구조로 관리합니다.

```python
prompts = [
    {
        "title": "AI 최신 뉴스 콘텐츠 패키지",
        "content": "뉴스기사를 바탕으로 블로그, 이미지, 영상 콘텐츠를 제작하라.",
        "category": "자동화",
        "favorite": True
    }
]
```

| 필드 | 타입 | 설명 |
|---|---|---|
| `title` | string | 프롬프트 제목 |
| `content` | string | 프롬프트 본문 |
| `category` | string | 카테고리 |
| `favorite` | boolean | 즐겨찾기 여부 |

### JSON 영속화 (보너스 과제 1)

필수 요구사항은 "실행 중에만 데이터가 유지되고 종료 시 초기화"이지만, 보너스 과제를 반영하여 **종료 후에도 데이터가 유지되도록** `prompts.json` 저장·불러오기를 구현했습니다.

- 시작할 때 `prompts.json`을 UTF-8로 읽어 옵니다.
- 파일이 없거나 JSON이 손상된 경우 코드에 정의된 기본 프롬프트 3개로 파일을 다시 만듭니다.
- 프롬프트 추가, 즐겨찾기 변경, `0. 종료` 시점에 전체 목록을 저장합니다.
- 저장 시 `ensure_ascii=False`, `indent=2`를 사용해 한글을 그대로 유지합니다.
- `Path(__file__).parent.parent`로 경로를 계산하므로 실행 위치와 무관하게 프로젝트 루트의 데이터 파일을 사용합니다.

---

## 6. 실행 화면

아래는 실제 실행 결과를 그대로 옮긴 것입니다.

**프롬프트 목록 (메뉴 2)**

```text
=== 프롬프트 목록 ===
1. [자동화] AI 최신 뉴스 콘텐츠 패키지 ⭐
2. [영상 생성] 심리학 롱폼 대본 및 이미지 제작
3. [텍스트 생성] 맞춤형 글쓰기 프롬프트 생성
4. [기타] 캐릭터 시트 생성기

총 4개의 프롬프트
```

**카테고리별 조회 (메뉴 3)**

```text
=== 카테고리별 조회 ===
1) 텍스트 생성
2) 이미지 생성
3) 영상 생성
4) 페르소나
5) 자동화
6) 기타
선택: 1

[텍스트 생성] 카테고리 프롬프트:
1. [텍스트 생성] 맞춤형 글쓰기 프롬프트 생성

총 1개의 프롬프트
```

**프롬프트 검색 (메뉴 4)**

```text
=== 프롬프트 검색 ===
검색어: 심리학

검색 결과:
1. [영상 생성] 심리학 롱폼 대본 및 이미지 제작

총 1개의 프롬프트
```

**프롬프트 상세 보기 (메뉴 5)**

```text
=== 프롬프트 상세 보기 ===
번호 입력: 1

────────────────────────────
제목: AI 최신 뉴스 콘텐츠 패키지
카테고리: 자동화
즐겨찾기: ⭐
────────────────────────────
내용:
뉴스기사를 바탕으로 블로그, 이미지, 영상 콘텐츠를 제작하라.
────────────────────────────
```

**즐겨찾기 관리 (메뉴 6)**

```text
번호 입력: 2
'심리학 롱폼 대본 및 이미지 제작' 프롬프트를 즐겨찾기에 추가했습니다!
```

**입력값 검증**

```text
=== 프롬프트 추가 ===
제목: 값을 입력해야 합니다. 다시 입력하세요.
제목: 블로그 글 작성 도우미
```

```text
선택: 9
0부터 7까지 입력하세요.
```

---

## 7. 수행 순서 — 실제 입력한 명령어 정리

과제를 진행하면서 실제로 입력한 명령을 **수행 순서 그대로** 정리했습니다.
`기능 하나 구현 → 실행 확인 → 커밋` 순서를 지켰습니다.

### 1단계 — 개발 환경 확인

```powershell
python --version
```

```powershell
git --version
```

### 2단계 — Git 사용자 설정

```powershell
git config --global user.name "GitHub사용자이름"
```

```powershell
git config --global user.email "GitHub이메일"
```

```powershell
git config --global init.defaultBranch main
```

```powershell
git config --global --list
```

### 3단계 — Hello Python 실행

`hello.py`에 아래 코드를 작성합니다.

```python
print("Hello")
```

```powershell
python hello.py
```

### 4단계 — 로컬 저장소 초기화와 첫 커밋

```powershell
git init
```

```powershell
git status
```

```powershell
git add hello.py
```

```powershell
git commit -m "feat: Hello Python 실행"
```

### 5단계 — GitHub 원격 저장소 연결과 첫 push

```powershell
git remote add origin https://github.com/art-ruby/python-prompt-manager.git
```

```powershell
git push -u origin main
```

### 6단계 — README와 .gitignore 작성

`.gitignore` 내용은 다음과 같습니다.

```gitignore
__pycache__/
*.pyc
.venv/
venv/
.env
.vscode/
```

```powershell
git add .
```

```powershell
git commit -m "docs: README와 gitignore 추가"
```

```powershell
git push
```

### 7단계 — 프로젝트 구조와 기본 프롬프트 등록

```powershell
mkdir src
```

```powershell
python src/main.py
```

```powershell
git add src/main.py
```

```powershell
git commit -m "feat: 기본 프롬프트 3개 등록"
```

```powershell
git push
```

### 8단계 — 메뉴 구조와 프롬프트 추가 기능

```powershell
git commit -m "refactor: 메뉴를 과제 요구 순서의 7개 기능으로 재구성하고 show_menu() 분리"
```

```powershell
git commit -m "feat: 프롬프트 추가 시 빈 입력 재요청과 카테고리 번호 선택 구현"
```

### 9단계 — 별도 브랜치에서 목록 기능 개발 (checkout)

```powershell
git checkout -b feature/prompt-list
```

```powershell
git branch
```

```powershell
git commit -m "feat: 프롬프트 목록을 번호·카테고리·즐겨찾기 요약 형식으로 출력"
```

### 10단계 — main 브랜치로 병합 (merge)

```powershell
git checkout main
```

```powershell
git merge --no-ff feature/prompt-list -m "merge: feature/prompt-list 브랜치의 프롬프트 목록 기능을 main에 병합"
```

### 11단계 — 나머지 기능 구현

```powershell
git commit -m "feat: 카테고리별 조회 기능 구현"
```

```powershell
git commit -m "feat: 프롬프트 상세 보기 기능 구현"
```

```powershell
git commit -m "feat: 즐겨찾기 관리와 즐겨찾기 목록을 요약 목록 기반으로 정리"
```

```powershell
git commit -m "fix: 검색 결과 출력 형식을 통일하고 사용하지 않는 함수 제거"
```

### 12단계 — 공개 샘플 저장소 clone 확인

```powershell
git clone https://github.com/octocat/Hello-World.git sample-repo
```

```powershell
git log --oneline
```

구조와 로그를 확인한 뒤 샘플 폴더는 삭제했습니다.

### 13단계 — pull로 원격 변경 사항 반영

```powershell
git pull origin main
```

### 14단계 — 최종 확인과 제출

```powershell
git log --oneline --graph
```

```powershell
git push origin main
```

---

## 8. Git 사용 명령 충족 현황

과제가 요구하는 8개 명령을 모두 1회 이상 사용했습니다.

| 명령 | 사용 위치 |
|---|---|
| `init` | 4단계 — 로컬 저장소 초기화 |
| `add` | 4·6·7단계 — 커밋 전 스테이징 |
| `commit` | 전 단계 — 기능 단위 커밋 |
| `push` | 5·6·7·14단계 — GitHub 업로드 |
| `pull` | 13단계 — 원격 변경 사항 반영 |
| `checkout` | 9·10단계 — 브랜치 생성 및 전환 |
| `clone` | 12단계 — 공개 샘플 저장소 확인 |
| `merge` | 10단계 — `feature/prompt-list` → `main` 병합 |

### 브랜치 분기와 병합 기록

```text
* fix: 검색 결과 출력 형식을 통일하고 사용하지 않는 함수 제거
* feat: 즐겨찾기 관리와 즐겨찾기 목록을 요약 목록 기반으로 정리
* feat: 프롬프트 상세 보기 기능 구현
* feat: 카테고리별 조회 기능 구현
*   merge: feature/prompt-list 브랜치의 프롬프트 목록 기능을 main에 병합
|\
| * feat: 프롬프트 목록을 번호·카테고리·즐겨찾기 요약 형식으로 출력
|/
* feat: 프롬프트 추가 시 빈 입력 재요청과 카테고리 번호 선택 구현
* refactor: 메뉴를 과제 요구 순서의 7개 기능으로 재구성하고 show_menu() 분리
* chore: .gitnore 오탈자를 .gitignore로 수정하고 README 파일명 정리
```

---

## 9. 프로젝트 구조

```text
python-prompt-manager/
├── src/
│   └── main.py                            # 프로그램 본체 (기능별 함수 분리)
├── images/                                # 제출보고서 캡처 이미지 (수행 순서대로 정렬)
├── .gitignore                             # 캐시·가상환경·환경변수 제외 규칙
├── hello.py                               # Python 실행 확인용 첫 파일
├── prompts.json                           # 프롬프트 데이터 파일
├── README.md                              # 본 문서
└── Python_Git_미션과제_제출보고서.md      # 과제 제출보고서
```

---

## 10. 과제 요구사항 충족 현황

| 구분 | 요구사항 | 상태 |
|---|---|---|
| 프로그램 | 콘솔 메뉴 방식, 번호 선택, 종료, 메뉴 복귀 | 충족 |
| 프로그램 | 잘못된 번호 입력 시 안내 후 메뉴 재출력 | 충족 |
| 데이터 | 이전 미션 프롬프트 3개 이상 기본 등록 | 충족 (4개) |
| 데이터 | 리스트 + 딕셔너리 구조, 4개 필드 | 충족 |
| 기능 | 프롬프트 추가 (빈 값 재입력, 카테고리 선택) | 충족 |
| 기능 | 프롬프트 목록 (번호·카테고리·⭐·총 개수) | 충족 |
| 기능 | 카테고리별 조회 | 충족 |
| 기능 | 프롬프트 검색 (제목·내용) | 충족 (카테고리까지 검색) |
| 기능 | 프롬프트 상세 보기 (번호 검증) | 충족 |
| 기능 | 즐겨찾기 추가/해제 및 목록 | 충족 |
| 코드 | 기능별 함수 분리 | 충족 (15개 함수) |
| Git | 의미 있는 커밋 10개 이상 | 충족 (20개 이상) |
| Git | 브랜치 생성 및 병합 기록 | 충족 (`feature/prompt-list`) |
| Git | 8개 명령 각 1회 이상 사용 | 충족 |
| 문서 | README에 설명·실행법·기능·카테고리 | 충족 |
| 보너스 1 | JSON 저장·불러오기 | 구현 |
| 보너스 1 | 카테고리별 Markdown 내보내기 | 미구현 |
| 보너스 2 | 수정/삭제, 조회수, Top 목록 | 미구현 |

---

## 11. 사용 시 주의사항

- 저장은 `prompts.json` 전체를 덮어쓰는 방식입니다. 중요한 데이터가 있다면 실행 전에 백업해야 합니다.
- 손상된 JSON으로 실행하면 코드에 정의된 기본 프롬프트 3개로 파일이 다시 작성됩니다.
- 터미널에서 한글이나 `⭐`가 깨져 보이면 UTF-8을 지원하는 터미널과 글꼴을 사용해야 합니다.
- 즐겨찾기 변경과 상세 보기 번호는 **화면에 표시된 목록 번호**를 기준으로 합니다.
