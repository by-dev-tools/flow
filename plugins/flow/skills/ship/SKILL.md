---
name: ship
description: >
  Final-pass pipeline for a completed workstream. Runs security-review and
  accessibility-review as a final safety net (assuming staff-review already
  ran during the feature work), applies any blocker/cheap-nit fixes, then
  synthesizes session feedback, updates project docs (history, plan,
  roadmap, spec, feedback) with the rationale, commits, pushes, and opens
  a PR. Never merges. Trigger phrases: "ship it", "ship this", "/flow:ship",
  "push and open the PR", "wrap this up".
disable-model-invocation: true
allowed-tools: Read, Edit, Write, Glob, Grep, Bash, Agent, TaskCreate, TaskUpdate
---

You are running the flow ship pipeline. Follow every step in order. **Never merge.**

## Project context (resolved at invocation)

- Project config: !`cat flow.config.json 2>/dev/null || echo "(no flow.config.json — using built-in defaults)"`
- Default branch (for PR base): !`git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@' || cat flow.config.json 2>/dev/null | jq -r '.defaultBranch // "main"' 2>/dev/null || echo "main"`
- Current branch: !`git branch --show-current`

The `flow.config.json` slots referenced below have built-in fallbacks (see "Config slots" at the bottom of this skill). If a slot is unset and has no safe default, the pipeline prints a loud `⚠️` warning rather than silently no-op.

## 0. Pre-flight

Confirm there is something to ship. In parallel:
- `git status --short`
- `git log --oneline origin/$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@' || echo main)..HEAD`
- `gh pr list --head $(git branch --show-current) --json number,url 2>/dev/null`

Classify:
- **PR-OPEN** — at least one PR returned. Note the number for body updates.
- **LOCAL-ONLY** — commits ahead and/or dirty tree, no PR yet.
- **NOTHING-TO-SHIP** — clean tree at the default branch. Stop and tell the user.

If on the default branch, create a descriptive kebab-case branch first.

## 1. Final-pass reviews

> **[PR 1 LIMITATION]** `/flow:security-review` and `/flow:accessibility-review` are not yet available in the flow plugin — they ship in PR 2. Until then, this step is a no-op placeholder.
>
> If your project ships its own equivalents (e.g., a project-local `/security-review` skill), invoke them manually here. Otherwise, the user should run them manually before saying "ship it" for any user-visible or high-risk change. Low-risk changes (typo fixes, doc-only edits, internal refactors) can skip without manual review.
>
> When PR 2 backfills this section, it will sequentially invoke `/flow:security-review` and `/flow:accessibility-review` via the Skill tool; each will self-triage and apply BLOCKER + cheap NIT fixes in-tree and return FOLLOW-UP findings for step 2 routing.

## 2. Route follow-ups

Any FOLLOW-UP findings from the (currently manual) reviews — or from `/simplify` / `/flow:staff-review` (PR 2) earlier in the loop — need to land in the right doc:

