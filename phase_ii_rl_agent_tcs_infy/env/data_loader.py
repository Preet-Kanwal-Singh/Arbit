"""Frequency-tagged OHLCV loader keyed on (ticker, timestamp)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SNAPSHOT_ID = "tcs_infy_v1_2026-07-04"


@dataclass(frozen=True)
class Bar:
    ticker: str
    timestamp: pd.Timestamp
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass(frozen=True)
class SnapshotDataLoader:
    snapshot_id: str
    bar_frequency: str
    tickers: tuple[str, ...]
    frame: pd.DataFrame

    @classmethod
    def from_snapshot(
        cls,
        snapshot_id: str = DEFAULT_SNAPSHOT_ID,
        bar_frequency: str = "1d",
        repo_root: Path | None = None,
    ) -> "SnapshotDataLoader":
        root = repo_root or REPO_ROOT
        snapshot_dir = root / "data" / "snapshots" / snapshot_id
        metadata_path = snapshot_dir / "metadata.json"
        ohlcv_path = snapshot_dir / "ohlcv.csv"
        close_path = snapshot_dir / "adjusted_close.csv"

        if not metadata_path.exists():
            raise FileNotFoundError(f"missing snapshot metadata: {metadata_path}")

        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        if metadata.get("snapshot_id") != snapshot_id:
            raise RuntimeError(
                f"snapshot_id mismatch: {metadata.get('snapshot_id')} != {snapshot_id}"
            )

        tickers = tuple(str(ticker) for ticker in metadata["tickers"])
        if ohlcv_path.exists():
            frame = cls._load_long_ohlcv(ohlcv_path, tickers)
        elif close_path.exists():
            frame = cls._load_legacy_close_only(close_path, tickers)
        else:
            raise FileNotFoundError(
                f"missing snapshot prices: expected {ohlcv_path.name} or {close_path.name}"
            )

        return cls(
            snapshot_id=snapshot_id,
            bar_frequency=bar_frequency,
            tickers=tickers,
            frame=frame,
        )

    @staticmethod
    def _load_long_ohlcv(path: Path, tickers: tuple[str, ...]) -> pd.DataFrame:
        raw = pd.read_csv(path, parse_dates=["date"]).sort_values(["date", "ticker"])
        required = {"date", "ticker", "open", "high", "low", "close", "volume"}
        missing_columns = required - set(raw.columns)
        if missing_columns:
            raise RuntimeError(f"snapshot missing OHLCV columns: {sorted(missing_columns)}")

        raw = raw[raw["ticker"].isin(tickers)].copy()
        price_complete = raw.groupby("date")[["open", "high", "low", "close"]].apply(
            lambda frame: frame.notna().all().all()
        )
        valid_dates = price_complete[price_complete].index
        raw = raw[raw["date"].isin(valid_dates)].copy()
        raw["volume"] = raw["volume"].fillna(0.0)

        rows: list[dict[str, object]] = []
        for row in raw.itertuples(index=False):
            rows.append(
                {
                    "ticker": str(row.ticker),
                    "timestamp": pd.Timestamp(row.date),
                    "open": float(row.open),
                    "high": float(row.high),
                    "low": float(row.low),
                    "close": float(row.close),
                    "volume": float(row.volume),
                }
            )

        return pd.DataFrame(rows).set_index(["ticker", "timestamp"]).sort_index()

    @staticmethod
    def _load_legacy_close_only(path: Path, tickers: tuple[str, ...]) -> pd.DataFrame:
        ticker_list = list(tickers)
        raw = pd.read_csv(path, parse_dates=["date"]).set_index("date").sort_index()
        missing = [ticker for ticker in tickers if ticker not in raw.columns]
        if missing:
            raise RuntimeError(f"snapshot missing tickers: {missing}")

        rows: list[dict[str, object]] = []
        for timestamp, price_row in raw[ticker_list].dropna(how="any").iterrows():
            for ticker in tickers:
                close = float(price_row[ticker])
                rows.append(
                    {
                        "ticker": ticker,
                        "timestamp": pd.Timestamp(timestamp),
                        "open": close,
                        "high": close,
                        "low": close,
                        "close": close,
                        "volume": 0.0,
                    }
                )

        return pd.DataFrame(rows).set_index(["ticker", "timestamp"]).sort_index()

    @property
    def timestamps(self) -> pd.DatetimeIndex:
        ts = self.frame.index.get_level_values("timestamp").unique()
        return pd.DatetimeIndex(ts).sort_values()

    def close_panel(self) -> pd.DataFrame:
        """Pivot to date-indexed close prices, one column per ticker."""
        closes = (
            self.frame.reset_index()
            .pivot(index="timestamp", columns="ticker", values="close")
            .sort_index()
        )
        return closes

    def get_bar(self, ticker: str, timestamp: pd.Timestamp) -> Bar:
        row = self.frame.loc[(ticker, pd.Timestamp(timestamp))]
        return Bar(
            ticker=ticker,
            timestamp=pd.Timestamp(timestamp),
            open=float(row["open"]),
            high=float(row["high"]),
            low=float(row["low"]),
            close=float(row["close"]),
            volume=float(row["volume"]),
        )

    def iter_bars(self, ticker: str) -> Iterable[Bar]:
        ticker_frame = self.frame.loc[ticker].sort_index()
        for timestamp, row in ticker_frame.iterrows():
            yield Bar(
                ticker=ticker,
                timestamp=pd.Timestamp(timestamp),
                open=float(row["open"]),
                high=float(row["high"]),
                low=float(row["low"]),
                close=float(row["close"]),
                volume=float(row["volume"]),
            )
