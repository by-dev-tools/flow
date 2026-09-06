### SAFETY: extend the canonical gh-resilience fallback to /flow:ship-spike — fan-out completion (v1.11.1, FB-0060)
**Date:** 2026-06-27
**Branch:** claude/vigilant-galileo-1d3593
**Commit:** `aa45347` (on branch; final SHA in the PR)

**What was done:**
Re-scoped the original FLOW-2 PR (REST PR-body writes, v1.10.1) down to its one non-duplicated delta after #56 independently shipped the same fix to `main`. #56 added a canonical `gh`-resilience fallback block (REST `gh api -X PATCH` body write + `markPullRequestReadyForReview`/`convertPullRequestToDraft` draft-toggle mutations) to `/flow:ship` Step 7 and referenced it from `/flow:staff-review` Step 7 — but **missed `/flow:ship-spike`'s PR-OPEN re-ship path** (the third PR-write site) and left the `/flow:staff-review` §1.5 gh-safety note stale. This PR:
- `/flow:ship-spike` Step 7 — added a **PR-OPEN (re-ship)** branch that references the canonical fallback for the body update + draft toggle on a `projectCards` error (was: only the LOCAL-ONLY `gh pr create` path).
- `/flow:staff-review` §1.5 — de-staled "the Step 7 `gh pr edit` invocation" → "the Step 7 PR-body write (`gh pr edit`, or its `gh api` projectCards fallback)".
- Version v1.11.0 → **v1.11.1**; CHANGELOG + roadmap headline reconciled; FB-0060.

**Why:**
On classic-projects repos with affected `gh` versions, a `/flow:ship-spike` re-ship's body update hits the same `projectCards` GraphQL deprecation #56 fixed everywhere else — but ship-spike was left exposed. A canonical block only closes a fan-out if every call site references it (FB-0010).

**Design decisions:**
- **Re-scope, don't duplicate (FB-0051).** The original PR was reset to `main` and reduced to the unique remainder rather than force-merging a near-duplicate of #56 or naively rebasing (which would leave two competing PR-body-write mechanisms — #56's fallback-on-error vs the original's REST-by-default-with-read-back). Mirrors what #56 itself did vs #57.
- **Reference the canonical block, don't re-inline.** ship-spike points at `/flow:ship` Step 7 § "gh resilience" (the same way staff-review does), so there's one implementation.

**Tradeoffs discussed:**
- **Dropped the read-back-verification idea** the original PR carried (verify the body landed after PATCH). #56's design is fallback-only-on-error, not REST-by-default; layering read-back onto it is a different shape and out of scope for this fan-out fix. Noted as a possible future enhancement, not pulled in.

**Lessons learned:**
- Triage against current HEAD before building (FB-0060): the original FLOW-2 work was done without noticing #56 was in flight shipping the same fix — exactly the "triage against HEAD" miss FB-0057 warned about, now generalized.
