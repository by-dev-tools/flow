# FB-0106 — Classify ships-or-paperwork before spending a human's attention

- **Date:** 2026-09-12
- **Source type:** user correction
- **What was said:** Presented with an escalation table on #146 asking whether to *declare* or
  *waive* a condition, Ben replied that he could not tell what was actually being asked of him and
  to surface the decision clearly. On inspection the two options produced a **byte-identical code
  diff** — the only difference was which document the rationale was written into.

- **Synthesized rule:** **Before escalating, ask whether the choice changes behaviour, a consumer
  surface, or a gate verdict — or only where something gets written.** If it is the latter, it is
  the orchestrator's call; escalating it spends the scarcest resource in the system on a decision
  with no outcome attached.

  The failure is subtle because the escalation was *well-formed*: it had options, a recommendation,
  a confidence level, and a rationale. Format compliance is not the bar. A decision can satisfy
  every rule of the communication contract and still be worthless to receive, because the contract
  governs *how* things are surfaced and says nothing about *whether* they should be. That is the
  gap this rule fills, and it is why the check runs before the formatting rules rather than as part
  of them.

  Note the asymmetry that makes the check cheap to apply and safe to get slightly wrong: guessing
  "paperwork" when it was really "ships" produces a wrong call the human can still catch at the
  merge gate, while guessing "ships" when it was paperwork produces a guaranteed waste with no
  upside. When genuinely unsure, the tie-break is to decide it, act, and *mention* the call in one
  line — which preserves the human's ability to reverse it without requiring their attention first.

- **Applies to:** canonical plan §4.8 (rule 7); `/flow:gate` and `/flow:orchestrate` (§4.10), which
  should apply the test to their own output rather than leaving it to a fresh seat to rediscover —
  this is the second time an orchestrator has had to learn it from the human directly.
