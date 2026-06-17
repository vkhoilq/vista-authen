from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import require_admin_role
from app.models.models import Admin, AdminRole
from app.services.cleanup_service import CleanupService

router = APIRouter(prefix="/admin/cleanup", tags=["cleanup"])

@router.post("", status_code=status.HTTP_200_OK)
async def trigger_cleanup(
    db: AsyncSession = Depends(get_db),
    admin: Admin = Depends(require_admin_role(AdminRole.SETUP_ADMIN, AdminRole.STAFF_ADMIN)),
):
    """Manually trigger pruning of expired tokens and old audit logs.
    
    Setup Admin or Staff Admin only.
    """
    svc = CleanupService(db)
    results = await svc.cleanup_all()
    return {
        "status": "success",
        "detail": f"Purged {results['purged_tokens']} expired/used tokens and {results['purged_audit_logs']} old audit logs.",
        "results": results
    }
