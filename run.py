"""
MLOps Batch Job — Rolling Mean Signal Pipeline
Usage: python run.py --input data.csv --config config.yaml --output metrics.json --log-file run.log
"""

import argparse
import json
import logging
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import yaml


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(description="MLOps batch signal pipeline")
    parser.add_argument("--input",    required=True, help="Path to input CSV file")
    parser.add_argument("--config",   required=True, help="Path to YAML config file")
    parser.add_argument("--output",   required=True, help="Path to output metrics JSON file")
    parser.add_argument("--log-file", required=True, dest="log_file", help="Path to log file")
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

def setup_logging(log_file: str) -> logging.Logger:
    logger = logging.getLogger("mlops_pipeline")
    logger.setLevel(logging.DEBUG)

    fmt = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S"
    )

    # File handler — full detail
    fh = logging.FileHandler(log_file, mode="w")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)

    # Console handler — INFO and above
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)

    logger.addHandler(fh)
    logger.addHandler(ch)
    return logger


# ---------------------------------------------------------------------------
# Config loading + validation
# ---------------------------------------------------------------------------

REQUIRED_CONFIG_KEYS = {"seed", "window", "version"}

def load_config(config_path: str, logger: logging.Logger) -> dict:
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(path, "r") as f:
        config = yaml.safe_load(f)

    if not isinstance(config, dict):
        raise ValueError("Config file is empty or not a valid YAML mapping")

    missing = REQUIRED_CONFIG_KEYS - config.keys()
    if missing:
        raise ValueError(f"Config missing required keys: {missing}")

    # Type checks
    if not isinstance(config["seed"], int):
        raise ValueError(f"Config 'seed' must be an integer, got: {type(config['seed'])}")
    if not isinstance(config["window"], int) or config["window"] < 1:
        raise ValueError(f"Config 'window' must be a positive integer, got: {config['window']}")
    if not isinstance(config["version"], str):
        raise ValueError(f"Config 'version' must be a string, got: {type(config['version'])}")

    logger.info(f"Config loaded — seed={config['seed']}, window={config['window']}, version={config['version']}")
    return config


# ---------------------------------------------------------------------------
# Dataset loading + validation
# ---------------------------------------------------------------------------

def load_dataset(input_path: str, logger: logging.Logger) -> pd.DataFrame:
    path = Path(input_path)
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    try:
        df = pd.read_csv(path)
    except Exception as exc:
        raise ValueError(f"Failed to parse CSV: {exc}") from exc

    if df.empty:
        raise ValueError("Input CSV is empty")

    if "close" not in df.columns:
        raise ValueError(f"Required column 'close' not found. Columns present: {list(df.columns)}")

    if df["close"].isnull().all():
        raise ValueError("Column 'close' contains only null values")

    logger.info(f"Dataset loaded — {len(df)} rows, columns: {list(df.columns)}")
    return df


# ---------------------------------------------------------------------------
# Signal computation
# ---------------------------------------------------------------------------

def compute_signals(df: pd.DataFrame, window: int, logger: logging.Logger) -> pd.DataFrame:
    logger.info(f"Computing rolling mean with window={window}")

    # Rolling mean — first (window-1) rows will be NaN; we exclude them from signal
    df = df.copy()
    df["rolling_mean"] = df["close"].rolling(window=window, min_periods=window).mean()

    valid_mask = df["rolling_mean"].notna()
    excluded = (~valid_mask).sum()
    logger.debug(f"Rolling mean computed — {excluded} leading rows excluded (NaN, window warm-up)")

    logger.info("Generating binary signal (1 if close > rolling_mean, else 0)")
    # Only compute signal for rows where rolling_mean is available
    df["signal"] = np.nan
    df.loc[valid_mask, "signal"] = (
        df.loc[valid_mask, "close"] > df.loc[valid_mask, "rolling_mean"]
    ).astype(int)

    signal_rows = valid_mask.sum()
    logger.info(f"Signal generated for {signal_rows} rows ({excluded} rows excluded from signal due to warm-up)")
    return df


# ---------------------------------------------------------------------------
# Metrics writing
# ---------------------------------------------------------------------------

def write_metrics(output_path: str, payload: dict, logger: logging.Logger):
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w") as f:
        json.dump(payload, f, indent=2)
    logger.info(f"Metrics written to {output_path}")


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def main():
    args = parse_args()
    logger = setup_logging(args.log_file)

    start_time = time.time()
    logger.info("=" * 60)
    logger.info("MLOps Batch Pipeline — JOB START")
    logger.info(f"  input   : {args.input}")
    logger.info(f"  config  : {args.config}")
    logger.info(f"  output  : {args.output}")
    logger.info(f"  log-file: {args.log_file}")
    logger.info("=" * 60)

    version = "unknown"

    try:
        # ── Step 1: Load + validate config ──────────────────────────────
        logger.info("Step 1/4 — Loading config")
        config = load_config(args.config, logger)
        version = config["version"]

        # Set seed for reproducibility
        np.random.seed(config["seed"])
        logger.info(f"Random seed set to {config['seed']}")

        # ── Step 2: Load + validate dataset ─────────────────────────────
        logger.info("Step 2/4 — Loading dataset")
        df = load_dataset(args.input, logger)

        # ── Step 3: Rolling mean + signal ───────────────────────────────
        logger.info("Step 3/4 — Computing rolling mean and signal")
        df = compute_signals(df, config["window"], logger)

        # ── Step 4: Compute metrics ──────────────────────────────────────
        logger.info("Step 4/4 — Computing metrics")

        valid_signals = df["signal"].dropna()
        rows_processed = len(valid_signals)
        signal_rate = round(float(valid_signals.mean()), 4)

        elapsed_ms = int((time.time() - start_time) * 1000)

        metrics = {
            "version":        version,
            "rows_processed": rows_processed,
            "metric":         "signal_rate",
            "value":          signal_rate,
            "latency_ms":     elapsed_ms,
            "seed":           config["seed"],
            "status":         "success",
        }

        logger.info(f"Metrics summary — rows_processed={rows_processed}, signal_rate={signal_rate}, latency_ms={elapsed_ms}ms")
        write_metrics(args.output, metrics, logger)

        # Print final metrics to stdout (required by Docker spec)
        print(json.dumps(metrics, indent=2))

        logger.info("JOB COMPLETE — status=success")
        logger.info("=" * 60)
        sys.exit(0)

    except Exception as exc:
        elapsed_ms = int((time.time() - start_time) * 1000)
        error_msg = str(exc)
        logger.error(f"Pipeline failed: {error_msg}", exc_info=True)

        error_payload = {
            "version":       version,
            "status":        "error",
            "error_message": error_msg,
        }

        try:
            write_metrics(args.output, error_payload, logger)
        except Exception as write_exc:
            logger.error(f"Could not write error metrics: {write_exc}")

        print(json.dumps(error_payload, indent=2))
        logger.info("JOB COMPLETE — status=error")
        logger.info("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    main()
