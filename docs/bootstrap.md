# Bootstrap: adopting flow in a new project

This walks through adopting the [flow plugin](https://github.com/by-dev-tools/flow) in a fresh project — no prior `.claude/` content. For projects that already have `.claude/` skills/rules/agents, see [`docs/migration.md`](./migration.md) instead.

**Time estimate:** ~10 minutes per stack.

## What you get

After bootstrap, your project has:

- The flow plugin installed (`/flow:*` skills available in Claude Code sessions: `ship`, `staff-review`, `security-review`, `accessibility-review`, `ship-spike`, `workflow-help`, `audit-plan`, `audit-completion`, `critique-plan`, `log-disagreement`).
- A `flow.config.json` declaring your project's paths + commands + conventions.
- `core-docs/` with 5 scaffolded docs (spec, plan, roadmap, history, feedback).
- `.claude/` with project-shaped safety rule, opt-in hooks for sensitive-file blocking, and (for UI stacks) a `link` skill for the dev server.
- Per-stack preflight + CI + `.gitignore` additions.

---

## Step 1 — Install the flow plugin

In any Claude Code session (or your global `~/.claude/settings.json`):

```
/plugin marketplace add by-dev-tools/flow
/plugin install flow@flow
```

Verify with `/help` — you should see `/flow:workflow-help`, `/flow:ship`, `/flow:staff-review`, etc.

(For project-scope install instead of user-scope: add `"enabledPlugins": { "flow@flow": true }` to your project's `.claude/settings.json` after Step 3.)

## Step 2 — Copy `template/base/` to your project root

The base layer is stack-agnostic. **All `cp` invocations use `-n` (no-clobber)** so an accidental run in a project that already has `CLAUDE.md` / `README.md` / `.gitignore` will skip rather than overwrite. If you intentionally want to replace existing files, drop the `-n` per `cp`. For projects with significant pre-existing `.claude/` content, you want [`migration.md`](./migration.md), not this doc.

From a checkout of `by-dev-tools/flow` (or via `gh api` lookup):

```sh
PROJECT_ROOT=/path/to/your/project
FLOW=/path/to/flow-checkout    # or use gh api per-file

# Copy base scaffolding (renaming .template files as you go; -n preserves any existing file)
cp -n $FLOW/template/base/CLAUDE.md.template          $PROJECT_ROOT/CLAUDE.md
cp -n $FLOW/template/base/README.md.template          $PROJECT_ROOT/README.md
cp -n $FLOW/template/base/flow.config.json.example    $PROJECT_ROOT/flow.config.json
cp -n $FLOW/template/base/.gitignore.template         $PROJECT_ROOT/.gitignore
mkdir -p $PROJECT_ROOT/.claude/rules
cp -n $FLOW/template/base/.claude/settings.json.example $PROJECT_ROOT/.claude/settings.json
cp -n $FLOW/template/base/.claude/rules/safety.md.template $PROJECT_ROOT/.claude/rules/safety.md
mkdir -p $PROJECT_ROOT/core-docs
cp -n $FLOW/template/base/core-docs/*.md $PROJECT_ROOT/core-docs/
```

If you don't have a flow checkout, fetch each file via `gh api repos/by-dev-tools/flow/contents/template/base/<path> --header "Accept: application/vnd.github.raw" > $PROJECT_ROOT/<dest>`.

## Step 3 — Overlay your stack

Pick one of `web`, `swift`, `tauri-rust-ts` (or a hybrid — see "Hybrid stacks" below).

### Web (Vite + React/Vue/Svelte + TypeScript)

```sh
mkdir -p $PROJECT_ROOT/.claude $PROJECT_ROOT/tools $PROJECT_ROOT/.github
cp -Rn $FLOW/template/stacks/web/.claude/.      $PROJECT_ROOT/.claude/
cp -Rn $FLOW/template/stacks/web/tools/.        $PROJECT_ROOT/tools/
cp -Rn $FLOW/template/stacks/web/.github/.      $PROJECT_ROOT/.github/
cat    $FLOW/template/stacks/web/.gitignore.append >> $PROJECT_ROOT/.gitignore
```

### Swift (Xcode-based macOS / iOS / multi-platform)

```sh
mkdir -p $PROJECT_ROOT/tools/preflight $PROJECT_ROOT/.github
cp -n $FLOW/template/stacks/swift/tools/preflight/check.sh $PROJECT_ROOT/tools/preflight/check.sh
chmod +x $PROJECT_ROOT/tools/preflight/check.sh
cat   $FLOW/template/stacks/swift/.claude/rules/safety.md.append >> $PROJECT_ROOT/.claude/rules/safety.md
cp -Rn $FLOW/template/stacks/swift/.github/.    $PROJECT_ROOT/.github/
cat   $FLOW/template/stacks/swift/.gitignore.append >> $PROJECT_ROOT/.gitignore
```

### Tauri (Vite frontend + Rust backend + TypeScript)

```sh
mkdir -p $PROJECT_ROOT/.claude $PROJECT_ROOT/tools $PROJECT_ROOT/.github
cp -Rn $FLOW/template/stacks/tauri-rust-ts/.claude/.  $PROJECT_ROOT/.claude/
cp -Rn $FLOW/template/stacks/tauri-rust-ts/tools/.    $PROJECT_ROOT/tools/
cp -Rn $FLOW/template/stacks/tauri-rust-ts/.github/.  $PROJECT_ROOT/.github/
cat    $FLOW/template/stacks/tauri-rust-ts/.gitignore.append >> $PROJECT_ROOT/.gitignore
```

### Hybrid stacks

If your project is a monorepo (web + swift), copy from both overlays. Resolve `.claude/rules/ui.md` collisions in favor of the web version (Tauri's UI rules append a section to the web version; you can layer manually).

## Step 4 — Fill in the placeholders

Open `CLAUDE.md`, `README.md`, `flow.config.json`, `.claude/rules/safety.md` and replace every `{{PLACEHOLDER}}`:

| Placeholder | Example |
|---|---|
| `{{PROJECT_NAME}}` | `acme-app` |
| `{{ONE_LINE_DESCRIPTION}}` | `Local-first markdown notes with repo sync.` |
| `{{STACK}}` | `TypeScript + React + Vite, Vitest tests, Vercel deploy` |
| `{{LIFECYCLE_STATUS}}` | `pre-alpha` / `beta` / `production` |
| `{{SAFETY_PATH_1}}`, `{{SAFETY_PATH_2}}`, ... | One YAML list item per glob in `.claude/rules/safety.md` — add/remove as needed. Example items: `"src/lib/persistence.ts"`, `"tools/migrate/*.mjs"`. |
| `{{INSTALL_STEPS}}` | `npm install && npm run dev` |

In `flow.config.json`: remove the `$comment-*` keys (they're docs for the bootstrap reader) and verify each slot value matches your project's reality:
- `typecheckCmd` matches your `package.json` `scripts.typecheck` (or `tsc --noEmit` if no script). **Trust model:** this slot is shell-executed by `/flow:ship` and `/flow:staff-review` (via `sh -c`), at the same trust level as `package.json` `scripts` or pre-commit hooks. Treat your committed `flow.config.json` with the same care.
- `defaultBranch` matches your repo's primary branch.
- Doc paths point to where you actually put `core-docs/`.
- `uiSurface: false` if your project has no UI (set explicitly so `/flow:accessibility-review` skips early).

In `.claude/rules/safety.md`: update the `paths:` frontmatter to match your project's actual safety-critical paths, and replace the commented-out example list with your real surfaces.

## Step 5 — Verify

In your project root:

```sh
# Validate config + manifest
jq -e . flow.config.json && echo "flow.config.json: valid JSON"
jq -e . .claude/settings.json && echo ".claude/settings.json: valid JSON"

# Verify plugin sees the project
claude --print "/flow:workflow-help" | head -20
```

The `/flow:workflow-help` output should show your `flow.config.json` slot values (resolved). If a slot prints `(default)` instead of your value, the slot isn't being read — re-check `flow.config.json` for typos.

## Step 6 — Try one PR

Smallest viable change: a typo fix in `core-docs/spec.md`.

```sh
git checkout -b bootstrap-smoke-test
# Make any small edit, e.g. `echo "" >> core-docs/spec.md`
git add core-docs/spec.md
git commit -m "Bootstrap smoke test"
```

In a Claude Code session: invoke `/flow:ship`. The pipeline runs (security + a11y skipped for doc-only; memory machinery probably no-ops since you have no prior entries), writes a history entry, opens a PR. Verify the PR opened against your `defaultBranch`. Close the PR — it's a smoke test, not real work.

If anything fails: check the `/flow:ship` output for `⚠️` warnings and resolve them in `flow.config.json`.

## What's next

- Read `${CLAUDE_PLUGIN_ROOT}/docs/workflow.md` for the full 11-step loop.
- Fill in your `core-docs/spec.md` with your actual product vision + feature table.
- Start your first real PR with `/flow:critique-plan` on the plan, then execute against the spec-walk checkboxes.

## Troubleshooting

- **`/flow:*` skills missing from `/help`.** Check `~/.claude/settings.json` `enabledPlugins` has `"flow@flow": true`. Run `/plugin marketplace update flow && /plugin install flow@flow`.
- **`flow.config.json` slot values not visible in `/flow:workflow-help`.** JSON parse error somewhere. Run `jq -e . flow.config.json` — if it errors, the slot reads in skill bodies will silently fall back to defaults.
- **Preflight fails on a stack-specific gate** (e.g. `cargo` not installed for tauri overlay). The preflight runner skips with a loud warning, exit code 0. Install the missing tool, then re-run.
- **`/flow:staff-review` produces empty findings.** That's valid (push-further lens explicitly preserves "Nothing to push" output). If multiple lenses produce nothing on a non-trivial diff, the lens prompts may need tuning for your project's idioms — file a feedback entry.

Open issues + improvements: https://github.com/by-dev-tools/flow/issues
