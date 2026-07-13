"""Acceptance test for Phase II env scaffolding v3_reward_registry."""

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
from phase_ii_rl_agent_tcs_infy.env.feature_registry import _compute_eg_pvalue_at  # noqa: E402
from phase_ii_rl_agent_tcs_infy.env.bar_frequency import slice_trailing_bars  # noqa: E402
from phase_ii_rl_agent_tcs_infy.env.reward import placeholder_spread_pnl  # noqa: E402

OUT_DIR = Path(__file__).resolve().parent
SNAPSHOT_ID = "tcs_infy_v4_2026-07-13"

EXPECTED_BOUNDARIES = {
    "500d_core": ("2020-01-31", "2021-12-31"),
    "730d_core": ("2020-12-31", "2023-03-31"),
}


@dataclass
class RunSummary:
    core_id: str
    policy: str
    steps: int
    episode_length: int
    episode_start: str
    episode_end: str
    reward_min: float
    reward_max: float
    nan_obs_steps: int
    inf_obs_steps: int
    nan_reward_steps: int
    inf_reward_steps: int
    strict_decrease_count: int


def _is_bad(value: float) -> tuple[bool, bool]:
    is_nan = math.isnan(value)
    is_inf = math.isinf(value)
    return is_nan, is_inf


def run_episode(core_id: str, policy: str, seed: int = 42) -> RunSummary:
    env0 = PairsTradingEnv(core_id=core_id, snapshot_id=SNAPSHOT_ID, bar_frequency="1d", cost_rate=0.0)
    env1 = PairsTradingEnv(core_id=core_id, snapshot_id=SNAPSHOT_ID, bar_frequency="1d", cost_rate=0.01)
    rng = np.random.default_rng(seed)

    expected_start, expected_end = EXPECTED_BOUNDARIES[core_id]
    if env0.episode_start.strftime("%Y-%m-%d") != expected_start:
        raise AssertionError(
            f"{core_id} start mismatch: {env0.episode_start.date()} != {expected_start}"
        )
    if env0.episode_end.strftime("%Y-%m-%d") != expected_end:
        raise AssertionError(
            f"{core_id} end mismatch: {env0.episode_end.date()} != {expected_end}"
        )

    obs0, _info0 = env0.reset(seed=seed)
    obs1, _info1 = env1.reset(seed=seed)
    steps = 0
    reward_min = float("inf")
    reward_max = float("-inf")
    nan_obs_steps = 0
    inf_obs_steps = 0
    nan_reward_steps = 0
    inf_reward_steps = 0
    
    strict_decrease_count = 0
    previous_position = 0.0
    previous_spread: float | None = None

    while True:
        if policy == "noop":
            action = 0.0
        elif policy == "random":
            action = float(rng.choice([-1.0, 0.0, 1.0]))
        else:
            raise ValueError(f"unknown policy: {policy}")

        if len(obs0) != 3:
            raise AssertionError(f"observation length is {len(obs0)}, expected 3")

        for value in obs0:
            is_nan, is_inf = _is_bad(float(value))
            if is_nan:
                nan_obs_steps += 1
            if is_inf:
                inf_obs_steps += 1

        obs0, reward0, terminated0, _truncated0, info0 = env0.step(action)
        obs1, reward1, terminated1, _truncated1, info1 = env1.step(action)
        
        current_spread = info0["spread"]
        current_position = info0["position"]
        
        # Regression test: cost_rate=0.0 must exactly match placeholder_spread_pnl
        expected_reward = placeholder_spread_pnl(previous_spread, current_spread, current_position)
        if reward0 != expected_reward:
            raise AssertionError(f"Regression failed at step {steps}: reward0 ({reward0}) != expected ({expected_reward})")
            
        # Strict decrease test: cost_rate=0.01 must strictly decrease reward when position changes
        if current_position != previous_position:
            if not (reward1 < reward0):
                raise AssertionError(f"Strict decrease failed at step {steps}: reward1 ({reward1}) >= reward0 ({reward0}) despite position change from {previous_position} to {current_position}")
            strict_decrease_count += 1
        else:
            if reward1 != reward0:
                raise AssertionError(f"Reward mismatch when position didn't change at step {steps}: reward1 ({reward1}) != reward0 ({reward0})")

        steps += 1
        reward_min = min(reward_min, reward0)
        reward_max = max(reward_max, reward0)

        is_nan, is_inf = _is_bad(float(reward0))
        if is_nan:
            nan_reward_steps += 1
        if is_inf:
            inf_reward_steps += 1

        previous_spread = current_spread
        previous_position = current_position

        if terminated0:
            for value in obs0:
                is_nan, is_inf = _is_bad(float(value))
                if is_nan:
                    nan_obs_steps += 1
                if is_inf:
                    inf_obs_steps += 1
            break

    if steps == 0:
        reward_min = 0.0
        reward_max = 0.0

    if policy == "random" and strict_decrease_count == 0:
        raise AssertionError(f"No position changes occurred in {core_id}/{policy}")

    return RunSummary(
        core_id=core_id,
        policy=policy,
        steps=steps,
        episode_length=env0.episode_length,
        episode_start=env0.episode_start.strftime("%Y-%m-%d"),
        episode_end=env0.episode_end.strftime("%Y-%m-%d"),
        reward_min=reward_min,
        reward_max=reward_max,
        nan_obs_steps=nan_obs_steps,
        inf_obs_steps=inf_obs_steps,
        nan_reward_steps=nan_reward_steps,
        inf_reward_steps=inf_reward_steps,
        strict_decrease_count=strict_decrease_count,
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
            f"reward_min: {summary.reward_min:.12g}",
            f"reward_max: {summary.reward_max:.12g}",
            f"nan_obs_steps: {summary.nan_obs_steps}",
            f"inf_obs_steps: {summary.inf_obs_steps}",
            f"nan_reward_steps: {summary.nan_reward_steps}",
            f"inf_reward_steps: {summary.inf_reward_steps}",
            f"strict_decrease_count: {summary.strict_decrease_count}",
        ]
    )


def main() -> None:
    runs: list[RunSummary] = []
    for core_id in EPISODE_CORES:
        for policy in ("noop", "random"):
            summary = run_episode(core_id, policy)
            if summary.nan_obs_steps or summary.inf_obs_steps:
                raise RuntimeError(f"{core_id}/{policy}: bad observation values detected")
            if summary.nan_reward_steps or summary.inf_reward_steps:
                raise RuntimeError(f"{core_id}/{policy}: bad reward values detected")
            runs.append(summary)

            log_name = f"run_log_{core_id}_{policy}.txt"
            header = (
                f"# env_scaffolding_v3_reward_registry acceptance run\n"
                f"# generated_at_utc: {datetime.now(timezone.utc).isoformat()}\n"
                f"# snapshot_id: {SNAPSHOT_ID}\n"
            )
            (OUT_DIR / log_name).write_text(header + format_summary(summary) + "\n", encoding="utf-8")

    combined_path = OUT_DIR / "run_log_summary.txt"
    combined_lines = [
        "# env_scaffolding_v3_reward_registry combined acceptance summary",
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
