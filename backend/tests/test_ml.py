"""
ML anomaly detection (Phase 6): feature engineering + Isolation Forest.

The honesty rules are tested explicitly: an unsupervised model on unlabeled
events must never report an accuracy figure.
"""

from datetime import datetime, timedelta, timezone

import joblib
import pandas as pd
import pytest

from app.ml.features import FEATURE_COLUMNS, _floor_to_window, build_feature_matrix
from app.ml.train import MIN_SAMPLES_TO_TRAIN, NotEnoughDataError, train_and_score
from app.models.ml_prediction import MLPrediction
from app.models.ml_training_run import MLTrainingRun
from helpers import make_event

T0 = datetime(2026, 3, 2, 10, 0, 0, tzinfo=timezone.utc)      # aligned to a 5-minute boundary


def _baseline(db, n=30):
    """n quiet source IPs: one successful login and one DNS lookup each."""
    for i in range(n):
        ip = f"10.0.0.{i + 1}"
        make_event(db, source="authentication", event_type="login", status="success", source_ip=ip, ts=T0)
        make_event(db, source="dns", event_type="dns_query", source_ip=ip, ts=T0 + timedelta(seconds=5))


def _attacker(db, ip="203.0.113.50"):
    for i in range(40):
        make_event(db, source="authentication", event_type="login", status="failed", source_ip=ip,
                   ts=T0 + timedelta(seconds=i))
    for i in range(15):
        make_event(db, source="network", event_type="network_anomaly", source_ip=ip, destination_ip=f"198.51.100.{i}",
                   ts=T0 + timedelta(seconds=i), metadata={"bytes_sent": 90_000_000})


# ------------------------------------------------------------------ features
def test_feature_columns_are_the_ten_from_the_spec():
    assert FEATURE_COLUMNS == [
        "login_frequency", "failed_login_count", "request_frequency", "bytes_sent", "bytes_received",
        "unique_destination_count", "dns_request_count", "connection_count", "process_frequency", "login_hour",
    ]


def test_no_events_gives_an_empty_frame_with_the_right_columns(db):
    df = build_feature_matrix(db)
    assert df.empty
    assert list(df.columns) == ["source_ip", "window_start"] + FEATURE_COLUMNS


def test_features_are_counted_per_source_ip_and_window(db):
    ip = "203.0.113.9"
    for _ in range(3):
        make_event(db, source="authentication", event_type="login", status="failed", source_ip=ip, ts=T0)
    make_event(db, source="authentication", event_type="login", status="success", source_ip=ip, ts=T0)
    for _ in range(2):
        make_event(db, source="dns", event_type="dns_query", source_ip=ip, ts=T0)
    make_event(db, source="endpoint", event_type="process_execution", source_ip=ip, ts=T0)
    make_event(db, source="network", event_type="network_anomaly", source_ip=ip, destination_ip="198.51.100.1",
               ts=T0, metadata={"bytes_sent": 1_000})
    make_event(db, source="network", event_type="network_anomaly", source_ip=ip, destination_ip="198.51.100.2",
               ts=T0, metadata={"bytes_sent": 500})

    (row,) = build_feature_matrix(db).to_dict("records")
    assert row["source_ip"] == ip
    assert row["login_frequency"] == 4 and row["failed_login_count"] == 3
    assert row["dns_request_count"] == 2 and row["process_frequency"] == 1
    assert row["connection_count"] == 2 and row["unique_destination_count"] == 2
    assert row["bytes_sent"] == 1500
    assert row["bytes_received"] == 0                      # documented: never fabricated
    assert row["request_frequency"] == 9
    assert row["login_hour"] == 10


def test_events_are_split_into_windows(db):
    make_event(db, source="dns", event_type="dns_query", source_ip="10.0.0.1", ts=T0)
    make_event(db, source="dns", event_type="dns_query", source_ip="10.0.0.1", ts=T0 + timedelta(minutes=6))
    assert len(build_feature_matrix(db, window_minutes=5)) == 2
    assert len(build_feature_matrix(db, window_minutes=15)) == 1


def test_events_without_a_source_ip_are_skipped(db):
    make_event(db, source="dns", event_type="dns_query", source_ip=None, ts=T0)
    assert build_feature_matrix(db).empty


def test_window_flooring():
    assert _floor_to_window(T0 + timedelta(minutes=3, seconds=40), 5) == T0
    assert _floor_to_window(T0 + timedelta(minutes=5), 5) == T0 + timedelta(minutes=5)
    naive = datetime(2026, 3, 2, 10, 4, 59)                # naive timestamps are treated as UTC
    assert _floor_to_window(naive, 5) == T0


# ------------------------------------------------------------------ training
def test_training_needs_enough_data(db, ml_sandbox):
    for i in range(MIN_SAMPLES_TO_TRAIN - 1):
        make_event(db, source="dns", event_type="dns_query", source_ip=f"10.0.0.{i}", ts=T0)
    with pytest.raises(NotEnoughDataError, match="need at least"):
        train_and_score(db)


