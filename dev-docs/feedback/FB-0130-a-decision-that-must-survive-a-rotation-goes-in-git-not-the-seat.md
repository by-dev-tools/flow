# FB-0130 — A decision that must survive an orchestrator rotation goes in git, not in the seat's journal

- **Date:** 2026-10-03
- **Source type:** user correction (Ben), at the orchestrator seat.

- **What was said:** asked to note that the in-sandbox worker watcher should be revisited after the
  program's stopping point, the orchestrator recorded it in `.context/orchestrator-journal.md` and said it
  would be folded into the roadmap "at the wrap-up". Ben: *"I want this noted in the repo itself,
  git-tracked. I don't want to forget about it if we cycle orchestrators."*

- **Why the first answer was wrong, specifically.** The seat had itself established, two days earlier,
  that a local file is **compaction-proof but not teardown-proof** (`dev-docs/roadmap.md` § "orchestrator
  seat policy"), and that the seat's sandbox is recycled when idle. It then put a decision Ben explicitly
  wanted to outlive the seat into exactly the medium it had classified as not outliving the seat — and
  deferred the git write to a "wrap-up" that only that same seat would remember to do. The journal was
  the right place for in-flight narrative; it was the wrong place for something the human has already
  decided must persist.

- **Synthesized rule:** **sort a decision by who needs it, not by when it is convenient to write.** If the
  human has said it must survive a rotation, or a successor seat would need it to act correctly, it goes
  to a git-tracked doc *now* — a small reviewed PR, not a note promising a later one. The journal holds
  only what this seat needs to resume itself. "I'll fold it in at the wrap-up" is a promise held in the
  one place that does not survive the wrap-up being skipped.

- **How to apply:** when a decision is recorded, ask "would a fresh orchestrator, reading only `main`,
  need this?" If yes, it is a PR this turn. Corollary for this program: deferred-item notes ("revisit X
  after the stopping point") belong in `dev-docs/roadmap.md` at the moment of deferral — they are the
  items most likely to be forgotten, because nothing forces them back into view.
