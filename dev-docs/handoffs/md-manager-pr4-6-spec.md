# Md-manager PRs 4–6 — flow plugin consumer migration spec

**Status:** ready for next session pickup IN md-manager (not flow)
**Repo:** `by-dev-tools/md-manager`, off `main`
**Prerequisites:** flow PR 2 (workflow surface backfill, v1.1.0) AND flow PR 3 (template directory, v1.2.0) both merged. **Do not start PR 4 until both upstream PRs are on flow's main.**
**Scope:** consume the `flow` plugin in md-manager. Stage 1 (PR 4) installs alongside existing local skills (non-breaking). Stage 2 (PR 5) dogfoods using only plugin skills. Stage 3 (PR 6) deletes the now-redundant local copies.

This spec is the source-of-truth handoff for the 3-PR md-manager-side migration. It lives in flow's repo (`dev-docs/handoffs/md-manager-pr4-6-spec.md`) per the Option-C cross-repo coordination decision from the consolidation doc — md-manager session fetches it via `gh api repos/by-dev-tools/flow/contents/dev-docs/handoffs/md-manager-pr4-6-spec.md --jq '.content' | base64 -d`.

Each PR is its own session with its own plan-approval gate. This document is the strategic plan; per-PR plans get drafted into `md-manager/core-docs/plan.md` Active Work Items at session start.

---

## Critical sequencing

```
flow PR 2 merged ──> flow PR 3 merged ──> md-manager PR 4 ──> PR 5 ──> PR 6
                                                                          │
                                                                          └─> umbrella retired
```

- **PR 4 starts only after flow PR 3 merges** (PR 4 needs PR 3's `template/base/flow.config.json.example` to derive md-manager's own `flow.config.json`).
- **PR 5 starts only after PR 4 merges** (needs flow installed alongside).
- **PR 6 starts only after PR 5 ships clean** (needs validated parity; do NOT skip the dogfood gate).
- **Inside any of PR 4 / 5 / 6, never merge.** User merges.

---

## PR 4 — Install flow alongside existing skills (non-breaking, Stage 1)

**Mode:** feature (small)
**Goal:** Install the `flow` plugin in md-manager via Claude Code's plugin marketplace, add a project-level `flow.config.json` declaring md-manager's specific slots (paths, default branch, preflight command, safety paths), add a one-line note to `md-manager/CLAUDE.md` pointing at the plugin. Existing `.claude/skills/`, `.claude/agents/`, `.claude/rules/` STAY IN PLACE — no deletion, belt-and-suspenders. Verify both can coexist via `/help` showing both local `/staff-review` and plugin `/flow:staff-review` cleanly namespaced.

### Scope (in)

- Install flow via either:
  - `~/.claude/settings.json` `enabledPlugins` add `"flow@flow": true` (user-scope; already done at the global level if you followed the post-PR-1 settings update).
  - OR `md-manager/.claude/settings.json` project-scope `enabledPlugins` entry — project-scope install means flow is only enabled when working in md-manager (cleaner for testing without polluting other projects).
- Write `md-manager/flow.config.json` at repo root with md-manager's specific slot values:
  - `defaultBranch: "main"`
  - `typecheckCmd: "npm run typecheck"` (or whatever md-manager's actual command is; verify via `cat md-manager/package.json | jq '.scripts.typecheck'`)
  - `historyPath: "core-docs/history.md"`
  - `planPath: "core-docs/plan.md"`
  - `roadmapPath: "core-docs/roadmap.md"`
  - `specPath: "core-docs/spec.md"`
  - `feedbackPath: "core-docs/feedback.md"`
  - `referenceGlob: "core-docs/*.md"` (matches consumer-side default; explicit to be unambiguous)
  - `uiSurface: true` (md-manager has UI)
  - `reviewLenses: ["staff-engineer","ux-designer","design-engineer","push-further"]` (default 4 lenses)
  - `memoryHardCap: 30`
  - `branchPrefix: "claude/"` (or `"feature/"` — match md-manager convention; if the v1.1 schema didn't include this slot, file a follow-up to flow's `dev-docs/plan.md` for v1.2 inclusion).
- Add a small section to `md-manager/CLAUDE.md` titled "Flow plugin" or similar — single paragraph: "md-manager uses the flow plugin (`by-dev-tools/flow@1.1.0+`) for its workflow surface. Skills are namespaced `flow:*`. Local `.claude/skills/`, `.claude/agents/`, `.claude/rules/` are preserved for parity testing and will be removed in PR 6 after PR 5's dogfood validates the plugin matches their behavior."
- Verify coexistence: `/help` lists BOTH local `/staff-review` AND plugin `/flow:staff-review` cleanly (plugins are auto-namespaced; no actual conflict per Anthropic docs — verify in practice).
- Smoke test: trigger `/flow:staff-review` on the diff for PR 4 itself. Capture any errors or rough edges in `flow.config.json` adjustments OR in a follow-up entry to flow's `dev-docs/feedback.md` (NOT md-manager's feedback.md — plugin feedback belongs in the plugin's repo).

### Scope (out)

- **No deletion of local skills, agents, rules.** That's PR 6, gated by PR 5 dogfood.
- **No actual use of `/flow:*` skills for non-PR-4 work.** PR 4 just installs + verifies coexistence; PR 5 is where dogfood begins.
- **No changes to md-manager's `core-docs/workflow.md`.** Replaced in PR 6 (or pointed at the plugin's workflow.md via an `@import` reference, depending on what works cleanly).
- **No upstream changes to flow.** Bugs found go in flow's `dev-docs/feedback.md` (the agent fetches that path via `gh api`); fixes happen in separate flow PRs, not bundled into PR 4.

