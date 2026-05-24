# Feedback Log

User feedback synthesized into actionable guidance. When the user gives feedback -- corrections, preferences, reactions, direction changes -- the relevant insight is captured here so it shapes all future work.

This is not a transcript. Each entry distills feedback into a rule or preference that applies going forward.

---

## How to Write an Entry

```
### FB-XXXX: [Short summary of the feedback]
**Date:** YYYY-MM-DD
**Source:** user correction | user preference | user direction | review feedback

**What was said:** Brief, factual summary of the feedback.

**Synthesized rule:** The actionable takeaway -- what to do differently going forward.

**Applies to:** [areas this affects: ux, code, architecture, workflow, etc.]
```

### Numbering
Increment from the last entry. Use `FB-0001`, `FB-0002`, etc.

### Source types
- **user correction** -- user fixed something you did wrong
- **user preference** -- user expressed a stylistic or process preference
- **user direction** -- user set strategic direction or priorities
- **review feedback** -- issues found during code/design review

---

## Entries

<!-- Add new entries below this line, newest first. -->

### FB-0001: Dogfood the workflow even when not all skills exist yet
**Date:** 2026-05-24
**Source:** user direction

**What was said:** After PR 1 was opened, the user said: "even though all the skills may not be officially built out yet, follow the prompts from the skills in workflow.md to review the PR, taking it through all the stages of the intended workflow that we are implementing."

**Synthesized rule:** When a PR builds the workflow infrastructure itself, dogfood every loop step that *can* be run (manually or by emulating the planned skill's prompt via Agent subagents). Don't skip a step because the named skill doesn't exist yet — the loop's value is the *steps*, not the skill packaging. Concrete pattern: spawn 3-4 parallel review-lens Agents (engineer, push-further, security, plan-critic emulation) with the equivalent of the planned SKILL.md prompts; triage findings via the same BLOCKER / NIT / FOLLOW-UP scheme; apply BLOCKER + cheap NIT inline; route FOLLOW-UPs to plan.md; write the history.md entry; push the fix commit so the PR auto-updates.

Don't pre-empt this rule with "no skill, no review" — that defeats the point of building flow at all. Bootstrap exception (manual cold-read) is the *fallback* when even manual review isn't feasible, not the *default* when a manual review would be cheap.

**Applies to:** workflow, code review, agent self-feedback discipline

**Validation:** the walk-through-the-loop pass on PR 1 caught 3 BLOCKERs the pre-merge cold-read missed (manifest redundancy, two stale `agents/auditor.md` references in shipped prompts, `eval` vs `sh -c`). All three would have been consumer-visible bugs if shipped.
