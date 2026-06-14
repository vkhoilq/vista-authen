from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_checker
from app.models.models import Checker, CheckerRole
from app.schemas.schemas import AccessVerifyRequest, AccessVerifyResponseGuard, AccessVerifyResponseManager
from app.services.access_service import AccessService

router = APIRouter(prefix="/access", tags=["access"])


@router.post("/verify")
async def verify_qr(
    body: AccessVerifyRequest,
    checker: Checker = Depends(get_current_checker),
    db: AsyncSession = Depends(get_db),
):
    """Verify a QR code payload. Authenticated checkers only.

    Returns minimal response for guards, extended response for managers.
    """
    svc = AccessService(db)
    result = await svc.verify(qr_payload=body.qr_payload, checker_id=checker.id)

    if checker.role == CheckerRole.MANAGER:
        return AccessVerifyResponseManager(
            status=result["status"],
            resident_name=result.get("resident_name"),
            unit=result.get("unit"),
        )
    else:
        return AccessVerifyResponseGuard(status=result["status"])