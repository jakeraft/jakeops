이제 코드베이스를 충분히 파악했습니다. 구현 계획을 작성하겠습니다.

---

# 구현 계획: Issue #13 - git sync 빈도 확인

## 현재 상태 분석

| 항목 | 현재 상태 |
|------|----------|
| 폴링 주기 | `GITHUB_POLL_INTERVAL` 환경변수 (기본 60초), UI에서 확인 불가 |
| 마지막 싱크 시각 | Source별 `last_polled_at` 필드 존재, "Last Synced" 컬럼으로 표시 |
| 싱크 결과 | `sync_once()` 반환값 (`created`/`closed`), 로그에만 기록 |
| 싱크 상태 확인 | 수동 "Sync Now" 버튼만 존재, 자동 싱크 상태 확인 불가 |

## 목표

사용자가 Sources 페이지에서 **싱크 주기 설정값**, **마지막 싱크 시각**, **싱크 건강 상태**를 한눈에 확인할 수 있도록 한다.

## 구현 범위

### Step 1: Backend - 싱크 상태 추적 및 API

**1-1. `DeliverySyncUseCase`에 상태 추적 추가**

| 파일 | 변경 |
|------|------|
| `./backend/app/usecases/delivery_sync.py` | `last_completed_at`, `last_result` 인스턴스 변수 추가 |

`sync_once()` 호출 후 결과를 인스턴스에 저장:
```python
class DeliverySyncUseCase:
    def __init__(self, ...):
        ...
        self.last_completed_at: str | None = None
        self.last_result: dict | None = None

    def sync_once(self) -> dict:
        ...
        result = {"created": created, "closed": closed}
        self.last_completed_at = datetime.now(KST).isoformat()
        self.last_result = result
        return result
```

**1-2. 새 엔드포인트 추가: `GET /api/sources/sync/status`**

| 파일 | 변경 |
|------|------|
| `./backend/app/adapters/inbound/sources.py` | 라우터에 `sync_status` 엔드포인트 추가 |
| `./backend/app/main.py` | `delivery_sync` + `GITHUB_POLL_INTERVAL`을 `app.state`에 노출 |

응답 형태:
```json
{
  "interval_sec": 60,
  "last_completed_at": "2026-02-20T15:30:00+09:00",
  "last_result": { "created": 0, "closed": 0 }
}
```

`main.py` 변경:
- `app.state.sync_interval = GITHUB_POLL_INTERVAL` 추가
- 기존 `app.state.delivery_sync`은 이미 존재

`sources.py` 라우터 추가:
```python
@router.get("/sources/sync/status")
def sync_status(request: Request):
    sync = request.app.state.delivery_sync
    return {
        "interval_sec": request.app.state.sync_interval,
        "last_completed_at": sync.last_completed_at,
        "last_result": sync.last_result,
    }
```

> 주의: `/sources/sync/status`는 `/sources/{source_id}` 보다 **앞에** 등록해야 path parameter 충돌을 방지한다.

**1-3. `sources.py`의 `get_issue_sync` 의존성 버그 수정**

현재 `get_issue_sync`가 `request.app.state.issue_sync`를 참조하지만 `main.py`에서는 `app.state.delivery_sync`으로 저장하고 있어 불일치가 있다. 이를 `delivery_sync`로 통일한다.

### Step 2: Frontend - 싱크 상태 표시

**2-1. TypeScript 타입 추가**

| 파일 | 변경 |
|------|------|
| `./frontend/src/types.ts` | `SyncStatus` 인터페이스 추가 |

```typescript
export interface SyncStatus {
  interval_sec: number
  last_completed_at: string | null
  last_result: { created: number; closed: number } | null
}
```

**2-2. `useSources` 훅에 싱크 상태 조회 추가**

| 파일 | 변경 |
|------|------|
| `./frontend/src/hooks/use-sources.ts` | `syncStatus` 상태 + `fetchSyncStatus` 함수 추가 |

- `refresh()` 호출 시 `GET /api/sources/sync/status`도 병렬 fetch
- `syncStatus` 상태로 반환

**2-3. Sources 페이지에 싱크 상태 표시 영역 추가**

