# Claim 003: EG-Halflife Ordering Robustness -- Antigravity/Opus

## Provenance

- Script: `C:\Users\preet\OneDrive\Desktop\Skool\Arbit\analysis\claim003\antigravity_opus\claim_003.py`
- Git commit: `dcd5f465aff03bbcf448a8e845767d364cfae098`
- Snapshot: `tcs_infy_v1_2026-07-04`
- Timestamp UTC: `2026-07-06T11:33:46.807691+00:00`
- Replicates: B=2000, seed=42
- `cell_results.csv` SHA256: `f27fcec61bc3e2dd970defb541343a30ef28985f1f0b15aae80b6d97893af822`

## Study-Level Classification: CONTRADICTED

### 500d Window

- Classification: **ROBUST**
- WELL-POWERED: True
- PARAMETER-STABLE: False

| Config | EG thresh | HL thresh | N_eff | P_hat | CI_lo | CI_hi | Classification | EG-only | HL-only | Neither | Simul |
|--------|-----------|-----------|-------|-------|-------|-------|----------------|---------|---------|---------|-------|
| C1 | 0.05 | 20.0 | 1322 | 0.9947 | 0.9891 | 0.9979 | ROBUST | 0.063 | 0.0 | 0.013 | 0.263 |
| C2 | 0.03 | 20.0 | 1381 | 0.9978 | 0.9937 | 0.9996 | ROBUST | 0.07 | 0.0 | 0.006 | 0.2335 |
| C3 | 0.1 | 20.0 | 1019 | 0.9588 | 0.9447 | 0.9701 | ROBUST | 0.0445 | 0.0015 | 0.0315 | 0.413 |
| C4 | 0.05 | 15.0 | 554 | 0.7347 | 0.6958 | 0.771 | ROBUST | 0.005 | 0.003 | 0.01 | 0.705 |
| C5 | 0.05 | 25.0 | 1409 | 1.0 | 0.9974 | 1.0 | ROBUST | 0.1535 | 0.0 | 0.013 | 0.129 |

**Spread AR(1) parameters:**

- phi_pre = 0.950351 (SE = 0.014359)
- phi_post = 0.988012 (SE = 0.008303)
- PARAMETER-UNSTABLE: True

**Real-data anchor:**

| Config | EG crossing | HL crossing | Order |
|--------|------------|------------|-------|
| C1 | 2022-01-31 | 2023-04-30 | EG-first |
| C2 | 2022-01-31 | 2023-04-30 | EG-first |
| C3 | 2023-02-28 | 2023-04-30 | EG-first |
| C4 | 2022-01-31 | 2022-03-31 | EG-first |
| C5 | 2022-01-31 | 2023-04-30 | EG-first |

### 730d Window

- Classification: **CONTRADICTED**
- WELL-POWERED: True
- PARAMETER-STABLE: True

| Config | EG thresh | HL thresh | N_eff | P_hat | CI_lo | CI_hi | Classification | EG-only | HL-only | Neither | Simul |
|--------|-----------|-----------|-------|-------|-------|-------|----------------|---------|---------|---------|-------|
| C1 | 0.05 | 20.0 | 286 | 0.2972 | 0.2448 | 0.3538 | CONTRADICTED | 0.046 | 0.077 | 0.5145 | 0.2195 |
| C2 | 0.03 | 20.0 | 300 | 0.8533 | 0.8082 | 0.8914 | ROBUST | 0.088 | 0.0105 | 0.4725 | 0.279 |
| C3 | 0.1 | 20.0 | 283 | 0.0883 | 0.058 | 0.1276 | CONTRADICTED | 0.0165 | 0.195 | 0.544 | 0.103 |
| C4 | 0.05 | 15.0 | 500 | 0.022 | 0.011 | 0.039 | CONTRADICTED | 0.0055 | 0.368 | 0.2235 | 0.153 |
| C5 | 0.05 | 25.0 | 342 | 0.9766 | 0.9544 | 0.9898 | ROBUST | 0.1765 | 0.0015 | 0.59 | 0.061 |

**Spread AR(1) parameters:**

- phi_pre = 0.961848 (SE = 0.01145)
- phi_post = 0.883325 (SE = 0.030395)
- PARAMETER-UNSTABLE: False

**Real-data anchor:**

| Config | EG crossing | HL crossing | Order |
|--------|------------|------------|-------|
| C1 | 2023-04-30 | 2023-04-30 | simultaneous |
| C2 | 2023-04-30 | 2023-04-30 | simultaneous |
| C3 | 2023-05-31 | 2023-04-30 | HL-first |
| C4 | 2023-04-30 | 2023-04-30 | simultaneous |
| C5 | 2023-04-30 | 2023-05-31 | EG-first |

## Stated Limitations

- 500d and 730d cores and degradation windows overlap; a WINDOW-LENGTH-DEPENDENT or CONTRADICTED result reflects overlapping, not independent, procedures.
- INFY's AR(1)-residual treatment preserves first-order serial correlation but not volatility clustering.
- Simulation uses bootstrap residuals (resampling with replacement), preserving marginal distribution but not temporal dependence of innovations.

## Method

Fixed-transition regime-switching simulation. Pre-regime parameters fitted on daily data within the strict healthy core; post-regime parameters fitted on daily data from the day after core end through 2023-12-31. INFY daily log-returns and spread (OLS residuals) each modeled as AR(1) with bootstrap innovations drawn from the regime-specific residual pool. At each month-end in the degradation window, the rolling pipeline re-estimates beta via OLS, computes Engle-Granger p-value via coint(trend='c', autolag='aic'), and half-life via AR(1) on the rolling OLS residuals. Crossing order determined by which metric first exceeds its threshold. P_hat = EG-first / (EG-first + HL-first); CI is Clopper-Pearson exact binomial at 95%.