### FB-0007: Per-diff non-UI early-exit in /flow:accessibility-review (uiSurface=true projects shipping docs-only)
**Date:** 2026-05-25
**Source:** review feedback (synthesized from md-manager PR 4 consumer-feedback report 2026-05-25)

**What was said:** md-manager's `flow.config.json` declares `uiSurface: true` (correct — the project has UI). md-manager PR #23 was docs+config only; no UI files in the diff. `/flow:accessibility-review` still triggered full agent spawn against the diff, returned "nothing to review," and the spawn cost was wasted. The `uiSurface: false` early-exit gate flow ships protects backend/CLI/library consumers but doesn't protect UI-surface projects shipping docs-only PRs.

**Synthesized rule:** `/flow:accessibility-review` Step 1 should pair the existing `uiSurface=false` project-wide gate with a per-diff non-UI detection. Pattern (`${DEFAULT_BRANCH}` resolved via PR-1's 3-tier fallback chain — see FB-0008 snippet):

```sh
# Existing: project-wide early-exit
UI_SURFACE=$(cat flow.config.json 2>/dev/null | jq -r '.uiSurface // true')
if [ "$UI_SURFACE" = "false" ]; then echo "[a11y-review] uiSurface=false; skipping."; exit 0; fi

# NEW: per-diff early-exit
UI_FILES_IN_DIFF=$(git diff "origin/${DEFAULT_BRANCH}..HEAD" --name-only | grep -E '\.(tsx|jsx|vue|svelte|css|scss|html)$|^(src|app|packages/ui)/' || true)
if [ -z "$UI_FILES_IN_DIFF" ]; then echo "[a11y-review] no UI files in diff; skipping."; exit 0; fi
```

The UI-file regex is necessarily heuristic; consider a `flow.config.json.uiFilePatterns` slot for projects that want to override (e.g., monorepos with non-standard layouts). Pair this PR with FB-0006 — same fix shape, same detection scaffolding, one PR.

**Applies to:** workflow, /flow:accessibility-review, cost-of-review

**Validation:** 1 wasted spawn in md-manager PR 4. Every consumer with `uiSurface: true` will hit this on every docs-only PR.
