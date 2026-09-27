"""
Auth dependencies used to protect routes:

- `get_current_user`: decodes the bearer token, loads the user, 401s
  if missing/invalid/inactive.
- `require_role(...)`: further restricts a route to specific roles,
  403s otherwise. This is the RBAC mechanism referenced throughout
  the project spec.
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models.user import User, UserRole
from app.security.jwt import decode_access_token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")
def get_current_user(token:str = Depends(oauth2_scheme), db: Session = Depends(get_db))-> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_access_token(token)
    if payload is None or "sub" not in payload:
        raise credentials_error
    user = db.query(User).filter(User.username == payload["sub"]).first()
    if user is None or not user.is_active:
        raise credentials_error
    return user
def require_role(*allowed_roles: UserRole):
    def _checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Role '{current_user.role.value}' is not permitted to "
                    f"perform this action."
                ),
            )
        return current_user
    return _checker
