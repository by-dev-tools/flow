#!/bin/sh
# Shared CI-status acquisition for /flow:ship §7a.7 and /flow:ship-spike's CI gate.
#
# SOURCED, not executed — the same reason `serve-preview.sh` and `verify-pr-body.sh` are:
# shell state does not cross Bash tool calls, so a value produced in one call cannot be
# read in the next. Sourcing puts the whole sequence in the caller's own fence by
# construction rather than by an instruction two skills must remember.
#
# WHY THIS FILE EXISTS AT ALL. The acquisition logic was written out twice, once per
# skill, and the copies had ALREADY DRIFTED inside the single PR that introduced them:
# ship read `flow.config.json` from `$FLOW_ROOT` while ship-spike read it CWD-relative,
# so running ship-spike from a subdirectory silently reverted `ciWaitSeconds` to its
# default. That is `.claude/rules/general.md` item 2 (a contract spelled in N places
# where a change touches some), measured on itself. The POLICY stays per-skill — ship
# drafts on all three non-green states, ship-spike only on a red check — because that
# asymmetry is deliberate. Only the acquisition is shared.
#
# IT WRITES NO FILES. An earlier cut staged the status JSON through `$FLOW_SCRATCH`,
# which dragged in a mkdir, a self-ignore write, two `rm -f` unlinks and a
# dangling-symlink unlink — roughly fourteen lines of CWE-59 defence for a file nothing
# read after the block ended. A shell variable needs none of it, so the security surface
# is removed rather than guarded.
#
# Sets, on return:
#   FLOW_CI_JSON    the engine's verdict object (JSON, always non-empty)
#   FLOW_CI_VERDICT PASS | FAIL | UNDECLARED
#   FLOW_CI_KIND    ci-failing | ci-pending | ci-unknown | (empty on PASS)
# Always returns 0 when it produced a verdict, 1 only when it could not run at all —
# because "I could not read CI" is a VERDICT here (`ci-unknown`), not an error.

