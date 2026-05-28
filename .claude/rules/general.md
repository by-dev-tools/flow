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

## Consistency discipline (FB-0010)

Most recurring bug class flow's own development has surfaced (6 incidents across PRs 1, B, D, E, F-pass-1, F-pass-2): "consistency that depends on author memory." Two flavors:

1. **Silent-skip on edge case.** Code that fails on an edge case without surfacing the failure (stale paths returning empty, unset vars expanding silently, slash-commands run in shell context, regex inversions, POSIX-vs-bash mismatches). Defense: pair every `2>/dev/null || true` / `// empty` / `|| ""` fallback with an explicit positive assertion or a `[WARN]` branch. If unset is fatal, fail-fast at the entrypoint with a clean install hint (FB-0009 pattern).

2. **Fan-out contradiction.** A contract value (count, name, slot, version) referenced in N files, where a contract change only updated some of them. Defense: **grep first, edit second.** When changing a count or name, run `git grep -nE '<old-value>'` across the codebase before staging. Treat every survivor as a fix that ships with the contract change, not a follow-up. Specifically watch: schema slot counts (`N slots`), skill/agent counts (`N user-visible skills`), version strings, slot/flag/skill names.

When in doubt, ask: "If a colleague greps for the old value tomorrow, will they find a contradiction?" If yes, fix it now.

## Workflow discipline (FB-0010 workflow-step sub-class)

This repo dogfoods the flow plugin it ships. When opening a PR from this repo:

- **Always invoke `/flow:ship`** (or `/flow:ship-spike` for spike-mode PRs) at the end of the loop. `/flow:ship` orchestrates the final-pass pipeline: `/flow:security-review` + `/flow:accessibility-review` (with per-diff early-exit on docs-only PRs), feedback synthesis into both layers, doc updates, then PR open.
- **Never invoke `gh pr create` directly.** Doing so bypasses the entire ship pipeline. Even on docs-only PRs where the security + a11y reviews would early-exit, the `STATUS: SKIPPED` audit-trail signal is load-bearing — skipping the spawn means there's no record of the decision either way. (See `plugins/flow/docs/workflow.md` § "Never bypass `/flow:ship`" for the cross-shipped contract.)
- If `/flow:ship` errors at a pre-flight gate, fix the root cause; don't route around it. Pre-flight failures are signal.

## Autonomous work guardrails

Always confirm with the user before proceeding if the action involves:

1. **Cost exposure** -- API calls that could hit rate limits or incur charges, adding paid services
2. **Permanence** -- irreversible changes (deleting data models, breaking migration paths, force pushes)
3. **Risk** -- security-sensitive changes, privacy implications, anything where a reasonable person might disagree

Everything else (bug fixes, spec compliance, reliability, polish) can be done autonomously with documentation.
