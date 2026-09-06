### Flow plugin v1.2.0 — template directory + bootstrap docs + PR-2 follow-up absorption (PR 3 of extraction umbrella)
**Date:** 2026-05-25
**Branch:** pr3/template-directory
**Commit:** 215c875..[push] (7 phase commits; PR opened at Phase 8)

**What was done:**
Shipped the consumer-side scaffolding so a new project can adopt flow in ~10 minutes per `docs/bootstrap.md`. Three deliverable surfaces:

1. **`template/base/`** (11 files) — Tier 1 (CLAUDE.md.template, README.md.template, flow.config.json.example, .claude/settings.json.example, .claude/rules/safety.md.template, .gitignore.template) + Tier 2 (5 core-docs scaffolds with format headers: spec, plan, roadmap, history, feedback).
2. **`template/stacks/{web,swift,tauri-rust-ts}/`** (16 files) — per-stack overlays: preflight runner (web/tauri = .mjs; swift = .sh), CI workflow yaml, `.gitignore.append`, UI rules (web + tauri), dev-server rule (web + tauri), link skill (web + tauri), swift safety.md.append.
3. **`docs/bootstrap.md`** (NEW projects, ~8 KB) + **`docs/migration.md`** (EXISTING projects, ~11 KB; renamed PR A/B/C → Stage 1/1.5/2 to eliminate umbrella numbering collision).

Plus absorbed 2 PR-2 FOLLOW-UPs as security regression fixtures:
4. **`plugins/flow/evals/security/test_cwd_constraint.py`** — 4 strong asserts on `extract_session.py` `--reference-paths` defense (rejects absolute outside-cwd via content-sentinel check, accepts with opt-out, accepts under-cwd, rejects dotdot traversal).
5. **`plugins/flow/evals/security/test_malicious_config.py`** — 3 asserts on `flow.config.json` shell-meta handling (jq -r is string-safe across 10 string slots, sh -c "$TYPECHECK" executes per documented trust model, critique-plan referenceGlob preserves literal string in quoted-arg form).
6. **`plugins/flow/evals/run_security_evals.py`** — discovery-based runner companion to `run_evals.py`.

Plus schema slot #14 added: **`rustWorkspaceDir`** (consumer of the tauri preflight script that was dead per FB-0003 rule).

Manifest bump: v1.1.0 → v1.2.0 (additive; no breaking changes).

Phased execution (Phases 1-8, all success criteria verified):

- **Phase 1:** Schema slot enumeration; md-manager web-stack signal survey (npm scripts, settings.json hook patterns, .gitignore baseline). 4 observations recorded; per-PR plan committed.
- **Phase 2:** template/base/ Tier 1 (6) + Tier 2 (5). Placeholder consistency verified (caught + fixed `INSTALL_STEPS` vs `INSTALLATION_STEPS` inconsistency pre-commit).
- **Phase 3:** 3 stack overlays. node --check on the .mjs runners; bash -n on the swift .sh runner; ci.yml structural grep.
- **Phase 4:** bootstrap.md (~7.9 KB, 6 steps, covers 3 stacks) + migration.md (~11.2 KB, 3 stages with validation gate at Stage 1.5). Migration deletion list verified against md-manager-pr4-6-spec.md (12/12 expected items).
- **Phase 5:** 2 security fixtures + runner. Bug caught + fixed during execution (parents[3] → .parent.parent.parent in path derivation). All 7 asserts pass.
- **Phase 6:** Bootstrap verification — followed `docs/bootstrap.md` Steps 1-5 from scratch in `/tmp/flow-bootstrap-smoke/` for the web stack. Plugin loaded; 5 user-visible skills surfaced via `/help`; preflight chain ran end-to-end (typecheck pass; build + test fail as expected for empty smoke project, demonstrating the gate contract works); claude plugin validate clean. Swift + tauri preflight runners verified syntax-only (no Xcode/cargo env in this session). All template paths referenced by bootstrap.md resolved (12/12).
- **Phase 7:** Dogfood via 3 parallel lens Agents (engineer+simplify combined, push-further, security; skipped UX-designer + design-engineer + accessibility with explicit reason — pure docs+template+JSON-example surface). Caught 4 BLOCKER + 9 NIT + 4 FOLLOW-UP findings; all BLOCKER + NIT fixed in commit `33428e6`; FOLLOW-UPs routed to dev-docs/plan.md.
- **Phase 8:** This entry. Manifest bumped 1.1.0 → 1.2.0; history.md + plan.md + feedback.md FB-0004 written; PR opens at end of phase.

**Why:**
PR 3 of the flow extraction umbrella. After PR 3 ships, md-manager (the canonical reference consumer) can run PRs 4 → 5 → 6 against a complete v1.2.0 surface — install non-breaking using the template, dogfood, then delete duplicates. Without PR 3, md-manager PR 4 has nothing to derive its `flow.config.json` shape from. Now flow ships its own consumer scaffolding.

PR 3 also absorbs 2 of the 8 PR-2 FOLLOW-UPs (the eval coverage items) because PR 3 was touching the eval surface anyway — closes them as concrete tests rather than open promises.

**Design decisions:**

