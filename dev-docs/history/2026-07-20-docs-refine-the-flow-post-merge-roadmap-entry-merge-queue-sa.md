### docs: refine the `/flow:post-merge` roadmap entry — merge-queue-safe gate + compose-with-land
**Date:** 2026-07-20
**Branch:** claude/post-merge-design-refinements (commit: pending ship)

**What was done:**
Two design refinements to the `/flow:post-merge` roadmap entry (captured in #78), from the design conversation that followed:
1. **Merge-detect is now three-state, not two.** The original "MERGED → proceed, else fail loud" gate would false-fail on every merge-queue / auto-merge repo (a ~1–2 min delay between clicking merge and the PR actually merging). Rewrote function (1) to distinguish terminal ("will never merge" — CLOSED-unmerged → fail loud) from transient ("not merged yet" — OPEN → bounded poll, then a graceful "still queued, re-run" exit, never a hard fail), with `autoMergeRequest` as a confidence signal and a new optional `postMergeWaitSeconds` slot (default ≈150, `0` = fail-fast).
2. **Compose with `/flow:land`, don't combine.** Added an explicit paragraph: `/flow:post-merge` should *call* `/flow:land` (orchestrator pattern, like `/flow:ship` calls its reviewers), not absorb it — with the four reasons (different write surfaces, different responsibilities, divergent automation futures, land's standalone value) and the idempotency note that makes server-auto-land + local-post-merge-calls-land converge safely.

**Why:**
The user raised the merge-queue timing concern directly ("I don't want a fail every single time if nothing actually went wrong"), and had agreed to the compose-not-combine conclusion — both are load-bearing design decisions the eventual part-B plan must inherit. Leaving them only in the conversation would be the exact leak `/flow:post-merge` exists to fix (a decision that never reaches a durable doc), so they go in the entry now.

**Design decisions:**
- **Framed the gate fix as the general "transient vs terminal" principle**, cross-referencing FB-0012 and the flaky-test roadmap item, so it reads as an instance of an established flow lesson rather than a one-off merge-queue patch.
- **Kept it in the roadmap entry, not a new plan/skill.** Part B (the actual skill plan + build) is still deferred; this only sharpens the capture.

**Tradeoffs discussed:**
- Compose vs combine: full combination saves one skill file but loses land's independent invocability (GitHub-web-merge case) and its headless-auto-fire future (FB-0063). Composition keeps both — documented in the entry so it isn't relitigated at build time.
