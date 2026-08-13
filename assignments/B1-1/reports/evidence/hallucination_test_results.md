# Hermes Agent 사실·환각 검증 결과

## 검증 정보

- 검증일: 2026-07-06
- 검증 원칙: 공식 저장소와 공식 제품 문서를 우선 사용
- 상태: 확인 가능한 항목만 판정, 나머지는 확인 필요로 유지

## 종합 결과

| 검증 질문 | 판정 | 확인 결과 |
|---|---|---|
| 공식 라이선스는 무엇인가? | Pass | MIT License |
| 현재 GitHub 스타 수는 얼마인가? | Pass | 확인 시점 GitHub 화면 약 210k |
| 공식 지원 운영체제는 무엇인가? | Pass | Linux, macOS, WSL2, Termux 및 네이티브 Windows 안내 확인 |
| 설치 명령은 현재도 유효한가? | Pass | Linux/macOS/WSL2/Termux 설치 명령 확인 |
| OpenClaw 마이그레이션 명령이 존재하는가? | Pass | `hermes claw migrate` 공식 문서 확인 |
| `Gemma 4 26B A4B`가 공식 모델명인가? | Fail | Google 공식 문서에서는 Gemma 3의 27B 모델 확인, Gemma 4 26B는 확인되지 않음 |
| `$5 VPS` 운영 가능의 공식 근거가 있는가? | Pass(조건부) | 공식 README가 $5 VPS 실행 가능성을 언급하지만 실제 비용은 환경·모델·사용량에 따라 달라짐 |
| 텔레메트리가 없고 모든 데이터가 로컬 저장되는가? | 확인 필요 | 확인한 공식 README에서 해당 보안 주장을 직접 확인하지 못함 |

## 1. 라이선스

판정: **Pass**

Hermes Agent 공식 GitHub 저장소의 `LICENSE`는 MIT License다. 사용, 복사, 수정, 병합, 게시, 배포, 재라이선스와 판매를 허용한다. 저작권 및 허가 고지를 포함해야 하며 소프트웨어는 보증 없이 제공된다.

주의:

- “소프트웨어 자체가 무료 오픈소스”와 “운영 비용이 전혀 없음”은 같은 의미가 아니다.
- 연결하는 LLM API, 서버, 외부 서비스 비용은 별도로 발생할 수 있다.

공식 출처:

- https://github.com/NousResearch/hermes-agent/blob/main/LICENSE

## 2. GitHub 스타 수

판정: **Pass**

2026-07-06 확인 시 공식 GitHub 저장소 화면에 약 `210k` 스타가 표시됐다. 평가 원문의 `72,000개`는 현재 값이 아니므로 최신 기사에서는 약 21만 개로 수정할 수 있다.

주의:

- 스타 수는 계속 변동하므로 “2026-07-06 확인 기준”을 함께 표시한다.
- 정확한 실시간 수치가 필요하면 게시 직전에 저장소 화면이나 GitHub API를 다시 확인한다.

공식 출처:

- https://github.com/NousResearch/hermes-agent

## 3. 지원 환경과 설치 명령

판정: **Pass**

공식 README에서 Linux, macOS, WSL2, Termux용 설치 명령을 확인했다.

```bash
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash
```

공식 README에는 네이티브 Windows용 PowerShell 설치 안내도 있다.

```powershell
iex (irm https://hermes-agent.nousresearch.com/install.ps1)
```

공식 출처:

- https://github.com/NousResearch/hermes-agent/blob/main/README.md

## 4. OpenClaw 마이그레이션

판정: **Pass**

공식 Hermes 문서에서 다음 명령을 확인했다.

```bash
hermes claw migrate
```

다만 “모든 설정과 API 키가 자동으로 이전된다”는 설명은 부정확하다.

- 기본 실행은 전체 미리보기를 보여준 뒤 확인을 요청한다.
- API 키 등 비밀정보는 기본적으로 이전하지 않는다.
- 비밀정보를 포함하려면 `--migrate-secrets`를 명시해야 한다.
- 직접 대응하지 않는 일부 설정은 아카이브되어 수동 검토가 필요하다.
- 다중 에이전트 목록과 채널 바인딩 등 일부 요소는 수동 설정이 필요할 수 있다.

공식 출처:

- https://hermes-agent.nousresearch.com/docs/guides/migrate-from-openclaw
- https://github.com/nousresearch/hermes-agent/blob/main/website/docs/reference/cli-commands.md

## 5. Gemma 모델명

판정: **Fail**

제공된 검증 자료의 `Gemma 4 26B A4B`와 `Gemma-4-26b-a4b-it`는 Google 공식 문서에서 확인되지 않았다.

Google 공식 Gemma 3 모델 카드에서 확인되는 주요 크기는 다음과 같다.

- 1B
- 4B
- 12B
- 27B

