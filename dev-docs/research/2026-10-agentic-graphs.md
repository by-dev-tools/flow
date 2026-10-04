# Agentic graphs — is an explicit graph layer a useful addition to flow? (2026-10)

> **Status: RESEARCH, resolved: NO wholesale adoption; two small, already-validated-pattern
> follow-ups recommended.** Commissioned by Ben, dispatched by the orchestrator seat,
> 2026-10-04. Findings only — **no code changed, no decision made, nothing built**. All claims
> about flow's own shipped behavior are read from this checkout on `main` at commit `f6cd08f`
> (v1.57.0). Every external claim is cited to a primary source (Anthropic, OpenAI, LangChain/
> LangGraph official docs, Google ADK official docs, Microsoft official docs, or arXiv papers
> from identifiable authors); anything synthesized by a search tool rather than fetched directly
> from the cited page is marked **[search-synthesized, official domain]** rather than presented
> as a direct quote. Nothing here is from a personal blog or listicle — several appeared in
search results and were discarded.

## 0. The question, restated precisely

"Agentic graph" in the sources below means a specific, named thing: an orchestration layer with
**explicit nodes** (units of work), **explicit edges** (what runs next), **shared state** that
nodes read and write, **conditional routing** (edges chosen by a function over that state), and
**checkpoints** (persisted snapshots that let execution pause and resume). LangGraph is the
clearest working example of all five at once; the question is whether flow's three real surfaces
— the 11-step loop, the orchestrator/spawn suite, and the fresh-context reviewer fan-outs — would
be better off with that machinery, worse off, or (the actual answer) already structured the same
way without the library.

## 1. What the authoritative sources actually say