### Phased execution + per-phase success criteria

#### Phase 4.1 — Plan + sanity checks

**Work:**
- Read this spec end-to-end.
- Read `md-manager/core-docs/plan.md` § "Flow plugin extraction" Active Work Item for the umbrella's current state.
- Read `md-manager/CLAUDE.md` for md-manager's current voice/conventions.
- Verify flow at v1.1.0+ available: `gh api repos/by-dev-tools/flow/contents/plugins/flow/.claude-plugin/plugin.json --jq '.content' | base64 -d | jq -r '.version'` returns `"1.1.0"` or higher.
- Verify flow PR 3 (template) merged: `gh api repos/by-dev-tools/flow/contents/template/base/flow.config.json.example --jq '.size'` returns non-error (file exists).
- Draft PR 4 plan into `md-manager/core-docs/plan.md` Active Work Items. Surface to user. Wait for "approved."

**Success criteria:**
- [ ] flow plugin version on main is ≥ 1.1.0 (verified via gh api).
- [ ] flow PR 3 template files exist on main (verified via gh api).
- [ ] `md-manager/core-docs/plan.md` has a new PR 4 Active Work Item with mode + goal + scope + spec-walk + confidence verdicts + risks + files touched.
- [ ] User explicitly approved.

#### Phase 4.2 — Install + config + coexistence verify

**Work:**
- Decide install scope (user-scope vs project-scope). Recommended: project-scope in `md-manager/.claude/settings.json` to avoid polluting other projects during the dogfood window.
- Create `md-manager/flow.config.json` per the slot list above. Validate against flow's schema: `cat md-manager/flow.config.json | jq -e .` exits clean; if flow v1.1.0+ ships the schema, validate against it.
- Add CLAUDE.md section describing the plugin install + coexistence-during-migration disclaimer.
- Launch a fresh `claude` session in md-manager; run `/help`; confirm both `/staff-review` (local) and `/flow:staff-review` (plugin) appear distinctly. Same for `/security-review` vs `/flow:security-review`, `/ship` vs `/flow:ship`, etc.

**Success criteria:**
- [ ] `md-manager/.claude/settings.json` includes `"enabledPlugins": { "flow@flow": true }` (project-scope) OR equivalent user-scope entry exists.
- [ ] `md-manager/flow.config.json` exists and parses with `jq -e .` cleanly.
- [ ] `md-manager/CLAUDE.md` has a "Flow plugin" section (or equivalent) referencing the plugin.
- [ ] Fresh `claude` session in md-manager: `/help` output contains both `/staff-review` and `/flow:staff-review` lines (verifying namespace separation works).
- [ ] No errors at session start from missing plugin files, malformed config, or rule conflicts.

#### Phase 4.3 — Smoke `/flow:staff-review` on this PR's diff

**Work:**
- After committing the install + config + CLAUDE.md edits, invoke `/flow:staff-review` on md-manager's current diff (which is just the PR 4 work itself).
- The plugin's 4 lens agents should spawn in parallel, each producing findings.
- If any agent fails to spawn, crashes, or produces malformed output: capture in flow's `dev-docs/feedback.md` (via a follow-up PR in flow's repo) AND defer PR 4 close-out until the issue is fixed upstream.
- If findings are clean: apply any BLOCKER + cheap NIT fixes inline; route FOLLOW-UPs to flow's `dev-docs/plan.md` PR-3-or-later sections (NOT md-manager's plan.md — plugin feedback belongs to plugin).
- Verify the doc-path slot reads work: the SKILL reads `flow.config.json.referenceGlob` → finds `core-docs/*.md` → loads md-manager's actual reference docs.