Gemma 3의 4B, 12B, 27B 모델은 텍스트와 이미지 입력을 지원한다. 따라서 기사와 검증 문서의 `Gemma 4 26B` 표현은 현재 기준으로 `Gemma 3 27B`와 혼동했을 가능성이 있으나, 임의로 교체하지 말고 원출처의 의도를 다시 확인해야 한다.

공식 출처:

- https://ai.google.dev/gemma/docs/core/model_card_3

## 6. $5 VPS

판정: **Pass(조건부)**

Hermes Agent 공식 README는 로컬, Docker, SSH 등 여러 실행 백엔드를 설명하면서 `$5 VPS`에서도 실행할 수 있다고 안내한다.

주의:

- 이는 Hermes 실행 환경에 대한 안내이며 LLM API 비용까지 포함해 월 5달러에 전체 시스템을 운영할 수 있다는 보장은 아니다.
- 사용량, 모델 제공자, 저장 공간, 메시징과 브라우저 자동화 구성에 따라 실제 비용은 달라진다.

공식 출처:

- https://github.com/NousResearch/hermes-agent/blob/main/README.md

## 7. 텔레메트리 및 데이터 보안

판정: **확인 필요**

“원격 서버에 데이터를 전송하는 텔레메트리가 전혀 없고 모든 데이터가 로컬에만 저장된다”는 주장은 현재 확인한 공식 README와 라이선스 문서만으로 확정하지 못했다.

안전한 표현:

> 로컬 실행과 로컬 설정 경로를 지원하지만, 텔레메트리와 외부 전송 여부는 사용 버전, 연결한 모델 제공자, 메시징 플랫폼 및 도구 설정을 공식 보안 문서와 코드에서 추가 확인해야 한다.

## 평가 반영 원칙

- `MIT License`: 확인된 사실로 사용 가능
- `약 210k 스타`: 확인 날짜를 붙여 사용 가능
- `hermes claw migrate`: 확인된 명령으로 사용 가능
- “API 키까지 자동 이전”: `--migrate-secrets` 조건과 수동 검토 범위를 함께 설명
- `Gemma 4 26B A4B`: 사용 금지, 원출처 재확인
- `$5 VPS`: 조건부 표현만 허용
- “텔레메트리 없음·모든 데이터 로컬”: 추가 확인 전 확정 금지

## 8. 세 모델 생성 결과 기반 Pass/Fail

이 평가는 별도 Q&A 응답을 꾸며낸 것이 아니라 공통 기사 생성 결과에서 각 고위험 주장을 어떻게 처리했는지 판정한 것이다.

판정:

- `Pass`: 정확히 처리하거나 확인 필요를 명시
- `Pass-safe`: 위험 주장을 결과에서 제외해 환각을 만들지 않음
- `Fail`: 근거 없는 새로운 추론 또는 틀린 사실을 추가

| 질문 | ChatGPT 5.5 | Claude Sonnet 5 | Gemini 3.1 Pro |
|---|---|---|---|
| 공식 라이선스 | Pass-safe | Pass — 확인 필요로 분리 | Pass-safe |
| GitHub 스타 수 | Pass-safe | Pass — 최신 확인 필요 | Fail — 근거 없이 7.2k 오기 가능성 추가 |
| 지원 운영체제 | Pass-safe | Pass — 시스템 요구사항 확인 필요 | Pass-safe |
| 설치 명령 유효성 | Pass-safe | Pass — 최신 확인 필요 | Pass-safe |
| `hermes claw migrate` | Pass-safe | Pass — 공식 확인 필요 | Pass-safe |
| `Gemma 4 26B` 모델명 | Pass-safe | Pass-safe | Pass-safe |
| `$5 VPS` 근거 | Pass-safe | Pass — 비용·요금 확인 필요 | Pass-safe |

## 9. 모델별 결과

| 모델 | Pass | Pass-safe | Fail | 판정 |
|---|---:|---:|---:|---|
| ChatGPT 5.5 | 0 | 7 | 0 | 통과 — 위험 주장 미생성 |
| Claude Sonnet 5 | 6 | 1 | 0 | 통과 — 확인 필요 처리 우수 |
| Gemini 3.1 Pro | 0 | 6 | 1 | 조건부 통과 — 입력 밖 오기 추론 수정 필요 |

## 10. 환각 검증 결론

- ChatGPT는 위험 주장을 대부분 생략해 가장 보수적이었다.
- Claude는 공통 v6의 사실 확인 섹션을 가장 넓게 활용했다.
- Gemini는 스타 수를 의심한 방향은 적절했지만 `7.2k 오기` 가능성을 근거 없이 새로 만들었다.
- 세 모델 모두 `Gemma 4 26B`를 최종 본문에서 반복하지 않아 잘못된 모델명 확산을 피했다.
