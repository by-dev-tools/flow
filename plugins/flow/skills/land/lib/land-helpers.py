#!/usr/bin/env python3
"""Deterministic mechanical helpers for /flow:land (post-merge doc-currency, FB-0061).

`/flow:land`'s narrative reconciliation (flipping a roadmap/plan item from "at PR
(#N)" to "merged (#N)", moving it between slots) is agent judgment — the same
prose-driven shape as `/flow:ship` Step 5a, which has no helper because the text
is free-form. This module owns ONLY the two operations that ARE unambiguous and
therefore worth pinning deterministically + idempotently:

  changelog-check  — does the CHANGELOG carry a `## v<version>` entry? (the FLOW-1
                     gap that let v1.10.0 merge with no changelog line). exit 0 if
                     present, 1 if missing (caller WARNs), 2 on a missing/empty
                     source. Accepts a single file OR a fragmented directory
                     (one file per release) — see `_read`.

  (clear-reservation was REMOVED in v1.38.0 alongside `reserved-feedback-numbers.md`.
   With one file per feedback entry, an FB-number collision IS a filename collision,
   which git reports as a both-added conflict — a mechanical, unmissable check that
   replaces a protocol depending on author memory. Leaving the subcommand behind
   would have made it a permanent silent no-op: the caller guarded it with
   `[ -f "$RESV" ]` on a file that no longer exists, so it would have looked healthy
   forever while doing nothing. That is the exact class this release removes.)

Stdlib only. Run: python3 land-helpers.py <subcommand> ...
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


def _read(path: str) -> str | None:
    """Read a changelog source that is EITHER a single file or a fragmented
    directory (one file per release).

    FB-0100: `changelogPath` may now point at a directory. The caller used to guard
    this whole check with `[ -f "$CHANGELOG" ]`, which is FALSE on a directory — so
    a directory-valued slot made the currency check a silent no-op: it never ran and
    never said so. That is the same class as FB-0082, and it is worse here than at
    the reviewer preludes, because the reviewers at least printed something.
    """
    p = Path(path)
    if p.is_file():
        return p.read_text()
    if p.is_dir():
        # Concatenate the release fragments. Order is irrelevant — the caller only
        # asks whether a `## vX.Y.Z` heading exists anywhere in the corpus.
        parts = [
            f.read_text()
            for f in sorted(p.glob("*.md"))
            if f.is_file() and f.name != "README.md" and not f.name.startswith("_")
        ]
        # An EMPTY directory is not the same as a corpus with no matching version.
        # Returning "" here would make the check report "no v1.38.0 entry" when the
        # truth is "there are no entries at all" — a misdiagnosis that sends the
        # reader to write an entry rather than to fix a broken migration.
        return "\n".join(parts) if parts else None
    return None


def changelog_check(args) -> int:
    """exit 0: `## v<version>` present. 1: absent (WARN). 2: file missing/unreadable."""
    text = _read(args.changelog)
    if text is None:
        p = Path(args.changelog)
        detail = (
            f"directory {args.changelog} holds no release fragments (a fragmentation "
            f"migration probably failed halfway)"
            if p.is_dir()
            else f"file not found at {args.changelog}"
        )
        sys.stderr.write(f"[land] changelog-check: {detail} — cannot verify currency.\n")
        return 2
    ver = args.version.lstrip("vV")
    # Match a heading line `## vX.Y.Z` (allow a trailing " — date"/" (...)" etc.).
    # The `(?![\d.])` lookahead anchors the version so a check for v1.10 is NOT
    # satisfied by `## v1.10.1` (a `\b` would wrongly match the 0→. transition).
    pat = re.compile(r"^##\s+v" + re.escape(ver) + r"(?![\d.])", re.MULTILINE)
    if pat.search(text):
        print(f"[land] changelog-check: PASS — '## v{ver}' present in {args.changelog}.")
        return 0
    sys.stderr.write(
        f"[land] changelog-check: WARN — no '## v{ver}' entry in {args.changelog}. "
        f"The merged version shipped without a changelog line (a post-merge currency "
        f"gap); add the entry in this reconciliation PR.\n"
    )
    return 1


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="land-helpers.py")
    sub = parser.add_subparsers(dest="cmd", required=True)

    cc = sub.add_parser("changelog-check")
    cc.add_argument("changelog")
    cc.add_argument("--version", required=True)
    cc.set_defaults(func=changelog_check)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
