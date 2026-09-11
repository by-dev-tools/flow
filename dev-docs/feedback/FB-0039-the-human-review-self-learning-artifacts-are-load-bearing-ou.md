### FB-0039: The human-review + self-learning artifacts are load-bearing outputs that must survive dynamic-workflows adoption — Flow-run PR table, companion HTML case-study, and the core-docs + FB-entity + memory pipeline
**Date:** 2026-06-03
**Source:** user direction (dynamic-workflows alignment conversation)

**What was said:** "the format of human review and self learning from feedback (pr structure and companion html files showing visual changes, as well as flow's core docs system and feedback entities) is very important, and I want to preserve that as we adopt dynamic workflows."

**Synthesized rule:** When porting any Flow stage to a native dynamic workflow, the *artifacts* the stage produces are part of its contract, not incidental output. Three must survive untouched (or be strengthened):

```
(a) The per-step `## Flow run` PR table (FB-0019) — the loop's execution made
    legible on the PR page. A workflow can ENRICH it (fold in the saved-script
    path + per-phase agent/token summary from /workflows) but never replace it
    with a turn-by-turn transcript or a bare "ran a workflow" line.
(b) Companion HTML case-study reports + visual history showing visual/
    behavioral changes — the rendered page a human opens before the merge gate.
    ASPIRATIONAL, NOT YET SHIPPED: this is a roadmap VISION ("Verify-build HTML
    case-study report", PR-R-successor candidate), not a baseline to build on.
    What IS shipped: /flow:verify-build (PR Q, v1.3.0) — behavioral verification
    that captures some screenshot / a11y-tree observation; its JSON findings
    buffer is the intended data source for the future HTML report. Visual
    sign-off folds into the merge gate (FB-0035), never a third human gate.
    Treat the rich visual artifacts as a target the workflow direction should
    enable, not as an existing surface to preserve.
(c) The core-docs (history/plan/roadmap/spec) + FB-entities + memory self-
    learning pipeline. A workflow script CANNOT write files directly (script ≠
    filesystem); a synthesis agent must. Under fan-out, multiple agents writing
    feedback race on FB numbers — so PR K1's reserved-numbers protocol becomes
    LOAD-BEARING, not optional, the moment feedback synthesis fans out.
```

The general principle: dynamic workflows isolate intermediate results in script variables and return only a final answer — which is a context win, but means the durable human-facing + self-learning surfaces must be explicitly produced as the workflow's outputs, or they silently disappear.

**Applies to:** dynamic-workflows adoption, `/flow:ship` PR-body + feedback synthesis, verify-build HTML report, core-docs discipline, FB-collision protocol (K1), memory pipeline
