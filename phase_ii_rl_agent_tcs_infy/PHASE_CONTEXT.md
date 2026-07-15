# Phase II — RL Agent (TCS/INFY) — Phase Context

## Status: Active (since 2026-07-11; was Planned)

This phase reuses the TCS/INFY frozen snapshot(s) under the shared
`/data/snapshots/` — see `PROJECT_BASE_CONTEXT.md` §6 — rather than creating
a duplicate. Any Phase I admitted fact this phase relies on (e.g. episode
boundaries) should be cited explicitly by claim_id in this phase's own Spec
Blocks, not assumed silently.

## Tier C work completed, 2026-07-11

No Tier A or Tier B work yet. Both items below are pure engineering
(§4 Tier C) — reviewed and merged, not ledger entries, and nothing here
touches `VERIFIED_FACTS.md`.

### 1. Env scaffolding v0 — `analysis/wq_env_scaffolding_v0/`

Gym-style environment (`env/pairs_trading_env.py` and supporting modules)
with frequency-agnostic bar-windowing (`env/bar_frequency.py`). Feature
registry (`env/feature_registry.py`, `default_v0`) is limited to two
features — `beta` (intercept-inclusive OLS slope) and `eg_p`
(Engle-Granger p-value); ADF is deliberately excluded as redundant, per
Phase I's `claim_003` finding. Reward is a placeholder.

I opened `run_acceptance_test.py` directly: it asserts episode start/end
dates against Phase I's `claim_002`/`claim_004` boundaries and raises on
mismatch — 500d core 2020-01-31–2021-12-31, 730d core
2020-12-31–2023-03-31, both exact matches. Ran noop and random policies on
both cores; `run_log_summary.txt` shows `nan_obs_steps`, `inf_obs_steps`,
`nan_reward_steps`, `inf_reward_steps` all 0 across all four runs. The EG
p-value call — `statsmodels.tsa.stattools.coint(trend="c",
autolag="aic")` — I checked directly against Phase I's admitted
`claim_003` Codex script and it's the same call signature, not just a
similar-sounding description.

Provenance: `git_commit 44a899da0d3da3a5f649f981d1c2a4c4156804e8` in
`provenance.json`, stamped after outputs were committed per that file's own
note — I confirmed this hash is `main`'s current tip
(`.git/refs/heads/main`).

### 2. Frozen snapshot `tcs_infy_v2_2026-07-11` — `data/snapshots/tcs_infy_v2_2026-07-11/`

Full OHLCV (v1 was close-only). I read `metadata.json` directly: 4,214
rows, 2018-01-01 through 2026-07-10, via `yfinance` (`auto_adjust=True` for
Open/High/Low/Close). Volume is explicitly flagged as **not**
split-adjusted — `volume_policy` in the metadata states a real
discontinuity risk around any split in the window and that volume must not
be treated as comparable to the adjusted price fields without explicit
handling. Created by Codex per `PROJECT_BASE_CONTEXT.md` §6
(explicit-instruction-only). Provenance stamped with the same
`git_commit 44a899da...` as above. File sha256 recorded in `metadata.json`;
I did not independently recompute it this session.

**Not yet actioned:** the loader supports v2, but nothing has been run
against it. `tcs_infy_v1_2026-07-04` remains the default — every currently
admitted Phase I claim is pinned to v1, and no Phase II Spec Block has
named v2 yet.

## Tier C work completed, 2026-07-12

### 3. EG p-value trend feature — `analysis/wq_env_scaffolding_v1_eg_trend/`

