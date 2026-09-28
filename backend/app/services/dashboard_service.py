"""
Dashboard aggregation.

Events (Phase 4), alerts/detection-type breakdown (Phase 5), ML
anomaly counts (Phase 6), and incidents/systems-at-risk (Phase 7) are
all real, computed straight from the DB. attack_category (MITRE
mapping), detection_rate_pct, and avg_response_time_seconds stay a
genuine zero/null until those pipelines exist in Phases 11-12 —
never a fabricated number.
"""

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.alert import Alert
from app.models.common import Severity
from app.models.event import Event
from app.models.incident import Incident
from app.models.ml_prediction import MLPrediction
from app.models.ml_training_run import MLTrainingRun
from app.schemas.dashboard import (
    CategoryCount,
    DashboardCharts,
    DashboardKpis,
    DashboardResponse,
    IncidentSummary,
    TimeSeriesPoint,
)


def _events_over_time(db: Session, minutes: int = 30) -> list[TimeSeriesPoint]:
    since = datetime.now(timezone.utc) - timedelta(minutes=minutes)
    bucket = func.date_trunc("minute", Event.timestamp)
    stmt = (
        select(bucket.label("bucket"), func.count().label("count"))
        .where(Event.timestamp >= since)
        .group_by(bucket)
        .order_by(bucket)
    )
    rows = db.execute(stmt).all()
    return [
        TimeSeriesPoint(label=row.bucket.strftime("%H:%M"), value=row.count)
        for row in rows
    ]


def _severity_distribution(db: Session) -> list[CategoryCount]:
    stmt = (
        select(Alert.severity, func.count())
        .where(Alert.status == "open")
        .group_by(Alert.severity)
    )
    return [
        CategoryCount(category=severity.value, count=count)
        for severity, count in db.execute(stmt).all()
    ]


def _detection_type_distribution(db: Session) -> list[CategoryCount]:
    stmt = select(Alert.rule_name, func.count()).group_by(Alert.rule_name)
    return [
        CategoryCount(category=rule_name, count=count)
        for rule_name, count in db.execute(stmt).all()
    ]


def _latest_training_run_id(db: Session) -> int | None:
    return db.scalar(
        select(MLTrainingRun.id).order_by(MLTrainingRun.trained_at.desc()).limit(1)
    )


def _ml_anomalies_over_time(db: Session, training_run_id: int | None) -> list[TimeSeriesPoint]:
    if training_run_id is None:
        return []
    bucket = func.date_trunc("minute", MLPrediction.window_start)
    stmt = (
        select(bucket.label("bucket"), func.count().label("count"))
        .where(
            MLPrediction.training_run_id == training_run_id,
            MLPrediction.is_anomalous.is_(True),
        )
        .group_by(bucket)
        .order_by(bucket)
    )
    rows = db.execute(stmt).all()
    return [
        TimeSeriesPoint(label=row.bucket.strftime("%H:%M"), value=row.count)
        for row in rows
    ]


def build_dashboard_snapshot(db: Session) -> DashboardResponse:
    events_processed = db.scalar(select(func.count()).select_from(Event)) or 0
    critical_alerts = (
        db.scalar(
            select(func.count())
            .select_from(Alert)
            .where(Alert.severity == Severity.CRITICAL, Alert.status == "open")
        )
        or 0
    )
    total_alerts = db.scalar(select(func.count()).select_from(Alert)) or 0

    latest_run_id = _latest_training_run_id(db)
    anomalies_detected = 0
    if latest_run_id is not None:
        anomalies_detected = (
            db.scalar(
                select(func.count())
                .select_from(MLPrediction)
                .where(
                    MLPrediction.training_run_id == latest_run_id,
                    MLPrediction.is_anomalous.is_(True),
                )
            )
            or 0
        )

    recent_events = list(
        db.scalars(select(Event).order_by(Event.timestamp.desc()).limit(10))
    )

    total_incidents = db.scalar(select(func.count()).select_from(Incident)) or 0
    active_incidents = (
        db.scalar(
            select(func.count()).select_from(Incident).where(Incident.status == "open")
        )
        or 0
    )
    systems_at_risk = (
        db.scalar(
            select(func.count(func.distinct(Incident.primary_hostname))).where(
                Incident.status == "open", Incident.primary_hostname.is_not(None)
            )
        )
        or 0
    )
    recent_incidents = [
        IncidentSummary(
            incident_id=i.incident_id,
            title=i.title,
            severity=i.severity.value,
            alert_count=i.alert_count,
            last_seen=i.last_seen.isoformat(),
        )
        for i in db.scalars(select(Incident).order_by(Incident.last_seen.desc()).limit(6))
    ]

    kpis = DashboardKpis(
        active_incidents=active_incidents,
        critical_alerts=critical_alerts,
        events_processed=events_processed,
        anomalies_detected=anomalies_detected,
        detection_rate_pct=None,
        avg_response_time_seconds=None,
        systems_at_risk=systems_at_risk,
    )

    charts = DashboardCharts(
        events_over_time=_events_over_time(db),
        severity_distribution=_severity_distribution(db),
        detection_type_distribution=_detection_type_distribution(db),
        attack_category_distribution=[],
        ml_anomalies_over_time=_ml_anomalies_over_time(db, latest_run_id),
    )

    live_events = [
        {
            "timestamp": e.timestamp.isoformat(),
            "source": e.source,
            "message": e.message,
        }
        for e in recent_events
    ]

    if events_processed == 0:
        message = (
            "No telemetry yet — run a scenario from Demo Mode or wait for "
            "seeded events."
        )
        data_status = "no_data"
    else:
        ml_part = (
            f", {anomalies_detected} ML-flagged anomal(ies)"
            if latest_run_id is not None
            else " (train the model on the ML Anomaly Detection page to add anomaly scoring)"
        )
        message = (
            f"{events_processed} event(s), {total_alerts} alert(s) correlated "
            f"into {total_incidents} incident(s){ml_part}. Risk scoring, MITRE "
            "mapping, and response actions arrive in Phases 8-12."
        )
        data_status = "live"

    return DashboardResponse(
        kpis=kpis,
        charts=charts,
        live_events=live_events,
        recent_incidents=recent_incidents,
        data_status=data_status,
        message=message,
    )
