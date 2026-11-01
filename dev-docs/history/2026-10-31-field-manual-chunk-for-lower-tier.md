## 2026-10-31 — Field manual: scope a dispatch to one shippable PR, corrected same day (orchestrator seat, docs-only)

**Branch:** `orchestrator/chunk-for-lower-tier` · **Feedback:** FB-0139

**What:** one addition to `research/orchestrator-field-manual.md` § 3 (presentation rules the human
has stated directly), recording Ben's 2026-10-31 direction ahead of a move to a lower Conductor
usage tier: chunk dispatches so work ships consistently rather than accumulating unshipped on one
branch. **The first version of this entry justified it by "fits inside one weekly-limit window."
Ben corrected that the same day, before this PR merged:** the orchestrator has no way to measure or
predict usage-limit consumption, so that yardstick doesn't hold up. The entry now justifies the
same practice — chunk work, ship consistently — by something auditable instead: whether a dispatch
produced the one shippable PR its brief named, which is decided at dispatch time and checked after
the fact, not predicted.

**Why now, and why in git:** the same reasoning as FB-0130 — a direction Ben wants to outlast this
session belongs in a git-tracked doc, not only in the orchestrator's chat or its scratch journal.
This one had extra weight: while reviewing the live fleet the same session, two workers (`effic`,
`mobile-opts`) turned out to have been sitting correctly-idle for 21–25 days because the seat never
sent the merge-ping it owed them after #179 and #183 landed — a live instance of exactly the
"lost, not delayed, progress" failure this rule names, discovered while writing it down.

**Decisions and tradeoffs:**
- **Placed alongside the existing presentation rules (§ 3)** rather than as a new top-level
  section — it's the same shape (a direct Ben quote, dated, with the reasoning spelled out) as the
  "Waiting on you" and `[watcher]`-label entries already there.
- **Explicitly reconciled against the earlier `token-not-time` entry** rather than left to read as
  a contradiction: that one says don't ration tokens to save capacity; this one says don't let
  scope drift past what the dispatch named — unaffected by the correction, since neither half was
  about time or token measurement.
- **No new mechanism, before or after the correction.** The rule is about how a dispatch brief is
  scoped, not a scheduler or a stricter watcher — consistent with Ben's standing "don't overbuild"
  direction. The correction changed the *justification* (measurable scope, not an unmeasurable
  budget), not the practice itself (split large work into sequential, independently-shippable PRs).
- **Caught before the PR merged, not after.** Worth naming because it's the better outcome than the
  alternative: a rule resting on a claim nobody could check would have sat in the field manual
  looking authoritative until someone tried to act on it and found the yardstick didn't exist.
