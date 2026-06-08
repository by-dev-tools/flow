# Upgrading flow

How to pick up new flow versions in a project where flow is already installed.

**Per-version what-changed:** [`CHANGELOG.md`](../CHANGELOG.md) at repo root.

## TL;DR — keep flow current automatically

The simplest path is **auto-update**: set it once and flow updates itself at each session start — no commands, no reinstall, ever.

```jsonc
// ~/.claude/settings.json — on your flow marketplace entry
{
  "extraKnownMarketplaces": {
    "flow": {
      "source": { "source": "github", "repo": "by-dev-tools/flow" },
      "autoUpdate": true          // ← refreshes the catalog AND updates the installed plugin, at session start
    }
  }
}
```

Prefer to update manually? **One command:**

```sh
/plugin marketplace update flow      # refreshes the catalog AND updates the installed plugin
/flow:doctor                         # optional: verify the upgrade landed
```

## One command, not two

`/plugin marketplace update flow` is **not** catalog-only — it bumps the installed plugin to the latest version in the same step (per current Claude Code: `code.claude.com` discover-plugins + plugin-marketplaces docs). You do **not** need a separate `/plugin install flow@flow` afterward. `autoUpdate: true` performs exactly this — catalog refresh + installed-version bump — automatically at each session start.

**The one caveat:** auto-update fires at **session start**, not continuously. If a new flow version ships while you're mid-session, run `/plugin marketplace update flow` to pull it immediately; otherwise you pick it up next session.

## When to run it

**TL;DR cadence:** run when you want a specific new feature, OR weekly-ish as hygiene. Patch bumps (`1.2.x → 1.2.y`) are additive — your existing install keeps working between checks. Don't run mid-session, and don't run "just to be safe" before every task. (Or skip the manual ritual entirely by setting `autoUpdate: true` — see the Auto-update section below.)

| Trigger | Action |
|---|---|
| **Major bump (`x.0.0`)** — e.g., `1.x → 2.0` | **Run before next session.** Read `CHANGELOG.md`'s "Breaking changes:" block first. |
| **Minor bump (`1.x.0`)** — new user-visible skills/surface | **Run before next session** in projects where you'll use the new surface. |
| **Patch bump (`1.2.x → 1.2.y`)** | **Optional.** Batch them — flow's discipline is additive at patch level. Run when CHANGELOG mentions something you want, OR weekly as hygiene. |
| **`/flow:doctor` reports `[FAIL]`/`[WARN]` you don't recognize** | Run — your installed plugin may be older than your `flow.config.json` expects. |
| **A skill named in flow's docs isn't in `/help`** | Run — the skill exists in a newer version. |
| **Mid-session** | Skip — plugins don't pick up changes mid-session anyway. |
| **"Just to be safe"** | Skip — read CHANGELOG instead. The ritual without a specific reason is sub-30s of friction with no upgrade. |

Practical heuristic for an active flow contributor (dogfooding flow on your own consumer projects): at the start of any non-trivial new feature, run `git log -5 origin/main` on the flow repo. If anything looks relevant, run the ritual. Otherwise carry on.

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
      "source": { "source": "github", "repo": "by-dev-tools/flow" },
      "autoUpdate": true        // ← opt-in
    }
  }
}
```

**Tradeoff:** auto-update means you'll silently pick up new versions without reading the CHANGELOG. For patch bumps (`1.2.x → 1.2.y`), flow aims to be additive-only — typically safe. For minor + major bumps, you may want to read CHANGELOG first. **Principle:** when a major bump ships (any `x.0.0`), default to auto-update off until you've read the major-bump CHANGELOG; flip back on after you've understood the breaking changes. The discipline (patch = additive, minor = additive user-visible surface, major = breaking changes) is enforced by author care + `lens-staff-engineer` + `/flow:doctor` Check 2.5 — it's not a hard guarantee, so verify each upgrade with `/flow:doctor` regardless of cadence.

## Multi-project: once per machine (for user-scope installs)

If flow is installed at **user-scope** (the default — `~/.claude/settings.json`'s `enabledPlugins` has `"flow@flow": true`), the marketplace catalog cache and the installed plugin both live at user-scope. **Run the ritual once on the machine and all your projects pick up the new version.** You don't need to repeat per-project.

Quick check that you're user-scope:

```sh
# jq version (clean output):
jq '.enabledPlugins' ~/.claude/settings.json 2>/dev/null \
  || echo "(no user-scope settings.json — flow may be project-scope-only or not installed)"

# Fallback if jq isn't installed:
grep -A 3 enabledPlugins ~/.claude/settings.json 2>/dev/null \
  || echo "(no user-scope settings.json — flow may be project-scope-only or not installed)"
```

If `"flow@flow": true` appears in the user-scope output, you're user-scope. If not, check `.claude/settings.json` inside your project. The presence of the entry — not its scope per se — is what tells you where the install lives.

If you've installed flow at **project-scope** (custom workflow — `.claude/settings.json` inside a specific project enables flow), each project's install is independent. Run the ritual in each project where you've enabled it. Most consumers don't set this up; the default of user-scope handles multi-project for free.

**Note:** `/plugin marketplace update flow` refreshes the catalog **and** bumps the installed plugin in the same step — it is not catalog-only (per current Claude Code docs). One command per project picks up the new version; no separate `/plugin install` is required. (A fresh first-time install still uses `/plugin install flow@flow` — that's installation, not updating.)

## What's NOT in this doc

- **How to install flow for the first time** — see [`docs/bootstrap.md`](bootstrap.md).
- **How to migrate an existing project to flow** — see [`docs/migration.md`](migration.md).
- **What's new in each version** — see [`CHANGELOG.md`](../CHANGELOG.md).
- **How the workflow loop works** — see [`plugins/flow/docs/workflow.md`](../plugins/flow/docs/workflow.md) or run `/flow:workflow-help`.
- **How to extend or modify flow** — see [`dev-docs/`](../dev-docs/) (plugin's own development tracking).
