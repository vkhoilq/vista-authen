import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ResidentStatus(str, enum.Enum):
    PENDING = "pending"
    ACTIVE = "active"
    REVOKED = "revoked"


class CheckerRole(str, enum.Enum):
    GUARD = "guard"
    MANAGER = "manager"


class AdminRole(str, enum.Enum):
    SETUP_ADMIN = "setup_admin"
    RESIDENT_ADMIN = "resident_admin"
    STAFF_ADMIN = "staff_admin"


class Unit(Base):
    __tablename__ = "units"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    unit_number: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    max_residents: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    residents: Mapped[list["Resident"]] = relationship(back_populates="unit", lazy="selectin")


class Resident(Base):
    __tablename__ = "residents"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    unit_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("units.id"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    public_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[ResidentStatus] = mapped_column(
        Enum(ResidentStatus), nullable=False, default=ResidentStatus.PENDING
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    unit: Mapped["Unit"] = relationship(back_populates="residents")
    activation_token: Mapped["ActivationToken | None"] = relationship(back_populates="resident", uselist=False)


class Checker(Base):
    __tablename__ = "checkers"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[CheckerRole] = mapped_column(Enum(CheckerRole), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Admin(Base):
    __tablename__ = "admins"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[AdminRole] = mapped_column(Enum(AdminRole), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    action: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    actor_role: Mapped[str | None] = mapped_column(String(50), nullable=True)
    unit_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("units.id"), nullable=True)
    checker_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("checkers.id"), nullable=True)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class ActivationToken(Base):
    __tablename__ = "activation_tokens"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    resident_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("residents.id"), unique=True, index=True, nullable=False
    )
    token: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    resident: Mapped["Resident"] = relationship(back_populates="activation_token")