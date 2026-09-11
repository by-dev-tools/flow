# Changelog

All notable changes to flow are recorded here.

This is the **consumer-facing changelog** — read this before upgrading. For per-PR design decisions + tradeoffs, see [`dev-docs/history/`](../dev-docs/history/) (verbose, internal-tracking).

## One file per release

**Every release is its own file: `vX.Y.Z.md`.** There is no rollup and no index file, deliberately — either would recreate the merge conflict this structure exists to remove. `ls changelog/` **is** the index.

Plain `ls` sorts lexically, which puts `v1.10.0` before `v1.9.0`. **Use `ls -v changelog/`** (version sort) or read the `## vX.Y.Z` heading inside each file. Read everything with `cat changelog/v*.md`.

Format: each entry has a date, version, headline, 2-4 bullets, and an explicit "Breaking changes:" callout.

To upgrade: see [`../docs/upgrade.md`](../docs/upgrade.md).

## Notes on versioning

- Flow follows **semver as a discipline, not a contract**. Patch bumps (`1.2.x`) aim to be additive; minor bumps (`1.y.0`) add user-visible surface; major bumps (`x.0.0`) are reserved for breaking changes (none have happened). The discipline is enforced by `lens-staff-engineer` review + `/flow:doctor` Check 2.5 + author care — there is no mechanical gate today that BLOCKS a breaking change from landing in a patch bump. Always verify upgrades with `/flow:doctor`; treat any patch-level regression as a bug worth filing.
- The plugin manifest version (`plugins/flow/.claude-plugin/plugin.json`) and marketplace metadata version (`.claude-plugin/marketplace.json`) are kept in sync.
- **Docs-only changes at the repo root** (e.g., this changelog itself, `docs/upgrade.md`) ship without a version bump — they don't change plugin behavior and consumers fetch them from GitHub directly, not via `/plugin install`.
