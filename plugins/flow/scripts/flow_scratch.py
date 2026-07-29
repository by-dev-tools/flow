#!/usr/bin/env python3
"""
Repo-local scratch resolution + handoff stamping for flow (FB-0075).

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

SCRATCH_DIRNAME = ".flow"
# Used only when cwd is not inside a git repo. Deliberately NOT a stable shared name:
# a detached run has no repo identity, so it gets no cross-run continuity either.
DETACHED_PREFIX = "flow-detached"


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


def scratch_dir(cwd=None, create=True):
    """Resolve the repo-local scratch dir. Falls back to a temp dir when detached.

    Returns (path, is_repo_local). `is_repo_local` False means the caller is not in
    a git repo, so the path is NOT shared with a forked skill -- callers that depend
    on the handoff crossing that boundary must treat it as a hard failure, not a
    silent degrade (that silent degrade is the bug this module exists to remove).
    """
    root = repo_root(cwd=cwd)
    if root:
        path = Path(root) / SCRATCH_DIRNAME
        repo_local = True
    else:
        import tempfile

        path = Path(os.environ.get("TMPDIR") or tempfile.gettempdir()) / DETACHED_PREFIX
        repo_local = False
    if create:
        try:
            path.mkdir(parents=True, exist_ok=True)
            if repo_local:
                _ensure_ignored(path)
        except OSError:
            pass
    return str(path), repo_local


def scratch_path(name, cwd=None, create=True):
    """Path for one named scratch artifact inside the scratch dir."""
    d, _ = scratch_dir(cwd=cwd, create=create)
    return str(Path(d) / name)


def _ensure_ignored(scratch):
    """Self-ignore so flow never dirties a consumer's `git status`.

    A `.gitignore` INSIDE `.flow/` ignoring `*` keeps the whole thing out of the
    index without touching the project's own `.gitignore` -- flow must not edit a
    file the project owns just to hold its scratch.
    """
    marker = Path(scratch) / ".gitignore"
    if marker.exists():
        return
    try:
        marker.write_text("# Created by flow. Ephemeral scratch; never committed.\n*\n", encoding="utf-8")
    except OSError:
        pass


def current_stamp(cwd=None):
    """The identity a handoff is stamped with / checked against."""
    return {
        "repo": repo_root(cwd=cwd),
        "branch": _git(["branch", "--show-current"], cwd=cwd),
        "head": _git(["rev-parse", "--short", "HEAD"], cwd=cwd),
    }


def stamp_payload(payload, cwd=None):
    """Return `payload` with a `flow_stamp` attached (dict payloads only)."""
    if not isinstance(payload, dict):
        return payload
    out = dict(payload)
    out["flow_stamp"] = current_stamp(cwd=cwd)
    return out


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
    """CLI so shell callers can resolve paths without re-implementing the logic."""
    import argparse

    ap = argparse.ArgumentParser(description="flow repo-local scratch resolution")
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("dir", help="print the scratch dir")
    d.add_argument("--no-create", action="store_true")
    p = sub.add_parser("path", help="print the path for one named artifact")
    p.add_argument("name")
    p.add_argument("--no-create", action="store_true")
    sub.add_parser("stamp", help="print the current repo/branch/head stamp as JSON")
    c = sub.add_parser("check", help="stamp-check a JSON handoff; exit 0 only when usable")
    c.add_argument("path")

    args = ap.parse_args(argv[1:])
    if args.cmd == "dir":
        path, repo_local = scratch_dir(create=not args.no_create)
        print(path)
        return 0 if repo_local else 3
    if args.cmd == "path":
        print(scratch_path(args.name, create=not args.no_create))
        return 0
    if args.cmd == "stamp":
        print(json.dumps(current_stamp()))
        return 0
    payload, status, reason = read_stamped(args.path)
    print(json.dumps({"status": status, "reason": reason}))
    return 0 if status == "ok" else (1 if status == "absent" else 2)


if __name__ == "__main__":
    import sys

    sys.exit(main(sys.argv))
