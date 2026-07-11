# Process Notes

Cross-cutting tooling or process gaps that apply across phases and aren't
yet resolved (so don't belong in `decisions.md`, which is for accepted
decisions) and aren't specific to one phase's research (so don't belong in
any phase's `open_questions.md`). Maintained by Desktop Claude A (Ledger
Keeper).

## 1. Provenance-stamping design gap

The git commit hash recorded in a candidate's `provenance.json` reflects
HEAD at the moment the script ran, not the commit whose tree actually
contains the output files being described — because outputs get committed
*after* the run, sometimes hours after, sometimes not at all until flagged.

Seen five times across Phase I: claim_001, claim_002's original non-Tier-A
pass, claim_003, claim_002's Tier A dual reproduction (2026-07-09 — the
worst instance, no later commit existed at all until Preet committed on
request), and claim_004 (2026-07-09/10 — same pattern, also required a
manual commit after being flagged).

Worth fixing upstream now rather than catching this a sixth time, in any
phase: stamp provenance with the commit made immediately after committing
outputs, not the pre-run HEAD. See Phase I's
`ledger/worklog/claim_002_healthy_episode_characterization.md` and
`ledger/worklog/claim_004_episode1_beta_range.md` (2026-07-09/10 entries)
for the full detail behind each instance.
