# Worklog — Claim 005: Volume Event Study, TCS 500d-Core Boundary

Maintained by Desktop Claude A (Ledger Keeper). Follows the same per-claim
file pattern as claim_001–004. See `worklog.md` for the index.

---

## 2026-07-12 — Claim 005: Volume Event Study TCS-500d (Spec Block v2) — ADMITTED to `VERIFIED_FACTS.md` as a non-reproduction

Reviewed against Spec Block v2, pasted directly by Preet, approved by
Claude #3. This is the Tier A escalation of the Tier B finding logged at
`ledger/worklog/worklog_tier_b.md` (`wq_volume_signal_test_tier_b_v2`),
anchored to `claim_002`'s **admitted** 500d-core boundary (2021-12-31)
rather than the unadmitted date the original exploratory pass used
(2022-01-31, `open_questions.md` #18, still open — this claim does not
close it).

### Files opened directly

`analysis/claim_005_volume_event_study_tcs500d/codex/` and
`.../opus_tier_a/`, both containing `provenance.json`, `regression_results.csv`,
`data_quality_report.csv`, `dropped_zero_volume_dates.csv`,
`event_window_dates.csv`, `summary.md`, `run_claim_005.py`.

### Required pre-check (spec's own explicit ordering): dropped-date lists compared before coefficients

- **Event window dates:** identical, 20/20, same order, both starting
  2021-12-03 and ending 2021-12-30.
- **Zero-volume dropped dates:** identical, 23/23, same dates, same order,
  both confirming 0 of the 23 fall inside the event window.
- **Inner-join TCS-only dropped dates:** spec only requires a **count** here
  (not an explicit list) — both report 7. Codex's `provenance.json` also
  happens to list the 7 dates explicitly (2019-01-01, 2019-10-27,
  2020-11-14, 2026-01-15, 2026-05-01, 2026-05-28, 2026-06-26); Opus's does
  not surface the list anywhere in its outputs, only the count. Not a spec
  violation — the explicit-list requirement was written for the zero-volume
  drop specifically, not this one — but worth Opus's implementer knowing
  Codex's list is available if anyone wants to cross-check it later.

Both pre-checks clear. Proceeding to compare coefficients was appropriate
per the spec's own gating logic.

### Coefficient comparison

| | Codex | Antigravity/Opus | Diff |
|---|---|---|---|
| gamma (EventWindowDummy) | -0.15753297598819485 | -0.15625938835119407 | 0.00127 |
| HC3 SE | 0.0680480035086849 | 0.06824369994149956 | finite, both |
| one-sided p (gamma>0) | 0.9896942770023477 | 0.9889814034464772 | both ≫0.05 |
| n_obs | 1907 | 1907 | match |

`|gamma_A - gamma_B| = 0.00127`, well inside the pre-declared `≤0.03`
tolerance. Both HC3 SEs finite. Neither one-sided p-value is anywhere near
0.05 — both implementations find gamma **negative**, i.e. abnormal volume
in this specific window is if anything below baseline, not above it.

Per Spec Block v2's own outcome rules: *"Neither reproduction reaches
p<0.05: claim does not reproduce. Plain language, no special tag needed."*
That is the outcome here. This is **not** `REPRODUCED-ADJACENT-WINDOW` —
that label requires both p<0.05, which did not happen — and it is **not**
`DISPUTED-BORDERLINE` or `DISPUTED-VALUE` either, since both implementations
agree closely and agree on the (null) conclusion. This is a clean,
tolerance-checked, mutually-agreeing negative result.

### A real, unreconciled specification gap — doesn't change the outcome, but flagging it

The spec's methodology line just says "[day-of-week dummies]," without
pinning down which days get their own dummy or what the reference category
is. The two implementations resolved this differently:

