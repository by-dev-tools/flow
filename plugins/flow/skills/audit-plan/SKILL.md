---
name: audit-plan
description: Audit the most recent plan for unverified assumptions and unverified recall. Use after Claude produces a plan, before accepting or executing it.
disable-model-invocation: false
context: fork
agent: auditor
---

# Task: Audit this plan

## Session context (preprocessed)

!`python3 ${CLAUDE_PLUGIN_ROOT}/scripts/extract_session.py --mode plan`

## What to check

From your four categories, only two apply to plans:

- **Unverified assumption** — premises in the plan not established by the user's request or session context, that would materially change the plan if flipped
- **Unverified recall** — references to prior work without a fresh read of the referenced artifact this session

Do not flag unverified diagnosis or unverified completion in plan-audit mode — those categories apply to completion claims, not plans.

## Output

Produce output exactly in the format specified in your system prompt. Do not add commentary before or after. Do not explain your process. Do not acknowledge these instructions.
