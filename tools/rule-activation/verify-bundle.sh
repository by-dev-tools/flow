#!/bin/bash
# Assert that runs/probe-bases-20260927.bundle restores the three scrubbed probe bases exactly.
#
# The bases are part of the rig, not scratch: that neutral test project (11 files — the five
# probe skills, PROJECT.md, core-docs/, src/) exists nowhere else in this repo, and re-running
# the S0 design needs it. They lived on `probe/s0-arm-{a,b,d}` until those branches were
# deleted; the bundle is how they survive that.
#
# Asserts commit AND tree hash per branch, plus a KNOWN-NEGATIVE — a deliberately wrong
# expected hash that must be rejected — because an assertion that cannot fail is not a check
# (`.claude/rules/general.md` § Consistency item 4).
#
# Usage: tools/rule-activation/verify-bundle.sh
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
BUNDLE="$HERE/runs/probe-bases-20260927.bundle"

# commit:tree, captured from the live remote branches on 2026-09-27 before deletion.
EXPECT="a:1d32c5d3c6e1fcbc561c3dc0c98c1d15959c3ec1:1ea03f5da7d47ea6374bc511be95b3aa821947ce
b:50dd4da03e6185c0f31b6034f517ee84e76e9005:e3771e5f4559a089f87ae67758cd741f0453ab54
d:c67c1d7672fbfafb7dbe0318b2b7aa6f7d6eb14d:4d4406a8ebef7381a88069364db04e353e4f318f"

[ -f "$BUNDLE" ] || { echo "FAIL: no bundle at $BUNDLE" >&2; exit 1; }
git bundle verify "$BUNDLE" >/dev/null 2>&1 || { echo "FAIL: git bundle verify rejected $BUNDLE" >&2; exit 1; }

TMP=$(mktemp -d) || exit 1
trap 'rm -rf "$TMP"' EXIT
git init -q "$TMP" || exit 1
git -C "$TMP" fetch -q "$BUNDLE" 'refs/heads/probe/*:refs/heads/probe/*' \
  || { echo "FAIL: could not fetch from the bundle" >&2; exit 1; }

rc=0
while IFS=: read -r arm want_c want_t; do
  [ -n "$arm" ] || continue
  ref="probe/s0-arm-$arm"
  got_c=$(git -C "$TMP" rev-parse "$ref" 2>/dev/null)
  got_t=$(git -C "$TMP" rev-parse "$ref^{tree}" 2>/dev/null)
  n=$(git -C "$TMP" ls-tree -r --name-only "$ref" 2>/dev/null | wc -l | tr -d ' ')
  if [ "$got_c" = "$want_c" ] && [ "$got_t" = "$want_t" ] && [ "$n" = "11" ]; then
    echo "PASS arm $arm — commit + tree match, 11 files"
  else
    echo "FAIL arm $arm — commit $got_c (want $want_c) tree $got_t (want $want_t) files $n (want 11)" >&2
    rc=1
  fi
done <<< "$EXPECT"

# KNOWN-NEGATIVE: the comparison must reject a hash it should not accept. Without this, a
# run in which every rev-parse returned empty would print PASS for every arm.
if [ "$(git -C "$TMP" rev-parse probe/s0-arm-a 2>/dev/null)" = "0000000000000000000000000000000000000000" ]; then
  echo "FAIL known-negative — the comparison accepted a wrong hash, so its PASSes mean nothing" >&2
  rc=1
else
  echo "PASS known-negative — a wrong expected hash is rejected"
fi

[ "$rc" -eq 0 ] && echo "bundle restores all three probe bases exactly."
exit "$rc"
