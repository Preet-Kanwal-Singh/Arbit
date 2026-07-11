# ARBIT — Base Context

Load this into every tool's context before giving it a task: Claude Projects
(as project knowledge), Antigravity (paste at the start of a session), Codex
(as AGENTS.md or equivalent). If a per-tool prompt conflicts with this file,
this file wins. This file covers process only — phase-specific investigation
history, carry-forward status, and open Tier A questions live in each
phase's own `PHASE_CONTEXT.md` (§0).

## 0. Active phases

| Phase | Folder | Status | One-line scope |
|---|---|---|---|
| I | `phase_i_tcs_infy_pairs_trading/` | Active | TCS/INFY cointegration pairs-trading track — the original investigation. |
| II | `phase_ii_rl_agent_tcs_infy/` | Planned | RL agent built on TCS/INFY. |
| III | `phase_iii_tatasteel_jswsteel/` | Planned | Pairs-trading analysis on a second pair (TATASTEEL/JSWSTEEL, or whichever pair is actually chosen). |

Every Spec Block, question, or task must state which phase it belongs to
before any tool touches that phase's files. See that phase's
`PHASE_CONTEXT.md` for its specific history before starting work in it.

## 1. Why this process exists

Phase I's early investigation (GLM sandboxes, rounds 1–7) produced four
consecutive "decisive" findings that were each retracted, and one
foundational number whose origin became untraceable — no script or data
computation could be found backing it, in any sandbox. Full detail in
`phase_i_tcs_infy_pairs_trading/PHASE_CONTEXT.md`. The root cause was not
any one tool being unreliable — it was (a) sandboxes that didn't persist
across sessions, and (b) a model's self-report about its own authorship or
correctness being treated as evidence. Every rule below exists to close one
of those two gaps, for every phase, not just Phase I. Do not re-add process
on top of this without checking it's closing a gap that's actually present
— the last version of this system became too heavy and was deliberately cut
back.

## 2. Tool roster and roles

| Role | Tool | Model | Filesystem access | Writes to ledger? |
|---|---|---|---|---|
| Builder | Codex | — | yes, local repo | no |
| Independent reproduction (Tier A only) | Antigravity | Opus — select manually | yes, local repo | no |
| Bulk engineering (Tier B/C) | Antigravity | Gemini 3.1 Pro (default) | yes, local repo | no |
| Ledger Keeper | Desktop Claude A (Project) | Claude | yes, filesystem MCP | **yes — sole writer, all phases** |
| Orchestrator / spec writer | Desktop Claude B (Project) | Claude | yes, filesystem MCP | no |
| Adversary | Claude #3 (Project, offshore) | Claude | **no filesystem access** | no |
| Generic literature/methodology only | GLM 5.2 | — | **no project access at all** | no |

Every tool above should know this full table exists, including the tools it
never directly interacts with, and that its scope spans every phase, not
just the one it's currently working in. If you're unsure whether something
is your job, it's probably one of the other rows — check before doing it
anyway.

## 3. GLM — hard boundary, read this even if GLM isn't the tool you are

