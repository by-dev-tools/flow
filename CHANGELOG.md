# Changelog

All notable changes to flow are recorded here. Reverse chronological (newest first).

This is the **consumer-facing changelog** — read this before upgrading. For per-PR design decisions + tradeoffs, see [`dev-docs/history.md`](dev-docs/history.md) (verbose, internal-tracking).

Format: each entry has a date, version, headline, 2-4 bullets, and an explicit "Breaking changes:" callout (currently always "none").

To upgrade: see [`docs/upgrade.md`](docs/upgrade.md).

---

## v1.2.3 — 2026-05-27

**Consistency discipline (FB-0010 defense for the recurring bug class.)**

- `lens-staff-engineer` agent now explicitly hunts two flavors of "consistency that depends on author memory": silent-skip on edge case (failures swallowed via `2>/dev/null` / unset-fallback / regex inversion) + fan-out contradiction (count/name/slot referenced in N places, only some updated).
- `/flow:doctor` gains **Check 2.5** comparing the schema's actual slot count (`jq '.properties | keys | length'`) against any documented "N slots" claim in `CLAUDE.md` / `README.md` / `docs/` / `core-docs/` / `dev-docs/`. Flags WARN on mismatch.
- `plugins/flow/docs/workflow.md` Step 4 adds a "Consistency sweep" paragraph naming the discipline at preflight, before `/simplify` runs.
- Defends against the most-recurring bug class flow's own development has surfaced — 6 incidents across PRs 1, B, D, E, F (pass 1), F (pass 2).

**Breaking changes:** none. Additive prompt + new doctor check + new workflow.md paragraph.

## v1.2.2 — 2026-05-26

**Consumer dogfood-readiness.**

- New skill: `/flow:doctor` — PASS/FAIL/WARN punch-list verifying flow is correctly installed + project is correctly configured. Use after `bootstrap.sh` or any time something feels off.
- New scaffolder: `template/base/bootstrap.sh` — one-command project setup (`bash bootstrap.sh --stack web|swift|tauri-rust-ts`). Idempotent; re-running on a populated project skips existing files.
- New walkthrough: `docs/first-pr.md` — step-by-step concrete guide for your first PR through the loop.
- Refreshed `README.md` + `template/base/CLAUDE.md.template` — explains the 3-layer enforcement mechanism (auto-loading rules + skill triggers + `/flow:ship` Step 1.0 surface).

**Breaking changes:** none.

## v1.2.1 — 2026-05-25

