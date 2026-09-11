## 2026-08-24 — Handoff without a docs-only PR class: canonical-plan §4.5 + #122 currency folded (no standalone `/flow:land` PR)

**Branch:** `handoff-without-land` · **PR:** #(assigned at open; refer to it by that number per the §4.5 convention below) · **Mode:** docs

**What was done.** Added §4.5 "Handoff without a docs-only PR class (the land-elimination)" to the canonical plan (`research/2026-08-23-flow-cloud-workflow-plan.md`) plus execution rows 1a/1b in §5. And **dogfooded it in the same change**: #122's post-merge currency (history entry + FB-0087/0088 reservation clears) was folded into THIS substantive PR instead of the standalone `/flow:land` PR (#123, now closed) — the first instance of "durable currency rides the next ship, not its own docs-only PR."

**Why.** Ben's question: given the Conductor orchestrator model, does the `/flow:land` post-merge PR (which doubles PR count and adds a handoff hop) still earn its place? `/flow:land` exists to keep `main`'s forward docs current for a **cold reader** — a new contributor, or the autonomous loop as a cold agent re-reading `main` each run (its own SKILL §0 header). The orchestrator breaks that assumption: the next workspace is spawned by a coordinator holding live state and handed a dispatch brief, not a cold `main` read. So land's forward-pointer job is superseded, and its durable-currency job needs no PR of its own.

**Design decisions.**
- **Reference merged PRs by `#N`, not SHA, in history** (dogfooded here: #122's line is now `**PR:** #122 (merged)`, not a `merged @ <sha>` stamp). The merge SHA was land's *only* value unknowable until merge — #N is known at PR-open. Removing the SHA dependency removes the ordering constraint that forced a *separate* after-merge PR. Verified against #123's actual diff: its entire content was the SHA stamp + two reservation clears.
- **Fold currency into the next ship; gate `/flow:land` behind a slot** rather than delete it — the pure cold-autonomous-loop consumer (no orchestrator) genuinely re-reads `main`, so land stays available, just off the default path. FB-0088 discipline: encode the fact (currency belongs on `main`), not the procedure (a standing second PR).
- **Guardrail kept:** durable currency still reaches `main` through a *reviewed* PR, never a direct push — the merge gate (G3) is untouched. The orchestrator speeds the handoff to the next workspace; it does not skip the human merge.

**Tradeoffs.** `main`'s forward pointers can be briefly stale between merges — harmless when a coordinator knows the true frontier, load-bearing without one (hence the slot, not a delete). The plugin-side implementation (ship/land skill edits for the `#N` convention + the slot) is execution rows 1a/1b — queued, not in this docs change.

**Three-surface note.** Docs-only: `research/` + `dev-docs/` only. No `plugins/flow/` artifact changed — the skill edits are the queued 1a/1b work.
