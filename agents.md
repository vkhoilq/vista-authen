# Vista Authen — System Agents

This document defines all actors (human and system) in the Hardware-Bound Offline QR Access Control System, their roles, capabilities, and interaction flows.

---

## Human Actors

### 1. Setup Admin

**Role:** One-time building configuration. Sets up the building structure before any residents or staff exist.

| Capability | Description |
|-----------|-------------|
| Create units | `POST /api/v1/units` — Define unit number and max resident capacity |
| Update capacity | `PATCH /api/v1/units/{id}` — Adjust `max_residents` for a unit |
| Delete units | `DELETE /api/v1/units/{id}` — Remove unit (only if no residents bound) |

**Constraints:**
- Only active during initial setup or rare reconfiguration.
- Cannot manage residents, staff, or checkers.
- Unit deletion blocked if residents exist in that unit.

---

### 2. Resident Admin

**Role:** Day-to-day resident lifecycle management. Registers, binds, and revokes residents.

| Capability | Description |
|-----------|-------------|
| Provision residents | `POST /api/v1/residents` — Register a resident to a unit (enforces capacity cap) |
| Revoke residents | `PATCH /api/v1/residents/{id}/revoke` — Revoke access, nullify public key |
| View unit residents | `GET /api/v1/units/{id}/residents` — List all residents in a unit |
| View resident details | `GET /api/v1/residents/{id}` — See status, key binding, unit assignment |

**Constraints:**
- Cannot exceed `max_residents` per unit. Blocked attempts are logged with action `registration_blocked`.
- Cannot create units, staff, or checkers.
- Re-activation requires revoke → re-provision (new activation token).

---

### 3. Staff Admin

**Role:** Daily staff account management. Creates and manages all non-resident human accounts.

| Capability | Description |
|-----------|-------------|
| Create checkers | `POST /api/v1/checkers` — Create guard or manager accounts |
| Update checkers | `PATCH /api/v1/checkers/{id}` — Change role, reset password |
| Deactivate checkers | `PATCH /api/v1/checkers/{id}/deactivate` — Disable account without deletion |
| View audit logs | `GET /api/v1/audit-logs` — Full access to all audit trail entries |
| View staff roster | `GET /api/v1/checkers` — List all checker accounts and roles |

**Constraints:**
- Cannot manage residents or units.
- Audit log access is read-only — cannot modify or delete logs.
- Checker deactivation is soft-delete (account disabled, not removed).

---

### 4. Checker — Staff (Guard)

**Role:** Front-door security personnel. Minimal data access.

| Capability | Description |
|-----------|-------------|
| Login | `POST /api/v1/auth/login` → JWT |
| Scan & verify QR | `POST /api/v1/access/verify` with JWT auth → receive minimal response |
| View scan result | Green ✓ / Red ✗ only. No resident name or unit number. |

**Response payload (guard):**
```json
{ "status": "valid" | "invalid" | "expired" }
```

**Constraints:**
- Cannot view resident identity data.
- Cannot view audit logs.
- Rate-limited to 30 verify requests per minute.

---

### 5. Checker — Manager

**Role:** Senior security or building manager. Extended data access.

| Capability | Description |
|-----------|-------------|
| Login | `POST /api/v1/auth/login` → JWT |
| Scan & verify QR | `POST /api/v1/access/verify` with JWT auth → receive extended response |
| View audit logs | `GET /api/v1/audit-logs` — Paginated, filterable |

**Response payload (manager):**
```json
{
  "status": "valid" | "invalid" | "expired",
  "resident_name": "Nguyen Van A",
  "unit": "A-402"
}
```

**Constraints:**
- Same rate limits as guard.
- Audit log access is read-only.
- Cannot manage residents, units, or staff.

---

### 6. Resident

**Role:** Occupant who generates offline QR codes for building access.

| Capability | Description |
|-----------|-------------|
| Activate device | Input one-time activation token → generate hardware-bound key pair → submit public key to `POST /api/v1/residents/register` |
| Generate QR (offline) | Every 30 seconds: sign `{resident_id}|{timestamp}` with hardware private key → render QR. **No network required.** |
| View own status | See activation state, unit assignment, key binding status |

**Constraints:**
- Private key never leaves the device Secure Enclave / Keystore.
- One active key per resident. Re-activation requires Resident Admin to revoke and re-provision.
- QR is valid only within ±60 seconds of server time.
- Cannot generate QR until device is activated (status = `active`).

**Lifecycle States:**
```
pending  ──(activation)──→  active  ──(revocation)──→  revoked
```

---

## System Agents

### 7. CryptoService

**Role:** Signature verification engine. Stateless.

| Input | Output |
|-------|--------|
| `public_key_pem`, `payload_bytes`, `signature_bytes` | `bool` — valid/invalid |

