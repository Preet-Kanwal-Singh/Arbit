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
`VERIFIED_FACTS.md` entry. See
`phase_i_tcs_infy_pairs_trading/ledger/worklog/worklog_tier_b.md`,
2026-07-04 entry (relocated 2026-07-10, see that date's entry below), for
supporting detail and for the remaining data-hygiene items (Antigravity's
use of a live data pull instead of the frozen snapshot; Codex's git-commit
provenance mismatch) that are unaffected by this decision — those are about
the quality of the two working numbers, not about tier admission.

One thing worth flagging once, not re-litigating: the base context's own tool
roster (§2) describes Antigravity-as-Opus as "Independent reproduction
(Tier A only)." Using it for Tier B work, as happened here, isn't wrong given
the reasoning above, but it's a slight tension with how that row is described
elsewhere in the project — worth keeping in mind if it causes confusion for
another tool reading this repo later.

## 2026-07-06 — Standing GLM disclosure policy: qualitative/directional findings permitted, exact numbers and identifiers never

**Decision (Preet, confirmed directly):** GLM 5.2 may be given qualitative or
directional project findings when needed to frame a question, provided that
ticker/company identifiers and any computed or exact values (phi, beta, FNR,
p-values, specific dates, or any other specific number) are never disclosed.
Default remains hypothetical/generic phrasing whenever the qualitative fact
isn't actually load-bearing for the question being asked.

**How this arose:** Desktop Claude B raised this as a standing-principle
question, via Preet, after the same GLM-provenance question reportedly came
up for a third time across separate sessions with Claude #3. Before
recording this, I flagged that the plain text of `PROJECT_BASE_CONTEXT.md`
§3 is written as a hard boundary — "GLM never receives... anything that
would let a reader reconstruct what this project has found" — and that a
qualitative, project-specific directional finding can do that even with no
ticker and no number attached, which is a broader test than "strip the
numbers and tickers." Preet confirmed explicitly, aware of that distinction:
qualitative/directional content is permitted, exact numbers are not, in what
gets sent to GLM. Recording this as a real loosening of §3's literal text,
not merely a clarification of it, per my own read of the base context —
not softening that characterization just because it was approved.

**Scope:** applies to every future GLM query project-wide, not just one
claim. Supporting claim reference: `claim_003_eg_halflife_ordering_robustness`. Preet's original framing
(relayed from Desktop Claude B) cited `[claim_003]`, which does not exist in
this repo as of 2026-07-06 — only `claim_001_window_validation` and
`claim_002_healthy_episode_characterization` exist under `analysis/`.
Recording the decision now rather than blocking on that detail; the
citation should be corrected here once it's clear what it actually refers to.

**Not done by me:** `PROJECT_BASE_CONTEXT.md` §3 itself is unchanged — this
decision currently lives only in this ledger entry. If the goal is to stop
this being re-litigated with Claude #3 or anyone else who works from the
base context rather than the ledger, §3 likely needs amending to match.
That's a base-context edit, outside my role as Ledger Keeper — would need
Desktop Claude B or Preet to do it directly.

## 2026-07-07 — Worklog modularization

**Decision (Preet, confirmed directly):** the research worklog is reorganized
from a single monolithic file into a modular structure.

**Reasoning given:** Tier A claim histories grow substantially through multiple
review and update cycles, while Tier B investigations are short-lived and
append-only. Filesystem-based agents (Desktop Claude A and Desktop Claude B)
cannot search file contents directly and were increasingly forced to reread a
large worklog for claim-specific tasks. The new structure keeps retrieval
efficient while preserving complete append-only audit trails.

**New layout (as of 2026-07-07 — superseded 2026-07-10, see that entry
below for the current phase-scoped locations; recorded here unchanged as
the accurate historical description of what this decision actually put in
place at the time):**

- `ledger/worklog.md` — permanent index.
- `ledger/worklog/<claim_id>.md` — append-only worklog for each Tier A claim.
- `ledger/worklog/worklog_tier_b.md` — chronological log of Tier B working
  questions and exploratory investigations.

**Effect:** references throughout the project that previously pointed to
`worklog.md` should now refer either to the worklog index or to the appropriate
Tier A/Tier B worklog file as applicable. This is a repository-governance
change only; it does not alter any statistical methodology, claim outcome, or
ledger admission criteria.

## 2026-07-08 - Claim 004
claim_004 proceeds using claim_002's Q1 boundary determination as a fixed input, despite claim_002 lacking a Spec Block/admission, because Q1 is a deterministic exact-match with independent reproduction, not a judgment call. Does not extend to claim_002's other findings (Q2–Q5), which remain unresolved

## 2026-07-10 — Multi-phase modular restructuring

**Decision (Preet, stated directly):** the project is restructured from a
single flat TCS/INFY investigation into multiple self-contained phases, each
with its own ledger. Phase I is the existing TCS/INFY pairs-trading work.
Phase II is a planned RL agent built on TCS/INFY. Phase III is a planned
pairs-trading analysis on a different pair (example given: TATASTEEL/
JSWSTEEL). Further phases follow the same pattern.

**Reasoning given:** the same problem the worklog modularization
(2026-07-07) solved at the claim level now applies at the project level —
phases are substantively different investigations (different research
questions, potentially different tickers or methods entirely) that
shouldn't share one global claim-numbering space, one global
`VERIFIED_FACTS.md`, or one global open-questions backlog. Keeping each
phase self-contained keeps it portable and keeps retrieval efficient the
same way the earlier split did.

**New layout (each phase fully self-contained):**

    Arbit/
    ├── PROJECT_BASE_CONTEXT.md        (process rules only, phase-agnostic)
    ├── decisions.md                    (stays global, unsplit — see below)
    ├── process_notes.md                (new — cross-cutting tooling/process
    │                                     gaps that belong to no single phase)
    ├── data/snapshots/                 (stays global — shared across phases,
    │                                     already keyed by ticker pair + date)
    ├── phase_i_tcs_infy_pairs_trading/
    │   ├── PHASE_CONTEXT.md            (phase history/carry-forward status,
    │   │                                 migrated from PROJECT_BASE_CONTEXT
    │   │                                 §1/§8)
    │   ├── VERIFIED_FACTS.md
    │   ├── open_questions.md
    │   ├── worklog.md                  (phase-level index)
    │   ├── ledger/worklog/<claim_id>.md, worklog_tier_b.md
    │   └── analysis/<claim_id>/, analysis/wq_*/
    ├── phase_ii_rl_agent_tcs_infy/      (same skeleton, empty until populated)
    └── phase_iii_tatasteel_jswsteel/    (same skeleton, empty until populated)

**Claim numbering:** per-phase, not global — restarts at `claim_001` inside
each phase folder. Phase I's existing `claim_001`–`claim_004` are
unaffected.

**`decisions.md`:** stays a single global file, not split — decision volume
is low enough that one chronological cross-phase log is more useful than
fragmenting it; entries name their phase where relevant.

**Migration note:** `PROJECT_BASE_CONTEXT.md` §1/§8's phase-specific content
moved to `phase_i_tcs_infy_pairs_trading/PHASE_CONTEXT.md` verbatim, with
one deliberate exclusion (the old §8 "open Tier A questions" list, already
duplicated and more current in that phase's `open_questions.md` — copying
it again would have re-introduced a stale, already-resolved item). Old
`ledger/open_questions.md` item #14 (provenance-stamping gap) moved to the
new root `process_notes.md` #1, since it's a cross-cutting tooling issue,
not Phase I-specific research — item left in place in `open_questions.md`
with a pointer, not deleted, per this project's append-only convention for
resolved/relocated items.

**Effect:** every path reference in every existing ledger file that pointed
to a project-root ledger location now points to a phase-scoped one instead.
Repository-governance change only — no statistical methodology, claim
outcome, or admission criteria changes for anything already admitted.
