from fastapi import APIRouter, Depends,HTTPException, status
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, TokenResponse, UserOut
from app.security.dependencies import get_current_user
from app.security.jwt import create_access_token
from app.services.auth_service import authenticate_user
from backend.app.models import user
router = APIRouter(prefix="/auth", tags=["auth"])
@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = authenticate_user(db, payload.username, payload.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token(username=user.username, role=user.role.value)
    return TokenResponse(access_token=token, role=user.role)

@router.get("/me", response_model=UserOut)
def read_current_user(current_user:User = Depends(get_current_user)) -> User:
    return current_user
