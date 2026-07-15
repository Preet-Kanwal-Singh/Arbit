"""Pluggable feature registry for RL observations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Protocol

import numpy as np
import pandas as pd

from .bar_frequency import slice_trailing_bars
from .data_loader import SnapshotDataLoader


class FeatureContext(Protocol):
    loader: SnapshotDataLoader
    y_ticker: str
    x_ticker: str
    bar_frequency: str
    timestamp: pd.Timestamp
    beta_lookback_span: str
    eg_lookback_span: str
    eg_p_cache: dict[tuple, float]


FeatureFn = Callable[[FeatureContext], float]


def _ols_with_intercept(x: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    design = np.column_stack([np.ones(len(x)), x])
    coeffs, *_ = np.linalg.lstsq(design, y, rcond=None)
    fitted = design @ coeffs
    return coeffs, y - fitted


def _log_price_window(
    loader: SnapshotDataLoader,
    y_ticker: str,
    x_ticker: str,
    timestamp: pd.Timestamp,
    span: str,
    bar_frequency: str,
) -> tuple[np.ndarray, np.ndarray]:
    closes = loader.close_panel()
    window_index = slice_trailing_bars(closes.index, timestamp, span, bar_frequency)
    window = closes.loc[window_index]
    y = np.log(window[y_ticker].to_numpy(dtype=float))
    x = np.log(window[x_ticker].to_numpy(dtype=float))
    return y, x


def compute_beta(ctx: FeatureContext) -> float:
    y, x = _log_price_window(
        ctx.loader,
        ctx.y_ticker,
        ctx.x_ticker,
        ctx.timestamp,
        ctx.beta_lookback_span,
        ctx.bar_frequency,
    )
    coeffs, _ = _ols_with_intercept(x, y)
    return float(coeffs[1])


def _compute_eg_pvalue_at(ctx: FeatureContext, timestamp: pd.Timestamp) -> float:
    cache_key = (timestamp, ctx.eg_lookback_span, ctx.y_ticker, ctx.x_ticker)
    if cache_key in ctx.eg_p_cache:
        return ctx.eg_p_cache[cache_key]

    from statsmodels.tsa.stattools import coint

    y, x = _log_price_window(
        ctx.loader,
        ctx.y_ticker,
        ctx.x_ticker,
        timestamp,
        ctx.eg_lookback_span,
        ctx.bar_frequency,
    )
    _, p_value, _ = coint(y, x, trend="c", autolag="aic")
    
    result = float(p_value)
    ctx.eg_p_cache[cache_key] = result
    return result


def compute_eg_pvalue(ctx: FeatureContext) -> float:
    return _compute_eg_pvalue_at(ctx, ctx.timestamp)


def compute_eg_p_trend(ctx: FeatureContext) -> float:
    closes = ctx.loader.close_panel()
    window = slice_trailing_bars(closes.index, ctx.timestamp, "21d", ctx.bar_frequency)
    past_timestamp = window[0]
    
    p_t = _compute_eg_pvalue_at(ctx, ctx.timestamp)
    p_past = _compute_eg_pvalue_at(ctx, past_timestamp)
    
    return p_t - p_past


@dataclass
class FeatureRegistry:
    features: dict[str, FeatureFn]

    @classmethod
    def default_v0(cls) -> "FeatureRegistry":
        return cls(
            features={
                "beta": compute_beta,
                "eg_p": compute_eg_pvalue,
                "eg_p_trend": compute_eg_p_trend,
            }
        )

    @property
    def feature_names(self) -> list[str]:
        return list(self.features.keys())

    def compute_vector(self, ctx: FeatureContext) -> np.ndarray:
        values = [self.features[name](ctx) for name in self.feature_names]
        return np.asarray(values, dtype=np.float64)
