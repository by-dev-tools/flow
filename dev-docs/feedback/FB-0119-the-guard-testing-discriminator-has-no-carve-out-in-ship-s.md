# FB-0119 — The guard-testing discriminator (FB-0115) has no carve-out in `/flow:ship`'s shipped "never auto-add the criterion" rule

- **Date:** 2026-09-26
- **Source type:** hand-harvest of the lesson-harvest queue (see [[FB-0111]], [[FB-0118]] — same
  drain-was-disabled circumstance).

- **What was said:** [[FB-0115]] established a narrow, load-bearing exception to the "never
  self-declare a criterion" doctrine: **does the undeclared behaviour guard something whose absence is
  invisible?** If yes — a sanitization step, an injection guard, anything whose deletion would leave
  every *declared* criterion still green — the agent should write the test **now**, while the criterion
  itself still waits for human approval as usual, because the approval-waiting period is exactly the
  window in which the guard is untested. This discriminator was applied once, live, in v1.49.0, to a
  prompt-context guard on a surface with a shipped RCE in its history — so it is not theoretical.

  But the rule it carves an exception *into* — `/flow:ship` Step 2's `/flow:audit-coverage` routing
  (`plugins/flow/skills/ship/SKILL.md:351`, "Do NOT auto-add the criterion yourself — that is the agent
  grading its own homework") — ships with **no exception clause**. A consumer (or a future flow
  maintainer) reading that line has no signal that a guard-testing carve-out exists at all; the
  discriminator currently lives only in a feedback-doc entry, which is not read at ship time.

- **Synthesized rule:** when a general doctrine ships a narrow, deliberately-scoped exception, the
  exception belongs in the same prose as the doctrine it modifies — not only in the feedback record that
  motivated it. A rule with an un-shipped exception is a trap for the next agent who follows it literally
  and either (a) waits on a criterion whose guard should have been tested immediately, or (b) invents a
  looser version of the exception from memory, without the "absence is invisible" boundary that keeps it
  narrow.

- **Candidate promotion (not implemented here):** add one clause to `plugins/flow/skills/ship/SKILL.md`
  Step 2's `/flow:audit-coverage` routing, immediately after the "never self-declare a criterion" line —
  the FB-0115 discriminator verbatim: *"Exception: if the undeclared behaviour guards something whose
  absence is invisible to every already-declared criterion (a sanitization step, an injection guard),
  write the test now — the criterion still routes for human approval as usual; only the guard's own test
  is written ahead of it."* Same location gets the same clause in `plugins/flow/skills/ship-spike/
  SKILL.md` if its Step 4c/coverage routing carries the parent rule.

- **Applies to:** `plugins/flow/skills/ship/SKILL.md` (Step 2, `/flow:audit-coverage` routing),
  `plugins/flow/skills/ship-spike/SKILL.md` (parity), `plugins/flow/agents/auditor.md` if it states the
  same doctrine independently. Related: [[FB-0115]] (origin), [[FB-0118]] (sibling promotion candidate
  from the same drain).
