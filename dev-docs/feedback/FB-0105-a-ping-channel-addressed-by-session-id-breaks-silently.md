# FB-0105 — A ping channel addressed by session ID breaks silently at succession

- **Date:** 2026-09-12
- **Source type:** user direction (+ design consequence found while acting on it)
- **What was said:** Ben observed he kept having to message the orchestrator to ask whether
  workers were blocked, and proposed the inverse: workers ping the orchestrator when they finish
  an assigned task, so the human is not the thing that notices. The protocol was implemented and
  dogfooded (~9 pings across five workers).

- **Synthesized rule:** **Prefer push over poll for status — but a push channel addressed by a
  mortal identity must be re-addressed whenever that identity rotates, and the protocol must say
  who does it.** The worker→orchestrator ping targets a Conductor *session ID*. That ID belongs to
  the orchestrator seat, and §4.9 makes the seat deliberately disposable. So the moment the seat
  rotates, every live worker is pinging an address that no longer exists.

  What makes this worth a feedback entry rather than a footnote is the **shape of the failure, not
  the bug**: it is silent and it inverts the signal. A broken poll is loud — the sweep errors, or
  returns nothing where something was expected. A broken push produces *silence*, and silence on
  this channel is indistinguishable from "no worker needs anything." The successor's reasonable
  reading of a dead channel is that all is well, so the protocol fails in the direction of false
  confidence — which is worse than the polling it replaced, because polling at least degraded
  loudly. The same reasoning applies to any push channel keyed to something mortal (a webhook URL,
  a callback address, a workspace-scoped queue), not just this one.

  Two consequences, both now in the canonical plan:
  1. The successor's **first action** is to re-derive the worker list and broadcast its own session
     ID to each live worker (§4.9 step 4). Nothing in the successor's environment reveals the
     channel is stale, so this cannot be left to inference.
  2. **A ping protocol is not coverage.** A rate-limited worker has no turn in which to ping, so
     the failure the protocol most needs to report is exactly the one it cannot report. Sweeps of
     *silent* workers are still owed until a time-since-last-activity backstop exists
     (`conductor session status` exposes `Updated`). Recorded as a known gap rather than fixed,
     because pretending the protocol is complete is how the gap becomes invisible.

- **Applies to:** canonical plan §4.8 (rule 6) + §4.9 (wind-down step 4); the future
  `/flow:handoff` and `/flow:spawn` skills (§4.10), which must emit the re-broadcast and the
  worker-side ping instruction respectively rather than relying on an orchestrator remembering.
