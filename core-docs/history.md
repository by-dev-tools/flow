# History

Detailed record of shipped work. Reverse chronological (newest first). This is not a changelog -- it captures the **why**, **tradeoffs**, and **decisions** behind each change so future sessions have full context on how the project evolved.

---

## How to Write an Entry

```
### [Short title of what was shipped]
**Date:** YYYY-MM-DD
**Branch:** branch-name
**Commit:** [SHA or range]

**What was done:**
[Concrete deliverables -- what changed in user-facing terms.]

**Why:**
[The problem this solved or the goal it served.]

**Design decisions:**
- [UX or product choice + reasoning]

**Technical decisions:**
- [Implementation choice + reasoning]

**Tradeoffs discussed:**
- [Option A vs Option B -- why this one won]

**Lessons learned:**
- [What didn't work, what did, what to do differently]
```

Use the `SAFETY` marker on any entry that modifies error handling, persistence, data loss prevention, or fallback behavior.

---

## Entries

<!-- Add new entries below this line, newest first. -->

### Initialize project-dev docs and Claude Code infra
**Date:** 2026-04-20
**Branch:** codebase-overview
**Commits:** e30b75b, 4d3522b, + in-progress fixup

**What was done:**
Added `CLAUDE.md`, `core-docs/`, and `.claude/` scaffolding for developing the plugin. Kept the new project-dev files strictly separate from the plugin's own published artifacts (root `agents/`, `skills/`, `scripts/`, `evals/`, `.claude-plugin/`, `README.md`, `DISAGREE.md`). Added a `.gitignore` for `.claude/settings.local.json`, `.claude/forge/`, and `.DS_Store`.

**Why:**
Before this change, the repo had no project-dev infrastructure -- no agent specs, no rules, no living docs. Sessions developing the plugin had to rediscover context every time. The template provides a scoped, predictable place for that context.

**Design decisions:**
- Explicit plugin-vs-dev boundary documented at the top of CLAUDE.md. The dual-name collision (`agents/` at root vs. `.claude/agents/`) is structural -- Claude Code's plugin convention requires plugin artifacts at root, and Claude Code's project convention requires project-dev infra under `.claude/`. Resolved via documentation, not reorganization.
- Renamed `.claude/skills/audit/` to `.claude/skills/preship/` to avoid slash-command collision with the plugin's own `/audit-plan` and `/audit-completion`. The pre-ship skill's frontmatter `name:` was updated to match (caught in review -- would otherwise have registered as `/audit`).
- Deleted template pieces inapplicable to a headless plugin: `core-docs/design-language.md`, `.claude/agents/ui.md`, `.claude/rules/ui.md`, `.claude/rules/dev-server.md`, `.claude/skills/link/`, `.claude/skills/dev-panel/`, `.claude/skills/setup/`.
- Scoped `.claude/rules/safety.md` to plugin-critical files: `agents/auditor.md`, `scripts/*.py`, plugin manifests, eval harness. These are the files whose silent breakage would be most expensive.

**Technical decisions:**
- `.claude/settings.local.json` gitignored per Claude Code convention (per-user permissions should not be shared).
- Empty `.claude/forge/` directory left in tree (git doesn't track empty dirs) but gitignored to prevent Forge's local cache from being committed later.
- `core-docs/plan.md` Current Focus populated with the real v0.1.0 state (eval harness stub + SKIP'd fixtures) rather than left as a template placeholder.

**Tradeoffs discussed:**
- Keep vs. rename `.claude/skills/audit/`: renaming adds a small cognitive cost (users typing `/audit` won't find it) but eliminates a real collision risk during plugin development. Renaming won.
- Populate vs. leave template placeholders in `plan.md`/`history.md`/`feedback.md`: populated plan.md because the current focus is knowable and useful; left history.md and feedback.md format-only because the first real entries should come from real work, not backfill.
- Merge template README content into the existing plugin README: skipped. Template README is generic philosophy; plugin README is concrete install/use docs. Nothing to merge.

**Lessons learned:**
- Directory renames don't automatically update frontmatter `name:` fields. Always grep for the old name after a skill rename. The preship skill's frontmatter was missed in the first pass and caught in self-review -- the exact kind of "declared done, didn't actually verify" error the plugin itself is designed to catch.
- Full-repo grep for references to deleted files (`design-language`, `UI Agent`, etc.) after cleanup is load-bearing. Four agent/workflow files had stale references the deletion step missed.
