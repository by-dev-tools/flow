# Flow

Claude Code plugin marketplace + plugin for the **managed-autonomy workflow**: a single 11-step loop with two load-bearing human gates (plan approval, merge), a third automatic gate on LOW-confidence assumptions, and a feedback pipeline that compounds quality across sessions.

This repo is **the marketplace** (`flow`) and **the only plugin in it** (also `flow`). Install once and every project on your machine can adopt the loop.

## Quick start for new projects

```sh
# 1. Install plugin (one-time per machine, from inside a Claude Code session):
/plugin marketplace add by-dev-tools/flow
/plugin install flow@flow

# 2. Bootstrap your project (one command, from your project root):
bash /path/to/flow-checkout/template/base/bootstrap.sh --stack web   # or swift | tauri-rust-ts

# 3. Fill placeholders + verify (from inside your project's Claude session):
#    Edit CLAUDE.md, README.md, .claude/rules/safety.md to replace {{PLACEHOLDER}}s,
#    then:
/flow:doctor   # PASS/FAIL punch-list. Fix what's flagged.

# 4. Try your first PR through the loop:
#    See docs/first-pr.md for a step-by-step walkthrough.
```

**Full bootstrap docs:** [`docs/bootstrap.md`](docs/bootstrap.md) (new project) | [`docs/migration.md`](docs/migration.md) (existing project with prior `.claude/` content) | [`docs/upgrade.md`](docs/upgrade.md) (already installed; picking up a newer version).

**The loop itself:** [`plugins/flow/docs/workflow.md`](plugins/flow/docs/workflow.md) — canonical 11 steps with rationale, gate semantics, spike/tiny modes, config-slot reference.

## What v1.2.5 ships

### Workflow surface (11 user-visible skills)

| Skill | What it does |
|---|---|
| **`/flow:ship`** | Final-pass pipeline: workflow-step assumption surface → stale-base preflight → gh+jq fail-fast → security-review → accessibility-review → BLOCKER/NIT fixes → synthesize feedback (user + agent-memory layers) → update docs → commit → push → open PR. Never merges. |
| **`/flow:ship-spike`** | Lightweight pipeline for spike-mode PRs. Same pre-flight gates as `/flow:ship`; skips heavy reviews; writes history.md entry (the deliverable); opens `spike`-labeled PR. |
| **`/flow:staff-review`** | Four parallel lenses (engineer / UX-designer / design-engineer / push-further), each a separate plugin-shipped agent. Triages BLOCKER / NIT / FOLLOW-UP / EXPLORATION; fixes inline; routes follow-ups. |
| **`/flow:security-review`** | Diff-focused security audit (XSS, secrets, unsafe URL handling, path traversal, dependency risk, persistence leakage). Per-diff early-exit on doc-only PRs via `flow.config.json.sourceFilePatterns`. |
| **`/flow:accessibility-review`** | Diff-focused WCAG 2.1 AA audit. Two early-exit gates: project-wide `uiSurface=false`, and per-diff via `flow.config.json.uiFilePatterns`. |
| **`/flow:workflow-help`** | Prints the 11-step loop + your project's resolved `flow.config.json` slots + skill catalog. Onboarding front door. |
| **`/flow:doctor`** | Verification punch-list for a project's flow setup. Use after bootstrap or any time something feels off. |
| **`/flow:critique-plan`** | Plan-critic: scope drift / spec violation / internal incoherence against the user's request and reference docs. |
| **`/flow:audit-plan`** | Evidence-auditor: unverified assumptions + unverified recall in the most recent plan. |
| **`/flow:audit-completion`** | Evidence-auditor: false-verification proxies (build passed ≠ behavior verified) on completion claims. |
| **`/flow:log-disagreement`** | Auto-invoked when the user pushes back on a finding; captures the dispute for prompt-tuning input. |

### Supporting surface

- **8 agents:** `auditor`, `plan-critic`, `planner`, `docs`, plus 4 staff-review lens agents (`lens-staff-engineer`, `lens-ux-designer`, `lens-design-engineer`, `lens-push-further`).
- **4 auto-loading portable rules:** `general.md` (on `**/*` — workflow discipline), `plan-discipline.md` (on `**/plan.md` — required fields + LOW=gate), `documentation.md` (on `**/{history,feedback,plan,roadmap,spec}.md` — format rules), `exploration.md` (on `src/**`, `app/**`, `lib/**`, `packages/**` — § Exploration triggers).
- **Memory tool:** `plugins/flow/tools/memory/check.mjs` — failure-pattern corpus cap + audit-due check.
- **Schema:** `plugins/flow/schema/flow.config.schema.json` — 21 slots documented with defaults + examples.
- **Hooks:** `plugins/flow/hooks/default-hooks.json` — 2 opt-in PreToolUse hooks (sensitive-file write blocker + path-validation warn).
- **CI workflow:** `.github/workflows/ci.yml` — `evals` + `security` jobs on pull_request + merge_group.

### Consumer scaffolding (`template/` + `docs/`)

- **`template/base/`** — Tier 1 (CLAUDE.md.template, README.md.template, flow.config.json.example, .claude/{settings.json.example, rules/safety.md.template}, .gitignore.template) + Tier 2 (5 core-docs scaffolds with format headers) + `bootstrap.sh` (one-command scaffolder).
- **`template/stacks/{web,swift,tauri-rust-ts}/`** — per-stack overlays: preflight runner, CI workflow, `.gitignore.append`, UI/dev-server rules (web + tauri), link skill (web + tauri).
- **`docs/bootstrap.md`** — step-by-step adoption for a new project (3 stacks covered).
- **`docs/migration.md`** — 3-stage pattern for existing projects with prior `.claude/` content (install non-breaking → dogfood validate → delete duplicates).
- **`docs/first-pr.md`** — concrete walkthrough of your first PR using the loop.

