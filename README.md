# Flow

Claude Code plugin marketplace + plugin for the **managed-autonomy workflow**: a single 11-step loop with two load-bearing human gates (plan approval, merge), a third automatic gate on LOW-confidence assumptions, and a feedback pipeline that compounds quality across sessions.

This repo is **the marketplace** (`flow`) and **the only plugin in it** (also `flow`). Install once and every project on your machine can adopt the loop.

## Install

From inside Claude Code:

```
/plugin marketplace add by-dev-tools/flow
/plugin install flow@flow
```

(For local development against this checkout: `/plugin install /path/to/flow`.)

## What v1.0.0 ships

| Skill | What it does | Status |
|---|---|---|
| `/flow:ship` | Final-pass pipeline: review + synthesize feedback + update docs + commit + push + open PR. Never merges. | v1.0.0 (security/a11y reviews and memory machinery placeholdered until PR 2) |
| `/flow:critique-plan` | Plan-critic: scope drift / spec violation / internal incoherence against the user's request and reference docs | v1.0.0 |
| `/flow:audit-plan` | Auditor: unverified assumptions + unverified recall in the most recent plan | v1.0.0 |
| `/flow:audit-completion` | Auditor: false-verification proxies (build passed ≠ behavior verified) on completion claims | v1.0.0 |
| `/flow:log-disagreement` | Auto-invoked when the user pushes back on a finding; captures the dispute for prompt-tuning input | v1.0.0 |

Plus the two reviewer subagents the audit/critique skills wrap (`auditor`, `plan-critic`) and the canonical loop reference at [`plugins/flow/docs/workflow.md`](plugins/flow/docs/workflow.md).

**Coming next:**
- **PR 2** — rest of the workflow surface: `/flow:staff-review` (four parallel lenses), `/flow:security-review`, `/flow:accessibility-review`, `/flow:ship-spike`, `/flow:workflow-help`; portable rules (`general`, `plan-discipline`, `documentation`, `exploration`); context-isolation agents (`planner`, `docs`); `tools/memory/check.mjs`; `flow.config.json` JSON Schema; backfills the PR-1 placeholders inside `/flow:ship`.
- **PR 3** — template directory (`template/base/` + per-stack overlays for web / swift / tauri-rust-ts) so adopting flow in a new project is `cp -r` + minimal edits.

## Project config

Skills read project-specific values from `flow.config.json` at your project repo root. Every slot is optional; flow has sensible defaults but never silently no-ops on an unset slot that would change behavior (see the loud-warning pattern in `/flow:ship`).

The narrative slot table lives in [`plugins/flow/docs/workflow.md`](plugins/flow/docs/workflow.md) § "Project config slots." PR 2 adds a formal JSON Schema.

## The loop

Long-form: [`plugins/flow/docs/workflow.md`](plugins/flow/docs/workflow.md).

Cheat sheet:

```
 1. Clarify          read source-of-truth docs; surface conflicts; ask 2–4
                     targeted questions (or list assumptions if autonomous)
 2. Plan             write plan with spec-walk checkboxes + confidence
                     verdict; run /flow:critique-plan; WAIT for human gate
 3. Execute          implement against checkboxes; stay in scope
 4. Preflight        mechanical gates (typecheck/build/test + invariants) —
                     MUST be green before /simplify runs
 5. Commit           "why" not "what"; co-author trailer; per-phase
 6. /simplify        (bundled with Claude Code) cold-read for reuse,
                     clarity, efficiency; fix in-tree; re-run preflight
 7. /flow:staff-review (PR 2) four lenses in parallel (engineer / UX /
                     design-eng / push-further); BLOCKER + cheap NIT in-tree;
                     FOLLOW-UP → roadmap/plan
 8. Present          reviewer notes + dev URL + branch state; flag MEDIUM-
                     confidence assumptions for user redirect
 9. Iterate          apply user feedback (mini-loop of 1–7)
10. /flow:ship       security + a11y final pass (PR 2 backfill) → synthesize
                     feedback → update docs → commit → push → open PR
11. STOP             the user merges; Claude never does
```

## What the auditor + plan-critic catch

### Auditor ([`plugins/flow/agents/auditor.md`](plugins/flow/agents/auditor.md))

| Category | Fires on |
|---|---|
| Unverified diagnosis | Confident root-cause claim acted on, no investigation supporting it |
| Unverified completion | "Done / fixed / ready" claim backed only by build / typecheck / startup |
| Unverified assumption | Plan premise not in the request, not in session context, load-bearing |
| Unverified recall | "We tried X" / "ruled this out" with no fresh read of the named artifact |

### Plan-critic ([`plugins/flow/agents/plan-critic.md`](plugins/flow/agents/plan-critic.md))

| Category | Fires on |
|---|---|
| Scope drift | Plan element outside the user's request, or absent element the user explicitly requested |
| Spec violation | Plan step that contradicts a rule in the reference docs or established earlier in the session |
| Internal incoherence | Plan steps that contradict each other, or success criteria that don't map onto the goal |

