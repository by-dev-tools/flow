#!/bin/bash
# SessionStart hook — keep FLOW'S OWN dev workspace on the version it develops.
#
# Ported from byamron/health-tracker PR #116 `.claude/hooks/session-start.sh`,
# which closed exactly this skew in a real cloud workspace (1.29.0 -> 1.41.0).
# Flow built that auto-updater for consumers and never pointed it at itself:
# cobbler's children. FB-0107 is what that cost — twelve releases of divergence
# that no gate noticed, so every flow PR's ship pipeline reviewed the PREVIOUS
# release while everyone involved believed otherwise.
#
# THIS HOOK CANNOT FIX THE CURRENT SESSION, and saying so is the point.
# `claude plugin update` documents "restart required to apply", so this makes the
# NEXT session current and does nothing for this one. It converges; it does not
# fix. That is precisely why the provenance REPORT in the PR body (the four
# `## Flow run` rows from skills/ship/lib/plugin-provenance.py) is the
# load-bearing half of FB-0107 and this hook is the backstop — on any session
# that starts stale, only the report can say what actually ran.
#
# Deletion criterion (FB-0088): removable when Claude Code refreshes plugin
# marketplaces at session start natively, OR when flow's dev workspaces are
# provisioned from the checkout rather than from an image with a pinned
# ~/.claude/plugins. Either removes the skew this exists to close.
#
# Idempotent, non-interactive, and it NEVER exits non-zero — a network blip must
# not wedge a session start.
set -uo pipefail

# ---------------------------------------------------------------- the gate
#
# Ground truth, not an environment variable. #116's gate was
# `CLAUDE_CODE_REMOTE != true`, which is right for Claude Code on the web and
# silently WRONG in a Conductor cloud sandbox, where that variable is UNSET — so
# the hook no-op'd and the pinned plugin never refreshed. That is the FB-0085
# class (shipped, believed effective, never firing), and it is the same class
# FB-0107 itself belongs to. So: probe the repo, not the environment.
#
# This gate differs from #116's on purpose. #116 asks "is this a host that cannot
# build the iOS project?" and must NOT touch a developer's user-scope install.
# Here the question is "is this the flow checkout?", and the answer runs on every
# host including a Mac — because for flow the installed plugin IS the artifact
# under development, and its staleness is the bug.
[ -f .claude-plugin/marketplace.json ] || exit 0
grep -q '"name"[[:space:]]*:[[:space:]]*"flow"' .claude-plugin/marketplace.json 2>/dev/null || exit 0

ENGINE="plugins/flow/skills/ship/lib/plugin-provenance.py"

# FLOW_CURRENCY_DRY_RUN=1 inspects the decision WITHOUT mutating anything: no
# clone refresh, no install. It exists because the update is not freely
# re-runnable in the one workspace where the evidence lives — applying it
# destroys the only live record of the stale state a provenance PR is arguing
# about. It is also how the eval harness drives this script.
#
# Dry-run reports UNCONDITIONALLY, including when the local comparison says
# "current". That is deliberate: without the clone refresh the comparison is
# computed against possibly-pinned local data, so a silent exit would be the one
# output a dry run must never produce — indistinguishable from "verified current".
DRY="${FLOW_CURRENCY_DRY_RUN:-0}"
cc() {
    if [ "$DRY" = "1" ]; then
        echo "[flow-currency] [dry-run] would run: claude $*" >&2
        return 0
    fi
    claude "$@"
}

