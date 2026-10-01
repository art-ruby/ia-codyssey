# Tailscale Funnel 기반 Hermes 중계 설계

## 목표

이 PC와 Tailscale이 켜져 있을 때 Render에 배포된 AI Secretary API가 이 PC의 Hermes API를 사용할 수 있게 합니다. Hermes 포트와 Hermes API 키는 인터넷에 직접 공개하지 않습니다.

## 현재 상태와 배경

- Hermes는 이 PC의 `http://127.0.0.1:8642/v1`에서 요청을 받습니다.
- 기존 AI Provider는 `AI_PROVIDER_BASE_URL`을 기준으로 `GET /toolsets`와 `POST /chat/completions`를 호출하고, Bearer 키로 인증합니다.
- Render에서는 이 PC의 loopback 주소에 접속할 수 없습니다.
- 외부 연결 방식으로 Tailscale Funnel을 선택했습니다. Funnel HTTPS 주소는 인터넷에서 접속할 수 있으므로, 중계 서버가 매 요청을 인증하고 Provider에 필요한 경로만 허용해야 합니다.
- Tailscale은 설치되어 있고 기기가 온라인입니다. Funnel은 아직 켜지 않았습니다.

## 선택한 구성

```text
Render FastAPI
  -- HTTPS + Bearer 중계 토큰 --> Tailscale Funnel 공개 주소
    --> 이 PC의 loopback 전용 Hermes 중계 서버
      -- HTTP + Hermes API 키 --> 127.0.0.1:8642의 Hermes
```

중계 서버는 별도 프로세스로 실행하고 `127.0.0.1`에만 바인딩합니다. Funnel은 Hermes가 아니라 중계 서버로 연결합니다. 공개 구간에서는 기존 `OPENAI_API_KEY` 설정에 중계 토큰을 넣습니다. 중계 서버는 Bearer 값을 검증한 뒤, 별도로 보관한 로컬 Hermes API 키로 바꿔 Hermes에 전달합니다. 두 키 모두 로그에 남기거나 응답으로 돌려주지 않습니다.

## 중계 서버 API 계약

다음 두 요청만 허용합니다.

- `GET /v1/toolsets`
- `POST /v1/chat/completions`

그 밖의 메서드, 경로, 쿼리 문자열은 모두 거부합니다. 범용 프록시, 임의 경로 전달, 리다이렉트, Hermes의 다른 API 접근 기능은 제공하지 않습니다. 요청자가 보낸 Authorization 헤더나 hop-by-hop 헤더를 Hermes에 전달하지 않습니다. 로컬 Hermes 키를 사용해 새 요청을 만들고, Hermes가 처리하는 데 필요한 최소한의 Content 헤더와 JSON 본문만 전달합니다.

중계 서버는 다음 조건을 지켜야 합니다.

- 중계 토큰 비교에 상수 시간 비교를 사용합니다.
- 토큰이 없거나 틀리면 Hermes에 연결하기 전에 거부합니다.
- `127.0.0.1`에만 바인딩합니다.
- 요청 본문 크기는 1 MiB로 제한합니다.
- 설정된 AI 요청 제한 시간을 사용하되 최대 120초로 제한합니다.
- Hermes에 연결할 수 없을 때 비밀정보가 포함되지 않은 일반 오류를 반환합니다.
- 요청 본문, 인증 값, 응답 본문, 상위 서버 예외의 상세 내용을 로그에 남기지 않습니다.

## 설정과 비밀정보 관리

- 로컬 Hermes API 키는 이 PC의 Git 제외 환경설정 파일에만 보관합니다.
- 별도로 생성한 무작위 중계 토큰은 이 PC와 Render 서버 환경변수에 보관합니다. Render에서는 `OPENAI_API_KEY`에 중계 토큰을, `AI_PROVIDER_BASE_URL`에 Funnel HTTPS 주소와 `/v1`을 설정합니다.
- 로컬 중계 서버가 Hermes에 사용할 키는 중계 토큰과 다르게 유지합니다.
- Git에 올리는 설정 예시에는 빈 값 또는 비밀이 아닌 예시만 둡니다. Funnel 호스트명과 두 키를 브라우저 설정에 넣지 않습니다.
- 기존 로컬 Hermes 설정을 바꾸거나, 작업 트리의 무관한 변경을 덮어쓰지 않습니다.

## 활성화 및 운영 범위

- Funnel을 켜기 전에 중계 서버를 구현하고 테스트합니다.
- 유효한 중계 토큰으로 허용된 두 경로만 Hermes에 도달하는지, 잘못된 토큰과 그 밖의 경로는 거부되는지 로컬에서 확인합니다.
- 로컬 검증을 통과한 뒤 Funnel을 시작합니다. Funnel HTTPS 주소는 인터넷에 공개되며, AI 경로의 사용에는 중계 토큰이 필요합니다.
- PC 종료, Hermes 종료 또는 Tailscale 연결 중단 시 원격 AI를 사용할 수 없습니다. 다른 Provider로 자동 전환하지 않습니다.
- 실제 Render 서비스에서 Funnel을 거쳐 Hermes까지 요청을 보내고 응답을 받기 전에는 원격 연결 검증을 완료로 표시하지 않습니다.

## 오류 처리

- 중계 토큰이 없거나 틀림: 일반 메시지의 HTTP 401
- 지원하지 않는 메서드·경로·쿼리 문자열: 전달 없이 HTTP 404 또는 405
- 요청 본문이 크기 제한 초과: HTTP 413
- Hermes 연결 또는 시간 초과: 일반 메시지의 HTTP 502 또는 504
- 정상적인 상위 응답: OpenAI 호환 클라이언트가 필요한 상태 코드와 JSON 본문을 유지하되 민감한 헤더는 복사하지 않습니다.

## 검증

자동 테스트는 허용된 요청, 토큰 누락·오류, 경로·메서드 거부, 쿼리 문자열 거부, 본문 크기 제한, 상위 Hermes 키로 교체하는 동작, 시간 초과·연결 실패, 오류·로그의 비밀정보 미노출을 확인합니다. 로컬 스모크 테스트로 기존 Hermes 도구 세트 확인과 텍스트 응답을 중계 서버를 통해 검증합니다. Funnel을 켠 뒤에는 HTTPS 접속을 확인하고, Render부터 Hermes까지 전체 경로를 검증합니다. 로컬 성공만으로 원격 연결을 통과 처리하지 않습니다.

## 이번 작업에서 제외할 내용

- Hermes API 포트를 인터넷에 직접 공개하는 기능
- 범용 역방향 프록시 또는 `/v1/models`, 관리자 API, 임의 URL 공개
- 이 PC가 꺼져 있어도 서비스를 계속 제공하는 기능
- 두 번째 AI Provider, 재시도 기반 장애 전환, 브라우저에서 Hermes에 직접 접속하는 기능
- 중계 서버 구현과 검증 전에 Funnel을 자동으로 켜는 동작
