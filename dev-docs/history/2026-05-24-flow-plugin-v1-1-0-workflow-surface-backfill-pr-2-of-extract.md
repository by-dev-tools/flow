### Flow plugin v1.1.0 — workflow surface backfill (PR 2 of extraction umbrella)
**Date:** 2026-05-24
**Branch:** pr2/workflow-backfill
**Commit:** 25ef3bc..ef8fd32 (7 phase commits + dogfood fix commit; PR pending push to push at end of Phase 8)

**What was done:**
Backfilled the `[PR 1 LIMITATION]` placeholders inside `plugins/flow/skills/ship/SKILL.md` (step 2 security+a11y reviews; step 4b memory machinery) and ported the rest of the workflow surface from md-manager. The plugin now covers the full canonical 11-step loop end-to-end. 13 new shipped artifacts + 3 modified existing artifacts + manifest version bump.

Phased execution (Phases 1–8):

- **Phase 1:** Fetched 12 md-manager sources via `gh api` in parallel. Refined the handoff plan with 4 observations: staff-review extraction is more structural than handoff implied; security/a11y reviews carry heavier md-manager tokens; all 4 source skills start step numbering at 0; ship-spike references nonexistent `tools/preflight/check.mjs`. Committed plan refinement; user direction was "execute autonomously per success criteria" so no separate user-gate beyond the original PR-2-plan approval.

- **Phase 2:** Ported `/flow:security-review` and `/flow:accessibility-review`. De-projected (stripped 'markdown-notes app', 'Vite + React + TypeScript', src/lib/markdown.ts, `--sand-9`, `--page-text-quiet`). Added `uiSurface=false` skip-early gate to accessibility-review for backend-only consumers. Config-slot doc paths throughout. All locked PR-1 idioms applied.

- **Phase 3:** Extracted 4 lens prompts from md-manager's inline `staff-review/SKILL.md` (14.3KB single file) into separate plugin-shipped agent files (`lens-staff-engineer.md`, `lens-ux-designer.md`, `lens-design-engineer.md`, `lens-push-further.md`). Each agent has frontmatter + Inputs + Hunts + Specifically-asks + Triage scheme + Output format + Gotchas. Push-further lens's "Nothing to push — surface at ceiling for its scope" escape hatch preserved verbatim (load-bearing restraint contract).

- **Phase 4:** Ported `/flow:staff-review` as a pure orchestrator. The SKILL spawns 4 parallel `Agent` calls with `subagent_type: lens-{staff-engineer,ux-designer,design-engineer,push-further}`. File grew from md-manager's 14.3KB → only 12.9KB despite adding all the consumer-side config-slot scaffolding (the lens content extraction worked; the file is just slightly under what an orchestrator + scaffolding needs).

- **Phase 5:** Ported the remaining 9 artifacts in one phase: `/flow:ship-spike` (lightweight spike pipeline), `/flow:workflow-help` (new skill — prints loop + project config + skill catalog), `planner` + `docs` context-isolation agents (de-projected to read paths from spawner-injected slots), 4 portable rules (`general.md`, `plan-discipline.md`, `documentation.md`, `exploration.md`), `tools/memory/check.mjs` (canonical-path derivation with Claude-Code-worktree slug scoring added), `flow.config.schema.json` (13 slots — 2 more than the handoff estimated: `designLanguagePath` + `branchPrefix` per actual SKILL needs and the md-manager spec call-out), and `default-hooks.json` (2 PreToolUse hooks — sensitive-file write blocker + path-validation warn-only). Manifest bumped to v1.1.0.

- **Phase 6:** Backfilled `/flow:ship` placeholders with real `Skill('flow:security-review')` + `Skill('flow:accessibility-review')` invocations (step 2) and the full 6-substep memory machinery (step 4b). Addressed both PR-1 FOLLOW-UPs: `critique-plan` SKILL now reads `flow.config.json.referenceGlob` (default `core-docs/*.md`); `extract_session.py` rejects out-of-cwd `--reference-paths` by default with stderr message, opt-in via `--allow-external-paths`. Verified empirically (created minimal session file, tested `/etc/hosts` rejection-then-acceptance).

