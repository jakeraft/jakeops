# Issue Schema v3

Canonical schema reference for the current Issue model.

## Source of Truth

- Backend model: `backend/app/domain/models/issue.py`
- Schema endpoint: `GET /api/issues/schema`

## Design Principles

1. Keep external references as links, avoid duplicated source-of-truth fields.
2. Treat one `Issue` as one workflow unit.
3. Keep schema extensible via `refs[]`.
4. Server owns derived fields (`id`, timestamps, schema version).

## Key Fields

| Field | Owner | Notes |
|---|---|---|
| `id` | server | `sha256(repository:trigger_label)[:12]` |
| `schema_version` | server | currently `3` |
| `created_at`, `updated_at` | server | ISO 8601 |
| `status` | use case | workflow state |
| `summary` | caller | human summary |
| `repository` | caller | `owner/repo` |
| `refs` | caller | trigger/output/parent references |
| `plan` | agent/system | optional structured plan |
| `runs` | server | execution history |
| `error` | server/use case | optional error detail |

## Status Enum (current)

- `new`
- `planned`
- `approved`
- `implemented`
- `ci_passed`
- `deployed`
- `done`
- `failed`
- `canceled`

## Transcript Storage

- Path: `issues/{issue_id}/runs/{run_id}.transcript.json`
- API: `GET /api/issues/{issue_id}/runs/{run_id}/transcript`

## Source Schema (current)

```jsonc
{
  "id": "abc123def456",
  "type": "github",
  "owner": "organization",
  "repo": "repository-name",
  "token": "ghp_***",
  "active": true,
  "created_at": "2026-02-20T15:30:00+09:00"
}
```
