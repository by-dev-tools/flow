### docs: capture the `/flow:post-merge` skill design into the roadmap (recovered from a transcript)
**Date:** 2026-07-20
**Branch:** claude/roadmap-post-merge-skill (commit: pending ship)

**What was done:**
Added a `## Next` roadmap entry for **`/flow:post-merge`** — a human-invoked skill (bare `/post-merge` alias) that (1) verifies the branch's PR is actually merged, (2) synthesizes the *merge-gate* feedback window ship's Step 4 can't see, (3) safe-deletes the merged branch, and (4) emits a `✅ safe to archive` / `🚫 not safe` verdict. The entry records the full v1/v1b design, the resolved decisions (user-scope-store-only v1 with content-match dedup sidesteps both the watermark and the commit-to-merged-branch problems; no SessionStart hook; transcript-*timestamp* not commit-SHA watermark in v1b), and the enumerated edge cases. Docs-only; no version bump.

**Why:**
The design was worked out in full in a 2026-07-08 session ("AI coding workflows comparison") and the session ended on "want me to write this up as a roadmap entry + plan?" — which never happened, so it lived only in that transcript. A later session asked "is there a post-merge skill that analyzes transcripts and checks archive-safety?" and the answer was no — despite the user having designed exactly that. This entry stops the loss. (Itself a small instance of the very leak `/flow:post-merge` targets: a decision made in a session that never reached a durable doc.)

**Design decisions:**
- **Placed after the `/flow:land` merge-event auto-trigger item (FB-0063), not merged into it.** `/flow:post-merge` is the broader manual bundle (cleanup + archive-check + the feedback-window fix); FB-0063 is specifically about *auto-firing* land. Keeping them adjacent-but-distinct preserves the scope boundary — and `/flow:post-merge` could itself later become a target of the FB-0063 auto-trigger. Also kept distinct from `/flow:land` (doc-currency for the merged PR) so the two skills' scopes don't blur.
- **No FB number.** This is a recovered feature-direction, not a synthesized user-correction rule — roadmap direction, not a `feedback.md` entry.

**Tradeoffs discussed:**
- Considered writing the whole thing straight to a plan for the approval gate (part B). Deferred — part A (durable capture) is the cheap, loss-stopping half; the plan is a separate build the user gates when ready.
