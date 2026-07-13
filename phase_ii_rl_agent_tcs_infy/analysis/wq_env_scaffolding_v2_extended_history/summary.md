# Summary: Tier C — Extend Historical Coverage (v3/v4 Snapshots)

## Work Completed
1. **Extended History Snapshots**: Created two new snapshots (`tcs_infy_v3_2026-07-13` for close-only and `tcs_infy_v4_2026-07-13` for OHLCV) starting from `2017-10-01` rather than `2018-01-01`. This ensures there is ample history (greater than the 750 trading days required) before the start of the 730d core episode (`2020-12-31`), safely supporting the 730d window plus the 20d offset needed for `eg_p_trend`.
2. **Metadata Updates**: Updated the `purpose` string for both snapshots, correctly declaring that they extend coverage to support the `eg_p_trend` lookback requirement, rather than rebasing the primary analysis window. I clearly differentiated the close-only (v3) and full OHLCV (v4) lineages within the sequentially numbered family. The volume-policy caveat was properly maintained and expanded for the v4 OHLCV data.
3. **Reverted Registry Fallback**: Removed the graceful seeding (ValueError fallback logic) in `feature_registry.py`'s `_log_price_window`. The registry once again correctly demands exact strict spans via `slice_trailing_bars`, raising an explicit `ValueError` if the data isn't there, ensuring the integrity of the rolling window for phase I features.
4. **New Versioned Acceptance Test**: Copied and transitioned the acceptance test to `wq_env_scaffolding_v2_extended_history/run_acceptance_test.py`. 
    - Pointed the environment default snapshot parameter in this explicit test runner to `tcs_infy_v4_2026-07-13`.
    - Added an explicit test to guarantee that the first 10 steps of the 730d core produce valid non-NaN and non-infinity feature outputs (to specifically test the scenario where it used to crash from an insufficient `t-20` lookback).
5. **No Changes to Default Defaults**: Validated that `data_loader.py` remains unchanged (maintaining explicit snapshot requirement).

## Deliverables
- `phase_ii_rl_agent_tcs_infy/analysis/create_tcs_infy_snapshot_v3/codex/` and its outputs
- `phase_ii_rl_agent_tcs_infy/analysis/create_tcs_infy_snapshot_v4/codex/` and its outputs
- `phase_ii_rl_agent_tcs_infy/analysis/wq_env_scaffolding_v2_extended_history/` populated with tested results.
- Stamped `provenance.json` for all three run logs.
- All modifications neatly encapsulated in `feat/phase2_tier_c_extended_history`.
