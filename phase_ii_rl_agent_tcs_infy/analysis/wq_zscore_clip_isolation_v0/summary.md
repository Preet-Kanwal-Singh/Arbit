# Clip-Isolation Test (Tier B)

**Claim ID:** `wq_zscore_clip_isolation_v0`

## Setup
Re-ran the identical circular block bootstrap (`L=20`, `B=2000`, `cost_rate=0.0`, `seed=42`) on the `730d_core` real data snapshot `tcs_infy_v4_2026-07-13`. 
At every block seam (distance 0), logged the step's actual clipped reward alongside the hypothetical unclipped reward computed against the same identical path-dependent running estimates:
`reward_unclipped = ((mean - s_A) / std) * (s_B - s_A)`

This specifically isolates the marginal contribution of the clip operation while holding the path-dependence fixed.

## Results

Number of distance-0 seam observations: **54000**

| Series | Mean Reward (Seam) | SE |
|---|---|---|
| Actual (Clipped) | 0.02466 | 0.00015 |
| Unclipped | 0.03389 | 0.00023 |

*(Note: Explicitly out of scope: this isolates the clip's marginal contribution only, holding path-dependent statistics fixed. It does not test whether path-dependence itself contributes anything.)*
