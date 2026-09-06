### PR description opens with a plain-language summary + Scope label (v1.15.0, FB-0065)
**Date:** 2026-07-07
**Branch:** claude/relaxed-elbakyan-55dac6
**Commit:** merged #68 @ c80a1e9

**What was done:**
Restructured the `/flow:ship` and `/flow:ship-spike` PR-body template so `## Summary` now opens, top-down, with (1) a **Scope:** label — `docs-only | new feature | bugfix | refactor | test | chore | mixed` (`spike` for `/flow:ship-spike`) — and (2) a one-or-two-sentence plain-language description of what changed that a reader can follow without opening the diff, above the existing why-bullets. Added the authoring instruction that governs it (write the scope + plain-language line for a reader at the merge gate; no internal codenames or jargon). Updated `plugins/flow/docs/workflow.md` § "The PR body documents the full flow run" to describe the new `## Summary` shape, and the `resolution-confidence-routing` eval fixture's expected PR body to show the `**Scope:**` opener.

**Why:**
The PR body's first section was a bare list of "why this exists" bullets — no at-a-glance statement of *what kind of change* this is or *what it does* in plain terms. A human at the merge gate (or a teammate skimming the PR list) had to infer scope from the diff or the Flow-run table. Leading with a scope label + a jargon-free what-changed line makes the review's first read immediate.

**Design decisions:**
- **Folded into the existing `## Summary`, not a new heading.** A competing `## TL;DR`/`## Overview` heading would duplicate the summary role and fight the why-bullets. One section now reads scope → what → why.
- **Scope is a fixed small vocabulary**, mirroring flow's existing skip-reason and status-cell conventions, so a reviewer can triage what kind of review the change needs from one token; `mixed` only when two categories genuinely co-lead.
- **Plain-language line bars internal codenames (FB-XXXX, PR letters) and jargon** — consistent with the `feedback_direct_no_fluff_copy` preference and the external-reader posture of `docs/how-it-works.md`.

**Technical decisions:**
- Template-and-prose only. The mechanical `## Test plan` renderer (`render-test-plan.py`) and the `## Flow run` table machinery are untouched — no code path changed, so no new eval; the one eval fixture edit keeps the resolution-confidence expected-output in sync (FB-0010 fan-out discipline: the template lives in ship, ship-spike, workflow.md, and the fixture — all four updated together).

**Tradeoffs discussed:**
- Version bump vs. treat-as-docs: bumped to v1.15.0 because the change alters the PR-body *contract* every consumer's `/flow:ship` emits (user-visible output), unlike the purely-additive `docs/how-it-works.md` (#65) which stayed on v1.14.0.

**Lessons learned:**
- The worktree lost this session's uncommitted edits mid-session and the branch was 1 commit behind `origin/main`; re-verified file state with `git status` + `grep` before trusting "edits applied," rebased to clear the stale-base gate, and re-applied against current file contents. The stale-base gate (FB-0008) and a `git status` sanity check caught what an assume-my-edits-persisted flow would have shipped as an empty diff.
