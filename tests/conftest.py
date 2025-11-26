"""Pytest configuration and fixtures."""

import asyncio
from collections.abc import AsyncGenerator, Generator

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from src.my_awesome_api.core.database import get_db
from src.my_awesome_api.main import app
from src.my_awesome_api.models.base import Base

# Test database URL
# Use an in-memory SQLite database for testing
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# Create test engine
# The connect_args is specific to SQLite
engine = create_async_engine(
    TEST_DATABASE_URL, echo=False, connect_args={"check_same_thread": False}
)
TestSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create a new database session for a test."""
    async with engine.connect() as connection:
        await connection.run_sync(Base.metadata.create_all)

        session_maker = sessionmaker(bind=connection, class_=AsyncSession, expire_on_commit=False)
        session = session_maker()

        yield session

        await session.close()
        await connection.run_sync(Base.metadata.drop_all)


@pytest.fixture(scope="function")
def override_get_db(db_session: AsyncSession) -> None:
    """Override the get_db dependency."""

    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db


@pytest.fixture(scope="function")
def client(override_get_db) -> TestClient:
    """Create a test client."""
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="function")
async def async_client(override_get_db) -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac