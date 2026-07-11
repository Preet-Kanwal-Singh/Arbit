# Phase I — TCS/INFY Cointegration Pairs-Trading Track — Phase Context

Migrated verbatim from `PROJECT_BASE_CONTEXT.md` §1 and §8 during the
2026-07-10 multi-phase restructuring (see `decisions.md`), with one
exclusion noted explicitly below — nothing else reworded or trimmed.

## 1. Why this process exists (originally §1)

The prior investigation (GLM sandboxes, rounds 1–7) produced four
consecutive "decisive" findings that were each retracted, and one
foundational number ("Episode 1 beta range 0.20 to 1.91 across 22 months")
whose origin became untraceable — no script or data computation could be
found backing it, in any sandbox. The root cause was not any one tool being
unreliable — it was (a) sandboxes that didn't persist across sessions, and
(b) a model's self-report about its own authorship or correctness being
treated as evidence. Every rule in `PROJECT_BASE_CONTEXT.md` exists to close
one of those two gaps, for this phase and every other. Do not re-add process
on top of it without checking it's closing a gap that's actually present —
the last version of this system became too heavy and was deliberately cut
back.

## 2. Carry-forward status — do not re-litigate, do not re-trust (originally §8)

**Stands, not yet adversarially tested (test before leaning on further):**
- Episode 1 is the only long healthy trading episode for TCS/INFY.
- Three instability windows: Feb–Mar 2020, Sep–Oct 2020, Aug–Sep 2021.
- Aug–Sep 2021 as genuine early-warning signal (pre/post residual ratio
  4.46×) — predates the retracted thread, not itself challenged.
- Phi regime-dependence (pre-COVID ~0.95, post-COVID ~0.99) — called
  "load-bearing" by the prior investigation but **never itself
  adversarially tested.** Treat with the same suspicion as everything that
  got retracted, not as safe by default.

**Verified (Tier 1 from prior handoff, safe to reuse as-is):**
- The two cointegration-pipeline bugs (wrong ADF critical values;
  `regression="c"` instead of `"n"`) — confirmed by reading
  `statsmodels.coint()` source directly.
- TCS/INFY healthy-episode half-life ~10–20 days (phi ≈ 0.93–0.97).
- Kalman filter for beta tracking — ruled out, don't revisit without a
  different filter formulation.
- Pesavento (2004) — confirmed real and on-topic via independent search;
  better fit than Hjalmarsson-Österholm (2007), which is a different test
  variant.

**Discard entirely, recompute from raw data before using for anything:**
- "Episode 1 beta swings 0.20 to 1.91 across 22 months" — untraceable,
  origin unconfirmed even after tracing to a prior sandbox. (Superseded by
  `claim_004_episode1_beta_range`, admitted to `VERIFIED_FACTS.md`
  2026-07-10 — this entry stays as historical record of what was discarded
  and why, not as a live gap anymore.)
- Any specific FNR number from the retracted rounds (0.206, 0.340, 0.386,
  0.946→0.000), and the phi_β=0.998 / phi_β=0.086 point estimates.
- The beta-drift degradation curve and the phi-estimator SE/CI table from
  the authorship-uncertain sessions — recompute with logging, and this time
  add the bias check that was flagged but never done (OLS phi is known to
  be biased downward near the unit root).

**Note on migration — one thing deliberately not copied here:** the
original §8 also carried an "Open Tier A questions to work through first"
list (5 items). That list is not reproduced in this file. It already exists,
tracked live, as the first five entries of this phase's `open_questions.md`
— copying it here as well would create a second copy that drifts from the
real one (item 1, the beta-range recompute, is already resolved there as of
`claim_004`, and would have been silently wrong if pasted here unchanged).
See `open_questions.md` for the current, accurate version of that list.
