### FB-0081 — For UI work the prototype approval REPLACES the plan gate; the technical plan is written afterward and machine-gated, never human-gated

**Date:** 2026-08-02
**Source type:** user direction
**What was said:** After discovering that the prototype-first idea from this session's opening was never built (see [FB-0080]), the user re-specified the shape. On ordering: *"could the prototype and the plan be presented together? … that feels clean, unless we expect more iteration in the prototyping phase, in which case better to build that out than commit to writing the whole plan first — once the prototype is approved, write the corresponding plan and execute."* On gate count: *"agreed — keep two gates."* On rigor before prototyping: *"we do need to make sure that there is a clear understanding of the problem and the constraints/intended scope before prototypes are built — flow agent should still be asking me questions for clarity, and it needs some review steps for its own work similar to audit and critique before prototyping."* On the technical plan: *"shouldn't the technical plan still have a review stage, but if it passes the automated skill gates (and/or required changes are made), it can proceed automatically?"*

**Synthesized rule:** On a UI-surface change, the human's decision point moves from the plan to the prototype. This **moves** a gate rather than adding one — `plugins/flow/docs/workflow.md` currently argues visual sign-off must fold into the merge gate "not a third gate," and that objection is answered by replacement, not by exception. The resulting loop:

1. **Clarify** (already Step 1) — read source-of-truth docs, surface conflicts, ask 2–4 questions. This is where the human corrects the framing; it is interaction, not an artifact to approve.
2. **Design brief** — problem, whose moment, constraints, intended scope, what is deliberately excluded, and where the agent intends to push past the literal request. Short enough to read in twenty seconds.
3. **Review the brief before building anything** — `/flow:audit-plan` (assumptions invented rather than asked), `/flow:critique-plan` (scope drift, *absent elements the user explicitly requested*, incoherence vs the design-language doc), plus the FB-0046 experience/ambition lens. Reuses existing machinery: `/flow:critique-plan` already accepts an arbitrary file path and already supports standalone review with no transcript.
4. **Prototype** — iterative and cheap. No ship pipeline, no evals, no doc synthesis. Iteration here is the point; six rounds on the annotation layer is the reference case.
5. **Prototype approval — human gate 1.**
6. **Technical plan** — written *after* approval, against a design that survived contact. Reviewed by `/flow:audit-plan` + `/flow:critique-plan` + push-further-on-quality, then: clean ⇒ proceed automatically; `[auto-fixable]` ⇒ fix, re-review **once**, proceed; `[decision-required]` ⇒ escalate to the human as an answerable question (FB-0075's shape), never as a document to read. Loop only on mechanical signals, never on LLM judgment.
7. Execute → review → ship → **merge — human gate 2.**

**Why the plan must not come first or alongside:** writing it before the prototype is approved anchors both parties — the human reads a committed-looking plan and pushes back less on the prototype, which is exactly backwards, since the prototype is the cheap artifact to change. Any prototype revision also invalidates plan work already reviewed.

**Why the technical plan still exists at all, despite not being human-gated:** `/flow:audit-coverage`, `/flow:verify-build`'s Spec-walk, and the ship rigor gate all anchor to a plan. Auto-writing it after prototype approval means **a plan always exists** — which directly closes the hole in [FB-0080], where `/flow:critique-plan`'s drift check was structurally unreachable because no plan was ever produced.

**The trade to hold:** removing the human gate from the technical plan means the machine gate stops being a backstop behind a human and becomes the only thing there. That argues for *stricter* review at that point, not looser — and for "no plan produced" being impossible rather than the silent default.

**Proportionality guard:** the pre-prototype review is three agent passes before any prototype exists, which on a small surface costs more than the change. Gate the whole pre-prototype phase on the same trigger as the prototype itself, and collapse to Clarify + brief with no review passes on genuinely small surfaces — otherwise this rebuilds the ceremony it exists to remove.

**Applies to:** `plugins/flow/docs/workflow.md` (Steps 1–2 and the "not a third gate" argument at the Step 8/9 discovery boundary), `plugins/flow/skills/{critique-plan,audit-plan}/SKILL.md`, `plan-discipline.md`, `planner.md`, FB-0046 (the experience/ambition lens becomes load-bearing rather than optional), the Deliverable-quality roadmap track.
