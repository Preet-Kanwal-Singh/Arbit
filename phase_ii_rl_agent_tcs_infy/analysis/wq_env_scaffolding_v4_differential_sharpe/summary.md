# Summary: Tier C — differential_sharpe reward

## Work Completed
1. **`differential_sharpe` implementation** (`env/reward_registry.py`): Moody-Saffell differential Sharpe ratio, using persistent per-episode `A_t`/`B_t` EMA state (`eta=0.01` default). Reuses `compute_cost_adjusted_pnl` directly for `R_t` rather than restating the formula, so the two reward functions cannot drift apart on what "cost-adjusted return" means.
   - **Bug found and fixed in review**: the denominator `(B_prev - A_prev**2) ** 1.5` was originally exponentiated before being checked against the epsilon floor. Since Python's `**` returns a complex number for a negative base with a non-integer exponent, any float-precision cancellation pushing the pre-exponent quantity slightly negative would crash the step with a complex/float comparison TypeError, not a bad-but-survivable reward. Fixed by checking `variance_est = B_prev - A_prev**2` against `dsr_epsilon` before exponentiating.
   - `compute_differential_sharpe` mutates its `ctx` argument in place (`dsr_A`/`dsr_B`) to persist EMA state to the caller — documented via docstring, since this is asymmetric with `compute_cost_adjusted_pnl`'s pure-function behavior.
2. **Environment changes** (`pairs_trading_env.py`): `_dsr_A`/`_dsr_B` persist within an episode, reset to `0.0` in both `__init__` and `reset()` — confirmed no cross-episode leakage.
3. **Acceptance test** (`wq_env_scaffolding_v4_differential_sharpe`):
   - Boundary checks against both cores, matches expected dates.
   - Fallback correctness: for every step where the independently-tracked `variance_est <= dsr_epsilon`, asserts `reward == R_t` exactly.
   - Post-warmup sanity: asserts finite reward for the remainder of each episode once `variance_est > dsr_epsilon`.
   - Cross-check against `cost_adjusted_pnl` (`cost_rate=0.0` both): confirms `differential_sharpe` output is not a fixed scalar multiple of `cost_adjusted_pnl` output across the run (multiple distinct rounded ratios observed under the random policy, both cores). **This is a smoke test that the DSR math is doing something distinct from the base P&L reward — it is not a proof of formula correctness.**
   - Tested at `dsr_epsilon=1e-6`, the actual environment default — an earlier version of this test used `1e-8`, which was corrected before this was considered complete, since the earlier value meant the acceptance evidence didn't cover the configuration that actually ships.
   - **Snapshot Choice**: `tcs_infy_v4_2026-07-13`, same buffer-extension reasoning as `wq_env_scaffolding_v3_reward_registry` — see `provenance.json`.

## dsr_warmup_steps default: 100 (provisional)

Set via reconnaissance across 5 fixed random-policy seeds (42, 7, 123, 2024, 99),
both cores. A trailing 20-step coefficient-of-variation < 0.25 criterion on
variance_est placed the latest observed settling point at step 86 (730d_core,
seed 7); 100 provides margin above that. 86 is not a formally established
boundary — the CV criterion is a reconnaissance diagnostic, not a validated
statistical test, and this is Tier C scaffolding, not a Tier A claim.

Late-episode reward extremes (e.g. step 420/477 on 500d_core, seed 42; step
284/559 on 730d_core, seed 7) occur well after variance_est has settled by
this criterion and are not explained by initialization. These are recorded as
known observed DSR behavior under this diagnostic, not a confirmed failure
mode. No reward clipping has been added. Whether these extremes materially
affect optimization is deferred to Tier C smoke training with the actual RL
algorithm, per training diagnostics below.

## Deliverables
- `phase_ii_rl_agent_tcs_infy/env/reward_registry.py` (`differential_sharpe` added)
- Modifications to `phase_ii_rl_agent_tcs_infy/env/pairs_trading_env.py`
- `phase_ii_rl_agent_tcs_infy/analysis/wq_env_scaffolding_v4_differential_sharpe/`