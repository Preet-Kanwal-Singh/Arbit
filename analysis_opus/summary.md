# TCS/INFY Cointegration Window Validation — Antigravity/Opus

## Provenance

- Script: `C:\Users\preet\OneDrive\Desktop\Skool\Arbit\analysis_opus\run_cointegration_window_validation.py`
- Git commit: `unavailable`
- Data source: `yfinance adjusted close, TCS.NS and INFY.NS, 2018-01-01 through 2026-06-30`
- Snapshot ID: `none_live_yfinance_fetch_2018-01-01_2026-06-30`
- Timestamp UTC: `2026-07-04T17:05:14.395435+00:00`
- Seeds per condition per window: 100
- statsmodels: 0.14.6
- Part A hash: `3558438be472272e03d675d4dcf281961efec4593d5e4544de7c2d259fab508a`
- Part B hash: `23f6a0fcc0e18fe3c98cb5f99c94df2bb7f1df47d2474078903ad0907642c69c`

## Part A — Synthetic Window-Length Validation

### False-positive rates at p < 0.05 (non-cointegrated series incorrectly passing)

| Window | EG FPR | Residual ADF FPR |
|--------|--------|------------------|
| 60d | 0.060 | 0.490 |
| 120d | 0.110 | 0.570 |
| 250d | 0.090 | 0.490 |
| 500d | 0.040 | 0.570 |
| 730d | 0.060 | 0.580 |

The standalone residual-ADF false-positive rates are substantially higher than the Engle-Granger rates. This is expected and is not a bug: ADF critical values assume the series being tested is observed, not estimated. When ADF is applied to OLS residuals, the residuals are mechanically more stationary-looking than the true spread because OLS minimises the sum of squared residuals, biasing the ADF statistic toward rejection. The Engle-Granger procedure corrects for this by using critical-value tables specifically calibrated for the two-step case. Treating raw residual-ADF p-values as if they were Engle-Granger p-values would systematically overstate evidence for cointegration.

### Engle-Granger false-negative rates at p < 0.05

| Window | φ regime | Noise | FNR | Mean p |
|--------|----------|-------|-----|--------|
| 60d | fast_phi0.80 | high | 0.540 | 0.1532 |
| 60d | fast_phi0.80 | low | 0.560 | 0.1417 |
| 60d | moderate_phi0.95 | high | 0.830 | 0.3896 |
| 60d | moderate_phi0.95 | low | 0.850 | 0.3512 |
| 60d | near_unit_root_phi0.99 | high | 0.860 | 0.4548 |
| 60d | near_unit_root_phi0.99 | low | 0.890 | 0.4431 |
| 120d | fast_phi0.80 | high | 0.130 | 0.0324 |
| 120d | fast_phi0.80 | low | 0.180 | 0.0366 |
| 120d | moderate_phi0.95 | high | 0.820 | 0.3146 |
| 120d | moderate_phi0.95 | low | 0.870 | 0.2863 |
| 120d | near_unit_root_phi0.99 | high | 0.870 | 0.4046 |
| 120d | near_unit_root_phi0.99 | low | 0.920 | 0.4357 |
| 250d | fast_phi0.80 | high | 0.020 | 0.0076 |
| 250d | fast_phi0.80 | low | 0.000 | 0.0009 |
| 250d | moderate_phi0.95 | high | 0.670 | 0.1233 |
| 250d | moderate_phi0.95 | low | 0.650 | 0.1550 |
| 250d | near_unit_root_phi0.99 | high | 0.940 | 0.4203 |
| 250d | near_unit_root_phi0.99 | low | 0.920 | 0.4365 |
| 500d | fast_phi0.80 | high | 0.000 | 0.0000 |
| 500d | fast_phi0.80 | low | 0.000 | 0.0004 |
| 500d | moderate_phi0.95 | high | 0.180 | 0.0259 |
| 500d | moderate_phi0.95 | low | 0.080 | 0.0191 |
| 500d | near_unit_root_phi0.99 | high | 0.880 | 0.3453 |
| 500d | near_unit_root_phi0.99 | low | 0.870 | 0.2985 |
| 730d | fast_phi0.80 | high | 0.000 | 0.0000 |
| 730d | fast_phi0.80 | low | 0.000 | 0.0000 |
| 730d | moderate_phi0.95 | high | 0.010 | 0.0037 |
| 730d | moderate_phi0.95 | low | 0.010 | 0.0034 |
| 730d | near_unit_root_phi0.99 | high | 0.860 | 0.2865 |
| 730d | near_unit_root_phi0.99 | low | 0.850 | 0.2542 |

