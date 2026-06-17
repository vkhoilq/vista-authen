import base64
import uuid
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Checker, CheckerRole, Resident, ResidentStatus
from app.services.access_service import AccessService


async def _create_active_resident_with_key(db_session: AsyncSession, unit_id) -> tuple[Resident, ec.EllipticCurvePrivateKey]:
    """Helper: create an active resident with ECC key pair. Returns (resident, private_key)."""
    private_key = ec.generate_private_key(ec.SECP256R1())
    public_key = private_key.public_key()
    public_pem = public_key.public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()

    resident = Resident(
        unit_id=unit_id,
        name="Test Resident",
        status=ResidentStatus.ACTIVE,
        public_key=public_pem,
    )
    db_session.add(resident)
    await db_session.flush()
    await db_session.refresh(resident)
    return resident, private_key


def _sign_payload(private_key: ec.EllipticCurvePrivateKey, payload: str) -> str:
    """Sign a payload string and return base64-encoded signature."""
    signature = private_key.sign(payload.encode(), ec.ECDSA(hashes.SHA256()))
    return base64.b64encode(signature).decode()


def _build_qr_payload(resident_id: uuid.UUID, timestamp: int, signature_b64: str) -> str:
    return f"V1|{resident_id}|{timestamp}|{signature_b64}"


class TestAccessServiceVerifyValid:
    async def test_verify_valid_qr_guard(self, db_session: AsyncSession, sample_unit, sample_checker):
        resident, private_key = await _create_active_resident_with_key(db_session, sample_unit.id)
        svc = AccessService(db_session)

        timestamp = int(datetime.now(timezone.utc).timestamp())
        payload_str = f"{resident.id}|{timestamp}"
        sig_b64 = _sign_payload(private_key, payload_str)
        qr_payload = _build_qr_payload(resident.id, timestamp, sig_b64)

        result = await svc.verify(qr_payload, sample_checker.id)
        assert result["status"] == "valid"

    async def test_verify_valid_qr_manager(self, db_session: AsyncSession, sample_unit, sample_manager):
        resident, private_key = await _create_active_resident_with_key(db_session, sample_unit.id)
        svc = AccessService(db_session)

        timestamp = int(datetime.now(timezone.utc).timestamp())
        payload_str = f"{resident.id}|{timestamp}"
        sig_b64 = _sign_payload(private_key, payload_str)
        qr_payload = _build_qr_payload(resident.id, timestamp, sig_b64)

        result = await svc.verify(qr_payload, sample_manager.id)
        assert result["status"] == "valid"
        assert result["resident_name"] == "Test Resident"
        assert result["unit"] == "A-101"
        assert result["phone"] is None

    async def test_verify_valid_qr_manager_receives_owner_phone(self, db_session: AsyncSession, sample_unit, sample_manager):
        resident, private_key = await _create_active_resident_with_key(db_session, sample_unit.id)
        resident.is_owner = True
        resident.phone = "+1234567890"
        await db_session.flush()
        
        svc = AccessService(db_session)
        timestamp = int(datetime.now(timezone.utc).timestamp())
        payload_str = f"{resident.id}|{timestamp}"
        sig_b64 = _sign_payload(private_key, payload_str)
        qr_payload = _build_qr_payload(resident.id, timestamp, sig_b64)

        result = await svc.verify(qr_payload, sample_manager.id)
        assert result["status"] == "valid"
        assert result["resident_name"] == "Test Resident"
        assert result["unit"] == "A-101"
        assert result["phone"] == "+1234567890"

    async def test_verify_valid_qr_guard_no_phone(self, db_session: AsyncSession, sample_unit, sample_checker):
        resident, private_key = await _create_active_resident_with_key(db_session, sample_unit.id)
        resident.is_owner = True
        resident.phone = "+1234567890"
        await db_session.flush()
        
        svc = AccessService(db_session)
        timestamp = int(datetime.now(timezone.utc).timestamp())
        payload_str = f"{resident.id}|{timestamp}"
        sig_b64 = _sign_payload(private_key, payload_str)
        qr_payload = _build_qr_payload(resident.id, timestamp, sig_b64)

        result = await svc.verify(qr_payload, sample_checker.id)
        assert result["status"] == "valid"
        assert "phone" not in result



