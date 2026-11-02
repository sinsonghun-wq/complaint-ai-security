# ComplaintAI Security

민원 접수·분류·부서 처리와 문서 근거 기반 문의를 연결한 인턴십 프로젝트의 공개용 소스입니다.
원본 main의 기능 코드에서 출발해 민감 자료와 기존 Git 이력을 제외하고 보안 관련 변경을 적용했습니다.

## 기능

- React/Vite: 민원 작성·본인 민원 조회, 관리자 목록·접수·답변·이관·삭제 보관함
- FastAPI: 로그인·회원가입, 부서 ID 권한 검사, 민원·답변·채팅 API
- CSV/PDF/HWP/XLSX/이미지: 텍스트 추출, 민원 단위 처리, 중복 검사, 워커 진행률·중단·재개
- PostgreSQL/pgvector: 업무 데이터와 1024차원 임베딩 저장·검색
- 긴 RAG 자료: 원문 보존, 조각·완료 상태, 조문·예외·참조 연결과 근거 분량 제한
- 로컬 AI: Ollama 임베딩, llama-server 또는 Ollama 답변 모델, 학습·평가 코드

## 원본과의 차이

화면·API·민원 처리·AI/RAG 기능 구조는 유지합니다. 아래 공개 및 보안 변경을 적용했으므로 바이트 단위로 동일한 복제본은 아닙니다.

- 기존 DB/로그인/인증 값을 제거하고 새 로컬 환경변수를 요구합니다.
- DB 초기화는 공유 기본 계정을 만들지 않습니다. 계정은 본인의 비밀번호로 생성합니다.
- 테스트 fixture는 새 합성 비밀번호·해시로 교체하며 서비스용으로 사용하지 않습니다.
- 학습 원문, DB 백업, 모델 파일, ZIP 중복본, 운영 기록과 과거 Git 이력을 제외합니다.
- 노트북 실행 출력과 개인 메타데이터를 제거합니다. 학습·평가 코드는 유지합니다.
- 인증 키 누락 거부, 민감 채팅 로그 제거, 정적 경로 이탈 차단, 마스킹·벡터 정규화 보완을 적용합니다.

상세 범위와 실제 검사 결과는 [SECURITY.md](SECURITY.md), [PUBLICATION_CHANGES.md](PUBLICATION_CHANGES.md)를 참고하세요.

## 새 PC에서 실행

Python 3.12, Node.js 24.15 이상, PostgreSQL 17과 pgvector가 필요합니다.
PDF/이미지 OCR에는 Tesseract와 한국어 언어 데이터, HWP에는 별도 파서가 필요합니다.

```powershell
git clone https://github.com/sinsonghun-wq/complaint-ai-security.git
cd complaint-ai-security
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r dcm-back\requirements.txt
Copy-Item dcm-back\.env.example dcm-back\.env
```

`dcm-back/.env`의 `DATABASE_URL`은 본인의 DB 정보로 입력하고, `AUTH_TOKEN_SECRET`은 아래 명령으로 생성한 새 값을 넣습니다. 로컬 `.env`는 커밋하지 않습니다.

```powershell
.\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(48))"
```

새 빈 개발 DB에만 `database/init.sql`을 실행하세요. 이 SQL은 기존 프로젝트 테이블을 재생성하므로 보존해야 할 DB에 실행하면 안 됩니다.
초기 계정이 없는 상태에서 서버를 시작한 뒤 화면에서 일반 사용자를 가입할 수 있습니다.
관리자는 별도 터미널에서 `scripts/create_local_user.py --help`를 확인해 생성하세요. 비밀번호는 프롬프트에서 입력하며 명령행에 넣지 않습니다.

```powershell
# Ollama 임베딩 모델과 로컬 답변 서버를 준비한 뒤
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir dcm-back --host 127.0.0.1 --port 8000
```

```powershell
# 별도 터미널
cd dcm-front
npm ci
npm run dev
```

`http://localhost:5173`에서 사용합니다. 모델·DB·학습 원문은 포함하지 않으므로 본인의 합법적으로 사용할 수 있는 자료를 로컬에 준비해야 합니다.
기존 어댑터 사용 흐름과 학습 스크립트는 남아 있으며, 학습 실행 출력이나 비공개 데이터는 제공하지 않습니다.

## 검사

보안 검사는 저장소의 비밀정보·인증/권한·개인정보 가림·정적 파일·알려진 의존성 취약점을 대상으로 합니다.
실행 결과와 범위는 SECURITY.md에 기록합니다. 일부 로컬 모델·DB 연동 및 과거 채팅 계약 테스트는 별도로 구분합니다.

이 저장소를 그대로 인터넷 서비스로 배포하기보다는 HTTPS, 운영 DB 권한, 로그인 제한, 모델 서버 접근 제어와 개인정보 보관 정책을 서비스 환경에 맞춰 설정하세요.
