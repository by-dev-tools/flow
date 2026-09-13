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

  1. **Two layers, and each must state what it cannot reach.** Line anchoring closes the mid-line
     case. It does **not** close a finding embedding a newline followed by a bare marker — that is
     closed at write time by FB-0108's newline collapse. Neither layer is a seal; the PR says so
     rather than implying otherwise, because "the class is closed" is the claim that stops the next
     person looking.
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

- **Applies to:** `plugins/flow/skills/ship/lib/manifest_contract.py` (fixed here); FB-0108's
  write-time half; any future machine-readable region flow delimits in human-editable text — the
  question to ask at design time is "can the payload spell my delimiter?", and if yes the answer is
  an anchor, not a longer delimiter.
