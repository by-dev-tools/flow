### `/flow:ship` auto-invocable — autonomous-loop trigger at Step 8 (v1.4.0) SAFETY
**Date:** 2026-05-30
**Branch:** `claude/auto-ship-readiness-trigger` (commit at push time; stacked on the docs PR #29 squash)

**What was done:**
Flipped `/flow:ship`'s `disable-model-invocation` from `true` → `false` so the agent can invoke ship itself at the end of a driven loop, paired with a deterministic gate so it can't fire arbitrarily:
- **ship/SKILL.md** — flag flip + an auto-invocation contract in the description (the text Claude Code reads to decide auto-firing): auto-invoke only when the ship-readiness predicate holds and the FB-0011 risk gate is clear; never when verify-build is skipped; never merges.
- **workflow.md** — Step 8 "Present" rewritten as a **conditional gate**: a ship-readiness predicate (all spec-walk boxes checked, no open BLOCKER, no unresolved MEDIUM/LOW assumption, `/flow:verify-build` would return PASS), an FB-0011 risk gate, and explicit auto-advance vs stop-and-present paths. Loop diagram + MEDIUM confidence-row cross-referenced.
- **general.md** — workflow-discipline bullet encoding the trigger (auto-loads on `**/*`).
- Version bump v1.3.0 → **v1.4.0** (marketplace.json ×2, plugin.json, README header) + cumulative description sentences; README auto/manual table `ship` row → `AUTO·when-ready` + cold-start note revised; CHANGELOG v1.4.0 entry.

**Why:**
The user's goal is an autonomous coding loop with human gates only at plan approval and merge. `ship`'s `disable-model-invocation: true` was a blanket-conservative default set in v1.0.0 and never revisited toward that direction — it forced the user to type "ship it" at every loop end, which is not one of the two load-bearing gates. Auto-invoking ship does not violate the merge gate (ship opens a PR, never merges).

**Design decisions:**
- **verify-build is the load-bearing gate, not the predicate.** The predicate only decides whether to *enter* ship; ship's own Step 2 verify-build (`exit_code: 1` on FAIL/Unknown) re-confirms and halts pre-PR. So a falsely-confident auto-advance is caught mechanically — the model's self-report is not the safety boundary. This is why the predicate can be "soft" (rule + description guidance) without a Stop-hook.
- **Skipped-verify stays MANUAL** (user decision, 2026-05-30): library/none platform + doc-only diffs have no behavioral gate, so the predicate requires `overall_verdict: PASS`, not merely "verify-build didn't fail." Default-to-ESCALATE per FB-0011.
- **ship-spike stays MANUAL** — spikes are user-initiated explorations; the deliverable (the answer) is a judgment call, not a mechanical readiness signal.

**Technical decisions:**
- Encoded the predicate in `general.md` (already loads on `**/*`) rather than a new rule file — a 5th rule would break the "4 auto-loading rules" fan-out contract (README/doctor/manifest all cite the count).
- Verified no eval/doctor/CI assertion depended on `ship` being `disable-model-invocation: true` (`git grep` — none) before flipping. Evals + security evals green post-change.

**Tradeoffs discussed:**
- Flip-the-flag-alone vs flag-plus-gate. Flipping alone would let the model ship on a vibe (the un-gated judgment FB-0011 warns against). Chose flag + readiness predicate + verify-build hard gate so autonomy is earned by a mechanical signal, not asserted.
- Stacked this PR on the docs PR (#29) rather than basing both on the same `main` — the README auto/manual table only exists post-#29, so editing the `ship` row required #29 merged first. Avoided re-introducing the staleness #29 removed.

**Lessons learned:**
- The autonomy increase is reversible (flip the flag back) and bounded (merge stays human, verify-build gates pre-PR) — which is what made it shippable without a hard Stop-hook. The Stop-hook remains a deferred roadmap item for hard enforcement.
