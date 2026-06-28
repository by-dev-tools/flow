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
disable-model-invocation: false
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
# POSIX-portable (NOT bash array — breaks on dash; see /flow:ship Step 1.5).
MISSING=""
command -v gh >/dev/null 2>&1 || MISSING="$MISSING gh"
command -v jq >/dev/null 2>&1 || MISSING="$MISSING jq"
if [ -n "$MISSING" ]; then
  MISSING_TRIMMED=$(echo "$MISSING" | sed 's/^ //')
  echo "⚠️ BLOCKER: /flow:ship-spike requires $MISSING_TRIMMED (missing on PATH)." >&2
  echo "   Install:" >&2
  echo "     macOS:         brew install$MISSING" >&2
  echo "     Debian/Ubuntu: apt install$MISSING" >&2
  echo "     Other:         https://cli.github.com (gh), https://jqlang.org (jq)" >&2
  case " $MISSING_TRIMMED " in *" gh "*) echo "   After install, run: gh auth login" >&2 ;; esac
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

### 1c. Mechanical preflight (bounded retry — N ≤ 3)

Same contract as `/flow:ship` Step 1c — bounded-retry preflight that loops only on externally-verifiable exit codes (N=3 cap, oscillation detection via diff-hash, docs-only early-exit). **Reviewer outputs in Step 2 stay deliberately single-pass; the loop only fires on the preflight exit code, never on LLM-judgment outputs.** The consistency itself is the value: spike-mode work goes through the same mechanical gate as feature-mode work, even though spike code is disposable. A spike whose preflight is red is answering its research question conditionally on a broken state; flag that explicitly in the history entry rather than burying it.

```sh
# Resolve preflightCmd. Unset/whitespace-only → loud warning, proceed without retry (never silent).
PREFLIGHT_CMD=$(jq -r '.preflightCmd // empty' flow.config.json 2>/dev/null)
# Treat whitespace-only as unset (jq returns the literal whitespace string for "  " slot values).
if [ -z "$(printf '%s' "$PREFLIGHT_CMD" | tr -d '[:space:]')" ]; then
  echo "⚠️ flow.config.json.preflightCmd not set; skipping mechanical preflight. Set this slot to enable bounded-retry typecheck/lint/test on /flow:ship-spike."
  # Continue to Step 2 without running the loop.
else
  # Docs-only early-exit: reuse sourceFilePatterns (PR D lineage).
  DEFAULT_BRANCH=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@')
  [ -z "$DEFAULT_BRANCH" ] && DEFAULT_BRANCH=$(jq -r '.defaultBranch // "main"' flow.config.json 2>/dev/null)
  [ -z "$DEFAULT_BRANCH" ] && DEFAULT_BRANCH=main
  SOURCE_PATTERN=$(jq -r '.sourceFilePatterns // empty' flow.config.json 2>/dev/null)
  [ -z "$SOURCE_PATTERN" ] && SOURCE_PATTERN='\.(ts|tsx|js|jsx|mjs|cjs|py|rs|swift|go|rb|java|kt|sh|bash|tf|tfvars|sql|proto|graphql|gql)$|\.(json|ya?ml|toml)$|(^|/)(Dockerfile|Makefile)(\.|$)'

  # Validate sourceFilePatterns regex BEFORE using it (FB-0010 silent-skip prevention).
  echo "" | grep -qE "$SOURCE_PATTERN" 2>/dev/null
  GREP_RC=$?
  if [ "$GREP_RC" -gt 1 ]; then
    echo "⚠️ [preflight] flow.config.json.sourceFilePatterns is invalid as an extended regex (grep exit $GREP_RC); falling back to default." >&2
    SOURCE_PATTERN='\.(ts|tsx|js|jsx|mjs|cjs|py|rs|swift|go|rb|java|kt|sh|bash|tf|tfvars|sql|proto|graphql|gql)$|\.(json|ya?ml|toml)$|(^|/)(Dockerfile|Makefile)(\.|$)'
  fi

  # Three checks (PR D pattern): committed + uncommitted + untracked.
  SOURCE_FILES_COMMITTED=$(git diff "origin/${DEFAULT_BRANCH}..HEAD" --name-only 2>/dev/null | grep -E "$SOURCE_PATTERN" || true)
  SOURCE_FILES_MODIFIED=$(git diff HEAD --name-only 2>/dev/null | grep -E "$SOURCE_PATTERN" || true)
  SOURCE_FILES_UNTRACKED=$(git ls-files --others --exclude-standard 2>/dev/null | grep -E "$SOURCE_PATTERN" || true)
  if [ -z "$SOURCE_FILES_COMMITTED" ] && [ -z "$SOURCE_FILES_MODIFIED" ] && [ -z "$SOURCE_FILES_UNTRACKED" ]; then
    echo "[preflight] no source files in diff (committed+uncommitted+untracked); skipping mechanical preflight (docs-only spike)."
    # Continue to Step 2 without running the loop.
  fi
  # If PREFLIGHT_CMD is set AND source files exist anywhere, follow the retry contract below.
fi
```

