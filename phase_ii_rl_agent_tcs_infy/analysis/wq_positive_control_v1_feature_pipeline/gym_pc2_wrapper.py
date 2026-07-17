"""Gymnasium wrapper for PC-2 cycling through the 4 synthetic episodes."""

from __future__ import annotations

import gymnasium as gym
from gymnasium import spaces
import numpy as np
import pandas as pd
from pathlib import Path

from phase_ii_rl_agent_tcs_infy.env.pairs_trading_env import PairsTradingEnv
from phase_ii_rl_agent_tcs_infy.env.data_loader import SnapshotDataLoader
from phase_ii_rl_agent_tcs_infy.env.episode_config import EPISODE_CORES

def _inject_synthetic_cores(loader: SnapshotDataLoader):
    """Inject PC-2 cores into the global EPISODE_CORES config."""
    if getattr(_inject_synthetic_cores, "_injected", False):
        return
    _inject_synthetic_cores._injected = True
    
    # PC-2 is 2800 bars. Warmup = 750 bars.
    # 4 episodes of 500 bars each.
    timestamps = loader.timestamps
    
    bounds = [
        (750, 1249),
        (1250, 1749),
        (1750, 2249),
        (2250, 2749)
    ]
    
    for i, (start_idx, end_idx) in enumerate(bounds):
        core_id = f"pc2_core_{i}"
        
        # Collision guard requested by user
        assert core_id not in EPISODE_CORES, f"Collision detected: {core_id} already exists in EPISODE_CORES!"
        
        EPISODE_CORES[core_id] = {
            "start": timestamps[start_idx],
            "end": timestamps[end_idx],
            "beta_lookback_span": "730d",
            "eg_lookback_span": "730d"
        }

class PC2GymPairsTradingEnv(gym.Env):
    metadata = {"render_modes": []}

    def __init__(self, reward_name: str = "cost_adjusted_pnl", **kwargs):
        super().__init__()
        
        # Load the synthetic data
        repo_root = Path(__file__).resolve().parent
        self.loader = SnapshotDataLoader.from_snapshot(
            snapshot_id="synthetic_pair_v1",
            bar_frequency="1d",
            repo_root=repo_root
        )
        
        _inject_synthetic_cores(self.loader)
        
        # Instantiate 4 underlying PairsTradingEnv instances
        self.envs = []
        for i in range(4):
            env = PairsTradingEnv(
                loader=self.loader,
                core_id=f"pc2_core_{i}",
                y_ticker="SYN.Y",
                x_ticker="SYN.X",
                reward_name=reward_name,
                **kwargs
            )
            self.envs.append(env)
            
        self.action_space = spaces.Box(low=-1.0, high=1.0, shape=(1,), dtype=np.float64)
        # observation: [beta, eg_p, eg_p_trend]
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf, shape=(3,), dtype=np.float64
        )
        
        self._current_env_idx = 0
        self._current_env = self.envs[self._current_env_idx]

    def reset(self, *, seed: int | None = None, options: dict | None = None):
        super().reset(seed=seed)
        
        # Cycle to the next environment
        self._current_env_idx = (self._current_env_idx + 1) % len(self.envs)
        self._current_env = self.envs[self._current_env_idx]
        
        obs, info = self._current_env.reset(seed=seed)
        return np.asarray(obs, dtype=np.float64), info

    def step(self, action: np.ndarray):
        scalar_action = float(np.asarray(action).reshape(-1)[0])
        obs, reward, terminated, truncated, info = self._current_env.step(scalar_action)
        return np.asarray(obs, dtype=np.float64), float(reward), bool(terminated), bool(truncated), info
