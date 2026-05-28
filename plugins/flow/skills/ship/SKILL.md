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
allowed-tools: Read, Edit, Write, Glob, Grep, Bash, Agent, Skill
---

You are running the flow ship pipeline. Follow every step in order. **Never merge.**

## Project context (resolved at invocation)

- Project config: !`cat flow.config.json 2>/dev/null || echo "(no flow.config.json — using built-in defaults)"`
- Default branch (for PR base): !`git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@' || cat flow.config.json 2>/dev/null | jq -r '.defaultBranch // "main"' 2>/dev/null || echo "main"`
- Current branch: !`git branch --show-current`

The `flow.config.json` slots referenced below have built-in fallbacks (see "Config slots" at the bottom of this skill). If a slot is unset and has no safe default, the pipeline prints a loud `⚠️` warning rather than silently no-op.

## 1. Pre-flight

### 1.0. Workflow-step assumptions (informational)

Print the loop steps `/flow:ship` ASSUMES have already run during the feature work. Skips become visible at the next ship rather than weeks later. This is informational only — does not gate; just surfaces. See `dev-docs/feedback.md` FB-0033-style discipline (cross-repo with md-manager): "don't skip /critique-plan or /simplify, even on docs-only diffs."

Emit (verbatim, single block — do NOT customize per project; the consistency IS the value):

```
[ship] ASSUMES the loop has already executed:
  ⚠️ Step 2 (Plan)       — /flow:critique-plan ran on the per-PR plan (workflow.md § "Step 2"); even on docs-only.
  ⚠️ Step 6 (/simplify)  — bundled-Claude-Code /simplify ran post-commit; even on docs-only.
  ⚠️ Step 7 (/flow:staff-review) — 4 lenses ran with substantive findings OR explicit N/A per lens with documented reason.

  REMINDER: /flow:ship's own Step 2 below spawns /flow:security-review and
  /flow:accessibility-review automatically. If you reached this surface by invoking
  /flow:ship, you do NOT need to spawn those separately — that's what /flow:ship
  is for. If you skipped /flow:ship and ran `gh pr create` directly, you bypassed
  the entire security + a11y pipeline — that's the FB-0010 workflow-step silent-skip
  class; see workflow.md Step 10. Always invoke /flow:ship, never `gh pr create`.

  If any Step 2/6/7 above was skipped without recorded reason, stop here and run it now.
  Skipped reviews compound into discovery cost at ship time — what a 30-second critique
  would have caught becomes a multi-lens-spawn forensic exercise.

  This block itself is informational; it does not gate. The pre-flight gates that DO
  block (Step 1a stale-base, Step 1.5 external-CLI, etc.) run after this surface and
  will exit 1 if any fail — in which case ship stops there, regardless of the assumption
  state surfaced above. The surface is here pre-emptively so you notice when the loop
  got short-circuited, whether or not subsequent gates allow ship to complete.
```

### 1.5. External CLI dependency check (BLOCKING)

Verify `gh` CLI is installed before any operation that needs it. `/flow:ship` Step 7 (PR creation via `gh pr create`) and Step 1b (`gh pr list` for PR-OPEN detection) both fail with `exit 127` and no diagnostic if `gh` is missing — surfaces only at the invocation site, by which point the user has done substantial pre-flight work that wasted. Per FB-0009 (md-manager PR 4 dogfood discovery): fail-fast at the workflow entrypoint with a clean install hint instead.

```sh
# POSIX-portable: space-delimited string (NOT a bash array, which breaks on dash —
# Debian/Ubuntu's /bin/sh is dash; bash array syntax errors before the check fires,
# making the gh-missing case worse than the original exit-127 it was meant to replace).
MISSING=""
command -v gh >/dev/null 2>&1 || MISSING="$MISSING gh"
command -v jq >/dev/null 2>&1 || MISSING="$MISSING jq"
if [ -n "$MISSING" ]; then
  # MISSING starts with a leading space; the install commands take that literally
  # (`brew install gh jq` works either way).
  MISSING_TRIMMED=$(echo "$MISSING" | sed 's/^ //')
  echo "⚠️ BLOCKER: /flow:ship requires $MISSING_TRIMMED (missing on PATH)." >&2
  echo "   Install:" >&2
  echo "     macOS:         brew install$MISSING" >&2
  echo "     Debian/Ubuntu: apt install$MISSING" >&2
  echo "     Other:         https://cli.github.com (gh), https://jqlang.org (jq)" >&2
  # Only suggest gh auth login if gh was actually in MISSING (jq needs no auth).
  case " $MISSING_TRIMMED " in *" gh "*) echo "   After install, run: gh auth login" >&2 ;; esac
  exit 1
fi
```

