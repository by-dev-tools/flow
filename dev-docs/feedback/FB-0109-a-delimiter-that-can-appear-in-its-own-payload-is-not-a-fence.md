# FB-0109 — A delimiter that can appear in its own payload is not a fence

- **Date:** 2026-09-13
- **Source type:** adversarial finding (P5, from the FB-0108 payload suite) + orchestrator verification

- **What happened:** `/flow:ship`'s NOT-READY manifest is delimited by an HTML-comment fence, and
  `extract_manifest_region` found the closing fence with
  `text.split(MANIFEST_CLOSE, 1)[0]` — everything up to the **first** closing marker anywhere in the
  text. A manifest *entry* whose finding text contained that marker therefore ended the region at
  itself, and every entry after it disappeared from the parse. Measured on `main`: a body carrying
  one marker-bearing entry followed by a real `[verify-build]` blocker parsed with the verify-build
  blocker **absent**, verdict `DECIDE` → `READY`. A PR with a failed behavioural gate reads as
  merge-ready.

- **Synthesized rule:** **A delimiter that can legally appear inside its own payload is not a
  delimiter — it is a suggestion.** This is the same defect as
  [#148](https://github.com/by-dev-tools/flow/pull/148)'s heredoc (`FLOWEOF` appearing in the text it
  was bounding) and the same reason FB-0108 refused every sentinel design. It recurred here because
  the *fence* was never re-examined when the *argument* was: the finding text stopped going through a
  shell, and went on going into a text-delimited region unchanged.

  The fix is to make the boundary something the payload structurally cannot produce. Here that is
  **line anchoring** — the emitter writes each fence alone on its own line, so a marker quoted
  mid-prose is inert. It is cheap precisely because the producer already had the property; nothing
  was reading it.

  Three things worth separating, because they generalize past this bug:

  1. **A boundary claim is only as narrow as the API you used to compute it.** The first version of
     this fix used `str.splitlines()` and asserted — in the docstring, the changelog, the FB entry
     and the plan — that a newline was the **only** remaining residual. A staff-engineer review
     refuted it by measurement: `splitlines()` breaks on eight further code points, and all eight
     still erased the blocker. The sibling detector `pr-coherence.py` already split on `\n`; the fix
     had diverged from an in-repo precedent that was correct.

     Note the shape of the error, because it is the interesting part. The claim was not sloppy —
     it named a specific residual and routed it to a specific owner. It was *stated from reading
     the code rather than from running it*, which is the exact failure FB-0108 exists to name, made
     by the fix written to close FB-0108's sibling. "Only X remains" is a measurement, never a
     reading.
  2. **Degrade toward the gate, not past it.** If the fences are not found line-anchored, the parser
     now returns the whole text, so it sees *more* candidate entries, never fewer. A merge gate that
     fails open is worse than one that fails noisy.
  3. **Reachability claims need the same rigor as the bug.** The first framing of this — including
     the orchestrator's escalation — said the payload was "already committed, no attacker required",
     on the strength of `dev-docs/roadmap.md` carrying the literal marker. Measured, that is wrong:
     `[status-surface]` findings quote from *scanned candidates* (`CLAUDE.md`, `AGENTS.md`,
     `README.md`, `GEMINI.md`, `.cursorrules`, `.github/copilot-instructions.md`) and none carries
     the marker; `roadmap.md` is the reference the scan compares against. The accurate statement is
     **a latent self-trigger, one docs commit from live** — `README.md` already discusses the
     manifest. Stronger than "crafted payload", weaker than "reachable now", and the distinction was
     only found by someone re-running the check instead of repeating the sentence.

  4. **Count the tokens before claiming the class.** This entry's first two revisions each named
     a residual too narrowly, and a third token was found later by someone else: `has_manifest()`
     substring-matches BOTH the fence marker and the `🚫 NOT READY TO MERGE` heading, unanchored.
     Its failure direction is inverted — a body that merely *mentions* the sentinel wedges a clean
     ship rather than passing a dirty one — which is probably why it stayed invisible while three
     passes hunted bypasses. **When a mechanism has N structural tokens, enumerate all N before
     writing "the residual is X."** Here N turned out to be **4**, and this sentence itself first
     shipped saying 3 — the rule's own count was wrong in the revision that introduced the rule,
     which is as clean a demonstration as it is likely to get. The four: the two fences, the
     `🚫 NOT READY TO MERGE` heading, and — sharpest — **`_LINE_RE`'s field separators**.

     The fourth is the one that matters most and was found last. `classify()` derives an entry's
     class from its `needs` verb (`manifest-triage.py:569`, `_class_for(kind, e.get("needs"))`)
     and derives `waivable` from that class (`:584`). So forging a separator inside free text
     rewrites both: `--needs reconcile` forges class **auto** — the one class that triggers a
     silent re-run → commit → push — and `--kind security --needs "secret rotation"` moves a
     leaked-secret item from **blocked/not-waivable** to **ask/waivable**, one-word-waivable from
     bytes the attacker supplied.

     **Why three passes missed it is the transferable part:** it was dismissed as LOW on a
     measurement of the *adjacent* field. The reasoning "`classify()` keys on `kind`, not on the
     parsed `confidence`" is true and irrelevant — the load-bearing field is `needs`, and nobody
     tested it. Twice on this work a severity call was wrong for exactly that reason. **Measuring
     the field next to the load-bearing one produces a confident, wrong, and cheap-to-believe
     answer.**

- **Applies to:** `plugins/flow/skills/ship/lib/manifest_contract.py` (fixed here);
  `pr-coherence.py::has_manifest`'s unanchored match on the third token (owned by the FB-0108
  branch, write-side defang); FB-0108's
  write-time half; any future machine-readable region flow delimits in human-editable text — the
  question to ask at design time is "can the payload spell my delimiter?", and if yes the answer is
  an anchor, not a longer delimiter.
