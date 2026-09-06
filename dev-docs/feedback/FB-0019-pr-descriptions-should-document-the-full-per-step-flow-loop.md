### FB-0019: PR descriptions should document the full per-step flow-loop run, not a generic Reviews line — and the per-step honesty rule cuts both ways (never imply a step ran that didn't; never imply one was skipped that ran)
**Date:** 2026-06-01
**Source:** user direction (stated while dogfooding flow on another project)

**What was said:** Dogfooding flow on another project, the user wanted richer PR descriptions: the PR body should document the full flow-loop run — every step that ran, which steps were skipped and *why* (spike/tiny mode, no UI surface, etc.), and any significant decision or change each step produced. A step with nothing notable shows "—" with no manufactured filler. The user's request included a conditional ("if security/a11y are not-yet-shipped in this flow version, say so") that, on inspection, evaluates false in v1.4.x — those reviewers ship and run; the plan-critic caught that carrying the clause forward unconditionally would instruct the agent to write "skipped — not yet shipped" for steps that actually execute.

**Synthesized rule:** A flow PR body documents the loop's *execution*, not just its reviews. The canonical shape (`/flow:ship` §7) is a `## Flow run` table — one row per loop step, each marked `✓` (ran) or `skipped (<reason>)` with the reason always named, and a **Notable** cell carrying genuine signal or `—`. Three durable sub-rules:

```
(a) Honesty cuts both ways. Never imply a step ran when it didn't (the
    original failure mode), AND never imply a step was skipped when it ran
    (the inverse). "skipped — not yet shipped" is reserved for a step
    genuinely absent from the running flow version; it is NOT a synonym for
    a runtime-config skip (doc-only / uiSurface:false / verifyEnabled:false
    / platform library|none) and must never be written for a step that
    executed. When a user request carries a conditional ("if X is true,
    say Y"), evaluate the condition against the current codebase before
    encoding it as an unconditional instruction.

(b) No manufactured notes. A routine step gets "—". An invented
    "improved error handling" line is worse than an honest blank — it
    erodes the signal the table exists to carry.

(c) The table points at follow-ups; it does not home them. Deferred
    follow-ups stay canonical in the roadmap/plan docs (existing doctrine);
    the table's closing line only references that they exist. The PR is
    still never merged by Claude.
```

The skip-reason vocabulary is duplicated across four surfaces (`ship/SKILL.md` §7, the dogfood `.claude/skills/ship/SKILL.md`, `ship-spike/SKILL.md`, `workflow.md` §10) — treat it as an FB-0010 fan-out contract: grep the skip strings across all four after any wording change.

**Applies to:** `/flow:ship` + `/flow:ship-spike` PR body, workflow.md ship narration, PR-description quality, FB-0010 fan-out discipline

**Validation:** Encoded in PR T (v1.4.1). The plan-critic's REDIRECT on the "not-yet-shipped" conditional (sub-rule (a)) is the concrete catch that motivated making the honesty rule bidirectional rather than one-directional.
