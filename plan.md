# Vista Authen — Project Plan & Architecture

## Overall Goal

**Hardware-Bound Offline QR Access Control System** — a secure, self-hosted residential access control system that replaces traditional password authentication with asymmetric cryptography (public/private keys). Residents generate dynamic, anti-replay QR codes entirely offline. Checkers scan and verify them via a centralized backend.

---

## System Architecture

```
┌──────────────────────┐     ┌──────────────────────┐
│   Resident Client     │     │    Checker Client     │
│  (Web / Mobile)      │     │   (Web / Mobile)      │
│                       │     │                       │
│  - Activation (token) │     │  - Login (JWT)        │
│  - Key gen (ECC P-256)│     │  - Camera scan QR     │
│  - Offline QR (30s)   │     │  - Manual paste QR    │
│  - Private key never  │     │  - Audit log viewer   │
│    leaves hardware    │     │    (manager only)     │
└──────────┬───────────┘     └───────────┬───────────┘
           │                             │
           │  POST /residents/register   │  POST /access/verify
           │  (activation only —         │  POST /auth/*/login
           │   one-time online)          │  GET  /audit-logs
           │                             │
           ▼                             ▼
┌─────────────────────────────────────────────────────────┐
│                   FastAPI Backend                        │
│                                                         │
│  ┌─────────────┐  ┌────────────┐  ┌──────────────────┐ │
│  │  Auth (JWT) │  │  Services  │  │  CryptoService   │ │
│  │  RBAC deps  │  │  (6)       │  │  (ECC + RSA)     │ │
│  └─────────────┘  └────────────┘  └──────────────────┘ │
│                                                         │
│  ┌────────────────────────────────────────────────────┐ │
│  │  PostgreSQL 16  │  Redis 7  │  Nginx (TLS)        │ │
│  └────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

---

## Actor Model (6 Roles)

| # | Role | Scope | Auth |
|---|------|-------|------|
| 1 | **Setup Admin** | One-time: create units, set capacity limits | JWT (`setup_admin`) |
| 2 | **Resident Admin** | Day-to-day: provision/revoke residents | JWT (`resident_admin`) |
| 3 | **Staff Admin** | Daily: create/deactivate checker accounts, view audit logs | JWT (`staff_admin`) |
| 4 | **Checker — Guard** | Scan QR → minimal result (`{status: "valid"}`) | JWT (`guard`) |
| 5 | **Checker — Manager** | Scan QR → extended result (+ resident_name, unit) + audit logs | JWT (`manager`) |
| 6 | **Resident** | Activate device, generate offline QR codes | One-time token |

---

## Key Architectural Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Crypto algorithm** | ECC P-256 | 64-byte signatures vs RSA's 256 bytes — fits in denser QR codes |
| **QR payload format** | `V1\|{id}\|{ts}\|{sig_b64}` | Pipe-delimited, version-prefixed, base64 signature |
| **QR rotation** | 30 seconds | Short enough to prevent screenshot replay, long enough to scan |
| **QR validity window** | ±60 seconds server-side | 2x rotation cycle — tolerates clock skew |
| **Activation** | Single-use token (UUID, 24h TTL) | Durable audit trail in PostgreSQL; one-time use enforced |
| **Key storage (prod)** | Secure Enclave (iOS) / Keystore (Android) | Private key never leaves hardware |
| **Key storage (web test)** | Web Crypto API + localStorage | For internal testing only; documented as not production-safe |
| **Auth** | JWT (HS256) with role claims | Stateless; `"type": "admin"|"checker"` + `"role"` claim |
| **RBAC** | FastAPI dependency injection | `require_admin_role(AdminRole.STAFF_ADMIN)` per-route |
| **DB driver** | Async SQLAlchemy + asyncpg | FastAPI is async-native; connection pooling built-in |
| **DB schema** | Declarative with UUID PKs | Portable, no auto-increment ID collisions in distributed setups |
| **Audit logs** | JSON column (PostgreSQL `jsonb`) | Flexible schema for `details`; indexed on `action` and `timestamp` |
| **Web client** | Vite + React 19 + TypeScript | Fast HMR, type sharing with backend via mirrored TS interfaces |
| **Test DB** | SQLite via aiosqlite | No Docker required for tests; JSON column works on both SQLite and PG |

---

## QR Verification Flow

```
Resident Device              Checker Device              Backend
      │                          │                          │
      │  [Every 30s]             │                          │
      │  timestamp = now()       │                          │
      │  payload = id|ts         │                          │
      │  sig = sign(payload)     │                          │
      │  qr = "V1|id|ts|sig"     │                          │
      │                          │                          │
      │── show QR ──────────────→│                          │
      │                          │── POST /access/verify ──→│
      │                          │                          │── parse QR (split on |)
      │                          │                          │── replay check (±60s)
      │                          │                          │── fetch resident by id
      │                          │                          │── load public_key (PEM)
      │                          │                          │── verify ECDSA signature
      │                          │                          │── RBAC filter (role)
      │                          │                          │── insert audit log
      │                          │←── response ──────────────│
      │                          │                          │
      │               Guard: {"status": "valid"}            │
      │               Manager: {"status", "resident_name", "unit"}
