## 2026-09-16 — Harvest four lessons by hand, because Step 4c never ran (FB-0111)

**Branch:** `conductor/reviewer-verdict-context-conditional-fb-0111` · docs-only, no version bump.

### Why this PR exists at all

The FB-0107 provenance PR (#150) merged, and the pre-archive check on its workspace asked for a manual
export of the contribution queue. The queue directory **did not exist**, and `last_harvested.json` was
**absent**. That second fact is the one that mattered: an absent watermark proves `/flow:ship` Step 4c
never executed, so "empty queue" meant *never harvested*, not *nothing qualified*.

**The cause was an operator skip, not absent code** — and that is a different failure from the one
FB-0107 predicted. FB-0107's case is code that was not present to run (the installed plugin lagging the
repo). Here the code was present and simply never reached: the ship run went pre-flight → reviewers → PR
creation, skipping Steps 3–5 because the doc work had already been done by hand, and 4c sits inside that
range. Four flow-generalizable lessons were therefore sitting in a chat transcript with no commit behind
them, one archive away from deletion. This PR is the hand-harvest.

### What shipped

- **FB-0111** — a reviewer's verdict must be conditional on its own context having resolved.
- **Four roadmap § Next lines** — the watermark tell, the negative-grep sanity check, the
  count-in-prose fan-out corollary, and the pinned-at-run-start rule for "what ran" reporters. Each
  cites its incident so it is checkable rather than folklore.

### The correction that shaped FB-0111, and why it is worth recording

The lesson was **first stated wrongly**, and the orchestrator caught it before it was filed. The original
claim was a live inconsistency: `extract_session.py` warns on a bad glob while `staff-review` renders
`(no feedback doc at dev-docs/feedback)` as an unremarkable context line — one sibling warns, the other
does not.

**That is not live on `main`.** Verified independently rather than accepted: `sh
plugins/flow/lib/resolve-doc-slot.sh feedbackPath dev-docs/feedback.md` returns `DIR dev-docs/feedback
(93 entries, one file per entry)`, `staff-review` on `main` calls that resolver, and the resolver's own
header documents the silent `(no … doc at X)` fallback as the bug **#146 fixed**. What had been observed
was 1.29.0's pre-#146 behaviour — another FB-0107 artifact. Filing it would have created the worst kind
of inherited to-do: a future seat re-investigating a bug that no longer exists.

**The surviving rule is stronger than the one first written, and narrower than "reviewers should warn".**
Measured while writing the entry:

- The `"This is not an APPROVED"` sentence already exists in `skills/critique-plan/SKILL.md` — for
  exactly **two** preconditions, `ROOT-UNRESOLVED` and `JQ-MISSING`. Both are failures to *start*.
- The case actually hit was a failure to *find*: root resolved, jq present, globs ran, matched nothing.
  No rule covers it.
- The rule lives in the wrapper, not in the agent that authors the verdict. `agents/plan-critic.md`
  names `APPROVED` three times with **zero** instructions making it conditional on context;
  `agents/auditor.md` likewise.

So the gap is: the warning and the verdict are independent, and the conditional is missing from the one
place where the verdict is written. A critic can print `⚠️ MISSING` and return `APPROVED` in the same
output, and nothing forbids it.

### Tradeoff

**Filed as a rule, not built as a fix.** The change belongs in the agent prompts — deployed surface under
this repo's own "prompt changes are code changes" bar, needing eval fixtures and a new verdict token so a
consumer can distinguish "reviewed and clean" from "could not review". That is a scoped PR, not a
docs-only one, and inventing the token here without a fixture would be the shape FB-0056 warns about.

### The finding worth keeping past this PR

Three of the four defects in #150 were caught by reviewers **disagreeing** — with each other or with the
author. `/simplify`'s lenses split on whether `ROW_LABELS` was dead code or the single definition (reuse
was right). The UX lens diagnosed the cry-wolf defect correctly and prescribed a fix that would have made
the flagship case *worse*, because it keyed severity on a predicate that is false in exactly the failure
the PR existed to expose. `/flow:security-review` found a verdict-forgery the other four missed.

**The value was not any single gate being right; it was having enough of them that being wrong was
survivable.** That is a direct argument against trimming the reviewer suite on token cost: a cost model
that justifies each gate independently will conclude the redundant ones are waste, when the redundancy is
the mechanism. Recorded here because it is evidence, and evidence outlives the session that produced it.
