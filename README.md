# Assumption Auditor

Two passive, skeptical reviewers for Claude Code. The **auditor** flags claims in session output that lack supporting evidence. The **plan-critic** critiques proposed plans for misalignment with the user's request, reference documents, and the plan's own internal logic.

Neither subagent runs verification itself — they read the session and surface gaps in a fixed output format. Verification is the user's call.

## Slash commands

| Command            | Purpose                                                                                          | Runs when                                                              |
| ------------------ | ------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------- |
| `/audit-plan`      | Auditor pass over the most recent plan — looks for unverified assumptions and unverified recall  | After Claude produces a plan, before executing it                      |
| `/audit-completion`| Auditor pass over the most recent completion claim — looks for false-verification proxies        | After Claude declares work done / fixed / ready, before trusting it    |
| `/critique-plan`   | Plan-critic pass over the most recent plan — looks for scope / spec / coherence misalignment     | After Claude produces a plan, before user approval (complementary to `/audit-plan`) |

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

## Output

Plain text. Either a single `ISSUE` block, a multi-issue summary (`AUDIT SUMMARY` or `CRITIQUE SUMMARY`), or a clean signal (`No issues flagged.` / `APPROVED`). Exact format lives in `agents/auditor.md` and `agents/plan-critic.md`.

## Layout

```
.claude-plugin/   plugin.json, marketplace.json
agents/           auditor.md, plan-critic.md
skills/           audit-plan/, audit-completion/, critique-plan/
scripts/          extract_session.py, bounding_logic.py
evals/            ground_truth.yaml, run_evals.py, fixtures/
DISAGREE.md       append-only log of reviewer outputs the user disagreed with
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

When a reviewer's output is wrong, append to `DISAGREE.md`. Those entries feed the next prompt-tuning pass and become eval cases.
