---
name: staff-review
description: >
  Reviews the current workspace's pending changes from four parallel
  staff-level perspectives — staff engineer, staff UX designer, staff
  design engineer, and push-further (uncommon-care lens) — to catch
  bugs, regressions, accessibility gaps, craft issues, and missed
  opportunities to push the surface beyond on-system to memorable.
  Works on any branch with changes vs the project's default branch,
  whether or not a PR exists. Triages findings into BLOCKER, NIT,
  FOLLOW-UP, and EXPLORATION; fixes blockers and cheap nits in the
  same workspace; captures follow-ups to the project's roadmap/plan
  (via flow.config.json slots) and exploration directions to roadmap §
  Exploration (not just the PR body); updates the PR body with
  reviewer notes when a PR exists; never merges. Use whenever a
  workstream is implementation-complete, when the user asks for a
  "staff" or "multi-perspective" review, or before opening a PR.
  Defer to `/flow:security-review` for security-specific audits.
allowed-tools: Read, Edit, Write, Glob, Grep, Bash, Agent
---

# Staff-perspective review

A workstream is implementation-complete. Run four independent reviews **in parallel**, each from a distinct staff-level lens (extracted to separate plugin-shipped agent files in `${CLAUDE_PLUGIN_ROOT}/agents/lens-*.md`), then triage and fix before requesting human review. **Never merge.**

The source of truth is the workspace diff vs the project's default branch, **not** the PR. Uncommitted edits, committed-but-unpushed work, and an open PR are all valid inputs.

## Project context (resolved at invocation)

- Project config: !`cat flow.config.json 2>/dev/null || echo "(no flow.config.json — using built-in defaults)"`
- Default branch (diff base): !`git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@' || cat flow.config.json 2>/dev/null | jq -r '.defaultBranch // "main"' 2>/dev/null || echo "main"`
- Current branch: !`git branch --show-current`
- Review lenses enabled: !`cat flow.config.json 2>/dev/null | jq -r '.reviewLenses // ["staff-engineer","ux-designer","design-engineer","push-further"] | join(",")' 2>/dev/null || echo "staff-engineer,ux-designer,design-engineer,push-further"`
- Spec doc: !`SPEC=$(cat flow.config.json 2>/dev/null | jq -r '.specPath // empty'); [ -z "$SPEC" ] && SPEC="dev-docs/spec.md"; [ -f "$SPEC" ] && echo "$SPEC" || echo "(no spec doc at $SPEC)"`
- Design-language doc: !`DL=$(cat flow.config.json 2>/dev/null | jq -r '.designLanguagePath // empty'); [ -z "$DL" ] && DL="dev-docs/design-language.md"; [ -f "$DL" ] && echo "$DL" || echo "(no design-language doc at $DL — many projects don't have one)"`
- Feedback doc: !`FB=$(cat flow.config.json 2>/dev/null | jq -r '.feedbackPath // empty'); [ -z "$FB" ] && FB="dev-docs/feedback.md"; [ -f "$FB" ] && echo "$FB" || echo "(no feedback doc at $FB)"`

## When to invoke

- A feature's implementation is complete, `/simplify` (bundled with Claude Code) has already run, and the user is ready for review.
- The user asks for a "staff", "multi-perspective", or "design + engineering" review.
- Before opening a PR on any non-trivial change.

In the canonical 11-step loop (see `${CLAUDE_PLUGIN_ROOT}/docs/workflow.md`), `/simplify` is **step 6** and `/flow:staff-review` is **step 7**. If you're entering this skill and `/simplify` hasn't run yet, run it first — staff-review wastes lens-time on "this could be shorter" issues that `/simplify` removes pre-emptively.

Skip if:
- The change is doc-only or a typo fix.
- The change is already merged into the default branch.
- The user asked for a security review — use `/flow:security-review`.
- There is no diff vs the default branch.

## Why four perspectives, in parallel

