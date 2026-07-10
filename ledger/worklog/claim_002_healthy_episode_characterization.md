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

---

## 2026-07-09 — Claim 002: Tier A Dual Reproduction (Spec Block v3) — ADMITTED

Answers item 1 above: Preet confirmed Tier A directly. Answers item 2: Desktop
Claude B wrote Spec Block v3, with a pre-declared tolerance table (checked
for arithmetic and metric-coverage completeness before use — clean). Claude
#3 reviewed and approved it (Preet recorded this directly; the spec's own
"Next step" line still read as if review were pending, which was stale
boilerplate, not a live status — confirmed with Preet before proceeding).

Inputs: `analysis/claim_002_healthy_episode_characterization/codex_tier_a/`
and `opus_tier_a/`, both already complete when I looked — Preet had not yet
pasted candidate results, but filesystem access made that unnecessary this
round.

### Provenance check — one real blocker, since fixed

Both `provenance.json` files self-report git_commit
`1717ffb3ed62e6b502d7c6ef2791545737673d89` ("Restore Claim 002
implementation script", 2026-07-06T12:14:45Z). Checked file-creation
timestamps directly: Codex's script was created 2026-07-09T09:55:06Z (matches
its own execution timestamp, 09:55:42Z); Opus's was created
2026-07-09T10:40:30Z (matches 10:41:43Z). Both three days after the cited
commit — that commit's tree cannot contain either script. Checked
`.git/logs/HEAD` for anything later: nothing. Unlike claim_001 and claim_003,
where a correct-but-uncited later commit existed by the time I looked, here
there was no commit at all covering this work — fully uncommitted working-
directory files. Flagged to Preet before doing anything else; Preet committed
both directories (`8105c13004a96737ae15d120c93f4e62ed9ead39`, "Claim 002
Tier A dual reproduction", 2026-07-09T12:54:48Z, current HEAD as of this
writing). That's the commit cited in the `VERIFIED_FACTS.md` entry below.

Same recurring gap otherwise: snapshot_id and snapshot sha256
(`tcs_infy_v1_2026-07-04`, `7f2b69cc...`) match exactly between both
provenance files. Execution timestamps are 46 minutes apart (Codex first),
consistent with the spec's required sequencing, though only a start instant
is recorded on either side, not a duration — can't formally rule out overlap,
same as every prior claim. Did not recompute either candidate's sha256 —
still no hashing tool reaches this filesystem from where I sit.

### Part-by-part comparison against Spec Block v3's pre-declared tolerance

Used a scripted comparison (not manual arithmetic) against the exact
tolerance table in the spec, to avoid the error risk of checking ~280 cells
by hand. Full breakdown:

**Part 1 (boundary identification) — exact match, all 4 bases:**

| Basis | Start | End | Count | Codex/Opus agree? |
|---|---|---|---|---|
| 500d_strict | 2020-01-31 | 2021-12-31 | 24 | Yes, and matches Fixed Input |
| 730d_strict | 2020-12-31 | 2023-03-31 | 28 | Yes, and matches Fixed Input |
| 500d_730d_consensus_strict | 2020-12-31 | 2021-12-31 | 13 | Yes |
| 500d_borderline_tolerant | 2020-01-31 | 2023-01-31 | 37 | Yes |

**Part 2 (regime characterization) — 168 cells (7 metrics × 12 stats × 2
windows), zero disputes.** Largest cross-implementation gap on any cell:
~1e-13. Expected — same fixed dates, same snapshot, same deterministic
formulas (OLS, `coint`, `adfuller`, AR(1) fit); this checks for
implementation bugs, not statistical agreement, and finds none.

**Part 3 (sub-regime test) — both cores `natural_split_supported`, zero
disputes:**

| Core | Split date (both) | RSS improvement (Codex / Opus) | Permutation p (Codex / Opus) |
|---|---|---|---|
| 500d_strict | 2020-06-30 | 0.38844203662304 / 0.38844203662303955 | 0.000499750124937531 / 0.0004997501249375312 |
| 730d_strict | 2022-08-30 | 0.392289875163584 / 0.3922898751635837 | 0.000499750124937531 / 0.0004997501249375312 |

This resolves `open_questions.md` #17. The original Q4 dispute (Codex's
6-variable search found the 500d split significant; Opus's independent
4-variable search did not, and picked a different split point) was traced
to the variable set, not a real disagreement about the data. v3 fixed the
metric list, the RNG seed (`20260705`), and the exact call order (500d then
730d permutations, one `rng` call per draw) — with those three pinned down,
a seeded RNG is fully deterministic, so two correct implementations produce
the same permutation draws, not just similar ones. That's *why* the
agreement here is to machine epsilon, not evidence on its own that isolation
was respected — noted explicitly in the `VERIFIED_FACTS.md` entry so a
future agent doesn't misread bit-identical numbers as suspicious, or as
proof of independence either way.

Also answers the second half of #17 directly: yes, Codex's search — now
re-run under the fixed variable set — agrees with Opus's original finding
that 730d's split is significant, at the same date Opus found
(implicitly, since both now report 2022-08-30 as the split — note this is a
different date from Opus's original blind 730d finding of 2021-02-28 logged
in #17; the fixed-variable-set split point moved once the variable set
changed, which is expected and not itself a new discrepancy since both
implementations now agree on the new point).

**Part 4 (degradation diagnostics) — 108 cells (6 metrics × 6 stats × 3
windows: 500d core, 730d core, shoulder), zero disputes.** Same
floating-point-noise level of agreement as Part 2, same reason.

### What this admission does and doesn't cover

All four parts cleared together, so one `VERIFIED_FACTS.md` entry covers all
of them — the staged/partial-admission mechanics the spec flagged as mine to
decide never came up, since nothing needed to be held back.

Mapping back to the original five exploratory questions:
- **Q1 (boundaries) → Part 1.** Re-confirmed under formal tolerance.
- **Q4 (sub-regime significance) → Part 3.** Resolved, see above.
- **Q2 (beta step-change), Q3 (degradation ordering by specific date), Q5
  (Opus's named EG-to-ADF gap) are NOT covered.** Parts 2 and 4 ask for
  distributional stats and trend slopes over fixed windows, not the specific
  dated events or step-change framing Q2/Q3/Q5 were about. These remain
  open on their original terms — item 4 below is unchanged.

### Outstanding, not blocking

- The spec said prior `codex/`/`opus/` (non-Tier-A) dirs get relabeled
  superseded-prior-work on completion. Not done yet — still plain
  directory names, no marker.
- Q5 (item 4 in the original next-action list) still needs Codex's own
  confirmation before it's more than a single-source observation — untouched
  by this spec.
- Provenance stamping citing pre-commit HEAD instead of a commit that
  actually contains the output happened a fourth time here, and for the
  first time manifested as *no* commit at all rather than a stale-but-
  findable one. Worth fixing upstream now rather than continuing to catch it
  per claim.

### Status: ADMITTED — see `VERIFIED_FACTS.md`, `claim_002_healthy_episode_characterization` entry, 2026-07-09.
