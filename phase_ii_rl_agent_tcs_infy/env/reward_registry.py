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


RewardFn = Callable[[RewardContext], float]


def compute_cost_adjusted_pnl(ctx: RewardContext) -> float:
    if ctx.previous_spread is None:
        pnl = 0.0
    else:
        pnl = ctx.position * (ctx.current_spread - ctx.previous_spread)
    
    cost = ctx.cost_rate * abs(ctx.position - ctx.previous_position)
    return pnl - cost


@dataclass
class RewardRegistry:
    rewards: dict[str, RewardFn]

    @classmethod
    def default_v0(cls) -> "RewardRegistry":
        return cls(
            rewards={
                "cost_adjusted_pnl": compute_cost_adjusted_pnl,
            }
        )

    def compute(self, name: str, ctx: RewardContext) -> float:
        if name not in self.rewards:
            raise KeyError(f"Reward '{name}' not found in registry")
        return self.rewards[name](ctx)