**Behavior:**
- Supports ECC P-256 (primary) and RSA 2048 (fallback).
- Uses `cryptography` library: `ECDSA(SHA256())` for ECC, `PKCS1v15()` for RSA.
- No key storage — receives public key per request from ResidentService.

---

### 8. AccessService

**Role:** Orchestrates QR verification flow. Stateless.

**Processing pipeline:**
```
QR string → Parse → Replay check → Fetch resident → Verify signature → RBAC response → Audit log
```

**Rejection reasons and audit actions:**

| Condition | Audit action | Response status |
|-----------|-------------|-----------------|
| Timestamp ±60s expired | `scan_failed_expired` | `expired` |
| Resident not found or inactive | `scan_failed_bad_signature` | `invalid` |
| Signature verification fails | `scan_failed_bad_signature` | `invalid` |
| Valid scan | `scan_success` | `valid` |

---

### 9. ResidentService

**Role:** Resident lifecycle management. Stateful (DB).

**Key operations:**
- `provision(unit_id, name)` — Create resident with capacity check. Generate activation token.
- `register_device(activation_token, public_key_pem)` — Bind key, activate resident.
- `revoke(resident_id)` — Deactivate, clear public key.

**Capacity enforcement:**
```sql
SELECT COUNT(*) FROM residents
WHERE unit_id = :uid AND status != 'revoked'
-- if count >= max_residents → block + audit log
```

---

### 10. AuditService

**Role:** Immutable audit trail writer.

**Logged actions:**

| Action | Trigger |
|--------|---------|
| `registration_blocked` | Capacity exceeded on resident provisioning |
| `device_activated` | Resident successfully binds public key |
| `device_revoked` | Resident Admin revokes a resident |
| `scan_success` | Valid QR verification |
| `scan_failed_expired` | Expired timestamp in QR |
| `scan_failed_bad_signature` | Invalid signature or inactive resident |

**Schema:** `id`, `timestamp`, `action`, `actor_id` (who performed the action), `unit_id` (nullable), `details` (JSONB).

---

## Interaction Flows

### Initial Setup Flow
```
Setup Admin              Backend
 │── create unit ──────→ │
 │←── 201 Created ───────│
 │── update capacity ──→ │
 │←── 200 OK ────────────│
```

### Resident Provisioning Flow
```
Resident Admin           Backend                    Resident Device
 │── provision ────────→ │                              │
 │←── token + id ────────│                              │
 │── (sends token ──────────────────────────────────→)  │
 │                        │←── register(token, pubkey) ─│
 │                        │── activate + audit ──────────│
 │                        │── 200 OK ──────────────────→│
```

### QR Verification Flow
```
Resident Device          Checker Device              Backend
 │── show QR ──────────→ │                            │
 │                       │── scan QR ───────────────→ │
 │                       │                            │── parse + replay check
 │                       │                            │── fetch resident
 │                       │                            │── verify signature
 │                       │                            │── RBAC filter
 │                       │                            │── audit log
 │                       │←── response ─────────────── │
```

### Capacity Block Flow
```
Resident Admin           Backend
 │── provision ────────→ │
 │                        │── count residents >= max
 │                        │── insert audit (registration_blocked)
 │←── 400 Bad Request ───│
```

### Staff Management Flow
```
Staff Admin              Backend
 │── create checker ───→ │
 │←── 201 Created ────────│
 │── deactivate checker → │
 │←── 200 OK ─────────────│
```

---

## Data Ownership Matrix

| Data | Setup Admin | Resident Admin | Staff Admin | Guard | Manager | Resident |
|------|-------------|----------------|-------------|-------|---------|----------|
| Unit info | CRUD | R | — | — | — | — |
| Resident identity | — | CRUD | — | — | R | R (own) |
| Public key | — | R | — | — | — | W (own) |
| Activation token | — | R, create | — | — | — | R (own) |
| Checker accounts | — | — | CRUD | — | — | — |
| QR payload | — | — | — | Scan | Scan | Generate |
| Verification result | — | — | — | Minimal | Extended | — |
| Audit logs | — | — | R | — | R | — |

---

## Threat Model Summary

| Threat | Mitigation |
|--------|-----------|
| QR screenshot/replay | 30s rotation + ±60s server timestamp check |
| QR forgery | Asymmetric signature — private key never leaves hardware |
| Token reuse | Single-use activation token, marked `used_at` on consumption |
| Over-provisioning | `max_residents` cap enforced at DB/service level |
| Key extraction | Secure Enclave / Keystore — private key inaccessible to OS |
| Checker impersonation | JWT auth required for verify endpoint |
| Brute-force verify | Rate limiting (30 req/min per checker) |
| Privilege escalation | Role-based JWT claims — each role can only access its own endpoints |
| Orphaned access | Revocation nullifies public key; re-provisioning requires Resident Admin |