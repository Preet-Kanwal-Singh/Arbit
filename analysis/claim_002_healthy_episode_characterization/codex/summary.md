<!--
script_path: C:\Users\preet\OneDrive\Desktop\Skool\Arbit\analysis\claim_002_healthy_episode_characterization\codex\characterize_episode_1.py
git_commit: 8452b6849ee79050d213ebfc5de84b3e127fd4ef
snapshot_id: tcs_infy_v1_2026-07-04
timestamp_utc: 2026-07-05T12:35:58.046603+00:00
output_content_sha256: 7b9781c82cdcd58baa0af12efc151f4d4cf4cd3b7fcc5257600fdc6c9add685d
output_hash_scope: bytes after this provenance header
final_file_sha256: recorded in output_manifest.csv and provenance.json
-->

# Healthy Episode Characterization - TCS/INFY

## Inputs

- Snapshot: `tcs_infy_v1_2026-07-04`
- Snapshot date range: `2018-01-01` to `2026-06-30`
- Adjustment policy: `auto_adjust=True in yfinance; saved the adjusted Close columns for TCS.NS and INFY.NS; no manual corporate-action handling.`
- Rolling method: log adjusted closes; TCS as dependent variable; INFY as hedge-ratio regressor; month-end rolling OLS windows `60, 120, 250, 500, 730`.
- Test methods: Engle-Granger `statsmodels.tsa.stattools.coint(trend="c", autolag="aic")`; residual ADF `adfuller(regression="n", autolag="aic")`.

## Episode 1 Boundaries

The rolling results support multiple plausible Episode 1 boundaries:

| Boundary basis | Start | End | Month-ends | Interpretation |
|---|---:|---:|---:|---|
| 500d strict | 2020-01-31 | 2021-12-31 | 24 | Responsive long-window healthy core. |
| 730d strict | 2020-12-31 | 2023-03-31 | 28 | Lagged long-window boundary; smooths later weakening. |
| 500d/730d consensus strict | 2020-12-31 | 2021-12-31 | 13 | Conservative overlap once the 730d window exists. |
| 500d borderline tolerant | 2020-01-31 | 2023-01-31 | 37 | Degradation shoulder, not the strict healthy core. |

I would describe the strict healthy core as 2020-01-31 through 2021-12-31 on 500d month-end diagnostics, with a narrower consensus core from 2020-12-31 through 2021-12-31 when requiring both 500d and 730d strict passes. The 730d rule extends to 2023-03-31, but that boundary is plausibly lagged by its 730-trading-day lookback.

## Healthy Regime Shape

For the 500d strict healthy core, beta ranges from 0.545 to 0.977, with median 0.659 and standard deviation 0.104. The largest beta movement occurs early in the core; the later months are materially tighter.

Spread half-life ranges from 10.497 to 14.643 trading days, with median 12.704. That is a stable, mean-reverting spread profile by these diagnostics.

Engle-Granger p-values range from 0.000066 to 0.048, with median 0.005. Residual ADF p-values range from 0.000000 to 0.000819, with median 0.000044. Both stay below 0.05 throughout the strict 500d core.

Spread volatility, measured as the standard deviation of the log residual over each rolling window, has median 0.046; daily spread-change volatility has median 0.015. The full distributions are in `episode_regime_summary.csv`.

## Homogeneity And Sub-Regimes

The 500d strict core is not statistically homogeneous by the exploratory split test. The strongest split is after 2020-06-30, with RSS improvement 0.388 and permutation p-value 0.000. The split mainly separates an early beta-adjustment segment from a later stable segment; both segments still satisfy the strict healthy-test rule.

The 730d strict candidate is smoother and less responsive. Its sub-regime result should be read as a lagged view because each point contains 730 trailing trading days.

## Degradation Evidence

Within the strict 500d core, the final two month-ends have Engle-Granger p-values near the 0.05 threshold, while ADF p-values remain small and half-life remains in the healthy range. That is weak evidence of gradual degradation, not a strict failure.

After the strict 500d core, the 500d borderline-tolerant rule continues through 2023-01-31. In that shoulder, Engle-Granger p-values remain below 0.10 but start at 0.055 and end at 0.040; half-life moves from 13.026 to 16.260 trading days. This is evidence of degradation, not a strict healthy pass.

No RL recommendations are made here, and no training window is selected.

## Supporting Outputs

- `rolling_metrics.csv` final SHA256 `1cd07736e6e721220694d5bff4b1bee86407c7854bf02a0db36ca907d17e60e9`
- `episode_boundary_candidates.csv` final SHA256 `9233cef86b3a7c08dfe34a1eee43c62eaa83a94ed10db79b33762c57e5e7f8cc`
- `all_pass_runs.csv` final SHA256 `b9e477f2d8f3d10526335f3ad0aaab3aed1acb3db53e839ca197e4691089a06f`
- `episode_regime_summary.csv` final SHA256 `c79ff7cb578409ce51994948ca46fcd96efa88b2e249f66f60aca8ac5b3f1032`
- `subregime_tests.csv` final SHA256 `ad2616a994e5161c195194c596c84d656474310a8347116c1304bf23afa3e3b5`
- `degradation_diagnostics.csv` final SHA256 `617ac0d9111effb727444131efb70ffb731a8a3bdcf024bb3007600ba9d957f3`
- `plot_boundary_diagnostics.svg` final SHA256 `0f010b21739996a00f54b918c3ecc30e89dc05828bea826f5b9e59aeb431f927`
- `plot_episode_metrics.svg` final SHA256 `98e45be5bf6103e2d93ff3fefef5a80dda1eaaa93f4a501fc260b03b45fc452d`
- `plot_subregime_boxplots.svg` final SHA256 `c244961a8ad0a3cb6bbda54d6ab1e4a5ae8cbd8e451b5a03b841cb49d94be4b4`