## The loop

11 steps, 2 human gates:

> **Clarify → Plan (gate) → Execute → Preflight → Commit → `/simplify` → `/flow:staff-review` → Present → Iterate → `/flow:ship` → User merges (gate)**

Long-form with rationale for every step, gate semantics, spike/tiny mode escapes, and config-slot defaults: [`plugins/flow/docs/workflow.md`](plugins/flow/docs/workflow.md).

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
| New feature | `/flow:audit-plan` + `/flow:critique-plan` + `/flow:staff-review` + `/flow:audit-completion` | full loop: silent assumptions, scope drift, four-lens craft review, "shipped but never exercised" |
| Refactor | `/flow:audit-plan` + `/flow:critique-plan` + `/flow:staff-review` | surface-area assumptions, scope discipline, contract preservation |
| Doc-only PR | `/flow:critique-plan` + `/flow:audit-completion` + `/flow:ship` (security + a11y will early-exit cleanly) | discipline + minimum mechanical gates |
| Throwaway prototype | `/flow:ship-spike` only | reviewer overhead doesn't earn its keep on disposable code |

## Feedback loop

When a reviewer's output is wrong, **just say so in plain language** — "no, finding 2 is wrong because ...", "false positive on the scope drift", "the spec rule doesn't apply here". The plugin's `log-disagreement` skill auto-invokes when it detects pushback on a recent finding and captures the disagreement to:

```
~/.claude/plugins/data/flow/disagreements/
```

Each disagreement produces two paired files — a `.jsonl` slice of the session (the audit output plus your pushback) and a `.meta.json` with the dispute metadata. These become candidate eval fixtures in the next prompt-tuning pass.

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
  agents/                           # auditor.md, plan-critic.md, planner.md, docs.md,
                                    #   lens-{staff-engineer,ux-designer,design-engineer,push-further}.md
  skills/                           # ship/, ship-spike/, staff-review/, security-review/,
                                    #   accessibility-review/, workflow-help/, doctor/,
                                    #   audit-plan/, audit-completion/, critique-plan/,
                                    #   log-disagreement/
  rules/                            # general.md, plan-discipline.md, documentation.md,
                                    #   exploration.md (auto-load on path matches)
  scripts/                          # extract_session.py, bounding_logic.py, log_disagreement.py
  tools/memory/                     # check.mjs (corpus cap + audit-due)
  schema/                           # flow.config.schema.json (21 slots)
  hooks/                            # default-hooks.json (opt-in baseline)
  evals/                            # ground_truth.yaml, run_evals.py, run_security_evals.py,
                                    #   fixtures/, security/ (cwd-constraint + malicious-config tests)
  docs/workflow.md                  # canonical 11-step loop reference
  DISAGREE.md                       # free-form feedback log

template/                           # consumer scaffolding (copied via bootstrap.sh)
  base/                             # CLAUDE.md, README.md, flow.config.json.example,
                                    #   .claude/{settings.json,rules/safety.md} templates,
                                    #   core-docs/{spec,plan,roadmap,history,feedback}.md scaffolds,
                                    #   bootstrap.sh
  stacks/{web,swift,tauri-rust-ts}/ # per-stack preflight + CI + .gitignore + UI/link rules

docs/                               # consumer-facing guides
  bootstrap.md                      # new-project adoption walkthrough
  migration.md                      # existing-project 3-stage migration pattern
  first-pr.md                       # concrete walkthrough of your first PR through the loop

dev-docs/                           # plugin's own dev-tracking (not shipped to consumers)
  plan.md, history.md, feedback.md, spec.md, roadmap.md, workflow.md
  handoffs/                         # per-PR briefs + md-manager PR-4-6 spec

.github/workflows/ci.yml            # this repo's own CI (evals + security jobs)
.claude/                            # this repo's own project-dev infra (rules/agents/skills
                                    #   for building flow itself). Not shipped.
```

## Known limitations (tune-points, not blockers)

- Regex artifact detection misses files with no extension or unusual paths
- Tool-call history truncates at 50 calls
- Bounding logic occasionally grabs the wrong user turn (short follow-ups)
- Plan/completion mode detection is heuristic
- SwiftUI proxy handling is hardcoded; other frameworks need explicit additions
- Eval harness reads pre-recorded `.expected.txt` files for the auditor + plan-critic; regression-only, not live correctness validation
- Workflow enforcement is "soft" today (auto-loading rules + skill-trigger descriptions + `/flow:ship` Step 1.0 surface). Hard enforcement via Stop hook + Edit|Write scope check lands in v1.x post-extraction work
- `/flow:init` (auto-create scaffolding with detection + prompting) deferred; today's path is `bootstrap.sh` (deterministic cp-ladder) plus manual placeholder fill

## History

This repo was previously published as `byamron/llm-auditor` (marketplace) hosting the `assumption-auditor` plugin. It was renamed in place to `by-dev-tools/flow` on 2026-05-23, and converted from a flat root layout to the Anthropic marketplace + plugin pattern in v1.0.0. The pre-v1.0.0 content (flat root layout, `llm-auditor` marketplace name, `assumption-auditor` plugin name) is recoverable via:

```sh
git checkout pre-flow-plugin
```

GitHub maintains a redirect from `byamron/llm-auditor` → `by-dev-tools/flow`, so old clones still pull from the same place.

**Per-version changelog:** [`CHANGELOG.md`](CHANGELOG.md) — read this before upgrading.

**Upgrading?** [`docs/upgrade.md`](docs/upgrade.md) — the 2-command ritual + verification with `/flow:doctor` + troubleshooting.

## License

MIT — see [LICENSE](LICENSE).
