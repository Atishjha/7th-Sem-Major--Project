"""
Central application settings.

Everything here is read from environment variables (see ../.env.example
at the project root). Nothing sensitive has a real default — the demo
values are placeholders clearly marked as such.
"""
from pydantic_settings import BaseSettings,SettingsConfigDict
class Settings(BaseSettings):
    #--General --- 
    APP_NAME: str = "AI Cyber Defense Command Center"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    #API
    API_V1_PREFIX: str = "/api"
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]
    #Database
    DATABASE_URL: str = (
        "postgresql+psycopg2://socuser:socpassword@localhost:5432/soc_db"
    )
    #Auth 
    JWT_SECRET_KEY: str = "CHANGE_ME_DEMO_SECRET_NOT_FOR_PRODUCTION"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    #ai provider abstraction (Phase 10)
    AI_PROVIDER: str = "mock"  # mock | gemini | groq | openai_compatible | openrouter
    AI_API_KEY: str | None = None
    AI_MODEL: str | None = None
    model_config = SettingsConfigDict(env_files=".env",extra="ignore")
settings = Settings()