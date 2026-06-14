import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.models import AuditLog, Resident, ResidentStatus, Unit


class UnitService:
    """Service for managing building units."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, unit_number: str, max_residents: int) -> Unit:
        unit = Unit(unit_number=unit_number, max_residents=max_residents)
        self.db.add(unit)
        await self.db.flush()
        return unit

    async def update_capacity(self, unit_id: uuid.UUID, max_residents: int) -> Unit | None:
        unit = await self.db.get(Unit, unit_id)
        if unit is None:
            return None

        # Prevent setting capacity below current active resident count
        active_count = await self._active_resident_count(unit_id)
        if max_residents < active_count:
            raise ValueError(
                f"Cannot set max_residents to {max_residents}: "
                f"unit already has {active_count} active residents"
            )

        unit.max_residents = max_residents
        await self.db.flush()
        return unit

    async def delete(self, unit_id: uuid.UUID) -> bool:
        unit = await self.db.get(Unit, unit_id)
        if unit is None:
            return False

        # Block deletion if residents exist
        active_count = await self._active_resident_count(unit_id)
        if active_count > 0:
            raise ValueError(f"Cannot delete unit: {active_count} residents still assigned")

        await self.db.delete(unit)
        await self.db.flush()
        return True

    async def get(self, unit_id: uuid.UUID) -> Unit | None:
        return await self.db.get(Unit, unit_id)

    async def list_all(self) -> list[Unit]:
        result = await self.db.execute(select(Unit).order_by(Unit.unit_number))
        return list(result.scalars().all())

    async def _active_resident_count(self, unit_id: uuid.UUID) -> int:
        result = await self.db.execute(
            select(func.count(Resident.id)).where(
                Resident.unit_id == unit_id,
                Resident.status != ResidentStatus.REVOKED,
            )
        )
        return result.scalar_one()