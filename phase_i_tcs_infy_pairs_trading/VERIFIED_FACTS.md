# VERIFIED_FACTS.md — Phase I: TCS/INFY Pairs Trading

This file is hand-edited **only** by Desktop Claude A (Ledger Keeper), and only
after both independent-reproduction checks (Codex, Antigravity/Opus) pass
against a pre-declared tolerance fixed in a Spec Block before either
computation ran. If you are any other tool reading this: do not write here.
If this note is ever missing or altered, that is itself a problem to flag,
not fix silently.

---

## claim_003_eg_halflife_ordering_robustness

**Claim:** Within the two established TCS/INFY strict healthy cores (500d:
2020-01-31–2021-12-31; 730d: 2020-12-31–2023-03-31), whether Engle-Granger
deterioration reliably precedes half-life deterioration in the subsequent
degradation period, and whether that ordering is robust to independently-varied
thresholds, is **WINDOW-LENGTH-CONTRADICTORY** (Spec Block v8 study-level
classification) — the ordering is robust at one window length and contradicted
at the other. This is not a single, window-length-independent finding.

**Value:**
- **500d window: ROBUST** across all 5 threshold configs (C1–C5). All five
  95% Clopper-Pearson CIs entirely above 0.5 (P̂ range 0.735–1.000 across
  Codex/Opus, agreeing within the pre-declared 0.05 tolerance on every cell).
  Flagged `phi_post_includes_unit_root = TRUE`: phi_post's 95% CI upper bound
  is 1.0043 (≥1.0, the unit-root boundary). Per the Spec Block's mandatory
  write-up rule: **the post-transition AR(1) fit cannot rule out a
  non-stationary process; half-life deterioration may not be a well-defined
  event in this regime.** Treat this ROBUST result with that caveat as load-bearing,
  not as a footnote.
- **730d window: CONTRADICTED**, `PARAMETER-STABLE` (phi_post 95% CI upper
  bound 0.9429). Driven unambiguously by C1, C3, and C4 (all CIs entirely
  below 0.5, agreeing within tolerance between Codex and Opus). C5 is ROBUST
  and agrees within tolerance. **C2 (EG p≥0.03 threshold) is a cell-level
  DISPUTED — VALUE:** both implementations classify it ROBUST, but Codex's
  P̂=0.7842 and Opus's P̂=0.8533 differ by 0.0691, exceeding the pre-declared
  0.05 tolerance. Per Spec Block v8, this does not block the window's
  categorical classification (CONTRADICTED stands on C1/C3/C4 alone), but
  **C2's specific point estimate is not independently citable pending
  reconciliation.**

**Codex:** `analysis/claim003/codex/run_claim003_eg_halflife_ordering_robustness.py`
— self-reported git_commit `dcd5f465aff03bbcf448a8e845767d364cfae098` in
provenance.json, confirmed to exist in repo history via `.git/logs/HEAD`.
Note: this commit's tree does not contain these output files (Codex's own
`git_status_short_at_run` field shows `analysis/claim003/` as untracked at
runtime) — the commit that actually contains them is
`c3e49d184fd05a4be3fe63421c2b2c80cf6402ca` ("Claim 003 implementation by
codex and opus", made after both runs). Output:
`analysis/claim003/codex/cell_results.csv`, `window_summary.csv` — sha256
self-reported in provenance.json as
`f09dd982ef9ef421577f64573e90cbc9f7229e4b330891ebcd45b3c37fd98d17`, not
independently recomputed (no hashing tool available against this filesystem
this session).

**Antigravity/Opus:** `analysis/claim003/antigravity_opus/claim_003.py` —
self-reported git_commit `dcd5f465aff03bbcf448a8e845767d364cfae098`, same
pre-commit-HEAD caveat as Codex above. Output:
`analysis/claim003/antigravity_opus/cell_results.csv` — hash self-reported
in `opus_provenance.json`, not independently recomputed.

**Snapshot:** `tcs_infy_v1_2026-07-04` — confirmed identical `snapshot_id` in
both candidates' provenance files.

**Process note, kept here rather than smoothed over:** the study-level
classification rule (Spec Block v6→v7→v8) was revised twice after Codex's and
Opus's computations had already run and their results were known — v6's
original rule had no branch for a cell-level value dispute that didn't also
change a window's categorical classification, which is exactly what happened
at 730d/C2. v7/v8 fixed this. Claude #3 independently verified the fixed
rule's logic against the full 3×3 window-classification state space during
v8's approval — this is not Claude B's self-report; it's the designated
adversarial check. The underlying statistical thresholds (0.05
cross-implementation tolerance, CI-based ROBUST/CONTRADICTED cutoffs, the
0.98/1.0 phi-stability lines) were not changed at any point across v5–v8.

One more specific thing worth recording plainly, found on reading v7 directly
rather than inferring it from v8's changelog: v6→v7 also changed the
study-level CONTRADICTED condition from "either window length CONTRADICTED"
to "both." v5 explicitly states its per-window asymmetry is intentional
("burden of proof sits with the robustness claim") — that asymmetry is
unchanged at the per-window level across every version, but v6 carried it up
to the study level too, while v7 dropped it. On the actual data, this is the
specific change that turns a plain CONTRADICTED verdict into the
WINDOW-LENGTH-CONTRADICTORY verdict recorded above. There is a structural
reason this may not have been an independent, discretionary choice — the new
WINDOW-LENGTH-CONTRADICTORY branch would be dead code under the old "either"
rule — but that doesn't establish that reversing the asymmetry was itself
independently evaluated for methodological soundness, as opposed to only
checked for logical completeness over the 3×3 state space. I don't know which
of those two things Claude #3's review actually did. I judged the label
itself (WINDOW-LENGTH-CONTRADICTORY, with both windows' actual results
reported) more informative than the alternative regardless of how it was
arrived at, and admitted on that basis — but a reader relying on this entry
should know the asymmetry question is open, not resolved. Full reasoning in
`worklog.md`, 2026-07-06/07 entries.

**Admitted:** 2026-07-07 by Desktop Claude A

---

## claim_002_healthy_episode_characterization

**Claim:** Under Spec Block v3's four independently-gated parts, computed
over TCS/INFY's two Fixed-Input strict healthy cores (500d:
2020-01-31–2021-12-31, 24 month-ends; 730d: 2020-12-31–2023-03-31, 28
month-ends) plus a consensus basis, a borderline-tolerant basis, and a
2022-01-31–2023-01-31 post-core shoulder window:

