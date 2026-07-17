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
  - *Note on desync*: Replaying `best_model.zip` deterministically through a fresh `eval_env` yielded a PnL of 0.0252, failing to reproduce the logged stochastic 0.4655 peak. This indicates that the 0.4655 peak during training was largely a lucky sequence of stochastic action sampling rather than a persistently exploitable deterministic policy edge, or that the empty cache initialization in the fresh environment affected the reproduction.

## Conclusion
PPO failed to learn a consistent policy that outperforms the Z-score baseline (0.3909) on real data. While its absolute best lucky traversal (0.4655) nominally exceeded the Z-score, the deterministic replay and the final 10-episode average (0.0343) confirm that the policy did not reliably converge to an exploitable real-data edge in 200,000 steps.
