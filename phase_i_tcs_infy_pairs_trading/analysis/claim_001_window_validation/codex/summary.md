# TCS/INFY Cointegration Window Validation

## Provenance

- Script path: `C:\Users\preet\OneDrive\Desktop\Skool\Arbit\analysis\run_cointegration_window_validation.py`
- Git commit: `606cc817c1de5fda7b57dc5814239e36592cc70e`
- Data source: `data\snapshots\tcs_infy_v1_2026-07-04\adjusted_close.csv`
- Snapshot ID: `tcs_infy_v1_2026-07-04`
- Snapshot adjusted close SHA256: `7f2b69cc3c2030bb10c6e7a6f9a727743bff8d7003f7db2f36fa3661bbd60959`
- Timestamp UTC: `2026-07-04T17:30:14.109071+00:00`
- `part_a_synthetic_validation.csv` SHA256: `81c4cdd6c21d36d307ef079b8a1e2017b53eae6ac07e65b3f8d04afb6b5f07ae`
- `part_b_tcs_infy_rolling_cointegration.csv` SHA256: `801fb88207cdccc253a0863f649d797bde65f169db6f976274b8a024df313411`

## Part A

At p < 0.05, no tested window keeps both the worst-case false positive rate and worst-case false negative rate below 10% across all simulated regimes. Across the candidate windows, the p < 0.05 worst-case diagnostics were: 60d max FPR 0.610, max FNR 0.950; 120d max FPR 0.620, max FNR 0.930; 250d max FPR 0.580, max FNR 0.890; 500d max FPR 0.550, max FNR 0.940; 730d max FPR 0.580, max FNR 0.860.

The high false-positive side of that worst-case result is driven by standalone residual ADF p-values, not by the Engle-Granger test alone. At p < 0.05, Engle-Granger false-positive rates by window were 60d 0.130, 120d 0.070, 250d 0.030, 500d 0.030, 730d 0.080, while standalone residual ADF false-positive rates were 60d 0.610, 120d 0.620, 250d 0.580, 500d 0.550, 730d 0.580. That matters because standard ADF p-values on estimated residuals are not the same null calibration as Engle-Granger cointegration p-values.

The conclusion depends materially on persistence. The near-unit-root spread regime is the hardest case, with the largest false-negative rates appearing in 60d engle_granger FNR 0.950; 500d engle_granger FNR 0.940; 120d engle_granger FNR 0.930. Shorter windows can look adequate when the spread mean-reverts quickly or has favorable scale, but that is the easy simulated case rather than evidence that short windows are reliable across regimes.

## Part B

Because Part A found no window satisfying the across-regime <10% FPR/FNR criterion at p < 0.05, Part B evaluated all candidate windows as diagnostics rather than treating any as validated. The rolling causal diagnostics by window were: 60d: first weakening signal 2018-05-31; first borderline result 2018-03-28; first failed test 2018-03-28; first month with both tests failing 2018-03-28. 120d: first weakening signal 2018-08-31; first borderline result 2018-07-31; first failed test 2018-06-29; first month with both tests failing 2018-07-31. 250d: first weakening signal 2019-03-28; first borderline result 2019-09-30; first failed test 2019-01-31; first month with both tests failing 2021-07-30. 500d: first weakening signal 2020-04-30; first borderline result 2022-01-31; first failed test 2022-01-31; first month with both tests failing 2023-12-29. 730d: first weakening signal 2023-04-28; first borderline result 2023-04-28; first failed test 2023-04-28; first month with both tests failing 2024-02-29. The 60d, 120d, and 250d windows fail frequently from their first available dates, which is consistent with Part A's warning that these windows are not reliable across persistence regimes; they are therefore poor evidence for dating a real degradation event on their own. The 500d window enters a borderline/failing transition in January-July 2022: Engle-Granger p-values sit between 0.024 and 0.077 over that interval, with residual ADF remaining below 0.05. The 730d window remains below the 0.05 threshold until its first Engle-Granger failure on 2023-04-28; both tests first fail on 2024-02-29, and from December 2023 through September 2024 its half-life ranges from 51.0 to 126.6 trading days.

Using the longer 500d/730d diagnostics and only the supplied quarterly boundary that the first FLAGGED label is 2022-07-01, the first pre-label deterioration signal appears on 2022-01-31, about 6 months earlier. On the longer windows, the evidence first looks borderline around early 2022 in the 500d window, becomes more visibly weak in 2023, and looks consistently broken by late 2023 into 2024. The 730d window lags the 500d window materially, so conclusions about the exact onset depend on window length. The full quarterly classification table was not included in the prompt, so this run cannot enumerate every quarterly-label disagreement; it can only compare against the stated first FLAGGED date.

## Method Notes

Part B loads adjusted close data from frozen snapshot `tcs_infy_v1_2026-07-04` rather than downloading fresh market data. Engle-Granger p-values come from `statsmodels.tsa.stattools.coint(..., trend="c", autolag="aic")`. Standalone residual/spread ADF p-values come from `statsmodels.tsa.stattools.adfuller(..., regression="n", autolag="aic")`. TCS is the dependent variable and INFY is the hedge-ratio regressor in the real-data rolling beta estimates.