| 파일 | 변경 |
|------|------|
| `./frontend/src/pages/sources/list.tsx` | 헤더 아래에 싱크 상태 배너 추가 |

표시할 정보:
- **Sync Interval**: `60s` (설정된 폴링 주기)
- **Last Sync**: `2m ago` (마지막 완료 시각의 상대 시간)
- **Last Result**: `0 created, 0 closed` (마지막 싱크 결과)
- **Health indicator**: `last_completed_at`이 `interval_sec * 3`보다 오래되면 경고 표시

UI 레이아웃 (Sources 헤더와 테이블 사이):
```
┌──────────────────────────────────────────────────────┐
│  ⏱ Interval: 60s  │  Last Sync: 2m ago  │  0 new    │
└──────────────────────────────────────────────────────┘
```

`Badge` + `text-muted-foreground` 스타일로 간결하게 구현한다.

**2-4. 자동 새로고침 (선택)**

`useSources` 훅에 `useEffect` 기반 interval refresh를 추가하여 sources 목록과 sync status를 주기적으로 갱신한다 (30초 간격).

이를 통해 "Last Synced" 컬럼의 상대 시간이 실시간으로 업데이트된다.

### Step 3: 테스트

**3-1. Backend 테스트**

| 파일 | 변경 |
|------|------|
| `./backend/tests/test_delivery_sync.py` | `last_completed_at`, `last_result` 추적 테스트 추가 |
| `./backend/tests/test_sources_api.py` | `GET /api/sources/sync/status` 엔드포인트 테스트 추가 |

테스트 케이스:
- `sync_once()` 후 `last_completed_at`이 설정되는지 확인
- `sync_once()` 후 `last_result`가 결과와 일치하는지 확인
- `GET /api/sources/sync/status` 응답 형태 검증
- 최초 상태(아직 sync 안 됨)에서 `null` 반환 확인

**3-2. Frontend 테스트**

| 파일 | 변경 |
|------|------|
| `./frontend/src/hooks/__tests__/use-sources.test.ts` | `syncStatus` 관련 테스트 추가 |

## 수정 파일 요약

| 파일 | 변경 유형 | 설명 |
|------|----------|------|
| `./backend/app/usecases/delivery_sync.py` | 수정 | 싱크 상태 인스턴스 변수 추적 |
| `./backend/app/main.py` | 수정 | `sync_interval`을 `app.state`에 노출 |
| `./backend/app/adapters/inbound/sources.py` | 수정 | `sync/status` 엔드포인트 추가, `issue_sync` → `delivery_sync` 수정 |
| `./frontend/src/types.ts` | 수정 | `SyncStatus` 타입 추가 |
| `./frontend/src/hooks/use-sources.ts` | 수정 | 싱크 상태 조회 + 자동 새로고침 |
| `./frontend/src/pages/sources/list.tsx` | 수정 | 싱크 상태 배너 UI 추가 |
| `./backend/tests/test_delivery_sync.py` | 수정 | 상태 추적 테스트 |
| `./backend/tests/test_sources_api.py` | 수정 | 새 엔드포인트 테스트 |
| `./frontend/src/hooks/__tests__/use-sources.test.ts` | 수정 | syncStatus 테스트 |

## 구현 순서

1. Backend: `delivery_sync.py`에 상태 추적 추가
2. Backend: `main.py`에 `sync_interval` state 추가
3. Backend: `sources.py`에 엔드포인트 추가 + `issue_sync` 버그 수정
4. Backend: 테스트 작성 및 실행
5. Frontend: `types.ts`에 `SyncStatus` 타입 추가
6. Frontend: `use-sources.ts`에 싱크 상태 조회 + 자동 새로고침 추가
7. Frontend: `list.tsx`에 싱크 상태 배너 UI 추가
8. Frontend: 테스트 작성 및 실행
9. 전체 lint + test 실행

## 참고: 발견된 버그

`./backend/app/adapters/inbound/sources.py:13`에서 `get_issue_sync`가 `request.app.state.issue_sync`를 참조하지만, `main.py:70`에서는 `app.state.delivery_sync`로 저장하고 있다. 이 불일치를 이번 작업에서 함께 수정한다.