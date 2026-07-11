# Worklog — Claim 004: Episode 1 Beta Range

Maintained by Desktop Claude A (Ledger Keeper). Follows the same per-claim
file pattern as claim_001/002/003. See `worklog.md` for the index across all
labels (moved from `ledger/worklog.md` on 2026-07-10, see `decisions.md`
same-date entry).

---

## 2026-07-09/10 — Claim 004: Episode 1 Beta Range (Spec Block v3) — CLOSES `open_questions.md` #1, admitted to `VERIFIED_FACTS.md` 2026-07-10

Reviewed against Spec Block v3, pasted directly by Preet. Preet confirmed
this claim's job is to close `open_questions.md` #1 (replace the
untraceable "0.20 to 1.91 across 22 months" figure) — per the spec's own
§8 non-goal ("Does not admit to `VERIFIED_FACTS.md` directly"), this was
initially recorded here and in `open_questions.md` only. Preet then
separately instructed the entry be added to `VERIFIED_FACTS.md` as well,
reversing that routing — see the process note in that entry. Both records
now hold the same finding.

### Sequencing note, so this isn't misread later

Claim 004's dual reproduction (`.git/logs/HEAD`: branch checked out
2026-07-09T05:21:20Z, both runs 05:24:31Z/05:32:51Z) happened *before*
Claim 002's Tier A rework (checked out 09:50:00Z, runs 09:55:42Z/10:41:43Z)
on the same day, per Preet's direction to review in numerical rather than
chronological order — I don't have a record of that instruction in this
conversation, noting it here as Preet's stated reason rather than something
I can independently confirm, though it doesn't change anything about the
check itself. That ordering means Spec Block v3 §1's provenance argument
(that claim_002's boundaries are un-admitted) was accurate when written and
is now stale — claim_002 was admitted after claim_004 was drafted, and now
covers exactly the boundaries this spec uses. Not an error in the spec;
just sequencing. §1's "Preet's call" question is moot as of claim_002's
admission.

### Provenance and commit — corrected during review

Both `provenance.json` files self-report git_commit
`1717ffb3ed62e6b502d7c6ef2791545737673d89` (2026-07-06, "Restore Claim 002
implementation script"). Checked file-creation timestamps: both scripts
created 2026-07-09 (Codex 05:23:26Z matching its 05:24:31Z execution
timestamp), three days after the cited commit. Checked `.git/logs/HEAD`
directly: `codex/claim-004-episode1-beta-range` was checked out at
05:21:20Z, both runs happened on it, and the branch was checked out *away*
at 09:50:00Z with zero commits in between — at the time of this check,
nothing covered claim_004's outputs in git history. Flagged this to Preet;
Preet's initial response was that claim_004, having run before claim_002,
could not still be uncommitted — the reflog doesn't support that inference
(chronological execution order and commit order are independent facts, and
the reflog shows no commit on that branch before the checkout away from
it), but the practical point is now moot regardless: Preet committed
directly afterward. Current HEAD is `6c920dc8533b2fd46c7f5ccbb79d665ef12b884a`
("Claim 002 rework ledger update", 2026-07-10T05:12:02Z) — timestamped
after both claim_004 runs, so it can contain them. I cannot independently
confirm the tree contents of that commit (no git-show/diff tool reaches this
session, same standing limitation as every prior claim's provenance check) —
noting this as self-reported-and-timing-consistent, not independently
verified at the tree level, consistent with how every other commit citation
in this project has been handled.

Snapshot: `tcs_infy_v1_2026-07-04`, identical `snapshot_id` and sha256 in
both provenance files. Sequencing: Codex 05:24:31Z, Opus 05:32:51Z, 8
minutes apart, consistent with required ordering (only a start instant is
recorded on either side, same caveat as always). Did not recompute sha256 —
same standing tooling gap.

### Isolation — one gap in scope worth naming

§6 prohibits reading `wq_recompute_episode1_beta_range/`,
`wq_recompute_episode1_beta_range_v2/`, `worklog_tier_b.md`, and each
other's output. Opus's `summary.md` explicitly attests to avoiding all four.
Neither implementation was asked to avoid, and neither declares anything
about, `claim_002_healthy_episode_characterization/codex_tier_a/` or
`opus_tier_a/` — which, as it happens, already contain this exact beta-range
answer (see cross-check below). The agreement found is fully explained by
both implementations doing the same deterministic OLS computation over the
same fixed dates and snapshot — same reasoning as claim_002's Parts 2 and 4
— so this isn't read as evidence of anything having gone wrong. But the
isolation list should probably have named claim_002's Tier A outputs
explicitly, given how directly they overlap in content. Worth having Claude
B include claim_002_tier_a in the isolation list for any future claim that
reuses these boundaries.

### Numeric comparison against Spec Block v3 §5's tolerance (±0.001 per
statistic, exact match on dates, exact match on codex_count == opus_count)

| Statistic | 500d core: Codex / Opus | 730d core: Codex / Opus |
|---|---|---|
| min β | 0.545092233 / 0.545092 | 0.647703964 / 0.647704 |
| max β | 0.977380659 / 0.977381 | 0.749515135 / 0.749515 |
| mean β | 0.681180555 / 0.681181 | 0.670868820 / 0.670869 |
| median β | 0.659426694 / 0.659427 | 0.662591966 / 0.662592 |
| std β | 0.103646156 / 0.103646 | 0.024954254 / 0.024954 |
| first date | 2020-01-31 / 2020-01-31 | 2020-12-31 / 2020-12-31 |
| last date | 2021-12-31 / 2021-12-31 | 2023-03-31 / 2023-03-31 |
| count | 24 / 24 | 28 / 28 |

All ten level values within ±0.001 (largest gap ~0.0001, most well under
that). Dates exact match both cores. Counts match each other and the
expected 24/28, which also matches claim_002 Part 1's already-admitted
counts for the same two bases. Zero disputes.

**Cross-check against claim_002 (not required by this spec, noted for the
record):** these values match claim_002's already-admitted Part 2 beta
distributional stats for the same two bases to full precision (e.g. Codex's
claim_004 500d mean_beta `0.6811805549568977` = claim_002 Part 2's Codex
500d_strict beta mean `0.681180554956898`). Expected, since it's the same
computation on the same fixed dates — claim_002's own non-goals section
anticipated this overlap as fine.

### Resolution

Closes `open_questions.md` #1. Verified range, month-end sampled, per core:
- 500d core (2020-01-31–2021-12-31, 24 obs): β ranges 0.5451–0.9774, mean
  0.6812, median 0.6594, std 0.1036.
- 730d core (2020-12-31–2023-03-31, 28 obs): β ranges 0.6477–0.7495, mean
  0.6709, median 0.6626, std 0.0250.

Per spec §2's non-goal: these are month-end sample points only, not a bound
on the continuous rolling-β process — β could move outside this range
between sampled dates. Same limitation the old untraceable "0.20 to 1.91"
figure had; the fix here is a traceable, tolerance-checked replacement, not
an elimination of the limitation.

### Status: ADMITTED to `VERIFIED_FACTS.md`, 2026-07-10 — see that entry's
process note for the §8 routing reversal. Also closes `open_questions.md` #1.
