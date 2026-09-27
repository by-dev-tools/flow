# FB-0124 — A mechanism claim has layers, and each one looks like the guarantee beneath it

**What was said (2026-09-27):** at the S0 human gate, choosing option (c), the orchestrator named the
pattern rather than just the bug: *"We asserted **registration** and meant **activation**; the hook would
assert **delivery** and still not be **compliance**. Each layer looks like the guarantee from one layer
down."*

**Synthesized rule:** when claiming a mechanism works, **name which layer you verified and which layer you
are claiming** — they are routinely different, and the resemblance between adjacent layers is what makes
the substitution feel safe. For a context-injection mechanism the ladder is:

| Layer | Question | How it is verified | What it does NOT establish |
|---|---|---|---|
| **Registration** | Does the runtime know the component exists? | `claude plugin details` lists the name | that anything ever loads it |
| **Activation** | Did the body reach a session's context? | a `Skill` tool_use in a transcript, or a body-only sentinel recalled | that it reached context *because of* the thing you changed |
| **Delivery** | Does it reach context every time, deterministically? | a `SessionStart` hook whose stdout is added to context | that the model then follows it |
| **Compliance** | Did behaviour change? | the behaviour, measured | — (the only layer that is the actual goal) |

`/flow:doctor` Check 3.2 verified **registration** and printed a claim about **activation** — and stayed
green for twenty releases over a feature that had never fired. The proposed `SessionStart` hook would
verify **delivery** and is documented as *"context, not enforced configuration"* — so it would not
establish **compliance** either. Three layers, same shape of error available at each.

**How to apply:**

- In any check's output, state the layer it actually observed. `[PASS] … REGISTERED with the loader` is a
  true narrow claim; `[PASS] … auto-load on path matches` was a false broad one from the same evidence.
- When a layer is genuinely unobservable from where you stand, say so **in the check's own output** with
  the mechanism that would make it observable — `[UNCHECKED] … Checkable by: …`. Never `[PASS]`, and never
  `[WARN]` (see [[FB-0121]]: unchecked is epistemically different, not merely milder). The
  `Checkable by:` clause is the line's own deletion criterion.
- Keep `[UNCHECKED]` **outside** the verdict arithmetic and print the count inline (`[READY] (2
  unchecked)`). Routing it to `[WARN]` puts every consumer permanently below `[READY]` over an item nobody
  can clear, which then argues for retiring `[READY]` — and burying it entirely loses the signal. Both
  properties, not one.
- **Distinguish "the mechanism is inert" from "I never exercised it."** S0's own diagnosis got this wrong
  twice over: E1 concluded `paths:` does not activate a skill, but every probe carried a restrictive glob
  *and* a suppressive description, so the cause was never isolated — and the probes only ever *read a
  file*, never ran a task the rule was for, so the model-invocation path was never exercised at all. The
  measured fact ("these never loaded") was solid; the mechanism attribution built on top of it was not.
  See [[FB-0112]] — validate the instrument on a known positive — and note the sharper variant here:
  **an instrument can be valid and still be pointed at the wrong mechanism.**
- **Segment a measurement by turn when the measurement asks about itself.** This rig's first result showed
  all three arms firing, including the control arm expected to return zero. The cause was the scorer
  counting the whole session: turn 2 *asks* which rules were consulted, and a model can satisfy that by
  invoking one right then. That measures "can a model invoke a skill when asked about it" — trivially yes.
  Only the turn before the question is attributable to the treatment.

**Related:** [[FB-0121]] (a gate reporting nothing found must say whether that meant nothing-wrong or
could-not-see), [[FB-0112]] (validate the instrument on a known positive), [[FB-0118]] (pin a claim at the
layer where it is claimed), [[FB-0085]] (the original never-loading-feature class), [[FB-0077]] (a
prohibition satisfiable by deletion is not a check).