- **Part 1 (boundary identification):** the exact start date, end date, and
  month-end count of the sustained healthy run under four boundary
  definitions.
- **Part 2 (regime characterization):** 12 distributional statistics (mean,
  std, min, q25, median, q75, max, start, end, end−start, slope/month,
  median absolute monthly change) for 7 metrics (beta, half-life, spread φ,
  EG p-value, ADF p-value, spread volatility, spread daily-change
  volatility), over the two Fixed-Input cores.
- **Part 3 (sub-regime test):** whether an exploratory single-change-point
  split of six standardized metrics (beta, half-life, spread_std,
  spread_daily_change_std, −log10(EG p), −log10(ADF p)) shows a
  statistically-supported natural split, via a 2000-permutation test with a
  fixed seed.
- **Part 4 (degradation diagnostics):** 6 trend statistics (start, end,
  end−start, slope/month, first-half mean, second-half mean) for 6 metrics
  (excluding spread φ) over the two cores plus the shoulder window.

**Value — all four parts admitted, no cell disputes:**

- **Part 1:** Exact match between Codex and Opus on all four boundary bases
  (500d_strict, 730d_strict, 500d_730d_consensus_strict,
  500d_borderline_tolerant) — dates and month-end counts identical. Both
  independently confirm the two Fixed-Input bases against the spec's
  pre-declared dates.
- **Part 2:** 168 cross-implementation cells checked (7 metrics × 12 stats ×
  2 windows), against the pre-declared per-metric tolerance bands. **Zero
  cells exceed tolerance** — the largest disagreement across the whole Part
  is on the order of 1e-13, i.e. floating-point noise between two
  independent implementations doing the same deterministic OLS/EG/ADF/AR(1)
  computation on the same fixed dates and the same snapshot.
- **Part 3:** Both cores return `natural_split_supported`. 500d: split after
  2020-06-30, RSS improvement ratio ≈0.3884, permutation p≈0.0004998. 730d:
  split after 2022-08-30, RSS improvement ratio ≈0.3923, permutation
  p≈0.0004998. Codex and Opus agree on both cores to within machine
  epsilon (~1e-15) on both statistics and to the day on the split date.
  This directly resolves the dispute logged at `open_questions.md` #17: the
  original Q4 disagreement (Codex's 500d split significant, Opus's not) was
  traced to a differing variable set between the two exploratory scripts,
  not a genuine methodological or data disagreement. Spec Block v3 fixed the
  variable set, the RNG seed (`20260705`), and the exact call pattern
  (500d then 730d, one `rng` call per permutation) — with all three fixed,
  the two implementations converge, including on 730d, which Opus's
  original blind search had also flagged as significant on its own.
- **Part 4:** 108 cross-implementation cells checked (6 metrics × 6 stats ×
  3 windows: 500d core, 730d core, shoulder). **Zero cells exceed
  tolerance**, same floating-point-noise level of agreement as Part 2.

