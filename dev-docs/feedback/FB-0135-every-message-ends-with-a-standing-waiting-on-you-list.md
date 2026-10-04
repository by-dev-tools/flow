# FB-0135 — Every orchestrator message ends with a standing "Waiting on you" list, and the watcher's label is `[watcher]`

- **Date:** 2026-10-04
- **Source type:** user preference, stated directly (Ben).

- **What was said:** *"End every orchestrator message to Ben with a short standing 'Waiting on
  you' list of the manual tests and decisions only he can do, kept even when the message is about
  something else, so worker and [watcher] messages can't push them out of view."* And: *"the
  watcher's label is '[watcher]'."*

- **Why it was asked for.** The orchestrator seat's product is the human's attention, and the
  failure this addresses is not verbosity — it is **accumulation**. An open manual test (something
  only Ben can run: a look at a rendered surface on his phone, a taste call, a merge) gets stated
  once, then buried under unrelated worker and watcher traffic. Nothing in the loop re-surfaces
  it, so it ages out of view while remaining open. That is the same attention cost § 1
  requirement 5 names, arriving by a different route.

- **Synthesized rule:** **a message ends with the standing list of what only the human can do.**
  Three parts, and the middle one is the one that gets dropped:
  1. **Short** — a list of open asks, not a status report.
  2. **Only what the human can do** — classify ships-or-paperwork first (§ 7); anything the seat
     could resolve itself does not belong on the list.
  3. **Kept even when the message is about something else** — the list is *standing*. A message
     reporting a worker's completion still carries it. This is the whole mechanism.

  Drop an item only when it is genuinely done, and say so when dropping it.

- **It lives in git, not in the seat's memory.** Recorded in
  `research/orchestrator-field-manual.md` § 3 with Ben's words quoted, because a durable
  preference held only in a seat's context dies at the next rotation or teardown — [[FB-0130]]
  exactly. A seat that "remembers" to append the list is one rotation away from not.

- **How to apply:** when composing any message to the human from an orchestrator seat, the last
  block is the standing list. `[watcher]` is the watcher's short-name within the
  `[w:<short-name>] <STATUS>` opener convention ([[FB-0132]]), so watcher traffic reads
  `[watcher] FYI` and stays greppable and distinguishable from worker messages.
