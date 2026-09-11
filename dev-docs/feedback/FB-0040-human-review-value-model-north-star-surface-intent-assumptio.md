### FB-0040: Human-review value model (north star) — surface intent / assumptions / subjective questions / rationale FOR the human; automate implementation from clear intent; catalogue feedback + decisions to improve the process
**Date:** 2026-06-03
**Source:** user direction (dynamic-workflows alignment conversation — stated as the goal the other constraints serve)

**What was said:** "we're working towards maximizing the value of human review (grounding decisions in user needs, making assumptions clear, raising subjective questions for the human to give input on, and having rationale for everything, then automating the implementation based on clear intent and cataloguing feedback and decisions for future reference to improve the process)."

**Synthesized rule:** This is the **north star** that FB-0037 (designer lenses), FB-0038 (cost-aware workflow use), and FB-0039 (preserve review/learning artifacts) all serve — and the lens through which every dynamic-workflows adoption decision should be judged. Human review is most valuable when spent on **intent, assumptions, subjective judgment, and rationale** — not on mechanical implementation. So the loop's job is to:

```
(a) Ground decisions in user needs (cite the need/spec/intent).
(b) Make assumptions explicit and confidence-rated (existing: confidence
    verdicts; LOW auto-gates, MEDIUM surfaces at Present).
(c) Raise SUBJECTIVE questions for human input — the things a machine
    shouldn't unilaterally decide (taste, priority, one-way doors). Use
    AskUserQuestion-style surfacing at a gate, not a guess.
(d) Carry rationale for everything (existing: history.md "why" + tradeoffs,
    plan confidence verdicts, two-citation reviewer evidence).
(e) THEN automate implementation from clear intent (the autonomous interior
    between gates).
(f) Catalogue feedback + decisions for future reference to improve the
    process (existing: feedback.md FB-entities, memory pipeline, history.md).
```

**Load-bearing consequence for dynamic workflows:** because a workflow takes **no mid-run input**, every assumption and subjective question a segment depends on must be surfaced and resolved **at the gate that precedes it** — never deferred into the fan-out interior (which can't pause to ask) and never silently guessed. This is the operational tie between this value model and the segment-bounded adoption shape (O4/O5): gates are where (a)–(d) happen; the workflow interior is where (e) happens; (f) is the workflow's durable output (FB-0039). Maximizing human-review value is therefore NOT "more gates" — it's making the two existing gates carry richer, better-grounded, assumption-explicit, subjectively-informed decisions.

**Applies to:** the whole managed-autonomy loop, dynamic-workflows adoption (esp. O4 segment doctrine + O5 ultracode policy), confidence-gate doctrine, plan/Present gates, AskUserQuestion usage, history.md + feedback.md + memory cataloguing, FB-0037/0038/0039 (this is their shared root)
