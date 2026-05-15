# Plan

## Current Focus

v0.3.0 ships the auto-invoked disagreement loop. Next load-bearing step is replacing the eval harness stub (`evals/run_evals.py:195` reads pre-recorded `.expected.txt` files) with live reviewer invocation so disagreement-captured fixtures can flow back into the regression set.

## Handoff Notes

None.

## Active Work Items

### Disagreement loop (v0.3.0)

Auto-invoked feedback capture so users can push back on findings in plain language without manual slash commands.

**Done:**
- `skills/log-disagreement/SKILL.md` — model-invokable skill (`disable-model-invocation: false`) with a tight description listing the invocation triggers and anti-triggers.
- `scripts/log_disagreement.py` — captures session window (last ~12 turns from the audit output forward) to a `.jsonl`, plus a `.meta.json` with reviewer/category/severity/claim/reason. Stored under `~/.claude/plugins/data/assumption-auditor/disagreements/`.
- `agents/auditor.md` + `agents/plan-critic.md` — added output footer schema requiring every output to end with the disagreement invitation. Anchors the auto-invocation contract: the model sees the invitation and listens for pushback in the next user message.
- `evals/fixtures/*.expected.txt` — footer appended to all five existing fixtures so they stay aligned with the new schema.
- README updated with the auto-invocation flow.
- `.claude-plugin/{plugin,marketplace}.json` bumped to 0.3.0.

**Next:**
- Real-session smoke test: confirm the model reliably invokes `/log-disagreement` on plain-language pushback. If silent-miss rate is high, add a `UserPromptSubmit` hook in v0.3.1 as a deterministic fallback.
- Maintainer-side tooling: a script that walks `~/.claude/plugins/data/assumption-auditor/disagreements/` and surfaces accumulated disputes by category/frequency.

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
