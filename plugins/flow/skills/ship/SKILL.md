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

### 1c. Mechanical preflight (bounded retry — N ≤ 3)

Run the project's mechanical preflight (typecheck + lint + fast tests) BEFORE invoking reviewers. On non-zero exit, fix and retry — up to 3 total invocations, with oscillation detection via diff-hash. **Loop only on this externally-verifiable exit signal.** Reviewer outputs at Step 2 are deliberately single-pass; iterating LLM-judgment outputs is reward-hackable. Per Anthropic's evaluator-optimizer guidance (Building Effective Agents): agent loops require mechanical stopping conditions and explicit success criteria; preflight exit code is the only loop-exit signal flow trusts.

```sh
# Resolve preflightCmd. Unset/whitespace-only → loud warning, proceed without retry (never silent).
PREFLIGHT_CMD=$(jq -r '.preflightCmd // empty' flow.config.json 2>/dev/null)
# Treat whitespace-only as unset (jq returns the literal whitespace string for "  " slot values;
# `[ -z "$VAR" ]` doesn't catch that — would `sh -c "   "` silently pass and skip the loop).
if [ -z "$(printf '%s' "$PREFLIGHT_CMD" | tr -d '[:space:]')" ]; then
  echo "⚠️ flow.config.json.preflightCmd not set; skipping mechanical preflight. Set this slot to enable bounded-retry typecheck/lint/test on /flow:ship."
  # Continue to Step 2 without running the loop.
else
  # Docs-only early-exit: reuse sourceFilePatterns (PR D lineage). DEFAULT_BRANCH
  # is NOT in scope from earlier Bash invocations — re-resolve via the 3-tier chain.
  DEFAULT_BRANCH=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@')
  [ -z "$DEFAULT_BRANCH" ] && DEFAULT_BRANCH=$(jq -r '.defaultBranch // "main"' flow.config.json 2>/dev/null)
  [ -z "$DEFAULT_BRANCH" ] && DEFAULT_BRANCH=main
  SOURCE_PATTERN=$(jq -r '.sourceFilePatterns // empty' flow.config.json 2>/dev/null)
  [ -z "$SOURCE_PATTERN" ] && SOURCE_PATTERN='\.(ts|tsx|js|jsx|mjs|cjs|py|rs|swift|go|rb|java|kt|sh|bash|tf|tfvars|sql|proto|graphql|gql)$|\.(json|ya?ml|toml)$|(^|/)(Dockerfile|Makefile)(\.|$)'

  # Validate sourceFilePatterns BEFORE using it — invalid regex would cause grep to exit 2,
  # `|| true` would swallow it, and SOURCE_FILES would be empty → docs-only branch taken
  # silently. Exactly the FB-0010 silent-skip class. Capture grep's raw exit code: 0=match,
  # 1=no match (both fine), 2=regex error (fall back loud).
  echo "" | grep -qE "$SOURCE_PATTERN" 2>/dev/null
  GREP_RC=$?
  if [ "$GREP_RC" -gt 1 ]; then
    echo "⚠️ [preflight] flow.config.json.sourceFilePatterns is invalid as an extended regex (grep exit $GREP_RC); falling back to default." >&2
    SOURCE_PATTERN='\.(ts|tsx|js|jsx|mjs|cjs|py|rs|swift|go|rb|java|kt|sh|bash|tf|tfvars|sql|proto|graphql|gql)$|\.(json|ya?ml|toml)$|(^|/)(Dockerfile|Makefile)(\.|$)'
  fi

  # Three checks (PR D pattern): committed diff, uncommitted modifications, untracked files.
  # The common 'iterate locally then /flow:ship' loop hits uncommitted/untracked — must catch
  # all three or the docs-only branch fires on a source-touching PR.
  SOURCE_FILES_COMMITTED=$(git diff "origin/${DEFAULT_BRANCH}..HEAD" --name-only 2>/dev/null | grep -E "$SOURCE_PATTERN" || true)
  SOURCE_FILES_MODIFIED=$(git diff HEAD --name-only 2>/dev/null | grep -E "$SOURCE_PATTERN" || true)
  SOURCE_FILES_UNTRACKED=$(git ls-files --others --exclude-standard 2>/dev/null | grep -E "$SOURCE_PATTERN" || true)
  if [ -z "$SOURCE_FILES_COMMITTED" ] && [ -z "$SOURCE_FILES_MODIFIED" ] && [ -z "$SOURCE_FILES_UNTRACKED" ]; then
    echo "[preflight] no source files in diff (committed+uncommitted+untracked); skipping mechanical preflight (docs-only PR)."
    # Continue to Step 2 without running the loop.
  fi
  # If PREFLIGHT_CMD is set AND source files exist anywhere, follow the retry contract below.
fi
```

