코드베이스 분석이 완료되었습니다. 아래에 구현 계획을 작성합니다.

---

# Implementation Plan: Settings Dashboard for Application Configuration

## Issue
GitHub Issue #6 — `feat: Settings Dashboard for Application Configuration`

## Context

현재 JakeOps는 환경변수(`GITHUB_POLL_INTERVAL`, `JAKEOPS_DATA_DIR`, `JAKEOPS_SOURCES_DIR`, `JAKEOPS_CORS_ORIGINS`)로만 설정을 관리하며, 런타임에 설정을 변경할 수 있는 UI가 없습니다. Settings Dashboard를 추가하여 애플리케이션 설정을 UI에서 조회/수정할 수 있도록 합니다.

## Scope of Settings

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `github_poll_interval` | int (seconds) | `60` | GitHub 폴링 주기 |
| `github_poll_enabled` | bool | `true` | GitHub 폴링 활성화 여부 |
| `default_exit_phase` | Phase enum | `"deploy"` | 새 Delivery 기본 종료 단계 |
| `data_dir` | string | `deliveries/` | Delivery 저장 디렉토리 (read-only) |
| `sources_dir` | string | `sources/` | Source 저장 디렉토리 (read-only) |

Read-only 항목은 현재 설정값을 UI에서 확인만 가능하도록 합니다. 편집 가능한 항목은 `github_poll_interval`, `github_poll_enabled`, `default_exit_phase` 세 가지입니다.

## Architecture

기존 Source CRUD 패턴을 정확히 따릅니다:

```
[Frontend]                        [Backend]
Settings page                     GET  /api/settings
  └─ useSettings hook             PATCH /api/settings
       └─ api.ts wrappers         
                                  SettingsUseCases (Protocol)
                                    └─ SettingsUseCasesImpl
                                         └─ SettingsRepository (Protocol)
                                              └─ FileSystemSettingsRepository
                                                   └─ settings.json (single file)
```

Settings는 Source와 달리 **singleton** 패턴입니다 (단일 JSON 파일). CRUD 중 Create/Delete 불필요하고 Get/Update만 존재합니다.

## Step-by-Step Implementation

### Step 1: Backend Domain Model

**파일**: `backend/app/domain/models/settings.py`

```python
from pydantic import BaseModel

class Settings(BaseModel):
    github_poll_interval: int = 60
    github_poll_enabled: bool = True
    default_exit_phase: str = "deploy"

class SettingsUpdate(BaseModel):
    github_poll_interval: int | None = None
    github_poll_enabled: bool | None = None
    default_exit_phase: str | None = None

class SettingsResponse(BaseModel):
    github_poll_interval: int
    github_poll_enabled: bool
    default_exit_phase: str
    data_dir: str          # read-only, from env
    sources_dir: str       # read-only, from env
```

### Step 2: Backend Port (Outbound)

**파일**: `backend/app/ports/outbound/settings_repository.py`

```python
from typing import Protocol

class SettingsRepository(Protocol):
    def get_settings(self) -> dict: ...
    def save_settings(self, data: dict) -> None: ...
```

### Step 3: Backend Port (Inbound)

**파일**: `backend/app/ports/inbound/settings_usecases.py`

```python
from typing import Protocol
from app.domain.models.settings import SettingsUpdate

class SettingsUseCases(Protocol):
    def get_settings(self) -> dict: ...
    def update_settings(self, body: SettingsUpdate) -> dict: ...
```

### Step 4: Backend Use Case

**파일**: `backend/app/usecases/settings_usecases.py`

- `SettingsUseCasesImpl.__init__(repo, data_dir, sources_dir)` — read-only 경로를 생성 시 주입
- `get_settings()` — repo에서 설정을 읽고 `data_dir`, `sources_dir`을 추가하여 반환
- `update_settings(body)` — None이 아닌 필드만 merge 후 save, 갱신된 설정 반환
- `default_exit_phase` 검증: `Phase` enum에 포함된 값인지 확인

### Step 5: Backend Adapter (Outbound) — FileSystem

**파일**: `backend/app/adapters/outbound/filesystem_settings.py`

