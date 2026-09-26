#!/usr/bin/env python3
"""Deterministic change inventory for /flow:audit-coverage (FB-0115).

WHY THIS EXISTS. Across four live runs with known ground truth the coverage reviewer
found 10-of-10, 5-of-10, 0-of-5 and 2-of-5 of the gaps present, at precision 4/4 --
it has never once reported a gap that was not real. Recall is the whole problem. The
mechanism, read off the shipped prompt rather than guessed: `SKILL.md`'s single pass
fuses *enumerate* the behaviours, *match* them against criteria, and *suppress* weak
findings into one invisible step. Because the enumeration is never written down, a run
that enumerated 6 of 11 behaviours emits a clean result INDISTINGUISHABLE from a
thorough one. That is `.claude/rules/general.md` Consistency item 4 -- a measurement
that can only return "clean" -- living inside a shipped gate.

This script supplies the half that must NOT be judgment. It enumerates the hunks
deterministically so the reviewer's Stage 1 has a checklist it must account for: a
behaviour it fails to enumerate now shows up as an UNACCOUNTED row instead of as
silence. "The model can suggest, but never define."

It also answers the sequencing question that produced 3 of the 5 measured misses in
#158 and all 5 in #159: behaviour added during `/simplify` and `/flow:staff-review`
lands AFTER the Spec-walk was written, so no declared criterion CAN cover it. That is
not a heuristic and not a prior -- it is a `git` fact, computed here:

  POST-PLAN            the hunk's new-side lines are also changed by
                       <last-plan-commit>..HEAD, i.e. it landed after the plan was
                       last edited. No criterion can have been written for it.
  UNCOMMITTED          present only in the working tree. Same logic, stronger.
  SAME-COMMIT          the commit that last touched the plan also touched this
                       file's lines. Genuinely ambiguous, labelled rather than
                       guessed either way.
  pre-plan             the plan was edited after this landed, so a criterion could
                       exist. The unremarkable case; lower-cased so the eye goes to
                       the others.
  PLAN-PREDATES-BRANCH the plan was never touched on this branch at all -- a
                       STRONGER signal than POST-PLAN, not a missing one, so it gets
                       its own tier instead of collapsing into "unknown".

FAIL LOUD, NEVER CLEAN. Every failure path prints `INVENTORY-UNAVAILABLE -- <reason>`
and exits 0. It must never print nothing, and must never print the evidence block's
`SKIPPED` line: "I could not build the checklist" and "there was nothing to check"
have opposite consequences, and only the first must weaken the result (FB-0074's shape,
applied to a new outcome).

Stdlib only. Python 3.7+.

Usage (the evidence block's call -- the file list arrives on stdin so there is exactly
ONE source-file filter in the system, the block's own, and no fan-out to keep in sync):

    printf '%s\n' "$FILES" | python3 change-inventory.py --base origin/main --plan dev-docs/plan.md
"""

from __future__ import annotations

import argparse
import pathlib
import re
import subprocess
import sys

# Cap + its warning, together. An uncapped inventory on a large PR would crowd out the
# diff it annotates; an uncapped-but-silent one would hide that it did (FB-0010: pair
# every cap with a [WARN]).
DEFAULT_MAX_ROWS = 250
# Funcname context from a hunk header is attacker-influenced text (it is a line of the
# file under review) landing in prompt context. It is indented by the renderer and
# truncated here so it cannot carry a plausible control line.
FUNCNAME_MAX = 70

# Tier strength, one definition. `put()` never demotes a row, so a hunk present in both
# the cumulative and the post-plan diff keeps POST-PLAN rather than whichever loop ran last.
_RANK = {"pre-plan": 0, "SAME-COMMIT": 1, "POST-PLAN": 2, "UNCOMMITTED": 3,
         "PLAN-PREDATES-BRANCH": 4}

_HUNK_RE = re.compile(r"^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,(\d+))? @@ ?(.*)$")


class Unavailable(Exception):
    """Raised anywhere a deterministic answer cannot be produced. Always caught."""


