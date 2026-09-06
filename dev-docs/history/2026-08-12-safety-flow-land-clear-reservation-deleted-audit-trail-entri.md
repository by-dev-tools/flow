### SAFETY: `/flow:land` clear-reservation deleted audit-trail entries, not just the reservation (found by #88's own land run)
**Date:** 2026-08-12
**Branch:** land-88 (SHA lands with the PR)

**What was done.** `land-helpers.py clear_reservation` matched the id with `re.search` over every line, so striking a shipped `FB-XXXX` removed **every** line mentioning it — including the audit-trail entries in the second half of `reserved-feedback-numbers.md`. Anchored the predicate to a bullet that *opens* with the id (bold optional). Pinned by a new `cr 2b` case asserting both directions: the reservation goes, an audit-trail line citing the same id survives.

**Why.** Caught by dogfooding, not review: running `/flow:land 88` deleted the reservation **and three collision-history entries** — the record of why this PR was renumbered five times (FB-0074 → 0075 → 0078 → 0080 → 0082). That file's second half is institutional memory whose whole purpose is to stop the next collision; silently erasing it while "cleaning up" is worse than leaving a stale reservation. Restored from git and re-cleared with the narrow predicate.

**Design decision.** The anchor is the bullet opening, not a section-heading parse. Reservation bullets open with the id; audit-trail bullets open with a date (`- **2026-08-11** — …`), so the two are separable without teaching the helper the file's structure — which would couple it to a layout projects are free to vary. Bold is optional because real files use `- **FB-0082** —` while the eval fixture uses `- FB-0013 (PR P)`; requiring bold broke `cr 1`/`cr 2` and was caught immediately.

**Tradeoff.** Fixing a helper inside a `docs: land` PR mixes concerns. Accepted because the bug corrupted this very run and would silently corrupt every future land that clears a number cited in the audit trail — leaving it to a follow-up would mean shipping a known data-loss path. The change is 4 lines plus a regression case.
