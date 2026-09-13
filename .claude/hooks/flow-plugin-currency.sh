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
# version rows rendered by skills/ship/lib/plugin-provenance.py) is the
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
#
# COST, stated rather than hidden (measured; /simplify efficiency lens). One
# `claude plugin` CLI boot is ~379 ms on a cloud sandbox, and the clone refresh
# below is unconditional, so this adds roughly 1-3 s of blocking session start.
# Two optimisations were identified and deliberately NOT taken here — both are on
# the roadmap with their reasoning:
#   1. `"matcher": "startup|resume"` in settings.json, so this stops re-running on
#      every `/clear` and auto-compact (same process, where the update provably
#      cannot apply anyway). Not taken because SessionStart matcher support could
#      not be verified locally, and shipping an unverified declaration is the exact
#      FB-0085 class the PR that added this file was about.
#   2. A freshness gate on the clone's `.git` mtime. Not taken because it adds a
#      time-based staleness gate to the mechanism that exists to prevent silent
#      staleness — a wrong default reintroduces the bug.
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
# Deliberately the SAME marker + spelling as the 12 existing shipped call sites
# (staff-review x3, a11y x2, security x2, land x2, verify-build, ship-spike, doctor)
# and the one run_doc_slot_resolution_evals.py pins. A third spelling over a
# different file would be invisible to the check that guards this predicate.
[ -f plugins/flow/.claude-plugin/plugin.json ] || exit 0
grep -q '"name"[[:space:]]*:[[:space:]]*"flow"' plugins/flow/.claude-plugin/plugin.json 2>/dev/null || exit 0

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
    elif ! claude plugin marketplace update flow >/dev/null 2>&1 \
         && ! claude plugin marketplace add by-dev-tools/flow >/dev/null 2>&1; then
        # `update` first, `add` second: on every non-fresh host `add` fails and
        # `update` is the real path, so trying `add` first bought one guaranteed-
        # wasted ~380ms CLI boot per session. Identical semantics (both attempted,
        # warning only when both fail); the rare fresh-container path eats the
        # extra call instead of the common one.
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
    # ONE interpreter start, not four. The previous shape spawned python3 per field
    # and computed INST/MKT/BR before the silent-exit branch below, so three of the
    # four spawns were pure waste on the common (already-current) path.
    #
    # The delimiter is `|`, NOT a tab, and that is load-bearing rather than taste.
    # Tab is an IFS *whitespace* character, so `read` collapses runs of it and an
    # EMPTY field silently vanishes -- shifting every later field left. Reproduced:
    # with a malformed registry (no installed version) the fields shifted by one and
    # the warning below reported the MARKETPLACE version as the installed one. The
    # predicate itself was unaffected (it is field 1), so this was cosmetic -- but
    # printing a shifted version number inside a diagnostic about version confusion
    # is the worst possible place for it. A non-whitespace IFS preserves empty fields.
    # Values are sanitised of the delimiter on the python side so a version string
    # can never re-introduce the shift.
    FIELDS=$(printf '%s' "$PROV" | python3 -c '
import json, sys
d = json.load(sys.stdin)
def g(k):
    return str((d.get(k) or {}).get("version") or "").replace("|", "")
print("|".join([str(d.get("update_available")), str(d.get("report_drift")),
                g("installed"), g("marketplace_head"), g("branch")]))' 2>/dev/null)
    # Still reads the predicate FROM the engine -- no version comparison in shell.
    IFS='|' read -r AVAIL RDRIFT INST MKT BR <<EOF
$FIELDS
EOF

    if [ "$DRY" = "1" ]; then
        echo "[flow-currency] installed flow $INST · marketplace HEAD $MKT · this branch declares $BR" >&2
        echo "[flow-currency] update_available=$AVAIL (computed WITHOUT refreshing the clone," >&2
        echo "   so a 'False' here may only mean the local clone is pinned too)" >&2
        cc plugin update flow@flow
        echo "[flow-currency] NOTE: 'restart required to apply' — a real run would leave THIS" >&2
        echo "   session on $INST. The PR body's version rows report what actually ran." >&2
        exit 0
    fi

    if [ "$AVAIL" = "False" ]; then
        # Genuinely current against the refreshed clone, so no update is attempted.
        # But the two predicates are not one: `report_drift` can still be TRUE here
        # (a feature branch declares an unreleased version by construction — the
        # steady state of every flow branch), and this hook is the ONLY in-session
        # surface resolved from the CHECKOUT rather than the stale install. So it is
        # the only thing that can say so on a session whose installed ship prose is
        # too old to carry the provenance rows at all. Report; never act on it.
        if [ "$RDRIFT" = "True" ]; then
            echo "[flow-currency] installed flow $INST is current with the marketplace, but this" >&2
            echo "   branch declares $BR — the /flow:* skills and reviewers in THIS session run" >&2
            echo "   $INST, not your working tree. Check the PR's version rows, which name" >&2
            echo "   what ran. Restart Claude Code if this session will run any /flow:* command." >&2
        fi
        exit 0
    fi
    if [ "$AVAIL" != "True" ]; then
        echo "⚠️ [flow-currency] could not compare installed (${INST:-unreadable}) against" >&2
        echo "   marketplace HEAD (${MKT:-unreadable}) — whether an update exists is UNKNOWN," >&2
        echo "   which is NOT the same as 'no'. Run 'claude plugin list' before relying on the" >&2
        echo "   /flow:* machinery being current." >&2
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
    echo "   $INST. The PR body's version rows report what actually ran." >&2
    echo "   → Restart Claude Code now if this session will run any /flow:* command." >&2
    # No trailing `claude plugin list`: it was a ~380ms CLI boot whose output merely
    # restated the "$INST → $NEW" line immediately above, which the engine already
    # sourced from the registry. #116 prints it because it has no engine to ask.
} 1>&2

exit 0
