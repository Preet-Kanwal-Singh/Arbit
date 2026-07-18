# Z-Score Block-Bootstrap Check — Tier B (wq_zscore_block_bootstrap_v0)

## Procedure
A deterministic Z-score rule (expanding mean/std, 10-step warm-up, `clip(-z, -1, 1)`, `cost_rate=0.0`) was evaluated on circular block-bootstrapped resamples of the `730d_core` spread sequence. We drew `B=2000` resamples at three different block lengths (`L=20` primary, `L=10` and `L=40` sensitivity) to estimate the empirical distribution of PnLs.

**Note:** This null distribution (deterministic rule evaluated on resampled price paths) is distinct from the random-action baseline evaluated in `wq_real_data_capacity_v0` (stochastic actions evaluated on a fixed price path).

## Empirical Results
The observed PnL on the original sequence was **0.3909**.
The p-value denotes the fraction of bootstrap resamples that achieved a PnL $\ge$ the observed value.

### Block Length `L=10`
- **Mean PnL:** 1.8885
- **Std Dev:** 0.2555
- **Percentiles:** 25th: 1.7052 | Median: 1.8842 | 75th: 2.0651
- **p-value:** `1.0000`

### Block Length `L=20` (Primary)
- **Mean PnL:** 1.1914
- **Std Dev:** 0.2062
- **Percentiles:** 25th: 1.0466 | Median: 1.1816 | 75th: 1.3277
- **p-value:** `1.0000`

### Block Length `L=40`
- **Mean PnL:** 0.8322
- **Std Dev:** 0.1780
- **Percentiles:** 25th: 0.7012 | Median: 0.8197 | 75th: 0.9511
- **p-value:** `0.9990`

*(Exploratory check only. No significance threshold was applied or evaluated.)*
