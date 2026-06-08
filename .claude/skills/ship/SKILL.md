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
- **Doc-currency (mirror of `/flow:ship` Step 5a/5b — keeps these docs from going stale):** refresh `dev-docs/roadmap.md` "Now" (current version from `plugins/flow/.claude-plugin/plugin.json`, Recently-shipped line, ▶ Next-up pointer), sweep shipped items in `plan.md` → "Recently Completed", and **clear this PR's now-shipped `FB-XXXX` line(s) from `dev-docs/reserved-feedback-numbers.md`** (the step this dev-side `/ship` historically forgot — do it here). Then verify the `plugin.json` version token appears in roadmap "Now" + plan "Current Focus"; if not, reconcile before committing.

If the user gave feedback during this session that isn't already captured:
- Add a synthesized entry to `dev-docs/feedback.md`

## 3. Stage and commit

- Stage all relevant files (code + doc updates). Never stage `.env`, secrets, or credentials.
- Write a concise commit message explaining **why** the change was made.

## 4. Push and create PR

- Push with `-u` flag
- Create a PR using `gh pr create` with:
  - Short title (under 70 characters)
  - Body with `## Summary` (1-3 bullets) and `## Test plan` (checklist)
  - **If this PR came out of a driven flow loop** (you ran `/flow:critique-plan`,
    `/simplify`, `/flow:staff-review`, etc. earlier in the session), also add a
    `## Flow run` table documenting the loop — see `/flow:ship` §7 for the table
    shape and the fill rules (✓ ran / `skipped (<reason>)`, Notable = genuine
    signal or `—`, no manufactured notes).

> **Note:** this dev-side `/ship` is the older, simpler push+PR+merge command.
> It does not itself orchestrate the loop's review steps, and CLAUDE.md treats it
> as a surface distinct from the published `/flow:ship` (no sync convention). The
> `## Flow run` table documents the *session's* loop, so include it only when the
> loop was actually driven — otherwise there's nothing to document and the
> Summary + Test plan suffice. Flow's own PRs should ship via `/flow:ship` per
> `.claude/rules/general.md`, which produces the table directly.

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
