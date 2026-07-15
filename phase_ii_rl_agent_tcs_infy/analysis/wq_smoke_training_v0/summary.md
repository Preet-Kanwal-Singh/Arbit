# PPO Smoke Training Diagnostics

This summarizes the results of the 50,000 timestep smoke training run (`phase_ii_rl_agent_tcs_infy/analysis/wq_smoke_training_v0`).

**Note:** `total_timesteps=50_000` is purely a smoke testing budget. This corresponds to approximately 104 episodes (at ~477 steps each) and is intended solely to verify infrastructure, stability, and absence of immediate reward hacking. It is **not** a claim about converged agent quality or a fully trained model.

## 1. Network Stability (NaNs/Infs)
- **Result:** **Stable.** 
- **Details:** The SB3 built-in logger (policy loss, value loss, explained variance, gradient norm) remained finite throughout the entire run. There were zero occurrences of `nan` or `inf` in any metric. The training completed its 25 iterations (51,200 timesteps) successfully.

## 2. Reward Outlier Frequency (`|reward| > 5.19`)
- **Result:** **Stable, no explosion.**
- **Details:** The outlier count remained in the low single digits per rollout (consistently between 4 and 9 steps per 2048-step rollout). The differential Sharpe transformation successfully contained the reward scale without breaking down as the policy updated.

## 3. Parallel Metric: Realized Cost-Adjusted P&L
- **Result:** **No reward hacking signature.**
- **Details:** The episode-level realized `cost_adjusted_pnl` metric hovered around zero, ranging between roughly `-0.17` and `+0.20`. The training reward (`ep_rew_mean`) did not artificially detach or trend exponentially upward while the real P&L remained flat. There is no telltale divergence indicating the agent is exploiting a mathematical loophole in the differential Sharpe formula.

## 4. Action Distribution (Exploitation Signature Check)
- **Result:** **Nominal exploration, no pathological jitter.**
- **Details:** The `action_diff_mean` (mean of `|action_t - action_{t-1}|`) started at ~1.15 and ended at ~1.07. The standard deviation remained stable (~0.8). An action diff mean of ~1.0 in a `[-1, 1]` action space is consistent with continued wide exploration. Importantly, there was no shift toward extreme, high-frequency position flapping (which would have manifested as a shrinking action diff mean coupled with zero improvement in P&L, signaling degenerate exploitation).
