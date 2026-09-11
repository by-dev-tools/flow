# History

Detailed record of shipped work. This is not a changelog -- it captures the **why**, **tradeoffs**, and **decisions** behind each change so future sessions have full context on how the project evolved.

## One file per entry

**Every entry is its own file: `YYYY-MM-DD-<slug>.md`.** There is no rollup and no index file, deliberately — either would recreate the merge conflict this structure exists to remove. `ls dev-docs/history/` **is** the index.

`ls` sorts oldest-first because of the date prefix, inverting this doc's historical newest-first reading order. **Use `ls -r dev-docs/history/`** for newest-first. Read the whole corpus with `cat dev-docs/history/2*.md`.

Two heading shapes exist in the corpus, both preserved verbatim from the pre-fragmentation doc: newer entries lead with `## YYYY-MM-DD — Title`, older ones with `### Title` plus a `**Date:**` line. New entries should use the `## YYYY-MM-DD — Title` form.

## How to Write an Entry

```
## YYYY-MM-DD — [Short title of what was shipped]
**Branch:** branch-name · **SHA:** [SHA or range]

**What was done:**
[Concrete deliverables -- what changed in user-facing terms.]

**Why:**
[The problem this solved or the goal it served.]

**Design decisions:**
- [UX or product choice + reasoning]

**Technical decisions:**
- [Implementation choice + reasoning]

**Tradeoffs discussed:**
- [Option A vs Option B -- why this one won]

**Lessons learned:**
- [What didn't work, what did, what to do differently]
```

Use the `SAFETY` marker on any entry that modifies error handling, persistence, data loss prevention, or fallback behavior.

## Known duplicate — scheduled, not lost

`2026-08-15-f11-reword-...-a.md` and `...-b.md` are **the same entry twice with different bodies**, preserved exactly as found in `main`. PRs #114 and #115 each added it at a slightly different offset and git auto-merged both, cleanly and invisibly. Nothing was repaired at migration time — the reversible option was taken deliberately. Merge them whenever someone has the context.
