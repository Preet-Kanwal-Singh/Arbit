<!--
script_path: C:\Users\preet\OneDrive\Desktop\Skool\Arbit\analysis\claim003\codex\run_claim003_eg_halflife_ordering_robustness.py
git_commit: dcd5f465aff03bbcf448a8e845767d364cfae098
snapshot_id: tcs_infy_v1_2026-07-04
timestamp_utc: 2026-07-06T09:30:39.968404+00:00
output_content_sha256: 1aa0cd1cae4be23c7cddf6c2395750e940fbb9a120ffaa32303ded880171709f
output_hash_scope: bytes after this HTML provenance header
final_file_sha256: recorded in output_manifest.csv
-->
# Claim 003 EG Half-Life Ordering Robustness - Codex

## Study-Level Result

CONTRADICTED

## Window Summary

| window_length | classification | well_powered | parameter_stable | min_effective_N | max_effective_N | phi_pre | phi_post | phi_post_ci_high |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 500 | ROBUST | True | False | 351 | 1118 | 0.950351 | 0.988012 | 1.004286 |
| 730 | CONTRADICTED | True | True | 255 | 455 | 0.961848 | 0.883325 | 0.942900 |

## Cell Summary

| window_length | config_id | effective_N | p_hat_EG_first_given_ordered | ci95_low | ci95_high | adequate_N | classification | parameter_unstable | real_actual_order |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 500 | C1 | 924 | 0.9946 | 0.9874 | 0.9982 | True | ROBUST | True | EG_FIRST |
| 500 | C2 | 971 | 1.0000 | 0.9962 | 1.0000 | True | ROBUST | True | EG_FIRST |
| 500 | C3 | 755 | 0.9656 | 0.9499 | 0.9774 | True | ROBUST | True | EG_FIRST |
| 500 | C4 | 351 | 0.7578 | 0.7095 | 0.8017 | True | ROBUST | True | EG_FIRST |
| 500 | C5 | 1118 | 0.9991 | 0.9950 | 1.0000 | True | ROBUST | True | EG_FIRST |
| 730 | C1 | 266 | 0.2744 | 0.2217 | 0.3323 | True | CONTRADICTED | False | SIMULTANEOUS |
| 730 | C2 | 278 | 0.7842 | 0.7311 | 0.8311 | True | ROBUST | False | SIMULTANEOUS |
| 730 | C3 | 255 | 0.0784 | 0.0486 | 0.1185 | True | CONTRADICTED | False | HL_FIRST |
| 730 | C4 | 455 | 0.0154 | 0.0062 | 0.0314 | True | CONTRADICTED | False | SIMULTANEOUS |
| 730 | C5 | 298 | 0.9765 | 0.9522 | 0.9905 | True | ROBUST | False | EG_FIRST |

## Method Notes

- Claim id: `claim_003_eg_halflife_ordering_robustness`.
- Snapshot: `tcs_infy_v1_2026-07-04`, `adjusted_close.csv`, no substitution or refresh.
- Replicates: `2000`. Seed: `42`.
- Rolling pipeline: log adjusted closes; TCS dependent, INFY regressor; intercept-inclusive OLS slope beta; residual spread equals `log(TCS) - (alpha + beta * log(INFY))` for ADF and half-life. This matches the claim 002 core-boundary convention used by the supplied strict healthy cores.
- Engle-Granger call: `statsmodels.tsa.stattools.coint(trend="c", autolag="aic")`.
- Residual ADF call: `adfuller(regression="n", autolag="aic")`.
- Half-life: `-log(2) / log(phi)` for `0 < phi < 1`, `inf` for `phi >= 1`, and blank/NaN for `phi <= 0`.
- Fixed-transition simulation: pre parameters are estimated on the strict core and applied to the full simulated pre-transition history needed by the rolling windows; post parameters start after the fixed core-end transition.
- INFY return process is AR(1) on daily log returns with a residual pool; this preserves first-order serial correlation, not volatility clustering.
- Real-data crossing dates are anchors only and are not used in the simulation classification.
- 500d and 730d cores/degradation windows overlap; non-robust or window-length-dependent results reflect overlapping procedures, not independent procedures.

## Output Hashes

- `analysis\claim003\codex\cell_results.csv` final SHA256 `683d190c2558323b24a0c4a4720eebc365d8631f49ca39a67037c01e75b68408`
- `analysis\claim003\codex\window_summary.csv` final SHA256 `27eba15ad123428cd70fa978d94e6860ad751df82fe9aea4752c15c6d4cc359f`
- `analysis\claim003\codex\regime_parameters.csv` final SHA256 `5ae961ac68099e6fdbd132378e2b818e27739b4101ba2ee4e1e40e88bef20250`
- `analysis\claim003\codex\real_data_anchors.csv` final SHA256 `a4f41dc3d4f75b3959800ca36fa2d39eefab33f84b706af054881546f1a70bf4`
- `analysis\claim003\codex\real_rolling_metrics.csv` final SHA256 `497d9246ce66b6fd2e4253249c4faa260b897e839deb765918ac73d96c0814cf`
- `analysis\claim003\codex\provenance.json` final SHA256 `ebe1b3fee596277086384a51be170e8ff26277b616195077c965fc98cfbfac97`
