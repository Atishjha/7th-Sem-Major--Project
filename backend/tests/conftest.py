"""
Shared pytest fixtures for the AI Cyber Defense Command Center backend.

WHY A REAL POSTGRES TEST DATABASE (not SQLite)
----------------------------------------------
app/utils/ids.py allocates human-readable ids (EVT-000123, ALT-..., INC-1001,
RESP-...) with `SELECT nextval('<table>_id_seq')`. That is PostgreSQL-only, so
the suite runs against a throw-away Postgres database. Locally that is the
`postgres` service from docker-compose; create the test DB once with:

    docker compose up -d postgres
    docker compose exec postgres psql -U socuser -d soc_db -c "CREATE DATABASE soc_test;"

Override the target with TEST_DATABASE_URL if yours differs.

SAFETY GUARD
------------
The suite TRUNCATEs every table between tests. To make it impossible to wipe
your real data by accident, it refuses to run unless the database name ends
in "_test".
"""

import os
from functools import lru_cache

# --- must happen BEFORE any `app` import: app.database.session builds its engine
# --- from settings.DATABASE_URL at import time.
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg2://socuser:socpassword@localhost:5432/soc_test",
)
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["AI_PROVIDER"] = "mock"      # tests never call an external LLM
os.environ["AI_API_KEY"] = ""
os.environ["JWT_SECRET_KEY"] = "test-secret-not-for-production"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.engine import make_url  # noqa: E402

_db_name = make_url(TEST_DATABASE_URL).database or ""
if not _db_name.endswith("_test"):
    pytest.exit(
        f"Refusing to run: test database name must end in '_test' (got '{_db_name}'). "
        "The suite truncates all tables.",
        returncode=2,
    )

import app.models  # noqa: E402,F401  (registers every table on Base.metadata)
from app.database.base import Base  # noqa: E402
from app.database.session import SessionLocal, engine  # noqa: E402
from app.detectors.engine import ensure_default_rules  # noqa: E402
from app.main import app  # noqa: E402
from app.models.user import User, UserRole  # noqa: E402
from app.security.hashing import hash_password  # noqa: E402
from app.security.jwt import create_access_token  # noqa: E402
from app.services.risk_engine import ensure_default_assets  # noqa: E402


# ----------------------------------------------------------------- database
@pytest.fixture(scope="session", autouse=True)
def _schema():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture(autouse=True)
def _clean_db(_schema):
    """Empty every table (and restart every id sequence) after each test."""
    yield
    tables = ", ".join(f'"{t.name}"' for t in Base.metadata.sorted_tables)
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))


@pytest.fixture()
def db():
    """A session on the test DB, pre-loaded with the default detection rules
    and assets (what the app's lifespan hook does at startup)."""
    session = SessionLocal()
    try:
        ensure_default_rules(session)
        ensure_default_assets(session)
        yield session
    finally:
        session.close()


# -------------------------------------------------------------------- users
@lru_cache(maxsize=None)
def _hash(password: str) -> str:
    # bcrypt is deliberately slow; hash each demo password once per run.
    return hash_password(password)


DEMO_USERS = {
    "admin": ("admin123", UserRole.ADMIN),
    "analyst": ("analyst123", UserRole.SOC_ANALYST),
    "viewer": ("viewer123", UserRole.VIEWER),
}


@pytest.fixture()
def users(db):
    created = {}
    for username, (password, role) in DEMO_USERS.items():
        user = User(username=username, hashed_password=_hash(password), role=role, is_active=True)
        db.add(user)
        created[username] = user
    db.commit()
    return created


@pytest.fixture()
def headers(users):
    """headers['admin'] / ['analyst'] / ['viewer'] -> Authorization header.
    Tokens are minted directly (login is covered separately in test_auth.py)."""
    return {
        name: {"Authorization": "Bearer " + create_access_token(username=name, role=role.value)}
        for name, (_pw, role) in DEMO_USERS.items()
    }


@pytest.fixture()
def client(db):
    # `with` runs the app's lifespan hook (default rules/assets, backfills).
    with TestClient(app) as c:
        yield c


# ----------------------------------------------------- filesystem isolation
@pytest.fixture()
def ml_sandbox(tmp_path, monkeypatch):
    """Point every data/ml path used by training + dataset code at tmp_path,
    so tests never write into the real data/ or ml/models/ folders."""
    import app.ml.dataset as dataset_mod
    import app.ml.train as train_mod

    raw, processed, models = (tmp_path / "data" / "raw", tmp_path / "data" / "processed", tmp_path / "ml" / "models")
    for p in (raw, processed, models):
        p.mkdir(parents=True)

    monkeypatch.setattr(dataset_mod, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(dataset_mod, "RAW_DIR", raw)
    monkeypatch.setattr(dataset_mod, "PROCESSED_DIR", processed)
    monkeypatch.setattr(dataset_mod, "MODEL_DIR", models)
    monkeypatch.setattr(train_mod, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(train_mod, "MODEL_DIR", models)
    return tmp_path
