# FB-0133 — `git grep` does not see the files this PR is adding, so the grep-first rule has a hole exactly where new work lives

- **Date:** 2026-10-04
- **Source type:** reviewer finding (`/flow:staff-review`, staff-engineer lens), endorsed; recurrence of the FB-0010 fan-out class with a newly-identified cause.

- **What happened.** A review pass corrected the mechanism behind a rule mid-ship: a check that
  pointed at `/flow:spawn`'s admission-control sweep was re-pointed at the backend's `listWorkers`
  verb, because the sweep structurally could not detect the collision it was meant to catch. I
  then did what `.claude/rules/general.md` § Consistency item 2 prescribes — grep first, edit
  second — ran `git grep` for the old mechanism, found two survivors, fixed them, and reported the
  fan-out closed.

  **Three more survivors were still there**, and one was the *user-facing changelog*, which
  re-advertised the known-broken instrument as the feature. A reviewer found them with plain
  `grep -rn`. The reason `git grep` missed all three: **they were untracked.** `git grep` searches
  the index and tracked worktree files only, and all three were files this PR was *creating* —
  `changelog/v1.61.0.md`, the new `dev-docs/history/` entry, and the new `dev-docs/feedback/` entry.

- **Why this is worth an entry rather than a one-off fix.** The grep-first rule exists to stop a
  contract change from leaving contradictions behind. Its blind spot is **precisely the files a
  contract change adds** — the changelog, the history entry, the feedback entry, the new eval. On
  a repo with one-file-per-entry docs (which this one deliberately is, to avoid merge conflicts)
  *every* PR adds several untracked prose files that restate the thing being changed. So the hole
  is not an edge case here; it is the common case, and it is biased toward the single most
  user-visible file in the set.

  It also fails in the most misleading direction: `git grep` returning fewer hits reads as
  *progress* ("the survivors are fixed"), not as *a narrower search*. That is the
  measurement-that-can-only-return-clean shape from item 4, wearing the costume of item 2.

- **Synthesized rule:** **for a contract/fan-out sweep, use `grep -rn` (or `git grep
  --untracked`), never bare `git grep`.** State the tool in the check, not just the intent — "grep
  for the old value" is satisfiable by a command that cannot see half the diff. And when a sweep
  reports zero survivors, confirm the search actually covered the files the PR adds: `git status
  --short` lists them, and if any is a doc that restates the contract, it must be in scope.

- **How to apply:** before claiming a fan-out closed, run the sweep as
  `grep -rn '<old-value>' --include='*.md' --include='*.py' . | grep -v '^./.git/'` and separately
  eyeball the untracked set. The three doc classes that most often carry a restated contract and
  are most often untracked: the changelog entry, the history entry, and the feedback entry — i.e.
  exactly the three a `/flow:ship` run creates. Related: [[FB-0010]] (the fan-out class this is a
  cause of), and `.claude/rules/general.md` § Consistency items 2 and 4.
