# Agentic graphs research — resolved NO wholesale adoption

**Date:** 2026-10-04
**Branch:** `conductor/research-agentic-graphs-for-flow`
**Commit:** [this commit]
**Mode:** spike (research)
**Scope:** `dev-docs/research/2026-10-agentic-graphs.md`, its `dev-docs/README.md` index row,
this entry. No code changed.

## What this is

A commissioned research spike: does an explicit agentic-graph layer (nodes, edges, shared state,
conditional routing, checkpoints — the LangGraph/Semantic-Kernel-Process-Framework shape) improve
flow's three real use cases — the 11-step loop with two human gates, the `/flow:orchestrate` +
`/flow:spawn` cloud-worker suite, and the fresh-context reviewer fan-outs (`/flow:staff-review`,
`/flow:review-brief`)? Sources restricted to Anthropic, OpenAI, LangChain/LangGraph official docs,
Google ADK official docs, Microsoft official docs, and arXiv papers from identifiable authors —
no personal blogs or listicles, per the brief.

## What was found

**Flow already implements all five of Anthropic's named workflow patterns**
(prompt chaining = the loop itself; routing = D1's prototype-first/classic split and mode
selection; parallelization = staff-review's four lenses and review-brief's three reviewers;
orchestrator-workers = the spawn suite; evaluator-optimizer = verify-build's fresh-context judge),
independently of the vocabulary — the loop was never built against this taxonomy and lands on
most of it anyway.

**Flow already has a checkpoint/resume primitive**, just not as a library call:
`/flow:prototype`'s gate-execute assertion (a sha-shaped digest + verbatim quote, read from
committed state only) is structurally the same thing as LangGraph's `interrupt()` /
`Command(resume=...)` pair, and more durable than an in-memory checkpointer at zero added
dependency, because flow's checkpoint store is git itself.

**Flow already writes deterministic "graph nodes" in code exactly where judgment-only prose
previously failed** — `autoplan/lib/gate.py`'s three-arm state machine, `gate/lib/
gate-classify.py`'s four-axis table, `ship/lib/manifest-triage.py`, `audit-skips`'s
`skip-audit-checks.py`. None import a graph library; each is a small stdlib script a prose
SKILL.md calls and trusts over its own judgment. This is the validated pattern to extend, not a
case for a framework.

**Two genuine prose-only gaps exist**, found by checking the scheduler-theoretic arXiv paper's
three named failure modes (implicit dependencies, unbounded recovery loops, mutable history)
against flow directly: the Step 8 ship-readiness predicate (five ANDed conditions, computed only
by an agent's own running memory of the session — nothing re-derives it from artifacts the way
every other flow gate is re-derived) and the Step 8→9 pause/resume (no committed-state resume
marker, unlike the D1 prototype gate's).

**Graphs are the wrong tool, for a substrate reason rather than a taste reason.** Flow's
"workers" are separate cloud sandboxes on separate machines communicating via git branches, PR
bodies, and file-based pings — not coroutines under one in-process scheduler, which is what a
`StateGraph` requires. Adopting a graph framework would describe an architecture flow does not
have. Combined with Anthropic's and OpenAI's own measured-cost guidance (3-10x token overhead
per added coordination layer; "start with one agent whenever you can") and CLAUDE.md's
stdlib-only quality bar, the honest verdict is an explicit no, not a hedge.

## Recommendations (ranked, nothing built)

1. Formalize the Step 8 ship-readiness predicate as a deterministic checker, same template as the
   four gates above. Falsifiable against past PRs' actual Step 8 outcomes. **Linked to FB-0131's
   third corollary** ("the ship pipeline never reads CI status") per the orchestrator's note mid-
   spike: "CI checks green, with pending as its own state" is a sixth condition for the same
   checker, not a second item.
2. Do not adopt a graph-orchestration framework — but the two halves carry different-strength
   justifications, kept distinct rather than flattened: for the orchestrator suite it's close to
   a structural impossibility (workers are separate OS processes, no shared runtime to hold a
   graph object); for the 11-step loop itself (already one session) it's cost/benefit, not
   impossibility, and reverses the moment that cost/benefit call changes.
3. If a future fleet genuinely outgrows judgment-driven dispatch, the validated escalation is the
   `Workflow` tool's plain-code primitives (`agent`/`parallel`/`pipeline`), not a graph DSL —
   named as a fallback with an honest substrate caveat, not a recommendation to build now.
4. Extend the D1 prototype gate's committed-state digest/resume pattern to the Step 8→9 resume —
   unverified whether this has caused a real incident; names the cheap check before building it.
5. A hand-authored (not runtime-generated) state diagram of the 11-step loop in `docs/
   workflow.md`, mirroring the one framework-free benefit LangGraph's docs claim (visualization
   "emerges naturally from declarative structure") without the framework.

## Design decisions

- **Labeled Google ADK and Microsoft Agent Framework claims `[search-synthesized, official
  domain]` rather than presenting WebSearch summaries as direct quotes.** A provenance
  distinction, not a citation downgrade — it lets a reader tell which claims were verified by
  direct fetch (Anthropic, OpenAI, LangGraph, both arXiv papers) from which came back through a
  search tool's own synthesis of an official-domain page.
- **Split R2's justification into two different-strength arguments** (structural impossibility
  for the orchestrator suite's separate-sandbox substrate; cost/benefit for the 11-step loop,
  which already runs as one session) rather than one blanket "physical fact" verdict covering
  both — so a future reversal of the loop's cost/benefit call isn't mistaken for a reversal of
  the orchestrator suite's substrate argument, and vice versa.
- **Labeled R3 as a contingency, not a sized backlog item**, after a staff-review lens flagged
  that giving it the same confidence/cost shape as R1/R4/R5 implied it was buildable now, when
  its own text says the opposite.

## Technical decisions

None — no code changed, by design (the scope is a research doc, not an implementation). The
nearest analog: R1's cost note (added after a staff-review lens flagged it) that folding FB-0131's
CI-status corollary into the Step 8 checker changes its cost profile — five artifact-reads are
LOW cost, a live `gh pr checks` call with auth/retry/timeout and a pending tri-state is not — and
that distinction is stated explicitly rather than smoothed into one "LOW cost" label.

## Tradeoffs discussed

- **Scope of "official source."** Google ADK and Microsoft Agent Framework claims came back from
  WebSearch rather than a direct WebFetch of the docs page; both are labeled
  `[search-synthesized, official domain]` in the research doc rather than presented as direct
  quotes, to keep the citation discipline honest about provenance.
- **The arXiv scheduler-theoretic paper's citation discipline** — see "What was found" above
  (only 1 of 3 named failure modes applies to flow, checked individually rather than cited
  wholesale). Citing a paper's conclusion without checking which parts transfer would have been
  the research equivalent of the "disclosed confound is still a confound" class (FB-0127) this
  repo already tracks.

## Lessons learned

The clearest finding of this spike is architectural self-validation, but not an all-clear: flow
arrived at all five of Anthropic's composable workflow patterns and at its own checkpoint
primitive without the vocabulary for either, which is a stronger signal that the current design
is sound than any external framework's feature list would be — and it sits alongside two real,
costed follow-ups (recommendations 1 and 4) that the same spike found and did not wave away.
