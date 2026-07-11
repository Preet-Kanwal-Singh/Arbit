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

## Root-level process finding surfaced during this work

`main` had never received a merge across this project's history before
today. Full detail, including a disagreement with how this was framed to
me, is logged at the project-root `process_notes.md` (§2) rather than
duplicated here, since it isn't Phase II-scoped — it retroactively affects
which commits Phase I's `claim_002` and `claim_003` citations were reachable
from on `main`.
