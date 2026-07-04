from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / ".venv" / "Lib" / "site-packages"))

import pandas as pd
import yfinance as yf


ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_ID = "tcs_infy_v1_2026-07-04"
SNAPSHOT_DIR = ROOT / "data" / "snapshots" / SNAPSHOT_ID
ADJUSTED_CLOSE_CSV = SNAPSHOT_DIR / "adjusted_close.csv"
METADATA_JSON = SNAPSHOT_DIR / "metadata.json"
TICKERS = ["TCS.NS", "INFY.NS"]
START_DATE = "2018-01-01"
END_DATE_INCLUSIVE = "2026-06-30"
YFINANCE_END_EXCLUSIVE = "2026-07-01"


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


def fetch_adjusted_close() -> pd.DataFrame:
    data = yf.download(
        TICKERS,
        start=START_DATE,
        end=YFINANCE_END_EXCLUSIVE,
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
    return close


def main() -> None:
    if SNAPSHOT_DIR.exists() and any(SNAPSHOT_DIR.iterdir()):
        raise RuntimeError(f"snapshot directory already exists and is not empty: {SNAPSHOT_DIR}")

    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    close = fetch_adjusted_close()
    close.to_csv(ADJUSTED_CLOSE_CSV, float_format="%.17g")

    metadata = {
        "snapshot_id": SNAPSHOT_ID,
        "creation_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "created_by": "Codex",
        "tickers": TICKERS,
        "start_date": START_DATE,
        "end_date_inclusive": END_DATE_INCLUSIVE,
        "yfinance_download_end_exclusive": YFINANCE_END_EXCLUSIVE,
        "first_data_date": close.index.min().date().isoformat(),
        "last_data_date": close.index.max().date().isoformat(),
        "row_count": int(len(close)),
        "columns": ["date", *TICKERS],
        "source": "Yahoo Finance via yfinance.download",
        "adjustment_policy": (
            "auto_adjust=True in yfinance; saved the adjusted Close columns for TCS.NS and INFY.NS; "
            "no manual corporate-action handling."
        ),
        "yfinance_version": yf.__version__,
        "git_commit": git_commit(),
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