Four lenses catch different classes of issue. Three ask "is this good" (engineer, UX-designer, design-engineer); the fourth asks "could this be pushed further." Running them sequentially lets each prime the next; running them in parallel keeps each independent so the findings actually triangulate. **Do not skip a lens** because a human gave a visual opinion or because another lens already ran — AI review and human opinion catch different things, and the four lenses cover distinct surfaces. The only legitimate skip is when a lens genuinely doesn't apply (e.g., backend-only change → no design-engineer surface); in that case say so explicitly rather than running an empty review.

The lens prompts live in separate plugin-shipped agent files at `${CLAUDE_PLUGIN_ROOT}/agents/lens-{staff-engineer,ux-designer,design-engineer,push-further}.md`. They are invoked via the `Agent` tool with `subagent_type` matching each agent's name.

## 1. Detect what artefact exists

### 1.5. External CLI dependency check (warn-only for `gh`; informational for `jq`)

`gh` is used in Step 1b (`gh pr list` for PR-OPEN detection) but the failure mode is graceful (`2>/dev/null`); staff-review works without it (PR detection just returns LOCAL-ONLY). `jq` is used by the frontmatter slot reads + Step 1a stale-base check + Step 4 config-slot consumers; if jq is missing, those silently degrade via `|| default` chains — which is fine for non-fatal slot reads but masks the real diagnostic. Both warn-only — do NOT block.

```sh
# POSIX-portable (same shape as /flow:ship Step 1.5 but warn-only — no exit).
MISSING=""
command -v gh >/dev/null 2>&1 || MISSING="$MISSING gh"
command -v jq >/dev/null 2>&1 || MISSING="$MISSING jq"
if [ -n "$MISSING" ]; then
  MISSING_TRIMMED=$(echo "$MISSING" | sed 's/^ //')
  echo "ℹ️ [staff-review] $MISSING_TRIMMED not installed on PATH:" >&2
  case " $MISSING_TRIMMED " in
    *" gh "*) echo "   - gh missing → PR-OPEN/LOCAL-ONLY detection will return LOCAL-ONLY for any branch." >&2 ;;
  esac
  case " $MISSING_TRIMMED " in
    *" jq "*) echo "   - jq missing → flow.config.json slot reads silently degrade to defaults; project-specific config won't apply." >&2 ;;
  esac
  echo "   Install for full functionality: brew install$MISSING | apt install$MISSING | https://cli.github.com (gh), https://jqlang.org (jq)" >&2
fi
```

(Why warn-only here vs BLOCKING in /flow:ship + /flow:ship-spike: those skills MUST `gh pr create` at Step 7 / Step 6; /flow:staff-review's only mandatory `gh` use is the optional artefact-classification at Step 1b. The Step 7 PR-body write (`gh pr edit`, or its `gh api` projectCards fallback) on the reviewer-notes template IS unsafe if gh is missing — but safe in practice because Step 1b's PR-OPEN detection silently fails to LOCAL-ONLY when gh is missing, so the Step 7 PR-OPEN branch is unreachable in the gh-missing case. jq is the same shape — slot reads degrade gracefully, so warn-only.)

### 1a. Stale-base check (BLOCKING)

Same gate as `/flow:ship` Step 1a — staff-review reads the diff vs the default branch as its source of truth, so a stale base produces phantom-deletion findings that burn 4 lens spawns surfacing what's really just "rebase first." See `dev-docs/feedback.md` FB-0008 for the dogfood discovery + `/flow:ship` Step 1a for the rationale on the `[ -z ]` guards.

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

### 1b. Detect the artefact state

Run in parallel (each command is its own Bash invocation — `DEFAULT_BRANCH` from 1a does NOT persist, so the `git log` line re-resolves inline):
```sh
git status --short
git log --oneline "origin/$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@' || jq -r '.defaultBranch // "main"' flow.config.json 2>/dev/null || echo main)..HEAD"
gh pr list --head $(git branch --show-current) --json number,url 2>/dev/null
```