# All output to stderr so nothing is injected into the session's context.
{
    if ! command -v claude >/dev/null 2>&1; then
        echo "⚠️ [flow-currency] \`claude\` is not on PATH — the flow plugin CANNOT be" >&2
        echo "   refreshed from here. Do NOT assume the /flow:* machinery is current." >&2
        exit 0
    fi
    if [ ! -f "$ENGINE" ]; then
        echo "⚠️ [flow-currency] provenance engine missing at $ENGINE — cannot tell which" >&2
        echo "   flow version is installed, so cannot tell whether an update is needed." >&2
        exit 0
    fi

    # ------------------------------------------------- refresh the clone FIRST
    #
    # This ordering is a correction to #116, forced by a measurement taken while
    # porting it. `update_available` compares the install against the LOCAL
    # marketplace clone — and that clone can itself be pinned at the same stale
    # commit as the install. It was: 1.29.0 installed against a 1.29.0 clone at
    # cf783ac, with `main` at 1.41.0. So the comparison is MEANINGLESS until the
    # clone is refreshed; gating the refresh on `update_available` would have
    # made the hook permanently no-op in exactly the workspace it was written
    # for. Refresh unconditionally, THEN compare.
    #
    # `add` is tried first because a fresh container may have no marketplace at
    # all; on an existing one it fails and `update` is the real path. Either
    # succeeding is fine — but BOTH failing is not, and unlike #116 that case is
    # loud here. If the clone cannot be refreshed, any "already current" verdict
    # below is computed against stale data, which is the silent-confidence shape
    # this whole PR exists to remove.
    if [ "$DRY" = "1" ]; then
        cc plugin marketplace update flow
    elif ! claude plugin marketplace add by-dev-tools/flow >/dev/null 2>&1 \
         && ! claude plugin marketplace update flow >/dev/null 2>&1; then
        echo "⚠️ [flow-currency] could NOT refresh the flow marketplace clone (offline, or" >&2
        echo "   the source is unreachable). Any 'already current' verdict below is computed" >&2
        echo "   against a possibly stale clone — treat the installed version as UNVERIFIED." >&2
    fi

    PROV=$(python3 "$ENGINE" report --json 2>/dev/null)
    if [ -z "$PROV" ]; then
        echo "⚠️ [flow-currency] the provenance engine produced no output — cannot determine" >&2
        echo "   whether the installed flow plugin is current." >&2
        exit 0
    fi

    # One predicate, one place. The comparison is NOT re-derived here: doctor's
    # first cut at a shared predicate re-derived it inline and the two copies
    # disagreed inside a single commit, producing [PASS] in one surface and a ⚠️
    # in another for one identical on-disk state.
    read_field() { printf '%s' "$PROV" | python3 -c "import json,sys;print(json.load(sys.stdin).get('$1'))" 2>/dev/null; }
    read_nested() { printf '%s' "$PROV" | python3 -c "import json,sys;print((json.load(sys.stdin).get('$1') or {}).get('$2',''))" 2>/dev/null; }

    AVAIL=$(read_field update_available)
    INST=$(read_nested installed version)
    MKT=$(read_nested marketplace_head version)
    BR=$(read_nested branch version)

    if [ "$DRY" = "1" ]; then
        echo "[flow-currency] installed flow $INST · marketplace HEAD $MKT · this branch declares $BR" >&2
        echo "[flow-currency] update_available=$AVAIL (computed WITHOUT refreshing the clone," >&2
        echo "   so a 'False' here may only mean the local clone is pinned too)" >&2
        cc plugin update flow@flow
        echo "[flow-currency] NOTE: 'restart required to apply' — a real run would leave THIS" >&2
        echo "   session on $INST. The PR body's '## Flow run' provenance rows report what ran." >&2
        exit 0
    fi

    if [ "$AVAIL" = "False" ]; then
        # Genuinely current against the refreshed clone. Silent: a session start
        # is not the place for a line that always prints. Note this is the
        # REPORT-vs-UPDATE split doing its job — `report_drift` may still be true
        # here (a feature branch declares an unreleased version by construction),
        # and keying the updater on THAT would make this branch print a warning
        # forever, including after a fully successful update.
        exit 0
    fi
    if [ "$AVAIL" != "True" ]; then
        echo "⚠️ [flow-currency] could not compare installed ($INST) against marketplace" >&2
        echo "   HEAD ($MKT) — 'is an update available' is UNKNOWN, not 'no'." >&2
        exit 0
    fi

    echo "[flow-currency] installed flow $INST · marketplace HEAD $MKT · this branch declares $BR" >&2
    echo "[flow-currency] updating the installed plugin…" >&2

    # NOT `|| true`, and this is the one line in the script that must fail loud.
    # It is the line that pulls marketplace HEAD, so swallowing its exit status
    # would make a hijacked or unreachable marketplace indistinguishable from a
    # clean run. An auto-updater that is silent on failure is strictly WORSE than
    # no auto-updater, because it manufactures confidence about the version —
    # which is FB-0107's own failure shape, one level up. (Ported from #116 with
    # its reasoning; the escalation it accepts is that more hosts now pull
    # automatically, and loudness is the mitigation.)
    if ! cc plugin update flow@flow; then
        echo "⚠️ [flow-currency] 'claude plugin update flow@flow' FAILED — the flow plugin" >&2
        echo "   may be stale or the marketplace unreachable. Do NOT assume the /flow:*" >&2
        echo "   machinery is current; run 'claude plugin list' before relying on it." >&2
        exit 0
    fi

    NEW=$(python3 "$ENGINE" report --json 2>/dev/null \
          | python3 -c "import json,sys;print((json.load(sys.stdin).get('installed') or {}).get('version',''))" 2>/dev/null)
    echo "[flow-currency] installed flow: $INST → ${NEW:-unknown}" >&2
    echo "[flow-currency] NOTE: 'restart required to apply' — THIS session still runs" >&2
    echo "   $INST. The PR body's '## Flow run' provenance rows report what actually ran." >&2
    claude plugin list 2>/dev/null || true
} 1>&2

exit 0
