import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import require_admin_role
from app.models.models import Admin, AdminRole
from app.schemas.schemas import UnitCreate, UnitRead, UnitUpdate
from app.services.unit_service import UnitService

router = APIRouter(prefix="/units", tags=["units"])


@router.post("", response_model=UnitRead, status_code=status.HTTP_201_CREATED)
async def create_unit(
    body: UnitCreate,
    db: AsyncSession = Depends(get_db),
    admin: Admin = Depends(require_admin_role(AdminRole.SETUP_ADMIN)),
):
    """Create a new unit. Setup Admin only."""
    svc = UnitService(db)
    unit = await svc.create(unit_number=body.unit_number, max_residents=body.max_residents)
    await db.flush()

    # Compute current resident count (0 for new unit)
    return UnitRead(
        id=str(unit.id),
        unit_number=unit.unit_number,
        max_residents=unit.max_residents,
        current_resident_count=0,
        created_at=unit.created_at,
        updated_at=unit.updated_at,
    )


@router.get("", response_model=list[UnitRead])
async def list_units(
    db: AsyncSession = Depends(get_db),
    admin: Admin = Depends(require_admin_role(AdminRole.SETUP_ADMIN, AdminRole.RESIDENT_ADMIN)),
):
    """List all units. Setup Admin and Resident Admin."""
    svc = UnitService(db)
    units = await svc.list_all()
    return [
        UnitRead(
            id=str(u.id),
            unit_number=u.unit_number,
            max_residents=u.max_residents,
            current_resident_count=len(u.residents) if u.residents else 0,
            created_at=u.created_at,
            updated_at=u.updated_at,
        )
        for u in units
    ]


@router.get("/{unit_id}", response_model=UnitRead)
async def get_unit(
    unit_id: str,
    db: AsyncSession = Depends(get_db),
    admin: Admin = Depends(require_admin_role(AdminRole.SETUP_ADMIN, AdminRole.RESIDENT_ADMIN)),
):
    """Get a unit by ID. Setup Admin and Resident Admin."""
    svc = UnitService(db)
    unit = await svc.get(uuid.UUID(unit_id))
    if unit is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unit not found")
    return UnitRead(
        id=str(unit.id),
        unit_number=unit.unit_number,
        max_residents=unit.max_residents,
        current_resident_count=len(unit.residents) if unit.residents else 0,
        created_at=unit.created_at,
        updated_at=unit.updated_at,
    )


@router.patch("/{unit_id}", response_model=UnitRead)
async def update_unit_capacity(
    unit_id: str,
    body: UnitUpdate,
    db: AsyncSession = Depends(get_db),
    admin: Admin = Depends(require_admin_role(AdminRole.SETUP_ADMIN)),
):
    """Update unit capacity. Setup Admin only."""
    svc = UnitService(db)
    try:
        unit = await svc.update_capacity(uuid.UUID(unit_id), max_residents=body.max_residents)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    if unit is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unit not found")

    return UnitRead(
        id=str(unit.id),
        unit_number=unit.unit_number,
        max_residents=unit.max_residents,
        current_resident_count=len(unit.residents) if unit.residents else 0,
        created_at=unit.created_at,
        updated_at=unit.updated_at,
    )


@router.delete("/{unit_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_unit(
    unit_id: str,
    db: AsyncSession = Depends(get_db),
    admin: Admin = Depends(require_admin_role(AdminRole.SETUP_ADMIN)),
):
    """Delete a unit. Setup Admin only. Blocked if residents exist."""
    svc = UnitService(db)
    try:
        result = await svc.delete(uuid.UUID(unit_id))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unit not found")