## 2026-09-17 — Ship the orchestrator field manual (docs-only, no version bump)

**Branch:** `conductor/ship-the-orchestrator-field-manual`.

### What was done

Opened the PR for `research/orchestrator-field-manual.md` — written across 8 commits on
2026-09-12/13, pushed, then left without a PR for four days. Rebased onto `main` (which had
advanced past #154 in the interim; rebase was clean, no conflicts — the branch's 3 touched files
(`dev-docs/README.md`, `research/2026-08-23-flow-cloud-workflow-plan.md`,
`research/orchestrator-field-manual.md`) are disjoint from everything that merged since). Ran the
full `/flow:ship` pipeline and opened the PR. No content edits — the doc's five measurement traps,
resolve-vs-escalate calls, and presentation rules were authored in a prior session and are out of
scope for this pass by explicit instruction.

### Why

Another in-flight branch (the §4.10 orchestrator skill suite) is blocked on this doc existing on
`main`: its PR satisfies three of the field manual's own deletion criteria and, per the standing
rule that whoever satisfies a deletion criterion deletes it in the same PR, needs the file to exist
in the target branch to do that. It doesn't, because this branch sat unshipped. Shipping this first,
unedited, unblocks that PR to make its own deletions in its own diff.

### Design / technical decisions

- **No version bump.** Diff touches no `plugins/flow/**` or `.claude-plugin/*` path — confirmed by
  grepping the diff for those paths before pushing. Docs-only self-repo tracking never bumps the
  plugin version.
- **Index entry was already present.** The branch's own commits had already added the
  `dev-docs/README.md` row and the doc's own `**Status: LIVING.**` line in its first 12 lines —
  `python3 dev-docs/check-index.py` passed clean pre-rebase and again post-rebase. Nothing to author
  here; just verified.
- **Reviewers all self-skipped legitimately.** Security, accessibility, verify-build, and
  audit-coverage all ran and returned clean SKIPPED verdicts (docs-only diff, no UI files, `platform:
  library`, no behavior-bearing source). `/flow:audit-skips` confirmed all 7 stage skips (including
  `/simplify` and `/flow:staff-review`, which this docs-only ship never invoked) as LEGITIMATE —
  none required a re-run.

### Tradeoffs

**Content review deliberately not performed.** The task was scoped to shipping already-written
material, not auditing it — the three sections the blocked PR would satisfy stay in the doc,
undeleted, for that PR to remove after this one merges and it rebases. Any staleness in those
sections is flagged to the dispatcher, not acted on here.

### Lessons learned

A written-but-unshipped doc is a liability, not neutral: this file sat mergeable for four days
while another workstream's correctness depended on its presence on `main`. The cost of "it's done,
just needs a PR" is not zero — it compounds onto whoever's blocked on it discovering the branch was
never opened.
