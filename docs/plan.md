## Implementation Plan: Handle GitHub API Rate Limit (403) in Delivery Sync

### 문제 분석

현재 코드에서 GitHub API 403 (rate limit) 응답을 받으면:

| 레이어 | 현재 동작 | 문제점 |
|--------|----------|--------|
| `GitHubApiAdapter` | `HTTPStatusError` 그대로 raise | 403과 500 구분 없음 |
| `DeliverySyncUseCase` | generic `Exception` catch → 다음 source 계속 | 같은 rate limit에 걸린 나머지 source들도 불필요하게 시도 |
| `Source` 모델 | sync 에러 정보 없음 | 사용자에게 에러 원인 불투명 |
| Frontend | sync 에러 표시 없음 | rate limit 여부를 알 수 없음 |

추가 발견: `./backend/app/adapters/inbound/sources.py:13`에서 `app.state.issue_sync`를 참조하지만 `./backend/app/main.py:70`에서는 `app.state.delivery_sync`로 저장 (naming mismatch 버그)

### 변경 파일 요약 (10개)

| 파일 | 유형 | 설명 |
|------|------|------|
| `backend/app/domain/exceptions.py` | **신규** | `GitHubRateLimitError` 도메인 예외 (reset_at 포함) |
| `backend/app/domain/models/source.py` | 수정 | `sync_error: str | None` 필드 추가 |
| `backend/app/adapters/outbound/github_api.py` | 수정 | 403 → `X-RateLimit-Reset` 파싱 → `GitHubRateLimitError` raise |
| `backend/app/usecases/delivery_sync.py` | 수정 | rate limit catch → skip remaining sources + sync_error 기록 |
| `backend/app/adapters/inbound/sources.py` | 수정 | naming fix (`issue_sync` → `delivery_sync`) |
| `backend/tests/test_github_api.py` | 수정 | rate limit 테스트를 `GitHubRateLimitError` 확인으로 변경 |
| `backend/tests/test_delivery_sync.py` | 수정 | rate limit 핸들링 테스트 4건 추가 |
| `frontend/src/types.ts` | 수정 | `Source.sync_error` 타입 추가 |
| `frontend/src/hooks/use-sources.ts` | 수정 | syncNow 반환값에서 rate limit 정보 처리 |
| `frontend/src/pages/sources/list.tsx` | 수정 | Sync Status 컬럼 + rate limit 경고 UI |

### 핵심 설계 결정

1. **도메인 예외 분리**: `GitHubRateLimitError`를 `domain/exceptions.py`에 정의하여 adapter → usecase 간 Port/Adapter 패턴 유지
2. **같은 토큰 skip**: rate limit 발생 시 `skipped_tokens` set으로 동일 토큰의 나머지 source들 skip (불필요한 API 호출 방지)
3. **per-source sync_error**: 성공 시 `None`으로 클리어, 실패 시 에러 메시지 저장 (기존 JSON 파일과 하위 호환)
4. **sync_once() 반환값 확장**: `rate_limited`, `rate_limit_reset_at` 추가

### 구현 순서

```
1. domain/exceptions.py (신규)
2. domain/models/source.py (sync_error 추가)
3. adapters/outbound/github_api.py (403 감지)
4. usecases/delivery_sync.py (rate limit 핸들링)
5. adapters/inbound/sources.py (naming fix)
6-7. tests (adapter + usecase)
8-10. frontend (types → hook → UI)
11. pytest + lint + test 실행
```

상세 계획은 `./plan.md`에 작성 완료.