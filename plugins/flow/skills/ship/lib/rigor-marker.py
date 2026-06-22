#!/usr/bin/env python3
"""Rigor-gate marker helper — shared by /flow:staff-review (writer) and /flow:ship (reader).

The marker is the mechanical evidence that /simplify + /flow:staff-review actually ran on
THIS source (FB-0047 "enforce, don't attest"). /flow:staff-review writes it after its lenses
run and its blocker/nit fixes are applied; /flow:ship Step 1.0 reads it for a source-touching,
non-spike diff and routes a missing/stale marker to the draft manifest as a [decision-required]
finding. Centralizing the contract here keeps the source-fingerprint logic in ONE place rather
than duplicated across two SKILL.md shell blocks (FB-0054(b) "share the primitive").

Subcommands (stdlib only):

    rigor-marker.py source-sha [--default-branch B] [--source-pattern P]
        Print a deterministic hex fingerprint of the SOURCE-file portion of the diff vs the
        default branch. COMMIT-INVARIANT: it diffs `origin/<default>` against the WORKING TREE
        (not `..HEAD`), so committing staff-review's fixes between staff-review and ship does
        NOT change the fingerprint — only an actual source-content change does. Untracked source
        files are folded in by content. Resolves the default branch via git symbolic-ref →
        --default-branch → "main"; uses the built-in source pattern unless --source-pattern given.
        Always exits 0 (a broken/absent git context degrades to the empty-input hash, which both
        writer and reader compute identically, so the gate no-ops rather than false-failing).

    rigor-marker.py write --branch B --source-sha S [--path P]
        Write marker JSON {"branch", "source_sha"}. Default path (when --path omitted):
        /tmp/flow-staff-review-marker-<branch-slug>.json. Prints the path. Exit 0; a write
        failure → stderr + exit 1 (graceful: the caller warns, never aborts the review).

    rigor-marker.py check --branch B --source-sha S [--path P]
        Exit 0 + "ok" iff the marker exists AND .branch == B AND .source_sha == S. Otherwise
        exit 1 + a named reason on stdout: "missing", "branch-mismatch", or "source-drift".

Exit codes are the contract the shell keys on; keep them stable.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

# Default extended-regex source pattern — MUST match ship Step 1c / verify-build Step 2.
DEFAULT_SOURCE_PATTERN = (
    r"\.(ts|tsx|js|jsx|mjs|cjs|py|rs|swift|go|rb|java|kt|sh|bash|tf|tfvars|sql|proto|graphql|gql)$"
    r"|\.(json|ya?ml|toml)$|(^|/)(Dockerfile|Makefile)(\.|$)"
)


def _git(args: list[str]) -> str:
    """Best-effort git read; empty string on any failure (callers degrade gracefully)."""
    try:
        out = subprocess.run(["git", *args], capture_output=True, text=True, timeout=15)
        return out.stdout if out.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def _git_bytes(args: list[str]) -> bytes:
    try:
        out = subprocess.run(["git", *args], capture_output=True, timeout=15)
        return out.stdout if out.returncode == 0 else b""
    except (OSError, subprocess.SubprocessError):
        return b""


def _resolve_default_branch(arg: str | None) -> str:
    ref = _git(["symbolic-ref", "refs/remotes/origin/HEAD"]).strip()
    if ref:
        return ref.rsplit("/", 1)[-1]
    return arg or "main"


def source_sha(default_branch: str | None, source_pattern: str | None) -> str:
    """Commit-invariant fingerprint of the source-file delta vs origin/<default> + untracked."""
    branch = _resolve_default_branch(default_branch)
    pat = re.compile(source_pattern or DEFAULT_SOURCE_PATTERN)
    base = f"origin/{branch}"

    # Tracked files whose working-tree content differs from base (committed OR uncommitted —
    # `git diff <base>` with no `..HEAD` compares base to the working tree, so the partition
    # between committed and uncommitted is irrelevant: only net content matters).
    tracked = sorted(
        f for f in _git(["diff", base, "--name-only"]).splitlines() if f and pat.search(f)
    )
    untracked = sorted(
        f for f in _git(["ls-files", "--others", "--exclude-standard"]).splitlines()
        if f and pat.search(f)
    )

    h = hashlib.sha256()
    h.update(("\n".join(tracked) + "\0").encode("utf-8"))
    # Net tracked patch vs base, restricted to the source files (deterministic, commit-invariant).
    if tracked:
        h.update(_git_bytes(["diff", base, "--", *tracked]))
    h.update(b"\0")
    h.update(("\n".join(untracked) + "\0").encode("utf-8"))
    # Untracked files have no diff — fold their bytes in by sorted path.
    for f in untracked:
        try:
            h.update(Path(f).read_bytes())
        except OSError:
            pass
        h.update(b"\0")
    return h.hexdigest()


def _slug(branch: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]", "-", branch) or "detached"


def _default_path(branch: str) -> Path:
    return Path(f"/tmp/flow-staff-review-marker-{_slug(branch)}.json")


def cmd_write(args) -> int:
    path = Path(args.path) if args.path else _default_path(args.branch)
    try:
        path.write_text(
            json.dumps({"branch": args.branch, "source_sha": args.source_sha}),
            encoding="utf-8",
        )
    except OSError as e:
        print(f"[rigor-marker] could not write marker {path}: {e}", file=sys.stderr)
        return 1
    print(str(path))
    return 0


def cmd_check(args) -> int:
    path = Path(args.path) if args.path else _default_path(args.branch)
    if not path.is_file():
        print("missing")
        return 1
    try:
        m = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        print("missing")  # unreadable marker is no evidence — treat as absent
        return 1
    if str(m.get("branch", "")) != args.branch:
        print("branch-mismatch")
        return 1
    if str(m.get("source_sha", "")) != args.source_sha:
        print("source-drift")
        return 1
    print("ok")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Rigor-gate marker helper.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_sha = sub.add_parser("source-sha")
    p_sha.add_argument("--default-branch")
    p_sha.add_argument("--source-pattern")

    p_w = sub.add_parser("write")
    p_w.add_argument("--branch", required=True)
    p_w.add_argument("--source-sha", required=True)
    p_w.add_argument("--path")

    p_c = sub.add_parser("check")
    p_c.add_argument("--branch", required=True)
    p_c.add_argument("--source-sha", required=True)
    p_c.add_argument("--path")

    args = ap.parse_args(argv)
    if args.cmd == "source-sha":
        print(source_sha(args.default_branch, args.source_pattern))
        return 0
    if args.cmd == "write":
        return cmd_write(args)
    if args.cmd == "check":
        return cmd_check(args)
    return 2


if __name__ == "__main__":
    sys.exit(main())
