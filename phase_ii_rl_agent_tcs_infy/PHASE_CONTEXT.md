# Phase II — RL Agent (TCS/INFY) — Phase Context

## Status: Active (since 2026-07-11; was Planned)

**Currency notice, added 2026-07-17:** this file is current through entry 9
below (PC-1 positive control). If you're reading this to answer PC-2 or any
later question: the *absence* of an entry for something is not evidence it
didn't happen — it may just mean this file hadn't been updated yet when you
needed it. Ask rather than assume, or check `analysis/` and `.git/logs/HEAD`
directly. Separately, and more specifically: entries 1, 3, 4, 5, 6 below
(everything dated before 2026-07-16 06:20 UTC) cite specific git commits for
`env/*.py` changes that are very likely wrong in a deeper way than a
mistimed stamp — `env/` was accidentally gitignored for essentially all of
Phase II's history until that point, so those commits probably don't
contain the `env/*.py` diffs their messages describe at all. See
`process_notes.md` #4 for the full finding. The code-content observations
in those entries (what I read directly from the working tree) are still
accurate; the commit citations attached to them are not to be trusted
without independently re-checking.

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

## Tier C work completed, 2026-07-15 through 2026-07-17

### 8. Episode-persistent `eg_p` caching — `analysis/wq_feature_caching_v0/`

Pure performance work, no behavior change intended or found.
`FeatureContext.eg_p_cache` replaces the earlier step-scoped, lazily-created
cache from entry 3 with a dict the caller is now responsible for persisting
across an environment's lifetime; I confirmed in the current
`feature_registry.py` that the cache key is now
`(timestamp, eg_lookback_span, y_ticker, x_ticker)` — the ticker pair was
added, which matters for `SyntheticOracleEnv` (entry 9) and any future
multi-pair use, not just this cache's original TCS/INFY purpose.

Acceptance test claims bit-identical output on both cores versus the
pre-change baseline, plus a real speedup (500d: 29.20→45.05 FPS, ~1.54x;
730d: 19.91→33.01 FPS, ~1.66x). I did not re-run the comparison myself —
taking the bit-identical claim on the acceptance test's word, same as I do
for every other Tier C acceptance test in this project; the code change
itself (dict-based memoization with no change to what gets computed, only
when it gets recomputed) is the kind of change where that's a reasonable
level of trust.

**Provenance:** cites `git_commit b7216461ca5fc77d5904f0c8971ecda4b8ddfb80`.
Per `process_notes.md` #4, this citation is unreliable for the actual
`feature_registry.py` diff (made while `env/` was still gitignored) even
though the acceptance-test outputs themselves (under `analysis/`, never
gitignored) are likely fine.

### 9. PC-1: Oracle-state positive control — `analysis/wq_positive_control_v0/`

B's spec, reviewed against the actual implementation rather than the
summary alone. Purpose: confirm the harness (PPO + this environment +
`differential_sharpe`/`cost_adjusted_pnl`) can learn *something*, on a
signal engineered to be unambiguously learnable, before spending any more
compute asking whether TCS/INFY's silence (if it turns out to be silent) is
a weak real edge or a broken harness.

**Synthetic DGP:** AR(1) mean-reverting spread (`kappa=0.1`, `sigma=0.3`,
`master_seed=20260101`, 51,000 steps), written to
`data/snapshots/synthetic_positive_control_v1/spread.csv`.
`provenance.json` marks `"synthetic": true` with the DGP formula and
parameters inline, per spec — confirmed directly, not assumed.

**Faithful reuse, the part the spec called load-bearing — checked, holds
up:** I read `env/synthetic_oracle_env.py` directly. It imports
`RewardRegistry`/`RewardContext` from `reward_registry.py` and calls
`self.reward_registry.compute(self.reward_name, reward_ctx)` — the actual
production reward functions, not a reimplementation. The context object
built per step has the identical field set the spec specified
(`previous_spread`, `current_spread`, `previous_position`, `position`,
`cost_rate`, `dsr_A`, `dsr_B`, `dsr_eta`, `dsr_epsilon`, `dsr_warmup_steps`,
`dsr_step_count`). This is genuine compliance with the one part of the spec
B was strictest about, not a close-enough approximation.

