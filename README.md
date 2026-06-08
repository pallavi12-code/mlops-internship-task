# MLOps Batch Signal Pipeline

A minimal MLOps-style batch job that loads OHLCV market data, computes a rolling-mean trading signal, and writes structured metrics + logs — fully Dockerized for reproducible, one-command execution.

---

## Project Structure

```
.
├── run.py           # Main pipeline script
├── config.yaml      # Job configuration (seed, window, version)
├── data.csv         # 10,000-row OHLCV dataset
├── requirements.txt # Python dependencies
├── Dockerfile       # Container definition
├── metrics.json     # Sample output from a successful run
├── run.log          # Sample log from a successful run
└── README.md        # This file
```

---

## What It Does

```
data.csv  →  load + validate  →  rolling mean (window=5)  →  binary signal  →  metrics.json + run.log
```

- **Signal rule:** `signal = 1` if `close > rolling_mean`, else `0`
- **Warm-up rows:** The first `window - 1` rows have no rolling mean (NaN) and are excluded from signal computation and `rows_processed`
- **Determinism:** All runs with the same config produce identical output

---

## Local Run

### Prerequisites
```bash
pip install -r requirements.txt
```

### Run the pipeline
```bash
python run.py \
  --input    data.csv \
  --config   config.yaml \
  --output   metrics.json \
  --log-file run.log
```

The final metrics JSON is printed to stdout and also written to `metrics.json`.

---

## Docker Build & Run

### Build
```bash
docker build -t mlops-task .
```

### Run
```bash
docker run --rm mlops-task
```

- Exit code `0` → success  
- Exit code `1` → pipeline error (error payload still written to `metrics.json`)

---

## Configuration (`config.yaml`)

| Key       | Type    | Description                              |
|-----------|---------|------------------------------------------|
| `seed`    | int     | NumPy random seed for reproducibility    |
| `window`  | int     | Rolling mean window size (rows)          |
| `version` | string  | Pipeline version tag in output metrics   |

```yaml
seed: 42
window: 5
version: "v1"
```

---

## Output: `metrics.json`

### Success
```json
{
  "version": "v1",
  "rows_processed": 9996,
  "metric": "signal_rate",
  "value": 0.5091,
  "latency_ms": 11,
  "seed": 42,
  "status": "success"
}
```

> `rows_processed` = total rows minus the `window - 1` warm-up rows excluded from signal computation.

### Error
```json
{
  "version": "v1",
  "status": "error",
  "error_message": "Required column 'close' not found. Columns present: ['open', 'high']"
}
```

---

## Logging (`run.log`)

Logs include:
- Job start timestamp and CLI arguments
- Config loaded and validated (seed / window / version)
- Rows loaded and column validation
- Rolling mean computation and warm-up exclusions
- Signal generation summary
- Final metrics
- Job end status and any exceptions

---

## CLI Reference

```
python run.py --input <csv> --config <yaml> --output <json> --log-file <log>

  --input      Path to input OHLCV CSV file (must contain 'close' column)
  --config     Path to YAML config file (seed, window, version required)
  --output     Path to write metrics JSON output
  --log-file   Path to write detailed log file
```

---

## Validation & Error Handling

The pipeline handles the following cases and writes an error `metrics.json` for each:

| Case | Behavior |
|---|---|
| Input file not found | Error + non-zero exit |
| Invalid / unparseable CSV | Error + non-zero exit |
| Empty CSV | Error + non-zero exit |
| Missing `close` column | Error + non-zero exit |
| Config file not found | Error + non-zero exit |
| Missing required config keys | Error + non-zero exit |
| Invalid config value types | Error + non-zero exit |
