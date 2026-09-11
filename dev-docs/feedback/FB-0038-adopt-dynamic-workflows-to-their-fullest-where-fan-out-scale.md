### FB-0038: Adopt dynamic workflows to their fullest where fan-out scale earns it — but never force a workflow when a single subagent pass suffices; token/cost is a first-class constraint
**Date:** 2026-06-03
**Source:** user direction (dynamic-workflows alignment conversation)

**What was said:** "I want the flow process to be able to use dynamic workflows to the fullest extent, but I don't necessarily want to force it off [if] it's not necessary. I want to keep token efficiency and cost in mind."

**Synthesized rule:** A dynamic workflow spawns many agents and costs meaningfully more tokens than the same task in conversation. Treat "should this be a workflow?" as a **workflow-worthiness predicate**, analogous to the Step-8 ship-readiness predicate — not a default. A workflow earns its cost when fan-out scale adds real value (large/migration-scale diffs, codebase-wide audits, per-file or per-criterion coverage, cross-checked research). For a small diff or a focused task, a single subagent pass (the current primitive) is the cheaper, correct choice. Two durable sub-rules:

```
(a) No blanket ultracode. Do not set /effort ultracode as a standing default
    for this repo's work — it turns every substantive task into a workflow,
    multiplying cost AND risking the gate-bypass in FB-TBD/ultracode policy.
    Reach for a workflow per-task when scale warrants it.
(b) Keep the existing cost gates. Flow's per-diff skip-paths (FB-0006/0007),
    stale-base preflight (FB-0008), and verifyBudgetCalls cap are the cost-
    consciousness model; a workflow port inherits them, it doesn't discard them.
    Gauge spend on a small slice before a large run (docs guidance).
```

**Applies to:** dynamic-workflows adoption strategy, ultracode policy, `/flow:staff-review` + `/flow:verify-build` ports, cost-of-review discipline, FB-0006/0007/0008 lineage
