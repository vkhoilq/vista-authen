import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import require_admin_role, require_checker_role
from app.models.models import Admin, AdminRole, Checker, CheckerRole
from app.schemas.schemas import AuditLogRead
from app.services.audit_service import AuditService

router = APIRouter(prefix="/audit-logs", tags=["audit-logs"])


@router.get("", response_model=list[AuditLogRead])
async def list_audit_logs(
    action: str | None = Query(None),
    unit_id: str | None = Query(None),
    actor_role: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    # Staff Admin or Manager can view audit logs
    _admin: Admin = Depends(require_admin_role(AdminRole.STAFF_ADMIN)),
):
    """List audit logs with pagination and filtering. Staff Admin only."""
    svc = AuditService(db)

    unit_uuid = uuid.UUID(unit_id) if unit_id else None

    logs, total = await svc.list_logs(
        action=action,
        unit_id=unit_uuid,
        actor_role=actor_role,
        page=page,
        page_size=page_size,
    )

    return [
        AuditLogRead(
            id=str(log.id),
            timestamp=log.timestamp,
            action=log.action,
            actor_id=str(log.actor_id) if log.actor_id else None,
            actor_role=log.actor_role,
            unit_id=str(log.unit_id) if log.unit_id else None,
            details=log.details,
        )
        for log in logs
    ]