### SAFETY: /flow:land — post-merge doc-currency skill (v1.12.0, FB-0061)
**Date:** 2026-06-28
**Branch:** claude/flow-land
**Commit:** `6d780b3` (on branch; final SHA in the PR)

**What was done:**
New human-invoked skill `/flow:land <PR#>` (`plugins/flow/skills/land/SKILL.md`, `disable-model-invocation: true`) that runs the post-merge reconciliation `/flow:ship` structurally can't: verify the PR is merged (`gh pr view --json state,mergedAt`; fail loud + edit nothing otherwise) → flip the item to "merged (#N)" across roadmap/plan/history + move it to Recently-shipped (gh + doc-scan discovery; WARN-not-silent on no match) → CHANGELOG-currency check → late `§5c` visual-history distill if a blocked visual pass since completed → clear reserved FB/VH numbers → open a small `docs: land #N` PR (never merges; idempotent on re-run). Backed by the stdlib `lib/land-helpers.py` (deterministic `changelog-check` + `clear-reservation`) + `evals/run_land_evals.py` (wired into CI). Registered across plugin.json + marketplace.json + workflow.md (surface bullet + cheat-sheet + Step 11) + workflow-help; version → v1.12.0.

**Why:**
Closes FLOW-1 (the recurring stale-`main` after merge) + FLOW-5b (the late visual-history distill) from the v1.8.0 health-tracker dogfood report. See FB-0061.

**Design decisions:**
- **Separate human-invoked skill, not a ship step** — Claude can't merge, so the reconciliation must run after the human merges (FB-0061). `disable-model-invocation: true` so it never auto-fires mid-loop.
- **Narrative status-flip is agent judgment** (like `/flow:ship` Step 5a) — the docs are free-form, so a regex flip would be FB-0010-fragile; the helper owns only the unambiguous deterministic bits (changelog-check, reserved-number clearing).
- **Reuse `§5c`, don't fork** the visual-history distill — one record format.

**Technical decisions:**
- **Rebased off the superseded FLOW-2 work (FB-0051).** The original PR was stacked on the v1.10.1 REST-PR-body commit; after #56 shipped that to main and #59 added the ship-spike delta, this branch was reset to `main` and reduced to the genuinely-new `/flow:land` skill. Version/FB renumbered to avoid collisions (v1.11.0→v1.12.0, FB-0058→FB-0061).
- Helper's `changelog-check` uses a `(?![\d.])` lookahead so `v1.10` doesn't match `v1.10.1`; `clear-reservation` is word-boundary + FB/VH-id-guarded + idempotent.
- Step 1b branch creation reuses an existing `land-<N>` branch on re-run (idempotency); Step 2 discovery guards the empty-`HEADREF` alternative so the no-match WARN stays reachable (both staff-review BLOCKERs from the PR-2 review, pinned by `run_land_evals` skill-6/7).

**Tradeoffs discussed:**
- **Dropped a deterministic status-flip helper** — considered, rejected as regex-fragile over free-form narrative (FB-0010). The agent flips in context; the helper stays to the unambiguous operations.

**Lessons learned:**
- Reconciliation gated on an event Claude can't perform (the merge) must be a separate human-invoked step (FB-0061).
