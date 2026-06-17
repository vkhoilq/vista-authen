from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_checker
from app.core.limiter import limiter, get_checker_rate_limit_key
from app.models.models import Checker, CheckerRole
from app.schemas.schemas import AccessVerifyRequest, AccessVerifyResponseGuard, AccessVerifyResponseManager
from app.services.access_service import AccessService

router = APIRouter(prefix="/access", tags=["access"])


@router.post("/verify")
@limiter.limit("30/minute", key_func=get_checker_rate_limit_key)
async def verify_qr(
    request: Request,
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