#!/usr/bin/env python3
"""Shared predicate: find "N slots" literals that contradict the schema's actual
slot count (FB-0010 fan-out class; FB-0079's wrap-tolerant hardening; roadmap
"`/flow:doctor` Check 2.5 is the line-oriented twin of a guard we just made
wrap-tolerant").

Before this module existed, flow ran the SAME predicate in two places that could
silently drift: `run_merge_status_evals.py`'s internal sweep over `plugins/` +
`template/` (regex, wrap-tolerant, scanning `.md`/`.json`/`.sh`/`.template`), and
`/flow:doctor` Check 2.5's consumer-facing sweep over a project's own docs
(`grep -rEn`, line-oriented, `.md`-ish paths only). FB-0079 hardened the first
after `all 30\n  slots` — wrapped across a newline inside YAML frontmatter — slipped
a line-oriented grep; Check 2.5 still had every property that produced that miss.
Hoisting the regex here and having both callers invoke it collapses the two
implementations to one, so a fixture proving the wrap-tolerant case is verified
against the SAME code both runtimes run, not a private copy of it.

Scanning is deliberately restricted to text-ish extensions where "N slots" prose
plausibly appears (`.md`, `.json`, `.sh`, `.template`) — the same restriction the
internal sweep already made, to keep noise (binaries, lockfiles, generated
artifacts) out of the survivor list.

Deliberately scoped to the "slots" noun only, not parameterized to any "N <noun>"
shape (skill count, lens count, rule count are the same fan-out class per FB-0010,
named but not built in `dev-docs/plan.md` § "Generalize Check 2.5 beyond slot
count"). Widening this module's API to a configurable noun is that roadmap item's
job, not this hoist's — this PR fixes the wrap-tolerance/line-orientation/scan-target
gap the roadmap named, not a second, larger scope change.

Exit codes: 0 clean (scanned > 0, no stale survivors), 1 stale survivor(s) found,
2 a vacuous scan (scanned == 0 — nothing was measured, so a PASS verdict here would
be false; the FB-0010 silent-skip class applied to this check itself), 3 a usage
error (bad flags, missing --expected — kept distinct from 2 so a caller can't
misread "the arguments were wrong" as "the scan found nothing to check").
Stdlib only. Python 3.7+.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Wrap-tolerant by construction: matched over each file's FULL text (not per-line),
# so whitespace between the number and "slots" — including a newline — still matches.
# Second group captures "slot"/"slots" so survivor messages can render the human words
# instead of Python's repr() (which would print a literal "\n" for a wrapped match).
SLOT_RE = re.compile(r"(\d+)\s+(slots?)\b")

# Extensions worth scanning for "N slots" prose. Kept narrow deliberately (see
# module docstring) rather than scanning every file a directory walk turns up.
SCAN_SUFFIXES = (".md", ".json", ".sh", ".template")

PREFIX = "[slot-count-scan]"


def _iter_candidate_files(paths):
    """Yield every file under `paths` (files passed through, directories walked)
    whose suffix is in SCAN_SUFFIXES. Nonexistent paths are silently skipped —
    callers are expected to pass only paths they already confirmed exist."""
    for raw in paths:
        p = Path(raw)
        if p.is_file():
            candidates = [p]
        elif p.is_dir():
            candidates = sorted(f for f in p.rglob("*") if f.is_file())
        else:
            continue
        for f in candidates:
            if f.suffix in SCAN_SUFFIXES:
                yield f


def scan_paths(paths, expected, exclude_substrings=(), root=None):
    """Return (stale, scanned) — `stale` is a list of "path:line: "N slots"" strings
    whose N disagrees with `expected`; `scanned` is how many files were read.

    `root`, if given, renders each survivor's path relative to it (`Path.relative_to`)
    instead of however it was passed in — callers that want repo-relative display no
    longer have to reconstruct that themselves by string-splitting the result.

    Survivor lines carry a line number and the human words ("N slots"), not Python's
    repr() — a wrapped match's repr prints a literal two-character "\\n" escape, which
    reads as a tool bug to a CLI user rather than "these two words are on separate
    lines in your file" (caught by `/flow:staff-review`'s UX-designer lens).

    A shell-comment line (`.sh` files only) is exempt — a `# schema bumped from 13
    to 16 slots` narrating history is not a stale claim. A markdown heading also
    starts with `#`, so this exemption is scoped to `.sh` only; exempting it
    repo-wide would let `## Config (30 slots)` hide (see the internal sweep this
    was hoisted from).
    """
    stale = []
    scanned = 0
    expected_str = str(expected)
    for f in _iter_candidate_files(paths):
        if any(sub in str(f) for sub in exclude_substrings):
            continue
        try:
            text = f.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        scanned += 1
        for m in SLOT_RE.finditer(text):
            line_start = text.rfind("\n", 0, m.start()) + 1
            prefix = text[line_start:m.start()].lstrip()
            if f.suffix == ".sh" and prefix.startswith("#"):
                continue
            if m.group(1) != expected_str:
                line_no = text.count("\n", 0, m.start()) + 1
                words = f'"{m.group(1)} {m.group(2)}"'
                if "\n" in m.group(0):
                    words += " (wrapped across a line break)"
                display = f.relative_to(root) if root is not None else f
                stale.append(f"{display}:{line_no}: {words}")
    return stale, scanned


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="slot_count_scan.py")
    ap.add_argument("--expected", required=True, type=int,
                     help="the schema's actual slot count")
    ap.add_argument("--exclude", action="append", default=[],
                     help="substring to exclude from the scan (repeatable)")
    ap.add_argument("paths", nargs="+", help="files or directories to scan")
    # argparse's own SystemExit(2) on a bad-args error is remapped to 3 below, so a
    # caller can tell "you asked me something I couldn't parse" apart from "I parsed
    # your request and scanned nothing" — argparse itself only ever hands us "2".
    try:
        args = ap.parse_args(argv)
    except SystemExit as e:
        raise SystemExit(3 if e.code not in (0, None) else e.code) from None

    stale, scanned = scan_paths(args.paths, args.expected, exclude_substrings=args.exclude)

    # Machine-parseable trailer, not just prose: a caller shelling out to this CLI
    # (doctor's Check 2.5) needs the scanned-file count without coupling to word
    # position in a human sentence that could be reworded later (staff-review NIT).
    print(f"{PREFIX} SCANNED {scanned} file(s) across {len(args.paths)} path(s)")
    print(f"{PREFIX} SCANNED_COUNT={scanned}")
    for line in stale:
        print(f"{PREFIX} STALE {line}")

    if scanned == 0:
        return 2
    return 1 if stale else 0


if __name__ == "__main__":
    raise SystemExit(main())
