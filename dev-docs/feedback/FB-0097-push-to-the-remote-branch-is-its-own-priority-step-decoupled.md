### FB-0097 — Push to the remote branch is its own priority step, decoupled from finishing `/flow:ship`, in ephemeral/session-limited environments

**Date:** 2026-08-27
**Source type:** user direction (repeated twice, same session)

**What was said.** This session hit its rate limit twice, both times within moments of the user clearing it to run `/flow:ship`. Each time, fully green, reviewed, committed-ready work sat only in the sandbox's local git state — uncommitted and unpushed — until the user's next message, hours later, explicitly named the risk: *"getting it into a PR is now the priority: it exists only in this sandbox, and a Conductor workspace has a hard ~23.8h lifetime... Do this first, before anything else, so the work cannot be lost: commit locally and push the branch."*

**Synthesized rule.** In an orchestrator-dispatched or otherwise session/workspace-limited environment (Conductor cloud sandboxes, any host with a hard lifetime or rate-limit exposure), commit + push to the remote branch is a **priority step in its own right**, not merely the tail end of `/flow:ship`. The moment work is genuinely green (harnesses pass, reviews applied, nothing left to fix) — commit and push immediately, *before* proceeding into the rest of the ship pipeline (final-pass reviewers, doc synthesis, PR body rendering). A local, unpushed commit in a sandbox with a hard lifetime is not durable; a pushed branch with no PR yet is fully recoverable. If the session dies mid-ship after that point, at worst a PR needs to be opened by hand or by a fresh session against a branch that already has the real work on it — never a full re-do.

**Corollary — this generalizes the existing plan-gate/merge-gate durability doctrine one layer down.** Canonical plan §4.9 already treats "recoverable from GitHub, the API, or already delivered to the human" as the bar for orchestrator-seat state; this is the identical bar applied to a worker/implementation session's own in-progress commits, and it argues for pushing *before* the full ship pipeline completes, not only after.

**Applies to:** any `/flow:ship` execution from a Conductor or similarly session-limited cloud workspace; the ordering of Step 6 (commit) and Step 7 (push+PR) relative to the rest of the pipeline when a session has already shown a pattern of dying mid-flow.
