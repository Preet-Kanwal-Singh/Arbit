# Worklog — Claim 002: Healthy Episode Characterization

Maintained by Desktop Claude A (Ledger Keeper). Split out of `ledger/worklog.md`
on 2026-07-07 per Preet's decision — see `ledger/decisions.md`, 2026-07-07
entry ("Worklog split by label"). See `ledger/worklog.md` for the index
across all labels.

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
