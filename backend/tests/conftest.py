"""
conftest.py – Fixtures compartidos para toda la suite de tests.

Usamos SQLite en memoria para no depender de PostgreSQL.

CLAVE: usamos StaticPool para que TODAS las conexiones SQLAlchemy
compartan la misma base de datos en memoria. Sin esto, create_all
crea las tablas en la conexión A pero el test usa la conexión B
(vacía) → "no such table".
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool  # ← la corrección clave

SQLALCHEMY_TEST_URL = "sqlite:///:memory:"

# StaticPool garantiza que todas las checkins/checkouts del pool
# devuelvan LA MISMA conexión subyacente → misma DB en memoria.
test_engine = create_engine(
    SQLALCHEMY_TEST_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

# ---------------------------------------------------------------
# Monkey-patch ANTES de importar app para que main.py use SQLite
# ---------------------------------------------------------------
import app.infrastructure.database as db_module
db_module.engine = test_engine
db_module.SessionLocal = TestingSessionLocal

from app.infrastructure.database import Base, get_db
from app.main import app
from fastapi.testclient import TestClient


# ---------------------------------------------------------------
# Fixtures de ciclo de vida
# ---------------------------------------------------------------

@pytest.fixture(autouse=True)
def setup_database():
    """Crea tablas antes de cada test y las destruye al terminar."""
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


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
    """TestClient con override de get_db apuntando a SQLite."""
    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ---------------------------------------------------------------
# Fixtures de datos compartidos
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
