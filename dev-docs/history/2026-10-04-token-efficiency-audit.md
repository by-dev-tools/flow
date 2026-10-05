# Token-efficiency audit — measuring where the program's spend actually went

**Date:** 2026-10-04
**Branch:** `conductor/audit-flow-token-efficiency`
**Version:** [docs-only, no plugin version bump]
**Feedback:** none synthesized this entry (research deliverable, no correction received)
**Scope:** `dev-docs/research/2026-10-efficiency-audit.md` + its index row. No plugin artifacts
touched.

## What this is

Ben asked for a measured (not estimated) audit of whether the program's token/cost spend across
every Conductor workspace since 2026-09-06 was buying progress, after noticing the account
"hitting limits pretty quickly." Full findings live in
`dev-docs/research/2026-10-efficiency-audit.md`; this entry records the method decisions, since
several of them are reusable and none were obvious going in.

## Why

No existing tool measured this. `tools/model-measure/model_measure.py` reads local Claude Code
transcript files, which only exist for sessions that ran on the sandbox they ran on — it can't see
any other workspace's sandbox. The Conductor API's `.flow/usage.tsv` on the orchestrator seat
wasn't reachable either (no filesystem access, and the contract explicitly said not to create new
sessions to go get it). Needed a different source entirely.

## Design decisions

- **Used Claude Code's own `result` events as the authoritative cost source, not manual token
  summation.** Every session transcript (`conductor session message <id> --json`) contains
  periodic `rawPayload.type == "result"` records carrying `total_cost_usd` and a per-model
  `modelUsage` breakdown — Anthropic's own list-price computation, already reconciled against
  real billing logic. Pulling the last such event per session gives a session total without
  reimplementing token-to-dollar pricing by hand (which would have required guessing at
  long-context tiered pricing for `opus-5-5-1m`).
- **Discovered and corrected for a non-monotonic cost counter.** The orchestrator seat's `result`
  events showed 17 downward jumps in cumulative cost across its 185 events (coinciding with
  successions and, apparently, compactions). Trusting the last reading alone ($184.69) would have
  undercounted; the fix was to sum every detected downward "lost" amount and add it back
  ($283.79). Cross-checked against an independent method (manually summing every assistant turn's
  raw `usage` across the whole transcript, which can't suffer the same reset) — that gave roughly
  double the cache-read tokens the last `modelUsage` reading implied, confirming the correction
  was in the right direction, not just plausible-sounding.
- **Sampled rather than fully measured the S0 probe suite (95 sessions across 8 workspaces).**
  Counting exact session names by type was cheap (plain `conductor workspace session` listings);
  fetching full token/cost data for all 95 would not have been economical for what turned out to
  be a mostly-zero-cost suite. Sampled 13 directly, found a clean split: `documentation`/
  `exploration`/`general`-type probes cost exactly $0 on every check (no real model call —
  `num_turns: 1`, all-zero usage), `plan-discipline`-type probes cost $0.07–$1.03 depending on
  model. Extrapolated the remaining 82 from that split rather than fetching each one.
- **Found the rate-limit-stall evidence by cross-referencing two independently-collected signals**
  rather than trusting either alone: `rate_limit_event` records with `status: "rejected"` (24 in
  the orchestrator's own session), and gaps of 8+ hours between consecutive transcript messages
  (27 found). Only the 12 gaps that start within 10 minutes of a confirmed rejection are
  attributed to rate-limiting (~134 hours); the other 15 are left unattributed as likely ordinary
  offline periods, rather than claiming all 27 as waste.

## Tradeoffs

- **Precision vs. economy on the S0 probe suite.** Choosing to sample 13 of 95 sessions means the
  $8.56 estimate for the probe suite's non-zero-cost sessions could be off by some amount if the
  sampled sessions weren't representative. Accepted because the dollar amount is small either way
  (it doesn't change any ranked recommendation) and the "be economical" instruction in the
  dispatch brief explicitly asked for this tradeoff.
- **Reporting a cost range ($185–$284) for the orchestrator seat instead of a single number.**
  Could have picked one and moved on; chose to report both because the discrepancy itself is a
  finding (the live running-cost display under-reports after a compaction) and picking either
  number alone would have hidden that.
- **Not reconciling the ~2× gap between the two cache-read-token measurement methods to an exact
  number.** Flagged as unresolved in the doc rather than forcing a false-precision reconciliation;
  doing so would have required assumptions about exactly which turns' usage records survive a
  reset, which I couldn't verify from the data available.

## Revision after orchestrator review

The orchestrator reviewed a first draft and flagged two claims as stronger than the measurement:

1. **The orchestrator's own "134 idle hours after a rate-limit rejection" was being presented as
   limit-caused waste without checking whether anything was actually blocked.** Re-checked: of
   the 12 qualifying gaps, every one resolves on exactly one message — a content-free "continue"
   from Ben, arriving at the very end of the gap. Nothing shows a worker report or decision
   sitting queued during the gap. Reclassified as "mechanical-restart lag" (real and measured,
   but not evidence of blocked work) and demoted to the bottom of the ranked waste list, replaced
   at #1 by a worker-side finding that IS directly confirmed in-transcript — the orchestrator's
   own resume message to a worker states outright that the worker's window reset at 04:30 but
   wasn't re-pinged until 14:30.
2. **The subagent-vs-workspace recommendation for the S0 probe suite was treating all 95 sessions
   as equivalent.** Reading the actual first-message setup commands for each arm showed arms
   `c2`/`c-old`/`c-v1` explicitly reinstall a specific `flow@flow` snapshot at plugin scope
   (`claude plugin marketplace add` + `claude plugin install`) — machine-wide state a subagent
   can't hold independently of its parent's own install. Only arms `a`/`b`/`d`/`c` (no reinstall
   step) support the subagent recommendation; the doc and recommendation were rescoped
   accordingly.

Lesson for next time: when a measurement correlates two events (a rejection and a gap, a workspace
and a probe type), check what's actually inside the gap / what the setup commands actually do
before generalizing the correlation into a claim about cause or into a blanket recommendation.

## Lessons learned

- Claude Code's own `result`/`modelUsage` events are a much better source of ground truth for
  cross-workspace cost measurement than reimplementing token-to-dollar math — this is reusable for
  any future cost audit and should be the default starting point rather than local transcript
  parsing.
- A session's live cumulative cost counter is not reliable evidence of total spend once a long
  session has compacted or changed hands (succession) — always check for downward jumps before
  trusting a single "current total" reading.
