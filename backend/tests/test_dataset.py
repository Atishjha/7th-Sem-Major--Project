"""
Dataset upload / preprocess / train (Phase 14).

Covers the file-handling attack surface (extension allow-list, path traversal)
and the honesty rule: accuracy metrics exist only when a label column does.
"""

import io

import numpy as np
import pandas as pd
import pytest

from app.ml.dataset import (
    DatasetError, attack_mask, list_processed_files, list_raw_files, preprocess_dataset, save_uploaded_file,
    train_on_dataset,
)
from app.models.ml_training_run import MLTrainingRun


def _labeled_frame(n_normal=190, n_attack=10, seed=0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    normal = pd.DataFrame({"f1": rng.normal(0, 1, n_normal), "f2": rng.normal(0, 1, n_normal), "Label": "benign"})
    attack = pd.DataFrame({"f1": rng.normal(9, 0.5, n_attack), "f2": rng.normal(9, 0.5, n_attack), "Label": "attack"})
    return pd.concat([normal, attack], ignore_index=True)


def _write_raw(sandbox, name, df):
    path = sandbox / "data" / "raw" / name
    if name.endswith(".parquet"):
        df.to_parquet(path)
    else:
        df.to_csv(path, index=False)
    return path


# ------------------------------------------------------------------ upload
def test_upload_saves_a_csv_and_lists_it(client, headers, ml_sandbox):
    r = client.post("/api/dataset/upload", headers=headers["analyst"], files={"file": ("traffic.csv", b"a,b\n1,2\n")})
    assert r.status_code == 201
    assert r.json()["filename"] == "traffic.csv" and r.json()["size_bytes"] == 8
    assert (ml_sandbox / "data" / "raw" / "traffic.csv").read_bytes() == b"a,b\n1,2\n"
    files = client.get("/api/dataset/files", headers=headers["viewer"]).json()
    assert [f["filename"] for f in files["raw"]] == ["traffic.csv"] and files["processed"] == []


@pytest.mark.parametrize("name", ["malware.exe", "notes.txt", "script.py", "archive.zip", "noextension", "data.csv.exe"])
def test_upload_rejects_everything_but_csv_and_parquet(client, headers, ml_sandbox, name):
    r = client.post("/api/dataset/upload", headers=headers["admin"], files={"file": (name, b"x")})
    assert r.status_code == 400
    assert "Only .csv and .parquet" in r.json()["detail"]
    assert list((ml_sandbox / "data" / "raw").iterdir()) == []


@pytest.mark.security
@pytest.mark.parametrize("name", ["../../evil.csv", "../evil.csv", "/tmp/evil.csv", "sub/dir/evil.csv", "..\\..\\evil.csv"])
def test_upload_filename_cannot_escape_the_raw_directory(client, headers, ml_sandbox, name):
    client.post("/api/dataset/upload", headers=headers["admin"], files={"file": (name, b"a\n1\n")})
    raw = ml_sandbox / "data" / "raw"
    assert not (ml_sandbox / "evil.csv").exists() and not (ml_sandbox.parent / "evil.csv").exists()
    assert not any(p.is_file() for p in ml_sandbox.rglob("evil.csv") if p.parent != raw)


def test_extension_check_is_case_insensitive(ml_sandbox):
    assert save_uploaded_file("DATA.CSV", b"a\n1\n")["filename"] == "DATA.CSV"


def test_listing_ignores_non_dataset_files(ml_sandbox):
    (ml_sandbox / "data" / "raw" / "readme.txt").write_text("hi")
    (ml_sandbox / "data" / "raw" / "d.csv").write_text("a\n1\n")
    assert [f["filename"] for f in list_raw_files()] == ["d.csv"]
    assert list_processed_files() == []


# -------------------------------------------------------------- preprocess
def test_preprocess_keeps_numeric_columns_drops_text_and_reports_it(ml_sandbox):
    _write_raw(ml_sandbox, "d.csv", pd.DataFrame({"a": [1, 2, 3], "b": [4.0, 5.0, 6.0], "note": ["x", "y", "z"]}))
    result = preprocess_dataset("d.csv", None)
    assert result["feature_names"] == ["a", "b"]
    assert result["dropped_columns"] == ["note"]
    assert result["num_records"] == 3 and result["num_features"] == 2 and result["rows_dropped"] == 0
    assert result["label_column"] is None and result["label_distribution"] is None
    assert result["processed_filename"] == "d.processed.csv"
    assert (ml_sandbox / "data" / "processed" / "d.processed.csv").exists()


def test_preprocess_drops_rows_with_missing_or_infinite_values(ml_sandbox):
    df = pd.DataFrame({"a": [1.0, np.nan, 3.0, np.inf, 5.0], "b": [1, 2, 3, 4, 5]})
    _write_raw(ml_sandbox, "d.csv", df)
    result = preprocess_dataset("d.csv", None)
    assert result["num_records"] == 3 and result["rows_dropped"] == 2
    processed = pd.read_csv(ml_sandbox / "data" / "processed" / "d.processed.csv")
    assert np.isfinite(processed.to_numpy()).all()


def test_preprocess_strips_whitespace_from_headers(ml_sandbox):
    """CICIDS2017 ships headers like ' Label' with a leading space."""
    (ml_sandbox / "data" / "raw" / "cic.csv").write_text(" Flow Duration, Label\n10,BENIGN\n20,DDoS\n30,BENIGN\n")
    result = preprocess_dataset("cic.csv", "Label")
    assert result["feature_names"] == ["Flow Duration"]
    assert result["label_distribution"] == {"BENIGN": 2, "DDoS": 1}


def test_preprocess_keeps_the_label_column_and_distribution(ml_sandbox):
    _write_raw(ml_sandbox, "d.csv", _labeled_frame())
    result = preprocess_dataset("d.csv", "Label")
    assert result["label_column"] == "Label"
    assert result["label_distribution"] == {"benign": 190, "attack": 10}
    assert "Label" not in result["feature_names"]


def test_preprocess_errors(ml_sandbox):
    _write_raw(ml_sandbox, "d.csv", pd.DataFrame({"a": [1, 2], "txt": ["x", "y"]}))
    _write_raw(ml_sandbox, "text.csv", pd.DataFrame({"a": ["x", "y"], "b": ["p", "q"]}))
    _write_raw(ml_sandbox, "allnan.csv", pd.DataFrame({"a": [np.nan, np.nan], "b": [1.0, 2.0]}))
    with pytest.raises(DatasetError, match="Label column 'nope' not found"):
        preprocess_dataset("d.csv", "nope")
    with pytest.raises(DatasetError, match="No numeric feature columns"):
        preprocess_dataset("text.csv", None)
    with pytest.raises(DatasetError, match="No complete rows"):
        preprocess_dataset("allnan.csv", None)
    with pytest.raises(DatasetError, match="No raw file named"):
        preprocess_dataset("missing.csv", None)


def test_preprocess_reads_parquet(client, headers, ml_sandbox):
    df = _labeled_frame(40, 5)
    buf = io.BytesIO()
    df.to_parquet(buf)
    r = client.post("/api/dataset/upload", headers=headers["analyst"], files={"file": ("d.parquet", buf.getvalue())})
    assert r.status_code == 201
    r = client.post("/api/dataset/preprocess", headers=headers["analyst"], json={"raw_filename": "d.parquet", "label_column": "Label"})
    assert r.status_code == 200 and r.json()["num_records"] == 45


@pytest.mark.security
@pytest.mark.parametrize("name", ["../secret.csv", "../../etc/passwd", "/etc/passwd", "sub/x.csv", "..", "."])
def test_filenames_in_request_bodies_cannot_escape_the_data_directories(client, headers, ml_sandbox, name):
    (ml_sandbox / "secret.csv").write_text("a\n1\n")
    for path, body in [
        ("/api/dataset/preprocess", {"raw_filename": name}),
        ("/api/dataset/train", {"processed_filename": name}),
    ]:
        r = client.post(path, headers=headers["analyst"], json=body)
        assert r.status_code == 400, (path, name, r.text)
        assert "Invalid filename" in r.json()["detail"] or "No raw file" in r.json()["detail"] or "No processed file" in r.json()["detail"]


# ------------------------------------------------------------------ attack mask
def test_attack_mask_by_attack_or_by_benign_values():
    labels = pd.Series(["BENIGN", "DDoS", "PortScan", " BENIGN "])
    assert attack_mask(labels, attack_values=["DDoS", "PortScan"]).tolist() == [False, True, True, False]
    assert attack_mask(labels, benign_values=["BENIGN"]).tolist() == [False, True, True, False]


def test_attack_mask_needs_exactly_one_kind_of_value():
    labels = pd.Series(["a", "b"])
    with pytest.raises(DatasetError, match="not both"):
        attack_mask(labels, ["a"], ["b"])
    with pytest.raises(DatasetError, match="neither attack nor benign"):
        attack_mask(labels, None, None)


# ------------------------------------------------------------------- training
def _processed(sandbox, df, name="p.processed.csv"):
    path = sandbox / "data" / "processed" / name
    df.to_csv(path, index=False)
    return name


def test_unlabeled_training_reports_not_applicable_and_no_metrics(db, ml_sandbox):
    name = _processed(ml_sandbox, _labeled_frame().drop(columns="Label"))
    run = train_on_dataset(db, name, None, None)
    assert run.accuracy_status == "not_applicable"
    assert not ({"accuracy", "precision", "recall", "f1"} & set(run.evaluation))
    assert run.source == "uploaded_dataset" and run.dataset_filename == name
    assert run.num_samples == 200 and run.num_features == 2


def test_labeled_training_computes_real_consistent_metrics(db, ml_sandbox):
    name = _processed(ml_sandbox, _labeled_frame())
    run = train_on_dataset(db, name, "Label", ["attack"], contamination=0.05)
    ev = run.evaluation
    assert run.accuracy_status == "computed"
    for metric in ("accuracy", "precision", "recall", "f1"):
        assert 0.0 <= ev[metric] <= 1.0
    # the confusion matrix must add up to the data we actually trained on
    assert ev["true_positives"] + ev["false_positives"] + ev["true_negatives"] + ev["false_negatives"] == 200
    assert ev["true_positives"] + ev["false_negatives"] == 10             # real attack count
    assert ev["true_positives"] + ev["false_positives"] == run.anomalies_flagged
    assert ev["accuracy"] == pytest.approx((ev["true_positives"] + ev["true_negatives"]) / 200, abs=1e-4)
    assert ev["attack_label_values"] == ["attack"]


def test_model_finds_clearly_separated_attacks(db, ml_sandbox):
    """Quality guard, not a benchmark. Attacks sit ~9 sigma from normal traffic, so the
    model must do far better than chance (chance recall here is ~0.05). A tight cluster of
    attack rows is a little harder for an Isolation Forest to isolate than scattered
    outliers (it catches ~7 of 10 here), hence 0.5 rather than a stricter bar."""
    run = train_on_dataset(db, _processed(ml_sandbox, _labeled_frame()), "Label", ["attack"], contamination=0.05)
    assert run.evaluation["recall"] >= 0.5
    assert run.evaluation["precision"] >= 0.5


def test_training_saves_a_loadable_model_inside_the_sandbox(db, ml_sandbox):
    import joblib

    run = train_on_dataset(db, _processed(ml_sandbox, _labeled_frame().drop(columns="Label")), None, None)
    bundle = joblib.load(ml_sandbox / run.file_path)
    assert bundle["features"] == ["f1", "f2"]


def test_training_errors(db, ml_sandbox):
    labeled = _processed(ml_sandbox, _labeled_frame(), "labeled.csv")
    tiny = _processed(ml_sandbox, pd.DataFrame({"a": [1, 2, 3]}), "tiny.csv")
    with pytest.raises(DatasetError, match="No processed file named"):
        train_on_dataset(db, "ghost.csv", None, None)
    with pytest.raises(DatasetError, match="Label column 'nope' not in processed file"):
        train_on_dataset(db, labeled, "nope", ["attack"])
    with pytest.raises(DatasetError, match="neither attack nor benign"):
        train_on_dataset(db, labeled, "Label", None)
    with pytest.raises(DatasetError, match="non-numeric"):
        train_on_dataset(db, labeled, None, None)            # label column present but not declared
    with pytest.raises(DatasetError, match="need at least 5"):
        train_on_dataset(db, tiny, None, None)
    assert db.query(MLTrainingRun).count() == 0              # failed runs leave no trace


# ------------------------------------------------------------------ full API flow
def test_upload_preprocess_train_flow_over_http(client, headers, ml_sandbox, db):
    h = headers["analyst"]
    csv = _labeled_frame().to_csv(index=False).encode()
    assert client.post("/api/dataset/upload", headers=h, files={"file": ("net.csv", csv)}).status_code == 201

    pre = client.post("/api/dataset/preprocess", headers=h, json={"raw_filename": "net.csv", "label_column": "Label"})
    assert pre.status_code == 200
    processed = pre.json()["processed_filename"]

    r = client.post("/api/dataset/train", headers=h, json={
        "processed_filename": processed, "label_column": "Label", "attack_label_values": ["attack"], "contamination": 0.05})
    assert r.status_code == 200
    assert r.json()["accuracy_status"] == "computed" and r.json()["dataset_filename"] == processed

    runs = client.get("/api/dataset/runs", headers=headers["viewer"]).json()
    assert [x["dataset_filename"] for x in runs] == [processed]


def test_dataset_runs_lists_only_uploaded_dataset_runs(client, headers, ml_sandbox, db):
    _processed(ml_sandbox, _labeled_frame().drop(columns="Label"), "u.csv")
    train_on_dataset(db, "u.csv", None, None)
    from app.models.event import Event  # noqa: F401  (event-stream run below)
    from helpers import make_event
    from datetime import datetime, timezone
    for i in range(6):
        make_event(db, source="dns", event_type="dns_query", source_ip=f"10.0.0.{i}", ts=datetime(2026, 3, 2, 10, tzinfo=timezone.utc))
    client.post("/api/ml/train", headers=headers["analyst"], json={})
    assert db.query(MLTrainingRun).count() == 2
    assert [r["source"] for r in client.get("/api/dataset/runs", headers=headers["viewer"]).json()] == ["uploaded_dataset"]


def test_dataset_api_reports_user_errors_as_400(client, headers, ml_sandbox):
    h = headers["analyst"]
    assert client.post("/api/dataset/preprocess", headers=h, json={"raw_filename": "missing.csv"}).status_code == 400
    assert client.post("/api/dataset/train", headers=h, json={"processed_filename": "missing.csv"}).status_code == 400


@pytest.mark.parametrize("contamination", [0, -0.2, 0.75, 5])
def test_dataset_train_rejects_invalid_contamination(client, headers, ml_sandbox, contamination):
    _processed(ml_sandbox, _labeled_frame().drop(columns="Label"), "u.csv")
    r = client.post("/api/dataset/train", headers=headers["analyst"], json={"processed_filename": "u.csv", "contamination": contamination})
    assert r.status_code == 422