Third feature added to `env/feature_registry.py`: `eg_p_trend`, computed as
`eg_p(t) - eg_p(t - ~20 bars)` (implemented via a 21-bar trailing window,
taking the window's first element as the "20 bars ago" reference).
Observation vector is now length 3 (`beta`, `eg_p`, `eg_p_trend`), up from
2. Two supporting changes I read directly in the diff: a step-scoped cache
on `_compute_eg_pvalue_at` (keyed on timestamp+span, avoids re-running
`coint` twice for the same point when both `eg_p` and `eg_p_trend` need it
in the same step), and a graceful-fallback path in `_log_price_window` — on
insufficient history at the very start of an episode, it now uses all
available history down to a floor of 20 bars instead of raising. This
matters because `eg_p_trend`'s `t-20` lookback would otherwise fail on
episode's first ~20 steps.

Acceptance test (I opened `run_acceptance_test.py` directly, not just
`summary.md`): asserts `len(obs) == 3`; asserts `eg_p_trend` isn't
constantly zero across a full episode pass (both cores); and at steps 10,
50, 100, independently calls `_compute_eg_pvalue_at` and
`slice_trailing_bars` itself and checks the result matches `obs[2]` to
`1e-9`. Worth being precise about what this checks: it calls the *same*
underlying helper functions the feature registry itself uses, so it's a
self-consistency check (did the observation plumbing wire up the feature
correctly), not an independent re-derivation of the EG p-value trend from
scratch. That's an appropriate bar for Tier C, not a gap — flagging it only
so the distinction is on record. All four runs (500d/730d × noop/random):
episode boundaries still exact-match `claim_002`/`claim_004`, zero
NaN/inf, `eg_p_trend` confirmed non-constant on both cores. Still on
`tcs_infy_v1_2026-07-04`, not v2.

**A real fix to the provenance-timing gap, verified, not just claimed:**
this is the first artifact in the whole project where the provenance
workflow was inverted correctly — commit code+logs first, *then* run
`stamp_provenance.py` against the already-existing commit, instead of
stamping pre-run HEAD and committing later. I didn't take the file's own
`"note": "commit hash recorded after outputs were committed, not pre-run
HEAD"` on faith — I converted the actual commit epoch timestamps myself:
code commit at 17:29:08 UTC, `provenance.json`'s own `stamped_at_utc` at
17:29:21 UTC (13 seconds later, correctly inside the window after the code
commit), provenance committed at 17:29:49 UTC. The ordering holds up. If
this workflow is used going forward, it closes `process_notes.md` #1 for
real rather than accumulating a seventh occurrence — worth confirming with
whoever's producing Codex's commits that this is now the standard sequence,
not a one-off.

**Two small hygiene items, not blocking, worth a cleanup pass sometime:**
`v1_eg_trend`'s `provenance.json` has `"claim_id": "wq_env_scaffolding_v0"`
— copied from the v0 template and not updated. And `FeatureRegistry`'s
constructor method is still named `default_v0()` despite now returning 3
features, not the 2 it shipped with. Neither affects correctness — both are
just labels — but if a v2 scaffolding pass happens, worth renaming rather
than letting `default_v0` become permanently misleading.

**Branch staleness recurred, then was resolved by someone else — not me.**
When I last checked, `main` was one merge behind
`feat/phase2_tier_c_eg_p_trend`, and I noted I have no git-execution tool in
this environment (I can read `.git/logs/HEAD` and `.git/refs/*`, I cannot
run `git merge`). Checking again now: it's fixed — `main` was fast-forwarded
into this branch, and every branch since (`feat/phase2_tier_c_extended_history`,
`feat/phase2_tier_c_differential_sharpe`, `feat/phase2_tier_c_smoke_training`)
was also fast-forward merged back into `main` promptly, confirmed via
`.git/logs/HEAD`. `main` is current as of this entry
(`.git/refs/heads/main` = `89d1f7b677d36bab69aa2f292892f874bbe2dbcc`). Whoever
has git write access on this project fixed the specific instance I flagged
and kept doing it right on every subsequent branch — four for four. The
underlying process question from `process_notes.md` #2 (should this be
automatic rather than manual) is still open, but it isn't currently causing
problems.

## Tier C work completed, 2026-07-13 through 2026-07-15

