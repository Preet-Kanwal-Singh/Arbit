# PC-1: Oracle-state positive control

## Objective
Establish whether the PPO training harness (with `cost_adjusted_pnl` and `differential_sharpe` rewards) can learn to exploit an unambiguously profitable synthetic spread signal. A success condition requires that the agent realizes at least 50% of the oracle P&L over the final 5 of 25 rollouts (50,000 steps).

## Setup
We generated a continuous 51,000-step synthetic spread trajectory using an AR(1) mean-reverting process:
- `kappa = 0.1`
- `sigma = 0.3`
- `master_seed = 20260101`
- `spread_0 ~ N(0, sigma_stationary^2)`

We built a `SyntheticOracleEnv` which exposes this continuous trace across 100 sequential 500-step episodes (`[500k, 500(k+1))`), mirroring the slicing mechanism in `PairsTradingEnv`. Crucially, this environment strictly preserves the causal action-observation alignment found in the main environment (where an action chosen after observing the state at $T_t$ evaluates over the $T_{t+1} - T_t$ return).

## Oracle Baseline
Using the policy `action_t = -sign(spread_t)`, we evaluated the theoretical maximum performance:
- `oracle_mean_episode_pnl`: 27.28
- `p99_threshold_pnl`: 0.80
- `oracle_mean_episode_dsr`: 8.15
- `p99_threshold_dsr`: 2.83

The 50% success threshold for both training passes was thus set to **13.64** realized `eval_cost_adjusted_pnl`.

## Results
### PC-1a (Cost-Adjusted P&L)
The agent achieved an average of **24.18** `eval_cost_adjusted_pnl` across the final 5 rollouts (88% of oracle).
- **Result**: PASS

### PC-1b (Differential Sharpe)
The agent achieved an average of **23.84** `eval_cost_adjusted_pnl` across the final 5 rollouts (87% of oracle).
- **Result**: PASS

## Conclusion
Both reward functions correctly align the gradient with P&L on a learnable signal. The harness is sound. We can now proceed to evaluating real data, with the assurance that if the agent fails to learn on TCS/INFY, it is due to signal/noise ratio or non-stationarity, not a broken scaffolding or broken reward function.

**Next step (PC-2)**: Open question pending, to verify feature structure preservation (`beta` / `eg_p` / `eg_p_trend`).
