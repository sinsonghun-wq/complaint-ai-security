# 공개용 보안 검사 범위

검사일: 2026-11-03. 실제 검사 결과를 기록하며, 모든 환경에서의 무결점이나 침투 테스트 인증을 뜻하지 않습니다.

## 로컬에서 확인한 결과

| 검사 | 결과 | 범위 |
|---|---|---|
| Gitleaks 8.30.1 | 비밀정보 탐지0건 | 공개 대상 전체 파일. Git 이력도 업로드 전에 별도로 검사 |
| Bandit 1.9.4 | 미해결 중간·높음 등급0건 | 앱·학습 코드. 검토한 SQL 경고의 사유는 security/static-analysis-review.json에 기록 |
| pip-audit 2.10.1 | 알려진 취약점0건 | 앱과 검사 도구를 설치한 가상환경의 전이 의존성 포함 |
| npm audit | 알려진 취약점0건 | 잠금 파일 기준 전체 프론트 의존성 |
| 인증·권한·가림·업로드·공개 자료 회귀 검사 | 53개 통과 | 임시 합성 데이터, 네트워크·실제 DB 변경 없음 |
| 백엔드 단위 검사 | 107개 통과·94개 DB 의존 검사 건너뜀 | 로컬 PostgreSQL 미설치. 총201개 발견 |
| 관리자·현재 채팅 화면 검사 | 86개 통과, 진행률4개 통과 | 현행 /api/chat 계약 |
| 현재 계약 전체 프론트 검사·빌드 | 90개·진행률4개 통과, 빌드 성공 | 아래의 과거 계약은 별도 분리 |

GitHub Actions는 일회용 PostgreSQL/pgvector 컨테이너를 생성해 DB 의존 검사도 실행합니다. DB 비밀번호는 실행마다 생성하고 로그에서 가리며 저장소에 보관하지 않습니다. 실행 결과는 저장소의 Actions 및 체크 상태에서 확인할 수 있습니다.

## 판정 기준과 예외

- Gitleaks 기본 규칙은 유지하며, 공개 BGE 토크나이저의 정확한 SHA-256 한 값만 해당 파일에서 예외로 둡니다. 이 값은 인증 키가 아닌 파일 무결성 검사값입니다.
- 동적 SQL은 서버가 정의한 컬럼·조건문 조각만 사용하고 외부 값은 바인딩합니다. 해당 경고를 코드별로 검토하고 사유를 남겼습니다. 조회 상한도 SQL 매개변수로 바꿨습니다.
- 학습의 SHA-1은 데이터 분할·샘플 순서 재현용이며 인증·서명에 쓰지 않습니다. usedforsecurity=False를 명시했습니다.
- 모델 다운로드에는 검토한 40자 Hugging Face 커밋을 BASE_MODEL_REVISION에 지정해야 합니다. 학습 데이터·모델·어댑터는 포함하지 않습니다.

## 기존 검사와 실행 환경의 한계

과거 `/api/ai-recommendations/intent` 계약을 검사하는 프론트2개 파일은 현행 `/api/chat` 코드와 맞지 않습니다. 삭제하지 않고 `npm run test:legacy`로 보존했습니다. `npm test`는 현재 계약의 검사를 실행합니다. 과거 검사까지 전부 통과했다고 표현하지 않습니다.

로컬 LLM·Ollama·OCR 실행 파일과 실제 회사 DB·운영 데이터, 모델 학습 전후 품질·속도는 이번 공개 검사에서 검증하지 않았습니다. 인터넷 서비스 운영에는 별도 배포 보안 검토가 필요합니다.

## 재현 명령

```powershell
.\.venv\Scripts\python.exe scripts\run_checks.py --suite security
.\.venv\Scripts\python.exe scripts\run_checks.py --suite unit
.\.venv\Scripts\python.exe -m bandit -r dcm-back\app model-training scripts -ll
.\.venv\Scripts\python.exe -m pip_audit --local --skip-editable
cd dcm-front
npm ci
npm audit
npm test
npm run build
```

DB 검사까지 실행할 때만 일회용 개발 DB 접속값을 `TEST_DATABASE_URL`에 지정합니다. 이 계정은 임시 DB 생성·삭제 권한이 필요하며 운영 DB를 지정하면 안 됩니다.
