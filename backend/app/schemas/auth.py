from pydantic import BaseModel
from app.models.user import UserRole
class LoginRequest(BaseModel):
    username: str
    password: str
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: UserRole
class UserOut(BaseModel):
    id: str
    username: str
    role: UserRole
    is_active: bool

    class Config:
        from_attributes = True
        