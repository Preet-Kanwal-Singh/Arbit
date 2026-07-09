<!--
    "snapshot_id": "tcs_infy_v1_2026-07-04",
  "git_commit": "1717ffb3ed62e6b502d7c6ef2791545737673d89",
  "script_path": "C:\\Users\\preet\\OneDrive\\Desktop\\Skool\\Arbit\\analysis\\wq_recompute_episode1_beta_range\\recompute_episode1_beta_range.py",
  "execution_timestamp_utc": "2026-07-08T14:51:53.711498+00:00",
  "outputs": {
    "beta_series.csv": "6910dc26275f066a311057ec66d8d9b66c72d3f00abbf30b4385b218bd4f098e",
    "summary.md": "45b46af0089fc4f84d9a4cbf832db192b9eaef16e5b3a924351dab7697669947"
-->

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