- Belongs to active work → `flow.config.json.planPath` (default `dev-docs/plan.md` for the plugin's own repo; consumers typically set this to `core-docs/plan.md`). Under the current work item.
- Larger / future work → `flow.config.json.roadmapPath` (default `dev-docs/roadmap.md`; consumers typically `core-docs/roadmap.md`). Under the relevant horizon.

Mention follow-ups in the PR body for reviewer awareness, but **never only in the PR body** — the doc entry is canonical.

If any new BLOCKER fix changed code, re-run the project's typecheck once before moving on:

```sh
# Resolve and run the configured typecheck command
TYPECHECK=$(cat flow.config.json 2>/dev/null | jq -r '.typecheckCmd // empty')
if [ -n "$TYPECHECK" ]; then
  eval "$TYPECHECK"
else
  echo "⚠️ flow.config.json.typecheckCmd not set; skipping typecheck re-run. Set this slot to enable typecheck on /flow:ship."
fi
```

## 3. Synthesize session feedback (two layers)

### 3a. User feedback → `flow.config.json.feedbackPath` (default `dev-docs/feedback.md`; consumers typically `core-docs/feedback.md`)

Review this conversation (and any prior session since the last PR on this branch) for:
- User corrections — places you got it wrong and the user fixed your direction.
- User preferences — stylistic or process calls the user made.
- User direction — strategic priorities or scope changes.
- Challenges solved — a non-obvious problem and how it was resolved.

Add new entries to the configured feedback doc following the FB-XXXX format. Increment from the last ID. Skip anything already captured. The bar: would a future session benefit from this rule? If yes, write it down.

### 3b. Agent self-feedback → failure-pattern memory

> **[PR 1 LIMITATION]** The memory machinery (`tools/memory/check.mjs`, the source-diversity bar tooling, the audit-due check) ships in flow PR 2 at `plugins/flow/tools/memory/`. Until then, skip this sub-step.
>
> Single-source findings are intentionally low-value to capture; the source-diversity bar exists for a reason. For now, surface any pattern you noticed in the PR body under "Lessons learned" — it can be promoted to a real memory entry once PR 2 lands the tooling and the pattern recurs.
>
> When PR 2 backfills this section, it will: (i) check corpus size via `node ${CLAUDE_PLUGIN_ROOT}/tools/memory/check.mjs`; (ii) apply the source-diversity bar against this PR's findings; (iii) resolve contradictions with the feedback doc; (iv) write new entries to `~/.claude/projects/<canonical>/memory/feedback_<name>.md`; (v) update fire logs and flag 2+ fires as promotion candidates; (vi) trigger a fresh-context audit if `--audit-due` exits 1.

## 4. Update project docs

For each meaningful change in the diff, update via the config slots (all default to `dev-docs/<name>.md`; consumer projects typically set them to `core-docs/<name>.md`):

- **`flow.config.json.historyPath`** (default `dev-docs/history.md`) — add an entry (newest first) with: title, date, branch, what was done, why, design decisions, technical decisions, tradeoffs, lessons learned. Flag with `SAFETY` if it touches persistence, error handling, or fallback behavior.
- **`flow.config.json.planPath`** (default `dev-docs/plan.md`) — move shipped items from "Current Focus" → "Recently Completed". Update "Current Focus" to reflect what's next. Clear stale "Handoff Notes" if the work is done.
- **`flow.config.json.roadmapPath`** (default `dev-docs/roadmap.md`) — log any deferred follow-ups from review under the relevant horizon. Update workstream status if a workstream completed.
- **`flow.config.json.specPath`** (default `dev-docs/spec.md`) — if features changed status (planned → shipped) or new features were added, update the features table. If the product surface area changed materially, update the relevant section.

Do **not** add entries that already exist. Skip silently.

## 5. Commit

Stage code changes + doc updates together (or in two commits if cleaner). Never stage `.env`, secrets, or credentials.

Commit message style: explain **why**, not what. Short subject line, blank line, body if needed. End with:
```
Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```

If safety-critical code changed, include `SAFETY` in the commit subject.

## 6. Push and PR

Push with `-u` if the branch isn't tracking yet.

The PR base branch is resolved via this fallback chain:
1. `git symbolic-ref refs/remotes/origin/HEAD` (the repo's actual default branch)
2. `flow.config.json.defaultBranch`
3. literal `main`

**LOCAL-ONLY**: `gh pr create --base $BASE_BRANCH` with:
- Short title (under 70 chars).
- Body:
  ```markdown
  ## Summary
  - <1-3 bullets on why this exists>

  ## Test plan
  - [ ] <how to verify>

  ## Reviews
  Security and accessibility reviews ran in ship (or were skipped — note explicitly which); staff-review ran during feature work. Deferred follow-ups: see the configured roadmap and plan docs.

  🤖 Generated with [Claude Code](https://claude.com/claude-code)
  ```

**PR-OPEN**: push the new commits. Update the PR body if the summary/test plan needs to reflect the latest scope; otherwise leave it.

## 7. Hand off

Output the PR URL and a one-line summary of what shipped.

If your project has a dev-server skill (e.g., a `/link`-style skill), invoke it now and include the URL so the user can verify in-browser before they review. Flow itself does not bundle a dev-server skill — that's deliberately project-shaped.

**Do not merge.** Do not approve. Do not run `gh pr merge`. The user handles merging.

## Gotchas

- **Untracked files are invisible to `git diff`.** Use `git ls-files --others --exclude-standard` and hand the list to reviewers.
- **Don't double-document.** If a prior review step already updated the history or plan doc for this work, don't duplicate — extend.
- **Reviewers can be confidently wrong.** Spot-check findings before fixing.
- **Scope creep is the failure mode.** A reviewer suggestion that expands scope is a FOLLOW-UP for roadmap/plan, not a blocker.
- **Typecheck is cheap.** Run the configured `typecheckCmd` after any code fix from review; it catches the silly mistakes. The loud-warning pattern (above) exists so an unset slot can't silently no-op — set the slot or accept the no-typecheck risk explicitly.

## Config slots (narrative — JSON Schema lands PR 2)

| Slot | Default | Used by |
|---|---|---|
| `flow.config.json.defaultBranch` | falls back to `git symbolic-ref` then literal `main` | Step 0 (NOTHING-TO-SHIP check), Step 6 (PR base) |
| `flow.config.json.typecheckCmd` | unset → loud warning, never silent | Step 2 (post-fix re-check) |
| `flow.config.json.historyPath` | `dev-docs/history.md` | Step 4 |
| `flow.config.json.planPath` | `dev-docs/plan.md` | Steps 2, 4 |
| `flow.config.json.roadmapPath` | `dev-docs/roadmap.md` | Steps 2, 4 |
| `flow.config.json.specPath` | `dev-docs/spec.md` | Step 4 |
| `flow.config.json.feedbackPath` | `dev-docs/feedback.md` | Step 3a |

Consumer projects (md-manager, designer, etc.) typically override the `*Path` slots to `core-docs/<name>.md` since they keep their own project docs under `core-docs/`. Flow's own dev-tracking lives under `dev-docs/` to leave `core-docs/` free as a name that consumer-template-shipped scaffolding uses.
