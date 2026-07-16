"""Compute oracle reference values for PC-1."""

from __future__ import annotations

import sys
import json
from pathlib import Path

import numpy as np

sys.path.append(str(Path(__file__).resolve().parents[3]))

from phase_ii_rl_agent_tcs_infy.env.synthetic_oracle_env import SyntheticOracleEnv


def run_oracle_pass(reward_name: str) -> tuple[float, float]:
    env = SyntheticOracleEnv(reward_name=reward_name)
    
    episode_pnls = []
    all_abs_rewards = []
    
    for ep in range(100):
        env.set_episode(ep)
        obs, info = env.reset(seed=42)
        done = False
        
        ep_pnl = 0.0
        while not done:
            spread = obs[0]
            if spread > 0:
                action = -1.0
            elif spread < 0:
                action = 1.0
            else:
                action = 0.0
                
            obs, reward, terminated, truncated, info = env.step(action)
            ep_pnl += reward
            all_abs_rewards.append(abs(reward))
            
            done = terminated or truncated
            
        episode_pnls.append(ep_pnl)
        
    mean_ep_pnl = float(np.mean(episode_pnls))
    p99_threshold = float(np.percentile(all_abs_rewards, 99))
    
    return mean_ep_pnl, p99_threshold


def main() -> None:
    print("Running oracle pass 1 (cost_adjusted_pnl)...")
    mean_pnl, p99_pnl = run_oracle_pass("cost_adjusted_pnl")
    
    print("Running oracle pass 2 (differential_sharpe)...")
    mean_dsr, p99_dsr = run_oracle_pass("differential_sharpe")
    
    print(f"\noracle_mean_episode_pnl: {mean_pnl:.6f}")
    print(f"p99 threshold (pnl): {p99_pnl:.6f}")
    print(f"oracle_mean_episode_dsr: {mean_dsr:.6f}")
    print(f"p99 threshold (dsr): {p99_dsr:.6f}")
    
    out_dir = Path(__file__).resolve().parent
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # We will temporarily store these to a json so train scripts can read them,
    # or just print them and let train_pc1a.py import them. 
    # Let's save them to oracle_refs.json.
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
