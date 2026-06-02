---
name: ship
description: >
  Commit changes, create a PR, and merge to main. Use when shipping completed
  work -- updates core docs, stages changes, writes a commit message, creates
  a GitHub PR, and merges it. Triggered by /ship or phrases like "push this",
  "ship it", "create a PR", or "merge to main".
disable-model-invocation: true
allowed-tools: Read, Edit, Write, Glob, Grep, Bash
---

You are running the ship workflow. Follow every step in order.

## 1. Understand the changes

- Run `git status` and `git diff` (staged + unstaged)
- Run `git log --oneline main..HEAD` to see commits on this branch
- If on `main`, create a new branch with a descriptive kebab-case name

## 2. Update core docs

Read `dev-docs/history.md` and `dev-docs/plan.md`.

For each meaningful change on this branch:
- Add an entry to `dev-docs/history.md` following the existing format (what, why, decisions, tradeoffs). Use today's date. Skip if an entry already exists.
- Update `dev-docs/plan.md` -- mark completed items, update "Current focus" if needed.

If the user gave feedback during this session that isn't already captured:
- Add a synthesized entry to `dev-docs/feedback.md`

## 3. Stage and commit

- Stage all relevant files (code + doc updates). Never stage `.env`, secrets, or credentials.
- Write a concise commit message explaining **why** the change was made.

## 4. Push and create PR

- Push with `-u` flag
- Create a PR using `gh pr create` with:
  - Short title (under 70 characters)
  - Body with `## Summary` (1-3 bullets), `## Test plan` (checklist), and a `## Flow run` table (below)

The `## Flow run` table documents the full loop run — every step that ran, what
was skipped and why, and any significant decision or finding. (Same shape as the
published `/flow:ship` §7; this dogfood skill mirrors it for consistency.)

```markdown
## Flow run
Each loop step — ran or skipped (mode-dependent) — and any significant decision
or finding it produced. Leave the note "—" when routine; don't force it.

| Step | Status | Notable |
|---|---|---|
| Clarify | ✓ | — |
| Plan + /flow:critique-plan | ✓ | <critic findings that changed the plan / —> |
| Execute | ✓ | <load-bearing impl decisions / —> |
| Preflight | ✓ | green / <what ran> |
| /simplify | ✓ · skipped (spike/tiny) | <what collapsed / —> |
| /flow:staff-review | ✓ · skipped (spike/tiny) | <BLOCKERs fixed, real findings / —> |
| /flow:security-review | ✓ · skipped (<reason>) | <result / —> |
| /flow:accessibility-review | ✓ · skipped (<reason>) | <result / —> |
| /flow:verify-build | ✓ · skipped (<reason>) | <overall_verdict / —> |
| Doc synthesis | ✓ | <docs updated> |

Deferred follow-ups: see the roadmap and plan docs.
```

Populate it from THIS session's loop history. **Status:** `✓` if the step ran,
`skipped (<reason>)` otherwise — always name the reason (spike skips /simplify +
/flow:staff-review; tiny also skips spec-walk; a11y skips on `uiSurface:false` or
no UI in diff; security skips on a doc-only diff; verify-build skips on
`verifyEnabled:false` or `platform` library|none). **Notable:** genuine signal
only — a plan-critic catch, a load-bearing decision, a fixed BLOCKER, a real
review finding, the docs updated; routine steps get `—`. **Do not manufacture
notes.** Follow-ups stay canonical in the roadmap/plan docs; the table only
points at them.

## 5. Handle conflicts (if any)

If the push or merge fails due to conflicts:

1. **Surface the conflict clearly.** Show which files conflict and a brief explanation of why (e.g., "main has new commits that touch the same lines your branch changed").
2. **Present options:**
   - **Rebase onto target branch** -- rewrites your commits on top of the latest target. Best when: your branch has a small number of clean commits you want to preserve individually.
   - **Merge target into your branch** -- creates a merge commit. Best when: you want to preserve exact branch history or the rebase would be complex.
   - **Abort and let the user resolve manually** -- safest when conflicts look non-trivial or touch critical code.
3. **Recommend the best option** based on the situation (number of commits, conflict complexity, whether the files are safety-critical).
4. **Wait for user approval** before resolving. Never force-push or auto-resolve conflicts without confirmation.
5. After resolution, re-push and verify the PR is clean before proceeding.

## 6. Merge

- Ask the user how to merge if not obvious from project conventions (squash, merge commit, rebase)
- Ask which branch to merge into if the project uses a staging/integration branch before main
- Merge using the appropriate `gh pr merge` strategy
- Confirm success and return the PR URL
