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

## What v1.11.0 ships

### Workflow surface (14 user-visible skills)

Listed in **loop order** — top to bottom is the sequence you move through. The **Fires** column is the part most newcomers miss: it says what runs on its own vs what you have to type.

- **AUTO** — fires by itself when its trigger condition is met; you never type it.
- **MANUAL** — never fires on its own; you'd type it. *As of v1.5.0 no flow skill is MANUAL-only* — every skill is at least model-invocable (the reviewers + `ship-spike` flipped to `disable-model-invocation: false`). The label is kept for reference; the only things that require a human are the two gates (plan approval, PR merge), not any skill.
- **BOTH** — you can type it, *and* it runs when `/flow:ship` calls it or a matching phrase + a diff-to-review triggers it. Won't cold-start on a bare "build me X".
- **AUTO·when-ready** — `/flow:ship` only (new in v1.4.0). Auto-advances from Step 8 *at the end of a driven loop* when the ship-readiness predicate holds (every spec-walk box checked, no open BLOCKER, no unresolved MEDIUM/LOW assumption, `/flow:verify-build` would return PASS) and the FB-0011 risk gate is clear; otherwise you type it / say "ship it". Never auto-advances when verify-build is skipped (library/none platform, doc-only diff), and never on a cold start.

> **⚠️ Cold-start reality — read this if you won't be typing commands.** Install flow, open a session, and just say "build me X" with no slash commands, and **only the auto-loading rules attach** — workflow-discipline *guidance* in Claude's context that nudges it to plan-before-coding and wait for your approval. That nudge is the entire automatic footprint. **No audit, plan critique, staff/security/a11y review, verify-build, or ship pipeline runs from a cold "build me X" until you (or a phrase trigger) invoke it**, and the plugin registers no hooks by default. `/flow:critique-plan` at the plan gate is model-invocable within a driven loop but never fires from a cold start. As of v1.4.0, `/flow:ship` *does* auto-advance — but only after the loop has been driven all the way to Step 8 with a green readiness predicate; it still won't start itself from a cold request. And the readiness predicate itself is *guidance* (a rule + the skill description), not a hard hook — the mechanical backstop is `/flow:verify-build` inside the ship pipeline, which routes a FAIL/Unknown regression to a draft PR + a pinned `🚫 NOT READY TO MERGE` manifest (never a merge-ready PR on a non-PASS build). The human gates that never move are **plan approval** (Step 2) and **merge** (Step 11) — and as of v1.5.0 `/flow:critique-plan`, `/flow:audit-plan`, `/flow:audit-completion`, and `/flow:ship-spike` are model-invocable too (Claude fires them at the plan/present/spike-end points *within a driven loop*), so no review or ship-spike skill requires a human keystroke — but none of them cold-start either. Enforcement is otherwise *soft* (see [Known limitations](#known-limitations-tune-points-not-blockers)).

