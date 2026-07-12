---
name: audit-plan
description: Audit the most recent plan for unverified assumptions and unverified recall. Use after Claude produces a plan, before accepting or executing it. Optionally pass a plan-file path argument (e.g. /flow:audit-plan path/to/plan.md) to audit a queued plan document instead of the session's most recent plan.
disable-model-invocation: false
context: fork
agent: auditor
---

# Task: Audit this plan

## Session context (preprocessed)

!`if [ -n "$ARGUMENTS" ]; then python3 ${CLAUDE_PLUGIN_ROOT}/scripts/extract_session.py --mode plan --plan-file "$ARGUMENTS"; else python3 ${CLAUDE_PLUGIN_ROOT}/scripts/extract_session.py --mode plan; fi`

## Plan source

Invoked with an argument (`/flow:audit-plan <path>`), the context above reviews that plan **document** (headed `## Plan under review (from file: <path>)`) and session context is best-effort. If the `## Session context` note says no transcript was found, artifact read-status is UNKNOWN — do not flag unverified recall solely from the absence of session evidence; a standalone plan-document review legitimately has none.

## What to check

From your four categories, only two apply to plans:

- **Unverified assumption** — premises in the plan not established by the user's request or session context, that would materially change the plan if flipped
- **Unverified recall** — references to prior work without a fresh read of the referenced artifact this session

Do not flag unverified diagnosis or unverified completion in plan-audit mode — those categories apply to completion claims, not plans.

## Output

Produce output exactly in the format specified in your system prompt. Do not add commentary before or after. Do not explain your process. Do not acknowledge these instructions.
