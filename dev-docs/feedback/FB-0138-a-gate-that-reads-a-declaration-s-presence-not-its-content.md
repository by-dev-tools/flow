---
name: fb-0138-presence-not-content
description: A gate that reads a declaration's PRESENCE rather than its CONTENT inverts the incentive to be explicit
metadata:
  type: feedback
---

# FB-0138 — A gate that reads a declaration's PRESENCE, not its CONTENT, punishes being explicit

> **Renumbered from FB-0132 on 2026-10-09.** [#179](https://github.com/by-dev-tools/flow/pull/179)
> merged its own `FB-0132` (*"a label identifies a sender only if it is unique"*) on 2026-10-06,
> before this branch landed. Both files used the number with **different slugs**, so the filenames
> differed and git reported **no conflict** — the two entries simply coexisted after the rebase.
> That is the gap in "pushing the file IS the claim": the claim is only collision-*proof* when two
> authors pick the same slug. Theirs merged first, so this one moved. **This branch's commit
> messages predate the renumber and still say FB-0132** — they are left as written rather than
> rewritten, since the history is accurate about what was believed at the time.

**Date:** 2026-10-04 · **Source:** Ben, via the orchestrator seat · **Shipped:** v1.62.0

## What happened

`visual-significance.py` decided a change was visually significant if a `Visual-walk` block was
*present* — `block_count >= 1` — and never read what the block said. So an author writing
`**Visual-walk:** N/A — no UI in this change` to be helpful set `visual_significant: true`, and
`/flow:ship` §7a then demanded a rendered walkthrough and a visual-history entry for a diff with no
UI: artifacts that cannot be produced. **Omitting the block entirely gave the correct verdict.**

The predicate rewarded careless authoring and punished careful authoring.

## The rule

**A gate that keys on a declaration's PRESENCE rather than its CONTENT can be satisfied by an explicit
denial of the very thing it is checking for.** Whenever a predicate asks "is there a declaration?",
ask the next question: *could that declaration say the opposite of what its presence implies?* If it
could, the predicate is inverted for the most conscientious authors — the ones who bothered to write
it down.

This is a sibling of `.claude/rules/general.md` § Consistency item 3 (a prohibition satisfiable by
deletion) with the polarity flipped: there, *removing* a thing passes the check; here, *adding* an
explicit negation passes it.

## How to apply

- **When a gate reads a marker, section, heading, or file for its existence, check whether the
  contents can contradict the inference.** Grep for `block_count`, `is not None`, `exists()`,
  `len(...) > 0` on anything an author writes prose into.
- **Prefer a declared value to an inferred one** — but a *natural-language* denial the author already
  writes is a legitimate declaration, and reading it beats inventing a second field nobody will use.
  Gate the reading behind the structural condition (here, zero assertions) so a miss fails safe.
- **"Fails safe" needs its polarity named, not asserted.** I argued the N/A match fails safe because a
  *miss* keeps forcing — true, and it says nothing about a *false match*, which suppresses. A
  false-positive in a suppression predicate is the dangerous direction, and my first two guards both
  had one. State which direction is safe and then check the other one.
- **A denial that defers or redirects is not a denial.** `None, will fill in later` says *when*;
  `N/A, see the prototype for frames` says *elsewhere*. Both assert the thing exists. The
  discrimination is not in the punctuation — the first two guards tried to spell the separator set
  correctly and both failed — it is in whether the sentence un-denies itself.

## The part that generalises past this bug

**An accept/reject table pins the shapes its author happened to think of, not the class.** My table
had 22 rows and still let five deferral spellings through, because I had written down the three I
imagined and treated the boundary as the mechanism. The table is necessary and it is not evidence of
coverage. What found the rest was a reviewer asked specifically to *find a shape the table misses* —
which is a different instruction from "review this", and the one worth giving.

**And publish the convention you are enforcing.** `plan-discipline` told authors Visual-walk was "N/A
under `tiny`" and never said what to write, so the token set existed only because this repo's authors
happened to write the same way. Authors were being matched against an unpublished convention. A parser
contract that lives only in the parser is a trap with extra steps.

Related: [[FB-0131]] (same session; instruments that can only return one answer), and the
`skip-audit-checks.py` Spec-walk instance of this same shape, filed in `dev-docs/roadmap.md` § Next
rather than fixed here.
