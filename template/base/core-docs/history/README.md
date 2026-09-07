# History

Detailed record of shipped work. This is not a changelog — it captures the **why**, **tradeoffs**, and **decisions** behind each change so future sessions have full context on how the project evolved.

`/flow:ship` writes one entry per shipped PR at step 5 — **as a new file**, `YYYY-MM-DD-<slug>.md`.

## One file per entry

**Every entry is its own file.** There is no rollup file and no index file, deliberately: an append-only doc is the single
biggest source of merge conflicts in a repo where more than one branch is ever open at once, because every concurrent PR
appends at the same insertion point. One file per entry removes the shared line entirely.

It also removes a subtler failure. A text merge can drop an entry with **no conflict markers and a clean parse** — the
result looks fine and nobody notices. A merge cannot silently drop a *file*: deletion shows up as a visible file deletion
in the diff.

Do not add an index file. `ls` **is** the index — and a committed index would recreate the exact conflict this structure
removes, since every new entry would append a line to it.

Oldest-first is `ls`; newest-first is `ls -r`.

---

## How to write an entry

```
## YYYY-MM-DD — [Short title of what was shipped]
**Branch:** branch-name · **SHA:** [SHA or range; PR link]

**What was done:**
[Concrete deliverables — what changed in user-facing terms.]

**Why:**
[The problem this solved or the goal it served.]

**Design decisions:**
- [UX or product choice + reasoning]

**Technical decisions:**
- [Implementation choice + reasoning]

**Tradeoffs discussed:**
- [Option A vs Option B — why this one won]

**Lessons learned:**
- [What didn't work, what did, what to do differently]
```

Use the `SAFETY` marker on any entry that modifies error handling, persistence, data loss prevention, or fallback behavior.
