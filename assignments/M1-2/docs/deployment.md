# Hermes 원격 연결 — Tailscale Funnel

상태: **로컬 중계 구현·검증 완료, Funnel 공개 연결·무인증 차단 확인, Render 원격 연결 미검증**. Tailscale Funnel을 통해 Render API가 이 PC의 Hermes를 호출하는 절차와 검증 기준을 기록한다. 원격 AI가 실제 동작한다고 확인되기 전에는 T08.02를 완료로 표시하지 않는다.

## 구성

```text
Render FastAPI
  → HTTPS + Bearer 중계 토큰
  → Tailscale Funnel 공개 HTTPS 주소
  → 이 PC의 127.0.0.1:8766 Hermes 중계 서버
  → HTTP + Hermes API 키
  → 이 PC의 127.0.0.1:8642 Hermes API
```

Funnel은 인터넷에서 접속 가능한 HTTPS 주소를 제공한다. Hermes API 포트 `8642`는 공개하지 않는다. Funnel은 `127.0.0.1:8766`에 바인딩된 별도 중계 서버만 대상으로 삼는다. 중계 서버는 다음 요청만 전달한다.

- `GET /v1/toolsets`
- `POST /v1/chat/completions`

두 요청 모두 전용 Bearer 중계 토큰이 있어야 한다. 중계 서버는 토큰을 확인한 뒤 요청의 인증값을 로컬 Hermes API 키로 바꿔 전달한다. 허용 목록 밖의 메서드·경로·쿼리는 거부한다.

## 비밀 설정

- 이 PC의 `.env`에서 `OPENAI_API_KEY`는 Hermes의 `API_SERVER_KEY`, `HERMES_RELAY_TOKEN`은 별도로 생성한 무작위 중계 토큰이다.
- Render 환경변수 `OPENAI_API_KEY`에는 Hermes 키가 아니라 같은 중계 토큰을 넣는다.
- Render `AI_PROVIDER_BASE_URL`은 `https://<Tailscale이 할당한 호스트명>/v1`로 설정한다. 모델과 Provider 경로는 현재 검증값인 `gpt-6-luna`, `openai-codex`를 사용한다.
- 두 비밀값을 서로 바꾸거나 같은 값으로 쓰지 않는다. 둘 다 Git, 브라우저 설정, 이 대화에 올리지 않는다.
- `.env`와 `.env.*`는 Git에서 제외된다. `.env.example`에는 값이 없는 변수 이름만 기록한다.

중계 토큰은 PowerShell에서 로컬로 생성한다. 출력된 값은 이 PC의 `.env`와 Render의 서버 환경변수에 직접 붙여넣고 대화창이나 저장소에 입력하지 않는다.

```powershell
$bytes = New-Object byte[] 32
[System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
[Convert]::ToBase64String($bytes)
```

## 로컬 확인 순서

1. 이 PC의 `.env`에 기존 Hermes `OPENAI_API_KEY`와 새 `HERMES_RELAY_TOKEN`을 각각 설정한다.
2. Hermes가 `127.0.0.1:8642`에서 실행 중인지 확인한다.
3. M1-2 폴더에서 중계 서버를 실행한다. 현재 기본 포트는 8766이다.

   ```powershell
   .\.venv\Scripts\python.exe server/scripts/run_hermes_relay.py
   ```

4. 별도의 PowerShell 창에서 로컬 중계 서버에 인증된 `GET /v1/toolsets`와 짧은 합성 텍스트 `POST /v1/chat/completions`를 보내고, 도구 세트가 모두 꺼져 있으며 텍스트 응답이 정상 종료되는지 확인한다. 잘못된 토큰, 허용하지 않은 경로, 쿼리 문자열, 1 MiB 초과 본문은 거부되어야 한다.
5. 확인 전까지 `tailscale funnel` 명령을 실행하지 않는다.

로컬 확인은 relay 구현과 이 PC 내부 연결만 검증한다. HTTPS 공개 주소나 Render까지의 연결을 검증한 것은 아니다.

## Funnel 활성화 — 로컬 검증 뒤 진행

이 PC에서 중계 서버가 실행 중이고 로컬 테스트를 통과한 뒤에만 실행한다.

```powershell
& "$env:ProgramFiles\Tailscale\tailscale.exe" funnel 8766
```

Tailscale CLI가 Funnel 활성화를 위한 웹 승인 절차를 열 수 있다. 승인 후 CLI가 출력하는 `https://<device>.<tailnet>.ts.net` 주소를 기록한다. `8766`은 이 PC의 로컬 중계 대상 포트이며, 외부 HTTPS는 Tailscale이 지원하는 공개 포트로 제공한다. 인증서와 DNS 준비 조건이 맞지 않으면 CLI 안내를 따른다.

상태 확인:

```powershell
& "$env:ProgramFiles\Tailscale\tailscale.exe" funnel status
```

공개 연결을 끌 때는 활성화한 설정을 끈다.

```powershell
& "$env:ProgramFiles\Tailscale\tailscale.exe" funnel 8766 off
```

Funnel은 인터넷에 공개되는 기능이다. AI API 경로는 중계 토큰으로 보호하지만, 토큰을 외부에 노출하면 누구든 허용된 호출을 시도할 수 있다. 테스트·사용이 끝나면 Funnel을 끄고, 토큰이 노출됐다고 의심되면 새 토큰으로 교체한다.

## Render 연결과 원격 검증

1. Render의 서버 환경변수에 `AI_PROVIDER_BASE_URL=https://<device>.<tailnet>.ts.net/v1`, `OPENAI_API_KEY=<중계 토큰>`, `AI_PROVIDER_MODEL=gpt-6-luna`, `AI_PROVIDER_ROUTE=openai-codex`를 설정한다. Firebase 서비스 계정 등 다른 서버 비밀값은 기존 절차대로 별도 설정한다.
2. 배포된 Render FastAPI가 `/v1/toolsets`를 통해 도구 비활성을 확인하고, 합성 텍스트 한 건이 `/v1/chat/completions`를 거쳐 정상 응답하는지 확인한다.
3. 로그·응답·브라우저 산출물에 중계 토큰, Hermes API 키, 입력 원문이 노출되지 않는지 확인한다.
4. 로컬 로그만으로 성공을 선언하지 않는다. 실제 요청이 Render → Funnel → 로컬 중계 → Hermes를 왕복해야 원격 경로가 검증된 것이다.

PC, Hermes, Tailscale 또는 중계 서버가 꺼져 있으면 Render의 AI 요청은 실패한다. 자동 Provider 전환이나 재시도는 하지 않는다.

## 현재 검증 결과와 남은 항목

- 로컬 Hermes의 `GET /v1/toolsets`와 텍스트 채팅은 T01.04에서 통과했고, 현재 선택된 경로는 `openai-codex` / `gpt-6-luna`다. 기록은 [verification.md](verification.md)에 있다.
- Tailscale Funnel을 활성화했다. `funnel status --json`에서 공개 HTTPS 443이 로컬 `127.0.0.1:8766`으로 연결됨을 확인했고, 공개 주소의 무인증 `GET /v1/toolsets`는 HTTP 401이었다. 공개 주소는 `https://win11-01.tailf062fb.ts.net`이다. 인증된 Render 왕복 호출은 아직 검증하지 않았다.
- 로컬 중계 테스트와 Render에서 실제로 수행한 왕복 요청만 `docs/verification.md`에 결과를 기록한다.

참고 문서: [Tailscale Funnel 안내](https://tailscale.com/docs/features/tailscale-funnel), [Funnel CLI](https://tailscale.com/docs/reference/tailscale-cli/funnel)
