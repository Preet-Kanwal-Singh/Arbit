# Worklog — Claim 003: EG/Half-Life Ordering Robustness

Maintained by Desktop Claude A (Ledger Keeper). Split out of `ledger/worklog.md`
on 2026-07-07 per Preet's decision — see `ledger/decisions.md`, 2026-07-07
entry ("Worklog split by label"). See `ledger/worklog.md` for the index
across all labels. This claim was ADMITTED to `VERIFIED_FACTS.md`; that file
holds the final entry, this file holds the full process history behind it.

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

### Update, same session — v8 spec received; fixes the gap, doesn't answer the question I actually asked

Desktop Claude B (via Preet) sent Spec Block v8, self-contained, changing
"the study-level tree, phi_post reporting, and dispute reporting" from v7 —
which I have not seen; only v6 and now v8.

**What v8 fixes, cleanly:** it splits the old blanket "mismatch → withhold the
whole window" rule into DISPUTED-CLASSIFICATION (categorical labels differ —
blocks the window, marks UNRESOLVED) versus DISPUTED-VALUE (categories agree,
|ΔP̂|>0.05 — that cell's point estimate isn't citable, but it does not block
the window's categorical rollup). Under this rule, 730d/C2 (both ROBUST,
Δ=0.069) is DISPUTED-VALUE, not DISPUTED-CLASSIFICATION — so 730d's window
classification (CONTRADICTED, driven cleanly by C1/C3/C4) is not blocked.
v8 also adds a genuine new top-level branch, WINDOW-LENGTH-CONTRADICTORY (one
window ROBUST, one CONTRADICTED), which v6 didn't have. I re-applied this tree
myself to the actual per-window data already on file (500d: ROBUST,
`phi_post` CI high 1.0043, i.e. `phi_post_includes_unit_root=TRUE`; 730d:
CONTRADICTED, CI high 0.9429, stable) and independently arrive at the same
verdict the spec's own worked example states: **WINDOW-LENGTH-CONTRADICTORY,
with the 500d (ROBUST) side flagged for a phi_post CI that includes the unit
root.** Per v8's mandatory write-up rule, that means: *the post-regime AR(1)
fit cannot rule out a non-stationary process; half-life deterioration may not
be a well-defined event in this regime* for the 500d side specifically.

Worth being precise about one consequence of this: both Codex's and Opus's
own self-reported `study_status` field say plain `"CONTRADICTED"` in their
provenance.json. That's now stale — it reflects whatever tree version their
scripts had built in, not v8. `WINDOW-LENGTH-CONTRADICTORY` is a materially
different, more accurate characterization of what's actually in the data
(one window supports the ordering, one doesn't) than a flat "CONTRADICTED,"
and I'm recording the v8-correct label here rather than the two tools' own
outdated self-reports.

**What v8 does not address — the actual question I asked last turn.** I asked,
precisely: when was the synthesis rule actually finalized relative to Codex's
(09:30:39Z) and Opus's (11:33:46Z) runs; is v5 available to diff against; and
who actually verified the "full 3×3 state space" claim, and how. None of that
was answered. Instead I've now been handed a *third* revision (v6 → v7 → v8)
of exactly the logic that determines how this specific, already-known dataset
gets classified — each one, including this one, arriving with a worked example
built from the exact numbers I disclosed. A rule that keeps getting refined in
direct response to disclosed results, however well-reasoned each individual
refinement is, is what data-dependent rule construction looks like in
practice. I'm not concluding that's what happened — I don't have the facts to
conclude that — but I'm also not going to let three iterations of good
engineering substitute for an answer to the actual question.

**One real mitigating fact, stated plainly because it cuts the other way:**
the underlying data-affecting thresholds — the 0.05 cross-implementation
tolerance, the CI-based ROBUST/CONTRADICTED cutoffs, the 0.98/1.0 phi
thresholds — are unchanged across v6/v7/v8 per the spec's own text ("unchanged
from v6/v7"). What's been revised each time is the aggregation/reporting logic
for combining already-fixed per-cell numbers into a top-level label, not the
criteria that produced those per-cell numbers in the first place. That's a
meaningfully smaller integrity problem than moving the actual pass/fail
threshold after seeing the data, and I don't want to overstate the concern by
ignoring it.

**Where this leaves Claim 003:** I applied v8's tree (a mechanical exercise —
re-classifying already-existing, already-fixed per-window numbers, not
computing anything new) and recorded the correct label above. I have not
admitted anything to `VERIFIED_FACTS.md`, and I'm not going to, until Preet
answers the sequencing question directly — not through a further spec
revision, an actual account of when the synthesis rule was locked relative to
the two runs. See `open_questions.md` #26.

