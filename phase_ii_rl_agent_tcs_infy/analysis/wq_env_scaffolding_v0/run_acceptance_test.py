"""Acceptance test for Phase II env scaffolding v0."""

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

OUT_DIR = Path(__file__).resolve().parent
SNAPSHOT_ID = "tcs_infy_v1_2026-07-04"

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


def _is_bad(value: float) -> tuple[bool, bool]:
    is_nan = math.isnan(value)
    is_inf = math.isinf(value)
    return is_nan, is_inf


def run_episode(core_id: str, policy: str, seed: int = 42) -> RunSummary:
    env = PairsTradingEnv(core_id=core_id, snapshot_id=SNAPSHOT_ID, bar_frequency="1d")
    rng = np.random.default_rng(seed)

    expected_start, expected_end = EXPECTED_BOUNDARIES[core_id]
    if env.episode_start.strftime("%Y-%m-%d") != expected_start:
        raise AssertionError(
            f"{core_id} start mismatch: {env.episode_start.date()} != {expected_start}"
        )
    if env.episode_end.strftime("%Y-%m-%d") != expected_end:
        raise AssertionError(
            f"{core_id} end mismatch: {env.episode_end.date()} != {expected_end}"
        )

    obs, _info = env.reset(seed=seed)
    steps = 0
    reward_min = float("inf")
    reward_max = float("-inf")
    nan_obs_steps = 0
    inf_obs_steps = 0
    nan_reward_steps = 0
    inf_reward_steps = 0

    while True:
        if policy == "noop":
            action = 0.0
        elif policy == "random":
            action = float(rng.choice([-1.0, 0.0, 1.0]))
        else:
            raise ValueError(f"unknown policy: {policy}")

        for value in obs:
            is_nan, is_inf = _is_bad(float(value))
            if is_nan:
                nan_obs_steps += 1
            if is_inf:
                inf_obs_steps += 1

        obs, reward, terminated, _truncated, _info = env.step(action)
        steps += 1
        reward_min = min(reward_min, reward)
        reward_max = max(reward_max, reward)

        is_nan, is_inf = _is_bad(float(reward))
        if is_nan:
            nan_reward_steps += 1
        if is_inf:
            inf_reward_steps += 1

        if terminated:
            for value in obs:
                is_nan, is_inf = _is_bad(float(value))
                if is_nan:
                    nan_obs_steps += 1
                if is_inf:
                    inf_obs_steps += 1
            break

    if steps == 0:
        reward_min = 0.0
        reward_max = 0.0

    return RunSummary(
        core_id=core_id,
        policy=policy,
        steps=steps,
        episode_length=env.episode_length,
        episode_start=env.episode_start.strftime("%Y-%m-%d"),
        episode_end=env.episode_end.strftime("%Y-%m-%d"),
        reward_min=reward_min,
        reward_max=reward_max,
        nan_obs_steps=nan_obs_steps,
        inf_obs_steps=inf_obs_steps,
        nan_reward_steps=nan_reward_steps,
        inf_reward_steps=inf_reward_steps,
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
                f"# env_scaffolding_v0 acceptance run\n"
                f"# generated_at_utc: {datetime.now(timezone.utc).isoformat()}\n"
                f"# snapshot_id: {SNAPSHOT_ID}\n"
            )
            (OUT_DIR / log_name).write_text(header + format_summary(summary) + "\n", encoding="utf-8")

    combined_path = OUT_DIR / "run_log_summary.txt"
    combined_lines = [
        "# env_scaffolding_v0 combined acceptance summary",
        f"# generated_at_utc: {datetime.now(timezone.utc).isoformat()}",
        f"# snapshot_id: {SNAPSHOT_ID}",
        "",
    ]
    for summary in runs:
        combined_lines.append(format_summary(summary))
        combined_lines.append("")
    combined_path.write_text("\n".join(combined_lines), encoding="utf-8")

    print(f"wrote {len(runs)} run logs to {OUT_DIR}")
    for summary in runs:
        print(
            f"[ok] {summary.core_id}/{summary.policy}: "
            f"steps={summary.steps}, reward=[{summary.reward_min:.6g}, {summary.reward_max:.6g}]"
        )


if __name__ == "__main__":
    main()
