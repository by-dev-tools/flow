### PR H1 — Upgrade docs + CHANGELOG (pre-install shore-up, docs-only at repo root, no version bump)
**Date:** 2026-05-27
**Branch:** `pr-h1/upgrade-docs-changelog`
**Commit:** [SHA at ship time]

**What was done:**
Shipped two cheap fixes from the Tier-2 audit of flow's update infrastructure, before user begins active dogfood across two consumer projects (md-manager + health-tracker):

1. **`docs/upgrade.md` (new)** — the 2-command ritual (`/plugin marketplace update flow` → `/plugin install flow@flow` → `/flow:doctor`), when-to-run guidance, verification via doctor's final-line verdict, 4 troubleshooting cases (marketplace-not-found, missing skills in /help, doctor Section 1 FAIL, unexpected breaking change), optional auto-update opt-in with tradeoff callout, multi-project ritual section.
2. **`CHANGELOG.md` (new, at repo root)** — extracted v1.0.0 through v1.2.3 from the inline README "Versions:" block + history.md entries. Reverse chronological; date + headline + 2-4 bullets + explicit "Breaking changes:" callout per entry. v1.0.0 is the only entry with a real breaking change (install identity changed from `assumption-auditor@llm-auditor` to `flow@flow`). Keep-a-Changelog-style — distinct from history.md format (no SHA/branch/tradeoffs; intentionally terse).
3. **`README.md`** — replaced 6-line inline "Versions:" block with a single line linking to CHANGELOG.md + a separate line linking to docs/upgrade.md. Also added upgrade.md to the "Full bootstrap docs" rail under the Quick Start.
4. **`docs/bootstrap.md`** — appended "When a new flow version ships, pick it up via the 2-command ritual in docs/upgrade.md" to the "What's next" section.
5. **`docs/migration.md`** — appended a "Keeping flow up to date" subsection pointing at upgrade.md.

**No version bump.** Pure docs-at-root changes; `docs/` and `CHANGELOG.md` are not included in the plugin install package (`/plugin install flow@flow` ships only `plugins/flow/*`). Consumers fetch the new docs from GitHub directly. Spares a no-op `/plugin marketplace update` cycle.

**Why:**
User asked "is the update infrastructure solid?" before installing across md-manager + health-tracker. Audit identified Tier-2 gaps:
- Update requires 2 commands consumers must remember; no auto-update by default for third-party marketplaces.
- No CHANGELOG at the canonical repo-root location (per-version notes were buried inline in README + verbosely in history.md).
- No "your installed version is behind" surfacing anywhere.

The first two are mechanizable as docs. The third (silent version drift) is left for PR H proper (FB-0010 FOLLOW-UP #2 — generalize Check 2.5 to a `minFlowVersion` slot + Doctor Check 6) per explicit Scope (out) call.

**Design decisions:**
- **CHANGELOG distinct from history.md (intentional divergence).** history.md retains the verbose internal-tracking format (SHA + tradeoffs + design decisions); CHANGELOG is terse user-facing (date + headline + bullets + breaking-change callout). Plan-critic specifically flagged this divergence as worth naming; spec-walk item 9 makes the divergence explicit so future docs hygiene PRs don't try to merge the two formats.
- **No version bump for docs-at-root.** Verified: `/plugin install flow@flow` packages only the `plugins/flow/*` subtree; root-level `docs/`, `CHANGELOG.md`, `README.md` are read from GitHub directly. Consumers on v1.2.3 get the new docs the moment we merge — no client action. Bumping to v1.2.4 would force a no-op upgrade cycle.
- **Cross-links in 5 places (README × 2, bootstrap.md, migration.md, plan.md).** A CHANGELOG nobody can find is the FB-0005 silent-failure class re-stated. Plan-critic explicitly approved this scope expansion as "polished over partial" per CLAUDE.md quality bar.
- **Multi-project ritual section in upgrade.md.** User's stated use case is 2 active consumer projects. Explicit guidance prevents the "I updated once, why didn't it stick everywhere?" failure mode.

**Technical decisions:**
- CHANGELOG written manually (not auto-generated from history.md or git log). Manual extraction risks drift; MEDIUM confidence verdict #2 flagged this. Mitigation: FB-0010 lens-engineer hunt + Check 2.5 catch survivors at review (and indeed Check 2.5 passed against the current tree post-edit).
- Upgrade.md "Pin to a prior version" troubleshooting uses `cd ~/.claude/plugins/flow && git checkout v1.2.3`. This assumes the plugin install directory is a git checkout (Claude Code's plugin manager treats marketplaces as git repos). If a future Claude Code release changes the install shape, this hint becomes stale — accept the risk; the doc names the assumption.
- Auto-update opt-in example uses the schema documented by Claude Code (`"autoUpdate": true` in `extraKnownMarketplaces.<name>`). Doc surfaces the tradeoff (silent breaking-change exposure) so consumers choose deliberately.

**Tradeoffs discussed:**
- **Bump or no bump?** Considered bumping to v1.2.4 to give consumers a discoverability signal that new upgrade docs exist. Decided against: the docs land on GitHub immediately; a version bump would force no-op `/plugin install` cycles across all consumers; sets a bad precedent (every README polish = version bump = upgrade burden). If consumers report they don't notice the new docs, revisit per the verdict-#1 mitigation.
- **CHANGELOG location.** Considered putting under `docs/CHANGELOG.md`. Decided on repo root — Keep-a-Changelog convention is `CHANGELOG.md` at root, and the file is short enough that root placement keeps it visible on GitHub's repo landing.
- **Manual vs auto extraction.** Auto-extracting from history.md per-version blocks via a script would prevent drift but adds a dependency (script must run on every history.md edit) and complicates docs hygiene. For 6 versions of history, manual is cheaper. Revisit when CHANGELOG hits 15+ entries.

**Lessons learned:**
- Plan-critic ran cleanly in parallel with execution and produced APPROVED + 3 actionable findings (CHANGELOG format spec + file count cleanup + verdict #1 mitigation reword). Folding the 3 into the plan before write-time was cheaper than catching them at review.
- FB-0010 discipline applied to PR H1's own work caught the inline-versions-block-in-README as a fan-out source for the future CHANGELOG; cleaner to delete the inline block than maintain two copies (FB-0010 single-source-of-truth principle).
