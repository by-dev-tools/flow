### FB-0061: A post-merge doc-currency step needs its own human-invoked skill — the open-PR ship can't reconcile a merge it runs before

**Date:** 2026-06-28
**Source:** review feedback (a health-tracker iOS consumer dogfood — FLOW-1) + the PR-2 build

**What was said:** A consumer's `/flow:ship` run reconciled the forward docs (roadmap "Now", plan "Current Focus") to the just-shipped item at *PR-open* time, but after the human merged, nothing flipped the item to "merged (#N)" or moved it out of the active slot — `main` sat stale until a manual `docs: post-merge currency` PR, repeatedly. The fix is a dedicated post-merge skill; it can't live inside `/flow:ship` because Claude can't merge, so the reconciliation has to happen in a separate human-invoked pass after the merge.

**Synthesized rule:** **Reconciliation that depends on the merge having happened belongs in a post-merge step, not in the pre-merge ship pipeline.** `/flow:ship` runs *before* the merge gate, so it can only ever record "at PR (#N)"; the "→ merged (#N)" transition, moving the item to Recently-shipped, the late visual-history distill (a visual pass blocked at ship that completed afterward), and clearing the PR's reserved numbers all require the merge to have occurred. Ship those as a human-invoked `/flow:land <PR#>` (`disable-model-invocation: true` — Claude can't merge, so it must never auto-fire), built fail-loud (verify `state == MERGED` before editing anything), WARN-not-silent on a no-match discovery (FB-0010), idempotent on re-run, and reusing the one canonical distill implementation rather than forking it.

**Applies to:** `skills/land/SKILL.md`, `skills/land/lib/land-helpers.py`, `evals/run_land_evals.py`; `/flow:ship` §5c (reused distill); `docs/workflow.md` Step 11; FB-0010 (silent-skip / fan-out), FB-0051 (re-scope-to-delta — this PR was rebased off the superseded FLOW-2 work), FB-0057/FB-0060 (the sibling gh-resilience lessons).
