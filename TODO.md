# TODO.md — Remaining Implementation Tasks

## Completed Phases

- [x] **Phase 0** — Project scaffolding, Docker Compose, config, web client scaffold
- [x] **Phase 1** — Database models (Unit, Resident, Checker, Admin, AuditLog, ActivationToken) + Alembic
- [x] **Phase 2** — Pydantic schemas (Unit, Resident, Checker, Admin, Access, Audit, Auth)
- [x] **Phase 3** — Core services (UnitService, ResidentService, CheckerService, AdminService, CryptoService, AccessService, AuditService, Security)
- [x] **Tests Phases 1–3** — 75 unit tests across 8 test files
- [x] **Phase 4** — API routes (Units, Residents, Checkers, Auth, Access, Audit) + RBAC dependencies
- [x] **Phase 5** — Web resident client (activation, QR generation, 30s rotation)
- [x] **Phase 6** — Web checker client (login, camera scanner, manual paste, audit log viewer)

---

## Phase 7: Security Hardening & Edge Cases

### 7.1 QR Payload Format
- [ ] Finalize `V1|{resident_id}|{timestamp}|{signature_b64}` format
- [ ] Add version negotiation header / content type
- [ ] Add payload size validation (max 10KB)

### 7.2 Rate Limiting
- [ ] Wire `slowapi` middleware into FastAPI app
- [ ] Apply rate limit to `POST /api/v1/access/verify` (30 req/min per checker)
- [ ] Apply rate limit to `POST /api/v1/auth/*/login` (5 req/min per IP)
- [ ] Test: 31st request within a minute returns 429

### 7.3 HTTPS Enforcement
- [ ] Terminate TLS at nginx/Caddy reverse proxy
- [ ] Enforce HSTS headers
- [ ] Redirect HTTP → HTTPS
- [ ] Self-signed cert for local dev, Let's Encrypt for production

### 7.4 Key Revocation Flow
- [ ] Test end-to-end: revoked resident's QR → `POST /api/v1/access/verify` → returns `invalid`
- [ ] Verify audit log entry for revocation
- [ ] Verify re-provisioning works after revocation (new token → new key)

### 7.5 Token Cleanup
- [ ] Add APScheduler or Celery periodic task
- [ ] Purge expired activation tokens (hourly cron)
- [ ] Purge audit logs older than N days (configurable retention policy)
- [ ] Add `/api/v1/admin/cleanup` manual trigger endpoint

### 7.6 CORS Configuration
- [ ] Whitelist only specific web client origins (no wildcard `*`)
- [ ] Validate requests from checker app (port 5174) and resident app (port 5173)
- [ ] Handle preflight OPTIONS requests correctly

### 7.7 Input Validation
- [ ] Pydantic validators for: resident_id (UUID), timestamp (int), signature (base64)
- [ ] Sanitize audit log details — strip oversized JSONB payloads
- [ ] Validate `public_key_pem` is a real PEM key (not arbitrary string)
- [ ] Max field lengths on all string inputs

### 7.8 RBAC Enforcement
- [ ] Verify each role can only access its own endpoints
- [ ] Setup Admin cannot manage residents → 403
- [ ] Resident Admin cannot manage checkers → 403
- [ ] Guard cannot view audit logs → 403
- [ ] Deactivated checker/admin cannot get valid JWT at login
- [ ] Expired JWT returns 401 on any protected route

---

## Phase 8: Backend Testing (Integration & Edge Cases)

### 8.1 Integration Tests — Full HTTP Flow
- [ ] `tests/integration/test_api.py` — Use FastAPI `TestClient` with async SQLite
- [ ] Test: Setup Admin creates unit → 201
- [ ] Test: Resident Admin provisions resident → returns token
- [ ] Test: Resident self-registers with activation token → 200, status = active
- [ ] Test: Checker logs in → receives JWT + role
- [ ] Test: Generate valid QR client-side → verify via endpoint → 200, status = valid
- [ ] Test: Expired QR → verify → 200, status = expired
- [ ] Test: Tampered QR → verify → 200, status = invalid

### 8.2 RBAC Tests
- [ ] Test: Staff Admin tries to create unit → 403
- [ ] Test: Setup Admin tries to provision resident → 403
- [ ] Test: Resident Admin tries to create checker → 403
- [ ] Test: Guard tries to view audit logs → 403
- [ ] Test: Manager views audit logs → 200
- [ ] Test: No auth header → any protected route → 401

### 8.3 Edge Case Tests
- [ ] Duplicate activation token use → 400
- [ ] Revoked resident scan → invalid
- [ ] Over-capacity provisioning → 400 + audit `registration_blocked`
- [ ] Concurrent registration race condition (two residents for last slot)
- [ ] Soft-deactivated checker login → 401
- [ ] Activation token expiry → 400
- [ ] Invalid QR payload format → invalid
- [ ] Extremely large QR payload → rejected
- [ ] Empty public key PEM → 400

### 8.4 Web Client E2E Smoke Test
- [ ] Manual: Open resident web client (port 5173)
- [ ] Activate device with token → QR appears
- [ ] Open checker web client (port 5174) in another tab
- [ ] Login as guard → scan QR → verify returns valid
- [ ] Login as manager → scan QR → verify returns resident_name + unit
- [ ] Manager → Audit Logs tab → logs visible and filterable

---

## Phase 9: Mobile App (Deferred — Last)

### 9.1 React Native Scaffold
- [ ] Expo managed workflow init
- [ ] Add deps: `react-native-biometrics`, `react-native-qrcode-svg`, `expo-camera`, `expo-secure-store`, `axios`

### 9.2 Resident Mode — Activation
- [ ] Input activation token
- [ ] `react-native-biometrics.createKeys()` — generates RSA/ECC in Secure Enclave / Keystore
- [ ] Extract public key → `POST /api/v1/residents/register`
- [ ] Store `resident_id` in `expo-secure-store`
- [ ] Private key never leaves hardware

### 9.3 Resident Mode — Offline QR
- [ ] 30s interval: get timestamp → sign with `react-native-biometrics.createSignature()`
- [ ] Render QR via `react-native-qrcode-svg`
- [ ] Countdown timer UI
- [ ] **No network required** — works fully offline

### 9.4 Checker Mode — Login + Scan
- [ ] JWT auth → store in secure storage
- [ ] Camera via `expo-camera` → detect QR → `POST /api/v1/access/verify`
- [ ] Display result (guard: minimal, manager: extended)
- [ ] Manager: Audit log viewer screen

### 9.5 Anti-Screenshot
- [ ] Android: `FLAG_SECURE` on QR activity window
- [ ] iOS: Secure text entry hack or app background overlay

### 9.6 Mobile Testing
- [ ] Jest + React Native Testing Library for component tests
- [ ] Manual E2E on physical devices (hardware key binding requires real device)
- [ ] Test offline QR generation (airplane mode)

---

## Summary

| Phase | Status | Remaining Tasks |
|-------|--------|----------------|
| 0–6 + Tests | ✅ Done | 0 |
| 7 — Security Hardening | 🔴 Not started | 8 tasks |
| 8 — Backend Testing | 🔴 Not started | 4 task groups |
| 9 — Mobile App | 🔴 Deferred | 6 task groups |
