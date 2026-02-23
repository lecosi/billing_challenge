"""
conftest.py – Fixtures compartidos para toda la suite de tests.

Usamos SQLite en memoria para no depender de PostgreSQL.

CLAVE: usamos StaticPool para que TODAS las conexiones SQLAlchemy
compartan la misma base de datos en memoria. Sin esto, create_all
crea las tablas en la conexión A pero el test usa la conexión B
(vacía) → "no such table".
"""
import os
# Must be set BEFORE any app module is imported so database.py picks up
# SQLite instead of the Postgres URL from .env.
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.infrastructure.database import Base, get_db
from app.main import app
from fastapi.testclient import TestClient
import app.infrastructure.database as db_module

SQLALCHEMY_TEST_URL = "sqlite:///:memory:"

test_engine = create_engine(
    SQLALCHEMY_TEST_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

db_module.engine = test_engine
db_module.SessionLocal = TestingSessionLocal

# ---------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------

@pytest.fixture(autouse=True)
def setup_database():
    """Crea tablas antes de cada test y las destruye al terminar."""
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(autouse=True)
def mock_redis():
    """Patches the Redis client for ALL tests so no live Redis is needed.

    The mock simulates the INCR counter behaviour so rate-limit tests
    can exercise the 429 path by controlling the return value directly.
    """
    mock = MagicMock()
    mock.incr.return_value = 1   # default: first request in the window
    mock.expire.return_value = True
    with patch("app.api.auth.redis_client", mock):
        yield mock


@pytest.fixture
def db_session(setup_database):
    """Sesión directa a SQLite para tests de use_cases/repositorios."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client(setup_database):
    """TestClient con override de get_db apuntando a SQLite.

    base_url is set so that Starlette populates request.client with a
    loopback address — without it request.client is None and the
    rate_limiter crashes with AttributeError: 'NoneType'.host.
    """
    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, base_url="http://testclient") as c:
        yield c
    app.dependency_overrides.clear()


# ---------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------

@pytest.fixture
def headers():
    return {"X-API-Key": "api-key-secret"}


@pytest.fixture
def valid_doc_payload():
    return {
        "invoice_type": "invoice",
        "amount": 1500.50,
        "metadata": {"client": "Test Client"},
    }
