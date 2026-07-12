<!--
script_path: C:\Users\preet\OneDrive\Desktop\Skool\Arbit\phase_i_tcs_infy_pairs_trading\analysis\claim_005_volume_event_study_tcs500d\opus_tier_a\run_claim_005.py
git_commit: c4b24437d5c562dd064e1c2e5235a55fe88f0920
tcs_snapshot_id: tcs_infy_v2_2026-07-11
nsei_snapshot_id: nifty_it_benchmark_v1_2026-07-11
timestamp_utc: 2026-07-12T09:58:27.737545+00:00
output_content_sha256: 8312b148a67796f2f472e7aae36695b8160b521368b5b0588c8484cd6c27d41e
-->

# Volume Event Study -- TCS.NS 500d-Core Boundary (Opus Tier A)

## Result

- **gamma (event window coefficient):** -0.156259
- **HC3 standard error:** 0.068244
- **t-statistic:** -2.2897
- **p-value (one-sided, H1: gamma > 0):** 0.988981
- **Conclusion:** not significant at the 0.05 level

## Outcome Label

If the paired reproduction (Codex Tier A) also finds p < 0.05 one-sided,
|gamma_A - gamma_B| <= 0.03, and both report finite HC3 SE, the verdict is:

**REPRODUCED-ADJACENT-WINDOW**

This exact label is deliberate and permanent. It is NOT equivalent to plain
"REPRODUCED." See Required Limitation below.

Other possible outcomes:
- **DISPUTED-BORDERLINE** -- tolerance met, significance conclusions differ
- **DISPUTED-VALUE** -- coefficients disagree beyond tolerance (|gamma_A - gamma_B| > 0.03)
- Neither reproduction reaches p < 0.05: claim does not reproduce (no special tag)

## Required Limitation

This claim tests a window anchored to claim_002's admitted healthy-core
boundary (2021-12-31), not the window explored in the prior Tier B pass
(2022-01-31, an unadmitted date -- see open_questions.md #18, still open).
The two prior exploratory runs that motivated this Tier A escalation tested
a different window and do not constitute prior replication of this specific
result. The window was selected because a nearby window showed a strong
result in that unadmitted exploratory pass -- readers should weight a bare
p < 0.05 pass here accordingly, not as equivalent evidence to a
pre-registered blind test.

This spec tests exactly one window definition (20 trading days, anchored to
end-of-day 2021-12-31, i.e. [-20,-1] trading days). Alternative nearby
specifications -- 15 or 25 trading days, or anchoring one day earlier/later
-- were not tested and must not be assumed to produce the same result.
Testing alternatives here would reopen the exact multiple-comparisons
problem this claim was rewritten to avoid, so none were tried; this is a
deliberate scope limit, not an oversight.

## Data Quality

- **Merged sample (before zero-drop):** 1930 observations
- **Zero-volume rows dropped:** 23 (dates: 2018-09-11, 2018-09-24, 2018-10-10, 2018-10-25, 2018-11-06, 2018-11-15, 2018-11-26, 2018-11-27, 2020-02-17, 2020-09-17, 2021-03-08, 2021-04-07, 2021-05-27, 2021-07-14, 2022-08-16, 2023-03-22, 2023-08-16, 2024-02-19, 2024-04-01, 2024-07-01, 2024-07-02, 2024-07-03, 2025-03-18)
- **Zero-volume dates in event window:** 0
- **Regression sample:** 2018-09-06 to 2026-07-10 (1907 observations)
- **TCS-only dates dropped (in range):** 7
- **NSEI-only dates dropped (in range):** 0
- **Event window observations in regression:** 20
- **Log base:** natural log (ln)

## Event Window

20 trading days at positions [-20, -1] before 2021-12-31:
- Start: 2021-12-03
- End: 2021-12-30

## Model

```
log(TCS_Volume_t) = a + b*log(NSEI_Volume_t) + DOW_dummies + g*EventWindow_t + e_t
```

HC3 robust standard errors. Day-of-week dummies: Mon-Thu (Friday = reference).
One-sided test: H1: gamma > 0.

## Non-goals

Does not confirm or deny the original Tier B finding (window before
2022-01-31) -- that remains open, tracked separately. Does not re-test
730d or INFY. Does not test window-length sensitivity.