Plan-critic findings carry severity (`BLOCKER` / `REDIRECT` / `FOLLOW-UP`) so calling agents (or you) can decide whether the plan needs revision before approval. A clean critique returns `APPROVED`. A clean audit returns `No issues flagged.`

`/flow:audit-plan` and `/flow:critique-plan` are complementary — they don't duplicate categories. Run both at a plan-approval gate for full coverage; run either alone for a lighter-weight check.

### When to use each reviewer

| Work type | Suggested reviewers | Why |
|---|---|---|
| Bug fix | `/flow:audit-plan` + `/flow:audit-completion` | catches premature diagnosis and "fixed but unverified" — the two most common bug-fix failure modes |
| New feature | `/flow:audit-plan` + `/flow:critique-plan` + `/flow:audit-completion` | catches silent assumptions, scope drift / spec violation, and "shipped but never exercised" |
| Refactor | all three audit/critique skills | surface-area assumptions, scope discipline, and "build passes ≠ behavior preserved" |
| Throwaway prototype | none required | the reviewers' value is in trust contexts; one-off prototypes don't have one |

Features benefit from the audit/critique skills more than bug fixes, not less. Bug fixes have an obvious verification target (does the bug still reproduce?), so the user can manually spot a missing check. Features don't — there's no "before" state to compare against, so the auditor's "you claimed X but didn't check" prompt catches gaps the user would otherwise miss.

## Feedback loop

When a reviewer's output is wrong, **just say so in plain language** — "no, finding 2 is wrong because ...", "false positive on the scope drift", "the spec rule doesn't apply here". The plugin's `log-disagreement` skill auto-invokes when it detects pushback on a recent finding and captures the disagreement to:

```
~/.claude/plugins/data/flow/disagreements/
```

Each disagreement produces two paired files — a `.jsonl` slice of the session (the audit output plus your pushback) and a `.meta.json` with the dispute metadata. These become candidate eval fixtures in the next prompt-tuning pass.

> **Note on the rename from `assumption-auditor`:** flow v1.0.0 absorbed the prior `assumption-auditor` plugin. If you have pre-v1.0.0 disagreement records at `~/.claude/plugins/data/assumption-auditor/disagreements/`, they're preserved in place but no longer accumulate new entries. Move them with `mv ~/.claude/plugins/data/assumption-auditor/disagreements/* ~/.claude/plugins/data/flow/disagreements/` if you want continuity.

For wider feedback that isn't tied to a specific finding (overall behavior, missing features, requested categories), append to [`plugins/flow/DISAGREE.md`](plugins/flow/DISAGREE.md) manually.

### What auto-invocation looks like

After each reviewer returns its findings, every output ends with:

```
---
If a finding is wrong, just say so. Your pushback will be logged for prompt tuning.
```

You don't have to do anything special. Push back in plain language; the skill catches it. You'll see a one-line confirmation when a disagreement is logged.

## Repo layout

```
.claude-plugin/marketplace.json     # marketplace declaration (one plugin: "flow")
plugins/flow/
  .claude-plugin/plugin.json        # plugin manifest
  agents/                           # auditor.md, plan-critic.md
  skills/                           # audit-plan/, audit-completion/, critique-plan/,
                                    #   log-disagreement/, ship/
  scripts/                          # extract_session.py, bounding_logic.py,
                                    #   log_disagreement.py
  evals/                            # ground_truth.yaml, run_evals.py, fixtures/
  docs/workflow.md                  # canonical 11-step loop reference
  DISAGREE.md                       # free-form feedback log
dev-docs/                           # plugin's own dev-tracking (plan.md, history.md,
                                    #   feedback.md, spec.md, workflow.md). Not
                                    #   shipped to consumers — that's template/
                                    #   coming in PR 3.
.claude/                            # this repo's own project-dev infra (rules,
                                    #   agents, skills for building flow itself).
                                    #   Not shipped to consumers.
```

## Known limitations (audit/critique side — tune-points, not blockers)

- Regex artifact detection misses files with no extension or unusual paths
- Tool-call history truncates at 50 calls
- Bounding logic occasionally grabs the wrong user turn (short follow-ups)
- Plan/completion mode detection is heuristic
- SwiftUI proxy handling is hardcoded; other frameworks need explicit additions
- Eval harness reads pre-recorded `.expected.txt` files rather than invoking reviewers live; regression-only, not correctness

## History

This repo was previously published as `byamron/llm-auditor` (marketplace) hosting the `assumption-auditor` plugin. It was renamed in place to `by-dev-tools/flow` on 2026-05-23, and converted from a flat root layout to the Anthropic marketplace + plugin pattern in v1.0.0. The pre-v1.0.0 content (flat root layout, `llm-auditor` marketplace name, `assumption-auditor` plugin name) is recoverable via:

```sh
git checkout pre-flow-plugin
```

GitHub maintains a redirect from `byamron/llm-auditor` → `by-dev-tools/flow`, so old clones still pull from the same place.

## License

MIT — see [LICENSE](LICENSE).
