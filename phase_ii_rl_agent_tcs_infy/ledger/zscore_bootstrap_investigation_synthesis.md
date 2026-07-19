# Synthesis: Z-Score Block-Bootstrap Investigation

**This is a synthesis, not a new empirical finding.** It reports zero new
computation — no new snapshot, no new script, nothing needing the usual
`provenance.json` / post-commit-stamping treatment any `wq_` item in this
ledger gets. Every number below traces back to one of the seven checks
listed in §0. Treat this file as an index and cross-check of existing work,
not an eighth `wq_` item with its own independent evidence.

Written by Desktop Claude A at B's request, from B's draft synthesis text.
I independently re-derived every numerical claim below from the underlying
JSON/`.md` files in each `wq_` directory before writing this — not
transcribed from B's arithmetic or from `worklog_tier_b.md`'s prose. Where
I couldn't fully verify something, that's stated plainly in §4, not
smoothed over.

## 0. What this synthesizes — seven checks, four directories

B's count of "7 chained items" is correct, but they span four `wq_`
directories, not seven — some directories bundle more than one distinct
check. Listed so a reader can trace any claim below to its source without
reconstructing this from conversation history:

1. **`analysis/wq_zscore_block_bootstrap_v0/`** — the original finding:
   circular block-bootstrap (B=2000, L=10/20/40) of the deterministic
   Z-score rule on `730d_core` real data, PnL running systematically
   *higher* on resampled paths than the real one.
2. **`analysis/wq_zscore_seam_diagnostics_v0/`, Part A** (`summary.md`) —
   single-series OLS AR(1) fit on the full `730d_core` spread, φ=0.9599.
3. **`analysis/wq_zscore_seam_diagnostics_v0/`, Part B** (`summary.md`) —
   L=20 seam-adjacent-vs-mid-block reward diagnostic; found the artifact
   localized almost entirely at seam distance 0.
4. **`analysis/wq_zscore_seam_diagnostics_v0/phi_joint_fit.md`** — zero-cost
   recomputation: single φ jointly fit by SSR minimization across all three
   observed L=10/20/40 ratios, φ=0.975088.
5. **`analysis/wq_zscore_seam_diagnostics_v1/`** (`summary.md`,
   `seam_results_v1.json`) — regime-crossing vs. within-regime seam reward,
   with proper per-group SEs this time (54,000 raw observations).
6. **`analysis/wq_zscore_seam_diagnostics_v1/seam_index_reanalysis.md`** —
   same directory, separate script: granular reward by seam index (1
   through 6+), testing the early-position-noise hypothesis specifically.
7. **`analysis/wq_zscore_clip_isolation_v0/`** — L=20 seam reward with the
   `clip(-z,-1,1)` operation held fixed vs. removed, isolating the clip's
   own marginal contribution.

## 1. What has been ruled out — verified, not transcribed

Four mechanisms, tested as explanations for why bootstrap-resampled PnL
runs systematically higher than the real path under the same rule.

**Regime-mediation.** I pulled `seam_results_v1.json` directly:
`difference.mean = -0.0002583782607249521`,
`difference.se = 0.00030477109581295486`. Matches B's `-0.000258 ± 0.000305`
to the reported precision, and I checked it's a bit-level match to the raw
JSON, not just consistent with the worklog's rounded transcription.
`n=20,827` (regime-crossing) / `33,173` (within-regime), summing to the
full 54,000 — checked. Difference is 0.85 SE from zero, and roughly 1% of
the pooled seam effect's own ~0.0247 magnitude (0.000258/0.0247 ≈ 1.05%).
Tight, well-powered null — confirmed.

**Single-φ / AR(1) misspecification.** This is where I did the most
independent work, since neither the worklog nor B's synthesis shows the
SE-conversion arithmetic directly — I reconstructed it from two separate
source files to check the "5.7/7.7/14.8 SEs" claim wasn't asserted:

- Residuals (Predicted − Observed), from `phi_joint_fit.md` directly:
  L=10: `+0.0829`, L=20: `−0.0909`, L=40: `−0.1506`.
