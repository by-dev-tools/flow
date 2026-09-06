### README + workflow.md + config.example — surface auto-vs-manual reality, list skills in loop order, de-stale v1.0.0→v1.3.0
**Date:** 2026-05-30
**Branch:** `claude/nice-lamarr-3c30c0` (commit at push time)

**What was done:**
Docs/config correction PR, three coherent pieces:
- **README.md** — reordered the skill catalog from importance-order into **loop order** (the user's explicit complaint: "skills aren't listed in workflow order, confusing"). Added a **Fires** column (AUTO / MANUAL / BOTH) + a `Step · gate` column, a `⚠️ Cold-start reality` callout stating plainly that on a bare "build me X" only the auto-loading rules attach and nothing executable fires until typed, added the missing **`/flow:verify-build`** row, and fixed the header (`v1.2.5`→`v1.3.0`, `11`→`12 skills`). Expanded the one-line `## The loop` arrow into a numbered table naming every skill at its step and marking the three human pauses (Gate 1 plan, Gate 3 LOW-confidence, Gate 2 merge) + mechanical stops.
- **plugins/flow/docs/workflow.md** — de-staled `Bootstrap status (flow v1.0.0)` → `Shipped surface (flow v1.3.0)`; stripped every `(PR 2)` / `(PR 3)` / `[not yet shipped]` marker that described already-shipped surface (staff-review, security/a11y review, ship-spike, workflow-help, memory machinery, template dir) as future work; updated the skills cheat sheet + config-slot prose. (This change was pre-staged in the worktree from a prior session; verified and folded in as in-scope.)
- **template/base/flow.config.json.example** — expanded from 14 to all 21 documented slots (added `preflightCmd`, `sourceFilePatterns`, `uiFilePatterns`, and the four verify-build slots) so adopters reading the example discover the mechanical-preflight + behavioral-verification gates instead of shipping them off-by-default. (Also pre-staged; verified and folded in.)

**Why:**
A workflow-driven production-readiness audit surfaced that (a) the README presented skills in an order no reader could map onto the loop and never distinguished auto-fire from manual-typing, and (b) the canonical workflow doc the README points to as "the loop itself" still described half the shipped plugin as unshipped PR-2/PR-3 work — contradicting a v1.3.0 install. Both erode adopter trust. The 14-of-21 example config silently disabled the headline reliability + verification gates for anyone who only read the example.

**Design decisions:**
- Kept the README's "When to use each reviewer" matrix (a by-work-type view) alongside the new loop-order catalog rather than collapsing them — different lookups for different reader intents.
- The cold-start honesty note is deliberately blunt ("a typed-command toolkit with a thin auto-loaded guidance layer, not a loop that drives itself") because the gap between the "managed-autonomy loop" framing and the typed-command reality was the single biggest UX surprise the audit found.

**Technical decisions:**
- No code touched; markdown + JSON-with-comments only. No version bump (docs/config at root, same precedent as prior docs-only PRs). Skill/rule counts unchanged (12 skills, 4 rules) so no fan-out sweep needed beyond the version-string + skill-count edits in README, which were the contract change.
- Verified each pre-staged diff (`workflow.md`, `config.example`) before staging rather than committing an unreviewed change.

**Tradeoffs discussed:**
- Documenting today's manual reality vs the intended auto-ship end-state. Chose to describe what's shipped (manual) here and split the auto-ship capability into its own PR (`claude/auto-ship-readiness-trigger`) rather than write forward-looking docs about unbuilt behavior — the exact staleness class this PR removes.

**Lessons learned:**
- The audit found the most dangerous staleness wasn't wrong code but a canonical doc confidently describing shipped features as future work. De-staling docs is as load-bearing as fixing code when the doc is the adopter's map.
