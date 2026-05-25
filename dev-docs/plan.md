# Plan

## Current Focus

**PR 1 merged** (squash commit `f8610a1`, 2026-05-24). **PR 2 plan ready for next-session pickup** — full handoff at [`dev-docs/handoffs/pr2-flow-plan.md`](handoffs/pr2-flow-plan.md). 8 phases, each with verifiable success criteria. Phase 8 publishes the md-manager handoff at [`dev-docs/handoffs/md-manager-pr4-6-spec.md`](handoffs/md-manager-pr4-6-spec.md) (also already drafted in this docs-only precursor; Phase 8 verifies + updates against PR 2's actual shipped surface).

After PR 2 merges: PR 3 (template directory: `template/base/` + per-stack overlays for web / swift / tauri-rust-ts). After PR 3 merges: md-manager PRs 4 → 5 → 6 sequentially per the md-manager handoff spec. Cross-repo umbrella canonical state: md-manager's `core-docs/plan.md` § "Flow plugin extraction".

## Handoff Notes

- **PR 1 needs user-side settings.json update after merge.** One line: `enabledPlugins."assumption-auditor@llm-auditor"` → `"flow@flow"`. Plus re-add marketplace under the new name: `/plugin marketplace remove llm-auditor && /plugin marketplace add by-dev-tools/flow && /plugin install flow@flow`. settings.json backup exists at `~/.claude/settings.json.bak.20260523-144832` from PR 0.
- **Optional disagreement-records migration:** `mv ~/.claude/plugins/data/assumption-auditor/disagreements/* ~/.claude/plugins/data/flow/disagreements/` if you want pre-v1.0.0 records to surface alongside post-rename ones.
- **PR 2 brief is owed.** Lives in md-manager once the PR-1 handoff loop closes (`md-manager/core-docs/handoffs/pr2-flow-plugin-rest.md`).

## PR 2 follow-ups from PR 1 review

The walk-through-the-loop review on PR 1 surfaced two findings that are out-of-scope for PR 1 but in-scope for PR 2. Quoted here verbatim so PR 2's planner doesn't have to re-derive them:

1. **Consumer-vs-flow path divergence in critique-plan default.** `plugins/flow/skills/critique-plan/SKILL.md:13` hardcodes `--reference-glob "core-docs/*.md"`. When flow runs `/flow:critique-plan` on itself (which uses `dev-docs/` not `core-docs/`), the plan-critic sees zero reference docs. The fix is a `flow.config.json.referenceGlob` slot that the SKILL reads at invocation, with the documented default chain (consumer projects: `core-docs/*.md`; flow's own repo: `dev-docs/*.md`). PR 2's `flow.config.schema.json` work picks this up. Cost: ~10 min once the config-slot machinery exists.

2. **`extract_session.py --reference-paths` accepts arbitrary host paths.** Currently, `gather_reference_docs` reads any absolute path the caller passes; output is injected verbatim into the auditor subagent's context. In the current invocation chain, the caller is the `critique-plan` SKILL with a hardcoded glob, so consumer input never reaches it. But if a future skill or recipe ever forwards user-controlled paths, an attacker could exfil file contents (e.g., `~/.ssh/config`) into the subagent's prompt and out via tool output. Constrain to `cwd` (reject resolved paths outside `Path.cwd()`) unless an explicit override flag says otherwise. Document the trust model in the script docstring. Pairs naturally with PR 2's path-validation rule baseline (`plugins/flow/hooks/default-hooks.json`).

## Active Work Items

### PR 2 — Workflow surface backfill (executing autonomously per user direction)

**Mode:** feature
**Branch:** `pr2/workflow-backfill` (off `docs/pr2-handoffs`)
**Canonical plan:** [`dev-docs/handoffs/pr2-flow-plan.md`](handoffs/pr2-flow-plan.md). 8 phases, per-phase verifiable success criteria, 6 confidence verdicts, 6 risks, ~24 files. User direction: execute autonomously, self-grade against success criteria, follow the workflow being implemented at each stage.

**Phase 1 status (complete):** all 12 md-manager sources fetched to `/tmp/pr2-sources/` (sizes match estimates ±2%). Source-read observations refining the handoff plan:
- Staff-review extraction (Phase 3-4): md-manager uses `subagent_type: Explore` with inline prompts; PR 2 changes to `subagent_type: lens-*` with extracted agent files. Structural change confirmed MEDIUM. Fallback documented.
- Security/a11y reviews: heavier md-manager-specific token references than handoff anticipated (`--sand-9`, `--page-text-quiet`, "markdown-notes app"). De-projection effort scaled accordingly.
- All 4 skills start step numbering at 0 (same off-by-one PR 1's `/flow:ship` had). Apply PR-1 NIT fix (start at 1) across all ports.
- `ship-spike` references non-existent `tools/preflight/check.mjs` — port keeps as a config-slot opportunity (consumer-side preflight is project-specific per consolidation doc Decision 1).

Execution proceeds through Phases 2-8 per the handoff.

### PR 1 — Flow plugin restructure + initial workflow surface (SHIPPED — awaiting merge)

Status: all spec-walk checkboxes complete; PR opened at [by-dev-tools/flow#5](https://github.com/by-dev-tools/flow/pull/5); walk-through-the-loop review pass surfaced 3 BLOCKERs + 2 cheap NITs, all fixed in follow-up commit `65a0a58`; plan-critic retroactive verdict APPROVED; recovery anchor at git tag `pre-flow-plugin`. Full history entry in `dev-docs/history.md`. Original plan spec-walk preserved below for reference.

---

**Mode:** feature

**Goal:** Move existing root-level plugin content into `plugins/flow/*`, rename `llm-auditor` / `assumption-auditor` identifiers to `flow` (both marketplace name and plugin name), bump to v1.0.0, add `/flow:ship` skill (ported from md-manager via the locked /ship port table — 3a/3b split, loud-warning pattern, default-branch discovery, config-slot doc paths) and `plugins/flow/docs/workflow.md` (canonical 11-step loop, de-projected), rename this repo's `core-docs/` to `dev-docs/` to match the consumer-vs-plugin convention. The result is an installable v1.0.0 `flow` plugin whose marketplace shape matches Anthropic's pattern and whose own dev-tracking is cleanly separated from the plugin artifacts it ships.

**Scope (in):**
- Create recovery tag `pre-flow-plugin` against current HEAD (`8857ebd`) and push it. Brief calls this the recovery anchor; it doesn't exist yet.
- Restructure plugin artifacts via `git mv` (preserve history):
  - `agents/{auditor,plan-critic}.md` → `plugins/flow/agents/`
  - `skills/{audit-plan,audit-completion,critique-plan,log-disagreement}/SKILL.md` → `plugins/flow/skills/`
  - `scripts/{extract_session,bounding_logic,log_disagreement}.py` → `plugins/flow/scripts/`
  - `evals/{ground_truth.yaml,run_evals.py,fixtures/}` → `plugins/flow/evals/`
  - `DISAGREE.md` → `plugins/flow/DISAGREE.md`
- Rename `.claude-plugin/marketplace.json`: marketplace `name` `llm-auditor` → `flow`; plugin `name` `assumption-auditor` → `flow`; plugin `source` `./` → `plugins/flow`; add `metadata.pluginRoot: "./plugins"`; update `homepage`/`repository` URLs to `https://github.com/by-dev-tools/flow`; bump marketplace `metadata.version` and plugin `version` to `1.0.0`; expand `description` to reflect the workflow scope.
- Rename `.claude-plugin/plugin.json`: `name` `assumption-auditor` → `flow`, `version` `0.3.0` → `1.0.0`, `homepage`/`repository` URLs to by-dev-tools/flow, updated `description` covering the audit/critique + workflow surface.
- Move `.claude-plugin/plugin.json` to `plugins/flow/.claude-plugin/plugin.json` (Anthropic pattern: marketplace at repo root, plugin manifest inside its own directory).
- Update `plugins/flow/scripts/log_disagreement.py` disagreement-storage path: `~/.claude/plugins/data/assumption-auditor/disagreements/` → `~/.claude/plugins/data/flow/disagreements/`. Note: pre-existing user data at the old path becomes orphaned (acceptable — it's local dev/debug data; called out in PR body and README).
- Add `plugins/flow/skills/ship/SKILL.md` — port from md-manager `.claude/skills/ship/SKILL.md` (fetched via `gh api repos/by-dev-tools/md-manager/contents/...`) per the locked PR-1 /ship port table:
  - Steps 0, 2, 4–5: port as-is.
  - Step 1 (`/security-review`, `/accessibility-review`): `[PR 1 LIMITATION]` placeholder block; skills land in PR 2.
  - Step 3a (user-feedback → `feedback.md`): port active — pure markdown, no tooling dep.
  - Step 3b (memory machinery via `tools/memory/check.mjs`): `[PR 1 LIMITATION]` placeholder; memory tooling lands in PR 2.
  - Step 6 (`gh pr create --base main`): replace hardcoded `main` with default-branch discovery (`git symbolic-ref` → `flow.config.json.defaultBranch` slot → literal `main` fallback).
  - Step 7 (`/link`): replace with generic "if your project has a dev-server skill, invoke it now" note.
  - `npm run typecheck` references: config-slot via `flow.config.json.typecheckCmd`; **loud warning** if unset (`⚠️ flow.config.json.typecheckCmd not set; skipping preflight re-run. Set this slot to enable typecheck on /ship.`) — never silent no-op.
  - Doc paths (`core-docs/history.md`, etc.): config-slot via `flow.config.json.historyPath` / `planPath` / `roadmapPath` / `feedbackPath` / `specPath` with sensible defaults.
  - De-project: strip md-manager-specific tokens (`src/store.tsx`, `--sand-*`, `Geist`, `Mini`, `pattaya`, etc.).
- Add `plugins/flow/docs/workflow.md` — port from md-manager `core-docs/workflow.md` (already fetched at `/tmp/md-workflow.md`):
  - Strip md-manager-specific examples (designer cargo gates, md-manager preflight lists, etc.).
  - Annotate `/simplify`, `/batch`, `/debug`, `/loop`, `/claude-api` as **"(bundled with Claude Code)"** wherever referenced — they are Anthropic-native, not flow-provided.
  - Annotate `/critique-plan`, `/audit-plan`, `/audit-completion` as **flow-internal** (not an external assumption-auditor plugin anymore — they're bundled into flow).
  - Add a "Project config slots" section narratively documenting `flow.config.json` (paths, defaultBranch, typecheckCmd, etc.). JSON Schema lands PR 2.
  - Add a "Bootstrap status" / "v1.0.0 scope" section: only `/flow:ship` + the four audit/critique skills + 2 agents (`auditor`, `plan-critic`) shipped; full workflow surface comes in PR 2.
- Rename `core-docs/` → `dev-docs/` (flow's own dev-tracking; per Decision 4 + the consumer-vs-plugin convention). Move all files: `plan.md` (this plan + prior content preserved), `history.md`, `feedback.md`, `spec.md`, `workflow.md`. Note: this is a `git mv` rename, not a content rewrite.
- Update `CLAUDE.md` (project-dev concern, not plugin-shipped) for the new layout: plugin artifacts at `plugins/flow/*` (not root); project-dev knowledge at `dev-docs/` (not `core-docs/`); identity is "flow" (not "assumption-auditor"); call out the `template/core-docs/` (consumer-side) vs `dev-docs/` (plugin-side) distinction explicitly so future sessions don't conflate them.
- Update `.claude/rules/safety.md`: rewrite path references for the new layout. Safety-critical paths become `plugins/flow/agents/auditor.md`, `plugins/flow/scripts/extract_session.py`, `plugins/flow/scripts/bounding_logic.py`, `plugins/flow/skills/audit-plan/SKILL.md`, `plugins/flow/skills/audit-completion/SKILL.md`, `plugins/flow/.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `plugins/flow/evals/run_evals.py`, `plugins/flow/evals/ground_truth.yaml`. (Plus add `plugins/flow/skills/ship/SKILL.md` to the safety-critical list — it's new published surface.)
- Update `.claude/rules/general.md`, `.claude/agents/*.md`, `.claude/skills/*/SKILL.md` (project-dev infra): any references to `core-docs/...` get updated to `dev-docs/...`.
- Rewrite root `README.md` for the marketplace-shaped identity: what the marketplace is (`flow`), how to install (`/plugin marketplace add by-dev-tools/flow && /plugin install flow@flow`), pointer to `plugins/flow/docs/workflow.md` for what the plugin does, v1.0.0 status (audit/critique + `/flow:ship` shipped; rest of workflow surface lands PR 2; template directory lands PR 3), History section referencing the `pre-flow-plugin` tag for archeology and noting the rename from `llm-auditor`. The pre-rename assumption-auditor README content is preserved at the tag — not lost.
- Manual cold-read of full diff with security + simplification + project-agnostic lenses (the plugin's own `/flow:simplify` doesn't exist — `/simplify` is bundled-native, can be used; flow's `/flow:staff-review` doesn't exist yet — bootstrap exception per the brief).
- Per-phase commits with `Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>` trailer.
- Open PR against `main`; user merges.

**Scope (out):**
- Workflow skills `/flow:staff-review`, `/flow:security-review`, `/flow:accessibility-review`, `/flow:ship-spike`, `/flow:workflow-help` — PR 2.
- Agents `planner`, `docs`, the four staff-review lens agents (`staff-engineer`, `ux-designer`, `design-engineer`, `push-further`), optional `uncommon-care` — PR 2.
- Rules `general.md`, `plan-discipline.md`, `documentation.md`, `exploration.md` (the project-dev ones at `.claude/rules/*` that would become plugin-shipped portable rules) — PR 2.
- `tools/memory/check.mjs` — PR 2.
- `plugins/flow/schema/flow.config.schema.json` — PR 2.
- `plugins/flow/hooks/*` — PR 2.
- `template/` directory (web / swift / tauri-rust-ts overlays + `template/base/`) — PR 3.
- Backfilling `/flow:ship`'s PR-1-limitation placeholders — PR 2.
- Any md-manager-side changes (config layer, dogfood, deletion of duplicates) — PRs 4–6.
- Updating `~/.claude/settings.json` (`assumption-auditor@llm-auditor` → `flow@flow`) — user-side one-liner after merge; flagged in PR body.
- v1.x+ post-extraction features (autonomous routines, JTBD substrate, visual artifacts, design lenses) — out of the extraction umbrella entirely.

**Spec-walk checkboxes** (each binds to a verification step):

- [ ] `pre-flow-plugin` tag exists on `origin` and points at the pre-PR-1 HEAD (`git ls-remote --tags origin | grep pre-flow-plugin` matches `8857ebd`).
- [ ] All plugin artifacts live under `plugins/flow/` (verify: no `agents/`, `skills/`, `scripts/`, `evals/`, `DISAGREE.md` at repo root; all six moved).
- [ ] `.claude-plugin/marketplace.json` parses with `jq .` and declares marketplace `name: "flow"` + plugin `name: "flow"` + plugin `source: "plugins/flow"` (or equivalent `pluginRoot`-relative form).
- [ ] `plugins/flow/.claude-plugin/plugin.json` parses with `jq .` and declares `name: "flow"`, `version: "1.0.0"`, by-dev-tools/flow URLs.
- [ ] `plugins/flow/skills/ship/SKILL.md` exists, contains the explicit `[PR 1 LIMITATION]` placeholder for `/security-review` + `/accessibility-review`, contains the loud-warning string for unset `typecheckCmd`, has no md-manager-specific tokens (`grep -i "md-manager\|sand-\|space-\|geist\|mini\|pattaya"` returns empty).
- [ ] `plugins/flow/docs/workflow.md` exists, annotates `/simplify` (and `/batch`, `/debug`, `/loop`, `/claude-api`) as "(bundled with Claude Code)" wherever referenced, annotates `/critique-plan`+`/audit-plan`+`/audit-completion` as flow-internal, documents `flow.config.json` slots narratively, lists v1.0.0 scope and PR-2 backfill plan.
- [ ] `dev-docs/{plan,history,feedback,spec,workflow}.md` exist (all five files moved from `core-docs/`); `core-docs/` directory no longer exists.
- [ ] `plugins/flow/scripts/log_disagreement.py` writes to `~/.claude/plugins/data/flow/disagreements/` (grep for the new path; old `assumption-auditor` string absent).
- [ ] `.claude/rules/safety.md` lists the new `plugins/flow/*` paths; old root paths absent.
- [ ] `.claude/rules/general.md`, `.claude/agents/*.md`, `.claude/skills/*/SKILL.md` reference `dev-docs/` (not `core-docs/`); grep for `core-docs/` in `.claude/` returns empty.
- [ ] Root `README.md` describes the `flow` marketplace identity, includes install command, History section, and `pre-flow-plugin` tag reference.
- [ ] `CLAUDE.md` describes the new `plugins/flow/*` layout, `dev-docs/` convention, and the consumer-vs-plugin distinction (`template/core-docs/` vs `dev-docs/`).
- [ ] `grep -rn "llm-auditor\|assumption-auditor" .claude-plugin/ plugins/ README.md CLAUDE.md` returns only intentional history-tag references (in README "History" section and any commit-message archeology lines).
- [ ] `claude plugin validate .` exits clean.
- [ ] Local smoke test: `mkdir /tmp/flow-smoke && cd /tmp/flow-smoke && git init && claude` → `/plugin marketplace add <local-or-branch-ref>` → `/plugin install flow@flow` succeeds → `/help` lists `flow:ship`, `flow:audit-plan`, `flow:audit-completion`, `flow:critique-plan`, `flow:log-disagreement` (5 user-visible skills). If installing from the open branch fails because Claude Code can't read unmerged refs, document the failure and note "re-run smoke after merge" — don't block PR open on it.
- [ ] Manual cold-read pass complete: security (no command-injection in `` !`<cmd>` ``, no leaked paths, no secrets), simplification (no duplicated content between SKILL.md files, no dead text from md-manager source), project-agnostic (grep diff for `md-manager`, `pattaya`, `sand-`, `--space-`, `Geist`, `Mini`).

**Confidence verdicts (per load-bearing assumption):**

**Assumption:** Restructuring root content into `plugins/flow/*` via `git mv` preserves all behavior because skill files reference `${CLAUDE_PLUGIN_ROOT}/scripts/...` (dynamic) and `.claude-plugin/marketplace.json`'s plugin `source` slot is the only thing telling Claude Code where the plugin lives.
**Confidence:** HIGH
**Why:** Verified the three skill files (`critique-plan`, `audit-plan`, `audit-completion`, `log-disagreement`) all use `${CLAUDE_PLUGIN_ROOT}/scripts/...`. CLAUDE_PLUGIN_ROOT resolves dynamically to the installed plugin's path. The marketplace `source` field is the only static path reference and updates as part of this PR.
**If it flips:** A skill file has a hardcoded path that breaks after move. Smoke test (Step verify) catches it; fix the reference; the move stands. Single-file correction, not architectural.

**Assumption:** Renaming the marketplace from `llm-auditor` to `flow` and plugin from `assumption-auditor` to `flow` doesn't break any existing user installs in a way we have to handle gracefully. Pre-PR-1 installs will simply stop receiving updates until users re-run `/plugin marketplace add by-dev-tools/flow && /plugin install flow@flow`.
**Confidence:** HIGH
**Why:** Anthropic plugins are identified by `marketplace-name@plugin-name`; renaming both ends produces a new identity that the user must opt into. No silent breakage — the old key continues to point at a marketplace key that no longer exists, so the user sees an obvious "update failed" prompt. User is currently the sole consumer; coordinated migration is a one-line settings.json edit.
**If it flips:** Some Claude Code internal caches the old identity in a way that breaks the user's session on next launch. Mitigation: PR body documents the one-line settings.json edit + explicit `/plugin marketplace remove llm-auditor` if needed. The user already has a settings.json backup from PR 0 at `~/.claude/settings.json.bak.20260523-144832`.

**Assumption:** md-manager's `.claude/skills/ship/SKILL.md` (the port source for `/flow:ship`) ports per the locked PR-1 table at ~19% replacement rate (the consolidation doc's metric from the prior closed PR-1 attempt). Specifically: 3a stays active, 3b becomes a placeholder, security+a11y review invocations become placeholders, `typecheckCmd` becomes a loud-warning config slot, doc paths become config slots, default-branch becomes a fallback chain.
**Confidence:** MEDIUM
**Why:** The 19% metric came from a prior agent's port attempt against the SAME source file in a DIFFERENT host repo. The locked port table is stable. But: (a) md-manager's `/ship` source may have evolved since that estimate (I haven't read it yet — fetch + read happens during execution), and (b) edge cases in the port (e.g., new pipeline steps added to `/ship` in md-manager since the estimate) could push the replacement rate higher.
**If it flips:** If replacement exceeds ~30% (the prior re-plan trigger threshold), surface a mid-execution re-plan to the user rather than silently absorb scope. The mitigation pattern is exactly what the prior PR-1 attempt did with the `/simplify`-is-bundled discovery — proposal + approval, not silent expansion. Adds one round-trip; no architectural change.

**Assumption:** The `core-docs/` → `dev-docs/` rename doesn't break any rules/agents/skills under `.claude/` that read from `core-docs/` paths, because we update all references atomically in the same commit as the rename.
**Confidence:** MEDIUM
**Why:** The grep shows `.claude/rules/general.md`, `.claude/agents/*.md`, and `.claude/skills/*/SKILL.md` reference `core-docs/` paths. Atomic update is straightforward in principle, but path references can hide in non-obvious places (e.g., `paths:` frontmatter for rule auto-load, glob patterns in skills' `!` shell-substitution blocks). The risk is a missed reference that silently fails (a rule that no longer auto-loads, a skill whose context-injection cat-fails).
**If it flips:** A project-dev rule or agent stops working correctly in mid-PR. Discovery happens when the agent next tries to invoke that rule/agent during PR 1 execution itself, and the failure mode is visible (rule doesn't load, agent reports cat-error). Mitigation: pre-rename grep + post-rename verification grep + smoke-invoke each updated agent/skill at least once before push. Single-commit reversion is trivial if needed.

**Assumption:** `pre-flow-plugin` tag created against current HEAD (`8857ebd`) is sufficient as the recovery anchor — i.e., users (the user) can run `git checkout pre-flow-plugin` on the merged main branch and see the pre-restructure state.
**Confidence:** HIGH
**Why:** Standard git tag operation; `git push origin pre-flow-plugin` persists the tag remotely. The brief explicitly names this as the recovery mechanism.
**If it flips:** Tag push fails (auth / branch-protection issue). Trivial to retry; surface to user if it persists.

**Assumption:** Moving `.claude-plugin/plugin.json` from repo root to `plugins/flow/.claude-plugin/plugin.json` is the correct Anthropic-pattern shape — i.e., marketplace.json lives at repo root, plugin.json lives inside the plugin's own subdirectory.
**Confidence:** HIGH
**Why:** Verified against `code.claude.com/docs/en/plugin-marketplaces` in the prior consolidation session: marketplace.json at root + `plugins/<name>/.claude-plugin/plugin.json` inside is the explicit pattern. The current flat layout (both manifests at root) was acceptable when there was only ever going to be one plugin; the marketplace pattern formalizes the separation.
**If it flips:** `claude plugin validate .` rejects the new layout. Surface, fix path, re-validate. Single fix, no architectural impact.

**Risks / open questions:**
- **`log_disagreement.py` storage path orphan.** Renaming `~/.claude/plugins/data/assumption-auditor/disagreements/` → `~/.claude/plugins/data/flow/disagreements/` orphans any pre-existing disagreement records on the user's machine. Acceptable: it's local debug/dev data; the user has been the sole consumer; called out in README + PR body so the user can `mv` the old dir manually if they want continuity.
- **`/ship` port may surface unknown coupling.** If the md-manager source has evolved since the prior port-attempt's 19% estimate (e.g., new memory machinery references, new review skills baked in), the port could spill scope. Mitigation per the prior PR-1 pattern: surface re-plan rather than silently absorb. Re-plan trigger threshold is >30% replacement.
- **`/plugin marketplace add` from an unmerged branch.** The brief notes `/tmp/flow-smoke` may not be able to install from an open branch ref. If so, document and proceed; smoke can be re-run post-merge. Don't block PR open on this.
- **The `pre-flow-plugin` tag doesn't exist yet.** Verified empty via `git tag --list` and `gh api repos/by-dev-tools/flow/git/refs/tags` (404). The plan creates it as Step A. If for some reason tag creation fails (auth, branch-protection on tag namespaces), surface to user — the restructure is destructive enough that a recovery anchor is non-negotiable.
- **Marketplace `source` field shape.** The current marketplace.json declares `"source": "./"` because there's only one plugin and it lives at root. After restructure, `source` becomes `"plugins/flow"` (or `metadata.pluginRoot: "./plugins"` + `"source": "flow"` per the consolidation doc's docs-verified pattern). I'll use the `pluginRoot` form per Anthropic's example — cleaner if more plugins ever ship.
- **`spec.md` legacy content.** The current `core-docs/spec.md` describes the assumption-auditor product (audit categories, plugin scope, etc.). After rename to `dev-docs/spec.md`, this content describes flow's *audit-side* legacy product, but flow's broader workflow-plugin identity now exceeds what that spec covers. PR 1 preserves spec.md verbatim under the rename (do not rewrite scope in PR 1 — that's a separate dev-docs hygiene PR if needed). Flag in handoff notes that dev-docs/spec.md will need broadening in a follow-up.

**Files touched (anticipated):**

**Moves (`git mv` — history preserved):**
- `agents/auditor.md` → `plugins/flow/agents/auditor.md`
- `agents/plan-critic.md` → `plugins/flow/agents/plan-critic.md`
- `skills/audit-plan/SKILL.md` → `plugins/flow/skills/audit-plan/SKILL.md`
- `skills/audit-completion/SKILL.md` → `plugins/flow/skills/audit-completion/SKILL.md`
- `skills/critique-plan/SKILL.md` → `plugins/flow/skills/critique-plan/SKILL.md`
- `skills/log-disagreement/SKILL.md` → `plugins/flow/skills/log-disagreement/SKILL.md`
- `scripts/extract_session.py` → `plugins/flow/scripts/extract_session.py`
- `scripts/bounding_logic.py` → `plugins/flow/scripts/bounding_logic.py`
- `scripts/log_disagreement.py` → `plugins/flow/scripts/log_disagreement.py`
- `evals/run_evals.py` → `plugins/flow/evals/run_evals.py`
- `evals/ground_truth.yaml` → `plugins/flow/evals/ground_truth.yaml`
- `evals/fixtures/` → `plugins/flow/evals/fixtures/`
- `DISAGREE.md` → `plugins/flow/DISAGREE.md`
- `.claude-plugin/plugin.json` → `plugins/flow/.claude-plugin/plugin.json`
- `core-docs/plan.md` → `dev-docs/plan.md`
- `core-docs/history.md` → `dev-docs/history.md`
- `core-docs/feedback.md` → `dev-docs/feedback.md`
- `core-docs/spec.md` → `dev-docs/spec.md`
- `core-docs/workflow.md` → `dev-docs/workflow.md`

**Modified (post-move):**
- `.claude-plugin/marketplace.json` (rename names, URLs, source, pluginRoot, version, description)
- `plugins/flow/.claude-plugin/plugin.json` (rename, version bump, URLs, description)
- `plugins/flow/scripts/log_disagreement.py` (storage path rename)
- `README.md` (rewrite for marketplace identity)
- `CLAUDE.md` (update layout references)
- `.claude/rules/safety.md` (update safety-critical path list)
- `.claude/rules/general.md` (`core-docs/` → `dev-docs/`)
- `.claude/agents/{planner,domain,testing,docs}.md` (`core-docs/` → `dev-docs/`)
- `.claude/skills/{ship,preship}/SKILL.md` (`core-docs/` → `dev-docs/`)

**New:**
- `plugins/flow/skills/ship/SKILL.md` (port from md-manager)
- `plugins/flow/docs/workflow.md` (port from md-manager)

**Tag:**
- `pre-flow-plugin` at `8857ebd` (pushed to origin)

**Execution sequence** (each step → its own commit unless trivially small):

1. **Step A — Recovery tag.** `git tag pre-flow-plugin 8857ebd && git push origin pre-flow-plugin`. Verify via `git ls-remote --tags origin`.
2. **Step B — Restructure (move).** `git mv` all 19 file/dir paths above into `plugins/flow/*` and `dev-docs/*`. Move `.claude-plugin/plugin.json` into `plugins/flow/.claude-plugin/plugin.json`. Single commit: "Restructure: hoist plugin artifacts into plugins/flow/; rename core-docs/ → dev-docs/".
3. **Step C — Manifest rename.** Update `.claude-plugin/marketplace.json` and `plugins/flow/.claude-plugin/plugin.json` for `flow` identity + v1.0.0 + by-dev-tools URLs + descriptions. Validate with `jq .` + `claude plugin validate .`. Commit: "Rename marketplace + plugin to flow; bump to 1.0.0".
4. **Step D — log_disagreement storage path.** Edit `plugins/flow/scripts/log_disagreement.py` for the `assumption-auditor` → `flow` storage-dir rename. Commit: "Rename disagreement storage path: assumption-auditor → flow".
5. **Step E — Reference updates under `.claude/`.** Grep + edit all `.claude/rules/`, `.claude/agents/`, `.claude/skills/` references for `core-docs/` → `dev-docs/` and old root paths → `plugins/flow/*`. Commit: "Update project-dev infra path references for restructure".
6. **Step F — Port `/flow:ship`.** Fetch md-manager's `.claude/skills/ship/SKILL.md` via `gh api`. Read it. If replacement rate looks >30%, surface re-plan before writing. Otherwise port per the locked PR-1 table → `plugins/flow/skills/ship/SKILL.md`. Commit: "Add /flow:ship skill (ported from md-manager; PR 2 backfills placeholders)".
7. **Step G — Port `workflow.md`.** Port `/tmp/md-workflow.md` → `plugins/flow/docs/workflow.md` per the de-projection rules above. Commit: "Add canonical workflow.md (de-projected; v1.0.0 scope notes)".
8. **Step H — Rewrite README + CLAUDE.md.** Marketplace identity in README; new layout in CLAUDE.md. Commit: "Rewrite README + CLAUDE.md for flow marketplace identity".
9. **Step I — Manual cold-read pass.** Run greps for md-manager-specific tokens; check for command-injection in `` !`<cmd>` ``; verify no secrets / hardcoded user paths. Apply fixes inline. Commit only if fixes: "Manual review pass: <findings>".
10. **Step J — Verification.** `claude plugin validate .` clean; `jq .` parses both manifests; smoke test in `/tmp/flow-smoke` per the spec-walk checklist. Capture any smoke-test friction in `dev-docs/feedback.md` to surface in PR 2.
11. **Step K — Push + open PR.** `git push -u origin claude/trusting-jackson-0de7f4`; `gh pr create --base main --title "PR 1: Restructure into plugins/flow/; rename to flow@1.0.0; add /flow:ship + workflow.md" --body "..."`. Output PR URL. **Do not merge.**

---

## Recently Completed

- **v0.3.0 — auto-invoked disagreement loop** (PR #3, 2026-04-XX) — see `dev-docs/history.md` (post-rename) for full entry.

## Backlog

(Items below predate the flow extraction; preserved for continuity. Most fold into PR 2 or post-extraction roadmap.)

- Verification skill (sibling plugin) — see prior plan content at `pre-flow-plugin` tag for full context. Reassess after extraction settles.
- Wire `evals/run_evals.py` to live auditor subagent invocation (remove `.expected.txt` stub) — flow-internal eval improvement, post-extraction.
- Capture fixtures for `trio_navigation_stack_cycle_3`, `portfolio_blank_screen`, `trio_morphing_recall`.
- Structured output schema for auditor (replace substring matching in eval checks).
- Expand artifact regex beyond the hardcoded 28-extension list in `plugins/flow/scripts/extract_session.py` (post-restructure path).
- Raise or remove the 50-call tool-history cap in `plugins/flow/scripts/extract_session.py`.
- Generalize hardcoded SwiftUI proxy handling to other frameworks.
- Broaden `dev-docs/spec.md` beyond the audit-only scope to cover flow's full workflow-plugin identity (follow-up hygiene PR after extraction).
