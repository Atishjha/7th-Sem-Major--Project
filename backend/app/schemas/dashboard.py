from pydantic import BaseModel
class DashboardKpis(BaseModel):
    active_incidents: int
    critical_alerts: int
    events_processed: int
    anomalies_detected: int
    detection_rate_pct: float | None
    avg_response_time_seconds: float | None
    systems_at_risk: int

class TimeSeriesPoint(BaseModel):
    label: str
    value: float
class CategoryCount(BaseModel):
    category: str
    count: int
class DashboardCharts(BaseModel):
    events_over_time: list[TimeSeriesPoint]
    severity_distribution: list[CategoryCount]
    detection_type_distribution: list[CategoryCount]
    attack_category_distribution: list[CategoryCount]
    ml_anomalies_over_time: list[TimeSeriesPoint]
class LiveEvent(BaseModel):
    timestamp: str
    source: str
    message: str
class DashboardResponse(BaseModel):
    kpis: DashboardKpis
    charts: DashboardCharts
    live_events: list[LiveEvent]
    data_status: str  # "no_data" | "live"
    message: str
