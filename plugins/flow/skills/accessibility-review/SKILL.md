---
name: accessibility-review
description: >
  Cold-reads the current workspace diff vs the project's default branch
  for accessibility issues: semantic HTML, keyboard navigation, focus
  management, ARIA labels, color contrast (WCAG 2.1 AA), reduced-motion
  support, screen-reader announcements, zoom/responsive behavior, form
  labeling. Returns BLOCKER / NIT / FOLLOW-UP findings. Use during
  /flow:ship's final-pass review, on demand for any UI change, or when
  the user says "a11y", "accessibility review", or similar. Honors
  `flow.config.json.uiSurface`: if `false`, exits early with a clean
  "no UI surface declared" message. Invokable directly by the user
  (`/flow:accessibility-review`) or programmatically by `/flow:ship`
  via the Skill tool.
allowed-tools: Read, Glob, Grep, Bash, Agent
---

# Accessibility review

Cold-read the workspace diff for accessibility issues. Target: **WCAG 2.1 AA** for a web app rendered in modern browsers (or the project's stated user-agent baseline if different — check the spec). This skill is invoked by `/flow:ship` as a final pass and can be invoked directly.

## When to invoke

- `/flow:ship` invokes this automatically as one of the two final-pass reviews.
- The user asks for an "accessibility review" or "a11y check".
- Any UI change ships — new component, new interaction, new modal/popover, new keyboard shortcut, new visual state.

Skip if the diff is non-UI (data layer, build config, doc-only).

## Project context (resolved at invocation)

- Project config: !`cat flow.config.json 2>/dev/null || echo "(no flow.config.json — using built-in defaults)"`
- UI surface declared: !`cat flow.config.json 2>/dev/null | jq -r 'if .uiSurface == false then "FALSE (skip a11y review)" else "TRUE (run review)" end' 2>/dev/null || echo "TRUE (default — no flow.config.json found)"`
- Default branch: !`git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@' || cat flow.config.json 2>/dev/null | jq -r '.defaultBranch // "main"' 2>/dev/null || echo "main"`
- Design-language doc (for context): !`DL=$(cat flow.config.json 2>/dev/null | jq -r '.designLanguagePath // empty'); [ -z "$DL" ] && DL="dev-docs/design-language.md"; [ -f "$DL" ] && echo "$DL" || echo "(no design-language doc at $DL — many projects don't have one)"`
- Feedback doc (for context): !`FB=$(cat flow.config.json 2>/dev/null | jq -r '.feedbackPath // empty'); [ -z "$FB" ] && FB="dev-docs/feedback.md"; [ -f "$FB" ] && echo "$FB" || echo "(no feedback doc at $FB)"`

## 0. Honor uiSurface=false (project-wide gate)

If `flow.config.json.uiSurface` is `false`, exit early with this message and stop:

```
✅ Project declares uiSurface: false. Accessibility review skipped — no UI surface to audit.
   If this is wrong, set "uiSurface": true in flow.config.json.
```

This lets backend-only projects (CLI tools, libraries, build systems) declare a11y N/A without false-positive findings.

## 1. Save the diff (with per-diff non-UI early-exit)

```sh
# Resolve default branch via the 3-tier fallback chain with [ -z ] guards
# (NOT the pipe-OR form; see /flow:ship Step 1a + FB-0008 lesson).
BASE=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@')
[ -z "$BASE" ] && BASE=$(jq -r '.defaultBranch // "main"' flow.config.json 2>/dev/null)
[ -z "$BASE" ] && BASE=main

# Per-diff UI-file detection (PR D / FB-0007). Pairs with the project-wide uiSurface=false
# gate above — that gate catches non-UI PROJECTS; this gate catches docs-only PRs in
# UI-surface PROJECTS. Patterns configurable via flow.config.json.uiFilePatterns;
# default covers TSX/JSX/Vue/Svelte/Astro/MDX/CSS/SCSS/Sass/Less/HTML/template files.
# Path-prefix anchors require extension within prefixed dirs (avoids false-positive
# on src/**/*.md docs).
UI_PATTERN=$(jq -r '.uiFilePatterns // empty' flow.config.json 2>/dev/null)
[ -z "$UI_PATTERN" ] && UI_PATTERN='\.(tsx|jsx|vue|svelte|astro|mdx|css|scss|sass|less|html|njk|hbs|ejs)$|^(src|app|packages/ui|public|static)/.+\.(tsx|jsx|vue|svelte|astro|mdx|css|scss|sass|less|html|njk|hbs|ejs)$'

# Validate the regex before using it. Invalid regex → empty result → silent skip
# (FB-0008 class). Fall back to default on invalid input + log a loud warning.
if ! echo "" | grep -qE "$UI_PATTERN" 2>/dev/null && [ $? -ne 1 ]; then
  echo "⚠️ [a11y-review] flow.config.json.uiFilePatterns is invalid as an extended regex; falling back to default." >&2
  UI_PATTERN='\.(tsx|jsx|vue|svelte|astro|mdx|css|scss|sass|less|html|njk|hbs|ejs)$|^(src|app|packages/ui|public|static)/.+\.(tsx|jsx|vue|svelte|astro|mdx|css|scss|sass|less|html|njk|hbs|ejs)$'
fi

# Three checks (not two): committed + uncommitted-modified + untracked. The uncommitted-
# modified check catches the 'iterate locally, then ship' loop that the two-check form
# missed (work-in-progress UI files weren't seen by the reviewer).
UI_FILES_IN_DIFF=$(git diff "origin/$BASE..HEAD" --name-only 2>/dev/null | grep -E "$UI_PATTERN" || true)
UI_MODIFIED=$(git diff HEAD --name-only 2>/dev/null | grep -E "$UI_PATTERN" || true)
UNTRACKED_UI=$(git ls-files --others --exclude-standard 2>/dev/null | grep -E "$UI_PATTERN" || true)
if [ -z "$UI_FILES_IN_DIFF" ] && [ -z "$UI_MODIFIED" ] && [ -z "$UNTRACKED_UI" ]; then
  echo "[a11y-review] STATUS: SKIPPED — no UI files in diff (committed+uncommitted+untracked). Pattern: $UI_PATTERN. Override via flow.config.json.uiFilePatterns."
  exit 0
fi

{ git diff "origin/$BASE..HEAD"; git diff HEAD; } > /tmp/flow-a11y-diff.patch
git ls-files --others --exclude-standard > /tmp/flow-a11y-untracked.txt
```

## 2. Run focused greps

These surface mechanical patterns the model reviewer often misses:

```sh
git diff "origin/$BASE..HEAD" | grep -nE '<div[^>]*onClick|<span[^>]*onClick' || true
git diff "origin/$BASE..HEAD" | grep -nE 'tabIndex\s*=\s*\{?-?[2-9]' || true
git diff "origin/$BASE..HEAD" | grep -nE 'role=["'\'']button["'\'']' || true
grep -rEn 'prefers-reduced-motion' --include='*.{css,scss,less}' . 2>/dev/null | head -5 || true
```

Treat survivors AND absences (e.g. new animations with no `prefers-reduced-motion` check anywhere in the codebase) as candidate findings.

## 3. Launch the a11y reviewer

Single `Agent` call with `subagent_type: Explore`. Cap at ~1000 words. Prompt scaffold:

> You are a staff accessibility engineer cold-reading a diff. Target: WCAG 2.1 AA in modern web browsers (or the project's stated baseline — check the spec doc if accessible). The project's tech stack and product domain are documented in the spec doc and `flow.config.json`; read those first to ground your audit.
>
> **Inputs:**
> - Diff: `/tmp/flow-a11y-diff.patch`
> - Untracked files (Read in full): `/tmp/flow-a11y-untracked.txt`
> - Design-language doc (path injected above; may be absent — many projects don't have one)
> - Feedback doc (path injected above; may be absent)
>
> **Hunt for:**
> 1. **Semantic HTML** — `<div onClick>` / `<span onClick>` for interactive elements (should be `<button>` or `<a>`). Heading hierarchy gaps (h1 → h3 skipping h2). Lists not using `<ul>`/`<ol>`. Forms without labels.
> 2. **Keyboard navigation** — Every interactive element reachable via Tab? Logical tab order? Custom keyboard shortcuts conflict with browser/AT defaults (e.g. blocking `/` or Cmd+F)? Escape closes modals/popovers? Enter/Space activate buttons?
> 3. **Focus management** — Modal/popover traps focus on open and restores on close? Focus rings visible on all focusable elements (no `outline: none` without a replacement)? Newly mounted content receives focus when appropriate?
> 4. **ARIA & screen reader** — Icon-only buttons have `aria-label`. Live regions for dynamic content (saves, errors). `aria-expanded` on disclosure controls. No redundant or wrong ARIA roles.
> 5. **Color contrast** — Text vs background meets 4.5:1 (or 3:1 for large text / UI components). If the project has a design-language doc, check muted colors / quiet text against background tokens. State indicators (focus, hover, selected) distinguishable without color alone.
> 6. **Reduced motion** — Animations and transitions respect `prefers-reduced-motion: reduce`. Check stylesheets for media queries; absence is a finding for any new animation.
> 7. **Renderer accessibility** — Headings produce real heading tags. Images have alt text. Links describe their destination. Code blocks have a language label where useful.
> 8. **Zoom & responsive** — Layout holds at 200% browser zoom and at a narrow window (< 600px). No overflow that hides interactive elements.
> 9. **Form & input** — Inputs have associated `<label>` (visible or `aria-labelledby`). Placeholders are not labels. Error states are announced to AT, not just visually colored.
>
> **Output format**, grouped by severity:
> ```
> ## BLOCKER
> - <description> — `path:line` — WCAG criterion if applicable — suggested fix
>
> ## NIT
> - <description> — `path:line` — suggested fix
>
> ## FOLLOW-UP
> - <description> — why deferred — proposed owner/horizon
> ```
>
> Bar: WCAG 2.1 AA is the floor, not the ceiling. **Honesty over polish** — if a category has nothing of consequence, say so.

## 4. Triage and act

When invoked standalone (not via `/flow:ship`):

- **BLOCKER** — fix in workspace. Re-run typecheck via `flow.config.json.typecheckCmd` (loud-warning fallback if unset). Manually verify keyboard nav for the fix where applicable.
- **NIT** — fix if cheap.
- **FOLLOW-UP** — capture to `flow.config.json.{roadmapPath,planPath}` (defaults `dev-docs/*`; consumer projects typically `core-docs/*`). **Never only in the PR body.**

## 5. Report

Same convention as `/flow:security-review`: standalone → user; via `/flow:ship` → return findings.

## Gotchas

- **Contrast must include hover/focus states**, not just resting state. A muted resting color that becomes invisible on hover is still a finding.
- **Tab order follows DOM order**, not visual order. A grid-laid-out toolbar may tab in an unexpected sequence.
- **`prefers-reduced-motion` is not optional** — it's a user preference exposed by every modern OS. Any transition longer than ~150ms or any non-essential animation must check it.
- **Icon-only buttons need `aria-label`**, but the label should describe the **action**, not the icon ("Open menu", not "Three dots").
- **Reviewers can be confidently wrong.** Spot-check before fixing — especially contrast claims, which depend on the exact rendered color.
- **Don't add ARIA when semantic HTML works.** `<button>` beats `<div role="button" tabindex="0" onKeyDown=...>` every time.

## Config slots used

| Slot | Default | Used in |
|---|---|---|
| `flow.config.json.uiSurface` | `true` | Step 0 (skip-early gate) |
| `flow.config.json.defaultBranch` | `git symbolic-ref` → `main` | Step 1 (diff base) |
| `flow.config.json.typecheckCmd` | unset → loud warning | Step 4 (post-fix re-check) |
| `flow.config.json.designLanguagePath` | `dev-docs/design-language.md` | Project context (optional doc) |
| `flow.config.json.feedbackPath` | `dev-docs/feedback.md` | Project context |
| `flow.config.json.roadmapPath` | `dev-docs/roadmap.md` | Step 4 (FOLLOW-UP routing) |
| `flow.config.json.planPath` | `dev-docs/plan.md` | Step 4 (FOLLOW-UP routing) |
