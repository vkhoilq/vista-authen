# Vista Authen — Development Instructions

## Project Purpose

Hardware-Bound Offline QR Access Control System. Residents generate dynamic QR codes signed with device-bound private keys (ECC P-256) to gain building access. Checkers scan and verify via a centralized FastAPI backend. The private key never leaves the device.

---

## How to Work on This Project

### Workflow Philosophy

- **Plan first, code second.** Before any implementation, define the full plan with phases and concrete deliverables. Refer to `plan.md` for the current phase map.
- **Backend-first.** Core logic (models → schemas → services → routes) must be solid before touching UI. Mobile is deliberately deferred to last.
- **Phase with checkpoints.** Each phase produces verifiable output. Run tests after every phase. Never proceed with broken tests.
- **Single-word answers are fine.** No preamble, no flattery, no summaries unless asked. Just execute.

### Communication Style

- Be concise. Answer directly.
- Don't explain what you did unless asked.
- Don't praise code or ideas.
- If a request is ambiguous, ask one targeted question — don't guess.
- Push back on obviously wrong approaches, but don't lecture.

---

## Technical Conventions

### Python / Backend

| Convention | Rule |
|------------|------|
| **Framework** | FastAPI with async endpoints throughout |
| **ORM** | SQLAlchemy 2.0 async (`AsyncSession`, `async_sessionmaker`) |
| **Database** | PostgreSQL 16 in production, SQLite via aiosqlite in tests |
| **Migrations** | Alembic with async engine (`env.py` configured for async) |
| **Models** | Single file `app/models/models.py` — all 6 models together (Unit, Resident, Checker, Admin, AuditLog, ActivationToken). Use `Mapped[]` + `mapped_column()`. UUID PKs, not auto-increment. |
| **Schemas** | Single file `app/schemas/schemas.py`. Pydantic v2 with `model_config = {"from_attributes": True}` on ORM-facing schemas. |
| **Services** | One file per service in `app/services/`. Constructor takes `db: AsyncSession`. Methods call `await self.db.flush()` not `commit()` — commit is handled by the `get_db` dependency. |
| **Routes** | One file per resource in `app/routes/`. Prefix set in `main.py` via `app.include_router(router, prefix="/api/v1")`. |
| **Auth** | JWT (HS256) with `"sub"`, `"role"`, `"type": "admin"|"checker"` claims. RBAC via FastAPI dependency injection: `require_admin_role(AdminRole.STAFF_ADMIN)`. |
| **Password hashing** | bcrypt via `passlib[bcrypt]`. `hash_password()` and `verify_password()` in `app/core/security.py`. |
| **Package manager** | `uv` — use `uv sync`, `uv run`, `uv run pytest` |
| **Python version** | 3.12 minimum |
| **Linting** | Ruff (E, F, I, N, W, UP rules) |
| **Type checking** | mypy strict mode — but only for production code, not tests |

### Testing (Backend)

| Convention | Rule |
|------------|------|
| **Framework** | pytest + pytest-asyncio (`asyncio_mode = "auto"`) |
| **Test DB** | SQLite via `aiosqlite` — in-memory, created/dropped per test |
| **Fixtures** | All in `tests/conftest.py`. Use `setup_database` autouse fixture for table creation/destruction. Entity fixtures (`sample_unit`, `sample_checker`, etc.) use `await db_session.flush()`. |
| **Test file naming** | `test_{service_name}.py` — one file per service |
| **Test class naming** | `Test{Service}{MethodGroup}` — e.g., `TestResidentServiceProvision` |
| **Test method naming** | `test_{action}_{condition}` — e.g., `test_verify_valid_qr_guard` |
| **Assertions** | Plain `assert`, not `self.assertEqual`. Use `pytest.raises(ValueError, match="...")` for error cases. |
| **Crypto tests** | Use real `cryptography` key generation. Test both ECC P-256 and RSA 2048. Test base64 roundtrip (entire QR flow). Test wrong key, tampered sig, corrupted sig, empty sig. |
| **No mocks** | Tests use real SQLite, real crypto, real JWT. Don't mock services — mock at boundaries only if absolutely needed. |

### JSON Column Handling

**Lesson learned:** `JSONB` (PostgreSQL dialect) does NOT work with SQLite test database. Use `JSON` from `sqlalchemy.types` instead — it compiles correctly on both SQLite and PostgreSQL.

```python
# CORRECT:
from sqlalchemy import JSON
details: Mapped[dict | None] = mapped_column(JSON, nullable=True)

# WRONG (breaks SQLite tests):
from sqlalchemy.dialects.postgresql import JSONB
details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
```

### Crypto Service Type Safety

**Lesson learned:** `cryptography.hazmat.primitives.serialization.load_pem_public_key()` returns a union type that confuses type checkers. Use `isinstance` checks to narrow:

```python
public_key = serialization.load_pem_public_key(public_key_pem.encode())

if isinstance(public_key, ec.EllipticCurvePublicKey):
    public_key.verify(signature, payload, ec.ECDSA(hashes.SHA256()))
elif isinstance(public_key, rsa.RSAPublicKey):
    public_key.verify(signature, payload, padding.PKCS1v15(), hashes.SHA256())
else:
    return False  # unsupported key type
```

### TypeScript / Web Client

