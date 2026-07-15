"""Pluggable reward registry for RL environments."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Protocol


class RewardContext(Protocol):
    previous_spread: float | None
    current_spread: float
    previous_position: float
    position: float
    cost_rate: float
    dsr_A: float
    dsr_B: float
    dsr_eta: float
    dsr_epsilon: float
    dsr_warmup_steps: int
    dsr_step_count: int


RewardFn = Callable[[RewardContext], float]


def compute_cost_adjusted_pnl(ctx: RewardContext) -> float:
    if ctx.previous_spread is None:
        pnl = 0.0
    else:
        pnl = ctx.position * (ctx.current_spread - ctx.previous_spread)
    
    cost = ctx.cost_rate * abs(ctx.position - ctx.previous_position)
    return pnl - cost


def compute_differential_sharpe(ctx: RewardContext) -> float:
    """Mutates ctx.dsr_A / ctx.dsr_B / ctx.dsr_step_count in place to persist
    state to the caller — unlike compute_cost_adjusted_pnl, this is not a pure
    function. Calling it twice on the same ctx will not produce the same
    output twice.

    Warm-up and numerical-floor are deliberately separate mechanisms:
    - dsr_warmup_steps (step-count) gates whether the EMA has seen enough
      samples to be trustworthy. Comparable across environments/cores with
      different return scales because it's counted in steps, not return units.
    - dsr_epsilon is a numerical guard only (~1e-12) — it should essentially
      never fire except at genuine zero (t=0, or a policy that never changes
      position). It is NOT a warm-up mechanism; do not tune it to gate on
      episode duration.
    See analysis/wq_env_scaffolding_v4_differential_sharpe/summary.md for the
    reconnaissance behind dsr_warmup_steps=100.
    """
    R_t = compute_cost_adjusted_pnl(ctx)

    A_prev = ctx.dsr_A
    B_prev = ctx.dsr_B
    step_count = ctx.dsr_step_count

    delta_A = R_t - A_prev
    delta_B = R_t**2 - B_prev

    A_t = A_prev + ctx.dsr_eta * delta_A
    B_t = B_prev + ctx.dsr_eta * delta_B

    variance_est = B_prev - A_prev**2

    if step_count < ctx.dsr_warmup_steps or variance_est <= ctx.dsr_epsilon:
        # variance_est <= ctx.dsr_epsilon (rather than <= 0.0) still guards
        # against float-noise pushing the base negative before the
        # fractional power below — Python's ** on a negative base with a
        # non-integer exponent returns a complex number, not a float.
        reward = R_t
    else:
        denominator = variance_est ** 1.5
        reward = (B_prev * delta_A - 0.5 * A_prev * delta_B) / denominator

    ctx.dsr_A = A_t
    ctx.dsr_B = B_t
    ctx.dsr_step_count = step_count + 1

    return reward


@dataclass
class RewardRegistry:
    rewards: dict[str, RewardFn]

    @classmethod
    def default_v0(cls) -> "RewardRegistry":
        return cls(
            rewards={
                "cost_adjusted_pnl": compute_cost_adjusted_pnl,
                "differential_sharpe": compute_differential_sharpe,
            }
        )

    def compute(self, name: str, ctx: RewardContext) -> float:
        if name not in self.rewards:
            raise KeyError(f"Reward '{name}' not found in registry")
        return self.rewards[name](ctx)
