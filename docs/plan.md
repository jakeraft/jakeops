## 구현 계획 완료

GitHub Issue #5 **"Docker Compose for Self-hosted Deployment"** 에 대한 설계 및 구현 계획을 작성했습니다.

### 생성된 문서

| 문서 | 위치 |
|------|------|
| 설계 문서 | `./docs/plans/2026-02-20-docker-compose-design.md` |
| 구현 계획 | `./docs/plans/2026-02-20-docker-compose-plan.md` |

### 아키텍처 요약

**2-service Docker Compose** 구성:
- **frontend** (nginx:alpine) — static file 서빙 + `/api/` reverse proxy → port 3000
- **backend** (python:3.11-slim) — FastAPI/uvicorn → 내부 port 8000 (외부 미노출)
- **jakeops-data** named volume — file-based 데이터 영속성

### 구현 Step (8단계)

| Step | 파일 | 내용 |
|------|------|------|
| 1 | `.dockerignore` | 빌드 컨텍스트 최적화 |
| 2 | `backend/Dockerfile` | Python 3.11-slim, layer caching 최적화 |
| 3 | `frontend/nginx.conf` | Reverse proxy + SPA fallback |
| 4 | `frontend/Dockerfile` | Multi-stage (Node build → nginx serve) |
| 5 | `docker-compose.yml` | 서비스 오케스트레이션, 포트 설정 가능 |
| 6 | *(검증)* | `docker compose build && up` 전체 테스트 |
| 7 | `README.md` | Docker Quick Start 가이드 추가 |
| 8 | `.gitignore` | 필요시 패턴 추가 |

### 핵심 설계 결정

- Backend는 외부 포트를 노출하지 않음 (nginx만 프록시)
- `JAKEOPS_PORT` 환경변수로 호스트 포트 변경 가능 (기본 3000)
- 컨테이너 환경에서 `LOG_FORMAT=json` 기본값
- Health check, TLS, K8s 배포는 scope 외 (향후 별도 이슈)