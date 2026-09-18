# FB-0112 — A measurement that can only return "clean" is not a measurement: validate the instrument on a known positive

- **Date:** 2026-09-18
- **Source type:** user correction (orchestrator seat, self-reported)
- **What was said:** The orchestrator found that a queue-conflict recipe it had written and shipped
  in `research/orchestrator-field-manual.md` § 7 could never report a conflict:

  ```sh
  git merge-tree $(git merge-base $HA $HB) $HA $HB | grep -c '^<<<<<<<'   # 0 = clean
  ```

  Old-form `merge-tree` emits **diff-prefixed** markers — `+<<<<<<<`, not `<<<<<<<` at column 0 —
  so a column-anchored grep matches nothing for every input and the count is always `0 = clean`.

## The incident, and the part that made it stick

The recipe was written from memory and then *validated* — on [#153](https://github.com/by-dev-tools/flow/pull/153) × [#154](https://github.com/by-dev-tools/flow/pull/154), which returned `0`. **Those two PRs were genuinely disjoint, so `0` was the right answer for the wrong reason**, and that false confirmation is precisely what gave the recipe enough confidence to be codified into a shipped doc. It survived until it reported "clean" for [#156](https://github.com/by-dev-tools/flow/pull/156) × [#157](https://github.com/by-dev-tools/flow/pull/157), which conflict in three files (`.claude-plugin/marketplace.json`, `dev-docs/plan.md`, `plugins/flow/.claude-plugin/plugin.json`).

Note where it landed: inside the tool built to answer the queueing question, in the section whose own heading says **measure, never predict**.

## Synthesized rule

**Before trusting an instrument's negative result, run it against a case you KNOW is positive.**
Validating a detector only on inputs where it should stay quiet cannot distinguish a working
detector from a broken one — *both hypotheses predict the same output*. A clean result from an
unvalidated instrument is not evidence of cleanliness; it is evidence of nothing.

This applies to **anything whose output you will act on** — a grep, a merge simulation, a mutation
run, a corpus load, a file-presence probe — not only to assertions that ship in a repo.

**Corollary — prefer a tool's own exit code over a grep of its output.** `grep -c` returning `0`
is ambiguous between "no matches" and "my pattern is wrong"; an exit code is a signal the tool's
author designed and maintains against their own output format. This is the stronger defense
because it *removes* the judgment call rather than adding one more thing to remember. The corrected
recipe is `git merge-tree --write-tree --name-only "$HA" "$HB"`, read by exit status (0 clean,
1 conflicts) — and it names the conflicting files as a bonus.

## Why the existing rules did not catch it — the gap is scope, not content

[[FB-0104]] ("a checker's own eval fixtures must exercise every branch") and
`.claude/rules/general.md` § Consistency item 3 ("prohibition satisfiable by deletion") both
describe this shape accurately. Both are written about **artifacts that ship**. A shell one-liner
inside a docs recipe did not register as "a check" — it was a *tool used*, not a *check shipped* —
so neither rule was consulted. Item 4 exists to close that scope gap, and deliberately says
"anything whose output you will act on."

**Item 3 and item 4 are siblings, not duplicates**, and the distinction is worth keeping: item 3
is about the *logical shape of an assertion* (a negative-only assertion passes in two opposite
worlds — contract honored, or contract deleted); item 4 is about *instrument validation* (the
detector was never exercised on a positive). A broken grep is not satisfiable-by-deletion — nothing
was deleted, the detector was simply incapable — and a negative-only assertion can be a perfectly
functional instrument and still be satisfiable by deletion. They share a symptom (unearned green)
and need **different defenses**: pair with a positive assertion, versus run against a known
positive.

## The family this belongs to

This is the **fifth instance in one week** of one shape: *a measurement returns a clean-looking
result because the instrument is broken, and the clean result is read as evidence.*

1. Mutation testing scoring "survived" when the mutation was never applied (5× in one session).
2. A SyntaxError mutant scoring zero test failures — the suite could not even import it.
3. `strings` returning zero hits on a packed binary, read as "no secrets present."
4. A reviewer whose corpus silently failed to load returning well-formed findings ([[FB-0110]]'s
   second corollary — the sibling entry, and the closest in spirit: there too, nothing in the
   output marked the boundary).
5. This recipe.

**Name the family: silently-broken instrument, confidently-shaped output.** Its signature is that
the failure is invisible *from the output alone* — which is exactly why the defense has to be
applied at the instrument, before the output is read, rather than by inspecting results afterward.

- **Applies to:** `.claude/rules/general.md` § Consistency discipline item 4 (new);
  `research/orchestrator-field-manual.md` § 7 (the corrected recipe + a note recording why the old
  line was wrong, so it is not "simplified" back). Related: [[FB-0104]] and item 3 as the
  near-misses whose scope did not reach it, and [[FB-0110]] as the sibling instance.
