# FB-0132 — A sender label identifies a sender only if it is unique, and the seat that designed it broke it first

- **Date:** 2026-10-04
- **Source type:** user correction (Ben), at the orchestrator seat, delivered inside the approval
  of the plan that *created* the convention being violated.

- **What was said:** *"Fix your own label: you've been sending `[w:mobile]`, which is the research
  worker's name. Two workers on one label defeats the point. Yours is `[w:status]`. Since a name
  collision just happened, make sure the convention text says short-names must be unique across
  live workers."*

- **What actually happened.** This seat spent a planning pass designing a message-label convention
  whose entire stated purpose is *"so the sender and the reason are readable without parsing a
  sentence"* — and sent that plan under a short-name already held by a live worker. The plan was
  simultaneously the argument for the convention and a counterexample to it. Ben had to
  disambiguate two senders by content, which is the exact cost the label exists to remove.

- **Why the omission was structural, not careless.** The plan derived the label's *shape* from how
  it would be read (sender first so it survives truncation; a bracket so it reads as metadata) and
  derived the *status set* from the three ping triggers it had to cover. Both derivations are about
  one message in isolation. Uniqueness is the only property of the convention that is invisible
  from inside a single message — it is a property of the **set** of live senders, and a seat
  reasoning about message design never has the set in view. So the gap was not "forgot a line": it
  was reasoning at the wrong scope and never being forced up a level.

- **Synthesized rule:** **when you design an identifier, specify its uniqueness scope in the same
  breath as its format.** A format rule tells a sender how to spell the label; a scope rule tells
  the system whether the label means anything. Shipping the first without the second produces a
  convention that looks complete, passes any per-message check you write, and still fails to
  identify anyone. Ask: *across what set must this value be distinct, and who checks?* If the
  answer is "nobody checks", say so in the text rather than leaving it implied.

- **The second-order lesson, which is the more useful one.** This seat was the convention's author
  and its first violator **in the same artifact**. Authoring a rule confers no compliance with it,
  and self-review at the moment of authorship is the weakest possible check, because the author is
  the one person who cannot see the assumption they are making. Prefer a mechanical check at the
  point of use (`/flow:spawn` §3 now tells the seat to check the name against its own
  live-worker listing *before* writing the brief) over a resolution to remember.

- **How to apply:** when writing or reviewing any naming convention — worker short-names, feedback
  ids, version numbers, doc slugs, branch names — state the uniqueness scope and name the sweep
  that enforces it. This repo already serializes three contested values this way (version numbers,
  FB ids, the ship slot) and every one of them has a documented "re-sweep main **and** open
  branches" rule; a worker short-name is the fourth contested value and had none. Related:
  [[FB-0010]] (consistency that depends on author memory), and `.claude/rules/general.md`
  § Consistency item 4 — a convention nothing exercises against a known-positive collision cannot
  be distinguished from one that works.
