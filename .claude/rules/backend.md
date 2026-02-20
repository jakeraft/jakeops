---
paths:
  - "backend/**"
---

# Backend Convention

## Stack
- Python 3.11+ / FastAPI / uvicorn / Pydantic v2

## Architecture Rules (Absolute)
- Dependency direction: adapters/inbound -> usecases -> ports/outbound <- adapters/outbound
- usecases must only depend on ports/outbound Protocols, never import adapters/outbound directly
- adapters/inbound (routers) must only depend on usecases, may reference domain/models
- domain/services/ must not depend on ports or adapters (pure domain logic only)
- DI assembly happens only in main.py

## File Creation Order for New Features
1. domain/models/ — Define Pydantic domain models
2. ports/outbound/ — Define Repository Protocol (if needed)
3. ports/inbound/ — Define Use Case Protocol
4. usecases/ — Implement Use Case
5. adapters/outbound/ — Implement Repository (if needed)
6. adapters/inbound/ — FastAPI router
7. main.py — Add DI assembly

## Coding Rules
- Use Python typing for all functions/methods
- Domain models inherit from Pydantic BaseModel
- Protocols use typing.Protocol
- No business logic in routers — delegate to usecases
- Environment variables are read only at the top of main.py

## Testing
- pytest + httpx (TestClient)
- Usecase unit tests: inject mock repositories
- Router integration tests: use TestClient