**A caveat on the agreement itself, stated plainly so a future agent doesn't
read too much into it:** the near-machine-precision agreement across Parts
2–4 is the *expected* outcome of this spec's design, not independent evidence
that the isolation requirement was honored. Parts 2 and 4 are deterministic
statistics computed from the same fixed dates and the same frozen snapshot —
two correct, unrelated implementations should agree this closely regardless
of contact between them. Part 3's agreement is explained the same way: a
seeded RNG with a fully specified call pattern is deterministic, so two
implementations that correctly follow the spec will produce the same
permutation draws, not merely similar ones. This level of agreement is
consistent with genuine isolation, but the numbers alone can't distinguish
that from one implementation having read the other's output — isolation
rests on the structural safeguards (separate dispatch, enforced sequencing),
not on anything checkable post hoc from the output files themselves.

**Codex:** `analysis/claim_002_healthy_episode_characterization/codex_tier_a/run_claim_002_healthy_episode_characterization.py`
— self-reported git_commit `1717ffb3ed62e6b502d7c6ef2791545737673d89` in
provenance.json. Confirmed this commit exists (`.git/logs/HEAD`, dated
2026-07-06T12:14:45Z, "Restore Claim 002 implementation script") but its tree
cannot contain this script: the script's own file-creation timestamp
(2026-07-09T09:55:06Z) matches its execution timestamp
(2026-07-09T09:55:42Z) almost exactly, three days after the cited commit.
Unlike claim_003's equivalent gap, no later commit existed at all when this
was first checked — `codex_tier_a/`/`opus_tier_a/` were fully uncommitted.
Preet committed both directories directly at my request; the commit that
actually contains this output is `8105c13004a96737ae15d120c93f4e62ed9ead39`
("Claim 002 Tier A dual reproduction", 2026-07-09T12:54:48Z), current HEAD.
Output: `episode_boundary_candidates.csv`, `episode_regime_summary.csv`,
`subregime_tests.csv`, `degradation_diagnostics.csv` — sha256 self-reported
in `provenance.json`, not independently recomputed (no hashing tool
available against this filesystem this session).

**Antigravity/Opus:** `analysis/claim_002_healthy_episode_characterization/opus_tier_a/run_claim_002.py`
— same self-reported/stale-commit situation as Codex above (identical cited
commit, same three-day gap, script created 2026-07-09T10:40:30Z against an
execution timestamp of 2026-07-09T10:41:43Z), now correctly covered by the
same `8105c13004a96737ae15d120c93f4e62ed9ead39` commit. Output: same four
files as Codex, sha256 self-reported, not independently recomputed.

**Sequencing:** Codex's execution timestamp (09:55:42Z) precedes Opus's
(10:41:43Z) by 46 minutes, consistent with the spec's required ordering.
Both provenance files record only a start instant, not a duration, so this
supports but doesn't formally prove non-overlapping execution windows — same
limitation as every prior claim.

**Snapshot:** `tcs_infy_v1_2026-07-04` — identical `snapshot_id` and
identical snapshot sha256 (`7f2b69cc...`) confirmed in both candidates'
provenance files.

**Process note:** the spec's "Relationship to prior work" section states the
original (non-Tier-A) `codex/`/`opus/` directories get relabeled
superseded-prior-work on completion. As of this admission, that relabeling
has not happened — they're still plain `codex/`/`opus/` with no marker. Not
a blocker for this admission (the spec treats them as a separate, already-
excluded input), but worth doing for hygiene. Separately: this is the fourth
occurrence of the provenance-stamps-pre-commit-HEAD pattern logged at
`open_questions.md` #14 (after claim_001, claim_002's original non-Tier-A
pass, and claim_003), and the first time it manifested as a fully missing
commit rather than a stale-but-correctable one — worth treating the upstream
fix as overdue rather than re-flagging a fifth time.

