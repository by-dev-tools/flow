### Bootstrap doc — document `allow_auto_merge` prereq for the merge queue
**Date:** 2026-05-25
**Branch:** [next branch off main]
**Commit:** [next commit]

**What was done:**
Added an "Optional — GitHub merge queue" section to `docs/bootstrap.md` (between Step 6 and "What's next") and a matching Troubleshooting entry. Documents the four-step recipe (enable auto-merge → add CI workflow → apply ruleset → queue with `gh pr merge --auto`) and calls out `allow_auto_merge=true` as the load-bearing prereq that produces the `enablePullRequestAutoMerge` GraphQL error if skipped.

**Why:**
Flow's own merge queue setup in the prior history entry hit this exact error mid-flow (`gh pr merge 14 --auto` failed; had to `gh api -X PATCH /repos/by-dev-tools/flow -f allow_auto_merge=true` before queueing worked). md-manager already had it enabled, so the divergence was invisible until flow's first queued PR. Any consumer following flow's lead and setting up a queue will hit the same wall.

**Design decisions:**
- **Placed in `docs/bootstrap.md`, not `plugins/flow/docs/workflow.md`.** Workflow.md is a 413-line loop reference with no GitHub-infra section; expanding its scope to cover repo settings would dilute its purpose. Bootstrap.md already covers GitHub PR setup at Step 6, so this fits naturally as an optional sub-step.
- **Framed as optional, not mandatory.** Flow doesn't ship a merge-queue requirement — it ships a loop. The queue is one of several ways to enforce the loop's "every PR through CI" discipline; consumers without a queue still get the loop's value.
- **Included the four-step recipe inline, not as a separate doc.** Bootstrap.md is already a stepwise recipe; adding another markdown file for one optional configuration would fragment the consumer's read path.

**Technical decisions:**
- Referenced both `by-dev-tools/flow` (Python stdlib CI) and `by-dev-tools/md-manager` (Node CI) as reference workflows so consumers can pick whichever matches their stack.
- The ruleset-copy instruction points at `gh api /repos/by-dev-tools/flow/rulesets/<id>` rather than embedding a JSON payload — the payload is long and would drift if the source ruleset evolves.

**Tradeoffs discussed:**
- Inline section vs. standalone `docs/merge-queue.md`. Standalone would be easier to deep-link but adds a file for ~30 lines of content; the bootstrap reader is already in the right mental context for "PR machinery setup". Kept inline.
- Whether to also add this to `template/base/README.md.template`. The template is project-generic README boilerplate (consumer's own README), not flow's setup docs — would be confusing to inject flow-specific GitHub setup into a project README scaffold. Skipped.
