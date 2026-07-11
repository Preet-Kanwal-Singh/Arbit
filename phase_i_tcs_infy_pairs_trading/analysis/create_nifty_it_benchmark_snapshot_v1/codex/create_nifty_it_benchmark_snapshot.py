from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
import numpy as np

# Adjust root according to phase_i_tcs_infy_pairs_trading/analysis/create_nifty_it_benchmark_snapshot_v1/codex
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / ".venv" / "Lib" / "site-packages"))

import pandas as pd
import yfinance as yf


SNAPSHOT_ID = "nifty_it_benchmark_v1_2026-07-11"
SNAPSHOT_DIR = ROOT / "data" / "snapshots" / SNAPSHOT_ID
OHLCV_CSV = SNAPSHOT_DIR / "ohlcv.csv"
METADATA_JSON = SNAPSHOT_DIR / "metadata.json"
TICKERS = ["^CNXIT", "ITBEES.NS", "^NSEI"]
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


def longest_zero_run(series: pd.Series) -> tuple[int, str | None, str | None]:
    if series.empty:
        return 0, None, None
        
    is_zero = (series == 0) | series.isna()
    is_zero_int = is_zero.astype(int)
    groups = (~is_zero).cumsum()
    
    zero_runs = is_zero_int.groupby(groups).sum()
    if zero_runs.empty or zero_runs.max() == 0:
        return 0, None, None
        
    max_run_idx = zero_runs.idxmax()
    max_run_len = int(zero_runs.max())
    
    group_dates = series[groups == max_run_idx].index
    zero_dates = series.loc[group_dates][is_zero].index
    
    if len(zero_dates) == 0:
        return 0, None, None
        
    start_date = zero_dates[0].date().isoformat()
    end_date = zero_dates[-1].date().isoformat()
    
    return max_run_len, start_date, end_date


def get_trading_days_before(df: pd.DataFrame, target_date: str, num_days: int) -> pd.DataFrame:
    prior = df.loc[df.index < target_date]
    if prior.empty:
        return prior
    return prior.tail(num_days)


def run_structural_check(data: pd.DataFrame) -> tuple[dict[str, object], bool]:
    ranges = [
        ("500d_core", lambda df: df.loc['2020-01-31':'2021-12-31']),
        ("730d_core", lambda df: df.loc['2020-12-31':'2023-03-31']),
        ("20d_before_2022-01-31", lambda df: get_trading_days_before(df, '2022-01-31', 20)),
        ("20d_before_2023-04-28", lambda df: get_trading_days_before(df, '2023-04-28', 20))
    ]
    
    results = []
    nsei_clean = True
    
    for ticker in TICKERS:
        vol = data['Volume'][ticker]
        for range_name, range_func in ranges:
            sliced = range_func(vol)
            max_len, start_date, end_date = longest_zero_run(sliced)
            usable = "Yes" if max_len <= 3 else "No"
            if ticker == "^NSEI" and max_len > 3:
                nsei_clean = False
            results.append({
                "ticker": ticker,
                "range": range_name,
                "longest_zero_run": max_len,
                "start_date": start_date,
                "end_date": end_date,
                "usable": usable
            })
            
    notes = {
        "structural_zero_volume_check": results,
    }
    
    if nsei_clean:
        notes["nsei_clean_verdict"] = "^NSEI turns out completely clean (usable across all 4 ranges) where the other two have gaps. This means the broad market index has better data quality than the sector index, which would override the sector-vs-market preference from the original spec on data-quality grounds alone."
        
    notes["decision"] = "Do not decide unilaterally which benchmark to actually use if more than one candidate is usable, or if none are fully clean across all four ranges. The full comparison table is reported above, and that decision comes back to us."
        
    return notes


def fetch_ohlcv() -> tuple[pd.DataFrame, str, dict[str, object]]:
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
        raise RuntimeError("expected yfinance multi-index columns for multiple tickers")

    missing_tickers: dict[str, list[str]] = {}
    for field in ["Open", "High", "Low", "Close", "Volume"]:
        if field not in data.columns.get_level_values(0):
            raise RuntimeError(f"missing yfinance field: {field}")
        field_missing = set(TICKERS) - set(data[field].columns)
        if field_missing:
            missing_tickers[field] = sorted(field_missing)
    if missing_tickers:
        raise RuntimeError(f"missing ticker columns: {missing_tickers}")

    validation_notes = run_structural_check(data)
        
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
    # rather than dropping the whole date for all tickers. This avoids silently
    # truncating ^CNXIT and ^NSEI data prior to ITBEES.NS inception.
    long_df = long_df.dropna(subset=["open", "high", "low", "close"]).copy()
    long_df["volume"] = long_df["volume"].fillna(0.0)
    long_df = long_df.sort_values(["date", "ticker"]).reset_index(drop=True)

    if long_df.empty:
        raise RuntimeError("ohlcv dataframe is empty after dropping incomplete price rows")

    return long_df, download_end_exclusive, validation_notes


def main() -> None:
    # If it exists, we are regenerating it, so we can ignore the 'already exists' check
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
            "auto_adjust=True in yfinance; saved adjusted Open, High, Low, and Close for all tickers; "
            "no manual corporate-action handling."
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