- **3 stacks for v1.2.0 (web / swift / tauri-rust-ts), not more.** Matches the umbrella's stated targets. Python / Go / Rust-only / Ruby / etc. defer to v1.3+ if/when consumers ask. Shipping 3 well > shipping 7 thinly.
- **Tier 1 + Tier 2 base split.** Tier 1 = required for any consumer (CLAUDE.md, flow.config.json, settings.json, safety.md, README, .gitignore). Tier 2 = recommended-but-shippable-empty core-docs scaffolds (spec/plan/roadmap/history/feedback) with format headers. Consumers who want flow but don't care about the doc discipline can skip Tier 2. Tier 1 is non-negotiable.
- **Bootstrap docs as 6 numbered steps, not collapsed to 4.** Push-further lens suggested collapsing install+copy and verify+smoke. Held the 6-step shape: each step has a different verification outcome; collapsing would compress two distinct cognitive transitions into one. PR 4 dogfood will surface whether the step count feels heavy in practice — FB-0004 captures the watch-this-pattern signal.
- **`$comment-*` keys in flow.config.json.example.** Push-further suggested replacing with a sibling `.example.md` cheat-sheet. Held: putting docs in a separate file means consumers hold two files in their head during bootstrap. The bootstrap step explicitly tells them to strip the comments. FB-0004 captures this for PR 4 reconsideration.
- **Migration Stage 1/1.5/2 naming, not PR A/B/C.** Push-further caught the umbrella numbering collision (PR 4/5/6 in flow's plan vs PR A/B/C in migration doc). Stage names match the parenthetical labels the doc already used.
- **`.claude/settings.json.example` documents intentional divergence from default-hooks.json.** Initially claimed "pulled from" — false. Switched to "modeled on … differs intentionally" + named the differences (POSIX case vs bash [[]] + omitted *.pem/*_rsa patterns). Replicating default-hooks.json verbatim was the alternative; chose documented-divergence because the template needs POSIX-portability and the omitted patterns produced false positives in earlier consumer feedback.

**Technical decisions:**

- **Preflight scripts share the same shape pattern (loadConfig → runGate → summary) but ship as 3 separate files**, one per stack. Push-further routed "shared helper library" as FOLLOW-UP — defer until a 4th stack lands or until an existing stack's preflight needs a behavior change that has to land in all three.
- **Security fixtures live under `plugins/flow/evals/security/`**, separate from `plugins/flow/evals/fixtures/` (auditor regression). Different runner (`run_security_evals.py`), different shape (assert-on-exit-code, not assert-on-rendered-text). Avoids polluting the auditor harness's contract.
- **Strong asserts on content sentinels, not path strings.** PR-3 engineer-lens caught that `assert "/etc/hosts" not in stdout` is vacuous (leak prints `127.0.0.1`, not the path). Switched both rejection + accept tests to content-sentinel checks. **FB-0004** captures the rule.
- **`cp -n` (no-clobber) in all bootstrap recipes.** Security NIT: a user who misreads bootstrap.md as suitable for an existing project would silently clobber CLAUDE.md / README.md / .gitignore. -n + an explanatory note + a pointer at migration.md closes the foot-gun.
- **`rustWorkspaceDir` slot landed in v1.2.0 schema (not deferred).** Engineer NIT: the tauri preflight already read the slot; documenting it inline closes the FB-0003 schema-without-implementation gap (in the wrong direction — implementation-without-schema). Pair landed.

**Tradeoffs discussed:**

- **Skip UX/design-engineer/accessibility lenses in Phase 7 dogfood vs run them anyway.** Skipped with explicit reason: PR 3 is pure docs+templates+JSON-examples — no visual surface, no UI code. Running them would have produced empty reviews (per the staff-review SKILL's "Don't skip a lens... legitimate skip is when a lens genuinely doesn't apply"). Logged explicitly rather than skipped silently.
- **`cp -n` vs `cp --backup=numbered`.** Picked `-n` (skip-existing). `--backup` would preserve clobbered files as `.~1~` versions but adds complexity for the common case (fresh project — nothing to backup).
- **Stage 1.5 vs Stage 2 numbering.** Considered just three stages (1/2/3). Picked Stage 1/1.5/2 because the dogfood gate (Stage 1.5) is structurally a checkpoint, not a deliverable PR like Stages 1 + 2 — the half-step naming reflects that.
- **Bootstrap.md vs migration.md as two files** vs one merged "adopting flow" doc. Two files = clearer entry point for each audience (the first paragraph of each doc tells you whether you're in the right place). Migration doc is 50% longer than bootstrap; merging would dilute both.

**Lessons learned:**

- **Vacuous-pass test asserts are a class of bug only adversarial review catches.** test_absolute_outside_cwd_rejected initially asserted on `"/etc/hosts" not in stdout` — passes trivially because a leak prints content, not the path string. Engineer lens flagged it as a BLOCKER. FB-0004 captures the rule: when writing security regression tests, the assert must check on the THING THAT WOULD LEAK, not on a proxy for it.
- **Schema slots without consumers and consumers without schema slots are symmetric bugs.** PR 2 caught `memoryHardCap` documented-but-not-read; PR 3 caught `rustWorkspaceDir` read-but-not-documented. Both surface the same way: dogfood, not greps. Pre-commit grep recipe from FB-0003 needs the bi-directional version (every consumer reference must have a schema entry AND vice versa).
- **Push-further lens caught two structural design questions (collapsing bootstrap steps, replacing $comment keys with sibling cheat-sheet) that benefit from real-consumer signal before settling.** Held both; routed to plan.md "PR 4+ follow-ups" so md-manager's PR 4 dogfood can pressure-test them. This is the lens working correctly — surfacing direction-worthy questions, not demanding immediate change.
- **Per-phase commits + per-phase verification + per-phase task-list updates compounded.** When Phase 7's lens reviews surfaced 4 BLOCKERs, locating each one took seconds (each was in a specific phase commit's diff). Monolithic commits would have made the dogfood loop more expensive.
