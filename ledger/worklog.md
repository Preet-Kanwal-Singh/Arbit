# Worklog

Chronological record of completed work, provenance, outcome, and next action.
Maintained by Desktop Claude A (Ledger Keeper).

---

## 2026-07-04 — Cointegration window-length validation (Tier B, confirmed by Preet)

### Sequence of events (from `.git/logs/HEAD`, times converted to UTC)

| Time (UTC) | Event |
|---|---|
| 17:23:05 | Commit `606cc817c1de5fda7b57dc5814239e36592cc70e` — "Tier B: Cointegration window validation baseline" — on branch `antigravity/tier-b-cointegration-window-validation` |
| 17:26:17 | Checkout to new branch `codex/freeze-tcs-infy-v1`, same commit (`606cc817...`) |
| ~17:05:14 | (Out of order vs. above — see note) Antigravity/Opus's analysis provenance timestamp |
| 17:28:14 | Frozen snapshot `tcs_infy_v1_2026-07-04` created (by Codex, per its metadata.json) |
| 17:30:14 | Codex's analysis run completes; provenance cites git_commit `606cc817...` |
| 17:33:20 | Commit `a82ed569995207fbad37a287f0a8b3182d26d146` — "Added Freezed csv" (this is the commit that actually adds the snapshot files to git) |
| 17:51:22 | Commit `8eaf601671806e8153cd1446aeb67afedd746def` — "Project Restructure" — current tip of `codex/freeze-tcs-infy-v1` (current HEAD) |

Note on ordering: Antigravity/Opus's provenance.json timestamp (17:05:14 UTC)
predates the initial commit (17:23:05 UTC) entirely. That means Antigravity's
run did not happen after Codex's — it ran first, against data this repo's
frozen snapshot didn't exist yet. This is consistent with, and explains, the
next finding.

### Two candidate result sets exist

**Codex** — `analysis/codex/` (`run_cointegration_window_validation.py`,
`part_a_synthetic_validation.csv`, `part_b_tcs_infy_rolling_cointegration.csv`,
`summary.md`, `provenance.json`)
- Cites snapshot `tcs_infy_v1_2026-07-04`, snapshot sha256
  `7f2b69cc3c2030bb10c6e7a6f9a727743bff8d7003f7db2f36fa3661bbd60959`, git commit
  `606cc817c1de5fda7b57dc5814239e36592cc70e`.
- The commit exists in this repo's history — confirmed via `.git/logs/HEAD`
  and `.git/refs/heads/codex/freeze-tcs-infy-v1` (as the branch's starting
  point) and `.git/refs/heads/antigravity/tier-b-cointegration-window-validation`.
- Problem: that commit's tree does not contain the frozen snapshot file at
  all — the snapshot was only added to git three minutes later, in commit
  `a82ed569...` ("Added Freezed csv"). The script's `git_commit()` helper
  correctly reported whatever HEAD was at the moment it ran, but HEAD at that
  moment does not correspond to a git state that actually contains the data
  file the analysis claims to have used. Checking out `606cc817...` will not
  reproduce the input data. I could not do a full historical diff (no git
  command tool available to me, filesystem-read only), so I'm reporting what
  the reflog/refs show, not a verified content-match.
- The script path recorded in `provenance.json`
  (`...\Arbit\analysis\run_cointegration_window_validation.py`) no longer
  exists there — the file is currently at
  `...\Arbit\analysis\codex\run_cointegration_window_validation.py`. Current
  HEAD (`8eaf6016...`, "Project Restructure") is two commits ahead of what
  Codex's provenance cites, and that restructure commit is what moved the file.
- I did not recompute the sha256 hashes myself. The filesystem MCP tools have
  no hashing function, and manually re-transcribing the 2099-row snapshot CSV
  through chat to hash it separately was judged too error-prone to trust — a
  single transcription slip would produce a false mismatch. Reporting this as
  an open gap, not a pass.

