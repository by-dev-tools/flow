# shellcheck shell=sh
# verify-pr-body.sh — mandatory read-back after every PR-body / draft-state write (FB-0067).
#
# Source this from any flow skill that mutates a PR body or draft state:
#     . "${CLAUDE_PLUGIN_ROOT}/skills/ship/lib/verify-pr-body.sh"   # plugin-installed
#     . "plugins/flow/skills/ship/lib/verify-pr-body.sh"            # inside the flow repo
#
# The failure it exists to catch: a PR-body write that silently no-ops (a masked
# gh exit code, a projectCards GraphQL error swallowed by a pipe, a hand-edit that
# never saved) leaves the STALE body in place while the pipeline reports success —
# the recurring "ready PR still carrying the 🚫 NOT READY TO MERGE manifest" bug.
# So: after EVERY write, re-fetch and assert the write took. Never trust the write's
# own exit status alone.
#
# HARD RULE (enforced by convention, stated here so it is un-missable): a gh write is
# its own checked statement. NEVER pipe a gh write into a filter to grab a URL —
#     gh pr edit "$N" --body-file f | tail -1 && gh pr ready "$N"   # WRONG
# the pipe makes the pipeline exit status `tail`'s 0, masking gh's non-zero. Run the
# write, check `$?`, THEN read back with flow_verify_pr_write.
#
# Functions (all POSIX sh; return 0 on success, 1 on mismatch, 2 on a fetch/tooling
# error — every failure prints a loud multi-line diagnostic to stderr):
#
#   flow_fetch_pr_state <num>
#       Re-fetch the live PR. On success sets FLOW_PR_BODY_FILE (a temp file holding
#       the body) and FLOW_PR_ISDRAFT (true|false). Uses `gh pr view --json`, falling
#       back to the REST API on the Projects-classic `projectCards` deprecation error
#       (same fallback family as /flow:ship Step 7 § "gh resilience").
#
#   flow_verify_pr_write <num> [--expect S]... [--forbid S]... [--want-draft true|false]
#       Post-write read-back. Re-fetches, then asserts via lib/pr-coherence.py that
#       every --expect substring is present, every --forbid substring is absent, the
#       draft state matches --want-draft (when given), AND the coherence invariant
#       holds. Call this immediately after any gh pr edit / gh api PATCH / gh pr ready.
#
#   flow_assert_pr_coherent <num>
#       Re-fetch + assert ONLY the body↔draft invariant (ready PR ⇒ no manifest).
#       The final gate at ship Step 7 and the doctor/land drift checks call this.

# Resolve pr-coherence.py once (plugin-installed, else in-repo).
_flow_pr_coherence_py() {
  if [ -n "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -f "${CLAUDE_PLUGIN_ROOT}/skills/ship/lib/pr-coherence.py" ]; then
    printf '%s' "${CLAUDE_PLUGIN_ROOT}/skills/ship/lib/pr-coherence.py"
  elif [ -f "plugins/flow/skills/ship/lib/pr-coherence.py" ]; then
    printf '%s' "plugins/flow/skills/ship/lib/pr-coherence.py"
  else
    return 1
  fi
}

flow_fetch_pr_state() {
  _num="$1"
  if [ -z "$_num" ]; then
    echo "⚠️ [verify-pr-body] flow_fetch_pr_state: no PR number given." >&2
    return 2
  fi
  FLOW_PR_BODY_FILE="$(mktemp 2>/dev/null || echo /tmp/flow-pr-readback-$$.md)"
  # Primary path.
  _json="$(gh pr view "$_num" --json body,isDraft 2>/tmp/flow-pr-fetch-err)"
  if [ -n "$_json" ]; then
    printf '%s' "$_json" | jq -r '.body // ""' > "$FLOW_PR_BODY_FILE"
    FLOW_PR_ISDRAFT="$(printf '%s' "$_json" | jq -r 'if .isDraft then "true" else "false" end')"
    return 0
  fi
  # Fallback: try REST unconditionally on any gh pr view failure — the projectCards
  # deprecation is the common cause, but the REST endpoint is a safe fallback for any
  # failure reason (it doesn't query projectCards either way).
  _repo="$(gh repo view --json nameWithOwner -q .nameWithOwner 2>/dev/null)"
  if [ -n "$_repo" ]; then
    _rest="$(gh api "repos/$_repo/pulls/$_num" 2>/tmp/flow-pr-fetch-err)"
    if [ -n "$_rest" ]; then
      printf '%s' "$_rest" | jq -r '.body // ""' > "$FLOW_PR_BODY_FILE"
      FLOW_PR_ISDRAFT="$(printf '%s' "$_rest" | jq -r 'if .draft then "true" else "false" end')"
      return 0
    fi
  fi
  echo "⚠️ [verify-pr-body] could not re-fetch PR #$_num (gh pr view AND REST both failed):" >&2
  sed 's/^/    /' /tmp/flow-pr-fetch-err 2>/dev/null >&2
  echo "    → cannot confirm the write took. Do NOT proceed as if the PR body is correct." >&2
  return 2
}

flow_verify_pr_write() {
  _num="$1"; shift
  _py="$(_flow_pr_coherence_py)" || {
    echo "⚠️ [verify-pr-body] pr-coherence.py not reachable — cannot read-back-verify PR #$_num." >&2
    return 2
  }
  flow_fetch_pr_state "$_num" || return 2
  # Forward --expect/--forbid/--want-draft straight through to the checker.
  python3 "$_py" readback --body-file "$FLOW_PR_BODY_FILE" --is-draft "$FLOW_PR_ISDRAFT" "$@"
  _rc=$?
  if [ "$_rc" -ne 0 ]; then
    echo "⚠️ [verify-pr-body] read-back FAILED for PR #$_num — the intended write did NOT land." >&2
    echo "    The PR body on GitHub does not match what you wrote. Re-apply the write and re-verify;" >&2
    echo "    never report success on an unverified write." >&2
  fi
  return "$_rc"
}

flow_assert_pr_coherent() {
  _num="$1"
  _py="$(_flow_pr_coherence_py)" || {
    echo "⚠️ [verify-pr-body] pr-coherence.py not reachable — cannot assert coherence for PR #$_num." >&2
    return 2
  }
  flow_fetch_pr_state "$_num" || return 2
  python3 "$_py" coherence --body-file "$FLOW_PR_BODY_FILE" --is-draft "$FLOW_PR_ISDRAFT"
}
