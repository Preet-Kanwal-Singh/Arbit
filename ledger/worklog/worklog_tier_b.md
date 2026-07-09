# Worklog — Tier B Entries

Maintained by Desktop Claude A (Ledger Keeper). Bundled Tier B numeric
outputs — split out of `ledger/worklog.md` on 2026-07-07 per Preet's
decision — see `ledger/decisions.md`, 2026-07-07 entry ("Worklog split by
label"). See `ledger/worklog.md` for the index across all labels.

Per base context §4: no dual-reproduction requirement, no formal ledger
review, no `VERIFIED_FACTS.md` path for anything in this file. Each entry
below is a single provenance-stamped numeric output, appended as-is when
produced — not decision-gating.

---

<!--
script_path: C:\Users\preet\OneDrive\Desktop\Skool\Arbit\analysis\wq_beta_instability_vs_eg_ordering_tier_b\beta_vs_eg.py
git_commit: 1717ffb3ed62e6b502d7c6ef2791545737673d89
snapshot_id: tcs_infy_v1_2026-07-04
timestamp_utc: 2026-07-07T09:42:01.920638+00:00
output_content_sha256: dbb19ffe48ad2451f7f99b4b12385e0e9ae00dffe13362c7564d59d2a714a5da
-->

## wq_beta_instability_vs_eg_ordering_tier_b

| Core | Mean β | Std β | β Instability Onset | EG Loss Onset | Which First |
|---|---|---|---|---|---|
| 500d | 0.681181 | 0.103646 | 2023-06-30 | 2022-01-31 | eg_loss |
| 730d | 0.670869 | 0.024954 | 2023-08-31 | 2023-04-28 | eg_loss |

<!--
script_path: C:\Users\preet\OneDrive\Desktop\Skool\Arbit\analysis\wq_earliest_warning_metric_4way_tier_b\four_way_rank.py
git_commit: 1717ffb3ed62e6b502d7c6ef2791545737673d89
snapshot_id: tcs_infy_v1_2026-07-04
timestamp_utc: 2026-07-07T09:42:12.344333+00:00
output_content_sha256: b22b27d2be3913cd91fdc3354050a6ebd3418bdbee69a00a94c07f4f7a76d44c
-->

## wq_earliest_warning_metric_4way_tier_b

| Core | EG Onset | HL Onset | β Onset | ADF Onset | Rank 1 to 4 |
|---|---|---|---|---|---|
| 500d | 2022-01-31 | 2023-04-28 | 2023-06-30 | 2023-12-29 | EG -> HL -> Beta -> ADF |
| 730d | 2023-04-28 | 2023-04-28 | 2023-08-31 | 2024-02-29 | EG -> HL -> Beta -> ADF |

<!--
script_path: C:\Users\preet\OneDrive\Desktop\Skool\Arbit\analysis\wq_earliest_warning_metric_4way_normalized_tier_b\four_way_normalized.py
git_commit: 1717ffb3ed62e6b502d7c6ef2791545737673d89
snapshot_id: tcs_infy_v1_2026-07-04
timestamp_utc: 2026-07-07T09:55:42.197462+00:00
output_content_sha256: 9cc2e9afb5d10d3b9bf9f87c4257ef539c65fe626d0b98b82907a2be355ea9b1
-->

## wq_earliest_warning_metric_4way_normalized_tier_b

| Core | EG Onset | HL Onset | β Onset | ADF Onset | Rank 1 to 4 |
|---|---|---|---|---|---|
| 500d | 2022-01-31 | 2022-03-31 | 2023-06-30 | 2022-01-31 | EG -> ADF -> HL -> Beta |
| 730d | 2023-04-28 | 2023-04-28 | 2023-08-31 | 2023-04-28 | EG -> HL -> ADF -> Beta |
<!--
script_path: C:\Users\preet\OneDrive\Desktop\Skool\Arbit\analysis\wq_residual_variance_volatility_vs_cluster_tier_b\six_way_normalized.py
git_commit: 1717ffb3ed62e6b502d7c6ef2791545737673d89
snapshot_id: tcs_infy_v1_2026-07-04
timestamp_utc: 2026-07-07T14:49:39.116345+00:00
output_content_sha256: 489b04155b2b896eb287706d30a55acf50fe44047b931fc2867af99c71235112
-->

## wq_residual_variance_volatility_vs_cluster_tier_b

| Core | EG Onset | HL Onset | ADF Onset | β Onset | Resid Var Onset | Vol Onset | Rank Grouped |
|---|---|---|---|---|---|---|---|
| 500d | 2022-01-31 | 2022-03-31 | 2022-01-31 | 2023-06-30 | 2024-01-31 | None | {ADF, EG} -> HL -> β -> ResidVar |
| 730d | 2023-04-28 | 2023-04-28 | 2023-04-28 | 2023-08-31 | 2024-01-31 | None | {ADF, EG, HL} -> β -> ResidVar |

<!--
script_path: C:\Users\preet\OneDrive\Desktop\Skool\Arbit\analysis\wq_hurst_onset_dfa_tier_b\dfa_hurst.py
git_commit: 1717ffb3ed62e6b502d7c6ef2791545737673d89
snapshot_id: tcs_infy_v1_2026-07-04
timestamp_utc: 2026-07-08T04:37:54.708221+00:00
output_content_sha256: 916030a6a2d53b212325c7a4bfede6de8a3deed1206cd36a038976a325cff357
-->

## wq_hurst_onset_dfa_tier_b

| Core | Mean H | Std H | Hurst Onset Date |
|---|---|---|---|
| 500d | 1.108249 | 0.117354 | 2024-04-30 |
| 730d | 1.000113 | 0.092260 | 2024-04-30 |

*FLAGGED, 2026-07-08 (Claude B): a synthetic AR(1)(φ=0.9) control — stationary, no genuine long-memory — reproduces H≈0.90–1.05 under this same `min_s=30` box-size range, indistinguishable from the real-data values above. Given `phi_post`'s 95% CI already touches the unit-root boundary in the 500d post-transition period (see `claim_003_eg_halflife_ordering_robustness`), this onset is very likely re-detecting the same φ-driven deterioration already captured by EG/ADF/half-life — not an independent signal. No pre-whitening, surrogate-data null, or bias-corrected estimator has been applied; do not cite this as a 7th independent onset metric until that's done, or drop Hurst from the candidate list.*

<!--
script_path: C:\Users\preet\OneDrive\Desktop\Skool\Arbit\analysis\wq_healthy_core_leading_drift_tier_b\core_drift.py
git_commit: 1717ffb3ed62e6b502d7c6ef2791545737673d89
snapshot_id: tcs_infy_v1_2026-07-04
timestamp_utc: 2026-07-08T05:24:41.443926+00:00
output_content_sha256: 85992d20f7d67596e8f7601acdf7bbe9b98d23d4e3773de825e1922c93c66f22
-->

## wq_healthy_core_leading_drift_tier_b

| Core | Metric | N Obs | Slope | HAC t-stat | HAC p-value | Direction |
|---|---|---|---|---|---|---|
| 500d | engle_granger_p_value | 24 | 1.058956e-03 | 2.5538 | 1.0654e-02 | Rising |
| 500d | half_life | 24 | 2.362808e-02 | 0.5838 | 5.5938e-01 | Rising |
| 500d | beta | 24 | -7.268894e-03 | -1.6089 | 1.0765e-01 | Falling |
| 500d | spread_std | 24 | -3.828544e-04 | -2.7267 | 6.3970e-03 | Falling |
| 730d | engle_granger_p_value | 28 | 1.522349e-04 | 1.2862 | 1.9838e-01 | Rising |
| 730d | half_life | 28 | 1.701021e-02 | 0.2630 | 7.9255e-01 | Rising |
| 730d | beta | 28 | -1.890893e-03 | -2.0804 | 3.7487e-02 | Falling |
| 730d | spread_std | 28 | -4.929643e-04 | -3.9657 | 7.3181e-05 | Falling |

*Note: Given how much the rolling windows overlap relative to each core's own length, the prescribed Newey-West lag count is very likely an under-correction, not a full fix — in the 730d core especially, most observations may share the bulk of their underlying daily data with each other. Report this as descriptive/exploratory. Do not treat the HAC p-values as validated significance claims.*

<!--
script_path: C:\Users\preet\OneDrive\Desktop\Skool\Arbit\analysis\wq_phi_redundancy_test_tier_b\phi_redundancy.py
git_commit: 1717ffb3ed62e6b502d7c6ef2791545737673d89
snapshot_id: tcs_infy_v1_2026-07-04
timestamp_utc: 2026-07-08T09:42:06.322669+00:00
output_content_sha256: 6596dcd3c48e3dcc89302a6c9b10b991beef0166ace0dbad4c11674e1e2a407d
-->

## wq_phi_redundancy_test_tier_b

### 500d Core
| Metric | R²/Corr | n_eff | Verdict |
|---|---|---|---|
| Residual Variance | Corr: -0.8131 | 2.1 (ρ=0.95) | No Structure (|t|=0.83) |
| EG p-value | R2: 0.9190 | 16.7 (ρ=0.65) | No Structure (|t|=0.70) |
| ADF p-value | R2: 0.9347 | 15.8 (ρ=0.66) | No Structure (|t|=0.76) |

### 730d Core
| Metric | R²/Corr | n_eff | Verdict |
|---|---|---|---|
| Residual Variance | Corr: -0.8784 | 1.4 (ρ=0.96) | No Structure (|t|=1.29) |
| EG p-value | R2: 0.9540 | 11.8 (ρ=0.70) | No Structure (|t|=0.32) |
| ADF p-value | R2: 0.9710 | 7.3 (ρ=0.80) | No Structure (|t|=0.29) |

### Classification Summary
- **500d window**: Case 1 (pure redundancy). 0/3 metrics showed significant post-Jan-2024 structure beyond AR(1) redundancy.
- **730d window**: Case 1 (pure redundancy). 0/3 metrics showed significant post-Jan-2024 structure beyond AR(1) redundancy.

<!--
script_path: C:\Users\preet\OneDrive\Desktop\Skool\Arbit\analysis\wq_phi_redundancy_test_tier_b\phi_redundancy.py
git_commit: 1717ffb3ed62e6b502d7c6ef2791545737673d89
snapshot_id: tcs_infy_v1_2026-07-04
timestamp_utc: 2026-07-08T09:54:12.243369+00:00
output_content_sha256: 1cbf5c583f4332e1037ac6983ef53432c06b132574d0cc4e216946613f025105
superseded_entry: wq_phi_redundancy_test_tier_b (2026-07-08 run -- classification
  logic did not use the reported correlation diagnostic, and the levels
  regression was not checked for spurious-regression risk)
-->

## wq_phi_redundancy_test_tier_b_v2

### 500d Core
| Metric | R2 (levels) | ADF-on-resid p | R2 (first-diff, PRIMARY) | n_eff | Shift verdict |
|---|---|---|---|---|---|
| Residual Variance (sigma_eps_sq) | 0.6611 | 0.0025 (OK (resid stationary)) | 0.3491 | 56.7 (rho=0.15) | No Structure (|t|=0.90) |
| EG p-value (logit) | 0.9190 | 0.0016 (OK (resid stationary)) | 0.5961 | 134.5 (rho=-0.27) | No Structure (|t|=0.44) |
| ADF p-value (logit) | 0.9347 | 0.0002 (OK (resid stationary)) | 0.6342 | 140.0 (rho=-0.29) | No Structure (|t|=0.18) |

### 730d Core
| Metric | R2 (levels) | ADF-on-resid p | R2 (first-diff, PRIMARY) | n_eff | Shift verdict |
|---|---|---|---|---|---|
| Residual Variance (sigma_eps_sq) | 0.7717 | 0.0540 (SPURIOUS RISK (resid non-stationary)) | 0.2093 | 80.3 (rho=-0.10) | No Structure (|t|=1.34) |
| EG p-value (logit) | 0.9540 | 0.0007 (OK (resid stationary)) | 0.5767 | 65.6 (rho=0.00) | No Structure (|t|=0.19) |
| ADF p-value (logit) | 0.9710 | 0.0077 (OK (resid stationary)) | 0.7309 | 50.3 (rho=0.14) | No Structure (|t|=0.02) |

### Classification Summary
- **500d window**: Case 1 (pure redundancy). 0/3 metrics show real independent information (low first-differenced R2 against phi, and/or a genuine post-Jan-2024 shift in the differenced-regression residuals).
- **730d window**: Case 2 (partial redundancy). 1/3 metrics show real independent information (low first-differenced R2 against phi, and/or a genuine post-Jan-2024 shift in the differenced-regression residuals).

*Methodology note: classification is now based on the FIRST-DIFFERENCED regression R2 and the shift test on ITS residuals, not the levels R2. The levels R2 and the ADF-on-residuals check are reported for reference and to flag spurious-regression risk (two trending series can produce a high levels R2 with no real relationship) -- treat a large gap between levels R2 and first-diff R2, combined with a non-stationary levels residual, as a sign the levels R2 was inflated.*
<!--
script_path: C:\Users\preet\OneDrive\Desktop\Skool\Arbit\analysis\wq_recompute_episode1_beta_range\recompute_episode1_beta_range.py
git_commit: 1717ffb3ed62e6b502d7c6ef2791545737673d89
snapshot_id: tcs_infy_v1_2026-07-04
timestamp_utc: 2026-07-08T14:51:53.711498+00:00
output_content_sha256: 45b46af0089fc4f84d9a4cbf832db192b9eaef16e5b3a924351dab7697669947
-->

## wq_recompute_episode1_beta_range

# Episode 1 Recomputed Beta Range

This is a descriptive reconstruction of the rolling beta range observed during Episode 1 (2018-01-01 to 2023-12-31), computed directly from the frozen snapshot (`tcs_infy_v1_2026-07-04`).

**These values supersede the previously untraceable "0.20–1.91" figure, which is now deprecated.**

## Descriptive Statistics
- **Minimum β:** -0.832086
- **Maximum β:** 2.306484
- **Mean β:** 0.600324
- **Median β:** 0.644011
- **Standard Deviation:** 0.290498
- **First Observation:** 2018-03-28 (window: 60d, β: 0.871890)
- **Last Observation:** 2023-12-29 (window: 730d, β: 0.462287)
- **Number of Observations:** 282 month-end β calculations (across all defined rolling windows)

*Note: No smoothing, filtering, thresholding, or statistical inference was applied. The computation strictly followed the established rolling-beta implementation on the frozen snapshot.*

<!--
script_path: C:\Users\preet\OneDrive\Desktop\Skool\Arbit\analysis\wq_recompute_episode1_beta_range_v2\recompute_episode1_beta_range_v2.py
git_commit: 1717ffb3ed62e6b502d7c6ef2791545737673d89
snapshot_id: tcs_infy_v1_2026-07-04
timestamp_utc: 2026-07-09T04:19:17.692341+00:00
output_content_sha256: 0726281b720108c90a0c9be9052bc03e96ca0b2b821b79d3c0f9309cc173b564
-->

## wq_recompute_episode1_beta_range_v2

> **Deviations from v1:**
> 1. Fixed the date range to map strictly to the established 500d and 730d cores from `VERIFIED_FACTS.md` instead of a generic 2018-2023 boundary.
> 2. Fixed the pooled window length issue: used 500d for the 500d core, and 730d for the 730d core, strictly separate.
> 3. Fixed `beta_series.csv` column format by emitting two specific CSVs containing only `date` and `beta`.
> 4. Fixed `provenance.json` serialization by exporting it as a standalone file instead of relying on manual copying.

# Episode 1 Recomputed Beta Range v2

This descriptive reconstruction replaces both the historically untraceable "0.20–1.91" figure and the flawed v1 recomputation (which incorrectly pooled multiple window lengths over an unestablished 2018–2023 date range).

The values below establish the authoritative reference for Episode 1 beta ranges, computed individually for each of the two established healthy cores using their matching window lengths, straight from the frozen snapshot (`tcs_infy_v1_2026-07-04`).

## 500d Strict Core (2020-01-31 to 2021-12-31)
- **Minimum β:** 0.545092
- **Maximum β:** 0.977381
- **Mean β:** 0.681181
- **Median β:** 0.659427
- **Standard Deviation:** 0.103646
- **First Observation:** 2020-01-31 (β: 0.977381)
- **Last Observation:** 2021-12-31 (β: 0.666108)
- **Number of Observations:** 24 month-end β calculations

## 730d Strict Core (2020-12-31 to 2023-03-31)
- **Minimum β:** 0.647704
- **Maximum β:** 0.749515
- **Mean β:** 0.670869
- **Median β:** 0.662592
- **Standard Deviation:** 0.024954
- **First Observation:** 2020-12-31 (β: 0.749515)
- **Last Observation:** 2023-03-31 (β: 0.663902)
- **Number of Observations:** 28 month-end β calculations

*Note: No smoothing, filtering, thresholding, or statistical inference was applied. The computation strictly followed the established rolling-beta implementation on the frozen snapshot.*

