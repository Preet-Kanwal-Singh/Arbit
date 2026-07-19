"""Tier B — Z-score seam diagnostics (per-seam rerun)."""

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
    timestamps = []
    
    while not done:
        _, _, term, trunc, info = env.step(np.array([0.0], dtype=np.float64))
        spreads.append(info["spread"])
        timestamps.append(info["timestamp"])
        done = term or trunc
        
    S = np.array(spreads, dtype=np.float64)
    T = len(S)
    print(f"Extracted spread sequence of length {T}")
    
    timestamps_dt = pd.to_datetime(timestamps)
    target_dt = pd.Timestamp("2022-08-30")
    idx_split = np.argmin(np.abs(timestamps_dt - target_dt))
    print(f"Nearest bar to 2022-08-30 is at index {idx_split}")
    
    L = 20
    B = 2000
    rng = np.random.default_rng(42)
    
    records = []
    
    for b in range(B):
        resample_S = np.empty(T, dtype=np.float64)
        resample_orig_idx = np.empty(T, dtype=int)
        
        filled = 0
        while filled < T:
            start = rng.integers(0, T)
            indices = (np.arange(start, start + L) % T)
            block = S[indices]
            
            take = min(L, T - filled)
            resample_S[filled:filled+take] = block[:take]
            resample_orig_idx[filled:filled+take] = indices[:take]
            filled += take
            
        action = 0.0
        running_sum = 0.0
        running_sq_sum = 0.0
        
        for t in range(T):
            s_val = resample_S[t]
            
            reward = 0.0
            if t > 0:
                reward = (s_val - resample_S[t-1]) * action
                
            running_sum += s_val
            running_sq_sum += s_val * s_val
            
            n = t + 1
            if n < 10:
                action = 0.0
            else:
                mean = running_sum / n
                var = (running_sq_sum / n) - (mean * mean)
                if var > 1e-12:
                    std = np.sqrt(var)
                    z = (s_val - mean) / std
                    action = np.clip(-z, -1.0, 1.0)
                else:
                    action = 0.0
                    
            if t >= L and t % L == 0:
                idx_A = resample_orig_idx[t]
                idx_B = resample_orig_idx[t-1]
                
                is_regime_A = idx_A >= idx_split
                is_regime_B = idx_B >= idx_split
                is_regime_crossing = (is_regime_A != is_regime_B)
                
                pos_in_path = t / T
                
                records.append({
                    "reward_at_dist0": float(reward),
                    "position_in_path": float(pos_in_path),
                    "is_regime_crossing": bool(is_regime_crossing)
                })
                
    df = pd.DataFrame(records)
    df.to_csv(out_dir / "seams_raw.csv", index=False)
    
    rc_mask = df["is_regime_crossing"]
    rc_df = df[rc_mask]
    wr_df = df[~rc_mask]
    
    rc_n = len(rc_df)
    rc_mean = rc_df["reward_at_dist0"].mean()
    rc_std = rc_df["reward_at_dist0"].std(ddof=1)
    rc_se = rc_std / np.sqrt(rc_n)
    
    wr_n = len(wr_df)
    wr_mean = wr_df["reward_at_dist0"].mean()
    wr_std = wr_df["reward_at_dist0"].std(ddof=1)
    wr_se = wr_std / np.sqrt(wr_n)
    
    diff_mean = rc_mean - wr_mean
    diff_se = np.sqrt(rc_se**2 + wr_se**2)
    
    q1 = df[(df["position_in_path"] >= 0.00) & (df["position_in_path"] < 0.25)]["reward_at_dist0"].mean()
    q2 = df[(df["position_in_path"] >= 0.25) & (df["position_in_path"] < 0.50)]["reward_at_dist0"].mean()
    q3 = df[(df["position_in_path"] >= 0.50) & (df["position_in_path"] < 0.75)]["reward_at_dist0"].mean()
    q4 = df[(df["position_in_path"] >= 0.75) & (df["position_in_path"] <= 1.00)]["reward_at_dist0"].mean()
    
    results = {
        "regime_crossing": {
            "n": int(rc_n),
            "mean": float(rc_mean),
            "se": float(rc_se)
        },
        "within_regime": {
            "n": int(wr_n),
            "mean": float(wr_mean),
            "se": float(wr_se)
        },
        "difference": {
            "mean": float(diff_mean),
            "se": float(diff_se)
        },
        "quartiles": {
            "q1": float(q1),
            "q2": float(q2),
            "q3": float(q3),
            "q4": float(q4)
        }
    }
    
    with open(out_dir / "seam_results_v1.json", "w") as f:
        json.dump(results, f, indent=4)
        
    summary_md = f"""# Z-Score Seam Diagnostics (Per-Seam Rerun) — Tier B (wq_zscore_seam_diagnostics_v1)

## Setup
Same exact underlying logic as `wq_zscore_seam_diagnostics_v0` (`L=20`, `B=2000` resamples, `cost_rate=0.0`). Instead of aggregating means inside the loop, one raw record per seam crossing (distance 0) was saved (~54,000 total seams) recording:
- `reward_at_dist0`
- `position_in_path` (`seam_t / T`)
- `is_regime_crossing`

The raw log is saved in `seams_raw.csv`.

## Regime Comparison
Properly powered statistical difference between regime-crossing seams and within-regime seams (split at 2022-08-30).

- **Regime-Crossing Seams:** `n` = {rc_n}, `mean` = {rc_mean:.5f}, `SE` = {rc_se:.5f}
- **Within-Regime Seams:** `n` = {wr_n}, `mean` = {wr_mean:.5f}, `SE` = {wr_se:.5f}
- **Difference (Crossing - Within):** `mean` = {diff_mean:.5f}, `SE` = {diff_se:.5f}

## Position-Within-Path Stratification
Testing the hypothesis that finite-sample noise heavily affects early running-means, seam rewards were grouped into quartiles by `position_in_path`.

- **Q1 (0% - 25%):** Mean Reward = {q1:.5f}
- **Q2 (25% - 50%):** Mean Reward = {q2:.5f}
- **Q3 (50% - 75%):** Mean Reward = {q3:.5f}
- **Q4 (75% - 100%):** Mean Reward = {q4:.5f}

*(Exploratory check only. No significance threshold was applied or evaluated.)*
"""

    (out_dir / "summary.md").write_text(summary_md)
    print("Completed per-seam analysis.")

if __name__ == "__main__":
    main()
