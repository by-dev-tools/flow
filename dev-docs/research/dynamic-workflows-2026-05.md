# Dynamic Workflows (Claude Code) — Impact Analysis for Flow

*Research + strategic analysis of Anthropic's dynamic-workflows research preview (shipped 2026-05-28 with Opus 4.8) and what it means for Flow's design.*

**Date:** 2026-05-28
**Scope:** the dynamic-workflows announcement + official docs + the in-session Workflow tool API. Strategic read against Flow's current architecture (v1.2.6) and queued PRs (J shipped, M shipped, K/L/N/O/P queued).
**Status:** Living document — supplement as the research preview evolves toward GA.
**Sister docs:** [`agent-orchestration-2026-05.md`](agent-orchestration-2026-05.md) (the broader orchestration survey this extends), [`../feedback.md`](../feedback.md), [`../plan.md`](../plan.md) (the "reviewer-chain-as-workflow" spike).

---

## TL;DR

Dynamic workflows are an **orchestration substrate**, not a competing workflow product. They operate one layer *below* Flow: Flow is doctrine (gates, intent↔spec fidelity, compounding feedback, never-merge); workflows are the engine (fan-out, context isolation, adversarial-refute, structured output, resume). The engine got dramatically more powerful — which makes Flow's doctrine **more** valuable, not less.

