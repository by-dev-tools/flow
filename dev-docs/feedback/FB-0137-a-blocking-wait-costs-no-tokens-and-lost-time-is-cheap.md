# FB-0137 — A blocking wait costs no tokens, and lost wall-clock is the cheap resource

**Date:** 2026-10-05
**Source:** Ben, relayed through the ready-check dispatch brief
**Status:** shaping the design of the Step 8 CI condition (v1.63.0, plan gate)

## What was said

> **"tokens matter, lost time doesn't. Keep review rounds proportionate."**

Stated as a constraint on the ready-check work, where the open design question was how
`/flow:ship` should wait for GitHub's checks to settle before deciding whether a PR may be called
ready.

## Why this resolves the question rather than merely constraining it

The obvious implementation of "wait for CI" is an agent polling loop: call `gh pr checks`, read the
output, decide whether to wait, sleep, call again. Every iteration of that loop is a model turn —
it re-reads its own prior output, re-reasons about the same tri-state, and bills for the privilege.
A twenty-minute CI suite becomes dozens of turns whose entire informational content is "still not
done."

A blocking command — `timeout <N> gh pr checks <PR> --watch` — produces the identical verdict for
**zero** model turns. The process sleeps; the agent does not think. Measured on this host: a settled
PR returns in 1s, exit 0.

So Ben's constraint does not merely *permit* the blocking form, it *selects* it. Under "tokens
matter, lost time doesn't", the polling loop is strictly dominated: same answer, same wall-clock,
many times the cost. The two framings disagree only if wall-clock is the scarce resource, and it is
explicitly not.

The second clause — *keep review rounds proportionate* — is the same economy applied to judgment
rather than waiting: a round of LLM review is expensive and reward-hackable, so the repo's existing
discipline of **one** bounded re-review cycle (never iterating on an LLM verdict) is the proportionate
shape, and a deterministic checker that can be re-run for free is preferable to a reviewer that must
be re-asked.

## How to apply

1. **When waiting on an external state the harness cannot notify you about, reach for a blocking
   command with a timeout before reaching for a loop.** `timeout <N> <cmd> --watch` is the default
   shape; an agent-driven poll is the fallback for when no blocking form exists, not the first choice.
2. **Never upgrade a timeout into a pass.** The cost asymmetry runs the other way here: a blocking
   wait is cheap, so there is no budget pressure justifying "it probably passed." On timeout, report
   the pending state honestly — this is [[FB-0121]]'s rule ("couldn't see" is not "nothing there")
   meeting a cost argument that happens to point the same direction.
3. **Prefer a deterministic check that is free to re-run over an LLM round that is not.** Where a
   gate can be expressed as a script, the proportionality constraint is satisfied by construction:
   re-running it costs nothing, so it never has to be rationed.

Related: [[FB-0131]] (whose third corollary is the defect this work fixes), [[FB-0121]],
[[FB-0011]] (escalation triggers — a cheap wait is not a reason to skip the human gate).
