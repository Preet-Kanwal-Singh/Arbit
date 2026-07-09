# ARBIT / TCS-INFY Cointegration Track — Base Context

Load this into every tool's context before giving it a task: Claude Projects (as project
knowledge), Antigravity (paste at the start of a session), Codex (as AGENTS.md or
equivalent). If a per-tool prompt conflicts with this file, this file wins.

## 1. Why this process exists

The prior investigation (GLM sandboxes, rounds 1–7) produced four consecutive "decisive"
findings that were each retracted, and one foundational number
("Episode 1 beta range 0.20 to 1.91 across 22 months") whose origin became untraceable —
no script or data computation could be found backing it, in any sandbox. The root cause
was not any one tool being unreliable — it was (a) sandboxes that didn't persist across
sessions, and (b) a model's self-report about its own authorship or correctness being
treated as evidence. Every rule below exists to close one of those two gaps. Do not
re-add process on top of this without checking it's closing a gap that's actually
present — the last version of this system became too heavy and was deliberately cut back.

## 2. Tool roster and roles

| Role | Tool | Model | Filesystem access | Writes to ledger? |
|---|---|---|---|---|
| Builder | Codex | — | yes, local repo | no |
| Independent reproduction (Tier A only) | Antigravity | Opus — select manually | yes, local repo | no |
| Bulk engineering (Tier B/C) | Antigravity | Gemini 3.1 Pro (default) | yes, local repo | no |
| Ledger Keeper | Desktop Claude A (Project) | Claude | yes, filesystem MCP | **yes — sole writer** |
| Orchestrator / spec writer | Desktop Claude B (Project) | Claude | yes, filesystem MCP | no |
| Adversary | Claude #3 (Project, offshore) | Claude | **no filesystem access** | no |
| Generic literature/methodology only | GLM 5.2 | — | **no project access at all** | no |

Every tool above should know this full table exists, including the tools it never
directly interacts with. If you're unsure whether something is your job, it's
probably one of the other rows — check before doing it anyway.

## 3. GLM — hard boundary, read this even if GLM isn't the tool you are

