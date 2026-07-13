# Summary: Tier C — Reward Registry + cost_adjusted_pnl

## Work Completed
1. **Reward Registry**: Created `env/reward_registry.py` mirroring `feature_registry.py`'s pattern. Implemented `RewardContext` protocol and the default `RewardRegistry`.
2. **`cost_adjusted_pnl` implementation**: Implemented the exact required reward formulation for `cost_adjusted_pnl`, cleanly factoring position spreads while accounting for cost deductions based on positional churn.
   - **Design Decision**: When `previous_spread` is `None` (on the first step), `pnl` defaults to `0.0`, but the cost term applies explicitly using the `previous_position = 0.0` reset state. Entering a position for the first time is a real trade and carries execution costs.
3. **Environment Refactor (`pairs_trading_env.py`)**:
   - Added `reward_registry`, `reward_name`, and `cost_rate` to initialization.
   - Captured `_previous_position` seamlessly before the action-driven state transition in `step()`, avoiding ordering bugs mirroring the existing spread tracking.
   - Evaluated the new reward registry within `step()`.
4. **Acceptance Test (`wq_env_scaffolding_v3_reward_registry`)**:
   - Designed a new test suite maintaining the current NaN/Inf validations while adding dual-instance simulations (`env0` with `cost=0.0` vs `env1` with `cost=0.01`).
   - Ran an exact regression check where the new default framework (with zero cost) rigorously matched the original `placeholder_spread_pnl` at every step over thousands of loops.
   - Executed a strict-decrease sanity validation where `cost_rate=0.01` appropriately depreciated the resulting reward exclusively during steps recording non-zero positional changes.

## Deliverables
- `phase_ii_rl_agent_tcs_infy/env/reward_registry.py`
- Modifications to `phase_ii_rl_agent_tcs_infy/env/pairs_trading_env.py`
- `phase_ii_rl_agent_tcs_infy/analysis/wq_env_scaffolding_v3_reward_registry/`
- Provenance accurately stamped tracking the test evaluations.
