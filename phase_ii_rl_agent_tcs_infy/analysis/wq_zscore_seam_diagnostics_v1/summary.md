# Z-Score Seam Diagnostics (Per-Seam Rerun) — Tier B (wq_zscore_seam_diagnostics_v1)

## Setup
Same exact underlying logic as `wq_zscore_seam_diagnostics_v0` (`L=20`, `B=2000` resamples, `cost_rate=0.0`). Instead of aggregating means inside the loop, one raw record per seam crossing (distance 0) was saved (~54,000 total seams) recording:
- `reward_at_dist0`
- `position_in_path` (`seam_t / T`)
- `is_regime_crossing`

The raw log is saved in `seams_raw.csv`.

## Regime Comparison
Properly powered statistical difference between regime-crossing seams and within-regime seams (split at 2022-08-30).

- **Regime-Crossing Seams:** `n` = 20827, `mean` = 0.02450, `SE` = 0.00023
- **Within-Regime Seams:** `n` = 33173, `mean` = 0.02476, `SE` = 0.00019
- **Difference (Crossing - Within):** `mean` = -0.00026, `SE` = 0.00030

## Position-Within-Path Stratification
Testing the hypothesis that finite-sample noise heavily affects early running-means, seam rewards were grouped into quartiles by `position_in_path`.

- **Q1 (0% - 25%):** Mean Reward = 0.02227
- **Q2 (25% - 50%):** Mean Reward = 0.02514
- **Q3 (50% - 75%):** Mean Reward = 0.02549
- **Q4 (75% - 100%):** Mean Reward = 0.02538

*(Exploratory check only. No significance threshold was applied or evaluated.)*
