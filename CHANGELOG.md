# Changelog

All notable changes to flow are recorded here. Reverse chronological (newest first).

This is the **consumer-facing changelog** — read this before upgrading. For per-PR design decisions + tradeoffs, see [`dev-docs/history.md`](dev-docs/history.md) (verbose, internal-tracking).

Format: each entry has a date, version, headline, 2-4 bullets, and an explicit "Breaking changes:" callout (currently always "none").

To upgrade: see [`docs/upgrade.md`](docs/upgrade.md).

---

## v1.2.5 — 2026-05-27

**Adversarial sharpening of the reviewer pipeline (PR J; research-grounded — see Anthropic's "adversarial review step" best-practice + CriticGPT recall results).**

- `auditor` agent gains a **Self-check before emitting** step: each finding must survive an attempted disproof — name the specific session text that would invalidate the finding, re-scan for it, drop if found or if the lookup is fuzzy. Mitigates the documented "reviewer prompted to find gaps will report some even when work is sound" failure mode.
- `plan-critic` agent gains the same self-check adapted to the two-citation rule: each finding must survive an attempted third citation that would resolve the apparent conflict. Plan-critic's `Internal incoherence` category now also explicitly covers **fan-out contradictions within the plan** (count/name/slot/version referenced in N places where values disagree) — PR-G FOLLOW-UP #5 absorbed.
- `lens-staff-engineer` agent gains an explicit **adversarial reading** preamble ("assume the diff is broken — what's the most likely break?"). This is the engineer-lens analog of the security lens's threat-model stance; the published research convergence is that explicit "find the break" framing materially raises recall on real defects.
- `/flow:security-review` agent prompt shifts to **fully red-team identity** ("you are a red-team operator; your goal is to find an exploitable vulnerability — not to evaluate whether the code is good"). Adds a trace-input-source-back disprove step: if the dangerous sink can't be reached via a concrete attacker scenario, drop the finding. Operational logic (FB-0006/FB-0007 source-file early-exit, FB-0008 `[ -z ]` defaultBranch fallback chain discipline, FB-0009 fail-fast gh+jq, three-source diff capture) unchanged.
- All four edited prompts adopt Anthropic's verbatim *"flag only gaps that affect correctness or the stated requirements, and treat the rest as optional"* warning at the top of each prompt, before any category logic — the explicit countermeasure to the over-engineering tax adversarial framing brings.

**Breaking changes:** none. Prompt-only PR; existing eval fixtures remain green. Reviewer output schema unchanged. The change is additive: clean diffs continue to produce `No issues flagged.` / `APPROVED`; the sharper recall surfaces on diffs that genuinely warrant it.

## v1.2.4 — 2026-05-27

**Workflow-spawn skip prevention (FB-0010 workflow-step sub-class).**

- `/flow:staff-review` now ends with an explicit "After this skill" footer naming `/flow:ship` as the canonical next step. Reframes the existing "ends with work ready, not merged" line into actionable forward motion.
- `/flow:ship` Step 1.0 workflow-step assumption surface gains `⚠️` visual emphasis per ASSUMES line + a REMINDER paragraph explicitly naming the "never bypass `/flow:ship` with `gh pr create`" rule.
- `plugins/flow/docs/workflow.md` Step 10 adds a "Never bypass `/flow:ship`" subsection. Names the failure mode: skipping `/flow:ship` skips the entire Step 2 (security + a11y reviews) of the pipeline, and the `STATUS: SKIPPED` audit-trail signal is load-bearing even on docs-only PRs.
- Defends against the 9th FB-0010 incident, surfaced during PR H1 when the author skipped spawning `/flow:security-review` + `/flow:accessibility-review` and ran `gh pr create` directly. 1 incident isn't usually enough for FB encoding, but the fix is trivially mechanizable (prompt-level reminders + workflow.md discipline statement).

**Breaking changes:** none. Additive workflow guardrails — no skill behavior or contract changed.

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

- Flow follows **semver as a discipline, not a contract**. Patch bumps (`1.2.x`) aim to be additive; minor bumps (`1.y.0`) add user-visible surface; major bumps (`x.0.0`) are reserved for breaking changes (none have happened). The discipline is enforced by `lens-staff-engineer` review + `/flow:doctor` Check 2.5 + author care — there is no mechanical gate today that BLOCKS a breaking change from landing in a patch bump. Always verify upgrades with `/flow:doctor`; treat any patch-level regression as a bug worth filing.
- The plugin manifest version (`plugins/flow/.claude-plugin/plugin.json`) and marketplace metadata version (`.claude-plugin/marketplace.json`) are kept in sync.
- **Docs-only changes at the repo root** (e.g., this CHANGELOG itself, `docs/upgrade.md`) ship without a version bump — they don't change plugin behavior and consumers fetch them from GitHub directly, not via `/plugin install`.
