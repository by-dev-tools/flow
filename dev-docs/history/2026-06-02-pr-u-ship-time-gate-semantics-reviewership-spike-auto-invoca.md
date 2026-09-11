### PR U — ship-time gate semantics + reviewer/ship-spike auto-invocability (v1.5.0) SAFETY
**Date:** 2026-06-02
**Branch:** `claude/pr-u-ship-gate-semantics` (rebased onto `main` @ `1eb4ad9` v1.4.2; squash SHA filled at merge)

**What was done:** Combined PR T umbrella Facets 2 + 3 + 5 (Facet 5 absorbed from the abandoned "Track A") into one PR:
- **Facet 5 — auto-invocability:** flipped `disable-model-invocation: true → false` on `audit-plan`, `audit-completion`, `critique-plan`, `ship-spike`. README + workflow.md relabeled accurately (the three reviewers → BOTH, never cold-start; `ship-spike` → auto but judgment-gated). FB-0010 grep confirms zero MANUAL survivors for the four.
- **Facet 2 — resolution-confidence + draft-routing:** `[auto-fixable]`/`[decision-required]` axis on security/a11y; `/flow:ship` routes decision-required findings (and non-converging verify-build regressions) to a **draft PR + `🚫 NOT READY TO MERGE` manifest** instead of a silent proceed or hard halt. Integrated into the v1.4.1 `## Flow run` PR body.
- **Facet 3 — verify-build placement:** ship-time verify-build reframed as a confirmation re-run (discovery → Step 8/9 readiness boundary; visual sign-off folds into the merge gate).
- Fixture `evals/fixtures/resolution-confidence-routing/`; v1.4.2 → **v1.5.0**; FB-0034/0035/0036.

**Why:** Closes the asymmetry where security/a11y BLOCKERs had no ship-stopping gate while verify-build hard-halted — both could yield a best-effort not-ready PR or an arbitrary mid-loop stop. Operationalizes the two-gate thesis: escalation routes INTO the merge gate (draft), and no reviewer/ship-spike skill is itself a gate.

**Design decisions:**
- **Draft-routing, not hard-halt** (plan-critic BLOCKER): auto-advance-into-ship stays verify-build-PASS-gated (PR S predicate + FB-0018 invariant unchanged); only ship-*internal* unresolvable findings route to draft. Invariant: no merge-ready PR on a non-PASS build.
- **Visual sign-off → merge gate** (plan-critic REDIRECT, user decision): preserves exactly two human gates.
- **Facet 5 depends on #33** (session-discovery fix): the `context: fork` reviewers need it to resolve transcripts from worktree cwds, else they auto-invoke but audit nothing. The parallel session that merged #33 live-verified fork-path parity is PASS once #33 is in base — closing the original auditor UNVERIFIED concern.

**Technical decisions:**
- Manifest is an in-memory per-run accumulator (Step 2 → Step 7); machine-consumable sentinel shipped as the *producer*; the *consumer* (CI/doctor merge-block + persistence breadcrumb) routed to roadmap as the deliberate second half.
- **Rebase collision reconciliation (FB-0010):** collided with merged #32 ("PR T — Flow-run descriptions") on the **PR-T letter** (this PR is "PR U"; the planning umbrella keeps the "Managed-autonomy confidence" name) and on **FB-0019** (renumbered this PR's entries → **FB-0034/0035** + added **FB-0036**, above the cross-session high-water flagged in the #33 handoff). Draft-manifest integrated into #32's `## Flow run` body rather than reverting it.

**Tradeoffs discussed:**
- Resolution-confidence self-tagging is an LLM judgment (MEDIUM) — mitigated by default-to-decision-required + the fixture pinning the boundary.
- ship-spike left on hard-halt (separate scope; roadmap follow-up).

**SAFETY:** edits `ship/SKILL.md` (ship contract) + the reviewer prompts + 4 skill invocation flags. Preserved: ship never merges; PR S auto-advance predicate; FB-0011/0012/0018 contracts. Pre-ship caught a self-inflicted secret-scanner trap (fixture used a realistic live-key-prefixed literal → push protection scans history → soft-reset + clean re-commit, not the unblock URL). staff-review (4 lenses) returned 0 BLOCKERs.
