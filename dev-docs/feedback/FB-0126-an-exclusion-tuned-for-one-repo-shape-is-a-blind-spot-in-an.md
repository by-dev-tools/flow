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

- **Second measured site, found while shipping the first fix — and it is the gate that certifies
  reviews ran.** `/flow:ship` Step 1.0a's rigor gate asks "did `/simplify` + `/flow:staff-review`
  actually run on this source?" and answers it from a fingerprint that
  `skills/ship/lib/rigor-marker.py:98` builds by filtering `git diff --name-only` through
  **`sourceFilePatterns`** — the same allowlist, with the same `.md` gap. Measured on this very PR:
  of 29 changed files, 16 are fingerprinted and **0 of the 11 changed `.md` files are**, including
  `plugins/flow/skills/audit-coverage/SKILL.md`. I changed that file in a commit made *after*
  writing the marker, and the gate still reported `ok`. So on a repo whose deployed surface is
  prompts, **a PR that changes only prompts can never invalidate its own staff-review marker** —
  the enforcement mechanism for "reviews ran on this source" is structurally unable to see the
  source. The reviews did happen here (the lenses cite `SKILL.md` line numbers throughout); what is
  broken is the mechanism's ability to *prove* it, which is the whole point of FB-0047's
  "enforce, don't attest".

  It generalises the rule above rather than repeating it: **one filter, written for one question,
  gets reused as the answer to a different question.** `sourceFilePatterns` was written to answer
  "is this diff worth a security review / a preflight run?" — a cost-and-risk question about
  *language*. Four gates now consume it as if it answered "is this file deployed surface?", a
  question about *role*. Before reusing a path filter, ask what question it was written for; if
  that differs from yours, you have inherited its blind spots along with its convenience.
  Tracked in `dev-docs/roadmap.md` § Next. Not fixed alongside the first site:
  `plugins/flow/skills/ship/**` is in flow's own `sensitivePaths`, so it never routes below the top
  tier and does not belong bundled into another change's scope.

- **Applies to:** workflow, code, architecture — any gate whose scope comes from a path pattern.
