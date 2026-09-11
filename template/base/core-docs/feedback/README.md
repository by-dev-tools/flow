# Feedback Log

User feedback synthesized into actionable guidance. When the user gives feedback — corrections, preferences, reactions, direction changes — the relevant insight is captured here so it shapes all future work.

This is not a transcript. Each entry distills feedback into a rule or preference that applies going forward.

`/flow:ship` writes entries at step 4a (user-feedback layer) — **as a new file**, `FB-XXXX-<slug>.md`.

## One file per entry

**Every entry is its own file.** There is no rollup file and no index file, deliberately: an append-only doc is the single
biggest source of merge conflicts in a repo where more than one branch is ever open at once, because every concurrent PR
appends at the same insertion point. One file per entry removes the shared line entirely.

It also removes a subtler failure. A text merge can drop an entry with **no conflict markers and a clean parse** — the
result looks fine and nobody notices. A merge cannot silently drop a *file*: deletion shows up as a visible file deletion
in the diff.

Do not add an index file. `ls` **is** the index — and a committed index would recreate the exact conflict this structure
removes, since every new entry would append a line to it.

## Claiming an FB number

There is no reservations file. **Claiming a number is pushing the file:** create `FB-XXXX-<slug>.md` and push it before you invest in cross-file `FB-XXXX` references elsewhere. If another branch claims the same number, git reports a **both-added filename conflict** — which cannot be auto-merged and cannot be forgotten. A registry file cannot make that guarantee: it is itself an append-only doc that git merges happily.

---

## How to write an entry

```
### FB-XXXX: [Short summary of the feedback]
**Date:** YYYY-MM-DD
**Source:** user correction | user preference | user direction | review feedback

**What was said:** Brief, factual summary of the feedback.

**Synthesized rule:** The actionable takeaway — what to do differently going forward.

**Applies to:** [areas this affects: ux, code, architecture, workflow, etc.]
```

### Numbering

Increment from the last entry. Use `FB-0001`, `FB-0002`, etc.

### Source types

- **user correction** — user fixed something you did wrong
- **user preference** — user expressed a stylistic or process preference
- **user direction** — user set strategic direction or priorities
- **review feedback** — issues found during code/design review