**Antigravity/Opus** — `analysis/antigravity_opus/` (same file set)
- `provenance.json`: `"git_commit": "unavailable"`, `"data_source": "yfinance
  adjusted close, TCS.NS and INFY.NS, 2018-01-01 through 2026-06-30"`,
  `"snapshot_id": "none_live_yfinance_fetch_2018-01-01_2026-06-30"`.
- This candidate did not use the frozen snapshot at all — it pulled live from
  yfinance. It also has no git commit to check.
- Script path recorded (`...\Arbit\analysis_opus\run_cointegration_window_validation.py`)
  does not exist anywhere in this repo. The actual file is at
  `...\Arbit\analysis\antigravity_opus\run_cointegration_window_validation.py`.

**No Spec Block found anywhere.** No `VERIFIED_FACTS.md` or Spec Block existed
in the repo before this session. No claim_id traces to a Spec Block, no
pre-declared tolerance anywhere.

`analysis/claim_001_window_validation/` exists but is empty.

### The two candidates also disagree on substance

Both, at p < 0.05:
- **500-day window, near-unit-root regime, Engle-Granger false-negative rate:**
  Codex's summary cites 0.940; Opus's table reports 0.880 (high noise) / 0.870
  (low noise) for the same nominal cell. See the Part A follow-up below for
  the actual cause.
- **500-day window, first "borderline" Engle-Granger reading in the real
  TCS/INFY series:** Codex dates this 2022-01-31; Opus dates this 2020-08-31 —
  about 17 months apart. See the Part B follow-up below — this turned out to
  be a definitional difference, not a real disagreement.
- **Headline early-warning lead time ahead of the first quarterly FLAGGED
  label (2022-07-01):** Codex's summary states the earliest pre-label
  deterioration signal is "about 6 months earlier" (2022-01-31). Opus's
  summary states the 500-day window turns borderline "approximately 22 months
  before" the same label (2020-08-31).

Both candidates independently reach the same qualitative headline — no single
tested window (60/120/250/500/730 days) keeps both false-positive and
false-negative rates under 10% across all simulated persistence regimes at
p < 0.05. Noting that agreement descriptively, not as a verified finding.

### Data-quality observation, unrelated to the above

Reading the frozen snapshot file directly
(`data/snapshots/tcs_infy_v1_2026-07-04/adjusted_close.csv`), several
consecutive rows have byte-identical prices for both tickers across different
dates — e.g. 2026-04-30 and 2026-05-01, and 2026-05-27 and 2026-05-28. Pattern
is consistent with a holiday/weekend forward-fill or stale-price artifact in
the yfinance pull. Not investigated further — recording the observation, not
a diagnosis.

### Status

Nothing from this work has been written to `VERIFIED_FACTS.md`, and — per the
tier decision below — nothing needs to be. `VERIFIED_FACTS.md` does not exist
anywhere in the repo, flagged separately to Preet rather than created
unprompted.

### Update, same session — tier resolved; disagreement checked against actual code

**Tier: confirmed Tier B by Preet.** Stated reasoning: the goal was an
exploratory hit-and-trial pass over candidate window lengths, not a
decision-gating claim; Codex and Antigravity were run in parallel specifically
so there'd be a way to cross-check one against the other, not to produce a
formal Tier A independent-reproduction admission. Recorded in `decisions.md`.

Because it's Tier B, base context §4 applies directly: no Spec Block, no
pre-declared tolerance, no adversary review, and no `VERIFIED_FACTS.md` entry
were ever required here. The items below are data-hygiene notes about the two
working numbers, not process blockers.

**Part B timeline disagreement — Preet's explanation checked against the
actual code, and it holds.** Codex's script defines `borderline` as
single-month Engle-Granger p in `[0.05, 0.10)` OR ADF p in `[0.05, 0.10)` —
i.e., a mild instance of *already failing* (p ≥ 0.05). Antigravity/Opus's
script defines `first_border` as single-month EG p `> 0.03` with no upper
bound — a genuinely earlier signal that fires while the test is still
formally passing (p < 0.05). Different, explicitly different-threshold
milestones, not the same measurement computed two ways.

