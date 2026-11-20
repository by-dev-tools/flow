#!/usr/bin/env python3
"""Deterministic core for /flow:retro (v1, FB-0072; group-aware since v1.69.0).

Subcommands, each a pure-ish function the SKILL's bash drives so the
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

Group handling (v1.69.0) — a batch of merged PRs is closed out in ONE run:

  parse-prs     — raw tokens → normalized, de-duplicated PR numbers (accepts `151`, `#151`,
                  comma/space-separated). Refuses anything else, URLs included, with exit 2.
  select        — the DEFAULT group: `gh pr list --state merged` JSON (stdin) → the PR
                  numbers merged since the last retro, per a per-repo watermark. Excludes
                  `docs: land` PRs (the output of a previous retro is not input to the next).
  advance       — advance that watermark past the PRs that were fully closed out.
  branch-plan   — per-PR cleanup decision (remote/local) from the PR's own head ref + head
                  SHA and the repo's real git state. Decides; never deletes.

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
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone


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


# --------------------------------------------------------------------------------------
# Group handling (v1.69.0)
# --------------------------------------------------------------------------------------

def parse_prs(tokens: list[str]) -> list[int]:
    """Normalize raw argument tokens into an ordered, de-duplicated list of PR numbers.

    Accepts `151`, `#151`, and comma- or space-separated runs (`151,153`, `"151 153"`). A PR URL
    is deliberately NOT accepted: it names an owner/repo, and reducing it to a bare number would
    run the close-out (including branch cleanup) against the CURRENT repo's PR of that number. Anything else raises ValueError — a non-number reaching `gh pr view` or a
    branch name is how a typo becomes a cleanup of the wrong thing, so it stops here."""
    out: list[int] = []
    for raw in tokens:
        for tok in re.split(r"[,\s]+", raw):
            tok = tok.strip()
            if not tok:
                continue
            num = tok[1:] if tok.startswith("#") else tok
            if not num.isdigit() or int(num) <= 0:
                raise ValueError(f"not a PR number: {tok!r}")
            n = int(num)
            if n not in out:
                out.append(n)
    return out


# What /flow:land actually emits: `docs: land #<N> …`. A bare "docs: land" prefix would also drop
# a legitimate "docs: landing page copy" PR from the default group, and the watermark would then
# advance past it.
_LAND_TITLE_RE = re.compile(r"docs: land #\d", re.IGNORECASE)


def _parse_ts(value: str):
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def _load_watermark(path: str, repo: str) -> dict:
    try:
        with open(path, encoding="utf-8") as fh:
            obj = json.load(fh)
        rec = obj.get(repo) if isinstance(obj, dict) else None
        return rec if isinstance(rec, dict) else {}
    except (OSError, ValueError):
        return {}


def select_group(prs: list, watermark: dict, now: datetime, fallback_days: int = 7,
                 cap: int = 20) -> tuple[list[int], int]:
    """The default group: merged PRs since the last retro. Returns (numbers, remaining).

    `prs` is the `gh pr list --state merged --json number,title,mergedAt` array.
    - `docs: land` PRs are excluded: they are the OUTPUT of a retro, and once the human
      merges one it would otherwise be picked up as the next retro's input — forever.
    - With a watermark `{"since": <mergedAt>, "done": [numbers merged AT that instant]}`: a PR
      is in iff it merged strictly after `since`, or at `since` and is not in `done`. The
      `done` list is what lets the boundary be inclusive without re-picking its own PRs.
    - Without one (first run in this repo): only the last `fallback_days` days, so a repo's
      whole history is never swept up by a bare `/flow:retro`.
    - Oldest first, at most `cap`; `remaining` says how many more a re-run would pick up, so
      the cap is never a silent truncation."""
    since = _parse_ts(watermark.get("since", "")) if watermark else None
    done = {int(n) for n in watermark.get("done", [])} if watermark else set()
    floor = now - timedelta(days=fallback_days)
    picked = []
    for pr in prs if isinstance(prs, list) else []:
        if not isinstance(pr, dict):
            continue
        title = str(pr.get("title", "") or "")
        if _LAND_TITLE_RE.match(title):
            continue
        ts = _parse_ts(pr.get("mergedAt", ""))
        num = pr.get("number")
        if ts is None or not isinstance(num, int):
            continue
        if since is not None:
            if ts < since or (ts == since and num in done):
                continue
        elif ts < floor:
            continue
        picked.append((ts, num))
    picked.sort()
    nums = [n for _, n in picked]
    return nums[:cap], max(0, len(nums) - cap)


def advance_watermark(path: str, repo: str, closed: list) -> dict:
    """Move the per-repo watermark to the newest `mergedAt` among `closed` PRs
    (`[{"number":…, "mergedAt":…}]`). Monotonic: never moves backwards, and keeps other
    repos' records. Atomic (temp file + replace). Returns the record written."""
    stamped = []
    for p in closed:
        ts = _parse_ts(p.get("mergedAt", "")) if isinstance(p, dict) else None
        if ts is not None and isinstance(p.get("number"), int):
            stamped.append((ts, int(p["number"])))
    if not stamped:
        return {}
    newest = max(ts for ts, _ in stamped)
    done = sorted(n for ts, n in stamped if ts == newest)
    try:
        with open(path, encoding="utf-8") as fh:
            whole = json.load(fh)
        if not isinstance(whole, dict):
            whole = {}
    except (OSError, ValueError):
        whole = {}
    prev = whole.get(repo) if isinstance(whole.get(repo), dict) else {}
    prev_since = _parse_ts(prev.get("since", ""))
    if prev_since is not None:
        if newest < prev_since:
            return prev
        if newest == prev_since:
            done = sorted(set(done) | {int(n) for n in prev.get("done", [])})
    rec = {"since": newest.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"), "done": done}
    whole[repo] = rec
    d = os.path.dirname(os.path.abspath(path))
    os.makedirs(d, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=d, prefix=".last_retro.")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(whole, fh, indent=2, sort_keys=True)
            fh.write("\n")
        os.replace(tmp, path)
    except OSError:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    return rec


_REF_SAFE_RE = re.compile(r"[A-Za-z0-9._/-]+")


def _worktree_branches(cwd: str | None) -> dict:
    """branch short-name -> worktree path, for every worktree that has a branch checked out."""
    rc, out = _git(["worktree", "list", "--porcelain"], cwd)
    found: dict = {}
    if rc != 0:
        return found
    path = None
    for ln in out.splitlines():
        if ln.startswith("worktree "):
            path = ln[len("worktree "):]
        elif ln.startswith("branch refs/heads/") and path:
            found[ln[len("branch refs/heads/"):]] = path
    return found


def branch_plan(blob: dict, default_branch: str, cwd: str | None = None) -> dict:
    """Per-PR branch-cleanup DECISION from the PR's own fields and the repo's real git state.
    Decides only — the SKILL executes, and executes only `delete` verdicts.

    remote: skip-fork | skip-default | unsafe-name | unverified | gone | moved | delete
      - A fork PR's head ref names a branch on someone else's repo; a same-named origin
        branch is unrelated, so a fork is never deleted from here.
      - `delete` requires the remote tip to EQUAL the PR's `headRefOid`. A squash-merge makes
        the merged content unrecognizable to `git branch -d`, so "is it merged?" cannot be
        asked of git; the question that can be answered is "is the branch still exactly what
        the PR merged?". `moved` means someone pushed after the merge — those commits were
        never reviewed, so the branch stays.
      - no `headRefOid` ⇒ `unverified`, never `delete`: no claim to compare against.
    local: absent | skip-* | current | worktree:<path> | delete
      - `worktree:<path>` — checked out in ANOTHER worktree; `git branch -d` would refuse and
        the branch is somebody's live workspace. Named, never touched.
      - `tip_matches` says whether the local tip is the PR's head. `-d` refuses a
        squash-merged branch even then; the SKILL reports it left behind rather than force
        deleting, and this flag lets the report say how safe a manual delete would be."""
    plan = {"remote": "unverified", "local": "absent", "tip_matches": None, "detail": ""}
    name = str(blob.get("headRefName", "") or "")
    oid = str(blob.get("headRefOid", "") or "")
    if blob.get("isCrossRepository") is True:
        plan.update(remote="skip-fork", local="skip-fork", detail="fork PR: head branch lives on the contributor's repo")
        return plan
    if not name:
        plan["detail"] = "gh did not report a head branch"
        return plan
    if name == default_branch:
        plan.update(remote="skip-default", local="skip-default", detail="head is the default branch")
        return plan
    if not _REF_SAFE_RE.fullmatch(name) or name.startswith("-"):
        plan.update(remote="unsafe-name", local="unsafe-name", detail=f"unusual branch name {name!r}")
        return plan

    # `ls-remote <pattern>` matches by ref SUFFIX: `x` also returns `refs/heads/a/x`. Query the
    # full ref and keep only the line whose ref is EXACTLY that one, or a namespaced sibling
    # whose tip happens to equal the merged head would be approved for deletion in its place.
    rc, out = _git(["ls-remote", "--heads", "origin", "--", f"refs/heads/{name}"], cwd)
    tips = []
    for ln in out.splitlines():
        parts = ln.split()
        if len(parts) == 2 and parts[1] == f"refs/heads/{name}":
            tips.append(parts[0])
    if rc != 0:
        plan["remote"] = "unverified"
        plan["detail"] = "could not reach origin"
    elif not tips:
        plan["remote"] = "gone"
    elif not oid:
        plan["remote"] = "unverified"
        plan["detail"] = "no headRefOid to compare the remote tip against"
    elif tips[0] == oid:
        plan["remote"] = "delete"
    else:
        plan["remote"] = "moved"
        plan["detail"] = f"remote tip {tips[0][:9]} != merged head {oid[:9]}"

    rc, lsha = _git(["rev-parse", "--verify", "--quiet", f"refs/heads/{name}"], cwd)
    if rc != 0:
        plan["local"] = "absent"
        return plan
    plan["tip_matches"] = bool(oid) and lsha.strip() == oid
    owners = _worktree_branches(cwd)
    rc_top, top = _git(["rev-parse", "--show-toplevel"], cwd)
    here = os.path.realpath(top.strip()) if rc_top == 0 else None
    owner = owners.get(name)
    if owner is None:
        plan["local"] = "delete"
    elif here is not None and os.path.realpath(owner) == here:
        plan["local"] = "current"
    else:
        plan["local"] = f"worktree:{owner}"
    return plan


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Deterministic core for /flow:retro.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("classify", help="gh pr view --json blob (stdin) → merged/closed/open")

    pv = sub.add_parser("poll-verdict", help="pure poll policy (state, elapsed, cap)")
    pv.add_argument("--state", required=True, choices=["merged", "closed", "open"])
    pv.add_argument("--elapsed", type=float, required=True)
    pv.add_argument("--cap", type=float, required=True)

    ac = sub.add_parser("archive-check", help="git-state cleanliness → safe/not-safe")
    ac.add_argument("--cwd", default=None, help="repo dir (default: current)")

    pp = sub.add_parser("parse-prs", help="raw tokens → normalized PR numbers, one per line")
    pp.add_argument("tokens", nargs="*")

    se = sub.add_parser("select", help="gh pr list --state merged JSON (stdin) → PRs since the last retro")
    se.add_argument("--watermark-file", required=True)
    se.add_argument("--repo", required=True)
    se.add_argument("--fallback-days", type=int, default=7)
    se.add_argument("--cap", type=int, default=20)

    mk = sub.add_parser("advance", help="[{number,mergedAt}] (stdin) → advance the per-repo watermark")
    mk.add_argument("--watermark-file", required=True)
    mk.add_argument("--repo", required=True)

    bp = sub.add_parser("branch-plan", help="gh pr view blob (stdin) → JSON cleanup decision")
    bp.add_argument("--default-branch", required=True)
    bp.add_argument("--cwd", default=None)

    args = ap.parse_args(argv)

    # classify + poll-verdict emit their verdict as the printed WORD and always exit 0
    # (the SKILL branches on stdout). Only archive-check carries a consumed exit code.
    if args.cmd == "classify":
        print(classify(_load_blob()))
        return 0

    if args.cmd == "poll-verdict":
        print(poll_verdict(args.state, args.elapsed, args.cap))
        return 0

    if args.cmd == "parse-prs":
        try:
            nums = parse_prs(args.tokens)
        except ValueError as exc:
            print(f"parse-prs: {exc}", file=sys.stderr)
            return 2
        if not nums:
            print("parse-prs: no PR numbers given", file=sys.stderr)
            return 2
        print("\n".join(str(n) for n in nums))
        return 0

    if args.cmd == "select":
        try:
            prs = json.loads(sys.stdin.read() or "[]")
        except ValueError:
            print("select: stdin is not JSON (did `gh pr list` fail?)", file=sys.stderr)
            return 2
        nums, remaining = select_group(prs, _load_watermark(args.watermark_file, args.repo),
                                       datetime.now(timezone.utc), args.fallback_days, args.cap)
        if nums:
            print("\n".join(str(n) for n in nums))
        if remaining:
            print(f"select: {remaining} more merged PR(s) beyond the cap of {args.cap} — re-run to take them",
                  file=sys.stderr)
        return 0

    if args.cmd == "advance":
        try:
            closed = json.loads(sys.stdin.read() or "[]")
        except ValueError:
            print("advance: stdin is not JSON", file=sys.stderr)
            return 2
        rec = advance_watermark(args.watermark_file, args.repo, closed)
        print(json.dumps(rec) if rec else "no-change")
        return 0

    if args.cmd == "branch-plan":
        print(json.dumps(branch_plan(_load_blob(), args.default_branch, args.cwd), sort_keys=True))
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
