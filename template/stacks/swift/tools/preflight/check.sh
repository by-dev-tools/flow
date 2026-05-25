#!/usr/bin/env bash
# Swift-stack preflight runner. xcodebuild + xcodebuild test + swift-format lint.
# See template/stacks/web/tools/preflight/check.mjs header for the workflow contract.
#
# Exit codes: 0 = green, 1 = red gate, 2 = script/env error.
#
# Required env: macOS with Xcode + swift-format installed.

set -u
TAG="[preflight]"
GATES=()
FAILED=0

# Load flow.config.json (best-effort)
SCHEME=""
WORKSPACE_OR_PROJECT=""
DESTINATION="platform=macOS"
if [ -f flow.config.json ]; then
  SCHEME=$(jq -r '.xcodebuild.scheme // empty' flow.config.json 2>/dev/null || true)
  WORKSPACE_OR_PROJECT=$(jq -r '.xcodebuild.workspaceOrProject // empty' flow.config.json 2>/dev/null || true)
  DESTINATION=$(jq -r '.xcodebuild.destination // "platform=macOS"' flow.config.json 2>/dev/null || true)
else
  echo "$TAG ⚠️ flow.config.json not found at repo root. Using all built-in defaults; some gates may not run." >&2
fi

# Discover xcworkspace/xcodeproj if not configured
if [ -z "$WORKSPACE_OR_PROJECT" ]; then
  WS=$(ls *.xcworkspace 2>/dev/null | head -n1)
  PROJ=$(ls *.xcodeproj 2>/dev/null | head -n1)
  if [ -n "$WS" ]; then
    WORKSPACE_OR_PROJECT="-workspace $WS"
  elif [ -n "$PROJ" ]; then
    WORKSPACE_OR_PROJECT="-project $PROJ"
  else
    echo "$TAG ⚠️ No .xcworkspace or .xcodeproj found at repo root and flow.config.json.xcodebuild.workspaceOrProject not set. Skipping xcodebuild gates." >&2
  fi
fi

run_gate() {
  local name="$1"
  shift
  echo "$TAG $name: $*" >&2
  if "$@"; then
    GATES+=("✓ $name: pass")
  else
    GATES+=("✗ $name: fail")
    FAILED=$((FAILED+1))
  fi
}

# Gate 1: xcodebuild build (requires SCHEME + WORKSPACE_OR_PROJECT)
if [ -n "$SCHEME" ] && [ -n "$WORKSPACE_OR_PROJECT" ]; then
  # shellcheck disable=SC2086
  run_gate "xcodebuild" xcodebuild $WORKSPACE_OR_PROJECT -scheme "$SCHEME" -destination "$DESTINATION" build
else
  echo "$TAG ⚠️ flow.config.json.xcodebuild.scheme not set; skipping xcodebuild gate." >&2
  GATES+=("— xcodebuild: skipped (scheme unset)")
fi

# Gate 2: xcodebuild test
if [ -n "$SCHEME" ] && [ -n "$WORKSPACE_OR_PROJECT" ]; then
  # shellcheck disable=SC2086
  run_gate "xcodebuild test" xcodebuild $WORKSPACE_OR_PROJECT -scheme "$SCHEME" -destination "$DESTINATION" test
else
  GATES+=("— xcodebuild test: skipped (scheme unset)")
fi

# Gate 3: swift-format lint (if installed)
if command -v swift-format >/dev/null 2>&1; then
  run_gate "swift-format" swift-format lint --recursive --strict .
else
  echo "$TAG ⚠️ swift-format not installed (brew install swift-format). Skipping lint gate." >&2
  GATES+=("— swift-format: skipped (not installed)")
fi

# Summary
echo "" >&2
echo "$TAG summary:" >&2
for g in "${GATES[@]}"; do
  echo "  $g" >&2
done

if [ "$FAILED" -gt 0 ]; then
  echo "" >&2
  echo "$TAG $FAILED gate(s) failed. Fix before /simplify runs." >&2
  exit 1
fi
echo "" >&2
echo "$TAG all gates green." >&2
exit 0
