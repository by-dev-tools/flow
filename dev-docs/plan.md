# Plan

## Current Focus

v0.3.0 ships the auto-invoked disagreement loop. Next load-bearing step is replacing the eval harness stub (`evals/run_evals.py:195` reads pre-recorded `.expected.txt` files) with live reviewer invocation so disagreement-captured fixtures can flow back into the regression set.

## Handoff Notes

None.

## Active Work Items

### Verification skill (planned, separate plugin)

Build a sibling plugin (working name: `assumption-verifier`) that takes an `/audit-completion` or `/audit-plan` finding's `Verification checks:` list and executes the checks. Closes the loop between "auditor names a gap" and "user/agent confirms the gap is real" — the gating capability for the long-term trust-staging goal in `spec.md`.

**Architecture decision:** separate plugin, not in `assumption-auditor`. The auditor's identity depends on being passive; mixing active behaviors dilutes the trust guarantee. Separate distribution lets users opt in to the active sibling without forcing it on everyone. Same reasoning pattern as the `forge vs independent marketplace` and `plugin vs in-repo` tradeoffs in history.md.

**Prototype step before committing to a full plugin:**

1. Build a non-shipped skill in this repo (`.claude/skills/verify-finding/`) that takes the most recent ISSUE block from the conversation and tries to execute its `Verification checks:` items.
2. Smoke-test against real audit findings produced by `/audit-completion`. Two open questions only real-session use can answer:
   - Can the human-readable `Verification checks:` list reliably translate into executable steps? (Today these are written for human readers — short imperatives that assume project context.)
   - How often does the user want one-click verify vs. take the suggestion and adapt manually? (Shapes whether the skill is a "run these checks" button or a "draft the test, let me edit" assistant.)
3. If both answers favor automation, split into a separate plugin and follow the `assumption-auditor` shipping pattern (marketplace metadata, version cadence, README, evals).
4. If the answers favor per-project tuning, the verifier may need a configuration model that doesn't fit the plugin pattern — could become a per-project skill template instead.

**Why this matters for the broader arc:** today the auditor surfaces gaps and the user closes them manually. For an agent to ever be trusted at a high-stakes gate (e.g., md-manager plan approval), there needs to be a credible "AI confirmed the gap is real / not real" step. The verifier is that step. Without it, agents are stuck at "AI flags the concern, human resolves it" — useful, but not trust-shifting.

---

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