**Retry contract** (followed by the agent executing this skill — iteration discipline is in the prompt, not in shell):

For each attempt `N` in 1..3:

1. Run `sh -c "$PREFLIGHT_CMD"`. Capture exit code and stderr.
2. If **exit 0**: log `[preflight] attempt N of 3: PASSED.` → proceed to Step 2.
3. If **exit 127** (command not found): abort with `BLOCKER: preflightCmd resolved to a command not found on PATH ($PREFLIGHT_CMD). Fix the slot or install the script. Halting before Step 2.` → exit 1. Do NOT count this against the retry budget.
4. If **any other non-zero exit**: log `[preflight] attempt N of 3: FAILED (exit code <N>).` Capture the diff hash via `git diff HEAD | sha256sum | cut -d' ' -f1`. Record for oscillation detection. Proceed to step 5.
5. If `N == 3`: abort with `BLOCKER: preflight failed 3 attempts without convergence. Last error: <stderr>. All attempted fixes preserved in tree; inspect with 'git diff origin/${DEFAULT_BRANCH}..HEAD'. Halting before Step 2.` → exit 1.
6. **Fix the failure.** Read stderr; identify the specific failure. Make the **minimal** fix:
   - Touch only files in the failure's blast radius. Do NOT refactor adjacent code.
   - Do NOT modify or disable tests unless the failure is a genuine test bug — and if so, name the bug explicitly in the attempt log. Disabling a test to make preflight green is reward hacking; for spike mode, this is doubly important because the spike's history entry IS the deliverable — a silently-disabled test corrupts the answer.
   - Do NOT add `// @ts-ignore`, `# noqa`, `# type: ignore`, `eslint-disable-next-line`, `// biome-ignore`, `@SuppressWarnings`, `#[allow(...)]`, or equivalent suppressors.
7. Compute the new diff hash. Compare against ALL prior hashes from this Step 1c run. If it matches ANY prior hash: abort with `BLOCKER: oscillation detected (attempt N+1 produced the same diff as attempt M). The fix is reverting a prior fix — a different approach is required. Last error: <stderr>. Halting before Step 2.` → exit 1.
8. Increment `N`. Return to step 1.

If Step 1c fails for a spike: the spike answered its research question conditional on a broken state. Either fix the broken state OR document the conditional explicitly in the history entry at Step 3 (`What we learned: <answer> — caveat: this assumes <broken thing> is resolved upstream`). Do NOT bypass Step 1c by deleting tests; that corrupts the spike's value.

## 2. Skip the heavy reviews; run verify-build in spike mode

`/simplify` and `/flow:staff-review` do not run for spikes. Reviewing throwaway code for craft is theater. Step 1c above already enforces the bounded-retry mechanical preflight; this step is a one-shot typecheck confirmation that mirrors `/flow:ship` Step 3's role (re-check after any review-applied fixes, even though spike skips reviews):

```sh
# Configured typecheck via flow.config.json.typecheckCmd (one-shot; Step 1c already
# ran the full preflight loop with retry). If preflightCmd already includes typecheck,
# this is redundant but safe. If they're configured to overlap, the user owns that
# choice — see schema description's precedence note.
TYPECHECK=$(cat flow.config.json 2>/dev/null | jq -r '.typecheckCmd // empty')
if [ -n "$TYPECHECK" ]; then
  sh -c "$TYPECHECK"
else
  echo "⚠️ flow.config.json.typecheckCmd not set; skipping typecheck. Set this slot to enable typecheck on /flow:ship-spike."
fi
```

Step 1c (above) is the load-bearing preflight gate for spikes; a spike that survives Step 1c's bounded retry and this Step 2 one-shot typecheck has passed mechanical checks. If a spike's mechanical checks would fail in a way that invalidates the research answer, document that conditionally in Step 3's history entry rather than disabling the checks.