Corroborating evidence: the one milestone both scripts define identically —
"first month both tests fail" (`EG p ≥ 0.05 AND ADF p ≥ 0.05` in both) —
lands on nearly the same real date in both candidates: Codex 2023-12-29,
Opus 2023-12-31, two days apart. Where the definitions actually match, the
answers converge. Good support for treating the "6 months vs. 22 months"
headline gap as definitional rather than a real disagreement.

**Part A FNR disagreement — the milestone explanation does not apply here,
and this one is still open.** Part A has no milestones — it's a direct
Engle-Granger false-negative rate at p < 0.05 under a synthetic
data-generating process, meant to be the same experiment in both scripts.
Real implementation differences found in the code: trend-innovation std 0.012
(Codex) vs 0.01 (Opus); true beta 1.15 (Codex) vs 1.0 (Opus); Codex adds a
small extra idiosyncratic noise term to `x` that Opus's version does not.
Codex tests three spread-noise levels (0.005 / 0.02 / 0.05); Opus tests only
two (0.005 / 0.02).

Even at the one spread-sigma level both scripts label the same way (0.005),
at window = 500, phi ≈ 0.99, alpha = 0.05: Codex's
`part_a_synthetic_validation.csv` shows FNR = 0.94; Opus's shows FNR = 0.87.
Same nominal cell, a real 7-point gap, because the underlying synthetic data
isn't generated the same way — not a labeling issue. Not resolved by the
Part B explanation above; recording as still open.

### Next action (Preet's call, not mine)
1. ~~Decide tier~~ — done, Tier B confirmed.
2. Antigravity's run still used a live yfinance pull instead of the frozen
   snapshot, and Codex's provenance still cites a commit whose tree doesn't
   contain the snapshot file. Neither blocks anything now that this is
   Tier B, but both reduce how much weight either number should be given if
   reused later.
3. If this window-length comparison continues, worth deciding whether to
   standardize the two scripts' synthetic DGP parameters (trend sigma, true
   beta, the extra x-noise term, the spread-sigma grid) — see
   `open_questions.md` #13.

### Correction, same session

An earlier attempt to write this file (and `open_questions.md` and
`decisions.md`) used the wrong tool — a sandboxed-container file tool that
does not reach this repo at all — rather than the filesystem MCP server's
`write_file`/`edit_file` tools. That earlier attempt reported success but
never touched this repo; the `ledger/` folder was genuinely empty when Preet
checked, correctly. This file is the first version that has actually been
written here, confirmed by reading it back after writing.

---

## 2026-07-05 — Claim 002: Healthy Episode Characterization — NOT ADMITTED

Inputs reviewed: `analysis/claim_002_healthy_episode_characterization/codex/`
(implementation by Codex; per `AGENTS.md` and `.agents/AGENTS.md`, Gemini 3.1
Pro running under Antigravity may have executed this exact script without
methodology changes — that role is documented for Tier B "bulk engineering"
work specifically, and I could not confirm from the files whether it was
Codex or Gemini that actually produced this run) and
`analysis/claim_002_healthy_episode_characterization/opus/` (independent
implementation by Antigravity/Opus).

### Two blockers, independent of the comparison below

**No Spec Block exists.** Same as Claim 001. Checked this file and the rest
of the repo — no Spec Block, no pre-declared tolerance, for Claim 002.
Nothing can be admitted to `VERIFIED_FACTS.md` this round on that basis alone.

**Tier is ambiguous, same pattern as Claim 001.** `analysis/.../opus/evaluate_claim_002.py`
has this in its own docstring: `"Antigravity/Opus -- Tier B"`. Preet's request
for this review invoked the full Tier A checklist (provenance, snapshot
consistency, commit references, `VERIFIED_FACTS.md` admission). Not resolving
this myself — flagged to Preet.

### Provenance, snapshot, and commit — checked directly, not from the summaries

