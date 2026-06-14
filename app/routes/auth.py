from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import create_access_token
from app.models.models import AdminRole, CheckerRole
from app.schemas.schemas import AdminLogin, CheckerLogin, TokenResponse
from app.services.admin_service import AdminService
from app.services.checker_service import CheckerService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/admin/login", response_model=TokenResponse)
async def admin_login(body: AdminLogin, db: AsyncSession = Depends(get_db)):
    """Authenticate an admin and return a JWT."""
    svc = AdminService(db)
    admin = await svc.authenticate(username=body.username, password=body.password)
    if admin is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    token = create_access_token(
        data={"sub": str(admin.id), "role": admin.role.value, "type": "admin"}
    )
    return TokenResponse(access_token=token, role=admin.role.value)


@router.post("/checker/login", response_model=TokenResponse)
async def checker_login(body: CheckerLogin, db: AsyncSession = Depends(get_db)):
    """Authenticate a checker and return a JWT."""
    svc = CheckerService(db)
    checker = await svc.authenticate(username=body.username, password=body.password)
    if checker is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    token = create_access_token(
        data={"sub": str(checker.id), "role": checker.role.value, "type": "checker"}
    )
    return TokenResponse(access_token=token, role=checker.role.value)