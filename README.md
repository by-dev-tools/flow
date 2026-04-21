# Assumption Auditor

A Claude Code plugin that audits plans and completion claims for unverified
assumptions, diagnoses, and completion claims. It does not run verification
itself — it reads the session, finds claims that lack supporting evidence, and
surfaces them in a fixed output format.

## What it catches

| Category                  | Fires on                                                                 |
| ------------------------- | ------------------------------------------------------------------------ |
| Unverified diagnosis      | Confident root-cause claim acted on, no investigation supporting it      |
| Unverified completion     | "Done / fixed / ready" claim backed only by build / typecheck / startup |
| Unverified assumption     | Plan premise not in the request, not in session context, load-bearing   |
| Unverified recall         | "We tried X" / "ruled this out" with no fresh read of the named artifact |

## Install

From inside Claude Code:

```
/plugin install <path-or-marketplace-url>
```

The plugin registers two slash commands: `/audit-plan` and `/audit-completion`.

## Use

After Claude produces a plan, before executing it:

```
/audit-plan
```

After Claude declares work done, fixed, ready, or implemented, before trusting
the claim:

```
/audit-completion
```

Both commands run preprocessing (`scripts/extract_session.py`) to assemble a
labeled context bundle, then dispatch to the `auditor` subagent in an isolated
context. The auditor reads only what the script provided — it does not invoke
verification tools itself in v1.

## Output

Plain text. Either a single `ISSUE` block, an `AUDIT SUMMARY` with multiple
issues, or `No issues flagged.` See `agents/auditor.md` for the exact format.

## Layout

```
.claude-plugin/   plugin.json, marketplace.json
agents/           shared auditor subagent (system prompt + frontmatter)
skills/           audit-plan/SKILL.md, audit-completion/SKILL.md
scripts/          extract_session.py (preprocessing), bounding_logic.py
evals/            ground_truth.yaml, run_evals.py, fixtures/
DISAGREE.md       append-only log of auditor outputs the user disagreed with
```

## v1 limitations

These are tune-points, not blockers — see the build handoff for the full list:

- Regex artifact detection misses files with no extension or unusual paths
- Tool-call history truncates at 50 calls
- Bounding logic occasionally grabs the wrong user turn (short follow-ups)
- Plan/completion mode detection is heuristic
- SwiftUI proxy handling is hardcoded; other frameworks need explicit additions

## Feedback loop

When the auditor's output is wrong, append to `DISAGREE.md`. Those entries feed
the next prompt-tuning pass and become eval cases.
