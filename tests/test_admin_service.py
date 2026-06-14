import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import AdminRole
from app.services.admin_service import AdminService


class TestAdminServiceCreate:
    async def test_create_admin(self, db_session: AsyncSession):
        svc = AdminService(db_session)
        admin = await svc.create(username="admin1", password="admin123", role=AdminRole.RESIDENT_ADMIN)
        assert admin.username == "admin1"
        assert admin.role == AdminRole.RESIDENT_ADMIN
        assert admin.is_active is True

    async def test_create_setup_admin(self, db_session: AsyncSession):
        svc = AdminService(db_session)
        admin = await svc.create(username="setup1", password="setup123", role=AdminRole.SETUP_ADMIN)
        assert admin.role == AdminRole.SETUP_ADMIN

    async def test_create_duplicate_username(self, db_session: AsyncSession):
        svc = AdminService(db_session)
        await svc.create(username="admin1", password="admin123", role=AdminRole.STAFF_ADMIN)
        with pytest.raises(ValueError, match="already exists"):
            await svc.create(username="admin1", password="different", role=AdminRole.STAFF_ADMIN)


class TestAdminServiceAuthenticate:
    async def test_authenticate_success(self, db_session: AsyncSession):
        svc = AdminService(db_session)
        await svc.create(username="admin1", password="admin123", role=AdminRole.RESIDENT_ADMIN)
        admin = await svc.authenticate(username="admin1", password="admin123")
        assert admin is not None
        assert admin.username == "admin1"

    async def test_authenticate_wrong_password(self, db_session: AsyncSession):
        svc = AdminService(db_session)
        await svc.create(username="admin1", password="admin123", role=AdminRole.RESIDENT_ADMIN)
        admin = await svc.authenticate(username="admin1", password="wrong")
        assert admin is None

    async def test_authenticate_nonexistent(self, db_session: AsyncSession):
        svc = AdminService(db_session)
        admin = await svc.authenticate(username="nobody", password="test")
        assert admin is None

    async def test_authenticate_deactivated_admin(self, db_session: AsyncSession):
        svc = AdminService(db_session)
        admin = await svc.create(username="admin1", password="admin123", role=AdminRole.RESIDENT_ADMIN)
        admin.is_active = False
        await db_session.flush()
        result = await svc.authenticate(username="admin1", password="admin123")
        assert result is None