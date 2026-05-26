---
name: ship-spike
description: >
  Lightweight terminal pipeline for spike-mode PRs (exploratory work that
  answers a question rather than shipping a feature). Skips /simplify and
  /flow:staff-review (they ran for the full /flow:ship; spikes don't need
  them since the code is disposable). Writes the history.md entry — which
  IS the deliverable for a spike — commits, pushes, and opens a PR labeled
  `spike`. Never merges. Only invoke when the plan declared `mode: spike`.
  Trigger phrases: "ship the spike", "/flow:ship-spike", "wrap up the spike".
disable-model-invocation: true
allowed-tools: Read, Edit, Write, Glob, Grep, Bash, Agent
---

You are running the flow ship-spike pipeline for a spike-mode PR. **Never merge.**

## Project context (resolved at invocation)

- Project config: !`cat flow.config.json 2>/dev/null || echo "(no flow.config.json — using built-in defaults)"`
- Default branch (PR base): !`git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@' || cat flow.config.json 2>/dev/null | jq -r '.defaultBranch // "main"' 2>/dev/null || echo "main"`
- Current branch: !`git branch --show-current`
- History doc path: !`cat flow.config.json 2>/dev/null | jq -r '.historyPath // "dev-docs/history.md"' 2>/dev/null || echo "dev-docs/history.md"`
- Plan doc path: !`cat flow.config.json 2>/dev/null | jq -r '.planPath // "dev-docs/plan.md"' 2>/dev/null || echo "dev-docs/plan.md"`

## Pre-condition

The plan in the project's plan doc for the current work item must declare `**Mode:** spike`. If it doesn't, stop and tell the user — they want `/flow:ship`, not `/flow:ship-spike`. A spike-mode plan has:
- A research question.
- A disposability statement (deleted / kept behind flag / gates next PR).

If neither field exists, this is a feature plan and the wrong skill.

## 1. Pre-flight

### 1.5. External CLI dependency check (BLOCKING)

Fail-fast on missing `gh` CLI per FB-0009. Same shape as `/flow:ship` Step 1.5.

```sh
MISSING=()
command -v gh >/dev/null 2>&1 || MISSING+=("gh")
command -v jq >/dev/null 2>&1 || MISSING+=("jq")
if [ ${#MISSING[@]} -gt 0 ]; then
  echo "⚠️ BLOCKER: /flow:ship-spike requires ${MISSING[*]} (missing on PATH)." >&2
  echo "   Install:" >&2
  echo "     macOS:         brew install ${MISSING[*]}" >&2
  echo "     Debian/Ubuntu: apt install ${MISSING[*]}" >&2
  echo "     Other:         https://cli.github.com (gh), https://jqlang.org (jq)" >&2
  echo "   After install, run: gh auth login   (gh only — jq needs no auth)" >&2
  exit 1
fi
```

Identical shape to `/flow:ship` Step 1.5 — the consistency itself is the value per FB-0009.

### 1a. Stale-base check (BLOCKING)

Same gate as `/flow:ship` Step 1a — spike branches diff vs the default branch too, and a stale spike base produces phantom-deletion noise that obscures the actual research-question answer. See `dev-docs/feedback.md` FB-0008. See `/flow:ship` Step 1a for the rationale on the `[ -z ]` guards (the `||` pipe form silently fails on empty stdout).

```sh
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

### 1b. Confirm there is something to ship

In parallel (each bullet is its own Bash invocation — `DEFAULT_BRANCH` from 1a does NOT persist):
- `git status --short`
- `` git log --oneline origin/$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@' || jq -r '.defaultBranch // "main"' flow.config.json 2>/dev/null || echo main)..HEAD ``
- `gh pr list --head $(git branch --show-current) --json number,url 2>/dev/null`

Classify (same shape as `/flow:ship`):
- **PR-OPEN** — at least one PR returned. Note the number for body updates; we'll push new commits to the existing spike PR rather than open a new one.
- **LOCAL-ONLY** — commits ahead and/or dirty tree, no PR yet. The normal spike-ship path.
- **NOTHING-TO-SHIP** — clean tree at default branch. Stop and tell the user.

If on the default branch: create a spike branch first. The conventional prefix is `spike/`; if `flow.config.json.branchPrefix` is set, prepend it (e.g., `claude/` + `spike/` → `claude/spike/<short-name>`).

```sh
PREFIX=$(cat flow.config.json 2>/dev/null | jq -r '.branchPrefix // empty' 2>/dev/null)
git checkout -b "${PREFIX}spike/<short-name>"
```

## 2. Skip the heavy reviews

`/simplify` and `/flow:staff-review` do not run for spikes. Reviewing throwaway code for craft is theater. **Do** ensure preflight is green — that's still required:

```sh
# Project-specific preflight runner (project ships its own; flow doesn't bundle one)
[ -f tools/preflight/check.mjs ] && node tools/preflight/check.mjs

# Configured typecheck via flow.config.json.typecheckCmd
TYPECHECK=$(cat flow.config.json 2>/dev/null | jq -r '.typecheckCmd // empty')
if [ -n "$TYPECHECK" ]; then
  sh -c "$TYPECHECK"
else
  echo "⚠️ flow.config.json.typecheckCmd not set; skipping typecheck. Set this slot to enable typecheck on /flow:ship-spike."
