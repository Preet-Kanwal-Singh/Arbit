# Claim 005 Volume Event Study — Independent Tier A Implementation

## Individual Reproduction Result

| gamma | HC3_SE | test_statistic | one_sided_p_gamma_gt_0 | p_lt_0_05 | individual_result |
| --- | --- | --- | --- | --- | --- |
| -0.1575329760 | 0.0680480035 | -2.3150271553 | 0.989694277 | False | DOES_NOT_REACH_P_LT_0.05 |

Cross-implementation status is intentionally not assigned by this script. The second
independent reproduction must be compared using the pre-declared coefficient tolerance
`|gamma_A - gamma_B| <= 0.03`, finite HC3 standard errors in both runs, and the claim's
outcome rules.

## Event Window

- Anchor date: `2021-12-31`.
- Definition: the 20 merged-calendar trading days immediately preceding the anchor,
  `[-20,-1]`.
- First event date: `2021-12-03`.
- Last event date: `2021-12-30`.
- The event window was fixed before zero-volume rows were dropped.

## Model

`ln(TCS_Volume_t) = alpha + beta * ln(NSEI_Volume_t) + day-of-week dummies + gamma * EventWindowDummy_t + epsilon_t`

- Natural logarithms throughout.
- Monday is the omitted day-of-week category.
- HC3 robust covariance.
- One-sided alternative: `gamma > 0`.
- One-sided p-value uses the asymptotic standard-normal tail of `gamma / HC3_SE`.

## Data Handling

- TCS snapshot: `tcs_infy_v2_2026-07-11`.
- Benchmark snapshot: `nifty_it_benchmark_v1_2026-07-11`; only `^NSEI` is used.
- Estimation bounds: `2018-09-06` through `2026-07-10`.
- TCS and NSEI are inner-joined on date.
- Exact unmatched-date counts and zero-volume diagnostics are in
  `data_quality_report.csv`.
- Exact zero-volume rows removed after event-window construction are in
  `dropped_zero_volume_dates.csv`.
- Exact event dates are in `event_window_dates.csv`.

## Required Limitation

This claim tests a window anchored to claim_002's admitted healthy-core boundary (2021-12-31), not the window explored in the prior Tier B pass (2022-01-31, an unadmitted date; open_questions.md #18 remains open). The two prior exploratory runs tested a different window and do not constitute prior replication of this specific result. This window was selected because a nearby window showed a strong result in that unadmitted exploratory pass; therefore a bare p<0.05 pass here should not be weighted as equivalent evidence to a pre-registered blind test. If cross-implementation agreement is achieved, the permanent positive outcome label is REPRODUCED-ADJACENT-WINDOW, not REPRODUCED.

## Non-Goals

This implementation does not confirm or deny the original Tier B finding for the window
before `2022-01-31`. It does not re-test the 730d core or INFY.
