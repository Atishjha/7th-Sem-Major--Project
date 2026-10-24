"""
First-run bootstrap and migrations (Phase 16).

These tests rebuild the schema from scratch several times, so each one gets a
blank database and the normal create_all schema is restored afterwards.
"""

import logging

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect, text

import app.bootstrap as bootstrap
from app.bootstrap import (
    DEMO_ACCOUNTS, alembic_config, migrate, seed_demo_users, wait_for_database, warn_about_insecure_defaults,
)
from app.config import settings
from app.database.base import Base
from app.database.session import SessionLocal, engine
from app.models.user import User, UserRole
from app.security.hashing import verify_password

ENUM_TYPES = ("actionstatus", "actiontype", "severity", "userrole")


def _wipe():
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS alembic_version"))
    Base.metadata.drop_all(engine)


def _current_revision():
    with engine.connect() as conn:
        return MigrationContext.configure(conn).get_current_revision()


def _head():
    return ScriptDirectory.from_config(alembic_config()).get_current_head()


@pytest.fixture()
def blank_db():
    """An empty database; the standard schema is put back afterwards."""
    _wipe()
    yield
    _wipe()
    Base.metadata.create_all(engine)


# ----------------------------------------------------------------- migrations
def test_there_is_exactly_one_migration_head():
    """Two heads (a branched history) would make `alembic upgrade head` fail."""
    assert len(ScriptDirectory.from_config(alembic_config()).get_heads()) == 1


def test_fresh_install_builds_the_whole_schema(blank_db):
    assert inspect(engine).get_table_names() == []
    assert migrate(engine) == "upgraded"
    tables = set(inspect(engine).get_table_names())
    assert tables == set(Base.metadata.tables) | {"alembic_version"}
    assert _current_revision() == _head()


def test_migration_and_models_have_not_drifted_apart(blank_db):
    """If someone edits a model without adding a migration, a fresh Docker
    install would get a different schema than the tests run against. This
    fails the moment that happens."""
    migrate(engine)
    with engine.connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn), Base.metadata)
    assert diff == [], f"models differ from migrations - run `alembic revision --autogenerate`: {diff}"


def test_running_twice_is_a_no_op(blank_db):
    migrate(engine)
    assert migrate(engine) == "up_to_date"


def test_downgrade_then_upgrade_round_trips_cleanly(blank_db):
    cfg = alembic_config()
    migrate(engine)
    command.downgrade(cfg, "base")
    assert set(inspect(engine).get_table_names()) <= {"alembic_version"}
    with engine.connect() as conn:
        leftover = conn.execute(
            text("SELECT typname FROM pg_type WHERE typname = ANY(:names)"), {"names": list(ENUM_TYPES)}
        ).scalars().all()
    assert leftover == [], "downgrade left PostgreSQL enum types behind"
    command.upgrade(cfg, "head")                                   # would fail on a leftover type
    assert set(inspect(engine).get_table_names()) == set(Base.metadata.tables) | {"alembic_version"}


def test_baseline_creates_the_id_sequences_the_app_relies_on(blank_db):
    """app/utils/ids.py allocates ids with nextval('<table>_id_seq')."""
    migrate(engine)
    with engine.connect() as conn:
        for table in ("events", "alerts", "incidents", "response_actions"):
            assert conn.execute(text(f"SELECT nextval('{table}_id_seq')")).scalar() == 1


# ------------------------------------------------------ adopting existing DBs
def test_existing_database_is_adopted_without_touching_its_data(blank_db):
    Base.metadata.create_all(engine)                      # what a pre-Phase-16 install looks like
    with SessionLocal() as db:
        db.add(User(username="pre_existing", hashed_password="keep-me", role=UserRole.ADMIN))
        db.commit()
    assert "alembic_version" not in inspect(engine).get_table_names()

    assert migrate(engine) == "adopted"
    assert _current_revision() == _head()
    with SessionLocal() as db:
        user = db.query(User).filter_by(username="pre_existing").one()
        assert user.hashed_password == "keep-me"
    assert migrate(engine) == "up_to_date"


def test_database_stamped_by_foreign_migrations_is_restamped(blank_db):
    Base.metadata.create_all(engine)
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL PRIMARY KEY)"))
        conn.execute(text("INSERT INTO alembic_version VALUES ('zzz_from_somewhere_else')"))
    assert migrate(engine) == "restamped"
    assert _current_revision() == _head()


# -------------------------------------------------------------------- seeding
def test_demo_accounts_are_created_hashed_and_with_the_right_roles(db):
    assert seed_demo_users() == 3
    with SessionLocal() as s:
        for username, password, role in DEMO_ACCOUNTS:
            user = s.query(User).filter_by(username=username).one()
            assert user.role == UserRole(role) and user.is_active
            assert user.hashed_password != password and verify_password(password, user.hashed_password)


def test_seeding_is_idempotent_and_never_overwrites_an_existing_account(db):
    with SessionLocal() as s:
        s.add(User(username="admin", hashed_password="my-own-hash", role=UserRole.ADMIN))
        s.commit()
    assert seed_demo_users() == 2                          # analyst + viewer only
    assert seed_demo_users() == 0
    with SessionLocal() as s:
        assert s.query(User).filter_by(username="admin").one().hashed_password == "my-own-hash"
        assert s.query(User).count() == 3


def test_demo_credentials_match_what_the_readme_documents():
    readme = (bootstrap.BACKEND_DIR.parent / "README.md").read_text()
    for username, password, _role in DEMO_ACCOUNTS:
        assert username in readme and password in readme


# ------------------------------------------------------------ waiting / warnings
def test_waiting_for_an_unreachable_database_fails_with_a_useful_message():
    dead = create_engine("postgresql+psycopg2://socuser:socpassword@localhost:5999/nothing")
    with pytest.raises(SystemExit) as exc:
        wait_for_database(dead, timeout=0.2, interval=0.05)
    assert "Database not reachable" in str(exc.value) and "DATABASE_URL" in str(exc.value)


def test_waiting_returns_immediately_when_the_database_is_up():
    wait_for_database(engine, timeout=5)


def test_insecure_defaults_are_flagged_outside_development(monkeypatch, caplog):
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(settings, "JWT_SECRET_KEY", "CHANGE_ME_DEMO_SECRET_NOT_FOR_PRODUCTION")
    monkeypatch.setattr(settings, "SEED_DEMO_USERS", True)
    with caplog.at_level(logging.WARNING, logger="bootstrap"):
        warn_about_insecure_defaults()
    text_ = " ".join(r.getMessage() for r in caplog.records)
    assert "JWT_SECRET_KEY" in text_ and "Demo accounts" in text_


def test_no_warnings_in_development_or_with_a_real_secret(monkeypatch, caplog):
    monkeypatch.setattr(settings, "ENVIRONMENT", "development")
    with caplog.at_level(logging.WARNING, logger="bootstrap"):
        warn_about_insecure_defaults()
    assert caplog.records == []

    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(settings, "JWT_SECRET_KEY", "x" * 64)
    monkeypatch.setattr(settings, "SEED_DEMO_USERS", False)
    with caplog.at_level(logging.WARNING, logger="bootstrap"):
        warn_about_insecure_defaults()
    assert caplog.records == []
