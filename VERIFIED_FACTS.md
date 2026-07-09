# VERIFIED_FACTS.md

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