class TestAccessServiceVerifyExpired:
    async def test_verify_expired_timestamp(self, db_session: AsyncSession, sample_unit, sample_checker):
        resident, private_key = await _create_active_resident_with_key(db_session, sample_unit.id)
        svc = AccessService(db_session)

        # Timestamp 120 seconds in the past (beyond 60s tolerance)
        timestamp = int(datetime.now(timezone.utc).timestamp()) - 120
        payload_str = f"{resident.id}|{timestamp}"
        sig_b64 = _sign_payload(private_key, payload_str)
        qr_payload = _build_qr_payload(resident.id, timestamp, sig_b64)

        result = await svc.verify(qr_payload, sample_checker.id)
        assert result["status"] == "expired"


class TestAccessServiceVerifyBadSignature:
    async def test_verify_tampered_signature(self, db_session: AsyncSession, sample_unit, sample_checker):
        resident, private_key = await _create_active_resident_with_key(db_session, sample_unit.id)
        svc = AccessService(db_session)

        timestamp = int(datetime.now(timezone.utc).timestamp())
        payload_str = f"{resident.id}|{timestamp}"
        sig_b64 = _sign_payload(private_key, payload_str)
        # Tamper with the signature
        tampered_sig = base64.b64encode(b"\x00" * 64).decode()
        qr_payload = _build_qr_payload(resident.id, timestamp, tampered_sig)

        result = await svc.verify(qr_payload, sample_checker.id)
        assert result["status"] == "invalid"

    async def test_verify_wrong_resident_id(self, db_session: AsyncSession, sample_unit, sample_checker):
        resident, private_key = await _create_active_resident_with_key(db_session, sample_unit.id)
        svc = AccessService(db_session)

        timestamp = int(datetime.now(timezone.utc).timestamp())
        # Sign with correct key but use wrong resident_id
        wrong_id = uuid.uuid4()
        payload_str = f"{wrong_id}|{timestamp}"
        sig_b64 = _sign_payload(private_key, payload_str)
        qr_payload = _build_qr_payload(wrong_id, timestamp, sig_b64)

        result = await svc.verify(qr_payload, sample_checker.id)
        assert result["status"] == "invalid"

    async def test_verify_revoked_resident(self, db_session: AsyncSession, sample_unit, sample_checker):
        resident, private_key = await _create_active_resident_with_key(db_session, sample_unit.id)
        # Revoke the resident
        resident.status = ResidentStatus.REVOKED
        resident.public_key = None
        await db_session.flush()

        svc = AccessService(db_session)
        timestamp = int(datetime.now(timezone.utc).timestamp())
        payload_str = f"{resident.id}|{timestamp}"
        sig_b64 = _sign_payload(private_key, payload_str)
        qr_payload = _build_qr_payload(resident.id, timestamp, sig_b64)

        result = await svc.verify(qr_payload, sample_checker.id)
        assert result["status"] == "invalid"


class TestAccessServiceVerifyMalformed:
    async def test_verify_invalid_format(self, db_session: AsyncSession, sample_checker):
        svc = AccessService(db_session)
        result = await svc.verify("not-a-valid-qr", sample_checker.id)
        assert result["status"] == "invalid"

    async def test_verify_missing_version(self, db_session: AsyncSession, sample_checker):
        svc = AccessService(db_session)
        result = await svc.verify("resident-id|timestamp|sig", sample_checker.id)
        assert result["status"] == "invalid"

    async def test_verify_invalid_resident_id_format(self, db_session: AsyncSession, sample_checker):
        svc = AccessService(db_session)
        result = await svc.verify("V1|not-a-uuid|1700000000|sig", sample_checker.id)
        assert result["status"] == "invalid"

    async def test_verify_invalid_timestamp_format(self, db_session: AsyncSession, sample_checker):
        svc = AccessService(db_session)
        result = await svc.verify(f"V1|{uuid.uuid4()}|not-a-number|sig", sample_checker.id)
        assert result["status"] == "invalid"