"""Tier B — Z-score block-bootstrap check."""

import sys
import json
from pathlib import Path
import numpy as np

sys.path.append(str(Path(__file__).resolve().parents[3]))

from phase_ii_rl_agent_tcs_infy.env.gym_wrapper import GymPairsTradingEnv

def compute_z_score_pnl(S: np.ndarray) -> float:
    T = len(S)
    pnl = 0.0
    action = 0.0
    
    running_sum = 0.0
    running_sq_sum = 0.0
    
    for t in range(T):
        s_val = S[t]
        
        if t > 0:
            pnl += (s_val - S[t-1]) * action
            
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
                action = -z
                if action < -1.0: action = -1.0
                elif action > 1.0: action = 1.0
            else:
                action = 0.0
                
    return pnl

def circular_block_bootstrap(S: np.ndarray, L: int, B: int, rng: np.random.Generator) -> np.ndarray:
    T = len(S)
    resampled_pnls = np.empty(B, dtype=np.float64)
    
    for b in range(B):
        resample = np.empty(T, dtype=np.float64)
        filled = 0
        while filled < T:
            start = rng.integers(0, T)
            indices = (np.arange(start, start + L) % T)
            block = S[indices]
            
            take = min(L, T - filled)
            resample[filled:filled+take] = block[:take]
            filled += take
            
        resampled_pnls[b] = compute_z_score_pnl(resample)
        
    return resampled_pnls

def main():
    out_dir = Path(__file__).resolve().parent
    
    print("Extracting raw spread sequence from 730d_core...")
    # 1. Data: get the raw spread sequence
    env = GymPairsTradingEnv(
        core_id="730d_core", 
        snapshot_id="tcs_infy_v4_2026-07-13", 
        reward_name="cost_adjusted_pnl", 
        cost_rate=0.0
    )
    env.reset(seed=42)
    done = False
    spreads = []
    
    # Step through once with action=0.0 to extract spreads
    while not done:
        _, _, term, trunc, info = env.step(np.array([0.0], dtype=np.float64))
        spreads.append(info["spread"])
        done = term or trunc
        
    S = np.array(spreads, dtype=np.float64)
    T = len(S)
    print(f"Extracted spread sequence of length {T}")
    
    # Base PnL on original sequence
    observed_pnl = compute_z_score_pnl(S)
    print(f"Observed PnL on original sequence: {observed_pnl:.4f} (Expected ~0.3909)")
    
    # 2 & 3. Block bootstrap at L=10, 20, 40
    block_lengths = [10, 20, 40]
    B = 2000
    rng = np.random.default_rng(42)  # Seed explicitly pinned to 42
    
    results = {}
    
    for L in block_lengths:
        print(f"\nRunning circular block bootstrap for L={L}, B={B}...")
        pnls = circular_block_bootstrap(S, L, B, rng)
        
        p_val = np.mean(pnls >= observed_pnl)
        
        results[f"L_{L}"] = {
            "mean": float(np.mean(pnls)),
            "std": float(np.std(pnls)),
            "p25": float(np.percentile(pnls, 25)),
            "p50": float(np.percentile(pnls, 50)),
            "p75": float(np.percentile(pnls, 75)),
            "p_val": float(p_val)
        }
        
        print(f"L={L}: Mean={results[f'L_{L}']['mean']:.4f}, Std={results[f'L_{L}']['std']:.4f}")
        print(f"L={L}: p-value (Fraction >= {observed_pnl:.4f}) = {p_val:.4f}")
        
    # Save JSON results
    with open(out_dir / "bootstrap_results.json", "w") as f:
        json.dump(results, f, indent=4)
        
    # Generate summary.md
    summary_md = f"""# Z-Score Block-Bootstrap Check — Tier B (wq_zscore_block_bootstrap_v0)

## Procedure
A deterministic Z-score rule (expanding mean/std, 10-step warm-up, `clip(-z, -1, 1)`, `cost_rate=0.0`) was evaluated on circular block-bootstrapped resamples of the `730d_core` spread sequence. We drew `B=2000` resamples at three different block lengths (`L=20` primary, `L=10` and `L=40` sensitivity) to estimate the empirical distribution of PnLs.

**Note:** This null distribution (deterministic rule evaluated on resampled price paths) is distinct from the random-action baseline evaluated in `wq_real_data_capacity_v0` (stochastic actions evaluated on a fixed price path).

## Empirical Results
The observed PnL on the original sequence was **{observed_pnl:.4f}**.
The p-value denotes the fraction of bootstrap resamples that achieved a PnL $\ge$ the observed value.

### Block Length `L=10`
- **Mean PnL:** {results['L_10']['mean']:.4f}
- **Std Dev:** {results['L_10']['std']:.4f}
- **Percentiles:** 25th: {results['L_10']['p25']:.4f} | Median: {results['L_10']['p50']:.4f} | 75th: {results['L_10']['p75']:.4f}
- **p-value:** `{results['L_10']['p_val']:.4f}`

### Block Length `L=20` (Primary)
- **Mean PnL:** {results['L_20']['mean']:.4f}
- **Std Dev:** {results['L_20']['std']:.4f}
- **Percentiles:** 25th: {results['L_20']['p25']:.4f} | Median: {results['L_20']['p50']:.4f} | 75th: {results['L_20']['p75']:.4f}
- **p-value:** `{results['L_20']['p_val']:.4f}`

### Block Length `L=40`
- **Mean PnL:** {results['L_40']['mean']:.4f}
- **Std Dev:** {results['L_40']['std']:.4f}
- **Percentiles:** 25th: {results['L_40']['p25']:.4f} | Median: {results['L_40']['p50']:.4f} | 75th: {results['L_40']['p75']:.4f}
- **p-value:** `{results['L_40']['p_val']:.4f}`

*(Exploratory check only. No significance threshold was applied or evaluated.)*
"""
    (out_dir / "summary.md").write_text(summary_md)
    print("\nResults written to summary.md")

if __name__ == "__main__":
    main()
