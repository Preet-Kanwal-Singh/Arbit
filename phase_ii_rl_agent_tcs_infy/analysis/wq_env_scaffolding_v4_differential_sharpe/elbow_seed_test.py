"""Multi-seed diagnostic: locate where DSR reward extremes occur in the
episode (unfiltered by warmup), and separately check whether variance_est
itself stabilizes. Tier C reconnaissance, not a dual-reproduction check.
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
EPSILON = 1e-12  # crash guard only — not a warmup mechanism in this diagnostic
SEEDS = [42, 7, 123, 2024, 99]
CANDIDATE_WARMUPS = [10, 20, 30, 50, 75, 100, 150]
CV_WINDOW = 20
CV_THRESHOLD = 0.25
TOP_K = 6


def simulate(core_id: str, seed: int):
    env = PairsTradingEnv(core_id=core_id, snapshot_id=SNAPSHOT_ID, bar_frequency="1d", cost_rate=0.0, reward_name="cost_adjusted_pnl")
    rng = np.random.default_rng(seed)
    env.reset(seed=seed)

    A_prev = 0.0
    B_prev = 0.0
    previous_spread = None
    previous_position = 0.0
    variance_ests = []
    rewards = []  # "no-warmup" DSR reward, crash-guard only

    terminated = False
    while not terminated:
        action = float(rng.choice([-1.0, 0.0, 1.0]))
        obs, reward, terminated, truncated, info = env.step(action)
        current_spread = info["spread"]
        current_position = info["position"]
        R_t = placeholder_spread_pnl(previous_spread, current_spread, current_position)

        variance_est = B_prev - A_prev**2
        variance_ests.append(variance_est)

        delta_A = R_t - A_prev
        delta_B = R_t**2 - B_prev

        if variance_est <= EPSILON:
            r = R_t
        else:
            denom = variance_est ** 1.5
            r = (B_prev * delta_A - 0.5 * A_prev * delta_B) / denom
        rewards.append(r)

        A_prev = A_prev + ETA * delta_A
        B_prev = B_prev + ETA * delta_B

        previous_spread = current_spread
        previous_position = current_position

    return np.array(variance_ests), np.array(rewards)


def find_settle_step(variance_ests: np.ndarray, window: int, threshold: float):
    """First step S such that the trailing `window`-step coefficient of
    variation of variance_est stays below `threshold` for the rest of the
    episode (no later violation). Independent of reward magnitude."""
    n = len(variance_ests)
    cv = np.full(n, np.nan)
    for t in range(window, n):
        w = variance_ests[t - window : t]
        m = w.mean()
        if m > 0:
            cv[t] = w.std() / m
    violations = np.where(cv >= threshold)[0]
    if len(violations) == 0:
        return window
    last_violation = violations[-1]
    if last_violation + 1 >= n:
        return None
    return int(last_violation + 1)


def main():
    for core_id in ["500d_core", "730d_core"]:
        print(f"===== {core_id} =====")
        all_variance = {}
        all_rewards = {}
        for seed in SEEDS:
            v, r = simulate(core_id, seed)
            all_variance[seed] = v
            all_rewards[seed] = r

        pooled_abs = np.concatenate([np.abs(all_rewards[s]) for s in SEEDS])
        p99 = np.percentile(pooled_abs, 99)
        print(f"pooled |reward| 99th percentile across {len(SEEDS)} seeds: {p99:.4g}\n")

        extreme_steps_by_seed = {}
        print(f"top-{TOP_K} |reward| events per seed (step order, not magnitude order):")
        for seed in SEEDS:
            rewards = all_rewards[seed]
            variance_ests = all_variance[seed]
            abs_r = np.abs(rewards)
            top_idx = sorted(np.argsort(abs_r)[::-1][:TOP_K].tolist())
            print(f"  seed={seed}:")
            for idx in top_idx:
                print(f"    step={idx:4d}  reward={rewards[idx]:9.4g}  variance_est={variance_ests[idx]:.4g}")
            extreme_steps_by_seed[seed] = np.where(abs_r > p99)[0]
        print()

        last_extreme_step = max((s.max() if len(s) else -1) for s in extreme_steps_by_seed.values())
        print(f"last step, across all seeds, where |reward| exceeded the pooled p99: {last_extreme_step}")
        clearing = [w for w in CANDIDATE_WARMUPS if w > last_extreme_step]
        print(f"  -> smallest tested warmup clearing this: {clearing[0] if clearing else 'none tested large enough'}\n")

        print(f"variance_est settle step per seed (trailing {CV_WINDOW}-step CV < {CV_THRESHOLD}, holds to episode end):")
        settle_steps = []
        for seed in SEEDS:
            s = find_settle_step(all_variance[seed], CV_WINDOW, CV_THRESHOLD)
            settle_steps.append(s)
            print(f"  seed={seed}: {'never settles' if s is None else s}")
        finite = [s for s in settle_steps if s is not None]
        if finite:
            print(f"  max settle step across seeds: {max(finite)}")
        print()

        print("candidate warmup -> post-cutoff max|reward|, and whether a p99-extreme persists at/after cutoff:")
        for w in CANDIDATE_WARMUPS:
            maxes = [np.max(np.abs(all_rewards[s][w:])) for s in SEEDS if len(all_rewards[s][w:])]
            persisting = sum(int(np.any(extreme_steps_by_seed[s] >= w)) for s in SEEDS)
            print(f"  warmup={w:4d}: max|reward| post-cutoff = {max(maxes):8.4g}  | seeds with extreme still at/after cutoff: {persisting}/{len(SEEDS)}")
        print()


if __name__ == "__main__":
    main()