# M1-2 — AI Agent 개발: 나만의 AI 비서 구축

**AI Secretary**의 기획 문서와 MVP 구현을 함께 관리합니다. 인증·데이터 기반·웹 공통 화면을 구현했고, 자료 분석·채팅·배포는 아직 진행 중입니다.

| 문서 | 내용 |
|---|---|
| [ai-secretary/AI_SECRETARY_SCENARIO.md](ai-secretary/AI_SECRETARY_SCENARIO.md) | 사용자 시나리오 — 비서가 필요한 이유와 사용 장면 |
| [mockup/index.html](mockup/index.html) | 10개 메뉴 단일 HTML 화면 목업 (실제 연결 없음) |
| [prd.md](prd.md) | MVP 제품 요구사항 명세서 — 범위, 화면, 데이터, 승인 규칙, API, 인수 기준 |
| [task.md](task.md) | Phase별 완료 상태와 다음 작업 |
| [.env.example](.env.example) | 환경변수 이름 예시. 실제 키는 `.env`에만 두고 커밋하지 않습니다. |

## 로컬 Hermes AI 연결

FastAPI 서버는 `M1-2/.env`의 Hermes API 주소·키·모델·구독 경로를 읽습니다. 현재 확인된 경로는 `http://127.0.0.1:8642/v1`, `openai-codex`, `gpt-6-luna`입니다. `OPENAI_API_KEY`에는 Hermes의 API 서버 키를 넣으며 구독 계정 자격증명을 웹이나 저장소에 넣지 않습니다.

Hermes 호스트의 `config.yaml`에서 `platform_toolsets.api_server: [no_mcp]`로 설정해 API 호출에 파일·터미널·MCP 도구가 붙지 않게 합니다. 서버 Adapter도 호출 전에 `/v1/toolsets`를 확인해 도구가 활성화됐으면 중단합니다. 로컬 검증 명령은 `./.venv/Scripts/python.exe server/scripts/smoke_hermes.py`이며 성공 시 모델·정상 종료·토큰 수만 출력합니다.

이 연결은 로컬 텍스트 호출까지 확인한 상태입니다. 자료 기반 분석과 채팅 화면은 [task.md](task.md)의 T04.01·T07.02 이후 연결됩니다. Render에서는 이 PC의 loopback 주소로 접속할 수 없어 별도의 인증된 Hermes 배포 경로가 필요합니다.


## Telegram Bot 연동

Telegram은 AI Secretary API의 webhook(`/api/telegram/webhook`)으로 연결한다. 서버가 기존 채팅 문맥과 Hermes Provider를 재사용하므로, Hermes에 직접 연결하지 않는다. 필요한 Render 환경변수는 `TELEGRAM_BOT_TOKEN`, `TELEGRAM_ALLOWED_CHAT_ID`, `TELEGRAM_WEBHOOK_SECRET`이며, 설정 절차는 `docs/deployment.md`의 "Telegram Bot 연동"을 따른다.
