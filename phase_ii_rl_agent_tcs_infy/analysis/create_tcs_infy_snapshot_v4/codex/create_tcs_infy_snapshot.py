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


SNAPSHOT_ID = "tcs_infy_v4_2026-07-13"
SNAPSHOT_DIR = ROOT / "data" / "snapshots" / SNAPSHOT_ID
OHLCV_CSV = SNAPSHOT_DIR / "ohlcv.csv"
METADATA_JSON = SNAPSHOT_DIR / "metadata.json"
TICKERS = ["TCS.NS", "INFY.NS"]
START_DATE = "2017-10-01"
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


def fetch_ohlcv() -> tuple[pd.DataFrame, str]:
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

    price_complete = long_df.groupby("date")[list(OHLCV_FIELDS[:-1])].apply(
        lambda frame: frame.notna().all().all()
    )
    valid_dates = price_complete[price_complete].index
    long_df = long_df[long_df["date"].isin(valid_dates)].copy()
    long_df["volume"] = long_df["volume"].fillna(0.0)
    long_df = long_df.sort_values(["date", "ticker"]).reset_index(drop=True)

    if long_df.empty:
        raise RuntimeError("ohlcv dataframe is empty after dropping incomplete price rows")

    return long_df, download_end_exclusive


def main() -> None:
    if SNAPSHOT_DIR.exists() and any(SNAPSHOT_DIR.iterdir()):
        raise RuntimeError(f"snapshot directory already exists and is not empty: {SNAPSHOT_DIR}")

    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    ohlcv, download_end_exclusive = fetch_ohlcv()
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
            "auto_adjust=True in yfinance; saved adjusted Open, High, Low, and Close for TCS.NS and "
            "INFY.NS; no manual corporate-action handling."
        ),
        "volume_policy": (
            "Volume is as reported by Yahoo Finance via yfinance and is not split-adjusted. "
            "Open/High/Low/Close use auto_adjust=True (split- and dividend-adjusted). "
            "Volume therefore has a real discontinuity around any stock split in the 2018-2026 window "
            "and must not be treated as comparable to the adjusted price fields without explicit handling. "
            "Note: TCS's 2018-05-31 split and INFY's 2018-09-05 bonus issue are now both inside the "
            "estimation history."
        ),
        "purpose": (
            "These snapshots extend coverage backward specifically to support the eg_p_trend feature's "
            "lookback requirement — not a re-basing of the project's primary analysis window. v4's version "
            "number is sequential in the global tcs_infy snapshot family; it belongs to the full OHLCV lineage."
        ),
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
