### FB-0017: Document the skill catalog in loop order and mark auto-fire vs manual-typing + gate locations — a non-expert can't map an importance-ordered list onto the workflow
**Date:** 2026-05-30
**Source:** user direction (stated while reviewing flow's own README for production-readiness)

**What was said:** Reviewing how ready flow is for other projects, the user asked for "a full overview of the expected user experience when they open a Claude session with this plugin installed and try to build something, assuming they aren't an expert in the plugin and don't manually invoke skills" — what fires automatically, what they must call themselves, what advances step-to-step, where the pauses are — and directed: "make sure this is clearly indicated in the readme. right now, the skills aren't listed in workflow order, which is confusing."

**Synthesized rule:** When documenting flow's (or any flow-using project's) skill surface for adopters, the catalog must:

```
(a) List skills in LOOP ORDER (the sequence the user moves through), not
    alphabetical or perceived-importance order.
(b) Mark each skill's invocation: AUTO (self-fires) / MANUAL (you type it;
    disable-model-invocation:true) / BOTH (typed or called by ship/triggered
    on a diff). State plainly which high-value skills are MANUAL.
(c) Mark the human pauses (plan gate, merge gate, LOW-confidence gate) and
    mechanical stops at their steps.
(d) Include a blunt cold-start note: on a bare "build me X" with no commands,
    only the auto-loading rules attach — nothing executable fires until typed.
```

The gap to avoid: framing flow as a "managed-autonomy loop" while the docs leave a non-expert unable to tell what runs on its own vs what they must invoke. Honesty about the typed-command reality beats aspirational framing.

**Applies to:** README / consumer-facing docs, workflow.md, onboarding, `/flow:workflow-help` output
