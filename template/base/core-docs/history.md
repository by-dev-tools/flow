# History

Detailed record of shipped work. Reverse chronological (newest first). This is not a changelog — it captures the **why**, **tradeoffs**, and **decisions** behind each change so future sessions have full context on how the project evolved.

`/flow:ship` writes one entry per shipped PR at step 5.

---

## How to write an entry

```
### [Short title of what was shipped]
**Date:** YYYY-MM-DD
**Branch:** branch-name
**Commit:** [SHA or range; PR link]

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

---

## Entries

<!-- Add new entries below this line, newest first. -->