def test_training_run_is_recorded_honestly(db, ml_sandbox):
    _baseline(db)
    run = train_and_score(db, contamination=0.1)
    assert run.model_type == "IsolationForest"
    assert run.num_samples == 30 and run.num_features == 10
    assert run.feature_names == FEATURE_COLUMNS
    assert run.contamination == 0.1
    assert run.source == "event_stream"
    # Honesty rule: no labels exist, so no accuracy number may be reported.
    assert run.accuracy_status == "not_applicable"
    assert not ({"accuracy", "precision", "recall", "f1"} & set(run.evaluation))


def test_every_window_gets_a_prediction_with_a_valid_score(db, ml_sandbox):
    _baseline(db)
    run = train_and_score(db, contamination=0.1)
    preds = db.query(MLPrediction).filter_by(training_run_id=run.id).all()
    assert len(preds) == run.num_samples
    assert all(0.0 <= p.anomaly_score <= 1.0 for p in preds)
    assert sum(p.is_anomalous for p in preds) == run.anomalies_flagged


def test_the_model_file_is_saved_and_loadable(db, ml_sandbox):
    _baseline(db)
    run = train_and_score(db)
    saved = ml_sandbox / run.file_path
    assert saved.exists() and saved.suffix == ".joblib"
    bundle = joblib.load(saved)
    assert set(bundle) == {"model", "scaler", "features"} and bundle["features"] == FEATURE_COLUMNS
    assert not list((ml_sandbox / "ml" / "models").glob("../../../*.joblib"))   # nothing escaped the sandbox


def test_an_obvious_outlier_is_flagged_and_ranked_first(db, ml_sandbox):
    _baseline(db)
    _attacker(db, "203.0.113.50")
    run = train_and_score(db, contamination=0.05)
    top = db.query(MLPrediction).filter_by(training_run_id=run.id).order_by(MLPrediction.anomaly_score.desc()).first()
    assert top.source_ip == "203.0.113.50"
    assert top.is_anomalous is True and top.anomaly_score == pytest.approx(1.0)
    normal = db.query(MLPrediction).filter_by(training_run_id=run.id, source_ip="10.0.0.1").one()
    assert normal.is_anomalous is False


def test_back_to_back_training_runs_get_unique_versions(db, ml_sandbox):
    """Regression for the Phase 14 bug: two runs in the same second used to
    collide on the unique model_version constraint."""
    _baseline(db)
    versions = {train_and_score(db).model_version for _ in range(3)}
    assert len(versions) == 3
    assert db.query(MLTrainingRun).count() == 3


# ----------------------------------------------------------------------- API
def test_status_before_and_after_training(client, headers, db, ml_sandbox):
    assert client.get("/api/ml/status", headers=headers["viewer"]).json() == {"has_model": False, "latest_run": None}
    assert client.get("/api/ml/predictions", headers=headers["viewer"]).json() == []

    _baseline(db)
    r = client.post("/api/ml/train", headers=headers["analyst"], json={"contamination": 0.1})
    assert r.status_code == 200 and r.json()["accuracy_status"] == "not_applicable"
    status = client.get("/api/ml/status", headers=headers["viewer"]).json()
    assert status["has_model"] is True and status["latest_run"]["num_samples"] == 30


def test_train_with_too_little_data_is_a_400(client, headers, ml_sandbox):
    r = client.post("/api/ml/train", headers=headers["analyst"], json={})
    assert r.status_code == 400 and "need at least" in r.json()["detail"]


def test_predictions_endpoint_filters_and_orders(client, headers, db, ml_sandbox):
    _baseline(db)
    _attacker(db)
    client.post("/api/ml/train", headers=headers["analyst"], json={"contamination": 0.05})
    allp = client.get("/api/ml/predictions", headers=headers["viewer"]).json()
    scores = [p["anomaly_score"] for p in allp]
    assert scores == sorted(scores, reverse=True)
    only = client.get("/api/ml/predictions?anomalous_only=true", headers=headers["viewer"]).json()
    assert only and all(p["is_anomalous"] for p in only) and len(only) < len(allp)
    assert len(client.get("/api/ml/predictions?limit=3", headers=headers["viewer"]).json()) == 3


@pytest.mark.parametrize("payload", [{"contamination": 0}, {"contamination": 0.9}, {"contamination": -0.1},
                                     {"window_minutes": 0}, {"window_minutes": -5}])
def test_train_rejects_invalid_parameters_with_422_not_500(client, headers, db, ml_sandbox, payload):
    _baseline(db)
    r = client.post("/api/ml/train", headers=headers["analyst"], json=payload)
    assert r.status_code == 422, r.text


