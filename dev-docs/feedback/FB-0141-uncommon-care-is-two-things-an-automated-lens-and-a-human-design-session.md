# FB-0141 — Uncommon care is two things: an automated lens, and a design session the human is in

**Date:** 2026-11-01
**Source:** user direction — Ben, in the session that inventoried the uncommon-care / push-further permutations
**Status:** shaping the centralization plan (plan gate)
**Applies to:** `plugins/flow/agents/lens-push-further.md`, `lens-experience.md` Lens B, the new
interactive design-session skill, and every consumer repo carrying its own `uncommon-care` copy

## Synthesized rule

Uncommon care ships as two surfaces: an **unattended review lens** that stays general enough for any
surface, may find nothing, and never asks; and an **interactive design session** about interactions,
which owns Puckett's 8 lenses and in which the agent generates and evaluates but the human makes
every taste call. The lens consults the 8 lenses only when the surface is an interaction. Never
collapse the session into a longer automated critique, and never bind the lens to the eight.
A **quick mode** inside the session skill is welcome (refined 2026-11-03), as long as it is an
addition and not a replacement: it recommends, never decides or applies, and ends by handing
control back to the human.

## What was said

> "i think i want to have two versions of this concept. one should be a review lens, which can live
> in flow like it already does. the other should be a skill that facilitates an interactive design
> session for exploring interactions and evaluating them according to puckett's approach and pushing
> them further. it's not an automated process but one in which the human user is involved"

## Context

An inventory found seven definitions of Josh Puckett's "uncommon care" across nine repos, in two
shapes: the automated `lens-push-further` reviewer (flow, plus a pre-flow inline copy in md-manager)
and a standalone 8-lens `/uncommon-care` critique skill (ui-playground, todolist, mini-design-system,
designer). The proposed fix was one doctrine with the standalone skill re-homed in flow as a deeper
*automated* critique.

## Why this changes the design rather than just the location

The standalone copies are all one-shot: the agent reads the surface, walks eight lenses, and emits a
critique with a Top 3. Re-homing that unchanged would have produced a longer version of the lens —
the same automated judgment, more of it. Ben's distinction is about **who holds the taste call**:

- The **lens** is restraint-first and unattended. It may return "Nothing to push", and its output
  routes to inline fixes / roadmap / § Exploration without anyone in the room.
- The **session** is a collaboration. Exploring an interaction means generating range the human can
  actually touch, and the human — not the agent — picks which direction is worth taking to depth.
  An agent that picks the winner and reports it has turned the session back into the lens.

## How to apply

- Keep the two surfaces distinct in purpose, not just in length: the lens never asks; the session
  never decides on the human's behalf.
- **The 8 lenses belong to the session, not the review lens.** Refined in the same conversation:
  > "i don't know if the review lens necessarily needs to be tied to the exact 8 lenses in a rigid
  > way - i want it to be generalizable enough that it works across a range of applications, not
  > just deep interactions like what puckett was talking about … the skill/design session is
  > intentionally about interactions so the 8 lenses apply more readily here"

  Puckett's lenses are interaction-shaped (fidgetability, morphing, materiality); the review lens
  runs over every diff flow reviews — CLIs, docs, pipelines, data views. Binding it to the eight
  would make it wrong on most of its inputs. So the lens keeps its general "could this go further?"
  questions and *consults* the 8 lenses only when the surface under review is an interaction. One
  copy of the lens definitions, owned by the session skill; nothing to keep in sync.
- **An absent quality the surface doesn't call for is not a finding, and the lens never holds up a
  PR.** Ben's example: "i dont want a regular feature to get held up in staff review because it
  doesn't have fidgetability - not every single thing in an app can have that." Today this holds
  only structurally — the lens has no BLOCKER bucket — and is stated nowhere; make it explicit in
  the lens and pin it so a future edit cannot quietly give the lens a blocking verdict.
- The session is exploratory and cheap, like `/flow:prototype`'s iteration phase: no ship pipeline,
  no evals, no commits of product code.
- **The session must not require flow.** Ben, on why ui-playground — the most active home of the
  standalone skill — has no flow config: "these projects are meant for quicker interactive
  prototyping and iteration; I don't want to spend so much time or tokens building everything
  perfectly because that isn't the point. We're not making production code in ui-playground; we're
  incubating ideas." Enabling the flow plugin there would bring its model-invoked workflow rules
  (plan-before-code, confidence verdicts) into exactly the place they cost most and earn least. So
  the session cannot live where using it means adopting flow, and its own process must stay
  incubation-weight: throwaway sketches, short turns, no setup.
- **A quick review belongs in deep-dives too, beside the session, not instead of it.** Ben, after
  comparing ui-playground's one-pass `/uncommon-care` with the deep-dives session: "we're still
  forming the shape of deep dives, but i think the lighter weight shape mode would make sense. i want
  to leave room for back and forth and control and interactivity, but sometimes a quick review is
  nice." So `/deep-dives:puckett-uncommon-care quick` gives one read through the lenses that fit, a
  Top 3, and a question back: apply, sketch one, or go deeper. The full session stays the default.
  ui-playground keeps its own copy for now; Ben will decide whether to switch once the quick mode is
  in use.