- SE of each observed ratio, which I derived myself: the ratio is
  `mean_bootstrap_PnL / observed_real_PnL`, and `observed_real_PnL`
  (0.3909) is a fixed point from the one real deterministic path, not a
  random draw — so `SE(ratio) = (std_bootstrap / √B) / 0.3909`. Pulling
  `std` and `B=2000` from `wq_zscore_block_bootstrap_v0/summary.md`:
  - L=10: std=0.2555 → SE(ratio) = (0.2555/√2000)/0.3909 = 0.01461
  - L=20: std=0.2062 → SE(ratio) = (0.2062/√2000)/0.3909 = 0.01180
  - L=40: std=0.1780 → SE(ratio) = (0.1780/√2000)/0.3909 = 0.01018
- Residual ÷ SE(ratio): L=10: 0.0829/0.01461 = **5.67**, L=20:
  0.0909/0.01180 = **7.70**, L=40: 0.1506/0.01018 = **14.79**.

Matches B's "5.7/7.7/14.8 SEs" exactly, built from first principles rather
than checked against a number I was handed. A well-powered misfit — the
best possible single φ still leaves a real, structured, non-noise residual
pattern (over-predicts L=10, under-predicts L=20 and L=40 with growing
severity), confirmed.

**Clip.** From `clip_isolation_results.json` directly: actual (clipped)
mean=0.024656037..., SE=0.000149989...; unclipped mean=0.033892052...,
SE=0.000232240.... Difference = 0.009236; combined SE =
√(0.000149989² + 0.000232240²) = 0.0002765; ratio = **33.4 SEs**. Percent
change = 0.009236/0.033892 = **27.2%** reduction from unclipped to clipped.
Both match B's "~33 SEs" and "~27%" almost exactly, and direction is
confirmed opposite to what's needed: removing the clip *increases* seam
reward, so clip isn't the source of the inflation.

**Early-position noise.** From `seam_index_reanalysis.md`: Index 1
(n=2,000) mean=0.01584, SE=0.00094; Index 6+ (n=44,000) mean=0.02537,
SE=0.00016. Difference=0.00953; combined SE=√(0.00094²+0.00016²)=0.000954;
ratio = **~10.0 SEs**. Matches B's "~10-SE effect" — real, but Index 1 is
only ~3.7% of the pooled 54,000 observations, so its effect on the *pooled*
average is small even though the effect at Index 1 itself is far from
noise. Direction: Index 1 sits *below* the settled level, so this dampens,
not inflates — confirmed opposite to what's needed to explain the original
finding, same as B's synthesis states.

## 2. The φ-arithmetic correction — stated visibly, not silently absorbed

**C's originally-reported implied-φ figures contained a sign error and
were corrected before this synthesis was written.** C's method computed
`predicted_ratio = observed − residual`, but `phi_joint_fit.md` defines
`residual = Predicted − Observed`, so that formula actually computes
`observed − (predicted − observed) = 2×observed − predicted` — a
reflection of the predicted value around the observed one, not the
predicted value itself. I checked the arithmetic: at L=10,
`2×4.8312 − 4.9141 = 4.7483`, exactly C's originally-reported figure.

