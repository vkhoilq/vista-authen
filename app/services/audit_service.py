import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import AuditLog


class AuditService:
    """Service for writing and querying audit logs."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def log(
        self,
        action: str,
        actor_id: uuid.UUID | None = None,
        actor_role: str | None = None,
        unit_id: uuid.UUID | None = None,
        checker_id: uuid.UUID | None = None,
        details: dict | None = None,
    ) -> AuditLog:
        """Insert an audit log entry."""
        log = AuditLog(
            action=action,
            actor_id=actor_id,
            actor_role=actor_role,
            unit_id=unit_id,
            checker_id=checker_id,
            details=details,
        )
        self.db.add(log)
        await self.db.flush()
        return log

    async def list_logs(
        self,
        action: str | None = None,
        unit_id: uuid.UUID | None = None,
        actor_role: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[AuditLog], int]:
        """Query audit logs with pagination and filtering."""
        query = select(AuditLog)
        count_query = select(AuditLog)

        if action:
            query = query.where(AuditLog.action == action)
            count_query = count_query.where(AuditLog.action == action)
        if unit_id:
            query = query.where(AuditLog.unit_id == unit_id)
            count_query = count_query.where(AuditLog.unit_id == unit_id)
        if actor_role:
            query = query.where(AuditLog.actor_role == actor_role)
            count_query = count_query.where(AuditLog.actor_role == actor_role)

        # Get total count
        from sqlalchemy import func

        total_result = await self.db.execute(select(func.count()).select_from(count_query.subquery()))
        total = total_result.scalar_one()

        # Get paginated results
        result = await self.db.execute(
            query.order_by(AuditLog.timestamp.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        logs = list(result.scalars().all())

        return logs, total