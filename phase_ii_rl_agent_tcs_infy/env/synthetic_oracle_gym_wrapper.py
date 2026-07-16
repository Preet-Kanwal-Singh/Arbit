"""Gymnasium wrapper around SyntheticOracleEnv for use with stable-baselines3."""

from __future__ import annotations

import numpy as np
import gymnasium as gym
from gymnasium import spaces

from .synthetic_oracle_env import SyntheticOracleEnv


class GymSyntheticOracleEnv(gym.Env):
    metadata = {"render_modes": []}

    def __init__(self, **env_kwargs):
        super().__init__()
        self._env = SyntheticOracleEnv(**env_kwargs)
        # action: single continuous position target in [-1, 1]
        self.action_space = spaces.Box(low=-1.0, high=1.0, shape=(1,), dtype=np.float64)
        # observation: [spread]
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(1,), dtype=np.float64)
        
    def set_episode(self, episode_idx: int) -> None:
        self._env.set_episode(episode_idx)

    def reset(self, *, seed: int | None = None, options: dict | None = None) -> tuple[np.ndarray, dict]:
        super().reset(seed=seed)
        obs, info = self._env.reset(seed=seed)
        return obs.astype(np.float64), info

    def step(self, action: np.ndarray) -> tuple[np.ndarray, float, bool, bool, dict]:
        act_val = float(action.item())
        obs, reward, terminated, truncated, info = self._env.step(act_val)
        return obs.astype(np.float64), reward, terminated, truncated, info
