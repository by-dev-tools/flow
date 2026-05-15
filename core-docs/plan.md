# Plan

## Current Focus

v0.1.0 plugin scaffold is shipped. Next load-bearing step is replacing the eval harness stub (`evals/run_evals.py:195` reads pre-recorded `.expected.txt` files) with live auditor invocation, then capturing fixtures for the three SKIP'd canonical cases in `evals/ground_truth.yaml`.

## Handoff Notes

None.

## Active Work Items

### Plan critic (sibling to the evidence auditor)

A second subagent that critiques a proposed plan against intent and reference docs, complementing the evidence auditor. Three categories — scope drift, spec violation, internal incoherence — with severity tiers (BLOCKER / REDIRECT / FOLLOW-UP) and an explicit `APPROVED` signal for the agent-driven plan-approval gate.

**Done:**
- `agents/plan-critic.md` prompt drafted with two-citation discipline and severity tiers
- `skills/critique-plan/SKILL.md` — user-invocable entry point, mirrors the audit-plan skill pattern (`disable-model-invocation: true`, `context: fork`, `agent: plan-critic`); preprocesses with `--reference-glob "core-docs/*.md"`
- `scripts/extract_session.py` extended with `--reference-paths` and `--reference-glob` (opt-in). Reads matching docs from CWD, skips `history.md` / `plan.md` / `roadmap.md`, caps each doc at 12000 chars. Existing audit-plan / audit-completion flows unaffected.
- `evals/fixtures/scope_drift_form_fix.{jsonl,expected.txt}` — exercises scope-drift category
- `evals/fixtures/spec_violation_bundled_ui.{jsonl,expected.txt}` — exercises spec-violation category; reference rule embedded via in-session Read of `core-docs/feedback.md`
- `evals/fixtures/internal_incoherence_jwt_migration.{jsonl,expected.txt}` — exercises internal-incoherence category; two contradictory plan steps (keep + remove same file)
- `evals/ground_truth.yaml` entries with `reviewer: plan-critic` dispatch field (harness does not yet use it)

**Next:**
- Add a fixture that exercises the new `--reference-glob` path (rule lives only in the loaded doc, not in session) to prove the deterministic-context mechanism end to end
- Wire `evals/run_evals.py` to live invocation, with `reviewer:` field dispatching to the right subagent and `--reference-glob` passed through for plan-critic cases
- Stage trust before replacing the human approval gate (see workflow ref: md-manager `staff-review` pattern)

**Cross-repo follow-ups (md-manager, not this plugin):**
- Add a Clarify-step rule that the plan-writer Reads reference docs before drafting the plan (informs the planner, independent of the critic's deterministic context)
- Insert step 3.5 in `core-docs/workflow.md` to run `/critique-plan` between plan-written and user-approval

---

## Recently Completed

- **Project-dev scaffolding** (2026-04-20) -- CLAUDE.md, core-docs, .claude/ infra added with plugin-vs-dev boundary documented.

## Backlog

- Wire `evals/run_evals.py` to live auditor subagent invocation (remove `.expected.txt` stub)
- Capture fixtures for `trio_navigation_stack_cycle_3`, `portfolio_blank_screen`, `trio_morphing_recall`
- Structured output schema for auditor (replace substring matching in eval checks)
- Expand artifact regex beyond the hardcoded 28-extension list in `scripts/extract_session.py`
- Raise or remove the 50-call tool-history cap in `scripts/extract_session.py`
- Generalize hardcoded SwiftUI proxy handling to other frameworks
