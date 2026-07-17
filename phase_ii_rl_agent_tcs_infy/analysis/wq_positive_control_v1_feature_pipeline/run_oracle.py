"""Compute oracle reference values for PC-2."""

import sys
import json
from pathlib import Path
import numpy as np

sys.path.append(str(Path(__file__).resolve().parents[3]))

from phase_ii_rl_agent_tcs_infy.env.reward_registry import RewardRegistry, RewardContext

def main():
    print("Regenerating true spread...")
    master_seed = 20260101
    np.random.seed(master_seed)

    n_bars = 2800
    kappa = 0.1
    sigma = 0.3
    
    sigma_stationary = sigma / np.sqrt(1 - (1 - kappa)**2)
    spread = np.zeros(n_bars)
    spread[0] = np.random.normal(0, sigma_stationary)
    
    eps_spread = np.random.normal(0, 1, n_bars)
    for t in range(1, n_bars):
        spread[t] = (1 - kappa) * spread[t-1] + sigma * eps_spread[t]

    bounds = [
        (750, 1249),
        (1250, 1749),
        (1750, 2249),
        (2250, 2749)
    ]

    registry = RewardRegistry.default_v0()
    
    def evaluate_reward(reward_name: str):
        episode_pnls = []
        all_abs_rewards = []
        
        for start_idx, end_idx in bounds:
            ep_pnl = 0.0
            prev_pos = 0.0
            pos = 0.0
            
            dsr_A = 0.0
            dsr_B = 0.0
            dsr_step = 0
            
            for step in range(500):
                t_current = start_idx + step
                t_next = t_current + 1
                
                pos = -1.0 if spread[t_current] > 0 else (1.0 if spread[t_current] < 0 else 0.0)
                
                from dataclasses import dataclass
                
                @dataclass
                class MockContext:
                    previous_spread: float
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
                    
                ctx = MockContext(
                    previous_spread=spread[t_current],
                    current_spread=spread[t_next],
                    previous_position=prev_pos,
                    position=pos,
                    cost_rate=0.0010,
                    dsr_A=dsr_A,
                    dsr_B=dsr_B,
                    dsr_eta=1/252,
                    dsr_epsilon=1e-6,
                    dsr_warmup_steps=0,
                    dsr_step_count=dsr_step
                )
                
                reward = registry.compute(reward_name, ctx)
                ep_pnl += reward
                all_abs_rewards.append(abs(reward))
                
                ret = ctx.position * (ctx.current_spread - ctx.previous_spread) - ctx.cost_rate * abs(ctx.position - ctx.previous_position)
                dsr_A = dsr_A + ctx.dsr_eta * (ret - dsr_A)
                dsr_B = dsr_B + ctx.dsr_eta * (ret**2 - dsr_B)
                dsr_step += 1
                
                prev_pos = pos
                
            episode_pnls.append(ep_pnl)
            
        return float(np.mean(episode_pnls)), float(np.percentile(all_abs_rewards, 99))

    print("Running oracle pass 1 (cost_adjusted_pnl)...")
    mean_pnl, p99_pnl = evaluate_reward("cost_adjusted_pnl")
    
    print("Running oracle pass 2 (differential_sharpe)...")
    mean_dsr, p99_dsr = evaluate_reward("differential_sharpe")
    
    print(f"\noracle_mean_episode_pnl: {mean_pnl:.6f}")
    print(f"p99 threshold (pnl): {p99_pnl:.6f}")
    print(f"oracle_mean_episode_dsr: {mean_dsr:.6f}")
    print(f"p99 threshold (dsr): {p99_dsr:.6f}")
    
    out_dir = Path(__file__).resolve().parent
    out_dir.mkdir(parents=True, exist_ok=True)
    
    refs = {
        "oracle_mean_episode_pnl": mean_pnl,
        "pnl_p99_threshold": p99_pnl,
        "oracle_mean_episode_dsr": mean_dsr,
        "dsr_p99_threshold": p99_dsr,
    }
    (out_dir / "oracle_refs.json").write_text(json.dumps(refs, indent=2))
    
    print("\nSaved oracle_refs.json")


if __name__ == "__main__":
    main()
