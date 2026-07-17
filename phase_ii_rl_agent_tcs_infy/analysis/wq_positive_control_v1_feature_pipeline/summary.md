# PC-2: Feature-pipeline positive control

**Claim ID:** `wq_positive_control_v1_pc2`
**Tier:** C

## Objective
Test whether `beta`, `eg_p`, and `eg_p_trend` as computed by the real, unmodified `feature_registry.py` preserve enough of an embedded mean-reverting signal for PPO to learn to exploit it.

## Execution
We generated a synthetic panel with a log-normal random walk `X_t` and an AR(1) spread process.
`eps_x_t ~ N(0, 0.000225) (σ_x = 0.015)`
`kappa = 0.1`, `sigma = 0.3`, `beta = 0.70`, `master_seed = 20260101`

We implemented `PC2GymPairsTradingEnv` that wraps the real environment.
- It dynamically injects 4 synthetic episode cores into the shared in-process `EPISODE_CORES` dict at import time.
- `episode_config.py` on disk is never touched.
- The 2 real admitted keys (`500d_core`, `730d_core`) are never read or modified.
- A collision guard asserts that the injected keys do not already exist.

## Results
- **Oracle PnL threshold (35%):** 9.83
- **PC-2a (cost_adjusted_pnl reward):** Reached a maximum eval_cost_adjusted_pnl of ~11.8 (exceeding 35% of oracle).
- **PC-2b (differential_sharpe reward):** Reached a maximum eval_cost_adjusted_pnl of ~12.5 (exceeding 35% of oracle).
- **Cache Hit Rate:** >98% hit rate on `eg_p` cache across 50,000 steps, demonstrating that caching correctly persists across episodes and windows.

Both PC-2a and PC-2b successfully crossed the 35% oracle threshold, validating that the real `feature_registry.py` preserves the signal structure well enough for the agent to learn.