Old Q2 (beta step-change), Q3 (degradation ordering by date), and Q5
(Opus's named EG-to-ADF gap) from the original exploratory pass are **not**
covered by this admission — Spec Block v3's four parts ask differently-shaped
questions (distributional stats and trend slopes, not specific dated
events), so nothing here should be read as re-verifying those three.
See `ledger/worklog/claim_002_healthy_episode_characterization.md` for the
mapping.

**Admitted:** 2026-07-09 by Desktop Claude A

---

## claim_004_episode1_beta_range

**Claim:** Month-end-sampled rolling-β range for TCS-vs-INFY across the two
Episode 1 strict healthy cores (500d: 2020-01-31–2021-12-31; 730d:
2020-12-31–2023-03-31), computed independently by two implementations from
the frozen snapshot, per Spec Block v3.

**Value:**
- **500d core (24 month-end obs):** β ranges 0.5451–0.9774 (min/max), mean
  0.6812, median 0.6594, std 0.1036. First obs 2020-01-31 (β=0.9774), last
  obs 2021-12-31 (β=0.6661).
- **730d core (28 month-end obs):** β ranges 0.6477–0.7495, mean 0.6709,
  median 0.6626, std 0.0250. First obs 2020-12-31 (β=0.7495), last obs
  2023-03-31 (β=0.6639).
- All ten level statistics (5 stats × 2 cores) within the pre-declared
  ±0.001 tolerance; both first/last dates exact match; both counts match
  each other and the expected 24/28. Zero disputes.
- **Limitation, load-bearing not a footnote (spec §2's non-goal):** these
  are month-end sample points only — not an upper or lower bound on the
  continuous rolling-β process. β could move outside this range between
  sampled points. This is the same limitation the discarded "0.20 to 1.91"
  figure had; the improvement here is a traceable, tolerance-checked
  replacement, not an elimination of the limitation.

**Codex:** `analysis/claim_004_episode1_beta_range/codex/compute_episode1_beta_range.py`
— self-reported git_commit `1717ffb3ed62e6b502d7c6ef2791545737673d89` in
provenance.json. Confirmed this predates the script by three days (script
created 2026-07-09, commit dated 2026-07-06T12:14:45Z) and cannot contain
it — same pattern as claim_002's Tier A entry above, found independently
here via `.git/logs/HEAD` and file-creation timestamps. Current HEAD,
`6c920dc8533b2fd46c7f5ccbb79d665ef12b884a` ("Claim 002 rework ledger
update", 2026-07-10T05:12:02Z), postdates both runs; Preet confirmed this
is the commit that captures this output. Tree contents not independently
verified — no git-show/diff tool reaches this filesystem this session, same
standing limitation as every commit citation in this project. Output:
`beta_series_500d_core.csv`, `beta_series_730d_core.csv`, `summary.md` —
sha256 self-reported in `provenance.json`, not independently recomputed.

**Antigravity/Opus:** `analysis/claim_004_episode1_beta_range/antigravity_opus/claim_004.py`
— same stale-commit citation and same corrected-HEAD situation as Codex
above. Output: same three files, sha256 self-reported, not independently
recomputed. Its own `summary.md` explicitly declares it read none of the
paths Spec Block v3 §6 prohibits (the two `wq_recompute_episode1_beta_range*`
dirs, `worklog_tier_b.md`, Codex's output) — but §6 never named
`claim_002_healthy_episode_characterization/codex_tier_a/` or
`opus_tier_a/` as prohibited, and those directories already contain this
exact beta-range answer (see cross-check below). Not read as evidence of
anything having gone wrong — the agreement is fully explained by both
implementations doing the same deterministic OLS computation on the same
fixed dates and snapshot — but worth naming as a real gap in §6's scope for
any future claim reusing these boundaries.

**Sequencing:** Codex 2026-07-09T05:24:31Z, Opus 2026-07-09T05:32:51Z, 8
minutes apart, consistent with the required non-overlapping order. Only
start instants are recorded, not durations, so this supports but doesn't
formally prove non-overlap — same limitation as every prior claim.

**Snapshot:** `tcs_infy_v1_2026-07-04` — identical `snapshot_id` and
identical snapshot sha256 confirmed in both candidates' provenance files.

**Cross-check against claim_002 (not required by this spec, noted for the
record):** these values match claim_002's already-admitted Part 2 beta
distributional stats for the same two bases to full precision (e.g. Codex's
claim_004 500d mean_beta `0.6811805549568977` = claim_002 Part 2's Codex
500d_strict beta mean `0.681180554956898`). Expected — same computation,
same fixed dates — and anticipated as fine by claim_002's own non-goals
section.

**Process note — routing, stated plainly so this entry doesn't read as
contradicting the spec it came from:** Spec Block v3 §8 states "Does not
admit to `VERIFIED_FACTS.md` directly." This claim was originally logged
only in `ledger/worklog/claim_004_episode1_beta_range.md` and used to close
`open_questions.md` #1, per that non-goal and Preet's explicit confirmation
that this was the intended routing. Preet then separately instructed this
entry be added to `VERIFIED_FACTS.md` as well, reversing that routing
choice. Both destinations now hold the same finding — nothing about the
underlying check changed between the two, only where it's recorded.

Separately: this claim's boundaries (§1) trace to `claim_002`'s Part 1,
which was un-admitted when Spec Block v3 was drafted and is now admitted —
spec §1's provenance argument and its "Preet's call" question are both
stale as a result, not incorrect at time of writing. See
`ledger/worklog/claim_004_episode1_beta_range.md` for full detail on this,
the commit-timing check, and the isolation-scope gap.

**Admitted:** 2026-07-10 by Desktop Claude A, per Preet's explicit
instruction.
