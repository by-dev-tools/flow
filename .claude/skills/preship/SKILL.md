---
name: preship
description: >
  Pre-ship review against project standards. Use after completing a feature
  or before shipping to catch gaps. Checks recent changes against spec,
  feedback rules, and plugin quality bar. Distinct from the plugin's own
  /audit-plan and /audit-completion commands -- this is project-dev only.
context: fork
agent: Explore
allowed-tools: Read, Grep, Glob, Bash
---

You are auditing recent changes against project standards. This runs in an isolated context.

## 1. Gather context

- Run `git diff main..HEAD --name-only` to list changed files
- Run `git log --oneline main..HEAD` for commit history
- Read `CLAUDE.md` for project standards and the plugin-vs-dev boundary
- Read `dev-docs/feedback.md` for documented rules and past corrections
- Read `dev-docs/spec.md` for the canonical feature list and known limitations

## 2. Check documentation completeness

- Does `dev-docs/history.md` have entries for the changes? Are they complete (what, why, tradeoffs)?
- Does `dev-docs/plan.md` reflect the current state?
- Were any user corrections made that aren't captured in `dev-docs/feedback.md`?

## 3. Check against feedback rules

For each entry in `dev-docs/feedback.md`, check if the recent changes violate any synthesized rules. Flag violations.

## 4. Check plugin quality bar (from CLAUDE.md)

For any changes under `plugins/flow/agents/`, `plugins/flow/skills/`, `plugins/flow/scripts/`, `plugins/flow/evals/`, or the manifests (`.claude-plugin/marketplace.json`, `plugins/flow/.claude-plugin/plugin.json`):

- **Correct:** auditor outputs still match the `ISSUE` / `AUDIT SUMMARY` / `No issues flagged.` schema in `plugins/flow/agents/auditor.md`. Evals pass.
- **Evidence-backed:** any new category, rule, or heuristic has a fixture in `plugins/flow/evals/fixtures/` demonstrating it.
- **Graceful on malformed input:** preprocessing paths still handle missing session files, empty transcripts, and malformed JSONL without crashing.
- **Lean:** Python stdlib only. No new dependencies.
- **Honest limitations:** if a limitation listed in `README.md` was addressed or a new one introduced, the README reflects it.

## 5. Report

Produce a concise report:

```
## Pre-Ship Review

### Documentation
- [pass/fail] history.md updated
- [pass/fail] plan.md reflects current state
- [pass/fail] feedback.md captures corrections

### Feedback Rules
- [list any violations of synthesized rules]

### Quality Bar
- [list any gaps against the CLAUDE.md quality bar]

### Recommendations
- [actionable items to fix before shipping]
```