| Convention | Rule |
|------------|------|
| **Framework** | Vite 6 + React 19 + TypeScript strict mode |
| **Structure** | Monorepo with 3 packages: `web/shared`, `web/resident`, `web/checker` |
| **Shared package** | `@vista-authen/shared` — linked via `"file:../shared"`. Contains API client (`api.ts`), types (`types.ts`), crypto utils (`crypto.ts`), barrel export (`index.ts`). |
| **Types** | Mirror backend Pydantic schemas. Union types for discriminated responses (`AccessVerifyResponse = Guard | Manager`). Type guard functions (`isManagerResponse()`). |
| **API client** | Axios with JWT interceptor — reads token from localStorage (resident) or sessionStorage (checker). |
| **Crypto** | Web Crypto API for ECDSA P-256. Key stored as JWK in localStorage. **This is for testing only** — production uses `react-native-biometrics` hardware binding. |
| **QR** | `qrcode.react` for generation, `react-webcam` + `jsQR` for scanning. |
| **Auth** | Checker token in sessionStorage (cleared on tab close). Resident data in localStorage (persists). |
| **Ports** | Resident: 5173, Checker: 5174 |
| **Build check** | `npx tsc --noEmit` must pass before considering work done |

### Running the Project

```bash
# Backend
uv sync                           # Install Python deps
uv run uvicorn app.main:app --reload --port 8000
uv run pytest tests/ -v           # Run all tests (75 currently)

# Docker (full stack)
docker compose up -d              # postgres, redis, api, nginx

# Web clients
cd web/resident && npm install && npm run dev  # port 5173
cd web/checker  && npm install && npm run dev  # port 5174
```

---

## Actor / Role Model

Six distinct roles with strict RBAC. Refer to `agents.md` for full definitions.

| # | Role | JWT Claim | Capabilities |
|---|------|-----------|-------------|
| 1 | Setup Admin | `setup_admin` | CRUD units, set capacity |
| 2 | Resident Admin | `resident_admin` | Provision/resident CRUD |
| 3 | Staff Admin | `staff_admin` | CRUD checkers, view audit logs |
| 4 | Checker Guard | `guard` | Scan QR → minimal result |
| 5 | Checker Manager | `manager` | Scan QR → extended result + audit logs |
| 6 | Resident | (token-based) | Activate device, generate offline QR |

**RBAC rules:**
- Setup Admin cannot manage residents or checkers
- Resident Admin cannot create units or checkers
- Staff Admin cannot manage residents or units
- Guard cannot view audit logs or resident identity
- Manager can view audit logs and resident identity in verify results
- All endpoints return 403 if role doesn't match

---

## Key Design Decisions (Don't Change Without Discussion)

1. **ECC P-256, not RSA** — smaller signatures → denser QR codes
2. **`V1|{id}|{ts}|{sig_b64}`** QR format — pipe-delimited, version-prefixed
3. **30s QR rotation**, **±60s server tolerance** — anti-replay without annoying users
4. **UUID PKs** everywhere — no auto-increment, portable across DBs
5. **Async SQLAlchemy** — FastAPI is async-native; don't use sync DB sessions
6. **Commit in `get_db` dependency, not in services** — services call `flush()`, DI commits
7. **Single-use activation token** — stored in PostgreSQL, 24h TTL, marked `used_at` on consumption
8. **JSON not JSONB in models** — test compatibility; PostgreSQL stores JSON as jsonb internally anyway
9. **No mobile yet** — web clients for internal testing first, mobile last

---

## File Creation Rules

- Never create README, CONTRIBUTING, CHANGELOG, or any `*.md` file unless explicitly asked
- `agents.md`, `plan.md`, `TODO.md`, `instructions.md` were explicitly requested — these are project docs, not auto-generated
- Never create `__pycache__` manually — Python handles it
- Never run `git init` — the repo already exists
- Never commit, push, or create PRs unless asked

---

## Common Pitfalls (Avoid These)

1. **Don't commit in services** — always use `flush()`, let `get_db` handle commit/rollback
2. **Don't use `JSONB` type** — use `JSON` for SQLite test compatibility
3. **Don't mock in tests** — use real SQLite, real crypto, real JWT
4. **Don't add routes without RBAC** — every protected endpoint needs `require_*_role()` dep
5. **Don't skip `await db_session.flush()` in test fixtures** — UUIDs aren't generated until flush
6. **Don't use `import.meta.env` in shared package** — it won't have Vite types. Use static config.
7. **Don't pass JWT token as prop** — the API interceptor reads it from storage; components don't need it
8. **Don't nest services** — each service is independent. `AccessService` can use `CryptoService` but not `ResidentService` — do DB queries directly.

---

## Quick Reference: File Purposes

| File | Purpose |
|------|---------|
| `app/main.py` | FastAPI app factory, middleware, router registration |
| `app/core/config.py` | Environment config via `pydantic-settings` |
| `app/core/database.py` | Async engine, session factory, `Base`, `get_db` dependency |
| `app/core/security.py` | `hash_password`, `verify_password`, `create_access_token`, `decode_access_token` |
| `app/core/deps.py` | `get_current_admin`, `get_current_checker`, `require_admin_role()`, `require_checker_role()` |
| `app/models/models.py` | All 6 ORM models + enums |
| `app/schemas/schemas.py` | All Pydantic request/response schemas |
| `app/services/` | One file per service (unit, resident, checker, admin, crypto, access, audit) |
| `app/routes/` | One file per resource (units, residents, checkers, auth, access, audit) |
| `tests/conftest.py` | Async SQLite fixtures, entity fixtures |
| `web/shared/src/api.ts` | Axios client with JWT interceptor |
| `web/shared/src/types.ts` | TypeScript interfaces mirroring backend schemas |
| `web/shared/src/crypto.ts` | Web Crypto ECDSA utilities |
| `agents.md` | Role definitions, interaction flows, threat model |
| `plan.md` | Architecture summary, completed + remaining phases, API reference |
| `TODO.md` | Remaining tasks (Phases 7–9) in checkbox format |
| `instructions.md` | This file — how to work on this project |
