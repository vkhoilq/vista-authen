import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import require_admin_role
from app.models.models import Admin, AdminRole
from app.schemas.schemas import ResidentCreate, ResidentRead, ResidentRegisterRequest, ResidentUpdateContact
from app.services.resident_service import ResidentService

router = APIRouter(prefix="/residents", tags=["residents"])


def _map_resident(r) -> ResidentRead:
    """Helper to convert Resident DB model to ResidentRead Pydantic model."""
    return ResidentRead(
        id=str(r.id),
        unit_id=str(r.unit_id),
        name=r.name,
        status=r.status,
        has_public_key=r.public_key is not None,
        is_owner=r.is_owner,
        phone=r.phone,
        email=r.email,
        created_at=r.created_at,
        revoked_at=r.revoked_at,
    )


@router.post("", status_code=status.HTTP_201_CREATED)
async def provision_resident(
    body: ResidentCreate,
    db: AsyncSession = Depends(get_db),
    admin: Admin = Depends(require_admin_role(AdminRole.RESIDENT_ADMIN)),
):
    """Provision a new resident. Resident Admin only. Enforces unit capacity."""
    svc = ResidentService(db)
    try:
        result = await svc.provision(
            unit_id=uuid.UUID(body.unit_id),
            name=body.name,
            phone=body.phone,
            email=body.email,
            actor_id=admin.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    resident = result["resident"]
    token = result["activation_token"]

    return {
        "resident": _map_resident(resident),
        "activation_token": token.token,
        "expires_at": token.expires_at.isoformat(),
    }


@router.post("/register")
async def register_device(body: ResidentRegisterRequest, db: AsyncSession = Depends(get_db)):
    """Register a device public key. Self-service — no auth required (uses activation token)."""
    svc = ResidentService(db)
    try:
        resident = await svc.register_device(
            activation_token=body.activation_token,
            public_key_pem=body.public_key_pem,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return _map_resident(resident)


@router.patch("/{resident_id}/revoke", response_model=ResidentRead)
async def revoke_resident(
    resident_id: str,
    db: AsyncSession = Depends(get_db),
    admin: Admin = Depends(require_admin_role(AdminRole.RESIDENT_ADMIN)),
):
    """Revoke a resident's access. Resident Admin only."""
    svc = ResidentService(db)
    resident = await svc.revoke(uuid.UUID(resident_id), actor_id=admin.id)
    if resident is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resident not found")

    return _map_resident(resident)


@router.patch("/{resident_id}/contact", response_model=ResidentRead)
async def update_resident_contact(
    resident_id: str,
    body: ResidentUpdateContact,
    db: AsyncSession = Depends(get_db),
    admin: Admin = Depends(require_admin_role(AdminRole.RESIDENT_ADMIN)),
):
    """Update contact info of a resident (Owner only). Resident Admin only."""
    svc = ResidentService(db)
    try:
        resident = await svc.update_contact(
            resident_id=uuid.UUID(resident_id),
            phone=body.phone,
            email=body.email,
            actor_id=admin.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    if resident is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resident not found")

    return _map_resident(resident)


@router.get("/{resident_id}", response_model=ResidentRead)
async def get_resident(
    resident_id: str,
    db: AsyncSession = Depends(get_db),
    admin: Admin = Depends(require_admin_role(AdminRole.RESIDENT_ADMIN)),
):
    """Get resident details. Resident Admin only."""
    svc = ResidentService(db)
    resident = await svc.get(uuid.UUID(resident_id))
    if resident is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resident not found")

    return _map_resident(resident)


@router.get("/by-unit/{unit_id}", response_model=list[ResidentRead])
async def list_residents_by_unit(
    unit_id: str,
    db: AsyncSession = Depends(get_db),
    admin: Admin = Depends(require_admin_role(AdminRole.RESIDENT_ADMIN)),
):
    """List all residents in a unit. Resident Admin only."""
    svc = ResidentService(db)
    residents = await svc.list_by_unit(uuid.UUID(unit_id))
    return [_map_resident(r) for r in residents]