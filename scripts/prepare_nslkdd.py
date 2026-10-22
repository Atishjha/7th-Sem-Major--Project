"""
Turn NSL-KDD's KDDTrain+.txt into a CSV the Dataset & ML page can use.

What it does:
  1. Adds the 41 standard feature names (the raw file has no header row).
  2. Drops the "difficulty" column (a score, not a feature).
  3. Collapses every attack name (neptune, smurf, ...) into one label,
     "attack", so you only have to tell the page one attack value.
  4. Keeps all normal rows and subsamples attacks to ~8% of the result.
     Isolation Forest assumes attacks are rare; the raw file is ~47%
     attacks, which makes it look bad for the wrong reason.

Usage (quote the name — it contains a '+'):
    python prepare_nslkdd.py "KDDTrain+.txt" nslkdd_binary.csv
"""
import sys

import pandas as pd

FEATURES = [
    "duration", "protocol_type", "service", "flag", "src_bytes", "dst_bytes",
    "land", "wrong_fragment", "urgent", "hot", "num_failed_logins", "logged_in",
    "num_compromised", "root_shell", "su_attempted", "num_root",
    "num_file_creations", "num_shells", "num_access_files", "num_outbound_cmds",
    "is_host_login", "is_guest_login", "count", "srv_count", "serror_rate",
    "srv_serror_rate", "rerror_rate", "srv_rerror_rate", "same_srv_rate",
    "diff_srv_rate", "srv_diff_srv_rate", "dst_host_count",
    "dst_host_srv_count", "dst_host_same_srv_rate", "dst_host_diff_srv_rate",
    "dst_host_same_src_port_rate", "dst_host_srv_diff_host_rate",
    "dst_host_serror_rate", "dst_host_srv_serror_rate", "dst_host_rerror_rate",
    "dst_host_srv_rerror_rate",
]
COLUMNS = FEATURES + ["label", "difficulty"]
ATTACK_FRACTION = 0.08


def main(src: str, dst: str) -> None:
    df = pd.read_csv(src, header=None)

    if df.shape[1] != len(COLUMNS):
        sys.exit(
            f"Expected {len(COLUMNS)} columns (41 features + label + difficulty) "
            f"but found {df.shape[1]}. This script is for the raw KDDTrain+.txt; "
            "send me the first few column names and I'll adapt it."
        )
    try:
        float(df.iloc[0, 0])
    except ValueError:
        sys.exit(
            "The first row isn't numeric, so this file probably already has a "
            "header row. This script is for the headerless KDDTrain+.txt."
        )

    df.columns = COLUMNS
    df = df.drop(columns=["difficulty"])
    df["label"] = df["label"].astype(str).str.strip().where(lambda s: s == "normal", "attack")

    normal = df[df["label"] == "normal"]
    attack = df[df["label"] == "attack"]
    n_attack = min(len(attack), int(len(normal) * ATTACK_FRACTION / (1 - ATTACK_FRACTION)))
    out = pd.concat([normal, attack.sample(n=n_attack, random_state=42)])
    out = out.sample(frac=1, random_state=42)
    out.to_csv(dst, index=False)

    share = n_attack / len(out)
    print(f"Wrote {dst}")
    print(f"  normal: {len(normal)}   attack: {n_attack}   (attack share {share:.1%})")
    print(f"  from {len(attack)} attack rows in the original file")
    print(f"  suggested contamination: {share:.2f}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
