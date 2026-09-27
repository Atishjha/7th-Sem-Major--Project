"""
AI Cyber Defense Command Center — backend entrypoint.

This is an educational defensive-cybersecurity demo. All telemetry,
indicators, and response actions produced by this system are
synthetic or simulated — see /docs and the README for the full
academic disclaimer.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.api import health 
app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "Educational SOC simulation: rule + ML detection, alert "
        "correlation, incident management, AI-assisted investigation, "
        "and simulated (non-destructive) response actions."
    ),
    version="0.1.0"
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(health.router, prefix=settings.API_V1_PREFIX)
@app.get("/")
def root() -> dict:
    return {
        "message": f"{settings.APP_NAME} API",
        "docs":"/docs",
        "health":f"{settings.API_V1_PREFIX}/health",
    }