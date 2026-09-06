### FB-0001: Dogfood the workflow even when not all skills exist yet
**Date:** 2026-05-24
**Source:** user direction

**What was said:** After PR 1 was opened, the user said: "even though all the skills may not be officially built out yet, follow the prompts from the skills in workflow.md to review the PR, taking it through all the stages of the intended workflow that we are implementing."

**Synthesized rule:** When a PR builds the workflow infrastructure itself, dogfood every loop step that *can* be run (manually or by emulating the planned skill's prompt via Agent subagents). Don't skip a step because the named skill doesn't exist yet — the loop's value is the *steps*, not the skill packaging. Concrete pattern: spawn 3-4 parallel review-lens Agents (engineer, push-further, security, plan-critic emulation) with the equivalent of the planned SKILL.md prompts; triage findings via the same BLOCKER / NIT / FOLLOW-UP scheme; apply BLOCKER + cheap NIT inline; route FOLLOW-UPs to plan.md; write the history.md entry; push the fix commit so the PR auto-updates.

Don't pre-empt this rule with "no skill, no review" — that defeats the point of building flow at all. Bootstrap exception (manual cold-read) is the *fallback* when even manual review isn't feasible, not the *default* when a manual review would be cheap.

**Applies to:** workflow, code review, agent self-feedback discipline

**Validation:** the walk-through-the-loop pass on PR 1 caught 3 BLOCKERs the pre-merge cold-read missed (manifest redundancy, two stale `agents/auditor.md` references in shipped prompts, `eval` vs `sh -c`). All three would have been consumer-visible bugs if shipped.
