# General Rules

These rules apply to all work in this project. They enforce the documentation workflow, not code style -- code style is project-specific and belongs in CLAUDE.md or a separate rule file.

## Documentation discipline

- Every non-trivial change must have a corresponding `dev-docs/history.md` entry before committing.
- `dev-docs/plan.md` must reflect reality. If you completed something, mark it done. If scope changed, update it.
- When the user corrects your approach or expresses a preference, add a synthesized entry to `dev-docs/feedback.md` before continuing.
- Read `dev-docs/feedback.md` before starting work to avoid repeating documented mistakes.

## Decision tracking

- When a change involves a non-trivial decision (a reasonable alternative existed), document the options considered and why this one was chosen in `dev-docs/history.md`.
- "What" goes in the change itself. "Why" goes in the documentation.
- Tradeoffs discussed during implementation must be captured -- they are the most valuable part of the history for future context.

## Scope discipline

- Do what was asked. Don't refactor adjacent code, add unrequested features, or "improve" things that work.
- No dead code, commented-out code, unused imports, or placeholder files.
- If something isn't needed yet, don't create it.

## Autonomous work guardrails

Always confirm with the user before proceeding if the action involves:

1. **Cost exposure** -- API calls that could hit rate limits or incur charges, adding paid services
2. **Permanence** -- irreversible changes (deleting data models, breaking migration paths, force pushes)
3. **Risk** -- security-sensitive changes, privacy implications, anything where a reasonable person might disagree

Everything else (bug fixes, spec compliance, reliability, polish) can be done autonomously with documentation.