Four more pieces of engineering since the `eg_p_trend` entry above, plus
the smoke test Preet asked me to log. Reviewed in commit order via
`.git/logs/HEAD`, not just by reading each `summary.md` in isolation.

### 4. Extended-history snapshots `tcs_infy_v3_2026-07-13` / `tcs_infy_v4_2026-07-13` — `analysis/wq_env_scaffolding_v2_extended_history/`

Two new snapshots, both starting 2017-10-01 instead of 2018-01-01: `v3`
(close-only, 2,170 rows) and `v4` (full OHLCV, 4,340 rows). Purpose per
`metadata.json`, and I agree with the framing: this extends the *lookback
buffer* so the 730d core (starting 2020-12-31) plus `eg_p_trend`'s 20-bar
offset always has enough real history before it — it is explicitly not a
rebasing of the primary analysis window, and none of Phase I's admitted
claims are affected (they're pinned to `v1`).

**Worth being precise about what this means for `v4` specifically:** its
longer window now includes TCS's 2018-05-31 stock split and INFY's
2018-09-05 bonus issue, both inside the estimation history for the first
time (`v1`/`v2`'s 2018-09-06 floor excluded them). `metadata.json`'s
`volume_policy` flags this directly. This is fine for the stated purpose
(pre-episode lookback buffer, not itself an analysis window), but if `v4`
is ever used for anything beyond feature lookback, this is the first
snapshot in the project where a corporate action sits inside the covered
range, and that should be treated deliberately, not silently.

**This entry also reverted `eg_p_trend`'s graceful-fallback fix from
entry 3**, replacing it with the better fix: since `v4` now provides enough
real history, `_log_price_window` goes back to raising `ValueError` on
insufficient history instead of silently falling back to a shorter window.
I confirmed this directly in the current `feature_registry.py` — the
try/except block from entry 3 is gone. This is a cleaner fix than the one I
logged before (an explicit data-sufficiency guarantee beats a silent
shorter-window fallback), and I'm noting the reversal explicitly rather than
just describing the current state, since entry 3 is still in this file
describing something that's since been superseded.

### 5. Reward registry + `cost_adjusted_pnl` — `analysis/wq_env_scaffolding_v3_reward_registry/`

`env/reward_registry.py` created, mirroring `feature_registry.py`'s
pattern. First real reward, replacing the placeholder:
`cost_adjusted_pnl = position * (current_spread - previous_spread) -
cost_rate * |position - previous_position|`. On the very first step
(`previous_spread is None`), pnl is `0.0` but the cost term still applies
against a `previous_position = 0.0` reset state — a documented design
choice (entering a position for the first time is a real trade). Acceptance
test confirms `cost_rate=0.0` exactly reproduces the old placeholder reward
step-for-step, and `cost_rate=0.01` strictly decreases reward only on
steps with a position change — both are checks I'd have wanted to see, not
just taken on the summary's word for. This is where the phase switched its
default snapshot from `v1` to `v4` — documented as reusing entry 4's
lookback reasoning, not an unexplained substitution.

### 6. `differential_sharpe` reward — `analysis/wq_env_scaffolding_v4_differential_sharpe/`

Moody-Saffell differential Sharpe ratio, built on top of
`compute_cost_adjusted_pnl` for `R_t` (so the two reward functions can't
disagree on what "cost-adjusted return" means). I read `reward_registry.py`
directly rather than trusting the summary: `dsr_warmup_steps` (a step-count
gate) and `dsr_epsilon` (~1e-12, a numerical floor only) are two genuinely
separate mechanisms, documented as such in the docstring so they don't get
conflated later.

**A real bug, caught and fixed before this shipped, not after:** the
variance floor check originally happened *after* exponentiating
`(B_prev - A_prev**2) ** 1.5`. Python raises a negative base to a
non-integer power as a complex number, not an exception — so float-precision
cancellation pushing that quantity slightly negative would have produced a
complex/float `TypeError` crash mid-training, not a graceful bad-reward
step. Fixed by checking `variance_est <= dsr_epsilon` *before* the `**1.5`.
I confirmed the fix is in the current code (`reward_registry.py`), matching
the `git_commit`-titled "Variance Est value fix."

`dsr_warmup_steps=100` is provisional, set by reconnaissance across 5
seeds on both cores (a trailing-20-step coefficient-of-variation < 0.25
criterion settled by step 86 at the latest observed point; 100 gives
margin) — explicitly labeled in `summary.md` as a diagnostic, not a
validated statistical result, which is the right label for Tier C. That
same entry also recorded **late-episode reward extremes** (e.g. step
420/477 on 500d_core seed 42) occurring well after variance had settled by
this criterion, unexplained by initialization, and explicitly deferred to
"Tier C smoke training with the actual RL algorithm." That's entry 7 below.

### 7. PPO smoke training — `analysis/wq_smoke_training_v0/` (what Preet asked me to log)

`train.py`: PPO (`stable_baselines3`, `MlpPolicy`, default hyperparameters,
`seed=1337`), `total_timesteps=50_000` (rounds up to 51,200 = 25 × 2048 SB3
rollout length). **Single core (`500d_core`) and a single seed** — this is
narrower than every acceptance test so far, which all ran both cores.
Trained on `differential_sharpe`; a parallel, separately-instantiated
`cost_adjusted_pnl` env tracks real economic P&L alongside it purely for
diagnostics, with an explicit `AssertionError` guard if the two envs'
episode lengths ever desync. **`cost_rate=0.0` in both envs** — worth being
precise that "cost-adjusted P&L" in this run's diagnostics is actually raw
spread P&L with the cost term switched off, not a transaction-cost-aware
result; a nonzero-cost smoke pass hasn't been run yet.

Own framing in `summary.md`, which I agree with and want to preserve
exactly: this is 104 episodes, meant to check infrastructure stability and
the absence of obvious reward hacking — explicitly **not** a claim about
agent quality or convergence. Four checks, all clean: zero NaN/Inf in any
SB3 logger metric across all 25 iterations; reward-outlier count
(`|reward|>5.19`, a threshold inherited from entry 6's reconnaissance, not
re-derived here) stayed at 4–9 per 2048-step rollout, no growth; realized
`cost_adjusted_pnl` stayed in roughly [−0.17, +0.20] with no divergence from
the training reward (the reward-hacking check); action-diff mean held
~1.0–1.15 with no collapse toward degenerate high-frequency flipping.

**This is a partial, not complete, answer to entry 6's deferred question.**
The late-episode reward-extreme behavior didn't blow up training here — but
that's one seed, one core, zero transaction cost. It doesn't confirm the
extremes are harmless in general, only that they didn't break this
particular run. Worth being explicit about that gap rather than letting
"smoke test passed" quietly read as "question resolved."

Provenance timing verified the same way as entry 3, not assumed from the
file's own note: code commit (amend) at 08:44:38 UTC, `stamped_at_utc` at
08:45:00 UTC, provenance commit at 08:45:10 UTC — correct order, holds up.

### A pattern worth naming once instead of per-entry: `default_v0()`

Both `FeatureRegistry.default_v0()` (now 3 features) and
`RewardRegistry.default_v0()` (now 2 rewards, one of which supersedes the
original placeholder) still carry a `_v0` name that no longer describes
their content. Not a correctness issue, purely a label — flagging it as one
item covering both registries rather than repeating it per-entry.

All Tier C, all reviewed and merged per commit messages traced in
`.git/logs/HEAD`, nothing above touches `VERIFIED_FACTS.md`.

## Root-level process finding surfaced during this work

`main` had never received a merge across this project's history before
today. Full detail, including a disagreement with how this was framed to
me, is logged at the project-root `process_notes.md` (§2) rather than
duplicated here, since it isn't Phase II-scoped — it retroactively affects
which commits Phase I's `claim_002` and `claim_003` citations were reachable
from on `main`.
