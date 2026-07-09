<!--
script_path: C:\Users\preet\OneDrive\Desktop\Skool\Arbit\analysis\claim_002_healthy_episode_characterization\opus_tier_a\run_claim_002.py
git_commit: 1717ffb3ed62e6b502d7c6ef2791545737673d89
snapshot_id: tcs_infy_v1_2026-07-04
timestamp_utc: 2026-07-09T10:41:43.721168+00:00
output_content_sha256: e85f1606793970a8383dc570bbe70a8343aa087a9eb7a283f463b91bd81a0dca
-->

# Healthy Episode Characterization — TCS/INFY (Opus Tier A)

## Inputs

- **Snapshot:** `tcs_infy_v1_2026-07-04`
- **Date range:** 2018-01-01 to 2026-06-30
- **Rolling windows:** 60, 120, 250, 500, 730 trading days
- **Method:** Log adjusted closes; TCS.NS dependent, INFY.NS regressor; OLS with intercept
- **Cointegration:** `coint(trend="c", autolag="aic")`; ADF: `adfuller(regression="n", autolag="aic")`
- **Z-scoring ddof:** 1 (addendum item 3 — cancels in RSS ratio)
- **P-value floor:** 1e-300 (addendum item 4 — clip before -log10)

## Part 1 — Episode Boundaries

| Candidate | Start | End | Month-ends | Status |
|-----------|-------|-----|------------|--------|
| 500d_strict | 2020-01-31 | 2021-12-31 | 24 | sustained_run |
| 730d_strict | 2020-12-31 | 2023-03-31 | 28 | sustained_run |
| 500d_730d_consensus_strict | 2020-12-31 | 2021-12-31 | 13 | sustained_run |
| 500d_borderline_tolerant | 2020-01-31 | 2023-01-31 | 37 | sustained_run |

### Fixed Input verification

- `500d_strict`: spec says 2020-01-31 to 2021-12-31 -> computed [OK] MATCH
- `730d_strict`: spec says 2020-12-31 to 2023-03-31 -> computed [OK] MATCH

## Part 2 — Regime Characterization

Full distributional statistics in `episode_regime_summary.csv`.  Key highlights for 500d_strict core:

- **Beta:** mean 0.6812, std 0.1036, range [0.5451, 0.9774]
- **Half-life:** mean 12.5, median 12.7 trading days, range [10.5, 14.6]
- **EG p-value:** median 0.004648, range [0.000066, 0.048052]
- **ADF p-value:** median 0.000044, range [0.000000, 0.000819]
- **Spread volatility:** median 0.045768

## Part 3 — Sub-regime Test

- **500d_strict:** best split after 2020-06-30, RSS improvement = 0.3884, permutation p = 0.0005 → natural_split_supported
- **730d_strict:** best split after 2022-08-30, RSS improvement = 0.3923, permutation p = 0.0005 → natural_split_supported

## Part 4 — Degradation Diagnostics

Numbers-only output in `degradation_diagnostics.csv`.
Descriptive reconstruction only — no RL recommendations, no training-window selection, no claim of 'failure.'

## Output Hashes

- `rolling_metrics.csv`: `55e8d9c4b0933026e8901a2e95ef105051d2eacba1ccd0b30d42f24a6457acaa`
- `episode_boundary_candidates.csv`: `478074a582ca05c0c1f88ed49339bd90aa56bd4a9d01115a662099ce54651ef0`
- `episode_regime_summary.csv`: `5e877bc9efc00ddb7cb4ac3acb96acf68018feeff2e58586dc8a64e8ff0b898f`
- `subregime_tests.csv`: `ec9bb7e46a6dc7e7d74ba4ca3c759bf9afd1304252883ecb3e5eccf5a1b1245f`
- `degradation_diagnostics.csv`: `fc0609a77a027045a8e040abb5ee68f8530386cd542d84200b48d4d26c060fae`
