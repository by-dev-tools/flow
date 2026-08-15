# dev-docs — index

Flow's own development tracking. **Not shipped** — none of this is part of the plugin (see `CLAUDE.md` § Repository Layout for the three-surface boundary).

This file exists because point-in-time docs get buried by default: `CLAUDE.md`'s Core Documents table listed only the five living docs, so `research/` and `handoffs/` were invisible to any agent orienting from it. **Every new doc under `research/` or `handoffs/` must be added here in the same PR that creates it** — see § Rules below.

---

## Living docs — always current, read before acting

| Doc | Purpose |
|---|---|
| [`plan.md`](plan.md) | Current focus, active work items, handoff notes |
| [`roadmap.md`](roadmap.md) | Now / Next / Later / § Exploration |
| [`history.md`](history.md) | Per-PR decision log — what, why, tradeoffs |
| [`feedback.md`](feedback.md) | Synthesized user corrections (FB-XXXX) |
| [`spec.md`](spec.md) | Plugin scope. ⚠️ **Known stale** — still describes the audit-only scope; broadening to full flow identity is a queued hygiene PR |
| [`workflow.md`](workflow.md) | Flow-internal dev workflow (≠ the shipped `plugins/flow/docs/workflow.md`) |
| [`design-language.md`](design-language.md) | Visual/interaction rules for the browser UI flow ships (annotation overlay, verify-build report). `uiSurface` flipped to `true` in v1.24.0 |
| [`reserved-feedback-numbers.md`](reserved-feedback-numbers.md) | FB-number reservation protocol + collision audit trail. **Reserve before drafting an FB entry** |

## Research — point-in-time findings, not living docs

Each is accurate as of its date and is **not** maintained afterward. Read the Status line before trusting one.

| Doc | Date | Status |
|---|---|---|
| [`research/service-agnostic-2026-07.md`](research/service-agnostic-2026-07.md) | 2026-07 | ⚠️ **Partially superseded** — field survey (standards, prior art, 13-host landscape). For execution decisions the roadmap below is authoritative |
| [`research/anthropic-canon-alignment-2026-08.md`](research/anthropic-canon-alignment-2026-08.md) | 2026-08 | Alignment check vs Anthropic's first-party agent canon. **Elevated M (model routing) + AB (attention budget) to top priority** in `roadmap.md` § Now |
| [`research/ai-workflow-landscape-2026-07.md`](research/ai-workflow-landscape-2026-07.md) | 2026-07 | Competitive benchmark vs Flow; fed the roadmap's § ▶ Active program sequence. ⚠️ Its own header flags throttled provenance — the `/deep-research` fan-out was cut off mid-run |
| [`research/voice-annotation-pipeline-2026-07.md`](research/voice-annotation-pipeline-2026-07.md) | 2026-07 | ⏸️ **PARKED — DO NOT BUILD.** macOS dictation solves it with zero code. Retained for *why Web Speech can never work here* |
| [`research/jq-absence-handling-2026-06.md`](research/jq-absence-handling-2026-06.md) | 2026-06 | Surfaces the shape of silent degradation when `jq` is absent across 16 skills. **No fix shipped** |
| [`research/agent-orchestration-2026-05.md`](research/agent-orchestration-2026-05.md) | 2026-05 | Field survey of multi-agent patterns; informed the loop's gate design |
| [`research/dynamic-workflows-2026-05.md`](research/dynamic-workflows-2026-05.md) | 2026-05 | Reviewer-refutation spike (empirical layer) |
| [`research/dynamic-workflows-alignment-2026-06.md`](research/dynamic-workflows-alignment-2026-06.md) | 2026-06 | Architecture-alignment layer; companion to the above |
| [`research/visual-verification-blueprint-2026-06.md`](research/visual-verification-blueprint-2026-06.md) | 2026-06 | **Largely implemented** — the V2/V3 Deliverable-quality track shipped across v1.6.0–v1.8.1 |

### Also: repo-root `research/`

A **second** research location exists outside `dev-docs/`, added by #104. It is deliberately quarantined (exploratory notes not being pursued, kept greppable without touching any tracked surface), so it is not governed by the Rules below — but it is listed here so it is findable rather than buried.

| Doc | Status |
|---|---|
| [`research/2026-08-14-cloud-ios-simulator-limrun.md`](../research/2026-08-14-cloud-ios-simulator-limrun.md) | ⏸️ **Parked** — cloud iOS simulators (Limrun + alternatives) for agent workflows. Not being pursued |

## Handoffs — per-PR execution plans

| Doc | Status |
|---|---|
| [`handoffs/service-agnostic-roadmap-2026-07.md`](handoffs/service-agnostic-roadmap-2026-07.md) | 🟢 **ACTIVE — not started.** Codex + Cursor support from one source tree. **Contains Phase 00, a confirmed live bug** (plugin `rules/` and default hooks never load). Self-contained; §0 is a cold-start reading order |
| [`handoffs/active-program-2026-07-08.md`](handoffs/active-program-2026-07-08.md) | 🟡 **PRESERVED, NOT APPLIED** — a roadmap section that never reached main, recovered verbatim before its worktree was archived. Re-integrating is a judgment call: the roadmap moved v1.19.0 → v1.27.0 since |
| [`handoffs/pr-q-verify-build-plan.md`](handoffs/pr-q-verify-build-plan.md) | ⚪ **SHIPPED** — `/flow:verify-build`, v1.3.0 (#26). Historical record; its "Phase 3 in progress" status line is stale |
| [`handoffs/pr2-flow-plan.md`](handoffs/pr2-flow-plan.md) | ⚪ **SHIPPED** — the workflow-skills extraction. Historical record; status line is stale |
| [`handoffs/md-manager-pr4-6-spec.md`](handoffs/md-manager-pr4-6-spec.md) | ⚪ **FOREIGN REPO** — spec for md-manager PRs 4–6, not flow. Kept for cross-repo context |

---

## Rules

1. **Index at creation.** A new doc under `research/` or `handoffs/` is added to the table above **in the same PR**. An unindexed point-in-time doc is a buried doc.
   **This is enforced**, not just asked: `dev-docs/check-index.py` runs as the `dev-docs index` CI job and fails the build on any unindexed or status-less doc. Run it locally with `python3 dev-docs/check-index.py`. It deliberately does **not** check that a status is *accurate* — no script can, and pretending otherwise would be the failure-open this repo keeps fixing.
2. **Every point-in-time doc carries a `Status:` line in its header** — and the status must be true *now*, not when it was written. A stale "in progress" is indistinguishable from a current one; that is the FB-0074 class.
3. **Living docs are never archived**; point-in-time docs are never edited to stay current. If a research doc's conclusion is overturned, mark it superseded inline and point at what replaced it — don't silently rewrite history.
4. **`spec.md` is the known-stale one.** Fix or retire it; don't add to it.
