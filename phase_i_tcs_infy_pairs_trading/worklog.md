# ARBIT Worklog Index — Phase I: TCS/INFY Pairs Trading

This file is the permanent index for ARBIT's research worklog.

Detailed histories are stored separately to keep retrieval efficient for filesystem-based agents while preserving complete audit trails.

## Claim Worklogs

| Claim ID | Tier | Status | Date Range | Worklog |
|----------|------|--------|------------|---------|
| `claim_001_window_validation` | B (confirmed by Preet, `decisions.md` 2026-07-04) | Logged — 1 open item: DGP parameter standardization (`open_questions.md` #13) | 2026-07-04 | `ledger/worklog/claim_001_window_validation.md` |
| `claim_002_healthy_episode_characterization` | A (confirmed by Preet, 2026-07-09) | ADMITTED to `VERIFIED_FACTS.md` — Spec Block v3, all four parts (boundaries, regime stats, sub-regime split, degradation diagnostics) cleared with zero cell disputes | 2026-07-05 → 2026-07-09 | `ledger/worklog/claim_002_healthy_episode_characterization.md` |
| `claim_003_eg_halflife_ordering_robustness` | A | ADMITTED to `VERIFIED_FACTS.md` — WINDOW-LENGTH-CONTRADICTORY (500d ROBUST/unit-root caveat, 730d CONTRADICTED/parameter-stable) | 2026-07-06 → 2026-07-07 | `ledger/worklog/claim_003_eg_halflife_ordering_robustness.md` |
| `claim_004_episode1_beta_range` | A (Preet's designation) | ADMITTED to `VERIFIED_FACTS.md` (2026-07-10, per Preet's explicit instruction, reversing Spec Block v3 §8's original non-goal) — closes `open_questions.md` #1; zero cell disputes | 2026-07-09 → 2026-07-10 | `ledger/worklog/claim_004_episode1_beta_range.md` |

## Tier B — Working Questions

All Tier B investigations (excluding `claim_001`, which has its own file above
despite being Tier B) are maintained chronologically in:

`ledger/worklog/worklog_tier_b.md`

---

## Purpose

This index exists to:

- keep the top-level worklog permanently small,
- allow agents to open only the relevant claim history,
- preserve complete append-only audit trails for each claim,
- keep Tier B exploratory investigations separate from decision-gating claims.

This file should remain an index only. Do not append claim updates here.
Append updates to the appropriate claim worklog under `ledger/worklog/`, or
to `worklog_tier_b.md` for new Tier B working questions.
