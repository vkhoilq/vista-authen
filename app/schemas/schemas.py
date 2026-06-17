from datetime import datetime

from pydantic import BaseModel, Field, field_validator
from cryptography.hazmat.primitives import serialization

from app.models.models import AdminRole, CheckerRole, ResidentStatus


# ============================================================
# Unit
# ============================================================

class UnitCreate(BaseModel):
    unit_number: str = Field(..., min_length=1, max_length=50)
    max_residents: int = Field(..., ge=1)


class UnitUpdate(BaseModel):
    max_residents: int = Field(..., ge=1)


class UnitRead(BaseModel):
    id: str
    unit_number: str
    max_residents: int
    current_resident_count: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ============================================================
# Resident
# ============================================================

class ResidentCreate(BaseModel):
    unit_id: str
    name: str = Field(..., min_length=1, max_length=255)
    phone: str | None = Field(None, max_length=50)
    email: str | None = Field(None, max_length=255)


class ResidentRead(BaseModel):
    id: str
    unit_id: str
    name: str
    status: ResidentStatus
    has_public_key: bool
    is_owner: bool
    phone: str | None = None
    email: str | None = None
    created_at: datetime
    revoked_at: datetime | None = None

    model_config = {"from_attributes": True}


class ResidentUpdateContact(BaseModel):
    phone: str | None = Field(None, max_length=50)
    email: str | None = Field(None, max_length=255)


class ResidentRegisterRequest(BaseModel):
    activation_token: str
    public_key_pem: str = Field(..., min_length=1, max_length=10240)

    @field_validator("public_key_pem")
    @classmethod
    def validate_public_key(cls, v: str) -> str:
        try:
            serialization.load_pem_public_key(v.encode("utf-8"))
        except Exception as e:
            raise ValueError(f"Invalid PEM public key: {str(e)}")
        return v


# ============================================================
# Checker
# ============================================================

class CheckerCreate(BaseModel):
    username: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=8)
    role: CheckerRole


class CheckerUpdate(BaseModel):
    role: CheckerRole | None = None
    is_active: bool | None = None


class CheckerRead(BaseModel):
    id: str
    username: str
    role: CheckerRole
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class CheckerLogin(BaseModel):
    username: str
    password: str


# ============================================================
# Admin
# ============================================================

class AdminCreate(BaseModel):
    username: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=8)
    role: AdminRole


class AdminRead(BaseModel):
    id: str
    username: str
    role: AdminRole
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class AdminLogin(BaseModel):
    username: str
    password: str


# ============================================================
# Access / Verify
# ============================================================

class AccessVerifyRequest(BaseModel):
    qr_payload: str = Field(..., min_length=1, max_length=10240)


class AccessVerifyResponseGuard(BaseModel):
    status: str  # "valid" | "invalid" | "expired"


class AccessVerifyResponseManager(BaseModel):
    status: str  # "valid" | "invalid" | "expired"
    resident_name: str | None = None
    unit: str | None = None
    phone: str | None = None


# ============================================================
# Audit
# ============================================================

class AuditLogRead(BaseModel):
    id: str
    timestamp: datetime
    action: str
    actor_id: str | None = None
    actor_role: str | None = None
    unit_id: str | None = None
    details: dict | None = None

    model_config = {"from_attributes": True}


class AuditLogFilter(BaseModel):
    action: str | None = None
    unit_id: str | None = None
    actor_role: str | None = None
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)


# ============================================================
# Auth
# ============================================================

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str