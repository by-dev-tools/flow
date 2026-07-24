#!/usr/bin/env python3
"""Deterministic core for /flow:post-merge (v1, FB-0072).

Three subcommands, each a pure-ish function the SKILL's bash drives so the
merge-queue-safe gate + the archive-safety verdict are testable without a live
`gh` or a real merge:

  classify      — a `gh pr view --json state,mergedAt,autoMergeRequest` blob → one of
                  merged / closed / open. The three-state gate: distinguish
                  "will never merge" (terminal) from "not merged yet" (transient).
  poll-verdict  — the POLL POLICY as a pure function of (state, elapsed, cap): given the
                  classified state and how long we've waited, decide proceed / terminal /
                  wait / giveup-graceful. The SKILL loops `gh view | classify` + this;
                  the I/O (gh + sleep) stays in bash, the *decision* is tested here.
  archive-check — git-state cleanliness in the cwd → `safe` / `not-safe: <reasons>`. The
                  answer to "merged — anything left, safe to archive?".

The verdict is the printed WORD (stdout): `classify` prints merged/closed/open, and
`poll-verdict` prints proceed/terminal/wait/giveup-graceful — the SKILL branches on those
words. There is exactly ONE consumed exit code: `archive-check`'s 0 (safe) / 1 (not-safe),
which the SKILL uses in an `if`. classify/poll-verdict always exit 0 (the word is the signal),
so no caller is tempted to key on a code that can't carry the elapsed/cap-dependent verdict.
Stdlib only, Python 3.7+.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys


def _load_blob() -> dict:
    """Read the `gh pr view --json` blob from stdin (the SKILL pipes it in)."""
    raw = (sys.stdin.read() or "").strip()
    if not raw:
        return {}
    try:
        obj = json.loads(raw)
        return obj if isinstance(obj, dict) else {}
    except (ValueError, TypeError):
        return {}


def classify(blob: dict) -> str:
    """Three-state merge classification from a `gh pr view --json` object.

    - `state == "MERGED"` (or a truthy `mergedAt`) → 'merged'.
    - `state == "CLOSED"` and NOT merged → 'closed' (terminal — closed without merging).
    - anything else, incl. `state == "OPEN"` and the ambiguous/empty case → 'open'
      (transient; the poll decides whether to keep waiting). We default the UNKNOWN
      case to 'open' (poll), NOT 'closed' (fail): a transient "can't tell yet" must
      never be treated as the terminal "will never merge" — that's the whole point of
      the three-state gate (distinguish not-yet from never)."""
    state = str(blob.get("state", "") or "").upper()
    merged = state == "MERGED" or bool(blob.get("mergedAt"))
    if merged:
        return "merged"
    if state == "CLOSED":
        return "closed"
    return "open"


def poll_verdict(state: str, elapsed: float, cap: float) -> str:
    """Pure poll policy. `state` is a classify() result; `elapsed`/`cap` are seconds.

    merged                 → 'proceed'          (the SKILL breaks the loop)
    closed                 → 'terminal'         (fail loud — CLOSED-unmerged)
    open, elapsed <  cap    → 'wait'            (the SKILL sleeps + re-checks)
    open, elapsed >= cap    → 'giveup-graceful' (calm "still queued, re-run")

    cap == 0 (fail-fast, non-queue repos) short-circuits an OPEN PR straight to
    'giveup-graceful' — NOT 'terminal': it's still "not merged yet", we just don't wait.
    An unrecognized state is treated as still-pending, NEVER terminal (same rule as
    classify's unknown→open): we never turn "can't tell yet" into "will never happen"."""
    if state == "merged":
        return "proceed"
    if state == "closed":
        return "terminal"
    if cap > 0 and elapsed < cap:
        return "wait"
    return "giveup-graceful"


def _git(args: list[str], cwd: str | None = None) -> tuple[int, str]:
    try:
        p = subprocess.run(["git", *args], capture_output=True, text=True, cwd=cwd, timeout=15)
        return p.returncode, (p.stdout or "")
    except (OSError, subprocess.SubprocessError):
        return 1, ""


def archive_check(cwd: str | None = None) -> tuple[bool, list[str]]:
    """Is this worktree safe to archive? Returns (safe, reasons). `reasons` is empty
    iff safe. Each check is a distinct, nameable reason so the verdict is actionable —
    never a bare 'not safe'.

    Checks (each an independent 'you'd lose work' signal):
      - uncommitted tracked changes (staged or unstaged) — `git status --porcelain`
        lines that are not untracked (`??`).
      - stray untracked files — `??` lines (build artifacts included: an archive that
        silently drops them is still surprising; the verdict NAMES them so the human
        decides, it does not delete).
      - unpushed commits — commits on HEAD not on its upstream (`@{u}..HEAD`). No
        upstream configured is itself worth surfacing (can't confirm the work is pushed).
    """
    reasons: list[str] = []

    rc, porcelain = _git(["status", "--porcelain"], cwd)
    if rc != 0:
        return False, ["not a git repository (or git unavailable)"]
    lines = [ln for ln in porcelain.splitlines() if ln.strip()]
    tracked = [ln for ln in lines if not ln.startswith("??")]
    untracked = [ln for ln in lines if ln.startswith("??")]
    if tracked:
        reasons.append(f"{len(tracked)} uncommitted change(s) (staged/unstaged)")
    if untracked:
        reasons.append(f"{len(untracked)} untracked file(s)")

    # Unpushed commits — only meaningful when an upstream exists.
    rc_up, _ = _git(["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"], cwd)
    if rc_up == 0:
        rc_ahead, ahead = _git(["rev-list", "--count", "@{u}..HEAD"], cwd)
        if rc_ahead == 0 and ahead.strip() not in ("", "0"):
            reasons.append(f"{ahead.strip()} unpushed commit(s)")
    else:
        reasons.append("no upstream set for the current branch (cannot confirm work is pushed)")

    return (not reasons), reasons


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Deterministic core for /flow:post-merge.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("classify", help="gh pr view --json blob (stdin) → merged/closed/open")

    pv = sub.add_parser("poll-verdict", help="pure poll policy (state, elapsed, cap)")
    pv.add_argument("--state", required=True, choices=["merged", "closed", "open"])
    pv.add_argument("--elapsed", type=float, required=True)
    pv.add_argument("--cap", type=float, required=True)

    ac = sub.add_parser("archive-check", help="git-state cleanliness → safe/not-safe")
    ac.add_argument("--cwd", default=None, help="repo dir (default: current)")

    args = ap.parse_args(argv)

    # classify + poll-verdict emit their verdict as the printed WORD and always exit 0
    # (the SKILL branches on stdout). Only archive-check carries a consumed exit code.
    if args.cmd == "classify":
        print(classify(_load_blob()))
        return 0

    if args.cmd == "poll-verdict":
        print(poll_verdict(args.state, args.elapsed, args.cap))
        return 0

    if args.cmd == "archive-check":
        safe, reasons = archive_check(args.cwd)
        if safe:
            print("safe")
            return 0
        print("not-safe: " + "; ".join(reasons))
        return 1

    return 2


if __name__ == "__main__":
    sys.exit(main())
