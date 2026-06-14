import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password
from app.models.models import Admin, AdminRole


class AdminService:
    """Service for managing admin accounts."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, username: str, password: str, role: AdminRole) -> Admin:
        existing = await self.db.execute(select(Admin).where(Admin.username == username))
        if existing.scalar_one_or_none() is not None:
            raise ValueError(f"Admin with username '{username}' already exists")

        admin = Admin(
            username=username,
            hashed_password=hash_password(password),
            role=role,
        )
        self.db.add(admin)
        await self.db.flush()
        return admin

    async def authenticate(self, username: str, password: str) -> Admin | None:
        result = await self.db.execute(select(Admin).where(Admin.username == username))
        admin = result.scalar_one_or_none()

        if admin is None:
            return None
        if not admin.is_active:
            return None
        if not verify_password(password, admin.hashed_password):
            return None

        return admin

    async def get(self, admin_id: uuid.UUID) -> Admin | None:
        return await self.db.get(Admin, admin_id)