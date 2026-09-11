### CI workflow + merge queue ruleset on main — mirror md-manager structure  `SAFETY`
**Date:** 2026-05-25
**Branch:** claude/charming-goldwasser-f8a7b2
**Commit:** [this PR]

**What was done:**
1. Added `.github/workflows/ci.yml` with two jobs (`evals`, `security`) triggered on `pull_request:` + `merge_group:`. Both run Python stdlib invocations of the existing eval runners — no new deps. Concurrency-grouped on event + ref so superseded runs cancel.
2. Applied a GitHub ruleset on `main` mirroring md-manager's structure: deletion-block, non-fast-forward, required linear history, PR-required with squash-only merges (0 required reviewers), required status checks (`evals` + `security` — 2 contexts vs md-manager's 3, since flow's testable surface is different), and a merge queue (squash, ALLGREEN grouping, max 1 build / max 5 merge / 5-min wait / 60-min timeout). Every parameter on every rule matches md-manager exactly except the status-check context names + count, which differ by design.
3. **`SAFETY`** — wired 3 missing check types into `plugins/flow/evals/run_evals.py` (`severity`, `finding_count`, `reference_rule_contains`) so the 3 plan-critic fixtures (`scope_drift_form_fix`, `spec_violation_bundled_ui`, `internal_incoherence_jwt_migration`) stop failing under the runner. These keys were already in `ground_truth.yaml` from PR 1 but had no rule implementation; the runner returned `unknown=<key>` for them. Now: `severity` matches `· {value lower} ·` in output, `finding_count` regex-counts `^ISSUE(\s+N)?\s+·` lines on raw output, `reference_rule_contains` substring-matches the value in lowercased output. Existing pass/skip behavior preserved for the 5 other cases.

**Why:**
md-manager has a merge queue; flow had no branch protection, no CI, and no merge queue. Setting it up "in the same way" gives flow the same shipping discipline: every PR must clear evals + security before landing, merges are squash-only, history stays linear. This is the lightest layer of the loop's mechanical gates — feedback compounds when every change is forced through the same pipeline.

**Design decisions:**
- **`evals` + `security` as required checks** (vs. only `security`, vs. no required checks). User picked both. Required also fixing the 3 broken eval cases — a one-edit fix that lets the regression surface ship as a real gate from day one rather than as a follow-up.
- **No required reviewers (0).** Mirrors md-manager. Solo-dev cadence; the loop's human gate is plan approval, not PR review.
- **Squash-only.** Mirrors md-manager. Keeps `main` linear and each PR atomic.
- **Merge queue grouping = `ALLGREEN`** with `max_entries_to_merge: 5` and `min_entries_to_merge_wait_minutes: 5`. Mirrors md-manager exactly — at flow's volume, batching is unlikely to fire, but the config is identical so behavior is predictable when it does.

**Technical decisions:**
- **Eval harness check additions kept minimal** — three small `if key == …` branches in `check_required`. No restructuring of the dispatch, no new helper functions, no changes to `load_ground_truth` or `render_context`. The runner's exit-code contract (0 if no failures, 1 otherwise) is preserved.
- **`finding_count` counts on raw `output`**, not lowercased `text`, because `ISSUE` is uppercase in the schema and the regex is anchored on it. Other checks use lowercased `text` for case-insensitive substring matching, consistent with prior keys.
- **Workflow runs `python3` directly** (no `pip install`); flow declares stdlib-only.
- **Ruleset applied via `gh api POST /repos/by-dev-tools/flow/rulesets`** with the JSON payload structurally identical to md-manager's except in the `required_status_checks` list — md-manager has 3 contexts (`typecheck`/`build`/`test`); flow has 2 (`evals`/`security`).

**Post-ship audit findings (retroactive `/flow:security-review` + `/flow:audit-completion` against PR #14):**
- **Audit-completion finding 1 — Unverified completion** ("ready to merge via the queue"): CI green on `pull_request:` event ≠ behavioral verification of the queue. End-to-end merge-queue exercise (PR enters queue → `merge_group:` CI fires → PR lands) is the missing check. Action: hold the "ready" claim to "ruleset + CI in place; queue path untested" until PR #14 is actually queued.
- **Audit-completion finding 2 — Unverified completion** ("byte-for-byte"): corrected above. The required-status-checks list differs in size (2 vs 3) and contents by design; "structurally identical except for status-check contexts" is the accurate framing.
- **Security NITs:** (a) `actions/checkout@v4` / `actions/setup-python@v5` use major-version pins rather than commit SHAs — matches md-manager's posture deliberately; tightening pinning is a project-wide policy choice, not a flow-only one. (b) `python-version: '3.11'` hardcoded across two jobs — fine; multi-version matrix only needed if/when version-compat issues surface. No BLOCKERs found.

**Tradeoffs discussed:**
- Required checks set: only `security` (no eval-fix scope) vs. both (fix evals first). User picked both → fixed evals.
- Whether to gate the merge queue on a CI workflow that didn't yet exist on `main`. GitHub evaluates required status checks against PR head / merge_group SHAs, not historical default-branch runs, so applying the ruleset alongside the workflow PR works — this PR's own merge_group run satisfies the gate.

**Lessons learned:**
- The `unknown=<key>` failures from `run_evals.py` had been latent since PR 1 — running the harness end-to-end exits 1 today on `main`. Worth treating that exit code as part of the PR-1 acceptance bar in retrospect; the merge queue setup surfaces it for free.
