# ⚙️ MLOps Batch Signal Pipeline

A reproducible, Dockerized batch pipeline that loads OHLCV market data, validates inputs, computes a rolling-mean signal, and emits structured metrics and logs.

## Pipeline

```text
data.csv
   ↓
Load + Validate
   ↓
Rolling Mean
   ↓
Binary Signal
   ↓
metrics.json + run.log
```

Signal rule:

```text
signal = 1 if close > rolling_mean else 0
```

The pipeline excludes warm-up rows that do not have a complete rolling window and produces deterministic output when run with the same configuration.

## Engineering features

- Dockerized execution
- YAML-based configuration
- Deterministic processing with a configurable seed
- Structured JSON metrics
- Detailed application logging
- Input/configuration validation
- Explicit non-zero failure behavior
- CLI interface for reproducible runs

## Project structure

```text
mlops-internship-task/
├── run.py
├── config.yaml
├── data.csv
├── requirements.txt
├── Dockerfile
├── metrics.json
├── run.log
└── README.md
```

## Run locally

```bash
pip install -r requirements.txt
python run.py --input data.csv --config config.yaml --output metrics.json --log-file run.log
```

## Run with Docker

```bash
docker build -t mlops-batch-pipeline .
docker run --rm mlops-batch-pipeline
```

Exit code `0` indicates success; exit code `1` indicates a pipeline error.

## Configuration

```yaml
seed: 42
window: 5
version: "v1"
```

## Example metrics

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

## Validation

The pipeline handles missing files, invalid CSV input, empty datasets, missing required columns, missing configuration, missing configuration keys, and invalid configuration values with structured error output and a non-zero exit status.

## Tech stack

**Python · Pandas · NumPy · PyYAML · Docker · CLI automation**

## Future improvements

- Add automated unit/integration tests
- Add GitHub Actions CI
- Add data-quality checks
- Add experiment tracking
- Add container image publishing
- Add a small monitoring/metrics dashboard