**Anthropic's own taxonomy of agentic patterns**, from "Building Effective Agents"
([anthropic.com/engineering/building-effective-agents](https://www.anthropic.com/engineering/building-effective-agents)),
draws the line at the top: **workflows** are "systems where LLMs and tools are orchestrated
through predefined code paths," while **agents** are "systems where LLMs dynamically direct
their own processes and tool usage, maintaining control over how they accomplish tasks." Five
composable workflow patterns are named — prompt chaining, routing, parallelization (sectioning
and voting), orchestrator-workers, and evaluator-optimizer — plus autonomous agents for the
genuinely unpredictable case. The framework stance is explicit and repeated across every
Anthropic source fetched for this doc: "we recommend finding the simplest solution possible, and
only increasing complexity when needed," and frameworks "often create extra layers of abstraction
that can obscure the underlying prompts and responses, making them harder to debug."

**Anthropic's multi-agent guidance is sharper still about cost**
([claude.com/blog/building-multi-agent-systems-when-and-how-to-use-them](https://claude.com/blog/building-multi-agent-systems-when-and-how-to-use-them)):
"Today, multi-agent systems are often applied in situations where a single agent would perform
better." Multi-agent implementations "typically use 3-10x more tokens than single-agent
approaches for equivalent tasks," and the three *justified* reasons to go multi-agent are named
exhaustively: **context protection**, **parallelization**, and **specialization**. Nothing about
graphs, state machines, or checkpointing appears anywhere in this source — the entire
justification is stated in terms of token cost and failure-mode count ("every additional agent
represents another potential point of failure, another set of prompts to maintain, and another
source of unexpected behavior"), never in terms of missing structure.

**Anthropic's own orchestrator-worker implementation**
([anthropic.com/engineering/built-multi-agent-research-system](https://www.anthropic.com/engineering/built-multi-agent-research-system))
is the closest primary-source analog to flow's orchestrator seat. A lead agent "decomposes
queries into subtasks and describes them to subagents," each subagent gets "an objective, an
output format, guidance on the tools and sources to use, and clear task boundaries" and runs in
"separate context windows," and the lead agent "synthesizes results and decides whether more
research is needed." This is **judgment-driven dispatch**, not a compiled graph: there is no
fixed node list decided in advance, the lead agent decides fan-out width and depth per query. The
one piece of explicit structure is the trailing **CitationAgent** — a fixed, final evaluator step
after the dynamic phase, which is itself the evaluator-optimizer pattern, not a graph.

**Anthropic's own answer to "when a single turn-by-turn agent isn't enough, but you don't want
a model's context to drive 100 agents"** is the Claude Agent SDK's dynamic-workflows cookbook
([platform.claude.com/cookbook/claude-agent-sdk-08-dynamic-workflows](https://platform.claude.com/cookbook/claude-agent-sdk-08-dynamic-workflows)),
and it is the single most load-bearing source in this doc because it is the actual mechanism this
very research task is running under (the `Workflow` tool). Its primitives are plain code —
`agent()`, `parallel()`, `pipeline()`, `phase()` — composed in an ordinary async script, not a
node/edge DSL: "the plan lives in code instead of a model's context window... the script is a
file you can read, edit, save, and re-run." Its own stated reach criterion: "a workflow is worth
it when a task outgrows one context window, when you want verification enforced by structure, or
when the orchestration itself is worth keeping." Nowhere in this source — Anthropic's most
concrete answer to "how do I orchestrate many agents" — does a graph abstraction, node/edge
registry, or checkpointer appear. The stated design property closest to a "checkpoint" is
"Claude's context stays clean," achieved by never putting orchestration state in a model's
context at all, not by persisting it in a resumable graph.

**OpenAI's Agents SDK** draws a two-way split rather than a graph one
([developers.openai.com/api/docs/guides/agents/orchestration](https://developers.openai.com/api/docs/guides/agents/orchestration),
[openai.github.io/openai-agents-python/multi_agent](https://openai.github.io/openai-agents-python/multi_agent/)):
**handoffs** (control transfers, the new agent owns the rest of the turn) versus **agents-as-tools**
(a manager keeps ownership and calls specialists as bounded functions). The guidance is also
explicitly minimalist: "Start with one agent whenever you can. Add specialists only when they
materially improve capability isolation, policy isolation, prompt clarity, or trace legibility."
Graph language appears only descriptively, not prescriptively — a multi-agent system *can be
modeled* as a graph with agents as nodes, edges as tool-calls (manager pattern) or handoffs
(decentralized pattern) **[search-synthesized, official domain]** — OpenAI does not ship or
recommend an explicit graph-authoring API for this; code-based orchestration is called out as
"more deterministic and predictable" than LLM-driven routing, which is the same "use plain code
where you can" instinct as Anthropic's cookbook, from a different vendor.

**LangGraph is the one source here that is an actual graph framework**, and its own documentation
states what the abstraction buys: "nodes do the work, edges tell what to do next"
([docs.langchain.com/oss/python/langgraph/graph-api](https://docs.langchain.com/oss/python/langgraph/graph-api)).
`.compile()` performs "basic checks on the structure of your graph" before runtime; conditional
edges are themselves traced, callback-emitting functions; and the **checkpointer** is what makes
the rest meaningful — persisted state snapshots per thread, which is "essential infrastructure for
enabling robust human-in-the-loop workflows where graph execution can be paused, inspected, and
resumed with human input"
([docs.langchain.com/oss/python/langgraph/persistence](https://docs.langchain.com/oss/python/langgraph/persistence),
fetched directly). `interrupt()` pauses a node and waits "indefinitely" for external input;
`Command(resume=...)` continues from the exact persisted state. This is architecturally the same
primitive as a flow human gate (pause, wait for a human, resume from exactly where it stopped) —
but LangGraph's version requires an in-process runtime (a Python process holding the graph
object) and a checkpoint store (`AsyncPostgresSaver`, `MongoDBSaver`, or an in-memory saver that
is explicitly documented as unsafe for production: "when the process restarts, all checkpoints
are lost"). Section 3 below returns to why this requirement doesn't fit flow's actual execution
substrate.

**Google's Agent Development Kit** draws the workflow/agent line as a *composition* choice rather
than an either-or
([google.github.io/adk-docs/agents/workflow-agents](https://google.github.io/adk-docs/agents/workflow-agents/),
**[search-synthesized, official domain]**): `SequentialAgent`, `ParallelAgent`, and `LoopAgent`
are fixed-logic "template" wrappers that "determine the execution sequence according to their
type... without consulting an AI model for orchestration," explicitly meant to be nested
*inside* or *around* LLM-driven dynamic routing rather than replacing it. This is the same
hybrid stance as flow's own design — deterministic wrapper for the parts that should never vary
(preflight, the plan-gate's four fixed axes), judgment for the parts that should.

**Microsoft's Agent Framework 1.0** (unifying AutoGen + Semantic Kernel, April 2026) is the one
vendor that ships an explicit, named **graph-based workflow engine** as a first-class product
surface, with "type-safe routing, checkpointing, and human-in-the-loop support"
([learn.microsoft.com/en-us/agent-framework](https://learn.microsoft.com/en-us/agent-framework/overview/),
**[search-synthesized, official domain]**) — aimed explicitly at "structured business workflows"
with compliance/audit requirements, a different problem shape (enterprise process automation
with regulated steps) than flow's (one engineer's loop, gated by that engineer).

**The arXiv literature is split exactly along flow's own fault line.** "From Static Templates to
Dynamic Runtime Graphs: A Survey of Workflow Optimization for LLM Agents"
([arXiv:2603.22386](https://arxiv.org/abs/2603.22386)) frames the whole field as "agentic
computation graphs" and organizes prior work along *when* structure is decided (static vs.
dynamic) — a vocabulary, not a verdict on whether flow needs one. "From Agent Loops to Structured
Graphs: A Scheduler-Theoretic Framework for LLM Agent Execution"
([arXiv:2604.11378](https://arxiv.org/abs/2604.11378)) is the more pointed one: it names exactly
three structural failures in the "Agent Loop" pattern — **implicit dependencies** between steps,
**unbounded recovery loops** with no clear termination, and **mutable execution history** that
defeats debugging — and proposes an explicit static DAG as the fix, trading expressiveness for
"controllability, verifiability, and implementability." That is the single strongest piece of
evidence in this doc's source set that graph structure *can* be worth its cost — and § 2 below
checks each of its three named failure modes against flow's actual loop, because that is a
falsifiable claim rather than a vibe.

## 2. Where flow already *is* this taxonomy — mapped, not asserted

This is the finding most worth stating plainly: **flow was not built with this vocabulary, and
maps onto almost all of it anyway.**

| Anthropic pattern | Flow's implementation | Where |
|---|---|---|
| Prompt chaining | The 11-step loop itself — Clarify → Plan → Execute → Preflight → Commit → Simplify → Staff-review → Present → Iterate → Ship → Stop, each step consuming the previous step's output | `docs/workflow.md` §§1–11 |
| Routing | D1's prototype-first vs. classic pre-execution-gate selection (keyed on `uiSurface`, brief `Surface`, `Mode`); `Mode: feature\|spike\|tiny` selecting which steps run at all | `prototype/SKILL.md`, `docs/workflow.md` § 2 |
| Parallelization (sectioning) | `/flow:staff-review`'s four lenses, `/flow:review-brief`'s three reviewers (`auditor` + `plan-critic` + `lens-experience`) — all fanned in one tool message, one triaged verdict | `staff-review/SKILL.md`, `review-brief/SKILL.md` |
| Orchestrator-workers | `/flow:orchestrate` + `/flow:spawn` + `/flow:handoff` + `/flow:gate` — a seat dispatching independent worker workspaces, each running its own copy of the loop | `orchestrate/SKILL.md`, `spawn/SKILL.md` |
| Evaluator-optimizer | `/flow:verify-build`'s fresh-context judge over the implementer's own claims; `/flow:audit-skips`'s "verdict-without-artifact == skip" rule; `/flow:audit-coverage` vs. the Spec-walk the implementer wrote | `verify-build/SKILL.md`, `audit-skips/SKILL.md` |

All five of Anthropic's named workflow patterns, independently arrived at — evidence against
"adopt a graph framework" being the live gap, not proof there is no gap at all (§ 2 below names
two real ones).

**The checkpoint/interrupt primitive exists too, just not as a library call.** `/flow:prototype`'s
gate-execute assertion is structurally identical to LangGraph's `interrupt()` /
`Command(resume=...)` pair: execution pauses, a human must act, and resumption is gated on a
**committed-state artifact** — a sha-shaped digest plus a verbatim quote, read "only from the
header region above the active `**Spec-walk:**` heading," so a stale or borrowed digest cannot
satisfy a later gate (`prototype/lib/prototype-gate.py gate-execute`, `docs/workflow.md` § 3).
That is a hand-rolled checkpoint, deliberately scoped to **committed state only** rather than
session memory — "its verdict survives a lost workspace" — which is *more* durable than a
LangGraph `InMemorySaver` and arguably as durable as a Postgres-backed one, at zero added
dependency, because flow's checkpoint store is git itself.

**Flow already writes graph nodes in code, exactly where determinism earns its keep, and nowhere
else.** `autoplan/lib/gate.py` is a three-arm state machine with named arms (`arm-a`/`arm-b`/
`arm-c`), a `combine`/`gate` step, and an explicit routing table (`proceed` / `auto-fixable` /
`decision-required` / `blocked`) — a hand-written analog of a LangGraph conditional-edge function,
with the same "RED on absence, never GREEN on silence" discipline a checkpointer's resume
contract would also need. `gate/lib/gate-classify.py` is the same shape for the four-axis plan
gate. `ship/lib/manifest-triage.py`, `ship/lib/pr-coherence.py`, and `audit-skips`'s
`skip-audit-checks.py` are three more. None of these import or emulate a graph library; each is
a small, auditable, stdlib-only Python script that a prose SKILL.md calls and trusts over its own
judgment. **This is the pattern worth generalizing, not graph adoption** — see § 4.

**Where flow's control flow genuinely does live only in prose, and a reader cannot check it
mechanically:** the Step 8 **ship-readiness predicate** — five ANDed conditions (every Spec-walk
box checked, no open BLOCKER, no unresolved MEDIUM/LOW assumption, verify-build PASS not merely
"didn't fail," no unanswered `this-iteration` question) — is stated in `docs/workflow.md` § 8 as
markdown prose that an agent reads and self-evaluates. Unlike the autoplan gate, the plan gate, or
the skip audit, **nothing computes this predicate**; every sub-condition except verify-build's
PASS/FAIL is read off the agent's own running memory of the session. This is exactly the
"implicit dependencies between execution steps" failure the scheduler-theoretic paper names
([arXiv:2604.11378](https://arxiv.org/abs/2604.11378)) — not because the dependency is hidden
(workflow.md states it in full), but because nothing re-derives it from artifacts the way
`gate.py` re-derives the autoplan verdict from `arm-a`/`arm-b`/`arm-c` evidence files. The other
two named failure modes in that paper do **not** apply to flow as measured: "unbounded recovery
loops" is explicitly bounded everywhere flow retries (the FB-0012 bounded mechanical fix, Arm A's
exactly-one re-review, the skip-audit's exactly-one re-run-and-re-audit), and "mutable execution
history" is the opposite of flow's actual discipline — every gate decision that matters is pinned
to a git commit, a PR body, or a `dev-docs/history/` entry specifically because mutable
session-only state was identified (independently, across six incidents — `.claude/rules/
general.md` § "Consistency discipline") as the recurring bug class flow's own development has
hit hardest.

A second prose-only control-flow surface: **`ship/SKILL.md` is 1,868 lines.** A large fraction of
that length is routing logic — which manifest kind goes to `auto`/`ask`/`blocked`, which skip
reasons are legitimate under which mode, how the four coherence invariants compose — expressed as
markdown an agent re-reads and re-interprets on every single ship run, at full token cost, with
no compiled or cached representation of "what this file actually decides." `docs/workflow.md`
itself is 886 lines of the same shape one level up. Neither file is wrong to be long — the
decisions they encode are genuinely numerous — but neither has a structural representation a
machine (or a fast-skimming human) can check against the prose, the way `gate.py`'s routing table
can be checked against its evals. This is the second half of § 4's recommendation.

## 3. Where graphs are the wrong tool for flow — stated plainly, not hedged

**The execution substrate doesn't support it, and this is a physical fact, not a preference.** A
LangGraph `StateGraph` is an in-process Python object: one runtime holds the compiled graph, the
checkpointer, and the current node pointer, for the lifetime of a `thread_id`. Flow's "nodes" are
Claude Code **skills**, each invoked as its own model turn inside a session that itself has no
persistent process between invocations — and flow's "workers" (the orchestrator/spawn suite) are
not functions in a shared process at all, but **separate cloud sandboxes**, each running its own
independent Claude Code session against its own git branch. There is no host process in flow's
actual deployment that could hold a compiled graph object across a `/flow:spawn` call, because
the thing being spawned is not a function call — it is a new workspace, on a different machine,
communicating back only via git branches, PR bodies, and file-based ping messages
(`orchestrate/SKILL.md` §§ 2, 5; "one agent cannot run a skill inside another workspace... the
mechanism is *instruct, not remote-invoke*"). Adopting LangGraph (or any in-process graph
framework) would not formalize this architecture; it would describe a *different* one that flow
does not have, because flow's workers are OS-level processes on independent machines, not
coroutines under one scheduler.

**Flow already built, and prefers, the thing a checkpointer exists to replace** (§ 2's gate-execute
digest is the receipt). LangGraph's checkpointer exists so execution survives a restart; flow gets
the same property from its explicit, named design principle that durable state belongs in git, not
in any process (`dev-docs/feedback/FB-0130-a-decision-that-must-survive-a-rotation-goes-in-git-not-
the-seat.md`; `/flow:handoff`'s disposability invariant, "the seat holds no state that isn't
recoverable from git, the backend, or already delivered to you"). A graph library's checkpointer
would be a **second, redundant persistence layer** next to the one flow already has, and worse,
not the system of record — git already is.

**The token-cost argument applies directly, and flow's own measurements already demonstrate the
failure mode Anthropic warns about** (the 3-10x figure quoted in § 1): the roadmap's own
session-efficiency program (`dev-docs/handoffs/session-efficiency-program.md`) exists because flow
has already paid real cost for under-scoped coordination overhead, and `/flow:spawn`'s own routing
table exists because a fleet was measured running "4 of 4 workers on the top tier — including a
parked one doing nothing." Adding a graph framework on top of the orchestrator suite would add a
sixth layer of abstraction (`dispatchBackend` → cloud host CLI → cloud sandbox → Claude Code
session → flow skill → now also a graph runtime) to a system whose own documented failure mode is
already "too much coordination relative to work done."

**CLAUDE.md's quality bar forbids it outright, for the right reason.** "Lean: stdlib only. No new
dependencies without explicit discussion" is not an arbitrary constraint — it is the same
obscures-the-prompt instinct Anthropic states directly (quoted in § 1). A LangGraph, AutoGen, or
Semantic Kernel Process Framework dependency inside a Claude Code plugin whose entire runtime
today is "stdlib Python helper scripts called from markdown skill prose" would be the single
largest architectural inversion this repo has made, for a problem (§ 2's two named prose-only
gaps) that is solved more cheaply by extending a pattern flow has already shipped five times.

## 4. Ranked recommendations

Nothing below should be built from this doc alone — each is sized, costed, and falsifiable, per
the brief's own instruction to decide nothing.

### R1 — Formalize the Step 8 ship-readiness predicate as a deterministic checker (HIGH confidence, LOW cost)

**What changes.** A small stdlib script (same shape as `autoplan/lib/gate.py` or
`gate/lib/gate-classify.py`) that re-derives the five ANDed Step 8 conditions from artifacts that
already exist for every other reason — the plan's Spec-walk checkbox state, the staff-review/
simplify BLOCKER count, the confidence-verdict table, the verify-build findings buffer's
`aggregated_verdict`, and the `open_questions[]` routing field — rather than leaving the predicate
to be recomputed from an agent's running memory of its own session.

**Cost.** One script plus an eval fixture, following the exact template flow has used four times
already (`gate.py`, `gate-classify.py`, `manifest-triage.py`, `skip-audit-checks.py`). No new
dependency; no change to the loop's shape; the prose in `docs/workflow.md` § 8 stays as the
human-readable spec, the script becomes the thing that actually gets checked.

**What would prove it right or wrong.** Run the checker against a sample of past PRs where Step 8
auto-advanced vs. stopped-and-presented (both are visible in merged PR history via the `## Flow
run` table). If the checker's verdict matches the agent's actual decision on every case, it is a
faithful re-derivation and safe to wire in as a gate; a case where the checker says "proceed" but
the agent correctly stopped (or vice versa) identifies exactly which sub-condition the prose
encodes that the artifacts don't yet carry, which is itself useful signal about what to log.

**This should be one future item with the CI-status gap, not two.** `FB-0131`'s third corollary
names an adjacent, currently-unfiled hole in the exact same surface: *"A green local sweep is not
CI. The ship pipeline never reads CI status, so 'ready' in a PR body is not evidence that checks
pass"* (`dev-docs/feedback/FB-0131-a-self-updater-that-asks-the-artifact-whether-to-update.md`).
That is a sixth condition belonging on the same predicate this recommendation already re-derives
— "CI checks green, with pending as its own state" is exactly the shape a deterministic Step 8/
ship-readiness checker should carry, rather than living only as a `gh pr checks <N>` reminder a
human has to remember to run by hand. Filing these separately would duplicate the "which artifact
does this gate actually read" design question; the natural home for both is the one checker R1
proposes. **Note this changes R1's cost, not just its scope**: the other five conditions read
committed artifacts the session already produced, while CI status is a live external call (`gh
pr checks`) with auth, retry/timeout handling, and its own tri-state (pass/fail/**pending**) —
closer in shape to the toolchain-absence probe `/flow:verify-build` already carries than to a
pure-artifact re-derivation. The combined checker is still worth building; "LOW cost" describes
the first five conditions, not the sixth.

### R2 — Do not adopt a graph-orchestration framework, for either the loop or the orchestrator suite (HIGH confidence, this is an explicit NO)

**What changes.** Nothing. This is a decision not to spend engineering budget on LangGraph,
AutoGen/Semantic Kernel Agent Framework, or an in-house equivalent — for two distinct reasons that
should not be flattened into one. **For the orchestrator/spawn suite**, § 3's substrate-mismatch
argument is close to a structural impossibility: the workers are separate OS processes on separate
machines, and no runtime in flow's actual deployment could hold a compiled graph object across a
`/flow:spawn` call. **For the 11-step loop itself**, which already runs as one session, nothing
about its substrate rules a graph runtime out — the case there is cost/benefit, not impossibility:
redundant persistence (git already is the checkpoint store) and Anthropic/OpenAI's own measured
cost argument (3-10x token overhead per added layer, applied to a system already fighting that
exact cost in its own roadmap), against no identified gap a graph would close that § 4's smaller
fixes don't already close more cheaply. Same verdict, weaker and more reversible justification for
the loop than for the orchestrator suite — worth keeping distinct, since a future reader
relitigating "could the loop use a graph" should be told "not worth it," not "structurally
impossible."

**What would reverse this.** If flow's execution substrate changes — specifically, if `/flow:
orchestrate`/`/flow:spawn` stop creating separate cloud sandboxes and start running multiple
workers **in one process** (e.g., driven by something like the `Workflow` tool's model, see R3) —
the substrate argument in § 3 no longer holds, and the question should be re-asked against
whichever specific coordination gap exists at that time, not re-litigated in the abstract.

### R3 — CONTINGENCY, not a build item: if flow ever needs more orchestration structure than judgment-driven dispatch, the escalation path is the `Workflow` tool's plain-code primitives, not a graph DSL

**Labeled separately from R1/R4/R5 on purpose** — those three are sized, costed, buildable items;
R2 is an explicit non-action decision; this one is neither. It is a trigger condition to watch for,
not a backlog item to schedule, and carries no cost/confidence rating for that reason.

**What changes.** Nothing today. This is a named fallback, not a recommendation to build: *if*
a future fleet genuinely outgrows "one agent decides who to spawn next" — Anthropic's own
cookbook's criterion, "the task is bigger than one context window... or the orchestration itself
is worth keeping" — the validated next step (by Anthropic's own dynamic-workflows cookbook, and
literally the mechanism this research task itself ran under) is `agent()`/`parallel()`/
`pipeline()`/`phase()` composed in an ordinary script, not nodes-and-edges.

**Honest caveat.** This is not a drop-in replacement for `dispatchBackend` as it exists today.
The `Workflow` tool's `agent()` calls spawn in-process subagents sharing one host's tool access;
flow's `dispatchBackend` spawns independent cloud workspaces on independent machines with their
own git state. Using the Workflow tool to replace `/flow:spawn` would require `dispatchBackend`
to grow a genuinely new primitive — "launch a worker and block until it reports" — that no
current `dispatchBackend` verb (`listWorkers`, `createWorker`, `sendMessage`, `workerStatus`,
`selfSession`) provides, since today's dispatch is deliberately fire-and-forget
(`/flow:orchestrate`'s "workers ping the seat; the seat does not poll").

**What would prove this worth building.** A real measured case where an orchestrator seat spends
materially more attention relaying between workers than a `pipeline()`/`parallel()` script would
have spent compute — i.e., the same kind of before/after token or wall-clock measurement the
dynamic-workflows cookbook itself reports ($3.29, 2.5 minutes, ~60 tool calls for its own worked
example). No such case exists in this repo's history yet; the orchestrator suite's stated scope
("optional, and only worth it above roughly three independent workstreams") has not yet needed to
exceed hand-dispatched workers.

### R4 — Extend the committed-state digest/resume pattern from the D1 prototype gate to the Step 8 stop-and-present → Iterate resume (MEDIUM confidence, LOW cost)

**What changes.** Today, pausing at Step 8 ("stop and present") and resuming at Step 9 ("Iterate")
relies on conversation continuity — there is no committed-state artifact analogous to
`prototype-gate.py`'s sha-shaped digest proving "this exact pause state was resumed, not a stale
or borrowed one." Compare to `/flow:prototype`'s gate: that pause/resume is deliberately readable
from **committed state only**, specifically so "its verdict survives a lost workspace." A Step 8
pause currently does not survive a lost workspace or an orchestrator handoff the same way.

**Cost.** Low — the pattern (a digest of the stop reason + a verbatim quote of the blocking
condition, written to the plan doc) already exists once; this is a second call site, not new
design.

**What would prove it's needed.** Whether this gap has actually caused a real incident — a Step 8
pause that was silently lost or double-resumed across a session or seat rotation — is unverified
here; this doc names the structural asymmetry (one gate has a committed-state resume marker, the
other does not) without claiming the second gate has actually failed. The cheap experiment: grep
`dev-docs/history/` and `dev-docs/feedback/` for any incident matching "lost at the present gate"
or "resumed into the wrong iteration" before spending the (small) cost to build this.

### R5 — A hand-authored state diagram of the 11-step loop, committed as a diagram rather than generated at runtime (LOW confidence this is worth doing now, near-zero cost)

**What changes.** One Mermaid (or equivalent) diagram in `docs/workflow.md`, covering the loop's
nodes (11 steps), its conditional edges (mode selection, the D1 prototype-first vs. classic
split, the Step 8 predicate's five conditions as a single decision diamond), and its two
checkpoints (pre-execution gate, merge). This mirrors the one benefit LangGraph's docs claim that
is genuinely free-standing from the rest of the framework: "visualization capabilities emerge
naturally from the declarative structure" — flow can take the *output* (a reviewable diagram)
without the *input* (a graph-authoring runtime), by hand-drawing it from the already-written
prose.

**Cost.** Near-zero — a few hours, no code, no dependency, no runtime behavior change.

**What would prove it's worth keeping current.** Whether a new contributor (or a fresh orchestrator
seat reading `docs/workflow.md` cold) orients faster or more accurately with the diagram present
vs. absent is directly testable in one onboarding session, and the diagram rots exactly the way
every other point-in-time artifact in this repo rots — so it only earns its keep if something
commits to re-checking it against `docs/workflow.md` at the same cadence doc-currency checks
already run, which is itself a cost worth weighing before building it, not after.

## 5. Direct answers to the brief's "Done means" bullets

- **Would an explicit graph layer improve flow's three use cases?** No, for the loop and the
  orchestrator suite as currently substrated (§ 3); partially yes for two narrow prose-only gaps,
  addressed by extending a pattern flow already uses (R1, R4) rather than by adopting a graph
  framework.
- **What should flow adopt?** Nothing from the graph-framework family. Two small deterministic
  checkers (R1, R4) following the template `gate.py`/`gate-classify.py`/`manifest-triage.py`/
  `skip-audit-checks.py` already set, plus one documentation artifact (R5).
- **What does it already do?** All five of Anthropic's composable workflow patterns (§ 2's
  table), a hand-rolled checkpoint/resume primitive for its one gate that most needed it, and five
  independent hand-written deterministic "graph nodes" exactly where judgment-only prose had
  measurably failed before.
- **What should it avoid?** A graph-orchestration dependency (LangGraph, AutoGen/Semantic Kernel
  Agent Framework, or an in-house equivalent) for either the loop or the orchestrator suite, on
  substrate-mismatch, redundant-persistence, and measured-token-cost grounds (§ 3), all traceable
  to primary sources rather than asserted.
