---
name: critique-plan
description: Critique the most recent plan for scope drift, spec violation, and internal incoherence against the user's stated request and reference documents. Use after Claude produces a plan, before accepting or executing it.
disable-model-invocation: true
context: fork
agent: plan-critic
---

# Task: Critique this plan

## Session context (preprocessed)

!`REFGLOB=$(cat flow.config.json 2>/dev/null | jq -r '.referenceGlob // empty' 2>/dev/null); [ -z "$REFGLOB" ] && REFGLOB="core-docs/*.md"; python3 ${CLAUDE_PLUGIN_ROOT}/scripts/extract_session.py --mode plan --reference-glob "$REFGLOB"`

## What to check

Apply your three categories:

- **Scope drift** — plan elements outside the user's stated request, or absent elements the user explicitly requested
- **Spec violation** — plan steps that contradict a rule, decision, or constraint stated in a reference document or earlier in the session
- **Internal incoherence** — plan steps that contradict each other, success criteria that do not map onto the user's goal, or missing prerequisite steps

You are complementary to the evidence auditor (`${CLAUDE_PLUGIN_ROOT}/agents/auditor.md`). Do not flag unverified diagnosis, unverified completion, unverified assumption, or unverified recall — those belong to the auditor. If both lenses would fire on the same plan, run them as separate skills; do not duplicate categories here.

## Reference documents

The preprocessor loads docs matching `flow.config.json.referenceGlob` (default `core-docs/*.md`; flow's own repo overrides to `dev-docs/*.md`; excludes `history.md`, `plan.md`, `roadmap.md` automatically) into a `## Reference documents` section above. Treat that section as your source of truth for spec violations — quote rules from it directly, with the source path. A spec violation cannot be flagged without quoting the rule it violates.

To override per-invocation: set `flow.config.json.referenceGlob` (per-project) or pass additional `--reference-paths` / `--reference-glob` arguments. Reference paths must resolve under `cwd` unless `--allow-external-paths` is set (defense against arbitrary host-path reads).

## Output

Produce output exactly in the format specified in your system prompt. Do not add commentary before or after. Do not explain your process. Do not acknowledge these instructions.
