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
  NEVER auto-invoke when verify-build is skipped (platform library/none, a toolchain absent from this host, or a
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

### 1.0a. Rigor-gate evidence check (mechanical — re-run staff-review on stale evidence; draft only if unresolvable)

The Step 1.0 block above is informational; THIS is the gate. For a **source-touching** diff
that is NOT an explicit spike/tiny-mode ship (where `/simplify` + `/flow:staff-review` are
legitimately skipped), confirm there is **mechanical evidence** those steps actually ran on
the current source — FB-0047 "enforce, don't attest." `/flow:staff-review` writes a
commit-invariant marker (its Step 5a) after its lenses + fixes land; this reads it. A missing
or stale marker is **auto-resolvable by default** — re-run `/flow:staff-review` now on the
final tree (it re-reviews the post-fix source and refreshes the marker), exactly as Step 2a
re-runs a stage classified `SHOULD-RE-RUN · auto-resolvable`. It becomes a
**`[decision-required]`** draft-manifest finding *only* when the re-run can't happen in this
context, or the re-run itself surfaces an unresolved `[decision-required]`. **Do not route a
merely-stale marker to a draft PR** — a draft is reserved for genuine open decisions, not a
re-runnable step. (The common stale case is exactly this: staff-review ran, then its own
prescribed fixes — or a later `/flow:accessibility-review`'s fixes — landed *after* the marker,
moving the source; the correct resolution is to re-run staff-review on the final tree, not to
hand the user a draft to clear by hand.) Docs-only, spike, and tiny-mode ships skip this check
(those modes don't expect staff-review).

```sh
# Source-touching? (reuse the Step 1c three-way sourceFilePatterns check.)
DEFAULT_BRANCH=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@')
[ -z "$DEFAULT_BRANCH" ] && DEFAULT_BRANCH=$(jq -r '.defaultBranch // "main"' flow.config.json 2>/dev/null)
[ -z "$DEFAULT_BRANCH" ] && DEFAULT_BRANCH=main
SOURCE_PATTERN=$(jq -r '.sourceFilePatterns // empty' flow.config.json 2>/dev/null)
[ -z "$SOURCE_PATTERN" ] && SOURCE_PATTERN='\.(ts|tsx|js|jsx|mjs|cjs|py|rs|swift|go|rb|java|kt|sh|bash|tf|tfvars|sql|proto|graphql|gql)$|\.(json|ya?ml|toml)$|(^|/)(Dockerfile|Makefile)(\.|$)'
SRC=$( { git diff "origin/${DEFAULT_BRANCH}..HEAD" --name-only 2>/dev/null; git diff HEAD --name-only 2>/dev/null; git ls-files --others --exclude-standard 2>/dev/null; } | grep -E "$SOURCE_PATTERN" || true)

RIGOR=ok
if [ -n "$SRC" ]; then
  BRANCH=$(git branch --show-current)
  SRC_SHA=$(python3 "${CLAUDE_PLUGIN_ROOT}/skills/ship/lib/rigor-marker.py" source-sha --source-pattern "$SOURCE_PATTERN")
  RIGOR=$(python3 "${CLAUDE_PLUGIN_ROOT}/skills/ship/lib/rigor-marker.py" check --branch "$BRANCH" --source-sha "$SRC_SHA")
  if [ "$RIGOR" != "ok" ]; then
    echo "⚠️ [rigor-gate] no fresh /flow:staff-review marker for this source (reason: $RIGOR)." >&2
    echo "   /simplify + /flow:staff-review have no mechanical evidence of running on the current source." >&2
    echo "   → auto-resolve: re-run /flow:staff-review now on the final tree (refreshes the marker), then re-check." >&2
    echo "     Route a [decision-required] draft-manifest entry ONLY if it can't be re-run here or the re-run surfaces one." >&2
  else
    echo "[rigor-gate] ok — /flow:staff-review marker matches the current source."
  fi
fi
```

If `$RIGOR` was not `ok` on a source-touching, non-spike/tiny ship, **first re-run
`/flow:staff-review`** on the final tree and re-read the marker (auto-resolvable — the same
discipline as Step 2a's `SHOULD-RE-RUN · auto-resolvable`; re-run once, don't loop). Only if the
re-run is impossible in this context — or itself yields an unresolved `[decision-required]` —
**add to the draft manifest** (Step 2), in the canonical line shape (Step 2):
`[rigor] /simplify + /flow:staff-review evidence unresolvable for this source (<reason>) — needs: human-waive — confidence: decision-required — candidate resolutions: <what would make the re-run possible, e.g. run it from a checkout where the source is present>`. This keeps the gating
half of the Step 1.0 assumption block intact — a source-touching diff can't reach a *ready* PR
without the reviews genuinely running — while keeping the resolution auto-resolvable, so a
merely-stale marker never forces a draft PR the human must clear by hand (a draft is reserved for
genuine open decisions, not a re-runnable step).

### 1.0b. Reset the run's draft manifest

Producers append to a branch-scoped manifest file from §1.0a onward. Reset it here, once, before any of them fires — otherwise a previous run's entries survive into this one, and a stale `[verify-build]` entry among them is never subtractable (`CHECK_ONLY`), so the PR could never reach `verdict == READY` over a blocker from another branch.

```sh
TRIAGE="${CLAUDE_PLUGIN_ROOT}/skills/ship/lib/manifest-triage.py"; [ -f "$TRIAGE" ] || TRIAGE="plugins/flow/skills/ship/lib/manifest-triage.py"
python3 "$TRIAGE" init-run --branch "$(git branch --show-current)"
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
- **`[decision-required]` BLOCKER** (security/a11y tag the axis; see their output contracts) → do NOT best-effort it. Add it to the **draft manifest** (an in-memory list this run accumulates) in the canonical line shape (Step 2):
  `[security] <the reviewer's finding> — needs: <secret rotation | dep vetting | design decision> — confidence: decision-required — candidate resolutions: <the reviewer's candidate fixes, and the human input each needs>`
  `[a11y] <the reviewer's finding> — needs: <design decision | dep vetting> — confidence: decision-required — candidate resolutions: <the reviewer's candidate fixes, and the human input each needs>`
  The loop keeps going. Step 7a.5 triages it: `secret rotation`/`dep vetting` need an action outside this session (a genuine draft); anything else becomes a question the human answers at the Step 8 hand-off.
- **`/flow:audit-coverage` `ISSUE · Undeclared change`** → each uncovered behavior is an entry on the draft manifest in the canonical line shape (Step 2):
  `[coverage] <the uncovered behavior> — needs: declare + fence — confidence: decision-required — candidate resolutions: <the criterion you DRAFTED for the plan's Spec-walk block — drafting it is your job; declaring it is not>`. Do NOT auto-add the criterion yourself — that is the agent grading its own homework; the resolution is to declare the criterion in the plan's `**Spec-walk:**` block and let `/flow:verify-build` verify it (or the human waives it at the merge gate). A clean `No issues flagged.` adds nothing.
- **`/flow:verify-build` `metadata.no_plan_fallback: true` on a source-touching diff** → a draft-manifest entry in the canonical line shape (Step 2): `[verify-build] ran without a governing plan (no **Spec-walk:** block) — needs: declare + fence — confidence: decision-required — candidate resolutions: <the criteria you DRAFTED, for the human to approve into the Spec-walk block>`. The verdicts may be real (the §2b judged path produces genuine `adversarial-judged` PASSes over diff-derived criteria), but a plan was *expected* and absent: a production diff shouldn't reach a ready PR via the no-plan path. Resolve by declaring the criteria in the plan's `**Spec-walk:**` block (so the next run is full mode) or waiving at the merge gate. A docs-only no-plan run (smoke path) does not route here.
- **FOLLOW-UP** → Step 3 routing.

**How a producer writes an entry — never hand-compose the line.** The line shape lives in exactly one place (`lib/manifest-triage.py add-entry`), which validates `--kind` and `--needs` against the closed vocabularies at write time and appends to the run's manifest file. Hand-composing an em-dash format across 8 sites is how four of them drifted off-vocabulary before FB-0075:

```sh
TRIAGE="${CLAUDE_PLUGIN_ROOT}/skills/ship/lib/manifest-triage.py"; [ -f "$TRIAGE" ] || TRIAGE="plugins/flow/skills/ship/lib/manifest-triage.py"
python3 "$TRIAGE" add-entry --kind <kind> --finding "<finding>" --needs "<verb>" \
  --resolution "<the resolution you drafted>" >> "$(python3 "$TRIAGE" manifest-path --branch "$(git branch --show-current)")"
```

The manifest is that file — append to it as each producer fires, rather than carrying 8 lines in your context from §1.0a to §7a.5. The `--kind`/`--needs` values each producer passes are named at its own site below.

**Write `--finding` and `--resolution` in plain language.** They are rendered verbatim to a human who has not read the diff — `--finding` becomes the headline of a numbered question at Step 8. "criterion 3 FAIL/Unknown unresolved" and "visually-significant change is missing the rendered walkthrough" are the shorthand this whole step exists to remove; "the offline-retry behaviour didn't hold up when I ran it" and "this change is visible in the app and no screenshots were captured" say the same thing to the person who has to answer. No internal vocabulary (Spec-walk, buffer, HEAD, manifest, verdict, criterion N), no FB-XXXX.

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
- `/flow:verify-build`: skip if `flow.config.json.verifyEnabled` is `false` (project-wide opt-out), if `flow.config.json.platform` resolves to `library` or `none` (no runnable target), or if `platform` is toolchain-gated and **every** binary its build needs is absent from this host (verifiable in principle, not here — e.g. a Linux cloud workspace on a `platform: ios` project). The skill self-detects all three and exits early with a clean `[verify-build] ...skipping.` message. The third is not a free pass: `/flow:audit-skips` validates the claim against the host and routes a `toolchain` entry to the draft manifest, so the PR still opens as a draft. Unlike security + a11y, verify-build does NOT auto-skip on doc-only diffs — the user may have shipped a behavioral change in a non-code file (e.g., a config-driven feature toggle); the run-and-observe loop is cheap enough to attempt and fall through to Unknown if there's nothing to observe.
- `/flow:audit-coverage`: self-skips (prints `[audit-coverage] SKIPPED — ...`) when the diff has no behavior-bearing source files (doc/test/refactor-only) or the plan has no `**Spec-walk:**` block (spike/tiny/no plan) — there's nothing to compare. Runs on **all platforms** (under-declaration is not platform-specific — unlike verify-build, it does NOT skip on `platform: library|none`).

The first two reviewers are tuned for the in-flow ship context; the bundled Claude Code `/security-review` is fine for out-of-band deep audits but `/flow:security-review` carries the config-slot doc-path resolution this pipeline needs. Verify-build catches the Potemkin-interface / hallucinated-success class no static reviewer catches; it wraps bundled `/verify` with plan-driven criteria. At ship it's a confirmation re-run (discovery happened at the Step 8/9 readiness boundary); a non-converging FAIL/Unknown regression routes to the draft manifest, not a hard halt. **Audit-coverage** closes the complementary gap verify-build can't: verify-build tests the criteria that were *declared*; audit-coverage checks the diff for behavior that was *never declared* (so verify-build never tested it). Together: declared criteria are verified (verify-build → rendered Test plan) AND the declared set is complete (audit-coverage). It is best-effort LLM judgment — it raises the completeness bar, it does not deterministically guarantee it (false negatives possible); a flagged gap routes to draft, never a hard halt.

After all four Skill calls return, emit one consolidated user-facing line so the user can see what actually ran vs skipped:

```
Final-pass reviews: security=[ran|skipped: <reason>], accessibility=[ran|skipped: <reason>], verify-build=[ran|skipped: <reason>], coverage=[ran|skipped: <reason>], skip-audit=[all-legitimate|all-legitimate (K owe the manifest: <kind>)|N should-re-run].
```

Example: `Final-pass reviews: security=ran (3 NITs, 1 FOLLOW-UP), accessibility=skipped (uiSurface:false), verify-build=ran (overall_verdict:PASS, all criteria PASS), coverage=ran (no undeclared changes), skip-audit=all-legitimate.` On a host that could not run the behavioral gate: `… verify-build=skipped (toolchain absent: xcodebuild, xcrun not on PATH), coverage=ran, skip-audit=all-legitimate (1 owes the manifest: toolchain).`

(The `skip-audit=` field is filled by **Step 2a** below — `/flow:audit-skips` runs AFTER the four reviewers report and BEFORE Step 3.)

**Verify-build at ship time is a CONFIRMATION re-run, not discovery.** The behavioral discovery/iteration loop happens earlier, at the Present/Iterate boundary (loop steps 8–9; see `docs/workflow.md`). By the time ship runs, verify-build should already be PASS — ship re-runs it to confirm nothing regressed between the readiness check and now (a bad rebase, a doc/config edit that broke a path).

**On `exit_code: 1` (FAIL or Unknown per FB-0011) at ship time** — this means a *regression since readiness*. Handle it, do NOT hard-halt the loop:
1. Attempt the FB-0012 bounded mechanical fix (≤3, oscillation-checked, same contract as Step 1c — loop only on the verify-build exit code, never on judge prose). Re-run verify-build.
2. If it converges to PASS → continue.
3. If it does NOT converge → add an entry to the **draft manifest** in the canonical line shape (Step 2): `[verify-build] <criterion + evidence> — needs: regression fix — confidence: decision-required — candidate resolutions: <what you already tried, and the different approach you would take next>` — then continue to Step 3. The PR opens as a **draft** (Step 7) — never a merge-ready PR on a non-PASS build.

**Reconciliation with the merged PR S auto-advance predicate (do not weaken it):** PR S lets the agent auto-advance *into* `/flow:ship` only when the readiness predicate holds — which *requires* `verify-build` would return PASS (FB-0018: auto-ship needs a positive behavioral PASS, not absence-of-failure). That gate is UNCHANGED. This step only changes what ship does with a *ship-internal* failure: route to draft instead of hard-halt. The two are distinct decision points, and the safety invariant is preserved (in fact strengthened): **no merge-ready PR is ever produced on a non-PASS build** — a draft is mechanically NOT-READY and the human sees the manifest at the merge gate. (The reserved `--skip-verify` override remains a documented Step-1 escape hatch, not implemented in v1.)

### 2a. Skip-legitimacy audit (`/flow:audit-skips`) — runs AFTER the four reviewers, BEFORE Step 3

No stage skip is accepted on its own say-so, and **"the agent did it manually" never substitutes for a stage's real pipeline output.** After the four reviewers above report, audit every stage's skip (and every "ran" claim) against ground truth. The load-bearing rule: **a stage's claimed verdict is trusted only if its canonical artifact EXISTS and matches HEAD** — a verify-build PASS with no fresh findings buffer is the "confirmed manually + self-certified" failure, and the missing buffer is the tell.

1. **Write the per-stage report** (you have every stage's status from this loop run) to the handoff file the skill reads.

   The handoff goes in the **repo-local** scratch dir, never `/tmp` (FB-0082). Two reasons, both load-bearing: a forked skill **cannot see** a `/tmp` file this shell writes — which silently disabled this entire gate from v1.13.0 until FB-0082 — and `/tmp/flow-*` is one global namespace shared with every other project, so a concurrent session on another repo would clobber it. A repo-relative path fixes both, the second by construction. The `flow_stamp` is written **in shell, not via a helper script**, so this step carries no plugin-root dependency (`CLAUDE_PLUGIN_ROOT` is unset in Bash-tool calls).

```sh
# NOTE: this fence is deliberately NOT indented. A heredoc terminator must sit at
# column 0 — an indented `EOF` is treated as CONTENT, so the redirect swallows the
# rest of the script and the handoff is written as invalid JSON. That failure is
# invisible until something reads the file, which is exactly what FB-0082 made
# happen: every ship would then emit `stamp_error` and draft. Keep column 0.
FLOW_ROOT=$(git rev-parse --show-toplevel 2>/dev/null)
if [ -z "$FLOW_ROOT" ]; then
  # exit, don't warn-and-continue: with FLOW_ROOT empty the next line becomes
  # `mkdir -p /.flow` (read-only filesystem) and the raw errors bury this message.
  # A handoff a fork cannot read is not a degraded gate, it is no gate.
  echo "⚠️ BLOCKER: not inside a git repository, so no handoff can be written where a forked skill can read it. The skip-legitimacy gate CANNOT run — do NOT record it as legitimate. Re-run /flow:ship from inside the repo worktree." >&2
  exit 1
fi
# No `${TMPDIR:-/tmp}/flow-detached` fallback here BY DESIGN, unlike the other four
# copies of this idiom: a fork cannot see /tmp at all, so a detached run must fail
# loudly rather than write a handoff nothing will ever read.
FLOW_SCRATCH="$FLOW_ROOT/.flow"
# SECURITY (CWE-59): refuse to write scratch through a symlink. `.flow` is an ordinary
# repo path with none of git's .git/.gitmodules special-casing, so an untrusted clone can
# ship `.flow` as a symlink; `mkdir -p` on an existing symlink-to-dir exits 0 and FOLLOWS
# it, so every write below would land in an attacker-chosen directory outside the repo
# (e.g. truncating a `.gitignore` in ~ or a sibling repo). Moving the sink into
# repo-controlled namespace is what introduced this, so the guard ships with it.
if [ -L "$FLOW_SCRATCH" ]; then
  echo "⚠️ BLOCKER: $FLOW_SCRATCH is a symlink — refusing to write flow scratch through it, because writes would land outside the repo (CWE-59). Replace it with a real directory." >&2
  exit 1
fi
mkdir -p "$FLOW_SCRATCH" || { echo "⚠️ BLOCKER: cannot create $FLOW_SCRATCH — the skip-legitimacy gate cannot run." >&2; exit 1; }
[ -f "$FLOW_SCRATCH/.gitignore" ] || printf '# Created by flow. Ephemeral scratch; never committed.\n*\n' > "$FLOW_SCRATCH/.gitignore"
STAGES="$FLOW_SCRATCH/skip-audit-stages.json"
FLOW_BR=$(git branch --show-current 2>/dev/null); FLOW_HEAD=$(git rev-parse --short HEAD 2>/dev/null)

# Build the stamp with `jq -n --arg` rather than interpolating into the heredoc: a branch
# name may legally contain a double quote (`git check-ref-format --branch 'feat"x'` exits 0),
# which would close the JSON string early. The jq read-back below would catch the damage, but
# soundly escaping here removes the class instead of merely detecting it.
STAMP=$(jq -nc --arg repo "$FLOW_ROOT" --arg branch "$FLOW_BR" --arg head "$FLOW_HEAD" \
  '{repo:$repo, branch:$branch, head:$head}')
# Quoted terminator: the stage rows are literal, and the stamp is spliced in by jq below.
cat > "$STAGES" <<'EOF'
{"stages": [
  {"name": "simplify",            "status": "<ran|skipped>", "skip_reason": "<spike|tiny|doc-only|null>"},
  {"name": "staff-review",        "status": "<ran|skipped>", "skip_reason": "<spike|tiny|doc-only|null>"},
  {"name": "security",            "status": "<ran|skipped>", "skip_reason": "<doc-only|null>"},
  {"name": "accessibility",       "status": "<ran|skipped>", "skip_reason": "<uiSurface:false|no UI in diff|null>"},
  {"name": "verify-build",        "status": "<ran|skipped>", "verdict": "<PASS|FAIL|Unknown|null>", "skip_reason": "<platform library|verifyEnabled:false|toolchain absent: <binaries> not on PATH|null>"},
  {"name": "audit-coverage",      "status": "<ran|skipped>", "skip_reason": "<no Spec-walk|no behavior in diff|null>"},
  {"name": "visual-verification", "status": "<ran|skipped>", "skip_reason": "<null>"}
]}
EOF
# Splice the soundly-escaped stamp in (jq rewrites the file from its own parse, so this
# doubles as a syntax check on the rows above).
TMP_STAGES="$STAGES.tmp"
jq --argjson stamp "$STAMP" '{flow_stamp:$stamp} + .' "$STAGES" > "$TMP_STAGES" && mv "$TMP_STAGES" "$STAGES" \
  || { echo "⚠️ BLOCKER: could not stamp the handoff at $STAGES — the skip-legitimacy gate cannot run." >&2; rm -f "$TMP_STAGES"; exit 1; }

# Read-back the write (FB-0067: never trust a write's own exit status). An unparseable
# handoff is refused downstream as `invalid`, which reads as a gate failure rather than
# as the malformed-heredoc bug it actually is — so assert it here, at the write site.
jq . "$STAGES" >/dev/null 2>&1 || { echo "⚠️ BLOCKER: the handoff at $STAGES is not valid JSON — the skip-legitimacy gate cannot run. Check that the heredoc terminator is at column 0." >&2; exit 1; }
```

   Fill every `<…>` from what actually happened this run — do NOT leave placeholders. `verify-build`'s `verdict` is its `overall_verdict`; `visual-verification` is the Present-step visual sign-off (ran iff you captured + reviewed frames this run).

2. **Invoke the audit** (fresh-context, read-only — it classifies, it never fixes):

   ```
   Skill("flow:audit-skips")
   ```

   It returns a `SKIP-AUDIT SUMMARY` with one line per stage — `LEGITIMATE` or `SHOULD-RE-RUN` (with `auto-resolvable: re-run` or `decision-required`). The mechanical engine (`lib/skip-audit-checks.py`) backs every verdict; trust it. If it reports a **`root_error`** / `ROOT UNRESOLVED` (FB-0074 — the forked skill could not locate the repo under review from its inherited cwd, so it read no config and no diff), treat that as a `[decision-required]` draft-manifest entry (`[skip-audit] root unresolved — the gate never looked at this repo — needs: re-run from the repo worktree | human-waive — confidence: auto-resolvable — candidate resolutions: re-run /flow:ship with cwd inside the worktree, or set CLAUDE_PROJECT_DIR`), **never** a clean pass: an unanchored fork validates every unverifiable skip as LEGITIMATE, so its confident "all legitimate" is exactly the output you must not trust. If it instead reports an **`engine_error`** (the handoff was present but `skip-audit-checks.py` failed on it — the engine now exits non-zero on a malformed/unreadable report rather than collapsing to a silent `stages:[]`), treat that as a `[decision-required]` draft-manifest entry (`[skip-audit] engine failed on a present handoff — needs: fix the engine input | human-waive — confidence: decision-required — candidate resolutions: inspect the handoff JSON named in the error and re-run 2a.1`), **never** a clean pass. (A `no stage report` result when you DID write a handoff at 2a.1 is **not** benign and is no longer a known limitation: FB-0082 moved the handoff to a repo-local `.flow/` path both sides can see, so an absent handoff there means the transport broke again. Route it exactly like `stamp_error` — see 2a.3 — never as a clean pass.)

3. **Resolve — mirror audit-coverage's routing; never a hard mid-loop halt:**
   - **`SHOULD-RE-RUN · auto-resolvable`** → re-invoke that stage's Skill **now** (e.g. a stale/absent verify-build buffer → re-run `Skill("flow:verify-build")`; a contradicted security/a11y skip → run the reviewer), then **re-run `Skill("flow:audit-skips")` ONCE** over the refreshed report. Loop only this one re-audit cycle — do not iterate LLM judgment (reward-hackable; same discipline as Step 2's single-pass reviewers).
   - **`SHOULD-RE-RUN · decision-required`** (cannot be auto-resolved — e.g. a missing visual-history entry, a visual-deliverable gap on a no-sim host) → add a **`[decision-required]`** entry to the **draft manifest** (`[skip-audit] <stage>: <reason> — needs: <re-run | declare | human-waive> — confidence: <auto-resolvable | decision-required> — candidate resolutions: <what would clear it>`). The PR opens as a draft (Step 7).
   - **`⚠️ SKIP-AUDIT COULD NOT VERIFY …` (`stamp_unverifiable`)** → the stamp checker itself could not run (missing helper, no `python3`/`jq`). Do **not** re-run 2a.1 — that cannot fix a toolchain problem. Add a **`[decision-required]`** entry (`[skip-audit] the skip-check never ran — flow could not verify the handoff belongs to this workspace (<reason>), so NO stage skip in this change was audited — needs: install python3/jq or reinstall the flow plugin | human-waive — confidence: decision-required — candidate resolutions: restore the toolchain and re-run /flow:ship; or waive, accepting that no skip was checked`).
   - **`⚠️ SKIP-AUDIT REFUSED …` (`stamp_error`)** → the handoff present at the scratch path did not belong to this repo/branch/HEAD, so the gate did **not** run. Re-run 2a.1 to rewrite the handoff and re-invoke the skill **once**. If it refuses again, add a **`[decision-required]`** entry (`[skip-audit] the skip-check refused a handoff from another workspace (<reason>), so NO stage skip in this change was audited — needs: re-run ship Step 2a.1 | human-waive — confidence: auto-resolvable — candidate resolutions: rewrite the handoff from this workspace and re-audit once; a second refusal means the transport is broken (decision-required)`). Never record this as `all-legitimate`.
   - **`SKIP-AUDIT: no stage report to audit` on a run you launched from 2a.1** → you *did* write a handoff, so an "absent" verdict means the fork could not see it — the transport regression FB-0082 fixed. Treat it exactly like `stamp_error` above; do **not** proceed as if the skips were audited.
   - **`LEGITIMATE · manifest: <kind>`** → the skip was honest **and** the check still never ran, so this is **not** a clean pass. The engine — not you — decided it owes the PR an entry (today the only kind is `toolchain`: a validated toolchain absence on this host). Add it through the validated write path, never a hand-composed line:
     ```sh
     TRIAGE="${CLAUDE_PLUGIN_ROOT}/skills/ship/lib/manifest-triage.py"; [ -f "$TRIAGE" ] || TRIAGE="plugins/flow/skills/ship/lib/manifest-triage.py"
     BRANCH=$(git branch --show-current)
     python3 "$TRIAGE" add-entry --kind toolchain \
       --finding "verify-build could not run: this machine has none of the tools an <platform> build needs (<the binaries the engine named>), so nothing was built or exercised" \
       --needs re-run --confidence decision-required \
       --resolution "re-run /flow:verify-build on a machine that has the toolchain" \
       >> "$(python3 "$TRIAGE" manifest-path --branch "$BRANCH")"
     ```
     **The `>>` redirect is the whole point** — `add-entry` validates and PRINTS the line, it does not write it. Without the redirect the entry goes to stdout, Step 7a.5 classifies an empty manifest, the verdict is `READY`, and §7a.6 opens a **non-draft** PR: a validated-unverifiable skip reaching a ready PR with no behavioral gate, which is exactly what this bullet exists to prevent. Same reason the `TRIAGE` fallback is not optional: `CLAUDE_PLUGIN_ROOT` is unset in Bash-tool calls, so a bare `${CLAUDE_PLUGIN_ROOT}/…` path fails outright in the flow repo itself.
     Then continue. The entry makes the triage verdict `≠ READY`, so §7a.6 opens a **draft** through machinery that already exists — no special-casing there. Do **not** re-invoke verify-build: re-running a stage on a host that cannot run it is the wasted cycle this whole path removes.
   - **All `LEGITIMATE`, and none carrying a `manifest:` field** → emit a one-line confirmation (`skip-audit: all N stage skips legitimate`) and proceed. The qualifier is load-bearing: an unqualified "all legitimate → proceed" is exactly how a validated-but-unverifiable skip would reach a **ready** PR with no behavioral gate.

4. **Record the consolidated result** in the Step-2 `Final-pass reviews:` line (`skip-audit=all-legitimate` / `skip-audit=all-legitimate (K owe the manifest: <kind>)` / `skip-audit=N should-re-run`) and in the PR `## Flow run` table (the `/flow:audit-skips` row).

A docs-only or backend-only PR must rule clean here: those stage skips ARE legitimate (the diff/config back them), so the audit confirms them without noise — no false positives. The audit validates the skip; it does not ban skipping. Skips stay honest, not impossible.

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

**Read verify-build findings buffer (if verify-build ran at Step 2).** When Step 2's `Skill("flow:verify-build")` invocation completed (ran, not skipped), read the structured findings at the path resolved from `flow.config.json.verifyFindingsPath` (default `.flow/verify-findings.json`). The buffer's JSON shape is documented at `${CLAUDE_PLUGIN_ROOT}/skills/verify-build/lib/findings-schema.json` with a canonical example at `findings-example.json`.

For each criterion in `findings.criteria[]` with `aggregated_verdict ∈ {FAIL, Unknown}`:

- Treat it as a **candidate** FB-XXXX entry, not a guaranteed write. The per-dimension `evidence` quotes form the candidate's "What was said" field; the criterion text + per-dimension `notes` form the synthesized rule.
- Apply the source-diversity bar from `${CLAUDE_PLUGIN_ROOT}/docs/workflow.md` § "Continuous improvement": verify-build findings count as ONE review source. A candidate becomes a real FB entry only when paired with a second source (recurrence in time, a second reviewer's finding, or a user correction in this session).
- For Unknown-verdict criteria specifically: the candidate's synthesized rule should name what the verify pass could not observe (per the `notes` field) and suggest a verification mechanism for next time (e.g., "add explicit test for empty-required-field path" or "ensure spike rubric covers headline action").

Single-source verify-build findings without pairing source do NOT earn an FB entry — that's the bar protecting against memory-amplification slop (FB-0010 sub-class).

**Also derive candidates from resolved open questions.** For each `open_questions[]` entry with `routing = this-iteration` that the human **answered with a correction** during Present (Step 8/9) — i.e. they overruled the `recommended_default` — treat it as a candidate FB: that *is* a user correction, the canonical FB source (blueprint § 4). The question + the human's answer form the candidate's "What was said"; the synthesized rule is the corrected direction. This pairs the visual-decision loop with the feedback pipeline (the same answered questions feed the durable record's "questions carried forward" at Step 5c). The source-diversity bar still applies — a human correction is itself one strong source; pair it as usual before writing.

If verify-build was skipped at Step 2 (`verifyEnabled=false`, `platform=library|none`, a toolchain absent from this host, or doc-only diff per the skill's self-detection), no buffer read; skip this paragraph. If verify-build ran but the buffer is absent or unreadable, emit a `⚠️ verify-build ran but findings buffer at <path> is missing/unreadable; skipping FB-XXXX synthesis from verify-build` warning and continue — don't block ship on a missing diagnostic artifact (verify-build's verdict was already resolved at Step 2 — a non-converging regression would already be in the draft manifest).

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

Path: `~/.claude/projects/<canonical-project>/memory/feedback_<short_snake_name>.md` (the memory tool resolves the canonical path; see its top-of-file comment). Format per `${CLAUDE_PLUGIN_ROOT}/skills/documentation/SKILL.md` § "memory entry format" — required fields: Source, First seen, Source-diversity evidence, Pattern, Why I missed it, How to catch it next time, Promotion target, Fire log.

**4b.v — Update fire logs on existing entries.**

If a finding this PR matches an EXISTING memory entry's pattern, append `YYYY-MM-DD` to that entry's `Fire log`. When fire-log reaches 2+ entries, the pattern is a promotion candidate — file a roadmap entry naming the preflight rule that would catch it deterministically. Promotion is user-gated (preflight rules are permanent; a bad rule generates false positives forever).

**4b.vi — Trigger fresh-context audit if due.**

```sh
node ${CLAUDE_PLUGIN_ROOT}/tools/memory/check.mjs --audit-due
```

If exit 1 (audit due), spawn an Agent (subagent_type: Explore) with the memory directory as input. The audit reads ONLY the memory entries (no PR diff, no other context) and answers: which entries' fire logs show no activity in 60+ days (archive candidates)? which entries contradict each other (resolve)? which entries look like over-fitting on a single past incident (revise or delete)? This is the cure for memory ossification.

### 4c. Harvest flow-generalizable lessons → contribution queue (FB-0059)

4a/4b route lessons to **this project's** surfaces. Step 4c routes the *other* destination: lessons about **flow itself** (the workflow, the reviewers, the gates, transferable taste) that should become a PR back to the flow plugin. This is a **two-destination router gated by a noise/confidence filter** — same evidence Step 4 already gathered, one more routing decision on top. No cross-repo action here; it only enqueues to user-scope storage that `/flow:contribute` later drains.

**Determinism boundary:** the routing + noise judgment below are *best-effort LLM work* (like the auditor/critic), backstopped by the human at the `/flow:contribute` draft-PR gate — NOT a deterministic contract. Only the `confidence` score and the prescan gate are mechanical.

```sh
# Resolve scripts (installed plugin root, else this checkout) + the storage slots.
if [ -n "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -d "${CLAUDE_PLUGIN_ROOT}/scripts" ]; then S="${CLAUDE_PLUGIN_ROOT}/scripts"; else S="plugins/flow/scripts"; fi
# Honor contributionsQueuePath by EXPORTING FLOW_CONTRIB_DIR — the scripts read that env
# var (else the user-scope default). Without this export the slot is a no-op (the queue
# always lands in the default dir, diverging from a configured path).
QUEUE_ROOT="$(jq -r '.contributionsQueuePath // empty' flow.config.json 2>/dev/null | sed "s#^~#$HOME#")"
[ -n "$QUEUE_ROOT" ] && export FLOW_CONTRIB_DIR="$QUEUE_ROOT"
MARKER="$(jq -r '.lastHarvestedPath // empty' flow.config.json 2>/dev/null | sed "s#^~#$HOME#")"
[ -z "$MARKER" ] && MARKER="${FLOW_CONTRIB_DIR:-$HOME/.claude/plugins/data/flow/contributions}/last_harvested.json"
```

**Step 4c.i — Pre-scan cost gate (run FIRST; makes clean PRs ~free).**

```sh
python3 "$S/harvest_lesson.py" prescan --marker-file "$MARKER"   # exit 0 = signal; exit 1 = none
```

If the pre-scan exits 1 (no correction / symptom / human-overrule / endorsed-reviewer signal in the transcript since the last harvest), **STOP Step 4c here** — do not spend tokens on the analysis. Print `[analyze] pre-scan: no candidate signal — skipped` and continue to Step 5. Also skip 4c entirely on a docs-only/trivial diff (reuse the Step 1c source-file detection). Only run the analysis below when the pre-scan trips.

**Step 4c.ii — Analyze + route (only if the pre-scan tripped).**

Over the same Step-4 candidate set (corrections / preferences / direction / overruled defaults — do NOT re-read the transcript), apply, in order:

1. **Noise filter (drop first).** Drop generic "just how coding works" patterns and vague observations with no actionable rule. Apply flow's single-source protection (FB-0010/FB-0056): a lone weak signal with no recurrence does not promote. Count what you drop.
2. **Destination test (per surviving finding).** *Rewrite the lesson with every project-specific noun removed. If it still states an actionable rule about how flow should review/gate/plan → **FLOW-GENERALIZABLE**. If it collapses to project trivia → **PROJECT-LOCAL** (already handled by 4a/4b — no further action). If it does both → **BOTH**.*
3. **Source type** (feeds the confidence weight): a symptom/bug the human corrected → `error`/`correction`; **no symptom but the human overruled an agent proposal or stated a preference → `decision`/`taste`** (the highest-value harvest — the point of this feature; 4a already treats an overruled `recommended_default` as canonical). Endorsed reviewer finding → `feedback`.

For each FLOW-GENERALIZABLE / BOTH finding, enqueue it (the script captures the dialogue evidence window, records the origin project token, and dedups/recurrence-counts automatically):

```sh
python3 "$S/harvest_lesson.py" enqueue --marker-file "$MARKER" \
  --pr "<this PR url or branch>" --branch "$(git rev-parse --abbrev-ref HEAD)" \
  --source-type "taste|decision|correction|error|feedback" \
  --artifact-kind "rule-edit|reviewer-prompt|eval-fixture|new-check|fb-entry" \
  --summary "<one line>" --rule "<the synthesized, project-agnostic rule>" \
  --target-hint "<flow file/section it would touch>" \
  --evidence-strength "direct-quote|paraphrase|inferred"
```

**Step 4c.iii — Advance the watermark + report (always, even on the skip path).**

```sh
python3 "$S/harvest_lesson.py" mark --marker-file "$MARKER"
```

Print one line — `[analyze] N findings: P project-local, F flow-generalizable, D dropped (noise/low-confidence)` (or the pre-scan skip line). Never silent.

**Flow-repo nudge.** If `pwd` is the flow checkout (`flow.config.json.flowRepoPath`) and the queue is non-empty, also print `[contribute] N queued contribution(s) — run /flow:contribute to open the PR`.

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
- **Project-declared status surfaces (`flow.config.json.statusDocs`):** the two docs above are the surfaces flow knows about by name. A project may declare *additional* forward-looking status surfaces — e.g. a `CLAUDE.md` or `README.md` phase/status line that auto-loads into every session and silently rots after a sub-PR merges. Reconcile each one's fenced region to the just-shipped reality (you have that context — same as for "Current Focus"):

  ```sh
  HELPER="${CLAUDE_PLUGIN_ROOT}/skills/ship/lib/status-docs.py"
  # `entries` prints "<marker>\t<path>" per declared surface; empty/absent statusDocs → no output.
  # Capture (don't pipe) so a malformed statusDocs (non-array, missing path, bad JSON) surfaces
  # HERE — a `... | while` would discard the non-zero exit and silently no-op the reconcile step.
  SD_ENTRIES=$(python3 "$HELPER" entries flow.config.json 2>/tmp/flow-sd-5a-err)
  if [ $? -ne 0 ]; then
    echo "⚠️ [status-docs] statusDocs is malformed — cannot reconcile: $(cat /tmp/flow-sd-5a-err 2>/dev/null). Fix the array (each entry needs a string 'path'); Step 5b will BLOCK until it parses." >&2
  fi
  printf '%s\n' "$SD_ENTRIES" | while IFS="$(printf '\t')" read -r MARKER PATH_; do
    [ -z "$PATH_" ] && continue
    if ! python3 "$HELPER" region "$MARKER" "$PATH_" >/dev/null 2>&1; then
      echo "⚠️ [status-docs] declared surface $PATH_ has no <!-- $MARKER --> … <!-- /$MARKER --> region; cannot reconcile. Add the fence, or remove it from statusDocs." >&2
    fi
  done
  rm -f /tmp/flow-sd-5a-err
  ```

  For each surface whose region exists, **edit ONLY the text between the `<!-- {marker} -->` and `<!-- /{marker} -->` fences** so the narrative status matches what just shipped (the phase/sub-PR state, the real "next" action). This is a narrow, mechanical region update — **never** restructure the file around it (a consumer's CLAUDE.md may gate broad edits behind a human; the fenced region is the only part flow touches). A declared-but-unfenced surface is a loud `⚠️` here and a hard BLOCKER at Step 5b — fence it, don't skip it.

### 5a.5. Undeclared status-surface drift detection (discovery — routes to draft, never a hard halt)

Steps 5a/5b handle the **declared** (Tier 2) surfaces — the ones a project opted into via `statusDocs`. But the orientation doc a fresh agent reads *first* (`CLAUDE.md`, `AGENTS.md`, `README.md`, …) commonly carries a forward-looking status line that **nobody declared** — so it is invisible to the whole pipeline: 5a touches nothing, 5b prints "none declared", doctor 2.7 has nothing to check. It then silently rots after a merge (the dogfood: a merged sub-PR left `CLAUDE.md` reading "3c is next (not started)" — describing just-shipped work as upcoming; a separate hand PR was needed to fix it). This step closes that adoption gap with **best-effort discovery + drift detection** in the same shape as `/flow:audit-coverage`: LLM judgment, backstopped by the human at the merge gate, routed to the draft manifest — **never** a hard mid-loop halt, **never** a silent auto-edit of an un-fenced human doc.

**Gate: run ONLY when this ship moved forward-looking status.** If neither the plan `## Current Focus` nor the roadmap `## Now` section changed vs the base, there is nothing that could have gone stale — skip explicitly. This is the **same STATUS_MOVED signal** Step 5b computes for its declared-region gate; it is recomputed here (shell blocks don't share scope) via the same tested `status-docs.py section` text path, not a re-implementation of section extraction.

```sh
SSCAN="${CLAUDE_PLUGIN_ROOT}/skills/ship/lib/status-surface-scan.py"
SDHELP="${CLAUDE_PLUGIN_ROOT}/skills/ship/lib/status-docs.py"
# Re-resolve (separate shell block — not in scope from 5a/5b).
DEFAULT_BRANCH=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@')
[ -z "$DEFAULT_BRANCH" ] && DEFAULT_BRANCH=$(jq -r '.defaultBranch // "main"' flow.config.json 2>/dev/null)
[ -z "$DEFAULT_BRANCH" ] && DEFAULT_BRANCH=main
PLAN=$(jq -r '.planPath // "dev-docs/plan.md"' flow.config.json 2>/dev/null); [ -z "$PLAN" ] && PLAN=dev-docs/plan.md
ROADMAP=$(jq -r '.roadmapPath // "dev-docs/roadmap.md"' flow.config.json 2>/dev/null); [ -z "$ROADMAP" ] && ROADMAP=dev-docs/roadmap.md

# STATUS_MOVED — identical signal to Step 5b (plan Current Focus / roadmap Now
# section changed vs base), via the shared helper. New file (no base) reads
# empty → counts as moved (conservative).
STATUS_MOVED=0
for pair in "## Current Focus|$PLAN" "## Now|$ROADMAP"; do
  H=${pair%%|*}; F=${pair#*|}
  WORK=$(python3 "$SDHELP" section "$H" "$F" 2>/dev/null)
  BASE=$(git show "origin/${DEFAULT_BRANCH}:${F}" 2>/dev/null | python3 "$SDHELP" section "$H" - 2>/dev/null)
  [ "$WORK" != "$BASE" ] && STATUS_MOVED=1
done

if [ "$STATUS_MOVED" -eq 0 ]; then
  echo "[status-surface] status unchanged this ship — undeclared-candidate scan skipped."
else
  # Emits a header naming the N undeclared candidates present + a bounded,
  # line-numbered status-bearing slice per candidate for the judge below.
  python3 "$SSCAN" scan flow.config.json 2>/tmp/flow-sss-err
  [ -s /tmp/flow-sss-err ] && echo "⚠️ [status-surface] scan reported: $(cat /tmp/flow-sss-err)" >&2
  rm -f /tmp/flow-sss-err
fi
```

**Judge each emitted candidate (best-effort, fresh reasoning — same tier as `/flow:audit-coverage`).** For each `----- status-surface candidate: <path> -----` block the scan printed, decide: does this doc name — as "next / upcoming / in progress / not started / TODO" — something the just-reconciled plan/roadmap now marks **shipped/done**, OR point at a PR/phase *older than the current frontier* as the active edge?

**False-positive discipline — flag ONLY with a verbatim drift quote as evidence.** Mere keyword presence is NOT drift: a doc that says "Phase 3c" or "the 3c work" with no stale forward-looking claim is fine. You must be able to quote the exact stale sentence (e.g. `"3c is next (not started)"`). **If you can't quote the stale claim, don't flag it.** When in doubt, don't flag — the declared-surface gate (5b) and the human at the merge gate are the backstops; a false positive that wedged a ship would be worse than a missed nudge (doctor Check 2.9 catches the durable case at setup).

- **A flagged surface → a `[decision-required]` draft-manifest entry** (the same in-memory manifest Step 2 accumulates; it makes the PR a draft at Step 7). Format:
  `[status-surface] <path> carries stale forward-looking status ("<verbatim quote>") — needs: reconcile — confidence: decision-required — candidate resolutions: <the corrected line you DRAFTED, verbatim, for the human to approve> — or declare it in statusDocs + fence the region (<!-- flow:status --> … <!-- /flow:status -->) so it auto-reconciles every ship, or human-waive`
  Do **not** silently rewrite the un-fenced doc — the draft item **is** the "propose before editing" proposal (many CLAUDE.mds forbid silent edits; the fix is the human's call, or an opt-in to Tier 2). If the human resolves it in-session by fencing + declaring the surface, it becomes Tier 2 and 5a reconciles it on the next ship.
- **No candidate drifted (or the scan found 0 undeclared candidates)** → emit the explicit skip line (never a silent pass): `[status-surface] N candidates scanned, none drifted` (take N from the scan header).

This is Tier 1 (discovery → draft). A **declared + fenced** doc is Tier 2 — auto-reconciled by 5a, never a draft item here (the scan excludes declared paths, so it never double-counts).

### 5b. Doc-currency gate (mechanical — fail-and-reconcile; runs HERE, not only in manual `/flow:doctor`)

After 5a, **verify** the reconciliation landed. This is the automatic backstop: it fires in the pipeline on every ship, so "stale docs never happen" doesn't depend on anyone remembering to run `/flow:doctor`. Two assertions run here:

1. **Version-token assertion (versioned projects only).** Asserts the current version (from the plugin/package manifest) appears on the plan/roadmap headline. Cheap + unambiguous, but **silently N/A on projects with no manifest** — so it is NOT the whole gate.
2. **Marker-coverage assertion (`statusDocs` — runs with or WITHOUT a version manifest).** For each declared status surface: the marker region must exist, and — when this ship *moved forward-looking status* (the plan "## Current Focus" or roadmap "## Now" section changed vs the base) — that region must have changed too. This is the version-manifest-independent backstop that catches the dogfood failure (a `CLAUDE.md` status line left stale while plan/roadmap moved). Narrative correctness stays the judgment of 5a; this only asserts the region was *touched* when status moved.

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

**Marker-coverage assertion (`statusDocs`)** — runs **independent of the version block above**, so a project with no `plugin.json`/`package.json` still gets real doc-currency enforcement. Empty/absent `statusDocs` ⇒ clean skip (byte-identical to today). When the ship moved forward-looking status but a declared region was left untouched, this BLOCKS:

```sh
HELPER="${CLAUDE_PLUGIN_ROOT}/skills/ship/lib/status-docs.py"
ENTRIES=$(python3 "$HELPER" entries flow.config.json 2>/tmp/flow-statusdocs-err)
if [ $? -ne 0 ]; then
  echo "⚠️ BLOCKER: doc-currency — statusDocs is malformed: $(cat /tmp/flow-statusdocs-err 2>/dev/null)" >&2
  echo "   Fix the statusDocs array in flow.config.json (each entry needs a string 'path'), then re-run." >&2
  exit 1
fi
if [ -z "$ENTRIES" ]; then
  echo "[doc-currency] statusDocs: none declared — marker-coverage check skipped (no extra status surfaces)."
else
  # Re-resolve DEFAULT_BRANCH (not in scope from earlier Bash calls) via the 3-tier chain.
  DEFAULT_BRANCH=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@')
  [ -z "$DEFAULT_BRANCH" ] && DEFAULT_BRANCH=$(jq -r '.defaultBranch // "main"' flow.config.json 2>/dev/null)
  [ -z "$DEFAULT_BRANCH" ] && DEFAULT_BRANCH=main
  PLAN=$(jq -r '.planPath // "dev-docs/plan.md"' flow.config.json 2>/dev/null); [ -z "$PLAN" ] && PLAN=dev-docs/plan.md
  ROADMAP=$(jq -r '.roadmapPath // "dev-docs/roadmap.md"' flow.config.json 2>/dev/null); [ -z "$ROADMAP" ] && ROADMAP=dev-docs/roadmap.md

  # "Did this ship move forward-looking status?" — compare the plan "## Current Focus"
  # + roadmap "## Now" sections between the base revision and the working tree, via the
  # helper's `section` subcommand (same tested text path as the marker regions — no inline
  # awk). Scoped to those two sections (not whole-file) to hold false positives down. A new
  # file (no base) reads empty → counts as moved (conservative).
  STATUS_MOVED=0
  for pair in "## Current Focus|$PLAN" "## Now|$ROADMAP"; do
    H=${pair%%|*}; F=${pair#*|}
    # A missing working file means planPath/roadmapPath is misconfigured — warn rather than
    # swallow it (doctor Check 2.4 also flags bad path slots; don't let the section-diff
    # silently read empty and under-count STATUS_MOVED).
    [ -f "$F" ] || echo "⚠️ [status-docs] $F (from planPath/roadmapPath) not found — status-moved detection for '$H' may be incomplete; check the config slot." >&2
    WORK=$(python3 "$HELPER" section "$H" "$F" 2>/dev/null)
    BASE=$(git show "origin/${DEFAULT_BRANCH}:${F}" 2>/dev/null | python3 "$HELPER" section "$H" - 2>/dev/null)
    [ "$WORK" != "$BASE" ] && STATUS_MOVED=1
  done

  # Accumulate blockers in a temp file (the `entries | while read` pipe runs in a subshell;
  # a shell var wouldn't propagate, a file does).
  BLK=$(mktemp)
  printf '%s\n' "$ENTRIES" | while IFS="$(printf '\t')" read -r MARKER P; do
    [ -z "$P" ] && continue
    if ! python3 "$HELPER" region "$MARKER" "$P" >/tmp/flow-sd-region 2>/dev/null; then
      echo "  - $P: declared <!-- $MARKER --> … <!-- /$MARKER --> region is missing (fence the status region, or remove it from statusDocs)" >> "$BLK"
      continue
    fi
    if [ "$STATUS_MOVED" -eq 1 ]; then
      WORK_REGION=$(cat /tmp/flow-sd-region)
      BASE_REGION=$(git show "origin/${DEFAULT_BRANCH}:${P}" 2>/dev/null | python3 "$HELPER" region "$MARKER" - 2>/dev/null)
      if [ "$WORK_REGION" = "$BASE_REGION" ]; then
        echo "  - $P: plan/roadmap status moved this ship but the <!-- $MARKER --> region is unchanged (reconcile it per Step 5a)" >> "$BLK"
      fi
    fi
  done
  rm -f /tmp/flow-sd-region
  if [ -s "$BLK" ]; then
    echo "⚠️ BLOCKER: doc-currency (statusDocs) — declared status surface(s) not reconciled:" >&2
    cat "$BLK" >&2
    echo "   Reconcile the region(s) per Step 5a, then re-run. Do NOT delete the statusDocs entry to pass the gate." >&2
    echo "   (Known over-fire: if the plan/roadmap change was genuinely NON-status — a reorder, a typo, a follow-up note — and the region is already current, this is the documented false positive. Record that reason and proceed past the gate; do NOT make a cosmetic edit to the region just to silence it — a hollow touch defeats the signal the gate exists to carry.)" >&2
    rm -f "$BLK"
    exit 1
  fi
  rm -f "$BLK"
  echo "[doc-currency] statusDocs PASS — declared status surface(s) fenced$([ "$STATUS_MOVED" -eq 1 ] && echo ' + reconciled (status moved this ship)' || echo ' (status unchanged this ship)')."
fi
```

On BLOCKER, fix the docs (5a) — never route around the gate. A stale-docs ship is the exact failure this prevents (it shipped real drift: `roadmap.md` once read "v1.2.6" while the plugin was v1.5.1). Per the autonomy bar, this gate loops only on its own mechanical signal (version-string presence), never on judgment.

### 5c. Distill the durable visual record (`visual-history.html`) — the picture companion to the history doc

The history entry (Step 5) is the *written* timeline. **`visual-history.html`** is its **picture companion** (`flow.config.json.visualHistoryPath`): a single, curated, reverse-chronological record of the visual/UX decisions that changed how the product looks or feels (FB-0042). The per-run verify-build report (`verifyReportPath`) is **ephemeral** — regenerated each iteration, discarded after merge; without this durable target, the *decision-making* in each report dies. This step is the **distill bridge**: it converts the load-bearing visual decisions from this run's verify-build buffer into **one** curated entry.

**It is heavily gated — most ships skip it.** Run the mechanical gate first; emit an explicit one-line reason on every skip (never a silent no-op):

```sh
# NOT `.uiSurface // true` — jq's `//` treats boolean false as empty, so an explicit
# `uiSurface: false` would resolve to true and the §5c skip below would never fire,
# running the visual-history distill on a non-UI project (FB-0058 boolean-slot footgun).
UIS=$(jq -r 'if .uiSurface == false then "false" else "true" end' flow.config.json 2>/dev/null)
VHPATH=$(jq -r '.visualHistoryPath // "core-docs/visual-history.html"' flow.config.json 2>/dev/null); [ -z "$VHPATH" ] && VHPATH="core-docs/visual-history.html"
FINDINGS=$(jq -r '.verifyFindingsPath // ".flow/verify-findings.json"' flow.config.json 2>/dev/null); [ -z "$FINDINGS" ] && FINDINGS=".flow/verify-findings.json"
REPORT=$(jq -r '.verifyReportPath // ".flow/verify-report.html"' flow.config.json 2>/dev/null); [ -z "$REPORT" ] && REPORT=".flow/verify-report.html"
# The buffer's observations[].content paths are RELATIVE TO THE REPORT DIR (e.g. "assets/<slug>.jpg"),
# the same convention §5a writes and render-report.py reads via --assets-dir. Resolve frame sources
# against $REPORT_DIR — do NOT build a separate ".../assets" prefix (see the copy block in step 3).
REPORT_DIR="$(dirname "$REPORT")"

# Feature 1c — the ONE authoritative visual-significance verdict. Prefer the value
# verify-build stamped into the buffer metadata (do NOT re-derive); fall back to the
# shared helper only when there is no buffer (verify-build skipped/short-circuited).
if [ -f "$FINDINGS" ]; then
  VISSIG=$(jq -r '.metadata.visual_significant // empty' "$FINDINGS" 2>/dev/null)
fi
if [ -z "$VISSIG" ]; then
  if [ -n "${CLAUDE_PLUGIN_ROOT:-}" ]; then VS="${CLAUDE_PLUGIN_ROOT}/skills/verify-build/lib/visual-significance.py"; else VS="plugins/flow/skills/verify-build/lib/visual-significance.py"; fi
  PLAN_P=$(jq -r '.planPath // empty' flow.config.json 2>/dev/null); [ -z "$PLAN_P" ] && PLAN_P="dev-docs/plan.md"
  PLAN_A=""; [ -f "$PLAN_P" ] && PLAN_A="--plan $PLAN_P"
  VISSIG=$(python3 "$VS" --config flow.config.json $PLAN_A 2>/dev/null | jq -r '.visual_significant // false')
fi

if [ "$UIS" != "true" ]; then
  echo "[visual-history] skipped (uiSurface:false) — non-UI project, no visual record."
elif [ "$VISSIG" = "true" ]; then
  # FAILURE-OPEN FIX (Feature 1c): a visually-significant change ALWAYS gets a durable
  # entry — even with no buffer or no machine grounding. This is exactly the change that
  # most needs the record, so the old "skip when short-circuited / no grounding" path is
  # removed here. A hand-authored entry (the FB-0025 workaround) becomes the REQUIRED path.
  echo "[visual-history] REQUIRED (visual_significant=true) — author ONE curated entry (hand-author if the buffer lacks grounding/frames). See the REQUIRED-path note below."
elif [ ! -f "$FINDINGS" ]; then
  echo "[visual-history] skipped (no verify-build buffer at $FINDINGS) — verify-build skipped or didn't run this loop."
else
  echo "[visual-history] gate open — inspect the buffer for a load-bearing visual decision (next paragraph)."
fi
```

If the gate printed a `skipped` line, **stop here — do not author an entry.** If it printed the **`REQUIRED (visual_significant=true)`** line, you MUST author exactly one entry — jump to step 3 and hand-author it per the **REQUIRED-path note** below (do not take the hard-skip in step 2). Otherwise (the plain `gate open` line) proceed normally:

1. **Read the buffer** at `$FINDINGS` (the same structured findings buffer Step 4a reads — shape at `${CLAUDE_PLUGIN_ROOT}/skills/verify-build/lib/findings-schema.json`). The distill source is the buffer's structured fields, **not** the rendered HTML.
2. **Decide whether a visual decision is load-bearing this run.** A decision earns a durable entry only when it **changed the user's read of a surface** — judge against:
   - a `criteria[].grounding` entry whose rationale explains a visible/experiential choice this PR made or changed. The grounding `type` enum is the full schema set — `need | design-language | craft-commitment | open-question` — but the **load-bearing trigger is a *decided* rationale: the first three.** An `open-question`-typed grounding is by definition unresolved, so on its own it does **not** earn a durable entry (it belongs in `questions_carried`, not as the entry's grounding); **and**
   - optionally a **resolved** open question the human settled during Present, carried as `questions_carried` or folded into the grounding. Two routings, distinct meanings: a `this-iteration` question the human **answered with a decision** (e.g. "ship D-1f-A as planned") is a distill source once answered; a `future-planning` question is a forward call to revisit later (e.g. a declared design-language deviation routed to the roadmap) — also worth carrying, and the correct routing when the question is genuinely "later," not "fix before shipping." **Schema gap (see `roadmap.md` § Next "Resolved-this-iteration open questions"):** the buffer has no explicit *resolved* flag, and the Step 8 gate blocks while any unanswered `this-iteration` question is present — so distill a `this-iteration` question only after it has genuinely been answered, and do **not** relabel a still-open `this-iteration` blocker as `future-planning` just to clear the gate (that erases the "decided this iteration" signal). Routing a genuinely-forward question to `future-planning` is correct; relabeling to dodge the gate is not.

   **Hard skip (mechanical floor against the per-PR-dump failure mode) — applies ONLY when `visual_significant` is false:** if the buffer carries **no** `grounding` of type `need`/`design-language`/`craft-commitment` tied to a visible change this run — a behavioral-only change, a no-visual-delta refactor, or only `Unknown`/`not_tested` visual criteria — **skip with a reason**: `echo "[visual-history] skipped (no load-bearing visual decision in this run's buffer)"`. This is the common case even on UI projects; the record is **curated, not a per-PR dump** (FB-0042). Do **not** manufacture an entry to fill the doc. **If multiple legitimate decided groundings are present, author ONE entry for the single most load-bearing one** (the decision that most changed the user's read) — do not log several, and do not spread them across runs.

   **REQUIRED-path note (Feature 1c — `visual_significant` is true): the hard skip above does NOT apply.** A visually-significant change always earns exactly one durable entry, because that is precisely the change whose decision-making must not die with the ephemeral report. The old failure-open — §5c skipped when the buffer lacked grounding or when verify-build was spike/short-circuited (FB-0025) — is removed for this case: it skipped most on the changes that need it most. So:
   - If the buffer carries a decided `grounding`, distill from it as usual (step 3).
   - If it does **not** (no buffer, a short-circuited verify-build, or only `Unknown`/`not_tested` visual criteria), **hand-author** the entry (the FB-0025 workaround is now the REQUIRED path): supply real `before_after` frames (copy the captured frames per step 3's copy block; if NONE exist because frames were uncapturable, use the labelled CSS/SVG reconstruction fallback) and a `grounding` `statement` you write from the change itself. Set `entry.json`'s `branch` to the current branch (Step 7's dual-deliverable gate looks for a visual-history entry referencing THIS branch). Note in the ship log `[visual-history] hand-authored (visual_significant=true, no machine grounding)` so the provenance is honest.
   - Keep the **one-entry** discipline regardless of path: ONE entry for the single most load-bearing decision, never a per-PR dump.

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

> **`gh` resilience — Projects-classic GraphQL deprecation (canonical fallback; staff-review references this).** On repos with classic projects + affected `gh` versions, `gh pr edit`, `gh pr ready`, `gh pr view --json`, and the PR-OPEN body-update path fail with `GraphQL: Projects (classic) is being deprecated … projectCards` — they query `projectCards` even when you only want to touch the body or draft state. `gh pr create` is unaffected. When a PR-write `gh pr <edit|ready|view>` fails with a `projectCards` / Projects-classic error, fall back to the API directly (these endpoints don't query `projectCards`):
> ```sh
> R=$(gh repo view --json nameWithOwner -q .nameWithOwner)   # owner/repo
> # Set the PR body (replaces `gh pr edit --body`): pass the body via a file to avoid quoting issues.
> gh api -X PATCH "repos/$R/pulls/<num>" -F body=@/tmp/flow-pr-body.md >/dev/null
> # Resolve the PR's node id once for the draft-toggle mutations.
> PR_ID=$(gh api "repos/$R/pulls/<num>" -q .node_id)
> # Mark ready (replaces `gh pr ready <num>`):
> gh api graphql -f query='mutation($id:ID!){markPullRequestReadyForReview(input:{pullRequestId:$id}){pullRequest{isDraft}}}' -F id="$PR_ID" >/dev/null
> # Convert to draft (replaces `gh pr ready --undo <num>`):
> gh api graphql -f query='mutation($id:ID!){convertPullRequestToDraft(input:{pullRequestId:$id}){pullRequest{isDraft}}}' -F id="$PR_ID" >/dev/null
> ```
> Only use the fallback when the standard `gh pr` command actually errors with the projectCards signal — don't pre-emptively route around `gh pr` on healthy repos.

> **Mandatory read-back after EVERY PR-body / draft-state write (FB-0067).** A `gh` write can silently no-op — a masked exit code, a projectCards error swallowed downstream, an API hiccup — and leave the STALE body in place while the pipeline reports success. That is exactly how a ready PR ends up still carrying the `🚫 NOT READY TO MERGE` manifest. So after *any* `gh pr edit --body-file`, `gh api -X PATCH …/pulls/N -F body=@file`, `gh pr ready`, or `gh pr ready --undo`, **re-fetch the live PR and assert the write took** — never trust the write's own exit status alone. Source the shared helper and call `flow_verify_pr_write` immediately after the write:
> ```sh
> if [ -n "${CLAUDE_PLUGIN_ROOT:-}" ]; then . "${CLAUDE_PLUGIN_ROOT}/skills/ship/lib/verify-pr-body.sh"; else . "plugins/flow/skills/ship/lib/verify-pr-body.sh"; fi
> # ... do the write as its OWN checked statement (see the HARD RULE below) ...
> flow_verify_pr_write "$N" --expect "## Summary" --forbid "🚫 NOT READY TO MERGE" --want-draft false \
>   || { echo "read-back failed — the PR body on GitHub is NOT what you wrote; re-apply + re-verify, do not proceed" >&2; exit 1; }
> ```
> `flow_verify_pr_write` re-fetches (with the same projectCards→REST fallback above) and asserts, via `lib/pr-coherence.py`, that every `--expect` substring is present, every `--forbid` substring is absent, the draft state matches `--want-draft`, AND the body↔draft coherence invariant holds. On mismatch it fails loud — **do not report success on an unverified write.** The `exit 1` is load-bearing, not decorative: a bare `|| { echo ...; }` with no exit lets the compound command return 0 regardless of the check's outcome, so the pipeline sails through to hand-off having "reported" the failure without actually stopping for it — the exact silent-no-op class this fix exists to close, one abstraction level up. Every `flow_verify_pr_write` / `flow_assert_pr_coherent` call in this skill must end its failure block in `exit 1` (or a retry-then-`exit 1`), never a log-only echo.
>
> **HARD RULE — a gh write is its own checked statement; never pipe it into a filter.** `gh pr edit "$N" --body-file f | tail -1 && gh pr ready "$N"` is forbidden: the pipe makes the pipeline's exit status `tail`'s `0`, masking gh's non-zero, so a failed body write looks like it succeeded and the stale manifest survives (the original silent failure). Run the write, then read back — do not fold the two into one masked pipeline.

The PR base branch is resolved via this fallback chain:
1. `git symbolic-ref refs/remotes/origin/HEAD` (the repo's actual default branch)
2. `flow.config.json.defaultBranch`
3. literal `main`

### 7a. Visual-deliverable gate (Feature 1d — assert BOTH artifacts before marking ready)

Before the draft decision, on a **visually-significant** change (`metadata.visual_significant=true` — the §2c verdict, the same authoritative value §5c reads), assert that **BOTH** visual deliverables exist for THIS run. If either is missing, add a `[visual-deliverable]` entry to the draft manifest so the PR opens as a draft naming the missing artifact — never a silent ready PR with no visual walkthrough.

```sh
FINDINGS=$(jq -r '.verifyFindingsPath // ".flow/verify-findings.json"' flow.config.json 2>/dev/null); [ -z "$FINDINGS" ] && FINDINGS=".flow/verify-findings.json"
REPORT=$(jq -r '.verifyReportPath // ".flow/verify-report.html"' flow.config.json 2>/dev/null); [ -z "$REPORT" ] && REPORT=".flow/verify-report.html"
VHPATH=$(jq -r '.visualHistoryPath // "core-docs/visual-history.html"' flow.config.json 2>/dev/null); [ -z "$VHPATH" ] && VHPATH="core-docs/visual-history.html"
BRANCH=$(git branch --show-current)
HEAD_SHA=$(git rev-parse --short HEAD)

VISSIG=""
[ -f "$FINDINGS" ] && VISSIG=$(jq -r '.metadata.visual_significant // empty' "$FINDINGS" 2>/dev/null)
if [ -z "$VISSIG" ]; then
  if [ -n "${CLAUDE_PLUGIN_ROOT:-}" ]; then VS="${CLAUDE_PLUGIN_ROOT}/skills/verify-build/lib/visual-significance.py"; else VS="plugins/flow/skills/verify-build/lib/visual-significance.py"; fi
  PLAN_P=$(jq -r '.planPath // empty' flow.config.json 2>/dev/null); [ -z "$PLAN_P" ] && PLAN_P="dev-docs/plan.md"
  PLAN_A=""; [ -f "$PLAN_P" ] && PLAN_A="--plan $PLAN_P"
  VISSIG=$(python3 "$VS" --config flow.config.json $PLAN_A 2>/dev/null | jq -r '.visual_significant // false')
fi

if [ "$VISSIG" = "true" ]; then
  MISSING=""
  # (1) The ephemeral walkthrough rendered THIS run: buffer fresh (branch+sha match HEAD)
  #     AND ≥1 captured screenshot frame.
  BUF_OK=no
  if [ -f "$FINDINGS" ]; then
    BB=$(jq -r '.metadata.branch // ""' "$FINDINGS" 2>/dev/null)
    BS=$(jq -r '.metadata.head_sha_short // ""' "$FINDINGS" 2>/dev/null)
    FRAMES=$(jq '[.criteria[]?.observations[]? | select(.type=="screenshot")] | length' "$FINDINGS" 2>/dev/null)
    if [ "$BB" = "$BRANCH" ] && [ "$BS" = "$HEAD_SHA" ] && [ "${FRAMES:-0}" -ge 1 ]; then BUF_OK=yes; fi
  fi
  [ "$BUF_OK" = yes ] || MISSING="$MISSING the rendered walkthrough (a fresh verify-build report for ${BRANCH}@${HEAD_SHA} with ≥1 captured frame at $REPORT);"
  # (2) A NEW visual-history entry referencing this branch/PR.
  if ! { [ -f "$VHPATH" ] && grep -qF "$BRANCH" "$VHPATH"; }; then
    MISSING="$MISSING a visual-history entry referencing $BRANCH in $VHPATH (author it per Step 5c);"
  fi
  if [ -n "$MISSING" ]; then
    echo "⚠️ [visual-deliverable] visually-significant change missing:$MISSING" >&2
    echo "   → add a [visual-deliverable] entry to the draft manifest; the PR opens as a draft." >&2
  else
    echo "[visual-deliverable] OK — fresh walkthrough ($REPORT) + visual-history entry both present."
  fi
fi
```

**If `$MISSING` is non-empty, ATTEMPT the resolution before you gate (FB-0075).** §7a is the one producer that historically drafted without ever trying — every other one makes a bounded attempt first (§1.0a re-runs staff-review per #81, §2a re-runs the stage + re-audits once, §2 spends FB-0012's bounded retry). Both missing artifacts are agent work, so try once:

**The order is fixed, and getting it wrong wastes the attempt.** Step 7 pushed at Step 7's start, *before* this gate runs, and the assertion above compares the buffer's `head_sha_short` against `git rev-parse --short HEAD`. So:

1. **Apply** the resolution — re-run `Skill("flow:verify-build")` to capture frames, and/or author the visual-history entry per Step 5c.
2. **Commit** the resulting file changes (visual-history entry, any captured assets) as their own commit.
3. **Push** it, so the PR opens against a remote head that actually contains the resolution.
4. **Re-run** the producing check against the new `HEAD` (the capture must be stamped with the SHA the PR will carry — re-running before the commit stamps a SHA the commit then invalidates).
5. **Re-apply Step 2's verify-build accounting to the fresh buffer.** This is load-bearing, not ceremony: the assertion above is *artifact-shaped* (`branch`, `sha`, `FRAMES >= 1`) and never reads `overall_verdict`. A re-run that captures a frame but returns FAIL/Unknown would overwrite the buffer Step 2 already blessed and satisfy this gate anyway — a ready PR on a non-PASS build, produced by the step meant to reduce drafts. If the fresh verdict is not PASS, add a `[verify-build]` entry (Step 2's line shape).
6. **Re-assert** the `$MISSING` check above.

**Attempt ONCE.** Record it either way so the attempt survives a later reconcile:

```sh
TRIAGE="${CLAUDE_PLUGIN_ROOT}/skills/ship/lib/manifest-triage.py"; [ -f "$TRIAGE" ] || TRIAGE="plugins/flow/skills/ship/lib/manifest-triage.py"
python3 "$TRIAGE" record-attempt --branch "$BRANCH" --kind visual-deliverable --finding "<the finding text, verbatim>"
```

If the re-assert now passes, there is no manifest entry and nothing reaches the human. If it still fails, **add to the draft manifest via `add-entry`** (Step 2 — never hand-compose the line; `add-entry` validates `--kind`/`--needs` at write time):

```sh
python3 "$TRIAGE" add-entry --kind visual-deliverable \
  --finding "<plain language: this change is visible in the app and <named artifact(s)> is missing>" \
  --needs re-run \
  --resolution "re-run /flow:verify-build to capture frames, and/or hand-author the visual-history entry (Step 5c)" \
  >> "$(python3 "$TRIAGE" manifest-path --branch "$BRANCH")"
``` Because the attempt is recorded, Step 7a.5 classifies it `ask` rather than re-attempting — it becomes a question, not a silent second try. Because the walkthrough is **ephemeral/local (not committed)**, also record its local path in the PR-body handoff (the `## Flow run` table's visual row + the closing line) so the human can open it at the merge gate: `Walkthrough (local, uncommitted): <verifyReportPath>`.

### 7a.5. Manifest triage — a draft PR is a last resort, not a deliverable (FB-0075)

This is the step between accumulating the manifest and acting on it. Without it, three unlike populations reach the human identically: items the agent could have resolved, genuine decisions written in engineer shorthand (`needs: declare + verify the criterion, or human waive` — unanswerable to a non-engineer), and items blocked on an out-of-session action. Only the third deserves a draft.

**This step NEVER halts before the PR.** The pipeline always completes and the PR is always created. That is FB-0034 (three outcomes, escalation routes into an *existing* gate) and FB-0044 (stop-before-PR is reserved for genuine one-way-doors); a mid-loop question would be a third human gate the two-gate thesis forbids. What changes is the *shape of the hand-off*, at Step 8 — not when the question is asked.

Classify the manifest each producer appended to (the branch-scoped file `manifest-path` resolves, written via `add-entry` — see Step 2). The table is deterministic (`lib/manifest-triage.py`), keyed on `kind` — **not** your judgment, so the pass cannot be skipped by routing everything to draft:

```sh
TRIAGE="${CLAUDE_PLUGIN_ROOT}/skills/ship/lib/manifest-triage.py"; [ -f "$TRIAGE" ] || TRIAGE="plugins/flow/skills/ship/lib/manifest-triage.py"
BRANCH=$(git branch --show-current)
STATE=$(python3 "$TRIAGE" init-state --branch "$BRANCH")   # cache; the PR body is the durable record
MANIFEST=$(python3 "$TRIAGE" manifest-path --branch "$BRANCH")
# A MISSING manifest file is the common case — no producer fired, nothing to triage.
# classify treats that as an empty manifest and returns READY; it is not an error.
# Repo-local like every other flow scratch artifact (FB-0082): /tmp is one global
# namespace shared across projects, and a forked reader cannot see it at all.
FLOW_ROOT=$(git rev-parse --show-toplevel 2>/dev/null)
[ -n "$FLOW_ROOT" ] || { echo "⚠️ BLOCKER: not inside a git repository — cannot triage the manifest." >&2; exit 1; }
FLOW_SCRATCH="$FLOW_ROOT/.flow"
# Same CWE-59 refusal as every other .flow writer — an untrusted clone can ship .flow as a
# symlink, and mkdir -p follows it. A guard at five of six sites is not a guard.
if [ -L "$FLOW_SCRATCH" ]; then
  echo "⚠️ BLOCKER: $FLOW_SCRATCH is a symlink — refusing to write flow scratch through it." >&2; exit 1
fi
mkdir -p "$FLOW_SCRATCH"
[ -f "$FLOW_SCRATCH/.gitignore" ] || printf '# Created by flow. Ephemeral scratch; never committed.\n*\n' > "$FLOW_SCRATCH/.gitignore"
python3 "$TRIAGE" classify --entries-file "$MANIFEST" --state-file "$STATE" --branch "$BRANCH" > "$FLOW_SCRATCH/triage.json"
jq -r '.verdict, .counts' "$FLOW_SCRATCH/triage.json"
```

Three classes come back:

- **`auto`** — a resolution is prescribed and has not been attempted. Only `visual-deliverable` qualifies, and §7a above already attempts it, so an `auto` here means the attempt has not run: run it (§7a's ordered sequence), record it, re-classify. **One attempt.** A failed attempt **demotes to `ask`** — never to a silent draft, and never to a second try.
- **`ask`** — a decision the human can answer now. **Draft the resolution** — the criterion, the corrected status line, the specific candidate fix — into the entry's `candidate resolutions:` field. This is the half that answers "high-confidence recs, just do it", discharged safely: you do the work of *proposing*; the human supplies only the approval that doctrine reserves for them (Step 2's audit-coverage rule — never self-declare a criterion; §5a.5's rule — never silently rewrite an un-fenced human doc).
- **`blocked`** — needs an action outside this session (rotate a leaked secret, vet a dependency, or re-run the behavioral gate on a machine that has the toolchain this one lacks). Not waivable, never phrased as a question. This is what a draft PR genuinely exists for.

**Invariants the classifier enforces — do not work around any of them:**
- Clearing is not the classifier's job. Every entry carries `clears_when`; an entry leaves the manifest only when the check that produced it re-runs clean (FB-0062).
- **`residual` = every entry whose `clears_when` has not passed, minus recorded waivers — except `verify-build`, which is never subtracted.** Never a class filter: keying the draft decision on class is exactly how a failed `visual-deliverable` attempt could vanish into a ready PR.
- **No merge-ready PR on a non-PASS build** (§2, unqualified). A `verify-build` entry is never waivable-to-ready; a waiver on it is recorded and the PR **stays a draft**. If the human accepts the risk, they mark it ready on GitHub themselves — you do not.
- Fail-safe direction is toward the human: an unrecognized `needs:` verb classifies `blocked` for security/a11y and `ask` for every other kind, **never `auto`**. Likewise, if the state record cannot be recovered (a cross-session or fresh-host reconcile), `auto` downgrades to `ask` — a question is safe, a blind re-attempt is not.

### 7a.6. Create the PR

**Draft decision (mechanical):** the decision reads the triage **`verdict`** — not the raw manifest, not a class, and **not manifest emptiness**. `verdict == READY` → a normal ready PR. Anything else → create the PR as a **draft** (`gh pr create --draft`) with the rendered manifest block pinned at the TOP of the body. (Keying on emptiness is what would let a waived `verify-build` entry flip a non-PASS build to merge-ready; the verdict already encodes every exemption.)

```sh
# Re-resolve — separate shell block, so §7a.5's variables are NOT in scope.
# ($STATE/$BRANCH expanding empty would silently resolve to a nonexistent state
# path, drop every recorded waiver, and still exit 0 — the FB-0010 silent-skip class.)
# READERS use `state-path`, never `init-state`: creating an empty record makes a
# LOST state look `present`, which re-enables `auto` and defeats invariant 5.
TRIAGE="${CLAUDE_PLUGIN_ROOT}/skills/ship/lib/manifest-triage.py"; [ -f "$TRIAGE" ] || TRIAGE="plugins/flow/skills/ship/lib/manifest-triage.py"
BRANCH=$(git branch --show-current)
STATE=$(python3 "$TRIAGE" state-path --branch "$BRANCH")
MANIFEST=$(python3 "$TRIAGE" manifest-path --branch "$BRANCH")
python3 "$TRIAGE" render-manifest --entries-file "$MANIFEST" --state-file "$STATE" --branch "$BRANCH"
```

Draft status is the mechanical signal the human merge gate trusts; the manifest is the human-readable one. A not-ready PR can never *look* ready.

**LOCAL-ONLY**: `gh pr create --base $BASE_BRANCH` (add `--draft` iff `verdict != READY`) with:

> **After the create, read-back-verify (FB-0067).** `gh pr create` is unaffected by the projectCards deprecation, but a create can still land a body you didn't intend (a truncated `--body-file`, a race). Re-fetch and assert before handing off: source the helper and call `flow_verify_pr_write "$N"` — with `--forbid "🚫 NOT READY TO MERGE" --want-draft false` when `verdict == READY`, or `--expect "🚫 NOT READY TO MERGE" --want-draft true` otherwise. **Key on the verdict, not on manifest emptiness** — they diverge exactly in the case this change introduces: waive every non-`verify-build` entry and the manifest file is still non-empty while `verdict` is `READY` and `render-manifest` returns nothing, so an emptiness-keyed assertion would demand a manifest that is correctly absent and wedge Step 7. A mismatch means the body↔draft state on GitHub contradicts the manifest decision — fix it before Step 8, don't hand off a PR you never confirmed.

- Short title (under 70 chars).
- Body — if `verdict != READY`, prepend this block before `## Summary` (render it; see below):
  **Do NOT hand-author this block — render it** (`lib/manifest-triage.py render-manifest`, Step 7a.6). Hand-authoring is how the engineer shorthand got there, and the renderer is what guarantees each item carries its plain-language triple. Its shape:
  ```markdown
  ## 🚫 NOT READY TO MERGE — unresolved blockers
  <!-- flow:not-ready-manifest -->
  - [<rigor|security|a11y|verify-build|coverage|skip-audit|status-surface|visual-deliverable|toolchain>] <finding> — needs: <secret rotation | design decision | dep vetting | regression fix | re-run | reconcile | declare + fence | hand-author | human-waive> — candidate resolutions: <...>
    - **What this means:** <plain language, no jargon — what actually did not pass>
    - **What I need from you:** <the one decision, answerable in a word>
    - **What happens then:** <ONLY when it differs from the default stated in the trailer>
  > **What happens when you answer:** <the default, stated once> ...
  <!-- /flow:not-ready-manifest -->
  ```
  (The `— confidence:` field is carried on the manifest *file* line, not rendered here — it is machine metadata, and printing it at the reader is the jargon this block exists to remove. The trailer sits INSIDE the fence so the one line telling the reader they need not edit anything is covered by the byte-preserved region.)
  The `🚫 NOT READY TO MERGE` sentinel and both `<!-- flow:not-ready-manifest -->` fences are byte-preserved by the renderer, so `lib/pr-coherence.py`, `/flow:doctor` Check 2.10, and `/flow:land`'s pre-merge check keep matching (FB-0067 — do not "tidy" them).

- **If anything was waived** (`.waived[]` in the triage output — do not hand-author it from memory), add a `## Waived at ship` section (after `## Test plan`). A waiver is a decision the human made, never a silent delete — and Step 7c re-reads this section to reconstruct waivers when the `/tmp` cache is gone (a cross-session or fresh-host reconcile), so it is the durable record, not decoration:
  ```markdown
  ## Waived at ship
  - [<kind>] <finding, verbatim — the exact text the waiver was given for> — waived by you (<fixed anyway | shipped as-is>)
  ```
  A `verify-build` waiver is recorded here **and the PR stays a draft** — Step 2's no-merge-ready-on-a-non-PASS-build rule takes no carve-out.
- Then:
  ```markdown
  ## Summary
  **Scope:** <docs-only | new feature | bugfix | refactor | test | chore | mixed>

  <1-2 plain-language, non-technical sentences: what changed, understandable at a
  glance by someone who has not seen the diff. No internal codenames (FB-XXXX, PR
  letters), no jargon. This is an ADDITIVE opener — it does not replace the detail below.>

  - <why this exists + the specifics a reviewer needs — KEEP these; the plain-language
    line is a new top layer, not a substitute. Never trim detail just because the opener exists.>

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
  | /flow:audit-skips | ✓ | <all N stage skips legitimate / all N legitimate, K owe the manifest (toolchain) → draft / N should-re-run → re-ran M, K → draft> |
  | Manifest triage (§7a.5) | <✓ / n/a (nothing on the manifest)> | <N entries: A auto-resolved, B decisions surfaced at hand-off, C need you outside the session / —> |
  | Visual deliverable (§7a) | <✓ / n/a (not visually significant)> | <both present / draft: missing <walkthrough · visual-history entry>; Walkthrough (local, uncommitted): <verifyReportPath> / —> |
  | Doc synthesis | ✓ | <docs updated> |
  | Status surface (§5a.5) | <✓ / skipped (status unchanged)> | <N candidates scanned, none drifted / draft: <path> stale ("<quote>") / —> |
  | Visual history (§5c) | <✓ / skipped (reason)> | <curated entry: "<decision>" / hand-authored (visual_significant) / skipped (uiSurface:false · no load-bearing visual decision) / —> |

  If a not-ready blockers block is present above, this PR is a **draft** — the table's reviewer rows name the unresolved `[decision-required]` finding(s); resolve them per the manifest, not here.
  <!-- Never write the literal 🚫 sentinel in this sentence. `pr-coherence.py::has_manifest`
       substring-matches it (inline backticks do not exempt it), so on a READY PR the
       explanatory line alone trips the §7b coherence gate and halts a clean ship —
       and makes /flow:land report a false "merged in a not-ready state". --> For a `[visual-deliverable]` draft, the ephemeral walkthrough is **local + uncommitted** — open it at the path named in the Visual-deliverable row before reviewing. Deferred follow-ups: see the configured roadmap and plan docs.

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
  BUF=$(jq -r '.verifyFindingsPath // ".flow/verify-findings.json"' flow.config.json 2>/dev/null); [ -z "$BUF" ] && BUF=.flow/verify-findings.json
  # Resolve the renderer with the same installed-else-checkout fallback every other
  # helper call in this skill uses. This is load-bearing since FB-0074: an unresolved
  # renderer used to degrade softly (the agent hand-wrote a Test plan); now Step 7b
  # asserts provenance, so an unset CLAUDE_PLUGIN_ROOT would hard-fail the ship and
  # tell the operator to run the command that just failed.
  if [ -n "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -f "${CLAUDE_PLUGIN_ROOT}/skills/ship/lib/render-test-plan.py" ]; then
    RTP="${CLAUDE_PLUGIN_ROOT}/skills/ship/lib/render-test-plan.py"
  else
    RTP="plugins/flow/skills/ship/lib/render-test-plan.py"
  fi
  # exit, don't warn-and-continue: Step 7b now hard-fails on a missing stamp, so falling
  # through here just produces a second, less legible failure further down the pipeline.
  [ -f "$RTP" ] || { echo "⚠️ [test-plan] renderer not found at $RTP — the Test plan CANNOT be rendered, and Step 7b will refuse to verify a hand-written one. Reinstall the flow plugin, or run from the flow checkout." >&2; exit 1; }
  # If verify-build SKIPPED at Step 2 (verifyEnabled=false, platform=library|none, toolchain absent — see the
  # Step 2 consolidated line), pass --skipped "<reason>" so the renderer emits the honest
  # manual-verification fallback instead of reading a stale/absent buffer:
  #   python3 "$RTP" "$BUF" --skipped "platform library"
  # Otherwise (verify-build RAN), let it read the buffer; it self-detects no-buffer + stale
  # (buffer branch/sha ≠ current HEAD → manual fallback, never a stale render):
  python3 "$RTP" "$BUF"
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

  **Write the `## Summary` for a reader at the merge gate**, top-down. The Scope
  label + plain-language line are an **additive** top layer — a glanceable first
  read — **not** a replacement for detail. Adding the easy opener must never
  reduce what the PR body would otherwise carry: keep every why-bullet and all
  the specifics a reviewer needs.
  - **Scope** — the primary category of the change, so a reviewer knows what
    kind of review it needs: `docs-only`, `new feature`, `bugfix`, `refactor`,
    `test`, `chore` (build/tooling/deps), or `mixed`. Pick the one that
    dominates; use `mixed` only when two genuinely co-lead, and name the parts.
  - **The plain-language line** — what changed, in one or two non-technical
    sentences a reader can understand at a glance without opening the diff. No
    internal codenames (FB-XXXX, PR letters), no jargon — this is the first thing
    the human reads at the gate.
  - **The why-bullets (retained)** — the existing context/motivation + the
    specifics. Keep them in full; they carry the detail the plain-language line
    intentionally omits for readability. Never drop or thin a bullet just because
    the opener exists — the opener is *in addition to* the detail, not instead of it.

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
      or `platform` is `library`/`none` → `skipped (verifyEnabled:false)` / `skipped (platform library|none)`; or the platform's toolchain is absent from this host → `skipped (toolchain absent)`.
    - `/flow:audit-coverage` skips on a doc/test/refactor-only diff or a plan with no
      `**Spec-walk:**` block → `skipped (no behavior in diff)` / `skipped (no Spec-walk)`. Runs on all platforms.
    - `/flow:audit-skips` always runs at Step 2a (it audits the OTHER stages' skips) →
      `✓`; its Notable cell carries the consolidated verdict (`all N legitimate` /
      `all N legitimate, K owe the manifest (<kind>) → draft` / `N should-re-run →
      re-ran M, K → draft`).
    - **Visual deliverable (§7a)** is `n/a (not visually significant)` unless the §2c
      verdict is true; when true, `✓` (both deliverables present) or the draft note
      naming the missing artifact + the local walkthrough path.
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

**PR-OPEN**: push the new commits. If `verdict != READY`, ensure the PR is a draft (`gh pr ready --undo <num>` if it was marked ready) and refresh the `🚫 NOT READY TO MERGE` block; if `verdict == READY` (blockers since resolved), remove the block and `gh pr ready <num>` to mark it ready. Key on the verdict, never on manifest emptiness — same reason as §7a.6. Otherwise update the body only if the summary/test plan/Flow-run table needs to reflect the latest scope — and **re-render the `## Test plan` via `lib/render-test-plan.py`** (above), don't hand-edit it, so a re-ship after new commits reflects the fresh buffer (or correctly falls back if HEAD moved past the last verify-build run).

**Every body/draft write on the PR-OPEN path is read-back-verified (FB-0067).** This path is where the recurring bug bit: the manifest scrub + `gh pr ready` is coupled to a full re-ship, and a masked write left a ready PR carrying the manifest. So each write is its own checked statement, followed by `flow_verify_pr_write` (source the helper per the § "gh resilience" read-back block above):
- **`verdict == READY` → scrub + ready:** write the manifest-free body, run `gh pr ready <num>` (with the projectCards→`markPullRequestReadyForReview` fallback if it errors), then `flow_verify_pr_write "$N" --forbid "🚫 NOT READY TO MERGE" --want-draft false`. The `--forbid` + `--want-draft false` is the exact assertion that would have caught the original silent failure.
- **`verdict != READY` → refresh + draft:** write the refreshed block, ensure draft, then `flow_verify_pr_write "$N" --expect "🚫 NOT READY TO MERGE" --want-draft true`.
- **Body-only refresh (manifest unchanged):** after the edit, `flow_verify_pr_write "$N" --expect "<a stable substring you just wrote>"` so a no-op write can't pass silently.

### 7b. Body↔draft coherence + Test-plan provenance (FB-0067, FB-0074 — the final gate before hand-off)

After the body + draft state are settled (either path above), assert two invariants against the **live, re-fetched** body: a ready PR can never carry the NOT-READY manifest, and a published Test plan must carry the renderer's provenance stamp:

```sh
if [ -n "${CLAUDE_PLUGIN_ROOT:-}" ]; then . "${CLAUDE_PLUGIN_ROOT}/skills/ship/lib/verify-pr-body.sh"; else . "plugins/flow/skills/ship/lib/verify-pr-body.sh"; fi
N="<pr-number>"   # LOCAL-ONLY: the number gh pr create just returned; PR-OPEN: the existing number
flow_assert_pr_coherent "$N" || {
  echo "⚠️ [coherence] PR #$N violates the body↔draft invariant (NOT a draft, but its body still carries 🚫 NOT READY TO MERGE)." >&2
  echo "   → Fix in place: if the draft manifest is EMPTY, scrub the block from the body and confirm; if it is NON-EMPTY, re-draft (gh pr ready --undo). Then re-run flow_assert_pr_coherent." >&2
  exit 1
}
# FB-0074 — the published Test plan must have come from the renderer, not your keyboard.
# Branch on the code: 1 = a real provenance violation; anything else = the checker or gh
# could not run. Collapsing them would accuse the operator of forgery over a missing lib
# or a gh outage, and tell them to re-run the very command that just failed.
flow_assert_test_plan_provenance "$N"; TP_RC=$?
if [ "$TP_RC" -eq 1 ]; then
  echo "⚠️ [test-plan] PR #$N's '## Test plan' is not a faithful projection of the verify-build buffer — either it carries no renderer stamp (hand-authored) or its checkbox state no longer matches the stamped digest (a box was edited after rendering). Either way its checkboxes are self-assertion, not machine verdicts." >&2
  echo "   → Fix in place: re-render with ship/lib/render-test-plan.py (Step 7's own renderer call — it stamps every path, including the no-buffer fallback), re-publish the body, then re-run flow_assert_test_plan_provenance." >&2
  echo "   → Filling in the fallback block's '<how to verify>' TEXT is fine — the digest covers checkbox state, not prose. Re-typing the block or ticking a box is not." >&2
  echo "   → If this cannot be resolved here, add '[test-plan] provenance unresolvable — human-waive' to the draft manifest and open the PR as a DRAFT; do not hand off a ready PR whose Test plan you could not verify." >&2
  exit 1
elif [ "$TP_RC" -ne 0 ]; then
  echo "⚠️ [test-plan] could not VERIFY provenance for PR #$N (checker or gh unavailable, exit $TP_RC) — this is a tool failure, NOT a forgery finding." >&2
  echo "   → The Test plan is UNCHECKED, not clean. Fix the tool (is pr-coherence.py reachable? is gh authed?) and re-run; or route '[test-plan] provenance UNVERIFIED — human-waive' to the draft manifest and open as a draft." >&2
  exit 1
fi
```

`flow_assert_pr_coherent` re-fetches the live PR and runs `lib/pr-coherence.py coherence`. The invariant: **`NOT isDraft ⇒ body does NOT contain "🚫 NOT READY TO MERGE"`** (and its contrapositive — a non-empty manifest ⇒ the PR is a draft). **The `exit 1` above is load-bearing, not decorative** — a bare `|| { echo ...; }` with no exit lets the compound command return 0 regardless of whether the check failed, so the pipeline would silently fall through to Step 8 hand-off with an incoherent PR: exactly the class of bug this PR fixes, reproduced one abstraction level up in its own gate. On violation: apply the fix-in-place guidance above, re-run `flow_assert_pr_coherent "$N"` once, and only proceed to Step 8 once it exits 0. If it still fails after the fix attempt, the block above's `exit 1` halts the skill — do not hand off a PR you have not confirmed is coherent. This is the last thing Step 7 does — a ready-but-manifest-carrying PR is impossible to leave in that state through `/flow:ship`.

`flow_assert_test_plan_provenance` closes the matching hole one layer down (FB-0074). The `## Test plan` is *specified* as a non-forgeable projection of the verify-build buffer — but nothing checked that the block on GitHub actually came from `render-test-plan.py`, so a hand-written section with hand-ticked boxes read as a machine verdict.

`render-test-plan.py` stamps **every** path it emits — machine-judged, self-report, and the no-buffer manual fallback — with `<!-- flow:test-plan-rendered -->` **plus a content digest** over the block's checkbox states. Two distinct forgeries are therefore caught: a hand-written block (no stamp), and — the subtler one — a genuinely-rendered block whose boxes were flipped afterwards (stamp intact, digest mismatch).

**Honest limit — this raises the cost of forgery, it does not make forgery impossible.** The digest is an *unkeyed* checksum whose algorithm ships in this repo, and the renderer runs in the same trust domain as anything that would forge the block: an agent that wants all-`[x]` can recompute both comment lines. What the stamp genuinely defeats is the *cheap* forgery — hand-writing the section, or flipping a box on a rendered one and leaving the comments alone — plus any post-ship hand-edit of the published body. Closing it properly needs a secret or an out-of-band channel, which flow does not have today; the residual is stated here rather than papered over.

**What it does and does not guarantee.** The stamp attests *provenance*, not passage: an honest "no behavioral gate ran" fallback carries it too. The digest covers checkbox **state and count**, deliberately not criterion prose — Step 7 above instructs you to fill in the fallback's `<how to verify>` text, so hashing prose would make the documented happy path fail its own gate. Editing the surrounding narrative is fine; ticking a box is not. Checking the re-fetched body rather than the local buffer is also deliberate — the published artifact is the one a reviewer trusts.

### 7c. Reconcile-only fast-path (when a blocker was cleared out-of-band)

The manifest lifecycle above is correct only when `/flow:ship` re-runs end-to-end. But a blocker is often cleared *outside* a ship re-run — the operator drives the sim to clear the last Unknown criterion, or **the human answers one of the Step 8 decisions** (FB-0075 — that is a first-class trigger for this path, not an edge case) — and then wants the PR to read honestly without a full pipeline pass. **Hand-editing the PR body is the wrong path** (it is exactly the write that silently failed and produced FB-0067). Instead there is a side-effect-free reconcile that only re-renders the body + reconciles draft state — no reviewers, no `/simplify`, no doc synthesis:

0. **Fetch and parse the live PR body FIRST** — before anything overwrites it. Step 1 recomputes from gate state and step 2 *writes* a new body, so by the time the old §7b read-back runs, the durable record is already gone. Read `## Waived at ship` and each entry's `already-attempted` marker out of the live body and feed them into step 1:

   ```sh
   # Use the shared fetch helper, NOT a bare `gh pr view … > /tmp/<fixed-name>`:
   # it carries the projectCards→REST fallback, checks gh's exit code rather than
   # stdout emptiness, and writes to an mktemp path (a fixed /tmp name is a
   # symlink-attack surface — CWE-377/CWE-59 — which verify-pr-body.sh refuses).
   if [ -n "${CLAUDE_PLUGIN_ROOT:-}" ]; then . "${CLAUDE_PLUGIN_ROOT}/skills/ship/lib/verify-pr-body.sh"; else . "plugins/flow/skills/ship/lib/verify-pr-body.sh"; fi
   TRIAGE="${CLAUDE_PLUGIN_ROOT}/skills/ship/lib/manifest-triage.py"; [ -f "$TRIAGE" ] || TRIAGE="plugins/flow/skills/ship/lib/manifest-triage.py"
   flow_fetch_pr_state "$N" || exit 1
   python3 "$TRIAGE" state --branch "$(git branch --show-current)" --body-file "$FLOW_PR_BODY_FILE"
   ```

   The `/tmp` state file is a same-session cache; **the PR body is the durable record** (it travels with the branch, across sessions and hosts). If neither is recoverable, the classifier refuses to emit `auto` — a question is the safe direction.
1. Recompute the draft manifest from the current gate state (re-read the `verifyFindingsPath` buffer, the security/a11y/skip-audit findings, and §7a's visual-deliverable check) — the same accounting Step 2 + Step 7a do, nothing more — then **subtract recorded waivers** (step 0). Without the subtraction a recompute re-adds every entry the human just answered, and the manifest can never empty. A waiver is honored **only on an exact `(kind, finding)` fingerprint match** against an entry in this same recompute: an ambiguous or partial match is not subtracted, so an over-greedy body parse can never remove a real blocker. A `verify-build` waiver is never subtracted at all.
2. Re-render the body (the manifest via `lib/manifest-triage.py render-manifest`, `## Test plan` via `lib/render-test-plan.py`, the `## Flow run` table from this session) and write it as a checked statement.
3. Reconcile draft state — **keyed on the triage `verdict`, not on manifest emptiness**: `verdict == READY` → scrub + `gh pr ready`; anything else → refresh + ensure draft. Keying on emptiness is how a waived `verify-build` entry could flip a non-PASS build to merge-ready; the verdict already encodes every exemption.
4. Read-back-verify (`flow_verify_pr_write`) and run **both** §7b asserts — `flow_assert_pr_coherent` *and* `flow_assert_test_plan_provenance` (a reconcile re-renders the Test plan, so its digest changes and must be re-verified).
5. **If the post-reconcile residual is still non-empty, re-emit the decision list** (`lib/manifest-triage.py render-decisions`). A partial answer — two of four questions — otherwise hands back a refreshed draft with no in-session decision surface, which is strictly weaker than what Step 8 gives for the identical state. Round two gets the same surface as round one.

Invoke it as a scoped `/flow:ship` (state "reconcile the PR body to current gate state — no reviewers/doc-synthesis") or fold it into `/flow:land`'s pre-merge check (below). Either way the reconcile is one command and never a hand-edit, so the silent-write path is never the way a blocker gets cleared.

## 8. Hand off

**If the residual manifest is empty:** output the PR URL and a one-line summary of what shipped.

**If it is not empty, LEAD WITH THE DECISIONS — never a bare PR URL (FB-0075).** A draft PR handed back on its own is not a result the user can act on; it costs them a round-trip to ask you to fix it. Render the decision list and put it *first*, above the URL:

```sh
# Re-resolve every variable — §7a.5's shell state is long gone by Step 8.
# `state-path` RESOLVES without creating (see §7a.6), and --body-file lets a
# previously-waived entry be reconstructed from the live PR body when the /tmp
# cache is gone — without it, waivers the human already gave re-appear in this list.
TRIAGE="${CLAUDE_PLUGIN_ROOT}/skills/ship/lib/manifest-triage.py"; [ -f "$TRIAGE" ] || TRIAGE="plugins/flow/skills/ship/lib/manifest-triage.py"
BRANCH=$(git branch --show-current)
STATE=$(python3 "$TRIAGE" state-path --branch "$BRANCH")
MANIFEST=$(python3 "$TRIAGE" manifest-path --branch "$BRANCH")
BODY_ARG=""
if [ -n "${N:-}" ]; then
  if [ -n "${CLAUDE_PLUGIN_ROOT:-}" ]; then . "${CLAUDE_PLUGIN_ROOT}/skills/ship/lib/verify-pr-body.sh"; else . "plugins/flow/skills/ship/lib/verify-pr-body.sh"; fi
  flow_fetch_pr_state "$N" && BODY_ARG="--body-file $FLOW_PR_BODY_FILE"
fi
python3 "$TRIAGE" render-decisions --entries-file "$MANIFEST" --state-file "$STATE" --branch "$BRANCH" $BODY_ARG
```

Each `ask` entry becomes one numbered question carrying: what it means in plain language, the resolution **you drafted**, your recommendation first with its reasoning, what you already tried, and — on every entry except `verify-build` — "waive and ship as-is". Each `blocked` entry goes in a separate "needs you outside this session" list, never phrased as a question and never offered a waiver.

**When the user answers, resolve it immediately via the Step 7c reconcile fast-path** — apply the answer, record any waiver (`manifest-triage.py waive`), recompute, re-render, and `gh pr ready` once the verdict is `READY`. Not a hand-edit, and not a second full ship run. A `verify-build` entry is the one exception: a waiver on it is recorded and the PR stays a draft — if the user accepts the risk, they mark it ready themselves.

If nobody answers (an unattended autonomous-loop run), nothing is wedged: the draft stands, and its manifest is now written so the next action is an approval rather than authoring.

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
| `flow.config.json.verifyFindingsPath` | `.flow/verify-findings.json` | Step 4a (FB candidates) + Step 5c (distill source) + Step 7 (`lib/render-test-plan.py` renders the `## Test plan`) |
| `flow.config.json.visualHistoryPath` | `core-docs/visual-history.html` | Step 5c (durable visual record; created-on-first-write; gated on `uiSurface` + a load-bearing visual decision) |
| `flow.config.json.statusDocs` | `[]` | Step 5a (reconcile each declared marker region) + Step 5b (marker-coverage gate, manifest-independent) |
| `flow.config.json.statusSurfaceCandidates` | `[CLAUDE.md, AGENTS.md, README.md, GEMINI.md, .cursorrules, .github/copilot-instructions.md]` | Step 5a.5 (discover UNDECLARED orientation docs that drifted → draft manifest) |
| `flow.config.json.lastHarvestedPath` | `~/.claude/plugins/data/flow/contributions/last_harvested.json` | Step 4c (lesson-harvest watermark; only new transcript since last harvest is analyzed) |
| `flow.config.json.contributionsQueuePath` | `~/.claude/plugins/data/flow/contributions` | Step 4c (enqueue target) + `/flow:contribute` (drain source) |
| `flow.config.json.flowRepoPath` | unset → `/flow:contribute` disabled | Step 4c (flow-repo nudge) + `/flow:contribute` (run-from guard + PR target) |
| `flow.config.json.contributionThreshold` | `0.6` | `/flow:contribute` (auto-include vs hold cutoff) |

Consumer projects typically override the `*Path` slots to `core-docs/<name>.md` since they keep their own project docs under `core-docs/`. Flow's own dev-tracking lives under `dev-docs/` to leave `core-docs/` free as a name that consumer-template-shipped scaffolding uses.
