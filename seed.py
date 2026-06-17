import asyncio
import uuid
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.core.database import Base
from app.models.models import Admin, AdminRole, Checker, CheckerRole, Unit, Resident, ActivationToken, ResidentStatus
from app.core.security import hash_password
from app.core.config import settings

DATABASE_URL = "sqlite+aiosqlite:///dev.db"

async def main():
    engine = create_async_engine(DATABASE_URL, echo=True)
    async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    print("Recreating database tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    
    print("Seeding database...")
    async with async_session_factory() as session:
        # Create Setup Admin
        setup_admin = Admin(
            username="setup_admin",
            hashed_password=hash_password("admin1234"),
            role=AdminRole.SETUP_ADMIN,
            is_active=True,
        )
        # Create Resident Admin
        resident_admin = Admin(
            username="resident_admin",
            hashed_password=hash_password("admin1234"),
            role=AdminRole.RESIDENT_ADMIN,
            is_active=True,
        )
        # Create Staff Admin
        staff_admin = Admin(
            username="staff_admin",
            hashed_password=hash_password("admin1234"),
            role=AdminRole.STAFF_ADMIN,
            is_active=True,
        )
        # Create Guard
        guard = Checker(
            username="guard1",
            hashed_password=hash_password("checker1234"),
            role=CheckerRole.GUARD,
            is_active=True,
        )
        # Create Manager
        manager = Checker(
            username="manager1",
            hashed_password=hash_password("checker1234"),
            role=CheckerRole.MANAGER,
            is_active=True,
        )
        
        # Create Pre-configured Unit T13402
        unit_id = uuid.UUID("6bb9d19b-9339-427f-904a-bf8961cee5fc")
        unit = Unit(
            id=unit_id,
            unit_number="T13402",
            max_residents=3
        )
        
        # Create Resident 1 (Owner)
        res1 = Resident(
            id=uuid.UUID("6e272574-18dc-474c-84b6-320e5882eef9"),
            unit_id=unit_id,
            name="Test Resident 1",
            status=ResidentStatus.PENDING,
            is_owner=True,
            phone="+1234567890",
            email=f"owner@{settings.DOMAIN_NAME}"
        )
        token1 = ActivationToken(
            resident_id=res1.id,
            token="283b63e3caa44aa197e0ec0f370c6b3b",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24)
        )
        
        # Create Resident 2 (Regular Resident)
        res2 = Resident(
            id=uuid.UUID("e3f5b726-1bda-45cc-8199-5efde0a1d6bc"),
            unit_id=unit_id,
            name="Test Resident 2",
            status=ResidentStatus.PENDING,
            is_owner=False
        )
        token2 = ActivationToken(
            resident_id=res2.id,
            token="2463071114f246be9eb30b7145206b74",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24)
        )
        
        # Create Resident 3 (Regular Resident)
        res3 = Resident(
            id=uuid.UUID("02ac16e3-2bd1-4d1a-9694-817abdc381c8"),
            unit_id=unit_id,
            name="Test Resident 3",
            status=ResidentStatus.PENDING,
            is_owner=False
        )
        token3 = ActivationToken(
            resident_id=res3.id,
            token="f54a7fa85ae649eebfd80a5802b3ff07",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24)
        )
        
        session.add_all([
            setup_admin, resident_admin, staff_admin, guard, manager,
            unit, res1, token1, res2, token2, res3, token3
        ])
        await session.commit()
        
    print("Seeding completed successfully!")
    print("\nAdmins:")
    print("  - Setup Admin: setup_admin / admin1234")
    print("  - Resident Admin: resident_admin / admin1234")
    print("  - Staff Admin: staff_admin / admin1234")
    print("\nCheckers:")
    print("  - Guard: guard1 / checker1234")
    print("  - Manager: manager1 / checker1234")
    print("\nPre-configured unit T13402 & residents:")
    print("  - Test Resident 1 (Owner): token '283b63e3caa44aa197e0ec0f370c6b3b' (Phone: +1234567890)")
    print("  - Test Resident 2: token '2463071114f246be9eb30b7145206b74'")
    print("  - Test Resident 3: token 'f54a7fa85ae649eebfd80a5802b3ff07'")

if __name__ == "__main__":
    asyncio.run(main())
