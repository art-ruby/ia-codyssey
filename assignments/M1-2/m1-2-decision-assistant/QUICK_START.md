# 🚀 M1-2 RADAR Decision Assistant — 빠른 시작 가이드

## 1️⃣ 백엔드 시작

### Step 1: 가상환경 설정 및 패키지 설치

```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### Step 2: .env 파일 생성

```powershell
copy .env.example .env
# 편집기에서 열기 (또는 아래 단계를 따른다)
```

### Step 3: 최소 설정 (개발 모드 — 키 없이 시작 가능)

**편집:** `backend\.env`

```env
# OpenAI API 키 (선택사항 — 없으면 규칙 기반 응답)
OPENAI_API_KEY=

# Firebase (선택사항 — 없으면 메모리 저장)
FIREBASE_SERVICE_ACCOUNT_JSON=

# CORS (로컬 개발용)
ALLOWED_ORIGINS=*
```

> ✅ **키가 없어도 된다!** 
> - OpenAI 키 없음 → 규칙 기반 계산 응답
> - Firebase 없음 → 메모리 저장 (재시작 시 날라감)
> - `/api/health` 엔드포인트가 현재 모드를 알려준다

### Step 4: 백엔드 실행

```powershell
uvicorn app.main:app --reload --port 8000
```

**확인:**
- 터미널: `Uvicorn running on http://127.0.0.1:8000`
- 브라우저: http://127.0.0.1:8000/docs (Swagger UI)
- Health: http://127.0.0.1:8000/api/health

---

## 2️⃣ 프론트엔드 시작

### Step 1: 포트 8080에서 실행

```powershell
cd frontend
python -m http.server 8080
```

### Step 2: 브라우저 접속

**http://127.0.0.1:8080**

> 백엔드가 다른 주소면 우측 상단 **⚙️ (설정)** 에서 변경 가능

---

## 3️⃣ 표본 데이터 적재

### 옵션 A: 웹 화면에서 [표본 적재] 버튼 클릭

### 옵션 B: 터미널에서 직접

```powershell
# Python 스크립트로 168건 생성
python sample_data/generate.py

# FastAPI 엔드포인트로 적재
curl -X POST "http://127.0.0.1:8000/api/data/import?source=sample&replace=true"
```

---

## 4️⃣ 테스트 실행

```powershell
cd backend
pytest tests/ -v
```

---

## 📊 다음 단계

### API 엔드포인트 확인
- **Swagger UI**: http://127.0.0.1:8000/docs
- **ReDoc**: http://127.0.0.1:8000/redoc

### 주요 API들
- `POST /api/data` — 데이터 추가
- `GET /api/data` — 데이터 목록
- `GET /api/data/summary` — 데이터 요약
- `POST /api/chat` — AI 대화
- `POST /api/conversations` — 대화 저장
- `GET /api/conversations` — 대화 목록

---

## 🔑 OpenAI API 키 추가하기

### 1. OpenAI 계정 생성 (또는 로그인)
https://platform.openai.com

### 2. API 키 생성
- Settings → API Keys → Create new secret key

### 3. `.env` 파일에 추가
```env
OPENAI_API_KEY=sk-xxx...
OPENAI_MODEL=gpt-5-mini
OPENAI_MAX_TOKENS=800
```

### 4. 서버 재시작
```powershell
# 터미널에서 Ctrl+C 로 중지 후
uvicorn app.main:app --reload --port 8000
```

---

## 🔥 Firebase Firestore 연동 (선택)

### 1. Google Cloud Console에서 프로젝트 생성
https://console.cloud.google.com

### 2. Firestore Database 활성화
- Firestore Database 생성 (테스트 모드)

### 3. 서비스 계정 키 다운로드
- IAM 및 관리자 → 서비스 계정
- 서비스 계정 선택 → 키 탭 → JSON 키 생성

### 4. `.env` 파일에 추가
```env
FIREBASE_SERVICE_ACCOUNT_JSON={"type":"service_account","project_id":"...","private_key":"..."}
```

> ⚠️ **주의:** JSON 전체를 한 줄 문자열로 넣는다!

### 5. 서버 재시작

---

## 💡 개발 팁

### 터미널 하나에서 프론트+백엔드 동시 실행

**터미널 1 (백엔드)**
```powershell
cd m1-2-decision-assistant\backend
.venv\Scripts\activate
uvicorn app.main:app --reload --port 8000
```

**터미널 2 (프론트엔드)**
```powershell
cd m1-2-decision-assistant\frontend
python -m http.server 8080
```

---

## ✅ 체크리스트

- [ ] 백엔드 `.venv` 설정 완료
- [ ] `backend/.env` 파일 생성
- [ ] `uvicorn app.main:app --reload` 실행 확인
- [ ] Swagger UI (`/docs`) 접속 확인
- [ ] 프론트엔드 `python -m http.server 8080` 실행 확인
- [ ] http://127.0.0.1:8080 접속 확인
- [ ] 표본 데이터 적재 확인
- [ ] 백엔드-프론트엔드 통신 확인 (⚙️ 설정에서 API URL 확인)

---

문제가 있으면 `/api/health` 를 확인하세요!
