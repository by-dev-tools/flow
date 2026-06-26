# Flow

A Claude Code plugin that runs every coding task through one loop: clarify, plan, build, review, ship. You approve the plan and you merge the PR. Everything in between runs without you.

It exists to catch the mistakes that are cheap to fix early and expensive to fix late: plans that drift from the request, "done" claims that were never verified, code that ships without review. Each one gets a checkpoint.

Install once and every project on your machine can use it.

## The loop

The workflow is a progression of skills held together by two human gates. The skills (indented `↳`) fire in order on their own; the plain rows are the steps they attach to — including the two gates, which are the whole point and are not skills. Once you approve the plan, everything runs to the open PR without you.

| Step | What it does |
|---|---|
| **Clarify & plan** | Claude reads your source-of-truth docs, asks 2–4 questions, and writes a plan: a checkbox per requirement, a confidence rating per assumption. |
| ↳ `/flow:critique-plan` | Checks the plan for scope drift, spec violations, and internal incoherence against your request and reference docs. |
| ↳ `/flow:audit-plan` | Checks the plan for unverified assumptions and recall ("we ruled this out" with no fresh read). |
| **Gate 1 · you approve the plan** | Nothing is built until you do. A low-confidence assumption forces a question here first. |
| **Execute** | Claude builds against the checkboxes, runs preflight (typecheck / build / test), and commits per phase. Pauses only if preflight is red. |
| ↳ `/simplify` | Cold-reads the diff for duplication, dead code, and footguns; fixes in place. *(Built into Claude Code.)* |
| ↳ `/flow:staff-review` | Four reviewers in parallel — engineer, UX, design-engineer, and a "push further" lens — triage findings and fix what's cheap. |
| **Present** | Claude confirms the work is genuinely done, then advances to ship or stops and explains why. Your feedback here loops back through the sequence. |
| ↳ `/flow:audit-completion` | Vets "done / fixed / ready" claims for false-verification — a passing build is not a verified behavior. |
| ↳ `/flow:ship` | Opens the PR after a final pass; updates the project docs; commits and pushes. **Never merges.** Runs four checks first: |
| ↳ `/flow:security-review` | XSS, secrets, unsafe URLs, path traversal, dependency and persistence risk. Skips doc-only diffs. |
| ↳ `/flow:accessibility-review` | WCAG 2.1 AA audit. Skips non-UI diffs. |
| ↳ `/flow:verify-build` | Runs the built artifact, adversarially tested against the plan's criteria. A failure opens the PR as a draft with a `🚫 NOT READY TO MERGE` manifest. |
| ↳ `/flow:audit-coverage` | Flags changed behavior no criterion covers — the gap between "what was tested" and "what changed." |
| **Gate 2 · you merge the PR** | Claude never runs `gh pr merge`. |

So the autonomous path narrows to two touchpoints: **approve the plan → merge the PR.** The skills fire automatically *within a driven loop*, not from a cold "build me X" — see [automation boundaries](docs/automation-boundaries.md) for exactly what runs on its own.

## What the reviewers catch

The two review agents are deliberately narrow — they flag with specific evidence or stay silent. "No issues" is a valid result.

**Auditor** — unverified claims:

| Category | Fires on |
|---|---|
| Unverified diagnosis | A confident root-cause claim acted on with no investigation behind it |
| Unverified completion | "Done / fixed" backed only by a build or typecheck passing |
| Unverified assumption | A load-bearing plan premise that's in neither the request nor the session |
| Unverified recall | "We tried X" / "ruled this out" with no fresh read of the named file |

**Plan-critic** — plan integrity:

| Category | Fires on |
|---|---|
| Scope drift | A plan element outside the request, or a requested one that's missing |
| Spec violation | A step that contradicts a reference doc or an earlier decision |
| Internal incoherence | Steps that contradict each other, or success criteria that don't map to the goal |

Each runs as a Claude Code subagent. Full prompts: [`auditor.md`](plugins/flow/agents/auditor.md), [`plan-critic.md`](plugins/flow/agents/plan-critic.md).

## The feedback loop

When a reviewer is wrong, say so in plain language — "finding 2 is a false positive, the spec rule doesn't apply here." The `log-disagreement` skill detects the pushback and captures the exchange to `~/.claude/plugins/data/flow/disagreements/` as a candidate eval fixture for the next round of prompt tuning.

Three layers compound across sessions: user corrections shape *what* gets built, agent memory shapes *how*, and patterns that recur graduate into mechanical preflight checks. Each promotion takes work off the next session's plate. The promotion to a permanent check is user-gated, and the memory corpus is capped and periodically audited to keep it from ossifying.

## Setup

```sh
# 1. Install (once per machine, inside a Claude Code session):
/plugin marketplace add by-dev-tools/flow
/plugin install flow@flow

# 2. Bootstrap a project (from its root):
bash /path/to/flow-checkout/template/base/bootstrap.sh --stack web   # or swift | tauri-rust-ts

# 3. Fill the {{PLACEHOLDER}}s in CLAUDE.md / README.md / .claude/rules/safety.md, then verify:
/flow:doctor
```

`/flow:doctor` runs a PASS/FAIL punch-list and ends in a `[READY]` verdict, with a fix command for anything it flags. `/flow:workflow-help` prints the loop and your resolved config — the onboarding front door.

Adoption guides: [new project](docs/bootstrap.md) · [existing project](docs/migration.md) · [your first PR](docs/first-pr.md) · [upgrading](docs/upgrade.md).

## Under the hood

- **2 review agents** (`auditor`, `plan-critic`) + **4 staff-review lenses** (engineer, UX, design-engineer, push-further) + 2 context-isolation helpers (`planner`, `docs`).
- **4 auto-loading rules** that attach by file path — workflow discipline, plan requirements, doc format, exploration triggers.
- **A 24-slot `flow.config.json`** ([schema](plugins/flow/schema/flow.config.schema.json)) so every doc path, command, and branch name is configurable, never hardcoded.
- **A template directory** (`template/`) with per-stack overlays for web, Swift, and Tauri/Rust/TS — the scaffolding `bootstrap.sh` copies in.
- **No runtime dependencies.** Python stdlib for preprocessing; Markdown for everything else. No API calls — the plugin delegates to Claude Code subagents.

The canonical reference — every step with its rationale, gate semantics, spike/tiny modes, and config defaults — is [`plugins/flow/docs/workflow.md`](plugins/flow/docs/workflow.md).

## Auxiliary skills

| Skill | When |
|---|---|
| `/flow:workflow-help` | "What's the workflow?" — prints the loop + your config |
| `/flow:doctor` | After bootstrap, or when something feels off |
| `/flow:ship-spike` | Throwaway exploratory PRs — skips the heavy reviews |
| `/flow:log-disagreement` | Fires on its own when you dispute a finding |

## Boundaries & limitations

What runs automatically vs. what needs a keystroke, the soft-enforcement seams, and the honest list of known gaps: [automation boundaries](docs/automation-boundaries.md). Per-version detail: [`CHANGELOG.md`](CHANGELOG.md).

## License

MIT — see [LICENSE](LICENSE).
