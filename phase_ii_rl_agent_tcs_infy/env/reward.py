"""Placeholder reward: raw spread PnL without costs or shaping."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .bar_frequency import slice_trailing_bars
from .data_loader import SnapshotDataLoader


def _ols_with_intercept(x: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    design = np.column_stack([np.ones(len(x)), x])
    coeffs, *_ = np.linalg.lstsq(design, y, rcond=None)
    fitted = design @ coeffs
    return coeffs, y - fitted


def compute_spread(
    loader: SnapshotDataLoader,
    y_ticker: str,
    x_ticker: str,
    timestamp: pd.Timestamp,
    beta_lookback_span: str,
    bar_frequency: str,
) -> float:
    closes = loader.close_panel()
    window_index = slice_trailing_bars(
        closes.index, timestamp, beta_lookback_span, bar_frequency
    )
    window = closes.loc[window_index]
    y = np.log(window[y_ticker].to_numpy(dtype=float))
    x = np.log(window[x_ticker].to_numpy(dtype=float))
    coeffs, resid = _ols_with_intercept(x, y)
    return float(resid[-1])


def placeholder_spread_pnl(
    previous_spread: float | None,
    current_spread: float,
    position: float,
) -> float:
    if previous_spread is None:
        return 0.0
    return float(position * (current_spread - previous_spread))
