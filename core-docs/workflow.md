# Workflow

How to work with Claude and agents on this project.

---

## Session Start Checklist

Before starting any work (~1 minute):

1. **Read `plan.md`** -- check "Current focus" and "Handoff Notes."
2. **Spot-check relevant docs** -- if relying on a design or architecture claim, verify it against the actual code or session transcript.
3. **Pick your agent** -- see agent table in CLAUDE.md or use `claude --agent <name>`.

## Agent Workflow

For each piece of work, pick one primary agent. Full specs live in `.claude/agents/`.

### Standard feature workflow

```
1. Planner Agent   --> scope work, write success signals, update plan.md
2. Domain Agent    --> Python scripts, prompt changes, eval logic
3. Testing Agent   --> new eval fixtures and regression cases
4. Docs Agent      --> history.md, plan.md, commit
```

Use `/clear` between agent phases to keep context small.

### Quick recipes

**Prompt tuning (`agents/auditor.md`):**
1. Testing Agent: add a failing fixture in `evals/fixtures/` demonstrating the gap
2. Domain Agent: tune the prompt until the fixture passes and existing fixtures still pass
3. Docs Agent: log the change in history.md with before/after behavior

**Bugfix in `scripts/`:**
1. Testing Agent: write or identify a regression test reproducing the bug
2. Domain Agent: fix until the test passes
3. Docs Agent: update plan.md and commit (`SAFETY` marker if error handling changed)

**Feedback iteration (user appended to DISAGREE.md or corrected an audit):**
1. Planner Agent: decide whether to address via prompt tuning, new eval fixture, or scope change
2. Domain/Testing Agent: apply the corrected approach
3. Docs Agent: document feedback in feedback.md, update history.md