Classify into:
- **PR-OPEN** — at least one PR returned. Note the number for body updates.
- **LOCAL-ONLY** — commits ahead and/or dirty tree, no PR yet.
- **NOTHING-TO-REVIEW** — clean tree at the default branch. Stop and tell the user.

## 2. Save the workspace diff for the reviewers

Both committed-since-base and uncommitted, plus untracked files (which `git diff` misses):

```sh
BASE=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@' || cat flow.config.json 2>/dev/null | jq -r '.defaultBranch // "main"' 2>/dev/null || echo "main")
{ git diff "origin/$BASE..HEAD"; git diff HEAD; } > /tmp/flow-staff-diff.patch
git ls-files --others --exclude-standard > /tmp/flow-staff-untracked.txt
```

Reviewers reference both paths so each lens prompt stays small.

## 3. Launch the four reviews in parallel

A single tool message with four `Agent` calls. Each call uses `subagent_type` to invoke the corresponding plugin-shipped lens agent:

| Lens | `subagent_type` value | Agent file |
|---|---|---|
| Staff engineer | `lens-staff-engineer` | `${CLAUDE_PLUGIN_ROOT}/agents/lens-staff-engineer.md` |
| Staff UX designer | `lens-ux-designer` | `${CLAUDE_PLUGIN_ROOT}/agents/lens-ux-designer.md` |
| Staff design engineer | `lens-design-engineer` | `${CLAUDE_PLUGIN_ROOT}/agents/lens-design-engineer.md` |
| Push-further | `lens-push-further` | `${CLAUDE_PLUGIN_ROOT}/agents/lens-push-further.md` |

If `flow.config.json.reviewLenses` excludes any lens, skip its `Agent` call and note the exclusion in the reviewer notes (Section 7 below).

Each lens agent's prompt is its own file — you only need to pass the **session-specific inputs**:
- Diff path: `/tmp/flow-staff-diff.patch`
- Untracked-files list path: `/tmp/flow-staff-untracked.txt`
- Changed-files list (computed from the diff)
- Relevant project docs (paths resolved in the Project Context section above)
- PR body or workstream prompt if relevant

Cap each review at ~1200 words by including that cap in the per-call prompt.

## 4. Triage

A finding from any lens is:
- **BLOCKER** — user-visible regression, crash, data loss, accessibility violation, contract break, broken build. **Fix in this workspace.**
- **NIT** / **inline-cheap** — real improvement, cheap (single-file, no architectural change, no new tests). **Fix in this workspace.**
- **FOLLOW-UP** / **roadmap-concrete** — real issue or scoped extension; expanding scope here is wrong. **Capture, don't fix.**
- **future-exploration** — open-ended direction without a clear shape yet. **Capture to roadmap § Exploration.**

Spot-check high-impact findings against the actual code before fixing — reviewers can be confidently wrong.

## 5. Apply blocker + cheap-nit + inline-cheap fixes

Re-run the project's typecheck after the fixes via `flow.config.json.typecheckCmd`:

```sh
TYPECHECK=$(cat flow.config.json 2>/dev/null | jq -r '.typecheckCmd // empty')
if [ -n "$TYPECHECK" ]; then
  sh -c "$TYPECHECK"
else
  echo "⚠️ flow.config.json.typecheckCmd not set; skipping typecheck re-run. Set this slot to enable typecheck on /flow:staff-review."
fi
```

If a test suite or build also runs cheaply, run them too (project-specific).

### 5a. Write the rigor-gate marker (mechanical evidence this review ran on THIS source)

After the fixes are applied (so the marker fingerprints the post-fix tree), record the
rigor-gate marker. This is the mechanical evidence `/flow:ship` Step 1.0 keys on to confirm
that `/simplify` + `/flow:staff-review` actually ran on this source — FB-0047 "enforce, don't
attest." A source-touching ship with no/stale marker routes to the draft manifest. Graceful:
a write failure warns, never aborts the review.

