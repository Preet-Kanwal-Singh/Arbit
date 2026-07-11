<!--
script_path: C:\Users\preet\OneDrive\Desktop\Skool\Arbit\analysis\claim_004_episode1_beta_range\codex\compute_episode1_beta_range.py
git_commit: 1717ffb3ed62e6b502d7c6ef2791545737673d89
snapshot_id: tcs_infy_v1_2026-07-04
timestamp_utc: 2026-07-09T05:24:31.611552+00:00
output_content_sha256: 07eb561bf73b38871fa6962847b80e1c94389d1a2ecb45ad0c6debf1d6c93cd1
output_hash_scope: bytes after this provenance header
final_file_sha256: recorded in provenance.json
-->
# Claim 004 Episode 1 Beta Range - Codex

## Inputs

- Claim ID: `claim_004_episode1_beta_range`
- Snapshot: `tcs_infy_v1_2026-07-04`
- Price file: `data/snapshots/tcs_infy_v1_2026-07-04/adjusted_close.csv`
- Columns: `date`, `TCS.NS`, `INFY.NS`; rows missing either price dropped.
- No live pulls and no snapshot regeneration.

## Method

- `y = log(TCS.NS)`, `x = log(INFY.NS)`.
- Month-end trading dates within each supplied core boundary, inclusive.
- OLS with intercept over the trailing N trading days ending at each month-end.
- Beta is the coefficient on `x`; no pooling across cores or window lengths.
- Standard deviation is sample standard deviation (`ddof=1`).

## Results

| core_id | window_length | observations | min_beta | max_beta | mean_beta | median_beta | std_beta_sample_ddof1 | first_date | first_beta | last_date | last_beta |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | --- | ---: |
| 500d_core | 500 | 24 | 0.545092233079 | 0.977380658908 | 0.681180554957 | 0.659426694105 | 0.103646156153 | 2020-01-31 | 0.977380658908 | 2021-12-31 | 0.666108079493 |
| 730d_core | 730 | 28 | 0.647703964009 | 0.749515134878 | 0.670868819708 | 0.662591966026 | 0.024954253775 | 2020-12-31 | 0.749515134878 | 2023-03-31 | 0.663901726332 |

## Skipped Month-Ends

- `500d_core`: None
- `730d_core`: None

## Output Files

- `analysis\claim_004_episode1_beta_range\codex\beta_series_500d_core.csv` final SHA256 `dd5397d13ec185b6ec2298b89464084082dee21907bbc665df4f95ff2b6add72`
- `analysis\claim_004_episode1_beta_range\codex\beta_series_730d_core.csv` final SHA256 `e088588c9813af4862598ff38992fddfd709fbee50bc27d58d9ade5043e6a30c`

## Limitation

This output characterizes beta only at month-end sample points inside the supplied core boundaries. It does not characterize intra-month beta movement.
