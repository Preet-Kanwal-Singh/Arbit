"""One-off diagnostic: variance_est settling trajectory + candidate warmup_steps
comparison, to inform dsr_warmup_steps. Not part of the acceptance test."""

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
MILESTONES = [5, 10, 15, 20, 30, 40, 50, 75, 100, 150, 200]
CANDIDATE_WARMUPS = [10, 20, 30, 50, 75, 100]
EPSILON = 1e-12

for core_id in ["500d_core", "730d_core"]:
    env = PairsTradingEnv(core_id=core_id, snapshot_id=SNAPSHOT_ID, bar_frequency="1d", cost_rate=0.0, reward_name="cost_adjusted_pnl")
    rng = np.random.default_rng(42)
    env.reset(seed=42)

    A_prev = 0.0
    B_prev = 0.0
    previous_spread = None
    previous_position = 0.0
    variance_ests = []
    denominators = []
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
        denom = variance_est ** 1.5 if variance_est > 0 else None
        denominators.append(denom)

        delta_A = R_t - A_prev
        delta_B = R_t**2 - B_prev
        A_prev = A_prev + ETA * delta_A
        B_prev = B_prev + ETA * delta_B

        previous_spread = current_spread
        previous_position = current_position

    print(f"--- {core_id} (random policy, seed=42, {len(r_ts)} steps) ---")
    print("step | variance_est   | denominator")
    for m in MILESTONES:
        if m <= len(variance_ests):
            v = variance_ests[m - 1]
            d = denominators[m - 1]
            d_str = f"{d:.6g}" if d is not None else "undefined (var<=0)"
            print(f"  {m:4d} | {v:.6g} | {d_str}")

    print()
    print("candidate warmup_steps -> post-warmup DSR reward stats (epsilon=1e-12 crash guard only):")
    for w in CANDIDATE_WARMUPS:
        A2 = 0.0
        B2 = 0.0
        post_rewards = []
        for i, R_t in enumerate(r_ts):
            step_count = i
            delta_A = R_t - A2
            delta_B = R_t**2 - B2
            variance_est = B2 - A2**2
            if step_count < w or variance_est <= EPSILON:
                pass
            else:
                denom = variance_est ** 1.5
                reward = (B2 * delta_A - 0.5 * A2 * delta_B) / denom
                post_rewards.append(reward)
            A2 = A2 + ETA * delta_A
            B2 = B2 + ETA * delta_B
        if post_rewards:
            arr = np.array(post_rewards)
            print(
                f"  warmup={w:4d}: post-warmup steps={len(arr):4d} ({len(arr)/len(r_ts):5.1%} of episode), "
                f"reward min={arr.min():.4g} max={arr.max():.4g} "
                f"mean|reward|={np.abs(arr).mean():.4g} p99|reward|={np.percentile(np.abs(arr), 99):.4g}"
            )
        else:
            print(f"  warmup={w:4d}: no post-warmup steps")
    print()