| Step | Skill | Fires | What it does |
|---|---|---|---|
| pre-loop | **`/flow:workflow-help`** | BOTH | Prints the 11-step loop + your resolved `flow.config.json` slots + skill catalog. Auto-fires on "what's the workflow?". Onboarding front door. |
| pre-loop | **`/flow:doctor`** | BOTH | Setup PASS/FAIL/WARN punch-list ending in a `[READY]` verdict. Auto-fires on "is flow set up right?" / "skills not showing up". Run after bootstrap. |
| 2 · plan gate | **`/flow:critique-plan`** | BOTH | Plan-critic: scope drift / spec violation / internal incoherence vs your request + reference docs. Model-invocable at the plan gate within a driven loop (**never cold-start**); also typeable. |
| 2 · plan gate | **`/flow:audit-plan`** | BOTH | Evidence-auditor: unverified assumptions + unverified recall in the most recent plan. Complements critique-plan; both fire at the plan gate within a driven loop (never cold-start) or run manually. |
| 7 · review | **`/flow:staff-review`** | BOTH | Four parallel lenses (engineer / UX-designer / design-engineer / push-further), each a plugin-shipped agent. Triages BLOCKER / NIT / FOLLOW-UP / EXPLORATION; fixes inline. |
| ~8 · present | **`/flow:audit-completion`** | BOTH | Evidence-auditor: false-verification proxies (build passed ≠ behavior verified) on a "done / fixed / ready" claim. Model-invocable at the present gate within a driven loop (never cold-start); also typeable. |
| 10 · ship | **`/flow:ship`** | AUTO·when-ready | The pipeline: final-pass reviews → BLOCKER/NIT fixes → synthesize feedback (user + agent-memory layers) → update docs → commit → push → open PR with a per-step `## Flow run` body documenting the whole loop (v1.4.1). **Never merges.** Auto-advances from Step 8 when the readiness predicate holds (v1.4.0); else — or if the risk gate trips or verify-build was skipped — you type it / say "ship it" (see legend). |
| 10 · nested | **`/flow:security-review`** | BOTH | Diff-focused security audit (XSS, secrets, unsafe URL handling, path traversal, dependency risk, persistence leakage). Runs inside `/flow:ship`; early-exits on doc-only diffs. |
| 10 · nested | **`/flow:accessibility-review`** | BOTH | Diff-focused WCAG 2.1 AA audit. Runs inside `/flow:ship`; early-exits on `uiSurface=false` or non-UI diffs. |
| 10 · nested | **`/flow:verify-build`** | BOTH | Plan-driven behavioral gate: extracts spec-walk criteria, adversarially tests the built artifact via bundled `/verify`. Discovery runs at the Step 8/9 readiness boundary; inside `/flow:ship` it's a *confirmation* re-run — a FAIL/Unknown regression routes to a **draft PR + a pinned `🚫 NOT READY TO MERGE` manifest**, never a merge-ready PR. Needs `verifyEnabled` + `platform` set. |
| 10 · nested | **`/flow:audit-coverage`** | BOTH | Coverage auditor: flags behavior changes in the diff that **no declared `**Spec-walk:**` criterion covers** (under-declaration — a behavior verify-build never tested). A gap routes to the **draft manifest** (decision-required). Complements verify-build: verify-build checks the declared criteria *pass*; audit-coverage checks the declared set is *complete*. Best-effort LLM judgment (raises the bar, not a deterministic guarantee); runs on all platforms; self-skips on doc/test/refactor-only diffs. |
| 10 · spike | **`/flow:ship-spike`** | BOTH | Lightweight ship for `mode: spike` PRs. Same pre-flight gates; skips heavy reviews; writes the `history.md` entry (the deliverable); opens a `spike`-labeled PR. Model-invocable at the end of a spike loop or typed — but its auto-advance is **judgment-gated** (a spike has no mechanical readiness predicate, unlike `/flow:ship`'s verify-build PASS); never cold-start. Never merges. |
| 11 · post-merge | **`/flow:land`** | HUMAN | After **you** merge a PR: reconciles the forward docs to "merged (#N)" (the slot `/flow:ship` couldn't, since it runs before the merge), moves the item to Recently shipped, re-runs the visual-history distill if a visual pass was blocked at ship and has since completed, clears any feedback-ID reservations the PR claimed (a no-op if your project doesn't reserve numbers), then opens a small `docs: land #N` PR. `disable-model-invocation: true` — human-only, never auto-fires (Claude can't merge). **Never merges.** |
| cross-cutting | **`/flow:log-disagreement`** | AUTO | The one self-firing skill: when you dispute a finding from an audit/critique in plain language, it captures the pushback for prompt-tuning. Needs a prior finding in the conversation to dispute. |

### Supporting surface

- **8 agents:** `auditor`, `plan-critic`, `planner`, `docs`, plus 4 staff-review lens agents (`lens-staff-engineer`, `lens-ux-designer`, `lens-design-engineer`, `lens-push-further`).
- **4 auto-loading portable rules:** `general.md` (on `**/*` — workflow discipline), `plan-discipline.md` (on `**/plan.md` — required fields + LOW=gate), `documentation.md` (on `**/{history,feedback,plan,roadmap,spec}.md` — format rules), `exploration.md` (on `src/**`, `app/**`, `lib/**`, `packages/**` — § Exploration triggers).
- **Memory tool:** `plugins/flow/tools/memory/check.mjs` — failure-pattern corpus cap + audit-due check.
- **Schema:** `plugins/flow/schema/flow.config.schema.json` — 24 slots documented with defaults + examples.
- **Hooks:** `plugins/flow/hooks/default-hooks.json` — 2 opt-in PreToolUse hooks (sensitive-file write blocker + path-validation warn).
- **CI workflow:** `.github/workflows/ci.yml` — `evals` + `security` jobs on pull_request + merge_group.

### Consumer scaffolding (`template/` + `docs/`)

- **`template/base/`** — Tier 1 (CLAUDE.md.template, README.md.template, flow.config.json.example, .claude/{settings.json.example, rules/safety.md.template}, .gitignore.template) + Tier 2 (5 core-docs scaffolds with format headers) + `bootstrap.sh` (one-command scaffolder).
- **`template/stacks/{web,swift,tauri-rust-ts}/`** — per-stack overlays: preflight runner, CI workflow, `.gitignore.append`, UI/dev-server rules (web + tauri), link skill (web + tauri).
- **`docs/bootstrap.md`** — step-by-step adoption for a new project (3 stacks covered).
- **`docs/migration.md`** — 3-stage pattern for existing projects with prior `.claude/` content (install non-breaking → dogfood validate → delete duplicates).
- **`docs/first-pr.md`** — concrete walkthrough of your first PR using the loop.

## The loop

11 steps. It **pauses for you in three places** (two load-bearing human gates + one conditional gate); everything in between flows on its own once you approve.

| # | Step | Who drives | Pause for you? |
|---|---|---|---|
| 1 | **Clarify** — read source-of-truth docs; ask 2–4 questions (or list assumptions) | Claude | — |
| 2 | **Plan** — spec-walk checkboxes + confidence verdict; `/flow:critique-plan` + `/flow:audit-plan` run here | Claude + you (reviewers model-invocable within the loop, never cold-start; also typeable) | **GATE 1 — you approve the plan.** **GATE 3** halts even earlier on any LOW-confidence assumption until you answer it. |
| 3 | **Execute** — implement against the checkboxes | Claude | — |
| 4 | **Preflight** — typecheck / build / test must be green | Claude | pauses if red (mechanical, not a human gate) |
| 5 | **Commit** — explain "why", per phase | Claude | — |
| 6 | **`/simplify`** — cold-read for reuse / clarity / efficiency (bundled with Claude Code, not a flow skill) | Claude | — |
| 7 | **`/flow:staff-review`** — four-lens review; fix blockers + cheap nits inline | Claude | — |
| 8 | **Present (conditional gate)** — reviewer notes + branch state, **no PR yet**; MEDIUM-confidence assumptions surfaced | Claude | **auto-advances into `/flow:ship`** when the readiness predicate holds + risk gate clear; **else stops** — you redirect, resolve, or say "ship it" |
| 9 | **Iterate** — apply your feedback (sub-loop of 1–7) | Claude | starts only when you give feedback |
| 10 | **`/flow:ship`** — runs `/flow:security-review` + `/flow:accessibility-review` + `/flow:verify-build`, synthesizes feedback, updates docs, commits, pushes, opens the PR | auto-invoked from Step 8 when ready, or you type it | unresolved blocker (decision-required finding or non-converging verify-build regression) → **draft PR + a pinned `🚫 NOT READY TO MERGE` manifest**; never a silent proceed, never a merge-ready PR on a non-PASS build |
| 11 | **STOP** — Claude never runs `gh pr merge` | you | **GATE 2 — you merge.** |

Once you approve the plan, Steps 3–8 run as one continuous Claude-driven stretch — the only stop inside it is a red Preflight. At Step 8, if the ship-readiness predicate holds and the risk gate is clear, it **auto-advances into `/flow:ship`** (v1.4.0); otherwise it stops and presents for you to redirect or say "ship it". `/flow:ship` runs its whole pipeline autonomously, then stops at the open PR. So in the autonomous path the human touchpoints shrink to exactly the two load-bearing gates: **approve the plan → merge the PR.**

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
  schema/                           # flow.config.schema.json (24 slots)
  hooks/                            # default-hooks.json (opt-in baseline)
  evals/                            # ground_truth.yaml, run_evals.py, run_security_evals.py,
                                    #   run_render_evals.py, run_visual_history_evals.py,
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
- The PR `## Test plan` is rendered from the verify-build findings buffer, so a checked box attests **behavioral/text** verification by an adversarial judge — *not* visual correctness (bundled `/verify` narrates screenshots to the fresh-context judge rather than handing it pixels; rendered-visual judging lands in the Deliverable-quality track's V2). The rendered attestation also only covers criteria the plan **declared** in its `**Spec-walk:**` block. `/flow:audit-coverage` (v1.6.0) closes the worst of that under-declaration hole — it flags behavior changes in the diff that no declared criterion covers and routes each to the draft manifest — but it is **best-effort LLM judgment**: it raises the completeness bar, it does not deterministically guarantee it (a sufficiently subtle undeclared behavior can still slip past, a false negative). It is not a substitute for the human read at the merge gate

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