```sh
BRANCH=$(git branch --show-current)
SRC_SHA=$(python3 "${CLAUDE_PLUGIN_ROOT}/skills/ship/lib/rigor-marker.py" source-sha \
  --source-pattern "$(jq -r '.sourceFilePatterns // empty' flow.config.json 2>/dev/null)")
python3 "${CLAUDE_PLUGIN_ROOT}/skills/ship/lib/rigor-marker.py" write \
  --branch "$BRANCH" --source-sha "$SRC_SHA" \
  || echo "⚠️ [staff-review] could not write the rigor-gate marker; /flow:ship may flag this branch as un-reviewed." >&2
```

The marker is commit-invariant (it fingerprints `origin/<default>` vs the working tree, not
`..HEAD`), so committing these fixes before `/flow:ship` does NOT invalidate it — only an
actual source change after this point does, which correctly re-flags for re-review.

## 6. Capture follow-ups + exploration findings so they aren't lost

**Never only in the PR body.** Route them via `flow.config.json` slots:

- **FOLLOW-UP** belongs to active work → `flow.config.json.planPath` (default `dev-docs/plan.md`; consumer projects typically `core-docs/plan.md`). Under the current work item.
- **FOLLOW-UP / roadmap-concrete** larger / future work → `flow.config.json.roadmapPath` (default `dev-docs/roadmap.md`; consumer projects typically `core-docs/roadmap.md`). Under the relevant horizon.
- **future-exploration** → `flow.config.json.roadmapPath` § Exploration, with a `Surfaces when:` trigger that names the file paths or area that should re-surface the item later (so any auto-loading exploration rule can find it during future work in that area).

Can also mention in the PR body for reviewer awareness, but the doc entry is canonical.

## 7. Communicate reviewer notes

- **PR-OPEN**: `gh pr edit <number> --body "..."` — prepend/append the Reviewer notes section using the template below. If `gh pr edit` fails with a `GraphQL: Projects (classic) … projectCards` error (classic-projects repos on affected `gh` versions), fall back to the REST body-update: `gh api -X PATCH "repos/$(gh repo view --json nameWithOwner -q .nameWithOwner)/pulls/<number>" -F body=@<bodyfile>` — see `/flow:ship` Step 7 § "gh resilience" for the canonical fallback block (REST PATCH for body, `markPullRequestReadyForReview` / `convertPullRequestToDraft` GraphQL mutations for draft toggling).
- **LOCAL-ONLY**: send the same content as the final user-facing message of this skill. Also include the dev server URL (if the project ships a `/link`-style skill — start it first) so the user can verify in-browser.

### Reviewer notes template

Fill every lens with a real summary, OR with the explicit null-finding shape ("Nothing of consequence" / "Acted on: —" / "Deferred: —"). Bare ellipses (`...`) read like Claude forgot to fill in the template; always concretize, even when the answer is "nothing."

```markdown
## Reviewer notes

Four parallel reviews ran before this opened for human review. The first three (engineer / UX designer / design engineer) asked "is this good?"; the fourth (push-further) asked "could this go further?" and routes its findings to inline fixes, scoped roadmap items, or roadmap § Exploration.

**Staff engineer.** _Findings:_ [one-line summary, or "Nothing of consequence"]. _Acted on:_ [what was fixed, or "—"]. _Deferred:_ [follow-ups → roadmap/plan location, or "—"].

**Staff UX designer.** _Findings:_ [...]. _Acted on:_ [...]. _Deferred:_ [...].

**Staff design engineer.** _Findings:_ [...]. _Acted on:_ [...]. _Deferred:_ [...].

**Push-further (uncommon-care).** _Findings:_ [N inline-cheap / N roadmap-concrete / N future-exploration — or "Nothing to push — surface at ceiling for its scope"]. _Acted on:_ [what was applied inline, or "—"]. _Deferred:_ [roadmap-concrete → roadmap horizon, future-exploration → roadmap § Exploration, or "—"].

Typecheck (`flow.config.json.typecheckCmd`) re-run after fixes: [pass/fail/skipped].
Dev URL for in-browser check: [link from /link-style skill, if running].
```