**Then invoke `/flow:verify-build` in spike mode** for a minimal behavioral check (does the spike's experimental code actually launch + execute its headline action without log errors). This is the same 3-check spike rubric documented at `${CLAUDE_PLUGIN_ROOT}/skills/verify-build/lib/spike-rubric.md`. Invoke and tell the skill that you're calling from `/flow:ship-spike` so it treats Trigger 1 (caller signal) as satisfied:

```
Skill("flow:verify-build")
# Contextual hint to verify-build: this invocation is from /flow:ship-spike;
# enter spike mode per Step 2 Trigger 1. (The skill also auto-detects spike
# mode via Triggers 2 and 3 if no plan or no Spec-walk block exists.)
```

Skip behavior matches `/flow:verify-build` standalone: skip if `flow.config.json.verifyEnabled=false` or `platform=library|none`. Spike mode applies a lower verification bar (3 fixed checks vs N plan-derived) but the same Unknown-blocking gate — Unknown ⇒ exit 1 → spike ship halts. The lower bar is deliberate: spike code is throwaway, but "did this experiment actually launch and do the thing" is a load-bearing check the typecheck alone cannot answer.

If verify-build runs in spike mode and the gate blocks, the user adjudicates: either fix the headline-action behavior + re-run, OR document the failure in Step 3's history entry as the spike's actual finding ("the experiment confirmed that approach X does not work because Y") and proceed past the gate via re-invocation with `--skip-verify` (documented but not implemented in v1). The history entry IS the deliverable for a spike — a failed verify-build is a valid spike result if captured honestly.

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

**PR-OPEN (re-ship into an existing spike PR):** push the new commits to the existing PR. If you update its body and `gh pr edit`/`gh pr ready` fails with a `GraphQL: Projects (classic) … projectCards` error (classic-projects repos on affected `gh` versions), use the **canonical `gh`-resilience fallback** — see `/flow:ship` Step 7 § "gh resilience" (REST `gh api -X PATCH …/pulls/N -F body=@file` for the body; `markPullRequestReadyForReview` / `convertPullRequestToDraft` mutations for draft state). Don't route around `gh pr` pre-emptively — only on the explicit `projectCards` error.

**LOCAL-ONLY (new spike PR):** push with `-u` if needed. PR base from the resolved default branch:

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

## Flow run
Spike mode runs a trimmed loop. Each step — ran or skipped — with any signal it
produced; `—` when routine. Resolve every `<...>` placeholder before publishing.
(Full per-step guidance: `/flow:ship` §7.)

| Step | Status | Notable |
|---|---|---|
| Clarify | ✓ | — |
| Plan (research question) | ✓ | <approach / —> |
| Execute | ✓ | <smallest thing that answered the question / —> |
| Preflight | ✓ | green / <what ran> |
| /simplify | skipped (spike) | — |
| /flow:staff-review | skipped (spike) | — |
| /flow:verify-build | <✓ / skipped (reason)> | <3-check spike-rubric result / —> |

## Full writeup
See the history doc entry "Spike: <title>".

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

`/simplify` and `/flow:staff-review` are pre-marked `skipped (spike)` — spike mode
always skips them (workflow.md § Spike mode). Fill `/flow:verify-build` from the
Step 2 spike-mode invocation: `✓` with the 3-check rubric result if it ran, or
`skipped (verifyEnabled:false)` / `skipped (platform library|none)` if it didn't.
**Notable** is genuine signal only — don't manufacture notes for a spike.

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
| `flow.config.json.defaultBranch` | `git symbolic-ref` → `main` | Step 1 (pre-flight), Step 1c (docs-only diff base), Step 7 (PR base) |
| `flow.config.json.preflightCmd` | unset → loud warning | Step 1c (bounded-retry mechanical preflight, N≤3) |
| `flow.config.json.sourceFilePatterns` | covers common source/config extensions | Step 1c (docs-only early-exit) |
| `flow.config.json.typecheckCmd` | unset → loud warning | Step 2 (post-1c one-shot typecheck) |
| `flow.config.json.historyPath` | `dev-docs/history.md` | Step 3 (spike entry — THE deliverable) |
| `flow.config.json.planPath` | `dev-docs/plan.md` | Step 5 (move to Recently Completed) |
| `flow.config.json.feedbackPath` | `dev-docs/feedback.md` | Step 4 (contradiction check; not written to) |
| `flow.config.json.roadmapPath` | `dev-docs/roadmap.md` | Step 5 (next-PR scope if proceed) |
