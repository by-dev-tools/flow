# FB-0126 — An exclusion tuned for one repo's shape becomes a blind spot in another, and the gate has to say which shape it assumed

- **Date:** 2026-09-30
- **Source type:** user direction (CV1 dispatch) + measurement during execution.

- **What was said:** the task named three constraints and forbade relitigating them: `sourceFilePatterns`
  and `EXCL` are a **published contract every consumer inherits**, the 60 KB evidence cap is real, and
  "recall over what it sees" must stay separately measurable. So the fix could not be "widen the regex".

- **What was measured.** `/flow:audit-coverage`'s behaviour diff never selected a `.md` file — and the
  cause was not the `|\.md$` clause everyone pointed at. A `.md` path does not match
  `sourceFilePatterns` **at all**, so that clause was belt-and-braces: deleting it would have changed
  nothing. This is an **inclusion** problem wearing an exclusion's clothes, and the distinction decides
  the whole design. On flow — a plugin whose deployed surface *is* prose — #159's five undeclared
  behaviours all lived in one `SKILL.md`, and the reviewer returned "no issues" having never been shown
  the file. With the new slot set, the same reconstruction scores 2-of-5 and 1-of-5 single-run, union
  3-of-5. The 0 was never judgment.

- **Synthesized rule:** a path filter encodes an assumption about **the shape of the repo it runs in**,
  and that assumption is invisible to the consumer who inherits it. Two obligations follow, and the
  second is the one that is usually skipped:

  1. **Make the assumption a declared slot, defaulting to the old behaviour.** `behaviorBearingDocPatterns`
     defaults empty, so no consumer's result changes until they opt in. A filter change that silently
     reclassifies files for everyone is not a fix, it is a different bug.
  2. **Have the run state which shape it assumed, every time, when the assumption may be wrong.** With
     the slot unset the run prints `WEAKENED · DOC-BLIND` naming every changed doc-shaped file it did
     *not* read. Leaving the slot unset is legitimate; *not knowing it was unset* is not. This is
     [[FB-0121]]'s rule applied to file selection rather than to base-ref resolution: silence and "I
     could not look" must not render identically.

  And the diagnostic habit: **before widening a filter, check which clause actually excluded the file.**
  Two clauses can both match, and fixing the wrong one ships a no-op with a convincing rationale.

- **Applies to:** workflow, code, architecture — any gate whose scope comes from a path pattern.
