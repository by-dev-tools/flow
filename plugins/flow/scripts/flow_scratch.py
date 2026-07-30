#!/usr/bin/env python3
"""
Handoff stamping for flow (FB-0075).

Two failures this exists to close, which turned out to share one cause and one fix:

1. FORK TRANSPORT. A `context: fork` skill cannot see a `/tmp` handoff written by
   the parent shell. Reproduced as a same-file A/B: `/tmp/flow-skip-audit-stages.json`,
   valid and readable, yielded a full report from the parent shell and
   "no stage report to audit" from `Skill("flow:audit-skips")`. Every forked reader
   of a `/tmp` handoff is therefore blind to it, which silently disabled the
   skip-legitimacy gate. A REPO-RELATIVE path is visible to both.

2. CROSS-PROJECT COLLISION. `/tmp/flow-*` is one global namespace, so two sessions on
   two different projects clobber each other's reviewer inputs (observed: a staff-review
   lens reading another project's diff). A repo-relative path is per-repo BY
   CONSTRUCTION -- no hashing, no session id, nothing to keep unique.

So the scratch root is `<repo-root>/.flow` (already the schema's documented
project-local convention for `verifyFindingsPath` / `verifyReportPath`).

SCOPE: this module owns STAMPING only, not scratch-path resolution. Resolution lives
in shell, duplicated at each site, because `CLAUDE_PLUGIN_ROOT` is unset in Bash-tool
fenced blocks and a helper is therefore unreachable there -- the same justified
duplication as the FB-0008 base-resolution idiom. A parallel Python implementation
would be both unreached and, worse, a tempting test target that passes while the
shipped shell path goes unexercised. The shell idiom is pinned instead, by extracting
and EXECUTING it in `evals/run_scratch_isolation_evals.py`.

Namespacing alone is not sufficient, because two worktrees of ONE repo still collide,
and a stale file from an earlier branch in the SAME worktree still reads as current.
So every handoff also carries a `flow_stamp` (repo + branch + head), and readers
REFUSE a stamp that does not match HEAD rather than reading it and hoping the
consumer notices.

Stdlib only. Python 3.7+.

Shell counterpart (the canonical idiom -- keep these in sync; pinned by
`evals/run_scratch_isolation_evals.py`):

    FLOW_ROOT=$(git rev-parse --show-toplevel 2>/dev/null)
    [ -n "$FLOW_ROOT" ] && FLOW_SCRATCH="$FLOW_ROOT/.flow" || FLOW_SCRATCH="${TMPDIR:-/tmp}/flow-detached"
    mkdir -p "$FLOW_SCRATCH" 2>/dev/null
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

# The scratch dir name the shell idiom builds; kept here so the two agree.
SCRATCH_DIRNAME = ".flow"


def _git(args, cwd=None):
    """Run git, returning stripped stdout, or '' on any failure."""
    try:
        out = subprocess.run(
            ["git", *args], capture_output=True, text=True, timeout=10, cwd=cwd
        )
        return out.stdout.strip() if out.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def repo_root(cwd=None):
    """Absolute path of the enclosing git worktree, or '' when there is none.

    NOTE: this resolves against `cwd` like every other git call in flow. It cannot
    discover a repo the caller never pointed at -- that is not what it is for. Its
    job is to give the parent shell and a forked skill the SAME answer when both
    run in the same tree, which `/tmp` did not.
    """
    return _git(["rev-parse", "--show-toplevel"], cwd=cwd)


def current_stamp(cwd=None):
    """The identity a handoff is stamped with / checked against.

    Two git calls, not three: `rev-parse` returns toplevel and short HEAD together.
    (Folding the branch in as well does not work -- `--abbrev-ref` is sticky and makes
    the following `--short HEAD` re-emit the branch.) This runs synchronously inside a
    forked skill's context block while the user waits, so the call count is worth
    keeping down.
    """
    lines = _git(["rev-parse", "--show-toplevel", "--short", "HEAD"], cwd=cwd).splitlines()
    return {
        "repo": lines[0].strip() if len(lines) > 0 else "",
        "head": lines[1].strip() if len(lines) > 1 else "",
        "branch": _git(["branch", "--show-current"], cwd=cwd),
    }


def check_stamp(payload, cwd=None, expect=None):
    """Verify a handoff belongs to THIS repo+branch+HEAD.

    Returns (ok, reason). `ok` False means REFUSE the payload -- do not read it and
    hope someone notices. An ABSENT stamp is refused too: an unstamped handoff is
    indistinguishable from another project's, and "written by an older flow" is not
    a reason to trust it (fail closed -- FB-0062).
    """
    if not isinstance(payload, dict):
        return False, "handoff is not a JSON object"
    got = payload.get("flow_stamp")
    if not isinstance(got, dict):
        return False, "handoff carries no flow_stamp (cannot prove it belongs to this repo/HEAD)"
    want = expect if expect is not None else current_stamp(cwd=cwd)
    for field in ("repo", "branch", "head"):
        g, w = got.get(field), want.get(field)
        # A stamp is untrusted input (it can arrive in a checked-in handoff). A non-string
        # field must REFUSE, not raise: os.path.realpath(1) throws TypeError, which escaped
        # this function and violated its documented (ok, reason) contract -- the caller then
        # reported a toolchain problem for what is actually a malformed handoff.
        if g is not None and not isinstance(g, str):
            return False, f"handoff {field} is {type(g).__name__}, not a string -- malformed stamp"
        if field == "repo":
            # Compare RESOLVED paths. A symlinked repo root (macOS /var -> /private/var,
            # or a symlinked worktree) can otherwise render two spellings of the same
            # directory as a mismatch -> a spurious stamp_error -> a clean PR routed to
            # draft. This only removes FALSE positives: a genuinely different repo still
            # resolves differently. Refusing wrongly is as bad as passing wrongly here,
            # because a gate that cries wolf gets waived by habit.
            g = os.path.realpath(g) if g else g
            w = os.path.realpath(w) if w else w
        # An empty EXPECTED value means we could not determine it locally (detached
        # HEAD, no repo). Refuse rather than wave it through -- an undeterminable
        # identity cannot corroborate anything.
        if not w:
            return False, f"cannot determine local {field} to check the handoff against"
        if g != w:
            return False, f"handoff {field}={g!r} does not match this workspace ({w!r})"
    return True, "stamp matches this repo/branch/HEAD"


def read_stamped(path, cwd=None):
    """Read + stamp-check a JSON handoff.

    Returns (payload_or_None, status, reason) where status is one of:
      "ok"       -- present and the stamp matches; payload is usable
      "absent"   -- no file at that path (a legitimate no-op for optional handoffs)
      "invalid"  -- present but unparseable
      "stale"    -- present and parseable but the stamp does not match -> REFUSE

    "absent" and "stale" are deliberately DISTINCT: collapsing them is what let a
    foreign or out-of-date buffer read as "nothing to do".
    """
    p = Path(path)
    if not p.exists():
        return None, "absent", f"no handoff at {path}"
    try:
        payload = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return None, "invalid", f"handoff at {path} is unreadable: {exc}"
    ok, reason = check_stamp(payload, cwd=cwd)
    if not ok:
        return None, "stale", reason
    return payload, "ok", reason


def main(argv):
    """CLI so a skill's `!`-block can stamp-check a handoff (where CLAUDE_PLUGIN_ROOT IS set)."""
    import argparse

    ap = argparse.ArgumentParser(description="flow handoff stamping")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("stamp", help="print the current repo/branch/head stamp as JSON")
    c = sub.add_parser("check", help="stamp-check a JSON handoff; exit 0 only when usable")
    c.add_argument("path")

    args = ap.parse_args(argv[1:])
    if args.cmd == "stamp":
        print(json.dumps(current_stamp()))
        return 0
    payload, status, reason = read_stamped(args.path)
    print(json.dumps({"status": status, "reason": reason}))
    return 0 if status == "ok" else (1 if status == "absent" else 2)


if __name__ == "__main__":
    import sys

    sys.exit(main(sys.argv))
