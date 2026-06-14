import uuid
from datetime import datetime, timedelta, timezone

import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Resident, ResidentStatus
from app.services.resident_service import ResidentService


class TestResidentServiceProvision:
    async def test_provision_resident(self, db_session: AsyncSession, sample_unit):
        svc = ResidentService(db_session)
        result = await svc.provision(unit_id=sample_unit.id, name="Nguyen Van A")
        assert result["resident"].name == "Nguyen Van A"
        assert result["resident"].status == ResidentStatus.PENDING
        assert result["resident"].unit_id == sample_unit.id
        assert result["activation_token"] is not None
        assert result["activation_token"].token is not None

    async def test_provision_resident_with_actor(self, db_session: AsyncSession, sample_unit):
        svc = ResidentService(db_session)
        actor_id = uuid.uuid4()
        result = await svc.provision(unit_id=sample_unit.id, name="Test", actor_id=actor_id)
        assert result["resident"] is not None

    async def test_provision_nonexistent_unit(self, db_session: AsyncSession):
        svc = ResidentService(db_session)
        with pytest.raises(ValueError, match="not found"):
            await svc.provision(unit_id=uuid.uuid4(), name="Test")

    async def test_provision_at_capacity(self, db_session: AsyncSession, sample_unit):
        """Unit with max_residents=2 should block the 3rd resident."""
        svc = ResidentService(db_session)
        # Add 2 active residents to fill capacity
        r1 = Resident(unit_id=sample_unit.id, name="R1", status=ResidentStatus.ACTIVE)
        r2 = Resident(unit_id=sample_unit.id, name="R2", status=ResidentStatus.ACTIVE)
        db_session.add_all([r1, r2])
        await db_session.flush()

        with pytest.raises(ValueError, match="at capacity"):
            await svc.provision(unit_id=sample_unit.id, name="R3")

    async def test_provision_revoked_does_not_count(self, db_session: AsyncSession, sample_unit):
        """Revoked residents should not count toward capacity."""
        svc = ResidentService(db_session)
        r1 = Resident(unit_id=sample_unit.id, name="R1", status=ResidentStatus.ACTIVE)
        r2 = Resident(unit_id=sample_unit.id, name="R2", status=ResidentStatus.REVOKED)
        db_session.add_all([r1, r2])
        await db_session.flush()

        # Should succeed — only 1 active, max is 2
        result = await svc.provision(unit_id=sample_unit.id, name="R3")
        assert result["resident"] is not None


class TestResidentServiceRegisterDevice:
    async def test_register_device_success(self, db_session: AsyncSession, sample_unit):
        svc = ResidentService(db_session)
        result = await svc.provision(unit_id=sample_unit.id, name="Test Resident")
        token = result["activation_token"].token

        # Generate a real ECC key pair
        private_key = ec.generate_private_key(ec.SECP256R1())
        public_key_pem = private_key.public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode()

        resident = await svc.register_device(activation_token=token, public_key_pem=public_key_pem)
        assert resident.status == ResidentStatus.ACTIVE
        assert resident.public_key is not None

    async def test_register_device_invalid_token(self, db_session: AsyncSession):
        svc = ResidentService(db_session)
        with pytest.raises(ValueError, match="Invalid activation token"):
            await svc.register_device(activation_token="nonexistent", public_key_pem="key")

    async def test_register_device_already_used_token(self, db_session: AsyncSession, sample_unit):
        svc = ResidentService(db_session)
        result = await svc.provision(unit_id=sample_unit.id, name="Test")
        token = result["activation_token"].token

        private_key = ec.generate_private_key(ec.SECP256R1())
        public_pem = private_key.public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode()

        # First use — success
        await svc.register_device(activation_token=token, public_key_pem=public_pem)

        # Second use — should fail
        with pytest.raises(ValueError, match="already used"):
            await svc.register_device(activation_token=token, public_key_pem=public_pem)

    async def test_register_device_expired_token(self, db_session: AsyncSession, sample_unit):
        svc = ResidentService(db_session)
        result = await svc.provision(unit_id=sample_unit.id, name="Test")
        token_obj = result["activation_token"]

        # Manually expire the token
        token_obj.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        await db_session.flush()

        private_key = ec.generate_private_key(ec.SECP256R1())
        public_pem = private_key.public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode()

        with pytest.raises(ValueError, match="expired"):
            await svc.register_device(activation_token=token_obj.token, public_key_pem=public_pem)


class TestResidentServiceRevoke:
    async def test_revoke_active_resident(self, db_session: AsyncSession, sample_unit):
        svc = ResidentService(db_session)
        result = await svc.provision(unit_id=sample_unit.id, name="Test")

        # Activate the resident first
        private_key = ec.generate_private_key(ec.SECP256R1())
        public_pem = private_key.public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode()
        resident = await svc.register_device(
            activation_token=result["activation_token"].token, public_key_pem=public_pem
        )

        # Revoke
        revoked = await svc.revoke(resident.id)
        assert revoked is not None
        assert revoked.status == ResidentStatus.REVOKED
        assert revoked.public_key is None
        assert revoked.revoked_at is not None

    async def test_revoke_nonexistent_resident(self, db_session: AsyncSession):
        svc = ResidentService(db_session)
        result = await svc.revoke(uuid.uuid4())
        assert result is None


class TestResidentServiceGetAndList:
    async def test_get_resident(self, db_session: AsyncSession, sample_unit):
        svc = ResidentService(db_session)
        result = await svc.provision(unit_id=sample_unit.id, name="Test")
        found = await svc.get(result["resident"].id)
        assert found is not None
        assert found.name == "Test"

    async def test_list_by_unit(self, db_session: AsyncSession, sample_unit):
        svc = ResidentService(db_session)
        await svc.provision(unit_id=sample_unit.id, name="R1")
        await svc.provision(unit_id=sample_unit.id, name="R2")
        residents = await svc.list_by_unit(sample_unit.id)
        assert len(residents) == 2