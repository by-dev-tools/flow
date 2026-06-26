# Automation boundaries & known limitations

The README describes the happy path: drive the loop and it advances on its own between the two human gates. This doc covers the edges — what runs automatically, what doesn't, and where the seams are. Read it before relying on any step firing by itself.

## What fires on its own, and what doesn't

Each skill has an invocation mode:

- **AUTO** — fires by itself when its trigger condition is met. You never type it. Only `/flow:log-disagreement` is AUTO: it captures pushback when you dispute a finding in plain language.
- **BOTH** — you can type it, *and* it runs when `/flow:ship` calls it or when a matching phrase plus a diff-to-review triggers it. It won't cold-start on a bare "build me X".
- **AUTO·when-ready** — `/flow:ship` only. Auto-advances from Step 8 *at the end of a driven loop* when the ship-readiness predicate holds (every spec-walk box checked, no open BLOCKER, no unresolved MEDIUM/LOW assumption, `/flow:verify-build` would return PASS) and the risk gate is clear. Otherwise you type it or say "ship it." Never auto-advances when verify-build is skipped (library/none platform, or a doc-only diff), and never on a cold start.

There is no MANUAL-only skill: every skill is at least model-invocable. The only things that strictly require a human are the two gates — plan approval and PR merge.

## Cold-start reality

Install flow, open a session, and say "build me X" with no slash commands, and **only the auto-loading rules attach.** Those rules are workflow-discipline *guidance* in Claude's context that nudges it to plan before coding and wait for your approval. That nudge is the entire automatic footprint of a cold start.

No audit, plan critique, staff/security/a11y review, verify-build, or ship pipeline runs from a cold "build me X" until you — or a phrase trigger — invoke it. The plugin registers no hooks by default.

`/flow:critique-plan`, `/flow:audit-plan`, `/flow:audit-completion`, and `/flow:ship-spike` are all model-invocable within a driven loop (Claude fires them at the plan / present / spike-end points), but none of them cold-start. `/flow:ship` auto-advances only after the loop has been driven all the way to Step 8 with a green readiness predicate; it won't start itself from a cold request either.

## Soft enforcement

The readiness predicate is *guidance* — a rule plus the skill descriptions — not a hard hook. The mechanical backstop is `/flow:verify-build` inside the ship pipeline: a FAIL or Unknown regression routes to a draft PR with a pinned `🚫 NOT READY TO MERGE` manifest, never a merge-ready PR on a non-PASS build. Hard enforcement via a Stop hook + an Edit|Write scope check is planned but not yet shipped.

The two human gates never move: **plan approval** (Step 2) and **merge** (Step 11).

## Known limitations

- Regex artifact detection misses files with no extension or unusual paths.
- Tool-call history truncates at 50 calls.
- Bounding logic occasionally grabs the wrong user turn on short follow-ups.
- Plan/completion mode detection is heuristic.
- SwiftUI proxy handling is hardcoded; other frameworks need explicit additions.
- The eval harness reads pre-recorded `.expected.txt` files for the auditor + plan-critic — regression-only, not live correctness validation.
- `/flow:init` (auto-create scaffolding with detection + prompting) is deferred; today's path is `bootstrap.sh` plus manual placeholder fill.
- The PR `## Test plan` is rendered from the verify-build findings buffer, so a checked box attests **behavioral/text** verification by an adversarial judge — *not* visual correctness. Rendered-visual judging is on the roadmap. The attestation also only covers criteria the plan **declared** in its `**Spec-walk:**` block; `/flow:audit-coverage` closes the worst of that under-declaration hole but is best-effort LLM judgment, not a deterministic guarantee. It is not a substitute for the human read at the merge gate.

## Lineage

This repo was previously published as `byamron/llm-auditor` (marketplace) hosting the `assumption-auditor` plugin. It was renamed to `by-dev-tools/flow` on 2026-05-23 and restructured into the marketplace + plugin shape in v1.0.0. Pre-v1.0.0 content is recoverable via `git checkout pre-flow-plugin`. GitHub redirects `byamron/llm-auditor` → `by-dev-tools/flow`, so old clones still pull from the same place.

Per-version detail: [`CHANGELOG.md`](../CHANGELOG.md).
