# Seam-index Reanalysis (Tier B)

Extends `wq_zscore_seam_diagnostics_v1` by deriving `seam_index = round(position_in_path * T / L)` and tracking granular seam performance.

## Results by Seam Index

| Seam Index | n | Mean Reward | SE |
|---|---|---|---|
| 1 | 2000 | 0.01584 | 0.00094 |
| 2 | 2000 | 0.02228 | 0.00084 |
| 3 | 2000 | 0.02273 | 0.00079 |
| 4 | 2000 | 0.02229 | 0.00078 |
| 5 | 2000 | 0.02449 | 0.00077 |
| 6+ | 44000 | 0.02537 | 0.00016 |

*(Exploratory check only. No significance threshold was applied or evaluated.)*