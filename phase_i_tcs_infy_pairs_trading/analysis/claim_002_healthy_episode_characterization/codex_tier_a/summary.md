<!--
script_path: C:\Users\preet\OneDrive\Desktop\Skool\Arbit\analysis\claim_002_healthy_episode_characterization\codex_tier_a\run_claim_002_healthy_episode_characterization.py
git_commit: 1717ffb3ed62e6b502d7c6ef2791545737673d89
snapshot_id: tcs_infy_v1_2026-07-04
execution_timestamp_utc: 2026-07-09T09:55:42.568069+00:00
output_name: summary.md
output_content_sha256: 694c925f0bc53babc0e4199afbc64fcf85accfe8e79e67ed016db94b40784e9b
output_hash_scope: bytes after this provenance header
final_file_sha256: recorded in provenance.json
-->
# Claim 002 Healthy Episode Characterization - Codex Tier A

## Inputs

- Claim ID: `claim_002_healthy_episode_characterization`
- Snapshot: `tcs_infy_v1_2026-07-04`
- Price file: `data/snapshots/tcs_infy_v1_2026-07-04/adjusted_close.csv`
- Columns: `date`, `TCS.NS`, `INFY.NS`; rows missing either price dropped.
- No live pulls and no snapshot regeneration.

## Part 1 Boundary Candidates

| boundary_basis | status | start | end | count | fixed date match |
| --- | --- | --- | --- | ---: | --- |
| 500d_strict | selected_latest_ending_run | 2020-01-31 | 2021-12-31 | 24 | start=True; end=True; count=True |
| 730d_strict | selected_latest_ending_run | 2020-12-31 | 2023-03-31 | 28 | start=True; end=True; count=True |
| 500d_730d_consensus_strict | selected_latest_ending_run | 2020-12-31 | 2021-12-31 | 13 |  |
| 500d_borderline_tolerant | selected_latest_ending_run | 2020-01-31 | 2023-01-31 | 37 |  |

## Part 2 Regime Summary

- `500d_strict` observations: 24
- `730d_strict` observations: 28
- Full metric statistics are in `episode_regime_summary.csv`.

## Part 3 Sub-Regime Tests

| basis | split_after | improvement | p_value | interpretation |
| --- | --- | ---: | ---: | --- |
| 500d_strict | 2020-06-30 | 0.388442036623 | 0.000499750125 | natural_split_supported |
| 730d_strict | 2022-08-30 | 0.392289875164 | 0.000499750125 | natural_split_supported |

## Part 4 Degradation Diagnostics

- `500d_strict` observations: 24
- `730d_strict` observations: 28
- `500d_post_core_shoulder` observations: 13
- `degradation_diagnostics.csv` contains numbers only.

## Method Notes

- Rolling metrics follow the Spec Block method: OLS with intercept, `statsmodels.coint(..., trend="c", autolag="aic")`, residual `adfuller(..., regression="n", autolag="aic")`, AR(1) residual phi with intercept, and sample spread standard deviations.
- The shoulder window uses 500-day rolling metrics strictly after the fixed 500d core end and through `2023-01-31`.
- For odd first/second-half splits, the first half is the first `n//2` observations and the second half is the remainder; the output records both counts.
- Part 4 is descriptive numeric output only; this run makes no RL recommendation and no training-window selection.

## Output Files

- `analysis\claim_002_healthy_episode_characterization\codex_tier_a\rolling_metrics.csv` final SHA256 `608bdf881eed718c4f51c78715b17532b5d5a09448691e5b67ed2abf679bb206`
- `analysis\claim_002_healthy_episode_characterization\codex_tier_a\episode_boundary_candidates.csv` final SHA256 `d5e96c25b59b90bd05440ba555cf6348ec13965fdfd8f99e1f95c112f8c7a696`
- `analysis\claim_002_healthy_episode_characterization\codex_tier_a\episode_regime_summary.csv` final SHA256 `41c4dfb6a167d51c2db37292489a1b669456bae6fd05b58ca95b79234d3e605d`
- `analysis\claim_002_healthy_episode_characterization\codex_tier_a\subregime_tests.csv` final SHA256 `3dbd28f0c6caf9c54a2d60e954e5c7630bfbe0649039885df12041e983c9c0e4`
- `analysis\claim_002_healthy_episode_characterization\codex_tier_a\degradation_diagnostics.csv` final SHA256 `9b15fe939fd3238255ca40ba24a02d98c94a0357eeaa28c8849ae7c6afcbec53`