### Conclusion

No tested window length keeps both the Engle-Granger worst-case false-positive rate and worst-case false-negative rate below 10 % across all simulated persistence regimes at p < 0.05. The binding constraint is the false-negative rate in the near-unit-root regime (φ ≈ 0.99), where the stationary spread is barely distinguishable from a random walk over any practical horizon. In the fast mean-reversion regime (φ ≈ 0.80), detection power is adequate even at shorter windows, but this is the statistically easy case — a spread that reverts quickly is precisely the scenario Engle-Granger is designed for. The moderate regime (φ ≈ 0.95) falls between: detection improves materially with longer windows, but never reaches the < 10 % FNR threshold uniformly.

The conclusion is therefore strongly persistence-dependent. Shorter windows (60–120 days) perform adequately only when the spread mean-reverts fast or the signal-to-noise ratio is favourable — conditions that cannot be assumed in advance without circular reasoning, since estimating the spread's persistence requires having already established cointegration. Longer windows (500–730 days) gain power against slower mean reversion but at the cost of averaging over structural breaks, which is precisely the opposite of what a rolling degradation monitor needs.

Because no single window meets the dual < 10 % criterion across all regimes, Part B evaluates every candidate window as a diagnostic rather than treating any as validated. Conclusions about degradation timing should be read as what the evidence looks like at each window length, not as definitive pass/fail determinations.

## Part B — Real TCS/INFY Rolling Cointegration Analysis

### 60-day window

- First weakening (EG p > 0.01 while still < 0.05): 2018-12-31
- First borderline (EG p > 0.03): 2018-03-31
- First EG failure (p ≥ 0.05): 2018-03-31
- First month both tests fail: 2018-03-31
- EG failure precedes first quarterly FLAGGED label by ~51 months

### 120-day window

- First weakening (EG p > 0.01 while still < 0.05): 2018-09-30
- First borderline (EG p > 0.03): 2018-06-30
- First EG failure (p ≥ 0.05): 2018-06-30
- First month both tests fail: 2018-07-31
- EG failure precedes first quarterly FLAGGED label by ~48 months

### 250-day window

- First weakening (EG p > 0.01 while still < 0.05): 2019-03-31
- First borderline (EG p > 0.03): 2019-01-31
- First EG failure (p ≥ 0.05): 2019-01-31
- First month both tests fail: 2021-07-31
- EG failure precedes first quarterly FLAGGED label by ~41 months

### 500-day window

- First weakening (EG p > 0.01 while still < 0.05): 2020-07-31
- First borderline (EG p > 0.03): 2020-08-31
- First EG failure (p ≥ 0.05): 2021-07-31
- First month both tests fail: 2023-12-31
- EG failure precedes first quarterly FLAGGED label by ~11 months

### 730-day window

- First weakening (EG p > 0.01 while still < 0.05): 2021-07-31
- First borderline (EG p > 0.03): 2021-07-31
- First EG failure (p ≥ 0.05): 2023-04-30
- First month both tests fail: 2023-12-31

### Degradation Timeline Summary

The 500d window first shows borderline Engle-Granger results on 2020-08-31, approximately 22 months before the first quarterly FLAGGED label (2022-07-01). During this transition, half-life ranges from 11.3 to 19.9 trading days.

The 730d window first shows borderline Engle-Granger results on 2021-07-31, approximately 11 months before the first quarterly FLAGGED label (2022-07-01). During this transition, half-life ranges from 16.2 to 18.5 trading days.

The 60d window fails frequently (89% of months), consistent with Part A's finding that short windows are unreliable across persistence regimes. Its failures are therefore poor evidence for dating a real structural change.

The 120d window fails frequently (89% of months), consistent with Part A's finding that short windows are unreliable across persistence regimes. Its failures are therefore poor evidence for dating a real structural change.

The 250d window fails frequently (92% of months), consistent with Part A's finding that short windows are unreliable across persistence regimes. Its failures are therefore poor evidence for dating a real structural change.

### Method Notes

Engle-Granger p-values: `statsmodels.tsa.stattools.coint(..., trend='c', autolag='aic')`. Standalone residual ADF p-values: `statsmodels.tsa.stattools.adfuller(..., regression='n', autolag='aic')`. TCS is the dependent variable; INFY is the hedge-ratio regressor in all OLS beta estimates. Half-life estimated from AR(1) on OLS residuals: hl = -log(2) / log(phi_hat). Beta change is month-over-month absolute change in the OLS hedge ratio.