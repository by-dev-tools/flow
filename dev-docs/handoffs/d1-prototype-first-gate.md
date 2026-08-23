# D1 — Prototype-first gate: move the human's first gate from the plan to the prototype

**Mode:** feature (large; restructures the front half of the loop) | **Priority:** high (the load-bearing item of the Designer-signal track) | **Horizon:** now-ish, user-directed 2026-08-17
**Branch:** _(fresh — none yet)_
**Status:** 🟢 **PLAN — not started.** Design is settled (FB-0081 is the definitive spec, user-directed); this doc is the execution layer. Nothing implemented.
**Scope:** the front half of the flow loop (Clarify → Plan) for **UI-surface changes**. Does **not** touch the merge gate or `/flow:verify-build`.
**Source of truth (read these, do not re-derive):** `dev-docs/feedback.md` **FB-0081** (the shape + every ordering decision, verbatim user direction), **FB-0080** (why this exists — the drift-with-no-anchor failure), **FB-0046** (the experience/ambition lens = D3), and `dev-docs/roadmap.md` § "Designer-signal track" (D1–D5).

---

## 0. Picking this up cold

You need nothing from the originating conversation. Read in this order:

1. **§1 Goal + §2 Scope** — what this is and isn't.
2. **`dev-docs/feedback.md` FB-0081** in full — it is the user's own specification of the loop, including *why* the plan comes after the prototype and *why* there are still only two gates. Everything here implements it; if this doc and FB-0081 ever disagree, FB-0081 wins.
3. **§3 The target loop** — the seven steps, annotated with what's new vs reused.
4. **§4 Decisions already made** — do not relitigate these; they are user-directed. Relitigating burns the human's time on settled questions.
5. **§5 Substrate** — orchestrate the *agents*, do not merge the *skills*. This is the one architectural trap.
6. **§8 Spec-walk** — the work as checkboxes, phased.
7. **§9 Confidence verdicts** — two assumptions are MEDIUM/LOW and gate the build: the auto-written technical plan's quality (§9.3, needs a spike **before** committing to D1b) and the prototype medium for non-web surfaces (§9.4, a human decision). Resolve or escalate both before Phase 2.

**Prerequisite check before Phase 1:** confirm `/flow:critique-plan <path>` and `/flow:audit-plan <path>` still accept a plan-file argument (FB-0068, shipped v1.18.0) and that `extract_session.py --plan-file` still exists — the brief/plan review reuses exactly this. As of this writing both are present (`critique-plan/SKILL.md:43`, `extract_session.py:7`).

---

## 1. Goal

For a UI-surface change, move the human's **first** decision point from approving a written plan to approving a **prototype** — the artifact the human (especially a designer) can actually evaluate. The technical plan is written *after* the prototype is approved and is **machine-gated, never human-gated**. The result: the human evaluates a look, not a description of a look; the cheap artifact (the prototype) is the one under revision; and a plan always exists for the downstream gates to anchor to.

This **moves** a gate; it does not add one. Flow's thesis is two load-bearing human gates — plan approval and merge. D1 replaces *plan-text approval* with *prototype approval*. The merge gate and everything after execution (`/flow:verify-build`, `/flow:ship`) are untouched.

## 2. Scope

### In
- A **design-brief** artifact + template (the pre-prototype problem statement).
- A **pre-prototype review** that fans out `auditor` + `plan-critic` + a new **experience/ambition lens** over the brief and returns one triaged verdict.
- A **prototype phase** — iterative, cheap, no ship pipeline / evals / doc-synthesis — ending at **human gate 1: prototype approval**.
- The new **experience/ambition lens agent** (D3; content = FB-0046).
- An **auto-written technical plan** step (after approval) + its **machine-gate** (clean → proceed; auto-fixable → fix + re-review once → proceed; decision-required → escalate as a question per FB-0075).
- The **workflow.md re-ordering** (Steps 1–2 and the Step 8/9 "not a third gate" argument).
- A **trigger** that fires the whole pre-prototype phase, with a **proportionality collapse** to Clarify + brief on small surfaces.
- **D2 — a `role` slot in `flow.config.json`** (`designer` / `engineer` / …), because the trigger and the escalation-verbosity key off it. Ships with or just before D1.

