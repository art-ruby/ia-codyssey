# Phase 01 검증 기록

기준일: 2026-10-01. 실제 호출 결과만 완료로 기록한다. API 키와 사용자 자료 원문은 이 문서나 Git에 넣지 않는다.

## T01.01·T01.02

- 산출물 커밋: `424961b8` (`feat(M1-2): establish Phase 01 server baseline`).
- Python 3.11.9 환경에서 `python -m pytest server/tests -q`: **7 passed**.
- 키를 비운 상태로 Uvicorn을 실행해 `/health` HTTP 200(`ai`, `firebase` 모두 `missing`)과 `/docs` HTTP 200을 확인했다.
- Git 제외 확인: `.env`, `.env.codyssey`, `.venv`, `.pytest_cache`.

## T01.03 — Codyssey GPT 텍스트 호출

**상태: 실제 호출 전. A25 미통과.** M1-1 구현은 Codyssey 프록시 주소와 OpenAI 호환 요청 형식을 보여주지만, 현재 작업 환경에서 프록시 API 키와 사용할 GPT 모델명은 확인되지 않았다. 로컬 `.env`의 값은 별도 Hermes 연결용이므로 Codyssey 호출 결과가 아니다.

`server/scripts/smoke_ai.py`는 `M1-2/.env.codyssey`만 읽고 프록시 주소가 `https://copa.codyssey.kr/v1`인지 확인한다. 기본 파일에는 주소만 넣어 두었다. API 키를 채팅이나 Git에 올리지 말고 `.env.codyssey`의 `OPENAI_API_KEY`에 직접 입력한다. `AI_PROVIDER_MODEL`에는 실제 프록시에서 제공되는 GPT 모델명을 넣는다. 모델을 모르면 키를 입력한 뒤 먼저 목록을 요청한다.

```powershell
.\.venv\Scripts\python.exe server/scripts/smoke_ai.py --list-models
.\.venv\Scripts\python.exe server/scripts/smoke_ai.py
```

실제 성공 시 요청 모델명, 응답 모델명, OpenAI SDK 버전, `choices[0].message.content`가 비지 않았는지, 종료 이유를 기록한다. 현재 설치된 SDK는 `openai` 3.22.1이다. 키가 비어 있을 때 스크립트는 호출 전에 종료 코드 1로 중단됐고, Hermes 설정 파일을 명시해도 주소 검사에서 호출 전에 중단됐다. 실제 Codyssey 응답, 이미지 입력 지원, 비용, 한도는 아직 미확인이다.

MVP 서버 실행 경로는 PRD §12에 따라 Codyssey 프록시를 사용한다. A25가 통과한 뒤 서버용 `.env`를 Codyssey 설정으로 맞추고, 별도 Hermes 설정은 Git에서 제외한 다른 파일로 보관한다.
