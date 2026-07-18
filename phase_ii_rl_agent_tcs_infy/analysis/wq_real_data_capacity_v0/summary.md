# Real-Data Capacity Check — Tier B (wq_real_data_capacity_v0)

## Objective
Train PPO on the `730d_core` of real data (TCS/INFY) and compare its capability against three baselines (Random, Flat, Z-score) using an exploratory real-data capacity check.

## Baseline Results
- **Always-Flat PnL**: `0.0000`
- **Random Action PnL**: Mean `0.0009`, Standard Deviation (std) `0.1332` (over 357 traversals using a decoupled RNG)
- **Z-Score Baseline PnL**: `0.3909` (using an expanding mean/std of spread, with a 10-step initial flat warm-up guard)

## PPO Training Results (200,000 steps)
- **Final 10 Traversals Average PnL**: `0.0343`
  - The model slightly out-performed the random baseline mean, but is well within one standard deviation (0.1332) of zero noise.
- **Best Single-Traversal PnL**: `0.4655`
  - *Checkpoint Reference*: Occurred at `timestep 171448`, `traversal 307` (`best_model.zip`).
- **Post-Training Sanity Check**: `0.0252`
  - *Note on desync*: Replaying `best_model.zip` deterministically through a fresh evaluation environment yielded a PnL of 0.0252 rather than the logged stochastic peak of 0.4655. This indicates that the peak observed during training was driven primarily by stochastic action sampling rather than a deterministic policy that consistently reproduces the same performance.

## Conclusion
The expanding-window Z-score baseline achieved a PnL of 0.3909, substantially exceeding both the PPO policy's final average (0.0343) and the random baseline's observed variability. PPO's learned policy remained indistinguishable from the random baseline over its converged evaluation window, indicating that under the current training configuration it did not recover the mean-reversion signal exploited by the simple heuristic.

This exploratory study establishes that PPO did not match the simple Z-score baseline under the tested configuration; it does not identify which component of the learning pipeline is responsible.
