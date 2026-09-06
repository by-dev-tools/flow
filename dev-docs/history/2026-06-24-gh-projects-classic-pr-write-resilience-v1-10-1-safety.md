### `gh` Projects-classic PR-write resilience (v1.10.1) — SAFETY
**Date:** 2026-06-24
**Branch:** claude/vigorous-faraday-fcd39c
**Commit:** (this PR — repurposed #56)

**What was done.** Documented a `gh`-API fallback in `/flow:ship` Step 7 (canonical block) and `/flow:staff-review` Step 7 (reference) for the Projects-classic GraphQL deprecation: on classic-projects repos with affected `gh` versions, `gh pr edit` / `gh pr ready` / `gh pr view --json` fail with `GraphQL: Projects (classic) … projectCards` even when only the body/draft state is being touched. The fallback sets the body via REST (`gh api -X PATCH .../pulls/N -F body=@file`) and toggles draft via the `markPullRequestReadyForReview` / `convertPullRequestToDraft` mutations (neither queries `projectCards`). Bumped to v1.10.1 + backfilled the v1.10.0 CHANGELOG entry that #57 omitted. (The README version stamp this originally also bumped was removed entirely by #58's README rewrite, landed during the rebase — so the changelog is now the canonical version-history surface.)

**Why.** This was the "secondary, lower-confidence" item in the FB-0056 dogfood report. It became the *only* salvageable delta after **#57** independently shipped the report's two primary integrity gaps as v1.10.0 while this branch (PR #56) was implementing the same scope (per-criterion provenance + a `rigor-marker.py` commit-invariant + a diff-derived judged no-plan path — stronger than #56's top-level-provenance + prose-self-attestation approach). Rather than force-merge a duplicate v1.10.0, #56 was reset to main and repurposed down to this non-duplicated delta (the user chose "repurpose" over "close + reopen").

**Design decisions.**
- **Documented prose, not a helper script.** A `gh`-API wrapper script doing GraphQL mutations is easy to get subtly wrong and can't be tested here (no classic-projects repo in CI). Clear prose the agent adapts is more robust than an untested script — matches the repo's lean bar.
- **Canonical block in ship, reference in staff-review** (not duplicated) — FB-0010 fan-out defense: one source of truth, staff-review points at it.
- **Backfilled #57's missing v1.10.0 CHANGELOG entry** rather than letting the consumer-facing changelog skip 1.9.1 → 1.10.1 and hide the major integrity release.

**Tradeoffs discussed.** The bulk of PR #56's original work (the full provenance/no-plan implementation, a producer-contract eval, fixtures) was **discarded** as superseded by #57's more complete version — the honest outcome of a cross-worktree collision the stale-base gate caught at ship time (the same FB-0008/FB-0010 collision class the reserved-numbers protocol exists for). The `gh`-resilience fallback is documentation only; it does not change renderer or gate behavior.

**SAFETY:** adds a fallback path to the ship pipeline's PR-write step (ship/SKILL.md is a safety-critical surface); it strengthens resilience and never downgrades existing error handling — the standard `gh pr` path stays primary and the fallback fires only on the explicit `projectCards` error signal.
