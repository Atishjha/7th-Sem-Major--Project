# Machine learning and datasets

Two entry points feed the same model type (an Isolation Forest), and both follow one rule:
**an accuracy number is reported only when real labels exist.**

## 1. Live event stream (ML Anomaly Detection page)

Trains on the events already in the database.

* **Windows.** Events are grouped by source IP and a time window (default 5 minutes).
* **Ten features per window:** `login_frequency`, `failed_login_count`, `request_frequency`, `bytes_sent`,
  `bytes_received`, `unique_destination_count`, `dns_request_count`, `connection_count`, `process_frequency`,
  `login_hour`. (`bytes_received` is always 0: the simulated telemetry has no such field, and it is not fabricated.)
* **Model.** `StandardScaler` then `IsolationForest` (200 trees, fixed seed). Scores are normalised to 0-1;
  the top `contamination` fraction (default 5%) is flagged anomalous.
* **Minimum data.** At least 5 windows; otherwise the API answers 400 with a clear message.
* **Output.** A training run and one prediction per window. The highest anomaly score for an incident's source IP
  becomes the *ML anomaly* factor of its risk score.
* **No labels, so no accuracy.** The run records `accuracy_status = "not_applicable"`.

API parameters are validated: `contamination` must be in (0, 0.5] and `window_minutes` in 1-1440 (otherwise 422).

## 2. Uploaded datasets (Dataset & ML page)

For public datasets such as NSL-KDD or UNSW-NB15.

1. **Upload** a `.csv` or `.parquet` file.
2. **Preprocess.** Non-numeric columns are dropped (and reported), rows with missing or infinite values are
   dropped (and counted), header whitespace is stripped (CICIDS2017-style `" Label"`), and an optional label column
   is kept aside with its distribution.
3. **Train** on the processed file. If you declare which label values mean *attack* (or which mean *benign*),
   real accuracy, precision, recall, F1 and a confusion matrix are computed against those labels. If not, the run
   says accuracy is not applicable.

The confusion matrix always adds up to the rows trained on, and the attack count is the true number from the file.

### Large files: command line

Browser uploads are awkward for multi-hundred-MB files, so there is a script (run from the project root):

```powershell
# NSL-KDD: add headers, collapse attack names to one label, subsample attacks to ~8%
python scripts/prepare_nslkdd.py "KDDTrain+.txt" nslkdd_binary.csv

# Train and record the run (appears on the Dataset & ML page)
python scripts/train_model.py nslkdd_binary.csv --label-column label --attack-values attack --contamination 0.08
```

`prepare_nslkdd.py` subsamples attacks because Isolation Forest assumes anomalies are rare; the raw NSL-KDD file is
roughly half attacks, which would make the model look bad for the wrong reason. Run the commands with
`DATABASE_URL` pointing at your database (see [troubleshooting](troubleshooting.md)).

### What to expect

Isolation Forest is *unsupervised*: it flags what is unusual, not what is malicious. Tightly clustered attacks
are harder for it to isolate than scattered outliers, so recall on a clustered attack class is typically
moderate, not perfect. Report the numbers the page shows for your run and explain them in this light; do not quote
figures from anywhere else.

## Where files live

`data/raw/`, `data/processed/` and `ml/models/` (git-ignored; created on first use). Under Docker they are bind-mounted
from the project root so uploads and trained models survive container rebuilds.
