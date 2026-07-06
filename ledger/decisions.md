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
