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
  AUTO-INVOCATION (autonomous-loop trigger): you MAY invoke this yourself at
  the end of the loop ONLY when the ship-readiness predicate holds — every
  spec-walk checkbox in the approved plan is checked; /simplify and
  /flow:staff-review left no open BLOCKER; no load-bearing assumption is
  unresolved at MEDIUM or LOW confidence; and a behavioral gate exists and is
  green (i.e. /flow:verify-build would return overall_verdict PASS — NOT merely
  "didn't fail"). If ANY of FB-0011's escalation triggers hold — unclear path,
  significant risk, competing options of comparable merit, or a one-way-door
  decision — do NOT auto-invoke: present findings and wait (workflow.md Step 8).
  NEVER auto-invoke when verify-build is skipped (platform library/none, or a
  doc-only diff) — there is no behavioral gate, so those require an explicit
  "ship it" from the user. The plan and merge gates are untouched: this never
  starts before an approved plan and never merges.
disable-model-invocation: false
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

Sequentially invoke `/flow:security-review`, `/flow:accessibility-review`, `/flow:verify-build`, and `/flow:audit-coverage` via the Skill tool. Each reviewer cold-reads the workspace diff vs the default branch (or runs the built artifact, for verify-build), and returns findings for routing.

**Findings resolve into exactly one of three outcomes — never a silent proceed, never a hard mid-loop halt:**
- **`[auto-fixable]` BLOCKER + cheap NIT** → fix in-tree, continue (today's happy path).
- **`[decision-required]` BLOCKER** (security/a11y tag the axis; see their output contracts) → do NOT best-effort it. Add it to the **draft manifest** (an in-memory list this run accumulates) for Step 7. The loop keeps going — the human resolves it at the merge gate, not mid-flight.
- **`/flow:audit-coverage` `ISSUE · Undeclared change`** → each uncovered behavior is a **`[decision-required]`** entry on the draft manifest (`needs: declare + verify the criterion, or human waive`). Do NOT auto-add the criterion yourself — that is the agent grading its own homework; the resolution is to declare the criterion in the plan's `**Spec-walk:**` block and let `/flow:verify-build` verify it (or the human waives it at the merge gate). A clean `No issues flagged.` adds nothing.
- **FOLLOW-UP** → Step 3 routing.

The draft manifest starts empty. Anything added to it makes the eventual PR a **draft** (Step 7). This is how an unresolved blocker reaches the human at the merge gate they were hitting anyway, instead of halting the loop or shipping a merge-ready-looking PR that isn't ready.

```
Skill("flow:security-review")
Skill("flow:accessibility-review")
Skill("flow:verify-build")
Skill("flow:audit-coverage")
```

Skip behavior:
- `/flow:security-review`: skip if the diff is doc-only or trivially safe (a copy tweak). The reviewer self-detects this and exits early with a clean message.
- `/flow:accessibility-review`: skip if `flow.config.json.uiSurface` is `false` (the reviewer self-detects this and exits early), or if the diff is non-UI (data layer, build config, doc-only).
- `/flow:verify-build`: skip if `flow.config.json.verifyEnabled` is `false` (project-wide opt-out), or if `flow.config.json.platform` resolves to `library` or `none` (no runnable target). The skill self-detects both and exits early with a clean `[verify-build] ...skipping.` message. Unlike security + a11y, verify-build does NOT auto-skip on doc-only diffs — the user may have shipped a behavioral change in a non-code file (e.g., a config-driven feature toggle); the run-and-observe loop is cheap enough to attempt and fall through to Unknown if there's nothing to observe.
- `/flow:audit-coverage`: self-skips (prints `[audit-coverage] SKIPPED — ...`) when the diff has no behavior-bearing source files (doc/test/refactor-only) or the plan has no `**Spec-walk:**` block (spike/tiny/no plan) — there's nothing to compare. Runs on **all platforms** (under-declaration is not platform-specific — unlike verify-build, it does NOT skip on `platform: library|none`).

The first two reviewers are tuned for the in-flow ship context; the bundled Claude Code `/security-review` is fine for out-of-band deep audits but `/flow:security-review` carries the config-slot doc-path resolution this pipeline needs. Verify-build catches the Potemkin-interface / hallucinated-success class no static reviewer catches; it wraps bundled `/verify` with plan-driven criteria. At ship it's a confirmation re-run (discovery happened at the Step 8/9 readiness boundary); a non-converging FAIL/Unknown regression routes to the draft manifest, not a hard halt. **Audit-coverage** closes the complementary gap verify-build can't: verify-build tests the criteria that were *declared*; audit-coverage checks the diff for behavior that was *never declared* (so verify-build never tested it). Together: declared criteria are verified (verify-build → rendered Test plan) AND the declared set is complete (audit-coverage). It is best-effort LLM judgment — it raises the completeness bar, it does not deterministically guarantee it (false negatives possible); a flagged gap routes to draft, never a hard halt.

After all four Skill calls return, emit one consolidated user-facing line so the user can see what actually ran vs skipped:

```
Final-pass reviews: security=[ran|skipped: <reason>], accessibility=[ran|skipped: <reason>], verify-build=[ran|skipped: <reason>], coverage=[ran|skipped: <reason>].
```

Example: `Final-pass reviews: security=ran (3 NITs, 1 FOLLOW-UP), accessibility=skipped (uiSurface:false), verify-build=ran (overall_verdict:PASS, all criteria PASS), coverage=ran (no undeclared changes).`

**Verify-build at ship time is a CONFIRMATION re-run, not discovery.** The behavioral discovery/iteration loop happens earlier, at the Present/Iterate boundary (loop steps 8–9; see `docs/workflow.md`). By the time ship runs, verify-build should already be PASS — ship re-runs it to confirm nothing regressed between the readiness check and now (a bad rebase, a doc/config edit that broke a path).

**On `exit_code: 1` (FAIL or Unknown per FB-0011) at ship time** — this means a *regression since readiness*. Handle it, do NOT hard-halt the loop:
1. Attempt the FB-0012 bounded mechanical fix (≤3, oscillation-checked, same contract as Step 1c — loop only on the verify-build exit code, never on judge prose). Re-run verify-build.
2. If it converges to PASS → continue.
3. If it does NOT converge → add a `[decision-required]` entry to the **draft manifest** ("verify-build FAIL/Unknown unresolved: <criterion + evidence>") and continue to Step 3. The PR opens as a **draft** (Step 7) — never a merge-ready PR on a non-PASS build.

**Reconciliation with the merged PR S auto-advance predicate (do not weaken it):** PR S lets the agent auto-advance *into* `/flow:ship` only when the readiness predicate holds — which *requires* `verify-build` would return PASS (FB-0018: auto-ship needs a positive behavioral PASS, not absence-of-failure). That gate is UNCHANGED. This step only changes what ship does with a *ship-internal* failure: route to draft instead of hard-halt. The two are distinct decision points, and the safety invariant is preserved (in fact strengthened): **no merge-ready PR is ever produced on a non-PASS build** — a draft is mechanically NOT-READY and the human sees the manifest at the merge gate. (The reserved `--skip-verify` override remains a documented Step-1 escape hatch, not implemented in v1.)

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

**Also derive candidates from resolved open questions.** For each `open_questions[]` entry with `routing = this-iteration` that the human **answered with a correction** during Present (Step 8/9) — i.e. they overruled the `recommended_default` — treat it as a candidate FB: that *is* a user correction, the canonical FB source (blueprint § 4). The question + the human's answer form the candidate's "What was said"; the synthesized rule is the corrected direction. This pairs the visual-decision loop with the feedback pipeline (the same answered questions feed the durable record's "questions carried forward" at Step 5c). The source-diversity bar still applies — a human correction is itself one strong source; pair it as usual before writing.

If verify-build was skipped at Step 2 (`verifyEnabled=false`, `platform=library|none`, or doc-only diff per the skill's self-detection), no buffer read; skip this paragraph. If verify-build ran but the buffer is absent or unreadable, emit a `⚠️ verify-build ran but findings buffer at <path> is missing/unreadable; skipping FB-XXXX synthesis from verify-build` warning and continue — don't block ship on a missing diagnostic artifact (verify-build's verdict was already resolved at Step 2 — a non-converging regression would already be in the draft manifest).

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
- **`flow.config.json.specPath`** (default `dev-docs/spec.md`) — if features changed status (planned → shipped) or new features were added, update the features table. If the product surface area changed materially, update the relevant section.

Do **not** add entries that already exist. Skip silently.

### 5a. Doc-currency reconciliation (forward-looking docs — run on EVERY ship)

The history entry above is backward-looking. The roadmap "Now" and plan "Current Focus" are **forward-looking** — they're what a cold reader (a new contributor, or the autonomous loop, which is a cold agent on each run) reads to decide what to do next. They rot silently if not reconciled at ship; stale direction is the FB-0010 fan-out class applied to *what to work on*. Reconcile **every ship**, not just when it feels needed:

- **`flow.config.json.roadmapPath`** (default `dev-docs/roadmap.md`) "Now" section:
  - Set the current-version **headline line** — a line of the form `**Plugin at vX.Y.Z ...**` — from the source of truth (the plugin manifest `version`, or the project's `package.json` version); never leave a prior version labeled "current". (Step 5b asserts the version on THIS line specifically, so the "Recently shipped" list below can't mask a stale headline.)
  - Move the item this PR shipped into a **"Recently shipped"** line; trim the oldest if it exceeds ~5.
  - Refresh the **▶ Next up** pointer so the single highest-priority next step is unambiguous to a cold reader.
  - Strip "in flight" from any workstream that merged; log deferred follow-ups under the relevant horizon.
- **`flow.config.json.planPath`** (default `dev-docs/plan.md`):
  - Update "Current Focus" to the real current version + state.
  - Move shipped items from "Active Work Items" → "Recently Completed" (keep last 3–5); clear stale "Handoff Notes".
- **Reservations:** remove this PR's now-shipped `FB-XXXX` line(s) from `reserved-feedback-numbers.md` (this is the step the dev-side `/ship` historically forgot — do it here so reservations never go stale).

### 5b. Doc-currency gate (mechanical — fail-and-reconcile; runs HERE, not only in manual `/flow:doctor`)

After 5a, **verify** the reconciliation landed. This is the automatic backstop: it fires in the pipeline on every ship, so "stale docs never happen" doesn't depend on anyone remembering to run `/flow:doctor`. It asserts only the **version token** (the cheap, unambiguous signal); narrative correctness stays the judgment of 5a.

```sh
# Resolve the version source of truth: plugin manifest, else root package.json, else N/A.
VSRC=""
for cand in plugins/flow/.claude-plugin/plugin.json .claude-plugin/plugin.json package.json; do
  [ -f "$cand" ] && { VSRC="$cand"; break; }
done
if [ -z "$VSRC" ]; then
  echo "[doc-currency] no versioned manifest found — mechanical version check N/A; 5a reconciliation still applies."
else
  VER=$(jq -r '.version // empty' "$VSRC" 2>/dev/null)
  [ -z "$VER" ] && { echo "⚠️ BLOCKER: doc-currency — $VSRC has no .version; cannot verify currency." >&2; exit 1; }
  ROADMAP=$(jq -r '.roadmapPath // "dev-docs/roadmap.md"' flow.config.json 2>/dev/null); [ -z "$ROADMAP" ] && ROADMAP=dev-docs/roadmap.md
  PLAN=$(jq -r '.planPath // "dev-docs/plan.md"' flow.config.json 2>/dev/null); [ -z "$PLAN" ] && PLAN=dev-docs/plan.md
  # Scope to the current-status section if its heading exists, else the doc's top 40 lines.
  sect() { awk -v H="$1" 'index($0,H){f=1;next} f&&/^## /{exit} f' "$2"; }
  # Assert the version on the current-version HEADLINE line ("**Plugin at vX.Y.Z ...**", written by
  # 5a) — NOT merely anywhere in the section. Otherwise the 5a "Recently shipped" enumeration (which
  # also names the version) satisfies the gate while the headline stays stale — the exact drift this
  # gate exists to catch. Fall back to the whole section when no such headline line exists (consumer
  # projects that don't use the "Plugin at vX" convention keep the lenient section check).
  has_ver() {  # $1 = section text
    line=$(printf '%s\n' "$1" | grep -E '^\*\*Plugin at ')
    if [ -n "$line" ]; then printf '%s' "$line" | grep -qF "$VER"
    else printf '%s' "$1" | grep -qF "$VER"; fi
  }
  MISS=""
  scope=$(sect "## Now" "$ROADMAP");          [ -z "$scope" ] && scope=$(head -40 "$ROADMAP" 2>/dev/null)
  has_ver "$scope" || MISS="$MISS ${ROADMAP}(Now)"
  scope=$(sect "## Current Focus" "$PLAN");    [ -z "$scope" ] && scope=$(head -40 "$PLAN" 2>/dev/null)
  has_ver "$scope" || MISS="$MISS ${PLAN}(Current Focus)"
  if [ -n "$MISS" ]; then
    echo "⚠️ BLOCKER: doc-currency — current version $VER ($VSRC) is not referenced in:$MISS" >&2
    echo "   Those forward-looking docs are stale. Reconcile per Step 5a (set 'Now'/'Current Focus' to $VER), then re-run. Do NOT edit this gate to pass." >&2
    exit 1
  fi
  echo "[doc-currency] PASS — $VER referenced in roadmap Now + plan Current Focus."
fi
```

On BLOCKER, fix the docs (5a) — never route around the gate. A stale-docs ship is the exact failure this prevents (it shipped real drift: `roadmap.md` once read "v1.2.6" while the plugin was v1.5.1). Per the autonomy bar, this gate loops only on its own mechanical signal (version-string presence), never on judgment.

### 5c. Distill the durable visual record (`visual-history.html`) — the picture companion to the history doc

The history entry (Step 5) is the *written* timeline. **`visual-history.html`** is its **picture companion** (`flow.config.json.visualHistoryPath`): a single, curated, reverse-chronological record of the visual/UX decisions that changed how the product looks or feels (FB-0042). The per-run verify-build report (`verifyReportPath`) is **ephemeral** — regenerated each iteration, discarded after merge; without this durable target, the *decision-making* in each report dies. This step is the **distill bridge**: it converts the load-bearing visual decisions from this run's verify-build buffer into **one** curated entry.

**It is heavily gated — most ships skip it.** Run the mechanical gate first; emit an explicit one-line reason on every skip (never a silent no-op):

```sh
UIS=$(jq -r '.uiSurface // true' flow.config.json 2>/dev/null)
VHPATH=$(jq -r '.visualHistoryPath // "core-docs/visual-history.html"' flow.config.json 2>/dev/null); [ -z "$VHPATH" ] && VHPATH="core-docs/visual-history.html"
FINDINGS=$(jq -r '.verifyFindingsPath // "/tmp/flow-verify-findings.json"' flow.config.json 2>/dev/null); [ -z "$FINDINGS" ] && FINDINGS="/tmp/flow-verify-findings.json"
REPORT=$(jq -r '.verifyReportPath // "/tmp/flow-verify-report.html"' flow.config.json 2>/dev/null); [ -z "$REPORT" ] && REPORT="/tmp/flow-verify-report.html"
# The buffer's observations[].content paths are RELATIVE TO THE REPORT DIR (e.g. "assets/<slug>.jpg"),
# the same convention §5a writes and render-report.py reads via --assets-dir. Resolve frame sources
# against $REPORT_DIR — do NOT build a separate ".../assets" prefix (see the copy block in step 3).
REPORT_DIR="$(dirname "$REPORT")"

if [ "$UIS" != "true" ]; then
  echo "[visual-history] skipped (uiSurface:false) — non-UI project, no visual record."
elif [ ! -f "$FINDINGS" ]; then
  echo "[visual-history] skipped (no verify-build buffer at $FINDINGS) — verify-build skipped or didn't run this loop."
else
  echo "[visual-history] gate open — inspect the buffer for a load-bearing visual decision (next paragraph)."
fi
```

If the gate printed a `skipped` line, **stop here — do not author an entry.** Otherwise proceed:

1. **Read the buffer** at `$FINDINGS` (the same structured findings buffer Step 4a reads — shape at `${CLAUDE_PLUGIN_ROOT}/skills/verify-build/lib/findings-schema.json`). The distill source is the buffer's structured fields, **not** the rendered HTML.
2. **Decide whether a visual decision is load-bearing this run.** A decision earns a durable entry only when it **changed the user's read of a surface** — judge against:
   - a `criteria[].grounding` entry whose rationale explains a visible/experiential choice this PR made or changed. The grounding `type` enum is the full schema set — `need | design-language | craft-commitment | open-question` — but the **load-bearing trigger is a *decided* rationale: the first three.** An `open-question`-typed grounding is by definition unresolved, so on its own it does **not** earn a durable entry (it belongs in `questions_carried`, not as the entry's grounding); **and**
   - optionally a **resolved** open question the human settled during Present, carried as `questions_carried` or folded into the grounding. Two routings, distinct meanings: a `this-iteration` question the human **answered with a decision** (e.g. "ship D-1f-A as planned") is a distill source once answered; a `future-planning` question is a forward call to revisit later (e.g. a declared design-language deviation routed to the roadmap) — also worth carrying, and the correct routing when the question is genuinely "later," not "fix before shipping." **Schema gap (see `roadmap.md` § Next "Resolved-this-iteration open questions"):** the buffer has no explicit *resolved* flag, and the Step 8 gate blocks while any unanswered `this-iteration` question is present — so distill a `this-iteration` question only after it has genuinely been answered, and do **not** relabel a still-open `this-iteration` blocker as `future-planning` just to clear the gate (that erases the "decided this iteration" signal). Routing a genuinely-forward question to `future-planning` is correct; relabeling to dodge the gate is not.

   **Hard skip (mechanical floor against the per-PR-dump failure mode):** if the buffer carries **no** `grounding` of type `need`/`design-language`/`craft-commitment` tied to a visible change this run — a behavioral-only change, a no-visual-delta refactor, or only `Unknown`/`not_tested` visual criteria — **skip with a reason**: `echo "[visual-history] skipped (no load-bearing visual decision in this run's buffer)"`. This is the common case even on UI projects; the record is **curated, not a per-PR dump** (FB-0042). Do **not** manufacture an entry to fill the doc. **If multiple legitimate decided groundings are present, author ONE entry for the single most load-bearing one** (the decision that most changed the user's read) — do not log several, and do not spread them across runs.

3. **Author ONE curated entry** (the curation is your judgment — the helper enforces structure, not selection). Build an `entry.json` (shape documented at the top of `lib/insert-visual-history.py`):
   - `title` — the decision, not the PR (e.g. "Empty-state for the activity feed"), **no italic/emphasis** (the helper strips it, but author it clean).
   - `date` (`YYYY-MM-DD`), optional `pr` / `branch`.
   - `grounding` — `type` + `statement` (the user-need or design-language/craft rationale that changed the read) + optional `decision_test` + `citations` resolved from `flow.config.json.specPath` / `designLanguagePath` (**never** hardcoded doc names — project-agnostic).
   - `before_after` — **lean asset refs** preferred. Copy the cited persisted frames out of the ephemeral report's assets dir into a committed, sibling `visual-history-assets/` dir next to `$VHPATH`, then reference them by relative path:
     ```sh
     VHDIR="$(dirname "$VHPATH")"; mkdir -p "$VHDIR/visual-history-assets"
     # Each cited frame's buffer observations[].content is RELATIVE TO THE REPORT DIR ($REPORT_DIR) —
     # e.g. "assets/<slug>.jpg" — so the SOURCE is "$REPORT_DIR/<content>". Copy by basename into the
     # committed assets dir. Do NOT prefix an extra "assets/" (e.g. "$REPORT_DIR/assets/<content>"):
     # <content> already includes it, so that doubles the path to .../assets/assets/<slug> and the
     # rendered <img> ref points at a missing file (the dogfound image-load bug, fixed v1.8.1):
     #   for content in <cited observations[].content>; do
     #     cp "$REPORT_DIR/$content" "$VHDIR/visual-history-assets/$(basename "$content")"   # resized keepers, not raw retina
     #   done
     # then set the entry item: {"label":"After","src":"visual-history-assets/<basename>","alt":"..."}
     ```
     When no real capture is available (e.g. a no-simulator container), supply an **inline CSS/SVG reconstruction** instead (`{"label":"After","html":"<svg…>","recon":true}`) — the honest, labelled fallback (FB-0042(c)). Never base64-embed (that is the ephemeral report's mechanism; the durable record references assets so git stays healthy).
   - optional `questions_carried` — open questions the decision leaves for a future session.

4. **Insert** (creates the file from the bundled skeleton on first write — no bootstrap scaffold, so non-UI projects never get an empty doc):
   ```sh
   printf '%s' "$ENTRY_JSON" | python3 "${CLAUDE_PLUGIN_ROOT}/skills/ship/lib/insert-visual-history.py" --target "$VHPATH"
   ```
   The helper prepends the entry (reverse-chronological), regenerates the anchor-link TOC, and strips any heading emphasis. On a malformed target or invalid entry it fails loudly and writes nothing (your existing record is never corrupted) — fix the input, don't route around it.
5. **Stage** `$VHPATH` + the copied `visual-history-assets/` frames with the rest of the commit (Step 6). The ephemeral `verifyReportPath` stays **un-committed** (distill-then-discard).

> **Validation status (FB-0016):** the durable-record entry shape is **provisional pending a UI-surface dogfood.** flow's own repo is `uiSurface:false` → this step always self-skips here, so the shape is pinned by evals over a synthetic buffer, not yet by a live curated entry. The first real curated entry comes from the tracked health-tracker (iOS) cold-run follow-up (`roadmap.md` § Deliverable-quality track V3b). Treat the rendered entry as structurally-correct-but-editorially-unvalidated until then.

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

**Draft decision (mechanical):** if the **draft manifest** accumulated in Step 2 is non-empty, create the PR as a **draft** (`gh pr create --draft`) and pin the manifest block at the TOP of the body. An empty manifest → a normal (ready) PR. Draft status is the mechanical signal the human merge gate trusts; the manifest is the human-readable one. A not-ready PR can never *look* ready.

**LOCAL-ONLY**: `gh pr create --base $BASE_BRANCH` (add `--draft` iff the manifest is non-empty) with:
- Short title (under 70 chars).
- Body — if the draft manifest is non-empty, prepend this block before `## Summary`:
  ```markdown
  ## 🚫 NOT READY TO MERGE — unresolved blockers
  <!-- flow:not-ready-manifest -->
  - [<security|a11y|verify-build>] <finding> — needs: <secret rotation | design decision | dep vetting | regression fix> — candidate resolutions: <...>
  <!-- /flow:not-ready-manifest -->
  > Resolve every item above, then re-run `/flow:ship` — it removes this block and marks the PR ready (`gh pr ready`) once the manifest is empty. Do not merge while this block is present.
  ```
- Then:
  ```markdown
  ## Summary
  - <1-3 bullets on why this exists>

  ## Test plan
  {{rendered by lib/render-test-plan.py — see "Render the Test plan" below; paste its stdout here verbatim, replacing this line}}

  ## Flow run
  Each loop step — ran or skipped (mode-dependent) — and any significant
  decision or finding it produced. `✓` = ran, `—` = nothing notable; resolve
  every `<...>` placeholder (pick one side of an `a / b`) before publishing.

  | Step | Status | Notable |
  |---|---|---|
  | Clarify | ✓ | — |
  | Plan + /flow:critique-plan | ✓ | <critic findings that changed the plan / —> |
  | Execute | ✓ | <load-bearing impl decisions / —> |
  | Preflight | ✓ | green / <what ran> |
  | /simplify | <✓ / skipped (spike·tiny)> | <what collapsed / —> |
  | /flow:staff-review | <✓ / skipped (spike·tiny)> | <BLOCKERs fixed, real findings / —> |
  | /flow:security-review | <✓ / skipped (reason)> | <result, incl. any [decision-required] blocker / —> |
  | /flow:accessibility-review | <✓ / skipped (reason)> | <result, incl. any [decision-required] blocker / —> |
  | /flow:verify-build | <✓ / skipped (reason)> | <overall_verdict; a non-converging regression → draft / —> |
  | /flow:audit-coverage | <✓ / skipped (reason)> | <undeclared changes → draft / "no undeclared changes" / —> |
  | Doc synthesis | ✓ | <docs updated> |
  | Visual history (§5c) | <✓ / skipped (reason)> | <curated entry: "<decision>" / skipped (uiSurface:false · no load-bearing visual decision) / —> |

  If the `🚫 NOT READY TO MERGE` manifest above is present, this PR is a **draft** — the table's reviewer rows name the unresolved `[decision-required]` finding(s); resolve them per the manifest, not here. Deferred follow-ups: see the configured roadmap and plan docs.

  🤖 Generated with [Claude Code](https://claude.com/claude-code)
  ```

  **Render the `## Test plan` — do NOT hand-author it.** The Test plan is a
  non-forgeable projection of the `/flow:verify-build` findings buffer:
  checkbox state = the buffer's per-criterion `aggregated_verdict`, never your
  own say-so. A criterion renders `[x]` only when an adversarial fresh-context
  judge already returned PASS (verify-build Step 6/7). This is the enforcement
  half of "the human verifies testing was done, then merges" — you cannot show
  a criterion green without a real PASS in the buffer.

  Run the renderer and paste its stdout verbatim as the `## Test plan` section:

  ```sh
  BUF=$(jq -r '.verifyFindingsPath // "/tmp/flow-verify-findings.json"' flow.config.json 2>/dev/null); [ -z "$BUF" ] && BUF=/tmp/flow-verify-findings.json
  # If verify-build SKIPPED at Step 2 (verifyEnabled=false, platform=library|none — see the
  # Step 2 consolidated line), pass --skipped "<reason>" so the renderer emits the honest
  # manual-verification fallback instead of reading a stale/absent buffer:
  #   python3 "${CLAUDE_PLUGIN_ROOT}/skills/ship/lib/render-test-plan.py" "$BUF" --skipped "platform library"
  # Otherwise (verify-build RAN), let it read the buffer; it self-detects no-buffer + stale
  # (buffer branch/sha ≠ current HEAD → manual fallback, never a stale render):
  python3 "${CLAUDE_PLUGIN_ROOT}/skills/ship/lib/render-test-plan.py" "$BUF"
  ```

  The script always emits a complete, self-describing `## Test plan` block and
  always exits 0 — paste it as-is. On the fallback path (skip / no buffer /
  stale / malformed) it renders a `⚠️ No behavioral gate ran (<reason>); manual
  verification required` block with an unchecked `- [ ] <how to verify>` line —
  fill that one line in per the change. Do not re-check boxes by hand: an
  unchecked box is a real, unresolved verification gap. **Flow's own repo is
  `platform: library`, so verify-build self-skips and this PR takes the
  fallback path — that is expected, not a coverage gap** (the renderer's own
  behavior is pinned by `evals/run_render_evals.py`, the consumer-side
  verification for this surface).

  **Populate the `## Flow run` table from THIS session's loop history** — you
  have that context at ship time (the same context you used to write the
  Summary). For each row:

  - **Status** — `✓` if the step ran; `skipped (<reason>)` if it didn't, and
    always name the reason. The reasons are mode- and config-dependent:
    - **spike mode** skips `/simplify` and `/flow:staff-review` → `skipped (spike)`.
    - **tiny mode** skips the spec-walk, `/simplify`, and `/flow:staff-review` → `skipped (tiny)`.
    - `/flow:security-review` skips on a doc-only / trivially-safe diff → `skipped (doc-only)`.
    - `/flow:accessibility-review` skips when `flow.config.json.uiSurface` is
      `false`, or when the diff touches no UI files → `skipped (uiSurface:false)` / `skipped (no UI in diff)`.
    - `/flow:verify-build` skips when `flow.config.json.verifyEnabled` is `false`
      or `platform` is `library`/`none` → `skipped (verifyEnabled:false)` / `skipped (platform library|none)`.
    - `/flow:audit-coverage` skips on a doc/test/refactor-only diff or a plan with no
      `**Spec-walk:**` block → `skipped (no behavior in diff)` / `skipped (no Spec-walk)`. Runs on all platforms.
  - **Notable** — genuine signal only: a plan-critic catch that changed the
    plan, a load-bearing design/impl decision, a `/flow:staff-review` BLOCKER you
    fixed, a real security/a11y/verify-build finding, the docs you updated. A
    routine step with nothing to report gets `—`. **Do not manufacture notes** —
    an invented "improved error handling" line is worse than an honest `—`.

  Honesty rules for Status, in priority order:
  1. Never imply a step ran when it didn't, and never imply it was skipped when
     it ran. In flow v1.4.x, `/flow:security-review`, `/flow:accessibility-review`,
     and `/flow:verify-build` all ship and run from Step 2 — so their Status is
     `✓` unless one of the *runtime-config* skip reasons above actually applied
     this run. Do NOT write "not yet shipped" for them.
  2. `skipped — not yet shipped` is reserved for the genuinely-absent case: a step
     that does not exist in the flow version this project is running (e.g. a
     reviewer gated behind a later release). Use it only when true; otherwise
     drop the row entirely rather than marking it `✓`.

  Follow-ups stay canonical in the roadmap/plan docs (Steps 3 + 5 above); the
  table's closing line only points at them. The PR is still never merged by
  Claude (Step 8).

**PR-OPEN**: push the new commits. If the draft manifest is non-empty, ensure the PR is a draft (`gh pr ready --undo <num>` if it was marked ready) and refresh the `🚫 NOT READY TO MERGE` block; if the manifest is now empty (blockers since resolved), remove the block and `gh pr ready <num>` to mark it ready. Otherwise update the body only if the summary/test plan/Flow-run table needs to reflect the latest scope — and **re-render the `## Test plan` via `lib/render-test-plan.py`** (above), don't hand-edit it, so a re-ship after new commits reflects the fresh buffer (or correctly falls back if HEAD moved past the last verify-build run).

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
| `flow.config.json.verifyFindingsPath` | `/tmp/flow-verify-findings.json` | Step 4a (FB candidates) + Step 5c (distill source) + Step 7 (`lib/render-test-plan.py` renders the `## Test plan`) |
| `flow.config.json.visualHistoryPath` | `core-docs/visual-history.html` | Step 5c (durable visual record; created-on-first-write; gated on `uiSurface` + a load-bearing visual decision) |

Consumer projects typically override the `*Path` slots to `core-docs/<name>.md` since they keep their own project docs under `core-docs/`. Flow's own dev-tracking lives under `dev-docs/` to leave `core-docs/` free as a name that consumer-template-shipped scaffolding uses.
