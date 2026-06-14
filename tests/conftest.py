import asyncio
import uuid
from collections.abc import AsyncGenerator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base
from app.models.models import (
    ActivationToken,
    Admin,
    AdminRole,
    Checker,
    CheckerRole,
    Resident,
    ResidentStatus,
    Unit,
)


# Use SQLite for tests (in-memory)
TEST_DATABASE_URL = "sqlite+aiosqlite:///test.db"

engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
async def setup_database():
    """Create tables before each test and drop them after."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a clean database session for each test."""
    async with TestSessionLocal() as session:
        yield session
        await session.rollback()


# ============================================================
# Helper fixtures for creating test entities
# ============================================================


@pytest.fixture
async def sample_unit(db_session: AsyncSession) -> Unit:
    """Create a sample unit with max_residents=2."""
    unit = Unit(unit_number="A-101", max_residents=2)
    db_session.add(unit)
    await db_session.flush()
    await db_session.refresh(unit)
    return unit


@pytest.fixture
async def sample_resident(db_session: AsyncSession, sample_unit: Unit) -> Resident:
    """Create a sample pending resident."""
    resident = Resident(unit_id=sample_unit.id, name="Nguyen Van A", status=ResidentStatus.PENDING)
    db_session.add(resident)
    await db_session.flush()
    await db_session.refresh(resident)
    return resident


@pytest.fixture
async def active_resident(
    db_session: AsyncSession, sample_unit: Unit
) -> tuple[Resident, str]:
    """Create an active resident with a real ECC P-256 public key. Returns (resident, public_key_pem)."""
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.primitives import hashes, serialization

    private_key = ec.generate_private_key(ec.SECP256R1())
    public_key = private_key.public_key()
    public_key_pem = public_key.public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()

    resident = Resident(
        unit_id=sample_unit.id,
        name="Active Resident",
        status=ResidentStatus.ACTIVE,
        public_key=public_key_pem,
    )
    db_session.add(resident)
    await db_session.flush()
    await db_session.refresh(resident)
    return resident, public_key_pem


@pytest.fixture
async def sample_checker(db_session: AsyncSession) -> Checker:
    """Create a sample guard checker."""
    from app.core.security import hash_password

    checker = Checker(
        username="guard1",
        hashed_password=hash_password("password123"),
        role=CheckerRole.GUARD,
        is_active=True,
    )
    db_session.add(checker)
    await db_session.flush()
    await db_session.refresh(checker)
    return checker


@pytest.fixture
async def sample_manager(db_session: AsyncSession) -> Checker:
    """Create a sample manager checker."""
    from app.core.security import hash_password

    checker = Checker(
        username="manager1",
        hashed_password=hash_password("password123"),
        role=CheckerRole.MANAGER,
        is_active=True,
    )
    db_session.add(checker)
    await db_session.flush()
    await db_session.refresh(checker)
    return checker


@pytest.fixture
async def sample_admin(db_session: AsyncSession) -> Admin:
    """Create a sample resident_admin."""
    from app.core.security import hash_password

    admin = Admin(
        username="admin1",
        hashed_password=hash_password("admin123"),
        role=AdminRole.RESIDENT_ADMIN,
        is_active=True,
    )
    db_session.add(admin)
    await db_session.flush()
    await db_session.refresh(admin)
    return admin