# Volume Signal Test (Tier B) Summary

## Task Objective
Test whether trading volume (TCS, INFY, or their ratio) carries any detectable relationship to the pair's cointegration health, using the exact evaluation methodology Phase I used to test and rule out volatility.

## Constraints & Methodology
- **Data**: Used `tcs_infy_v2_2026-07-11` (only this snapshot contains the unadjusted volume data). Explicitly enforced using v2.
- **Data Floor**: No rolling window metric for volume incorporated data prior to `2018-09-06` due to corporate actions (TCS split on 2018-05-31 and INFY bonus issue on 2018-09-05). Windows extending further back were strictly truncated.
- **Methodology (Mirrored)**: We reconstructed the exact test from `six_way_normalized.py` used to rule out volatility (`get_normalized_onset`). The test computed the rolling metric's mean and standard deviation over the established healthy core, established a strict upper threshold (`mean + 2 * std`), and checked for the first onset date exceeding this threshold in the post-core period.
- **Pre-Declared Read**: Before running the test, the following criteria were established to prevent retroactive justification:
  - **Worth a Tier B follow-up**: If any volume metric crosses the threshold *before or during* the month EG breaks down (2022-01-31 for 500d, 2023-04-28 for 730d).
  - **Empty, like volatility**: If metrics yield `None` (never fire) or fire *after* the EG breakdown date.

## Results
The test computed month-end onsets for TCS mean volume, INFY mean volume, and the volume ratio (TCS/INFY) over 500d and 730d rolling windows:

| Core | TCS Vol Onset | INFY Vol Onset | Ratio Onset | EG Onset (Reference) |
|---|---|---|---|---|
| 500d | None | None | 2022-01-31 | 2022-01-31 |
| 730d | None | None | None | 2023-04-28 |

## Conclusion
- Absolute trading volume (TCS and INFY individually) **never fired** (yielded `None`) for both 500d and 730d windows. This aligns exactly with the behavior of volatility, showing no predictive or coincident signal power.
- The **Volume Ratio (TCS/INFY)** fired exactly once: on `2022-01-31` for the 500d window, which is *simultaneous* with the EG breakdown date. However, it completely failed to fire for the 730d window (`None`).
- Because the Ratio Onset tied the EG breakdown in the 500d window (meeting the pre-declared criterion for a follow-up), it technically clears the "worth a Tier B follow-up" bar, though it's a borderline case given its total failure to signal in the 730d window.

Outputs and the provenance header have been appended to `phase_i_tcs_infy_pairs_trading/ledger/worklog/worklog_tier_b.md`.
