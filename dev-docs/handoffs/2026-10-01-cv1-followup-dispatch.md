# CV1 follow-up — the orchestrator's dispatch, verbatim

**Status: ACTIVE.** This is the authority the plan block for
`conductor/cv1-followup-reviewer-rigor-walkextract` cites. Written because
`/flow:audit-plan` flagged it: the plan cited "the dispatch" six times as the source of its
scope bound and of both open decisions, and no artifact existed on disk — so a seat that did
not receive the dispatch could not check either side of a stated disagreement.

Quoted verbatim, not paraphrased. Trimmed only of the sequencing instructions about #172, which
are discharged (it merged as `a250b66`).

---

> **Ben decided (a): finish CV1 inside the stopping point.** After #172 ships, you get one
> follow-up PR covering three fixes. Order of operations: finish #172 first (wait for #171 to
> merge, rebase, mark ready, send the final SHA), then **branch the follow-up from `main` after
> #172 merges**, since it edits the same `audit-coverage` files.
>
> **Scope: these three fixes and nothing else.**
> 1. **Reviewer instructions.** Stage 1 and `auditor.md` tell the reviewer that doc changes are
>    not behaviours, which is the likeliest cause of 20–40% single-run recall. **Be careful with
>    `auditor.md`.** It is shared by `/flow:audit-plan` and `/flow:audit-completion`, which do
>    different jobs. Scope the change to the coverage path if you can. If it has to touch the
>    shared agent, measure those two reviewers too, not just coverage.
> 2. **`rigor-marker.py:98`** fingerprints only through `sourceFilePatterns`, so 0 of 11 changed
>    `.md` files were covered. Include the behaviour-bearing doc patterns, so a `SKILL.md` edit
>    after review makes the marker stale.
> 3. **`walk_extract.py` ending the block early** when a continuation line opens with `**`
>    (15 criteria became 5, with no warning). Fix it **paired**: a plan written that way keeps
>    every criterion, **and** a block that genuinely ends early says so out loud.
>
> **What "done" means. Both directions are required, because the first fix risks false alarms.**
> That instruction exists to stop the reviewer flagging wording edits. Removing it is exactly how
> precision breaks.
> - **Recall:** the #159 case, same rig, `--selftest` first. Report single-run scores and the
>   union, against today's 20–40% / 60%.
> - **Precision:** the pure-prose negative must still return `No issues flagged.`. Run it more
>   than once, since you'll be comparing rates and n=1 can't show that. Also report false
>   positives across every recall run. **If precision drops, it's a regression, not a
>   trade-off. Bring it back to me; don't ship it.**
> - Prompt changes are code changes: write the eval fixture first.
>
> **Process: stop at the plan gate.** Put the plan in `dev-docs/plan.md` as a fresh active block
> above the merged ones, run `/flow:critique-plan` and `/flow:audit-plan`, then message me. Take
> version and FB numbers at ship time; expect v1.56.0.

---

**Note on item 1's wording.** The dispatch says "Stage 1 and `auditor.md`" — i.e. it already
named two sites. The plan's first draft wrongly claimed only one existed; see the plan's "What I
got wrong" section. The dispatch was right and more precise than the correction applied to it.
