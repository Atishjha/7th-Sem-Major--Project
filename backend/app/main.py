"""
AI Cyber Defense Command Center — backend entrypoint.

This is an educational defensive-cybersecurity demo. All telemetry,
indicators, and response actions produced by this system are
synthetic or simulated — see /docs and the README for the full
academic disclaimer.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api import health, auth, dashboard, events, simulator, ws, alerts, detections, rules, ml, incidents, assets, mitre, response
from app.database.session import SessionLocal
from app.detectors.engine import ensure_default_rules
from app.services.correlation import backfill_uncorrelated_alerts
from app.services.risk_engine import ensure_default_assets, recompute_all_incidents


@asynccontextmanager
async def lifespan(app: FastAPI):
    db = SessionLocal()
    try:
        ensure_default_rules(db)
        backfill_uncorrelated_alerts(db)
        ensure_default_assets(db)
        recompute_all_incidents(db)
    finally:
        db.close()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "Educational SOC simulation: rule + ML detection, alert "
        "correlation, incident management, AI-assisted investigation, "
        "and simulated (non-destructive) response actions."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix=settings.API_V1_PREFIX)
app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
app.include_router(dashboard.router, prefix=settings.API_V1_PREFIX)
app.include_router(events.router, prefix=settings.API_V1_PREFIX)
app.include_router(simulator.router, prefix=settings.API_V1_PREFIX)
app.include_router(alerts.router, prefix=settings.API_V1_PREFIX)
app.include_router(detections.router, prefix=settings.API_V1_PREFIX)
app.include_router(rules.router, prefix=settings.API_V1_PREFIX)
app.include_router(ml.router, prefix=settings.API_V1_PREFIX)
app.include_router(incidents.router, prefix=settings.API_V1_PREFIX)
app.include_router(assets.router, prefix=settings.API_V1_PREFIX)
app.include_router(mitre.router, prefix=settings.API_V1_PREFIX)
app.include_router(response.router, prefix=settings.API_V1_PREFIX)
app.include_router(ws.router)  # no /api prefix — matches the frontend's /ws proxy rule


@app.get("/")
def root() -> dict:
    return {
        "message": f"{settings.APP_NAME} API",
        "docs": "/docs",
        "health": f"{settings.API_V1_PREFIX}/health",
    }
