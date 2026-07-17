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

## 2. Branch staleness — `main` had never received a merge (resolved 2026-07-11, recurred 2026-07-12)

Surfaced during Phase II Tier C work (env scaffolding v0), confirmed
directly against `.git/logs/HEAD` and `.git/refs/heads/main`, not taken on
description.

From this project's first commit through 2026-07-11, every task landed on
its own feature branch (`codex/...`) with no fast-forward back to `main`.
Concretely: `main`'s tip sat at
`1717ffb3ed62e6b502d7c6ef2791545737673d89` ("Restore Claim 002
implementation script", 2026-07-09) while `claim_002`'s Tier A
dual-reproduction rework (`8105c13004a96737ae15d120c93f4e62ed9ead39`,
`6c920dc8533b2fd46c7f5ccbb79d665ef12b884a`) and `claim_003`'s implementation
commit (`c3e49d184fd05a4be3fe63421c2b2c80cf6402ca`) happened on branches
`main` never reached.

Resolved via `git merge --ff-only codex/phase-ii-env-scaffolding-v0` into
`main`. Confirmed this is a genuine fast-forward — reflog records it as
"Fast-forward," no merge commit, linear chain — moving `main`'s tip to
`44a899da0d3da3a5f649f981d1c2a4c4156804e8`. That commit's ancestry (traced
by hand through the reflog's parent→child pairs) now includes
`c3e49d18...` and both `claim_002` rework commits above, none of which
`main` could reach before this merge.

**Retroactive effect on Phase I:** anyone who checked out `main` between
2026-07-09 and 2026-07-11 would not have seen `claim_003`'s implementation
or `claim_002`'s Tier A rework, despite both already being admitted to
Phase I's `VERIFIED_FACTS.md`. No evidence this affected any admission
decision — both claims' files were read directly off their actual feature
branches at the time, per the paths cited in Phase I's `VERIFIED_FACTS.md`
— but recording it since "check out `main`" is not a safe way to see the
project's current state, as of any point before today.

**Relationship to entry #1 — recorded as a disagreement, not folded in
silently:** this was relayed to me as "the root cause... behind the five
provenance-mismatch incidents" in entry #1. I don't think that's accurate
and am flagging it rather than accepting the framing. Entry #1's pattern is
a stamp taken at script-run time, before outputs are committed — that
happens regardless of which branch the commit lands on, including `main`
itself. Concretely, `claim_003`'s stamped-vs-actual mismatch was between two
commits both directly on `main` (the actual containing commit landed on
`main`, not a feature branch) — a same-branch timing problem, not a
branch-reachability one. The one entry-#1 case that does overlap with this
finding is `claim_002`'s Tier A rework, which sat on a feature branch until
today's merge — one of five, not the mechanism behind all five. Treating
this as its own finding, related to entry #1 but not its explanation.

**Not yet fixed upstream:** nothing currently prevents the same staleness
from recurring on the next feature branch. Whether merges to `main` should
happen automatically per task, or stay a periodic manual step, is open —
Preet's call.

**Recurred, 2026-07-12, exactly as predicted above.** Confirmed directly
against `.git/refs/heads/main`: `main` is still at
`83e8fedce564c0afa4dc14cfe4eb3f46a4427871` (the `claim_005` commit) while
three new commits exist on `feat/phase2_tier_c_eg_p_trend` (Phase II's
`eg_p_trend` feature work), unreached by `main`. I can detect this pattern
but can't fix it this time — I have read access to `.git/logs/HEAD` and
`.git/refs/*` via the filesystem tool, but no git-execution tool in this
environment, so merging `main` forward requires someone else's action.
Full detail in `phase_ii_rl_agent_tcs_infy/PHASE_CONTEXT.md`.

## 3. Path citations may not survive phase restructuring — checked 2026-07-11, one confirmed instance

Follow-up pass across all four Phase I claims, done at Preet's request:

- **`claim_003`:** confirmed stale. `VERIFIED_FACTS.md` cites
  `analysis/claim003/codex/run_claim003_eg_halflife_ordering_robustness.py`.
  This was correct at admission time — Codex's own `provenance.json` for
  this claim records `git_status_short_at_run` including
  `?? analysis/claim003/` at the moment the script ran, so the directory
  really was named `claim003` then. It has since been renamed to
  `claim_003_eg_halflife_ordering_robustness` (same subfolders and files) —
  I did not pin down the exact renaming commit, only that it's at or before
  "Project Phase Reconstruction" (`5f9c7121ebd357d5f700f46c96391cd973a97901`).
  Files confirmed present at the new path. Correction note added directly
  to that claim's `VERIFIED_FACTS.md` entry (2026-07-11), original citation
  left untouched.
- **`claim_002`:** checked both `codex_tier_a/run_claim_002_healthy_episode_characterization.py`
  and `opus_tier_a/run_claim_002.py` against the current repo layout — both
  resolve exactly as cited, no drift.
- **`claim_004`:** checked both `codex/compute_episode1_beta_range.py` and
  `antigravity_opus/claim_004.py` — both resolve exactly as cited, no
  drift.
- **`claim_001`:** Tier B, no `VERIFIED_FACTS.md` entry, nothing to check
  here.

So this is not a general restructuring problem — `claim_002` and
`claim_004`'s directories already had their full descriptive names before
the restructuring and were unaffected; `claim_003`'s directory was
abbreviated (`claim003`) and got renamed at some later point, breaking its
citation. Treating this as resolved for the four existing Phase I claims.
Worth keeping in mind for Phase II/III: if a claim's working directory ever
get renamed after `VERIFIED_FACTS.md` cites it, the citation goes stale
silently — nothing currently checks this automatically.

## 4. `env/` was gitignored — Phase II source history is incomplete before 2026-07-16

Found while updating `phase_ii_rl_agent_tcs_infy/PHASE_CONTEXT.md` at
Preet's request, after B flagged that file as stale. Confirmed directly
against `.git/logs/HEAD`: commit
`94393d55ca82fd4007c9e1daaec32075be94bec8`, "fix(phase2): remove env/ from
.gitignore, add previously-untracked env source files," made directly on
`main` (not a feature branch) at 2026-07-16 06:20:13 UTC (converted from
the reflog's epoch myself, not read off a label).

This is a different, more severe category of gap than #1 above. #1 is a
commit citing the wrong hash for content that exists *somewhere* in git
history. This is `phase_ii_rl_agent_tcs_infy/env/*.py` — every file
implementing the environment, feature registry, and reward registry — not
being tracked by git **at all** until this one commit. My evidence is the
commit message's own words ("add previously-untracked env source files")
plus the timeline; I don't have a git-log-for-path or git-show tool to
independently confirm zero prior history file-by-file, so I'm reporting
what the self-report and timeline support, not an exhaustive diff audit.

**Compounding this: the feature branch created for this exact window of
work was never actually used.** `feat/phase2_tier_c_positive_control_v1`
was checked out repeatedly between 2026-07-15 14:16 UTC and 2026-07-16
05:47 UTC (roughly 15.5 hours), but the reflog shows zero commits landing
on it in that entire span — its branch pointer never moved from the commit
it was created at. Every commit from `94393d55` onward (the gitignore fix,
two PC-1-provenance fix commits including one `git commit --amend`, and a
final correction commit dated 2026-07-17) was made directly on `main`, no
branch involved. So for this window, both this project's usual
branch-then-merge convention and (independently) `env/`'s trackability were
bypassed at the same time.

**What this means for Phase II `PHASE_CONTEXT.md` entries 1, 3, 4, 5, 6 (as
currently numbered), all dated before 2026-07-16 06:20 UTC:** each cites a
specific commit as where a described `env/*.py` change landed, based on
commit messages and the code-commit-then-provenance-stamp timing pattern.
Those commits almost certainly do not actually contain the `env/*.py`
diffs their messages describe, because `git add` (whatever form it took)
would have silently skipped everything under `env/` the entire time. What I
reported as "confirmed in the current code" in each of those entries is
still accurate — I read the live working tree, which reflects reality as of
when I read it — but the specific commit citations attached to those
observations are very likely broken in the way #1 describes, just
categorically worse: not mistimed, absent. I have not gone back and
re-verified each of those five entries' citations individually; that would
need a git-show/diff tool I don't have. Flagging the scope and mechanism
here rather than asserting a fix for each entry — see the notice added to
the top of `PHASE_CONTEXT.md` itself.

**One more loose end, not yet resolved, flagged rather than fixed by me:**
`wq_positive_control_v0/provenance.json` contains a `git_commit_correction`
note (attributed to Desktop Claude B) stating the corrected git_commit "has
not yet been committed to git as of this correction." That's no longer
accurate — I checked `.git/refs/heads/main`, and it's now
`4b07cca32a9eaec66a1274f39d952d4c6d9d41c2`, the exact commit the correction
points to. The correction was committed; the note saying otherwise wasn't
updated afterward. Not editing another Claude instance's attributed note
without being asked — flagging it for B or Preet to close out.

**Not yet fixed as a process:** nothing currently prevents a similarly
broad `.gitignore` pattern from silently excluding a real source directory
again, and nothing currently prevents a created feature branch from being
quietly bypassed in favor of committing straight to `main`. Both are
workflow gaps, not one-off mistakes.
