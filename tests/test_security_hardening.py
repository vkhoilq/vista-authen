import pytest
import uuid
import asyncio
from datetime import datetime, timedelta, timezone
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

from app.main import app
from app.core.database import get_db
from app.core.security import hash_password, create_access_token
from app.core.limiter import limiter
from app.models.models import ActivationToken, AuditLog, Admin, AdminRole, Unit, Resident, ResidentStatus
from app.services.cleanup_service import CleanupService

@pytest.fixture
async def client(db_session):
    async def _get_db_override():
        yield db_session
    
    app.dependency_overrides[get_db] = _get_db_override
    # Use ASGITransport for modern httpx version async testing
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_invalid_pem_public_key_rejected(client):
    # Try to register a device with an invalid public key PEM format
    payload = {
        "activation_token": "some-token",
        "public_key_pem": "not-a-real-pem-key"
    }
    response = await client.post("/api/v1/residents/register", json=payload)
    assert response.status_code == 422
    assert "Invalid PEM public key" in response.text


@pytest.mark.asyncio
async def test_oversized_qr_payload_rejected(client, sample_checker):
    # Authenticate as checker first
    token = create_access_token(
        data={"sub": str(sample_checker.id), "role": sample_checker.role.value, "type": "checker"}
    )
    headers = {"Authorization": f"Bearer {token}"}

    # Try to verify an oversized QR payload (> 10KB)
    oversized_payload = "A" * 11000
    payload = {
        "qr_payload": oversized_payload
    }
    
    # Send request with authorization headers
    response = await client.post("/api/v1/access/verify", json=payload, headers=headers)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_rate_limiting_login_endpoint(client):
    # Clear limiter state before test
    limiter.reset()
    
    payload = {
        "username": "nonexistent_admin",
        "password": "wrongpassword"
    }
    
    # Send 5 requests (which should get 401 Unauthorized)
    for _ in range(5):
        response = await client.post("/api/v1/auth/admin/login", json=payload)
        assert response.status_code == 401
        
    # The 6th request should get 429 Too Many Requests
    response = await client.post("/api/v1/auth/admin/login", json=payload)
    assert response.status_code == 429
    assert response.json()["detail"] == "Rate limit exceeded"


@pytest.mark.asyncio
async def test_database_cleanup_service(db_session, sample_unit):
    # Create three separate residents to satisfy UNIQUE activation token constraints
    res1 = Resident(unit_id=sample_unit.id, name="Resident A", status=ResidentStatus.PENDING)
    res2 = Resident(unit_id=sample_unit.id, name="Resident B", status=ResidentStatus.PENDING)
    res3 = Resident(unit_id=sample_unit.id, name="Resident C", status=ResidentStatus.PENDING)
    db_session.add_all([res1, res2, res3])
    await db_session.flush()

    # Create expired token
    expired_token = ActivationToken(
        resident_id=res1.id,
        token="expired-token-123",
        expires_at=datetime.now(timezone.utc) - timedelta(hours=2),
        used_at=None
    )
    # Create used token
    used_token = ActivationToken(
        resident_id=res2.id,
        token="used-token-123",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=2),
        used_at=datetime.now(timezone.utc) - timedelta(hours=1)
    )
    # Create valid token
    valid_token = ActivationToken(
        resident_id=res3.id,
        token="valid-token-123",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=2),
        used_at=None
    )
    
    db_session.add_all([expired_token, used_token, valid_token])
    await db_session.flush()

    # Create old and new audit logs
    old_log = AuditLog(
        timestamp=datetime.now(timezone.utc) - timedelta(days=95),
        action="scan_success",
        actor_role="checker",
        unit_id=sample_unit.id,
        details={}
    )
    new_log = AuditLog(
        timestamp=datetime.now(timezone.utc) - timedelta(days=10),
        action="scan_success",
        actor_role="checker",
        unit_id=sample_unit.id,
        details={}
    )
    
    db_session.add_all([old_log, new_log])
    await db_session.commit()

    # Run CleanupService
    svc = CleanupService(db_session)
    results = await svc.cleanup_all()
    
    assert results["purged_tokens"] == 2
    assert results["purged_audit_logs"] == 1
    
    # Assert database states
    tokens = (await db_session.execute(select(ActivationToken))).scalars().all()
    assert len(tokens) == 1
    assert tokens[0].token == "valid-token-123"

    logs = (await db_session.execute(select(AuditLog))).scalars().all()
    assert len(logs) == 1
    assert logs[0].timestamp > datetime.now(timezone.utc) - timedelta(days=90)