fi
```

If preflight is red on spike code, that's a real bug in something the spike depends on (or the spike is broken in a way that invalidates the answer). Either fix it or note explicitly in the history entry that the answer is conditional on the broken state.

## 3. Write the history entry — the entry IS the deliverable

The point of a spike is the learning, not the code. The history doc entry (path from `flow.config.json.historyPath`; default `dev-docs/history.md`) is the canonical artifact. Add an entry (newest first) with:

```markdown
### Spike: <one-line title>
**Date:** YYYY-MM-DD
**Branch:** <name>
**Mode:** spike

**Research question:** <the specific question the spike answers>

**What was built:** <smallest thing that answered the question; one paragraph max>

**What we learned:** <the answer, with any caveats>

**Recommendation:** proceed | pivot | abandon
- If proceed: what the next (real) PR looks like, in 1–3 sentences.
- If pivot: what the better question is, and what to try next.
- If abandon: why this direction is closed; what would re-open it.

**Disposability:** <code is being deleted / kept behind flag / gates next PR>
```

A spike's history entry is shorter than a feature's. Don't pad it with technical decisions or tradeoffs unless the spike itself surfaced them.

## 4. Capture agent self-feedback (if applicable)

Spikes often surface failure-pattern memory entries because the agent is operating with less guard-rail. **All 5 guardrails from `/flow:ship` step 4b apply equally to spike mode** — don't relax them just because the surrounding pipeline is lighter. See `${CLAUDE_PLUGIN_ROOT}/skills/ship/SKILL.md` § 4b for the full text (corpus health check, source-diversity bar, contradiction-with-feedback check, write format, fire-log update, audit-if-due).

Run the same sub-steps in order:
- 4b.i — `node ${CLAUDE_PLUGIN_ROOT}/tools/memory/check.mjs` (corpus health)
- 4b.ii — Apply the source-diversity bar (recurrence-likely + not mechanically checkable + 2-of-3 evidence)
- 4b.iii — Resolve contradictions with the project's feedback doc (path from `flow.config.json.feedbackPath`; user wins)
- 4b.iv — Write the entry if guardrails pass
- 4b.v — Update fire log on existing entries; flag promotion candidates to the project's roadmap
- 4b.vi — `node ${CLAUDE_PLUGIN_ROOT}/tools/memory/check.mjs --audit-due`; spawn audit Explore agent if exit 1

The bar is identical. Spike mode is **lighter on review** (skips /simplify + /flow:staff-review) but **not lighter on learning capture** — if anything, spikes are higher-yield for memory entries because the exploration surfaces failure modes feature work doesn't.

Do NOT synthesize user feedback to the feedback doc for spikes — the conversation density is different (less direction, more exploration). Spike-derived user preferences should wait until the follow-up feature PR confirms them.

## 5. Update the project's plan doc

Move the spike from "Active Work Items" to "Recently Completed" with a one-line summary including the recommendation (proceed / pivot / abandon).

If the recommendation is "proceed," **add the next-PR scope to "Active Work Items" or the project's roadmap doc** so the learning doesn't decay between sessions.

## 6. Commit

Stage code + doc updates. Commit with subject prefixed `spike:`:

```
spike: <one-line answer to the research question>

<optional body>

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```

## 7. Push and open PR

Push with `-u` if needed. PR base from the resolved default branch:

```sh
BASE=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@' || cat flow.config.json 2>/dev/null | jq -r '.defaultBranch // "main"' 2>/dev/null || echo "main")
gh pr create --base "$BASE" --label spike --title "spike: <answer>" --body "$(cat <<'EOF'
## Research question
<the question>

## Answer
<short answer>

## Recommendation
proceed | pivot | abandon — <one-line reasoning>

## Disposability
<what happens to the code: deleted, flagged, gates next PR>

## Full writeup
See the history doc entry "Spike: <title>".

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

The PR title MUST start with `spike:` and the PR MUST have the `spike` label. Both are spike-mode-abuse guards: a feature accidentally shipped through `/flow:ship-spike` should be visually obvious and easy to reject.

## 8. Hand off

Output the PR URL and the recommendation (proceed / pivot / abandon). The user merges or closes.

**Do not merge. Do not approve.** The user handles merging.

## Gotchas

- **Spike PRs that grew into features.** If during execution you realize the work is no longer answering a question but building a feature, **stop and rewrite the plan as `mode: feature`**. Do not try to ship a feature through this skill — the heavy reviews exist for a reason. The user can redirect.
- **Spike code that's being kept** (behind a flag, gating next PR): the disposability statement matters. "Kept behind a flag" means the next PR has to either polish it or remove it — file a roadmap entry naming which.
- **Don't write to the feedback doc.** That's `/flow:ship` (feature mode). Spikes are too sparse on user direction to distill reliably.

## Config slots used

| Slot | Default | Used in |
|---|---|---|
| `flow.config.json.defaultBranch` | `git symbolic-ref` → `main` | Step 1 (pre-flight), Step 7 (PR base) |
| `flow.config.json.typecheckCmd` | unset → loud warning | Step 2 (preflight) |
| `flow.config.json.historyPath` | `dev-docs/history.md` | Step 3 (spike entry — THE deliverable) |
| `flow.config.json.planPath` | `dev-docs/plan.md` | Step 5 (move to Recently Completed) |
| `flow.config.json.feedbackPath` | `dev-docs/feedback.md` | Step 4 (contradiction check; not written to) |
| `flow.config.json.roadmapPath` | `dev-docs/roadmap.md` | Step 5 (next-PR scope if proceed) |
