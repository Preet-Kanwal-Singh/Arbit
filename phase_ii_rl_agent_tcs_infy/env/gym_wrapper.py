"""Gymnasium wrapper around PairsTradingEnv for use with stable-baselines3."""

from __future__ import annotations

import numpy as np
import gymnasium as gym
from gymnasium import spaces

from .pairs_trading_env import PairsTradingEnv


class GymPairsTradingEnv(gym.Env):
    metadata = {"render_modes": []}

    def __init__(self, **env_kwargs):
        super().__init__()
        self._env = PairsTradingEnv(**env_kwargs)
        # action: single continuous position target in [-1, 1]
        self.action_space = spaces.Box(low=-1.0, high=1.0, shape=(1,), dtype=np.float64)
        # observation: [beta, eg_p, eg_p_trend] — unbounded, no verified hard limits yet
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(3,), dtype=np.float64)

    def reset(self, *, seed: int | None = None, options: dict | None = None):
        obs, info = self._env.reset(seed=seed)
        return np.asarray(obs, dtype=np.float64), info

    def step(self, action):
        scalar_action = float(np.asarray(action).reshape(-1)[0])
        obs, reward, terminated, truncated, info = self._env.step(scalar_action)
        return np.asarray(obs, dtype=np.float64), float(reward), bool(terminated), bool(truncated), info

    def render(self):
        return None
