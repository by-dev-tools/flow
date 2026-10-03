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
# ⚠️ THIS SCRIPT IS A REPO FILE AND RUNS AUTOMATICALLY AT SESSION START.
# Checking out someone else's branch therefore runs THEIR copy of this file, with no
# approval prompt. That residual is accepted and documented in CONTRIBUTING.md, which
# also records the measurement behind the decision: a hash-check fix was attempted and
# abandoned because a changed `settings.json` hook command string was measured to
# execute with NO re-approval, so the check would have enforced nothing. What IS
# mitigated is below — this script resolves its engine only from the INSTALLED plugin
# and never from the checkout.
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

# SECURITY: resolve the engine from the INSTALLED tree ONLY — never from the checkout.
#
# This hook fires automatically at SessionStart with no approval prompt, and the
# approved string in settings.json does not change when repo content does. So a
# checkout-resolved engine would mean `gh pr checkout <external-PR>` + a new session =
# arbitrary code execution as the user, from a contributor's branch. Flow takes
# external PRs, so that is a live path, not a hypothetical.
#
# A currency check has no legitimate reason to run the branch under review: the
# question it asks ("is the INSTALLED plugin current?") is answered entirely by the
# installed tree and the registry. If the engine is not installed, warn and exit —
# degrading to the checkout copy is precisely the move that creates the hole.
#
# Consumers are unaffected either way: `.claude/` is project-dev infra and is not part
# of the published plugin (the marketplace entry's source is ./plugins/flow).
ENGINE=""
_reg="$HOME/.claude/plugins/installed_plugins.json"
if [ -f "$_reg" ]; then
    _ip=$(python3 -c "
import json,sys
try:
    d=json.load(open(sys.argv[1]))
    e=(d.get('plugins') or {}).get('flow@flow') or []
    print(e[0].get('installPath','') if e and isinstance(e[0],dict) else '')
except Exception:
    print('')" "$_reg" 2>/dev/null)
    [ -n "$_ip" ] && [ -f "$_ip/skills/ship/lib/plugin-provenance.py" ] \
        && ENGINE="$_ip/skills/ship/lib/plugin-provenance.py"
fi

# The installed VERSION, straight from the registry — needed on the bootstrap arm
# below, which by definition has no engine to ask. Deliberately NOT a second
# version *comparison*: the predicate still lives in exactly one place (the
# engine). This reads one field so a before/after line can name a number, which
# is the only thing that makes a bootstrap run distinguishable from a no-op.
registry_version() {
    [ -f "$_reg" ] || return 0
    python3 -c "
import json,sys
try:
    d=json.load(open(sys.argv[1]))
    e=(d.get('plugins') or {}).get('flow@flow') or []
    print(str((e[0].get('version') or '') if e and isinstance(e[0],dict) else ''))
except Exception:
    print('')" "$_reg" 2>/dev/null
}

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
    # Diagnostics only: the plugin CLI's own progress chatter must not reach
    # stdout, which is now the seat-facing channel (see the output contract below).
    claude "$@" 1>&2
}

# ------------------------------------------------- the output contract
#
# REVERSAL, stated rather than left as a contradiction. This block used to be
# wrapped in `{ … } 1>&2` under the comment "All output to stderr so nothing is
# injected into the session's context." The mechanism was right and the
# consequence was not weighed. Per Claude Code's hook docs, stderr from a hook
# that exits 0 goes to the debug log only, never the transcript, and
# Claude never sees it — and this hook always exits 0, by design. So its output was
# invisible to the agent AND to the human, readable only under `--debug`.
# Measured: a fresh session asked for its `[flow-currency]` line reported none.
# That is how a 26-release skew survived in every seat of a program that had
# already built a report about it.
#
# `SessionStart` is one of the four events whose plain-text stdout IS added to
# Claude's context. So:
#
#   stdout — AT MOST ONE line, and only when there is a VERDICT the seat must act
#            on: an applied update, a drift, or any "I could not tell". Silence
#            when the install is current and undrifted, because a line printed
#            unconditionally would be noise on every healthy session and would
#            make the acting case indistinguishable again — the same failure one
#            level up.
#   stderr — the multi-line explanation, the remedy commands, the CLI's own
#            chatter. Debug-log material; nothing depends on it being read.
#
# Every `exit 0` path below therefore pairs `say` (the verdict) with the existing
# `>&2` detail, or emits neither.
say() { printf '%s\n' "$*"; }

