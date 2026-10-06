# FB-0134 — Git state cannot tell a parked worker from a dead one, and the rule I shipped resolved the ambiguity toward the reassuring answer

- **Date:** 2026-10-04
- **Source type:** user correction (Ben), during the merge-gate review of the worker-label PR.

- **What was said:** *"One correction to #3 before you declare it, because as drafted it hides
  exactly the failure SILENT exists for. 'Branch exists, no open PR, latest commit starts with
  `plan:` → parked at a gate' is the field-manual rule for *chasing*, and git can't tell parked
  from dead. This week's costliest case was precisely that shape: Track B had pushed `plan:`
  commits and then died on the session limit, idle for two days. Under your rule it reads
  **parked, fine**, the cheap-looking answer you yourself warned about. The discriminator lives
  in the transcript, not git: a worker whose last assistant message is a session-limit kill
  (`You've hit your session limit · resets …`) is SILENT regardless of git state."*

- **What I had done.** `/flow:orchestrate` §8's digest needed to classify workers it had heard
  nothing from, so I lifted `orchestrator-field-manual.md` § 8's branch/PR/`plan:`-subject test —
  a rule that doc states for deciding **whether to chase a quiet worker**. I used it as a
  **liveness classifier**. I even wrote, in the same section, that `GATE` "is the reassuring
  answer and defaulting to it is how the asymmetry bites" — and then shipped a rule that defaults
  to it on the exact measured case.

- **Why the error is instructive rather than careless.** I reasoned about the rule's *mechanics*
  (is it decidable? is it deterministic? does it carry both branches?) and never about its
  **domain**. A test can be perfectly mechanical, carry both halves, pass its own eval, and still
  be answering a different question than the one asked of it. Chasing and liveness are different
  questions over the same evidence, and git state is sufficient for the first and
  **under-determined** for the second: a worker that pushed `plan:` commits and then died has a
  byte-identical git signature to one parked at a gate. No amount of rigor applied to the wrong
  predicate recovers the missing bit.

- **Synthesized rule:** **when you reuse a rule from another document, check what question it was
  written to answer, not just whether it is well-formed.** A borrowed predicate inherits its
  original domain, and the citation makes it look sourced. Ask: *does the evidence this rule reads
  actually determine the thing I am now using it to decide?* If two states the rule must separate
  can produce identical evidence, the rule cannot separate them, and the missing discriminator is
  somewhere else — here, in the transcript rather than in git.

- **And resolve under-determination toward the ALARMING answer, never the reassuring one.** The
  asymmetry is the whole point: reading a plan you did not need to read costs minutes; reading a
  dead worker as parked costs days, silently. So an unreadable transcript must render *"parked or
  dead — can't tell"* rather than "parked". "I could not look" and "I looked and it is fine" must
  never render identically — the same distinction this repo already treats as load-bearing in
  `/flow:audit-coverage`'s skip line and in the digest's own zero-worker state.

- **How to apply:** before reusing a rule across documents, state the question it answers and the
  question you need answered, in one sentence each, and compare them. Where they differ, find the
  evidence that closes the gap before shipping the rule. Related: [[FB-0130]] (a decision that
  must survive a rotation goes in git), and `.claude/rules/general.md` § Consistency item 4 — a
  classifier that cannot distinguish two states is a measurement that can only return one of them.
