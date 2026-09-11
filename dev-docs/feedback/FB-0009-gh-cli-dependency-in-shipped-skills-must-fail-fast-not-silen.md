### FB-0009: `gh` CLI dependency in shipped skills must fail-fast, not silently 127
**Date:** 2026-05-25
**Source:** review feedback (synthesized from md-manager PR 4 consumer-feedback report 2026-05-25)

**What was said:** md-manager's PR 4 sibling-validation worktree (`~/dev/md-manager-pr4-validate`) lacked `gh` CLI. `/flow:ship` Step 1 (`gh pr list` for PR-OPEN detection) fell back gracefully via the `2>/dev/null` swallow. Step 7 (`gh pr create`) did NOT fall back — exit 127 with no diagnostic. The umbrella owner had to take over and run `gh pr create` from a worktree that had it installed.

**Synthesized rule:** Every flow skill that invokes `gh` (or any other external CLI not guaranteed by Claude Code) must fail-fast at Step 1 with a clean install hint, not at the invocation site with `exit 127`. Pattern: `if ! command -v gh >/dev/null 2>&1; then echo "⚠️ /flow:<skill> requires the gh CLI. Install: brew install gh (macOS) or https://cli.github.com" >&2; exit 1; fi`. Add to `/flow:ship` Step 1, `/flow:staff-review` Step 1 (gh-pr-list optional but used), and `/flow:ship-spike` Step 1 (`gh pr create` mandatory). Document `gh` as an install prerequisite in `docs/bootstrap.md` + `docs/migration.md` Step 1 sections. Same shape would apply to any future `jq`, `git`, or `node` dependency that flow assumes — fail-fast at the workflow entrypoint, not at the invocation site.

**Applies to:** workflow, dependency hygiene, error UX

**Validation:** 1 BLOCKER in md-manager PR 4 sibling worktree; recovery cost was a worktree switch + manual `gh` invocation. Could have been a clean stop with install hint at workflow entry.
