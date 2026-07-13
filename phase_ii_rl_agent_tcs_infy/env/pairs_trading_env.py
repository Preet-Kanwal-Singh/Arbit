"""TCS/INFY pairs-trading RL environment (scaffolding v0)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from .data_loader import SnapshotDataLoader
from .episode_config import EpisodeCoreConfig
from .feature_registry import FeatureRegistry
from .reward import compute_spread, placeholder_spread_pnl
from .reward_registry import RewardContext, RewardRegistry


@dataclass
class _StepContext:
    loader: SnapshotDataLoader
    y_ticker: str
    x_ticker: str
    bar_frequency: str
    timestamp: pd.Timestamp
    beta_lookback_span: str
    eg_lookback_span: str


@dataclass
class _EnvRewardContext:
    previous_spread: float | None
    current_spread: float
    previous_position: float
    position: float
    cost_rate: float
    dsr_A: float
    dsr_B: float
    dsr_eta: float
    dsr_epsilon: float


class PairsTradingEnv:
    """Minimal reset/step environment for infra validation."""

    def __init__(
        self,
        core_id: str,
        loader: SnapshotDataLoader | None = None,
        feature_registry: FeatureRegistry | None = None,
        reward_registry: RewardRegistry | None = None,
        reward_name: str = "cost_adjusted_pnl",
        cost_rate: float = 0.0,
        dsr_eta: float = 0.01,
        dsr_epsilon: float = 1e-6,
        y_ticker: str = "TCS.NS",
        x_ticker: str = "INFY.NS",
        bar_frequency: str = "1d",
        snapshot_id: str = "tcs_infy_v1_2026-07-04",
    ) -> None:
        self.core = EpisodeCoreConfig.from_core_id(core_id)
        self.loader = loader or SnapshotDataLoader.from_snapshot(
            snapshot_id=snapshot_id,
            bar_frequency=bar_frequency,
        )
        self.feature_registry = feature_registry or FeatureRegistry.default_v0()
        self.reward_registry = reward_registry or RewardRegistry.default_v0()
        self.reward_name = reward_name
        self.cost_rate = cost_rate
        self.dsr_eta = dsr_eta
        self.dsr_epsilon = dsr_epsilon
        self.y_ticker = y_ticker
        self.x_ticker = x_ticker
        self.bar_frequency = bar_frequency

        all_timestamps = self.loader.timestamps
        self._episode_timestamps = all_timestamps[
            (all_timestamps >= self.core.start) & (all_timestamps <= self.core.end)
        ]
        if len(self._episode_timestamps) == 0:
            raise RuntimeError(
                f"no trading bars for {core_id} between {self.core.start.date()} and {self.core.end.date()}"
            )

        self._step_idx = 0
        self._position = 0.0
        self._previous_position = 0.0
        self._previous_spread: float | None = None
        self._dsr_A = 0.0
        self._dsr_B = 0.0

    @property
    def episode_start(self) -> pd.Timestamp:
        return pd.Timestamp(self._episode_timestamps[0])

    @property
    def episode_end(self) -> pd.Timestamp:
        return pd.Timestamp(self._episode_timestamps[-1])

    @property
    def episode_length(self) -> int:
        return len(self._episode_timestamps)

    def _make_context(self, timestamp: pd.Timestamp) -> _StepContext:
        return _StepContext(
            loader=self.loader,
            y_ticker=self.y_ticker,
            x_ticker=self.x_ticker,
            bar_frequency=self.bar_frequency,
            timestamp=timestamp,
            beta_lookback_span=self.core.beta_lookback_span,
            eg_lookback_span=self.core.eg_lookback_span,
        )

    def reset(self, *, seed: int | None = None) -> tuple[np.ndarray, dict[str, Any]]:
        if seed is not None:
            np.random.seed(seed)
        self._step_idx = 0
        self._position = 0.0
        self._previous_position = 0.0
        self._previous_spread = None
        self._dsr_A = 0.0
        self._dsr_B = 0.0

        timestamp = self._episode_timestamps[self._step_idx]
        obs = self.feature_registry.compute_vector(self._make_context(timestamp))
        info = {
            "timestamp": timestamp.strftime("%Y-%m-%d"),
            "episode_start": self.episode_start.strftime("%Y-%m-%d"),
            "episode_end": self.episode_end.strftime("%Y-%m-%d"),
            "position": self._position,
        }
        return obs, info

    def step(self, action: float | int) -> tuple[np.ndarray, float, bool, bool, dict[str, Any]]:
        timestamp = self._episode_timestamps[self._step_idx]
        previous_position = self._position
        self._position = float(np.clip(action, -1.0, 1.0))

        spread = compute_spread(
            self.loader,
            self.y_ticker,
            self.x_ticker,
            timestamp,
            self.core.beta_lookback_span,
            self.bar_frequency,
        )
        reward_ctx = _EnvRewardContext(
            previous_spread=self._previous_spread,
            current_spread=spread,
            previous_position=previous_position,
            position=self._position,
            cost_rate=self.cost_rate,
            dsr_A=self._dsr_A,
            dsr_B=self._dsr_B,
            dsr_eta=self.dsr_eta,
            dsr_epsilon=self.dsr_epsilon,
        )
        reward = self.reward_registry.compute(self.reward_name, reward_ctx)
        
        self._dsr_A = reward_ctx.dsr_A
        self._dsr_B = reward_ctx.dsr_B
        self._previous_position = self._position
        self._previous_spread = spread

        obs = self.feature_registry.compute_vector(self._make_context(timestamp))

        terminated = self._step_idx >= len(self._episode_timestamps) - 1
        truncated = False

        if not terminated:
            self._step_idx += 1

        info = {
            "timestamp": timestamp.strftime("%Y-%m-%d"),
            "spread": spread,
            "position": self._position,
            "step_index": self._step_idx if not terminated else self._step_idx,
        }
        return obs, reward, terminated, truncated, info
