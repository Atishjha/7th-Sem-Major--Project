"""
First-run bootstrap (Phase 16).

Runs before the API starts inside the Docker container, and can be run by
hand too:

    python -m app.bootstrap

It makes `docker compose up` work on a completely empty machine:

  1. wait until PostgreSQL accepts connections
  2. bring the schema up to date with Alembic
       - brand-new database            -> `alembic upgrade head`
       - already has our tables, but
         was never managed by Alembic  -> adopt it: `alembic stamp head`
         (so existing local databases keep working, data untouched)
       - managed by Alembic            -> `alembic upgrade head`
  3. create the demo accounts if SEED_DEMO_USERS is true (idempotent)

It never drops or rewrites existing data.
"""

import logging
import sys
import time
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import inspect, text
from sqlalchemy.exc import OperationalError

from app.config import settings

BACKEND_DIR = Path(__file__).resolve().parents[1]
log = logging.getLogger("bootstrap")

DEMO_ACCOUNTS = [
    ("admin", "admin123", "ADMIN"),
    ("analyst", "analyst123", "SOC_ANALYST"),
    ("viewer", "viewer123", "VIEWER"),
]


def alembic_config() -> Config:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    return cfg


def wait_for_database(engine, timeout: float = 60.0, interval: float = 2.0) -> None:
    deadline = time.monotonic() + timeout
    attempt = 0
    while True:
        attempt += 1
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            log.info("database is accepting connections")
            return
        except OperationalError as exc:
            if time.monotonic() >= deadline:
                raise SystemExit(
                    f"Database not reachable after {timeout:.0f}s ({exc.orig}). "
                    "Check DATABASE_URL and that the postgres service is running."
                )
            log.info("waiting for database (attempt %d)...", attempt)
            time.sleep(interval)


def migrate(engine) -> str:
    """Bring the schema up to date. Returns what it did, for logging/tests."""
    cfg = alembic_config()
    heads = ScriptDirectory.from_config(cfg).get_heads()
    tables = set(inspect(engine).get_table_names())

    with engine.connect() as conn:
        current = MigrationContext.configure(conn).get_current_revision()

    known = {r.revision for r in ScriptDirectory.from_config(cfg).walk_revisions()}

    if current is None and "users" in tables:
        log.warning(
            "Found an existing database that was never managed by Alembic; "
            "adopting it as-is (stamping, not modifying any data)."
        )
        command.stamp(cfg, "head")
        return "adopted"

    if current is not None and current not in known:
        log.warning(
            "Database is at unknown revision %r (migrations from a different "
            "history). Re-stamping it to this project's head; data is untouched.",
            current,
        )
        command.stamp(cfg, "head", purge=True)
        return "restamped"

    if current in heads:
        log.info("schema already up to date (revision %s)", current)
        return "up_to_date"

    command.upgrade(cfg, "head")
    return "upgraded" if current is None else "upgraded_existing"


def seed_demo_users() -> int:
    """Create any missing demo accounts. Returns how many were created."""
    from app.database.session import SessionLocal
    from app.models.user import User, UserRole
    from app.security.hashing import hash_password

    created = 0
    db = SessionLocal()
    try:
        for username, password, role in DEMO_ACCOUNTS:
            if db.query(User).filter(User.username == username).first():
                continue
            db.add(User(username=username, hashed_password=hash_password(password),
                        role=UserRole(role), is_active=True))
            created += 1
        db.commit()
    finally:
        db.close()
    return created


def warn_about_insecure_defaults() -> None:
    if settings.ENVIRONMENT.lower() != "development" and settings.JWT_SECRET_KEY.startswith("CHANGE_ME"):
        log.warning("JWT_SECRET_KEY is still the demo placeholder while ENVIRONMENT=%s. "
                    "Set a long random secret before exposing this anywhere.", settings.ENVIRONMENT)
    if settings.SEED_DEMO_USERS and settings.ENVIRONMENT.lower() != "development":
        log.warning("Demo accounts with public passwords are enabled "
                    "(SEED_DEMO_USERS=true) outside a development environment.")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="[bootstrap] %(message)s")
    # Alembic's env.py applies alembic.ini's logging config, which resets the
    # root logger to WARN; pin our own level so our messages always show.
    log.setLevel(logging.INFO)
    from app.database.session import engine

    warn_about_insecure_defaults()
    wait_for_database(engine)
    result = migrate(engine)
    log.info("migrations: %s", result)

    if settings.SEED_DEMO_USERS:
        created = seed_demo_users()
        log.info("demo accounts: %d created, %d already present", created, len(DEMO_ACCOUNTS) - created)
    else:
        log.info("demo accounts: skipped (SEED_DEMO_USERS=false)")
    log.info("ready")


if __name__ == "__main__":
    sys.exit(main())