# ------------------------------------------- the two CLI calls, defined ONCE
#
# Both arms below (bootstrap and normal) need the same two commands, and a second
# copy of a command string is the FB-0010 fan-out shape — the kind where a typo in
# one copy is invisible because the other one works. So they live here, in one
# place, and both arms call these.
#
# SECURITY, and this is the line the next maintainer will want: these are
# subcommands of the user's own `claude` CLI resolved from PATH. They are NOT
# repository files. CONTRIBUTING.md's accepted residual is about this hook
# executing *a file in the repository* — its claimed mitigation is specifically
# that "the hook no longer executes any OTHER repository file" — and this script
# has invoked both commands on its normal path since `bb3bc60`, under the same
# approved `settings.json` command string. Running them on the bootstrap arm too
# therefore adds no new class of execution; it only removes an early exit that
# stood in front of calls this file was already trusted to make. What stays
# refused is resolving the provenance ENGINE from the checkout.

# `update` first, `add` second: on every non-fresh host `add` fails and `update`
# is the real path, so trying `add` first bought one guaranteed-wasted ~380ms CLI
# boot per session. Either succeeding is fine; BOTH failing is not, and the caller
# is expected to be loud about it. Returns non-zero only when both fail.
refresh_marketplace() {
    if [ "$DRY" = "1" ]; then
        cc plugin marketplace update flow
        return 0
    fi
    claude plugin marketplace update flow >/dev/null 2>&1 \
        || claude plugin marketplace add by-dev-tools/flow >/dev/null 2>&1
}

