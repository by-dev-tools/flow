---
paths:
  - "**/plan.md"
---

# Plan-discipline rule (flow plugin)

Loads when writing a plan in response to a user request (step 2 of the loop in `${CLAUDE_PLUGIN_ROOT}/docs/workflow.md`). Path-matches any `plan.md` file in the project tree so it auto-loads regardless of where the project keeps its plan doc (`flow.config.json.planPath` default `dev-docs/plan.md`; consumer projects typically `core-docs/plan.md`).

## Before drafting a plan

Read the source-of-truth docs that govern the change. Paths come from `flow.config.json` slots with defaults:

- **Spec doc** (`flow.config.json.specPath`) — feature scope and decisions
- **Feedback doc** (`flow.config.json.feedbackPath`) — synthesized user preferences and corrections
- **Design-language doc** (`flow.config.json.designLanguagePath`) — visual and interaction rules (UI projects)
- **Plan doc** (`flow.config.json.planPath`) — current focus + handoff notes
- Any doc the user pointed to in the request

A plan that contradicts one of these silently is a wasted iteration. Surface the conflict during Clarify (step 1) and resolve it before drafting.

## Required plan fields

Every plan written to the plan doc must include:

1. **Mode** — `feature` (default), `spike`, or `tiny`. See `${CLAUDE_PLUGIN_ROOT}/docs/workflow.md` for what each skips.
2. **Goal** — 1–3 sentences in user terms.
3. **Scope (in)** / **Scope (out)** — what's deliberately not happening.
4. **Spec-walk checkboxes** — every numbered/bulleted requirement from the spec or user request becomes a checkbox. For each: the user-perceptible behavior, and the test or verification step that pins it. Test-first for spec contracts.
5. **Confidence verdict per load-bearing assumption** — see below.
6. **Risks / open questions**.
7. **Files touched** — anticipated paths.

`spike` mode replaces (4) with a single "Research question" line and (5) with a "Disposability" line. `tiny` mode skips (4) and (5) entirely but still names the file + the one-line change.

## Confidence verdict

The trigger for a "load-bearing assumption": **would I plan a different feature if this assumption flipped?**

For each load-bearing assumption, declare:

```
**Assumption:** <what you're assuming>
**Confidence:** HIGH | MEDIUM | LOW
**Why:** <one line — what evidence supports the rating>
**If it flips:** <one line — what would change in the approach>
```

If "If it flips" answers "the entire approach," confidence is automatically **LOW**.

### Behavior per level

- **HIGH** — proceed on user approval, normal path.
- **MEDIUM** — proceed; surface the assumption in step 8 (Present) so the user can redirect before `/flow:ship`.
- **LOW** — **automatic human gate.** The plan cannot proceed. Surface the question to the user in the Clarify/Plan conversation and wait for an explicit answer that resolves the assumption (which then upgrades to HIGH or MEDIUM). The workflow's actual enforcement here is the human gate; `/flow:critique-plan` is advisory.

Do not lower confidence to dodge the gate. If two reasonable answers would meaningfully change the implementation, that's MEDIUM at minimum.

## Why this matters

Three consumers benefit from these reads + structured output:
1. **You, the planner** — the plan is informed by documented decisions instead of inventing them.
2. **`/flow:critique-plan`** — the critic loads these docs deterministically via its preprocessor (using `flow.config.json.referenceGlob` to find them); planner-side reads help avoid violations in the first place. The critic treats LOW-confidence plans as REDIRECT findings, but the workflow's actual enforcement is the human gate.
3. **The user** — confidence verdicts make the plan's risk surface visible without forcing the user to re-derive it from the prose.
