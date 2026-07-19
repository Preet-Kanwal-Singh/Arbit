"""Tier B — Clip-isolation test (wq_zscore_clip_isolation_v0)."""

import sys
import json
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[3]))

from phase_ii_rl_agent_tcs_infy.env.gym_wrapper import GymPairsTradingEnv

def main():
    out_dir = Path(__file__).resolve().parent
    
    print("Extracting raw spread sequence from 730d_core...")
    env = GymPairsTradingEnv(
        core_id="730d_core", 
        snapshot_id="tcs_infy_v4_2026-07-13", 
        reward_name="cost_adjusted_pnl", 
        cost_rate=0.0
    )
    env.reset(seed=42)
    done = False
    spreads = []
    
    while not done:
        _, _, term, trunc, info = env.step(np.array([0.0], dtype=np.float64))
        spreads.append(info["spread"])
        done = term or trunc
        
    S = np.array(spreads, dtype=np.float64)
    T = len(S)
    print(f"Extracted spread sequence of length {T}")
    
    L = 20
    B = 2000
    rng = np.random.default_rng(42)
    
    records = []
    
    for b in range(B):
        resample_S = np.empty(T, dtype=np.float64)
        
        filled = 0
        while filled < T:
            start = rng.integers(0, T)
            indices = (np.arange(start, start + L) % T)
            block = S[indices]
            
            take = min(L, T - filled)
            resample_S[filled:filled+take] = block[:take]
            filled += take
            
        action = 0.0
        unclipped_action = 0.0
        running_sum = 0.0
        running_sq_sum = 0.0
        
        for t in range(T):
            s_val = resample_S[t]
            
            reward_actual = 0.0
            reward_unclipped = 0.0
            
            if t > 0:
                s_A = resample_S[t-1]
                s_B = s_val
                
                reward_actual = (s_B - s_A) * action
                reward_unclipped = (s_B - s_A) * unclipped_action
                
                if t >= L and t % L == 0:
                    records.append({
                        "reward_actual": float(reward_actual),
                        "reward_unclipped": float(reward_unclipped)
                    })
                
            running_sum += s_val
            running_sq_sum += s_val * s_val
            
            n = t + 1
            if n < 10:
                action = 0.0
                unclipped_action = 0.0
            else:
                mean = running_sum / n
                var = (running_sq_sum / n) - (mean * mean)
                if var > 1e-12:
                    std = np.sqrt(var)
                    z = (s_val - mean) / std
                    action = np.clip(-z, -1.0, 1.0)
                    unclipped_action = -z
                else:
                    action = 0.0
                    unclipped_action = 0.0
                
    df = pd.DataFrame(records)
    df.to_csv(out_dir / "clip_raw.csv", index=False)
    
    n_seams = len(df)
    
    mean_actual = df["reward_actual"].mean()
    std_actual = df["reward_actual"].std(ddof=1)
    se_actual = std_actual / np.sqrt(n_seams)
    
    mean_unclipped = df["reward_unclipped"].mean()
    std_unclipped = df["reward_unclipped"].std(ddof=1)
    se_unclipped = std_unclipped / np.sqrt(n_seams)
    
    results = {
        "n": int(n_seams),
        "actual": {
            "mean": float(mean_actual),
            "se": float(se_actual)
        },
        "unclipped": {
            "mean": float(mean_unclipped),
            "se": float(se_unclipped)
        }
    }
    
    with open(out_dir / "clip_isolation_results.json", "w") as f:
        json.dump(results, f, indent=4)
        
    md_content = f"""# Clip-Isolation Test (Tier B)

**Claim ID:** `wq_zscore_clip_isolation_v0`

## Setup
Re-ran the identical circular block bootstrap (`L=20`, `B=2000`, `cost_rate=0.0`, `seed=42`) on the `730d_core` real data snapshot `tcs_infy_v4_2026-07-13`. 
At every block seam (distance 0), logged the step's actual clipped reward alongside the hypothetical unclipped reward computed against the same identical path-dependent running estimates:
`reward_unclipped = ((mean - s_A) / std) * (s_B - s_A)`

This specifically isolates the marginal contribution of the clip operation while holding the path-dependence fixed.

## Results

Number of distance-0 seam observations: **{n_seams}**

| Series | Mean Reward (Seam) | SE |
|---|---|---|
| Actual (Clipped) | {mean_actual:.5f} | {se_actual:.5f} |
| Unclipped | {mean_unclipped:.5f} | {se_unclipped:.5f} |

*(Note: Explicitly out of scope: this isolates the clip's marginal contribution only, holding path-dependent statistics fixed. It does not test whether path-dependence itself contributes anything.)*
"""

    (out_dir / "summary.md").write_text(md_content)
    print("Completed clip-isolation analysis.")
    print(f"n: {n_seams}")
    print(f"Actual: {mean_actual:.5f} (SE: {se_actual:.5f})")
    print(f"Unclipped: {mean_unclipped:.5f} (SE: {se_unclipped:.5f})")

if __name__ == "__main__":
    main()
