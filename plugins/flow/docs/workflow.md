# Flow Workflow

How features get built and shipped under flow's managed-autonomy loop. **Project-agnostic** — same loop, same primitives, same discipline across any project that installs the plugin. Project-specific values (preflight commands, doc locations, default branch, etc.) come from `flow.config.json`; flow's defaults assume a typical project layout but never silently no-op when a slot is missing.

This is the long-form narrative. Each invoked skill carries its own short-form instructions; this doc is the reference for *why* the loop has the shape it has and *how* the gates compose.

## Shipped surface (flow v1.7.0)

Everything described in the loop below is shipped and installable today. The full user-visible surface:

- **`/flow:ship`** / **`/flow:ship-spike`** — final-pass pipeline (security + a11y + verify-build reviews) → feedback synthesis → doc updates → commit → push → open PR. Never merges.
- **`/flow:staff-review`** — four-lens parallel review (engineer / UX-designer / design-engineer / push-further).
- **`/flow:security-review`** / **`/flow:accessibility-review`** / **`/flow:verify-build`** / **`/flow:audit-coverage`** — the four final-pass reviewers, each also invocable standalone. (`/flow:audit-coverage` flags diff behavior no declared `**Spec-walk:**` criterion covers — the under-declaration complement to verify-build.)
- **`/flow:critique-plan`** — plan-critic pass over the most recent plan (scope drift, spec violation, internal incoherence).
- **`/flow:audit-plan`** / **`/flow:audit-completion`** — auditor passes (unverified assumptions + recall; false-verification proxies).
- **`/flow:log-disagreement`** — auto-invoked feedback channel that captures user pushback on a finding for prompt-tuning input.
- **`/flow:workflow-help`** / **`/flow:doctor`** — onboarding (print the loop + resolved config) and setup verification.

Plus the two reviewer subagents (`auditor`, `plan-critic`) and the four staff-review lens agents, the `planner` and `docs` context-isolation agents, the portable rules (`general`, `plan-discipline`, `documentation`, `exploration`), the memory machinery (`tools/memory/check.mjs`), the `flow.config.json` JSON Schema (22 slots), default hooks, and the template directory (`template/base/` + per-stack overlays). `/simplify` is bundled with Claude Code — flow does **not** wrap it.

## What this workflow is (and isn't)

This is **hybrid managed autonomy**, not pure autonomous coding. The human stays in the loop at two load-bearing gates: (1) **Plan approval** before any code is written, and (2) **Merge** at the end. Between those, the agent operates with autonomy-friendly primitives — spec-walk checkboxes, confidence verdicts, preflight gates, `/simplify`, four-lens `/flow:staff-review` (engineer / UX designer / design engineer / push-further), agent self-feedback memory.

Confidence gates explicitly add a third gate when an assumption is LOW — surfacing a question that must be resolved before the plan can proceed. The implicit gate at Execute time (new scope discovered → re-plan → re-approve) is currently judgment-based, not enforced; extending the confidence-gate primitive into Execute and into `/flow:staff-review` BLOCKER triage is a roadmap item.

The doctrine is: **more human gates than pure autonomous, fewer than fully manual.** The agent does the work it can do well; the human stays in the loop where the cost of being wrong is high.

---

## The unified loop

The user's request kicks the loop off (input, not a Claude step). From there:

```
 1. Clarify          read source-of-truth docs; surface conflicts; ask 2–4
                     targeted questions (or list assumptions if autonomous)
 2. Plan             write a plan with spec-walk checkboxes + confidence
                     verdict; run /flow:critique-plan; WAIT for human gate
 3. Execute          implement against the checkboxes; stay in scope
 4. Preflight        mechanical gates (typecheck/build/test + project
                     invariants) — MUST be green before /simplify runs
 5. Commit           explain "why" not what; co-author trailer; per-phase
 6. /simplify        (bundled with Claude Code) cold-read for reuse,
                     clarity, efficiency; fix in-tree; re-run preflight;
                     commit
 7. /flow:staff-review  four lenses in parallel (engineer / UX
                     designer / design engineer / push-further); fix
                     BLOCKER + cheap NIT in-tree; FOLLOW-UP → roadmap /
                     plan; EXPLORATION → roadmap.md § Exploration; commit
 8. Present          CONDITIONAL GATE: auto-advance into /flow:ship when the
        (gate)       ship-readiness predicate holds + FB-0011 risk gate clear;
                     else stop, present reviewer notes + dev URL + branch state
                     (NO PR yet) + why it stopped, flag MEDIUM assumptions
 9. Iterate          apply user feedback (sub-loop of 1–7)
10. /flow:ship       security + a11y + verify-build final pass → feedback synthesis
                     → doc updates → commit → push → open PR
11. STOP             the user merges; Claude never does
```

**Spike mode** (`mode: spike` in the plan): a cheap escape hatch for throwaway exploratory PRs. Skips steps 6 and 7; replaces step 10 with `/flow:ship-spike`. See § "Spike mode" below.

**Tiny mode** (`mode: tiny` in the plan): a 1–3 line bug fix the user explicitly asked you to "just do." Skips spec-walk + confidence verdict + steps 6 and 7; preflight still runs. `/flow:ship` for tiny mode skips synthesis (step 3 of the ship pipeline) and goes straight to commit + push + PR — feedback synthesis is overhead a 1-line fix doesn't earn. Rarely the right call; bias toward the full loop.

### A note on bundled-vs-flow skills