- `FileSystemSettingsRepository.__init__(settings_file: Path)` — 단일 JSON 파일 경로
- `get_settings()` — 파일이 없으면 기본값 `{}` 반환 (UseCase에서 defaults merge)
- `save_settings(data)` — atomic write (기존 `_atomic_write` 패턴 동일)
- 저장 경로: `JAKEOPS_DATA_DIR/../settings.json` 또는 프로젝트 루트의 `settings.json`

### Step 6: Backend Adapter (Inbound) — FastAPI Router

**파일**: `backend/app/adapters/inbound/settings.py`

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/settings` | 현재 설정 조회 |
| `PATCH` | `/api/settings` | 설정 부분 업데이트 |

- `get_usecases(request)` — `request.app.state.settings_usecases` 의존성 주입
- `get_settings()` → `uc.get_settings()`
- `update_settings(body: SettingsUpdate)` → `uc.update_settings(body)`

### Step 7: Backend DI Assembly

**파일**: `backend/app/main.py` (수정)

- `FileSystemSettingsRepository` import 추가
- `SettingsUseCasesImpl` import 추가
- `settings` router import 추가
- lifespan에서 `settings_repo`, `settings_usecases` 조립
- `app.include_router(settings.router, prefix="/api")` 추가
- `SETTINGS_FILE = PROJECT_ROOT / "settings.json"` 상수 추가

### Step 8: Backend Tests

**파일**: `backend/tests/test_settings_usecases.py`

- `test_get_settings_defaults` — 파일 없을 때 기본값 반환
- `test_update_settings_partial` — 일부 필드만 업데이트
- `test_update_settings_invalid_phase` — 잘못된 exit_phase 시 에러
- `test_get_settings_includes_paths` — data_dir, sources_dir 포함 확인

**파일**: `backend/tests/test_settings_api.py`

- `test_get_settings` — GET 200 응답 확인
- `test_patch_settings` — PATCH 200 + 값 변경 확인
- `test_patch_settings_invalid_phase` — PATCH 422 확인

**파일**: `backend/tests/conftest.py` (수정)

- `SettingsUseCasesImpl` 및 `FileSystemSettingsRepository`를 `_test_storage` fixture에 추가
- `app.state.settings_usecases` 주입

### Step 9: Frontend Types

**파일**: `frontend/src/types.ts` (수정)

```typescript
// Settings
export interface Settings {
  github_poll_interval: number
  github_poll_enabled: boolean
  default_exit_phase: string
  data_dir: string        // read-only
  sources_dir: string     // read-only
}