def _git(args, cwd=None):
    try:
        p = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise Unavailable("git could not be invoked (%s)" % exc)
    if p.returncode != 0:
        tail = (p.stderr or "").strip().splitlines()
        raise Unavailable("git %s failed: %s" % (args[0], tail[-1] if tail else "exit %d" % p.returncode))
    return p.stdout


def _sanitize(s: str) -> str:
    """Strip CR/LF and collapse runs of whitespace. This script's stdout IS prompt
    context, so a filename or a funcname carrying a newline could otherwise inject a
    line at column 0 -- the same class the evidence block already guards for paths."""
    return re.sub(r"\s+", " ", s.replace("\r", " ").replace("\n", " ")).strip()


def hunks(rev_range, path, cwd=None):
    """New-side (start, count, funcname, is_whole_file) for every hunk of `path`.

    -U0 so a hunk's range is the changed lines themselves and nothing else -- context
    lines would inflate every range and make the POST-PLAN overlap test report true for
    neighbours of a post-plan change. Measured intent, not style.

    `is_whole_file` (old-side start 0, i.e. a file that did not exist at the base) is
    carried because it changes what the row MEANS. Measured on #158, which is why this
    field exists at all: `prototype-gate.py` is new on that branch, so its cumulative
    diff is ONE hunk of +987 lines and the first version of this script rendered the
    entire 987-line file as a single `pre-plan` row -- a checklist of one entry for the
    PR's centrepiece, tiered wrong because the row spans the plan's whole history. Found
    by running the instrument against the known positive before trusting it.
    """
    args = ["diff", "--no-color", "--unified=0"]
    if rev_range:
        args.append(rev_range)
    args += ["--", path]
    out = _git(args, cwd=cwd)
    found = []
    for line in out.splitlines():
        m = _HUNK_RE.match(line)
        if not m:
            continue
        start = int(m.group(2))
        count = 1 if m.group(3) is None else int(m.group(3))
        found.append((start, count, _sanitize(m.group(4))[:FUNCNAME_MAX],
                      m.group(1) == "0"))
    return found


