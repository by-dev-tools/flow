### FB-0018: `/flow:ship` should auto-invoke when ready — the autonomous loop's human gates are plan + merge, not "ship it"; but auto-ship requires a behavioral PASS, not just absence-of-failure
**Date:** 2026-05-30
**Source:** user direction (stated while reviewing why /flow:ship was manual-only)

**What was said:** "don't we want ship to be auto invocable? that's necessary to get to an autonomous coding loop ... the human gates are supposed to be plan and merge right?" On the follow-up scoping question — for projects where `/flow:verify-build` is skipped (library/none platform, doc-only diff) and there is no behavioral gate — the user chose **keep auto-ship MANUAL** there (default-to-ESCALATE), reserving auto-advance for cases with a real behavioral PASS.

**Synthesized rule:** The Flow loop's two load-bearing human gates are **plan approval (Step 2)** and **merge (Step 11)** — nothing else should require a human keystroke by default. `/flow:ship` is therefore auto-invocable: the agent auto-advances from Step 8 when the ship-readiness predicate holds (spec-walk complete, no open BLOCKER, no unresolved MEDIUM/LOW assumption, `/flow:verify-build` returns **PASS** — not merely "didn't fail") and the FB-0011 risk gate is clear. Two hard constraints when extending any auto-ship behavior:

```
(a) The readiness signal must be a positive behavioral PASS, not absence-of-
    failure. If verify-build is skipped (no runnable target), there is no gate
    → stay MANUAL. Never treat "nothing failed" as "ready."
(b) verify-build (mechanical, Step 2) — not the model's self-assessment of the
    predicate — is the load-bearing boundary. The predicate decides whether to
    ENTER ship; ship's own gate re-confirms and halts pre-PR on FAIL/Unknown.
```

This is FB-0011 (autonomy bar) applied to the ship-invocation decision: act autonomously only on a clear, low-risk, mechanically-confirmed signal; otherwise stop and present.

**Applies to:** `/flow:ship` invocation, workflow.md Step 8, autonomous-gate design, future widening of auto-ship scope (e.g. when adding behavioral gates for currently-skipped platforms)
