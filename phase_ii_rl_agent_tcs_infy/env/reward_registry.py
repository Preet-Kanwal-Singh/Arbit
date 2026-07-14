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


RewardFn = Callable[[RewardContext], float]


def compute_cost_adjusted_pnl(ctx: RewardContext) -> float:
    if ctx.previous_spread is None:
        pnl = 0.0
    else:
        pnl = ctx.position * (ctx.current_spread - ctx.previous_spread)
    
    cost = ctx.cost_rate * abs(ctx.position - ctx.previous_position)
    return pnl - cost


def compute_differential_sharpe(ctx: RewardContext) -> float:
    """Mutates ctx.dsr_A / ctx.dsr_B in place to persist EMA state to the
    caller — unlike compute_cost_adjusted_pnl, this is not a pure function.
    Calling it twice on the same ctx will not produce the same output twice."""
    R_t = compute_cost_adjusted_pnl(ctx)
    
    A_prev = ctx.dsr_A
    B_prev = ctx.dsr_B
    
    delta_A = R_t - A_prev
    delta_B = R_t**2 - B_prev
    
    A_t = A_prev + ctx.dsr_eta * delta_A
    B_t = B_prev + ctx.dsr_eta * delta_B
    
    variance_est = B_prev - A_prev**2
    
    if variance_est <= ctx.dsr_epsilon:
        reward = R_t
    else:
        reward = (B_prev * delta_A - 0.5 * A_prev * delta_B) / variance_est ** 1.5
        
    ctx.dsr_A = A_t
    ctx.dsr_B = B_t
    
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
