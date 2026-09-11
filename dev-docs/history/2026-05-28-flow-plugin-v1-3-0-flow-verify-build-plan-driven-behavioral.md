### Flow plugin v1.3.0 — `/flow:verify-build` plan-driven behavioral verification gate (PR Q) `SAFETY`
**Date:** 2026-05-28
**Branch:** `claude/lucid-matsumoto-730ba0`
**Commits:** `e722a9b` (PR Q skill) + `4cd5bbc` (staff-review fixes) + `5ad95f2` (manifest bump + flow self-config)

**What was done:**
Added `/flow:verify-build`, the third final-pass reviewer in `/flow:ship` Step 2 (alongside `/flow:security-review` and `/flow:accessibility-review`). Wraps bundled `/verify` (transitively `/run` + `/run-skill-generator`) with flow-specific orchestration: plan-driven criteria extraction from `**Spec-walk:**` checkboxes, fresh-context adversarial transformation, per-dimension parallel judges (PASS/FAIL/Unknown with two-citation evidence), Unknown-blocking gate per FB-0011, and structured findings buffer routed to `/flow:ship` Step 4a FB-XXXX synthesis. Closes the static-analysis-only gap in the loop's verification surface (Potemkin-interface / hallucinated-success class — the dominant agentic-dev failure mode no current flow step catches).

New plugin surface:
- `plugins/flow/skills/verify-build/SKILL.md` (~310 lines) — 9-step orchestrator
- `plugins/flow/skills/verify-build/lib/` — extract-criteria.py + 4 prompt files (adversarial.md, rubric.md, spike-rubric.md, not-tested-checklist.md) + findings-schema.json (JSON Schema draft-07) + findings-example.json
- 3 eval fixture sets: verify-unknown-blocks/, verify-toy-web-app/, verify-budget-overrun/ (14 fixture files)
- Schema slots: `platform`, `verifyEnabled`, `verifyFindingsPath`, `verifyBudgetCalls` (17 → 21)
- ship-spike Step 2 invokes verify-build in spike mode (3-check rubric)
- doctor Check 5.3 detects whether `/run-skill-generator` has been run
- workflow.md Step 10 + skills cheat sheet + config slots table; bootstrap.md Step 5.5 + migration.md Stage 1.5 name `/run-skill-generator` as Tier-1 prerequisite
- `flow.config.json` added at repo root: `platform: library` + `uiSurface: false` + `defaultBranch: main` (flow self-dogfoods the new schema by opting out of verify-build at platform check)

**Why:**
The 11-step loop verifies through static analysis only — typecheck/lint at Preflight, staff-review reading code at Step 7, security/a11y reviewers reading the diff at ship Step 2. No step actually runs the binary. The dominant agentic-dev failure mode is "Potemkin interface" (Replit Agent 3) / hallucinated success (Arize field analysis): an agent claims a feature works because it compiled, types passed, the diff looks plausible — when the button does nothing, the API call 400s and is silently swallowed, or rendered state never matches intent. PR Q closes that gap with a runtime gate that blocks ship on Unknown verdicts.

**Design decisions:**
- **Thin wrapper around bundled `/verify` rather than reimplementing run-and-observe** — first-pass draft proposed 20+ files with 5 platform runners (web/ios/android/tauri/cli) duplicating what bundled `/verify` + `/run` already do. User caught this; redraft shrinks to ~6 lib files leaning on bundled skills as the execution layer (FB-0015 lesson). Same pattern `/flow:security-review` and `/flow:accessibility-review` already follow.
- **Per-dimension parallel judges (correctness / regression / scope-creep) rather than one mega-judge** — Anthropic's evals guidance recommends one judge per dimension to reduce dimension contamination. Parallel for speed + position-bias isolation.
- **Unknown is a gate-blocking verdict** — Per FB-0011 (autonomy bar — ESCALATE on uncertainty). Judge forced to admit ignorance rather than fabricate PASS. Two-citation rule binding: verdict without verbatim observation quote + criterion quote ⇒ Unknown.
- **Findings-buffer JSON shape forward-compat with future HTML case-study renderer** — Per user vision note 2026-05-28. Buffer schema (per-criterion text + per-adversarial-case text + per-step observation captures with `type` discriminator + per-dimension verdict with evidence + top-level "not tested" checklist) is a superset of what an eventual HTML renderer needs. PR Q ships the JSON; the renderer PR (post-PR-Q) renders against this contract. No schema migration required.
- **Spike-mode (3-check rubric) for `/flow:ship-spike`** — Launch / one happy step / no log errors. Single-dimension (correctness only — regression + scope-creep are not meaningful without a plan defining scope). Same Unknown-blocking semantics; lower bar in number of checks, not verdict rigor.
- **Inherits FB-0012 bounded-retry contract from PR M** — Judge runs single-pass; budget cap (verifyBudgetCalls slot) forces Unknown on overrun (mechanical exit signal per FB-0012(a) — no judge-output loop); reward-hacking guards (no test-disabling, no @ts-ignore/eslint-disable) baked into adversarial.md prompt per FB-0012(c).
- **Flow self-config as `platform: library`** — flow itself has no runtime; verify-build cleanly skips at Step 1.2 platform check. Dogfoods the new schema slot; provides the canonical "this is a library plugin" reference config for any plugin-like consumer.

