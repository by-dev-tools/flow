### Flow plugin v1.2.4 — workflow-spawn skip prevention (FB-0010 workflow-step sub-class)  `SAFETY`
**Date:** 2026-05-27
**Branch:** `pr-i/workflow-spawn-prevention`
**Commit:** [SHA at ship time]

**What was done:**
Encoded the 9th FB-0010 incident as a workflow discipline. PR H1's review surfaced that the author ran `gh pr create` directly instead of invoking `/flow:ship`, skipping `/flow:ship`'s Step 2 pipeline (which spawns `/flow:security-review` + `/flow:accessibility-review`). The skip was justified after-the-fact ("would have early-exited anyway") but missed that the `STATUS: SKIPPED` audit-trail signal is load-bearing regardless of body execution.

Defenses encoded across 4 surfaces:

1. **`plugins/flow/skills/staff-review/SKILL.md`** (consumer-shipped) — new "After this skill" footer naming `/flow:ship` as the canonical next step. Reframes the existing "ends with work ready, not merged" line into actionable forward motion. Direct fix for the inflection point where the author would naturally choose between `/flow:ship` and `gh pr create`.

2. **`plugins/flow/skills/ship/SKILL.md` Step 1.0** (consumer-shipped) — visual emphasis (`⚠️` per ASSUMES line) + a new REMINDER paragraph naming the workflow-step silent-skip class explicitly + the "Always invoke /flow:ship, never `gh pr create`" rule.

3. **`plugins/flow/docs/workflow.md` Step 10** (consumer-shipped) — new "Never bypass `/flow:ship` with `gh pr create` directly" subsection. Names the failure mode: skipping `/flow:ship` skips the entire Step 2 (security + a11y reviews); the STATUS: SKIPPED line is load-bearing audit-trail. Canonical reference for the discipline.

4. **`.claude/rules/general.md` Workflow discipline subsection** (project-dev only) — auto-loads on every edit in this repo. Mirrors the workflow.md statement scoped to flow's own dev infrastructure.

Plus CHANGELOG.md v1.2.4 entry + manifest version bump v1.2.3 → v1.2.4 in both `.claude-plugin/marketplace.json` + `plugins/flow/.claude-plugin/plugin.json`.

**Why:**
PR H1's review pipeline missed `/flow:security-review` + `/flow:accessibility-review` entirely until the user caught it. Root cause: I bypassed `/flow:ship` and ran `gh pr create` manually. 1 incident isn't usually enough for FB encoding (FB-0010 was encoded after 6), but the fix is trivially mechanizable as prompt-level reminders. MEDIUM confidence in plan.md names the fallback: if a 2nd workflow-spawn-skip occurs after PR I, the next step is orchestration-level auto-spawn in `/flow:staff-review` (requires session-introspection helper that doesn't exist).

**Design decisions:**
- **Reduced scope from 12 files to 9.** Initial plan included reviewer-skill exit footers on staff-review + critique-plan + audit-plan + audit-completion + log-disagreement (5 SKILL.md files). Reading the latter 4 surfaced rigid `## Output` blocks ("Do not add commentary before or after.") that would conflict with appended footer prose. Reduced to staff-review only. Plan-critic Finding 1 REDIRECT confirmed this independently; Finding 3 BLOCKER (fan-out file count contradiction in the original plan) was also surfaced by plan-critic and validates FB-0010 working on its own defense PR.
- **Primary fix vs defense-in-depth.** Staff-review footer + `/flow:ship` Step 1.0 strengthening + workflow.md Step 10 are primary (directly address the bypass). `.claude/rules/general.md` is defense-in-depth (project-dev only).
- **No orchestration auto-spawn.** Considered auto-spawning security/a11y from `/flow:staff-review` Step 4. Rejected because it duplicates `/flow:ship` Step 2 (drift risk), needs session-introspection that doesn't exist, and prompt-level reminders are the cheap-first defense with auto-spawn as named fallback.
- **v1.2.4 patch-level.** Additive workflow guardrails — no skill behavior, contract, or schema changed.
- **SAFETY marker** because of `plugins/flow/skills/ship/SKILL.md` + both manifests (all on safety.md paths list). Runtime authority unchanged.

**Technical decisions:**
- Workflow.md Step 10 subsection placed BETWEEN pipeline list and "Why the PR opens here" — linear flow: pipeline → discipline → rationale.
- General.md subsection placed AFTER "Consistency discipline" and BEFORE "Autonomous work guardrails" — narrative arc: general → consistency → workflow → autonomy.
- CHANGELOG v1.2.4 entry follows Keep-a-Changelog-style format established in PR H1.

**Tradeoffs discussed:**
- **Encode-after-1-incident vs wait for 2-3.** FB-0010 encoded after 6. This is 1 incident of new sub-class. Decision: encode now because fix is cheap + user explicitly chose this over dogfood-first.
- **Reviewer-skill footer scope.** Wanted footers on all 5; rigid `## Output` blocks on audit/critique skills constrained to staff-review only.
- **Project-dev rule vs consumer-shipped rule.** Considered adding to `plugins/flow/rules/general.md` (consumer-shipped). Decided project-dev only because workflow.md Step 10 already carries the consumer-side contract; adding it as a rule too would be fan-out.

**Lessons learned:**
- **Plan-critic + parallel execution + self-correction converged on the same fix.** Plan-critic returned NOT APPROVED with a BLOCKER (fan-out count contradiction); independently I'd discovered the audit/critique-plan conflict and reduced scope. Two paths to the same answer.
- **FB-0010 self-application caught itself.** Plan-critic flagged "fan-out count contradiction inside the FB-0010 defense PR." The discipline works on its own defense PR. Catching it pre-commit validates the discipline.
- **Discipline-PR for 1-incident class is defensible when fix is mechanical.** Threshold isn't hard; it's "is encoding cost less than expected recurrence cost?" Cheap reminders justify low threshold. Invasive orchestration changes require higher threshold.
