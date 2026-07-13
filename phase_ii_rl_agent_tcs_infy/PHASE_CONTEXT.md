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

**Branch staleness has recurred — this is not fixed, and I can't fix it
myself.** This work lives on `feat/phase2_tier_c_eg_p_trend` (three commits,
last one `1393ed92be98546ecfceac0500dd43391efd729d`). `main` is still at
`83e8fedce564c0afa4dc14cfe4eb3f46a4427871` (the `claim_005` commit) —
checked `.git/refs/heads/main` directly. This is exactly the pattern
`process_notes.md` #2 predicted ("nothing currently prevents this from
recurring on the next feature branch") and it's recurred on the very next
branch. I don't have a git-execution tool in this environment — I can read
`.git/logs/HEAD` and `.git/refs/heads/*` but I cannot run `git merge`
myself, so I can't fix this the way I could describe it being fixed
last time (that fast-forward was already done by the time I checked it, not
something I executed). Flagging directly: `main` does not currently contain
this feature work, and someone with git write access needs to merge
`feat/phase2_tier_c_eg_p_trend` into `main`.

## Root-level process finding surfaced during this work

`main` had never received a merge across this project's history before
today. Full detail, including a disagreement with how this was framed to
me, is logged at the project-root `process_notes.md` (§2) rather than
duplicated here, since it isn't Phase II-scoped — it retroactively affects
which commits Phase I's `claim_002` and `claim_003` citations were reachable
from on `main`.
