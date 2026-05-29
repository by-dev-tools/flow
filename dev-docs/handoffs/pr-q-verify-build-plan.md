# PR Q — `/flow:verify-build`: plan-driven behavioral verification gate at ship

**Mode:** feature (medium) | **Priority:** high | **Horizon:** v1.3.0 (target manifest bump; may shift based on what's on main at ship time)
**Branch:** `claude/lucid-matsumoto-730ba0` during execution; renamed to `pr-q/verify-build-skill` at ship time (or `/flow:ship` creates it from this branch's state).
**Execution path:** **Path B — full skill built on this branch through all 11 phases; ships as a single PR when Phase 11 dogfood completes.** Not an intake-PR-then-phases pattern; one PR per skill.
**Status:** Phase 1 complete + Phase 2 partial (intake commit `afaa54e`); **Phase 3 in progress.** Remaining: Phases 3–11 (real prompts + fixtures + ship/doctor integration + workflow.md cascade + manifest bump + staff-review dogfood).

**Predecessor context (as of 2026-05-28):** PRs 1–3 + A–J + H1/H2 (docs cadence) + M (bounded-retry preflight) + K1 (reserved-feedback-numbers protocol) merged; plugin at **v1.2.6** on main. PRs N (research-driven orchestration hardening), O (test-edit reward-hacking PreToolUse hook), P (auditor model-diversity evaluation) queued behind M, targeting different surfaces than PR Q.

**Sequencing — orthogonal to N/O/P, not queued behind them:** N/O/P target `/flow:ship` preflight + reviewer infrastructure (Step 1c bounded-retry hardening, test-edit interception, auditor model swap). PR Q targets `/flow:ship` Step 2 final-pass review surface (alongside security-review + accessibility-review). Different files in the diff; no real content dependency. PR Q rebases onto main as N/O/P land — the rebase is mechanical. If PR Q ships before N: PR N rebases against a main that includes verify-build (cleanly — different surface). If N/O/P ship first: PR Q rebases (cleanly — different surface). Inherited locked patterns from already-shipped work (FB-0012 bounded-retry from PR M) bind verify-build's judge + budget design at Phase 4 / Phase 5.

**Letter history:** an earlier scoping iteration of this work was numbered "PR M" in conversation drafts (2026-05-27 → 2026-05-28 morning); a parallel work stream landed bounded-retry as PR M (commit `0cf642e`) before the verify-build scoping commits could be pushed. Renumbered to PR Q to resolve the collision; FB-0014 resolved per K1's reserved-feedback-numbers protocol (deferred FB-0013 to PR P's planned same-model-critic entry).

**Rebase strategy (Path B):** Between each phase commit, run `git fetch origin && git rebase origin/main`. Conflict surface should be near-zero — N/O/P touch `/flow:ship` Step 1c + auditor.md + new hook file; PR Q touches new files under `plugins/flow/skills/verify-build/` + `/flow:ship` Step 2. The only shared file is `dev-docs/{plan,feedback,roadmap,history}.md` cascades, which conflict cleanly (additive). Manifest version target shifts only at Phase 11 when the bump lands — current target v1.3.0 (signals new public skill surface); may go to v1.4.0 if N/O/P all minor-bump first.

This is a per-PR plan in the shape of `dev-docs/handoffs/pr2-flow-plan.md`. It will be summarized into `plan.md` § Active Work Items at execution time.

---

## Why this PR exists

The 11-step loop verifies through **static analysis only**: typecheck/lint at Step 4 (Preflight), staff-review reading code at Step 7, security/a11y reviewers reading the diff at Step 10. **No step actually runs the binary.**

The dominant agentic-dev failure mode is "Potemkin interface" (Replit Agent 3) / hallucinated-success (Arize field analysis): an agent claims a feature works because it compiled, types passed, and the diff looks plausible — when in fact the button does nothing, the API call 400s and is silently swallowed, or the rendered state never matches intent. No current flow step catches this class.

`/flow:verify-build` closes the gap by **wrapping bundled `/verify` with flow-specific orchestration**: plan-driven criteria extraction, Unknown-aware blocking gate, and feedback-loop routing. It is **not** a reimplementation of `/verify` — it is the gate-shaped wrapper, same pattern `/flow:security-review` and `/flow:accessibility-review` already follow vs their bundled equivalents.

## What bundled skills already do (FB-0014 discipline — check bundled first)

Per Anthropic's documentation (https://code.claude.com/docs/en/skills § "Run and verify your app"), Claude Code ships a 3-piece system, not standalone commands:

- **`/run-skill-generator`** (bundled, v2.1.145+): scaffolds a per-project launch recipe at `.claude/skills/run-<name>/`. One-time setup. `/run` and `/verify` automatically defer to this recipe.
- **`/run`** (bundled): Launches via the scaffolded recipe, or falls back to heuristic by project type (CLI, server, TUI, browser-driven, library). Reads README, `package.json`, `Makefile` for inference.
- **`/verify`** (bundled): Invokes `/run` + observes the running app + reports observations. Output is freeform stdout (no documented JSON schema, no PASS/FAIL contract). Docs explicitly: "Confirm a code change does what it should by building your project's app, running it, and observing the result, rather than relying on tests or type checks."

The documented extension point for plugin authors is `/run-skill-generator`'s output — ship a project run skill that `/run` and `/verify` automatically pick up. There is **no documented hook surface** for intercepting `/verify` directly.

These three cover the execution layer entirely. `/run-skill-generator` covers per-project launch scaffolding. `/run` covers dispatch. `/verify` covers the run-and-observe loop. Anything flow ships in the execution layer is duplication.

**Implication for flow:** every consumer of `/flow:verify-build` must have run `/run-skill-generator` once at project setup; flow's bootstrap docs must name this as a prerequisite alongside MCP install. Without the recipe, `/run` falls back to heuristic launch, which the Anthropic docs themselves describe as "unreliable for projects that need anything beyond a standard launch: a database, an env file, a graphical session, a multi-step build." Flow's verify gate fires on a `/verify` that can't launch, returns Unknown, the gate becomes noise.

## What `/flow:verify-build` adds (the actual scope)

Five orchestration concerns the bundled skills don't have:

1. **Plan-driven criteria.** Reads `**Spec-walk:**` checkboxes from `flow.config.json.planPath`, runs an adversarial transformation (1–2 "what would break this" cases per checkbox the implementer didn't author), feeds the result to `/verify` as the verification script. Generic `/verify` has no knowledge of flow's plan format.
2. **Unknown-aware blocking gate.** Per-dimension judge schema with explicit `Unknown` as a valid output; `Unknown ⇒ exit 1` so `/flow:ship` Step 2 can block on it. Generic `/verify` is descriptive, not gate-shaped.
3. **Findings buffer for `/flow:ship` Step 4a synthesis.** Emits structured JSON to a known path; `/flow:ship` Step 4a reads + merges into `feedback.md` FB-XXXX (single writer; no numbering races).
4. **Fixed "what we did NOT test" checklist.** Per-platform `✗/✓` list rendered into the PR body — closed-form list, not free-form prose (so agents can't under-list by accident).
5. **`/flow:ship` Step 2 integration.** Invoked alongside `/flow:security-review` and `/flow:accessibility-review` with parallel skip semantics.

## Placement in the loop

**Single-tier: `/flow:ship` Step 2 only.** All criteria + adversarial transformations + per-dimension parallel judges run at ship time, alongside `/flow:security-review` and `/flow:accessibility-review`.

Two-tier placement (Preflight fast-subset + ship full-pass) was considered and rejected: the "fast subset" is meaningless on iOS (60s minimum to build + sim boot) and Android (~30s emulator boot), so any tier worth running there isn't fast. Slowing the iterate cycle on half the supported platforms to catch a class reviewers can also catch is a bad trade.

Mid-iterate verification remains available — invoke **bundled `/verify` directly** for ad-hoc "does this work yet" checks during execution. Flow's verify gate runs once at ship.

If iterate-time data later shows demand for a fast subset (users repeatedly running bundled `/verify` between iterate cycles and missing flow's plan-criteria + Unknown gate), revisit in v1.4.

## Spike mode

`/flow:ship-spike` invokes `/flow:verify-build --spike` which uses a **fixed minimal spike rubric** instead of plan criteria:

- Does it launch without error?
- Does the headline path execute one happy step?
- Are there any uncaught console / log errors?

Three boolean checks; same Unknown-blocking semantics. Spike doesn't have a plan to derive criteria from, so flow ships the minimal rubric inline.

## Scope (in)

**New skill (~5 files):**

1. `plugins/flow/skills/verify-build/SKILL.md` — orchestrator. Steps:
   - **1.** External-CLI / MCP dependency check (FB-0009 pattern; checks bundled `/verify` + `/run` are available; per-platform MCP — Playwright / XcodeBuildMCP / mobile-mcp — only if needed for the detected platform). **Also checks: `.claude/skills/run-*/` exists** (a per-project run recipe scaffolded by `/run-skill-generator`); if absent, emit loud warning naming the missing recipe and the one-line fix (`/run-skill-generator`). Continue rather than block — heuristic-launch /verify may still work — but the warning surfaces the gap.
   - **2.** Spike-mode branch: if invoked with `--spike` or no `planPath` exists, use the fixed spike rubric and skip steps 3–4.
   - **3.** Extract criteria from plan via `lib/extract-criteria.py`.
   - **4.** Adversarial transformation: for each criterion, generate 1–2 "what breaks this" cases (separate subagent prompt so the implementer doesn't grade its own homework).
   - **5.** Invoke `Skill('verify')` with the criteria list as the verification script. (Bundled `/verify` calls `/run` internally for the launch, which in turn defers to `.claude/skills/run-*/` if scaffolded. Flow doesn't reimplement any layer.)
   - **6.** Per-dimension parallel judge pass: spawn N subagents, one per dimension (correctness, regression, scope-creep), each with an `Unknown`-allowed rubric. Parallel both for speed and position-bias isolation.
   - **7.** Aggregate: any dimension returning `Unknown` ⇒ exit 1 with structured findings. Any dimension returning `FAIL` ⇒ exit 1. All `PASS` ⇒ exit 0.
   - **8.** Emit findings buffer to `/tmp/flow-verify-findings.json` (path slot: `flow.config.json.verifyFindingsPath`, defaults inside `/tmp/`) for `/flow:ship` Step 4a to merge.
   - **9.** Render "what we did NOT test" fixed checklist into stdout for the PR-body author.
2. `plugins/flow/skills/verify-build/lib/extract-criteria.py` — parses `flow.config.json.planPath` for the current-PR `**Spec-walk:**` block; emits one criterion per checkbox. Graceful fallback ("no criteria parsed") when plan format is non-standard.
3. `plugins/flow/skills/verify-build/lib/rubric.md` — judge prompt template; one-dimension-per-call; explicit `Unknown`-allowed schema with pairwise-comparison instruction for any screenshot-judging dimension (per VLM-cannot-score-only-rank research).
4. `plugins/flow/skills/verify-build/lib/spike-rubric.md` — fixed 3-check spike rubric.
5. `plugins/flow/skills/verify-build/lib/not-tested-checklist.md` — per-platform fixed checklists (web / iOS / android / cli / library) for the "did NOT test" stamp. Closed-form lists; agent flips ✗ → ✓ only where it actually tested.

**Workflow integration (modify, don't add):**

6. `plugins/flow/skills/ship/SKILL.md` Step 2 — add `Skill("flow:verify")` invocation parallel to security/accessibility; mirror skip semantics. Step 4a — read findings buffer from step 5 above and synthesize into feedback.md.
7. `plugins/flow/skills/ship-spike/SKILL.md` — invoke `/flow:verify-build --spike` at its Step 2 equivalent.
8. `plugins/flow/docs/workflow.md` — document `/flow:verify-build` invocation under Step 10 (`/flow:ship`) Step 2 alongside security + accessibility reviewers; add note that mid-iterate verification is available via bundled `/verify` directly; update skills cheat sheet + config slots table. No new step in the 11-step loop.
9. `plugins/flow/schema/flow.config.schema.json` — add three slots:
   - `verifyEnabled` (bool, default `true`) — global opt-out.
   - `verifyFindingsPath` (string, default `/tmp/flow-verify-findings.json`) — where Step 8 writes.
   - `verifyBudgetCalls` (int, default `60`) — hard cap on MCP tool calls per run; over-budget ⇒ Unknown ⇒ block (fail closed).
10. `docs/bootstrap.md` + `docs/migration.md` — name MCP install prerequisites per platform (Playwright MCP for web, XcodeBuildMCP for iOS, mobile-mcp for Android); reference bundled `/verify` and `/run` as the execution layer flow leans on; **add Tier-1 bootstrap step: "Run `/run-skill-generator` once after install to teach `/run` and `/verify` how to launch your project; `/flow:verify-build` leans on this implicitly."** Without this, heuristic launch may fail and flow's verify gate produces Unknown noise.

11. `plugins/flow/skills/doctor/SKILL.md` — add **Check 5.3 — project run skill present** to Section 5 (optional infrastructure). Detects `.claude/skills/run-*/`; PASS if present, WARN with `/run-skill-generator` fix hint if absent. Gated on `flow.config.json.verifyEnabled`: skipped (`[SKIP]`) when verify is disabled. Surfaces the missing recipe at install/setup time rather than at first `/flow:ship`. Update summary count for Section 5 to reflect the new check.

**Evals:**

11. `plugins/flow/evals/fixtures/verify-criteria-extract/` — fixtures: standard plan with N checkboxes / plan without `**Spec-walk:**` heading / plan with malformed checkboxes / no plan file at all (spike mode).
12. `plugins/flow/evals/fixtures/verify-unknown-blocks/` — judge stub returns `Unknown` for one dimension; assert `/flow:verify-build` exits 1 and findings buffer contains the Unknown route.
13. `plugins/flow/evals/fixtures/verify-budget-overrun/` — fake high-tool-call run; assert budget-cap fires and routes to `Unknown`.

**Manifest:** v1.2.x → v1.3.0 (additive but new public skill warrants minor).

## Scope (out)

- **Platform-specific runners** (`{web,ios,android,tauri,cli}-runner.md`). Bundled `/run` handles platform dispatch. Flow doesn't reimplement.
- **Platform detection lib** (`platform-detect.sh`). Bundled `/run` already detects across CLI/server/TUI/Electron/browser-driven/library. Flow's `platform` slot is no longer needed — defer to bundled detection.
- **Per-platform schema slots** (`platform`, `verifyEntryPoint`). Bundled `/run` infers from project structure. Adding flow slots would create a divergence with bundled behavior.
- **`verify-judge.md` subagent.** Judge prompt lives inline in `lib/rubric.md`; invoked via Task tool with rubric as system prompt. No separate agent file.
- **Visual-regression baselines** (image diff against stored golden). v1.4+. Pairwise screenshot judging IS in scope as a tertiary signal; baseline management is not.
- **Auto-fix on failure.** Verify is a gate; the fix is the agent/user's call after.
- **Performance budgets** beyond the tool-call budget. Chrome DevTools MCP can expose perf data; converting to enforced budgets is v1.4+.
- **LLM-generated test cases.** Adversarial transformation produces edge cases from plan criteria; freeform test generation is a different concern.
- **Real-device iOS / Android testing.** Simulator/emulator only in v1. Real-device support requires per-project provisioning that doesn't generalize.
- **Native-desktop apps without a webview.** Computer-use territory; v1.4+.
- **Heal-once-on-locator-drift.** This is a regression-test-maintenance feature; v1 verify is stateless (each run derives criteria from current plan). Belongs in v1.4 visual-regression workstream.

## Locked patterns from PRs 1–P (still binding)

- **FB-0009** fail-fast on missing external CLIs / MCPs at Step 1 with install hint.
- **FB-0008** stale-base check at Step 1 — inherited from `/flow:ship`'s gate; no need to re-check here since `/flow:verify-build` invoked from ship runs after that gate.
- **FB-0010 (consistency discipline)** — both silent-skip and fan-out subclasses apply here. Silent-skip defense: every `2>/dev/null` / `// empty` / `|| true` paired with explicit positive assertion before consumer reads the value; missing-MCP and missing-run-skill paths emit `[WARN]` / `[SKIP]` with named cause, never empty-stdin-into-grep. Fan-out defense: when adding the three new schema slots (`verifyEnabled`, `verifyFindingsPath`, `verifyBudgetCalls`), grep for the slot-count value across README + CLAUDE.md.template + doctor + bootstrap.sh + workflow.md and update in lockstep (current count post-PR-M is 17 per `/flow:doctor` description; bumps to 20 with this PR).
- **FB-0011 (autonomy bar)** — `/flow:verify-build`'s gate routing follows the same `AUTO-FIX-SAFE` / `ESCALATE` model. Verify-build doesn't auto-fix (it's a gate, not a remediation skill), but the *escalation default* applies: when in doubt → `Unknown` → ESCALATE → exit 1 → user adjudicates. No silent pass-through, no fix-and-continue without explicit confidence.
- **FB-0012 (bounded-retry — `/flow:ship` Step 1c contract from PR M)** — directly binding on verify-build's judge + budget design:
  - **(a) Mechanical exit signal only.** Verify-build's `verifyBudgetCalls` cap (Step 5) loops on bundled `/verify`'s observable tool-call count, NOT on a judge-approval signal. The per-dimension judge (Step 6) runs single-pass — no retry-until-PASS loop. If a future Phase wants to add transient-failure retry around bundled `/verify` invocation, the retry MUST gate on `/verify`'s exit code (mechanically verifiable), not on judge verdict.
  - **(b) Cap + orthogonal abort.** If verify-build ever grows a retry primitive, it inherits PR M's N=3 + diff-hash oscillation pattern. v1 doesn't retry — single-pass + Unknown ⇒ block — but the architecture must not preclude inheriting M's pattern if added.
  - **(c) Explicit reward-hacking guards.** The adversarial-transformation prompt (Step 4) and judge rubric (Step 6) must explicitly forbid the implementing agent from disabling tests / suppressing warnings / patching assertions to satisfy a criterion. Inherit PR M Step 1c's verbatim guard language: *"do not modify or disable tests, do not add `@ts-ignore` / `# noqa` / `eslint-disable-next-line` or equivalent suppressors."*
- **FB-0014 (check bundled first)** — applied to this PR's redraft (rationale for thin-wrapper shape and no platform-runner reimplementation).
- **3-tier fallback chain** for any path resolution.
- **Loud-warning pattern** for unset slots — never silent no-op.
- **POSIX-portable shell** in `!` blocks (no bash arrays — dash compat).
- **Per-skill "Config slots used" table** at the bottom.
- **Project-agnostic** — no md-manager / flow-internal tokens hardcoded.
- **Subagent prompts** parallel `auditor.md` / `plan-critic.md` structure when subagents are spawned (judge dimensions in step 6 use this shape; PR J's over-engineering-warning + prove-or-disprove preamble pattern applies to the rubric judge).
- **PR N detection-point wiring (if it ships first)** — if PR N's research-driven orchestration hardening lands a generic Detection-Point-N pattern at `/flow:ship` Step 2 by PR Q's start, `/flow:verify-build` integrates via that pattern rather than inventing a parallel one.

## Spec-walk

- [ ] `plugins/flow/skills/verify-build/SKILL.md` exists with 9 steps; references bundled `/verify` and `/run` via `Skill('verify')` / `Skill('run')`, not platform-runner reimplementations.
- [ ] `allowed-tools` frontmatter includes `Skill, Bash, Read, Edit, Write, Agent, Task` (FB-0002 discipline — explicit allowlist for every tool invoked).
- [ ] Bundled-skill availability check at Step 1: `command -v <bundled-skill-check> >/dev/null || …` (or whatever the bundled-skill discovery shape is — verify at Phase 1).
- [ ] `.claude/skills/run-*/` existence check at Step 1: if absent, loud warning emitted naming `/run-skill-generator` as the fix; does NOT block (continues to heuristic launch).
- [ ] `docs/bootstrap.md` Tier-1 prerequisites name `/run-skill-generator` alongside MCP install.
- [ ] `/flow:doctor` Section 5 includes Check 5.3 (project run skill present); PASS / WARN / SKIP semantics correct; gated on `verifyEnabled` slot; summary count updated.
- [ ] Spike-mode branch fires when invoked with `--spike` arg OR when `flow.config.json.planPath` resolves to a non-existent file.
- [ ] `lib/extract-criteria.py` parses standard `**Spec-walk:**` blocks; produces N criteria for N checkboxes; gracefully degrades to "no criteria parsed" on non-standard plans.
- [ ] Adversarial transformation produces 1–2 edge cases per criterion via a Task subagent with a prompt distinct from the implementing agent's context.
- [ ] Judge schema in `lib/rubric.md` requires every dimension to return one of `PASS | FAIL | Unknown` — no free-form scores; pairwise comparison instruction for any screenshot-judging dimension.
- [ ] `Unknown` in any dimension ⇒ exit 1; eval fixture proves it.
- [ ] Findings buffer JSON shape documented at top of `verifyFindingsPath` schema slot; `/flow:ship` Step 4a reads it.
- [ ] "What we did NOT test" stamp is a per-platform closed-form checklist; agent must flip ✗→✓ explicitly per item.
- [ ] `flow.config.json.verifyEnabled=false` ⇒ `/flow:verify-build` exits 0 with a clean "[verify] disabled via config; skipping." message; `/flow:ship` Step 2 surfaces this in the consolidated review-results line.
- [ ] Budget guard: `tool-call count ≥ verifyBudgetCalls` ⇒ emit `Unknown` and route to feedback. Eval fixture proves it.
- [ ] workflow.md has new Step 4.5; cheat sheet + config-slots table updated; loop diagram reflects 4.5 placement.
- [ ] `claude plugin validate .` clean.
- [ ] Smoke test (web): run `/flow:verify-build` against a known-good toy Vite project; verify happy-path exit 0 with structured findings.
- [ ] Smoke test (spike): run `/flow:verify-build --spike` against a repo with no plan; verify minimal-rubric path fires.
- [ ] Smoke test (none): run `/flow:verify-build` against flow's own repo (library/docs, no UI); verify clean skip with "no verifiable platform detected; skipping" or similar via bundled `/run`'s library-detection.
- [ ] **Forward-compat:** findings-buffer JSON shape supports downstream HTML rendering without schema migration — per-criterion text + per-adversarial-case text + per-step observation captures with `type` discriminator (`screenshot` / `a11y_snapshot` / `network` / `console`) + per-dimension verdict with two-citation evidence + top-level "not tested" checklist. PR Q does not render HTML; the schema is forward-compat for PR N. (Vision: `roadmap.md` § Exploration "Verify-build HTML case-study report".)

## Confidence verdicts

**1. Bundled `/verify` + `/run` are stable enough to wrap.**
**Confidence:** HIGH
**Why:** Both shipped with Claude Code; described in the harness available-skills surface at every session start. They're official Anthropic surface, not third-party. Anthropic has documented commitment to skills as a contract layer.
**If it flips:** A bundled skill is renamed or removed in a Claude Code update. Detection: `command -v` style check at Step 1 fails ⇒ loud warning ⇒ exit 1 with install hint. Single-skill-update fix in flow.

**2. Plan Spec-walk format is a stable extraction target.**
**Confidence:** HIGH
**Why:** Every per-PR plan since PR 1 uses `- [ ] <criterion>` under `**Spec-walk:**`. Six PRs (1, 2, 3, A, B–E queued) conform. plan-critic.md enforces.
**If it flips:** A consumer's plan uses different formatting. extract-criteria.py emits "no criteria parsed" warning; verify falls back to spike-rubric or asks user to confirm scope.

**3. Adversarial-transformation subagent catches Potemkin without false-positive noise.**
**Confidence:** MEDIUM
**Why:** The transformation prompt is the critical surface. Too aggressive and the gate becomes noisy and ignored; too lax and the gate misses hallucinated success. Calibration needed.
**If it flips:** Iterate the prompt; add `--adversarial-strictness` slot for consumer override; surface in evals.

**4. Unknown-aware judge actually catches hallucination without being overzealous.**
**Confidence:** MEDIUM
**Why:** Whole point of Unknown-blocking is forcing the judge to admit ignorance. But if Unknown fires too often (e.g., on screenshots where VLM can't read fine text), the gate becomes ignored — same failure as overzealous CI. Calibration matters.
**If it flips:** Per-dimension thresholds; calibration against a held-out human-graded eval set during Phase 4.

**5. Single-tier placement (ship Step 2 only) is the right v1 shape.**
**Confidence:** HIGH
**Why:** Fast-subset Preflight tier was considered and rejected — meaningless on iOS (60s build+boot minimum) and Android (~30s emulator boot). Slowing iterate cycles on half supported platforms to catch a class reviewers can also catch is a bad trade. Mid-iterate verification remains available via bundled `/verify` directly.
**If it flips:** Iterate-time demand surfaces (consumers repeatedly running bundled `/verify` between cycles, missing flow's plan-criteria + Unknown gate). Revisit in v1.4 with a `verifyPreflightFastSubset` slot.

**6. Consumers will actually run `/run-skill-generator` at bootstrap.**
**Confidence:** MEDIUM
**Why:** It's a one-line command, documented in bootstrap.md as Tier-1, and the Step 1 warning fires every verify if skipped. But it's still an extra step a hurried consumer can skip, and the consequence (heuristic-launch noise) doesn't manifest until first `/flow:ship`.
**If it flips:** Heuristic-launch noise dominates consumer reports. Mitigation: promote the Step 1 warning to BLOCKER (exit 1 instead of continue); add a `flow.config.json.requireRunSkill` slot with default `false` initially, flipping to `true` once docs adoption is verified.

## Risks

- **Slowness undermines adoption.** 30–120s per /flow:ship is the worst case. Mitigation: only invoke from ship (and the fast subset from Preflight); `verifyEnabled=false` opt-out; cache warm dev server across iterate loops.
- **MCP install friction.** A consumer without Playwright MCP gets a verify-skip every ship for web projects. Mitigation: bootstrap.md names the MCPs as Tier-1 prereqs alongside `gh`/`jq`/`node`; consider `bootstrap.sh` extension to install MCPs as a follow-up.
- **VLM judge cost.** Per-dimension calls + screenshots add up. Mitigation: hard `verifyBudgetCalls` cap (default 60); over-budget ⇒ Unknown ⇒ block (fail closed, never silent).
- **Adversarial transformation may be inconsistent.** A different model or a context-poisoned implementing agent could produce weak edge cases. Mitigation: spawn the transformation subagent in a fresh context (Task tool with isolated session); calibrate against eval fixtures.
- **Findings-buffer write contention.** If two `/flow:verify-build` runs overlap (unlikely but possible during iterate), the buffer gets clobbered. Mitigation: include timestamp + PID in buffer path; `/flow:ship` reads the freshest matching the current branch.
- **Bundled-skill semantic drift.** `/verify` or `/run`'s behavior could change between Claude Code versions in a way that breaks flow's wrapper assumptions. Mitigation: pin the integration's expectations explicitly in SKILL.md prose ("invokes bundled `/verify` expecting it to return non-zero on failure"); regression eval against fixture project catches drift.

## Phased execution

Each phase ends with one commit; per-phase verifiable success criteria.

- **Phase 1 — Verify bundled-skill integration shape. ✓ COMPLETE 2026-05-28** (commit pending). SKILL.md skeleton at `plugins/flow/skills/verify-build/SKILL.md` contains the documented `/verify` contract (input/output, delegation through `/run` and `/run-skill-generator`, screenshot return TBD). Empirical verification deferred to first real `/flow:verify-build` run; documented as TODO in the SKILL.md "Bundled-skill integration contract" section.
- **Phase 2 — Skill skeleton + criteria extractor. ◐ PARTIAL 2026-05-28.** `lib/extract-criteria.py` real implementation landed + smoke-tested against PR A's actual Spec-walk block (3 of 3 visible criteria extracted; format-detection working). **Remaining Phase 2 work:** 4 fixtures under `evals/fixtures/verify-criteria-extract/` (standard / no-Spec-walk / malformed / no-plan); eval harness wiring. Also remaining: current-PR-scoping logic (extractor currently extracts ALL Spec-walks from a multi-PR file; needs branch-name → PR-letter → section-scope refinement before integration).
- **Phase 3 — Adversarial transformation prompt.** `lib/adversarial.md` prompt + Task-subagent invocation pattern. Test against the criteria extractor's output. **Success:** transformation produces 1–2 distinct edge cases per criterion on a sample plan.
- **Phase 4 — Rubric judge + Unknown-blocks fixture.** `lib/rubric.md` schema; judge invocation in Step 6; aggregation in Step 7. Eval fixture: judge stub returns Unknown ⇒ exit 1. **Success:** Unknown-blocks fixture passes.
- **Phase 5 — Findings buffer + ship Step 4a wiring.** `lib/not-tested-checklist.md` per-platform; Step 8 buffer write; `/flow:ship` Step 4a buffer read + FB-XXXX merge. **Success:** buffer roundtrip works; FB entries land in feedback.md format.
- **Phase 6 — Spike-mode branch.** `lib/spike-rubric.md` + step 2 branch; `/flow:ship-spike` Step 2 wiring. **Success:** spike-mode against a no-plan repo fires correctly.
- **Phase 7 — /flow:ship Step 2 integration.** `Skill("flow:verify")` invocation; skip-message parity with security/accessibility. **Success:** ship's review-results line includes verify.
- **Phase 8 — workflow.md + docs cascade + doctor check.** Document /flow:verify-build under Step 10 (`/flow:ship`) Step 2; mid-iterate-via-bundled-/verify note; cheat sheet + config slots table; bootstrap.md + migration.md MCP prereqs + `/run-skill-generator` Tier-1 step. Add `/flow:doctor` Check 5.3 (project run skill present) gated on `verifyEnabled`. **Success:** workflow.md cross-refs consistent; bootstrap.md includes the run-skill-generator step; `/flow:doctor` against a fixture project with no run skill emits the expected WARN.
- **Phase 9 — Smoke + budget overrun fixture.** Toy Vite app fixture + smoke; budget-overrun fixture. **Success:** smoke passes end-to-end; budget fixture proves fail-closed.
- **Phase 10 — Dogfood via `/flow:staff-review`.** 4-parallel lens spawn against the PR diff. Absorb BLOCKERs + cheap NITs inline; route FOLLOW-UPs to plan.md. **Success:** at least 3 of 4 lenses ran; all BLOCKERs fixed.
- **Phase 11 — `/flow:ship` + manifest bump + open PR.** v1.3.0 bump; pipeline; PR body; never merge. **Success:** PR open against main; MERGEABLE.

## Files touched (anticipated)

- **New under `plugins/flow/skills/verify-build/`:** `SKILL.md`, `lib/extract-criteria.py`, `lib/rubric.md`, `lib/spike-rubric.md`, `lib/not-tested-checklist.md`, `lib/adversarial.md` (6 files)
- **New under `plugins/flow/evals/fixtures/`:** `verify-criteria-extract/` (4 cases), `verify-unknown-blocks/`, `verify-budget-overrun/`
- **Modified:** `plugins/flow/skills/ship/SKILL.md`, `plugins/flow/skills/ship-spike/SKILL.md`, `plugins/flow/skills/doctor/SKILL.md`, `plugins/flow/docs/workflow.md`, `plugins/flow/schema/flow.config.schema.json`, `docs/bootstrap.md`, `docs/migration.md`, `.claude-plugin/marketplace.json`, `plugins/flow/.claude-plugin/plugin.json`, `dev-docs/{history,plan,feedback,roadmap}.md`

Approximate line counts: SKILL.md ~250 lines; extract-criteria.py ~80 lines; rubric.md ~60 lines; spike-rubric.md ~30 lines; not-tested-checklist.md ~80 lines (5 platforms × ~16 lines each); adversarial.md ~50 lines. Total new code ~550 lines. Compare to original draft estimate of ~2000+ lines.

## What this redraft fixed vs the first-pass draft

| Adversarial finding | Original draft | Redraft |
|---|---|---|
| #1 — Parrots bundled `/verify` (CRITICAL) | Reimplemented run+observe + platform detection | Thin wrapper; delegates to bundled `/verify` + `/run` |
| #2 — PR-1-scale scope | 20+ files, new subagent, 5 platform runners | ~6 new files, no subagent, no platform runners |
| #3 — Wrong placement (Step 9.5 only) | Post-commit gate; high friction | Two-tier: Preflight fast + Ship full |
| #4 — Tautological criteria | Spec-walk used verbatim | Adversarial transformation between extract and drive |
| #5 — No context strategy | Implicit | Judge-per-step + per-dimension parallel + evidence summarization |
| #6 — A11y-tree degradation | Hand-waved | Three-tier signal hierarchy (deferred: bundled `/verify` handles) |
| #7 — Heal-once is wrong primitive | Included | Dropped (v1.4+ regression-test maintenance) |
| #8 — Spike mode undefined | Hand-waved | First-class branch with fixed minimal rubric |
| #9 — Free-form "not tested" stamp | Free-form | Per-platform closed-form ✗/✓ checklist |
| #10 — FB routing collision | Direct write | Structured buffer; `/flow:ship` Step 4a merges |
| #11 — Sequential judges | Implicit | Explicit per-dimension parallel |
| #12 — Overloaded entryPoint slot | Single slot | Dropped (bundled `/run` infers) |
| #13 — Monorepo autodetect | Hand-waved | Dropped (bundled `/run` handles) |
| #14 — Light eval coverage | 4 fixtures | Added: unknown-blocks, budget-overrun, criteria-malformed |
| #15 — Tauri LOW confidence | Included as stub | Dropped (bundled `/run` already handles Electron-shape; Tauri webview when it materializes is consumer-extension territory) |

## Open questions (post-plan-critic on Decision 1, post-Decision-2)

All four design decisions resolved:

- **Decision 1 (skill vs inline):** Shape A — separate skill. Justifications: `/flow:ship-spike` composability, eval testability, separation of concerns (`/flow:ship` already orchestrates 8 phases), future Preflight-tier extensibility, standalone invocability for power users wanting flow's plan-criteria + Unknown gate vs bundled `/verify`'s freeform observation. Precedent: `/flow:security-review` wrapping bundled `/security-review` resolves the CLAUDE.md "don't wrap" ambiguity in favor of substantive-added-value wrappers.
- **Decision 2 (placement):** ship-only single-tier. Fast-subset Preflight rejected — meaningless on iOS/Android. Mid-iterate verification via bundled `/verify` directly.
- **Decision 3 (named agent vs inline adversarial):** inline `lib/adversarial.md`. Promote to `plugins/flow/agents/verify-adversarial.md` on rule-of-three.
- **Decision 4 (VLM pairwise instruction):** keep in v1 rubric, default-safe. Phase 1 characterization to confirm/drop based on whether bundled `/verify` returns screenshot evidence.

**Naming resolved:** `/flow:verify-build`. Verb-target convention (matches `/flow:audit-plan`, `/flow:critique-plan`, `/flow:security-review`). Suffix `-build` names the target (the built artifact being run), distinguishing from bundled `/verify` (general-purpose run-and-observe). Rejected candidates: `/flow:verify-plan` (false-suggests plan-stage operation, conflicts with `-plan` convention); `/flow:verify-test` ("test" overwhelmingly reads as "test suite"); `/flow:smoke` (too narrow — adversarial-criteria pass is more than a smoke check); `/flow:verify` (parrot risk per CLAUDE.md).

Plan-critic BLOCKER (`/run-skill-generator` as documented extension point) absorbed inline as a Step 1 warning + Tier-1 bootstrap step. No open critiques remain blocking.

**Scope-overlap reconciliation with PR K (`/flow:red-team`):** PR K ships an adversarial *static* reviewer (read-only; threat-model categories on diff/code; two-citation evidence; `AUTO-FIX-SAFE` / `ESCALATE` routing). PR Q (`/flow:verify-build`) ships a behavioral *runtime* verifier (executes the built artifact; drives plan criteria; Unknown-blocking gate). Different layers, different inputs, different outputs. They compose: PR K finds latent threats in the code; PR Q confirms the running implementation does what the plan said. Both invoked from `/flow:ship` Step 2 alongside `/flow:security-review` + `/flow:accessibility-review`; no scope collision.

**Pending dependency on PR L:** if PR L lands a generic Detection-Point-N wiring pattern at `/flow:ship` Step 2 (per FB-0011's routing model), PR Q's integration mirrors it rather than inventing a parallel detection-point. Reassess at PR L merge time before Phase 7 of PR Q.

**Forward-compatibility hook for PR N (HTML case-study report — vision note 2026-05-28):** PR Q's findings-buffer JSON should be designed as a superset of what an eventual HTML renderer would need — per-criterion text, per-adversarial-case text, per-step observation captures with `type` discriminator (`screenshot` | `a11y_snapshot` | `network` | `console`), per-dimension judge verdict with two-citation evidence, top-level "not tested" checklist. Phase 4 + Phase 5 acceptance criterion: "JSON shape supports downstream HTML rendering without schema migration." PR Q does NOT render to HTML — just shapes the JSON correctly so PR N can do the rendering work without re-designing the buffer contract. See `roadmap.md` § Exploration entry "Verify-build HTML case-study report" for the full vision (reference artifact: `/Users/benyamron/dev/health-tracker/.claude/worktrees/nervous-meitner-0f88be/case-study.html`).

## Validation against quality bar (CLAUDE.md)

- **Correct:** judge schema matches a documented shape (PASS / FAIL / Unknown per dimension); evals will pass.
- **Evidence-backed:** every new heuristic (adversarial transformation, Unknown-blocks, budget cap) has at least one fixture.
- **Graceful on malformed input:** no-plan / malformed-plan / no-MCP / over-budget all degrade to structured Unknown or clean skip, never silent no-op.
- **Lean:** Python stdlib only for extract-criteria.py; no new dependencies.
- **Project-agnostic:** no flow / md-manager / web-stack tokens hardcoded; all paths through config slots with defaults.
- **Honest limitations:** README + workflow.md "Bootstrap status" + the per-platform "did NOT test" checklist all carry the honest gaps.
