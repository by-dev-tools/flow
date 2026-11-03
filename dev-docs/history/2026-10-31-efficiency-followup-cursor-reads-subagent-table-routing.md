# Efficiency follow-up — cursor-based worker reads, a workspace-vs-subagent table, and routing by job fit

**Date:** 2026-10-31
**Branch:** `conductor/efficiency-follow-up-checking-subagents-routing`
**Version:** v1.66.0
**Feedback:** FB-0140 (capacity is not a routing reason)
**Scope:** `plugins/flow/lib/dispatch_backend.py` + its evals, `plugins/flow/skills/orchestrate/SKILL.md`,
`plugins/flow/skills/spawn/SKILL.md`, `research/orchestrator-field-manual.md` § 3.

## What was done

Executes three of `dev-docs/research/2026-10-efficiency-audit.md`'s findings against the follow-up
brief Ben filed the same day the audit merged (#181):

1. **`dispatch_backend.py` gains a sixth, optional verb, `readSince {session} {cursor}`** — messages
   since a cursor, not a full re-read. `KNOWN_PLACEHOLDERS` gains `cursor`; `VERBS`' per-verb tuple
   gains a 4th `optional` field, so `validate()` can report an absent `readSince` as `absent`
   without flipping `report["ok"]` to False, which every other (required) verb's absence still
   does. `/flow:orchestrate` step 4 states the contract explicitly, citing the audit's measured
   105,385-character transcript-polling finding and naming a concrete default query for the common
   no-backend case.
2. **`/flow:spawn` gains an unnumbered "Before Step 0: choose the primitive" section** — a
   workspace-vs-subagent table, plus the nuance that a subagent's output lands directly in the
   calling session's own context, so a long-lived seat should scope a subagent dispatch to a short,
   structured result rather than a broad explore-and-report.
3. **"Needs the account's capacity" is forbidden as a routing justification.** `/flow:spawn` step 2
   now names it explicitly, immediately after the existing "right-sizing, not rationing" paragraph;
   `research/orchestrator-field-manual.md` § 3 carries Ben's 2026-10-05 priority verbatim (FB-0140).

## Why

Ben, 2026-10-05: *"If I run out of usage I run out of usage, I just want to make sure that we're not
wasting the tokens we have. Lost time isn't a concern right now… If I do get a higher tier in the
future, flow should already be tuned to be as efficient as possible."* The audit had already found a
live dispatch brief informally rationing the shared rate-limit pool via a model downshift, with no
written rule against it anywhere — this closes that gap, plus the two measured process findings
(cursor-reads, workspace-vs-subagent) the same audit flagged as fixable without raising any ceiling.

## Design decisions

- **`readSince` is optional, not required.** Unlike every other verb in `dispatch_backend.py`'s closed
  vocabulary, a consumer with no cheap cursor primitive can leave it unconfigured without the adapter
  reporting itself broken. First shipped as a second, separately-maintained `OPTIONAL_VERBS` set
  cross-referenced by membership — `/simplify`'s reuse, simplification, and altitude lenses
  independently converged on the same finding (three of four lenses, unprompted) that this was the
  fan-out-contradiction class `general.md` names: two structures encoding the same fact, one of them
  invisible from the other. Fixed by folding `optional` into the existing per-verb tuple as a 4th
  field instead — one place to add a verb correctly, not two that can silently disagree.
- **The cursor-first read contract lives in `/flow:orchestrate` step 4 only, not duplicated into §8's
  digest.** §8 already says "run steps 2, 3 and 4, then stop" — it inherits step 4's rule by
  reference. The original plan drafted a second copy for §8; executing it found that would be the
  exact fan-out-contradiction class this repo's own `general.md` warns about (one contract, two
  places, no join). Caught during execution, not at plan time — recorded here since it's the kind of
  thing a future reader might otherwise "fix" by re-adding the duplicate.
- **No renumbering of `/flow:spawn`'s existing steps.** The orchestrator's ruling at the gate: other
  text (the #179 uniqueness rule, the field manual) cites the existing steps by number, and
  renumbering them to fit a new section in is the fan-out-contradiction class for no gain. The new
  section is titled "Before Step 0" and stays unnumbered.

## Tradeoffs discussed

- **`cursor` vs `since` as the placeholder name** — resolved by the orchestrator in favor of `cursor`
  ("opaque and accurate, and `since` implies a timestamp the backend may not have").
- **Subagent cost nuance vs. the audit's plain rule-of-thumb table** — the table alone would have let
  a future reader provision a broad, unscoped subagent as "correct" by the letter of the table while
  still relocating the audit's own Bash-output problem into the Agent tool. The prose nuance was kept
  deliberately alongside the table rather than folded into one of its rows, since it's a constraint on
  *how* to use the subagent primitive, not a *which-primitive* signal.

## Execution note — a second instance of the active-block-reorder hazard

Resuming after the orchestrator's merge-ping gap (#179 merged 2026-10-06; this branch resumed
2026-10-31) required a rebase onto five intervening PRs. The rebase itself conflicted in
`dev-docs/plan.md` (expected: shared-by-construction doc) but also produced a silent hazard: this
branch's own "Current Focus" block landed second in the file, not first, which `extract-criteria.py`
and the live `run_autoplan_evals.py` CI coupling (`dev-docs/roadmap.md` § "Three CI evals grade the
LIVE plan.md active block") would have graded against #184's already-merged criteria instead of this
branch's own — exactly the failure #179's own commit history separately documents hitting and fixing
for itself. Caught by running the extractor check the orchestrator specified, before any other gate
ran; fixed by moving this branch's block back to the top position. No plugin behavior changed as a
result — recorded here as a confirmed-again instance of a known hazard, not a new one.

## Lessons learned

- A plan document that's shared by construction (every PR appends to the same file) needs its
  "active block" position re-verified after every rebase, not just conflict-resolved. A clean,
  conflict-free rebase is not evidence the block order is still correct.
- "Add one paragraph to step 4 and to §8" in a plan is worth re-checking against what §8 actually
  says before executing it literally — §8's own text already delegates to step 4, and the plan's
  original phrasing would have introduced the exact duplication this repo's documentation discipline
  exists to prevent.
- **A number carried across a dispatch brief is not the same as a number in a committed document,
  and citing it as the latter is a fabricated citation waiting to be checked.** The dispatch brief's
  "reference point" ("573 messages in 6 API calls once, then 1 call / 0.6s per re-read") was written
  into `dispatch_backend.py`'s docstring and `/flow:orchestrate` step 4 attributed to
  `dev-docs/research/2026-10-efficiency-audit.md §3` — which does not contain that number, or
  "cursor" or "readSince," anywhere (confirmed by grep over the whole doc). `/simplify`'s
  altitude lens caught it on a direct source check, not on the strength of the number sounding
  plausible. Worse: the session that measured it was the earlier worker whose workspace was archived
  before it pushed anything, so the figure is now unverifiable at the source. Fixed by dropping it
  from every shipped artifact (lib docstring, skill prose, changelog) and keeping only the audit's
  own traceable figure (62 calls, 105,385 characters). `dev-docs/plan.md`'s own narrative text
  correctly distinguished "the dispatch's own reference point" from "the audit's §3" throughout and
  needed no correction — the error was introduced only when translating plan prose into shipped
  prose, under a verb ("§3: 573...") that reads as one citation covering two different-provenance
  numbers.
