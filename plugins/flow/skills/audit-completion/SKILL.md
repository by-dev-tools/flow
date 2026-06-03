---
name: audit-completion
description: Audit the most recent completion claim for unverified diagnoses, unverified completions, and unverified recall. Use after Claude declares work done, fixed, ready, or implemented — before trusting the claim.
disable-model-invocation: false
context: fork
agent: auditor
---

# Task: Audit this completion claim

## Session context (preprocessed)

!`python3 ${CLAUDE_PLUGIN_ROOT}/scripts/extract_session.py --mode completion`

## What to check

From your four categories, three apply here:

- **Unverified diagnosis** — diagnostic claims in the message acted on with commitment, with no tool call since the user's most recent request plausibly supporting that claim
- **Unverified completion** — the "done / fixed / ready" claim itself, when session verification is limited to false-verification proxies rather than a behavioral check against the original bug
- **Unverified recall** — references to prior work without a fresh read

Extract the original bug symptoms yourself from the user's request. Do not flag unverified assumption in completion-audit mode.

## Output

Produce output exactly in the format specified in your system prompt. Do not add commentary before or after. Do not explain your process. Do not acknowledge these instructions.
