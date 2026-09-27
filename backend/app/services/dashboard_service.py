"""
Dashboard aggregation.

As of Phase 2/3, the `events`, `alerts`, and `incidents` tables don't
exist yet (they arrive in Phases 4, 5/7, and 9 respectively) — so
every KPI and chart series here is a real, honest zero rather than a
fabricated number. This function is the single place later phases
will replace with actual SQLAlchemy aggregation queries once that
data exists; the response shape is already final so the frontend
never needs to change.
"""
from datetime import datetime, timezone
from app.schemas.dashboard import (
    DashboardCharts,
    DashboardKpis,
    DashboardResponse,
)

def build_dashboard_snapshot() -> DashboardResponse:
    kpis = DashboardKpis(
        active_incidents=0,
        critical_alerts=0,
        events_processed=0,
        anomalies_detected=0,
        detection_rate_pct=None,
        avg_response_time_seconds=None,
        systems_at_risk=0,
    )

    charts = DashboardCharts(
        events_over_time=[],
        severity_distribution=[],
        detection_type_distribution=[],
        attack_category_distribution=[],
        ml_anomalies_over_time=[],
    )

    return DashboardResponse(
        kpis=kpis,
        charts=charts,
        live_events=[],
        data_status="no_data",
        message=(
            "No telemetry yet — the Event Simulator, Detection Engine, and "
            "Incident pipeline are built in upcoming phases. This snapshot "
            f"reflects the real (empty) state of the system as of "
            f"{datetime.now(timezone.utc).strftime('%Y-%m-%d')}."
        ),
    )
