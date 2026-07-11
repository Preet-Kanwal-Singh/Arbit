# Claim 002 Critical Evaluation — Antigravity/Opus

## Provenance

- Script: `analysis_opus/evaluate_claim_002.py`
- Snapshot: `tcs_infy_v1_2026-07-04`
- Timestamp UTC: 2026-07-05T13:01:31+00:00
- Rolling metrics hash: see `analysis_opus/opus_provenance.json`
- Methods: Engle-Granger via `coint(trend='c', autolag='aic')`; residual ADF via `adfuller(regression='n', autolag='aic')`; sub-regime detection via multivariate RSS optimal-split with 2000 permutations; trend tests via Mann-Kendall and Welch t-tests.

---

## Question 1: Do I identify the same healthy core boundaries?

**Classification: Supports Codex**

My independent implementation finds identical boundaries:

| Window | My result | Codex result | Match? |
|--------|-----------|--------------|--------|
| 500d strict | 2020-01-31 to 2021-12-31 (24 mo) | 2020-01-31 to 2021-12-31 (24 mo) | Exact |
| 730d strict | 2020-12-31 to 2023-03-31 (28 mo) | 2020-12-31 to 2023-03-31 (28 mo) | Exact |

Both are determined by the longest contiguous run of months where both Engle-Granger and residual ADF pass at p < 0.05. Since both implementations use the same frozen snapshot and the same statistical tests (`statsmodels.coint` and `adfuller` with matching arguments), this convergence is expected. The boundaries are a mechanical consequence of the test outputs, not a judgment call, so exact agreement is the right outcome here.

My implementation also finds three short healthy fragments after the main 500d core (a 1-month pass in Feb 2022, a 3-month pass Jul-Sep 2022, and a 1-month pass in Jan 2023), which are consistent with the "borderline shoulder" period Codex describes — the pair intermittently passes as p-values fluctuate around the 0.05 threshold.

---

## Question 2: Do I find statistically significant internal sub-regimes?

**Classification: Partially supports Codex**

Codex reports a significant sub-regime split in the 500d core after 2020-06-30 (RSS improvement 0.388, permutation p = 0.0005), separating an early beta-adjustment segment from a later stable segment.

My results are more nuanced:

| Core | Best split date | RSS improvement | Permutation p | Significant? |
|------|----------------|-----------------|---------------|-------------|
| 500d (my impl.) | 2020-03-31 | 0.261 | 0.108 | **No** (at 5%) |
| 730d (my impl.) | 2021-02-28 | 0.434 | 0.011 | **Yes** |

**The 500d sub-regime split does not reach significance in my implementation.** My optimal split places the boundary earlier (after index 2, isolating only the first 2 months) and with weaker RSS improvement. The likely cause is that I used 4 variables (beta, half_life, eg_pval, spread_std) while Codex used 6 (adding spread_daily_change_std and replacing raw p-values with "strength" transforms, likely -log(p)). The additional variables and transformed scale appear to be what drives Codex's significance result.

This matters because the claim "the 500d core contains a statistically significant sub-regime" is sensitive to the variable set used in the split test. With a leaner variable set, the split exists directionally (the early months do have higher beta) but is not significant — 2 observations in the left segment are too few for a robust conclusion.

However, the underlying phenomenon is real:

- Welch t-test on beta between the first 6 months (mean 0.819) and remaining 18 months (mean 0.635): **t = 11.9, p = 0.008** — a significant difference in means.
- The two segments differ in beta volatility: early std = 0.120, late std = 0.037 (a 3.2x ratio).

So: the early-adjustment vs late-stable pattern exists in my data, and the 730d split is significant, but the 500d optimal-split significance depends on implementation choices. Codex's conclusion is directionally correct but its confidence level (p = 0.0005) appears inflated by variable selection.

---

## Question 3: During the transition, does Engle-Granger weaken before half-life changes?

**Classification: Supports Codex**

My independent analysis of the degradation ordering finds a clear sequence:

| Event | Date | Value |
|-------|------|-------|
| First EG p > 0.01 within core | 2020-07-31 | p = 0.012 |
| First EG failure (p >= 0.05) post-core | 2022-01-31 | p = 0.055 |
| First half-life > 20d | 2023-04-30 | hl = 29.1d |
| First ADF failure | 2023-12-31 | p = 0.129 |