### Update, 2026-07-07 — ADMITTED. `VERIFIED_FACTS.md` created, first entry.

Preet answered the sequencing question directly, not through a further spec
revision:

1. **Shared v5 on request.** v5 failed Claude #3's adversarial review. This is
   normal, expected process (base context §5 step 2: "Fail → back to step 1")
   — I was wrong to treat the existence of a pre-execution revision cycle
   itself as a concern last turn. Comparing v5 to v6: the fix was adding
   PARAMETER-STABLE as a gate on *every* exit path (v5 only gated the
   fallback/INCONCLUSIVE branch, meaning an unqualified ROBUST or CONTRADICTED
   verdict was possible even with an unstable phi estimate). That's a
   legitimate, generalizable methodological fix, of the kind adversarial
   review is supposed to produce — nothing about it is specific to this
   dataset.
2. **v8's "full 3×3 state space" check was done by Claude #3 during v8's
   approval** — not Claude B self-verifying its own fix. This was the actual
   gap in my last message, and it's now closed by a real, independent check,
   not a self-report (which per base context §9/§3 would not count as
   evidence on its own).

What remains only partially resolved, stated plainly rather than smoothed
over: I've still never seen v7, and don't have an exact timestamp for when v8
was finalized relative to my own disclosure of the specific 730d/C2 numbers.
Given the part that actually mattered — independent verification of the fix,
rather than Claude B's own account of it — is now confirmed, I judged this
sufficient to proceed rather than continuing to hold the claim on a gap I no
longer think is doing much work.

**Created `VERIFIED_FACTS.md`** (did not exist before this session) with the
mandatory note and one entry: `claim_003_eg_halflife_ordering_robustness`,
WINDOW-LENGTH-CONTRADICTORY (500d ROBUST + `phi_post_includes_unit_root=TRUE`;
730d CONTRADICTED + parameter-stable, with cell C2 flagged DISPUTED-VALUE and
its point estimate excluded from citation). Full entry in that file, including
the same process history noted above — kept in the ledger entry itself
rather than only here, so anyone reading `VERIFIED_FACTS.md` alone gets the
full picture, not just the clean-looking result.

Still open, not blocking admission but worth resolving: the 730d/C2 cell
itself (why that specific config diverges beyond tolerance), and getting v7
for completeness. See `open_questions.md` #26 (updated) and #21.

### Update, 2026-07-07 — v7 obtained; git commits confirmed; one more precise finding, admission stands

Preet confirmed directly: every ledger/base-context edit from earlier in this
session, up to but not including `VERIFIED_FACTS.md` itself, is git committed.
Resolves `open_questions.md` #25.

Preet also shared v7 (I had only inferred its existence from v8's changelog
line before). Reading it directly surfaced something the v6-vs-v8 comparison
alone didn't show me: **v6→v7 changed the study-level CONTRADICTED condition
from "either window length" to "both," not just the cross-implementation
dispute handling I already knew about.** v5 states outright: "Asymmetry is
intentional: burden of proof sits with the robustness claim" — true at the
per-window level in every version (ROBUST needs all 5 configs; CONTRADICTED
needs only one). v6 carried that same asymmetry up to the study level
(CONTRADICTED if *either* window is CONTRADICTED). v7 dropped it, requiring
*both* windows CONTRADICTED. On the real data, this is the exact change that
turns a plain CONTRADICTED verdict into the WINDOW-LENGTH-CONTRADICTORY
verdict I admitted.

There's a real, structural reason this may not have been optional: the new
WINDOW-LENGTH-CONTRADICTORY branch would be dead code under the old "either"
rule, since "either CONTRADICTED" would already resolve the
one-ROBUST-one-CONTRADICTED case before the tree ever reached it. Adding the
branch and flipping either→both are the same change, not two separate ones.
That's a genuine mitigating fact, not an excuse I'm constructing after the
fact — but it doesn't fully answer whether reversing a deliberately-stated
asymmetry was independently evaluated as methodologically sound, versus just
checked for logical completeness (does every cell in the 3×3 state space have
some branch). Those aren't the same review. I don't know which one happened.

**Not retracting the admission.** I think WINDOW-LENGTH-CONTRADICTORY is
genuinely more informative than a blunt CONTRADICTED would have been —
collapsing "one window robust, one window broken" into a flat rejection loses
real information regardless of how the label came to exist. But I've updated
the `VERIFIED_FACTS.md` process note to include this specific detail, since
the version I wrote before seeing v7 didn't have it, and a reader of that
file should get the full picture I have now, not the partial one I had
yesterday. See `open_questions.md` #30 for the specific open question this
leaves — not blocking, but real.
