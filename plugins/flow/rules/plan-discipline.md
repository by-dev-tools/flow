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
8. **Visual-walk** *(UI changes only — when `flow.config.json.uiSurface` is true and the diff has a UI surface)* — declared visual/UX acceptance criteria, parallel to Spec-walk. Each is a checkable assertion naming a user-perceptible visual state and how it's checked. Cover more than the happy-path look — span static state, token/motion, AND interaction/a11y: e.g. "empty/loading/error state renders correctly, not a blank panel"; "primary button uses the accent token, not a hardcoded hex"; "enter motion ≤ 200ms"; "opening the dialog moves focus into it and Esc closes it"; "the submit control shows a loading state and is disabled while the request is in flight". Write them against the design-language doc (`flow.config.json.designLanguagePath`). These are the criteria the agent dials in against at Step 8/9 (`${CLAUDE_PLUGIN_ROOT}/docs/workflow.md`) and the human signs off on at the merge gate. **Declaration only** — the criteria are not yet mechanically verified (that's a later link in the Deliverable-quality roadmap track); today's consumers are the agent's visual dial-in and the human at both gates.

`spike` mode replaces (4) with a single "Research question" line and (5) with a "Disposability" line. `tiny` mode skips (4) and (5) entirely but still names the file + the one-line change. `Visual-walk` (8) is appended, not inserted — it applies only to UI changes and is **N/A under `tiny`**. It is **N/A for a non-visual `spike`**, but a **visual/interaction `spike`** should still declare one: `/flow:verify-build` §5a captures frames + renders the ephemeral walkthrough only when a `Visual-walk` block is present (on a `uiSurface:true` project), independent of mode — so a visual spike without one gives §5a no declared states to capture and the walkthrough you wanted isn't produced (see `${CLAUDE_PLUGIN_ROOT}/docs/workflow.md` § Spike mode). The (4)/(5) mode-override references above are unaffected by its addition.

**Active-block placement (load-bearing for `/flow:verify-build`).** `/flow:verify-build` parses the **Spec-walk** and **Visual-walk** blocks mechanically (`extract-criteria.py` / `extract-visual-states.py`), and each parser extracts only the **first** block of its kind in the plan doc. So when a plan doc retains shipped PRs' blocks, **author the active PR's plan at the top** — the active Spec-walk/Visual-walk must precede any retained ones. Retained blocks below are simply ignored; they need no heading qualification. (If the active block isn't first, the parser warns loudly and extracts the wrong block — don't rely on the warning, place it correctly.)

One case placement alone can't fix: an active PR that declares a **Spec-walk** but deliberately **no Visual-walk** (a backend-only change), while a retained PR below declares one. There is no active Visual-walk to put at the top, and since only one Visual-walk block exists in the file the "multiple blocks" warning can't fire either. `extract-visual-states.py` therefore also requires the block to be **co-located with the active section** (anything above the *second* Spec-walk heading): a Visual-walk found only inside a retained section yields zero assertions plus a loud warning, rather than silently handing the active PR another PR's capture state-set. A `Visual-walk` written above its sibling `Spec-walk` in the same section still counts.

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
