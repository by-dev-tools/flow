### Add lesson-harvest Step 4c to `/flow:ship-spike` (v1.19.0, FB-0059 parity)
**Date:** 2026-07-12
**Branch:** claude/laughing-merkle-215513
**Commit:** _(on branch; final SHA in the PR)_

**What was done:**
Added a **Step 4c — Harvest flow-generalizable lessons → contribution queue** to `plugins/flow/skills/ship-spike/SKILL.md`, mirroring the section of the same name in `/flow:ship`. Spike ship now runs the same two-destination router — pre-scan cost gate (`harvest_lesson.py prescan`) → noise/destination/source-type analysis → `harvest_lesson.py enqueue` to the `contributionsQueuePath`, then `harvest_lesson.py mark` to advance the watermark — that a feature ship runs. Also added the three harvest config slots (`lastHarvestedPath`, `contributionsQueuePath`, `flowRepoPath`) to ship-spike's "Config slots used" table. Version bumped to 1.19.0 (plugin.json + marketplace.json ×2 + descriptions); CHANGELOG v1.19.0.

**Why:**
`/flow:ship-spike`'s Step 4 ran only the memory self-feedback sub-steps (4b.i–4b.vi) — there was **no** Step 4c anywhere through v1.18.0. So spikes never routed lessons about *flow itself* (gate misfires, reviewer false-positives, taste calls the human overruled) to the cross-project contribution queue. Spikes are *higher-yield* for exactly those lessons because the agent runs with less guardrail, so the omission dropped the highest-signal source. The FB-0010 fan-out class: a contract (`/flow:ship` has 4c) referenced in one skill but not its sibling.

**Design decisions:**
- **Always-run, not gated on spike-ness.** The harvest value is workflow-type-independent, so the step fires unconditionally (still cheap: the pre-scan cost gate makes a clean spike ~free, and it only enqueues locally — `/flow:contribute` drains later).
- **Faithful mirror of `/flow:ship` § 4c, not a re-derivation.** Same scripts, same slots, same env-export idiom (`FLOW_CONTRIB_DIR`), same watermark-marker default, same "never silent" reporting line — the two skills can't drift on the harvest contract (FB-0059 + FB-0010). The prose adapts for spike context (4c.ii draws from session context directly — spike Step 4 has no 4a candidate list to reuse).

**Technical decisions:**
- **No script changes.** `harvest_lesson.py` already exposes `prescan`/`enqueue`/`mark`; the new section reuses them verbatim, so the existing `run_contribution_evals.py` still pins the engine.
- **Fan-out swept.** The "`/flow:ship` Step 4c enqueues" attribution was updated to "+ /flow:ship-spike" across the 3 schema slot-descriptions, `contribute`/`doctor` SKILL.md, and `CLAUDE.md` (caught by `/simplify` after the initial schema-only edit).

**Tradeoffs discussed:**
- Inline the 4c body vs. reference `/flow:ship` § 4c: chose to inline (self-contained), matching how ship-spike inlines its other steps; the deeper de-duplication into a shared fragment is routed to `roadmap.md` § Next.

**Lessons learned:**
- Reinforces the FB-0010 fan-out discipline: a step added to `/flow:ship` (4c shipped in v1.11.0) is a contract that should have been greped across sibling skills the same commit — this entry is that follow-up landing seven minor versions late.
- **Renumbered v1.17.0 → v1.18.0 → v1.19.0** across three rebases — three concurrent branches (`#71` frame-integrity, `#70` PR-coherence, `#73` plan-file) each claimed the next version in the interim. The stale-base gate (FB-0008) + the CI-conflict monitor caught every collision; reconciled to the current frontier each time rather than shipping stale. A live demonstration of the "recheck version vs origin right before finalizing" invariant under rapid concurrent merges.