- **Codex:** baseline = Monday; separate dummies for Tue/Wed/Thu/Fri/**Sat**
  (5 dummies). `DOW_Saturday` coefficient is -1.598 with an SE of 48.0 —
  essentially unidentified, consistent with a handful of special Saturday
  trading sessions (Indian markets occasionally hold these). R² = 0.18694.
- **Opus:** baseline = Friday; dummies for Mon/Tue/Wed/Thu only, **no
  Saturday dummy at all** — Saturday observations are implicitly folded
  into whatever category Opus's join produced, not given their own
  control. R² = 0.18083.

Same `n_obs` (1907) in both, so this isn't a data discrepancy — it's a
genuine difference in nuisance-parameter specification that the spec didn't
fully pin down. It doesn't affect this claim's outcome: gamma is the only
coefficient the tolerance check cares about, and it agrees to within 0.0013
regardless of how the two implementations handled Saturday. But if this
model is ever reused for the 730d window or for INFY, Desktop Claude B
should probably pin down the day-of-week specification exactly (as
precisely as the zero-volume-drop rule was pinned down here) before running
it, so a future comparison isn't accidentally checking two different models
that happen to agree by coincidence rather than by construction.

### Provenance and commit — corrected in-file, per Preet's explicit instruction

Both `provenance.json` files originally self-reported `git_commit
c4b24437d5c562dd064e1c2e5235a55fe88f0920`. Codex's own
`git_status_short_at_run` field showed the entire
`claim_005_volume_event_study_tcs500d/` directory as untracked (`??`) at
that moment — that commit cannot contain either candidate's output. Checked
`.git/logs/HEAD` directly: the actual containing commit is
`83e8fedce564c0afa4dc14cfe4eb3f46a4427871` ("Claim 005 volume tcs 500d"),
confirmed as `main`'s current tip (`.git/refs/heads/main`). Sixth
occurrence of the provenance-stamps-pre-commit-HEAD pattern logged at
`process_notes.md` #1 — not re-opening that entry, just adding to the
count.

Unlike `claim_002`/`003`/`004`, where this same pattern was left in the
original files and only annotated downstream in `VERIFIED_FACTS.md`, Preet
instructed the `git_commit` field itself be corrected in both
`provenance.json` files before admission, not just noted as a curiosity.
Done: both files now have `git_commit` set to
`83e8fedce564c0afa4dc14cfe4eb3f46a4427871`, with the original
self-reported value preserved (not deleted) in a new
`git_commit_correction` object alongside it, dated and attributed to me.
This is a deliberate deviation from the append-only-annotation pattern used
on the three prior claims, scoped to this claim only — not a change to how
I'll handle this pattern by default going forward unless told otherwise.

One thing raised and resolved directly by Preet: the stale commit's message
("Second implementation by Codex," on branch
`codex/phase-i-volume-signal-independent`) looked like it might reference
some other, unexplained prior attempt at this claim. Preet confirmed it's
old Tier B context, unrelated to `claim_005`'s substance — the commit just
happened to be whatever `main`'s HEAD was at the moment both scripts ran.
Not investigated further.

### Sequencing

Opus's `execution_timestamp_utc` (2026-07-12T09:58:27Z) is *earlier* than
Codex's `timestamp_utc` (2026-07-12T14:20:13Z) — i.e., on these timestamps
alone, Opus appears to have run first, not second. The base context's
ordering requirement (§5 step 4) is about Opus not being shown Codex's
approach or numbers before producing its own, not about wall-clock order
per se, and I have no way to independently confirm what either operator saw
before running — same standing limitation as every previous claim's
sequencing note. Flagging the reversed timestamp order plainly rather than
assuming it doesn't matter.

### Snapshots

Both cite `tcs_infy_v2_2026-07-11` (sha256 `28d1ef41...`) and
`nifty_it_benchmark_v1_2026-07-11` (sha256 `fb842bcc...`), identical
between candidates. Neither hash independently recomputed — same standing
tooling gap as every prior claim.

### Resolution

Claim 005 does not reproduce a significant positive abnormal-volume effect
for TCS in the 20 trading days before the *admitted* 500d-core boundary
(2021-12-31). Both implementations agree closely (within the pre-declared
tolerance) that gamma is negative and nowhere near significant for the
one-sided test the spec specifies. This is a real result, not an absence of
one — it directly narrows what `wq_volume_signal_test_tier_b_v2`'s
adjacent-but-different-window finding can be used to argue, per the spec's
own required limitation.

### Status: ADMITTED to `VERIFIED_FACTS.md`, 2026-07-12, as a non-reproduction.
