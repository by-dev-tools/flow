### Docs-currency sweep — refresh the v1.6.0 handoff for a cold agent
**Date:** 2026-06-11
**Branch:** claude/docs-currency-v160-handoff (docs-only; SHA at commit time)

**What was done:** After PR TP (#46) + PR-2 (#47) merged, the plan's "Handoff Notes" + a few roadmap/plan cold-reader lines were stale: Handoff still read "v1.5.2" and listed the now-shipped PR-TP/PR-2 as "queued/staged", and several `this PR` references dangled post-merge. Refreshed Handoff to v1.6.0 + "Recently shipped (enforce-pair DONE)", and de-`this PR`'d the § Now / ▶ Next-up / Current Focus lines so a fresh agent lands on **▶ V2** cleanly (with the vacuous-criterion residual in roadmap § Next).

**Why / lesson:** This is the cleanup `/flow:ship` Step 5a (doc-currency reconciliation, shipped v1.5.2) does automatically — but the **dogfood install is flow 1.5.1**, which predates it, so the auto-sweep never ran across PR-TP + PR-2 and the staleness accumulated. Until the dogfood install updates to ≥ v1.5.2, forward-doc currency must be reconciled by hand at ship (or in a follow-up sweep like this). No code; reviewers + verify-build self-skipped (docs-only / platform library); no version bump.
