# General Rules

These rules apply to all work in this project. They enforce the documentation workflow, not code style -- code style is project-specific and belongs in CLAUDE.md or a separate rule file.

**Relationship to `plugins/flow/skills/general/SKILL.md` (FB-0085, Phase 00 / 00c):** that file is the plugin's shipped, project-agnostic rule-skill for *consumers* of flow; this file is flow's own dev-side meta-rule for *building* flow, and the two audiences genuinely diverge in most sections (this file's Consistency discipline and dogfooding-specific Workflow discipline below would violate the plugin's project-agnostic quality bar if shipped there; the plugin's Mode flags and ship auto-advance predicate don't belong in a meta-rule about developing flow itself). Three sections are pure overlap that had drifted out of sync for no reason -- **Scope discipline**, **Decision tracking**, **Autonomous work guardrails** -- and were re-synced to the plugin's wording in this pass. If you edit any of those three here, mirror the edit in the plugin file (and vice versa) or note here why this occurrence is deliberately different.

## Documentation discipline

- Every non-trivial change must have a corresponding `dev-docs/history.md` entry before committing.
- `dev-docs/plan.md` must reflect reality. If you completed something, mark it done. If scope changed, update it.
- When the user corrects your approach or expresses a preference, add a synthesized entry to `dev-docs/feedback.md` before continuing.
- Read `dev-docs/feedback.md` before starting work to avoid repeating documented mistakes.

## Decision tracking

- When a change involves a non-trivial decision (a reasonable alternative existed), note the tradeoff so `/flow:ship` can capture it in `dev-docs/history.md`. A one-line scratch note is fine; `/flow:ship` will write the formal entry.
- "What" goes in the code change itself. "Why" goes in the history doc at ship time.
- Tradeoffs are the most valuable part of the history doc -- they're what future sessions need to avoid re-litigating.

## Scope discipline

- Do what was asked. Don't refactor adjacent code, add unrequested features, or "improve" things that work.
- No dead code, commented-out code, unused imports, or placeholder files.
- If something isn't needed yet, don't create it.
- **New scope discovered mid-execution: surface to the user, don't silently absorb.** Update the plan with a fresh confidence verdict for the new assumption, get approval, then continue.

## Consistency discipline (FB-0010)

Most recurring bug class flow's own development has surfaced (6 incidents across PRs 1, B, D, E, F-pass-1, F-pass-2): "consistency that depends on author memory." Two flavors:

1. **Silent-skip on edge case.** Code that fails on an edge case without surfacing the failure (stale paths returning empty, unset vars expanding silently, slash-commands run in shell context, regex inversions, POSIX-vs-bash mismatches). Defense: pair every `2>/dev/null || true` / `// empty` / `|| ""` fallback with an explicit positive assertion or a `[WARN]` branch. If unset is fatal, fail-fast at the entrypoint with a clean install hint (FB-0009 pattern).

2. **Fan-out contradiction.** A contract value (count, name, slot, version) referenced in N files, where a contract change only updated some of them. Defense: **grep first, edit second.** When changing a count or name, run `git grep -nE '<old-value>'` across the codebase before staging. Treat every survivor as a fix that ships with the contract change, not a follow-up. Specifically watch: schema slot counts (`N slots`), skill/agent counts (`N user-visible skills`), version strings, slot/flag/skill names.

3. **Prohibition satisfiable by deletion.** An assertion that only forbids something — `X not in <text>`, "no `Skill()` call names a disabled target", "the manifest is absent" — passes in two opposite worlds: the contract is honored, *or* the contract was removed. The check cannot tell them apart, so deleting the protected thing turns it green. Defense: **never ship a negative assertion alone.** Pair it with the positive assertion of the thing it protects (`"branch -d" in skill` **and** `"branch -D" not in skill`). The same applies to lint remediation text — if the advice names a fix that deletes the call site, it is telling the author to satisfy the detector rather than the contract.

   This is not hypothetical, and the repo contains both outcomes. `run_visual_history_evals.py` pairs its negative with three positives and is correct. `skill-does-not-CALL-land` was the identical shape *without* the pairing, so when FB-0074 satisfied it by deleting `/flow:post-merge`'s composition call, CI went green over a feature that no longer existed — for four releases (FB-0077). Same repo, same class, opposite outcomes; the only variable was whether anyone remembered to add the positive.

When in doubt, ask: "If a colleague greps for the old value tomorrow, will they find a contradiction?" If yes, fix it now. And: "If someone deleted the thing this check protects, would the check still pass?" If yes, it isn't a check yet.

## Workflow discipline (FB-0010 workflow-step sub-class)

This repo dogfoods the flow plugin it ships. When opening a PR from this repo:

- **Always invoke `/flow:ship`** (or `/flow:ship-spike` for spike-mode PRs) at the end of the loop. `/flow:ship` orchestrates the final-pass pipeline: `/flow:security-review` + `/flow:accessibility-review` (with per-diff early-exit on docs-only PRs), feedback synthesis into both layers, doc updates, then PR open.
- **Never invoke `gh pr create` directly.** Doing so bypasses the entire ship pipeline. Even on docs-only PRs where the security + a11y reviews would early-exit, the `STATUS: SKIPPED` audit-trail signal is load-bearing — skipping the spawn means there's no record of the decision either way. (See `plugins/flow/docs/workflow.md` § "Never bypass `/flow:ship`" for the cross-shipped contract.)
- If `/flow:ship` errors at a pre-flight gate, fix the root cause; don't route around it. Pre-flight failures are signal.

## Autonomous work guardrails

This workflow is **hybrid managed autonomy** -- human-gated at Plan and Merge, with autonomy-friendly primitives between. Even inside the autonomous portion, always confirm with the user before proceeding if the action involves:

1. **Cost exposure** -- API calls that could hit rate limits or incur charges, adding paid services
2. **Permanence** -- irreversible changes (deleting data models, breaking migration paths, force pushes, `rm -rf`)
3. **Risk** -- security-sensitive changes, privacy implications, anything where a reasonable person might disagree

Bug fixes, spec compliance, reliability work, and polish can proceed autonomously (still requires a plan + user approval at the plan gate).
