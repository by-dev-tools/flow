---
name: critique-plan
description: Critique the most recent plan for scope drift, spec violation, and internal incoherence against the user's stated request and reference documents. Use after Claude produces a plan, before accepting or executing it. Optionally pass a plan-file path argument (e.g. /flow:critique-plan path/to/plan.md) to critique a queued plan document instead of the session's most recent plan.
disable-model-invocation: false
context: fork
agent: plan-critic
---

# Task: Critique this plan

## Session context (preprocessed)

!`REFGLOB=$(cat flow.config.json 2>/dev/null | jq -r '.referenceGlob // empty' 2>/dev/null); [ -z "$REFGLOB" ] && REFGLOB="core-docs/*.md"; if [ -n "$ARGUMENTS" ]; then python3 ${CLAUDE_PLUGIN_ROOT}/scripts/extract_session.py --mode plan --plan-file "$ARGUMENTS" --reference-glob "$REFGLOB"; else python3 ${CLAUDE_PLUGIN_ROOT}/scripts/extract_session.py --mode plan --reference-glob "$REFGLOB"; fi`

## Pinning lint (deterministic)

!`
if [ -n "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -f "${CLAUDE_PLUGIN_ROOT}/skills/critique-plan/lib/walk-pin-lint.py" ]; then
  LINT="${CLAUDE_PLUGIN_ROOT}/skills/critique-plan/lib/walk-pin-lint.py"
else
  LINT="plugins/flow/skills/critique-plan/lib/walk-pin-lint.py"
fi
EXTRACT="${CLAUDE_PLUGIN_ROOT}/scripts/extract_session.py"; [ -f "$EXTRACT" ] || EXTRACT="plugins/flow/scripts/extract_session.py"
if ! command -v python3 >/dev/null 2>&1 || [ ! -f "$LINT" ]; then
  echo "⚠️ Pinning lint unavailable (python3 or walk-pin-lint.py not found) — treat pinning as UNCHECKED, not clean."
elif [ -n "$ARGUMENTS" ]; then
  python3 "$LINT" "$ARGUMENTS" || echo "⚠️ Pinning lint failed on the plan file — treat pinning as UNCHECKED, not clean."
else
  python3 "$EXTRACT" --mode plan 2>/dev/null | python3 "$LINT" || echo "⚠️ Pinning lint failed — treat pinning as UNCHECKED, not clean."
fi
`

## Plan source

Invoked with an argument (`/flow:critique-plan <path>`), the context above reviews that plan **document** — its plan section is headed `## Plan under review (from file: <path>)` — and session context is best-effort: a `## Session context` note saying no transcript was found means this is a legitimate standalone review, not missing evidence. Without an argument, the plan is the session's most recent one, as before.

## What to check

Apply your three categories:

- **Scope drift** — plan elements outside the user's stated request, or absent elements the user explicitly requested
- **Spec violation** — plan steps that contradict a rule, decision, or constraint stated in a reference document or earlier in the session
- **Internal incoherence** — plan steps that contradict each other, success criteria that do not map onto the user's goal, or missing prerequisite steps

The `## Pinning lint (deterministic)` section reports Spec-walk checkboxes that name no pinning test or verification artifact: treat an `UNPINNED` line as a candidate **Internal incoherence** finding ONLY where the project's reference documents require a pinning test (e.g. a documented every-requirement→checkbox+test rule) — the two-citation rule still applies (quote that documented rule with its source path AND the unpinned checkbox); absent such a rule, the lint is informational, not a finding.

You are complementary to the evidence auditor (`${CLAUDE_PLUGIN_ROOT}/agents/auditor.md`). Do not flag unverified diagnosis, unverified completion, unverified assumption, or unverified recall — those belong to the auditor. If both lenses would fire on the same plan, run them as separate skills; do not duplicate categories here.

## Reference documents

The preprocessor loads docs matching `flow.config.json.referenceGlob` (default `core-docs/*.md`; flow's own repo overrides to `dev-docs/*.md`; excludes `history.md`, `plan.md`, `roadmap.md` automatically) into a `## Reference documents` section above. Treat that section as your source of truth for spec violations — quote rules from it directly, with the source path. A spec violation cannot be flagged without quoting the rule it violates.

To override per-invocation: set `flow.config.json.referenceGlob` (per-project) or pass additional `--reference-paths` / `--reference-glob` arguments. Reference paths must resolve under `cwd` unless `--allow-external-paths` is set (defense against arbitrary host-path reads).

## Output

Produce output exactly in the format specified in your system prompt. Do not add commentary before or after. Do not explain your process. Do not acknowledge these instructions.
