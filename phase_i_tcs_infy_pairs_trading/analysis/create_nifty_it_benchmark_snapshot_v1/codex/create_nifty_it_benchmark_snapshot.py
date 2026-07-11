from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Adjust root according to phase_i_tcs_infy_pairs_trading/analysis/create_nifty_it_benchmark_snapshot_v1/codex
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / ".venv" / "Lib" / "site-packages"))

import pandas as pd
import yfinance as yf


SNAPSHOT_ID = "nifty_it_benchmark_v1_2026-07-11"
SNAPSHOT_DIR = ROOT / "data" / "snapshots" / SNAPSHOT_ID
OHLCV_CSV = SNAPSHOT_DIR / "ohlcv.csv"
METADATA_JSON = SNAPSHOT_DIR / "metadata.json"
TICKERS = ["^CNXIT", "ITBEES.NS"]
START_DATE = "2018-01-01"
OHLCV_FIELDS = ("open", "high", "low", "close", "volume")
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


def fetch_ohlcv() -> tuple[pd.DataFrame, str, dict[str, str]]:
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

    missing_tickers: dict[str, list[str]] = {}
    for field in ["Open", "High", "Low", "Close", "Volume"]:
        if field not in data.columns.get_level_values(0):
            raise RuntimeError(f"missing yfinance field: {field}")
        field_missing = set(TICKERS) - set(data[field].columns)
        if field_missing:
            missing_tickers[field] = sorted(field_missing)
    if missing_tickers:
        raise RuntimeError(f"missing ticker columns: {missing_tickers}")

    # Explicit acceptance check for ^CNXIT volume
    cnxit_vol = data["Volume"]["^CNXIT"].dropna()
    cnxit_all_zero_or_null = len(cnxit_vol) == 0 or (cnxit_vol == 0).all()
    
    validation_notes = {}
    if cnxit_all_zero_or_null:
        validation_notes["cnxit_volume_status"] = "^CNXIT volume is all-zero/all-null. Falling back to ITBEES.NS for volume."
        data.loc[:, ("Volume", "^CNXIT")] = data["Volume"]["ITBEES.NS"]
    else:
        validation_notes["cnxit_volume_status"] = "^CNXIT volume is NOT all-zero/all-null (usable). No fallback needed."
        
    # Check ITBEES.NS inception date
    itbees_prices = data["Close"]["ITBEES.NS"].dropna()
    itbees_inception = itbees_prices.index.min().date().isoformat() if not itbees_prices.empty else None
    
    if itbees_inception and itbees_inception > START_DATE:
        validation_notes["itbees_inception_date"] = f"ITBEES.NS data only begins on {itbees_inception}. Dates before this are flagged as pre-inception rather than truncated silently."

    parts: list[pd.DataFrame] = []
    for ticker in TICKERS:
        part = pd.DataFrame(
            {
                "date": data.index,
                "ticker": ticker,
                "open": data["Open"][ticker].to_numpy(dtype=float),
                "high": data["High"][ticker].to_numpy(dtype=float),
                "low": data["Low"][ticker].to_numpy(dtype=float),
                "close": data["Close"][ticker].to_numpy(dtype=float),
                "volume": data["Volume"][ticker].to_numpy(dtype=float),
            }
        )
        parts.append(part)

    long_df = pd.concat(parts, ignore_index=True)
    long_df["date"] = pd.to_datetime(long_df["date"])

    # Drop rows where price is incomplete for that specific ticker on that date,
    # rather than dropping the whole date for both tickers. This avoids silently
    # truncating ^CNXIT data prior to ITBEES.NS inception.
    long_df = long_df.dropna(subset=["open", "high", "low", "close"]).copy()
    long_df["volume"] = long_df["volume"].fillna(0.0)
    long_df = long_df.sort_values(["date", "ticker"]).reset_index(drop=True)

    if long_df.empty:
        raise RuntimeError("ohlcv dataframe is empty after dropping incomplete price rows")

    return long_df, download_end_exclusive, validation_notes


def main() -> None:
    if SNAPSHOT_DIR.exists() and any(SNAPSHOT_DIR.iterdir()):
        raise RuntimeError(f"snapshot directory already exists and is not empty: {SNAPSHOT_DIR}")

    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    ohlcv, download_end_exclusive, validation_notes = fetch_ohlcv()
    ohlcv.to_csv(OHLCV_CSV, index=False, float_format="%.17g")

    first_data_date = ohlcv["date"].min().date().isoformat()
    last_data_date = ohlcv["date"].max().date().isoformat()

    metadata = {
        "snapshot_id": SNAPSHOT_ID,
        "creation_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "created_by": "Codex",
        "tickers": TICKERS,
        "start_date": START_DATE,
        "end_date_inclusive": last_data_date,
        "yfinance_download_end_exclusive": download_end_exclusive,
        "first_data_date": first_data_date,
        "last_data_date": last_data_date,
        "row_count": int(len(ohlcv)),
        "columns": ["date", "ticker", *OHLCV_FIELDS],
        "source": "Yahoo Finance via yfinance.download",
        "adjustment_policy": (
            "auto_adjust=True in yfinance; saved adjusted Open, High, Low, and Close for ^CNXIT and "
            "ITBEES.NS; no manual corporate-action handling."
        ),
        "validation_notes": validation_notes,
        "yfinance_version": yf.__version__,
        "git_commit": PENDING_COMMIT,
        "generated_by_script": str(Path(__file__).resolve()),
        "files": {
            OHLCV_CSV.name: {
                "path": str(OHLCV_CSV.relative_to(ROOT)),
                "sha256": file_sha256(OHLCV_CSV),
            }
        },
    }
    METADATA_JSON.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