- **Phase 7:** Dogfooded PR 2 through the newly-built `/flow:staff-review` lens orchestration. Spawned 4 parallel Agent subagents (engineer + UX-designer + push-further + security) on PR 2's own diff. Skipped design-engineer (no visual surface) + accessibility (uiSurface=false in flow's own repo) with explicit reason. Caught 2 BLOCKERs (`Skill` missing from ship.md `allowed-tools`; `memoryHardCap` schema slot dead) + 11 NITs + 8 FOLLOW-UPs. All BLOCKERs + NITs fixed in-tree. FOLLOW-UPs routed to `dev-docs/plan.md` § "PR 3+ follow-ups from PR 2 review".

- **Phase 8:** This entry. Doc synthesis (history.md + plan.md + feedback.md FB-0002 + FB-0003). Will verify md-manager-pr4-6-spec.md accuracy against shipped surface, then push + open PR.

**Why:**
PR 2 of the flow extraction umbrella. After PR 2, a consumer project with `flow.config.json` set can run the full 11-step loop using only `/flow:*` skills + Claude Code bundled natives (`/simplify`, `/batch`, `/debug`, `/loop`, `/claude-api`). The plugin is feature-complete for v1 — PR 3 ships the consumer-side template directory; PRs 4–6 migrate md-manager.

**Design decisions:**

- **Lens prompts extracted to separate agent files** (vs kept inline in staff-review SKILL): more modular (each lens individually invocable), the orchestrator is more readable, and lens prompts can be versioned independently. Trade-off: introduces a new subagent_type dispatch pattern that wasn't smoke-tested in plugin context before this PR. Mitigated by dogfooding in Phase 7 (which succeeded).

- **`workflow-help` is a new skill, not a port.** md-manager has no equivalent. Designed as the onboarding front door: prints the canonical 11-step loop + resolved project config + skill catalog + bundled-native annotations + project-shaped-surface list. Push-further lens correctly flagged that the first version jumped straight to a step list — added "Flow is a managed-autonomy loop: ..." opening sentence in Phase 7.

- **13 slots in `flow.config.schema.json`, not 11.** Handoff estimated 11. Added `designLanguagePath` (read by staff-review UX + design-engineer + push-further lenses + a11y-review for grounding) and `branchPrefix` (called out in md-manager spec as needed; landing now since the cost is one schema entry). Both must have at least one consumer wired in to avoid the FB-0003 "schema-without-implementation" anti-pattern.

- **Hooks are opt-in, not auto-applied.** `plugins/flow/hooks/default-hooks.json` ships the patterns; consumers merge them into their project's `.claude/settings.json` (template/settings.json.example in PR 3 will do this by default). Both hooks are warn-only or block-on-clear-pattern (Edit|Write sensitive-file matcher exits 2); neither blocks arbitrary actions.

**Technical decisions:**

- **`sh -c` over `eval` (idiom locked in PR 1)** applied to all 4 new typecheckCmd consumers (ship, ship-spike, staff-review, security-review, accessibility-review). Subshell isolation; trust boundary documented at each call site.

- **`${CLAUDE_PLUGIN_ROOT}` for all cross-file references in shipped prompts (idiom locked in PR 1)** applied universally. The 13 cross-file refs in PR 2's new artifacts all use the dynamic form. Three legitimate documentation references to `tools/preflight/check.mjs` remained un-prefixed because that path is CONSUMER-shipped (not plugin-shipped) — documented in commit messages.

- **Memory tool path derivation**: ported from md-manager's `tools/memory/check.mjs` with added scoring penalty for `-claude-worktrees-` slugs (parallel to the existing `-conductor-workspaces-` penalty), so the harness's canonical project path wins over the worktree path. The auditMarker lives next to the script (per-install, not per-project) — documented in the script's top-of-file comment as acceptable for v1.1 with a v1.2 revisit if cross-project misalignment surfaces.

