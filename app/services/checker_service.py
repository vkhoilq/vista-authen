import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password
from app.models.models import Checker, CheckerRole


class CheckerService:
    """Service for managing checker (guard/manager) accounts."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, username: str, password: str, role: CheckerRole) -> Checker:
        # Check uniqueness
        existing = await self.db.execute(select(Checker).where(Checker.username == username))
        if existing.scalar_one_or_none() is not None:
            raise ValueError(f"Checker with username '{username}' already exists")

        checker = Checker(
            username=username,
            hashed_password=hash_password(password),
            role=role,
        )
        self.db.add(checker)
        await self.db.flush()
        return checker

    async def update(self, checker_id: uuid.UUID, role: CheckerRole | None = None, is_active: bool | None = None) -> Checker | None:
        checker = await self.db.get(Checker, checker_id)
        if checker is None:
            return None

        if role is not None:
            checker.role = role
        if is_active is not None:
            checker.is_active = is_active

        await self.db.flush()
        return checker

    async def authenticate(self, username: str, password: str) -> Checker | None:
        result = await self.db.execute(select(Checker).where(Checker.username == username))
        checker = result.scalar_one_or_none()

        if checker is None:
            return None
        if not checker.is_active:
            return None
        if not verify_password(password, checker.hashed_password):
            return None

        return checker

    async def get(self, checker_id: uuid.UUID) -> Checker | None:
        return await self.db.get(Checker, checker_id)

    async def list_all(self) -> list[Checker]:
        result = await self.db.execute(select(Checker).order_by(Checker.created_at))
        return list(result.scalars().all())