def _untracked(path, cwd=None):
    """Is `path` present on disk but not known to git? `ls-files --error-unmatch` exits
    non-zero for exactly that case -- the tool's own exit code rather than a grep of its
    output (general.md item 4's corollary)."""
    try:
        p = subprocess.run(["git", "ls-files", "--error-unmatch", "--", path],
                           cwd=cwd, capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise Unavailable("git ls-files could not be invoked (%s)" % exc)
    return p.returncode != 0


def _line_count(path, cwd=None):
    base = pathlib.Path(cwd) if cwd else pathlib.Path(".")
    try:
        with (base / path).open("rb") as fh:
            return sum(1 for _ in fh)
    except OSError:
        return 0


def _overlaps(a, b):
    """Do new-side ranges (start, count) touch? A pure DELETION has count 0 and its
    start is the line it sits after, so it is a zero-length point -- `end < start`
    under a naive half-open test, which would make every deletion un-overlappable and
    silently untierable. Both ranges are widened to at least one line here, which is
    the only reading under which a deletion can be POST-PLAN at all."""
    (sa, ca), (sb, cb) = a, b
    ea = sa + max(ca, 1)
    eb = sb + max(cb, 1)
    return sa < eb and sb < ea


def build(files, base, plan, cwd=None, max_rows=DEFAULT_MAX_ROWS):
    """Returns (lines, meta). Raises Unavailable on any non-deterministic outcome.

    ROWS COME FROM TWO DIFFS, NOT FROM TIERING ONE. The first draft tiered the
    cumulative `base..HEAD` hunks by overlap and that is provably not enough: on #158
    (the known-positive case, replayed before this was believed) `prototype-gate.py` is
    a NEW file, so its cumulative diff is a single +987 hunk. One row, tiered `pre-plan`,
    for the PR whose five missed behaviours all live in that file. Emitting the
    `<plan-last>..HEAD` hunks as rows of their own is what gives the post-plan region
    real granularity (54 precise hunks on that branch, versus one); the cumulative rows
    stay so the checklist still covers everything the plan MIGHT have described.
    Duplicates -- the common case, a hunk that exists in both diffs identically -- are
    collapsed to one row carrying the stronger tier.
    """
    if base:
        # Assert the base is resolvable BEFORE any per-file diff, so an unreachable base
        # is one clear INVENTORY-UNAVAILABLE rather than N empty file diffs that would
        # render as a confident inventory of zero hunks -- a clean-looking checklist over
        # a change nobody enumerated is this whole script's failure mode.
        _git(["rev-parse", "--verify", "--quiet", base + "^{commit}"], cwd=cwd)

    plan_last = ""
    if plan:
        rng = "%s..HEAD" % base if base else "HEAD"
        plan_last = _git(["log", "-1", "--format=%H", rng, "--", plan], cwd=cwd).strip()
    plan_predates = not plan_last

    rows, truncated = [], False
    for path in files:
        if len(rows) >= max_rows:
            truncated = True
            break
        # An UNTRACKED file is invisible to every `git diff`, so the first version reported
        # "0 hunks" over a brand-new source file -- a clean-looking checklist covering a
        # change nobody enumerated, i.e. precisely the failure this engine exists to close,
        # reproduced inside it. Found by rendering the real evidence block against this very
        # PR's own new file, not by reasoning about it. The evidence block already surfaces
        # untracked files separately (`----- new file: -----`), so the inventory has to agree
        # with it or the two disagree about what is under review.
        if _untracked(path, cwd=cwd):
            n = _line_count(path, cwd=cwd)
            rows.append((path, 1, n, "", True, "UNCOMMITTED"))
            continue
        cum = hunks("%s..HEAD" % base if base else None, path, cwd=cwd)
        working = hunks("HEAD", path, cwd=cwd)
        post = [] if plan_predates else hunks("%s..HEAD" % plan_last, path, cwd=cwd)
        same = [] if plan_predates else hunks("%s^!" % plan_last, path, cwd=cwd)

        # (start, count) -> (funcname, whole, tier). Later writes win only when the tier
        # is stronger, so a POST-PLAN row is never demoted by an identical cumulative one.
        merged = {}

        def put(h, tier):
            key = (h[0], h[1])
            prev = merged.get(key)
            if prev is None or _RANK[tier] > _RANK[prev[2]]:
                merged[key] = (h[2] or (prev[0] if prev else ""), h[3], tier)

        for h in post:
            put(h, "POST-PLAN")
        for h in working:
            put(h, "UNCOMMITTED")
        for h in cum:
            if plan_predates:
                tier = "PLAN-PREDATES-BRANCH"
            elif any(_overlaps((h[0], h[1]), (r[0], r[1])) for r in post):
                tier = "POST-PLAN"
            elif any(_overlaps((h[0], h[1]), (r[0], r[1])) for r in same):
                tier = "SAME-COMMIT"
            else:
                tier = "pre-plan"
            put(h, tier)

        for (start, count) in sorted(merged):
            fn, whole, tier = merged[(start, count)]
            rows.append((path, start, count, fn, whole, tier))

    if len(rows) > max_rows:
        rows, truncated = rows[:max_rows], True

    tiers = {}
    for r in rows:
        tiers[r[5]] = tiers.get(r[5], 0) + 1

    lines = ["[audit-coverage] change inventory (deterministic) — %d hunk%s across %d file%s. "
             "EVERY row must be accounted for in Stage 1."
             % (len(rows), "" if len(rows) == 1 else "s",
                len(files), "" if len(files) == 1 else "s")]
    width = len(str(len(rows))) if rows else 1
    for i, (path, start, count, fn, whole, tier) in enumerate(rows, 1):
        lines.append("  H%-*d %s:%d (+%d)%s%s  %s"
                     % (width, i, _sanitize(path), start, count,
                        ("  NEW-FILE (this row is the whole file, not one hunk)"
                         if whole else ""),
                        ("  in " + fn) if fn else "", tier))
    if not rows:
        # A file list with no hunks is a real, reportable state -- and it must not read
        # like a successful inventory of a real change.
        lines.append("  (no hunks — the file list resolved to zero changed lines)")

    # A NEW-FILE row spans the whole file, so it overlaps the post-plan region whenever
    # ANY part of the file is post-plan -- which made the first headline read "12 of 12
    # hunks are POST-PLAN" on #158 when 11 were, and the 12th was the file itself. Counting
    # a row that contains all the others alongside them is double-counting, and the number
    # in that sentence is the one a reader acts on. Whole-file rows keep their tier (it is
    # true) and are excluded from the tally (it is not a hunk).
    precise = [r for r in rows if not r[4]]
    flagged = sum(1 for r in precise if r[5] in ("POST-PLAN", "UNCOMMITTED", "PLAN-PREDATES-BRANCH"))
    whole = len(rows) - len(precise)
    if flagged or (whole and any(r[5] != "pre-plan" for r in rows)):
        if plan_predates:
            lines.append("[audit-coverage] PLAN-PREDATES-BRANCH — the plan doc (%s) was never "
                         "touched on this branch, so NO declared criterion was written against "
                         "ANY hunk above. Treat the whole diff as undeclared until a criterion "
                         "is named for it." % _sanitize(plan or "(none)"))
        else:
            wholeclause = (" plus %d whole-file row%s spanning it"
                           % (whole, "" if whole == 1 else "s")) if whole else ""
            if precise:
                subject = ("%d of %d hunks%s carry lines that landed AFTER the plan was last "
                           "edited (%s)" % (flagged, len(precise),
                                            ("," + wholeclause) if wholeclause else "",
                                            plan_last[:12]))
            else:
                # All rows are whole-file (typically a brand-new, still-untracked source file).
                # "0 of 0 hunks" was the first rendering here and it read like a clean result
                # sitting directly above a NEW-FILE row -- the two halves of the same block
                # contradicting each other. A summary that disagrees with its own rows is worse
                # than no summary.
                subject = ("every row above is a whole NEW file, added after the plan was last "
                           "edited (%s)" % plan_last[:12])
            lines.append("[audit-coverage] POST-PLAN — %s. No declared criterion CAN have been "
                         "written for them; measured across four live runs, these are the hunks "
                         "missed most often. Enumerate them first." % subject)
    if truncated:
        lines.append("[audit-coverage] INVENTORY-TRUNCATED — more than %d hunks; rows past the "
                     "cap are NOT listed, so Stage 1's checklist is PARTIAL and a clean result "
                     "here is partial too. Say so, and recommend splitting the PR." % max_rows)
    return lines, {"rows": len(rows), "tiers": tiers, "plan_last": plan_last,
                   "plan_predates": plan_predates, "truncated": truncated}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base", default="", help="base ref (e.g. origin/main); empty = working tree only")
    ap.add_argument("--plan", default="", help="path to the plan doc, for the plan-relation tiers")
    ap.add_argument("--cwd", default=None, help="run git here (tests)")
    ap.add_argument("--max-rows", type=int, default=DEFAULT_MAX_ROWS)
    ap.add_argument("--files-from", default="-", help="file holding the file list; - = stdin")
    args = ap.parse_args(argv)

    try:
        raw = sys.stdin.read() if args.files_from == "-" else open(args.files_from, encoding="utf-8").read()
    except OSError as exc:
        print("[audit-coverage] INVENTORY-UNAVAILABLE — could not read the file list (%s). "
              "Stage 1 has no hunk checklist, so a clean result below is WEAKER than a normal "
              "one, not equal to it. This is NOT a skip." % exc)
        return 0

    files = [f.strip() for f in raw.splitlines() if f.strip()]
    if not files:
        print("[audit-coverage] INVENTORY-UNAVAILABLE — the file list was empty, but this script "
              "is only called when the evidence block found behavior-bearing files, so an empty "
              "list means the two disagree. Stage 1 has no hunk checklist, so a clean result "
              "below is WEAKER than a normal one, not equal to it. This is NOT a skip.")
        return 0

    try:
        lines, _meta = build(files, args.base, args.plan, cwd=args.cwd, max_rows=args.max_rows)
    except Unavailable as exc:
        print("[audit-coverage] INVENTORY-UNAVAILABLE — %s. Stage 1 has no hunk checklist, so a "
              "clean result below is WEAKER than a normal one, not equal to it. This is NOT a "
              "skip." % exc)
        return 0
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
