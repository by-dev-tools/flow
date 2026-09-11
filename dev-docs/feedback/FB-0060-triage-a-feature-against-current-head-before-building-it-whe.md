### FB-0060: Triage a feature against current HEAD before building it; when a sibling PR ships your overlap, re-scope to the non-duplicated delta — and a canonical fan-out block must cover EVERY site

**Date:** 2026-06-27
**Source:** review feedback (the FLOW-2 PR's own merge reconciliation) + FB-0051 (re-scope-to-delta) + FB-0010 (fan-out)

**What was said:** A FLOW-2 PR (REST PR-body writes, originally v1.10.1) was built switching `/flow:ship` + `/flow:staff-review` + `/flow:ship-spike` off `gh pr edit --body`. While it was in flight, **#56 independently shipped the same fix** to `main` (a canonical `gh`-resilience fallback block in `/flow:ship` Step 7, referenced by `/flow:staff-review`) — and went further (draft-toggle GraphQL mutations). At merge, the FLOW-2 PR was `CONFLICTING` and ~90% duplicate. Rather than force a duplicate, it was reset to `main` and reduced to its **one non-duplicated delta**: `#56` had wired the canonical block into ship + staff-review but **missed `/flow:ship-spike`'s PR-OPEN re-ship path** (the third PR-write site) and left the `/flow:staff-review` §1.5 note stale. So the re-scoped PR = extend the canonical block to ship-spike + de-stale the note.

**Synthesized rule:** Three, reinforcing:

1. **Triage against current HEAD before building.** Before implementing a fix from a feedback report, check whether `main` (or an in-flight sibling PR) already ships it. Half of one dogfood batch's items were already closed on HEAD; this batch's FLOW-2 was independently shipped by #56 mid-flight. `git fetch` + grep the target surface first — cheap insurance against building a duplicate.
2. **When a sibling ships your overlap, re-scope to the non-duplicated delta (FB-0051).** Don't force-merge a near-duplicate and don't naively rebase (which re-introduces a competing mechanism). Reset to `main`, find the genuinely-unique remainder, and ship only that. #56 did exactly this to itself vs #57; the FLOW-2 PR did it vs #56.
3. **A canonical fan-out block must cover EVERY site (FB-0010).** #56 introduced a *canonical* gh-resilience block precisely to avoid fan-out drift — then wired it into 2 of 3 PR-write skills, missing `ship-spike`. Centralizing the implementation doesn't close the fan-out unless every call site references it. When you add a "canonical, referenced everywhere" block, `git grep` the full set of call sites and wire them all in the same PR.

**Applies to:** `/flow:ship-spike` Step 7 (the missed site), `/flow:staff-review` §1.5 (stale note), the canonical gh-resilience block in `/flow:ship` Step 7; FB-0051 (re-scope-to-delta), FB-0010 (fan-out / grep-first), FB-0057 (the superseded REST-PR-body rule, now embodied by #56 on main).
