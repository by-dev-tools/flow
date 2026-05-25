---
name: workflow-help
description: >
  Prints the canonical 11-step flow loop and the project's current
  flow.config.json slot values. Use when the user asks "what's the
  workflow?", "how does flow work?", "show me the loop", or when
  onboarding a new contributor to a flow-using project. Read-only;
  produces no file edits, no commits, no PR changes.
allowed-tools: Read, Bash
---

# Workflow help

Print the canonical 11-step loop and the current project's resolved flow.config.json slots so the user can see what the plugin is configured to do in this project.

## Project context (resolved at invocation)

- Project config: !`cat flow.config.json 2>/dev/null || echo "(no flow.config.json — flow uses built-in defaults for every slot)"`
- Default branch: !`git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@' || cat flow.config.json 2>/dev/null | jq -r '.defaultBranch // "main"' 2>/dev/null || echo "main"`
- Current branch: !`git branch --show-current 2>/dev/null || echo "(not in a git repo)"`

## What to print

Output exactly this, with the resolved slot values substituted from the project context above. Do not paraphrase; the wording is canonical.

---

# The flow workflow loop (11 steps, 2 human gates)

```
 1. Clarify          read source-of-truth docs; surface conflicts; ask 2–4
                     targeted questions (or list assumptions if autonomous)
 2. Plan             write plan with spec-walk checkboxes + confidence
                     verdict; run /flow:critique-plan; WAIT for human gate
 3. Execute          implement against checkboxes; stay in scope
 4. Preflight        mechanical gates (typecheck/build/test + invariants) —
                     MUST be green before /simplify runs
 5. Commit           "why" not "what"; co-author trailer; per-phase
 6. /simplify        (bundled with Claude Code) cold-read for reuse,
                     clarity, efficiency; fix in-tree; re-run preflight
 7. /flow:staff-review four lenses in parallel (engineer / UX / design-eng /
                     push-further); BLOCKER + cheap NIT in-tree;
                     FOLLOW-UP → roadmap/plan
 8. Present          reviewer notes + dev URL + branch state; flag MEDIUM-
                     confidence assumptions for user redirect
 9. Iterate          apply user feedback (sub-loop of 1–7)
10. /flow:ship       /flow:security-review + /flow:accessibility-review →
                     synthesize feedback → update docs → commit → push →
                     open PR
11. STOP             the user merges; Claude never does
```

**Two load-bearing human gates** (non-negotiable): Plan approval (step 2) and Merge (step 11). A third automatic gate fires on LOW-confidence assumptions in the plan.

**Mode flags** declared in the plan: `feature` (default, full loop), `spike` (skips /simplify + /flow:staff-review; uses /flow:ship-spike), `tiny` (1–3 line fix; skips spec-walk + confidence verdict + reviews; /flow:ship skips synthesis).

Long-form rationale with gate semantics, why-the-PR-opens-last, continuous-improvement loop, confidence-gate worked examples, and anti-patterns: `${CLAUDE_PLUGIN_ROOT}/docs/workflow.md`.

# This project's flow configuration

Below are the project's flow.config.json values (with built-in defaults shown for unset slots).

| Slot | This project | Built-in default | Used by |
|---|---|---|---|
| `defaultBranch` | _(see Project context above)_ | discovered via `git symbolic-ref` then literal `main` | `/flow:ship`, `/flow:ship-spike`, `/flow:staff-review` |
| `typecheckCmd` | _(see Project context)_ | unset → loud `⚠️` warning | `/flow:ship`, `/flow:ship-spike`, `/flow:staff-review` |
| `historyPath` | _(see Project context)_ | `dev-docs/history.md` | `/flow:ship`, `/flow:ship-spike` |
| `planPath` | _(see Project context)_ | `dev-docs/plan.md` | `/flow:ship`, `/flow:staff-review`, planner agent |
| `roadmapPath` | _(see Project context)_ | `dev-docs/roadmap.md` | `/flow:ship`, `/flow:staff-review` |
| `specPath` | _(see Project context)_ | `dev-docs/spec.md` | `/flow:ship`, `/flow:security-review`, planner agent |
| `feedbackPath` | _(see Project context)_ | `dev-docs/feedback.md` | `/flow:ship`, every reviewer (context) |
| `designLanguagePath` | _(see Project context)_ | `dev-docs/design-language.md` | `/flow:staff-review`, `/flow:accessibility-review` |
| `referenceGlob` | _(see Project context)_ | `core-docs/*.md` (or override per project) | `/flow:critique-plan` |
| `uiSurface` | _(see Project context)_ | `true` | `/flow:accessibility-review` (skip-early if false) |
| `reviewLenses` | _(see Project context)_ | `["staff-engineer","ux-designer","design-engineer","push-further"]` | `/flow:staff-review` |

To customize: edit `flow.config.json` at the project root. The schema lives at `${CLAUDE_PLUGIN_ROOT}/schema/flow.config.schema.json` for editor validation (point your IDE at it).

# Available flow skills (this plugin)

| Skill | Purpose |
|---|---|
| `/flow:critique-plan` | Critique a plan for scope drift / spec violation / internal incoherence |
| `/flow:audit-plan` | Audit a plan for unverified assumptions / unverified recall |
| `/flow:audit-completion` | Audit a completion claim for false-verification proxies |
| `/flow:log-disagreement` | (Auto-invoked) capture user pushback on a reviewer finding |
| `/flow:staff-review` | Four-lens parallel review (engineer / UX / design-eng / push-further) |
| `/flow:security-review` | Diff-focused security audit |
| `/flow:accessibility-review` | Diff-focused WCAG 2.1 AA audit (skip if `uiSurface: false`) |
| `/flow:ship` | Final-pass reviews → synthesize feedback → update docs → push → open PR |
| `/flow:ship-spike` | Lightweight ship pipeline for `mode: spike` PRs |
| `/flow:workflow-help` | (This skill) print the loop and project config |

# Bundled Claude Code native skills

Not provided by flow — invoke directly from Claude Code:
- `/simplify`
- `/batch`
- `/debug`
- `/loop`
- `/claude-api`

# Project-shaped surface (not in flow)

These belong in your project, not the plugin:
- `tools/preflight/check.mjs` — wired to your typecheck/build/test commands
- `.claude/rules/safety.md` — your project's safety-critical paths
- `.claude/rules/ui.md` — your project's design tokens + a11y baseline
- `.claude/skills/link/SKILL.md` — your dev-server starter (if you have one)

---

That's the loop. Plan first, ship last, never merge.