**Causal ordering — checked, because the spec's oracle policy
`action_t = -sign(spread_t)` reads like it could be look-ahead if
implemented naively.** There's a `debug_math.py` scratch script in this
folder that explicitly compares `action_t = -sign(spread_t)` (look-ahead:
deciding the action using the same value that determines that step's own
return) against `action_t = -sign(spread_{t-1})` (causally valid) — which
reads like exactly this question being investigated before `run_oracle.py`
was finalized. I traced `run_oracle.py` and `SyntheticOracleEnv.step()`
line by line: the oracle script only ever acts on `obs` returned by the
prior `reset()`/`step()` call, never on a value it hasn't been given yet,
and `step()`'s reward computation pairs the action decided from the prior
observation against the transition ending at the newly-revealed value. This
is causally correct — not look-ahead — despite the spec's own shorthand
notation being ambiguous about it on paper. `debug_math.py` isn't listed in
`provenance.json`'s outputs and has no saved output of its own; I'm reading
it as investigative scratch work, not a verified deliverable.

**Sequencing (PC-1a before PC-1b, PC-1b gated on PC-1a passing):** results
are reported in that order and PC-1a did pass, so the gate wasn't violated
in outcome. I can't fully confirm from timestamps alone that PC-1b's launch
was actually *conditioned* on PC-1a's result rather than both being kicked
off close together regardless — the two runs' tensorboard event files are
only 73 seconds apart, which is plausible for a fast 50k-step run on a
1-dimensional observation space, but I don't have positive evidence of a
hard gate in the code, only that the documented outcome is consistent with
one having been used.

**Results (from `provenance.json`'s `oracle_refs` and `summary.md`,
arithmetic re-checked by hand):**

| | PC-1a (`cost_adjusted_pnl`) | PC-1b (`differential_sharpe`) |
|---|---|---|
| Realized `eval_cost_adjusted_pnl`, final 5/25 rollouts | 24.18 | 23.84 |
| Oracle (`oracle_mean_episode_pnl` = 27.28687) | 88% | 87% |
| Bar (50% of oracle = 13.643) | PASS | PASS |

Outlier threshold recalibrated per spec, not reused from real-data's
`5.19`: `pnl_p99_threshold=0.7995`, `dsr_p99_threshold=2.8348`, both from
the oracle run's own reward distribution.

**PC-2 stays exactly where the spec put it:** not specced, not started.
Added to `open_questions.md` as the next control, conditional on PC-1
passing (both legs did) — verifying whether `beta`/`eg_p`/`eg_p_trend`
preserve enough structure from a synthetic price series with an embedded
signal for the harness to detect it, which is a materially different
question from PC-1's raw-spread-observation test.

