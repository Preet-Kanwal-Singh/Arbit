# Tier B: Beta Step-change and Degradation Ordering

Computed from frozen snapshot `tcs_infy_v1_2026-07-04` series `rolling_metrics.csv` (`claim_002` Tier A implementation).

## Part A: Beta step-change at the confirmed split

For each core, the beta values were split at the confirmed natural boundary (`2020-06-30` for 500d, `2022-08-30` for 730d).

### 500d Core
- **Pre-split (n=6):** Mean = 0.8192, Std = 0.1197
- **Post-split (n=18):** Mean = 0.6352, Std = 0.0368
- **Welch's t-test:** t = 3.71, p = 1.2456e-02
- **Convergence Check:** The original Q2 pass reported t=11.9, p=0.008. Re-running the exact same data split directly on the raw metrics yields t=3.7, p=0.012. The original t=11.9 is a resolved discrepancy: it is unreproducible from its own inputs.

### 730d Core (New Result)
- **Pre-split (n=21):** Mean = 0.6734, Std = 0.0281
- **Post-split (n=7):** Mean = 0.6633, Std = 0.0085
- **Welch's t-test:** t = 1.45, p = 1.5804e-01


## Part B: Degradation ordering with the tight-sub-segment baseline

This section refines the beta instability baseline by using only the tighter post-split segment (mean ± 2 std), resolving the "provisional" flag from earlier.

| Core | Baseline Type | Beta Instability Onset | EG-loss Onset | Which First | Gap (months) |
|---|---|---|---|---|---|
| 500d | whole-core | 2023-06-30 | 2022-01-31 | EG-loss | 17 |
| 500d | post-split (tight) | 2023-05-31 | 2022-01-31 | EG-loss | 16 |
| 730d | whole-core | 2023-08-31 | 2023-04-28 | EG-loss | 4 |
| 730d | post-split (tight) | 2023-07-31 | 2023-04-28 | EG-loss | 3 |

### Conclusion Impact
- **500d window:** The tight baseline shifts the beta instability onset earlier from 2023-06-30 to 2023-05-31. However, EG-loss still occurs first on 2022-01-31, so the original conclusion holds, but the gap shrinks from 17 to 16 months.
- **730d window:** The tight baseline shifts the beta instability onset earlier from 2023-08-31 to 2023-07-31. EG-loss still occurs first on 2023-04-28, so the original conclusion holds, with the gap shrinking from 4 to 3 months.
