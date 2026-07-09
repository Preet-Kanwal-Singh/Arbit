# Episode 1 Recomputed Beta Range v2

This descriptive reconstruction replaces both the historically untraceable "0.20–1.91" figure and the flawed v1 recomputation (which incorrectly pooled multiple window lengths over an unestablished 2018–2023 date range).

The values below establish the authoritative reference for Episode 1 beta ranges, computed individually for each of the two established healthy cores using their matching window lengths, straight from the frozen snapshot (`tcs_infy_v1_2026-07-04`).

## 500d Strict Core (2020-01-31 to 2021-12-31)
- **Minimum β:** 0.545092
- **Maximum β:** 0.977381
- **Mean β:** 0.681181
- **Median β:** 0.659427
- **Standard Deviation:** 0.103646
- **First Observation:** 2020-01-31 (β: 0.977381)
- **Last Observation:** 2021-12-31 (β: 0.666108)
- **Number of Observations:** 24 month-end β calculations

## 730d Strict Core (2020-12-31 to 2023-03-31)
- **Minimum β:** 0.647704
- **Maximum β:** 0.749515
- **Mean β:** 0.670869
- **Median β:** 0.662592
- **Standard Deviation:** 0.024954
- **First Observation:** 2020-12-31 (β: 0.749515)
- **Last Observation:** 2023-03-31 (β: 0.663902)
- **Number of Observations:** 28 month-end β calculations

*Note: No smoothing, filtering, thresholding, or statistical inference was applied. The computation strictly followed the established rolling-beta implementation on the frozen snapshot.*
