### FB-0035: verify-build discovery belongs at the readiness boundary; ship-time verify-build is a confirmation re-run (refines FB-0018(b))
**Date:** 2026-06-01
**Source:** user direction (managed-autonomy confidence conversation)

**What was said:** "do we want verify-build before ship? if any iterating needs to be done based on visual review, that should probably be treated as something to dial in before we decide it's ready to ship." The "ship it" decision should mean "I've seen it work," not "go find out if it works."

**Synthesized rule:** Behavioral + visual *discovery* runs at the Step 8/9 readiness boundary, before the ship decision (the auto-advance predicate already requires a verify-build PASS there). At `/flow:ship` Step 2, verify-build is a **confirmation re-run** — a non-converging FAIL/Unknown means a *regression since readiness* → FB-0012 bounded mechanical fix, else route to the draft manifest (FB-0034). This **refines FB-0018(b)**: ship's gate no longer "halts pre-PR on FAIL/Unknown" — it routes to a draft pre-PR, preserving (and strengthening) the invariant *no merge-ready PR on a non-PASS build*. **Visual sign-off folds into the merge gate** (agent dials in pre-PR against plan-declared visual criteria; the authoritative human look is the PR preview) — never a third human gate. General rule: anything that can produce *iteration* runs before the ship decision; anything inside ship is a pass/fail *confirmation*, never a loop.

**Applies to:** `/flow:verify-build`, `/flow:ship` Step 2, `workflow.md` Step 8/10, FB-0018 reconciliation, UI-project visual workflow
