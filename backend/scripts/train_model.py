"""
Train and evaluate an Isolation Forest on a dataset from the command line.

This is the CLI twin of the Dataset & ML page, meant for the datasets that
are too big or awkward for a browser upload (NSL-KDD, UNSW-NB15,
CICIDS2017). The run is saved to the same table the page reads, so it shows
up in the page's training history, and it is audit-logged as user "cli".

Run it from the PROJECT ROOT, with the dataset already copied into data/raw/.
Because this runs on your own machine rather than inside Docker, point it at
the database port Docker publishes before you run it:

    PowerShell:  $env:DATABASE_URL="postgresql+psycopg2://socuser:socpassword@localhost:5432/soc_db"
    bash:        export DATABASE_URL=postgresql+psycopg2://socuser:socpassword@localhost:5432/soc_db

Examples (the file name is the bare name of a file inside data/raw/):

    NSL-KDD, after scripts/prepare_nslkdd.py has produced nslkdd_binary.csv:
      python scripts/train_model.py nslkdd_binary.csv --label-column label --attack-values attack --contamination 0.08

    UNSW-NB15 (the training-set CSV; label is 0/1, id is a row number):
      python scripts/train_model.py UNSW_NB15_training-set.csv --label-column label --attack-values 1 --drop-columns id --attack-fraction 0.08 --contamination 0.08

    CICIDS2017 (one day's CSV; benign rows are labelled BENIGN):
      python scripts/train_model.py Tuesday-WorkingHours.pcap_ISCX.csv --label-column Label --benign-values BENIGN --max-rows 200000 --contamination 0.03

With no --label-column the run is unsupervised and reports "Accuracy: Not
Applicable" instead of inventing a number.
"""

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[1] / "backend"))

from sqlalchemy import text  # noqa: E402
from sqlalchemy.exc import OperationalError  # noqa: E402

from app.database.session import SessionLocal  # noqa: E402
from app.ml.dataset import (  # noqa: E402
    RAW_DIR,
    DatasetError,
    attack_mask,
    load_raw_clean,
    preprocess_dataset,
    train_on_dataset,
)
from app.services.audit import log_action  # noqa: E402


def _csv_list(value: str | None) -> list[str] | None:
    if not value:
        return None
    return [v.strip() for v in value.split(",") if v.strip()]


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Train + evaluate an Isolation Forest on a file in data/raw/.",
        epilog="See the top of this file for per-dataset examples.",
    )
    p.add_argument("file", help="bare file name inside data/raw/ (.csv or .parquet)")
    p.add_argument("--label-column", help="column holding the attack/benign label; omit for an unsupervised run")
    group = p.add_mutually_exclusive_group()
    group.add_argument("--attack-values", type=_csv_list, help="label value(s) that mean 'attack', comma-separated")
    group.add_argument(
        "--benign-values", type=_csv_list,
        help="label value(s) that mean 'benign', comma-separated; every other value counts as an attack",
    )
    p.add_argument("--drop-columns", type=_csv_list, help="numeric columns to ignore, e.g. an 'id' row number")
    p.add_argument(
        "--attack-fraction", type=float,
        help="subsample attack rows to about this share of the data (0-1). Isolation Forest assumes "
             "attacks are rare; use this when a file is mostly attacks",
    )
    p.add_argument("--max-rows", type=int, help="randomly cap the number of rows (speed / memory)")
    p.add_argument("--contamination", type=float, default=0.05, help="expected anomaly share (default 0.05)")
    p.add_argument("--seed", type=int, default=42, help="random seed for sampling (default 42)")
    return p


def _check_database() -> None:
    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
    except OperationalError:
        sys.exit(
            "Could not connect to the database. Is Docker running (docker compose up), and did you set "
            "DATABASE_URL to use localhost rather than the 'postgres' hostname? See the top of this file."
        )
    finally:
        db.close()


