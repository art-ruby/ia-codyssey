# ia-codyssey

코디세이(Codyssey) 과정에서 수행한 과제를 한 저장소에서 순차적으로 관리하는 저장소입니다.
모든 과제물은 `assignments/` 아래에 **과제 코드 폴더** 단위로 보관합니다.

## 과제 목록

| 과제 | 주제 | 폴더 |
|---|---|---|
| A1-1 | Python & Git 기초 — 나만의 프롬프트 관리 프로그램 | [assignments/A1-1](assignments/A1-1) |
| A1-3 | LAPIS 향 큐레이터 서비스 | [assignments/a1-3](assignments/a1-3) |
| B1-1 | 브랜드 기획 | [assignments/B1-1](assignments/B1-1) |
| B1-2 | 브랜드 홈페이지 | [assignments/B1-2](assignments/B1-2) |
| B1-3 | 노코드 자동화 기초 — 워크플로우 설계 | [assignments/B1-3](assignments/B1-3) |

각 폴더의 `README.md`에 해당 과제의 개요, 실행 방법, 제출물이 정리되어 있습니다.

## 저장소 규칙

- 과제물은 새 저장소를 만들지 않고 `assignments/<과제코드>/` 아래에 추가합니다.
- 실행 결과물, 의존성, 비밀 정보는 커밋하지 않습니다. 제외 규칙은 [.gitignore](.gitignore)에 정의되어 있습니다.
  - 의존성: `node_modules/`, `.venv/`, `__pycache__/`
  - 비밀 정보: `.env`, `.env.local` (형식 예시는 `.env.example`로 대체)
  - 로컬 산출물: `.vercel/`, 로그 파일, Office 임시 파일(`~$*`)

## 에이전트 작업 규칙

- [CLAUDE.md](CLAUDE.md)
