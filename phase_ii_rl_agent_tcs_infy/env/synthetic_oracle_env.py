"""Synthetic AR(1) oracle environment for PC-1."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from .reward_registry import RewardRegistry, RewardContext


class _EnvRewardContext:
    def __init__(
        self,
        previous_spread: float | None,
        current_spread: float,
        previous_position: float,
        position: float,
        cost_rate: float,
        dsr_A: float,
        dsr_B: float,
        dsr_eta: float,
        dsr_epsilon: float,
        dsr_warmup_steps: int,
        dsr_step_count: int,
    ) -> None:
        self.previous_spread = previous_spread
        self.current_spread = current_spread
        self.previous_position = previous_position
        self.position = position
        self.cost_rate = cost_rate
        self.dsr_A = dsr_A
        self.dsr_B = dsr_B
        self.dsr_eta = dsr_eta
        self.dsr_epsilon = dsr_epsilon
        self.dsr_warmup_steps = dsr_warmup_steps
        self.dsr_step_count = dsr_step_count


class SyntheticOracleEnv:
    """Minimal reset/step environment against a synthetic AR(1) trace."""

    def __init__(
        self,
        episode_idx: int = 0,
        reward_registry: RewardRegistry | None = None,
        reward_name: str = "cost_adjusted_pnl",
        cost_rate: float = 0.0,
        dsr_eta: float = 0.01,
        dsr_epsilon: float = 1e-12,
        dsr_warmup_steps: int = 100,
        snapshot_id: str = "synthetic_positive_control_v1",
        steps_per_episode: int = 500,
    ) -> None:
        import os
        from pathlib import Path
        
        # Load frozen spread series
        root = Path(__file__).resolve().parents[2]
        csv_path = root / "data" / "snapshots" / snapshot_id / "spread.csv"
        df = pd.read_csv(csv_path)
        
        self.spread_series = df["spread"].to_numpy(dtype=np.float64)
        
        self.reward_registry = reward_registry or RewardRegistry.default_v0()
        self.reward_name = reward_name
        self.cost_rate = cost_rate
        self.dsr_eta = dsr_eta
        self.dsr_epsilon = dsr_epsilon
        self.dsr_warmup_steps = dsr_warmup_steps
        self.steps_per_episode = steps_per_episode
        
        # We handle up to 100 episodes
        self.max_episodes = len(self.spread_series) // self.steps_per_episode
        self.episode_idx = episode_idx
        
        self._step_idx = 0
        self._position = 0.0
        self._previous_position = 0.0
        self._previous_spread: float | None = None
        self._dsr_A = 0.0
        self._dsr_B = 0.0
        self._dsr_step_count = 0

    @property
    def episode_length(self) -> int:
        return self.steps_per_episode

    def set_episode(self, episode_idx: int) -> None:
        self.episode_idx = episode_idx % self.max_episodes

    def reset(self, *, seed: int | None = None) -> tuple[np.ndarray, dict[str, Any]]:
        if seed is not None:
            np.random.seed(seed)
            
        self._step_idx = 0
        self._position = 0.0
        self._previous_position = 0.0
        self._previous_spread = None
        self._dsr_A = 0.0
        self._dsr_B = 0.0
        self._dsr_step_count = 0
        
        self.current_episode_idx = self.episode_idx
        self.episode_idx = (self.episode_idx + 1) % self.max_episodes
        
        global_step = (self.current_episode_idx * self.steps_per_episode) + self._step_idx
        spread = self.spread_series[global_step]
        
        obs = np.array([spread], dtype=np.float64)
        info = {
            "position": self._position,
            "episode_idx": self.current_episode_idx,
        }
        return obs, info

    def step(self, action: float | int) -> tuple[np.ndarray, float, bool, bool, dict[str, Any]]:
        global_step = (self.current_episode_idx * self.steps_per_episode) + self._step_idx
        spread = self.spread_series[global_step]
        
        previous_position = self._position
        self._position = float(np.clip(action, -1.0, 1.0))

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
            dsr_warmup_steps=self.dsr_warmup_steps,
            dsr_step_count=self._dsr_step_count,
        )
        reward = self.reward_registry.compute(self.reward_name, reward_ctx)
        
        self._dsr_A = reward_ctx.dsr_A
        self._dsr_B = reward_ctx.dsr_B
        self._dsr_step_count = reward_ctx.dsr_step_count
        self._previous_position = self._position
        self._previous_spread = spread

        obs = np.array([spread], dtype=np.float64)

        terminated = self._step_idx >= self.steps_per_episode - 1
        truncated = False

        if not terminated:
            self._step_idx += 1

        info = {
            "spread": spread,
            "position": self._position,
            "step_index": self._step_idx if not terminated else self._step_idx,
            "episode_idx": self.current_episode_idx,
        }
        return obs, reward, terminated, truncated, info
