# Migration: adopting flow in an existing project

This walks through adopting the [flow plugin](https://github.com/by-dev-tools/flow) in a project that **already has `.claude/` content** — local workflow skills, project rules, custom agents. The pattern: install flow alongside (non-breaking), validate end-to-end on a real PR, then delete the now-redundant local copies. Across 3 PRs.

The reference case is `by-dev-tools/md-manager`, which carried the canonical implementation of the loop before flow extracted it. md-manager's migration is staged across PRs 4, 5, 6 of the flow extraction umbrella (sequenced after flow PR 3 — the PR that ships this doc).

For projects with NO prior `.claude/` content, see [`docs/bootstrap.md`](./bootstrap.md) instead.

---

## The pattern: 3 PRs, gated by validation

```
Stage 1 (install non-breaking) ──> Stage 1.5 (dogfood validation) ──> Stage 2 (delete duplicates)
                                       │
                                       │ MUST ship clean
                                       │ before deletion
                                       │
                                       └──► If blockers: fix in flow upstream, redo Stage 1.5
```

This is intentionally slower than a one-shot migration. The reason: parity is uncertain. Your local `/staff-review` may have project-specific behaviors flow doesn't yet — finding out at deletion time means losing work. Stage 1.5's dogfood gate exposes those gaps cheaply.

---

## Stage 1 — Install non-breaking (one PR)

**Goal:** flow installed alongside existing local skills. Both work simultaneously. Zero deletions.

### Scope (in)

- Install flow plugin (project-scope recommended for the migration window so other projects don't see flow before you've validated it). Edit `.claude/settings.json` — merge the `enabledPlugins` key in (Claude Code's settings.json is strict JSON, no comments):

  ```json
  {
    "enabledPlugins": {
      "flow@flow": true
    }
  }
  ```

  (If your `.claude/settings.json` already has `enabledPlugins`, add `"flow@flow": true` as a sibling key — don't replace the whole object.)

  Plus, if not already done at user-scope: `/plugin marketplace add by-dev-tools/flow && /plugin install flow@flow`.

  **Verify the install actually took** (two checks, both must pass — silent failure on either is a real consumer footgun per `dev-docs/feedback.md` FB-0005):

  ```
  /plugin marketplace list | grep -E '^flow($|[[:space:]])'   # must return a line — word-anchored so a sibling marketplace doesn't false-positive
  /help | grep -E '/flow:(ship|staff-review|workflow-help)'   # must return matches
  ```

  If `/plugin marketplace list | grep '^flow'` is empty, the marketplace registered under a different key (most common cause: stale-keyed `extraKnownMarketplaces.<old-name>` entry from before a rename — flow renamed from `llm-auditor`/`assumption-auditor` to `flow`/`flow` during PR 1, so any pre-rename install of the assumption-auditor plugin can leave this drift). Re-run `/plugin marketplace add by-dev-tools/flow` to register under the correct name; the stale entry is harmless once the canonical entry exists.

- Add `flow.config.json` at repo root declaring your project's slot values. Use `template/base/flow.config.json.example` as a starting point but tailor to your reality:

  ```json
  {
    "defaultBranch": "main",
    "typecheckCmd": "npm run typecheck",
    "historyPath": "core-docs/history.md",
    "planPath": "core-docs/plan.md",
    "roadmapPath": "core-docs/roadmap.md",
    "specPath": "core-docs/spec.md",
    "feedbackPath": "core-docs/feedback.md",
    "designLanguagePath": "core-docs/design-language.md",
    "referenceGlob": "core-docs/*.md",
    "uiSurface": true,
    "reviewLenses": ["staff-engineer", "ux-designer", "design-engineer", "push-further"],
    "memoryHardCap": 30,
    "branchPrefix": "claude/"
  }
  ```

- Add a short section to your `CLAUDE.md` referencing the plugin:

  > **Flow plugin (in-migration):** This project is migrating to the flow plugin for its workflow. Both local skills (`/staff-review`, `/security-review`, etc.) and plugin skills (`/flow:staff-review`, `/flow:security-review`, etc.) currently work. Local skills will be removed after Stage 1.5's dogfood validation lands. Authoritative loop reference: `${CLAUDE_PLUGIN_ROOT}/docs/workflow.md`.

- **Zero deletions of existing `.claude/` content.** Belt and suspenders.

### Verify coexistence

In a fresh `claude` session in your project:

```
/help | head -40
```

You should see BOTH `/staff-review` (your local) AND `/flow:staff-review` (plugin). Plugins are auto-namespaced — no conflict by design.

### Smoke test

Invoke `/flow:staff-review` on this PR's own diff (the install + config + CLAUDE.md edit). All 4 lenses should spawn; output should match the documented BLOCKER/NIT/FOLLOW-UP/EXPLORATION shape. Any rough edges: capture in **flow's** `dev-docs/feedback.md` via a follow-up PR in flow's repo — NOT in your project's feedback.md (plugin feedback belongs to plugin's dev-tracking).

Open the Stage 1 PR against `main`. Don't merge — let the user merge.

---

## Stage 1.5 — Dogfood validation (one PR, the load-bearing gate)

**Goal:** ship a real, small, user-facing change using ONLY `/flow:*` skills (+ bundled Claude Code natives: `/simplify`, `/batch`, etc.). NO invocation of local `/staff-review`, `/security-review`, `/ship`, `/ship-spike`, `/accessibility-review`. This is the validation that the plugin matches your project's actual needs.

### Scope (in)

- Pick a change from your `core-docs/roadmap.md` (Now or Next) or `core-docs/plan.md` (Backlog). Constraints:
  - Small: 1–3 files, < 100 LOC delta.
  - Real: actual product improvement, not contrived.
  - Touches code (not just docs) so all 4 lenses have something to engage with.
  - NOT safety-critical.

- Run the full 11-step loop using plugin skills only:
  1. Clarify — read `core-docs/*` per usual.
  2. Plan — write into `core-docs/plan.md`. Run `/flow:critique-plan`. User approves.
  3. Execute.
  4. Preflight — your project's own (project-specific by definition).
  5. Commit.
  6. `/simplify` — bundled native.
  7. `/flow:staff-review` — all 4 lenses must spawn + produce findings + triage.
  8. Present.
  9. Iterate.
  10. `/flow:ship` — runs `/flow:security-review` + `/flow:accessibility-review`, synthesizes feedback into both layers (user FB-XXXX in `core-docs/feedback.md` AND agent memory at `~/.claude/projects/<canonical>/memory/feedback_*.md`), updates `core-docs/*.md`, commits, pushes, opens PR.
  11. STOP.

- **Capture every rough edge** in flow's `dev-docs/feedback.md` via a follow-up flow PR. This is the load-bearing output.

- **Do NOT fix flow bugs as part of Stage 1.5.** Fixes happen as follow-up PRs in flow, not bundled here. Stage 1.5 is a clean test surface.

### Scope (out)

- No local-skill invocation (defeats the purpose).
- No flow bug fixes bundled.
- No expansion of the chosen change.

### Validation gate

If Stage 1.5 surfaces:
- **Zero blockers + minor friction only:** sign off in your project's plan ("Stage 1.5 validated; ready for Stage 2"), proceed to Stage 2.
- **Blockers OR substantial friction (>5 entries):** PAUSE. Address the flow bugs in separate flow PRs. Re-run Stage 1.5 on a second small change once flow's fixes ship. Do NOT proceed to Stage 2 until parity is real.

The dogfood gate is the load-bearing checkpoint in this migration. Skipping it risks discovering parity gaps at deletion time, when recovery is more expensive.

---

## Stage 2 — Delete local duplicates + retire migration (one PR, breaking)

**Goal:** Delete every file flow now provides redundantly. Your project becomes a pure consumer of the plugin: `.claude/` carries only project-shaped files (safety paths, UI tokens, dev-server skill).

### Delete

```sh
# Workflow skills now provided by flow
rm -rf .claude/skills/staff-review/
rm -rf .claude/skills/security-review/
rm -rf .claude/skills/accessibility-review/
rm -rf .claude/skills/ship/
rm -rf .claude/skills/ship-spike/

# Context-isolation agents now provided by flow
rm .claude/agents/planner.md
rm .claude/agents/docs.md

# Portable rules now provided by flow
rm .claude/rules/general.md
rm .claude/rules/plan-discipline.md
rm .claude/rules/documentation.md
rm .claude/rules/exploration.md

# Memory tool now provided by flow (delete only the plugin-provided files; preserve any project-shaped tools/memory/ content)
rm -f tools/memory/check.mjs tools/memory/.gitignore
rmdir tools/memory 2>/dev/null || true   # leaves the dir if it has other project files
```

Adjust the deletion list per what your project actually has. `/simplify` is bundled Claude Code native — your project never had a local `simplify` skill to delete.

### Keep

These are project-shaped — flow does NOT provide them:

```sh
# Project safety paths, UI tokens, dev-server skill — keep
.claude/rules/safety.md       # your project's safety-critical paths
.claude/rules/ui.md           # your project's design tokens + a11y rules
.claude/rules/dev-server.md   # your project's dev URL surfacing rule
.claude/skills/link/          # your project's dev server (port + command)

# Anything else project-specific
.claude/skills/<your-project-skills>/

# Core docs — always keep
core-docs/

# Project-specific preflight + invariants
tools/preflight/check.{mjs,sh}     # if you have one
tools/invariants/check.mjs         # if you have one
```

### Update `CLAUDE.md`

Remove the now-redundant references to deleted local skills. Strengthen the "Flow plugin" section:

> **This project is a pure consumer of the flow plugin.** Workflow questions, skill questions, generic rule questions → flow (`${CLAUDE_PLUGIN_ROOT}/docs/workflow.md`). Project-specific safety paths / UI tokens / dev-server start command stay here.

### Update `core-docs/workflow.md` (if you have one)

Three options:
- **Option A: delete.** Point CLAUDE.md at `${CLAUDE_PLUGIN_ROOT}/docs/workflow.md` directly.
- **Option B: thin overlay.** Keep ~20-30 lines describing only the bits your project layers on top of the canonical loop (preflight gate list, design-language coupling, project-specific rules). Pointer at the plugin's workflow.md for the canonical content.
- **Option C: keep as-is.** Only if your project has substantial workflow-doc content the plugin doesn't cover. Likely a sign you should be contributing back to flow.

Decide at PR-C plan time. Recommended default: Option B for projects with established workflow; Option A for fresh adopters.

### Verify

```sh
# No local workflow skills left
find .claude/skills -maxdepth 1 -type d
# Should list only project-specific skills (link, etc.), NOT staff-review/security-review/etc.

# No portable rules left
ls .claude/rules
# Should list only safety.md, ui.md, dev-server.md (project-shaped).

# No context-isolation agents
ls .claude/agents
# Should be empty (or only project-specific agents).

# Full plugin loop works on the Stage 2 PR itself
/flow:critique-plan   # on the Stage 2 PR's plan
/flow:staff-review    # on the Stage 2 PR's diff
/flow:ship            # to close out
```

### Retire migration tracking

In `core-docs/plan.md`: move any "Flow migration" Active Work Item to Recently Completed → eventually to `history.md`. From this point forward, plugin-related work happens in `by-dev-tools/flow/dev-docs/`, not in your project.

---

## Troubleshooting

- **Plugin skill missing a behavior your local skill had.** Don't restore the local skill. File a flow follow-up PR. Workarounds in your project belong in `.claude/rules/<project-rule>.md` if they're rules, or `.claude/skills/<project-skill>/` if they're project-specific orchestration.
- **`/flow:ship` writes docs to the wrong path.** Your `flow.config.json` slot values aren't being read. Run `claude --print "/flow:workflow-help"` — resolved slot values should match your `flow.config.json`. If not: JSON parse error.
- **Memory entries written to the wrong project.** The plugin's `tools/memory/check.mjs` derives the canonical project path from the harness; for worktrees / Conductor workspaces, slug scoring is in play. Verify entries land at `~/.claude/projects/<your-project-canonical-slug>/memory/`. If a foreign slug wins, file a flow follow-up (this is the path-derivation cross-scope question PR 4-6 are designed to surface).
- **Stage 1.5 surfaced 5+ rough edges.** That's the gate working. Don't proceed to Stage 2. Open a flow PR with the entries, get it merged, re-run Stage 1.5 on a second small change.

Open issues + improvements: https://github.com/by-dev-tools/flow/issues
