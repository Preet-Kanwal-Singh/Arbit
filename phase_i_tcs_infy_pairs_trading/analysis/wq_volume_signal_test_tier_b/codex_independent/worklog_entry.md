<!--
script_path: C:\Users\preet\OneDrive\Desktop\Skool\Arbit\phase_i_tcs_infy_pairs_trading\analysis\wq_volume_signal_test_tier_b\codex_independent\run_volume_signal_independent.py
git_commit: 1b7aaa9b2fc9029938da29bc81210e285444ce64
snapshot_id: tcs_infy_v2_2026-07-11; nifty_it_benchmark_v1_2026-07-11; rolling_metrics=tcs_infy_v1_2026-07-04
timestamp_utc: 2026-07-12T08:03:53.741912+00:00
output_file: worklog_entry.md
output_content_sha256: f2ce62a242591fe7597ba470cf26873e7c7afff9b2826a5511fe2ec57cb9e591
output_hash_scope: bytes after this provenance header
final_file_sha256: recorded in provenance.json
-->
## wq_volume_signal_test_tier_b_codex_independent

# Independent Volume Signal Test - Codex

Claim/work question: `wq_volume_signal_test_tier_b_codex_independent`

## Multiple-Comparisons Family

Bonferroni family size: `8`. Threshold: `0.00625000`.

| Part | Ticker | Core | Raw p-value | Bonferroni threshold | Passes threshold |
| --- | --- | --- | ---: | ---: | --- |
| A | TCS.NS | 500d | 0.0013981422574 | 0.00625000 | True |
| A | TCS.NS | 730d | 0.5 | 0.00625000 | False |
| A | INFY.NS | 500d | 0.444088782113 | 0.00625000 | False |
| A | INFY.NS | 730d | 0.5 | 0.00625000 | False |
| B | TCS.NS | 500d | 0.146926536732 | 0.00625000 | False |
| B | TCS.NS | 730d | 0.793103448276 | 0.00625000 | False |
| B | INFY.NS | 500d | 0.0169915042479 | 0.00625000 | False |
| B | INFY.NS | 730d | 0.359820089955 | 0.00625000 | False |

## Part A Event Study

| Ticker | Core | gamma | HC3 SE finite | HC3 t | one-sided p | n | R2 |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: |
| TCS.NS | 500d | 0.28444941115 | True | 2.99320277676 | 0.0013981422574 | 1907 | 0.189248734843 |
| TCS.NS | 730d | 0.0170727590517 | False | 0 | 0.5 | 1907 | 0.185937527544 |
| INFY.NS | 500d | 0.0114835376951 | True | 0.14062949066 | 0.444088782113 | 1907 | 0.175601082989 |
| INFY.NS | 730d | 0.279240695773 | False | 0 | 0.5 | 1907 | 0.178663185271 |

## Part B Bootstrap Granger

| Ticker | Core | actual F | bootstrap p | model n |
| --- | --- | ---: | ---: | ---: |
| TCS.NS | 500d | 2.413059111 | 0.146926536732 | 22 |
| TCS.NS | 730d | 0.0737248438959 | 0.793103448276 | 26 |
| INFY.NS | 500d | 6.82426946276 | 0.0169915042479 | 22 |
| INFY.NS | 730d | 0.882590804019 | 0.359820089955 | 26 |

## Required Limitation

`^NSEI` is a broad-market control, not a sector control -- it was used because `^CNXIT` and `ITBEES.NS` failed a structural data-quality check, not because sector-level confounding was judged less relevant. This result, whatever it is, doesn't settle the sector-specific question.

## Method Notes

- TCS/INFY volume observations before `2018-09-06` were excluded from every regression.
- Part A uses four separate event-dummy regressions and four separate no-dummy residual regressions, one per ticker/core pair.
- The model-level output records whether each event-dummy HC3 standard error is finite; non-finite HC3 standard errors are left visible rather than replaced.
- Part B uses monthly mean residuals, logit-transformed EG p-values, first differences, lag 1, and a residual bootstrap under the restricted null.
- Bootstrap RNG seed: `20260712`; replicate count per test: `2000`.
