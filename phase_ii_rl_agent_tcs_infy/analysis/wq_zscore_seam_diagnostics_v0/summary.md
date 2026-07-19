# Z-Score Seam Diagnostics + 730d_core phi estimate (Tier B)

## Part A: AR(1) phi estimate

An OLS AR(1) model (`spread_t = c + phi * spread_{t-1} + eps_t`) was fit on the full `730d_core` original spread sequence (length 559). 
*(Note: This is evaluated over the full series, deliberately distinct in scope from `claim_003`'s `phi_post` window. The numbers must not be conflated.)*

- **phi estimate:** 0.9599
- **95% CI:** [0.9370, 0.9828]

### Predicted Dilution Ratios
Using this fresh `phi`, the predicted theoretical performance ratios `Ratio(L) = (L-1)/L + 1/(L*(1-phi))` are compared against the prior proxies:

| L | New Prediction (phi=0.9599) | claim_002 proxy (phi=0.9506) | Observed Bootstrap |
|---|---|---|---|
| 10 | 3.39 | 2.92 | 4.83 |
| 20 | 2.20 | 1.96 | 3.05 |
| 40 | 1.60 | 1.48 | 2.13 |

**Check against single-phi fit:** The newly estimated `phi` (0.9599) lands remarkably close to the back-of-the-envelope `~0.975` estimate obtained by working backward from observed bootstrap ratios.

## Part B: Instrumented Seam Diagnostic (L=20)

Using the same `B=2000` circular block bootstrap procedure at `L=20`, original indices were carried through to identify artificial block boundaries ("seams") and whether those seams crossed the `2022-08-30` sub-regime split. 
We report the mean step-level reward at seam-adjacent steps (distance 0-3 from nearest preceding seam) vs. mid-block steps (distance $\ge$ 5).

### Pooled Seams
- **Seam-adjacent (dist 0-3):** 0.00697
- **Mid-block (dist $\ge$ 5):** 0.00102

### Regime-Crossing vs. Within-Regime
- **Regime-Crossing Adjacent:** 0.00693
- **Regime-Crossing Mid-block:** 0.00109
- **Within-Regime Adjacent:** 0.00700
- **Within-Regime Mid-block:** 0.00097

### Reward Decay Pattern (Distance from Seam)
- **Dist 0:** 0.02466
- **Dist 1:** 0.00109
- **Dist 2:** 0.00109
- **Dist 3:** 0.00104
- **Dist 4:** 0.00109
- **Dist 5:** 0.00101
- **Dist 6:** 0.00108
- **Dist 7:** 0.00110
- **Dist 8:** 0.00101
- **Dist 9:** 0.00100
- **... (Dist 10-19 avg):** 0.00101