- **Superseded (hand-rolled → now native):** PR N's STATUS-marker structured-result contract, PR M's prose-described retry loop, PR J's single-agent prove-or-disprove, the `extract_session.py` context-isolation hand-roll, and the "emulate skills via Agent subagents" dev pattern (FB-0001). All are markdown/prose emulations of primitives the runtime now provides directly (`agent({schema})`, JS loops + `budget`, independent refuters, script-variable isolation).
- **Not touched (Flow's irreplaceable core):** human gates, spec/intent fidelity, confidence gating, cross-session compounding feedback, never-merge, and cost discipline.
- **Trigger model:** workflows are a **tier invoked for specific phases**, not the default for every plan. There is no silent always-on auto-trigger; even `ultracode` is selective per substantive task.
- **The play:** reposition Flow as "the doctrine layer that makes large-scale autonomous orchestration safe and aimed at user intent," and re-base Flow's *mechanics* (the reviewer fan-out first) onto workflows as substrate.

---

## 1. What shipped (2026-05-28)

Research preview alongside Opus 4.8. Requires Claude Code v2.1.154+. Available on Pro/Max/Team/Enterprise, the Anthropic API, Bedrock, Vertex, and Foundry.

**Mechanism:** Claude writes a JavaScript orchestration script on the fly; a runtime executes it in the background while the session stays responsive. Intermediate results live in **script variables**, so Claude's context window holds only the final verified answer — not the exhaust of every step.

**Limits:** up to **1,000 subagents per run**, **16 concurrent** (fewer on low-core machines).

**Verification is first-class:** independent agents address a problem from different angles, *other* agents try to refute their findings, and the run iterates until answers converge. Only claims that survive refutation reach the user.

**Resume:** runs are resumable **within the same session** (completed agents return cached results). Across sessions they reset.

**Bundled workflow:** `/deep-research` (fan-out web search → cross-check sources → vote on claims → cited report).

**Real-world scale point:** the Bun Zig→Rust port — ~750k lines of Rust, 99.8% of the existing test suite passing, 11 days first-commit-to-merge — was done with dynamic workflows.

Sources: [Introducing dynamic workflows (claude.com)](https://claude.com/blog/introducing-dynamic-workflows-in-claude-code), [Orchestrate subagents at scale (code.claude.com docs)](https://code.claude.com/docs/en/workflows), [TechCrunch](https://techcrunch.com/2026/05/28/anthropic-releases-opus-4-8-with-new-dynamic-workflow-tool/), [MarkTechPost](https://www.marktechpost.com/2026/05/28/anthropic-ships-claude-opus-4-8-alongside-dynamic-workflows-and-cheaper-fast-mode-with-workflows-capped-at-1000-subagents/).

### 1.1 The script API (from the in-session Workflow tool; docs omit the primitives)

- `agent(prompt, {schema, model, isolation, agentType, phase, label})` — spawn one subagent. With `schema` (JSON Schema) it returns a validated object (tool-layer validation + auto-retry on mismatch); without, it returns final text.
- `parallel(thunks)` — concurrent, **barrier** (awaits all; failed thunks resolve to `null`).
- `pipeline(items, ...stages)` — each item flows through all stages independently, **no barrier**. The default for multi-stage work.
- `phase()`, `log()` — progress grouping + narrator lines.
- `budget` — token-aware loops (`budget.remaining()`); the user's `+Nk` directive is a hard ceiling.
- `isolation: 'worktree'` — per-agent git worktree for parallel mutation without conflict.
- `model` per stage/agent — route cheap stages to a smaller model.

This matters: the patterns Flow has been *describing in prose* (bounded retry, structured output, parallel review, context isolation) are **first-class callable primitives** here.

---

## 2. Trigger model — workflows are a tier, not the default

The question that drives Flow's design posture: *do plans run as workflows more often than not, or is it a special thing?* **Special thing, by design.**

| Path | How | Scope |
|---|---|---|
| Manual keyword | the word `workflow` in the prompt (`alt+w` suppresses the highlight) | that one task |
| Manual named | `/deep-research` or a saved `/<name>` workflow command | that invocation |
| Automatic (`ultracode`) | `/effort ultracode` → Claude evaluates each request, decides per-task | only **substantive** tasks; session-scoped; resets next session |

**There is no silent always-on auto-trigger.** Without the keyword, a workflow command, or ultracode, nothing becomes a workflow. And ultracode does **not** promote every plan — published criteria converge on three conditions that must hold together: (a) too big for one context window, (b) split strategy unknown in advance, (c) quality > token economy. Explicit guidance: *"If the task plan fits in two or three steps Claude can hold in its head, stick with subagents or skills"*; *"drop back to `/effort high` as soon as the heavy task is done."*

**Permission model (load-bearing for Flow safety):**
- Default / accept-edits mode: **prompted every run** (a free *launch* gate).
- Auto mode: first launch only; skipped under ultracode.
- Bypass / `claude -p` / Agent SDK: never prompted.
- **Workflow subagents always run in `acceptEdits`** (file edits auto-approved) regardless of session mode. The only runtime gate is at launch — there is **no mid-run user input** (*"For sign-off between stages, run each stage as its own workflow"*).

**Flow implication:** the correct posture is **selective promotion** — the loop stays conversational-with-gates by default; only specific phases that are wide/parallel/uncertain opt into workflow execution. Most Flow PRs are small-to-medium and gate-bounded; promoting all of them to fleet runs would blow cost with no quality gain.

Sources: [docs](https://code.claude.com/docs/en/workflows), [Geeky Gadgets](https://www.geeky-gadgets.com/anthropic-claude-code-workflows/), [The New Stack](https://thenewstack.io/claude-opus-48-release/).

---

## 3. The layer model — Flow and workflows do not compete

The docs' own comparison table frames it as *who holds the plan*:

| | Subagents | Skills | Workflows |
|---|---|---|---|
| What it is | a worker Claude spawns | instructions Claude follows | a script the runtime executes |
| Who decides next | Claude, turn by turn | Claude, per prompt | the script |
| Intermediate results live in | Claude's context | Claude's context | script variables |
| Scale | a few per turn | same | dozens–hundreds per run |
| Interruption | restarts the turn | restarts the turn | resumable in-session |

So the two layers:

| Layer | Provides | Owner |
|---|---|---|
| **Dynamic workflows** | orchestration substrate — fan-out, context isolation, adversarial-refute primitive, structured output, resume, repeatable-as-code | Anthropic runtime |
| **Flow** | doctrine — human gates, intent↔spec fidelity, confidence gating, compounding cross-session feedback, never-merge | Flow plugin |

Workflows belong in the same category CLAUDE.md already governs with *"Never wrap a bundled Claude Code skill."* Flow should **compose** workflows, never reimplement or wrap them.

**The nesting insight:** `ultracode`'s **understand → change → verify** loop is the *unguarded autonomous engine*. Flow's 11-step loop is that engine wrapped in a spec-fidelity front-half (clarify→plan→critique→confidence→**gate**) and a compounding-feedback back-half (synthesis→memory→preflight-promotion), with a **human at both ends**. Flow is the doctrine ultracode lacks.

---

## 4. What is now hand-rolled-redundant

Three recent/queued Flow investments are markdown/prose emulations of primitives the runtime now provides natively:

1. **PR N's STATUS-marker structured-result contract** (`STATUS: CLEAN | SKIPPED | FINDINGS`, parsed by text-grep in `/flow:ship` Step 2) ≈ `agent(prompt, {schema})`. Workflows give validated JSON structured output with tool-layer retry for free. **Recommendation: pause PR N Phase 2** before further investing in the text-grep contract; if the reviewer chain moves onto a workflow it largely evaporates.

2. **PR M's bounded-retry preflight** (N=3, diff-hash oscillation, expressed in SKILL.md *prose*, with the project's own MEDIUM-confidence worry that "prompt-driven looping is reliable enough"). Workflows make this a real `for`/`while` loop with a real counter and `budget` (loop-until-budget / loop-until-count are documented patterns). **The reliability worry disappears when the loop is code.** The load-bearing *discipline* survives untouched: loop only on a tool's exit code, never on reviewer judgment — and becomes *more* important because workflows make looping-on-judgment equally easy to express.

3. **PR J's prompt-level "prove-or-disprove" self-check** — a *single agent asked to disprove itself*, structurally weaker than an *independent* refuter. Workflows' refute-until-converge is the stronger implementation of the exact pattern PR J encoded. Keep the doctrine; the substrate offers a better mechanism.

Also hand-rolled-redundant: **`extract_session.py` context isolation** (workflows isolate intermediate results in script variables by construction) and the **"emulate planned skills via Agent subagents" dev pattern** (FB-0001) — workflows are the native fan-out.

---

## 5. Acceleration opportunities (re-basing, in leverage order)

1. **`/flow:staff-review` → a dynamic workflow.** Today: a *fixed* 4 lenses, parallel-then-merge, no cross-checking of findings (debate loops deliberately avoided per *Judging with Many Minds*, arxiv 2505.19477 — rightly, since that paper is about *debate*, where agents see each other and bias amplifies). A workflow delivers the pattern Flow actually wants and couldn't cheaply build: **find → adversarially refute each finding with independent blind agents → only survivors reach the user.** This directly attacks Flow's #1 quality cost — the false-positive tax — *without* the debate-loop bias risk (refutation is parallel and blind, not iterative consensus). Plus **dynamic fan-out** (scale finders to diff size, not fixed 4) and **native context isolation**.
2. **`/deep-research` for Flow's own research passes** — the bundled workflow is purpose-built for the cross-checked-sources shape Flow does by hand (this doc included).
3. **New distribution surface — BLOCKED as of 2026-05-28.** Saved workflows live in `.claude/workflows/*.js` (project) or `~/.claude/workflows/` (user) and become `/`-commands. Flow currently ships markdown (skills + agent prompts) and could in principle ship **orchestration scripts** as a new artifact type (e.g. a bundled `/flow:review` workflow). **RESOLVED:** a plugin **cannot** bundle workflows — the official plugin components are commands / agents / skills / hooks / MCP servers only; there is no `workflows/` directory ([anthropics/claude-code plugins README](https://github.com/anthropics/claude-code/blob/main/plugins/README.md)). So this distribution play is blocked until Anthropic adds workflows as a plugin component type. Until then, a Flow-authored review workflow can only be run in-session (via the `workflow` keyword) or saved per-project/per-user by the consumer — not shipped in the install bundle. Track as a roadmap item gated on the plugin-component list growing.

---

## 6. Gaps that remain after composing Flow + workflows

1. **Carrying doctrine into the script.** A workflow agent gets a prompt; it doesn't read `flow.config.json` / `core-docs`, doesn't enforce scope, doesn't gate on a LOW-confidence assumption. Flow's reviewer prompts become the `agentType`/prompts a workflow spawns — but the plumbing (config + spec/feedback → workflow agent prompt) doesn't exist yet.
2. **Mid-run gate ergonomics.** "One workflow per stage with a gate between" is correct, but Flow must own the *seam* between workflows (state hand-off, resume). The runtime resumes only within a session.
3. **Convergence ≠ ground truth.** Refute-until-converge among *same-model* agents is the queued **same-model-critic-collusion concern** (PR P; FB number assigned at ship time per the reserved-feedback-numbers protocol — not hard-coded), unsolved. Workflows make it *cheaper to run more same-model critics* — diminishing returns. PR M's "only an exit code is a trustworthy loop-exit" principle is the guard against treating model-consensus as truth; it needs restating as doctrine for the workflow era.
4. **Cross-session memory vs workflow caching** are different mechanisms that don't talk to each other. Flow's FB-XXXX → memory → preflight-promotion pipeline is the learning layer workflows structurally lack (they reset each session).
5. **Cost governance.** Workflows "consume meaningfully more usage." Flow's single-pass / parallel-then-merge / loop-only-on-exit-codes rules become the cost-control governor on a substrate that defaults to expensive.

---

## 7. Recommendations

**Reposition, don't rebuild.** Shift Flow's one-line identity from "a managed-autonomy loop" to *"the doctrine layer — gates, intent-fidelity, and compounding memory — that makes large-scale autonomous orchestration safe and aimed at user intent."*

1. **Spike: reviewer chain as a workflow** (see `plan.md`). Re-implement `staff-review` + security + a11y + auditor as one dynamic workflow with find→refute→triage, `schema` output, worktree isolation. Tests whether 3 hand-rolled mechanics collapse into the substrate. **Spike, because it spawns a fleet → cost exposure → needs the human gate + critique-plan before execution.**
2. **Pause PR N Phase 2 and PR M's prose-loop investment** pending the spike's verdict.
3. **Keep PR J's doctrine, plan to swap its mechanism** (independent refuters > self-disproof) once the substrate is proven in the spike.
4. **Add a feedback rule** for the workflow era: workflows make looping-on-judgment-convergence trivially expressible; Flow forbids it (only mechanical exit codes are trustworthy loop-exits). *Number to be assigned at ship time per the reserved-feedback-numbers protocol — do not hard-code an FB-XXXX here (FB-0013 is contended).*
5. **Plugin-can-bundle-workflows question — RESOLVED (no).** Verified 2026-05-28 against the [anthropics/claude-code plugins README](https://github.com/anthropics/claude-code/blob/main/plugins/README.md): plugin components are commands / agents / skills / hooks / MCP servers only. The distribution-surface play (§5.3) is blocked until the component list grows; track as a roadmap item, not a near-term PR. The reviewer-chain re-base (rec #1) is unaffected — it runs in-session via the `workflow` keyword.