**Retry contract** (followed by the agent executing this skill — the iteration discipline is in the prompt, not in shell):

For each attempt `N` in 1..3:

1. Run `sh -c "$PREFLIGHT_CMD"`. Capture exit code and stderr.
2. If **exit 0**: log `[preflight] attempt N of 3: PASSED.` → proceed to Step 2.
3. If **exit 127** (command not found): abort with `BLOCKER: preflightCmd resolved to a command not found on PATH ($PREFLIGHT_CMD). Fix the slot or install the script. Halting before Step 2.` → exit 1. Do NOT count this against the retry budget; a missing command isn't a fixable test failure.
4. If **any other non-zero exit**: log `[preflight] attempt N of 3: FAILED (exit code <N>).` Capture the diff hash via `git diff HEAD | sha256sum | cut -d' ' -f1`. Record it for oscillation detection. Proceed to step 5.
5. If `N == 3`: abort with `BLOCKER: preflight failed 3 attempts without convergence. Last error: <stderr>. All attempted fixes preserved in tree; inspect with 'git diff origin/${DEFAULT_BRANCH}..HEAD'. Halting before Step 2.` → exit 1.
6. **Fix the failure.** Read the stderr; identify the specific failure (test name, type error, lint rule, build error). Make the **minimal** fix:
   - Touch only files in the failure's blast radius. Do NOT refactor adjacent code.
   - Do NOT modify or disable tests unless the failure is a genuine test bug — and if so, name the bug explicitly in the attempt log. Disabling a test to make preflight green is reward hacking; surface it as a FOLLOW-UP, never silently merge it.
   - Do NOT add `// @ts-ignore`, `# noqa`, `# type: ignore`, `eslint-disable-next-line`, `// biome-ignore`, `@SuppressWarnings`, `#[allow(...)]`, or equivalent suppressors to silence the failure. Those are escape hatches; the human merge gate at Step 7 catches them but Step 1c should not produce them.
7. Compute the new diff hash. Compare against ALL prior hashes from this Step 1c run. If it matches ANY prior hash: abort with `BLOCKER: oscillation detected (attempt N+1 produced the same diff as attempt M). The fix is reverting a prior fix — a different approach is required. Last error: <stderr>. All attempted fixes preserved in tree. Halting before Step 2.` → exit 1.
8. Increment `N`. Return to step 1.

The contract reads top-to-bottom; the cap is 3 invocations of the preflight command total (1 initial + up to 2 retries). The oscillation check compares `git diff HEAD` hashes — pure A↔B↔A oscillation aborts before attempt 3 is wasted. Drift (A→B→C, each different but each broken) is caught by N=3 exhaustion.

If Step 1c passes (or is skipped via unset/docs-only), proceed to Step 2. The Step 3 `typecheckCmd` re-run is unaffected — it still fires after reviewer-applied BLOCKER fixes as a one-shot check.

## 2. Final-pass reviews

Sequentially invoke `/flow:security-review`, `/flow:accessibility-review`, and `/flow:verify-build` via the Skill tool. Each reviewer cold-reads the workspace diff vs the default branch (or runs the built artifact, for verify-build), applies BLOCKER + cheap NIT fixes in-tree, and returns FOLLOW-UP findings for step 3 routing.

```
Skill("flow:security-review")
Skill("flow:accessibility-review")
Skill("flow:verify-build")
```

Skip behavior:
- `/flow:security-review`: skip if the diff is doc-only or trivially safe (a copy tweak). The reviewer self-detects this and exits early with a clean message.
- `/flow:accessibility-review`: skip if `flow.config.json.uiSurface` is `false` (the reviewer self-detects this and exits early), or if the diff is non-UI (data layer, build config, doc-only).
- `/flow:verify-build`: skip if `flow.config.json.verifyEnabled` is `false` (project-wide opt-out), or if `flow.config.json.platform` resolves to `library` or `none` (no runnable target). The skill self-detects both and exits early with a clean `[verify-build] ...skipping.` message. Unlike security + a11y, verify-build does NOT auto-skip on doc-only diffs — the user may have shipped a behavioral change in a non-code file (e.g., a config-driven feature toggle); the run-and-observe loop is cheap enough to attempt and fall through to Unknown if there's nothing to observe.