- Both `codex/provenance.json` and `opus/opus_provenance.json` cite the same
  snapshot_id (`tcs_infy_v1_2026-07-04`) — an improvement over Claim 001,
  where the two candidates used different data entirely. Codex's provenance
  includes the snapshot's own sha256; Opus's provenance does not (only hashes
  its own output file) — a minor asymmetry, not a conflict.
- Both cite the same git commit, `8452b6849ee79050d213ebfc5de84b3e127fd4ef`.
  Confirmed this commit exists via `.git/logs/HEAD`: "Claim 002: initial
  Episode 1 characterization implementation", made 2026-07-05T05:55:57Z on
  branch `codex/claim-002-healthy-episode-characterization`.
- Same recurring gap as Claim 001: both provenance timestamps (Codex
  2026-07-05T12:35:58Z, Opus 2026-07-05T13:01:31Z) are hours after that
  commit, and the branch was checked out again in between. The commit each
  file cites is HEAD at the moment the script ran, not necessarily the
  commit whose tree contains the exact file bytes I'm reading. A later
  commit, `53241c123de12deacad3dbf6a67ef4aba2fe3951` ("Claim 2 opus critical
  analysis", 2026-07-05T13:11:55Z), is current HEAD and was made after both
  runs — the current file states are more likely captured there than under
  the commit either file self-reports. No git diff/show tool available to
  confirm either way. Second instance of the same pattern (provenance stamps
  pre-commit HEAD, not the commit that actually contains the artifact) —
  worth fixing upstream rather than re-flagging per claim. See
  open_questions.md #14.
- Did not recompute any sha256 myself, same tooling limitation as before.
  Instead, for the numeric findings below: opened both candidates' raw CSV
  outputs and cross-checked specific numbers against each other directly,
  rather than relying on either summary.md's prose.

### Q1 — Healthy core boundaries: exact match, confirmed from both raw files

Codex's `episode_boundary_candidates.csv` and Opus's `opus_rolling_metrics.csv`
(read directly, not from summaries) agree exactly:
- 500d strict: 2020-01-31 to 2021-12-31, 24 month-ends, both files.
- 730d strict: 2020-12-31 to 2023-03-31, 28 month-ends, both files.

Opus's own beta/EG-p/ADF-p/half-life values match Codex's to ~13-15
significant figures on shared dates (e.g. 2022-01-31 EG p-value: Codex
`0.054798650332854186`, Opus `0.054798650332854186` — identical; other rows
agree to floating-point noise in the last couple of digits). Consistent with
two genuinely separate implementations of the same computation on the same
data, not one copying the other.

As Opus's own summary points out, and this checks out: this level of match is
expected here, because the healthy-core boundary is a mechanical consequence
of (same snapshot + same test calls + same p<0.05 threshold), not a judgment
call. The agreement is real and worth having confirmed, but it mainly
confirms neither implementation has a bug in reading the snapshot or calling
`coint`/`adfuller` — it wouldn't have caught a genuine methodology
disagreement the way Q4 below does.

**Ready for admission?** On the numbers alone, about as clean as agreement
gets. Still no — blocked by the missing Spec Block regardless of match
quality; not a judgment call being made about the numbers themselves.

### Q2 — Beta dynamics: qualitative pattern well supported; not a continuous drift

Both describe the same shape: beta starts high (~0.9-1.0) and volatile in the
first several months of the 500d core, then drops to a lower (~0.6-0.7),
tighter range that persists. Opus adds formal tests Codex's summary doesn't
report: a Mann-Kendall test over the full core shows no persistent monotonic
trend (tau = -0.072, p = 0.637), and a Welch t-test comparing the first 6
months against the remaining 18 (the exact boundary Codex's own split-test
below lands on) is significant (t = 11.9, p = 0.008). Opus's own reframing —
a step-change / level-shift, not a continuous adjustment — is a real
refinement of Codex's wording ("largest movement occurs early"), not a
contradiction of it.

Qualitatively: well supported by both. Still not admissible — same Spec Block
gap.

### Q3 — Degradation ordering (EG before half-life before ADF): independently re-checked against Codex's raw numbers, holds up

Codex's summary is qualitative here ("final two month-ends have EG near 0.05
while ADF and half-life stay healthy"). Opus's summary gives a specific dated
sequence. Rather than take Opus's dates on faith, looked them up directly in
Codex's own `rolling_metrics.csv` (window_length=500):

| Opus's claim | Codex's raw row (500d) | Match? |
|---|---|---|
| First EG p > 0.01 within core: 2020-07-31, p=0.012 | 2020-07-31: engle_granger_p_value=0.01241682... | Yes |
| First EG failure (p>=0.05) post-core: 2022-01-31, p=0.055 | 2022-01-31: engle_granger_p_value=0.05479865... | Yes |
| First half-life > 20d: 2023-04-30, hl=29.1d | 2023-04-28: half_life=29.0697... (prior row 2023-03-31: 19.044, so the crossing is real) | Yes (date off by 2 days — Codex's month-end convention) |
| First ADF failure: 2023-12-31, p=0.129 | 2023-12-29: adf_p_value=0.12880455... (prior row 2023-11-30: 0.0258) | Yes (same 2-day convention gap) |

All four checked out against Codex's own numbers, not just Opus's report of
them. The ordering (EG weakens, then half-life rises, then ADF fails, with
months-long gaps between each) is well supported and independently
re-verifiable from data both sides produced. Still not admissible — same Spec
Block gap, but this is the strongest-evidenced of the five questions.

### Q4 — Internal sub-regimes: genuinely DISPUTED, not just a tolerance question

The one place a real, substantive disagreement shows up, and it would still
be disputed even with a tolerance, because it's a disagreement about whether
an effect is statistically real, not about a numeric margin. Read both
`subregime_tests.csv` (Codex) and the `optimal_split_test` function in
`evaluate_claim_002.py` (Opus) directly:

- Both use the identical algorithm and permutation convention: best-split RSS
  improvement search, 2000 permutations, p = (count_ge + 1) / (n_perm + 1),
  seed 42. Confirmed by reading both implementations, not assuming.
- Codex's search uses 6 variables (beta, half_life, spread_std,
  spread_daily_change_std, and transformed EG/ADF "strength" terms) and finds
  a highly significant split in the 500d core at 2020-06-30 (RSS improvement
  0.388, p = 0.0004997...).
- Opus's own independent blind search uses 4 variables (beta, half_life, raw
  eg_pval, spread_std) and does not find the 500d split significant (best
  split lands earlier, at 2020-03-31, p = 0.108). Opus's own search does find
  the 730d core's split significant (2021-02-28, p = 0.011).
