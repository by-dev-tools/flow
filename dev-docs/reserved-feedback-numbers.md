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

## Currently reserved (as of 2026-05-28)

⚠️ **Open arbitration:** `pr-m/verify-build-skill` (lucid-matsumoto-730ba0) drafts FB-0012 = "Check bundled Claude Code skills before drafting any new `/flow:*` skill" — but FB-0012 was claimed and shipped on 2026-05-28 by the bounded-retry preflight PR (squash `0cf642e`, #22) as "Bounded-retry agent loops…". The verify-build branch must renumber to **FB-0013** at its next rebase and run `git grep -nE 'FB-0012' -- dev-docs/ plugins/flow/` to sweep cross-references (currently lightweight: 1 textual entry + by-name handoff-doc references). The drafted "PR M" letter for the verify-build PR also collides — PR M is now taken by bounded-retry; suggest **PR N** at ship time, deferring after sweet-hellman's queued PR N/O/P if any of those advance first.

- **FB-0013 (suggested next claim)** — `pr-m/verify-build-skill` (lucid-matsumoto-730ba0) — "Check bundled Claude Code skills before drafting any new `/flow:*` skill." Pending re-letter and renumber sweep.
- **FB-0014** — `pr-r/flow-init-skill` (thirsty-napier-5a3ff4) — "Init skill must default to additive + per-item human approval; never overwrite or delete existing files." Provisional letter `PR R` to clear past lucid-matsumoto's pending re-letter (likely Q) and sweet-hellman's queued N/O/P; finalize at ship time. Plan landed 2026-05-28 in `dev-docs/plan.md` § "PR R — `/flow:init` skill (planning; queued)"; ship-vs-defer decision pending given prior v2.0+ backlog placement at `dev-docs/plan.md:891`.
- **FB-0015** — `pr-q/verify-build-skill` (lucid-matsumoto-730ba0) — "Check bundled Claude Code skills before drafting any new `/flow:*` skill." Cascaded through FB-0012 → FB-0013 → FB-0014 → FB-0015 as collisions surfaced (FB-0012 = bounded-retry shipped in PR M; FB-0013 reserved by PR P's same-model-critic plan; FB-0014 claimed by PR R's init-skill plan). PR letter Q preserved per PR R's reservation note. All cross-file references swept to FB-0015 at rebase time. Phases 1-9 complete on lucid-matsumoto; about to ship as v1.3.0.

## Audit trail (past collisions, kept for institutional memory)

- **2026-05-28** — Cross-worktree audit (post-PR-J merge at squash `2e8ab3c`) discovered three in-flight FB conflicts: sweet-hellman's drafted FB-0011 ("bounded-retry") vs main's merged FB-0011 ("autonomy bar"); and sweet-hellman + lucid-matsumoto both drafting FB-0012 with different concepts. At audit time, sweet-hellman had **20 FB-0011 references across 5 files** and **12 FB-0012 references across 2 files**; lucid-matsumoto had 1 FB-0012 textual entry + by-name handoff-doc references. None had reached rebase yet — no silent overwrite had occurred. PR K1 (this file's introduction) landed the protocol surface ahead of either rebase.
- **2026-05-28 (same day, resolution)** — Sweet-hellman rebased + shipped at `0cf642e` (#22) as v1.2.6 = "PR M (bounded-retry mechanical preflight)". They **renumbered drafted FB-0011 → FB-0012 and swept all 20 cross-file references cleanly before pushing** — no silent overwrite occurred at merge time. PR J's FB-0011 ("autonomy bar") survives untouched on main. The "PR M" letter for the verify-build branch also collided with this shipping PR's claim of "PR M"; lucid-matsumoto's PR will need a different letter at its ship time. Validation that the FB-0010 grep-first-edit-second discipline works when applied; PR K1's protocol file makes it harder to forget the sweep but doesn't change the mechanics. Remaining open item: lucid-matsumoto's FB-0012 (verify-build) → must renumber to **FB-0013**, plus PR letter change.