GLM 5.2 is used **only** for content that stays generic even given in full: general
cointegration test theory, general AR(1)/near-unit-root bias-correction literature,
whether a cited paper exists and is on-topic, general pairs-trading risk-control
literature. GLM never receives: ticker names, actual computed values (phi, beta, FNR
numbers), file/variable names, or anything that would let a reader reconstruct what
this project has found. A generic-sounding question with a real number attached
("does FNR≈0.46 at phi=0.95 match theory") is **not** generic — the number itself is
the leak. GLM's own past sessions are also why this project restarted at all: it
gave two contradictory, equally confident self-reports about whether it had
originated a number ("I fabricated this" — later shown false; "this is mine and
documented" — also unverified). Nothing GLM says about this project, including about
itself, is evidence of anything. No tool should ever paste GLM's output into
`VERIFIED_FACTS.md` or cite it as having verified a project-specific claim.

Exception logged 2026-07-06: qualitative/directional findings (no tickers, no computed values) may be disclosed to GLM when load-bearing for framing a question. See decisions.md, 2026-07-06.

## 4. Work tiers

**Tier A — decision-gating.** The finding would change what ARBIT actually does
(a live parameter, a go/no-go on a pair, a design choice that's expensive to reverse).
Full sequence below. Only the human (Preet) decides a claim is Tier A, and only Preet
decides a Tier B claim gets promoted to Tier A later — no tool self-promotes its own
finding.

**Tier B — working numbers.** Useful to keep building, not yet gating anything.
One computation (Codex or Antigravity/Gemini — cheaper model is fine here), saved
with a provenance header to `ledger/worklog/worklog_tier_b.md`. 
No adversary review, no dual reproduction, no ledger entry.

**Tier C — pure engineering.** No statistical claim (GEMMA v2 endpoints, RL env
code, UI work). Normal branch → implement → Preet or Desktop Claude B reviews →
merge. Ledger never touched.

## 5. Tier A sequence (exact order matters)

1. **Preet → Desktop Claude B.** State the question. B checks `ledger/worklog.md` (index), 
   the relevant Tier A claim worklog under
   `ledger/worklog/`, and `VERIFIED_FACTS.md` for prior attempts before producing a
   **Spec Block**:
   exact question, exact frozen snapshot ID to use, pre-declared tolerance for
   "the two computations agree," a claim_id. Tolerance is fixed here, before either
   computation runs.
2. **Preet → Claude #3.** Paste *only* the Spec Block. Adversary checks the spec
   itself (grid too sparse? tolerance vague? ambiguous method?) — pass/fail, not a
   computation. Fail → back to step 1.
3. **Preet → Codex.** Paste the approved Spec Block. Codex writes the script, runs
   it against the named frozen snapshot, saves script + output + a provenance
   header (script path, commit, data snapshot ID, output hash, timestamp) to the repo.
4. **Preet → Antigravity, switched to Opus.** Paste the same Spec Block —
   **verbatim, nothing from step 3.** Opus must not see Codex's approach or number
   before producing its own. Getting this order wrong breaks the independence the
   whole step exists for.
5. **Preet → Desktop Claude A.** Paste both candidates' file paths/hashes/values.
   A opens the actual files, checks hashes, checks the two values against the
   tolerance fixed in step 1 (not one it invents now). Admits to
   `VERIFIED_FACTS.md`, or logs DISPUTED in the appropriate Tier A claim worklog under
   `ledger/worklog/` with the specific discrepancy, routed back to Preet.
6. **Only if about to be acted on:** Preet → Claude #3 again, paste the admitted
   claim + both scripts + both outputs, ask "any reason not to act on this."

## 6. Frozen data snapshot

Created by Codex, on Preet's explicit instruction only — never auto-refreshed.
Naming: `tcs_infy_v{N}_{YYYY-MM-DD}`, stored under `/data/snapshots/`, immutable once
created. Each snapshot ships with a one-line note on adjustment policy (auto-adjusted
close vs. raw + manual corporate-action handling) — this is not cosmetic:
retroactively restated adjusted closes are a real, separate source of disagreement
between two "independent" reproductions that has nothing to do with either script
being wrong. Any Tier A spec must name which snapshot version it uses.

## 7. Ledger files

- `VERIFIED_FACTS.md` — hand-edited **only** by Desktop Claude A, after both
  independent-reproduction checks pass. A note at the top of the file itself
  states this; every other tool's prompt repeats it. If you're an agent reading
  this file and you're not the Ledger Keeper: don't write here.

- `ledger/worklog.md` — permanent index for the worklog. This file remains
  intentionally small and points to the appropriate Tier A claim worklog or the
  Tier B worklog.

- `ledger/worklog/<claim_id>.md` — append-only worklog for a single Tier A claim.
  Contains claim history, updates, disputes, process notes, and final resolution.

- `ledger/worklog/worklog_tier_b.md` — chronological log of all Tier B working
  questions and exploratory investigations.

- Entry format for `VERIFIED_FACTS.md`:

  ```
  ## <claim_id>
  Claim: <plain statement>
  Value: <value, with tolerance stated>
  Codex: <script path> @ <commit> — output <path>, hash <hash>
  Antigravity/Opus: <script path> @ <commit> — output <path>, hash <hash>
  Snapshot: <snapshot id>
  Admitted: <date> by Desktop Claude A
  ```

## 8. Carry-forward status — do not re-litigate, do not re-trust

**Stands, not yet adversarially tested (test before leaning on further):**
- Episode 1 is the only long healthy trading episode for TCS/INFY.
- Three instability windows: Feb–Mar 2020, Sep–Oct 2020, Aug–Sep 2021.
- Aug–Sep 2021 as genuine early-warning signal (pre/post residual ratio 4.46×) —
  predates the retracted thread, not itself challenged.
- Phi regime-dependence (pre-COVID ~0.95, post-COVID ~0.99) — called "load-bearing"
  by the prior investigation but **never itself adversarially tested.** Treat with
  the same suspicion as everything that got retracted, not as safe by default.

**Verified (Tier 1 from prior handoff, safe to reuse as-is):**
- The two cointegration-pipeline bugs (wrong ADF critical values; `regression="c"`
  instead of `"n"`) — confirmed by reading `statsmodels.coint()` source directly.
- TCS/INFY healthy-episode half-life ~10–20 days (phi ≈ 0.93–0.97).
- Kalman filter for beta tracking — ruled out, don't revisit without a different
  filter formulation.
- Pesavento (2004) — confirmed real and on-topic via independent search; better
  fit than Hjalmarsson-Österholm (2007), which is a different test variant.

**Discard entirely, recompute from raw data before using for anything:**
- "Episode 1 beta swings 0.20 to 1.91 across 22 months" — untraceable, origin
  unconfirmed even after tracing to a prior sandbox.
- Any specific FNR number from the retracted rounds (0.206, 0.340, 0.386,
  0.946→0.000), and the phi_β=0.998 / phi_β=0.086 point estimates.
- The beta-drift degradation curve and the phi-estimator SE/CI table from the
  authorship-uncertain sessions — recompute with logging, and this time add the
  bias check that was flagged but never done (OLS phi is known to be biased
  downward near the unit root).

**Open Tier A questions to work through first, in roughly this order:**
1. Recompute Episode 1's real beta range from the frozen snapshot, with full
   provenance.
2. Real phi_β for the TCS/INFY beta process (best prior candidate: 15-day-sampled
   phi≈0.77, CI [0.66, 0.87] — untested in the actual FNR grid, don't treat as
   confirmed either).
3. Where does FNR vs. phi_β actually threshold between 0.90 and 0.98 — untested
   range, use a dense grid, not two points.
4. Adversarially test the phi regime-dependence finding (item above) — nobody has
   tried to break it yet.
5. Was "excise the instability window" ever actually tested against global
   re-fitting, or did the investigation narrow to Option B without that
   comparison being run?

## 9. Language rules (all tools)

No "documented," "established," "decisive," or "confirmed" without a citation to a
`VERIFIED_FACTS.md` entry by claim_id. A model's own statement that it produced or
verified something is not evidence — provenance is a file path, a hash, and an
independent reproduction, not a claim.
