### SAFETY: audit-skips can't silently no-op on a broken handoff + Swift preflight `ls -d` glob fix (v1.21.1)
**Date:** 2026-07-29
**Branch:** claude/audit-skips-loud-plus-swift-preflight-glob (commit on this branch; SHA lands with the PR)

**What was done:**
Two harvested bug fixes (drained from the `/flow:contribute` queue and applied directly per FB-0073, not parked in a draft):
1. **audit-skips silent-no-op closed (SAFETY — error-handling contract flip).** `skills/audit-skips/lib/skip-audit-checks.py` used to `print({"error": …, "stages": []})` and **`return 0`** on a present-but-unreadable/malformed handoff — indistinguishable from a genuine absent-handoff standalone run, so the whole skip-legitimacy gate read "no stage report to audit" and silently no-op'd. Now it prints the diagnostic to **stderr** and **`return 1`** (a valid-but-empty report still exits 0). The audit-skips SKILL shell block captures the non-zero exit into a distinct `engine_error` JSON field (was `2>/dev/null`-swallowed) and the SKILL prose routes `engine_error` (loud → `[decision-required]` draft manifest) vs the absent-handoff `note` (the only clean no-op) vs a valid-empty audit. Implements the pre-queued roadmap item "audit-skips malformed-handoff vs empty-standalone disambiguation."
2. **Swift preflight `ls -d` glob fix.** `template/stacks/swift/tools/preflight/check.sh` used `ls *.xcodeproj` / `ls *.xcworkspace`; because those are directory **bundles**, bare `ls` lists their *contents* (`project.pbxproj`, …), so `WORKSPACE_OR_PROJECT` became `-project project.pbxproj` and xcodebuild failed on every auto-discovered project. `ls -d` lists the bundle name xcodebuild expects.

New eval cases in `run_skip_audit_evals.py` (malformed→nonzero + stdout-clean + stderr-diagnostic + valid-empty→zero). Version 1.21.0 → 1.21.1.

**Why:**
Both were consumer-cold-run bugs harvested via `/flow:contribute`, and two of them were **reproduced in this very session**: the audit-skips fork couldn't see the parent's `/tmp` handoff (a related transport issue) and I had to run the engine by hand; the `ls`-bundle bug is bug 2 of the same Swift cold-run whose bug 1 (rigor-marker false-drift) shipped in #82. The silent-no-op is the FB-0062 failure-open class (a gate that fails to "clean, nothing to check") applied to an *input-read* error.

**Design decisions:**
- **The deep fix is the engine's exit code, not per-caller guards (SAFETY).** Making `skip-audit-checks.py` exit non-zero on an unreadable report restores the failure/empty distinction *at the source*, so every caller can tell them apart. A prototyped `/flow:ship` Step 2a per-caller re-run guard was **removed** after the `/simplify` altitude lens flagged it as a symptom-patch that (a) duplicated the engine invocation and (b) treated a *possibly-systemic* fork-`/tmp`-visibility issue in one caller. That transport question is routed to `roadmap.md` § Exploration instead (candidates: a shared repo-relative handoff path, or run the deterministic engine in the parent and fork only the judgment layer).
- **A malformed report and an absent report both exit 1 today** (the shell's `[ -f "$STAGES" ]` filters absent-but-expected first). Noted in the Exploration entry: if the parent-run-engine option is chosen later, the engine must own the absent-vs-malformed split (a distinct code or `--require-report`).

**Technical decisions:**
- Diagnostic to **stderr**, stdout left clean, so the SKILL's `if OUT=$(python3 … 2>"$ENGINE_ERR")` cleanly routes success vs failure; the `engine_error` field wraps the captured stderr via `jq -Rs .` (sound JSON-string escaping; a safe-constant fallback if `jq` is absent).
- The audit-skips SKILL shell block runs inside a single-backtick `` !`…` `` dynamic-context span — an inner backtick truncates it (the FB-0010 backtick-truncation class the staff-engineer lens caught mid-review); the block is now backtick-free and `bash -n`-verified.

**Tradeoffs discussed:**
- Bumped patch version (1.21.1) for an internal robustness fix rather than leaving it under 1.21.0 — honest that shipped-skill behavior changed; description blobs left un-accreted per the roadmap "cap the description blobs" item.
- Applied directly to a **ready** PR (not a draft) per FB-0073 — the fixes are eval-pinned + staff-reviewed + security-reviewed; draft state would be friction, not a gate.

**Spec-walk (this PR — declares the behavior changes `/flow:audit-coverage` flagged as undeclared; each pinned by its verification):**
- [x] `skip-audit-checks.py` exits **non-zero** on a malformed/unreadable report (stderr diagnostic, clean stdout) and **0** on a valid-but-empty one — pinned by `run_skip_audit_evals.py` (`malformed-report-exits-nonzero`, `-stdout-clean`, `-stderr-diagnostic`, `valid-empty-report-exits-zero`; full suite green).
- [x] audit-skips SKILL routes `engine_error` (loud) vs absent-handoff `note` (no-op) vs valid-empty — verified by the block parsing (`bash -n`) + the prose distinguishing all three shapes.
- [x] Swift `check.sh` resolves the bundle **name** not its contents — verified: `ls -d *.xcodeproj` returns `Foo.xcodeproj`, bare `ls` returned `project.pbxproj`.

**Lessons learned:**
- A mechanical engine that returns error-as-data with a success exit code cannot be distinguished from an empty result by an exit-code-checking caller — the FB-0062 failure-open class hiding in an input-read path. Exit codes are the honest channel for "I could not do my job."