def prepare_sample(args: argparse.Namespace) -> str:
    """Optionally subsample; returns the name of the raw file to preprocess."""
    if args.attack_fraction is None and args.max_rows is None:
        return args.file
    if not args.label_column:
        raise DatasetError("--attack-fraction and --max-rows need --label-column (to know which rows are attacks).")
    if args.attack_fraction is not None and not 0 < args.attack_fraction < 1:
        raise DatasetError("--attack-fraction must be between 0 and 1, e.g. 0.08.")

    df = load_raw_clean(args.file)
    label_column = args.label_column.strip()
    if label_column not in df.columns:
        raise DatasetError(f"Label column '{label_column}' not found. Columns: {list(df.columns)}")

    mask = attack_mask(df[label_column], args.attack_values, args.benign_values)
    normal, attack = df[~mask], df[mask]
    print(f"Read {len(df):,} rows: {len(normal):,} normal, {len(attack):,} attack ({len(attack) / len(df):.1%})")

    if args.attack_fraction is not None:
        f = args.attack_fraction
        n_attack = min(len(attack), int(len(normal) * f / (1 - f)))
        attack = attack.sample(n=n_attack, random_state=args.seed)
    out = pd.concat([normal, attack])
    if args.max_rows and len(out) > args.max_rows:
        out = out.sample(n=args.max_rows, random_state=args.seed)
    out = out.sample(frac=1, random_state=args.seed)

    sampled_name = f"{Path(args.file).stem}.sampled.csv"
    out.to_csv(RAW_DIR / sampled_name, index=False)
    share = float(mask.loc[out.index].mean())
    print(f"Sampled to {len(out):,} rows ({share:.1%} attack) -> data/raw/{sampled_name}")
    return sampled_name


def main() -> None:
    args = build_parser().parse_args()
    args.file = Path(args.file).name  # only bare names inside data/raw/ are allowed

    try:
        _check_database()
        raw_name = prepare_sample(args)
        pre = preprocess_dataset(raw_name, args.label_column, args.drop_columns)

        print(f"\nPreprocessed -> data/processed/{pre['processed_filename']}")
        print(f"  {pre['num_records']:,} rows kept ({pre['rows_dropped']:,} dropped for missing/infinite values)")
        print(f"  {pre['num_features']} numeric features")
        if pre["dropped_columns"]:
            print(f"  ignored columns: {', '.join(pre['dropped_columns'])}")
        if pre["label_distribution"]:
            print(f"  label distribution: {pre['label_distribution']}")

        print("\nTraining (this can take a minute on large files)...")
        db = SessionLocal()
        try:
            run = train_on_dataset(
                db, pre["processed_filename"], args.label_column, args.attack_values,
                args.contamination, benign_label_values=args.benign_values,
            )
            # Copy out everything we print: log_action commits (which expires `run`)
            # and the session closes below, after which `run` can't be read.
            result = {
                "model_version": run.model_version,
                "num_samples": run.num_samples,
                "num_features": run.num_features,
                "anomalies_flagged": run.anomalies_flagged,
                "accuracy_status": run.accuracy_status,
                "evaluation": dict(run.evaluation),
            }
            log_action(
                db, username="cli",
                action=f"Trained ML model on dataset '{pre['processed_filename']}' (command line)",
                resource_type="dataset", resource_id=pre["processed_filename"],
                new_value={"model_version": result["model_version"],
                           "accuracy_status": result["accuracy_status"],
                           "evaluation": result["evaluation"]},
            )
        finally:
            db.close()
    except DatasetError as e:
        sys.exit(f"Error: {e}")

    ev = result["evaluation"]
    print(f"\nModel version: {result['model_version']}")
    print(f"Samples: {result['num_samples']:,}   Features: {result['num_features']}   "
          f"Flagged as anomalous: {result['anomalies_flagged']:,}")
    if result["accuracy_status"] == "computed":
        print(f"Accuracy {ev['accuracy']}   Precision {ev['precision']}   Recall {ev['recall']}   F1 {ev['f1']}")
        print(f"Confusion matrix: TP={ev['true_positives']:,}  FP={ev['false_positives']:,}  "
              f"TN={ev['true_negatives']:,}  FN={ev['false_negatives']:,}")
        print(f"\nNote: contamination was {args.contamination}. If you chose it because you know the attack share, "
              "that uses the labels to help the model, which flatters the scores — say so when you report them.")
        print("Note: the model is evaluated on the same rows it was fitted on (no held-out test split).")
    else:
        print("Accuracy: Not Applicable (no label column was given).")
    print("\nSaved. It now appears under 'Training history' on the Dataset & ML page.")


if __name__ == "__main__":
    main()