```

---

## Implementation Status

### Completed (This Session)

| Phase | Content | Files |
|-------|---------|-------|
| 0 | Project scaffold + Docker + config + web scaffold | `app/`, `docker-compose.yml`, `Dockerfile`, `nginx.conf`, `web/` |
| 1 | 6 ORM models + Alembic | `app/models/models.py`, `alembic/` |
| 2 | 17 Pydantic schemas | `app/schemas/schemas.py` |
| 3 | 7 services + security utils | `app/services/`, `app/core/security.py` |
| Tests | 75 unit tests (8 files) | `tests/` — all passing |
| 4 | 14 API routes + RBAC dependencies | `app/routes/`, `app/core/deps.py` |
| 5 | Web resident client (activation + QR) | `web/resident/` — builds clean |
| 6 | Web checker client (scanner + audit) | `web/checker/` — builds clean |

### Remaining

| Phase | Estimated Effort | Priority |
|-------|-----------------|----------|
| 7 — Security hardening | 1 session | High |
| 8 — Integration + edge case tests | 1 session | High |
| 9 — Mobile app (React Native) | 2–3 sessions | Deferred |

---

## Project Structure

```
vista-authen/
├── app/
│   ├── main.py                       # FastAPI app factory
│   ├── core/
│   │   ├── config.py                 # Pydantic BaseSettings
│   │   ├── database.py              # Async SQLAlchemy engine + session
│   │   ├── deps.py                  # JWT + RBAC dependency injection
│   │   └── security.py             # Password hashing + JWT encode/decode
│   ├── models/
│   │   └── models.py                # 6 ORM models (Unit, Resident, Checker, ...)
│   ├── schemas/
│   │   └── schemas.py               # 17 Pydantic request/response schemas
│   ├── services/
│   │   ├── unit_service.py          # CRUD units with capacity enforcement
│   │   ├── resident_service.py      # Provision, register device, revoke
│   │   ├── checker_service.py       # CRUD checkers + authenticate
│   │   ├── admin_service.py         # CRUD admins + authenticate
│   │   ├── crypto_service.py        # ECDSA + RSA signature verification
│   │   ├── access_service.py        # QR verify pipeline + RBAC response
│   │   └── audit_service.py         # Log + paginated/filtered query
│   └── routes/
│       ├── units.py                  # /api/v1/units (Setup Admin)
│       ├── residents.py             # /api/v1/residents (Resident Admin + self-service)
│       ├── checkers.py              # /api/v1/checkers (Staff Admin)
│       ├── auth.py                  # /api/v1/auth (admin + checker login)
│       ├── access.py                # /api/v1/access/verify (Checkers)
│       └── audit.py                 # /api/v1/audit-logs (Staff Admin + Manager)
├── tests/
│   ├── conftest.py                  # Async SQLite fixtures, sample entities
│   ├── test_security.py             # 7 tests — bcrypt + JWT
│   ├── test_crypto_service.py       # 9 tests — ECC + RSA sign/verify
│   ├── test_unit_service.py         # 8 tests — create, capacity, delete
│   ├── test_resident_service.py     # 11 tests — provision, activate, revoke
│   ├── test_checker_service.py      # 9 tests — create, update, auth
│   ├── test_admin_service.py        # 7 tests — create, auth
│   ├── test_access_service.py       # 10 tests — valid, expired, tampered, RBAC
│   └── test_audit_service.py        # 7 tests — log, filter, pagination
├── web/
│   ├── shared/                      # @vista-authen/shared
│   │   └── src/
│   │       ├── api.ts               # Axios client with JWT interceptor
│   │       ├── types.ts             # TS interfaces mirroring backend schemas
│   │       └── crypto.ts           # Web Crypto ECDSA P-256 key gen + signing
│   ├── resident/                    # Resident web app (port 5173)
│   │   └── src/screens/
│   │       ├── ActivationScreen.tsx  # Token → key gen → register
│   │       └── QRScreen.tsx         # 30s QR + countdown timer
│   └── checker/                     # Checker web app (port 5174)
│       └── src/
│           ├── components/
│           │   ├── QRScanner.tsx     # Live camera + jsQR decoding
│           │   └── AuditLogViewer.tsx # Paginated log table + filters
│           └── screens/
│               ├── LoginScreen.tsx   # Username/password → JWT
│               └── Dashboard.tsx    # Tabbed: Scanner + Audit Logs
├── docker-compose.yml               # postgres:16, redis:7, api, nginx
├── Dockerfile                       # Multi-stage Python build
├── nginx.conf                       # Reverse proxy + web client routes
├── pyproject.toml                   # Python deps + tool config
├── agents.md                        # Role definitions, flows, threat model
├── TODO.md                          # Remaining tasks (Phases 7–9)
└── plan.md                          # This file
```

---

## API Reference

| Method | Path | Auth | Role | Description |
|--------|------|------|------|-------------|
| `POST` | `/api/v1/units` | Admin JWT | Setup Admin | Create unit |
| `GET` | `/api/v1/units` | Admin JWT | Setup/Resident Admin | List units |
| `GET` | `/api/v1/units/{id}` | Admin JWT | Setup/Resident Admin | Get unit |
| `PATCH` | `/api/v1/units/{id}` | Admin JWT | Setup Admin | Update capacity |
| `DELETE` | `/api/v1/units/{id}` | Admin JWT | Setup Admin | Delete unit |
| `POST` | `/api/v1/residents` | Admin JWT | Resident Admin | Provision resident |
| `POST` | `/api/v1/residents/register` | Token | Self-service | Activate device |
| `GET` | `/api/v1/residents/{id}` | Admin JWT | Resident Admin | Get resident |
| `PATCH` | `/api/v1/residents/{id}/revoke` | Admin JWT | Resident Admin | Revoke resident |
| `GET` | `/api/v1/residents/by-unit/{id}` | Admin JWT | Resident Admin | List by unit |
| `POST` | `/api/v1/checkers` | Admin JWT | Staff Admin | Create checker |
| `GET` | `/api/v1/checkers` | Admin JWT | Staff Admin | List checkers |
| `PATCH` | `/api/v1/checkers/{id}` | Admin JWT | Staff Admin | Update checker |
| `POST` | `/api/v1/auth/admin/login` | — | — | Admin login → JWT |
| `POST` | `/api/v1/auth/checker/login` | — | — | Checker login → JWT |
| `POST` | `/api/v1/access/verify` | Checker JWT | Guard/Manager | Verify QR |
| `GET` | `/api/v1/audit-logs` | Admin JWT | Staff Admin | View audit logs |
| `GET` | `/health` | — | — | Health check |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend framework | FastAPI 0.136 (Python 3.12) |
| ORM | SQLAlchemy 2.0 (async) |
| Database | PostgreSQL 16 |
| Cache | Redis 7 |
| Reverse proxy | Nginx (TLS termination) |
| Containerization | Docker Compose |
| Auth | JWT (python-jose) + bcrypt (passlib) |
| Crypto | `cryptography` (ECC P-256 + RSA 2048) |
| Web frontend | Vite 6 + React 19 + TypeScript |
| QR generation | `qrcode.react` |
| QR scanning | `react-webcam` + `jsQR` |
| HTTP client | Axios |
| Testing (Python) | pytest + pytest-asyncio + aiosqlite |
| Testing (Web) | TypeScript strict mode + Vite build |
| Package manager (Python) | uv |
| Package manager (JS) | npm |
