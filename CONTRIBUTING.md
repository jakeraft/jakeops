# Contributing to JakeOps

Thanks for your interest in contributing.

## Before You Start

- Check open issues first and avoid duplicate work.
- For larger changes, open an issue and align on scope before implementation.
- Keep changes focused and reviewable.

## Development Setup

```bash
# backend
cd backend
pip install -e ".[test]"

# frontend
cd frontend
npm install
```

Run locally:

```bash
# backend
cd backend
uvicorn app.main:app --reload

# frontend
cd frontend
npm run dev
```

## Repository Structure

```text
jakeops/
├── backend/               # FastAPI backend
│   ├── app/
│   │   ├── domain/        # Domain models/services
│   │   ├── ports/         # Hexagonal interfaces
│   │   ├── usecases/      # Business logic
│   │   ├── adapters/      # Inbound/outbound adapters
│   │   └── main.py        # Composition root
│   └── tests/
├── frontend/              # React + Vite
│   └── src/
└── docs/                  # Product/architecture docs
```

## Docs

- Product vision: `docs/planning.md`
- Architecture: `docs/architecture.md`
- Delivery model: `docs/delivery-model.md`
- Frontend conventions: `docs/frontend-conventions.md`

## Tests and Checks

```bash
# backend
cd backend
pytest

# frontend
cd frontend
npm run lint
npm run test
npm run build
```

Please run relevant checks before opening a PR.

## `.gitignore` Policy

We use `github/gitignore` as the source of truth.

- Base templates:
  - `Python.gitignore`
  - `Node.gitignore`
  - `Global/macOS.gitignore`
- Keep repository-specific rules in a dedicated section at the bottom.
- Do not add ad-hoc ignore patterns without explaining why in the PR.
- If `.gitignore` changes, include links to the upstream templates used.

## Pull Request Guidelines

- Use clear, descriptive titles.
- Explain what changed and why.
- Link related issues (`Fixes #123`, `Refs #123`).
- Include test coverage for behavior changes.
- Keep PR size manageable.

## Commit Messages

Prefer conventional prefixes:

- `feat`: new feature
- `fix`: bug fix
- `docs`: documentation
- `refactor`: refactor without behavior change
- `test`: tests
- `chore`: maintenance/tooling

## Reporting Security Issues

Do not open public issues for sensitive vulnerabilities.  
See `SECURITY.md` for disclosure instructions.
