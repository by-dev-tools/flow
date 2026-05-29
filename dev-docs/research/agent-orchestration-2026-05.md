# Agent Orchestration & Multi-Agent Workflow Research

*Research compilation supporting Flow's design decisions on agent loops, skill chaining, sub-agent orchestration, and human-in-the-loop placement.*

**Date range:** 2026-05-26 through 2026-05-27
**Scope:** Anthropic + frontier labs (OpenAI / Google / Microsoft / Meta) + 13 AI-native companies + 8 major frameworks
**Status:** Living document — supplement with each research pass. Last updated 2026-05-27.
**Sister doc:** [`dev-docs/feedback.md`](../feedback.md) FB-0011 (the load-bearing design rule synthesized from this research).

---

## TL;DR — How Flow's design holds up against the field

| Flow design call | Field verdict | Source |
|---|---|---|
| Deterministic 11-step workflow (not LLM-decides-next-step) | **Consensus** — Anthropic, LangChain, Inngest, ADK all default deterministic | Anthropic [Building Effective Agents](https://www.anthropic.com/research/building-effective-agents) |
| Bounded-retry preflight (N=3 + oscillation) at Step 1c only | **Independently converged** with Microsoft Magentic (`max_rounds` + `max_stalls` + `max_resets`); ahead of LangGraph / CrewAI / Pydantic AI / DSPy which ship no oscillation primitive | [Magentic docs](https://learn.microsoft.com/en-us/agent-framework/user-guide/workflows/orchestrations/magentic) |
| Single-pass reviewers (audit, plan-critic, lenses) | **Defensible non-consensus** — field is silent on reward hacking; Flow's FB-0011 guards are ahead of published curve | Field gap (see §3 below) |
| Two-sided skeptical layer (plan-critic before + auditor after) | **No public analogue** — Replit has pre-only; Datadog has post-only; nobody has both | (see §2.3) |
| Plan-approval human gate | **Matches Replit Agent 3 and Magentic .NET `RequirePlanSignoff = true`** | [Replit docs](https://docs.replit.com/replitai/agent), Magentic .NET |
| Merge gate (never auto-merge) | **Universal** — every surveyed coding-agent product preserves this | All sources |
| Flat sub-agent orchestration (lens agents called from top-level) | **Matches Anthropic's documented rule** — *"Subagents cannot spawn other subagents"* | [Sub-agents docs](https://code.claude.com/docs/en/sub-agents) |
| Skill chaining via `Skill('a'); Skill('b')` in SKILL.md | **Emergent, not blessed** by Anthropic; alternatives exist in other frameworks (Magentic Sequential, ADK SequentialAgent, LangGraph edges) | (see §6.1) |
| `dev-docs/` cross-session institutional memory | **No published framework standard** — Flow-original | (no analog) |
| Loud-warning on unset config slot | **Matches Inngest "deterministic routing" philosophy + FB-0006/0007 lineage** | Flow-internal |

---

## Part 1: Initial research — agent loops, success criteria, stopping conditions

*Triggered by user question: "would `/loop` and goal-iteration help us iterate to quality? what about getting stuck? what does the official guidance say about verifiable success criteria?"*

### 1.1 The canonical taxonomy

Anthropic's [Building Effective Agents](https://www.anthropic.com/research/building-effective-agents) defines five workflow archetypes. Memorize these — they recur across every other framework's documentation.

| Archetype | Definition | When to use |
|---|---|---|
| **Prompt chaining** | Fixed-decomposition sequential subtasks with programmatic gates between steps | *"Task can be easily and cleanly decomposed into fixed subtasks"* |
| **Routing** | Different LLM calls handle different input categories | *"Distinct categories that are better handled separately"* |
| **Parallelization** | Subtasks fan out for speed (sectioning) or multiple perspectives (voting) | *"Subtasks can be parallelized for speed, or when multiple perspectives are needed"* |
| **Orchestrator-workers** | Central LLM decomposes work and delegates to workers | *"You can't predict the subtasks needed"* |
| **Evaluator-optimizer** | One LLM generates, another evaluates, iterate | *"Clear evaluation criteria, and iterative refinement provides measurable value"* |

**Key sentence on stopping conditions** (load-bearing for Flow):
> *"It's also common to include stopping conditions (such as a maximum number of iterations) to maintain control."*

**Key sentence on human-in-the-loop placement:**
> *"Once the task is clear, agents plan and operate independently, potentially returning to the human for further information or judgement... Agents can then pause for human feedback at checkpoints or when encountering blockers."*

### 1.2 The 2026 Agentic Coding Trends Report

[2026 Agentic Coding Trends Report (Anthropic)](https://resources.anthropic.com/hubfs/2026%20Agentic%20Coding%20Trends%20Report.pdf) tightens the success-criteria principle:

> *"Without explicit success criteria, verification becomes guesswork."*
> *"Agents can define outcomes and success criteria, then self-evaluate and iterate until they meet those criteria."*

The report emphasizes "objective outcomes, constraints, edge cases, and verification" as the four-part rubric for autonomous coding work. Same principle Flow encodes via `flow.config.json.preflightCmd` exit code.

### 1.3 Claude Code common-workflows guidance

[Claude Code common-workflows](https://code.claude.com/docs/en/common-workflows) on scheduled / autonomous tasks:

> *"Be explicit about what success looks like and what to do with results. The task runs autonomously, so it can't ask clarifying questions."*

The `/loop` bundled skill is for **wall-clock recurring polling**, not goal-seeking iteration. Different primitive than what Flow's Step 1c needs.

### 1.4 What this means for Flow

The research validated three design choices for PR H2 (the bounded-retry preflight):
1. Loop ONLY on mechanically-verifiable exit signals (preflight exit code) — never on LLM-judgment outputs (reviewer "approved").
2. Hard iteration cap is mandatory ("maximum number of iterations").
3. Pause for human at checkpoints — but the right checkpoints are *plan approval* and *merge*, not in-loop interruptions.

These distilled into **FB-0011** (in [`dev-docs/feedback.md`](../feedback.md)).

---

## Part 2: Validated recommendation for Step 1c

*Second research pass refined the original recommendation against Flow's actual code.*

### 2.1 The refined position

The first-pass recommendation said "add bounded retry to `/flow:ship` pre-flight." Reading the code revealed:

- Steps 1a/1b/1.5 are mechanical *gates* (stale-base, gh+jq present, something-to-ship) — they fail-fast, no iteration needed.
- Step 3 had a one-shot `typecheckCmd` re-run *after* reviewer-applied fixes.
- **No mechanical-quality preflight loop existed.**

The loop's correct slot is **new Step 1c — between 1b and 2** (before reviewers run, so reviewers see code that already typechecks). Running it *after* would risk reviewers + Claude fighting over the same files across iterations — exactly the reward-hacking failure mode the research identified.

### 2.2 The architectural decision

> **Loops are productive when the exit signal is an external tool's exit code. Loops are harmful when the exit signal is another LLM's judgment.**

Two reasons:
1. **Reward hacking.** A loop over LLM-as-judge teaches the writer to *phrase around* the reviewer rather than fix substance. This is exactly what passive-review-with-evidence-or-silence (Flow's core thesis) is designed to prevent.
2. **No ground truth.** Tests pass or fail — that's binary, externally produced, can't be gamed by Claude. Reviewer says "looks good" — that's another model's opinion, subject to drift and reward hacking.

This distilled into FB-0011's three required conditions for bounded-retry contracts: mechanical exit signal, iteration cap *paired with* orthogonal abort, explicit reward-hacking guards.

---

## Part 3: Comprehensive field survey

*Four research streams covering Anthropic + frontier labs + AI-native companies + frameworks.*

### 3.1 Anthropic ecosystem (sub-agents, skills, plugins, hooks, SDK)

| Surface | Documented pattern | Source |
|---|---|---|
| **Sub-agents** | *"Each subagent runs in its own context window... Subagents cannot spawn other subagents."* Flat orchestration. | [code.claude.com/docs/en/sub-agents](https://code.claude.com/docs/en/sub-agents) |
| **Skills** | Progressive disclosure (metadata / SKILL.md / bundled files). **No documented chain primitive.** | [platform.claude.com/docs/en/agents-and-tools/agent-skills/overview](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview) |
| **Plugins** | Packaging unit (`skills/` + `agents/` + `hooks/` + MCP). Orchestration is the consumer's responsibility. | [code.claude.com/docs/en/plugins](https://code.claude.com/docs/en/plugins) |
| **Hooks** | PreToolUse: `allow`/`deny`/`ask`/`defer`. PostToolUse: can only inform. Stop hook can prevent stopping. | [code.claude.com/docs/en/hooks](https://code.claude.com/docs/en/hooks) |
| **Agent SDK** | *"With the Client SDK you implement a tool loop. With the Agent SDK, Claude handles it."* | [code.claude.com/docs/en/agent-sdk/overview](https://code.claude.com/docs/en/agent-sdk/overview) |
| **`/loop` skill** | Prompt-based, model self-paces; for wall-clock polling, not goal-seeking iteration | [scheduled-tasks](https://code.claude.com/docs/en/scheduled-tasks) |

**Key Anthropic-internal usage pattern** ([How Anthropic teams use Claude Code](https://claude.com/blog/how-anthropic-teams-use-claude-code)): Product Design "give Claude abstract problems, let it work autonomously, then review solutions before final refinements." Security Engineering "guide Claude through pseudocode stages with periodic check-ins."

**This is *intermittent steering*, not gates** — a third HITL placement category beyond Flow's "plan + merge + LOW-confidence" gate triple. Looser; only viable for highly-skilled operators.

**Notable Anthropic silences:**
- No published canonical multi-skill orchestration recipe.
- No documented oscillation prevention or cycle caps for Claude Code product surfaces.
- No "chain skills" primitive (skills are session-scoped, loaded progressively, no `chain(skill_a, skill_b)` API).
- Slash command chaining is emergent, not blessed.

### 3.2 OpenAI / Google / Microsoft / Meta

| Lab | Sequencing primitive | HITL checkpoint | Cycle cap | Default mode |
|---|---|---|---|---|
| **OpenAI Agents SDK** | Handoffs + agents-as-tools | Tool-level `needsApproval` interrupt with resumable state | Per-run `max_turns` | Agentic (LLM-decided) |
| **Swarm** (deprecated) | Handoffs only | None | None | Agentic |
| **Responses API** | App code owns the loop | Developer-implemented | Developer-implemented | Whatever the app codes |
| **Google ADK** | `SequentialAgent`, `ParallelAgent`, `LoopAgent` + LLM routing | Not first-class | **Required for LoopAgent** | DAG-first, agentic opt-in |
| **MS Agent Framework / Magentic** | Sequential, Concurrent, Handoff, Group Chat, Magentic | Plan signoff (on by default in .NET) | `max_rounds`, `max_stalls`, `max_resets` | Agentic with deterministic safety nets |
| **Llama Stack** | Agent turns within session | Not documented | Not documented | Undefined |

**Two findings most relevant for Flow:**

**Google ADK `LoopAgent` *requires* termination** ([adk.dev/agents/workflow-agents/loop-agents](https://adk.dev/agents/workflow-agents/loop-agents/)):
> *"The LoopAgent itself does not inherently decide when to stop looping. You must implement a termination mechanism to prevent infinite loops."*

Two documented mechanisms: max iteration count, and sub-agent setting `tool_context.actions.escalate = True`. Exactly Flow's posture in Step 1c.

**Microsoft Magentic ships a stall counter** ([learn.microsoft.com/en-us/agent-framework/user-guide/workflows/orchestrations/magentic](https://learn.microsoft.com/en-us/agent-framework/user-guide/workflows/orchestrations/magentic)):
> *"Consecutive non-progressing rounds increment a stall counter, and exceeding the configured maximum triggers an automatic reset and replan."*

**This is the closest structural analog to Flow's diff-hash detector across the entire surveyed field.** Magentic counts non-progressing rounds; Flow detects exact-diff oscillation. Independent convergence on the same defensive idea — worth citing in FB-0011.

**Magentic also defaults plan signoff *on* in .NET:**
> *"Plan review is on by default (RequirePlanSignoff defaults to true)."*

Matches Flow's plan-approval gate semantically.

### 3.3 AI-native companies

13 companies surveyed for public material on agent workflows.

| Company | Orchestration model | Human checkpoint | Cycle cap surface |
|---|---|---|---|
| **Notion** (3.0) | Single-agent with workspace tools | Implicit (review pages) | "Up to 20 minutes" wall-clock |
| **Linear** | Tool surface (MCP) | PR/issue triage by humans | None — Linear is the target |
| **Vercel** AI SDK | Single-agent-with-tools | Developer-implemented | **`stepCountIs` — first-class step counter** |
| **Stripe** Agent Toolkit | Tool surface, multi-framework | Per-card spending limit (credentials = cap) | Credential issuance is upstream gate |
| **Ramp** Inspect | Sandbox-per-session via Modal | PR review (~30% of merged PRs agent-authored) | Modal sandbox timeout |
| **Block Goose** | Single-agent + extensions (MCP), Recipes for reusable runs | Implicit | None published |
| **Cursor** | Foreground (watch + redirect) / Background (clear scope) | Every agent PR gets human review | Not published as a number |
| **Replit** Agent 3 | Up to 200 min autonomous + checkpoints + rollback | **Mandatory pre-coding plan approval** | "200 minutes" wall-clock |
| **GitHub** Copilot | Ephemeral Actions workspace, draft PR | Draft PR review + CI requires approval | Actions runner timeout |
| **Anthropic-internal** | Intermittent steering, not rigid gates | Periodic check-ins | `CLAUDE.md` files as scaffolding |
| **Datadog Bits AI SRE** | Single-agent that validates own findings | Slack/Teams delivery | N/A |
| **Snowflake Cortex Agents** | **Multi-agent**: Analyst + Search under orchestrator | Implicit | N/A |
| **Cloudflare Project Think** | **Multi-agent**: parent + sub-agents as Durable Objects | Workflow signals | Durable Object lifecycle |

**Distinctive findings:**

- **Only Vercel ships a numeric step counter as a first-class API** — `stepCountIs` in the AI SDK. ([vercel.com/blog/you-can-just-ship-agents](https://vercel.com/blog/you-can-just-ship-agents))
- **Only Replit publicly documents a mandatory pre-coding plan gate.** Closest analog to Flow's plan-approval gate.
- **~80% of public material describes single-agent-with-tools.** Multi-agent (Cloudflare, Snowflake, Cursor parallel) is still frontier.
- **GitHub Copilot's draft-PR + CI-requires-approval double gate** is structurally similar to Flow's merge gate.

**Two surprises:**
- **Anthropic's own internal pattern is the loosest in the field** — intermittent steering, not gates. Worth knowing about even if Flow doesn't adopt it.
- **Stripe moves the gate upstream** — agents get money-moving capability but constrained by per-card caps the developer sets when minting the card. *"The credential itself is the cycle cap."*

### 3.4 Framework patterns

| Framework | Stopping conditions | HITL primitive | Reward-hacking guidance |
|---|---|---|---|
| **LangGraph** | User-encoded in graph state | `interrupt()` + `Command(resume=...)`; approve / edit-state / review-tool-call | Silent |
| **CrewAI** | Process termination by manager agent | Weak | Silent |
| **Pydantic AI** | Configurable retry budget on validation failures | Weak | Silent |
| **DSPy** | Optimizer convergence (not loop control) | None | Silent — and optimizers are structurally vulnerable to metric gaming |
| **Inngest AgentKit** | Step-level retry policies | Waitpoints | Silent |
| **Trigger.dev** | Per-iteration cap (examples use 10) | First-class waitpoints | Silent |
| **Temporal** | Step-level retries + workflow-level timeouts | Signals | Silent |
| **MCP** | N/A (protocol, not orchestrator) | N/A | N/A |

**Cross-cutting framework finding:**
> *"Oscillation detection and convergence criteria are essentially absent from official docs across all eight frameworks."*

None of the major frameworks ship a built-in stop-on-no-progress check. This is left to user code everywhere except Magentic.

**The biggest field-wide gap: reward hacking.**
> *"Nearly silent across official sources. Anthropic's evaluator-optimizer section recommends iterative refinement with 'clear evaluation criteria' but does not warn about the actor-evaluator collusion problem. DSPy's optimizers explicitly filter 'traces according to metric performance,' which is structurally vulnerable to metric-gaming, yet the docs do not address it."*

Flow's FB-0011 explicit "do not modify tests / no `@ts-ignore`" guards are **ahead of the published frontier on this dimension.**

---

## Part 4: The four cross-cutting questions

### 4.1 How do the docs say to chain skills in sequence?

**Anthropic:** essentially silent. Skills load progressively per session; chaining is emergent.

**Sub-agent chaining IS documented:**
> *"For multi-step workflows, ask Claude to use subagents in sequence. Each subagent completes its task and returns results to Claude, which then passes relevant context to the next subagent."* — [Sub-agents docs](https://code.claude.com/docs/en/sub-agents)

But: top-level Claude is the orchestrator; sub-agents can't chain each other.

**Other frameworks have explicit sequencing primitives:**
- LangGraph: graph nodes + edges, with cycles and conditional edges
- Magentic Semantic Kernel: `Sequential` orchestration — *"Passes the result from one agent to the next in a defined order"*
- Google ADK: `SequentialAgent`
- CrewAI: `sequential` and `hierarchical` Process modes
- OpenAI Agents SDK: handoffs (transfer control) + agents-as-tools (caller keeps control)

**Implication for Flow:** the `Skill('a'); Skill('b')` pattern in `/flow:ship` is an emergent sequencing approach that works but isn't blessed. See §6.1 below for alternatives worth considering.

### 4.2 Agent orchestrators and sub-agents

**Anthropic's model: flat.** Sub-agents are workers; top-level Claude is the orchestrator. No multi-level nesting.

**Most other frameworks support hierarchical orchestration:**
- CrewAI `hierarchical` Process
- Cloudflare Project Think (sub-agents as child Durable Objects)
- Snowflake Cortex Agents (Analyst + Search under orchestrator)
- Magentic Manager agent
- LangGraph supervisor nodes calling sub-graphs

**Implication for Flow:** Flow follows Anthropic's flat model. `/flow:staff-review`'s 4-lens parallel fan-out is the maximum complexity within this rule, and it works fine.

### 4.3 Where do humans show up?

**Three converging placements:**

| Placement | Who does it | Why |
|---|---|---|
| Plan approval (pre-execution) | Replit Agent 3, Magentic .NET, **Flow** | Catches scope drift and bad premises before any code is written |
| Tool-call gating (mid-execution) | OpenAI `needsApproval`, Anthropic hooks (`ask`), LangGraph `interrupt()` | Side-effecting actions need confirmation |
| Merge / PR review (post-execution) | GitHub Copilot, Cursor, Ramp Inspect, Replit, **Flow** | Universal terminal gate; nobody removes this |

**Where humans are increasingly NOT present:**
- In-loop quality validation (replaced by mechanical preflight — Flow Step 1c, Vercel `stepCountIs`, Modal sandboxes)
- Self-correction on mechanical failures (replaced by retry budgets — Pydantic AI, Magentic stall reset, Flow N=3)
- Intermediate observability (replaced by tracing — OpenAI Agents SDK, Copilot session logs)

**The Anthropic-internal *intermittent steering* pattern is a fourth placement** — not gates, but check-ins. Most product systems still default to gates.

### 4.4 What's increasingly automated?

| Function | Was manual | Now automated by |
|---|---|---|
| Quality validation | Engineer running locally | Mechanical preflight loops (Flow Step 1c, Modal sandboxes, Vercel SDK retries) |
| Tool selection | Engineer choosing tool | Tool-calling LLMs + MCP |
| Multi-step planning | Engineer breaking down | Orchestrator agents (Magentic manager, Cortex) |
| Self-validation | Engineer checking work | Datadog Bits, plan-critic / auditor in Flow |
| Failure recovery | Engineer reading stack trace | Step retries (Temporal, Inngest), bounded retry loops (Flow), validation-error replay (Pydantic AI) |
| Long-running survival | Engineer babysitting | Durable execution (Temporal, Inngest, Trigger.dev), session resumption (LangGraph checkpointers) |
| Context isolation | Engineer managing scratch | Sub-agents with isolated context (Anthropic, OpenAI, Cloudflare) |

**Not yet automated anywhere:**
- The merge decision.
- Reward-hacking detection during iterative refinement.
- Cross-session institutional knowledge (Flow's `dev-docs/` + memory tool are bespoke).

---

## Part 5: Comparison to previous findings

The first research pass cited three sources: *Building Effective Agents*, Claude Code *common-workflows*, and the *2026 Agentic Coding Trends Report*. **All three findings hold up under deeper research,** and the deeper research **strengthens** the case for Flow's bounded-retry approach:

1. **"Include stopping conditions (max iterations)" — confirmed canonical.** ADK *requires* it. Magentic ships *three* caps. Trigger.dev examples cap at 10. Anthropic's prescription is the minimum bar; everyone who's operationalized loops has gone beyond it.
2. **"Output quality measurable objectively" — confirmed essential.** The 2026 report's *"without explicit success criteria, verification becomes guesswork"* restated across the field: Vercel "predictable agent loop," DSPy "metric-driven," Cursor "success is objectively measurable."
3. **"Pause for human feedback at checkpoints" — confirmed universal.** Field converged on plan-approval + tool-gating + merge-review. Flow's plan + LOW-confidence + merge triple-gate is tighter than the field median (which usually has just merge) but looser than Magentic (which has all of Flow's + a stall reset).

**What was missing from the prior research:**
- **Microsoft Magentic's `max_stall_count`** — single closest structural analog to Flow's diff-hash detector. Worth citing in FB-0011.
- **The Anthropic-internal pattern of *intermittent steering*** — different HITL mode worth knowing.
- **Vercel `stepCountIs` API** — concrete numeric step-capping primitive, validates Flow's N=3 as a class of decision (just a different number).
- **The field's near-total silence on reward hacking** — Flow's FB-0011 explicit guards put it ahead of the curve, not behind.

---

## Part 6: Comparison to Flow's code (v1.2.4)

### 6.1 Where Flow aligns with field consensus

| Flow pattern | Field analog | Source |
|---|---|---|
| 11-step deterministic workflow | Anthropic prompt-chaining + workflow-over-agent default | Building Effective Agents |
| `/flow:staff-review` 4-lens parallel fan-out | Anthropic parallelization + ADK ParallelAgent + SK Concurrent | Multiple |
| Sub-agents called from top-level Claude | Anthropic flat-orchestration rule | code.claude.com/docs/en/sub-agents |
| Bounded-retry preflight (Step 1c) | Anthropic evaluator-optimizer + ADK LoopAgent + Magentic max_rounds | All three |
| Plan-approval human gate | Replit Agent 3, Magentic .NET RequirePlanSignoff | Their docs |
| Merge as terminal gate | Universal | Everyone |
| PreToolUse hooks for safety | Anthropic hooks API | code.claude.com/docs/en/hooks |
| Loud-warning on unset config | Inngest "deterministic routing" + FB-0006/0007 | Flow-internal |

### 6.2 Where Flow takes defensible non-consensus positions

| Flow choice | Field median | Why Flow's choice is defensible |
|---|---|---|
| **Single-pass reviewers** (audit, plan-critic, lens agents — none iterate) | Mixed: Datadog "validates own findings"; OpenAI handoffs imply iteration | Reward hacking — looping LLM-as-judge teaches phrase-around-reviewer behavior. Field is silent on this; Flow has FB-0011 explicit. |
| **Two-sided skeptical layer** (plan-critic + auditor) | One-sided is norm: Replit pre, Datadog post | Two failure modes (bad premise / unverified completion) are orthogonal; covering both is cheap. |
| **Diff-hash oscillation detection** | Absent in all 8 frameworks | Magentic stall counter is closest analog; Flow's exact-diff hash is stricter test that catches A↔B↔A precisely. |
| **No standalone `/flow:loop` skill** | Vercel `stepCountIs`, ADK `LoopAgent` are first-class | Flow's loop fires only inside `/flow:ship` so surrounding gates always apply — prevents misuse without ceremony. |
| **N=3 hardcoded, no `preflightMaxAttempts` slot** | Magentic has 3 configurable caps; ADK requires explicit max | FB-0003 — don't ship unproven slots. Cheap to add if real projects bite. |
| **`dev-docs/` + FB-XXXX feedback log** | No published framework standard | Cross-session institutional memory; Flow-original. |
| **Prompt-driven retry contract (vs shell harness)** | Magentic, Temporal, Inngest are shell/code-driven | Matches Flow's existing idiom; observable via per-attempt log line. Defensible until dogfood proves prompt-discipline insufficient. |

### 6.3 Where Flow has gaps the field has solved

| Gap | Field solution | Cost to adopt | Priority |
|---|---|---|---|
| No durable execution — sessions don't survive crashes | LangGraph checkpointers, Temporal, Inngest | High | LOW — Claude Code sessions usually short |
| No tracing primitive | OpenAI Agents SDK tracing, LangSmith | Medium | MEDIUM — would help dogfood debugging |
| No `needsApproval` tool-level interrupt | OpenAI `needsApproval`, Anthropic hooks `ask` | Low (use existing PreToolUse `ask`) | **MEDIUM — would harden the no-disable-tests rule mechanically** |
| No stall counter beyond exact-diff oscillation | Magentic `max_stall_count` | Low (track stderr error class change) | LOW — N=3 already exhausts these cases |
| No held-out evaluator — eval fixtures in same repo | DSPy compiled metrics, OpenAI Evals | High | LOW |
| No managed-agent hosting | Anthropic Managed Agents, OpenAI Responses, Cloudflare | Out of scope | N/A — Flow is a Claude Code plugin |

---

## Bibliography

**Anthropic:**
- [Building Effective Agents](https://www.anthropic.com/research/building-effective-agents)
- [Equipping Agents for the Real World with Agent Skills](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)
- [How Anthropic Teams Use Claude Code](https://claude.com/blog/how-anthropic-teams-use-claude-code)
- [How Anthropic Uses Claude for Cybersecurity](https://claude.com/blog/how-anthropic-uses-claude-cybersecurity)
- [Sub-agents](https://code.claude.com/docs/en/sub-agents) | [Skills](https://code.claude.com/docs/en/skills) | [Plugins](https://code.claude.com/docs/en/plugins) | [Hooks](https://code.claude.com/docs/en/hooks) | [Agent SDK](https://code.claude.com/docs/en/agent-sdk/overview) | [Common workflows](https://code.claude.com/docs/en/common-workflows) | [Scheduled tasks](https://code.claude.com/docs/en/scheduled-tasks)
- [2026 Agentic Coding Trends Report](https://resources.anthropic.com/hubfs/2026%20Agentic%20Coding%20Trends%20Report.pdf)

**OpenAI / Google / Microsoft:**
- [OpenAI Agents SDK](https://developers.openai.com/api/docs/guides/agents) | [Orchestration + handoffs](https://developers.openai.com/api/docs/guides/agents/orchestration) | [Guardrails + human review](https://developers.openai.com/api/docs/guides/agents/guardrails-approvals) | [A Practical Guide to Building Agents](https://openai.com/business/guides-and-resources/a-practical-guide-to-building-ai-agents/)
- [Google ADK — Loop Agents](https://adk.dev/agents/workflow-agents/loop-agents/) | [Build multi-agentic systems using Google ADK](https://cloud.google.com/blog/products/ai-machine-learning/build-multi-agentic-systems-using-google-adk)
- [Microsoft Agent Framework — Magentic Orchestrations](https://learn.microsoft.com/en-us/agent-framework/user-guide/workflows/orchestrations/magentic) | [Semantic Kernel Agent Orchestration](https://learn.microsoft.com/en-us/semantic-kernel/frameworks/agent/agent-orchestration/)

**AI-native companies:**
- Notion: [3.0 release](https://www.notion.com/releases/2025-09-18) | [Introducing Notion 3.0](https://www.notion.com/blog/introducing-notion-3-0)
- Linear: [MCP](https://linear.app/docs/mcp) | [Linear Agent](https://linear.app/docs/linear-agent)
- Vercel: [You can just ship agents](https://vercel.com/blog/you-can-just-ship-agents) | [Agentic Infrastructure](https://vercel.com/blog/agentic-infrastructure)
- Stripe: [Giving agents the ability to pay](https://stripe.com/blog/giving-agents-the-ability-to-pay) | [Agent Toolkit](https://github.com/stripe/agent-toolkit)
- Ramp: [Inspect coding agent on Modal](https://modal.com/blog/how-ramp-built-a-full-context-background-coding-agent-on-modal) | [Ramp Research](https://www.engineering.fyi/article/meet-ramp-research-our-agentic-data-analyst)
- Block Goose: [GitHub](https://github.com/block/goose) | [Recipe for Success](https://block.github.io/goose/blog/2025/05/06/recipe-for-success/)
- Cursor: [Agent best practices](https://cursor.com/blog/agent-best-practices)
- Replit: [Agent docs](https://docs.replit.com/replitai/agent)
- GitHub: [Coding agent announcement](https://github.blog/news-insights/product-news/github-copilot-meet-the-new-coding-agent/) | [About coding agent](https://docs.github.com/copilot/concepts/agents/coding-agent/about-coding-agent)
- Datadog: [Building Bits AI SRE](https://www.datadoghq.com/blog/building-bits-ai-sre/)
- Snowflake: [Multi-agent orchestration](https://www.snowflake.com/en/developers/guides/multi-agent-orchestration-snowflake-intelligence/)
- Cloudflare: [Project Think](https://blog.cloudflare.com/project-think/) | [Workflows v2](https://blog.cloudflare.com/workflows-v2/)

**Frameworks:**
- [LangGraph](https://docs.langchain.com/oss/python/langgraph/overview) | [LangChain](https://docs.langchain.com/oss/python/langchain/overview)
- [Pydantic AI](https://pydantic.dev/docs/ai/overview/) | [CrewAI](https://docs.crewai.com/introduction) | [DSPy](https://dspy.ai/)
- [Inngest AgentKit](https://www.inngest.com/blog/ai-orchestration-with-agentkit-step-ai) | [Trigger.dev AI agents](https://trigger.dev/product/ai-agents) | [Temporal — agentic AI](https://temporal.io/blog/build-resilient-agentic-ai-with-temporal)
- [Model Context Protocol](https://modelcontextprotocol.io/introduction)

---

## Open questions (for follow-up research)

- **Anthropic Agent Teams preview** — does this exist? What's been announced?
- **Sequential skill chaining alternatives** beyond `Skill('a'); Skill('b')` — supervisor agents, workflow-engine-hosted chains, DAG-style orchestration, plan-and-execute patterns. Which are production-validated?
- **Meta-skill / orchestration-skill patterns** — has anyone shipped a "skill that orchestrates other skills" primitive? Cursor `/` commands chaining? GPT actions chaining other GPTs?

These are addressed in **Part 7 (pending).** Research dispatched 2026-05-27; will be appended on completion.

---

## Part 7: Skill-chaining alternatives + Anthropic Agent Teams

*Research completed 2026-05-27.*

### 7.1 Anthropic Agent Teams + Managed Agents (CONFIRMED REAL)

Anthropic has shipped **three layered multi-agent primitives** in 2025–2026:

| Primitive | Released | Scope | Cost |
|---|---|---|---|
| **Multi-Agent Research System** (orchestrator-worker blueprint) | June 2025 | Conceptual / SDK pattern | ~15x token cost vs single-agent |
| **Claude Code Agent Teams** (experimental flag) | February 5, 2026 with Opus 4.6 / Claude Code v2.1.32+ | Cross-session multi-Claude coordination; peer messaging + shared task list | ~3-7x single session |
| **Claude Managed Agents** (hosted API) | April 8, 2026 | Lead + specialists on shared filesystem, sandboxed, long-running | $0.08/session-hour + tokens |

**Key distinction surfaced by the research** (the Anthropic-marketing copy is thin; third-party guides clarify):

> *"Subagents run within a single session and report results back to the parent. They can't talk to each other. Agent Teams removes that bottleneck. Teammates message each other directly, claim tasks from a shared list, and challenge each other's findings."* — [CloudZero](https://www.cloudzero.com/blog/claude-code-agents/) / [SitePoint](https://www.sitepoint.com/anthropic-claude-code-agent-teams/) / [Developers Digest](https://developersdigest.tech/) (Anthropic's own copy is thinner).

**Multi-agent research system reported gains** ([anthropic.com/engineering/multi-agent-research-system](https://www.anthropic.com/engineering/multi-agent-research-system)):
> *"A system with Claude Opus 4 as the lead agent and Claude Sonnet 4 as supporting subagents outperformed a single-agent setup by more than 90 percent."*

**Managed Agents framing** ([anthropic.com/engineering/managed-agents](https://www.anthropic.com/engineering/managed-agents)):
> *"A lead agent [can] break a job into pieces and delegate each piece to a specialist sub-agent with its own model, prompts, and tools, with the sub-agents working in parallel on a shared file system."*

**Critical documented gap across all three primitives:** Anthropic does NOT publish a verification protocol for how the lead/orchestrator validates worker output before integrating it. *"Subagents return findings to the LeadResearcher who synthesizes these results and decides whether more research is needed"* — but no explicit verification protocol. The orchestrator just reads and reasons.

**Implication for Flow:** Agent Teams + Managed Agents validate the *direction* Flow is going (workflow-with-skeptical-reviewers), but they don't provide a verification primitive Flow can adopt. Flow's auditor + plan-critic + lens-staff-review *is* the verification layer the field has not standardized.

**Should Flow adopt Agent Teams?** Not yet. (a) Experimental flag — not production-stable. (b) 3-7x cost. (c) Flow already has parallel lens spawning via in-session sub-agents which is cheaper. (d) Agent Teams' peer-messaging primitive is overkill for Flow's deterministic 11-step workflow.

### 7.2 Sequential skill-chaining beyond `Skill('a'); Skill('b')`

**Two production camps** for verification-aware orchestration:

**Camp A: LLM-as-orchestrator** (prompt-mediated verification)
- **LangGraph `langgraph-supervisor-py`**: `create_supervisor` factory; *"supervisor sits at the center of a star topology where every worker reports back; supervisor decides next step or terminates with FINISH"* ([LangGraph Supervisor](https://reference.langchain.com/python/langgraph-supervisor)).
- **Microsoft Magentic-One**: *"A dedicated Magentic manager coordinates a team of specialized agents, selecting which agent should act next based on the evolving context, task progress, and agent capabilities"* ([Magentic on Microsoft Learn](https://learn.microsoft.com/en-us/agent-framework/workflows/orchestrations/magentic)).
- **Anthropic Multi-Agent Research System**: lead agent reads subagent findings and reasons about whether to continue.

In all three, verification is **prompt-driven** — orchestrator reads worker's structured output and decides. No formal verifier.

**Camp B: Engine-as-orchestrator** (code-side verification + durable replay)
- **Inngest AgentKit**: *"checkpoints every step of a workflow, and if your server crashes mid-execution, the workflow picks up exactly where it left off"* ([Inngest AgentKit](https://agentkit.inngest.com/)).
- **Trigger.dev**: *"No execution time limit, allowing tasks to run for hours or days, and tasks can pause and resume via wait primitives without holding an open connection"* ([Trigger.dev](https://trigger.dev/)).
- **Temporal**: *"Durable Execution ensures workflows are completed even in the face of server or network failures by maintaining an Event History which preserves state indefinitely."*

Camp B verification is **mechanical** — step returns typed result; engine checkpoints; retries on failure with backoff.

**Plan-and-Execute** has crystallized as a 2026 production pattern with documented cost profile:
> *"The planner runs once on a capable model, the executor runs N times on a cheap one, and the cost profile is roughly 1 * strong_model + N * cheap_model, which for N > 3 tends to beat ReAct on the same task."* ([SurePrompts](https://sureprompts.com/blog/plan-and-execute-prompting); [outcomeschool](https://outcomeschool.com/blog/plan-and-execute-agent))

Production-form is layered: *"A Plan-and-Execute outer loop, where each executor step is a ReAct agent with its own tools, and the whole run is wrapped in a Reflection pass that re-runs the failing tests"* ([DEV / gabrielanhaia](https://dev.to/gabrielanhaia/react-plan-and-execute-or-reflection-the-three-agent-patterns-every-engineer-needs-in-2026-355p)).

**Critic / proposer chains** are the closest analog to Flow's auditor + plan-critic. Documented design rule:
> *"The critique must be structured, not free-form. In production environments, the default is 2 revision passes."* ([AgentWiki](https://agentwiki.org/agent_design_patterns))

Documented failure modes ([Self-Correcting Multi-Agent AI Systems](https://medium.com/@sohamghosh_23912/self-correcting-multi-agent-ai-systems-building-pipelines-that-fix-themselves-010786bae2db)):
1. **Critic-generator collusion when both use same model** ← *applies to Flow today*
2. Over-correction on edge cases
3. Critique quality degrades on subjective dimensions

### 7.3 Meta-skills / orchestration-skill patterns

**Anthropic does not document skill-invokes-skill.** Reading [code.claude.com/docs/en/skills](https://code.claude.com/docs/en/skills) end-to-end: `Skill(...)` appears only in **permission syntax** (`Skill(commit)`), never as an imperative invocation primitive. The composition surface Anthropic *does* document is `context: fork` + `agent:` frontmatter — i.e., skill-as-subagent-prompt, not skill-calls-skill.

**Block's Goose Recipes is the closest production analog.** [Goose Recipes](https://block.github.io/goose/docs/guides/recipes/) ship as "reusable workflows that package extensions, prompts, and settings." Sub-Recipes are first-class. Active proposal ([Goose discussion #6202](https://github.com/block/goose/discussions/6202)) unifies recipes / skills / subagents under two execution verbs:

- **`load`** — *"Inject sources into the current context — Teach me this"*
- **`delegate`** — *"Execute sources in isolated subagents — Do this for me"*

The framing: *"The tool determines the execution mode, not the file format."* This is the most thoughtful public take on resolving the meta-skill question: don't argue about whether a skill "calls" another skill; let the invocation verb decide.

**Third-party convention: thin orchestrator + modular children** (MindStudio, [shanraisshan/claude-code-best-practice](https://github.com/shanraisshan/claude-code-best-practice)):

> *"The orchestrator-plus-child-skills pattern gives you a scalable foundation: thin orchestrators that coordinate, modular child skills that execute. Keeping under 10-15 skills per orchestrator is generally good practice; beyond that, Claude can struggle to select the right skill reliably."* ([MindStudio: modular skills](https://www.mindstudio.ai/blog/modular-claude-skills-skill-systems))

**Anti-pattern documented**: *"Isolated skills and mega-skills both fail at scale — isolated skills can't combine, mega-skills collapse under their own weight when one giant prompt tries to do everything."*

**Caveat:** MindStudio is a vendor publishing Claude Skills marketing. Their framework is internally consistent but is not Anthropic guidance. I could not find equivalent Anthropic-authored prescriptive material.

### 7.4 The most actionable cross-cutting finding

> *"Multi-step workflows break at the first unexpected state when there's no shared state object and no per-step success/error field."* ([MindStudio: orchestrator skill](https://www.mindstudio.ai/blog/what-is-orchestrator-skill-claude-code))

**The production-validated pattern: structured-result contracts.** Every skill invoked by an orchestrator should return:

```typescript
{
  status: 'success' | 'skipped' | 'failed',
  reason?: string,        // why it skipped/failed
  findings?: Finding[],   // what it produced
  followUps?: FollowUp[], // what's deferred
}
```

The orchestrator checks each step's `status` before proceeding — *"giving fine-grained control over halting, skipping, retrying, or routing to error handling"* ([MindStudio: how to build skill systems](https://www.mindstudio.ai/blog/how-to-build-skill-systems-claude-code)).

**This maps directly to Flow's existing PR E+ follow-up #1** ("Structured exit-status marker for /flow:*review early-exit vs clean-run") — which was deferred. PR D added `STATUS: SKIPPED` for the early-exit path; symmetric `STATUS: CLEAN` / `STATUS: FINDINGS` for the substantive paths is the unfinished work. **The research validates this as the highest-leverage next move for `/flow:ship`'s orchestration robustness — not a "v1.3+ enhancement" but a current best-practice gap.**

### 7.5 Emerging patterns worth tracking (not adopting)

| Pattern | Signal | Source | Should Flow adopt? |
|---|---|---|---|
| **Lead-agent + persistent shared filesystem** for verification handoff | **Strong** | Anthropic Managed Agents + Agent Teams + research system | NOT YET — Flow's surface (Claude Code plugin) doesn't expose shared filesystem at orchestration layer; revisit if Anthropic ships skill-to-skill filesystem primitive |
| **Goose's `load` vs `delegate` execution-mode split** | **Moderate** | [Goose #6202](https://github.com/block/goose/discussions/6202) (single thoughtful proposal, not yet shipped) | NOT YET — wait for Anthropic to react or Goose to ship it; signal is one engineering discussion, not multiple converged sources |
| **`skills.json` dependency manifest** for cross-skill composition | **Weak-moderate** | [agentskills #210 RFC](https://github.com/agentskills/agentskills/discussions/210) (open, output contracts explicitly deferred) | NO — the load-bearing piece (output contracts) is unresolved; adopting prematurely is FB-0003 territory |

### 7.6 Patterns to avoid (Flow-specific applications)

| Anti-pattern | Documented failure mode | Flow status |
|---|---|---|
| **Mega-skills** (orchestration + execution in one prompt) | *"Mega-skills collapse under their own weight"* | **Flow is borderline** — `/flow:ship` does orchestration AND writes history.md/plan.md/feedback.md. Security/a11y/memory passes should NEVER get inlined. |
| **Same-model critic+generator pairs** | *"Critic-generator collusion when both use same model"* | **Flow has this weakness** — auditor and audited session both run on the same Claude model. Bounded by shared blind spots. Mitigation: Haiku/Sonnet for auditor (future PR). |
| **Unbounded critique-revise loops** | Production default is 2 passes then escalate | **Flow is conservative** — single-pass auditor + plan-critic, then human. Stricter than field default. Consistent with FB-0011. |
| **Orchestrator-that-also-implements** | *"Implementation noise pollutes architectural decision-making when Claude acts as both architect and implementer"* | **Flow has elements of this** — `/flow:ship` orchestrates AND writes doc entries. Acceptable for now (doc entries are simple); revisit if /flow:ship grows. |
| **Skill chains without structured-result contracts** | *"Multi-step workflows break at the first unexpected state"* — most actionable finding | **Flow has this gap** — PR E+ follow-up #1 (deferred). **Should ship in PR H3.** |

### 7.7 Synthesis — what changes for Flow

The single highest-leverage finding from this pass: **structured-result contracts for skills invoked by `/flow:ship`**. This is the production-validated convention across multiple sources, addresses a Flow gap already known and deferred (PR E+ follow-up #1), and aligns with the field's strongest orchestration-robustness pattern. **It is more impactful than the test-edit reward-hacking hook the v1 PR H3 plan proposed.**

Two secondary findings:
- **Same-model critic collusion is a known weakness in Flow's design.** Worth surfacing in feedback.md as a tracked limitation; mitigation is a future PR (auditor on a different model).
- **Agent Teams and Managed Agents are real but premature for Flow.** Validates the direction; not adoption candidates.

Updated PR H3 plan should:
- Keep Phase 1 (documentation grounding — Magentic + evaluator-optimizer)
- **Replace Phase 2** (test-edit hook) with **structured-result contracts for Skill('flow:security-review') + Skill('flow:accessibility-review')** invocations in `/flow:ship` Step 2.
- Move the test-edit hook to a separate PR H4 candidate (still real value, but lower-leverage than fixing the orchestration gap first).
- Add FB-0012 capturing same-model-critic-collusion as a tracked design limitation.

---

## Updated bibliography (Part 7 additions)

**Anthropic Agent Teams + Managed Agents:**
- [Anthropic engineering: multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system)
- [Anthropic engineering: Managed Agents](https://www.anthropic.com/engineering/managed-agents)
- [CloudZero on Agent Teams](https://www.cloudzero.com/blog/claude-code-agents/)
- [SitePoint Agent Teams setup guide](https://www.sitepoint.com/anthropic-claude-code-agent-teams/)
- [InfoQ on Managed Agents launch](https://www.infoq.com/news/2026/04/anthropic-managed-agents/)
- [9to5Mac Managed Agents update](https://9to5mac.com/2026/05/07/anthropic-updates-claude-managed-agents-with-three-new-features/)

**Sequential chaining patterns:**
- [LangGraph Supervisor reference](https://reference.langchain.com/python/langgraph-supervisor)
- [Magentic on Microsoft Learn](https://learn.microsoft.com/en-us/agent-framework/workflows/orchestrations/magentic)
- [Microsoft Research: Magentic-One](https://www.microsoft.com/en-us/research/articles/magentic-one-a-generalist-multi-agent-system-for-solving-complex-tasks/)
- [Focused.io: Multi-agent orchestration in LangGraph](https://focused.io/lab/multi-agent-orchestration-in-langgraph-supervisor-vs-swarm-tradeoffs-and-architecture)
- [Latitude: top tools event-driven LLM workflow](https://latitude.so/blog/top-tools-event-driven-llm-workflow-design)
- [SurePrompts: Plan-and-Execute](https://sureprompts.com/blog/plan-and-execute-prompting)
- [outcomeschool: Plan-and-Execute agent](https://outcomeschool.com/blog/plan-and-execute-agent)
- [DEV: ReAct vs Plan-and-Execute vs Reflection](https://dev.to/gabrielanhaia/react-plan-and-execute-or-reflection-the-three-agent-patterns-every-engineer-needs-in-2026-355p)
- [arxiv 2509.08646: Resilient LLM Agents](https://arxiv.org/pdf/2509.08646)
- [arxiv 2601.13383: AgentForge skill DAG composition](https://arxiv.org/pdf/2601.13383)

**Critic patterns + failure modes:**
- [AgentWiki: agent design patterns](https://agentwiki.org/agent_design_patterns)
- [Genta: agentic design patterns guide](https://genta.dev/resources/agentic-design-patterns-guide)
- [Self-Correcting Multi-Agent AI Systems](https://medium.com/@sohamghosh_23912/self-correcting-multi-agent-ai-systems-building-pipelines-that-fix-themselves-010786bae2db)

**Meta-skill / orchestration-skill:**
- [Goose Recipes docs](https://block.github.io/goose/docs/guides/recipes/)
- [Goose discussion #6202: load vs delegate](https://github.com/block/goose/discussions/6202)
- [Goose discussion #5761: subagent integration](https://github.com/block/goose/discussions/5761)
- [PulseMCP: building agents with Goose](https://www.pulsemcp.com/building-agents-with-goose)
- [agentskills discussion #210: skills.json RFC](https://github.com/agentskills/agentskills/discussions/210)
- [MindStudio: how to build skill systems Claude Code](https://www.mindstudio.ai/blog/how-to-build-skill-systems-claude-code)
- [MindStudio: orchestrator skill Claude Code](https://www.mindstudio.ai/blog/what-is-orchestrator-skill-claude-code)
- [MindStudio: modular Claude skills systems](https://www.mindstudio.ai/blog/modular-claude-skills-skill-systems)
- [shanraisshan/claude-code-best-practice](https://github.com/shanraisshan/claude-code-best-practice/blob/main/orchestration-workflow/orchestration-workflow.md)
- [Claude Code skills docs](https://code.claude.com/docs/en/skills)
- [Anthropic platform: agent skills best-practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices)