**Success criteria:**
- [ ] `/flow:staff-review` invocation completed (4 lens agents spawned + 4 reports collected).
- [ ] Each lens agent produced output that matches the documented BLOCKER/NIT/FOLLOW-UP/EXPLORATION triage format.
- [ ] `flow.config.json` slot reads worked (verify by checking that the staff-review prompts referenced md-manager's actual `core-docs/*.md` content, not flow's default `dev-docs/*.md`).
- [ ] Any errors / friction logged in flow's `dev-docs/feedback.md` via gh-api-fetched follow-up PR in flow's repo (not in md-manager).

#### Phase 4.4 — Ship via `/flow:ship`

**Work:**
- Optional: use plugin's `/flow:ship` to ship PR 4 itself. This is a second smoke test — does `/flow:ship` work end-to-end against md-manager's actual `flow.config.json` slot values?
- If `/flow:ship` works cleanly: PR 4 is doubly-validated (plugin shipped PR 4 itself).
- If `/flow:ship` rough-edges: fall back to manual ship (per md-manager's local `/ship` SKILL — they coexist for exactly this case).
- Either way: open PR against `main` (md-manager). Never merge.

**Success criteria:**
- [ ] PR 4 is open against `main` in md-manager.
- [ ] PR body documents which ship pipeline (plugin `/flow:ship` vs local `/ship`) was used and why.
- [ ] If plugin's `/flow:ship` was used: any friction captured in flow's `dev-docs/feedback.md`.
- [ ] PR is MERGEABLE.

### Confidence verdicts (PR 4)

**Assumption:** flow plugin install in md-manager's project-scope is clean and doesn't conflict with existing local skills (plugins are auto-namespaced).
**Confidence:** HIGH
**Why:** Anthropic documents plugin namespace separation explicitly; PR 1's smoke test confirmed `flow:*` namespace works in isolation.
**If it flips:** Fall back to user-scope install + accept the cross-project pollution during migration; or shim the local skills out of the way temporarily. Single-config-line revert.

**Assumption:** All 11 `flow.config.json` slots map cleanly to md-manager's actual project shape (paths, commands, conventions).
**Confidence:** MEDIUM
**Why:** PR 2's schema was designed against md-manager as the reference consumer, but edge cases (branchPrefix, multi-stack typecheck commands, monorepo paths) may surface gaps. PR 4 is the first real-world consumer test.
**If it flips:** Missing slots filed to flow's `dev-docs/plan.md` for v1.2 inclusion; meanwhile md-manager either tolerates the limitation or temporarily overrides via a local skill. Doesn't block PR 4.

### Risks (PR 4)

- **Doc-path slot semantics may surprise the plugin's skills.** Some flow skills may have assumed defaults (`dev-docs/*` for flow's repo) and not properly handle the consumer-side path (`core-docs/*`). Smoke test in Phase 4.3 surfaces this.
- **`/flow:ship` may have rough edges on first real consumer invocation.** Fall back to local `/ship`; capture rough edges in flow's `dev-docs/feedback.md`.
- **The CLAUDE.md "Flow plugin" section may need to evolve through PRs 5-6.** Acceptable; iterate.

### Files touched (PR 4)

- **New:** `md-manager/flow.config.json` (project-root, ~15 lines).
- **Modified:** `md-manager/.claude/settings.json` (enabledPlugins entry), `md-manager/CLAUDE.md` (new section).
- **Unchanged:** every `.claude/skills/`, `.claude/agents/`, `.claude/rules/` file. Zero deletions.

---

## PR 5 — End-to-end dogfood (the validation gate)

**Mode:** feature (sized to whatever the chosen real change is — keep small)
**Goal:** Pick a small, real, user-facing change in md-manager (typo fix, tiny refactor, a single component polish item) and ship it using ONLY `/flow:*` skills + bundled Claude Code natives. No invocation of md-manager's local `/staff-review`, `/security-review`, `/ship`, `/ship-spike`, `/accessibility-review` allowed in this PR. The output is a real shipped PR in md-manager driven by the plugin, validating the abstraction end-to-end on a non-trivial workflow. **This is the single most important checkpoint in the umbrella — do not rush PR 6 (deletion) until PR 5 surfaces zero blockers.**

### Scope (in)