# NOT `|| true`, and this is the one call in the script that must fail loud. It is
# the call that pulls marketplace HEAD, so swallowing its exit status would make a
# hijacked or unreachable marketplace indistinguishable from a clean run. An
# auto-updater that is silent on failure is strictly WORSE than no auto-updater,
# because it manufactures confidence about the version — which is FB-0107's own
# failure shape, one level up. (Ported from #116 with its reasoning; the
# escalation it accepts is that more hosts now pull automatically, and loudness is
# the mitigation.)
apply_update() { cc plugin update flow@flow; }
{
    if ! command -v claude >/dev/null 2>&1; then
        say "⚠️ [flow-currency] \`claude\` is not on PATH, so the installed flow plugin could NOT be checked or refreshed — do NOT assume the /flow:* machinery is current."
        echo "⚠️ [flow-currency] \`claude\` is not on PATH — the flow plugin CANNOT be" >&2
        echo "   refreshed from here. Do NOT assume the /flow:* machinery is current." >&2
        exit 0
    fi

    # ------------------------------------------------- BOOTSTRAP: no engine
    #
    # THE DEADLOCK THIS ARM EXISTS TO BREAK. The engine that answers "is the
    # install current?" ships INSIDE the artifact being updated (added v1.43.0), so
    # an install old enough to need an update was old enough to disable the
    # updater. This arm used to be an early exit that printed the two commands and
    # ran neither: the hook could only update installs that were already new enough
    # not to need it. Measured 2026-10-03 — EVERY Conductor cloud workspace boots
    # from a snapshot carrying 1.29.0 (identical `installedAt`, so it is baked into
    # the image), and the local marketplace CLONE is pinned at the same `cf783ac`,
    # so no seat in this program had ever converged. 26 releases.
    #
    # So: there is no engine to ask, and that is a reason to UPDATE, not a reason
    # to stop. Run both commands unconditionally — this arm is only reached when
    # the installed tree demonstrably lacks a file every version since v1.43.0
    # ships, which is already the answer the engine would have given.
    #
    # Still NOT falling back to this checkout's copy of the engine, and the
    # distinction is the whole security argument: see `apply_update` above. A
    # version number is reported by reading the REGISTRY, not by running repo code.
    if [ -z "$ENGINE" ] || [ ! -f "$ENGINE" ]; then
        _BEFORE=$(registry_version)
        echo "[flow-currency] the installed flow plugin (${_BEFORE:-unreadable}) predates the" >&2
        echo "   provenance engine (added in v1.43.0), so there is no engine to ask whether an" >&2
        echo "   update exists — which is itself the answer. Bootstrapping unconditionally with" >&2
        echo "   claude plugin marketplace update flow && claude plugin update flow@flow" >&2
        echo "   Those are CLI subcommands, NOT code from this checkout, and this is still" >&2
        echo "   NOT falling back to this checkout's copy of the engine — this hook fires" >&2
        echo "   with no approval prompt, so running repo code here would make checking out an" >&2
        echo "   untrusted branch equivalent to executing it." >&2

        refresh_marketplace || {
            echo "⚠️ [flow-currency] could NOT refresh the flow marketplace clone (offline, or" >&2
            echo "   the source is unreachable). The update below will have nothing newer to" >&2
            echo "   install, so a no-change result does NOT mean the install is current." >&2
        }

        if [ "$DRY" = "1" ]; then
            apply_update
            say "[flow-currency] [dry-run] installed flow ${_BEFORE:-unknown} has no provenance engine; a real run would bootstrap it. Nothing was changed."
            echo "[flow-currency] [dry-run] bootstrap arm reached and NOTHING was mutated." >&2
            exit 0
        fi

        if ! apply_update; then
            say "⚠️ [flow-currency] bootstrap FAILED — 'claude plugin update flow@flow' did not succeed, so installed flow is still ${_BEFORE:-unknown} and the /flow:* machinery is NOT current."
            echo "⚠️ [flow-currency] the bootstrap update FAILED. The installed plugin predates" >&2
            echo "   v1.43.0 and could not be moved; run 'claude plugin list' and the two" >&2
            echo "   commands above by hand before relying on any /flow:* command." >&2
            exit 0
        fi

        _AFTER=$(registry_version)
        # The one new silent-confidence shape this arm introduces, pinned in the
        # failing direction. `plugin update` can exit 0 having changed nothing (the
        # marketplace clone is stale, or the source regressed below v1.43.0), and
        # an unconditional "X → Y" line would then read as success while the seat
        # stayed on the old version AND re-paid the download every session.
        if [ -n "$_AFTER" ] && [ "$_AFTER" = "$_BEFORE" ]; then
            say "⚠️ [flow-currency] the flow plugin update reported SUCCESS but installed flow is STILL $_AFTER — treat the /flow:* machinery as stale, not current."
            echo "⚠️ [flow-currency] update exited 0 but the registry still reports $_AFTER." >&2
            echo "   Either the marketplace clone could not be refreshed, or its HEAD predates" >&2
            echo "   v1.43.0. This arm will re-run every session until the version moves." >&2
            exit 0
        fi
        say "[flow-currency] installed flow ${_BEFORE:-unknown} → ${_AFTER:-unknown} (it predated the provenance engine). THIS session still runs ${_BEFORE:-the old version} — restart Claude Code before relying on any /flow:* command."
        echo "[flow-currency] bootstrap complete: ${_BEFORE:-unknown} → ${_AFTER:-unknown}." >&2
        echo "   'restart required to apply' — THIS session is NOT fixed by it. The PR body's" >&2
        echo "   version rows report what actually ran." >&2
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
    # `add` covers the fresh container with no marketplace at all; see
    # `refresh_marketplace` above for the ordering and the cost. Either succeeding
    # is fine — but BOTH failing is not, and unlike #116 that case is loud here. If
    # the clone cannot be refreshed, any "already current" verdict below is computed
    # against stale data, which is the silent-confidence shape this whole PR exists
    # to remove.
    refresh_marketplace || {
        echo "⚠️ [flow-currency] could NOT refresh the flow marketplace clone (offline, or" >&2
        echo "   the source is unreachable). Any 'already current' verdict below is computed" >&2
        echo "   against a possibly stale clone — treat the installed version as UNVERIFIED." >&2
    }

    PROV=$(python3 "$ENGINE" report --json 2>/dev/null)
    if [ -z "$PROV" ]; then
        say "⚠️ [flow-currency] the flow provenance engine produced no output, so whether the installed plugin is current is UNKNOWN — do not assume the /flow:* machinery is current."
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
        apply_update
        say "[flow-currency] [dry-run] installed flow $INST · marketplace HEAD $MKT · this branch declares $BR · update_available=$AVAIL. Nothing was changed."
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
            say "[flow-currency] installed flow $INST is current with the marketplace, but this branch declares $BR — the /flow:* skills and reviewers in THIS session run $INST, not your working tree."
            echo "[flow-currency] installed flow $INST is current with the marketplace, but this" >&2
            echo "   branch declares $BR — the /flow:* skills and reviewers in THIS session run" >&2
            echo "   $INST, not your working tree. Check the PR's version rows, which name" >&2
            echo "   what ran. Restart Claude Code if this session will run any /flow:* command." >&2
        fi
        exit 0
    fi
    if [ "$AVAIL" != "True" ]; then
        say "⚠️ [flow-currency] could not compare installed flow (${INST:-unreadable}) against marketplace HEAD (${MKT:-unreadable}) — whether an update exists is UNKNOWN, which is NOT the same as 'no'."
        echo "⚠️ [flow-currency] could not compare installed (${INST:-unreadable}) against" >&2
        echo "   marketplace HEAD (${MKT:-unreadable}) — whether an update exists is UNKNOWN," >&2
        echo "   which is NOT the same as 'no'. Run 'claude plugin list' before relying on the" >&2
        echo "   /flow:* machinery being current." >&2
        exit 0
    fi

    echo "[flow-currency] installed flow $INST · marketplace HEAD $MKT · this branch declares $BR" >&2
    echo "[flow-currency] updating the installed plugin…" >&2

    # Fails loud by contract; the reasoning lives on `apply_update` above, once.
    if ! apply_update; then
        say "⚠️ [flow-currency] 'claude plugin update flow@flow' FAILED — installed flow may still be $INST and the marketplace may be unreachable; do NOT assume the /flow:* machinery is current."
        echo "⚠️ [flow-currency] 'claude plugin update flow@flow' FAILED — the flow plugin" >&2
        echo "   may be stale or the marketplace unreachable. Do NOT assume the /flow:*" >&2
        echo "   machinery is current; run 'claude plugin list' before relying on it." >&2
        exit 0
    fi

    NEW=$(python3 "$ENGINE" report --json 2>/dev/null \
          | python3 -c "import json,sys;print((json.load(sys.stdin).get('installed') or {}).get('version',''))" 2>/dev/null)
    if [ -n "$NEW" ] && [ "$NEW" = "$INST" ]; then
        # Same pin as the bootstrap arm, for the same reason: `plugin update` can
        # exit 0 having moved nothing, and an unconditional arrow would read as
        # success. Kept in both arms rather than hoisted, because the two have
        # different "before" sources (engine vs registry) and merging them would
        # mean one of the two reads a value it did not measure.
        say "⚠️ [flow-currency] the flow plugin update reported SUCCESS but installed flow is STILL $NEW — treat the /flow:* machinery as stale, not current."
    else
        say "[flow-currency] installed flow $INST → ${NEW:-unknown}. THIS session still runs $INST — restart Claude Code before relying on any /flow:* command."
    fi
    echo "[flow-currency] installed flow: $INST → ${NEW:-unknown}" >&2
    echo "[flow-currency] NOTE: 'restart required to apply' — THIS session still runs" >&2
    echo "   $INST. The PR body's version rows report what actually ran." >&2
    echo "   → Restart Claude Code now if this session will run any /flow:* command." >&2
    # No trailing `claude plugin list`: it was a ~380ms CLI boot whose output merely
    # restated the "$INST → $NEW" line immediately above, which the engine already
    # sourced from the registry. #116 prints it because it has no engine to ask.
# The `1>&2` that used to close this block is GONE — see the output contract
# above. Every intentional diagnostic still carries its own `>&2`, and the only
# commands in here that write to stdout at all are `say` and the plugin CLI,
# which `cc` redirects. The evals assert the stdout line COUNT per arm, so a
# future un-redirected command leaking into the seat's context turns them red.
}

exit 0