**Technical decisions:**
- **POSIX-portable shell** in SKILL.md `!` blocks (no bash arrays — dash compatibility per FB-0010 silent-skip discipline). External CLI fail-fast (FB-0009).
- **JSON Schema draft-07 with `additionalProperties: false`** at every level of findings-schema.json — strict. Additive changes require explicit schema bump; prevents drift.
- **8 observation type discriminators** (screenshot / a11y_snapshot / network / console / log / stdout / exit_code / narrative) — covers what bundled `/verify` can return + structured captures from Playwright/XcodeBuildMCP, with `narrative` as the freeform fallback.
- **Optional `timestamp_offset_ms` on observations** — relative-to-verify-start, for the future renderer's timeline layout. Absolute timestamp anchor deferred to PR R+ (FOLLOW-UP routed).
- **Spike-mode preserves schema shape** — regression + scope-creep dimensions emitted as Unknown with `evidence: ["(spike mode — dimension not applicable)", "<criterion>"]` so downstream consumers (ship Step 4a, future HTML renderer) don't need spike-aware branching.
- **Verify-build does NOT auto-skip on doc-only diffs** — unlike security + a11y, behavioral changes can live in non-code files (config-driven toggles, etc.). The run-and-observe loop is cheap to attempt; falls through to Unknown if nothing observable.

**Tradeoffs discussed:**
- **Single big PR vs phase-staged PRs.** User chose Path B (full skill on one branch, single PR) over Path A (intake PR + phase PRs). Reasoning: ship one focused PR per skill; let queued PRs (N/O/P/R) build on top regardless of sequencing order. PR Q is orthogonal to N/O/P/R (different files; mechanical rebase in either order). Ship order = whichever finishes first.
- **Wrap bundled `/verify` vs inline orchestration in `/flow:ship` Step 2.5.** Chose Shape A (separate skill) over Shape B (inline). Justifications: ship-spike composability, eval testability, separation of concerns, future Preflight-tier extensibility, standalone invocability for power users wanting flow's plan-criteria + Unknown gate vs bundled `/verify`'s freeform observation. Precedent: `/flow:security-review` resolves the CLAUDE.md "don't wrap bundled" ambiguity in favor of substantive-added-value wrappers.
- **Ship-only single-tier vs two-tier (Preflight fast-subset + ship full-pass).** Two-tier rejected — fast subset meaningless on iOS (60s min build+boot) and Android (~30s emu boot); slowing iterate cycles to catch a class reviewers can also catch is a bad trade. Mid-iterate verification available via bundled `/verify` directly.
- **Adversarial transformation: inline `lib/adversarial.md` vs named subagent.** Inline. Promote to `plugins/flow/agents/verify-adversarial.md` on rule-of-three (consistent with `flow:close-out` precedent).
- **VLM pairwise instruction kept in v1 rubric.** Default-safe — if bundled `/verify` returns screenshots structurally and judge doesn't pairwise-compare, scores are unreliable. Phase 1 empirical characterization may drop this if `/verify` is confirmed text-only.

**Lessons learned:**
- **Always check the harness's available-skills list before drafting a new flow skill** (FB-0015 — captured this PR). The 20+-file first-pass draft duplicated bundled `/verify` + `/run` + `/run-skill-generator` because I didn't audit available-skills at session start. Concrete pre-planning check: grep for the proposed skill's core verb (verify, run, audit, review, ship); if a match exists, justify the wrapper with substantive added value or drop the skill.
- **FB number / PR letter coordination is non-trivial under cross-worktree parallelism.** Drafted as FB-0010 → FB-0012 → FB-0013 → FB-0014 → FB-0015 across the session as collisions surfaced. PR letter drafted as M → Q after bounded-retry PR M took the slot. K1's reserved-feedback-numbers.md protocol made the collisions visible before merge; without it the cross-file references would have silently pointed at the wrong concepts (FB-0010 fan-out class applied to FB numbers).
- **Staff-review caught a fan-out BLOCKER on the manifest descriptions** (17-slot references that survived the diff). Doctor Check 2.5's scan misses install-surface JSON (`.claude-plugin/marketplace.json` + `plugins/flow/.claude-plugin/plugin.json`). FB-0010 strikes again; routed as FOLLOW-UP to extend Check 2.5's scan.
- **Flow's own `flow.config.json` was missing.** Adding it as `{platform: library, uiSurface: false}` IS dogfooding the schema — useful both for self-protection at /flow:ship invocation AND as a reference config for any plugin-like consumer.