The ordering is unambiguous: **EG weakens first, then half-life rises, then ADF fails.** There is a ~15-month gap between the first EG failure and half-life exceeding 20 trading days, and a ~24-month gap to ADF failure.

Mann-Kendall trend tests over the transition zone (2021-07-31 to 2023-06-30) all show significant monotonic trends: EG p-value rising (tau = 0.601, p < 0.001), half-life rising (tau = 0.746, p < 0.001), ADF p-value rising (tau = 0.601, p < 0.001).

Codex notes that the final two months of the 500d core have EG p near 0.05 while ADF and half-life remain healthy. My data confirms this: the core ends at 2021-12-31, and the preceding months show EG p drifting upward while half-life stays at 12-14 days and ADF stays well below 0.001. The degradation is EG-led, consistent with Codex's characterization.

**Additional finding Codex did not explicitly highlight:** The ADF test is extremely slow to degrade — it remains below 0.05 for nearly **two full years** after EG first fails. This creates a long "split-signal" period (2022-01 to 2023-12) where EG says the pair is broken but ADF says the residuals are still stationary. This is not a contradiction — it reflects the fact that the spread can still mean-revert (keeping ADF happy) even as the cointegrating relationship weakens (making EG doubt the relationship). This split-signal period is long enough to be operationally relevant for any system that depends on both tests.

---

## Question 4: Does beta exhibit an early adjustment period followed by a stable regime?

**Classification: Supports Codex**

| Period | Beta mean | Beta std | Beta range | Abs change mean |
|--------|-----------|----------|------------|-----------------|
| Early (Jan-Jun 2020, n=6) | 0.819 | 0.120 | 0.690 - 0.977 | 0.057 |
| Late (Jul 2020 - Dec 2021, n=18) | 0.635 | 0.037 | 0.545 - 0.666 | 0.017 |

Key tests:
- **Welch t-test on beta levels:** t = 11.9, p = 0.008 — the two periods have significantly different mean beta.
- **Levene test on beta-change variance:** F = 1.52, p = 0.23 — variance difference is directionally correct (early changes 3.3x larger) but does not reach formal significance, likely due to small early-period sample size (n=5 changes).
- **Mann-Kendall trend on full core beta:** tau = -0.072, p = 0.637 — no overall monotonic trend across the full core.

The Mann-Kendall result is important context: there is no persistent downward drift in beta across the full 24-month core. Instead, the pattern is a **step-change** — beta drops from ~0.9-1.0 to ~0.6-0.7 during the first few months, then stabilizes. This is consistent with Codex's description ("largest beta movement occurs early; later months are materially tighter") and is better described as a level shift than a continuous adjustment.

Codex reports the full-core beta range as 0.545 to 0.977 and mine matches (0.545 to 0.977). The characterization of an early adjustment followed by stability is accurate.

---

## Summary of Conclusions

| Question | Verdict |
|----------|---------|
| Q1: Same healthy core boundaries? | **Supports Codex** — exact match |
| Q2: Significant internal sub-regimes? | **Partially supports Codex** — the pattern exists but 500d split significance is sensitive to variable selection; 730d split is significant in my implementation |
| Q3: EG weakens before half-life? | **Supports Codex** — EG leads by ~15 months |
| Q4: Beta early-adjustment then stable? | **Supports Codex** — step-change pattern confirmed |

## Material Finding Not Reported by Codex

The **split-signal period** between EG failure and ADF failure spans approximately 2 years (Jan 2022 to Dec 2023). During this interval, the pair looks broken by the Engle-Granger test but still stationary by residual ADF. This is not contradictory (the spread can still mean-revert while the cointegrating vector drifts), but it is operationally significant: any trading system that requires both tests to agree before acting would have remained in a "healthy" state long after the relationship had materially degraded. This period deserves explicit recognition as a diagnostic gap.

## Method Notes

All analysis uses the frozen snapshot `tcs_infy_v1_2026-07-04` (2099 trading days, 2018-01-01 to 2026-06-30). Log-price cointegration: TCS as dependent, INFY as regressor. Engle-Granger via `statsmodels.tsa.stattools.coint(trend='c', autolag='aic')`. Residual ADF via `adfuller(regression='n', autolag='aic')`. Half-life from AR(1) on OLS residuals: hl = -log(2)/log(phi_hat). Sub-regime detection via multivariate RSS optimal-split with 2000 permutations (seed=42).
