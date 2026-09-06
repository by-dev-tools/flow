### FB-0036: All flow reviewer skills + ship-spike are model-invocable; the only two human gates are plan approval and PR merge — no skill is itself a gate
**Date:** 2026-06-01
**Source:** user direction (managed-autonomy confidence conversation)

**What was said:** "all skills should be auto invocable — the only human gates are final plan review and PR merge (so the skills/stages shouldn't handle these specifically, but they should be able to get up to that point autonomously)."

**Synthesized rule:** Flip `disable-model-invocation: false` on `audit-plan`, `audit-completion`, `critique-plan`, and `ship-spike` (`/flow:ship` already done in PR S / FB-0018). Reviewers are review *passes*; `ship-spike` opens a PR but never merges — none is a gate, so forcing a human to hand-type them was an artificial stop. Three durable sub-rules:

```
(a) Docs must stay in LOCKSTEP with the flag (FB-0010 fan-out): after any
    flip, zero "MANUAL"/"user-invocable"/"hand-typed" survivors for these
    four in README/workflow.md. The flag and the label are one contract.
(b) Model-invocable ≠ cold-start. The three reviewers fire WITHIN a driven
    loop (at the plan/present gates), not on a cold "build me X". Preserve
    that cold-start-honesty in the docs — label them BOTH (auto + typeable),
    not a bare AUTO that implies they self-start.
(c) ship-spike auto-advance is JUDGMENT-gated, not predicate-gated. Unlike
    /flow:ship (which auto-advances on a mechanical verify-build PASS), a
    spike's "done?" is a judgment. That's acceptable (spike code is
    disposable, never merges, human-reviewed) — do NOT invent a fake
    mechanical predicate to make it look symmetric with ship.
```

**Load-bearing dependency:** the three `context: fork` reviewers only work if `extract_session.py` can find the session transcript from a worktree (dotted-path) cwd — broken until #33 (v1.4.2) fixed slugify + added a `CLAUDE_CODE_SESSION_ID` primary. Without #33 in the base they auto-invoke but audit nothing. (Fork-path parity verified PASS once #33 is present.)

**Applies to:** the four skills' frontmatter, README + workflow.md invocation labels, FB-0010 fan-out discipline, the two-gate model, FB-0018 reconciliation
