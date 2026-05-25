---
paths:
  - "**/*"
---

# General Rules (flow plugin)

These apply to all work in any flow-using project. They reinforce the workflow defined in `${CLAUDE_PLUGIN_ROOT}/docs/workflow.md` — they don't replace it. If a rule here contradicts `workflow.md`, `workflow.md` wins (and the contradiction is itself a bug to fix in the plugin).

Doc-path references in this rule resolve via `flow.config.json` slots with built-in defaults (`dev-docs/<name>.md` for flow's own repo; consumer projects typically `core-docs/<name>.md`).

## Workflow discipline

- **Plan before code.** Every non-trivial request gets a plan in the project's plan doc (`flow.config.json.planPath`) with the **required fields from `${CLAUDE_PLUGIN_ROOT}/rules/plan-discipline.md`**: mode, goal, scope (in/out), spec-walk checkboxes, confidence verdict per load-bearing assumption, risks, files touched. Wait for user approval before executing. The exception is `mode: tiny` (a 1–3 line bug fix the user explicitly asked you to "just do") which skips spec-walk + confidence verdict but still gets a one-line plan.
- **Confidence verdicts gate the plan.** Every load-bearing assumption gets HIGH/MEDIUM/LOW per `plan-discipline.md`. **LOW = automatic human gate** — the assumption must be resolved by an explicit user answer before the plan can proceed. `/flow:critique-plan` is advisory; the workflow's enforcement is the human gate.
- **Preflight is a required step, not a tool.** Mechanical gates (the project's `tools/preflight/check.mjs` if present + typecheck via `flow.config.json.typecheckCmd` + build + test + project invariants) must be green before `/simplify` runs. Both `spike` and `tiny` modes still run preflight.
- **Run `/simplify` (bundled with Claude Code) after commit, before `/flow:staff-review`.** Code-quality pass (reuse, clarity, efficiency) lands first so staff-review can focus on architecture and craft instead of "this could be shorter." Both are part of the standard loop — not optional, not just for "big" changes. **Spike mode skips both** (the code is disposable; craft review on throwaway is theater).
- **The PR opens at `/flow:ship`, not before.** Mid-pipeline PRs create half-done state and force the PR body to lie about completed reviews / doc synthesis. See `${CLAUDE_PLUGIN_ROOT}/docs/workflow.md` § "Why the PR opens here, not earlier" for the full rationale. Spike-mode PRs open at `/flow:ship-spike` (also end-of-pipeline, just lighter).
- **`/flow:ship` owns narrative doc updates** (history doc, plan doc "Recently Completed", roadmap doc, spec doc, feedback doc). Don't update them piecemeal during execution. The carve-outs: **mechanical contract artifacts** (a component manifest, a generation log, a pattern log — anything that's tracked state, not narrative) update inline with the change; the plan doc's "Active Work Items" is allowed to update mid-feature for handoff/checkpoint purposes.
- **During a session, track corrections in your head (or scratchpad).** `/flow:ship` will surface them and write the feedback-doc entry as part of synthesis (step 4a). Don't update the feedback doc mid-conversation.
- **Agent self-feedback is captured at `/flow:ship` step 4b**, not earlier. Memory entries (`~/.claude/projects/.../memory/feedback_*.md`) must clear the 5 guardrails in `${CLAUDE_PLUGIN_ROOT}/docs/workflow.md` § "Continuous improvement" — especially the source-diversity bar (evidence from 2-of-3 sources). Single-source findings don't earn an entry.
- **Read before writing.** At session start: the plan doc for "Current Focus" + "Handoff Notes." Before UI work: also the feedback doc and the design-language doc (if the project has one). Before any plan: also the spec doc.
- **Never merge.** `gh pr merge` is not a Claude action.

## Mode flags

Every plan declares one of three modes:

- **`feature`** (default) — full 11-step loop in `${CLAUDE_PLUGIN_ROOT}/docs/workflow.md`.
- **`spike`** — exploratory PR that answers a question, not a feature ship. Skips `/simplify` + `/flow:staff-review`; uses `/flow:ship-spike` (which still runs preflight and writes a history entry as the deliverable). See `workflow.md` § "Spike mode" for the abuse-prevention guards.
- **`tiny`** — 1–3 line fix the user said "just do." Skips spec-walk, confidence verdict, `/simplify`, `/flow:staff-review`. `/flow:ship` for tiny mode skips synthesis (step 4) and goes straight to commit + push + PR. Rarely the right call; bias toward the full loop.

## Scope discipline

- Do what was asked. Don't refactor adjacent code, add unrequested features, or "improve" things that work.
- No dead code, commented-out code, unused imports, or placeholder files.
- If something isn't needed yet, don't create it.
- **New scope discovered mid-execution: surface to the user, don't silently absorb.** Update the plan with a fresh confidence verdict for the new assumption, get approval, then continue. This is the implicit human gate during Execute (workflow.md step 3).

## Decision tracking

- When a change involves a non-trivial decision (a reasonable alternative existed), note the tradeoff so `/flow:ship` can capture it in the history doc. A one-line scratch note is fine; `/flow:ship` will write the formal entry.
- "What" goes in the code change itself. "Why" goes in the history doc at ship time.
- Tradeoffs are the most valuable part of the history doc — they're what future sessions need to avoid re-litigating.

## Autonomous work guardrails

This workflow is **hybrid managed autonomy** — human-gated at Plan (step 2) and Merge (step 11), with autonomy-friendly primitives between. Even inside the autonomous portion, always confirm with the user before proceeding if the action involves:

1. **Cost exposure** — API calls that could hit rate limits or incur charges, adding paid services.
2. **Permanence** — irreversible changes (deleting data models, breaking migration paths, force pushes, `rm -rf`).
3. **Risk** — security-sensitive changes, privacy implications, anything where a reasonable person might disagree.

Bug fixes, spec compliance, reliability work, and polish can proceed autonomously inside the workflow (still requires a plan + user approval at step 2).

## When this file goes stale

If you notice this file contradicts the project's CLAUDE.md or `${CLAUDE_PLUGIN_ROOT}/docs/workflow.md`, **flag it** to the user. A stale rule file actively misleads every future session. The fix is a plugin-side PR; the cost of leaving it is every PR after.