flow_ci_status() {
  _pr="$1"
  FLOW_CI_JSON=''; FLOW_CI_VERDICT=''; FLOW_CI_KIND=''

  _r="${CLAUDE_PLUGIN_ROOT:-}/skills/ship/lib/ship-readiness.py"
  [ -f "$_r" ] || _r="plugins/flow/skills/ship/lib/ship-readiness.py"
  if [ ! -f "$_r" ]; then
    echo "⚠️ BLOCKER: ship-readiness.py not found — the CI gate cannot run. Treat CI as NOT confirmed green." >&2
    return 1
  fi

  _root=$(git rev-parse --show-toplevel 2>/dev/null)
  if [ -z "$_root" ]; then
    echo "⚠️ BLOCKER: not inside a git repository — the CI gate cannot run." >&2
    return 1
  fi

  # Repo-root-relative, never CWD-relative: from a subdirectory a CWD-relative read finds
  # no config and the slot silently reverts to its default — a setting the user believes
  # is in force and is not. The `case` degrades LOUDLY for the same reason.
  _wait=$(jq -r '.ciWaitSeconds // 600' "$_root/flow.config.json" 2>/dev/null)
  case "$_wait" in
    ''|*[!0-9]*)
      echo "⚠️ [ci-gate] flow.config.json.ciWaitSeconds is not a non-negative integer ('$_wait') — falling back to 600." >&2
      _wait=600 ;;
  esac

  if ! command -v gh >/dev/null 2>&1; then
    # FB-0121: "couldn't see" is not "nothing there". This is also the degrade path for a
    # project with no GitHub at all — it warns loudly, yields a verdict, and never halts.
    echo "⚠️ [ci-gate] gh is not installed — CI status cannot be read. This is NOT a passing CI." >&2
    FLOW_CI_JSON=$(python3 "$_r" ci --gh-failed)
  else
    [ -n "$_pr" ] || _pr=$(gh pr view --json number --jq .number 2>/dev/null)
    if [ -z "$_pr" ]; then
      echo "⚠️ [ci-gate] no PR found for this branch — CI status unknown, never assumed green." >&2
      FLOW_CI_JSON=$(python3 "$_r" ci --gh-failed)
    else
      # Block until the checks settle, bounded. `--watch` is the whole point: the process
      # sleeps and the agent does not think, so waiting costs zero tokens (FB-0137).
      #
      # This command's exit status is deliberately NOT the verdict — measured, exit 1 is
      # returned for a failing check, for "no checks reported", AND for a missing PR:
      # three unlike worlds in one value. It is used ONLY to detect `timeout`'s own 124.
      # `|| _rc=$?`, never `|| true; _rc=$?`, which would capture `true`.
      #
      # `-gt 0` is LOAD-BEARING. MEASURED (coreutils 8.32): `timeout 0` DISABLES the
      # timeout — `timeout 0 sleep 3` runs the full 3s and exits 0, against `timeout 1
      # sleep 3` which exits 124 at 1s. So passing the documented `ciWaitSeconds: 0`
      # ("read once, do not wait") straight to `timeout` produced an UNBOUNDED `--watch`
      # wait, the exact opposite of the contract, on the one value a user sets to avoid
      # waiting. Zero skips the wait and falls through to the single read below.
      _rc=0
      if [ "$_wait" -gt 0 ]; then
        timeout "$_wait" gh pr checks "$_pr" --watch --fail-fast >/dev/null 2>&1 || _rc=$?
      fi
      # ONE fetch, captured in a variable. A probe-then-refetch pair can succeed and then
      # fail, and that second failure arrives as empty stdin rather than the explicit
      # --gh-failed state — exactly the ambiguity this engine exists to remove.
      _raw=$(gh pr view "$_pr" --json statusCheckRollup,mergeStateStatus 2>/dev/null)
      if [ -n "$_raw" ]; then
        FLOW_CI_JSON=$(printf '%s' "$_raw" | python3 "$_r" ci)
        # SETTLE RE-READ — the one branch where PASS would come from an ABSENCE.
        # `gh pr checks --watch` does not wait for checks to APPEAR: with zero reported it
        # returns at once. So a PR created seconds ago has an empty rollup, and on a repo
        # with no branch protection its merge state is already CLEAN — indistinguishable
        # from a project with no CI. The engine refuses to call that a pass without
        # --settled, so give the checks a chance to register and look once more. Only this
        # second look makes the absence evidence.
        if [ "$(printf '%s' "$FLOW_CI_JSON" | jq -r '.state')" = "no-checks-unsettled" ]; then
          echo "[ci-gate] no checks reported yet — waiting ${FLOW_CI_SETTLE_SECONDS}s for them to register, then looking once more." >&2
          sleep "$FLOW_CI_SETTLE_SECONDS"
          _raw2=$(gh pr view "$_pr" --json statusCheckRollup,mergeStateStatus 2>/dev/null)
          [ -n "$_raw2" ] && FLOW_CI_JSON=$(printf '%s' "$_raw2" | python3 "$_r" ci --settled)
        fi
      elif [ "$_rc" -eq 124 ]; then
        FLOW_CI_JSON=$(python3 "$_r" ci --timed-out "$_wait")
      else
        echo "⚠️ [ci-gate] gh could not report this PR's status — treating CI as unknown, never as green." >&2
        FLOW_CI_JSON=$(python3 "$_r" ci --gh-failed)
      fi
    fi
  fi

  # Positive assertion paired with every fallback above. An empty result means no branch
  # ran, and in the one file whose thesis is "silence is not a pass" it must not read as
  # one (general.md item 1).
  if [ -z "$FLOW_CI_JSON" ]; then
    echo "⚠️ BLOCKER: the CI gate produced no verdict — treat CI as NOT confirmed green." >&2
    return 1
  fi
  FLOW_CI_VERDICT=$(printf '%s' "$FLOW_CI_JSON" | jq -r '.verdict')
  FLOW_CI_KIND=$(printf '%s' "$FLOW_CI_JSON" | jq -r '.kind // empty')
  printf '%s' "$FLOW_CI_JSON" | jq -r '"[ci-gate] " + .state + " — " + .reason' >&2
  echo "[ci-gate] verdict=$FLOW_CI_VERDICT kind=${FLOW_CI_KIND:-none}" >&2
  [ -n "$FLOW_CI_VERDICT" ] || return 1
  return 0
}

# How long to let checks register before a SECOND look decides an empty rollup is genuinely
# "no CI configured". A registration delay, not a CI duration — which is why it is a
# constant here rather than a config slot: `ciWaitSeconds` answers "how long can CI take",
# and conflating the two would let a 20-minute CI budget become a 20-minute settle wait.
# One definition, both callers (it was a literal `20` in two files).
: "${FLOW_CI_SETTLE_SECONDS:=20}"