The corrected method — which I re-derived independently from the raw
observed ratios, not from C's or B's numbers — solves
`Ratio(L,φ) = (L−1)/L + 1/(L(1−φ))` for φ directly at each L, using the
observed ratios from `wq_zscore_block_bootstrap_v0` (4.8312 / 3.0480 /
2.1291 at L=10/20/40, themselves re-derived as `mean_bootstrap_PnL /
0.3909` from that directory's own summary, not taken as given):

| L | Observed ratio | φ = 1 − 1/(L·(Observed − (L−1)/L)) |
|---|---|---|
| 10 | 4.8312 | **0.9746** |
| 20 | 3.0480 | **0.9762** |
| 40 | 2.1291 | **0.9783** |

This matches the corrected figures in B's synthesis to four decimal places
— independently reproduced, not just checked for consistency. Spread =
0.9783 − 0.9746 = **0.0037**, roughly half of C's originally-reported
0.0068 spread. The monotonic-increase pattern (implied persistence grows
with the resampling horizon) survives the correction; the evidence for it
is weaker than first presented, not absent. I also checked why back-solving
from the *joint-fit's own* predicted values (4.9141/2.9571/1.9785) would be
circular: doing so returns φ=0.975088 at all three L, by construction,
since those predictions were generated using that φ in the first place. The
corrected method above avoids this by solving from the independently
observed ratios, not the joint-fit's output.

## 3. What remains genuinely plausible — not confirmed, not ruled out

Per §1, four candidate mechanisms are ruled out, tested to well-powered
statistical tightness. Three are not:

- **Normalization** (the running σ's own stochastic behavior, correlated
  with `s_A`) — never isolated on its own; the clip-isolation test held it
  fixed identically in both branches rather than varying it.
- **Path-dependence more broadly** (dependence on the full trajectory, not
  a single-point approximation) — flagged as untested from the start of
  this chain, still fully open.
- **Multi-timescale / long-memory dynamics beyond simple AR(1)** — the
  corrected implied-φ pattern (§2) is real but weaker than first reported,
  and per B, confounded with an untested clip×L interaction (clip-isolation
  only ran at L=20 — I confirmed this structurally: both
  `seam_results_v1.json` and `clip_isolation_results.json` report n=54,000,
  consistent with L=20 alone across B=2000 draws on a 559-row series, not a
  pooled figure across block lengths).

B's framing, which I think is the right way to read this and am restating
rather than independently adjudicating (it's a reasoning conclusion, not a
file-checkable fact): four ruled out, none of the remaining three
confirmed. "Everything tested so far has failed to explain it" is evidence
the search has exhausted the cheap places, not evidence for any one
remaining candidate — including path-dependence, which is the
most-plausible-sounding of the three but not the demonstrated one.

## 4. What I could not verify — stated plainly

- **`seams_raw.csv`** (2.5MB, `wq_zscore_seam_diagnostics_v1/`) and
  presumably **`clip_raw.csv`** (`wq_zscore_clip_isolation_v0/`) could not
  be opened at all with my available tools — every attempt, down to a
  single line, returned a "result too large" error, meaning the file's
  content is not newline-delimited in a way my line-range reader can
  handle. I have no code-execution tool against this repository, so I
  could not independently recompute the seam-index or clip aggregates from
  raw per-observation rows. Everything in §1 is verified at the aggregated
  JSON/`.md` level (`seam_results_v1.json`, `seam_index_reanalysis.md`,
  `clip_isolation_results.json`), which in the one case I could check
  bit-for-bit (`seam_results_v1.json`) matched exactly. I have no reason to
  doubt the raw-level aggregation, but "no reason to doubt" is not the same
  standard as "independently recomputed," and I want that distinction on
  the record rather than implied away.
- I did not re-verify git-commit/provenance-timing for these five files
  the way I would for a claim going to `VERIFIED_FACTS.md` — B's request
  was specifically about the numerical claims in the synthesis, not a
  provenance audit of each constituent `wq_` item, and I've scoped this
  accordingly.

## 5. Decision relevance

Restating B's framing here since it's the operative conclusion, not an
independent finding of mine: the question this chain actually opened to
answer wasn't "what precisely explains the seam residual," it was "does
the block-bootstrap significance test give a trustworthy read on whether
Z-score's real-data edge (0.3909, from `wq_real_data_capacity_v0`) is
genuine." That question is answered independent of which of the three
remaining candidates turns out to be correct: **the test doesn't. It's
dominated by a bootstrap-construction artifact**, established through four
independent, well-powered checks (§1), not asserted. Resolving
normalization vs. path-dependence vs. long-memory would complete the
mechanistic story; it would not change this conclusion, since none of the
three remaining candidates point back toward the test being trustworthy
after all.

One thing named as decision-relevant on its own, not folded into the above:
if the long-memory story turns out real and dominant, it connects to Phase
I's own already-flagged, still-open Hurst/AR(1) confound at φ≈0.9 — a
separate research thread with its own standing, not something this
bootstrap-mechanism chain is positioned to resolve as a side effect.

## 6. Recommendation — B's, pending Preet's decision

**This is B's synthesis-based recommendation, not a closure that has
already happened.** Unless Preet has separately told me this is accepted,
treat this investigation as open pending that decision, not closed by
virtue of this file existing.

B recommends: close this as a well-characterized result — Z-score's
real-data baseline beats random-action noise; it does not show clean
bootstrap-null significance under this construction; the reason is a
partially-understood bootstrap-seam artifact interacting with high
persistence, four specific alternatives ruled out, none of the remainder
confirmed. Do not authorize L=10/L=40 clip-isolation, AR(1), or Hurst
testing as continuations of *this* chain. If the Hurst/AR(1) connection is
worth pursuing, B's position is that it should be scoped as its own
investigation against Phase I's original open question, not chained
further onto this one.
