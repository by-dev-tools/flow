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

It also answers the sequencing question behind the measured misses in #158 -- 3 of its 5 --
namely that behaviour added during `/simplify` and `/flow:staff-review`
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

KNOWN LIMITATION, MEASURED RATHER THAN DISCOVERED LATER. `plan_last` is the last commit
touching the plan FILE, not the last commit touching the ACTIVE Spec-walk BLOCK. Those
diverge systematically on flow's own ships, because /flow:ship Step 5 rewrites planPath in
the same commit that carries the code -- so on THIS repo's normal commit shape every
committed hunk lands SAME-COMMIT ("genuinely ambiguous") rather than POST-PLAN, and the sharp
signal is lost exactly where the measured miss class lives. It is honest, not wrong: the tier
reports that it cannot tell. Two independent /simplify lenses found this on the same run.

The deeper fix is real and is NOT taken here: have `walk_extract` export the active block's
line range (it already computes the indices) and tier off `git log -1 -L<start>,<end>:<plan>`,
which answers "when were the declared criteria last edited" instead of approximating it with
the whole file. Declined for this PR because (a) it is a shared-parser contract edit for a
local reason, and (b) the inventory's measured recall effect in diff mode is already ZERO --
deepening it would be shipping an unmeasured improvement to a component whose headline number
did not move, which is exactly what this PR's own rule forbids. Roadmapped, and the eval
below pins the SAME-COMMIT outcome as KNOWN AND INTENDED rather than leaving it to be read as
a passing tier.

FAIL LOUD, NEVER CLEAN. Every failure path prints `WEAKENED - INVENTORY-UNAVAILABLE -- <reason>`
and exits 0. The `WEAKENED -` token is the matchable half of the contract: the skill prose has
ONE rule for weakenings rather than a bullet per outcome, and without a token that rule would
also capture this engine's ordinary success lines (the inventory header, the tier legend, the
POST-PLAN summary) -- which would require the "this audit is weaker" note on every healthy run
and make the marker unable to tell healthy from degraded. New weakening outcomes get covered by
construction; informational lines never match. It must never print nothing, and must never print the evidence block's
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
# The tiers that mean "no declared criterion CAN cover this". ONE definition: the summary
# guard previously re-derived it as `!= "pre-plan"`, which also matches SAME-COMMIT -- so a
# diff with one SAME-COMMIT row and one pre-plan whole-file row printed a POST-PLAN headline
# over zero post-plan hunks. That is the same self-contradicting-summary defect the
# whole-file branch below was written to fix, reintroduced in the sibling condition.
FLAGGED_TIERS = frozenset(("POST-PLAN", "UNCOMMITTED", "PLAN-PREDATES-BRANCH"))

_HUNK_RE = re.compile(r"^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,(\d+))? @@ ?(.*)$")


class Unavailable(Exception):
    """Raised anywhere a deterministic answer cannot be produced. Always caught."""


def _unavailable(reason):
    """The one wording for "no checklist was built". It was stated three times in this file --
    the FB-0010 fan-out class applied to the file's own most load-bearing sentence, where a
    wording fix to one site would leave two stale and nothing would detect it. Callers supply
    only their distinct clause. (A fourth copy lives in the SKILL.md shell fallback and
    genuinely cannot share this -- different process, no import.)"""
    return ("[audit-coverage] WEAKENED · INVENTORY-UNAVAILABLE — %s Stage 1 has no hunk checklist, so a "
            "clean result below is WEAKER than a normal one, not equal to it. This is NOT a "
            "skip." % reason)


