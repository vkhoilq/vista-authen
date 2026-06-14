import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Resident, ResidentStatus
from app.services.unit_service import UnitService


class TestUnitServiceCreate:
    async def test_create_unit(self, db_session: AsyncSession):
        svc = UnitService(db_session)
        unit = await svc.create(unit_number="A-101", max_residents=3)
        assert unit.id is not None
        assert unit.unit_number == "A-101"
        assert unit.max_residents == 3

    async def test_create_multiple_units(self, db_session: AsyncSession):
        svc = UnitService(db_session)
        u1 = await svc.create(unit_number="A-101", max_residents=2)
        u2 = await svc.create(unit_number="A-102", max_residents=4)
        assert u1.unit_number != u2.unit_number


class TestUnitServiceGet:
    async def test_get_existing_unit(self, db_session: AsyncSession, sample_unit):
        svc = UnitService(db_session)
        found = await svc.get(sample_unit.id)
        assert found is not None
        assert found.unit_number == "A-101"

    async def test_get_nonexistent_unit(self, db_session: AsyncSession):
        svc = UnitService(db_session)
        found = await svc.get(uuid.uuid4())
        assert found is None


class TestUnitServiceUpdateCapacity:
    async def test_update_capacity(self, db_session: AsyncSession, sample_unit):
        svc = UnitService(db_session)
        updated = await svc.update_capacity(sample_unit.id, max_residents=5)
        assert updated is not None
        assert updated.max_residents == 5

    async def test_update_capacity_nonexistent(self, db_session: AsyncSession):
        svc = UnitService(db_session)
        result = await svc.update_capacity(uuid.uuid4(), max_residents=5)
        assert result is None

    async def test_update_capacity_below_active_residents(self, db_session: AsyncSession, sample_unit):
        """Cannot set max_residents below current active resident count."""
        # Add 2 residents (max_residents=2)
        r1 = Resident(unit_id=sample_unit.id, name="R1", status=ResidentStatus.ACTIVE)
        r2 = Resident(unit_id=sample_unit.id, name="R2", status=ResidentStatus.ACTIVE)
        db_session.add_all([r1, r2])
        await db_session.flush()

        svc = UnitService(db_session)
        with pytest.raises(ValueError, match="Cannot set max_residents"):
            await svc.update_capacity(sample_unit.id, max_residents=1)


class TestUnitServiceDelete:
    async def test_delete_unit_with_no_residents(self, db_session: AsyncSession, sample_unit):
        svc = UnitService(db_session)
        result = await svc.delete(sample_unit.id)
        assert result is True

    async def test_delete_unit_with_residents(self, db_session: AsyncSession, sample_unit):
        """Cannot delete a unit that has residents."""
        resident = Resident(unit_id=sample_unit.id, name="R1", status=ResidentStatus.ACTIVE)
        db_session.add(resident)
        await db_session.flush()

        svc = UnitService(db_session)
        with pytest.raises(ValueError, match="Cannot delete unit"):
            await svc.delete(sample_unit.id)

    async def test_delete_nonexistent_unit(self, db_session: AsyncSession):
        svc = UnitService(db_session)
        result = await svc.delete(uuid.uuid4())
        assert result is False


class TestUnitServiceList:
    async def test_list_all_units(self, db_session: AsyncSession):
        svc = UnitService(db_session)
        await svc.create(unit_number="A-101", max_residents=2)
        await svc.create(unit_number="A-102", max_residents=3)
        units = await svc.list_all()
        assert len(units) == 2