**Consumer-feedback follow-ups (5 fixes from md-manager's first real-consumer dogfood report).**

- **Stale-base preflight** in `/flow:ship`, `/flow:ship-spike`, `/flow:staff-review` Step 1 — prevents the "fork from old base → phantom-deletion diff" class of waste before any expensive review runs.
- **Marketplace install verification** docs (`docs/bootstrap.md` + `docs/migration.md`) — adds `/plugin marketplace list | grep '^flow'` step to catch the silent-omission failure when a stale `extraKnownMarketplaces` key points at flow's URL under a non-canonical name (FB-0005).
- **`/flow:ship` Step 1.0 workflow-step assumption surface** — prints which workflow steps `/flow:ship` ASSUMES already ran (critique-plan, simplify, staff-review). Skips become visible at ship time.
- **Per-diff non-UI early-exit** in `/flow:security-review` + `/flow:accessibility-review` — checks the diff for source/UI files; skips with `STATUS: SKIPPED` if none present. Saves spawn cost on docs-only PRs even for `uiSurface: true` projects.
- **`gh` + `jq` CLI fail-fast** — `/flow:ship` + `/flow:ship-spike` Step 1 check `command -v gh` / `command -v jq` and exit 1 with install hint if missing, rather than exit 127 at the invocation site. `/flow:staff-review` adds warn-only check (gh is optional there).

**Breaking changes:** none. All additive guardrails.

## v1.2.0 — 2026-05-25

**Consumer scaffolding (template directory + bootstrap/migration docs).**

- New `template/base/` — Tier 1 (CLAUDE.md.template, flow.config.json.example, .claude/settings.json.example, .claude/rules/safety.md.template, README.md.template, .gitignore.template) + Tier 2 (5 core-docs scaffolds: spec, plan, roadmap, history, feedback with format headers).
- New `template/stacks/{web,swift,tauri-rust-ts}/` — per-stack overlays: preflight runner, CI workflow, `.gitignore.append`, UI/dev-server rules (web + tauri), link skill (web + tauri).
- New `docs/bootstrap.md` — step-by-step adoption walkthrough for new projects, all 3 stacks covered.
- New `docs/migration.md` — 3-stage migration pattern for existing projects with prior `.claude/` content (install non-breaking → dogfood validate → delete duplicates).
- New security regression fixtures: `plugins/flow/evals/security/test_cwd_constraint.py` + `test_malicious_config.py` — protects against path traversal + shell-meta injection through `flow.config.json` values.
- Schema's first published slot set (current count lives in `plugins/flow/schema/flow.config.schema.json` — the single source of truth).

**Breaking changes:** none. Templates are consumer-pulled, not plugin-pushed.

## v1.1.0 — 2026-05-24

**Full workflow surface backfill.**

- 5 new shipped skills: `/flow:staff-review` (4 parallel lenses), `/flow:security-review`, `/flow:accessibility-review`, `/flow:ship-spike` (spike-mode lightweight pipeline), `/flow:workflow-help` (11-step loop + resolved config slots).
- 6 new shipped agents: `planner` + `docs` (context-isolation helpers), plus 4 staff-review lens agents (`lens-staff-engineer`, `lens-ux-designer`, `lens-design-engineer`, `lens-push-further`).
- 4 portable auto-loading rules: `general.md` (workflow discipline on every edit), `plan-discipline.md` (required plan fields + LOW=gate), `documentation.md` (history/feedback/plan format rules), `exploration.md` (§ Exploration triggers).
- New memory tool: `plugins/flow/tools/memory/check.mjs` — failure-pattern corpus cap + audit-due check.
- New `plugins/flow/schema/flow.config.schema.json` — JSON Schema for `flow.config.json`. The schema is the single source of truth for slot count + names; the README + `/flow:doctor` Check 2.5 derive from it.
- New default hooks at `plugins/flow/hooks/default-hooks.json` — opt-in PreToolUse hooks (sensitive-file write blocker + path-validation warn).
- `/flow:ship` PR-1 limitations backfilled (`/flow:security-review` + `/flow:accessibility-review` now wire in; memory machinery now active).

**Breaking changes:** none. PR-1 placeholder behavior replaced with real implementations.

## v1.0.0 — 2026-05-24

**Marketplace restructure + rename from `byamron/llm-auditor` → `by-dev-tools/flow`.**

- Repository renamed in place + restructured into Anthropic marketplace + plugin shape: marketplace at `.claude-plugin/marketplace.json` (one plugin: `flow`); plugin manifest at `plugins/flow/.claude-plugin/plugin.json`.
- 5 shipped skills: `/flow:ship` (port from md-manager's `/ship`), `/flow:audit-plan`, `/flow:audit-completion`, `/flow:critique-plan`, `/flow:log-disagreement` (the last 4 ported from the prior `assumption-auditor` plugin).
- 2 shipped agents: `auditor`, `plan-critic`.
- New canonical loop reference: `plugins/flow/docs/workflow.md` — the 11-step managed-autonomy loop.
- Pre-v1.0.0 content recoverable via `git checkout pre-flow-plugin`.

**Breaking changes:** install identity changed. Old `assumption-auditor@llm-auditor` users must re-add via `/plugin marketplace add by-dev-tools/flow && /plugin install flow@flow`. GitHub maintains a `byamron/llm-auditor` → `by-dev-tools/flow` redirect, so old clones still pull from the same place. The old user-scope `extraKnownMarketplaces.llm-auditor` key continues to resolve at the URL level but is invisible to the resolver (`enabledPlugins.<plugin>@<marketplace>` matches the marketplace's `name` field, NOT the user-scope settings key) — see FB-0005 and `docs/migration.md` for the install verification step that catches this.

---

## Notes on versioning

- Flow follows **semver**. Patch bumps (`1.2.x`) are additive — no breaking changes. Minor bumps (`1.y.0`) add user-visible surface. Major bumps (`x.0.0`) are reserved for breaking changes; none have happened.
- The plugin manifest version (`plugins/flow/.claude-plugin/plugin.json`) and marketplace metadata version (`.claude-plugin/marketplace.json`) are kept in sync.
- **Docs-only changes at the repo root** (e.g., this CHANGELOG itself, `docs/upgrade.md`) ship without a version bump — they don't change plugin behavior and consumers fetch them from GitHub directly, not via `/plugin install`.