**Provenance integrity, this entry specifically:** `provenance.json`
currently correctly cites `git_commit c779e56d18330928325799acccacffea6428335b`
(I confirmed this is reachable from `main`'s current tip,
`4b07cca32a9eaec66a1274f39d952d4c6d9d41c2`, one commit ahead). But see
`process_notes.md` #4 for two things worth knowing: the original commit
`b1ba4bbfaa7c8c9fceb780b5864d9b07111bb615` this correction replaced was
rewritten via `git commit --amend` and is no longer reachable from `main`
at all (not just superseded — gone from `main`'s history); and the
correction note inside that file still says it "has not yet been committed
to git," which is now stale — it has been, as of `4b07cca3`. I didn't edit
that note myself since it's attributed to Desktop Claude B; flagging it for
whoever's closing this out.

### 10. PC-2: Feature-pipeline positive control — `analysis/wq_positive_control_v1_feature_pipeline/` — **FAILED, both legs**

This is a substantive negative result, not a process note — flagging it as
such up front rather than letting it read like another infrastructure
entry. I did not review a PC-2 Spec Block before this ran, unlike PC-1;
this section exists already-executed, so my review here is of the
implementation and result only, not a pre-registration check the way PC-1
got.

**Question:** with the harness itself validated by PC-1, does the *real*
feature pipeline (`beta`, `eg_p`, `eg_p_trend`, unmodified
`feature_registry.py`) preserve enough of a known, embedded mean-reverting
signal for PPO to learn it — as opposed to PC-1's raw `[spread_t]`
observation?

**Setup, verified by reading the code, not just `summary.md`:** a new
synthetic pair, `log(Y_t) = 0.70*log(X_t) + spread_t`, `spread` the same
AR(1) form as PC-1 (`kappa=0.1`, `sigma=0.3`), `X` a log-normal random walk
(`sigma_x=0.015`), `master_seed=20260101`, 2,800 bars. Four 500-bar episode
cores are injected at runtime into the real `EPISODE_CORES` dict (a
collision guard asserts the injected keys don't already exist; the two real
admitted keys are never touched; `episode_config.py` on disk is never
written to) — confirmed directly in `gym_pc2_wrapper.py`, not assumed from
the summary. Each core carries a 750-bar warmup before its 500-bar episode
window — note this is exactly `730 + 20`, the `eg_lookback_span` plus
`eg_p_trend`'s offset, with zero slack, not a generous buffer. It evidently
was sufficient (no crash), but it's tight.

**Oracle construction is different from PC-1's, deliberately and
appropriately — not a shortcut.** PC-1's oracle ran through the actual
`SyntheticOracleEnv` class. PC-2's oracle (`run_oracle.py`) instead
regenerates the true spread series independently and evaluates
`RewardRegistry.compute()` directly via a mock context, never touching
`PairsTradingEnv` or the feature pipeline at all. I checked this makes
sense rather than treating it as a deviation to flag: PC-2's entire point is
measuring the *gap* between an oracle with perfect knowledge of the true
spread and an agent that only sees the (possibly lossy) feature
representation — the oracle has to bypass the features by construction, or
it wouldn't be measuring what PC-2 is asking. I traced the RNG call
sequence in both `generate_synthetic_pair.py` and `run_oracle.py` by hand:
both seed with `20260101`, draw the same first `spread[0]` sample, then the
same `n_bars`-length `eps_spread` array, in the same order — the oracle's
spread series is bit-identical to the one actually embedded in the saved
`synthetic_pair_v1` data. This is a checked fact, not an assumption. Same
causal action-then-transition alignment as PC-1 (action decided from the
spread value at the start of the transition, reward reflects the move to
the next value) — not look-ahead here either.

**Results:**

| | PC-2a (`cost_adjusted_pnl`) | PC-2b (`differential_sharpe`) |
|---|---|---|
| Realized `eval_cost_adjusted_pnl`, final 5 of 25 passes (last 10,000 steps) | ~0.35 | ~−0.07 |
| Oracle (`oracle_mean_episode_pnl` = 28.2426) | ~1.2% | negative — worse than doing nothing |
| Bar (35% of oracle ≈ 9.88) | **FAIL** | **FAIL** |

"25 passes" here means 25 full cycles through the 4 synthetic cores
(`n_steps=500` matches the 500-bar episode length exactly, so each PPO
rollout is exactly one episode on one core) — 100 episodes total, last 20
of them evaluated. This is a different mechanical definition of "pass" than
PC-1 used (PPO's default 2048-step rollout there), but lands on a
comparable absolute step count (~10,000 either way); not treating this as
an inconsistency, just noting the terms aren't mechanically identical
across the two entries.

**What I can't verify:** the commit history shows an initial commit
("Add PC-2: ... execution and results"), then training actually ran
(tensorboard files dated after that commit), then a later commit titled
"Fix PC-2 env params and update evaluation to average of final 5 passes."
The *same* tensorboard event files are cited in the final `provenance.json`
as in the run that happened before the fix — so training itself was not
redone; whatever "env params" issue was fixed, it was fixed in how the
oracle or the evaluation aggregation was computed against the *existing*
training run, not by retraining. I can't confirm this precisely without a
git-show/diff tool, and I want to flag the risk plainly: I don't know
whether the 35% threshold or the "final 5 of 25" aggregation window was
adjusted before or after someone saw how the training runs looked. Worth
asking directly rather than assuming either way.

**One process deviation, worth fixing going forward:** the synthetic data
lives at
`analysis/wq_positive_control_v1_feature_pipeline/data/snapshots/synthetic_pair_v1/`,
not at the project-root `data/snapshots/` every other snapshot in this
project uses (including PC-1's own `synthetic_positive_control_v1`). This
is deliberate in the code (`gym_pc2_wrapper.py` explicitly points
`repo_root` at the analysis folder), not an accident, but it breaks the
convention `PROJECT_BASE_CONTEXT.md` §6 establishes.

**Bottom line, stated plainly:** PC-1 showed the harness can learn a signal
it's handed directly. PC-2 shows that once the same signal is routed
through the real `beta`/`eg_p`/`eg_p_trend` pipeline, PPO does not learn to
exploit it under these conditions — one seed each, no hyperparameter
tuning, `differential_sharpe` actually landing negative. This does not by
itself prove the features are the problem; it's equally consistent with
undertrained runs, PPO defaults tuned for PC-1's simpler observation space,
or something else. But it does mean the harness's demonstrated ability to
learn (PC-1) has not yet been shown to survive contact with the actual
feature representation this project intends to use on real data — which is
exactly the gap PC-2 was built to check for, and it found one.

**Update, 2026-07-17, after Preet shared the actual PC-2 Spec Block
retroactively:** this resolves one of my flagged concerns and raises a more
concrete one.

*Resolved:* the 35% bar (vs. PC-1's 50%) was pre-declared in the spec
(§6: "Acceptance = 35% of that freshly-computed number"), not chosen after
seeing results. I no longer think the acceptance bar itself is a
post-hoc-adjustment concern.

*New, and this one matters for how much weight the FAIL result should
carry:* the spec (§4) calls for "25 rollouts × 2,000 steps/rollout" —
PPO's `n_steps` set to 2,000, matching the 4-episode/2,000-step block
explicitly. The actual code uses `n_steps=500` (one episode per rollout,
100 rollouts total). I missed this the first time through because the
result ("25 passes," "final 5 of 25") reads consistently with the spec on
the surface — it's only a real discrepancy once the spec's literal
PPO-hyperparameter instruction is checked against the code, which I
couldn't do until this spec text existed. The implementer's own comment in
`train_pc2a.py` shows this was a live judgment call, not an oversight: *"the
instructions say 'matches PC-1 scale exactly' which did 51,200. Let's just
use 500"* — i.e., "matches PC-1's scale" was read as matching PC-1's total
step count, not PC-1's rollout size, and `n_steps` was set to the episode
length instead of the spec's literal 2,000. A 4x smaller rollout buffer is
not a cosmetic difference for PPO — it changes what each policy update sees
before updating. This means PC-2's FAIL result was produced under
hyperparameters that deviate from spec, and I can no longer rule out
"undersized rollout buffer" as a contributor to the failure, separate from
the "feature pipeline destroys the signal" hypothesis I flagged as
unresolved above. Preet's or B's call whether this warrants a rerun at
`n_steps=2000` before treating the FAIL as informative about the features
specifically.

**Relocation, done today, per Preet's explicit instruction, matching PC-1's
convention:**
1. `synthetic_pair_v1/adjusted_close.csv` and `metadata.json` moved from
   the nested `analysis/wq_positive_control_v1_feature_pipeline/data/snapshots/`
   path to the project-root `data/snapshots/synthetic_pair_v1/`, via
   `filesystem:move_file` — confirmed both files present at the new
   location afterward.
2. `generate_synthetic_pair.py`'s `out_dir` updated to resolve to the
   project root (`parents[3]`, matching this script's own `run_oracle.py`
   sibling's existing `sys.path.append(... parents[3])` depth) instead of
   the analysis folder.
3. `gym_pc2_wrapper.py`'s `repo_root=Path(__file__).resolve().parent`
   override removed from the `SnapshotDataLoader.from_snapshot()` call. I
   verified this is safe before making the change, not just trusting the
   instruction: `data_loader.py`'s own `REPO_ROOT = Path(__file__).resolve().parents[2]`
   module-level default already resolves to the true project root when no
   `repo_root` is passed — confirmed by reading `data_loader.py` directly.
4. **Re-run not done — I can't do it.** I have no code-execution tool
   against this repository; everything above is a filesystem-level change,
   verified by reading files, not by running anything. The sanity-check
   rerun Preet asked for as step 4 still needs to happen, by whoever can
   actually execute Python here, before this entry's PASS/FAIL numbers
   should be treated as re-validated against the new file location. Until
   then: the relocation is complete, the numbers above are unchanged from
   before the move and unconfirmed to still load correctly.

One loose end: the now-empty directory tree at
`analysis/wq_positive_control_v1_feature_pipeline/data/snapshots/synthetic_pair_v1/`
is still there — I have no delete/rmdir tool, only `move_file`, which
leaves empty source directories behind. Harmless but not fully clean;
someone with shell access can remove it.