- **`extract_session.py` cwd constraint via `Path.resolve()` + `relative_to()`**: defeats symlink-following attacks (Path.resolve canonicalizes the path) AND `..` traversal (relative_to raises ValueError for out-of-tree paths). Verified empirically by the security lens reviewer with symlinks pointing outside cwd. The `--allow-external-paths` opt-out is only settable via explicit CLI flag.

**Tradeoffs discussed:**

- **Lens extraction (Option B, this PR) vs keep inline (Option A, md-manager's pattern):** chose extraction. Cost: one more layer of indirection at spawn time; introduces a `subagent_type` contract that wasn't pre-validated. Benefit: modular lenses, individually invocable, orchestrator file is readable rather than buried under 12KB of prompt content. Fallback would have been single-commit reversion if Phase 4 smoke-failed — it didn't.

- **`memoryHardCap` wire vs drop the slot:** engineer lens caught it as dead (schema doc says configurable, check.mjs hardcoded 30). Choices: (a) wire check.mjs to read the slot, (b) drop the slot from schema. Wiring is the better fix — the schema documents it as configurable for a real reason (consumers with bigger memory corpora) and the implementation cost is ~15 lines. Same calculus for `branchPrefix` (wired to ship + ship-spike branch creation).

- **Skill descriptions: trigger-quality vs body-completeness:** UX lens caught that `/flow:security-review`'s description didn't mention the doc-only skip — the auto-trigger machinery would fire on doc-only diffs that mention "rendering" in prose, then skip — wasted spin-up. Added "Skips doc-only diffs" to the description. Tradeoff: longer description, slightly more parse cost, but cleaner trigger contract.

- **Reviewer-notes template ellipses vs explicit null-finding:** UX lens caught that `_Findings:_ ...` reads as unfilled placeholder. Replaced with explicit empty-shape pattern (`Nothing of consequence` / `—`). Tradeoff: slightly more verbose; clearer signal to human reviewers.

- **Hook 2 known bypasses (warn-only vs hard-enforce):** Security lens noted bypasses (python -m, env-var indirection, equals-form arg). Choices: (a) widen regex to catch more, (b) drop the hook entirely, (c) keep warn-only and document bypasses. Chose (c) — the in-script `cwd` constraint in `extract_session.py` is the load-bearing defense; the hook is documented as belt-to-braces. Consumers wanting hard enforcement can change `exit 0` → `exit 2`.

**Lessons learned:**

- **Dogfooding caught 2 BLOCKERs that all the pre-commit greps + claude plugin validate + smoke test missed.** Specifically: (1) Skill missing from ship.md allowed-tools — runtime-only failure; (2) memoryHardCap dead slot — semantic mismatch between schema doc and implementation. Both classes are now FB entries (FB-0002 and FB-0003). The pattern is the same as PR 1's discovery that stale `agents/auditor.md` refs in shipped prompts survived the cold-read: only running the loop end-to-end exposes the surface.

- **The bootstrap exception is now FULLY lifted for PR 3+.** All review skills exist + work. Future PRs in the umbrella should walk themselves through `/flow:staff-review` + `/flow:security-review` (+ `/flow:accessibility-review` for UI work) WITHOUT having to spawn Agent subagents manually — the SKILLs themselves do that.

- **Per-phase commits with co-author trailer made the dogfood traversable.** When the engineer lens flagged the `Skill` missing from `allowed-tools`, locating the change took seconds (it was in Phase 6's commit message verbatim). Monolithic commits would have hidden the regression in noise.

- **Schema design needs the "every slot has a consumer" check.** Two of 13 slots in v1.1.0's first commit had no consumer — caught by engineer lens, fixed in Phase 7. FB-0003 captures the rule. The check can be a pre-commit grep; should land as a one-liner in flow's own preflight when that exists.
