"""AI analyst status: which provider will answer an investigation right now."""
from typing import Literal
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from app.ai.llm_provider import PROVIDER_DEFAULT_MODELS, configuration_problem
from app.config import settings
from app.models.user import User
from app.security.dependencies import get_current_user
router = APIRouter(prefix="/ai", tags=["ai"])
class AiStatus(BaseModel):
    mode: Literal["mock", "live"]
    provider: str
    model: str | None
    key_configured: bool
    label: str
    note: str | None = None
@router.get("/status", response_model=AiStatus)
def ai_status(_: User = Depends(get_current_user)) -> AiStatus:
    """Never returns the key, only whether one is set."""
    provider, key = settings.AI_PROVIDER, bool(settings.AI_API_KEY)
    if provider == "mock":
        return AiStatus(mode="mock", provider="mock", model=None, key_configured=key, label="mock",
                        note="Offline analyst. Set AI_PROVIDER and AI_API_KEY to use a real model.")
    if not key:
        return AiStatus(mode="mock", provider=provider, model=settings.AI_MODEL, key_configured=False, label="mock",
                        note=f"AI_PROVIDER is {provider} but AI_API_KEY is empty, so the offline analyst answers.")
    problem = configuration_problem()
    if problem:
        return AiStatus(mode="mock", provider=provider, model=settings.AI_MODEL, key_configured=True, label="mock",
                        note=f"{problem} The offline analyst answers until this is fixed.")
    model = settings.AI_MODEL or PROVIDER_DEFAULT_MODELS[provider]
    return AiStatus(mode="live", provider=provider, model=model, key_configured=True,
                    label=f"llm:{provider}:{model}",
                    note="A failed call falls back to the offline analyst and the report says so.")

