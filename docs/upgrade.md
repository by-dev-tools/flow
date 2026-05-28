# Upgrading flow

How to pick up new flow versions in a project where flow is already installed.

**Per-version what-changed:** [`CHANGELOG.md`](../CHANGELOG.md) at repo root.

## TL;DR — the 2-command ritual

```sh
# In a Claude Code session in your project root:
/plugin marketplace update flow      # Refresh the marketplace catalog
/plugin install flow@flow            # Pick up the new version
/flow:doctor                         # Verify the upgrade landed
```

Run this after any flow PR merges to main, or weekly, or before starting non-trivial work — whichever fits your habit. Both commands are idempotent; running them when there's nothing to update is a no-op.

## Why two commands

`/plugin install flow@flow` reads from the marketplace catalog **cached locally**. Without `/plugin marketplace update flow` first, the install command sees the stale catalog and reports "already installed" even when a newer version exists upstream. Re-running `install` alone is the most common silent-failure mode for flow upgrades.

A future Claude Code release may collapse these into a single `/plugin upgrade` command; until then, the two-step ritual is the canonical path.

## When to run it

| Trigger | Recommended action |
|---|---|
| **You merged a flow PR** (you're the maintainer) | Run the ritual in every consumer project before next session. Don't trust memory across two projects. |
| **You see a new version mentioned in CHANGELOG.md, dev-docs/history.md, or a flow PR description** | Run the ritual. |
| **`/flow:doctor` reports `[FAIL]` checks you don't recognize** | Run the ritual — your installed plugin may be older than your `flow.config.json` expects. |
| **A new skill is referenced in docs but not in `/help`** | Run the ritual — the skill exists in the new version but your install is behind. |
| **Nothing has changed but you want to be sure** | Run the ritual — it's idempotent and takes <30 seconds. |

## Verification

After running the ritual, **always** run `/flow:doctor`. The final-line verdict tells you whether the upgrade is healthy:

- `[READY] flow is correctly set up; all checks pass.` — you're done.
- `[READY with WARN-level items] flow is functional; N optional items can be addressed at your discretion.` — read the WARN lines; usually optional polish (e.g., `typecheckCmd` unset).
- `[NOT READY] N FAIL(s) block flow from working correctly.` — read each FAIL's "Fix:" line. If `Section 1 (install)` failed, the marketplace registration broke; try the troubleshooting steps below.

Per the FB-0010 consistency discipline, Check 2.5 (slot count vs schema source-of-truth) is the first sentinel for "your installed plugin and your project docs disagree." A `[WARN]` there usually means an upgrade you didn't realize you needed.

## Troubleshooting

### `/plugin marketplace update flow` errors with "marketplace not found"

The marketplace key in your `~/.claude/settings.json` doesn't match the name flow registers (`flow`). Common cause: a leftover `extraKnownMarketplaces.llm-auditor` key from before flow's 2026-05-23 rename, or a custom key from a previous experiment.

Fix:

```sh
/plugin marketplace add by-dev-tools/flow
```

This re-registers under the canonical `flow` name regardless of any stale keys.

### `/help` doesn't list the new skill after upgrade

Two possibilities:

1. **You skipped `/plugin marketplace update flow`** — the install command sees the cached catalog and reports "already installed." Re-run both commands.
2. **The plugin is enabled under a different marketplace name in `~/.claude/settings.json`.** Check `enabledPlugins`:

   ```sh
   # jq version (clean output):
   jq '.enabledPlugins' ~/.claude/settings.json 2>/dev/null \
     || echo "(no settings.json yet — run /plugin install flow@flow first, OR install jq via 'brew install jq')"

   # Fallback if jq isn't installed:
   grep -A 3 enabledPlugins ~/.claude/settings.json 2>/dev/null \
     || echo "(no settings.json at ~/.claude/settings.json)"
   ```

   The key must be `"flow@flow": true`. If it's `"flow@llm-auditor"` or anything else, fix it:

   ```sh
   # In a Claude Code session:
   /plugin install flow@flow
   ```

   This overwrites the enabled-plugins entry with the canonical name.

### `/flow:doctor` Section 1 reports `[FAIL]` after upgrade

`Check 1.1` (marketplace registered) or `Check 1.2` (plugin enabled) failed. The fix-it hints in the FAIL lines name the recovery command. If both fail, re-do the install from scratch:

```sh
/plugin marketplace remove flow
/plugin marketplace add by-dev-tools/flow
/plugin install flow@flow
/flow:doctor
```

### Upgrade brought a breaking change you didn't expect

Flow follows semver. Major bumps (`x.0.0`) are reserved for breaking changes and are called out in CHANGELOG.md with an explicit "Breaking changes:" block. Minor bumps (`1.y.0`) add user-visible surface. Patch bumps (`1.2.x`) follow flow's discipline of additive-only changes — but verify each upgrade with `/flow:doctor` regardless; the discipline is enforced by lens-staff-engineer + Check 2.5 + author care, not by tooling.

If a patch upgrade DOES break something, **that's a bug, not a feature**. File an issue at https://github.com/by-dev-tools/flow/issues with:
- The version you upgraded from + to (read from CHANGELOG.md headers).
- The `/flow:doctor` output (full).
- The first command that misbehaved.

**Version pinning is not yet supported.** Flow does not currently tag releases at the git-tag level, so `git checkout v1.2.3` won't work. If you need to roll back, the practical path today is: revert the consumer's `/plugin install flow@flow` action by removing flow from `enabledPlugins` in `~/.claude/settings.json` and re-installing after the fix ships. Tracked as a FOLLOW-UP in flow's `dev-docs/plan.md` (release tagging + version-pinning recipe).

## Auto-update (opt-in)

By default, third-party Claude Code marketplaces require manual `/plugin marketplace update` to pick up new versions. If you'd rather let flow auto-update at session start, set:

```jsonc
// ~/.claude/settings.json
{
  "extraKnownMarketplaces": {
    "flow": {
      "url": "https://github.com/by-dev-tools/flow",
      "autoUpdate": true        // ← opt-in
    }
  }
}
```

**Tradeoff:** auto-update means you'll silently pick up new versions without reading the CHANGELOG. For a patch bump (`1.2.x → 1.2.y`) this is usually fine — flow's discipline is additive-only at patch level. For minor + major bumps, you may prefer to read CHANGELOG first. Leave auto-update off if you want explicit control.

## Multi-project ritual

If you run flow across multiple projects (e.g., md-manager + health-tracker), the ritual must run **in each project's Claude Code session** — `/plugin marketplace update` updates the local catalog cache, which is per-session. A single update from one project doesn't propagate to others.

Practical pattern: after merging a flow PR, open a session in each consumer project and run the ritual. Or set `"autoUpdate": true` and accept the silent-upgrade tradeoff.

If you have flow installed **per-project** rather than user-scope (a custom workflow), the ritual is identical but the update is scoped to whichever project you run it in. Same `marketplace update` + `install` commands; just no cross-project propagation.

## What's NOT in this doc

- **How to install flow for the first time** — see [`docs/bootstrap.md`](bootstrap.md).
- **How to migrate an existing project to flow** — see [`docs/migration.md`](migration.md).
- **What's new in each version** — see [`CHANGELOG.md`](../CHANGELOG.md).
- **How the workflow loop works** — see [`plugins/flow/docs/workflow.md`](../plugins/flow/docs/workflow.md) or run `/flow:workflow-help`.
- **How to extend or modify flow** — see [`dev-docs/`](../dev-docs/) (plugin's own development tracking).
