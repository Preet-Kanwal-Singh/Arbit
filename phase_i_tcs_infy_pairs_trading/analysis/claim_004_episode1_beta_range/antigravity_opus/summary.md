<!--
script_path: C:\Users\preet\OneDrive\Desktop\Skool\Arbit\analysis\claim_004_episode1_beta_range\antigravity_opus\claim_004.py
git_commit: 1717ffb3ed62e6b502d7c6ef2791545737673d89
snapshot_id: tcs_infy_v1_2026-07-04
timestamp_utc: 2026-07-09T05:32:51.932797+00:00
beta_series_500d_core.csv_sha256: ac8e7bd2e994ac04b4b2b4aff2594605f8dd67d1925b93753e5cafcba5c3aab4
beta_series_730d_core.csv_sha256: e258a1a00552953d61cb8e8bd06794a0024724560f99e2d850492f4268dc0712
-->

# Claim 004: Episode 1 Beta Range -- Antigravity/Opus

## Isolation Declaration

This implementation has not read, opened, or referenced:
- `analysis/wq_recompute_episode1_beta_range/`
- `analysis/wq_recompute_episode1_beta_range_v2/`
- `ledger/worklog/worklog_tier_b.md`
- `analysis/claim_004_episode1_beta_range/codex/`

## Method

y = log(TCS.NS), x = log(INFY.NS). At each month-end trading date
within the core's date range (inclusive), OLS with intercept over the
trailing N trading days (N = window length). Beta = coefficient on x.
No pooling across cores or window lengths.

## 500d Core (2020-01-31 to 2021-12-31)

| Statistic | Value |
|-----------|-------|
| n observations | 24 |
| min beta | 0.545092 |
| max beta | 0.977381 |
| mean beta | 0.681181 |
| median beta | 0.659427 |
| std beta | 0.103646 |
| first observation | 2020-01-31, beta = 0.977381 |
| last observation | 2021-12-31, beta = 0.666108 |
| skipped month-ends | none |

## 730d Core (2020-12-31 to 2023-03-31)

| Statistic | Value |
|-----------|-------|
| n observations | 28 |
| min beta | 0.647704 |
| max beta | 0.749515 |
| mean beta | 0.670869 |
| median beta | 0.662592 |
| std beta | 0.024954 |
| first observation | 2020-12-31, beta = 0.749515 |
| last observation | 2023-03-31, beta = 0.663902 |
| skipped month-ends | none |

## Limitation

These are month-end sample points only. Beta could move outside
the reported range between sampled points. This does not characterize
intra-month excursions.
