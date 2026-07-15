"""One-off diagnostic: distribution of variance_est / denominator over an episode.
Not part of the acceptance test."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from phase_ii_rl_agent_tcs_infy.env import PairsTradingEnv
from phase_ii_rl_agent_tcs_infy.env.reward import placeholder_spread_pnl

SNAPSHOT_ID = "tcs_infy_v4_2026-07-13"
ETA = 0.01

for core_id in ["500d_core", "730d_core"]:
    env = PairsTradingEnv(core_id=core_id, snapshot_id=SNAPSHOT_ID, bar_frequency="1d", cost_rate=0.0, reward_name="cost_adjusted_pnl")
    rng = np.random.default_rng(42)
    env.reset(seed=42)

    A_prev = 0.0
    B_prev = 0.0
    previous_spread = None
    previous_position = 0.0
    variance_ests = []
    r_ts = []

    terminated = False
    while not terminated:
        action = float(rng.choice([-1.0, 0.0, 1.0]))
        obs, reward, terminated, truncated, info = env.step(action)
        current_spread = info["spread"]
        current_position = info["position"]
        R_t = placeholder_spread_pnl(previous_spread, current_spread, current_position)
        r_ts.append(R_t)

        variance_est = B_prev - A_prev**2
        variance_ests.append(variance_est)

        delta_A = R_t - A_prev
        delta_B = R_t**2 - B_prev
        A_prev = A_prev + ETA * delta_A
        B_prev = B_prev + ETA * delta_B

        previous_spread = current_spread
        previous_position = current_position

    r_ts = np.array(r_ts)
    variance_ests = np.array(variance_ests)
    denominators = np.array([v ** 1.5 for v in variance_ests if v > 0])

    print(f"--- {core_id} (random policy, seed=42) ---")
    print(f"R_t: min={r_ts.min():.6g} max={r_ts.max():.6g} std={r_ts.std():.6g}")
    print(f"variance_est: min={variance_ests.min():.6g} max={variance_ests.max():.6g} mean={variance_ests.mean():.6g}")
    if len(denominators):
        print(f"denominator (var^1.5), positive-variance steps only: min={denominators.min():.6g} max={denominators.max():.6g} mean={denominators.mean():.6g}")
        for eps in [1e-8, 1e-6, 1e-4, 1e-2]:
            frac = (denominators > eps).mean()
            print(f"  fraction of positive-variance steps clearing epsilon={eps}: {frac:.2%}")
    else:
        print("  no steps with positive variance_est")
    print()