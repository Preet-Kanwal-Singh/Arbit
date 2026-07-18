# Worklog — Tier B (Phase II: RL Agent, TCS/INFY)

Chronological log of Tier B working questions and exploratory investigations
for this phase.

## 2026-07-17 — `wq_real_data_capacity_v0`: Real-data capacity check

Added manually by Desktop Claude A. This ran and was committed by Gemini
but never made it into this file — Preet flagged the gap and pasted the
spec directly; I verified the implementation against it before writing this
entry, not just transcribed the spec or `summary.md`.

**Directory:** `analysis/wq_real_data_capacity_v0/`. **Provenance:**
`git_commit 1e69bac04f299b1a4ef3479838a16b980ba2e6bb` ("Add
wq_real_data_capacity_v0 results and artifacts"), stamped from the very
next commit (`c04b9d7a...`, 0 seconds later per `.git/logs/HEAD`) — correct
ordering, holds up, and confirmed as `main`'s current tip. Direct to `main`,
no feature branch, per spec §6.

**Setup, checked against the spec line by line in `train_real_data.py`:**
PPO on `GymPairsTradingEnv(core_id="730d_core",
snapshot_id="tcs_infy_v4_2026-07-13", reward_name="differential_sharpe",
cost_rate=0.0)`, 200,000 timesteps, `MlpPolicy` with no hyperparameter
overrides — PPO defaults throughout, unlike PC-2's `n_steps` deviation.
Shadow-eval env on `cost_adjusted_pnl`, logged once per traversal via
`custom/eval_cost_adjusted_pnl`, with the same train/eval desync
`AssertionError` guard used in `wq_smoke_training_v0`/PC-1/PC-2. Best-model
checkpointing added to the callback as specified — confirmed a genuine
running-max check gated `model.save()`, not a periodic save. All three
baselines present and matching spec exactly: always-flat (single
deterministic pass), z-score with the specified 10-step warm-up guard
(single deterministic pass), random action via a `np.random.default_rng(42)`
instance decoupled from the env/model RNGs, run for 357 traversals
(spec's own ≈200,000/560 estimate), mean and std both reported.

**Results (cross-checked against `temp_results.json`, not just
`summary.md`'s prose — they match exactly):**

| | Value |
|---|---|
| Always-flat | 0.0000 |
| Random (357 traversals) | mean 0.00095, std 0.13316 |
| Z-score (expanding, 10-step warmup) | 0.39087 |
| PPO, final 10 traversals avg | 0.03429 |
| PPO, best single traversal | 0.46550 |

Z-score clears both PPO's converged average and is well outside random's
observed spread. PPO's converged policy is statistically indistinguishable
from random. Purely descriptive, no pass/fail threshold, per spec — and
the entry doesn't need one to be informative.

**The most important finding here isn't in the table — it's a check that
wasn't in the spec at all.** After training, the script reloads
`best_model.zip` and replays it *deterministically* through a fresh eval
env. That replay produced `0.0252`, not the `0.4655` peak logged during
training. The gap means the logged "best" traversal was very likely driven
by a lucky draw from PPO's stochastic action sampling during rollout
collection, not a reproducible capability of the checkpointed policy —
`0.4655` should not be read as "the policy can do this," and `summary.md`
correctly doesn't lean on it in its conclusion. This is good, honest
engineering — flagging it prominently because it's easy to miss on a quick
read of the headline numbers, not to criticize the work.

**Two things I can't independently verify, worth knowing:**
- `temp_results.json` (the only structured, persisted result artifact)
  contains `best_pnl` but no `best_timestep`/`best_traversal` field. The
  "timestep 171448, traversal 307" figure in `summary.md` only exists in a
  `print()` statement in the code — not saved anywhere I can re-check. I'm
  taking it on `summary.md`'s word, same as any figure in this project I
  can't re-derive from a saved artifact.
- The `0.0252` deterministic-replay sanity-check value has the same
  property — printed to console, never written to `temp_results.json` or
  anywhere else. I have no code-execution tool against this repo to
  re-run the check myself and confirm it. Flagging as unverified-but-plausible,
  not as a reason to doubt it — the mechanism described (stochastic
  sampling vs. deterministic replay) is a real and well-known PPO gap, this
  isn't an implausible claim, I just can't independently confirm the exact
  number.

**One minor format departure:** this `provenance.json` lists output paths
only, no per-file sha256 — every other provenance file in this project,
Tier A through C, includes hashes. Not a Tier B requirement, but worth
knowing this one's thinner than the norm if anyone goes looking for a hash
to check later.

**Tier:** B, per spec and per `provenance.json`. No `VERIFIED_FACTS.md`
admission — correctly none intended.