Example of a clean null-finding fill: `**Staff UX designer.** _Findings:_ Nothing of consequence — no UI surface in this diff. _Acted on:_ —. _Deferred:_ —.`

The bar is honesty over polish — if a review found nothing of consequence, say so. If you disagreed with a finding and didn't fix it, say so and why.

## 8. Stop

Do not `gh pr merge`. Do not approve. Tell the user the work is ready for their review and link to the PR if one exists.

## Gotchas

- **Reviewers don't see the diff path automatically.** Each lens's prompt template (its own agent file) names the path; the orchestrator must still pass the diff path + untracked-files list as session-specific inputs in each `Agent` call.
- **Untracked files are invisible to `git diff`.** Hand reviewers the `git ls-files --others --exclude-standard` list and tell them to `Read` each one.
- **Reviewers can be confidently wrong.** Spot-check high-impact findings before acting.
- **Grep finds what reviewers miss.** After the reviews, run a focused `Grep` for patterns this change claims to introduce or migrate. Treat survivors as findings.
- **Don't skip a lens because human approval or another lens already ran.** AI review and human visual approval catch different things; the four lenses cover distinct surfaces. The only legitimate skip is when a lens genuinely doesn't apply — in that case say so explicitly rather than running an empty review; never skip with "live-tested" or "scope is tight" as the reason.
- **Scope creep is the failure mode.** "While you're here" suggestions are FOLLOW-UPs.
- **The skill ends with work ready, not merged.** No merge, no approval, no LGTM comment.

## Config slots used

| Slot | Default | Used in |
|---|---|---|
| `flow.config.json.defaultBranch` | `git symbolic-ref` → `main` | Steps 1, 2 (diff base) |
| `flow.config.json.reviewLenses` | `["staff-engineer","ux-designer","design-engineer","push-further"]` | Step 3 (which lenses to spawn) |
| `flow.config.json.typecheckCmd` | unset → loud warning | Step 5 (post-fix re-check) |
| `flow.config.json.specPath` | `dev-docs/spec.md` | Project context |
| `flow.config.json.designLanguagePath` | `dev-docs/design-language.md` | Project context (lens grounding) |
| `flow.config.json.feedbackPath` | `dev-docs/feedback.md` | Project context |
| `flow.config.json.planPath` | `dev-docs/plan.md` | Step 6 (FOLLOW-UP routing) |
| `flow.config.json.roadmapPath` | `dev-docs/roadmap.md` | Step 6 (FOLLOW-UP / EXPLORATION routing) |

## After this skill

Once `/flow:staff-review` reports + you've applied the cheap BLOCKER + NIT fixes inline, the **canonical next step is `/flow:ship`** (or `/flow:ship-spike` for spike-mode PRs). Don't `gh pr create` directly — that bypasses `/flow:ship`'s Step 2 pipeline, which spawns `/flow:security-review` + `/flow:accessibility-review`, synthesizes feedback into both layers (user FB-XXXX + agent memory), updates `core-docs/*.md`, then opens the PR.

Even when the diff is docs-only and you're convinced `/flow:security-review` + `/flow:accessibility-review` would just early-exit, **run `/flow:ship` anyway** — the per-diff gates emit explicit `STATUS: SKIPPED` log lines that show up in the session transcript as evidence the discipline ran. Always invoke `/flow:ship`; never `gh pr create` directly. See `plugins/flow/docs/workflow.md` § "Never bypass `/flow:ship`" for the discipline statement.
