import itertools

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import src.auth.models  # noqa: F401 — register models with Base.metadata
import src.bags.models  # noqa: F401
import src.packing.models  # noqa: F401
import src.trips.models  # noqa: F401
from src.auth import service as auth_service
from src.auth.schemas import UserCreate
from src.database import Base, get_db
from src.main import app

# ── Shared in-memory SQLite engine ──────────────────────────────────────────
# StaticPool keeps all sessions on the same underlying connection so
# in-memory data is visible across sessions within the test run.
TEST_ENGINE = create_async_engine(
    "sqlite+aiosqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionFactory = async_sessionmaker(TEST_ENGINE, expire_on_commit=False)

_uid = itertools.count(1)


async def override_get_db():
    async with TestSessionFactory() as session:
        yield session


# ── Session-scoped setup ─────────────────────────────────────────────────────


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_database():
    """Create schema, seed default packing templates, wire dependency override."""
    async with TEST_ENGINE.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    app.dependency_overrides[get_db] = override_get_db

    async with TestSessionFactory() as db:
        from src.packing.seed import seed_default_templates

        await seed_default_templates(db)

    yield

    app.dependency_overrides.clear()
    await TEST_ENGINE.dispose()


@pytest.fixture(scope="session", autouse=True)
def patch_upload_dir(tmp_path_factory):
    """Redirect file uploads to a temp directory for the whole test session."""
    from src.config import settings

    upload_path = tmp_path_factory.mktemp("uploads")
    settings.UPLOAD_DIR = upload_path
    return upload_path


# ── Per-test fixtures ────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def db():
    async with TestSessionFactory() as session:
        yield session


@pytest_asyncio.fixture
async def user(db):
    """Fresh user for each test (unique username via counter)."""
    n = next(_uid)
    return await auth_service.create_user(
        db,
        UserCreate(username=f"user{n}", email=f"user{n}@test.com", password="Password123!"),
    )


@pytest_asyncio.fixture
async def auth_client(user):
    """Async HTTP client authenticated as `user` via JWT cookie."""
    token = auth_service.create_access_token(user.id)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ac.cookies.set("access_token", token)
        yield ac


@pytest_asyncio.fixture
async def anon_client():
    """Unauthenticated async HTTP client."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


# ── Tiny valid JPEG bytes ────────────────────────────────────────────────────
# Minimal 1×1 JFIF for image-upload tests — httpx sends it as multipart.
TINY_JPEG = (
    b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
    b"\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n"
    b"\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d"
    b"\x1a\x1c\x1c $.' \",#\x1c\x1c(7),01444\x1f'9=82<.342\x1eC\t\x0b\x0b"
    b'\x0c\x0b\x0c\x18\r\r\x18"(\x1c(""""""""""""""""""'
    b'"""""""""""""""""""""""""\xff\xc0\x00\x0b\x08'
    b"\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x1f\x00\x00\x01\x05\x01"
    b"\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04"
    b"\x05\x06\x07\x08\t\n\x0b\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xf5\x00"
    b"\xff\xd9"
)
