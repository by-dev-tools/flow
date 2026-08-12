# AI coding-workflow landscape — competitive benchmark vs Flow

**Date:** 2026-07-08
**Status:** research / direction-setting. Fed the **§ ▶ Active program (2026-07-08)** sequence in `roadmap.md` (M → #5 → #2 → #4 → #3). No plugin artifacts changed by this doc.
**Companion docs:** `dynamic-workflows-alignment-2026-06.md` (the dynamic-workflows engine specifically), `agent-orchestration-2026-05.md`, `visual-verification-blueprint-2026-06.md`. This doc is the *external-landscape* layer those three assume.

**Provenance / confidence.** Gathered from a `/deep-research` fan-out that was **throttled mid-run** (account session limit hit during the adversarial-verification phase — the 25 generated claims never received verification votes, so they are *unverified*, not *refuted*). The load-bearing facts below were then recovered via **direct web search + fetch** (not rate-limited), which are cited inline. Where a claim rests only on the throttled run or on training knowledge, it is flagged **[unverified]**. Framework details (gstack / Superpowers / GSD) are from live 2026-07 sources and are solid; the model-routing cost percentages are directional, not audited.

---

## 0. One-line synthesis

> Every serious 2025–26 Claude Code framework is the same loop skeleton (clarify → plan → gate → build → review → test → ship) optimized for a *different failure mode*. Flow optimizes for **trust/verification** — and is the only one in the set with adversarial claim-auditing, confidence-gated planning, and a guarded compounding-feedback pipeline. Its clearest gaps are **per-subagent model routing** (which everyone else either does or the platform hands them for free) and **long-session context isolation**. Its visual-feedback surface is *ahead* of the market but fires unreliably.

---

## 1. The shared skeleton + the taxonomy

Having a disciplined loop is now table stakes. Frameworks differentiate by *what each loop refuses to trust*.

| Framework | Author | The loop | Optimizes for | Multi-agent? | Model routing? |
|---|---|---|---|---|---|
| **Flow** | this repo | 11 steps (clarify → plan+critique → execute → preflight → commit → /simplify → staff-review → present → iterate → ship → stop) | **Trust / verification** | Yes (4-lens review, N verify judges, auditor, plan-critic) — all in-session subagents | **No** — all subagents inherit session model |
| **gstack** | Garry Tan (YC) | Think → Plan → Build → Review → Test → Ship → Reflect | **Product/role coverage** | Yes — 23 role personas via slash commands | **Yes** — sidebar browser agent routes Sonnet(fast)/Opus(analysis) |
| **Superpowers** | Jesse Vincent (obra) | Brainstorm → Spec → Plan → TDD → Impl → Review → Finalize (7-phase) | **Test discipline** | Single mega-orchestrator + isolated impl subagents | No |
| **GSD** (Get Shit Done) | community | init → discuss → plan → execute → verify → ship | **Context longevity** | Multiple phase-specific orchestrators; state to disk between phases | No |
| **Spec Kit** | GitHub | specify → plan → tasks → implement | **Spec-as-source-of-truth** | Linear phases | No |
| **BMAD** | community | analyst → PM → architect → dev handoff | **Role handoff** | Yes (persona agents) | No **[unverified]** |

**Key reading:** flow is *not* differentiated by having a loop — everyone has one. It is differentiated by its **skeptical layer** (auditor + plan-critic, two-citation discipline, confidence-verdict gates, behavioral verify-build gate) and its **three-layer feedback pipeline** (user-feedback doc → agent memory → promoted preflight checks, with anti-ossification guardrails). Nothing else in the set has these.

---

## 2. Per-framework notes

### gstack (Garry Tan) — the closest competitor on ambition, and it routes models
Open-source Claude Code setup modeling a **23-person team** (CEO, PM, designer, DX lead, staff engineer, QA lead, release engineer, security reviewer, …), each a slash command. Ordered sprint **Think → Plan → Build → Review → Test → Ship → Reflect**; commands feed each other (`/office-hours` writes a design doc → `/plan-ceo-review` reads it → `/plan-eng-review` writes a test matrix → `/qa` references it → `/review` → `/ship`). Real-browser QA via Playwright (`/qa` "opens a real browser, clicks flows, finds and fixes a bug"). Uses a `gstack` section in `CLAUDE.md` to list skills and enforce tool discipline.

- **Ambition-at-plan-time:** `/plan-ceo-review` explicitly hunts "the 10-star product hiding inside the request" — it *expands* ambition before building. This is the philosophical inverse of flow's plan-critic, which *contracts* scope. Flow's deliberate resolution (per the user, 2026-07): capture ambition at plan time but **route it to the roadmap** for iterative delivery rather than forcing up-front scope expansion (→ roadmap #2 / FB-0046).
- **Model routing (the concrete evidence flow lacks it):** the sidebar/browser agent "auto-routes: Sonnet for fast actions (click, navigate, screenshot) and Opus for reading and analysis."
- **Weakness:** 23 roles is heavy for pure-infra work; strongest when the project has a product dimension.
- Productivity claim (Tan, 2026-03-12): "600k lines of production code in 60 days" — **[unverified marketing claim]**, cite with skepticism.

### Superpowers (Jesse Vincent / obra) — TDD discipline + reusable skills
Agentic skills framework; enforces **red-green-refactor** (tests must fail before implementation), a four-phase debugging methodology (root-cause before fix), Socratic brainstorming before coding, and a **skill that writes skills** + self-updating memory notes. Mega-orchestrator coordinating isolated implementation subagents.

- **Strength:** rigorous correctness via mandatory testing.
- **Weakness (reported):** the mega-orchestrator hits context limits on long sessions.
- **Relevance to flow:** flow's memory→preflight promotion pipeline is *more* rigorous than Superpowers' memory notes (flow has anti-model-collapse guardrails Superpowers lacks) — flow is ahead conceptually, behind in surface area / reusable-skill ergonomics.
- **No model routing.**

### GSD (Get Shit Done) — context-rot defense
Assigns a **fresh orchestrator per project phase**, writing state to disk between phases so each phase starts under ~50% context. XML-formatted quality gates detect "schema drift and scope reduction." Widest agent range (14+).

- **Strength:** "every phase starts with a full context budget because the previous phase handed off cleanly." Built for marathon multi-day/multi-file sessions + crash recovery.
- **Weakness:** overkill for a single-file change.
- **Relevance to flow:** flow's mostly-single-thread loop will hit the same context rot on long features. But flow's `plan.md`/`history.md` *already are* the disk handoff state GSD writes by hand — flow is closer to this than it looks. (Not yet on the active program; noted for a future context-isolation pass.)

### Spec Kit (GitHub) / Kiro (AWS) — spec-driven
Four-phase specify → plan → tasks → implement, with the spec as the durable source of truth. **[Spec Kit phase list unverified — from the throttled run.]** Flow's spec-walk + Visual-walk declared-criteria fields are the same instinct (declare the contract, verify against it), embedded inside a review-heavy loop rather than a standalone spec tool.

### Selection guidance (from the Pulumi comparison, mapped to failure modes)
| Failure mode | That article's pick |
|---|---|
| Code breaks after initial success | Superpowers (enforces testing) |
| Quality degrades after first hour | GSD (fresh context per phase) |
| Shipping unrequested features | gstack (product review first) |
| Multiple simultaneous problems | gstack for direction + bolt on Superpowers TDD |

Flow's implicit slot in that table would be a *fifth* row: **"ships confident-but-unverified claims" → Flow (adversarial auditing + behavioral gate).** No other framework targets that failure mode.

---

## 3. Orchestrators + model selection (the sharpest gap)

The through-line across the whole landscape — and stated by the Claude Code team directly — is **route cheap/fast models to mechanical work and the most capable model to judgment calls.**

- **Claude Code natively supports per-subagent model selection** via a `model:` frontmatter field (`opus` / `sonnet` / `haiku` / `inherit`); unspecified defaults to `inherit`. **[from the throttled run + platform knowledge; high confidence but re-verify against code.claude.com/docs before relying]** Flow's agent files already carry frontmatter, so this is a near-free lever flow doesn't pull.
- **Anthropic's own multi-agent research system** uses an **Opus lead orchestrating Sonnet workers** — canonical orchestrator-worker tiering. **[unverified — throttled run; the pattern is well-attested, the exact model pairing should be re-confirmed]**
- **gstack** routes in production (Sonnet fast-actions / Opus analysis) — see §2.
- **Cost claims:** tiered routing (Opus orchestrator / Sonnet workers / Haiku formatting) reported at ~40–60% cheaper than all-Opus. **[directional, unverified]** Treat as motivation to *measure*, not as a target.
- **General frameworks** (LangGraph, CrewAI, AutoGen, Microsoft Agent Framework) largely do **not** ship built-in cost-aware/dynamic per-task model routing — cost handling is usually just token instrumentation. **[unverified]** So flow adding measured routing would be at or ahead of the general-framework state of the art, not behind it.

**Flow's position + decision (user, 2026-07):** flow runs *everything* on the inherited session model (4 staff lenses + N verify judges + adversarial-transform subagents + auditor + plan-critic + security Explore). The user chose the **conservative, measurement-first** path over eager routing: Opus stays default, **Sonnet is the only challenger, no Haiku yet**, and nothing routes until a harness measures the quality/token delta. This became **roadmap item M** (per-subagent token attribution + offline Opus-vs-Sonnet fixture eval + a randomized/shadow sampler), extending PR P's existing measurement-first discipline. Prior standing direction — "plan-critic + lens agents stay on Opus" — is preserved.

---

## 4. The Claude Code "loops" article — flow's alignment

Article by @delba_oliveira (Claude Code team). Loop taxonomy mapped against flow:

| Article primitive | Flow status |
|---|---|
| **Turn-based loop + verification skills** ("encode your manual checks as a SKILL.md") | ✅ **This is literally flow.** The article's `verify-frontend-change` example is a simpler `/flow:verify-build`. |
| **`/goal`** (evaluator-checked stop condition + turn cap) | ❌ Not used, clean fit. Spec-walk = goal criteria; `verifyBudgetCalls` = a turn cap. Flow hand-rolled a `/goal`-shaped loop. → roadmap #5. |
| **`/loop`, `/schedule`** (time/event-based) | ❌ Not used. `/flow:contribute` runs via a SessionStart hook / OS job — a hand-rolled `/schedule`. |
| **Dynamic workflows / proactive loops** | ⚠️ **Deliberately deferred, well-analyzed** in `dynamic-workflows-alignment-2026-06.md` (workflows forbid mid-run human input → collides with flow's gates → prescribes *segment-bounded* fan-out, O1–O8). Execute O1/O4, don't re-decide. |
| **"Use scripts for deterministic work"** | ✅ Exemplary — `extract_session.py`, `check.mjs`, `render-report.py`, `extract-criteria.py`. |
| **"Use a second agent for code review" (fresh context)** | ✅ staff-review, auditor, plan-critic all fresh-context. (Article says "use built-in `/code-review`" — see §6 on bundled-skill overlap.) |
| **"Encode failures to improve the system for all future iterations"** | ✅ Flow's entire feedback→memory→preflight pipeline. Arguably ahead of the article. |
| **"Route routines to smaller/faster models, most capable for judgment"** | ❌ The one cross-cutting principle flow ignores everywhere. Same finding as §3. → roadmap M. |
| **`/goal` = stop-condition on the work; `/loop` = time/event trigger** | The clean distinction for roadmap #5's two goal-cycles (plan cycle + execution cycle). |

---

## 5. Reflection / self-improvement best practices

Sources: Reflexion (Shinn 2023), Self-Refine (Madaan 2023), Experiential Reflective Learning (2026), OpenAI Self-Evolving Agents Cookbook (Nov 2025), memory-for-agents surveys (2026).

- **Verbal post-mortems prepended to the next attempt** (Reflexion) — flow does this via memory entries. ✅ Flow's anti-model-collapse / anti-ossification guardrails are *more* sophisticated than most literature, which ignores the reinforcement risk flow explicitly designed against.
- **Multi-signal memory scoring (recency + relevance + importance)** beats flat retrieval and is now standard. **Flow's memory is count-capped (30) + mtime-sorted with no relevance/importance scoring**, injected wholesale by the harness rather than ranked per-task. This is the biggest delta.
- **Measured feedback / instrumentation** (OpenAI cookbook): diagnose failures with metrics. Flow's `check.mjs` counts entries + schedules audits but **does not measure whether an entry ever *fired* or *helped***. The workflow doc references a "Fire log" (2+ fires → preflight candidate) but it looks manually annotated, not instrumented.
- **Why the user "can't tell if memory is effective":** nothing measures effectiveness. → roadmap #3 (fire-counts on cite, relevance-ranked injection, dead-entry detection). Distinct from V4 (check-work-against-past-errors); #3 measures *which memories help*.

---

## 6. Visual-feedback landscape — flow is ahead, but fires unreliably

The external space is thin, which validates flow's bet.

- **Agentation** is the leading tool: click-to-annotate DOM elements → structured markdown with selectors + source refs → paste into Claude/Cursor/Windsurf. MCP two-way sync. **Requires React / a live DOM app** — this is the key differentiator: **the user primarily runs plain local HTML demos (opening files), which Agentation doesn't serve.**
- Broader practice ([Tweag agentic-coding handbook](https://tweag.github.io/agentic-coding-handbook/WORKFLOW_VISUAL_FEEDBACK/)) is just "screenshot → drop into agent."
- **Nobody in the eng-workflow space does what flow's V3a/V3b pipeline does:** plan-declared visual criteria → a11y-gated capture → baseline pairwise judging → an *ephemeral HTML walkthrough with a two-way click-to-pin annotation layer* → distilled into a *durable visual history*. Flow is further along than the market.

**Why it fires unreliably (diagnosis — the real problem).** Capture (§5a of `verify-build`) sits behind a long AND-chain, each link a silent-skip risk:
1. `verify-build` must run at all → **flow's own repo is `platform: library`, so it never runs on flow itself** (the user structurally never sees their own visual pipeline). Dogfood in **health-tracker + trio** instead.
2. `uiSurface: true` AND
3. a `Visual-walk` block authored in the plan (author-memory dependency — the FB-0010 failure class flow itself warns about) AND
4. the platform MCP must expose a **drive primitive** (tap/click/type), not just screenshot + a11y tree ("many MCP configs expose only screenshot → only the launch state is reachable, everything else Unknown") AND
5. a **baseline** must exist from a prior accepted run, else visual-layout claims resolve Unknown.

Plus heavy staging (`PLACEHOLDER — TBD Phase 2`, `Empirical verification TODO`, a `/verify`-output contract long marked UNKNOWN) means parts were never exercised against real output.

**User's reframe (2026-07) → roadmap #4:** the report currently reflects **build steps + test pass/fail**; the user wants it to reflect **what changed in product/visual terms for UX critique** (features/screens changed, before/after visuals, decisions to comment on), build-verdict demoted to a collapsed summary. Plus: fires on *every* PR; reliable delivery + findable vs the PR; **auto-opens in Claude-desktop preview**; images load reliably; **pin-to-anything** (elements/text, not just images); works on **plain local HTML**. Ultimate goal: maximally efficient for the user to impart design taste that is implemented and learned from.

---

## 7. Where flow stacks up — bottom line

- **Most rigorous on trust/verification of anything surveyed.** The skeptical auditor + confidence gates + guarded feedback pipeline is genuinely novel and best-in-set for high-stakes/long-lived code. Keep leaning in — it is the moat.
- **Behind on per-subagent model routing** — cheapest available win, native support, three independent sources point at it (gstack, Anthropic pattern, loops article). Addressed measurement-first as roadmap M.
- **Behind GSD on long-session context** — but closer than it looks (docs already are the handoff state). Not yet scheduled.
- **Ahead of the market on visual feedback** — but the pipeline's reliability is gated by a fragile AND-chain and dogfood-blindness on flow's own repo. Roadmap #4.
- **Ahead conceptually on reflection** — but under-instrumented (no relevance scoring, no effectiveness measurement). Roadmap #3.
- **Philosophically opposed to gstack on ambition-vs-discipline** — deliberate identity, resolved by capturing ambition to the roadmap (#2 / FB-0046), not by copying gstack's up-front expansion.

### Bundled-skill hygiene (audited 2026-07)
- Correctly does **not** wrap `/simplify`, `/batch`, `/debug`, `/loop`, `/claude-api`. ✅
- `/flow:verify-build` is the **gold standard**: a thin orchestrator over bundled `/verify` → `/run` → `/run-skill-generator`, explicitly not reimplementing them. ✅
- `/flow:security-review` **reimplements** a red-team prompt that overlaps heavily with bundled `/security-review` (it acknowledges the bundled one exists but keeps its own categories/greps). The clean fix mirrors verify-build: keep flow's wrapper (skip-logic, `STATUS: SKIPPED` audit log, `[auto-fixable]`/`[decision-required]` manifest routing, config-slot resolution) but **delegate the review core to bundled `/security-review` via `Skill()`**. Same question applies to the staff-review **engineer lens vs. bundled `/code-review`**. `/flow:accessibility-review` has no bundled equivalent — custom is justified. *(Captured here; not yet scheduled on the active program — candidate follow-up.)*

---

## 8. How this fed the roadmap

The **§ ▶ Active program (2026-07-08)** in `roadmap.md` sequences the recommendations: **M** (model-measurement harness) → **#5** (goals + required success criteria) → **#2** (plan-gate ambition lens + staff-review uncommon-care) → **#4** (visual reframe) → **#3** (memory instrumentation). Bundled-skill delegation (§7) and long-session context isolation (§2, GSD) are captured here as un-scheduled follow-ups.

---

## Sources

Live (2026-07, direct fetch/search — solid):
- Pulumi — [Superpowers/GSD/GSTACK comparison](https://www.pulumi.com/blog/claude-code-orchestration-frameworks/)
- [garrytan/gstack](https://github.com/garrytan/gstack) · [Agents' Codex writeup](https://agentscodex.com/posts/2026-03-20-garry-tan-gstack-agent-teams-claude-code/) · [MindStudio: What is GStack](https://www.mindstudio.ai/blog/what-is-gstack-gary-tan-claude-code-framework)
- [obra/superpowers](https://github.com/obra/superpowers) · [Simon Willison](https://simonwillison.net/2025/Oct/10/superpowers/) · [Jesse Vincent's original post](https://blog.fsck.com/2025/10/09/superpowers/)
- Reflection: [Reflexion](https://www.semanticscholar.org/paper/Reflexion:-an-autonomous-agent-with-dynamic-memory-Shinn-Labash/46299fee72ca833337b3882ae1d8316f44b32b3c) · [Experiential Reflective Learning](https://arxiv.org/html/2603.24639)
- Visual feedback: [Agentation (Medium)](https://medium.com/design-bootcamp/how-agentation-helps-ai-coding-agents-understand-ui-feedback-960ee81b9798) · [Agentation (Product Hunt)](https://www.producthunt.com/products/agentation) · [Tweag visual-feedback-loop handbook](https://tweag.github.io/agentic-coding-handbook/WORKFLOW_VISUAL_FEEDBACK/)

From the throttled `/deep-research` run (unverified — re-confirm before relying): Claude Code per-subagent `model:` frontmatter (code.claude.com/docs/en/sub-agents); Anthropic multi-agent research system Opus-lead/Sonnet-workers (anthropic.com/engineering/multi-agent-research-system); model-routing cost percentages (augmentcode / cloudzero / mindstudio); LangGraph/CrewAI human-in-the-loop-only (langchain.com/resources/ai-agent-frameworks).

The Claude Code "loops" article by @delba_oliveira was provided verbatim by the user (not a fetched URL) — quotes are from that text.