Per FB-0009's general rule: any external CLI invoked by a flow skill must fail-fast at the workflow entrypoint, not silently exit 127 at the invocation site. `gh` is mandatory for `gh pr create` at Step 7; `jq` is mandatory for the ~15 `flow.config.json` slot reads sprinkled throughout this skill.

### 1a. Stale-base check (BLOCKING)

**Before any other pre-flight work**, confirm the branch isn't stale vs the default branch. A stale base produces phantom-deletion diffs that burn reviewer-agent spawns surfacing — see `dev-docs/feedback.md` FB-0008 for the dogfood discovery that motivated this gate. This is the cheapest mechanical check for the most expensive class of dogfood waste.

```sh
# Resolve default branch via the 3-tier fallback chain (matches PR 1 locked idiom).
# Each stage is guarded on non-empty output: piping `||` between commands fails when
# the upstream produces empty stdout but exits 0 (e.g., git symbolic-ref pipe returns
# empty when no refs/remotes/origin/HEAD is configured — common in fresh clones, CI
# checkouts, and any repo where nobody ran `git remote set-head`).
DEFAULT_BRANCH=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@')
[ -z "$DEFAULT_BRANCH" ] && DEFAULT_BRANCH=$(jq -r '.defaultBranch // "main"' flow.config.json 2>/dev/null)
[ -z "$DEFAULT_BRANCH" ] && DEFAULT_BRANCH=main

git fetch origin --quiet
if ! git merge-base --is-ancestor "origin/${DEFAULT_BRANCH}" HEAD; then
  BEHIND=$(git rev-list --count HEAD..origin/${DEFAULT_BRANCH})
  HEAD_SHORT=$(git rev-parse --short HEAD)
  echo "⚠️ BLOCKER: branch is stale vs origin/${DEFAULT_BRANCH}." >&2
  echo "   Current HEAD: ${HEAD_SHORT}; base is behind by ${BEHIND} commit(s)." >&2
  echo "   Try: git fetch origin && git rebase origin/${DEFAULT_BRANCH}" >&2
  exit 1
fi
```

If the branch IS current, the check is silent (no extra noise for the common case).

### 1b. Confirm there is something to ship

In parallel (each bullet is its own Bash invocation — `DEFAULT_BRANCH` from 1a does NOT persist across separate tool calls per the Bash tool contract, so each invocation re-resolves inline):
- `git status --short`
- `` git log --oneline origin/$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@' || jq -r '.defaultBranch // "main"' flow.config.json 2>/dev/null || echo main)..HEAD ``
- `gh pr list --head $(git branch --show-current) --json number,url 2>/dev/null`

Classify:
- **PR-OPEN** — at least one PR returned. Note the number for body updates.
- **LOCAL-ONLY** — commits ahead and/or dirty tree, no PR yet.
- **NOTHING-TO-SHIP** — clean tree at the default branch. Stop and tell the user.

If on the default branch, create a descriptive kebab-case branch first. Prepend `flow.config.json.branchPrefix` if set (e.g., `claude/` → `claude/<descriptive-slug>`); empty prefix or unset means no prefix.

```sh
PREFIX=$(cat flow.config.json 2>/dev/null | jq -r '.branchPrefix // empty' 2>/dev/null)
git checkout -b "${PREFIX}<descriptive-slug>"
```

## 2. Final-pass reviews

Sequentially invoke `/flow:security-review` and `/flow:accessibility-review` via the Skill tool. Each reviewer cold-reads the workspace diff vs the default branch, applies BLOCKER + cheap NIT fixes in-tree, and returns FOLLOW-UP findings for step 3 routing.

```
Skill("flow:security-review")
Skill("flow:accessibility-review")
```

