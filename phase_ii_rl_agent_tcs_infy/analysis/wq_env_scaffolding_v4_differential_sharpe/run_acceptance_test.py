"""Acceptance test for Phase II env scaffolding v4_differential_sharpe."""

from __future__ import annotations

import math
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from phase_ii_rl_agent_tcs_infy.env import PairsTradingEnv  # noqa: E402
from phase_ii_rl_agent_tcs_infy.env.episode_config import EPISODE_CORES  # noqa: E402
from phase_ii_rl_agent_tcs_infy.env.reward import placeholder_spread_pnl  # noqa: E402

OUT_DIR = Path(__file__).resolve().parent
SNAPSHOT_ID = "tcs_infy_v4_2026-07-13"

EXPECTED_BOUNDARIES = {
    "500d_core": ("2020-01-31", "2021-12-31"),
    "730d_core": ("2020-12-31", "2023-03-31"),
}

ETA = 0.01
EPSILON = 1e-8


@dataclass
class RunSummary:
    core_id: str
    policy: str
    steps: int
    episode_length: int
    episode_start: str
    episode_end: str
    dsr_reward_min: float
    dsr_reward_max: float
    nan_obs_steps: int
    inf_obs_steps: int
    nan_dsr_reward_steps: int
    inf_dsr_reward_steps: int
    warmup_steps: int
    post_warmup_steps: int
    is_not_fixed_transform: bool


def _is_bad(value: float) -> tuple[bool, bool]:
    is_nan = math.isnan(value)
    is_inf = math.isinf(value)
    return is_nan, is_inf


def run_episode(core_id: str, policy: str, seed: int = 42) -> RunSummary:
    # Run differential_sharpe
    env_dsr = PairsTradingEnv(
        core_id=core_id, snapshot_id=SNAPSHOT_ID, bar_frequency="1d",
        cost_rate=0.0, reward_name="differential_sharpe", dsr_epsilon=EPSILON
    )
    # Run baseline cost_adjusted_pnl
    env_pnl = PairsTradingEnv(
        core_id=core_id, snapshot_id=SNAPSHOT_ID, bar_frequency="1d",
        cost_rate=0.0, reward_name="cost_adjusted_pnl"
    )

    rng = np.random.default_rng(seed)

    expected_start, expected_end = EXPECTED_BOUNDARIES[core_id]
    if env_dsr.episode_start.strftime("%Y-%m-%d") != expected_start:
        raise AssertionError(f"{core_id} start mismatch: {env_dsr.episode_start.date()} != {expected_start}")
    if env_dsr.episode_end.strftime("%Y-%m-%d") != expected_end:
        raise AssertionError(f"{core_id} end mismatch: {env_dsr.episode_end.date()} != {expected_end}")

    obs_dsr, _info_dsr = env_dsr.reset(seed=seed)
    obs_pnl, _info_pnl = env_pnl.reset(seed=seed)
    
    steps = 0
    dsr_reward_min = float("inf")
    dsr_reward_max = float("-inf")
    nan_obs_steps = 0
    inf_obs_steps = 0
    nan_dsr_reward_steps = 0
    inf_dsr_reward_steps = 0
    warmup_steps = 0
    post_warmup_steps = 0

    previous_position = 0.0
    previous_spread: float | None = None
    
    A_prev = 0.0
    B_prev = 0.0

    ratios = set()

    while True:
        if policy == "noop":
            action = 0.0
        elif policy == "random":
            action = float(rng.choice([-1.0, 0.0, 1.0]))
        else:
            raise ValueError(f"unknown policy: {policy}")

        # Check obs validity
        for value in obs_dsr:
            is_nan, is_inf = _is_bad(float(value))
            if is_nan: nan_obs_steps += 1
            if is_inf: inf_obs_steps += 1

        obs_dsr, reward_dsr, terminated_dsr, _truncated_dsr, info_dsr = env_dsr.step(action)
        obs_pnl, reward_pnl, terminated_pnl, _truncated_pnl, info_pnl = env_pnl.step(action)
        
        current_spread = info_dsr["spread"]
        current_position = info_dsr["position"]

        # Compute R_t via placeholder_spread_pnl since cost_rate=0.0
        R_t = placeholder_spread_pnl(previous_spread, current_spread, current_position)

        # Cross-check: ensure the two rewards are not the same fixed transform
        # We store the ratio reward_dsr / reward_pnl (if reward_pnl != 0) to verify variance
        if abs(reward_pnl) > 1e-8:
            ratios.add(round(reward_dsr / reward_pnl, 5))

        # Check fallback correctness
        denominator = (B_prev - A_prev**2) ** 1.5
        
        if denominator <= EPSILON:
            if not math.isclose(reward_dsr, R_t, rel_tol=1e-9, abs_tol=1e-12):
                raise AssertionError(f"Fallback failed at step {steps}: reward {reward_dsr} != R_t {R_t}")
            warmup_steps += 1
        else:
            # Post-warm-up sanity
            is_nan, is_inf = _is_bad(float(reward_dsr))
            if is_nan or is_inf:
                raise AssertionError(f"Post-warmup sanity failed at step {steps}: reward {reward_dsr} is invalid")
            post_warmup_steps += 1

        # Track manual state for next step
        delta_A = R_t - A_prev
        delta_B = R_t**2 - B_prev
        A_prev = A_prev + ETA * delta_A
        B_prev = B_prev + ETA * delta_B

        previous_spread = current_spread
        previous_position = current_position
        
        dsr_reward_min = min(dsr_reward_min, reward_dsr)
        dsr_reward_max = max(dsr_reward_max, reward_dsr)

        is_nan, is_inf = _is_bad(float(reward_dsr))
        if is_nan: nan_dsr_reward_steps += 1
        if is_inf: inf_dsr_reward_steps += 1

        if terminated_dsr:
            for value in obs_dsr:
                is_nan, is_inf = _is_bad(float(value))
                if is_nan: nan_obs_steps += 1
                if is_inf: inf_obs_steps += 1
            break
            
        steps += 1

    is_not_fixed_transform = len(ratios) > 1

    if policy == "random" and not is_not_fixed_transform:
        raise AssertionError(f"Cross-check failed: differential_sharpe appears to be a fixed transform of cost_adjusted_pnl in {core_id}/{policy}")

    return RunSummary(
        core_id=core_id,
        policy=policy,
        steps=steps + 1,
        episode_length=env_dsr.episode_length,
        episode_start=env_dsr.episode_start.strftime("%Y-%m-%d"),
        episode_end=env_dsr.episode_end.strftime("%Y-%m-%d"),
        dsr_reward_min=dsr_reward_min,
        dsr_reward_max=dsr_reward_max,
        nan_obs_steps=nan_obs_steps,
        inf_obs_steps=inf_obs_steps,
        nan_dsr_reward_steps=nan_dsr_reward_steps,
        inf_dsr_reward_steps=inf_dsr_reward_steps,
        warmup_steps=warmup_steps,
        post_warmup_steps=post_warmup_steps,
        is_not_fixed_transform=is_not_fixed_transform,
    )


