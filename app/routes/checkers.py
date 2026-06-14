import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import require_admin_role
from app.models.models import Admin, AdminRole
from app.schemas.schemas import CheckerCreate, CheckerRead, CheckerUpdate
from app.services.checker_service import CheckerService

router = APIRouter(prefix="/checkers", tags=["checkers"])


@router.post("", response_model=CheckerRead, status_code=status.HTTP_201_CREATED)
async def create_checker(
    body: CheckerCreate,
    db: AsyncSession = Depends(get_db),
    admin: Admin = Depends(require_admin_role(AdminRole.STAFF_ADMIN)),
):
    """Create a new checker account. Staff Admin only."""
    from app.models.models import CheckerRole

    svc = CheckerService(db)
    try:
        checker = await svc.create(
            username=body.username,
            password=body.password,
            role=CheckerRole(body.role.value) if isinstance(body.role, str) else body.role,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return CheckerRead(
        id=str(checker.id),
        username=checker.username,
        role=checker.role,
        is_active=checker.is_active,
        created_at=checker.created_at,
    )


@router.get("", response_model=list[CheckerRead])
async def list_checkers(
    db: AsyncSession = Depends(get_db),
    admin: Admin = Depends(require_admin_role(AdminRole.STAFF_ADMIN)),
):
    """List all checker accounts. Staff Admin only."""
    svc = CheckerService(db)
    checkers = await svc.list_all()
    return [
        CheckerRead(
            id=str(c.id),
            username=c.username,
            role=c.role,
            is_active=c.is_active,
            created_at=c.created_at,
        )
        for c in checkers
    ]


@router.patch("/{checker_id}", response_model=CheckerRead)
async def update_checker(
    checker_id: str,
    body: CheckerUpdate,
    db: AsyncSession = Depends(get_db),
    admin: Admin = Depends(require_admin_role(AdminRole.STAFF_ADMIN)),
):
    """Update a checker account (role, active status). Staff Admin only."""
    from app.models.models import CheckerRole

    svc = CheckerService(db)
    role = CheckerRole(body.role.value) if body.role is not None else None
    checker = await svc.update(
        checker_id=uuid.UUID(checker_id),
        role=role,
        is_active=body.is_active,
    )
    if checker is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Checker not found")

    return CheckerRead(
        id=str(checker.id),
        username=checker.username,
        role=checker.role,
        is_active=checker.is_active,
        created_at=checker.created_at,
    )