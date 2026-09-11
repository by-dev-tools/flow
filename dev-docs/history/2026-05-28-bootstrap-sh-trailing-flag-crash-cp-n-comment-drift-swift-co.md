### bootstrap.sh — trailing-flag crash + cp -n comment drift + swift counter miss SAFETY
**Date:** 2026-05-28
**Branch:** `claude/dazzling-goodall-1ea214`
**Commit:** [SHA at commit time]

**What was done:**
Fixed three defects in `template/base/bootstrap.sh` (shipped in the install bundle), all surfaced by a reviewer-refutation spike that fanned three review stances over the file:
1. **BLOCKER (error handling) — trailing-flag crash.** The arg-parse loop did `--stack) STACK="$2"; shift 2` (same for `--project` / `--flow-dir`) with no guard. Under the script's `set -eu`, a flag passed as the final token (`bootstrap.sh --stack`, or the realistic typo `--stack web --project`) expanded `$2` unbound and aborted with a raw `bash: $2: unbound variable` (rc 1), bypassing the guided `⚠️ … exit 2` usage path every other failure uses. Added a `need_val` helper that checks `[ $# -ge 2 ]` before `shift 2` and routes a missing value to the existing usage/`exit 2` path. Applied uniformly to all three value-taking flags.
2. **NIT — `cp -n` comment/code drift.** Header (line 27), the `set -eu` rationale (line 32), and the Step A banner (line 113) all credited idempotency to `cp -n`, but `copy_n` actually uses an `[ -e "$dest" ]` precheck + plain `cp` (no `-n`). The comments also contradicted the accurate Step C note (BSD cp returns 1 on skip under set -e). Rewrote the three comments to describe the `[ -e ]`-guard reality and cite why real `cp -n` is deliberately avoided.
3. **NIT — swift counter miss.** The swift-only `safety.md` append/skip branches mutated state but never did `copied=$((copied+1))` / `skipped=$((skipped+1))`, unlike the structurally-parallel `.gitignore.append` block, so the `scaffold complete: N created, M skipped` summary undercounted on the swift stack. Added the increments.

**Why:**
A blind-vs-self refutation spike (see `dev-docs/research/dynamic-workflows-2026-05.md`) reviewed `bootstrap.sh`; the trailing-flag crash was independently found by all three stances and kept by both verification methods — the highest-confidence finding in the run, and a textbook FB-0010 fail-loud violation living in flow's own scaffolder. The two NITs were high-agreement findings worth folding into the same fix.

**Design decisions:**
- Route the missing-value case to the *existing* guided usage path rather than inventing a new error shape — consistency with every other failure in the script (single `⚠️ … run with --help for usage … exit 2` voice).

**Technical decisions:**
- `need_val` helper rather than inline `${2:-}` guards ×3 — DRY + uniform messaging, consistent with FB-0009's "consistency is the value" lineage. One guard shape for all three flags.
- Verified the only trailing-arg-prone `$2` sites are the three arg-parse cases; `$2` at the `copy_n`/`copy_tree` definitions are function-local params (always bound when called) and need no guard.
- Left the Step B "17 slots" line untouched: the spike's slot-count finding was adjudicated a false positive — "slots" is the schema property count (16 at b1c8e01, 17 at HEAD post-PR-M `preflightCmd`), not the example file's populated-key count.

**Tradeoffs discussed:**
- `need_val` helper vs per-case inline check: helper won for uniformity; cost is one extra function. Acceptable.
- Scope: the fix made the pre-existing `--help` verbosity (the `grep -E '^# '` dumps all column-0 comments, including section dividers and rationale, not just the usage header) marginally longer. Did NOT fix the `--help` greediness — out of scope for this task, logged as a FOLLOW-UP. Restricting scope to the three named defects is the discipline the spike itself reinforced.

**Verification:**
- `bash -n` clean.
- Reproduced all three trailing-flag cases → now emit `⚠️ <flag> requires a value` + `exit 2` (was `$2: unbound variable` rc 1).
- Existing paths unaffected: missing `--stack`, unknown arg, `--help` all behave as before.
- Real swift scaffold in a temp dir: first run `16 created / 0 skipped`, re-run `0 created / 16 skipped` — the matched totals prove every mutation is now counted in exactly one branch (idempotency invariant).

**FOLLOW-UP:**
- `--help` greps every `^# ` line, so it prints section dividers + rationale comments, not just the usage header (lines 2–28). Pre-existing; restrict the grep to the contiguous header block (e.g. stop at the first blank line). Surfaces when: next edit to `bootstrap.sh`'s `--help` handling.
