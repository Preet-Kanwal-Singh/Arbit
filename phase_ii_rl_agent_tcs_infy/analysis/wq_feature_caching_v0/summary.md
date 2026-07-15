# Feature Caching Acceptance Test

## Objective
Verify that making the `eg_p` cache persistent across an environment's lifespan (instead of resetting per step) does not alter the output values in any way (must be bit-identical) and improves the step execution speed.

## Results
- **Bit-Identical Output**: Both `500d_core` and `730d_core` full-episode traces matched the pre-change baseline exactly. Not a single floating point deviation occurred.
- **Performance (FPS)**:
  - **`500d_core`**: 29.20 FPS (before) -> 45.05 FPS (after) — **~1.54x improvement**
  - **`730d_core`**: 19.91 FPS (before) -> 33.01 FPS (after) — **~1.66x improvement**

The single persistent dictionary successfully bypasses the redundant statsmodels `coint()` recalculation for the `eg_p_trend` 20-day lookback window across steps without breaking cross-ticker isolation.
