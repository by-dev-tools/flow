## 2026-08-26 — §4.9 externalize-non-git fix + §4.10 orchestrator skill suite (in flow) + FB-0091

**Branch:** `succession-file-externalization` · **PR:** #(assigned at open) · **Mode:** docs

**What was done.** Closed two gaps the first real orchestrator succession surfaced.
- **§4.9 file-externalization fix.** The disposability invariant was too loose — a *sandbox-local file* is recoverable from **neither** GitHub nor the Conductor API and dies when the sandbox is torn down, yet the first succession brief pointed the successor at a `/home/…` report path in the *outgoing* sandbox (a different sandbox it cannot reach). Wind-down is now **three steps** — flush durable currency to git, **externalize any non-git artifact that matters** (commit if repo content, else hand its contents to the human), then hand off the brief — and the invariant sharpens to "recoverable from GitHub, the API, **or already delivered to the human**." Added the rule that every brief reference must point at a reachable location, never the outgoing sandbox. (The report survived only because it had been surfaced to the human; caught live.)
- **FB-0091.** The successor was spawned on `sonnet-5-1m`/high; the family matched the routing table but the effort was a by-feel bump. Rule: the orchestrator routes *itself* (including its successor) per the §4.3 table with a logged `model · effort · why`, never silently by feel.

**Why.** Both are dogfood findings from executing the §4.9 succession this session — the model working, and revealing its own two soft spots.

- **§4.10 + §4.4 revision — the orchestrator skill suite moves INTO flow.** The user directed the orchestration workflow to be a core part of flow (not per-repo): a suite of **agent-invocable** skills — `/flow:orchestrate` (successor bootstrap), `/flow:spawn` (the model-decision-tree + dispatch brief), `/flow:handoff` (the §4.9 wind-down + archive-safety), optional `/flow:gate` — shipped in `plugins/flow/skills/`, with Conductor mechanics behind a `dispatchBackend` adapter slot so host-agnosticism holds (reversing §4.4's exclusion, whose revisit criterion is now met). Cross-workspace invocation is *instruct-not-remote-invoke*: `/flow:spawn` creates B and tells B's agent to run a named flow skill; B, having flow installed, invokes it locally — which is precisely why the suite must ship in flow and be agent-invocable. This is now the concrete shape of §5 Step 4 (orchestrator v1).

**Three-surface note.** Docs-only (`research/` + `dev-docs/`).
