### FB-0006: Per-diff doc-only early-exit in /flow:security-review (currently only prose, not structured)
**Date:** 2026-05-25
**Source:** review feedback (synthesized from md-manager PR 4 consumer-feedback report 2026-05-25)

**What was said:** md-manager PR #23 was docs+config only. `/flow:security-review`'s body says "skip if doc-only" in prose but has no structured early-exit gate — the orchestrator (or human) has to detect doc-only manually. By contrast, `/flow:accessibility-review` has a project-wide `uiSurface=false` gate (but lacks per-diff coverage; see FB-0007).

**Synthesized rule:** `/flow:security-review` Step 1 should add per-diff source-file detection paralleling FB-0007's a11y fix. Pattern (`${DEFAULT_BRANCH}` resolved via PR-1's 3-tier fallback chain — see FB-0008 snippet):

```sh
SOURCE_FILES_IN_DIFF=$(git diff "origin/${DEFAULT_BRANCH}..HEAD" --name-only | grep -E '\.(ts|tsx|js|jsx|py|rs|swift|go|rb|java|sh|mjs)$|\.json$|\.yaml$|\.yml$' || true)
if [ -z "$SOURCE_FILES_IN_DIFF" ]; then echo "[security-review] no source/config files in diff; skipping."; exit 0; fi
```

The source-file regex is necessarily heuristic; consider a `flow.config.json.sourceFilePatterns` slot for projects that want to override. Pair this PR with FB-0007 — same fix shape, same detection scaffolding, one PR.

**Applies to:** workflow, /flow:security-review, cost-of-review

**Validation:** 1 forced manual-skip-decision in md-manager PR 4. Every doc-only PR in any consumer triggers the same friction.
