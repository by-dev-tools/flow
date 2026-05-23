# Assumption Auditor

Two passive, skeptical reviewers for Claude Code. The **auditor** flags claims in session output that lack supporting evidence. The **plan-critic** critiques proposed plans for misalignment with the user's request, reference documents, and the plan's own internal logic.

Neither subagent runs verification itself — they read the session and surface gaps in a fixed output format. Verification is the user's call.

## Slash commands

| Command            | Purpose                                                                                          | Runs when                                                              |
| ------------------ | ------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------- |
| `/audit-plan`      | Auditor pass over the most recent plan — looks for unverified assumptions and unverified recall  | After Claude produces a plan, before executing it                      |
| `/audit-completion`| Auditor pass over the most recent completion claim — looks for false-verification proxies        | After Claude declares work done / fixed / ready, before trusting it    |
| `/critique-plan`   | Plan-critic pass over the most recent plan — looks for scope / spec / coherence misalignment     | After Claude produces a plan, before user approval (complementary to `/audit-plan`) |
| `log-disagreement` | (Auto-invoked, no slash command) — captures user pushback on a recent finding to user-scope storage | After a reviewer issues a finding the user disputes in plain language |

## What each reviewer catches

### Auditor (`agents/auditor.md`)

| Category                  | Fires on                                                                 |
| ------------------------- | ------------------------------------------------------------------------ |
| Unverified diagnosis      | Confident root-cause claim acted on, no investigation supporting it      |
| Unverified completion     | "Done / fixed / ready" claim backed only by build / typecheck / startup |
| Unverified assumption     | Plan premise not in the request, not in session context, load-bearing   |
| Unverified recall         | "We tried X" / "ruled this out" with no fresh read of the named artifact |

### Plan-critic (`agents/plan-critic.md`)

| Category              | Fires on                                                                                              |
| --------------------- | ----------------------------------------------------------------------------------------------------- |
| Scope drift           | Plan element outside the user's request, or absent element the user explicitly requested              |
| Spec violation        | Plan step that contradicts a rule in `core-docs/*.md` or established earlier in the session            |
| Internal incoherence  | Plan steps that contradict each other, or success criteria that don't map onto the goal                |

Plan-critic findings carry an explicit severity — **BLOCKER**, **REDIRECT**, or **FOLLOW-UP** — so calling agents (or you) can decide whether the plan needs revision before approval. A clean critique returns `APPROVED`.

## Install

From inside Claude Code:

```
/plugin marketplace add byamron/llm-auditor
/plugin install assumption-auditor
```

Or for local development:

```
/plugin install /path/to/llm-auditor
```

## Use

```
/audit-plan          # after a plan, looking for evidence gaps
/critique-plan       # after a plan, looking for reasoning gaps
/audit-completion    # after a completion claim, looking for verification proxies
```

`/audit-plan` and `/critique-plan` are complementary — they don't duplicate categories. Run both at a plan-approval gate for full coverage; run either alone for a lighter-weight check.

Both plan reviewers preprocess via `scripts/extract_session.py`. The plan-critic additionally loads `core-docs/*.md` (excluding `history.md`, `plan.md`, `roadmap.md`) into its context so it can quote project rules when flagging spec violations. Override the doc location via `--reference-paths` or `--reference-glob` if your project uses a different layout.

## When to use each reviewer

The right combination depends on the kind of work, not just the moment in the loop.

| Work type | Suggested reviewers | Why |
|---|---|---|
| Bug fix | `/audit-plan` + `/audit-completion` | catches premature diagnosis and "fixed but unverified" — the two most common bug-fix failure modes |
| New feature | `/audit-plan` + `/critique-plan` + `/audit-completion` | catches silent assumptions, scope drift / spec violation, and "shipped but never exercised" |
| Refactor | all three | surface-area assumptions (which callers exist?), scope discipline (no UI changes bundled in), and "build passes ≠ behavior preserved" |
| Throwaway prototype | none required | the reviewers' value is in trust contexts; one-off prototypes don't have one |

**Features benefit from this plugin more than bug fixes**, not less. Bug fixes have an obvious verification target (does the bug still reproduce?), so the user can manually spot a missing check. Features don't — there's no "before" state to compare against, so the auditor's "you claimed X but didn't check" prompt catches gaps the user would otherwise miss. The one bug-flavored category (`Unverified diagnosis`) rarely fires on features and stays quiet per the auditor's "Permission to find nothing" rule; the other three categories all matter.

## Output

Plain text. Either a single `ISSUE` block, a multi-issue summary (`AUDIT SUMMARY` or `CRITIQUE SUMMARY`), or a clean signal (`No issues flagged.` / `APPROVED`). Exact format lives in `agents/auditor.md` and `agents/plan-critic.md`.

## Layout

```
.claude-plugin/   plugin.json, marketplace.json
agents/           auditor.md, plan-critic.md
skills/           audit-plan/, audit-completion/, critique-plan/, log-disagreement/
scripts/          extract_session.py, bounding_logic.py, log_disagreement.py
evals/            ground_truth.yaml, run_evals.py, fixtures/
DISAGREE.md       legacy free-form log for feedback that isn't tied to a single finding
```

## Known limitations

These are tune-points, not blockers:

- Regex artifact detection misses files with no extension or unusual paths
- Tool-call history truncates at 50 calls
- Bounding logic occasionally grabs the wrong user turn (short follow-ups)
- Plan/completion mode detection is heuristic
- SwiftUI proxy handling is hardcoded; other frameworks need explicit additions
- Eval harness reads pre-recorded `.expected.txt` files rather than invoking reviewers live; regression-only, not correctness

## Feedback loop

When a reviewer's output is wrong, **just say so in plain language** — "no, finding 2 is wrong because ...", "false positive on the scope drift", "the spec rule doesn't apply here". The plugin's `log-disagreement` skill auto-invokes when it detects pushback on a recent finding and captures the disagreement to:

```
~/.claude/plugins/data/assumption-auditor/disagreements/
```

Each disagreement produces two paired files — a `.jsonl` slice of the session (the audit output plus your pushback) and a `.meta.json` with the dispute metadata. These become candidate eval fixtures in the next prompt-tuning pass.

For wider feedback that isn't tied to a specific finding (overall behavior, missing features, requested categories), append to `DISAGREE.md` manually.

### What auto-invocation looks like

After the critic returns its findings, every output ends with:

```
---
If a finding is wrong, just say so. Your pushback will be logged for prompt tuning.
```

You don't have to do anything special. Push back in plain language; the skill catches it. You'll see a one-line confirmation when a disagreement is logged.
