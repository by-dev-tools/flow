# FB-0115 — A reviewer with perfect precision and variable recall needs a *wider* stage one, not a better filter

- **Date:** 2026-09-26
- **Source type:** user correction + direction (Ben, dispatching the audit-coverage recall work)
- **What was said:** *"those gaps are huge; not really acceptable for an autonomous system that we're
  trusting."* And, on how to fix it: *"No overbuilding, no bloat, no new machinery we do not need."*

## The measurement behind it

`/flow:audit-coverage` across five live runs with known ground truth: **10 · 5 · 0-of-5 · 0-of-6 ·
2-of-5** found. **Precision unblemished in all five** — it has never once reported a gap that was not
real. Recall is the entire problem, and it is *variable* (0–100%) rather than uniformly low, which is a
different and worse failure shape: a variable-recall gate returns "no undeclared changes" over real gaps
and reads identically to a thorough pass.

## Synthesized rule

**Diagnose which half is broken before importing a fix.** The published practitioner pattern for
LLM code review — split recall and precision into two passes, the second one filtering — was written
for a tool with a **false-positive** problem. Ours is the mirror image: the filter is already
effectively perfect. Copying their second pass would add machinery to solve a problem we do not have,
while leaving the actual one untouched.

So when a reviewer has high precision and low recall:

1. **The lever is widening stage one** — separate *enumeration* from *matching*, and scope the
   precision-tuned suppression rules to the matching half only. On a single-pass reviewer, those rules
   ("default to covered", "do not invent findings to appear thorough", "a reviewer prompted to find gaps
   will usually report some") are applied to enumeration too, where they are pure recall loss.
2. **Perfect precision is what licenses unioning across runs.** Run-to-run variance stops being a defect
   and becomes a resource: a union can only add true positives if the filter never admits a false one.
   Without measured precision, union is just noise amplification — so the licence is the *measurement*,
   not the technique.
3. **An invisible stage cannot be audited.** If the enumeration is never written down, a run that
   enumerated 6 of 11 behaviours emits a clean result indistinguishable from a thorough one. Emit the
   enumeration. Same doctrine as [[FB-0112]], one step earlier in the pipeline.
4. **Compute what is derivable; do not ask the model for it.** Which hunks changed, and which of them
   landed in commits *after* the plan was last written, are both `git` questions. The model can suggest;
   it should never define.

**And the constraint that outranks all four:** a fix for a recall problem that *adds* a reviewer, an
agent, a skill or a config slot is almost certainly the wrong turn. The correct shape here is
**subtractive** — splitting one overloaded prompt into two labelled halves is a simplification, and the
practitioner report says so explicitly: they found the split *simpler* than the single complex prompt,
not more complex.

## How to apply

- Before tuning a reviewer, get its precision and recall separately. "It misses things" and "it
  invents things" take opposite fixes, and a single quality score hides which one you have.
- When a reviewer's output is a filtered list, name the unfiltered list in the output too, so a clean
  result is falsifiable by the one person who knows what was actually in the change.
- Ship a prompt change only against measured before/after on cases with real ground truth. A change that
  does not move the number is dropped, not shipped on plausibility — and the harness that produces the
  number gets [[FB-0112]]'s known-positive validation before any of its numbers are believed.
