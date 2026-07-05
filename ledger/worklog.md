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