def _git(args, cwd=None):
    try:
        # errors="replace", not text=True: strict UTF-8 decoding raises UnicodeDecodeError
        # OUTSIDE Unavailable, so a latin-1 funcname or path crashed the engine with a
        # traceback on stderr and NO [audit-coverage] line at all — verified, and the exact
        # opposite of this module's stated "never print nothing" contract. A mangled glyph in
        # a funcname costs nothing; a crash costs the whole checklist.
        p = subprocess.run(["git", *args], cwd=cwd, capture_output=True, timeout=60,
                           encoding="utf-8", errors="replace")
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
        fn = _sanitize(m.group(4))
        # Slice with a visible marker: 10 of 54 rows on a real run cut mid-word at exactly
        # FUNCNAME_MAX, and a reader cannot tell that from a genuinely odd identifier.
        if len(fn) > FUNCNAME_MAX:
            fn = fn[:FUNCNAME_MAX - 1] + "…"
        found.append((start, count, fn, m.group(1) == "0"))
    return found


def _line_count(path, cwd=None):
    """Lines in an untracked file. Raises Unavailable rather than returning 0 on an
    unreadable path: a `+0` row reads like a real measurement of an empty file, and it
    would be the only silent zero in an engine where every other failure path is loud."""
    base = pathlib.Path(cwd) if cwd else pathlib.Path(".")
    try:
        with (base / path).open("rb") as fh:
            return sum(1 for _ in fh)
    except OSError as exc:
        raise Unavailable("could not read the untracked file %s (%s)" % (path, exc))


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
    """Returns the output lines. Raises Unavailable on any non-deterministic outcome.

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

    # THREE WHOLE-SET PROBES, HOISTED OUT OF THE PER-FILE LOOP. Measured (64-file diff):
    # 322 spawns / 1.29s -> 197 / 0.75s, a 41% cut for three calls costing ~10ms together.
    # Deliberately NOT the full batching rewrite, which was measured at a further 33x and
    # declined: it needs a `diff --git` header parser (rename pairs, core.quotepath octal
    # escapes) inside the one script whose whole value is deterministic correctness, to buy
    # ~1.2s on a 64-file PR against an LLM audit that takes tens of seconds. The per-file
    # loop and its file->hunk attribution are untouched here; only the yes/no probes move.
    head_sha = _git(["rev-parse", "HEAD"], cwd=cwd).strip()
    # `plan_last == HEAD` is the NORMAL ship-time shape, not an edge case: /flow:ship commits
    # the doc updates last, so `<plan_last>..HEAD` is an empty range and the post-plan diff
    # was running once per file to learn nothing (64 empty spawns, 0.19s, on this very branch).
    post_range_empty = plan_predates or plan_last == head_sha
    untracked_set = set(
        _git(["ls-files", "--others", "--exclude-standard"], cwd=cwd).splitlines())
    dirty_set = set(_git(["diff", "HEAD", "--name-only"], cwd=cwd).splitlines())

    rows, unexamined = [], 0
    for i, path in enumerate(files):
        # Cost guard only. Setting `truncated` here warned "rows past the cap are NOT listed"
        # even when the remaining files would have contributed zero hunks -- a false "your
        # checklist is PARTIAL" that pushes a reviewer to split a PR that is not over the cap.
        # Truncation is now decided in exactly one place, from the slice below.
        if len(rows) >= max_rows:
            unexamined = len(files) - i
            break
        # An UNTRACKED file is invisible to every `git diff`, so the first version reported
        # "0 hunks" over a brand-new source file -- a clean-looking checklist covering a
        # change nobody enumerated, i.e. precisely the failure this engine exists to close,
        # reproduced inside it. Found by rendering the real evidence block against this very
        # PR's own new file, not by reasoning about it. The evidence block already surfaces
        # untracked files separately (`----- new file: -----`), so the inventory has to agree
        # with it or the two disagree about what is under review.
        if path in untracked_set:
            n = _line_count(path, cwd=cwd)
            rows.append((path, 1, n, "", True, "UNCOMMITTED"))
            continue
        cum = hunks("%s..HEAD" % base if base else None, path, cwd=cwd)
        working = hunks("HEAD", path, cwd=cwd) if path in dirty_set else []
        post = [] if post_range_empty else hunks("%s..HEAD" % plan_last, path, cwd=cwd)
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

    truncated = len(rows) > max_rows
    if truncated:
        rows = rows[:max_rows]

    # Header states BOTH denominators, because the summary below counts only precise hunks and
    # the reader could not otherwise derive its number (36 rows / "30 of 33" with 33 appearing
    # nowhere). And a one-line legend: three of the five tiers were explained only in this
    # docstring, including SAME-COMMIT -- the tier this repo sees MOST, whose meaning
    # ("genuinely ambiguous, I cannot tell") is not guessable from the name.
    # A NEW-FILE row spans the whole file, so it overlaps the post-plan region whenever ANY
    # part of the file is post-plan -- which made the first headline read "12 of 12 hunks are
    # POST-PLAN" on #158 when 11 were, and the 12th was the file itself. Counting a row that
    # contains all the others alongside them is double-counting, and the number in that
    # sentence is the one a reader acts on. Whole-file rows keep their tier (it is true) and
    # are excluded from the tally (they are not hunks).
    precise = [r for r in rows if not r[4]]
    flagged = sum(1 for r in precise if r[5] in FLAGGED_TIERS)
    whole_rows = len(rows) - len(precise)

    # PARTIAL IS SAID IN THE HEADER, not only 250 rows later. The count here was
    # post-truncation, so a clipped inventory opened with a complete-sounding total and its
    # own correction sat below every row it qualified -- the third instance in this block of
    # "a summary that disagrees with its own rows", at the one place the reader's eye lands
    # first. A qualifier must precede the data it qualifies.
    partial = " PARTIAL — the cap was reached; see INVENTORY-TRUNCATED below." if (
        truncated or unexamined) else ""
    lines = ["[audit-coverage] change inventory (deterministic) — %d row%s (%d hunk%s + %d "
             "whole-file) across %d file%s.%s EVERY row must be accounted for in Stage 1."
             % (len(rows), "" if len(rows) == 1 else "s",
                len(precise), "" if len(precise) == 1 else "s", whole_rows,
                len(files), "" if len(files) == 1 else "s", partial),
             "[audit-coverage] tiers — POST-PLAN / UNCOMMITTED / PLAN-PREDATES-BRANCH: no "
             "declared criterion CAN cover it · SAME-COMMIT: the plan moved in the same commit, "
             "so this is genuinely ambiguous · pre-plan: routine, a criterion could exist. "
             "NEW-FILE: the row is the whole file, not one hunk."]
    width = len(str(len(rows))) if rows else 1
    for i, (path, start, count, fn, whole, tier) in enumerate(rows, 1):
        # `(+0)` promised added lines and delivered none, reading as "the tool found nothing
        # here" -- the same hazard this file already guards for untracked files and then
        # shipped for deletions. A pure deletion says so.
        extent = "(+%d)" % count if count else ("DELETED" if start == 0 else "(deletion)")
        # NEW-FILE is a marker, not a sentence: the 48-char explanation was repeated per row
        # (8x in one real block) and was the largest contributor to the ragged column. The
        # semantics are stated once, in the legend — the same legend-vs-row split
        # manifest-triage.py uses for its recurring explanations.
        # A whole-file delete has new-side start AND count 0, so `path:0` would point at a
        # line that does not exist; render the path alone.
        coord = "%s:%d" % (_sanitize(path), start) if start else _sanitize(path)
        lines.append("  H%-*d %-20s  %s %s%s%s"
                     % (width, i, tier, coord, extent,
                        "  NEW-FILE" if whole else "",
                        ("  in " + fn) if fn else ""))
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
    flagged = sum(1 for r in precise if r[5] in FLAGGED_TIERS)
    whole_rows = len(rows) - len(precise)
    if any(r[5] in FLAGGED_TIERS for r in rows):
        if plan_predates:
            lines.append("[audit-coverage] PLAN-PREDATES-BRANCH — the plan doc (%s) was never "
                         "touched on this branch, so NO declared criterion was written against "
                         "ANY hunk above. Treat the whole diff as undeclared until a criterion "
                         "is named for it." % _sanitize(plan or "(none)"))
        else:
            wholeclause = (" (plus %d whole-file row%s spanning the same region)"
                           % (whole_rows, "" if whole_rows == 1 else "s")) if whole_rows else ""
            if precise and flagged:
                subject = ("%d of %d hunks%s carry lines that landed AFTER the plan was last "
                           "edited (plan last edited at %s)"
                           % (flagged, len(precise), wholeclause, plan_last[:8]))
            else:
                # No flagged PRECISE hunks -- either every row is a whole file, or the only
                # flagged rows are whole-file ones. Either way "0 of N hunks carry lines that
                # landed AFTER the plan" is the self-contradicting-summary shape the rest of
                # this function exists to avoid.
                # "0 of 0 hunks" was the first rendering here and it read like a clean result
                # sitting directly above a NEW-FILE row -- the two halves of the same block
                # contradicting each other. A summary that disagrees with its own rows is worse
                # than no summary.
                subject = ("%d whole-file row%s above %s a whole NEW file added after the plan "
                           "was last edited (plan last edited at %s)"
                           % (whole_rows, "" if whole_rows == 1 else "s",
                              "is" if whole_rows == 1 else "are each", plan_last[:8]))
            # No "measured across N live runs" here: that is flow's own measurement history,
            # and it printed into every consumer's PR in every project — a reader has no idea
            # whose runs, of what. "Enumerate them first" carries the whole operational payload.
            lines.append("[audit-coverage] POST-PLAN — %s. No declared criterion CAN have been "
                         "written for them, so they are the least likely to be covered. "
                         "Enumerate them first." % subject)
    if truncated or unexamined:
        extra = (" %d file%s past the cap were not examined at all."
                 % (unexamined, "" if unexamined == 1 else "s")) if unexamined else ""
        lines.append("[audit-coverage] WEAKENED · INVENTORY-TRUNCATED — the %d-hunk cap was reached, so "
                     "Stage 1's checklist is PARTIAL and a clean result here is partial too.%s "
                     "Say so, and recommend splitting the PR." % (max_rows, extra))
    return lines


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base", default="", help="base ref (e.g. origin/main); empty = working tree only")
    ap.add_argument("--plan", default="", help="path to the plan doc, for the plan-relation tiers")
    ap.add_argument("--cwd", default=None, help="run git here (tests)")
    ap.add_argument("--max-rows", type=int, default=DEFAULT_MAX_ROWS)
    ap.add_argument("--files-from", default="-", help="file holding the file list; - = stdin")
    args = ap.parse_args(argv)

    try:
        if args.files_from == "-":
            # Decode the file list permissively for the same reason as the git reads above.
            raw = sys.stdin.buffer.read().decode("utf-8", "replace")
        else:
            raw = open(args.files_from, encoding="utf-8", errors="replace").read()
    except OSError as exc:
        print(_unavailable("could not read the file list (%s)." % exc))
        return 0

    files = [f.strip() for f in raw.splitlines() if f.strip()]
    if not files:
        print(_unavailable("the file list was empty, but this script is only called when the "
                           "evidence block found behavior-bearing files, so an empty list means "
                           "the two disagree."))
        return 0

    try:
        lines = build(files, args.base, args.plan, cwd=args.cwd, max_rows=args.max_rows)
    except Unavailable as exc:
        print(_unavailable("%s." % exc))
        return 0
    except Exception as exc:                      # noqa: BLE001 — deliberate catch-all
        # The docstring promises "every failure path prints INVENTORY-UNAVAILABLE and exits 0".
        # A promise kept only for the exceptions someone remembered is not the contract; an
        # unexpected exception here would put a traceback where the checklist goes, above the
        # delimiter, matching no control-line rule — Stage 1 would then have no checklist AND
        # no weakening line, which is precisely the failure this engine exists to close.
        print(_unavailable("unexpected %s: %s." % (type(exc).__name__, exc)))
        return 0
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