- Separately, Opus ran a Welch t-test at Codex's specific 2020-06-30 boundary
  (not from Opus's own blind search) and found it significant (p = 0.008).
  That's a different, narrower question — is the level difference at Codex's
  chosen boundary real — than does an unconstrained independent search find
  and confirm the same boundary as significant, which is the harder bar and
  the one that actually fails for the 500d case.

So: qualitative pattern (an early segment differs from a later one) —
supported. Statistical significance of a blindly-detected 500d sub-regime via
an independent search — disputed, traced to a specific, identified cause
(variable set: 6 transformed variables vs. 4 raw ones), not vague
methodology hand-waving. Recording this as DISPUTED, not VERIFIED. Would need
the variable set standardized and re-run under a real Spec Block before it
could be admitted either way. The 730d split fares better — both would need
to independently confirm 730d specifically before that half of the claim
could even be considered.

### Q5 — Opus's "split-signal period" (EG failure precedes ADF failure by ~23 months): numbers hold up, but it's not a jointly-discovered finding

The two dates behind this (EG fails 2022-01-31 at p=0.055; ADF doesn't fail
until 2023-12-29 at p=0.129) are the same two rows already verified
independently in Q3, directly from Codex's raw data. The underlying numbers
are solid on both sides.

But Codex's own summary doesn't name or flag this ~23-month gap as a distinct
phenomenon — Codex's degradation discussion stops at the shorter "borderline
shoulder" through 2023-01-31 and doesn't extend the observation that far, or
give it this framing. So this isn't a case of two independent tools
discovering the same thing and describing it differently (like Q2's
level-shift framing) — it's Opus noticing something in data that's
consistent with Codex's own numbers, which Codex did not itself flag. The
numbers are trustworthy; the characterization as a named, operationally
relevant phenomenon has only one source. That's short of what should count as
an admitted joint finding, Spec Block or not. Recommend: open question, put
to Codex directly ("do you agree this gap is real and worth naming") rather
than a ledger entry either way. See open_questions.md #18.

### Status: NOT ADMITTED

Nothing from Claim 002 goes to `VERIFIED_FACTS.md` this round. Q1-Q3 are
well-supported by both implementations and independently re-checked against
raw data on both sides; Q4 is genuinely disputed on the merits, not just
unresolved on process; Q5 is a well-evidenced lead from one source. All of it
is blocked from admission by the missing Spec Block regardless of merit —
per instructions, no tolerance gets picked just because the numbers look
good.

### Next action (Preet's call, not mine)
1. Is Claim 002 Tier A or Tier B? (See open_questions.md #15.)
2. If Tier A: Desktop Claude B needs to write a Spec Block with a
   pre-declared tolerance before any of Q1-Q3 can be formally admitted.
3. Q4 needs the variable-set discrepancy resolved (or explicitly accepted as
   implementation-sensitive) before the sub-regime claim is usable for
   anything decision-relevant.
4. Q5 needs Codex's own confirmation before it's treated as more than an
   Opus-only observation.
5. Consider fixing provenance stamping so it captures the commit after
   outputs are committed, not HEAD at runtime before the commit — a repeated
   pattern across two claims now.

---

## 2026-07-06 — Claim 003: EG/Half-Life Ordering Robustness — PARTIALLY DISPUTED, spec gap found, NOT ADMITTED

Inputs: `analysis/claim003/codex/` and `analysis/claim003/antigravity_opus/`, per
Spec Block v6 (`claim_003_eg_halflife_ordering_robustness`), governance: Tier A,
passed adversarial review (Claude C), approved for execution. This is the
first claim reviewed against an actual pre-declared Spec Block — Claims 001
and 002 had none.

Note: the repo folder is named `analysis/claim003/`, not
`analysis/claim_003_eg_halflife_ordering_robustness/` (the actual claim_id).
Minor, but worth fixing for consistency with claim_001/002's naming.

### Provenance, snapshot, commit — checked directly

- Both provenance.json files cite the same snapshot_id
  (`tcs_infy_v1_2026-07-04`) and the same git commit
  (`dcd5f465aff03bbcf448a8e845767d364cfae098`). Confirmed this commit exists
  via `.git/logs/HEAD` ("Claim 002 Ledger update", 2026-07-05T18:13:34Z).
- Same recurring pattern as Claims 001/002, but this time Codex's own
  provenance is transparent about it: `git_status_short_at_run` literally
  records `"?? analysis/claim003/"` at the moment of the run — Codex's own
  outputs were untracked when it stamped that commit hash. A later commit,
  `c3e49d184fd05a4be3fe63421c2b2c80cf6402ca` ("Claim 003 implementation by
  codex and opus", 2026-07-06T11:43:16Z, made after both runs), is current
  HEAD and is what actually contains these files. Third occurrence of this
  exact pattern — worth Codex/Antigravity fixing the stamping order upstream
  rather than me re-flagging a fourth time.
- Same `git_status_short_at_run` also shows `M PROJECT_BASE_CONTEXT.md` and
  `M ledger/decisions.md` as uncommitted at that moment — consistent with my
  own decisions.md edit from earlier in this session (the GLM policy entry)
  and someone's edit to `PROJECT_BASE_CONTEXT.md` §3 adding the GLM exception
  language. I re-read `PROJECT_BASE_CONTEXT.md` just now: §3 has in fact been
  updated with "Exception logged 2026-07-06: qualitative/directional
  findings... may be disclosed to GLM... See decisions.md, 2026-07-06." That
  resolves the Spec Block's own caveat ("not yet reflected in
  PROJECT_BASE_CONTEXT.md §3 itself") — it has been, as of this session. I
  cannot confirm from here whether that edit and my decisions.md edit are
  themselves committed yet (no git status/diff tool available to me).
- Did not recompute sha256 hashes myself, same tooling limitation as before.
- Confirmed by reading both scripts directly: Codex's provenance flags a
  methodology judgment call ("the residual spread ... is intercept-inclusive
  OLS residual ... the spec's beta-only formula is treated as shorthand") —
  I checked Opus's `claim_003.py` and it makes the identical choice
  (`spread = log_tcs_arr - alpha - beta_val * log_infy_arr`, intercept
  included). Both implementations resolved the spec's shorthand the same way,
  independently. Not a source of the disagreement found below.

### Cell-by-cell cross-implementation check (spec's exact rule: |ΔP̂| ≤ 0.05 AND identical classification, or DISPUTED)

| Window | Config | Codex P̂ | Opus P̂ | |Δ| | ≤0.05? | Codex class | Opus class | Match? |
|---|---|---|---|---|---|---|---|---|
| 500 | C1 | 0.9946 | 0.9947 | 0.0001 | Y | ROBUST-UNSTABLE | ROBUST-UNSTABLE | Y |
| 500 | C2 | 1.0000 | 0.9978 | 0.0022 | Y | ROBUST-UNSTABLE | ROBUST-UNSTABLE | Y |
| 500 | C3 | 0.9656 | 0.9588 | 0.0068 | Y | ROBUST-UNSTABLE | ROBUST-UNSTABLE | Y |
| 500 | C4 | 0.7578 | 0.7347 | 0.0231 | Y | ROBUST-UNSTABLE | ROBUST-UNSTABLE | Y |
| 500 | C5 | 0.9991 | 1.0000 | 0.0009 | Y | ROBUST-UNSTABLE | ROBUST-UNSTABLE | Y |
| 730 | C1 | 0.2744 | 0.2972 | 0.0228 | Y | CONTRADICTED | CONTRADICTED | Y |
| 730 | **C2** | **0.7842** | **0.8533** | **0.0691** | **N** | ROBUST | ROBUST | **DISPUTED** |
| 730 | C3 | 0.0784 | 0.0883 | 0.0099 | Y | CONTRADICTED | CONTRADICTED | Y |
| 730 | C4 | 0.0154 | 0.0220 | 0.0066 | Y | CONTRADICTED | CONTRADICTED | Y |
| 730 | C5 | 0.9765 | 0.9766 | 0.0001 | Y | ROBUST | ROBUST | Y |

All five 500d cells pass cleanly — both value and classification agree, with
real (if small) numeric differences consistent with genuinely separate Monte
Carlo runs sharing seed=42 but not identical resampling order, not copied
numbers. One 730d cell, C2, has matching classification labels (both say
ROBUST) but the P̂ values differ by 0.0691, which exceeds the spec's 0.05
tolerance. Per the spec's literal rule ("Mismatch on either [condition] →
DISPUTED for that cell"), this is DISPUTED even though the classification
agrees — the spec requires both conditions, and I'm applying that exactly as
written, not softening it because the labels happen to match.

### The consequence of that one dispute, and a real gap in the spec I'm not resolving myself

Per the spec: "Mismatch on either → DISPUTED for that cell; **that window
length withheld from the study-level conclusion, not averaged.**" Read
literally, the C2 dispute means the entire 730d window — not just that one
cell — must be withheld from the study-level rollup, even though its other
four cells (C1, C3, C4, C5) all agree cleanly and would, on their own, support
CONTRADICTED for that window.

That leaves only the 500d window (ROBUST, flagged PARAMETER-UNSTABLE) as
usable input to the study-level decision tree. But the tree as written has
three branches: (1) CONTRADICTED if either window is CONTRADICTED, (2) else
ROBUST if both windows are ROBUST, (3) else INCONCLUSIVE-family, whose stated
precondition is "at least one window length is INCONCLUSIVE." None of these
cleanly fit "one window is withheld entirely, not classified INCONCLUSIVE by
its own data." Branch 1 can't fire (no CONTRADICTED window remains available
to check). Branch 2 can't honestly fire either ("both" requires a valid 730d
classification, which no longer exists for this purpose). Branch 3's own
precondition doesn't match (730d wasn't computed as INCONCLUSIVE by either
implementation — it was computed as CONTRADICTED by both; only one of its
five cells is in cross-implementation dispute).

I'm not picking a resolution here — this is the same category of problem as a
missing tolerance: the spec doesn't define what happens in the situation that
actually arose, so I'm sending it back rather than inventing the missing
branch myself. Notably, both Codex's and Opus's own self-reported
`study_status` fields say CONTRADICTED — but that's each tool applying the
tree to its own single set of numbers, before any cross-implementation check.
I'm not treating that agreement as sufficient; it's exactly the kind of
surface-level agreement the cross-implementation cell check exists to test
underneath, and the cell check found a real gap at 730d/C2.

### A substantive concern about the 500d result itself, not just process

Even setting the 730d question aside, the 500d ROBUST classification comes
with a flag worth taking seriously rather than treating as a checkbox: both
implementations independently estimate `phi_post`'s 95% CI upper bound at
1.0043 (Codex) / same to 4 decimals (Opus) — above 1.0. Per the method notes,
half-life is `inf` for phi ≥ 1. If the true post-transition AR(1) coefficient
is at or beyond the unit-root boundary, half-life may never cross the
threshold in a meaningful share of simulated replicates, which would make
"EG-first" close to mechanically likely rather than a clean signal that EG
genuinely tends to move first in a well-behaved degrading regime. This
doesn't invalidate the 500d result, but the PARAMETER-UNSTABLE flag isn't just
a procedural footnote here — it may be doing real interpretive work.

(Separately: `phi_pre`/`phi_post` themselves match near-exactly between Codex
and Opus, 0.950351/0.988012 both sides. That's expected, not meaningfully
independent confirmation — both are point estimates from the same real
historical data, not from the stochastic simulation. The P̂ values above,
which come from the actual Monte Carlo, are the part that's a genuine
independent check, and mostly held up.)

### Status: NOT ADMITTED, nothing sent to VERIFIED_FACTS.md

500d passes cleanly at every cell. 730d has one disputed cell that, per the
spec's literal text, voids the whole window for the study-level conclusion.
The study-level tree has no defined branch for that outcome. I'm not
unilaterally scoping a partial admission (e.g. "500d only") into
`VERIFIED_FACTS.md` under this claim_id without asking first — this would be
the first-ever entry in that file, and picking my own admission granularity
when the spec's actual top-level question is still blocked feels like exactly
the kind of judgment call that isn't mine to make unilaterally.

### Next action (Preet's call, not mine)
1. Does the 730d/C2 dispute get investigated (re-check both scripts' bootstrap
   procedure for that specific cell) before anything about 730d is usable, or
   is a 0.069 gap on one cell out of ten just accepted as noise and the spec
   amended to say so explicitly?
2. How should the study-level tree handle a withheld window length? This is a
   real spec gap — worth Desktop Claude B patching v6 (or issuing v7) with an
   explicit branch, since this will recur on any multi-window Tier A claim.
3. Do you want the 500d window-level finding (ROBUST, PARAMETER-UNSTABLE)
   admitted to `VERIFIED_FACTS.md` on its own, scoped explicitly as
   "500d window only, study-level conclusion pending," or held until the
   whole claim resolves? I can do either — didn't want to default to one
   without asking, given this is the first entry that file will ever have.
4. `analysis/claim003/` folder naming vs. the actual claim_id — worth an
   editorial fix, not urgent.