GLM 5.2 is used **only** for content that stays generic even given in full,
regardless of which phase it relates to: general cointegration test theory,
general AR(1)/near-unit-root bias-correction literature, RL methodology,
whether a cited paper exists and is on-topic, general risk-control
literature. GLM never receives: ticker names (any phase, any pair), actual
computed values (phi, beta, FNR numbers), file/variable names, or anything
that would let a reader reconstruct what any phase has found. A
generic-sounding question with a real number attached ("does FNR≈0.46 at
phi=0.95 match theory") is **not** generic — the number itself is the leak.
GLM's own past sessions are also why this project restarted at all: it gave
two contradictory, equally confident self-reports about whether it had
originated a number ("I fabricated this" — later shown false; "this is mine
and documented" — also unverified). Nothing GLM says about this project,
including about itself, is evidence of anything. No tool should ever paste
GLM's output into any phase's `VERIFIED_FACTS.md` or cite it as having
verified a project-specific claim.

Standing exception (`decisions.md`, 2026-07-06): qualitative/directional
findings (no tickers, no computed values) may be disclosed to GLM when
load-bearing for framing a question. This exception applies project-wide,
across every phase.

## 4. Work tiers

**Tier A — decision-gating.** The finding would change what that phase
actually does (a live parameter, a go/no-go on a pair or approach, a design
choice that's expensive to reverse). Full sequence below. Only the human
(Preet) decides a claim is Tier A, and only Preet decides a Tier B claim
gets promoted to Tier A later — no tool self-promotes its own finding.

**Tier B — working numbers.** Useful to keep building, not yet gating
anything. One computation (Codex or Antigravity/Gemini — cheaper model is
fine here), saved with a provenance header to
`<phase>/ledger/worklog/worklog_tier_b.md`. No adversary review, no dual
reproduction, no ledger entry.

**Tier C — pure engineering.** No statistical claim (GEMMA v2 endpoints, RL
env code, UI work). Normal branch → implement → Preet or Desktop Claude B
reviews → merge. Ledger never touched.

## 5. Tier A sequence (exact order matters)

0. **Identify the phase first.** Every step below operates on that phase's
   files only — `<phase>/VERIFIED_FACTS.md`, `<phase>/worklog.md`,
   `<phase>/ledger/worklog/`, `<phase>/open_questions.md`. Cross-phase
   citation (e.g. Phase II building on a Phase I admitted fact) is allowed
   and should be stated explicitly in the Spec Block, but each phase's own
   ledger only ever contains that phase's own admissions.
1. **Preet → Desktop Claude B.** State the question and its phase. B checks
   `<phase>/worklog.md` (index), the relevant Tier A claim worklog under
   `<phase>/ledger/worklog/`, and `<phase>/VERIFIED_FACTS.md` for prior
   attempts before producing a **Spec Block**: exact question, exact frozen
   snapshot ID to use, pre-declared tolerance for "the two computations
   agree," a claim_id (per-phase numbering — see §7). Tolerance is fixed
   here, before either computation runs.
2. **Preet → Claude #3.** Paste *only* the Spec Block. Adversary checks the
   spec itself (grid too sparse? tolerance vague? ambiguous method?) —
   pass/fail, not a computation. Fail → back to step 1.
3. **Preet → Codex.** Paste the approved Spec Block. Codex writes the
   script, runs it against the named frozen snapshot, saves script + output
   + a provenance header (script path, commit, data snapshot ID, output
   hash, timestamp) to the repo, under that phase's `analysis/` folder.
4. **Preet → Antigravity, switched to Opus.** Paste the same Spec Block —
   **verbatim, nothing from step 3.** Opus must not see Codex's approach or
   number before producing its own. Getting this order wrong breaks the
   independence the whole step exists for.
5. **Preet → Desktop Claude A.** Paste both candidates' file paths/hashes/
   values. A opens the actual files, checks hashes, checks the two values
   against the tolerance fixed in step 1 (not one it invents now). Admits
   to that phase's `VERIFIED_FACTS.md`, or logs DISPUTED in the appropriate
   Tier A claim worklog under `<phase>/ledger/worklog/` with the specific
   discrepancy, routed back to Preet.
6. **Only if about to be acted on:** Preet → Claude #3 again, paste the
   admitted claim + both scripts + both outputs, ask "any reason not to act
   on this."

## 6. Frozen data snapshots

Created by Codex, on Preet's explicit instruction only — never
auto-refreshed. Naming: `<ticker_pair>_v{N}_{YYYY-MM-DD}`, stored under
`/data/snapshots/` at the project root, immutable once created — and shared
across phases, not duplicated per phase. The naming convention already
disambiguates by ticker pair, so a phase reusing another phase's pair (e.g.
Phase II reusing Phase I's `tcs_infy_v1_2026-07-04`) references the same
snapshot file rather than creating a copy. Each snapshot ships with a
one-line note on adjustment policy (auto-adjusted close vs. raw + manual
corporate-action handling) — this is not cosmetic: retroactively restated
adjusted closes are a real, separate source of disagreement between two
"independent" reproductions that has nothing to do with either script being
wrong. Any Tier A spec must name which snapshot version it uses.

## 7. Ledger files

**Global, project root:**
- `decisions.md` — project decisions Preet has explicitly accepted, with
  reasoning and supporting claim_id or experiment. One file across all
  phases; entries name their phase where relevant.
- `process_notes.md` — cross-cutting tooling or process gaps that apply
  across phases and aren't yet resolved (so don't belong in `decisions.md`)
  and aren't specific to one phase's research (so don't belong in any
  phase's `open_questions.md`). Example: provenance stamping recording
  pre-commit HEAD instead of the commit that actually contains the output.

**Per phase, under `<phase>/`:**
- `VERIFIED_FACTS.md` — hand-edited **only** by Desktop Claude A, after both
  independent-reproduction checks pass, for claims belonging to that phase.
  A note at the top of the file itself states this; every other tool's
  prompt repeats it. If you're an agent reading this file and you're not
  the Ledger Keeper: don't write here.
- `worklog.md` — permanent index for that phase's worklog. Stays
  intentionally small, points to the appropriate Tier A claim worklog or
  the Tier B worklog.
- `open_questions.md` — that phase's current research questions, unanswered
  or generated by completed work. Cross-cutting tooling gaps go to
  `process_notes.md` instead, not here.
- `ledger/worklog/<claim_id>.md` — append-only worklog for a single Tier A
  claim in that phase.
- `ledger/worklog/worklog_tier_b.md` — chronological log of that phase's
  Tier B working questions and exploratory investigations.
- `PHASE_CONTEXT.md` — that phase's own investigation history and
  carry-forward status, in the same spirit as this file's old §8. Read
  before starting any work in that phase.
- `analysis/<claim_id>/`, `analysis/wq_*/` — that phase's implementation
  outputs.

**Claim numbering:** per-phase, not global. Each phase's claim IDs restart
at `claim_001` inside its own folder — Phase II's first claim is
`claim_001` under `phase_ii_rl_agent_tcs_infy/`, independent of Phase I's
`claim_001`–`claim_004`. See `decisions.md`, 2026-07-10.

**Entry format for a phase's `VERIFIED_FACTS.md`:**

  ```
  ## <claim_id>
  Claim: <plain statement>
  Value: <value, with tolerance stated>
  Codex: <script path> @ <commit> — output <path>, hash <hash>
  Antigravity/Opus: <script path> @ <commit> — output <path>, hash <hash>
  Snapshot: <snapshot id>
  Admitted: <date> by Desktop Claude A
  ```

## 8. Phase-specific carry-forward status

Moved out of this file — see each phase's own `PHASE_CONTEXT.md`. Phase I's
is at `phase_i_tcs_infy_pairs_trading/PHASE_CONTEXT.md` and carries the full
"stands but untested / verified / discard entirely" breakdown that used to
live here, unchanged in content (one list — already-duplicated open Tier A
questions — was deliberately not copied there; see that file's migration
note for why).

## 9. Language rules (all tools)

No "documented," "established," "decisive," or "confirmed" without a
citation to a `VERIFIED_FACTS.md` entry by claim_id **and phase**. A model's
own statement that it produced or verified something is not evidence —
provenance is a file path, a hash, and an independent reproduction, not a
claim.