- Pick the change from `md-manager/core-docs/roadmap.md` (Now or Next horizon) or `md-manager/core-docs/plan.md` Backlog. Constraints:
  - Small: 1-3 files, < 100 LOC delta.
  - Real: an actual product improvement, not a contrived test PR.
  - Touches code, not just docs (so all 4 lenses have something to engage with).
  - NOT safety-critical (don't risk a real bug while exercising the plugin).
- Run the full 11-step loop using plugin skills:
  - Step 1 Clarify: read md-manager's `core-docs/` per usual.
  - Step 2 Plan: write into `core-docs/plan.md`. Run `/flow:critique-plan` (NOT md-manager's local critique-plan if one exists). User approves.
  - Step 3 Execute: standard.
  - Step 4 Preflight: standard md-manager preflight (project-specific, not plugin-shipped).
  - Step 5 Commit: standard.
  - Step 6 `/simplify`: bundled Claude Code native; usable.
  - Step 7 `/flow:staff-review`: plugin version. All 4 lenses must spawn + produce findings + triage.
  - Step 8 Present: standard.
  - Step 9 Iterate: as needed.
  - Step 10 `/flow:ship`: plugin version. Runs `/flow:security-review`, `/flow:accessibility-review`, synthesizes feedback into BOTH md-manager's `core-docs/feedback.md` (user feedback) AND `~/.claude/projects/<canonical>/memory/feedback_*.md` (agent self-feedback per the source-diversity bar), updates `core-docs/{history,plan,roadmap,spec}.md`, commits, pushes, opens PR.
  - Step 11 STOP: user merges.
- Capture every rough edge, error, or friction in flow's `dev-docs/feedback.md` via a follow-up PR in flow's repo. This is the load-bearing output.
- **Do NOT fix flow bugs as part of PR 5.** Fixes happen as follow-up PRs in flow, not bundled here. PR 5 is a clean test surface; bundling fixes pollutes the validation signal.

### Scope (out)

- **No deletion of md-manager's local skills.** PR 6.
- **No invocation of md-manager's local workflow skills.** That defeats the purpose of the dogfood.
- **No flow bug-fixes bundled here.** Separate follow-up PRs.
- **No expansion of the chosen change.** Small + scoped + boring.

### Phased execution + per-phase success criteria

#### Phase 5.1 — Pick the change + draft plan

**Work:**
- Browse `md-manager/core-docs/roadmap.md` Now/Next + Backlog for candidates. Score against the in-scope constraints above. Confirm choice with user.
- Draft per-PR plan into `core-docs/plan.md` Active Work Items. Run `/flow:critique-plan` (the plugin version, not local). Surface plan + critique to user. Wait for "approved."

**Success criteria:**
- [ ] The chosen change is named in the plan (file paths, brief LOC estimate).
- [ ] The change meets all in-scope constraints (small, real, code-touching, non-safety).
- [ ] `/flow:critique-plan` (plugin) ran successfully and returned either APPROVED or a CRITIQUE SUMMARY.
- [ ] User explicitly approved the plan.
- [ ] No invocation of md-manager's local workflow skills in this phase.

#### Phase 5.2 — Execute + preflight + commit

**Work:**
- Implement the chosen change against the spec-walk checkboxes.
- Run md-manager's standard preflight (project-specific, not plugin-shipped).
- Commit per phase with co-author trailer.

**Success criteria:**
- [ ] All spec-walk checkboxes from Phase 5.1 plan are checked off with their corresponding code/tests landed.
- [ ] Preflight green (md-manager's typecheck + build + test all pass).
- [ ] Commits use the co-author trailer.
- [ ] No invocation of md-manager's local workflow skills in this phase.

#### Phase 5.3 — `/flow:staff-review` four-lens pass

**Work:**
- Invoke `/flow:staff-review` on the diff.
- Triage findings: BLOCKER + cheap NIT inline; FOLLOW-UP to `core-docs/{plan,roadmap}.md`.
- **Capture every plugin rough edge** (a lens that didn't spawn, malformed output, slot read failure, slow performance, confusing UX) in a follow-up flow PR's feedback entry.

**Success criteria:**
- [ ] `/flow:staff-review` invoked; output captured.
- [ ] All 4 lenses spawned (or "skip with reason" explicitly stated for any lens that didn't apply).
- [ ] All BLOCKER + cheap NIT findings addressed in-tree.
- [ ] All FOLLOW-UP findings routed to md-manager's `core-docs/{plan,roadmap}.md`.
- [ ] Any plugin rough edges captured (file paths + line numbers + repro steps) for a flow follow-up PR.

#### Phase 5.4 — `/flow:ship` end-to-end

**Work:**
- Invoke `/flow:ship`. The skill runs `/flow:security-review` + `/flow:accessibility-review`, synthesizes feedback into both layers (user FB-XXXX in md-manager + agent feedback_*.md in user-scope memory), updates md-manager's core-docs, commits, pushes, opens PR.
- The doc updates must happen via the `flow.config.json` slot paths (i.e., the plugin reads `historyPath: "core-docs/history.md"` from md-manager's config and writes there, not to its own `dev-docs/`).
- **Capture every rough edge.**

**Success criteria:**
- [ ] `/flow:ship` completed end-to-end without manual fallback.
- [ ] `core-docs/history.md` has a new entry written by the plugin (not manually).
- [ ] `core-docs/plan.md` has the shipped item moved to Recently Completed.
- [ ] `core-docs/feedback.md` has any new FB-XXXX entries the session surfaced (user-feedback layer).
- [ ] If the source-diversity bar held: a new agent-memory entry exists at `~/.claude/projects/.../memory/feedback_*.md`. If it didn't hold: explicitly note "no memory entry — source-diversity bar didn't hold" in the PR body.
- [ ] PR is OPEN against `main` (md-manager) via the plugin's `gh pr create` invocation.
- [ ] PR is MERGEABLE.
- [ ] **Most importantly:** zero usage of md-manager's local workflow skills across all of PR 5.

#### Phase 5.5 — Feedback handoff to flow

**Work:**
- Consolidate every rough edge captured during Phases 5.1–5.4 into a single PR in flow's repo that adds entries to `dev-docs/feedback.md` AND/OR opens flow follow-up issues.
- This is the validation signal: does the plugin work for a real consumer end-to-end?
- If feedback is substantial (>5 entries, or any BLOCKER-level issues): **PAUSE before PR 6.** Address the flow bugs in separate flow PRs, then re-validate by re-running PR 5's pipeline on a second small change.
- If feedback is light (<5 minor entries, no BLOCKERs): proceed to PR 6.

**Success criteria:**
- [ ] All Phase-5.1-through-5.4 rough edges are written up.
- [ ] Either: a flow PR is open with the feedback entries, OR a "PR 5 surfaced zero blockers" statement is committed to md-manager's `core-docs/history.md` as part of PR 5's history entry.
- [ ] User has explicitly signed off on "PR 6 can proceed" OR "pause for flow fixes."

### Confidence verdicts (PR 5)

**Assumption:** md-manager's current skill behaviors can be reproduced 1:1 by the parameterized plugin skills, modulo the project-specific slots in `flow.config.json`.
**Confidence:** MEDIUM
**Why:** Most behaviors are project-agnostic; a few (e.g., `/staff-review`'s push-further lens reading md-manager's `design-language.md`) depend on file presence + structure. flow.config.json should cover this via doc-path slots; won't know for sure until this dogfood.
**If it flips:** Diff-and-fix in flow follow-up PRs; defer PR 6 (duplicate removal) until parity is achieved. PR 4 + PR 5 are explicitly designed to surface this before any deletion.

**Assumption:** Plugin-shipped agents (planner, docs, 4 lens agents) work correctly when invoked from a consumer-scope context (md-manager) with the plugin installed at user OR project scope.
**Confidence:** MEDIUM
**Why:** Not validated until this PR. Plugin agents may read from `${CLAUDE_PLUGIN_ROOT}/...` which resolves dynamically — should work — but the consumer's project context (cwd, $CLAUDE_PROJECT_ROOT or equivalent) must also be accessible to them.
**If it flips:** Adapt the agent prompts to receive project-context env vars explicitly. Surface in Phase 5.3 + 5.4 smoke tests.

### Risks (PR 5)

- **PR 5 surfaces blockers requiring flow follow-up PRs.** Likely outcome (some friction is expected on first real consumer use). Don't rush to PR 6.
- **Local skill invocation slips in by habit.** The agent doing PR 5 must consciously type `/flow:*` not `/...`. Set up the prompt to remind itself.
- **Source-diversity bar may not hold for a small dogfood PR.** Expected — single PR, single source. Memory entry doesn't get written; that's fine.

### Files touched (PR 5)

- Whatever the chosen small change touches (1-3 files, <100 LOC).
- `md-manager/core-docs/{history,plan,feedback}.md` (via `/flow:ship` writes).
- Optionally: a `~/.claude/projects/<canonical>/memory/feedback_*.md` entry (via `/flow:ship` step 4b).
- A separate flow PR with feedback entries (out of md-manager's PR 5; tracked separately).

---

## PR 6 — Remove local duplicates + retire the umbrella (Stage 2, breaking)

**Mode:** feature
**Goal:** Delete from md-manager every file that's now redundantly provided by the flow plugin. md-manager becomes a pure consumer: its `.claude/` directory carries only project-shaped files (safety paths, UI tokens, dev-server skill). The cross-repo umbrella tracking in `md-manager/core-docs/plan.md` retires; future plugin work happens solely in flow's `dev-docs/`.

### Scope (in)

**Delete from md-manager** (the canonical list — verified against md-manager's current state):

`.claude/skills/` deletions:
- `staff-review/` (replaced by `flow:staff-review`)
- `security-review/` (replaced by `flow:security-review`)
- `accessibility-review/` (replaced by `flow:accessibility-review`)
- `ship/` (replaced by `flow:ship`)
- `ship-spike/` (replaced by `flow:ship-spike`)

NOTE: md-manager does NOT have `.claude/skills/simplify/` — `/simplify` is bundled Claude Code native. No deletion needed.

`.claude/agents/` deletions:
- `planner.md` (replaced by `flow:planner` — invoked via `Agent` tool with `subagent_type: planner` resolving to the plugin's agent file)
- `docs.md` (same pattern)

`.claude/rules/` deletions:
- `general.md` (replaced by plugin's `general.md`)
- `plan-discipline.md` (replaced by plugin's)
- `documentation.md` (replaced by plugin's)
- `exploration.md` (replaced by plugin's)

`tools/` deletions:
- `tools/memory/check.mjs` AND `tools/memory/.gitignore` (replaced by plugin's `${CLAUDE_PLUGIN_ROOT}/tools/memory/check.mjs`)

NOTE: md-manager does NOT have `tools/preflight/` per current state (preflight runner was deferred per umbrella plan; check before assuming presence). `tools/invariants/check.mjs` STAYS (project-shaped, not plugin-provided).

**Keep in md-manager** (project-shaped — NOT plugin-provided):

`.claude/rules/` keepers:
- `safety.md` (project safety-critical paths — different per project)
- `ui.md` (project design-system tokens + a11y baseline — different per project)
- `dev-server.md` (project dev URL surfacing — different per project)

`.claude/skills/` keepers:
- `link/` (project-specific dev server)
- `audit-a11y/`, `check-component-reuse/`, `elicit-design-language/`, `enforce-tokens/`, `generate-ui/`, `propagate-language-update/` (Mini-design-system skills — separate plugin work later; stay in md-manager for now)

`tools/` keepers:
- `tools/invariants/check.mjs` (md-manager-specific design-system invariants)
- `tools/preflight/check.mjs` IF it exists by PR 6 time (project-specific preflight runner)

`core-docs/` — entirely preserved (project knowledge).

**Update `md-manager/CLAUDE.md`:**
- Remove the now-redundant references to the deleted local skills/rules/agents.
- Strengthen the "Flow plugin" section: "md-manager is a pure consumer of the flow plugin. Workflow questions, skill questions, and rule questions belong to flow (`by-dev-tools/flow`); project-specific safety / UI / dev-server / invariants stay here."
- Point all workflow/skill/rule questions at the plugin's `docs/workflow.md`.

**Update `md-manager/core-docs/workflow.md`:**
- Decide: replace the long-form content with a one-line pointer to `${CLAUDE_PLUGIN_ROOT}/docs/workflow.md`, OR delete the file entirely and have CLAUDE.md point at the plugin's workflow.md, OR keep as a thin md-manager-overlay (only the bits md-manager adds beyond the canonical loop — likely empty after migration).
- The umbrella plan suggested workflow.md may need to be a one-time copy from flow's template + md-manager overlay (consolidation doc Risk #4). Test at PR 6 plan time.

**Retire the umbrella:**
- In `md-manager/core-docs/plan.md`: move the "Flow plugin extraction" Active Work Item from "Active Work Items" to "Recently Completed" as "Flow plugin extraction complete — md-manager is now a pure consumer of flow v1.1.0+. Cross-repo umbrella tracking retired; future plugin work tracked solely in flow's `dev-docs/`."
- In `md-manager/core-docs/history.md`: add a narrative entry covering PR 6 + the entire extraction arc, with a pointer to flow's `dev-docs/history.md` for per-PR detail.

**Run the full plugin loop on PR 6 itself** end-to-end (`/flow:critique-plan` → `/flow:staff-review` → `/flow:ship`) as a second dogfood validation. This is the final integration test before retirement.

### Scope (out)

- **Mini design system extraction.** Stays in md-manager; separate plugin work later.
- **`tools/invariants/check.mjs` extraction.** Project-specific; stays.
- **Any flow plugin improvements.** Separate flow PRs.
- **Reintroducing local skills "just in case."** Once they're gone, gone. Trust the plugin or revert PR 6 entirely if blocked.

### Phased execution + per-phase success criteria

#### Phase 6.1 — Plan + validate prerequisites

**Work:**
- Verify PR 5 shipped clean (`gh pr view <PR5-number> --json state` returns `MERGED`).
- Verify no outstanding flow follow-up bugs blocking PR 6 (read flow's `dev-docs/plan.md` Current Focus + Handoff Notes).
- Snapshot md-manager's current state: `git ls-files .claude/ tools/` saved to `/tmp/pr6-pre-snapshot.txt`.
- Verify the deletion list against the snapshot — every file named for deletion in this spec actually exists; every file named as "keep" actually exists.
- Draft PR 6 plan into `core-docs/plan.md`. Run `/flow:critique-plan`. Surface to user. Wait for "approved."

**Success criteria:**
- [ ] PR 5 is MERGED on md-manager's main.
- [ ] flow's current state has no BLOCKER-level open issues from PR 5's feedback handoff.
- [ ] Pre-deletion file snapshot exists at `/tmp/pr6-pre-snapshot.txt`.
- [ ] Every file in the spec's deletion list exists in md-manager's current state.
- [ ] Every file in the spec's "keep" list exists in md-manager's current state.
- [ ] PR 6 plan approved by user.

#### Phase 6.2 — Delete + update CLAUDE.md + workflow.md

**Work:**
- `git rm` every file in the deletion list. Single commit: "Remove local workflow skills/rules/agents now provided by flow plugin."
- Update `md-manager/CLAUDE.md` per the spec above. Commit: "Update CLAUDE.md for pure-consumer state."
- Update `md-manager/core-docs/workflow.md` per the chosen approach (pointer / delete / thin overlay). Commit: "Reduce md-manager workflow.md to plugin-overlay state."

**Success criteria:**
- [ ] `find md-manager/.claude/skills/ -maxdepth 1 -type d` returns only the keepers (`link`, `audit-a11y`, `check-component-reuse`, `elicit-design-language`, `enforce-tokens`, `generate-ui`, `propagate-language-update`) — none of the 5 deleted.
- [ ] `find md-manager/.claude/agents/ -type f` returns no files (both `planner.md` and `docs.md` deleted).
- [ ] `find md-manager/.claude/rules/ -type f -name "*.md"` returns only `safety.md`, `ui.md`, `dev-server.md` — the 4 portable rules deleted.
- [ ] `ls md-manager/tools/memory/ 2>&1 | head -1` returns "No such file or directory" or empty.
- [ ] `grep -nE 'local |our own |/staff-review|/security-review|/accessibility-review|/ship|/ship-spike' md-manager/CLAUDE.md` returns either zero matches OR all matches are inside the "Flow plugin" section noting the migration history.
- [ ] `md-manager/core-docs/workflow.md` is either deleted, or under 30 lines (thin overlay), or replaced with a pointer.

#### Phase 6.3 — Full-loop dogfood on PR 6 itself

**Work:**
- Invoke `/flow:critique-plan` on PR 6's plan (already done in 6.1).
- Invoke `/flow:staff-review` on PR 6's diff. Apply BLOCKER + cheap NIT fixes inline.
- Invoke `/flow:ship`. The skill must write to md-manager's `core-docs/*.md` paths via the `flow.config.json` slot reads, not to flow's `dev-docs/`.

**Success criteria:**
- [ ] All three plugin invocations completed successfully.
- [ ] `md-manager/core-docs/history.md` has a new PR-6 entry written by the plugin.
- [ ] `md-manager/core-docs/plan.md` has the "Flow plugin extraction" item moved to Recently Completed with the retirement language.
- [ ] PR 6 is OPEN against md-manager main; MERGEABLE.
- [ ] If `/flow:ship` had ANY rough edges in Phase 6.3, capture in flow's `dev-docs/feedback.md` via a follow-up flow PR — but don't block PR 6 merge on it (PR 6 fundamentally works; rough edges are polish for v1.2+).

#### Phase 6.4 — Umbrella retirement (post-merge)

**Work (post-merge, separate brief touch):**
- After user merges PR 6: update md-manager's `core-docs/plan.md` Current Focus to remove any extraction-related framing — md-manager moves on to its actual product work (Mini design system, color rail, persistence, etc.).
- Add a final breadcrumb to flow's `dev-docs/history.md` (via a tiny PR in flow's repo): "Flow plugin extraction umbrella retired. md-manager is the first validated consumer at md-manager@<sha>. Future plugin work tracked solely in `dev-docs/`."
- Close out any flow `dev-docs/handoffs/*` docs that reference the umbrella as active.

**Success criteria:**
- [ ] PR 6 merged on md-manager's main.
- [ ] md-manager `core-docs/plan.md` Current Focus no longer mentions flow extraction.
- [ ] flow `dev-docs/history.md` has the umbrella-retirement breadcrumb.
- [ ] `dev-docs/handoffs/` docs are either updated for post-extraction state OR moved to a `dev-docs/handoffs/archive/` subdirectory.

### Confidence verdicts (PR 6)

**Assumption:** Every file in the deletion list is genuinely redundant — the plugin's equivalent provides the same behavior md-manager's consumers rely on.
**Confidence:** HIGH (assuming PR 5 dogfood validated cleanly)
**Why:** PR 5's whole purpose was to validate parity. If PR 5 shipped clean, PR 6's deletion is safe.
**If it flips:** Restore deleted files from git history (`git checkout pre-pr6 -- <path>`). Reopen PR 5-style validation cycle on the deficient surface. Revert PR 6 if parity gap is structural.

**Assumption:** `md-manager/core-docs/workflow.md` can be either deleted entirely, made into a pointer, or made into a thin overlay without losing project-specific workflow knowledge.
**Confidence:** MEDIUM
**Why:** md-manager's workflow.md is canonical-across-projects per its header; reductions should be safe. But there may be md-manager-specific tweaks (preflight gate list, design-language coupling) that need to live somewhere — either in the CLAUDE.md "Flow plugin" section or in a thin overlay.
**If it flips:** Keep a thin overlay (under 30 lines) for the md-manager-specific bits; let plugin's workflow.md be the canonical loop reference. Decision happens at Phase 6.2 plan time.

### Risks (PR 6)

- **Deleting too aggressively.** Mitigation: the "keep" list is explicit; the pre-deletion snapshot at `/tmp/pr6-pre-snapshot.txt` provides recovery.
- **md-manager/core-docs/workflow.md decision is wrong.** Easy to iterate; this is a doc, not code.
- **Plugin behavior diverges from local behavior on a surface PR 5 didn't exercise.** Catch in Phase 6.3 dogfood; reopen for fix if surfaced.

### Files touched (PR 6)

- **Deleted (12 files / dirs):** 5 skill dirs, 2 agent files, 4 rule files, 1 memory tool dir.
- **Modified:** `md-manager/CLAUDE.md`, `md-manager/core-docs/workflow.md` (deletion or thin-overlay), `md-manager/core-docs/{plan,history,feedback?}.md` (via `/flow:ship` writes).
- **Created:** none (PR 6 is mostly deletions + doc updates).

---

## Cross-PR risks (PRs 4–6)

- **Flow upstream changes mid-migration.** Pin flow to a specific version in md-manager's settings.json during PRs 4-6 (`"flow@flow@1.1.0"` syntax if Anthropic supports it; else lock via the marketplace commit SHA). Reduces churn.
- **`/plugin marketplace update` friction.** User-driven; document in PR 4's body so the user knows when to update.
- **Memory entries written cross-scope.** Verify in PR 5: the plugin writes feedback entries to `~/.claude/projects/<md-manager-canonical-path>/memory/`, not somewhere else. Catch at Phase 5.4 success criterion.
- **Md-manager's local design-language / Mini coupling** may bind tighter to the local `/staff-review` than the plugin's generic version. Phase 5.3 dogfood surfaces; PR 6 deletion may need to defer specific Mini-coupled lenses to a v1.x flow PR.

---

## Files this spec references (for the md-manager agent to fetch via gh api)

- `gh api repos/by-dev-tools/flow/contents/plugins/flow/.claude-plugin/plugin.json` — verify v1.1.0+ shipped.
- `gh api repos/by-dev-tools/flow/contents/plugins/flow/schema/flow.config.schema.json` — schema for md-manager's flow.config.json.
- `gh api repos/by-dev-tools/flow/contents/template/base/flow.config.json.example` — PR 3 deliverable; reference template.
- `gh api repos/by-dev-tools/flow/contents/plugins/flow/docs/workflow.md` — canonical loop reference.
- `gh api repos/by-dev-tools/flow/contents/dev-docs/plan.md` — flow's Current Focus + any open follow-ups.
- `gh api repos/by-dev-tools/flow/contents/dev-docs/feedback.md` — flow's accumulated feedback; PR 5 contributes here.

---

## What NOT to do (across all 3 PRs)

- **Don't merge.** User merges.
- **Don't start PR 4 before flow PR 3 is on main.**
- **Don't start PR 5 before PR 4 is merged.**
- **Don't start PR 6 before PR 5 ships clean (zero blockers).** This is the load-bearing gate.
- **Don't bundle flow bug fixes into md-manager PRs.** Separate flow PRs.
- **Don't delete from the "keep" list** in PR 6.
- **Don't expand md-manager's product scope** during these PRs. PR 5's chosen change is small + boring + real.
- **Don't lose the pre-deletion snapshot in PR 6.** Recovery anchor.

---

## Start instruction (for md-manager session in PR 4)

1. Verify flow PR 3 is merged: `gh pr list --repo by-dev-tools/flow --state merged --search "PR 3" --json title,mergedAt`.
2. Fetch this spec into the md-manager session: `gh api repos/by-dev-tools/flow/contents/dev-docs/handoffs/md-manager-pr4-6-spec.md --jq '.content' | base64 -d`.
3. Read the spec end-to-end.
4. Read `md-manager/core-docs/plan.md` § "Flow plugin extraction" Active Work Item.
5. Read `md-manager/CLAUDE.md`.
6. Execute PR 4 Phase 4.1: draft per-PR plan into `md-manager/core-docs/plan.md`, run `/flow:critique-plan` (if plugin already in user-scope `~/.claude/settings.json` from PR 1's post-merge setup), surface to user, wait for "approved."
7. Execute Phases 4.2–4.4. Open PR. User merges.
8. Stop. Next session does PR 5; session after that does PR 6.