Skip behavior:
- `/flow:security-review`: skip if the diff is doc-only or trivially safe (a copy tweak). The reviewer self-detects this and exits early with a clean message.
- `/flow:accessibility-review`: skip if `flow.config.json.uiSurface` is `false` (the reviewer self-detects this and exits early), or if the diff is non-UI (data layer, build config, doc-only).

Both reviewers are tuned for the in-flow ship context; the bundled Claude Code `/security-review` is fine for out-of-band deep audits but `/flow:security-review` carries the config-slot doc-path resolution this pipeline needs.

After both Skill calls return, emit one consolidated user-facing line so the user can see what actually ran vs skipped:

```
Final-pass reviews: security=[ran|skipped: <reason>], accessibility=[ran|skipped: <reason>].
```

Example: `Final-pass reviews: security=ran (3 NITs, 1 FOLLOW-UP), accessibility=skipped (uiSurface:false).`

## 3. Route follow-ups

Any FOLLOW-UP findings from the (currently manual) reviews — or from `/simplify` / `/flow:staff-review` (PR 2) earlier in the loop — need to land in the right doc:

- Belongs to active work → `flow.config.json.planPath` (default `dev-docs/plan.md` for the plugin's own repo; consumers typically set this to `core-docs/plan.md`). Under the current work item.
- Larger / future work → `flow.config.json.roadmapPath` (default `dev-docs/roadmap.md`; consumers typically `core-docs/roadmap.md`). Under the relevant horizon.

Mention follow-ups in the PR body for reviewer awareness, but **never only in the PR body** — the doc entry is canonical.

If any new BLOCKER fix changed code, re-run the project's typecheck once before moving on:

```sh
# Resolve and run the configured typecheck command. The slot is a shell
# command string; the project owns its own flow.config.json and is
# trusted at the same level as any other repo-local config (package.json
# scripts, .eslintrc, pre-commit hooks). Use sh -c rather than eval so
# the subshell can't mutate caller-process state. The forthcoming PR-2
# JSON Schema will document the trust boundary explicitly.
TYPECHECK=$(cat flow.config.json 2>/dev/null | jq -r '.typecheckCmd // empty')
if [ -n "$TYPECHECK" ]; then
  sh -c "$TYPECHECK"
else
  echo "⚠️ flow.config.json.typecheckCmd not set; skipping typecheck re-run. Set this slot to enable typecheck on /flow:ship."
fi
```

## 4. Synthesize session feedback (two layers)

### 4a. User feedback → `flow.config.json.feedbackPath` (default `dev-docs/feedback.md`; consumers typically `core-docs/feedback.md`)

Review this conversation (and any prior session since the last PR on this branch) for:
- User corrections — places you got it wrong and the user fixed your direction.
- User preferences — stylistic or process calls the user made.
- User direction — strategic priorities or scope changes.
- Challenges solved — a non-obvious problem and how it was resolved.

Add new entries to the configured feedback doc following the FB-XXXX format. Increment from the last ID. Skip anything already captured. The bar: would a future session benefit from this rule? If yes, write it down.

### 4b. Agent self-feedback → failure-pattern memory

Memory entries (`~/.claude/projects/<canonical>/memory/feedback_*.md`) capture failure patterns the agent should watch for across sessions. **All 5 guardrails from `${CLAUDE_PLUGIN_ROOT}/docs/workflow.md` § "Continuous improvement" apply** — most importantly the source-diversity bar (write only when 2-of-3 evidence sources support the entry: recurrence in time / two reviewers / one review + user correction).

Run the sub-steps in order:

**4b.i — Corpus health check.**

```sh
node ${CLAUDE_PLUGIN_ROOT}/tools/memory/check.mjs
```

If output shows AT/OVER CAP, curate (archive or merge an existing entry) before writing a new one. The cap is `flow.config.json.memoryHardCap` (default 30).

**4b.ii — Apply the source-diversity bar to this PR's findings.**

For each finding from /simplify, /flow:staff-review (4 lenses), /flow:security-review, /flow:accessibility-review, ask: *would this same pattern recur on a similar surface, and is it not already mechanically checkable?* If yes AND 2-of-3 evidence sources support it, the finding earns a memory entry. Single-source findings do NOT earn an entry — that's the bar protecting against memory-amplification slop.

**4b.iii — Resolve contradictions with the feedback doc.**

If a candidate memory entry contradicts an FB-XXXX in `flow.config.json.feedbackPath`, user feedback wins automatically. Revise the candidate or skip.

**4b.iv — Write the entry.**

Path: `~/.claude/projects/<canonical-project>/memory/feedback_<short_snake_name>.md` (the memory tool resolves the canonical path; see its top-of-file comment). Format per `${CLAUDE_PLUGIN_ROOT}/rules/documentation.md` § "memory entry format" — required fields: Source, First seen, Source-diversity evidence, Pattern, Why I missed it, How to catch it next time, Promotion target, Fire log.

**4b.v — Update fire logs on existing entries.**

If a finding this PR matches an EXISTING memory entry's pattern, append `YYYY-MM-DD` to that entry's `Fire log`. When fire-log reaches 2+ entries, the pattern is a promotion candidate — file a roadmap entry naming the preflight rule that would catch it deterministically. Promotion is user-gated (preflight rules are permanent; a bad rule generates false positives forever).

**4b.vi — Trigger fresh-context audit if due.**

```sh
node ${CLAUDE_PLUGIN_ROOT}/tools/memory/check.mjs --audit-due
```

If exit 1 (audit due), spawn an Agent (subagent_type: Explore) with the memory directory as input. The audit reads ONLY the memory entries (no PR diff, no other context) and answers: which entries' fire logs show no activity in 60+ days (archive candidates)? which entries contradict each other (resolve)? which entries look like over-fitting on a single past incident (revise or delete)? This is the cure for memory ossification.

## 5. Update project docs

For each meaningful change in the diff, update via the config slots (all default to `dev-docs/<name>.md`; consumer projects typically set them to `core-docs/<name>.md`):

- **`flow.config.json.historyPath`** (default `dev-docs/history.md`) — add an entry (newest first) with: title, date, branch, what was done, why, design decisions, technical decisions, tradeoffs, lessons learned. Flag with `SAFETY` if it touches persistence, error handling, or fallback behavior.
- **`flow.config.json.planPath`** (default `dev-docs/plan.md`) — move shipped items from "Current Focus" → "Recently Completed". Update "Current Focus" to reflect what's next. Clear stale "Handoff Notes" if the work is done.
- **`flow.config.json.roadmapPath`** (default `dev-docs/roadmap.md`) — log any deferred follow-ups from review under the relevant horizon. Update workstream status if a workstream completed.
- **`flow.config.json.specPath`** (default `dev-docs/spec.md`) — if features changed status (planned → shipped) or new features were added, update the features table. If the product surface area changed materially, update the relevant section.

Do **not** add entries that already exist. Skip silently.

## 6. Commit

Stage code changes + doc updates together (or in two commits if cleaner). Never stage `.env`, secrets, or credentials.

Commit message style: explain **why**, not what. Short subject line, blank line, body if needed. End with:
```
Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```

If safety-critical code changed, include `SAFETY` in the commit subject.

## 7. Push and PR

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

## 8. Hand off

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
| `flow.config.json.defaultBranch` | falls back to `git symbolic-ref` then literal `main` | Step 1 (NOTHING-TO-SHIP check), Step 7 (PR base) |
| `flow.config.json.typecheckCmd` | unset → loud warning, never silent | Step 3 (post-fix re-check) |
| `flow.config.json.historyPath` | `dev-docs/history.md` | Step 5 |
| `flow.config.json.planPath` | `dev-docs/plan.md` | Steps 3, 5 |
| `flow.config.json.roadmapPath` | `dev-docs/roadmap.md` | Steps 3, 5 |
| `flow.config.json.specPath` | `dev-docs/spec.md` | Step 5 |
| `flow.config.json.feedbackPath` | `dev-docs/feedback.md` | Step 4a |

Consumer projects typically override the `*Path` slots to `core-docs/<name>.md` since they keep their own project docs under `core-docs/`. Flow's own dev-tracking lives under `dev-docs/` to leave `core-docs/` free as a name that consumer-template-shipped scaffolding uses.
