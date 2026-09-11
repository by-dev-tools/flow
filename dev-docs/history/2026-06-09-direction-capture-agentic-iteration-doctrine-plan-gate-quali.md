### Direction capture — agentic-iteration doctrine + plan-gate quality lenses (FB-0044/0045/0046)
**Date:** 2026-06-09
**Branch:** claude/happy-gates-b3cf0c
**Commit:** [this PR]

**What was done:**
Docs-only direction-capture from a design conversation about composing flow with two now-GA Claude primitives (`/goal`, dynamic workflows) and refining the autonomy loop. Three feedback entries + two roadmap entries:
- **FB-0044** — low confidence during Execute is a signal to *iterate*, not stop: the agent iterates against the plan's success criteria + craft bar until the design is genuinely good, then ships; only a genuine *preference fork* escalates. Splits FB-0011's escalation as **quality-gap → iterate** vs **preference-fork → escalate**; reserves stop-before-PR for one-way-doors, otherwise escalation routes into a draft PR (FB-0034).
- **FB-0045** — craft-iteration is a *permitted* judgment-loop under four guards (independent judge + declared criteria + real artifacts + bounded budget/merge backstop), refining FB-0012's correctness-only prohibition on iterate-to-approval. Guard #3 (real artifacts, not narration) is what V2 unlocks.
- **FB-0046** — experience + craft-ambition are first-class plan-gate quality gates: add a product-designer/experience lens + a push-further-on-quality (not scope) lens alongside the auditor + plan-critic. Corrects an earlier (wrong) dismissal of a plan-stage experience lens.
- **roadmap.md** — "Agentic-iteration doctrine" entry in the Deliverable-quality track (after V2, its precondition) + "Plan-gate quality lenses" entry under § Next (independent of the V-track).

**Why:**
The user's target loop: human approves a self-critiqued plan → agent executes, reviews, and *iterates against a strong craft/experience bar* autonomously → ships what it thinks is final (PR + eventual HTML walkthrough) → human merges or feeds back. The two load-bearing human gates (plan, merge) are preserved; the not-confident case must resolve by iteration, never a premature stop or draft. Capturing the doctrine before V2/V3 land so the implementation inherits it.

**Design decisions:**
- One FB per distinct rule, following the FB-0037 precedent (a lens-set bundles into one entry) — so FB-0046 carries both plan-gate lenses while FB-0044/0045 stay separate (loop behavior vs FB-0012 doctrine).
- Roadmap split: the iteration doctrine sequences against V2 (real-artifact dependency); the plan-gate lenses are V2-independent and can land anytime → placed in § Next, not the V-track.

**Technical decisions:**
- Direction-capture only — no plugin artifacts, no version bump (stays v1.5.2). FB numbers claimed via the reserved-numbers protocol (FB-0044/0045/0046), cleared at this ship.

**Tradeoffs discussed:**
- `/goal` vs a script-based Stop hook as the autonomous-convergence driver: the Stop hook is FB-0012-pure (deterministic on the verify-build exit code) and shippable in `default-hooks.json`; `/goal` is the ad-hoc, hooks-gated end-user alternative. Captured as direction, not yet built.

**Lessons learned:**
- The repo's research docs predate `/goal` (a real primitive, v2.1.139+) and call dynamic workflows "research preview" though they're now GA — flagged the stale `roadmap.md:242` line for a future touch. Flow's FB-0041 north-star nearly restates what `/goal` does natively; the design lesson is to compose with the primitive, not reinvent it in prose.
