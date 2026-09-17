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
     still erased the blocker.

     The *correction* then shipped its own reading. It said the sibling detector
     `pr-coherence.py` "already split on `\n`", so the fix had diverged from a correct in-repo
     precedent. Measured, that module is **mixed**: one `split("\n")` site and two
     `splitlines()` sites. A generalization drawn from one of three call sites, inside the very
     entry whose headline rule forbids exactly that. Two readings, one paragraph apart.

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

  5. **The same hazard at two layers can want OPPOSITE fixes, and "be consistent" is the
     trap.** After the fence scan was fixed to `split("\n")`, the consumer six lines downstream
     (`parse_entries`) was changed to match it — consistency, and backwards. The fence scan
     wants the NARROWEST line definition, because the fewer things count as a fence the wider
     the region and the more entries survive. The entry parser wants the WIDEST, because the
     fewer things count as a line the fewer blockers it finds. Measured, each single split
     erases a live `[verify-build]` blocker in the shape the other one handles:
     `splitlines()` alone fragments an entry whose own text carries one of the eight code
     points; `split("\n")` alone lets two entries *joined* by one of them be read as a single
     line, where the first swallows the second **and absorbs its `needs` verb** — the field
     `classify()` derives class and waivability from. The answer was the union of both,
     deduped, which is a superset of each by construction rather than by test coverage.

     The generalizable form: **before copying a fix from one layer to its neighbour, ask which
     direction each layer fails in.** Two layers of one mechanism steering toward the same
     safety property ("more blockers, never fewer") can need opposite implementations of the
     same predicate. Uniformity looked like rigor and was the bug.

  6. **A cross-branch claim goes stale without an edit, and `git grep` cannot see it.** Four
     documents asserted "there is no write-time layer on this branch". FB-0108 merged as #152,
     this branch rebased onto it, and all four became false with no diff touching them. Nothing
     in the repo could detect it, because the contradiction spanned a branch boundary. Measured
     after the rebase: `add-entry` now collapses the newline and defangs the marker, so the
     residual is closed for text it writes and open only for bodies composed outside it.
     **At every rebase, re-verify the claims that named another branch as an owner** — they are
     the only assertions that can change truth value without a change to the file.

  7. **A mutation that does not compile is a silent pass.** Re-measuring this entry's own
     failure counts, the first harness applied mutations to a `.git`-less copy and produced a
     `SyntaxError` in one variant; the eval crashed before its summary line, and the harness
     scored it **zero failures** — indistinguishable from "the test suite tolerates the bug".
     Every mutant must be compiled before its count is believed.

  8. **A defense must match on the same grammar its consumer parses with.** The sharpest
     instance of this entry's own headline rule, found by `/flow:security-review` at ship on
     this very branch. The manifest line's field separators are defanged at write time so a
     finding quoting one cannot forge the field — but the defang matched three **literal**
     strings while `_LINE_RE` matches a **whitespace class** (`\s+—\s*needs:`). A TAB or an
     NBSP before the em dash therefore matched the parser and missed the defang.

     Measured: `--kind security --needs "secret rotation"` (an out-of-session verb ⇒ class
     `blocked`, **not waivable**) parsed as `needs='design decision'` ⇒ class `ask`,
     `waivable: True`, verdict BLOCKED → DECIDE. A leaked-secret item became
     one-word-waivable from bytes the finding supplied.

     Three things make this worth its own rule rather than a footnote to rule 4:

     a. **The existing test passed while the hole was open, because it used the safe shape.**
        `P22` already attacked the separator — with a single space, the one whitespace the
        literal caught. Two spaces were safe only *by accident*: the one-space literal is a
        substring of them. A payload suite that samples one whitespace shape of a class the
        parser accepts is testing the sample, not the class.
     b. **The roadmapped fix would not have closed it.** The queued `FIELD_SEPS` item proposes
        deriving the token *set* so a fifth token cannot drift. This gap was not a missing
        token — it was two matchers of **different shapes** over the same grammar, and
        compiling `_LINE_RE` from a literal tuple would have preserved the mismatch exactly.
        "We already have a roadmap item near this" is not the same as "this is covered."
     c. **It falsified a boundary claim written the same day**, in this same document's
        rule 6 spirit: the docstring had just been corrected to say the two layers "together
        cover the reachable paths, with one honest gap — a body that did NOT come through
        `add-entry`." A body that *did* come through `add-entry` was forgeable.

     **Generalized:** when a guard and its consumer both recognize the same construct, they
     must do it with the same matcher — share the pattern, not a literal drawn from it. A
     literal guarding a regex is not a guard; it is a sample of one. And the direction to
     widen in is the one that defangs more, never the one that matches less: narrowing the
     *parser* instead would drop entries, which is the unsafe direction.

- **Applies to:** `plugins/flow/skills/ship/lib/manifest_contract.py`,
  `manifest-triage.py::parse_entries`, and `manifest-triage.py::_defang_fences` (all fixed here);
  `pr-coherence.py::has_manifest`'s unanchored match on the third token (owned by the FB-0108
  branch, write-side defang); FB-0108's
  write-time half; any future machine-readable region flow delimits in human-editable text — the
  question to ask at design time is "can the payload spell my delimiter?", and if yes the answer is
  an anchor, not a longer delimiter.