Claude Code bundles several native skills out of the box. Flow does **not** wrap any of them — wrapping bundled skills adds weight without value (the wrapper either parrots Anthropic's maintenance or drifts from it). The bundled skills referenced in this loop:

- `/simplify` — bundled with Claude Code.
- `/batch` — bundled with Claude Code.
- `/debug` — bundled with Claude Code.
- `/loop` — bundled with Claude Code.
- `/claude-api` — bundled with Claude Code.

When this doc references one of those by name, treat it as the native bundled skill. Everything else with a `/flow:` prefix is flow-provided.

### Flow's own audit/critique skills

`/flow:audit-plan`, `/flow:audit-completion`, `/flow:critique-plan`, and `/flow:log-disagreement` are **flow-internal** (bundled into flow v1.0.0), not an external `assumption-auditor` plugin. Prior versions of flow's lineage shipped them as a separate plugin; v1.0.0 absorbs them because they're used together with the workflow skills 100% of the time and separation imposes install friction without compositional value.

---

## Request (input)

User states a feature, change, or fix. May be one line, may be a paragraph. The request is the input that starts the loop; the numbered steps below are Claude's actions.

## 1. Clarify

Before asking anything, **read the source-of-truth docs that govern the change**. The default paths assume `core-docs/*.md` at repo root; override via the corresponding `flow.config.json.*Path` slots if your project keeps them elsewhere:

- `flow.config.json.specPath` (default `core-docs/spec.md`) — feature scope and decisions.
- `flow.config.json.planPath` (default `core-docs/plan.md`) — current focus + handoff notes.
- `flow.config.json.feedbackPath` (default `core-docs/feedback.md`) — synthesized user preferences and corrections.
- Project-specific design or domain docs — for UI projects, `design-language.md` is the common convention (visual and interaction rules).
- Any doc the user explicitly pointed to in the request.
- The directly-related code (one or two files; don't pre-implement).

Then:

- **Synchronous mode** (user present): ask **2–4 focused questions** to fill in gaps. Don't ask twenty. Surface conflicts ("the spec says X, you're asking for Y — which wins?").
- **Autonomous mode** (no user present at planning): replace questions with **explicit assumption list** in the plan. Each load-bearing assumption gets a confidence rating (see § "Confidence gates").

The goal: leave step 1 with enough shared understanding to plan without ambiguity.

## 2. Plan

Write the plan to the configured plan doc under "Active Work Items". The plan **must include**:

### Required fields

- **Mode** — one of `feature` (default, full loop), `spike` (exploratory), `tiny` (1–3 line fix).
- **Goal** — 1–3 sentences in user terms.
- **Scope (in)** / **Scope (out)** — what's deliberately not happening.
- **Spec-walk checkboxes** — every numbered/bulleted requirement from the spec or user request becomes a checkbox. For each: name the user-perceptible behavior, and decide what test or verification step pins it. Test-first for spec contracts. If you find yourself implementing from memory, walk back to the source.
- **Confidence verdict per load-bearing assumption** — see § "Confidence gates" below.
- **Risks / open questions** — failure modes, files at risk, tradeoffs being made.
- **Files touched** — anticipated paths.
- **Visual-walk** *(UI changes only — gated on `flow.config.json.uiSurface` AND the diff actually touching UI; N/A under spike/tiny)* — declared visual/UX acceptance criteria, parallel to Spec-walk: each a checkable assertion naming a user-perceptible visual state and how it's checked. Cover static state, token/motion, AND interaction/a11y, not just the happy-path look (e.g. "empty/loading/error state renders correctly"; "primary button uses the accent token, not a hardcoded hex"; "enter motion ≤ 200ms"; "opening the dialog moves focus into it and Esc closes it"; "the submit control shows a loading state and is disabled while the request is in flight"), written against the design-language doc (`flow.config.json.designLanguagePath`). These are the **declared visual criteria** the agent dials in against at Step 8/9 and the human signs off on at the merge gate. Declaration only today — mechanical verification is a later link in the Deliverable-quality roadmap track.

### After drafting, run `/flow:critique-plan`

**Run on EVERY plan — including docs-only ones.** The dogfood lesson from md-manager PR 4 (`dev-docs/feedback.md` FB-0008 + FB-0033-style cross-repo discipline): skips compound. A docs-only PR's missing `/critique-plan` step is what surfaced the stale-base BLOCKER class. Diff-size is not a legitimate skip reason.

The plan-critic reviews the plan against the user's request and the reference docs (`flow.config.json.referenceGlob`, default `core-docs/*.md`), returning either `APPROVED` or a `CRITIQUE SUMMARY` with BLOCKER / REDIRECT / FOLLOW-UP findings.

- **BLOCKER** — fix in-plan before showing it to the user.
- **REDIRECT** — surface to the user as part of the approval conversation.
- **FOLLOW-UP** — capture to the plan or roadmap doc, do not block.

`/flow:critique-plan` is advisory; the workflow's actual enforcement is the human gate below.

### Human gate

**User approves, redirects, or asks for revision. Claude does not start executing until the plan is approved.**

The critic informs the user's decision; it does not replace the human gate. **LOW-confidence plans cannot proceed until the assumption is resolved by an explicit user answer** — see § "Confidence gates".

## 3. Execute

Implement the approved plan against the spec-walk checkboxes. During execution:

- **Check off each checkbox as the code that satisfies it lands** alongside the test/verification that pins it. If a requirement is silently dropped, that's a workflow violation.
- Stay in scope. New scope discovered mid-execution gets **surfaced**, not silently absorbed. Update the plan (with confidence verdict for the new assumption), get approval, then continue.
- Read the feedback doc and any project-specific design/domain doc before touching their respective surfaces.
- Read safety-critical files' recent git log before modifying them (project's safety rule typically lives at `.claude/rules/safety.md`).
- Use project design tokens, not hardcoded values, for any UI work.

## 4. Preflight

**Mechanical gates that MUST be green before /simplify runs.** Sub-second to seconds. Resolved via `flow.config.json.preflightCmd` (project-specific). The flow plugin does not bundle a preflight runner — projects wire their own typecheck/build/test/invariants into a script (`tools/preflight/check.mjs` is the common name) and reference it from the config. Per-stack starter scripts (web / swift / tauri-rust-ts) ship in the template directory (`template/stacks/`).

**Why preflight has its own step.** Without it, `/simplify` and `/flow:staff-review` waste their judgment budget on mechanical issues a script catches in milliseconds. The preflight check fails fast, locally, before any reviewer-agent runs. If preflight is red, the loop pauses here.

**Failure-pattern memory** is the agent's running record of "things I've gotten wrong before." Memory entries (`~/.claude/projects/.../memory/feedback_*.md`) load automatically across sessions. They name patterns that aren't yet mechanically checkable. New entries are written at `/flow:ship` step 3 (see § "Continuous improvement"). Patterns that fire repeatedly graduate to preflight checks — that's the **promotion path** that keeps the loop closing.

**Consistency sweep** (FB-0010 discipline). If the diff changed a count, name, slot, version, or default path that's referenced elsewhere, grep the codebase for survivors of the OLD value before continuing. The diff is self-consistent by definition; fan-out contradictions live in unchanged files. `git grep -nE '<old-value>'` before `/simplify` catches this cheaply; the alternative is adversarial-review-pass-2 spotting the survivors in PR review. Same discipline applies to silent-skip patterns: every `2>/dev/null || true` / unset-var-fallback / `// empty` in shipped code should either log a `[WARN]` branch or fail-fast at the entrypoint — never flow into a downstream operation as-if-set.

## 5. Commit

Commit the implementation with a message explaining **why**, not what. Subject under 70 chars; body if the why takes more than a line. Co-author trailer:

```
Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```

If safety-critical code changed, include `SAFETY` in the subject.

**Commit at every phase boundary that produced changes** (Execute, /simplify, /flow:staff-review, /flow:ship). Deterministic rule, not judgment. Squash-merge on PR close keeps the default branch linear; intermediate commits live on the PR page indefinitely for review/recovery/blame.

## 6. /simplify (bundled with Claude Code)

**Run on EVERY diff — including docs-only ones.** Same cross-repo discipline as Step 2: skips compound. `/simplify` is cheap (single-pass cold-read); the cost of running it on a docs-only PR is seconds. The cost of NOT running it is the next PR re-discovering structural drift that one cold-read would have surfaced. Diff-size is not a legitimate skip reason.

Cold-read the changed code for **reuse, quality, and efficiency** and fix issues in-tree:

- Duplicated logic that could collapse into a helper.
- Functions doing two unrelated things; split them.
- Premature abstractions to delete (one caller, no second one coming).
- Dead code, unused imports, commented-out blocks.
- Mid-function early-returns hiding state machines that want their own function.
- Performance footguns matching known patterns (O(n²) where O(n) reads the same; useEffect deps misses that re-run heavy work).

**Why before staff-review.** If staff-review ran first, ~half its NITs would be "this is overcomplicated." `/simplify` removes that class of finding pre-emptively so the four-lens review focuses on architecture, correctness, craft, and push-further opportunities instead of bloat.

Re-run **Preflight** before committing the simplify fixes. Refactors are exactly where mechanical gates earn their keep.

## 7. /flow:staff-review

**Four** Explore agents review the diff in parallel from four lenses (engineer / UX designer / design engineer / push-further). The first three ask "is this good?"; the fourth asks "could this be pushed further?" — grounded in the project's design-language doc and Josh Puckett's "uncommon care" (executing limited scope to an extraordinarily high bar).

Findings triaged:

- **BLOCKER** — fix in-tree now. User-visible regression, crash, accessibility violation, broken build.
- **NIT** / **inline-cheap** — fix in-tree if cheap (single-file, no architectural change). (`inline-cheap` is the push-further lens's equivalent of NIT.)
- **FOLLOW-UP** / **roadmap-concrete** — capture to the roadmap or plan doc, **never only in the PR body.** Mention in PR body for reviewer awareness; the doc entry is canonical.
- **future-exploration** — open-ended direction without a clear shape yet. Routes to `roadmap.md § Exploration` with a `Surfaces when:` trigger naming the file paths / area that should re-surface the item later.

**Bias toward fixing small, defined issues.** Larger questions and deferred items go to roadmap/plan with rationale, not into review-comment limbo. **For FOLLOW-UPs, prefer doing over filing** — if it's small enough to land in the same PR without meaningfully expanding scope, just do it now. The push-further lens is permitted to return "Nothing to push — surface at ceiling for its scope" — empty is valid and often correct; false-positive "we could add X" findings are worse than no findings.

**Don't skip a lens** because a human gave a visual opinion or because another lens already ran. AI review and human opinion catch different things; the four lenses cover distinct surfaces. The only legitimate skip is when a lens genuinely doesn't apply (e.g., a backend-only change has nothing for the design-engineer or push-further lens) — in that case say so explicitly rather than running an empty review.

## 8. Present (conditional gate)

Step 8 is where the loop decides between two paths: **auto-advance into `/flow:ship`** (autonomous) or **stop and present** (human-in-the-loop). The decision is a predicate, not a vibe.

### Ship-readiness predicate

Auto-advance into `/flow:ship` **only when ALL hold**:

1. **Every spec-walk checkbox in the approved plan is checked** — the plan is fully satisfied, not partially.
2. **No open BLOCKER** from `/simplify` (Step 6) or `/flow:staff-review` (Step 7).
3. **No load-bearing assumption is unresolved at MEDIUM or LOW confidence** (see § "Confidence gates").
4. **A behavioral gate exists and returns PASS.** `/flow:verify-build` would return `overall_verdict: PASS` — a *positive* behavioral pass. **"verify-build didn't FAIL" is NOT sufficient, and skipped ≠ ready.** If verify-build is skipped (`verifyEnabled=false`, `platform=library|none`, or a doc-only diff) there is **no** behavioral gate, so the predicate is **not** satisfied — those changes stop and present, requiring an explicit "ship it". (This is FB-0018: the readiness signal must be a positive PASS, never absence-of-failure.)
5. **No unanswered `this-iteration` open question.** If verify-build's findings buffer carries an `open_questions[]` entry with `routing: this-iteration` that the human hasn't answered, the loop **stops and presents** it — it is a subjective/taste call only the human can make (distinct from an epistemic `Unknown`), and it mirrors an unresolved MEDIUM assumption. `future-planning` questions route to the roadmap and do NOT block. (V2: surfaced in the rendered walkthrough's "Open questions for you" block.)

**This step is the discovery boundary.** Behavioral *and visual* dialing-in happens HERE (steps 8–9), before the ship decision — running verify-build to know it would PASS, observing the app, iterating on visual gaps. `/flow:ship` only *confirms* (re-runs verify-build as a regression check); it must not be where you first find out whether the thing works or looks right. **Visual sign-off folds into the merge gate, not a third gate:** the agent dials in visual quality against the plan's declared visual criteria — its **`Visual-walk`** block (§ 2 "Required fields") — pre-PR; the *authoritative* human visual sign-off happens at the merge gate via the PR preview (ship Step 8 invokes the project's dev-server/preview skill if one exists). If the agent's visual confidence is low, that's a `[decision-required]` finding → draft PR + manifest, same routing as any unresolvable blocker. So "dialed in before ship" = the agent's best pass pre-PR; the human's authoritative look stays at merge — two gates preserved.

### Risk gate (FB-0011)

Even when the predicate holds, **stop and present** if any of FB-0011's escalation triggers apply: the path forward is unclear, significant risk remains, competing options of comparable merit exist, or the decision is one-way-door. Default to ESCALATE when in doubt — a false stop costs the user a moment of attention; a false auto-advance can open a PR built on a wrong call. (`/flow:ship` never merges, so the cost is bounded — but the merge gate is not a license to auto-advance carelessly.)

### Auto-advance path

When the predicate holds and the risk gate is clear, Claude invokes `/flow:ship` directly (Step 10) without waiting for "ship it". This is the autonomous-loop trigger — the loop runs unattended between the two load-bearing human gates (plan approval at Step 2, merge at Step 11). `/flow:ship`'s own mechanical gates (stale-base, Step 1c preflight, Step 2 verify-build confirmation) remain the safety net: a falsely-confident auto-advance produces a regression at ship's verify-build confirmation, which routes to a **draft PR + manifest** rather than a merge-ready PR — caught before the merge gate, never silently shipped.

### Stop-and-present path

When the predicate fails or the risk gate trips, Claude returns:
- Reviewer notes (findings, what was fixed, what was deferred and where).
- The dev server URL — flow does not bundle a dev-server skill; invoke your project's equivalent (e.g., a `/link`-style skill) if one exists.
- The branch and commit state. **No PR exists yet** — that's `/flow:ship`'s job.
- **Why it stopped** — which predicate condition failed, or which FB-0011 trigger applied. **Any MEDIUM-confidence assumptions that turned out to be load-bearing** surface here (the step-8 redirect window) so the user can redirect before `/flow:ship` locks the PR.

The user then redirects, resolves the open item, or says "ship it" to proceed.

**Never merged, either path.** The whole point is the human hand-off at merge.

## 9. Iterate

User responds with feedback. Claude addresses it — code changes, doc updates, more review if scope changed materially. Each iteration is a normal request → clarify → plan → execute sub-loop. New scope = new plan (or amended plan with fresh confidence verdict).

## 10. /flow:ship

Claude **auto-advances here from Step 8** when the ship-readiness predicate holds and the FB-0011 risk gate is clear (see § "8. Present (conditional gate)"), **or** the user says "ship it" (or `/flow:ship`). Either way, Claude runs the ship pipeline (full spec: `plugins/flow/skills/ship/SKILL.md`):

1. Final-pass reviews in sequence: `/flow:security-review` + `/flow:accessibility-review` + `/flow:verify-build` + `/flow:audit-coverage`. Each self-detects skip conditions (security: doc-only; a11y: `uiSurface=false` or non-UI diff; verify-build: `verifyEnabled=false` or `platform=library|none`; audit-coverage: doc/test/refactor-only diff or no `**Spec-walk:**` block — runs on all platforms). Verify-build here is a **confirmation re-run** — behavioral *discovery* already happened at the Step 8/9 readiness boundary; ship re-runs it to catch a regression since readiness. **Audit-coverage** flags behavior in the diff that no declared criterion covers (the under-declaration complement: verify-build checks the declared criteria *pass*; audit-coverage checks the declared set is *complete*) — an uncovered behavior is a `[decision-required]` finding routed to the draft manifest (the resolution is to declare the criterion + let verify-build verify it, or the human waives; never auto-add the criterion). It is best-effort LLM judgment, so it routes to draft, never a hard halt. Every finding resolves to one of three outcomes, **never a silent proceed and never a hard mid-loop halt**: `[auto-fixable]` BLOCKER + cheap NIT → fixed in-tree; `[decision-required]` BLOCKER (security/a11y tag this axis) or a non-converging verify-build regression → added to the **draft manifest** so the PR opens as a draft + `🚫 NOT READY TO MERGE` block (the human resolves it at the merge gate); FOLLOW-UP → plan/roadmap. A verify-build regression first gets the FB-0012 bounded mechanical fix (loop only on the exit code, never judge prose); only a non-converging one routes to draft. **Invariant: no merge-ready PR is ever produced on a non-PASS build.**
2. Apply blocker / cheap-nit fixes; re-run Preflight (`flow.config.json.typecheckCmd`) if code changed. Loud warning if the slot is unset.
3. **Synthesize session feedback (two layers)**:
   - **User feedback** — review the conversation since the last PR for corrections, preferences, decisions, and solved challenges. New entries go in `flow.config.json.feedbackPath`.
   - **Agent self-feedback (pattern capture)** — review the session for recurring failure patterns and write memory entries per the source-diversity bar (§ "Continuous improvement").
4. **Update project docs** (paths via config slots: `historyPath`, `planPath`, `roadmapPath`, `specPath`). This includes **doc-currency reconciliation** (ship Step 5a): the forward-looking roadmap "Now" + plan "Current Focus" are refreshed to the current version + ▶ next-up, shipped items swept to Recently-Completed, and shipped FB reservations cleared — then an **automatic mechanical gate** (ship Step 5b) blocks the ship if those docs don't reference the current version. Currency is enforced *in the pipeline*, not via manual `/flow:doctor` (which carries only a secondary mirror, Check 2.6). Stale direction docs are the FB-0010 fan-out class applied to *what to work on* — a cold reader (incl. the autonomous loop) relies on them.
5. Commit doc updates.
6. Push and open the PR with base branch via fallback chain (`git symbolic-ref` → `flow.config.json.defaultBranch` → literal `main`).
7. Output the PR URL.

**Still never merged.** The user merges.

### The PR body documents the full flow run

The PR body has three sections: `## Summary`, `## Test plan`, and `## Flow run`. The **`## Test plan` is rendered mechanically from the `/flow:verify-build` findings buffer** (`/flow:ship` Step 7 runs `skills/ship/lib/render-test-plan.py`) — *not* hand-authored: it opens with a one-line headline verdict (`✅ N/N declared criteria passed — confirm and merge`, or `⚠️ M/N passed; K unresolved`) so the merge decision is a glance, then one line per criterion whose checkbox state is its machine `aggregated_verdict` (PASS → `[x]`; FAIL/Unknown → `[ ]` + the judge's reason) with the buffer's evidence, then the `not_tested[]` residue as plain bullets (never checkboxes — a `[ ]` only ever means an unverified criterion). The human confirms-and-merges instead of re-verifying. The agent cannot show a criterion green without a real PASS from an adversarial fresh-context judge — that is the enforcement that lets the merge gate trust the section. When verify-build skipped, produced no buffer, or the buffer is stale (branch/sha ≠ current HEAD), the renderer emits an honest `⚠️ no behavioral gate ran (<reason>); manual verification required` fallback rather than a forged green or a stale render (so e.g. a `platform: library` repo — including flow's own — always takes the fallback). The `## Flow run` table is the loop's self-documentation — one row per loop step (Clarify → Plan+critique → Execute → Preflight → /simplify → /flow:staff-review → security/a11y/verify-build → Doc synthesis), each marked `✓` (ran) or `skipped (<reason>)`, with a **Notable** cell carrying genuine signal (a plan-critic catch that changed the plan, a load-bearing decision, a fixed BLOCKER, a real review finding) or `—` when routine. The ship agent fills it from the session's loop history; it is instructed **not to manufacture notes** — an honest `—` beats invented filler. Skips are mode- and config-dependent and the reason is always named, so a reader can tell a legitimate skip from a missed step (the canonical per-step skip-reason list lives in `/flow:ship` §7). The table only *points at* deferred follow-ups — those stay canonical in the roadmap/plan docs (it never becomes their home; see Step 7 + the anti-pattern below). `/flow:ship-spike` writes a trimmed version of the same table (fewer rows; /simplify + /flow:staff-review pre-marked `skipped (spike)`).

A filled `## Flow run` for a docs-only change on a library project (no UI surface, no runnable target) looks like:

| Step | Status | Notable |
|---|---|---|
| Clarify | ✓ | — |
| Plan + /flow:critique-plan | ✓ | critic flagged a stale spec cross-ref; fixed in-plan |
| Execute | ✓ | — |
| Preflight | ✓ | green |
| /simplify | ✓ | collapsed two near-duplicate helper sections |
| /flow:staff-review | ✓ | 1 NIT fixed inline; 1 FOLLOW-UP → roadmap |
| /flow:security-review | skipped (doc-only) | — |
| /flow:accessibility-review | skipped (uiSurface:false) | — |
| /flow:verify-build | skipped (platform library) | — |
| /flow:audit-coverage | skipped (no behavior in diff) | — |
| Doc synthesis | ✓ | history + plan + CHANGELOG |

Note the bottom four rows: each names *why* it skipped, so the reader sees a legitimate config/mode skip rather than wondering whether a gate was missed.

### Never bypass `/flow:ship` with `gh pr create` directly (FB-0010 workflow-step sub-class)

`/flow:ship` is not just "the thing that opens the PR" — it's the orchestrator that spawns `/flow:security-review` + `/flow:accessibility-review` (Step 1 above), synthesizes feedback into both layers, updates the project docs, and only THEN opens the PR. Running `gh pr create` directly skips all of that.

Skipping doesn't feel like a skip in the moment — the diff still gets to GitHub, CI still runs, the PR still opens. What goes missing is the **explicit `STATUS: SKIPPED` log line** from the per-diff gates of security + a11y reviews — visible in the session transcript as evidence the discipline ran. Even on a docs-only PR where both would early-exit, running them via `/flow:ship` produces that log; skipping the spawn means there's no record of the decision either way. (Today the log is transcript-only; nothing programmatically consumes it. If a future doctor check or hook starts asserting on STATUS lines, that's the upgrade path — but the discipline of producing the log holds regardless.)

This is the FB-0010 silent-skip class applied to workflow discipline (not code). Surfaced first as a 1-incident finding during PR H1; encoded here so the next loop doesn't repeat it. The rule:

- **Always invoke `/flow:ship`** (or `/flow:ship-spike` for spike-mode PRs) at the end of the loop.
- **Never invoke `gh pr create` directly** — even when the PR feels "obviously ready."
- If `/flow:ship` errors at a pre-flight gate, fix the gate cause first; don't route around `/flow:ship`.

### Why the PR opens here, not earlier

The PR is **deliberately the last artifact created**, not the first:

1. **Single-reviewer workflow.** The PR isn't a team-collaboration surface; it's "the work is done, please merge." Opening it mid-pipeline would create a half-done state nobody benefits from.
2. **Doc synthesis is load-bearing and has to be last.** The history/plan/roadmap/spec/feedback docs only get written after every review has surfaced its findings. A PR opened before that would either lie about what's done or require repeated body edits. The canonical "what shipped" record lives in those committed docs — not the PR body — and that record has to exist before the PR opens.
3. **CI doesn't help earlier.** Local gates (Preflight) already cover what CI would tell us.

**When this calculus changes:** a second human reviewer joins, deploy previews land, or CI starts running checks the laptop can't. Until then, end-of-pipeline PR creation is correct.

### Why doc updates centralize at /flow:ship

The temptation is to update the history doc as soon as a decision is made. **Resist it.** Mid-feature doc updates produce fragmentary slices that have to be reconciled later anyway. `/flow:ship` synthesizes the full change once, coherently. Two carve-outs:

- **Mechanical contract artifacts update inline** — e.g., a `component-manifest.json`, a `generation-log.md`, a `pattern-log.md`. They're not narrative; they're tracked state.
- **`plan.md` "Active Work Items"** is allowed to update mid-feature for handoff/checkpoint purposes. The "Recently Completed" section is `/flow:ship`-owned.

## 11. STOP

Claude does not merge. Ever. `gh pr merge` is not a Claude action. The user merges.

---

## Spike mode (`/flow:ship-spike`)

A **spike** is a time-boxed exploratory PR whose goal is to *answer a question*, not to ship a feature. The output is a learning, captured as a history entry (or ADR). The prototype code is usually thrown away, or it gates a follow-up "real" PR.

### Triggering spike mode

In the plan, set:

```
**Mode:** spike
**Research question:** <the specific question this PR answers>
**Disposability:** <what happens to the code: deleted, kept behind a flag, gates next PR>
```

### What spike mode skips

| Step | Default loop | Spike mode |
|---|---|---|
| 1. Clarify | Full docs read + questions | Only docs directly relevant to the question |
| 2. Plan | Spec-walk + confidence verdict | Research question + minimal approach |
| 3. Execute | Polish-bar implementation | Smallest thing that answers the question |
| 4. Preflight | Required | Required (cheap, keep it) |
| 5. Commit | Required | Required |
| 6. /simplify | Required | **SKIPPED** — code is disposable |
| 7. /flow:staff-review | Required | **SKIPPED** — review craft on throwaway code is theater |
| 8. Present | Required (the deliverable is the answer) | Required (same — present the answer) |
| 9. Iterate | If user has feedback | If user has feedback |
| 10. /flow:ship | Full pipeline | Replaced by `/flow:ship-spike` |

### `/flow:ship-spike`

Lightweight terminal pipeline:

1. Write the history entry — the entry IS the deliverable. Must include: research question, what was built, what was learned, recommendation (proceed / pivot / abandon).
2. Commit doc + code.
3. Push.
4. Open PR with `spike` label. PR body must include the research question + the answer, plus a **trimmed `## Flow run` table** (fewer rows than `/flow:ship`; /simplify + /flow:staff-review pre-marked `skipped (spike)`). The user merges or closes — Claude does not.

### Spike-mode abuse prevention

Claude doesn't merge anything (spike or feature), so abuse-prevention is the user's call at PR review time. Two signals make abuse visible:

- The PR title must start with `spike:` and the PR carries a `spike` label.
- The PR body must answer the research question. If the body reads like a feature PR (no question, no answer, no recommendation), the user should redirect or close.

The deeper check is on Claude's side: if you're in spike mode and realize you're building a feature, **stop and rewrite the plan as `mode: feature`**. Don't smuggle features through spike mode — the heavy reviews exist for a reason.

---

## Confidence gates

Every plan must declare confidence per load-bearing assumption. The trigger for "load-bearing": **would I plan a different feature if this assumption flipped?**

### Three levels

| Level | Meaning | Effect on the loop |
|---|---|---|
| **HIGH** | The assumption is well-supported by docs, prior decisions, or unambiguous user direction. Proceed normally. | Plan can be approved; Execute proceeds on user OK. |
| **MEDIUM** | Reasonable assumption but a different choice was defensible. The plan works either way; the specific solution might not. | Plan can be approved; **an unresolved MEDIUM assumption blocks Step 8 auto-advance** — the loop stops and presents it for redirect rather than auto-invoking `/flow:ship` (see § "8. Present (conditional gate)"). |
| **LOW** | A load-bearing assumption could flip the entire approach. Examples: ambiguous user intent, unresolved spec, conflicting prior decisions, unknown user preference on a one-way-door choice. | **Automatic human gate. The plan cannot proceed.** Surface the question to the user in step 2 and wait for an explicit answer that resolves the assumption (which then becomes HIGH or MEDIUM). `/flow:critique-plan` should treat LOW-confidence plans as REDIRECT findings; the human gate is the actual enforcement. |

### How to write a confidence verdict

In the plan, for each load-bearing assumption:

```
**Assumption:** <what you're assuming>
**Confidence:** HIGH | MEDIUM | LOW
**Why:** <one line — what evidence supports the rating>
**If it flips:** <one line — what would change in the approach>
```

If "If it flips" answers "the entire approach," confidence is automatically LOW.

---

## Continuous improvement

The workflow has three compounding layers of feedback, each with its own home and its own bar. **The layers form a strict precedence hierarchy** — user feedback wins ties against agent memory; preflight wins ties against both because it's mechanically verifiable.

| Layer | Home | Captures | Bar to write |
|---|---|---|---|
| **User feedback** | `flow.config.json.feedbackPath` (default `core-docs/feedback.md`; FB-XXXX format) | "The user wants X" — preferences, scoping calls, corrections | A future session would benefit from the rule |
| **Agent self-feedback** | `~/.claude/projects/.../memory/feedback_<name>.md` (cross-session memory) | "I tend to do X wrong; watch for it" — recurring failure patterns | Source-diversity bar (see below) + not yet mechanically checkable |
| **Preflight check** (project-resident) | `flow.config.json.preflightCmd` (typically `tools/preflight/check.mjs`) | Mechanically verifiable patterns promoted from memory | The rule can be expressed as a deterministic check + user approved promotion |

The three layers are a **promotion pipeline**: user feedback shapes what gets built, agent memory shapes how it gets built, and patterns that fire repeatedly graduate from agent memory into preflight checks. Each promotion takes work off the next session's plate.

### Why agent memory needs guardrails

The risk: agent writes a memory entry → next session reads it → agent is primed to "find" the same pattern → confirmation reinforces the entry → memory shapes review behavior → next memory entry written from the shaped behavior. The compounding direction is the same as the model-collapse failure mode in synthetic-data training. The mechanism is different (prompt-level bias amplification, not weight-level drift) and the consequences are smaller (no gradient updates; user-in-loop on every PR; bounded corpus), but the direction is real.

The bigger novel risk is **process ossification**: memory entries accumulate as load-bearing rules, no one prunes them, the corpus becomes a thicket of half-true patterns the agent feels obligated to honor. Same failure mode as human-team coding standards; memory makes it worse because the entries feel authoritative when context-injected.

The five guardrails below are designed to make the asymmetry favor compounding rather than degradation.

### Agent self-feedback (memory)

Captured at `/flow:ship` step 3b. **All five guardrails apply.**

1. **Source-diversity bar** — evidence from at least **2 of 3** sources: recurrence in time, two reviewers, or one review + user-feedback rule. Single-source findings don't earn an entry.
2. **Mechanical-check beats memory** — if a preflight rule could catch it deterministically, write the preflight rule (or file as follow-up). Memory is for judgment-level patterns that resist mechanization.
3. **User feedback wins ties** — if memory contradicts a feedback rule, user feedback wins. Memory entry gets revised or archived.
4. **Hard cap (~30 entries)** — forces curation pressure rather than unbounded growth. (Tunable; the PR-2 `tools/memory/check.mjs` checks this.)
5. **Periodic audit (every 5 ship runs)** — fresh-context audit pass over the corpus to identify stale, contradicting, or over-fitted entries.

### Promotion path: memory → preflight (user-gated)

When a memory entry's "Fire log" reaches 2+ entries, the pattern is recurring despite the memory being there — that's the promotion signal. **Promotion is not automatic.** `/flow:ship` surfaces the candidate to the user as a follow-up entry in the roadmap doc ("Promote memory entry X to preflight check Y"). The user approves the promotion explicitly because preflight rules are permanent and shape every future PR — a bad rule catches false positives forever.

### Workflow infrastructure is living

If a `/flow:staff-review` or `/flow:ship` finding suggests a missing rule, write the rule. If a debate happened during a feature and one option won, log the decision. If a step becomes friction without value, prune it. If a missed pattern would have been caught by a tighter checklist, tighten it.

**The cost of evolving the framework is one PR; the cost of running on a stale framework is every PR after.** Treat infrastructure changes with the same rigor as feature work, but don't hesitate to propose them.

---

## Skills cheat sheet

Listed in loop order. **Invocation:** AUTO (self-fires) / MANUAL (you type it; carries `disable-model-invocation: true`) / BOTH (typed, or called by `/flow:ship` / a phrase-trigger on a diff).

| Skill | What it does | When | Invocation | Source |
|---|---|---|---|---|
| `/flow:workflow-help` | Print the loop + resolved config | Reference / onboarding | BOTH | flow |
| `/flow:doctor` | Setup PASS/FAIL/WARN punch-list | After bootstrap / when something feels off | BOTH | flow |
| `/flow:critique-plan` | Critique plan vs. core-docs (scope drift / spec violation / internal incoherence) | At the plan gate within a driven loop (never cold-start); also typeable | BOTH | flow |
| `/flow:audit-plan` | Audit plan for unverified assumptions and unverified recall | At the plan gate, complementary to `/flow:critique-plan` (never cold-start); also typeable | BOTH | flow |
| `/simplify` | Cold-read changed code for reuse, clarity, efficiency; fix in-tree | After commit, before staff-review | — | bundled (Claude Code) |
| `/flow:staff-review` | Four-lens parallel review (engineer / UX / design-engineer / push-further) | After `/simplify`, before presenting | BOTH | flow |
| `/flow:audit-completion` | Audit "done / fixed / ready" claims for false-verification proxies | At the present gate within a driven loop (never cold-start); also typeable | BOTH | flow |
| `/flow:ship` | Final-pass reviews (security + a11y + verify-build) + doc updates + commit + push + PR (no merge) | Auto-advances from Step 8 when the readiness predicate holds; else user says "ship it" | AUTO·when-ready | flow |
| `/flow:security-review` | Diff-focused security audit | Inside `/flow:ship`; also standalone | BOTH | flow |
| `/flow:accessibility-review` | Diff-focused WCAG 2.1 AA audit | Inside `/flow:ship`; also standalone | BOTH | flow |
| `/flow:verify-build` | Plan-driven behavioral verification: extract criteria from `**Spec-walk:**` checkboxes, adversarial transform, judge bundled `/verify`'s observations per dimension. Discovery at the Step 8/9 readiness boundary; a *confirmation* re-run inside ship (a regression routes to draft, not a hard halt) | Step 8/9 readiness + `/flow:ship` Step 2 confirm + `/flow:ship-spike` Step 2; also standalone mid-iterate | BOTH | flow |
| `/flow:audit-coverage` | Coverage auditor: flags diff behavior changes no declared `**Spec-walk:**` criterion covers (under-declaration). A gap → draft manifest (decision-required). Best-effort LLM judgment; runs all platforms; self-skips on doc/test/refactor-only diffs or no Spec-walk | Step 8/9 readiness + `/flow:ship` Step 2; also standalone | BOTH | flow |
| `/flow:ship-spike` | Lightweight ship for spike-mode PRs (also invokes `/flow:verify-build --spike` for a 3-check smoke gate) | At spike-loop end (auto-advance is **judgment-gated** — no mechanical predicate, unlike `/flow:ship`; never cold-start); also typeable | BOTH | flow |
| `/flow:log-disagreement` | Capture user pushback on a finding for prompt tuning | After a reviewer issues a finding the user disputes in plain language | AUTO | flow |
| project's `/link` (or equivalent) | Start the dev server, return URL | Whenever you need a live preview | — | project-specific (not flow) |

---

## Project config slots (narrative; full JSON Schema at `plugins/flow/schema/flow.config.schema.json`)

`flow.config.json` lives at your project repo root. All slots are optional; flow ships sensible defaults but never silently no-ops on an unset slot that would change behavior — see the loud-warning pattern in `/flow:ship`.

| Slot | Default | Used by |
|---|---|---|
| `defaultBranch` | falls back to `git symbolic-ref refs/remotes/origin/HEAD`, then literal `main` | `/flow:ship` (NOTHING-TO-SHIP check, PR base) |
| `typecheckCmd` | unset → loud warning, never silent | `/flow:ship` (post-fix re-check) |
| `preflightCmd` | unset → consumer must wire (project-shaped); typical convention `node tools/preflight/check.mjs` | preflight step 4 |
| `historyPath` | `core-docs/history.md` (consumers) / `dev-docs/history.md` (flow's own repo) | `/flow:ship` step 4 |
| `planPath` | `core-docs/plan.md` (consumers) / `dev-docs/plan.md` (flow's own repo) | clarify, plan, `/flow:ship` steps 2 + 4 |
| `roadmapPath` | `core-docs/roadmap.md` (consumers) / `dev-docs/roadmap.md` (flow's own repo) | `/flow:ship` steps 2 + 4; `/flow:staff-review` follow-ups |
| `specPath` | `core-docs/spec.md` (consumers) / `dev-docs/spec.md` (flow's own repo) | clarify, `/flow:ship` step 4 |
| `feedbackPath` | `core-docs/feedback.md` (consumers) / `dev-docs/feedback.md` (flow's own repo) | clarify, `/flow:ship` step 3a |
| `referenceGlob` | `core-docs/*.md` | `/flow:critique-plan` preprocessor |
| `verifyEnabled` | `true` | `/flow:verify-build` skip-path (project-wide opt-out) |
| `verifyFindingsPath` | `/tmp/flow-verify-findings.json` | `/flow:verify-build` step 8 write; `/flow:ship` step 4a read |
| `verifyBudgetCalls` | `60` | `/flow:verify-build` step 5 (tool-call cap before forced Unknown) |

Why two defaults: flow's *own* dev-tracking lives at `dev-docs/` (so `core-docs/` stays free as the name consumer-template scaffolding ships at). Consumer projects typically use `core-docs/`. The defaults bake that distinction in.

**`/flow:verify-build` prerequisite:** `/flow:verify-build` wraps bundled `/verify`, which in turn invokes bundled `/run`. `/run` works best with a per-project launch recipe scaffolded by Anthropic's bundled `/run-skill-generator` at `.claude/skills/run-<name>/`. Without that recipe, heuristic launch may fail on projects with env files, databases, multi-step builds, or non-standard scheme/package selection (Anthropic's docs explicitly call out this limitation). After installing flow, run `/run-skill-generator` once per project; `/flow:doctor` Check 5.3 surfaces the gap if you skip it.

---

## Anti-patterns

- **Implementing without an approved plan.** Even if the change feels small, write the plan; it takes 60 seconds and prevents 60 minutes of rework.
- **Approving a LOW-confidence plan.** The gate exists because the assumption is load-bearing. Resolve it, don't bypass it.
- **Smuggling features through spike mode.** If the deliverable is a feature, not an answer, it's a feature PR.
- **Updating the history or feedback doc mid-feature.** Let `/flow:ship` synthesize at the end.
- **Putting follow-ups only in the PR body.** They get lost when the PR merges. Roadmap or plan is canonical.
- **Merging.** Claude doesn't merge. Ever.
- **Skipping Preflight before /simplify.** `/simplify` is judgment work; preflight is mechanical. Don't waste the former on the latter.
- **Asking 12 questions in step 1 (Clarify).** Ask 2–4 high-leverage ones, or list assumptions with confidence.
- **Wrapping a bundled Claude Code skill in a `/flow:` namespace.** `/simplify`, `/batch`, `/debug`, `/loop`, `/claude-api` are native. Use them as-is.
