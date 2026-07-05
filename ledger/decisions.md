# Decisions

Project decisions Preet has explicitly accepted, with the reasoning and the
supporting claim_id or experiment (per `PROJECT_BASE_CONTEXT.md` §7).
Maintained by Desktop Claude A (Ledger Keeper).

## 2026-07-04 — Tier classification: cointegration window-length validation is Tier B

**Decision (Preet, stated directly):** this work is Tier B, not Tier A.

**Reasoning given:** the goal was an exploratory hit-and-trial pass over
candidate window lengths for the cointegration monitor, not a decision-gating
claim. Codex and Antigravity/Opus were both run in parallel specifically so
there would be a way to cross-check one against the other — not to produce a
formal Tier A independent-reproduction admission.

**Effect:** per `PROJECT_BASE_CONTEXT.md` §4, this work does not require a
Spec Block, a pre-declared tolerance, adversary review, or a
`VERIFIED_FACTS.md` entry. See `worklog.md`, 2026-07-04 entry, for supporting
detail and for the remaining data-hygiene items (Antigravity's use of a live
data pull instead of the frozen snapshot; Codex's git-commit provenance
mismatch) that are unaffected by this decision — those are about the quality
of the two working numbers, not about tier admission.

One thing worth flagging once, not re-litigating: the base context's own tool
roster (§2) describes Antigravity-as-Opus as "Independent reproduction
(Tier A only)." Using it for Tier B work, as happened here, isn't wrong given
the reasoning above, but it's a slight tension with how that row is described
elsewhere in the project — worth keeping in mind if it causes confusion for
another tool reading this repo later.