### Out
- **The merge gate.** Untouched — human gate 2 stays exactly as is.
- **`/flow:verify-build` and everything post-execution.** D1 restructures Clarify→Plan; it does not touch Execute→Ship. Verify-build stays the post-execution behavioral gate. **This was the user's explicit constraint: the visual human-gate does not replace verify-build.**
- **D4 (split design/eng feedback) and D5 (message budget).** Separate roadmap items; sequence after D1. D5 keys off D2.
- **D6 (voice annotation).** PARKED — see `dev-docs/research/voice-annotation-pipeline-2026-07.md`. Do not build.
- **Merging the reviewer skills into one.** See §5 — this is forbidden and why.

## 3. The target loop (FB-0081, annotated)

For a UI-surface change that clears the trigger (§7):

| # | Step | New / reused |
|---|------|--------------|
| 1 | **Clarify** — read source-of-truth docs, surface conflicts, ask 2–4 questions. Interaction, not an artifact to approve. | **Reused** — this is today's Step 1. |
| 2 | **Design brief** — problem, whose moment, constraints, intended scope, what's deliberately excluded, where the agent intends to push past the literal request. Short enough to read in ~20 seconds. | **New** — the brief's shape + a template. |
| 3 | **Review the brief before building anything** — `auditor` (assumptions invented rather than asked) + `plan-critic` (scope drift, *absent elements the user explicitly requested*, incoherence vs the design-language doc) + the **experience/ambition lens** (is this the right problem, is the ambition high enough). Fanned out, one triaged verdict. | **New orchestration over reused reviewers** + **new lens** (D3). |
| 4 | **Prototype** — iterative and cheap. No ship pipeline, no evals, no doc synthesis. Iteration *is* the point (the six-round annotation-layer rebuild is the reference case). | **New phase.** |
| 5 | **Prototype approval — human gate 1.** | **Moved gate** (was: plan approval). |
| 6 | **Technical plan** — auto-written *after* approval, against a design that survived contact. Reviewed by `auditor` + `plan-critic` + push-further-on-quality, then **machine-gated**: clean ⇒ proceed; `[auto-fixable]` ⇒ fix + re-review **once** ⇒ proceed; `[decision-required]` ⇒ escalate as an answerable question (FB-0075's shape), never as a document to read. Loop only on mechanical signals, never on LLM judgment. | **New** (auto-write + machine-gate). Reviewers reused. |
| 7 | **Execute → review → ship → merge — human gate 2.** | **Reused, untouched.** |

## 4. Decisions already made — do NOT relitigate (all user-directed, FB-0081)

1. **Two gates, period.** Prototype approval (gate 1) + merge (gate 2). The user said "agreed — keep two gates." Do not add a technical-plan approval gate.
2. **Prototype comes BEFORE the plan — not first, not alongside.** Writing the plan before the prototype is approved anchors both parties: the human reads a committed-looking plan and pushes back less on the prototype, which is backwards since the prototype is the cheap thing to change. Any prototype revision also invalidates plan work already reviewed. (FB-0081 "Why the plan must not come first or alongside.")
3. **The technical plan is auto-written and machine-gated, never human-gated.** The trade: the machine gate stops being a backstop behind a human and becomes the only thing there — so review at that point is *stricter*, and "no plan produced" must be *impossible*, not the silent default.
4. **A plan must ALWAYS exist.** `/flow:audit-coverage`, `/flow:verify-build`'s Spec-walk, and the ship rigor gate all anchor to a plan. Auto-writing it after prototype approval is precisely what closes FB-0080 (drift detection had no anchor because no plan was ever produced).
5. **Rigor before prototyping is required.** The user: "flow agent should still be asking me questions for clarity, and it needs some review steps for its own work similar to audit and critique before prototyping." Hence Steps 1–3.
6. **The experience/ambition lens ships as an AGENT, not a skill** (D3). By D1's own test — would anyone invoke it standalone? no — it belongs in `agents/` alongside the `lens-*` family, reached only through the orchestrator.
7. **Proportionality is a first-class constraint, not a nicety.** Three review passes before a prototype exists costs more than a small change. Gate the whole pre-prototype phase on the same trigger as the prototype, and collapse to Clarify + brief (no review passes) on genuinely small surfaces — or this rebuilds the ceremony it exists to remove.

## 5. Substrate — orchestrate the agents; do NOT merge the skills

The brief review (Step 3) and the technical-plan review (Step 6) are **fan-out steps in the `/flow:staff-review` shape**: one orchestrator spawns `auditor`, `plan-critic`, and the D3 lens **in parallel, in one tool message**, and returns a single triaged verdict. But the parallel is with staff-review's *structure*, not its packaging:

- `/flow:staff-review`'s four lenses are **agents only** (`agents/lens-*.md`), no standalone skill, because nobody runs "the design-engineer lens" alone.
- `auditor` and `plan-critic` are agents **with** skill wrappers, and `/flow:critique-plan <path>` on a queued plan doc is a real shipped use case (FB-0068).

So the orchestrator spawns the **agents** (one source of truth per reviewer prompt) while `/flow:audit-plan` and `/flow:critique-plan` survive as thin wrappers for direct human invocation. **The test for whether a reviewer earns a standalone skill: would anyone run it alone?** That is why the two families are shaped differently — not an inconsistency to normalize away.

**The load-bearing reason for one orchestrator (not speed):** today each skill runs `extract_session.py` itself (`audit-plan` once, `critique-plan` twice), so running them back-to-back can hand each a *different* session window — there is no way to demonstrate the reviewers assessed the same artifact. One orchestrator = **one extraction, handed to all**. Under D1 that is three passes over one brief, which makes the guarantee more valuable.

**Do NOT collapse the reviewers into one.** They ask different kinds of question — `auditor` is epistemic ("is this claim actually verified?"), `plan-critic` is conformance ("does this match what was asked + the reference docs?") — each with its own eval-pinned output contract (`ISSUE`/`AUDIT SUMMARY` vs `CRITIQUE SUMMARY`/`APPROVED`). Merging also destroys the separate context windows that are the only current mitigation for FB-0013 (same-model critic collusion), and contradicts FB-0072's rule that skills sharing a trigger moment should compose, not merge — the concession that cost `/flow:post-merge` four releases of a silently-absent step (FB-0077).

## 6. New vs reused (so you build only what's genuinely new)

**Genuinely new:**
- The **design-brief shape + template** (§3 step 2).
- The **prototype phase** (iterative, no pipeline) + how the human approves it (gate 1 mechanics).
- The **D1 orchestrator** — the fan-out + single-extraction + triaged-verdict harness, used at Steps 3 and 6.
- The **experience/ambition lens agent** (D3; content from FB-0046 — two lenses: experience/product-designer *and* push-further-on-quality-not-scope with a loud anti-scope-creep guard).
- The **auto-written technical plan** + its machine-gate.
- The **trigger** + proportionality collapse.
- **D2** — the `role` slot.

**Reused (do not rebuild):**
- `extract_session.py --plan-file` + `/flow:critique-plan <path>` / `/flow:audit-plan <path>` standalone review (FB-0068).
- The `/flow:staff-review` fan-out *structure* (one message, N parallel `Agent` calls, triaged output).
- FB-0075's escalate-as-answerable-question shape for `[decision-required]`.
- Step 1 "Clarify" (exists).
- The downstream anchor consumers (`audit-coverage`, `verify-build` Spec-walk, rigor gate) — unchanged; they just always have a plan now.
- Held item **[10] from the #119 drain** (the HTML-prototype geometry-audit + fresh-eyes-taste evaluation) — **folds in here** as the agent's self-check during the prototype phase (Step 4) *before* it presents the prototype at gate 1. It is not a separate fork; its timing moves earlier (pre-execution).

## 7. The trigger + proportionality (get this right or the whole thing backfires)

The pre-prototype phase (Steps 2–3) fires on the **same trigger as the prototype**. Candidate trigger: `flow.config.json.role == "designer"` **OR** the change is UI-surface (`uiSurface: true` and the request/diff is visual) **AND** the surface is non-trivial. Small surfaces **collapse to Clarify + brief with no review passes**.

- **Open design point (§9.2):** define "small surface" concretely. Options: a size heuristic (files/lines), a declared `mode: tiny`, or the agent's own judgment gated by the human at Clarify. Pick one and pin it with a fixture; do not leave it to per-run vibes, or the ceremony returns.
- **D2 dependency:** the `role` slot is what lets a designer opt the whole loop into prototype-first while an engineer gets the classic plan gate. Build D2 first or in the same first PR.

## 8. Spec-walk (the work, phased)

Phasing is dependency-ordered. **Do not start Phase 2 until §9.3's spike resolves** (auto-plan quality) and §9.4 is a human decision (prototype medium).

### Phase 0 — D2 role slot (small, unblocks the trigger)
- [ ] Add `role` to `plugins/flow/schema/flow.config.schema.json` (enum incl. `designer`, `engineer`; optional; documented default = unset ⇒ classic behavior). Verify with a schema round-trip.
- [ ] `/flow:doctor` reports the resolved `role` (or "unset ⇒ classic plan gate").
- [ ] `plugins/flow/docs/workflow.md` documents the slot + that D1's trigger reads it.

### Phase 1 — the experience/ambition lens agent (D3) + the brief + the pre-prototype orchestrator
- [ ] Author `plugins/flow/agents/lens-experience.md` (or similarly named) from FB-0046: (a) experience/product-designer lens — right problem? ambition high enough? journey/edge-states/friction/feel; (b) push-further-on-quality — raise the craft bar of the *declared* scope, with a loud anti-scope-creep guard. Match the `lens-*.md` frontmatter + output shape. **Prompt change = code change: ship an eval fixture** (a brief that is conformant-but-low-ambition → the lens flags ambition; a genuinely-tight brief → "nothing to push").
- [ ] Define the **design-brief template** (the six fields from §3 step 2) — where it lives (a `/flow:*` skill or a workflow.md section) and its ~20-second-read constraint.
- [ ] Build the **pre-prototype review orchestrator** (Step 3): one extraction of the brief, fanned to `auditor` + `plan-critic` + `lens-experience` in one tool message, returning one triaged verdict (BLOCKER/decision-required routes to a human question per FB-0075; clean ⇒ proceed to prototype). Reuse `extract_session.py --plan-file` against the brief.
- [ ] Wire any new eval harness into `.github/workflows/ci.yml` (CI enumerates harnesses explicitly — an unwired harness gives zero protection).

### Phase 2 — the prototype phase + human gate 1 + the loop re-ordering
- [ ] Define the **prototype phase**: iterative, no ship pipeline/evals/doc-synthesis; the agent produces + self-evaluates an HTML prototype (fold in held item [10]'s geometry-audit + fresh-eyes-taste self-check) and iterates before presenting.
- [ ] Define **human gate 1** mechanics: how the prototype is presented (served HTML? the verify-build report surface? a static file?) and how approval is captured.
- [ ] Re-order `plugins/flow/docs/workflow.md` Steps 1–2 and rewrite the Step 8/9 "not a third gate" argument (FB-0081 says the objection is answered by *replacement*, not exception — update the prose so it no longer reads as forbidding a visual gate).
- [ ] Update `plan-discipline.md` + `planner.md` for the moved gate.

### Phase 3 — auto-written technical plan + machine-gate
- [ ] After gate 1, **auto-write the technical plan** (a real Spec-walk plan, against the approved prototype).
- [ ] **Machine-gate it**: `auditor` + `plan-critic` + push-further-on-quality → clean ⇒ proceed; `[auto-fixable]` ⇒ fix + re-review once ⇒ proceed; `[decision-required]` ⇒ escalate as an answerable question. **Loop only on mechanical signals.**
- [ ] Assert **"no plan produced" is impossible** on the D1 path (a mechanical check that a plan exists before Execute).

## 9. Confidence verdicts (load-bearing assumptions)

### 9.1 — Two-gate structure + reused review machinery — **HIGH**
FB-0081 is explicit and user-directed; `--plan-file`/standalone review shipped in v1.18.0 (FB-0068). **If it flips:** it won't — this is settled direction.

### 9.2 — Proportionality trigger threshold — **MEDIUM**
"Collapse to Clarify + brief on small surfaces" needs a concrete definition of "small." **If it flips** (too aggressive ⇒ ceremony on tiny changes; too lax ⇒ big changes skip the brief): the feature rebuilds the ceremony it removes, or misses the cases it exists for. **Resolve by:** picking one mechanism (size heuristic / `mode: tiny` / Clarify-gated judgment) and pinning it with a fixture during Phase 1.

### 9.3 — The auto-written technical plan is good enough to anchor verify-build — **LOW ⇒ SPIKE FIRST**
The whole design rests on an agent auto-writing, after prototype approval, a Spec-walk plan solid enough that the machine gate (and downstream verify-build/audit-coverage) have something real to check. If the auto-plan is thin, the machine gate is a rubber stamp and FB-0080's hole reopens one level down. **If it flips:** the technical plan needs a human gate after all — which breaks the two-gate thesis. **Resolve by a spike BEFORE Phase 3:** take one real approved prototype, auto-write its technical plan, run `audit-coverage` + `critique-plan` + a verify-build dry-read against it, and judge whether the criteria are genuine or hollow. This is an automatic human gate (LOW confidence) — do not build Phase 3 until the spike clears.

### 9.4 — The prototype medium for non-web surfaces — **MEDIUM, human decision**
FB-0081 assumes an HTML-ish prototype. Flow's consumers include native apps (the iOS/health-tracker cold-run lineage). For a native surface, is the prototype an HTML proxy of the intended UI, a platform-specific mockup, or is prototype-first web-only for now? The roadmap already notes the prototype must carry a **feasibility read** ("expensive to build for real"), since infeasibility now surfaces after a look is approved. **If it flips:** the gate approves a look that can't be built natively. **Resolve by:** a human decision at kickoff (this doc's owner should ask), scoped explicitly in the first PR.

### 9.5 — D2 role slot is low-risk — **HIGH**
A new optional config slot defaulting to classic behavior; additive. **If it flips:** unlikely; worst case a naming change.

## 10. Two things that make or break it (from FB-0081, restated because they are the failure modes)
1. **Proportionality** (§9.2) — the pre-prototype phase must collapse on small surfaces or it is net-negative.
2. **A plan must always exist** (§8 Phase 3) — auto-written, mechanically asserted present, because every downstream gate anchors to it and FB-0080 happened precisely because none was produced.

## 11. Files this will touch (anticipated)
- `plugins/flow/schema/flow.config.schema.json` (D2 `role` slot).
- `plugins/flow/agents/lens-experience.md` (new; D3 / FB-0046).
- `plugins/flow/docs/workflow.md` (Steps 1–2 re-order; the Step 8/9 "not a third gate" prose; the `role` slot + trigger).
- `plugins/flow/skills/{critique-plan,audit-plan}/SKILL.md` (awareness of the brief + the orchestrated path; keep the thin wrappers).
- `plugins/flow/rules/plan-discipline.md`, `plugins/flow/agents/planner.md` (moved gate; auto-written plan).
- A new orchestrator skill or workflow for the brief/plan fan-out (Steps 3 + 6).
- `plugins/flow/evals/` (lens fixture + orchestrator fixture) + `.github/workflows/ci.yml` (wire any new harness).
- `/flow:doctor` (report `role`).
- `dev-docs/roadmap.md` (move D1 from § Next to shipped as phases land), `dev-docs/README.md` (this handoff's status), `dev-docs/history.md`.

## 12. How to verify
- Each new reviewer/lens prompt ships an eval fixture (prompt change = code change; CLAUDE.md).
- The proportionality trigger is pinned by a fixture (§9.2).
- Phase 3's "a plan always exists" is a mechanical assertion with its own check.
- The §9.3 spike is judged by a fresh-context read, not the author's.
- Dogfood note: flow's own repo is `uiSurface: true` but `platform: library` — the *prototype phase itself* can't be dogfooded on flow (no app), so first real exercise is a consumer UI project (the health-tracker iOS lineage), which is also where §9.4 gets decided.

## 13. Suggested PR breakdown
- **PR 1 (Phase 0):** D2 `role` slot — small, unblocks the trigger.
- **PR 2 (Phase 1):** the experience/ambition lens agent + the design-brief template + the pre-prototype orchestrator. Self-contained; delivers the "review the brief" half.
- **Spike (before PR 3):** §9.3 auto-plan quality. Ship as `mode: spike` — the finding is the deliverable.
- **PR 3 (Phase 2):** the prototype phase + human gate 1 + the workflow re-ordering. Gated on §9.4 being decided.
- **PR 4 (Phase 3):** the auto-written technical plan + machine-gate + the "plan always exists" assertion.

Keep each small; the proportionality lesson applies to the meta-work too.