export interface SettingsUpdate {
  github_poll_interval?: number
  github_poll_enabled?: boolean
  default_exit_phase?: string
}
```

### Step 10: Frontend Hook

**파일**: `frontend/src/hooks/use-settings.ts`

기존 `use-sources.ts` 패턴 동일:
- `useSettings()` → `{ settings, loading, error, updateSettings, refresh }`
- `apiFetch<Settings>("/settings")` 로 조회
- `apiPatch<Settings>("/settings", body)` 로 업데이트

### Step 11: Frontend Settings Page

**파일**: `frontend/src/pages/settings/index.tsx`

UI 구성:
- **페이지 제목**: "Settings"
- **섹션 1 — GitHub Polling**:
  - `Switch`: `github_poll_enabled` 토글
  - `Input (number)`: `github_poll_interval` (초 단위)
- **섹션 2 — Delivery Defaults**:
  - `Select` 또는 `Input`: `default_exit_phase` (Phase enum 값 선택)
- **섹션 3 — Storage (read-only)**:
  - `data_dir` 표시 (disabled Input 또는 text)
  - `sources_dir` 표시 (disabled Input 또는 text)
- **Save 버튼**: 변경된 필드만 PATCH 호출

shadcn 컴포넌트 사용: `Card`, `CardHeader`, `CardContent`, `Button`, `Input`, `Label`, `Switch`, `Separator`

Select 컴포넌트가 현재 shadcn에 없으므로 `Input` 사용하거나 `select` shadcn 추가 필요 → Phase 값이 고정 8개이므로 shadcn `Select` 추가가 적합합니다.

### Step 12: Frontend Router & Navigation

**파일**: `frontend/src/App.tsx` (수정)

```tsx
import { SettingsPage } from "./pages/settings"
// Route 추가:
<Route path="settings" element={<SettingsPage />} />
```

**파일**: `frontend/src/components/app-sidebar.tsx` (수정)

```tsx
import { Settings } from "lucide-react"
// NAV_ITEMS 추가:
{ to: "/settings", label: "Settings", icon: Settings }
```

### Step 13: shadcn Select Component 추가

shadcn `Select` 컴포넌트가 없으므로 추가해야 합니다. MCP 또는 CLI로 설치:

```bash
cd frontend && npx shadcn@latest add select
```

이 컴포넌트는 `frontend/src/components/ui/select.tsx`에 생성됩니다. (convention에 따라 수정 금지)

### Step 14: Frontend Tests

**파일**: `frontend/src/hooks/__tests__/use-settings.test.ts`

- `test("fetches settings on mount")` — `apiFetch` mock 확인
- `test("updateSettings calls apiPatch")` — PATCH 호출 확인

## File Summary

### New Files (11)

| File | Layer |
|------|-------|
| `backend/app/domain/models/settings.py` | Domain Model |
| `backend/app/ports/outbound/settings_repository.py` | Port (Outbound) |
| `backend/app/ports/inbound/settings_usecases.py` | Port (Inbound) |
| `backend/app/usecases/settings_usecases.py` | Use Case |
| `backend/app/adapters/outbound/filesystem_settings.py` | Adapter (Outbound) |
| `backend/app/adapters/inbound/settings.py` | Adapter (Inbound) |
| `backend/tests/test_settings_usecases.py` | Backend Test |
| `backend/tests/test_settings_api.py` | Backend Test |
| `frontend/src/pages/settings/index.tsx` | Frontend Page |
| `frontend/src/hooks/use-settings.ts` | Frontend Hook |
| `frontend/src/hooks/__tests__/use-settings.test.ts` | Frontend Test |

### Modified Files (5)

| File | Change |
|------|--------|
| `backend/app/main.py` | DI assembly + router 등록 |
| `backend/tests/conftest.py` | settings_usecases fixture 추가 |
| `frontend/src/types.ts` | Settings, SettingsUpdate 타입 추가 |
| `frontend/src/App.tsx` | `/settings` route 추가 |
| `frontend/src/components/app-sidebar.tsx` | Settings nav item 추가 |

### Generated Files (1)

| File | Method |
|------|--------|
| `frontend/src/components/ui/select.tsx` | `npx shadcn@latest add select` |

## Implementation Order

```
1. Backend domain model        (settings.py)
2. Backend ports               (settings_repository.py, settings_usecases.py)
3. Backend adapter outbound    (filesystem_settings.py)
4. Backend use case            (settings_usecases.py)
5. Backend adapter inbound     (settings.py router)
6. Backend main.py DI          (wire up)
7. Backend tests               (test_settings_usecases.py, test_settings_api.py)
8. Run backend tests           (pytest -v)
9. Frontend types              (types.ts)
10. Frontend hook              (use-settings.ts)
11. shadcn Select component    (npx shadcn add select)
12. Frontend page              (pages/settings/index.tsx)
13. Frontend router + sidebar  (App.tsx, app-sidebar.tsx)
14. Frontend tests             (use-settings.test.ts)
15. Run all tests              (pytest + npm run test + npm run lint)
```

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| Singleton `settings.json` 파일 | Source처럼 ID별 파일이 아니라 앱 전체 설정이므로 단일 파일 |
| PATCH만 지원 (PUT 미지원) | 부분 업데이트가 자연스럽고 기존 Source 패턴과 일관 |
| Read-only 경로 포함 | 운영자가 현재 data/sources 경로를 UI에서 확인할 수 있도록 |
| 환경변수 override 유지 | `settings.json`이 없으면 환경변수 → 하드코딩 기본값 순 fallback |
| Phase validation | `default_exit_phase`에 잘못된 값 입력 시 422 반환 |