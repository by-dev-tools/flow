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

## Harness-weight audit (roadmap item AB, Step 1, FB-0095)

Parallel to the memory-corpus audit (`plugins/flow/tools/memory/check.mjs --audit-due`, run from `/flow:ship` §4b.vi), but over flow's own **static always-loaded and invoked-per-use surfaces** rather than memory entries. Dev-tooling only — see CLAUDE.md § 3.

**Cadence:** run `python3 tools/harness_audit/harness_audit.py --audit-due` periodically (e.g. at the start of a session picking up dev-docs work). Exit 1 means due (every 5 merged PRs to `main`, by commit count since the last audit's marker SHA). Exit 0 means not due yet — skip. **Not a side-effect-free peek:** every call advances the on-disk marker whenever it reports due — run it only when you're actually about to act on a "due" result (spawn the audit agent below), not to preview the count.

**When due, spawn a fresh-context Explore agent** (read-only: Read, Grep, Glob — no Edit/Write, matching "passive over active"). Give it ONLY this prompt and the output of `python3 tools/harness_audit/harness_audit.py --surfaces` — no PR diff, no other session context:

> You are auditing flow's own harness weight. Below is an inventory of two surface classes: **Class A (always-loaded)** — paid every session regardless of what the user asks — and **Class B (invoked-per-use)** — paid only when that specific skill runs. These are different cost models; do not compare or rank across them.
>
> For each surface, read its actual content (the inventory gives you paths) and answer, per surface:
> 1. **Expired-assumption scaffolding** — does any passage exist to compensate for a model limitation that a current-generation model no longer has? Name the passage and the assumption.
> 2. **Append-only growth** — is any passage pure accretion (the FB-0078 class: every update prepends instead of replacing) that could compact to a high-signal head with detail pushed to `history.md`?
> 3. **Cross-surface redundancy** — does this surface repeat content that another audited surface already states?
>
> **Hard constraints, non-negotiable:**
> - Never flag a comment or passage that documents a past incident, a footgun, or a "why this exists" rationale (the FB-0010 pattern) — those are load-bearing memory, not weight.
> - Never flag a curated canonical example as prunable for being long — a good example earns more than its token cost. Only flag *exhaustive* lists where one or two curated examples would teach the same lesson.
> - Never flag anything marked `SAFETY` or living under `.claude/rules/safety.md`.
> - "Minimal" is the bar, not "short." Do not recommend deleting information the next reader would need — recommend restructuring or relocating it instead.
>
> Output candidate findings only (surface, passage, category, one-line reason). If nothing is actionable, say so plainly — "no issues flagged" is a valid, complete answer.

**The audit never prunes.** Its output is a candidate list for a human (or a follow-up PR, e.g. AB.2's dev-doc compaction) to weigh — there is no ground truth for "still earns its cost," unlike the memory audit's partially-mechanizable fire-log staleness check.
