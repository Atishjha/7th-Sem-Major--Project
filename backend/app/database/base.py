"""
Shared SQLAlchemy declarative base.

Every ORM model in the project (users now; events, alerts, incidents,
etc. in later phases) inherits from this Base so they all register on
the same MetaData object — which is what Alembic autogenerate and
`Base.metadata.create_all()` both rely on.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
