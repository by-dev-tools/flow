# 2026-09-12 — Worker→orchestrator ping protocol, ships-or-paperwork test, and succession re-addressing

- **Date:** 2026-09-12
- **Branch:** `orchestrator-ping-protocol-and-succession`
- **Commit / PR reference:** [this commit]

## What was done

Flushed two orchestration protocols that had been implemented and dogfooded in the orchestrator
seat but never written down, plus the succession step that keeps the first one alive across a seat
rotation. Docs-only: canonical plan §4.8/§4.9, two feedback entries, this entry.

- **§4.8 rule 6 — workers ping the orchestrator** on completion, on a blocking question, and on a
  stall, instead of the orchestrator (or the human) sweeping for status. Records the ~9-ping
  dogfood result, and records the **rate-limit gap** as a gap rather than quietly omitting it.
- **§4.8 rule 7 — the ships-or-paperwork test.** Does the decision change behaviour, a consumer
  surface, or a gate verdict, or only where something is written? Paperwork is the orchestrator's
  call.
- **§4.9 wind-down step 4 — re-address the ping channel.** The successor's first action is to
  broadcast its own session ID to every live worker.
- Fixed the "**Four rules**" / five-item mismatch in §4.8 (the list gained rule 5 on 2026-08-27 and
  the count was never updated). Now seven and consistent.

## Why

§4.9's disposability invariant says the orchestrator may hold no state that is not recoverable from
GitHub or the Conductor API. Both protocols were live in the seat and in worker dispatch briefs but
in neither place — so they were exactly the state the invariant forbids, and a rotation would have
dropped them. This is the §4.9 step-1 flush performed for real, on the way out.

## Design decisions

- **The succession step lives in §4.9, not in the brief template.** A brief is generated per
  rotation and not maintained; putting the re-broadcast only there means it survives exactly as
  long as one orchestrator remembers to write it. In §4.9 it is part of the wind-down contract.
- **The rate-limit gap is documented rather than fixed.** The cheap backstop
  (time-since-last-activity via `conductor session status`) is named but not built, because
  building it now would be scope the seat took on itself mid-handoff. Naming it means the next
  seat can cost it; omitting it would have let "we have a ping protocol" read as coverage.

## Technical decisions

- No version bump. Nothing under `plugins/flow/` changed; this is plan + dev-doc content, and the
  §4.10 skills that will *enforce* these rules are not built yet.

## Tradeoffs discussed

- **Write the rules into the plan now vs. wait for `/flow:orchestrate` to exist and encode them
  there.** Encoding in a skill is strictly better — it is enforced rather than remembered — but the
  suite is not built, and the entire point of this pass is that the seat is rotating *today*.
  Prose in the canonical plan is the durable form available right now, and §4.10 already names the
  plan as the source the skills get built from, so this is the input to that work rather than a
  competing copy of it.
- **Two feedback entries vs. one.** They came from one session and both concern orchestrator
  communication, which argued for merging them. Kept separate because the rules they generate apply
  at different moments — one at succession, one before every escalation — and a future reader
  looking up "why does the successor broadcast its ID" should not have to read past an unrelated
  rule about escalation economics.

## Lessons learned

- **A push channel is only as durable as the identity it is addressed to.** Replacing a poll with a
  push removed the human from the status loop, and simultaneously created a failure mode the poll
  never had: a dead channel is silent, and silence on a "ping me if blocked" channel reads as
  *good* news. The protocol that reduces attention cost in the normal case inverts the signal in
  the failure case. Worth checking for on any future push-shaped mechanism here.
- **A well-formed escalation can still be the wrong thing to send.** The #146 escalation carried a
  recommendation, a confidence, and a rationale, and was still waste, because no formatting rule
  asks whether the decision has an outcome attached. Contract compliance measured the wrong thing.
