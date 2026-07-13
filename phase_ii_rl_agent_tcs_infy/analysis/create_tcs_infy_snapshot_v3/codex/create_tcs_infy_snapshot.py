from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / ".venv" / "Lib" / "site-packages"))

import pandas as pd
import yfinance as yf


SNAPSHOT_ID = "tcs_infy_v3_2026-07-13"
SNAPSHOT_DIR = ROOT / "data" / "snapshots" / SNAPSHOT_ID
ADJUSTED_CLOSE_CSV = SNAPSHOT_DIR / "adjusted_close.csv"
METADATA_JSON = SNAPSHOT_DIR / "metadata.json"
TICKERS = ["TCS.NS", "INFY.NS"]
START_DATE = "2017-10-01"
PENDING_COMMIT = "PENDING_POST_OUTPUT_COMMIT"


def git_commit() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=True,
        )
        return result.stdout.strip()
    except Exception:
        return "unavailable_no_commit_or_git_error"


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def yfinance_end_exclusive() -> str:
    """yfinance end is exclusive; use tomorrow UTC to include today's bar if available."""
    return (datetime.now(timezone.utc).date() + timedelta(days=1)).isoformat()


def fetch_adjusted_close() -> tuple[pd.DataFrame, str]:
    download_end_exclusive = yfinance_end_exclusive()
    data = yf.download(
        TICKERS,
        start=START_DATE,
        end=download_end_exclusive,
        auto_adjust=True,
        progress=False,
        threads=False,
    )
    if data.empty:
        raise RuntimeError("yfinance returned an empty dataframe")
    if not isinstance(data.columns, pd.MultiIndex):
        raise RuntimeError("expected yfinance multi-index columns for two tickers")
    close = data["Close"].copy()
    missing = set(TICKERS) - set(close.columns)
    if missing:
        raise RuntimeError(f"missing adjusted close columns: {sorted(missing)}")
    close = close[TICKERS].dropna()
    if close.empty:
        raise RuntimeError("adjusted close dataframe is empty after dropping missing values")
    close.index.name = "date"
    return close, download_end_exclusive


def main() -> None:
    if SNAPSHOT_DIR.exists() and any(SNAPSHOT_DIR.iterdir()):
        raise RuntimeError(f"snapshot directory already exists and is not empty: {SNAPSHOT_DIR}")

    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    close, download_end_exclusive = fetch_adjusted_close()
    close.to_csv(ADJUSTED_CLOSE_CSV, float_format="%.17g")

    metadata = {
        "snapshot_id": SNAPSHOT_ID,
        "creation_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "created_by": "Codex",
        "tickers": TICKERS,
        "start_date": START_DATE,
        "end_date_inclusive": close.index.max().date().isoformat(),
        "yfinance_download_end_exclusive": download_end_exclusive,
        "first_data_date": close.index.min().date().isoformat(),
        "last_data_date": close.index.max().date().isoformat(),
        "row_count": int(len(close)),
        "columns": ["date", *TICKERS],
        "source": "Yahoo Finance via yfinance.download",
        "adjustment_policy": (
            "auto_adjust=True in yfinance; saved the adjusted Close columns for TCS.NS and INFY.NS; "
            "no manual corporate-action handling."
        ),
        "purpose": (
            "These snapshots extend coverage backward specifically to support the eg_p_trend feature's "
            "lookback requirement — not a re-basing of the project's primary analysis window. v3's version "
            "number is sequential in the global tcs_infy snapshot family; it belongs to the close-only lineage."
        ),
        "yfinance_version": yf.__version__,
        "git_commit": PENDING_COMMIT,
        "generated_by_script": str(Path(__file__).resolve()),
        "files": {
            ADJUSTED_CLOSE_CSV.name: {
                "path": str(ADJUSTED_CLOSE_CSV.relative_to(ROOT)),
                "sha256": file_sha256(ADJUSTED_CLOSE_CSV),
            }
        },
    }
    METADATA_JSON.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