def format_summary(summary: RunSummary) -> str:
    return "\n".join(
        [
            f"core_id: {summary.core_id}",
            f"policy: {summary.policy}",
            f"steps: {summary.steps}",
            f"episode_length: {summary.episode_length}",
            f"episode_start: {summary.episode_start}",
            f"episode_end: {summary.episode_end}",
            f"dsr_reward_min: {summary.dsr_reward_min:.12g}",
            f"dsr_reward_max: {summary.dsr_reward_max:.12g}",
            f"nan_obs_steps: {summary.nan_obs_steps}",
            f"inf_obs_steps: {summary.inf_obs_steps}",
            f"nan_dsr_reward_steps: {summary.nan_dsr_reward_steps}",
            f"inf_dsr_reward_steps: {summary.inf_dsr_reward_steps}",
            f"warmup_steps: {summary.warmup_steps}",
            f"post_warmup_steps: {summary.post_warmup_steps}",
            f"is_not_fixed_transform: {summary.is_not_fixed_transform}",
        ]
    )


def main() -> None:
    runs: list[RunSummary] = []
    for core_id in EPISODE_CORES:
        for policy in ("noop", "random"):
            summary = run_episode(core_id, policy)
            runs.append(summary)

            log_name = f"run_log_{core_id}_{policy}.txt"
            header = (
                f"# env_scaffolding_v4_differential_sharpe acceptance run\n"
                f"# generated_at_utc: {datetime.now(timezone.utc).isoformat()}\n"
                f"# snapshot_id: {SNAPSHOT_ID}\n"
            )
            (OUT_DIR / log_name).write_text(header + format_summary(summary) + "\n", encoding="utf-8")

    combined_path = OUT_DIR / "run_log_summary.txt"
    combined_lines = [
        "# env_scaffolding_v4_differential_sharpe combined acceptance summary",
        f"# generated_at_utc: {datetime.now(timezone.utc).isoformat()}",
        f"# snapshot_id: {SNAPSHOT_ID}",
        "",
    ]
    for summary in runs:
        combined_lines.append(format_summary(summary))
        combined_lines.append("")
    combined_path.write_text("\n".join(combined_lines), encoding="utf-8")


if __name__ == "__main__":
    main()
