# PR 2 — Flow plugin workflow surface backfill (handoff plan)

**Status:** ready for next session pickup
**Repo:** `by-dev-tools/flow`, off `main` (currently squash commit `f8610a1`)
**Target version:** v1.0.0 → v1.1.0 (additive; no breaking changes)
**Mode:** feature
**Estimated phases:** 8 (Phases 1–7 ship the plugin; Phase 8 publishes the md-manager handoff that unblocks PRs 4–6)

This document is the comprehensive starting plan for PR 2 of the Flow plugin extraction umbrella. The next session reads this, refines it through their own plan-approval gate (per the workflow loop's Step 2), then executes Phases 1–8 against the success criteria below. Each phase has explicit, verifiable success criteria — the next session can check progress objectively rather than self-grading.

---

## Goal

Backfill the `[PR 1 LIMITATION]` placeholders inside `plugins/flow/skills/ship/SKILL.md` (security + a11y review invocations; memory machinery in step 4b) and port the rest of the workflow surface from `by-dev-tools/md-manager` so the plugin becomes a complete end-to-end workflow loop, not just an audit/critique + ship pipeline. After PR 2 merges, a consumer project with `flow.config.json` set should be able to run the full 11-step loop using only `/flow:*` skills + bundled native skills (`/simplify`, etc.).

PR 2 also addresses the two FOLLOW-UPs that PR 1's walk-through-the-loop review surfaced and quoted verbatim in `dev-docs/plan.md` § "PR 2 follow-ups from PR 1 review."

---

## Scope (in)

**New workflow skills (5 ports + 1 new):**
- `plugins/flow/skills/staff-review/SKILL.md` — four-lens parallel review (engineer / UX-designer / design-engineer / push-further). Spawns lens agents via the `Agent` tool with `subagent_type` pointing at the new lens-agent files (see "Agents" below). De-projected: strip md-manager-specific token references (`--sand-*`, `Mini`, etc.); reference design-system conventions via config slots.
- `plugins/flow/skills/security-review/SKILL.md` — diff-focused security audit. De-projected.
- `plugins/flow/skills/accessibility-review/SKILL.md` — diff-focused WCAG 2.1 AA audit. De-projected. Honors a `flow.config.json.uiSurface` boolean so non-UI projects can declare it doesn't apply (or the skill self-detects via diff inspection).
- `plugins/flow/skills/ship-spike/SKILL.md` — lightweight ship pipeline for `mode: spike` PRs. Inherits the PR-1 patterns from `/flow:ship` (default-branch fallback chain, config-slot doc paths).
- `plugins/flow/skills/workflow-help/SKILL.md` — new skill that prints the canonical 11-step loop on demand. Reads from `plugins/flow/docs/workflow.md` and pretty-prints the cheat-sheet + the current `flow.config.json` slot values. Lightweight; ~50 lines.

**New context-isolation agents (2 ports + 4 lens-agent extractions):**
- `plugins/flow/agents/planner.md` — port from md-manager; refactor to read doc paths from `flow.config.json` via env (`$FLOW_PLAN_PATH` style or a fetch-config helper) rather than hardcoding `core-docs/`.
- `plugins/flow/agents/docs.md` — port from md-manager; same config-slot refactor.
- `plugins/flow/agents/lens-staff-engineer.md` — **extract** from md-manager's `staff-review/SKILL.md` (the four lens prompts are embedded inline in md-manager's pattern — 14.3KB single file). PR 2 splits them into separate agent files so the staff-review SKILL can spawn each via `Agent` tool's `subagent_type` parameter rather than carrying ~3KB of inline prompt per lens.
- `plugins/flow/agents/lens-ux-designer.md` — extract from the same source.
- `plugins/flow/agents/lens-design-engineer.md` — extract from the same source.
- `plugins/flow/agents/lens-push-further.md` — extract from the same source.

