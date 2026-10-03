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
        default branch. COMMIT-INVARIANT (and tracking-invariant): every changed-or-new source
        file is folded in by its current WORKING-TREE CONTENT, not by diff-patch text, so
        committing staff-review's fixes — OR committing a brand-new untracked file — between
        staff-review and ship does NOT change the fingerprint; only an actual source-content
        change does. Resolves the default branch via git symbolic-ref →
        --default-branch → "main"; uses the built-in source pattern unless --source-pattern given.
        That pattern is UNIONED with `lib/doc_patterns.py`'s behaviour-bearing prose set (the
        same one /flow:audit-coverage uses) plus flow.config.json's `behaviorBearingDocPatterns`,
        so a skill or agent prompt rewritten after staff-review moves the fingerprint.
        Dev-tracking docs stay OUT on purpose — ship Step 5 rewrites the plan doc in the same
        commit as the code, so including them would report drift on every ship run.
        Always exits 0 (a broken/absent git context degrades to the empty-input hash, which both
        writer and reader compute identically, so the gate no-ops rather than false-failing).

    rigor-marker.py write --branch B --source-sha S [--path P]
        Write marker JSON {"branch", "source_sha"}. Default path (when --path omitted):
        <repo-root>/.flow/staff-review-marker-<branch-slug>.json. Prints the path. Exit 0; a
        write failure → stderr + exit 1 (graceful: the caller warns, never aborts the review).

        REPO-LOCAL since FB-0082. The old default was /tmp/flow-staff-review-marker-<slug>.json,
        keyed on branch name alone in one global namespace — so two projects on a same-named
        branch ("main", "claude/fix-x") wrote to the SAME file. That failed safe rather than
        open (the source_sha would mismatch, reading as "source-drift" instead of "ok"), but it
        made one project's staff-review invalidate another's rigor gate for no reason. Keying on
        the worktree root removes the collision instead of relying on the hash to absorb it.

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
import tempfile
from pathlib import Path

# Shared behaviour-bearing-prose patterns (`plugins/flow/lib/doc_patterns.py`) — the same
# definition `/flow:audit-coverage`'s evidence block uses. Imported rather than copied; a
# partial install degrades to the source-only fingerprint with a LOUD warning rather than
# silently restoring the doc-blind gate this closes.
_SHARED_LIB = Path(__file__).resolve().parents[3] / "lib"
if str(_SHARED_LIB) not in sys.path:
    sys.path.insert(0, str(_SHARED_LIB))
try:
    import doc_patterns  # type: ignore
except Exception as _e:  # noqa: BLE001 - see below
    # `except Exception`, not `except ImportError`: this module's documented contract is that
    # `source-sha` ALWAYS exits 0, and a truncated or corrupt `doc_patterns.py` from a partial
    # install raises SyntaxError, not ImportError. That escaped, tracebacked, and left
    # `SRC_SHA=""` in the caller's `$( )` -- a fingerprint of nothing, which compares equal
    # between writer and reader and silently passes the rigor gate.
    doc_patterns = None
    _DOC_IMPORT_ERROR = f"{type(_e).__name__}: {_e}"

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


def _resolve_default_branch(arg: str | None) -> str:
    ref = _git(["symbolic-ref", "refs/remotes/origin/HEAD"]).strip()
    if ref:
        return ref.rsplit("/", 1)[-1]
    return arg or "main"