@pytest.mark.asyncio
async def test_manual_cleanup_endpoint_rbac(client, db_session):
    # Clear limiter state before running login tests to prevent 429 bleed-over
    limiter.reset()

    # Create a Setup Admin and Staff Admin and Resident Admin
    setup_admin = Admin(
        username="setup_cleanup_admin",
        hashed_password=hash_password("admin123"),
        role=AdminRole.SETUP_ADMIN,
        is_active=True
    )
    resident_admin = Admin(
        username="resident_cleanup_admin",
        hashed_password=hash_password("admin123"),
        role=AdminRole.RESIDENT_ADMIN,
        is_active=True
    )
    db_session.add_all([setup_admin, resident_admin])
    await db_session.commit()

    # Login as Resident Admin (which is NOT authorized for cleanup)
    res_login = await client.post("/api/v1/auth/admin/login", json={
        "username": "resident_cleanup_admin",
        "password": "admin123"
    })
    assert res_login.status_code == 200
    res_token = res_login.json()["access_token"]

    # Try manual cleanup -> should return 403 Forbidden
    cleanup_res = await client.post(
        "/api/v1/admin/cleanup",
        headers={"Authorization": f"Bearer {res_token}"}
    )
    assert cleanup_res.status_code == 403

    # Reset limiter again just in case
    limiter.reset()

    # Login as Setup Admin (authorized)
    setup_login = await client.post("/api/v1/auth/admin/login", json={
        "username": "setup_cleanup_admin",
        "password": "admin123"
    })
    assert setup_login.status_code == 200
    setup_token = setup_login.json()["access_token"]

    # Try manual cleanup -> should return 200 OK
    cleanup_res = await client.post(
        "/api/v1/admin/cleanup",
        headers={"Authorization": f"Bearer {setup_token}"}
    )
    assert cleanup_res.status_code == 200
    assert cleanup_res.json()["status"] == "success"


@pytest.mark.asyncio
async def test_owner_provision_and_contact_update_api(client, db_session, sample_unit):
    # Clear rate limiter
    limiter.reset()
    admin = Admin(
        username="resident_admin_test",
        hashed_password=hash_password("admin123"),
        role=AdminRole.RESIDENT_ADMIN,
        is_active=True
    )
    db_session.add(admin)
    await db_session.commit()

    # Login as Resident Admin
    login_resp = await client.post("/api/v1/auth/admin/login", json={
        "username": "resident_admin_test",
        "password": "admin123"
    })
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Try to provision first resident (owner) without contact info -> should fail
    fail_payload = {
        "unit_id": str(sample_unit.id),
        "name": "First Resident Fail"
    }
    response = await client.post("/api/v1/residents", json=fail_payload, headers=headers)
    assert response.status_code == 400
    assert "must provide a telephone number and email address" in response.json()["detail"]

    # 2. Provision first resident (owner) with contact info -> should succeed
    success_payload = {
        "unit_id": str(sample_unit.id),
        "name": "First Resident Success",
        "phone": "+123456789",
        "email": "owner@example.com"
    }
    response = await client.post("/api/v1/residents", json=success_payload, headers=headers)
    assert response.status_code == 201
    data = response.json()
    owner_id = data["resident"]["id"]
    assert data["resident"]["is_owner"] is True
    assert data["resident"]["phone"] == "+123456789"
    assert data["resident"]["email"] == "owner@example.com"

    # 3. Try to provision second resident with contact info -> should fail
    subsequent_fail_payload = {
        "unit_id": str(sample_unit.id),
        "name": "Second Resident Fail",
        "phone": "+987654321",
        "email": "second@example.com"
    }
    response = await client.post("/api/v1/residents", json=subsequent_fail_payload, headers=headers)
    assert response.status_code == 400
    assert "Only the apartment Owner" in response.json()["detail"]

    # 4. Provision second resident without contact info -> should succeed
    subsequent_success_payload = {
        "unit_id": str(sample_unit.id),
        "name": "Second Resident Success"
    }
    response = await client.post("/api/v1/residents", json=subsequent_success_payload, headers=headers)
    assert response.status_code == 201
    data2 = response.json()
    regular_id = data2["resident"]["id"]
    assert data2["resident"]["is_owner"] is False
    assert data2["resident"]["phone"] is None
    assert data2["resident"]["email"] is None

    # 5. Update contact details of owner -> should succeed
    update_payload = {
        "phone": "+1999999999",
        "email": "new_email@example.com"
    }
    response = await client.patch(f"/api/v1/residents/{owner_id}/contact", json=update_payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["phone"] == "+1999999999"
    assert data["email"] == "new_email@example.com"

    # 6. Try to update contact details of non-owner -> should fail
    response = await client.patch(f"/api/v1/residents/{regular_id}/contact", json=update_payload, headers=headers)
    assert response.status_code == 400
    assert "Only the apartment Owner's contact information can be updated" in response.json()["detail"]

    # 7. Try to update contact details of owner with empty values -> should fail
    empty_payload = {
        "phone": "  ",
        "email": "owner@example.com"
    }
    response = await client.patch(f"/api/v1/residents/{owner_id}/contact", json=empty_payload, headers=headers)
    assert response.status_code == 400
    assert "Telephone number cannot be empty" in response.json()["detail"]

