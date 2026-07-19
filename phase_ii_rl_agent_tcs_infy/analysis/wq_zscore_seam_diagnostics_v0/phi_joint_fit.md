# AR(1) Joint-Fit Refit (Tier B)

Extends `wq_zscore_seam_diagnostics_v0` by jointly fitting a single $\phi$ to the observed bootstrap ratios across all three block lengths simultaneously.

## Optimal Joint-Fit $\phi$
Minimizing the sum-of-squared-residuals (SSR) across the target ratios ($L=10$: 4.8312, $L=20$: 3.0480, $L=40$: 2.1291) yields an optimal joint-fit of:
**$\phi$ = 0.975088**

### Comparison to OLS Confidence Interval
The 95% CI from the OLS fit on the raw series was [0.9370, 0.9828]. 
The optimal joint-fit $\phi$ (0.975088) falls **inside** this confidence interval.
This indicates the joint fit aligns with the raw data's structural estimate.

## Residual Analysis

| $L$ | Observed Ratio | Predicted Ratio ($\phi$=0.9751) | Residual (Pred - Obs) |
|---|---|---|---|
| 10 | 4.8312 | 4.9141 | 0.0829 |
| 20 | 3.0480 | 2.9571 | -0.0909 |
| 40 | 2.1291 | 1.9785 | -0.1506 |

### Residual Pattern
The residuals across $L=10, 20, 40$ are `0.0829`, `-0.0909`, and `-0.1506` respectively. 
This reveals a **systematic pattern**: the model systematically overpredicts $L=20$ and $L=40$ while drastically underpredicting $L=10$, showing that a single $\phi$ fails to produce a flat, small residual across all block lengths. This persistent systematic pattern argues strongly that the gap isn't merely a mis-set $\phi$, but rather that the theoretical ratio model itself doesn't fully capture the structural dynamics of the artifact.

*(Exploratory check only. No significance threshold was applied or evaluated.)*