The first two reviewers are tuned for the in-flow ship context; the bundled Claude Code `/security-review` is fine for out-of-band deep audits but `/flow:security-review` carries the config-slot doc-path resolution this pipeline needs. Verify-build is the runtime gate that catches the Potemkin-interface / hallucinated-success class no static reviewer catches; it wraps bundled `/verify` with plan-driven criteria + Unknown-blocking judgment.

After all three Skill calls return, emit one consolidated user-facing line so the user can see what actually ran vs skipped:

```
Final-pass reviews: security=[ran|skipped: <reason>], accessibility=[ran|skipped: <reason>], verify-build=[ran|skipped: <reason>].
```

Example: `Final-pass reviews: security=ran (3 NITs, 1 FOLLOW-UP), accessibility=skipped (uiSurface:false), verify-build=ran (overall_verdict:PASS, all criteria PASS).`

**Verify-build gate-blocking semantics:** If verify-build returns `exit_code: 1` (FAIL or Unknown verdict per FB-0011), the ship pipeline STOPS at this step. The agent should not proceed to Step 3+ until either the failing criteria are addressed (re-run verify-build) or the user explicitly overrides the gate by re-invoking `/flow:ship` with `--skip-verify` (documented in Step 1 pre-flight; not implemented in v1 but reserved). Single-pass per FB-0012 — no retry loop on verify-build's judge output.

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

**Read verify-build findings buffer (if verify-build ran at Step 2).** When Step 2's `Skill("flow:verify-build")` invocation completed (ran, not skipped), read the structured findings at the path resolved from `flow.config.json.verifyFindingsPath` (default `/tmp/flow-verify-findings.json`). The buffer's JSON shape is documented at `${CLAUDE_PLUGIN_ROOT}/skills/verify-build/lib/findings-schema.json` with a canonical example at `findings-example.json`.

For each criterion in `findings.criteria[]` with `aggregated_verdict ∈ {FAIL, Unknown}`:

- Treat it as a **candidate** FB-XXXX entry, not a guaranteed write. The per-dimension `evidence` quotes form the candidate's "What was said" field; the criterion text + per-dimension `notes` form the synthesized rule.
- Apply the source-diversity bar from `${CLAUDE_PLUGIN_ROOT}/docs/workflow.md` § "Continuous improvement": verify-build findings count as ONE review source. A candidate becomes a real FB entry only when paired with a second source (recurrence in time, a second reviewer's finding, or a user correction in this session).
- For Unknown-verdict criteria specifically: the candidate's synthesized rule should name what the verify pass could not observe (per the `notes` field) and suggest a verification mechanism for next time (e.g., "add explicit test for empty-required-field path" or "ensure spike rubric covers headline action").

Single-source verify-build findings without pairing source do NOT earn an FB entry — that's the bar protecting against memory-amplification slop (FB-0010 sub-class).

If verify-build was skipped at Step 2 (`verifyEnabled=false`, `platform=library|none`, or doc-only diff per the skill's self-detection), no buffer read; skip this paragraph. If verify-build ran but the buffer is absent or unreadable, emit a `⚠️ verify-build ran but findings buffer at <path> is missing/unreadable; skipping FB-XXXX synthesis from verify-build` warning and continue — don't block ship on a missing diagnostic artifact (the gate already fired at Step 2).

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
| `flow.config.json.defaultBranch` | falls back to `git symbolic-ref` then literal `main` | Step 1 (NOTHING-TO-SHIP check), Step 1c (docs-only diff base), Step 7 (PR base) |
| `flow.config.json.preflightCmd` | unset → loud warning, never silent | Step 1c (bounded-retry mechanical preflight, N≤3) |
| `flow.config.json.sourceFilePatterns` | covers common source/config extensions | Step 1c (docs-only early-exit) |
| `flow.config.json.typecheckCmd` | unset → loud warning, never silent | Step 3 (post-reviewer-fix one-shot re-check) |
| `flow.config.json.historyPath` | `dev-docs/history.md` | Step 5 |
| `flow.config.json.planPath` | `dev-docs/plan.md` | Steps 3, 5 |
| `flow.config.json.roadmapPath` | `dev-docs/roadmap.md` | Steps 3, 5 |
| `flow.config.json.specPath` | `dev-docs/spec.md` | Step 5 |
| `flow.config.json.feedbackPath` | `dev-docs/feedback.md` | Step 4a |

Consumer projects typically override the `*Path` slots to `core-docs/<name>.md` since they keep their own project docs under `core-docs/`. Flow's own dev-tracking lives under `dev-docs/` to leave `core-docs/` free as a name that consumer-template-shipped scaffolding uses.
