"""
User model and roles.

Three roles for the academic demo, matching the project spec exactly:
ADMIN, SOC_ANALYST, VIEWER. Passwords are always stored hashed —
never in plaintext, even for the demo accounts.
"""
import enum
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Enum, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.database.base import Base
class UserRole(str, enum.Enum):
    ADMIN = "ADMIN"
    SOC_ANALYST = "SOC_ANALYST"
    VIEWER = "VIEWER"
class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    username:Mapped[str] = mapped_column(String(64),unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(Enum(UserRole),default=UserRole.VIEWER)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),default=lambda: datetime.now(timezone.utc)
    )