# =========================================================== Phase 16 fixes
# Found while writing the demo script: the ML factor never updated after
# training, ML training wasn't audited, and an uploaded-dataset run could
# displace the event-stream model that the ML page / dashboard / risk engine read.
from app.models.audit_log import AuditLog  # noqa: E402
from helpers import replay_scenario  # noqa: E402


def _ml_factor(incident_json):
    return next(f for f in incident_json["incident_metadata"]["risk_breakdown"] if f["factor"] == "ml_anomaly")


def test_ml_training_is_audited(client, headers, db, ml_sandbox):
    _baseline(db)
    r = client.post("/api/ml/train", headers=headers["analyst"], json={"contamination": 0.1, "window_minutes": 5})
    assert r.status_code == 200
    (entry,) = db.query(AuditLog).filter(AuditLog.resource_type == "ml_model").all()
    assert entry.action == "Trained ML anomaly model on the event stream"
    assert entry.username == "analyst" and entry.resource_id == r.json()["model_version"]
    assert entry.new_value["num_samples"] == 30 and entry.new_value["contamination"] == 0.1
    assert {"anomalies_flagged", "window_minutes", "incidents_rescored"} <= set(entry.new_value)


def test_failed_training_is_not_audited(client, headers, db, ml_sandbox):
    assert client.post("/api/ml/train", headers=headers["analyst"], json={}).status_code == 400
    assert db.query(AuditLog).count() == 0


def test_training_rescores_incidents_that_already_exist(client, headers, db, ml_sandbox):
    """An attack happens first, the model is trained afterwards: the incident's
    risk score must pick up the ML factor instead of staying frozen at 0."""
    _baseline(db)
    _alerts, (incident,) = replay_scenario(db, "multi_stage")
    before = client.get(f"/api/incidents/{incident.incident_id}", headers=headers["viewer"]).json()
    assert _ml_factor(before)["points"] == 0 and _ml_factor(before)["detail"]["available"] is False

    assert client.post("/api/ml/train", headers=headers["analyst"], json={"contamination": 0.1}).status_code == 200

    after = client.get(f"/api/incidents/{incident.incident_id}", headers=headers["viewer"]).json()
    factor = _ml_factor(after)
    assert factor["detail"]["matched"] is True and factor["points"] > 0
    assert after["risk_score"] == before["risk_score"] + factor["points"]
    entry = db.query(AuditLog).filter(AuditLog.resource_type == "ml_model").one()
    assert entry.new_value["incidents_rescored"] == 1


def test_an_uploaded_dataset_run_does_not_displace_the_event_stream_model(client, headers, db, ml_sandbox):
    """Regression: training on NSL-KDD-style data used to make the ML page show
    that run (with no predictions), blank the dashboard chart and zero the ML factor."""
    import numpy as np

    from app.ml.dataset import train_on_dataset

    _baseline(db)
    _alerts, (incident,) = replay_scenario(db, "multi_stage")
    stream = client.post("/api/ml/train", headers=headers["analyst"], json={"contamination": 0.1}).json()
    predictions_before = client.get("/api/ml/predictions?limit=500", headers=headers["viewer"]).json()
    assert predictions_before

    rng = np.random.default_rng(1)
    pd.DataFrame({"f1": rng.normal(size=60), "f2": rng.normal(size=60)}).to_csv(
        ml_sandbox / "data" / "processed" / "later.processed.csv", index=False)
    dataset_run = train_on_dataset(db, "later.processed.csv", None, None)
    assert dataset_run.source == "uploaded_dataset"            # it really is the newest run

    status = client.get("/api/ml/status", headers=headers["viewer"]).json()
    assert status["latest_run"]["model_version"] == stream["model_version"]
    assert status["latest_run"]["source"] == "event_stream"
    assert client.get("/api/ml/predictions?limit=500", headers=headers["viewer"]).json() == predictions_before

    from app.services.risk_engine import recompute_and_save
    recompute_and_save(db, incident)
    db.commit()
    db.refresh(incident)
    ml = next(f for f in incident.incident_metadata["risk_breakdown"] if f["factor"] == "ml_anomaly")
    assert ml["detail"]["matched"] is True

    dash = client.get("/api/dashboard", headers=headers["viewer"]).json()
    assert dash["charts"]["ml_anomalies_over_time"], "dashboard ML chart went blank after a dataset run"


def test_with_only_a_dataset_run_there_is_no_event_stream_model(client, headers, db, ml_sandbox):
    from app.ml.dataset import train_on_dataset

    pd.DataFrame({"f1": range(10), "f2": range(10)}).to_csv(ml_sandbox / "data" / "processed" / "d.processed.csv", index=False)
    train_on_dataset(db, "d.processed.csv", None, None)
    assert client.get("/api/ml/status", headers=headers["viewer"]).json() == {"has_model": False, "latest_run": None}
    assert client.get("/api/ml/predictions", headers=headers["viewer"]).json() == []
