# Reserved feedback numbers (in-flight branches)

Mechanical defense for `FB-XXXX` collisions across parallel branches. Before drafting a new `FB-XXXX` entry in `dev-docs/feedback.md`, claim its number here. When the PR ships, `/flow:ship`'s synthesis step removes the line as part of the doc updates.

## Why this exists

`dev-docs/feedback.md`'s textual conflict only catches the *single* insertion point where the new entry is added. FB-XXXX numbers also live in `plan.md`, `history.md`, `CHANGELOG.md`, marketplace.json descriptions, schema JSON comments, and per-PR research docs. Those cross-references survive a feedback.md-only rebase resolution and silently point at the wrong concept once a second branch claims the same number — see `dev-docs/feedback.md` § FB-0010 "fan-out contradiction" sub-class.

This file is the **claim-time defense** (catches collisions before either branch invests in cross-file references). The **rebase-time + review-time defenses** — `/flow:doctor` Check 6 (mechanical FB-collision check vs `origin/main`) and `lens-staff-engineer.md`'s FB-number cross-file hunt — ship in PR K.

## Protocol

1. Before adding any new `FB-XXXX` entry in `feedback.md`, claim its number here.
2. Add one line per branch under `## Currently reserved`: `- FB-XXXX — \`branch-name\` — "short headline" — owner-worktree-slug`.
3. Push your reservation immediately (don't batch it with the entry itself — the early push is the race-detection mechanism).
4. If another branch races you to the same number, the merge conflict on this file catches it. Renumber to the next available.
5. When your PR ships, `/flow:ship` removes your line during step 4 (doc updates).

If you find this file with no `Currently reserved` lines, no in-flight branch is racing for a number. Still add your reservation before drafting the entry — another branch may start between your check and your commit.

## Currently reserved (as of 2026-06-03)

- **FB-0013** — same-model-critic-collusion / auditor model-diversity (**PR P**) — plan-level reservation; see `dev-docs/plan.md` PR P + `roadmap.md`. No active branch yet — add a worktree slug here when PR P starts.
- **FB-0014** — `pr-r/flow-init-skill` (thirsty-napier-5a3ff4) — "Init skill must default to additive + per-item human approval; never overwrite or delete existing files." Provisional letter `PR R`; finalize at ship time. Plan landed 2026-05-28 in `dev-docs/plan.md` § "PR R — `/flow:init` skill (planning; queued)".

## Audit trail (past collisions, kept for institutional memory)

- **2026-05-28** — Cross-worktree audit (post-PR-J merge at squash `2e8ab3c`) discovered three in-flight FB conflicts: sweet-hellman's drafted FB-0011 ("bounded-retry") vs main's merged FB-0011 ("autonomy bar"); and sweet-hellman + lucid-matsumoto both drafting FB-0012 with different concepts. At audit time, sweet-hellman had **20 FB-0011 references across 5 files** and **12 FB-0012 references across 2 files**; lucid-matsumoto had 1 FB-0012 textual entry + by-name handoff-doc references. None had reached rebase yet — no silent overwrite had occurred. PR K1 (this file's introduction) landed the protocol surface ahead of either rebase.
- **2026-05-28 (same day, resolution)** — Sweet-hellman rebased + shipped at `0cf642e` (#22) as v1.2.6 = "PR M (bounded-retry mechanical preflight)". They **renumbered drafted FB-0011 → FB-0012 and swept all 20 cross-file references cleanly before pushing** — no silent overwrite occurred at merge time. PR J's FB-0011 ("autonomy bar") survives untouched on main. The "PR M" letter for the verify-build branch also collided with this shipping PR's claim of "PR M"; lucid-matsumoto's PR will need a different letter at its ship time. Validation that the FB-0010 grep-first-edit-second discipline works when applied; PR K1's protocol file makes it harder to forget the sweep but doesn't change the mechanics. Remaining open item: lucid-matsumoto's FB-0012 (verify-build) → must renumber to **FB-0013**, plus PR letter change.
- **2026-05-29** — Cleanup pass (this PR, post-#27 merge). Two reservations cleared as **shipped**: **FB-0015** (verify-build / "check bundled skills first") shipped in **PR Q v1.3.0** (`aeadcb7`, #26) — the verify-build cascade FB-0012→0013→0014→0015 is fully resolved, so the prior "Open arbitration" note and the stale "FB-0013 (suggested next claim) = verify-build" bullet were removed (verify-build is **FB-0015**, NOT FB-0013; FB-0013 is the same-model-collusion / PR P reservation). **FB-0016** (dynamic-workflows reviewer-refutation spike, `claude/dazzling-goodall-1ea214`) shipped in **#27** (`96604d9`) — reservation removed per protocol. Net reserved after cleanup: FB-0013 (PR P, plan-level) + FB-0014 (PR R). Confirms the dev-side `/ship` gap: it does not auto-remove shipped reservations the way `/flow:ship` step 4 does, so a manual cleanup pass is needed when shipping via `/ship`.
- **2026-06-03** — Post-merge cleanup. Cleared four shipped reservations: **FB-0019** (flow-run PR descriptions) shipped in **#32** (v1.4.1); **FB-0034** (resolution-confidence + draft-routing), **FB-0035** (verify-build placement), **FB-0036** (reviewer/ship-spike model-invocability) all shipped in **PR U / #31** (v1.5.0, squash `ef75472`). Net reserved after cleanup: **FB-0013** (PR P, plan-level) + **FB-0014** (PR R). The 0020–0033 numbers remain held by other in-flight worktree branches (the cross-session high-water the #33 handoff flagged); PR U's 0034–0036 sat above them deliberately and merged without collision. Same dev-side-`/ship` gap as 2026-05-29 — these didn't auto-clear at merge; swept manually here.
