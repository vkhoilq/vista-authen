import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import CheckerRole
from app.services.checker_service import CheckerService


class TestCheckerServiceCreate:
    async def test_create_guard(self, db_session: AsyncSession):
        svc = CheckerService(db_session)
        checker = await svc.create(username="guard1", password="password123", role=CheckerRole.GUARD)
        assert checker.username == "guard1"
        assert checker.role == CheckerRole.GUARD
        assert checker.is_active is True
        assert checker.hashed_password != "password123"

    async def test_create_manager(self, db_session: AsyncSession):
        svc = CheckerService(db_session)
        checker = await svc.create(username="manager1", password="password123", role=CheckerRole.MANAGER)
        assert checker.role == CheckerRole.MANAGER

    async def test_create_duplicate_username(self, db_session: AsyncSession):
        svc = CheckerService(db_session)
        await svc.create(username="guard1", password="password123", role=CheckerRole.GUARD)
        with pytest.raises(ValueError, match="already exists"):
            await svc.create(username="guard1", password="different", role=CheckerRole.GUARD)


class TestCheckerServiceUpdate:
    async def test_update_role(self, db_session: AsyncSession):
        svc = CheckerService(db_session)
        checker = await svc.create(username="guard1", password="password123", role=CheckerRole.GUARD)
        updated = await svc.update(checker.id, role=CheckerRole.MANAGER)
        assert updated is not None
        assert updated.role == CheckerRole.MANAGER

    async def test_deactivate_checker(self, db_session: AsyncSession):
        svc = CheckerService(db_session)
        checker = await svc.create(username="guard1", password="password123", role=CheckerRole.GUARD)
        updated = await svc.update(checker.id, is_active=False)
        assert updated is not None
        assert updated.is_active is False

    async def test_update_nonexistent(self, db_session: AsyncSession):
        svc = CheckerService(db_session)
        result = await svc.update(uuid.uuid4(), role=CheckerRole.MANAGER)
        assert result is None


class TestCheckerServiceAuthenticate:
    async def test_authenticate_success(self, db_session: AsyncSession):
        svc = CheckerService(db_session)
        await svc.create(username="guard1", password="password123", role=CheckerRole.GUARD)
        checker = await svc.authenticate(username="guard1", password="password123")
        assert checker is not None
        assert checker.username == "guard1"

    async def test_authenticate_wrong_password(self, db_session: AsyncSession):
        svc = CheckerService(db_session)
        await svc.create(username="guard1", password="password123", role=CheckerRole.GUARD)
        checker = await svc.authenticate(username="guard1", password="wrong")
        assert checker is None

    async def test_authenticate_nonexistent_user(self, db_session: AsyncSession):
        svc = CheckerService(db_session)
        checker = await svc.authenticate(username="nobody", password="password123")
        assert checker is None

    async def test_authenticate_deactivated_checker(self, db_session: AsyncSession):
        svc = CheckerService(db_session)
        checker = await svc.create(username="guard1", password="password123", role=CheckerRole.GUARD)
        await svc.update(checker.id, is_active=False)
        result = await svc.authenticate(username="guard1", password="password123")
        assert result is None