def source_sha(default_branch: str | None, source_pattern: str | None) -> str:
    """Content fingerprint of the source-file delta vs origin/<default>, INVARIANT to each
    file's tracked/untracked + committed/uncommitted status.

    Every source file whose working-tree state differs from base — tracked-and-changed
    (committed OR uncommitted; `git diff <base>` with no `..HEAD` compares base to the working
    tree) OR untracked — is folded in by its PATH + current working-tree BYTES. It deliberately
    does NOT hash the `git diff` PATCH text: a patch of identical content differs between the
    untracked and tracked representations (the tracked side carries `diff --git` / `@@` / `+`
    framing the raw bytes lack), so hashing the patch made an untracked→committed transition
    flip the fingerprint — a FALSE source-drift at ship Step 1.0a on every new-file PR (a real
    dogfood + Swift-stack cold-run bug). Hashing working-tree content is representation-invariant,
    so committing a new file — like committing a modification — leaves the fingerprint unchanged."""
    branch = _resolve_default_branch(default_branch)
    base = f"origin/{branch}"

    # Source ∪ behaviour-bearing prose. `sourceFilePatterns` matches no `.md` path at all --
    # deliberately, since that is what keeps a docs-only PR off the source-touching branches of
    # /flow:ship -- so computing the rigor fingerprint through it alone left prose out of the
    # evidence that staff-review ran. Measured on #172: 0 of 13 changed `.md` files were in the
    # fingerprint, including the two SHIPPED SKILL.md files that PR existed to change. Prose is
    # deployed surface here, so a post-review rewrite of it must move the fingerprint.
    #
    # Union, not replacement: nothing is removed from the source side, and the ADDED half is
    # narrow by construction (`doc_patterns.DOC_BUILTIN` plus whatever the consumer declares).
    # A dev-tracking doc must stay OUT -- /flow:ship Step 5 rewrites planPath in the same commit
    # that carries the code, so pulling plan/history/feedback docs in would report source-drift
    # on every ship run, and a gate that always fires is one people learn to click past.
    # SEPARATELY COMPILED patterns, never a concatenation. A consumer's `sourceFilePatterns`
    # and their `behaviorBearingDocPatterns` are two independent values; joining them with `|`
    # created a third expression neither side had validated, and an inline flag in either one
    # then changed the meaning of the other. Matching is `any(p.search(f))`.
    pats = []
    src_expr = source_pattern or DEFAULT_SOURCE_PATTERN
    try:
        pats.append(re.compile(src_expr))
    except re.error as exc:
        # Pre-existing fail-open on a line this change rewrites anyway: an invalid
        # `sourceFilePatterns` raised out of a function contracted to always exit 0, leaving an
        # EMPTY fingerprint that compares equal to the other side's empty fingerprint. Degrade
        # to the documented default and say so.
        print(f"rigor-marker: [WARN] ⚠️ sourceFilePatterns is not a valid regex ({exc}); using "
              f"the built-in default instead.", file=sys.stderr)
        pats.append(re.compile(DEFAULT_SOURCE_PATTERN))
    if doc_patterns is not None:
        doc_pats, doc_warnings = doc_patterns.doc_patterns_list()
        for w in doc_warnings:
            print(f"rigor-marker: {w}", file=sys.stderr)
        pats.extend(doc_pats)
    else:
        print(f"rigor-marker: [WARN] ⚠️ cannot import doc_patterns from {_SHARED_LIB} "
              f"({_DOC_IMPORT_ERROR}) — behaviour-bearing DOC changes are NOT in this "
              f"fingerprint, so prose edited after staff-review will not be detected. "
              f"Reinstall the plugin.", file=sys.stderr)

    def _matches(path: str) -> bool:
        return any(p.search(path) for p in pats)

    # Union of (tracked-and-changed-vs-base) and (untracked) source files — the two ways a
    # file can be part of this PR's source delta. A file moving between these two sets across a
    # commit is exactly the transition that must NOT change the digest.
    changed = {
        f for f in _git(["diff", base, "--name-only"]).splitlines() if f and _matches(f)
    }
    changed |= {
        f for f in _git(["ls-files", "--others", "--exclude-standard"]).splitlines()
        if f and _matches(f)
    }

    h = hashlib.sha256()
    for f in sorted(changed):
        h.update(f.encode("utf-8"))
        h.update(b"\0")
        # Current working-tree content — identical whether f is tracked or untracked, so the
        # digest is stable across an untracked→committed transition. A path present only
        # because it was DELETED vs base has no working-tree bytes → a deletion sentinel.
        try:
            # NEVER follow a symlink or read a non-regular file. This loop now covers `.md`
            # paths, which is the file class a human reviewer is least likely to check for a
            # symlink, and `read_bytes()` on a link to /dev/zero raises MemoryError -- which is
            # not an OSError, so it escaped this handler, crashed the process, and produced the
            # empty-fingerprint fail-open described above. A sentinel keeps the digest
            # well-defined and keeps the path IN the fingerprint, so swapping a file for a link
            # still moves it.
            fp = Path(f)
            if fp.is_symlink():
                h.update(b"\2symlink-not-followed")
            elif not fp.is_file():
                h.update(b"\3not-a-regular-file")
            else:
                h.update(fp.read_bytes())
        except OSError:
            h.update(b"\1missing-or-deleted")
        h.update(b"\0")
    return h.hexdigest()


def _slug(branch: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]", "-", branch) or "detached"


def _default_path(branch: str) -> Path:
    """Repo-local marker path (FB-0082); falls back to the legacy /tmp form only when
    there is no enclosing worktree, so a detached run still functions rather than
    writing to the filesystem root."""
    root = _git(["rev-parse", "--show-toplevel"]).strip()
    if root:
        d = Path(root) / ".flow"
        try:
            d.mkdir(parents=True, exist_ok=True)
            ign = d / ".gitignore"
            if not ign.exists():
                ign.write_text("# Created by flow. Ephemeral scratch; never committed.\n*\n", encoding="utf-8")
        except OSError:
            pass
        return d / f"staff-review-marker-{_slug(branch)}.json"
    return Path(f"{tempfile.gettempdir()}/flow-staff-review-marker-{_slug(branch)}.json")


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