(Optional `plugins/flow/agents/lens-uncommon-care.md` is gated by `flow.config.json.reviewLenses` slot — port only if md-manager has the source file. Per current md-manager state, `.claude/agents/` only contains `planner.md` and `docs.md` — the `uncommon-care` lens lives in a separate skill `/uncommon-care` per md-manager's `core-docs/plan.md`; defer porting to v1.2 unless the PR 2 session finds time.)

**Portable rules (4 ports, plugin-shipped versions):**
- `plugins/flow/rules/general.md` — port from md-manager; strip project-specific references; doc paths via config slots.
- `plugins/flow/rules/plan-discipline.md` — port; same treatment.
- `plugins/flow/rules/documentation.md` — port; same treatment.
- `plugins/flow/rules/exploration.md` — port; same treatment.

**New tools:**
- `plugins/flow/tools/memory/check.mjs` — port from md-manager (~6.1KB, already generic per the consolidation doc). Verify canonical-path derivation works for plugin-at-user-scope vs consumer-at-project-scope (consolidation doc Risk #3).

**New schema:**
- `plugins/flow/schema/flow.config.schema.json` — JSON Schema for `flow.config.json`. Documents every slot (existing + new), built-in defaults, deprecation policy. Omits `$schema` URL per Anthropic convention (no canonical URL).

**New hooks:**
- `plugins/flow/hooks/default-hooks.json` — minimum: path-validation hook for any `tools/*` script that resolves filesystem paths (the rule that would have caught PR 1's `extract_session.py --reference-paths` FOLLOW-UP before the security lens did). Document opt-in/opt-out semantics in the schema.

**Backfill `/flow:ship`:**
- Replace the `[PR 1 LIMITATION]` block in step 2 with: sequential invocation of `/flow:security-review` and `/flow:accessibility-review` via the Skill tool; self-triage; apply BLOCKER + cheap NIT fixes in-tree; return FOLLOW-UP findings to step 3 routing.
- Replace the `[PR 1 LIMITATION]` block in step 4b with: invoke `${CLAUDE_PLUGIN_ROOT}/tools/memory/check.mjs` for corpus-size check; apply the source-diversity bar against this PR's findings; resolve contradictions with the feedback doc; write new entries to `~/.claude/projects/<canonical>/memory/feedback_<name>.md`; update fire logs; flag 2+ fires as promotion candidates; trigger fresh-context audit if `--audit-due` exits 1.

**Address the 2 PR-1 FOLLOW-UPs** (quoted verbatim in `dev-docs/plan.md` § "PR 2 follow-ups from PR 1 review"):
1. **`critique-plan/SKILL.md` hardcoded reference-glob.** Currently `--reference-glob "core-docs/*.md"` breaks when flow runs `/flow:critique-plan` on itself (flow uses `dev-docs/`). Fix: add `flow.config.json.referenceGlob` slot (default chain: project's slot → consumer projects use `core-docs/*.md` if unset → flow's own repo overrides to `dev-docs/*.md`); modify `critique-plan/SKILL.md` to read the slot at invocation; document in the schema.
2. **`extract_session.py --reference-paths` cwd constraint.** Currently `gather_reference_docs` reads any absolute path the caller passes. Fix: constrain to `cwd` (reject resolved paths outside `Path.cwd()`) unless an explicit `--allow-external-paths` override flag is set. Document the trust model in the script docstring + the schema. Pairs with the path-validation hook from `default-hooks.json`.

**Version + manifests:**
- Bump `plugins/flow/.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json` metadata.version: 1.0.0 → 1.1.0.
- Update plugin.json description to cover the full workflow surface (not just audit/critique + ship).

**Md-manager handoff publication (Phase 8):**
- Write `dev-docs/handoffs/md-manager-pr4-6-spec.md` (the document already prepared at this same path — Phase 8 verifies it's complete + accurate against PR 2's actual shipped surface, then commits + pushes so the md-manager session can fetch it via `gh api`).

---

## Scope (out)

- **Template directory** (`template/base/` + per-stack overlays for web / swift / tauri-rust-ts) — **PR 3**.
- **Md-manager-side install / dogfood / deletion** (PRs 4 / 5 / 6 of the umbrella) — separate sessions in `by-dev-tools/md-manager` worktrees; PR 2's only md-manager-side artifact is publishing the spec at `dev-docs/handoffs/md-manager-pr4-6-spec.md` (lives in flow's repo; md-manager session fetches via `gh api`).
- **Bundled Claude Code native skills**: `/simplify`, `/batch`, `/debug`, `/loop`, `/claude-api` — never re-port; reference as "(bundled with Claude Code)" when mentioned.
- **v1.x+ post-extraction features** — autonomous routines (v1.1 in the post-extraction roadmap; not the same numbering as the umbrella's PR 1/2/3), JTBD substrate (v1.2), plan visuals (v1.3), design lenses (v1.4), HTML reports (v1.5), Chrome-driven preview (v1.6), and beyond. All deferred.
- **Mini design system extraction** — stays in md-manager; separate plugin work later.
- **Changes to the workflow loop itself** — extraction preserves current behavior; loop redesign happens in separate PRs.
- **UserPromptSubmit hook for deterministic enforcement** — design in PR 2 but ship only as opt-in (consumer enables via template's `settings.json.example` in PR 3); default behavior stays model-invocation + CLAUDE.md stub.

---

## Locked patterns from PR 1 (idioms — match exactly; don't re-derive)

These were locked during PR 1's walk-through-the-loop review. The PR 2 session must match them in every new shipped artifact. The PR 1 cold-read missed two cases of these and the engineer lens caught them — don't repeat the same misses.

1. **Cross-file path references in shipped prompts use `${CLAUDE_PLUGIN_ROOT}/...`** — never bare relative paths like `agents/auditor.md`. Dynamic resolution works regardless of install location. (Grep your own diff before commit: `git diff origin/main...HEAD | grep -nE '\`(agents|skills|scripts|evals|tools|schema|hooks)/' | grep -v CLAUDE_PLUGIN_ROOT` — should return empty.)
2. **Config-slot shell commands use `sh -c "$VAR"`, never `eval "$VAR"`** — subshell isolation. Add a comment naming the trust boundary at the call site.
3. **Unset config slots print a loud `⚠️` warning, never silently no-op** — false-affordance risk. Pattern: `⚠️ flow.config.json.<slot> not set; <consequence>. Set this slot to <enable>.`
4. **Default-branch resolution uses the 3-tier fallback** — `git symbolic-ref refs/remotes/origin/HEAD` → `flow.config.json.defaultBranch` → literal `main`. Used in `/flow:ship` + `/flow:ship-spike` PR creation.
5. **Doc paths come from config slots** with built-in defaults — `flow.config.json.{history,plan,roadmap,spec,feedback}Path`. Defaults for flow's own repo: `dev-docs/<name>.md`. Defaults for consumer projects: `core-docs/<name>.md`.
6. **Marketplace `source` is absolute (`./plugins/flow`), no `metadata.pluginRoot`** — pick one form, keep it clean. PR 1 had both initially; engineer lens caught the ambiguity.
7. **No md-manager-specific tokens** in plugin artifacts. Pre-commit grep recipe: `grep -rEni 'md-manager|pattaya|sand-|--space-|geist|mini|--accent-' plugins/ schema/ hooks/ rules/ docs/` — should return empty (modulo `${CLAUDE_PLUGIN_ROOT}` constructions and intentional namespace-tag references).
8. **Per-phase commits with co-author trailer** — `Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>`. Commit message explains "why," not "what." Makes the loop-walk review trivially traversable (one of PR 1's load-bearing lessons).

---

## Bootstrap exception status (partially lifted)

PR 1 couldn't dogfood because none of the review skills existed. **PR 2 is the first PR where the loop is real.** `/flow:staff-review`, `/flow:security-review`, `/flow:accessibility-review` are being BUILT in PR 2 itself — by the end of execution they exist and the PR should walk itself through them.

Required: at Phase 6 (post-Phase-5 build), spawn the four lens agents on the PR diff via `Agent` tool calls (each with `subagent_type` pointing at the new lens-agent file). Invoke `/flow:security-review` and `/flow:accessibility-review` on the PR diff via Skill. Apply BLOCKER + cheap NIT fixes inline. Route FOLLOW-UPs to `dev-docs/plan.md`. **This is the first PR where the user shouldn't have to catch BLOCKERs the agent missed** — the agent does the loop on itself.

---

## Phased execution + per-phase success criteria

Each phase ends with one commit (or 2–3 cohesive commits if the phase is large). Success criteria are objectively verifiable — the next session should be able to check them with grep / jq / claude plugin validate / smoke install, not subjective judgment.

### Phase 1 — Setup + fetch sources + draft plan

**Work:**
- Verify worktree state: branched off `origin/main` at SHA `f8610a1`; `claude plugin validate .` exits clean (baseline).
- Fetch port sources via `gh api repos/by-dev-tools/md-manager/contents/<path> --jq '.content' | base64 -d` for each of:
  - `.claude/skills/staff-review/SKILL.md` (~14.3KB, contains 4 embedded lens prompts that get extracted in Phase 3)
  - `.claude/skills/security-review/SKILL.md` (~5.6KB)
  - `.claude/skills/accessibility-review/SKILL.md` (~6.2KB)
  - `.claude/skills/ship-spike/SKILL.md` (~6.8KB)
  - `.claude/agents/planner.md` (~2.6KB)
  - `.claude/agents/docs.md` (~3.5KB)
  - `.claude/rules/general.md` (~6.0KB)
  - `.claude/rules/plan-discipline.md` (~3.4KB)
  - `.claude/rules/documentation.md` (~3.4KB)
  - `.claude/rules/exploration.md` (~3.0KB)
  - `tools/memory/check.mjs` (~6.1KB)
- Draft the per-PR plan into `dev-docs/plan.md` as the active work item. Refine THIS handoff plan with any changes discovered during source-read.
- Surface plan to user; wait for explicit "approved."

**Success criteria:**
- [ ] All 11 source files fetched into a session-scratch directory (e.g., `/tmp/pr2-sources/`); `wc -l` matches the expected sizes within ±10%.
- [ ] `dev-docs/plan.md` has a new "PR 2 — Workflow surface backfill" Active Work Item with mode, goal, scope, spec-walk checkboxes bound to per-phase success criteria, confidence verdicts per load-bearing assumption (minimum 4: staff-review-lens-extraction-works, memory-tool-path-derivation, security-review-port-rate-under-30pct, schema-shape-captures-all-slots), risks, files touched.
- [ ] User has explicitly responded "approved" (or has redirected and the plan is updated to reflect that).
- [ ] No file edits outside `dev-docs/plan.md` in Phase 1.

### Phase 2 — Port `/flow:security-review` + `/flow:accessibility-review`

**Why these first:** they're the simplest skills to port (smallest, no orchestration), and `/flow:ship`'s step-2 backfill needs them existing.

**Work:**
- Port `security-review/SKILL.md` → `plugins/flow/skills/security-review/SKILL.md`. De-project (strip md-manager-specific references). Apply locked PR-1 patterns: `${CLAUDE_PLUGIN_ROOT}` for any cross-file refs; config-slot doc paths; loud-warning where applicable.
- Port `accessibility-review/SKILL.md` → `plugins/flow/skills/accessibility-review/SKILL.md`. Same de-projection. Add `flow.config.json.uiSurface` slot read: if `false`, the skill exits early with a clean "no UI surface declared; skipping" message rather than running an empty audit.
- Commit per skill (2 commits).

**Success criteria:**
- [ ] `plugins/flow/skills/security-review/SKILL.md` exists; `head -1` shows YAML frontmatter; `name: security-review` field present.
- [ ] `plugins/flow/skills/accessibility-review/SKILL.md` exists with same shape.
- [ ] `grep -rEni 'md-manager|pattaya|sand-|--space-|geist|mini' plugins/flow/skills/security-review plugins/flow/skills/accessibility-review` returns empty.
- [ ] Both SKILL.md files reference cross-plugin paths (if any) via `${CLAUDE_PLUGIN_ROOT}/...`, not bare `agents/...` / `scripts/...`. Verify: `grep -nE '\`(agents|skills|scripts|evals|tools)/' plugins/flow/skills/security-review/SKILL.md plugins/flow/skills/accessibility-review/SKILL.md | grep -v CLAUDE_PLUGIN_ROOT` returns empty.
- [ ] `claude plugin validate .` still exits clean.
- [ ] Local smoke test: `claude --plugin-dir ./plugins/flow --print "/help" 2>&1 | grep -E 'flow:(security|accessibility)-review'` returns both lines.

### Phase 3 — Extract the 4 staff-review lens agents

**Work:**
- Read md-manager's `staff-review/SKILL.md` carefully. The 4 lens prompts are in §§ "Staff engineer", "Staff UX designer", "Staff design engineer", and "Push further" (or similar — confirm by reading source).
- For each lens, extract the prompt into a new agent file:
  - `plugins/flow/agents/lens-staff-engineer.md` — frontmatter `name: lens-staff-engineer`, `description: <brief lens summary>`; body is the extracted prompt, with the input-section paragraph (where the source described "Hunts: ..." and "Specifically asks:") preserved verbatim. De-project: any md-manager-specific examples (e.g., `--sand-*`, `Mini`, `src/store.tsx`) replaced with generic "tokens from the project's design-language doc" or removed.
  - `plugins/flow/agents/lens-ux-designer.md` — same treatment.
  - `plugins/flow/agents/lens-design-engineer.md` — same treatment.
  - `plugins/flow/agents/lens-push-further.md` — same treatment. The push-further lens has the "Nothing to push — surface at ceiling" escape hatch; preserve that verbatim.
- Each lens agent file ends with a standard output-format section (BLOCKER / NIT / FOLLOW-UP / EXPLORATION triage) matching md-manager's pattern.
- Commit per lens (4 commits) OR single commit with all 4 if the extractions are small (~2-3 KB each).

**Success criteria:**
- [ ] All 4 lens agent files exist under `plugins/flow/agents/lens-*.md`.
- [ ] Each file has valid YAML frontmatter parseable by `python3 -c "import yaml,sys; yaml.safe_load(open(sys.argv[1]).read().split('---',2)[1])" plugins/flow/agents/lens-staff-engineer.md` (repeat for each).
- [ ] `grep -rEni 'md-manager|pattaya|--sand-|--space-|geist|mini|src/store|src/components' plugins/flow/agents/lens-*.md` returns empty.
- [ ] Each agent file ends with an output-format section that includes the BLOCKER/NIT/FOLLOW-UP/EXPLORATION triage labels (grep each for all four words).
- [ ] Push-further lens preserves the "Nothing to push" escape hatch (grep for "Nothing to push" or "surface at ceiling" in `lens-push-further.md`).

### Phase 4 — Port `/flow:staff-review` (4-lens parallel orchestration)

**Work:**
- Port `staff-review/SKILL.md` → `plugins/flow/skills/staff-review/SKILL.md`. The body shrinks significantly from md-manager's 14.3KB because the 4 lens prompts moved to Phase 3's agent files; the SKILL is now an orchestrator.
- Orchestration pattern: single tool message with 4 parallel `Agent` tool calls, each with `subagent_type: "lens-staff-engineer"` (or the corresponding lens). Each agent receives the same diff context (computed via `!\`git diff origin/$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@' || echo main)...HEAD\``) and produces independent findings.
- The orchestrator triages all 4 reports' findings into the standard BLOCKER / NIT / FOLLOW-UP / EXPLORATION buckets, applies BLOCKER + cheap NIT fixes in-tree, routes FOLLOW-UPs to `flow.config.json.{planPath,roadmapPath}` (defaults `dev-docs/plan.md` / `dev-docs/roadmap.md`), routes EXPLORATIONs to `flow.config.json.roadmapPath` § Exploration.
- "Skip a lens with reason" pattern: if a lens genuinely doesn't apply (e.g., backend-only change → no design-engineer surface), the SKILL must explicitly say so rather than running an empty review. Match md-manager's pattern.
- Commit single.

**Success criteria:**
- [ ] `plugins/flow/skills/staff-review/SKILL.md` exists; file size is meaningfully smaller than md-manager's 14.3KB source (target: <8KB; the lens prompts moved out).
- [ ] The SKILL body contains a single multi-tool-call block spawning 4 `Agent` calls in parallel (look for 4 contiguous `subagent_type: "lens-..."` strings near each other).
- [ ] Each of the 4 `subagent_type` values references a file that exists under `plugins/flow/agents/`.
- [ ] `grep -rEni 'md-manager|pattaya|--sand-|--space-|geist|mini' plugins/flow/skills/staff-review/SKILL.md` returns empty.
- [ ] `grep -nE '\`(agents|skills|scripts|evals|tools)/' plugins/flow/skills/staff-review/SKILL.md | grep -v CLAUDE_PLUGIN_ROOT` returns empty.
- [ ] Local smoke test: `claude --plugin-dir ./plugins/flow --print "/help" 2>&1 | grep 'flow:staff-review'` returns the line.
- [ ] `claude plugin validate .` still exits clean.

### Phase 5 — Port the rest: `/flow:ship-spike`, `/flow:workflow-help`, planner + docs agents, 4 rules, tools/memory, schema, hooks

**Work (5a — skills):**
- Port `ship-spike/SKILL.md` → `plugins/flow/skills/ship-spike/SKILL.md`. Apply all locked PR-1 patterns (default-branch fallback chain, config-slot doc paths, loud warnings for unset slots).
- Write new `plugins/flow/skills/workflow-help/SKILL.md` — frontmatter `name: workflow-help`, `description: "Print the canonical 11-step flow loop and current project config slots."`, `disable-model-invocation: false`. Body: reads `${CLAUDE_PLUGIN_ROOT}/docs/workflow.md` and `flow.config.json` and pretty-prints a cheat-sheet + slot values.

**Work (5b — agents):**
- Port `planner.md` → `plugins/flow/agents/planner.md`. Doc-path references (`core-docs/plan.md`, etc.) → config-slot reads via env or fetch-helper.
- Port `docs.md` → `plugins/flow/agents/docs.md`. Same treatment.

**Work (5c — rules):**
- Port `general.md` → `plugins/flow/rules/general.md`. Strip md-manager-specific references. Doc paths via config slots.
- Port `plan-discipline.md` → `plugins/flow/rules/plan-discipline.md`. Same treatment.
- Port `documentation.md` → `plugins/flow/rules/documentation.md`. Same treatment.
- Port `exploration.md` → `plugins/flow/rules/exploration.md`. Same treatment.

**Work (5d — tools/memory):**
- Port `tools/memory/check.mjs` → `plugins/flow/tools/memory/check.mjs`. Verify canonical-path derivation handles plugin-at-user-scope vs consumer-at-project-scope correctly (consolidation doc Risk #3): the script must compute the project's canonical memory path the same way Claude Code computes the project root, regardless of where the plugin itself is installed. Test in Phase 6 dogfood.

**Work (5e — schema):**
- Write `plugins/flow/schema/flow.config.schema.json` documenting every slot:
  - `defaultBranch` (string, default discovered via `git symbolic-ref`)
  - `typecheckCmd` (string, no default — loud-warning if unset)
  - `historyPath` (string, default `dev-docs/history.md` for flow's own repo / consumer-side typically `core-docs/history.md`)
  - `planPath` (string, similar default chain)
  - `roadmapPath` (string, similar)
  - `specPath` (string, similar)
  - `feedbackPath` (string, similar)
  - `referenceGlob` (string, default `core-docs/*.md` — addresses PR-1 FOLLOW-UP #1; flow's own repo overrides to `dev-docs/*.md`)
  - `uiSurface` (boolean, default `true` — declares whether `/flow:accessibility-review` applies)
  - `reviewLenses` (array of strings, default `["staff-engineer","ux-designer","design-engineer","push-further"]` — drives which lens agents `/flow:staff-review` spawns; future addition `uncommon-care` opt-in)
  - `memoryHardCap` (integer, default 30)
- Omit `$schema` URL reference per Anthropic convention.

**Work (5f — hooks):**
- Write `plugins/flow/hooks/default-hooks.json`. Minimum: a `PreToolUse` hook on `Bash` that runs a path-validation check for any `tools/*` script invocation that takes a path argument. Addresses PR-1 FOLLOW-UP #2 in the hook layer (complementing the in-script `cwd` constraint).
- Document opt-in semantics: consumers enable via `template/settings.json.example` in PR 3.

**Work (5g — manifest bump):**
- Update `plugins/flow/.claude-plugin/plugin.json`: `version: "1.0.0"` → `"1.1.0"`, description expanded to cover workflow surface.
- Update `.claude-plugin/marketplace.json`: `metadata.version: "1.0.0"` → `"1.1.0"`, plugin `version: "1.0.0"` → `"1.1.0"`.

**Commits:** 7 (5a/5b/5c/5d/5e/5f/5g), OR cluster as 4 (5a, 5b+5c, 5d+5e+5f, 5g) for review density.

**Success criteria (cumulative across 5a–5g):**
- [ ] All 9 new shipped artifacts exist:
  - `plugins/flow/skills/ship-spike/SKILL.md`
  - `plugins/flow/skills/workflow-help/SKILL.md`
  - `plugins/flow/agents/planner.md`
  - `plugins/flow/agents/docs.md`
  - `plugins/flow/rules/general.md`
  - `plugins/flow/rules/plan-discipline.md`
  - `plugins/flow/rules/documentation.md`
  - `plugins/flow/rules/exploration.md`
  - `plugins/flow/tools/memory/check.mjs`
  - `plugins/flow/schema/flow.config.schema.json`
  - `plugins/flow/hooks/default-hooks.json`
- [ ] `jq . plugins/flow/schema/flow.config.schema.json` parses clean and lists all 11 slots documented above.
- [ ] `jq . plugins/flow/hooks/default-hooks.json` parses clean.
- [ ] `node --check plugins/flow/tools/memory/check.mjs` exits clean (syntax).
- [ ] `node plugins/flow/tools/memory/check.mjs --help` (or no-arg invocation) runs without crashing on a project with no memory dir yet.
- [ ] `jq -r '.version' plugins/flow/.claude-plugin/plugin.json` returns `"1.1.0"`.
- [ ] `jq -r '.metadata.version, .plugins[0].version' .claude-plugin/marketplace.json` returns two `"1.1.0"` lines.
- [ ] `claude plugin validate .` exits clean.
- [ ] `grep -rEni 'md-manager|pattaya|--sand-|--space-|geist|mini|src/store|src/components' plugins/flow/{skills,agents,rules,tools,schema,hooks}/` returns empty (sweep across all new artifacts).
- [ ] `grep -rnE '\`(agents|skills|scripts|evals|tools|schema|hooks|rules|docs)/' plugins/flow/{skills,agents,rules}/ | grep -v CLAUDE_PLUGIN_ROOT | grep -v "^Binary"` returns empty.
- [ ] Local smoke test: `claude --plugin-dir ./plugins/flow --print "/help" 2>&1 | grep -E 'flow:(ship-spike|workflow-help)'` returns both lines.

### Phase 6 — Backfill `/flow:ship` placeholders + address PR-1 FOLLOW-UPs

**Work (6a — `/flow:ship` step 2 backfill):**
- In `plugins/flow/skills/ship/SKILL.md`, replace the `[PR 1 LIMITATION]` block in `## 2. Final-pass reviews` with: sequential invocation of `/flow:security-review` and `/flow:accessibility-review` via the Skill tool. Each reviewer self-triages and applies BLOCKER + cheap NIT fixes in-tree; returns FOLLOW-UP findings to step 3 for routing.
- Update the SKILL.md `allowed-tools` frontmatter to include `Skill` (if not already).

**Work (6b — `/flow:ship` step 4b backfill):**
- In `plugins/flow/skills/ship/SKILL.md`, replace the `[PR 1 LIMITATION]` block in `### 4b. Agent self-feedback → failure-pattern memory` with the full memory machinery flow per md-manager's `/ship` step 3b. Reference the memory tool via `${CLAUDE_PLUGIN_ROOT}/tools/memory/check.mjs`.

**Work (6c — PR-1 FOLLOW-UP #1: critique-plan reference-glob):**
- In `plugins/flow/skills/critique-plan/SKILL.md`, replace the hardcoded `--reference-glob "core-docs/*.md"` with a config-slot read. Pattern: `!\`REFGLOB=$(cat flow.config.json 2>/dev/null | jq -r '.referenceGlob // empty'); if [ -z "$REFGLOB" ]; then REFGLOB="core-docs/*.md"; fi; python3 ${CLAUDE_PLUGIN_ROOT}/scripts/extract_session.py --mode plan --reference-glob "$REFGLOB"\``.
- Verify it works when run from flow's own repo (where `flow.config.json.referenceGlob` should be `"dev-docs/*.md"`).

**Work (6d — PR-1 FOLLOW-UP #2: extract_session.py cwd constraint):**
- In `plugins/flow/scripts/extract_session.py`, modify `gather_reference_docs` to reject any resolved path outside `Path.cwd()` unless an `--allow-external-paths` flag is passed. Update CLI argparse. Document the trust model in the function docstring.
- Add unit-test-equivalent: a one-shot Python invocation that verifies a `../../../etc/passwd`-style path is rejected with a non-zero exit + clear error.

**Commits:** 4 (6a/6b/6c/6d) OR 2 (ship-backfill + followups) — caller's judgment.

**Success criteria:**
- [ ] `grep -c "PR 1 LIMITATION" plugins/flow/skills/ship/SKILL.md` returns `0` (both placeholders gone).
- [ ] `grep -n "/flow:security-review\|/flow:accessibility-review" plugins/flow/skills/ship/SKILL.md` shows step-2 invocations.
- [ ] `grep -n "tools/memory/check.mjs" plugins/flow/skills/ship/SKILL.md` shows memory-tool invocation in step 4b.
- [ ] `grep -n "referenceGlob" plugins/flow/skills/critique-plan/SKILL.md` shows the config-slot read.
- [ ] `grep -c "core-docs/\*.md" plugins/flow/skills/critique-plan/SKILL.md` is `1` (only as the fallback default, not as the hardcoded value).
- [ ] `python3 plugins/flow/scripts/extract_session.py --mode plan --reference-paths /etc/passwd 2>&1` exits non-zero with an explicit "outside cwd" error message (unless `--allow-external-paths` is passed).
- [ ] All previous Phase-5 success criteria still hold (`claude plugin validate .` clean; no md-manager tokens; no bare path refs).

### Phase 7 — Dogfood: walk PR 2 through the newly-built loop

**Why this phase exists:** Bootstrap exception is partially lifted (per "Bootstrap exception status" above). PR 2 is the first PR where `/flow:staff-review`, `/flow:security-review`, `/flow:accessibility-review` exist by end of execution. Use them on this PR's own diff before pushing.

**Work:**
- Local smoke test: `claude --plugin-dir ./plugins/flow --print "/help"` lists all expected `flow:*` skills (target: 9 total — audit-plan, audit-completion, critique-plan, log-disagreement, ship, security-review, accessibility-review, staff-review, ship-spike, workflow-help — that's 10 actually; verify count matches the SKILL files in `plugins/flow/skills/`).
- Invoke `/flow:staff-review` on the PR diff via Claude (or emulate by spawning the 4 lens agents in parallel via `Agent` tool with `subagent_type: lens-*` — same orchestration the SKILL itself does). Triage findings.
- Invoke `/flow:security-review` on the PR diff. Triage findings.
- Invoke `/flow:accessibility-review` on the PR diff. If the SKILL exits early due to `uiSurface: false`, document that's expected for this repo.
- Apply all BLOCKER + cheap NIT findings inline. Route FOLLOW-UPs to `dev-docs/plan.md`.
- Single commit covering all dogfood-driven fixes.

**Success criteria:**
- [ ] At least 3 of the 4 review skills were invoked on the PR diff (`/flow:accessibility-review` may legitimately skip if `uiSurface` is false; document why).
- [ ] All BLOCKER findings have corresponding fix commits, OR a written explanation of why each was reclassified as NIT / FOLLOW-UP.
- [ ] Any new FOLLOW-UPs are quoted verbatim in `dev-docs/plan.md` under a "PR 3 follow-ups from PR 2 review" section (analogous to PR 1's pattern).
- [ ] `claude plugin validate .` still exits clean post-fixes.
- [ ] If the dogfood surfaced a real bug (BLOCKER caught that pre-merge cold-read missed), it's logged in the eventual `dev-docs/history.md` Phase-8 entry's "Lessons learned" section.

### Phase 8 — Doc synthesis + open PR + publish md-manager handoff

**Work (8a — invoke `/flow:ship`):**
- Now that `/flow:ship` is fully backfilled (no more `[PR 1 LIMITATION]` blocks), invoke it on the PR. The skill will run security + a11y final-pass reviews, synthesize user feedback into `dev-docs/feedback.md`, write the failure-pattern memory entry to `~/.claude/projects/.../memory/feedback_*.md` (if the source-diversity bar holds), update `dev-docs/{history,plan,roadmap,spec}.md`, commit, push, open the PR. **Or run the pipeline manually** if `/flow:ship`'s self-invocation hits any rough edges (this is the first real invocation of the backfilled version; expect minor issues to surface and fix forward).

**Work (8b — verify md-manager handoff spec):**
- Read `dev-docs/handoffs/md-manager-pr4-6-spec.md` (the document already prepared in this PR's docs-only precursor at flow's `docs/pr2-handoffs` branch; merged to main before PR 2 started).
- Verify the spec is accurate against PR 2's actual shipped surface: does the consumer-side `flow.config.json` example align with the final v1.1.0 schema? Does the PR-6 deletion list match the skills that md-manager actually has? If PR 2 surfaced any new follow-ups affecting PRs 4–6, update the spec.
- If updates needed: commit the spec changes to PR 2.

**Work (8c — PR open):**
- Push `pr2-workflow-backfill` (or whatever branch name the next session chose); open PR against `main` via `gh pr create`. Body includes: summary, what shipped (all 13 new artifacts + backfills + FOLLOW-UP fixes + version bump), intentionally NOT in this PR (PR 3 = template, PRs 4–6 = md-manager), review-pass findings caught + fixed in Phase 7, FOLLOW-UPs routed to `dev-docs/plan.md`, required user follow-up after merge (re-validate `~/.claude/settings.json` if anything changed about `flow@flow` registration), test plan.

**Work (8d — never merge):**
- User merges. Period.

**Success criteria:**
- [ ] PR is open against `main`; URL captured.
- [ ] PR body has the standard PR-1-shape sections (Summary / What ships / Intentionally NOT in / Review pass findings / Test plan / Required follow-up / Next).
- [ ] `dev-docs/history.md` has a new top entry covering PR 2 with decisions + tradeoffs + lessons learned (the `/flow:ship` step-4 output).
- [ ] `dev-docs/plan.md` Current Focus advances to "PR 3 next" (template directory). PR 2 active work item is marked SHIPPED.
- [ ] `dev-docs/feedback.md` has any new FB-XXXX entries the session surfaced.
- [ ] `dev-docs/handoffs/md-manager-pr4-6-spec.md` exists at `main` and has been verified accurate against PR 2's shipped surface (any drift fixed via commit before push).
- [ ] PR is MERGEABLE per `gh pr view <num> --json mergeable --jq .mergeable`.
- [ ] No `gh pr merge` command was ever executed in this session.

---

## Confidence verdicts (per load-bearing assumption)

**Assumption:** Extracting md-manager's 4 inline lens prompts into separate agent files (Phase 3) preserves their review behavior, because the prompts are the load-bearing content and the SKILL → `Agent` tool dispatch is a structural refactor that doesn't change what each lens reads or produces.
**Confidence:** MEDIUM
**Why:** The extraction is mechanically straightforward (copy prompt text into new agent file with frontmatter wrapper). But md-manager's inline pattern may rely on the SKILL.md's surrounding context (the introductory paragraphs about "Why four perspectives, in parallel" etc.) priming each lens — context that wouldn't transfer if the agent files are read in isolation. Risk: lens behavior subtly drifts.
**If it flips:** Each lens agent file gets a fuller preamble at the top (extracted from the SKILL.md's framing sections) so each agent has the same priming the inline version had. Or, fall back to keeping prompts inline in the SKILL.md and not creating separate agent files — at the cost of less modular review-lens invocation. Single-commit reversion if needed.

**Assumption:** `plugins/flow/tools/memory/check.mjs` canonical-path derivation works for both plugin-at-user-scope and consumer-at-project-scope without modification (it's already "generic" per the consolidation doc).
**Confidence:** MEDIUM
**Why:** The consolidation doc claims it's generic, but that claim was made before flow shipped — no one's tested the actual cross-scope case. The script likely derives the project canonical path from `process.cwd()` or `git rev-parse --show-toplevel`, both of which work consumer-side; plugin-side it may need to read an env var Claude Code injects (`$CLAUDE_PROJECT_ROOT` or similar).
**If it flips:** Adapt the path-derivation logic to read whatever Claude Code provides for project-root context; document the env-var contract in the script docstring + the schema. Surface at Phase 5d smoke test.

**Assumption:** `/flow:staff-review`'s 4-parallel `Agent` tool spawn pattern works inside plugin context the same way md-manager's local Task-based spawn works.
**Confidence:** MEDIUM
**Why:** md-manager's SKILL.md says "Each is a separate `Agent` call ... in **a single tool message with multiple tool uses**" — that's Claude Code's standard parallel-tool-call pattern, which IS supported in plugin context. But the indirection through `subagent_type` pointing at a plugin-shipped agent file (rather than md-manager's inline-prompt pattern) hasn't been smoke-tested in plugin context yet.
**If it flips:** Two fallbacks: (a) move lens prompts back inline in the SKILL body and abandon the agent-extraction (same as the previous assumption's fallback); (b) replace `subagent_type: "lens-staff-engineer"` with a more explicit `Agent` invocation form that reads the agent file via `${CLAUDE_PLUGIN_ROOT}/agents/lens-staff-engineer.md` and passes it as the prompt. Surface at Phase 4 smoke test.

**Assumption:** Replacement rate when porting `/staff-review`, `/security-review`, `/accessibility-review`, `/ship-spike` is under PR 1's re-plan trigger threshold (~30%).
**Confidence:** MEDIUM
**Why:** PR 1's `/ship` port was 19% replacement (within threshold). These 4 ports each have different coupling profiles: `/staff-review` is structurally transformed (lens extraction is more than a rename), `/security-review` and `/accessibility-review` are simpler diff-focused skills, `/ship-spike` mirrors `/ship`'s patterns. The aggregate replacement rate across all 4 is plausibly within threshold; the per-skill rate for staff-review specifically may exceed.
**If it flips:** Surface a re-plan event mid-execution (same pattern PR 1 used for the `/simplify`-is-bundled discovery). Don't silently absorb scope. Likely fallback: ship `/flow:staff-review` with inline lens prompts (Phase 3 alternative) to keep the structural transformation small.

**Assumption:** `flow.config.schema.json` capturing the 11 slots above is sufficient for v1.1.0 — no slot is forgotten that consumer projects will need.
**Confidence:** MEDIUM
**Why:** The 11 slots cover everything `/flow:ship`, `/flow:ship-spike`, `/flow:critique-plan`, `/flow:staff-review`, `/flow:accessibility-review` reference. But edge cases discovered during PR 4 (md-manager install) may reveal missing slots (e.g., a `branchPrefix` for `claude/*` vs `feature/*` naming, a `prCommitConvention` for squash-vs-merge expectations). Won't know for sure until PR 4 dogfood.
**If it flips:** Add slots in v1.2 (additive); PR 4 captures the missing-slot findings in `flow.config.json.MISSING-SLOTS-FOUND` (or a follow-up to `dev-docs/feedback.md` in flow's repo). Not catastrophic; consumer-side workaround is to fork the relevant SKILL.md temporarily.

**Assumption:** PR 1's locked patterns (`${CLAUDE_PLUGIN_ROOT}`, `sh -c` not `eval`, loud warnings, default-branch fallback chain, `source` absolute) generalize correctly to all PR 2's new artifacts.
**Confidence:** HIGH
**Why:** These patterns are mechanical and PR 1's review pass validated them across 5 artifacts. PR 2 introduces 13 new artifacts following the same patterns. Risk is purely "did the agent remember to apply each pattern in each file" — caught by the pre-commit greps in the Phase success criteria.
**If it flips:** Same misses PR 1 had (the cold-read missed 2 `agents/auditor.md` bare-path refs that engineer-lens caught). Mitigation: the Phase-7 dogfood is specifically designed to catch these.

---

## Risks

- **`/flow:staff-review` parallel-spawn pattern may need adjustment for plugin context.** Smoke-test early in Phase 4. If broken, fall back to inline lens prompts (Phase 3 abandoned).
- **Memory tool path-derivation may break consumer-side vs plugin-side.** Smoke-test at Phase 5d. If broken, env-var contract added.
- **Schema may miss slots discovered in PR 4 dogfood.** Mitigation: additive slot adds in v1.2; not catastrophic.
- **Hooks file (`default-hooks.json`) format may differ from what Anthropic now ships.** Verify against current `code.claude.com/docs/en/hooks` before authoring. If shape changed, adapt.
- **`/flow:ship` self-invocation in Phase 8 may surface backfill bugs.** Expected; first real invocation. Fix-forward pattern: if `/flow:ship` hits a rough edge, run the pipeline manually and add the fix to PR 2's commits.
- **PR 2's commit count is large** (target: ~20-30 commits across 8 phases). Keep messages tight + per-commit-why to keep the loop-walk review traversable.

---

## Files touched (anticipated)

**New (PR 2 deliverables):**
- `plugins/flow/skills/{staff-review,security-review,accessibility-review,ship-spike,workflow-help}/SKILL.md` (5 files)
- `plugins/flow/agents/{planner,docs,lens-staff-engineer,lens-ux-designer,lens-design-engineer,lens-push-further}.md` (6 files)
- `plugins/flow/rules/{general,plan-discipline,documentation,exploration}.md` (4 files)
- `plugins/flow/tools/memory/check.mjs` (1 file)
- `plugins/flow/schema/flow.config.schema.json` (1 file)
- `plugins/flow/hooks/default-hooks.json` (1 file)
- (Already present in this branch from the docs-only precursor PR: `dev-docs/handoffs/pr2-flow-plan.md` and `dev-docs/handoffs/md-manager-pr4-6-spec.md` — Phase 8 verifies + updates the latter)

**Modified:**
- `.claude-plugin/marketplace.json` (version bump 1.0.0 → 1.1.0; description expansion)
- `plugins/flow/.claude-plugin/plugin.json` (same)
- `plugins/flow/skills/ship/SKILL.md` (backfill steps 2 + 4b)
- `plugins/flow/skills/critique-plan/SKILL.md` (config-slot reference-glob)
- `plugins/flow/scripts/extract_session.py` (cwd constraint on `--reference-paths`)
- `plugins/flow/docs/workflow.md` (update Bootstrap status section: v1.1.0 ships full surface)
- `dev-docs/{history,plan,feedback,roadmap?,spec?}.md` (synthesis at Phase 8)

**Approximate total:** 24 new + modified files. PR diff size: roughly +3000 / -300 lines (port content dominates; net additive).

---

## What NOT to do

- **Don't merge.** `gh pr merge` is never the agent's action.
- **Don't force-push.** Tag `v1.0.0` release on main before any v1.1.0 commits, if release-tag discipline matters.
- **Don't add `template/` directory.** PR 3.
- **Don't touch md-manager.** PRs 4–6 in separate sessions. PR 2's only md-manager-adjacent artifact is `dev-docs/handoffs/md-manager-pr4-6-spec.md` which lives in FLOW's repo; md-manager session fetches via `gh api`.
- **Don't port bundled-native skills** (`/simplify`, `/batch`, `/debug`, `/loop`, `/claude-api`). Annotate any references as "(bundled with Claude Code)".
- **Don't repeat PR 1's review-pass misses.** Run the pre-commit greps from each Phase's success criteria. The cold-read pattern that missed 2 `agents/auditor.md` references in PR 1 is exactly what the greps catch.
- **Don't expand scope.** New scope discovered mid-execution → surface re-plan to the user, get approval, then continue. The PR 1 `/simplify`-is-native discovery is the canonical example of doing this right.
- **Don't add v1.x+ post-extraction features** — autonomous routines, JTBD substrate, visuals, design lenses, HTML reports, Chrome-preview, deploy previews. All deferred to post-extraction.

---

## Start instruction for the next session

1. Read this entire document.
2. Read `dev-docs/history.md` PR-1 entry (lessons + locked patterns).
3. Read `dev-docs/plan.md` § "PR 2 follow-ups from PR 1 review" + Handoff Notes.
4. Read `dev-docs/feedback.md` FB-0001 (dogfooding rule).
5. Read `plugins/flow/skills/ship/SKILL.md` (the locked-pattern reference).
6. Read `dev-docs/handoffs/md-manager-pr4-6-spec.md` (Phase 8 verifies this; you should know its shape going in).
7. Execute Phase 1: fetch sources, draft your per-PR plan into `dev-docs/plan.md` Active Work Items, surface to user, wait for "approved."
8. Execute Phases 2 → 8 sequentially against the success criteria.
9. After Phase 8, return PR URL to user. Stop.
