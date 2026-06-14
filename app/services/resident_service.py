import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.models import ActivationToken, AuditLog, Resident, ResidentStatus, Unit


class ResidentService:
    """Service for managing residents and device activation."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def provision(self, unit_id: uuid.UUID, name: str, actor_id: uuid.UUID | None = None) -> dict:
        """Create a new resident with capacity enforcement. Returns dict with resident + token."""
        # Check unit exists
        unit = await self.db.get(Unit, unit_id)
        if unit is None:
            raise ValueError(f"Unit {unit_id} not found")

        # Enforce capacity cap
        active_count = await self._active_resident_count(unit_id)
        if active_count >= unit.max_residents:
            # Log blocked attempt
            await self._log_action(
                action="registration_blocked",
                actor_id=actor_id,
                actor_role="resident_admin",
                unit_id=unit_id,
                details={"attempted_name": name, "active_count": active_count, "max_residents": unit.max_residents},
            )
            raise ValueError(
                f"Cannot provision resident: unit {unit.unit_number} "
                f"is at capacity ({active_count}/{unit.max_residents})"
            )

        # Create resident
        resident = Resident(unit_id=unit_id, name=name, status=ResidentStatus.PENDING)
        self.db.add(resident)
        await self.db.flush()

        # Generate activation token
        token = ActivationToken(
            resident_id=resident.id,
            token=uuid.uuid4().hex,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=settings.ACTIVATION_TOKEN_TTL_HOURS),
        )
        self.db.add(token)
        await self.db.flush()

        # Log creation
        await self._log_action(
            action="resident_provisioned",
            actor_id=actor_id,
            actor_role="resident_admin",
            unit_id=unit_id,
            details={"resident_id": str(resident.id), "resident_name": name},
        )

        return {"resident": resident, "activation_token": token}

    async def register_device(self, activation_token: str, public_key_pem: str) -> Resident:
        """Bind a device public key to a resident, activating them."""
        # Find token
        result = await self.db.execute(
            select(ActivationToken).where(ActivationToken.token == activation_token)
        )
        token = result.scalar_one_or_none()

        if token is None:
            raise ValueError("Invalid activation token")

        if token.used_at is not None:
            raise ValueError("Activation token already used")

        if token.expires_at < datetime.now(timezone.utc):
            raise ValueError("Activation token expired")

        # Get resident
        resident = await self.db.get(Resident, token.resident_id)
        if resident is None:
            raise ValueError("Resident not found")

        if resident.status != ResidentStatus.PENDING:
            raise ValueError(f"Resident is not in pending state (current: {resident.status})")

        # Activate
        resident.public_key = public_key_pem
        resident.status = ResidentStatus.ACTIVE
        token.used_at = datetime.now(timezone.utc)

        await self.db.flush()

        # Log activation
        await self._log_action(
            action="device_activated",
            actor_id=resident.id,
            actor_role="resident",
            unit_id=resident.unit_id,
            details={"resident_id": str(resident.id)},
        )

        return resident

    async def revoke(self, resident_id: uuid.UUID, actor_id: uuid.UUID | None = None) -> Resident | None:
        """Revoke a resident's access, clearing their public key."""
        resident = await self.db.get(Resident, resident_id)
        if resident is None:
            return None

        resident.status = ResidentStatus.REVOKED
        resident.public_key = None
        resident.revoked_at = datetime.now(timezone.utc)

        await self.db.flush()

        # Log revocation
        await self._log_action(
            action="device_revoked",
            actor_id=actor_id,
            actor_role="resident_admin",
            unit_id=resident.unit_id,
            details={"resident_id": str(resident_id), "resident_name": resident.name},
        )

        return resident

    async def get(self, resident_id: uuid.UUID) -> Resident | None:
        return await self.db.get(Resident, resident_id)

    async def list_by_unit(self, unit_id: uuid.UUID) -> list[Resident]:
        result = await self.db.execute(
            select(Resident).where(Resident.unit_id == unit_id).order_by(Resident.name)
        )
        return list(result.scalars().all())

    async def _active_resident_count(self, unit_id: uuid.UUID) -> int:
        result = await self.db.execute(
            select(func.count(Resident.id)).where(
                Resident.unit_id == unit_id,
                Resident.status != ResidentStatus.REVOKED,
            )
        )
        return result.scalar_one()

    async def _log_action(
        self,
        action: str,
        actor_id: uuid.UUID | None = None,
        actor_role: str | None = None,
        unit_id: uuid.UUID | None = None,
        details: dict | None = None,
    ) -> AuditLog:
        log = AuditLog(
            action=action,
            actor_id=actor_id,
            actor_role=actor_role,
            unit_id=unit_id,
            details=details,
        )
        self.db.add(log)
        await self.db.flush()
        return log