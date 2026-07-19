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

## 2026-07-18 — `wq_zscore_block_bootstrap_v0`: Z-score block-bootstrap check

**Directory:** `analysis/wq_zscore_block_bootstrap_v0/`.

**Setup:** Evaluated the deterministic Z-score rule (expanding mean/std, 10-step flat warm-up guard, `clip(-z, -1, 1)`, `cost_rate=0.0`) on circular block-bootstrapped resamples of the `730d_core` real data spread sequence (snapshot `tcs_infy_v4_2026-07-13`). `B=2000` resamples per block length. `seed=42`.

**Results:**
- **L=10:** Mean PnL = 1.8885 | Std = 0.2555 | p-value (Fraction $\ge$ 0.3909) = 1.0000
- **L=20 (Primary):** Mean PnL = 1.1914 | Std = 0.2062 | p-value (Fraction $\ge$ 0.3909) = 1.0000
- **L=40:** Mean PnL = 0.8322 | Std = 0.1780 | p-value (Fraction $\ge$ 0.3909) = 0.9990

**Note:** No threshold was set because none was needed at this tier. The bootstrapped null distribution produces systematically higher PnL than the original path. If this is ever promoted to Tier A, the threshold and comparison family must be fixed before the promoted run.

## 2026-07-19 — `wq_zscore_seam_diagnostics_v0`: Z-score seam diagnostics + 730d_core φ estimate

**Directory:** `analysis/wq_zscore_seam_diagnostics_v0/`.

**Setup:** 
- **Part A:** Fit an AR(1) OLS model on the full `730d_core` original spread sequence to estimate $\phi$.
- **Part B:** Re-ran `B=2000` circular block bootstraps at `L=20` tracking the original indices to detect and characterize the artificial boundaries ("seams"), including classification around the `2022-08-30` sub-regime split.

**Results:**
- **Part A:** The fresh OLS estimate over the entire series is **$\phi$ = 0.9599** (95% CI: [0.9370, 0.9828]). This generated dilution ratios of 3.39 (L=10), 2.20 (L=20), and 1.60 (L=40), which land remarkably close to the back-of-the-envelope `~0.975` estimate that was obtained by working backward from observed bootstrap ratios.
- **Part B (Seam Rewards):** The jump artifact strictly localized at the block seams accounts for the vast majority of the inflated PnL. The average reward precisely at the seam (distance 0) was `0.02466`, whereas distances 1-19 were completely flat, averaging just `~0.00101`. There were no meaningful differences when comparing seam-adjacent vs mid-block crossing boundaries inside or across regimes.

## 2026-07-19 — `wq_zscore_seam_diagnostics_v1`: Z-score seam diagnostics (per-seam rerun)

**Directory:** `analysis/wq_zscore_seam_diagnostics_v1/`.

**Setup:** 
Same underlying logic as `v0` (L=20, B=2000, `cost_rate=0.0`), but saved exactly one raw record per seam crossing (distance 0) containing the `reward_at_dist0`, `position_in_path`, and `is_regime_crossing` status into a flat CSV (54,000 observations).

**Results:**
- **Regime Comparison:** 
  - Regime-Crossing (`n`=20,827): mean 0.02450, SE 0.00023
  - Within-Regime (`n`=33,173): mean 0.02476, SE 0.00019
  - Difference: mean -0.00026, SE 0.00030
- **Path Stratification (Quartiles):**
  - Q1 (0-25%): 0.02227 | Q2 (25-50%): 0.02514 | Q3 (50-75%): 0.02549 | Q4 (75-100%): 0.02538

**Note:** The difference between regime-crossing and within-regime seams is statistically indistinguishable from zero, and both groups have large sample sizes. Furthermore, the quartile stratification reveals the seam reward is completely flat across Q2-Q4 rather than decaying. This debunks the hypothesis that the artifact is purely driven by early finite-sample noise in the running mean, pointing instead to the inherent structural nature of the per-event reward at the disjoint boundary.

## 2026-07-19 — `wq_zscore_seam_diagnostics_v1` (Seam-index Reanalysis)

**Directory:** `analysis/wq_zscore_seam_diagnostics_v1/`.

**Setup:** 
Loaded the existing `seams_raw.csv` and derived a precise block `seam_index = round(position_in_path * T / L)`. Tracked granular `n`, `mean`, and `SE` exactly at seams 1 through 5, and pooled 6+.

**Results:**
- **Index 1:** `n`=2,000, `mean`=0.01584, `SE`=0.00094
- **Index 2:** `n`=2,000, `mean`=0.02228, `SE`=0.00084
- **Index 3:** `n`=2,000, `mean`=0.02273, `SE`=0.00079
- **Index 4:** `n`=2,000, `mean`=0.02229, `SE`=0.00078
- **Index 5:** `n`=2,000, `mean`=0.02449, `SE`=0.00077
- **Index 6+:** `n`=44,000, `mean`=0.02537, `SE`=0.00016

**Note:** The results firmly disconfirm the noisy-early-mean hypothesis. If the artifact was driven by early unstable estimates, Index 1 should show the highest elevation. Instead, Index 1 is strictly *lower* than 6+ and well outside its standard error bound. The elevation effect does not decay; it actually grows stronger as the running mean stabilizes over time.
