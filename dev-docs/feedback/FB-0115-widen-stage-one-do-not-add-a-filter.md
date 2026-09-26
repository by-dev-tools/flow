# FB-0115 — A reviewer with perfect precision and variable recall needs a *wider* stage one, not a better filter

- **Date:** 2026-09-26
- **Source type:** user correction + direction (Ben, dispatching the audit-coverage recall work)
- **What was said:** *"those gaps are huge; not really acceptable for an autonomous system that we're
  trusting."* And, on how to fix it: *"No overbuilding, no bloat, no new machinery we do not need."*

## The measurement behind it

`/flow:audit-coverage` was reported as five live runs — **10 · 5 · 0-of-5 · 0-of-6 · 2-of-5**.
**Two of those five numbers did not survive checking, and both corrections are part of the lesson:**

- `0-of-6` is the **same event** as `0-of-5`, described two ways and counted twice. Caught at the plan
  gate, minutes before shipping as "Across five live runs" into two files.
- the surviving `0-of-5` is a **file-filter** result, not a judgment one: all five of that PR's gaps were
  added in a `.md` file the behaviour diff excludes, so the reviewer was never shown the code. No prompt
  change could ever have moved it.

Honest series: **10-of-10 · 5-of-10 · 2-of-5** judgment recall, plus one structural miss. **Precision
unblemished in every run that produced findings** — it has never once reported a gap that was not real.
Recall is the entire problem, and it is *variable* rather than uniformly low, which is a different and
worse failure shape: a variable-recall gate returns "no undeclared changes" over real gaps and reads
identically to a thorough pass.

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

## Two corollaries the execution added

**A drop-rule that names only the headline metric will delete the wrong things.** The rule this work ran
under — *"if a change does not move recall, drop it"* — was good and was followed rather than argued with.
Applied literally it deleted a validated instrument whose value is **observability**: the deterministic
hunk inventory moved recall by 0 in diff mode *because it worked* — the enumerator found both missed
behaviours and the matcher dismissed them, relocating the bottleneck downstream. The headline number
cannot see that. So: before acting on a metric, check that the metric can see the thing you are changing.
Same error class as the rest of this entry, one level up — and the rule-setter is not exempt from it.

**A recall number is a floor when the key is not known to be exhaustive.** Two runs flagged a real gap
that the reference case's own documented list never carried. It was deliberately **not** added to the
key: fitting a key to the outputs it scores measures nothing. So both conditions under-credit equally,
and the honest claim is "at least 82%", which is stronger than the point estimate as well as truer.

## How to apply

- Before tuning a reviewer, get its precision and recall separately. "It misses things" and "it
  invents things" take opposite fixes, and a single quality score hides which one you have.
- When a reviewer's output is a filtered list, name the unfiltered list in the output too, so a clean
  result is falsifiable by the one person who knows what was actually in the change.
- Ship a prompt change only against measured before/after on cases with real ground truth. A change that
  does not move the number is dropped, not shipped on plausibility — and the harness that produces the
  number gets [[FB-0112]]'s known-positive validation before any of its numbers are believed.
