#!/usr/bin/env python3
"""Deterministic mechanical helpers for /flow:land (post-merge doc-currency, FB-0058).

`/flow:land`'s narrative reconciliation (flipping a roadmap/plan item from "at PR
(#N)" to "merged (#N)", moving it between slots) is agent judgment — the same
prose-driven shape as `/flow:ship` Step 5a, which has no helper because the text
is free-form. This module owns ONLY the two operations that ARE unambiguous and
therefore worth pinning deterministically + idempotently:

  changelog-check  — does the CHANGELOG carry a `## v<version>` entry? (the FLOW-1
                     gap that let v1.10.0 merge with no changelog line). exit 0 if
                     present, 1 if missing (caller WARNs), 2 on a missing file.

  clear-reservation — strike a shipped `FB-XXXX` (or `VH-XXXX`) reservation line
                     from reserved-feedback-numbers.md. Idempotent: removing an
                     absent id is a clean no-op (exit 0), never an error — so a
                     re-run of /flow:land can't fail on an already-cleared number.

Stdlib only. Run: python3 land-helpers.py <subcommand> ...
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


def _read(path: str) -> str | None:
    p = Path(path)
    if not p.is_file():
        return None
    return p.read_text()


def changelog_check(args) -> int:
    """exit 0: `## v<version>` present. 1: absent (WARN). 2: file missing/unreadable."""
    text = _read(args.changelog)
    if text is None:
        sys.stderr.write(
            f"[land] changelog-check: file not found at {args.changelog} — "
            f"cannot verify currency.\n"
        )
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


def clear_reservation(args) -> int:
    """Remove reservation lines naming <id> from the reserved-numbers file.

    A reservation line is any line mentioning the id token (e.g. `FB-0058` or
    `VH-0008`), matched on a word boundary so `FB-005` never strikes `FB-0058`.
    Idempotent: zero matches → clean no-op, exit 0.
    """
    text = _read(args.file)
    if text is None:
        sys.stderr.write(
            f"[land] clear-reservation: file not found at {args.file} — "
            f"nothing to clear (no reservations file).\n"
        )
        # Absent reservations file is not an error for land — many repos never
        # pre-reserve. Clean no-op.
        return 0
    token = args.id
    if not re.fullmatch(r"(FB|VH)-\d{1,6}", token):
        sys.stderr.write(
            f"[land] clear-reservation: '{token}' is not a FB-/VH- id; refusing to "
            f"strike lines on an unconstrained match.\n"
        )
        return 2
    tok_re = re.compile(r"\b" + re.escape(token) + r"\b")
    kept, removed = [], []
    for line in text.splitlines(keepends=True):
        (removed if tok_re.search(line) else kept).append(line)
    if not removed:
        print(f"[land] clear-reservation: no reservation line for {token} (already clear).")
        return 0
    Path(args.file).write_text("".join(kept))
    for line in removed:
        print(f"[land] clear-reservation: removed — {line.rstrip()}")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="land-helpers.py")
    sub = parser.add_subparsers(dest="cmd", required=True)

    cc = sub.add_parser("changelog-check")
    cc.add_argument("changelog")
    cc.add_argument("--version", required=True)
    cc.set_defaults(func=changelog_check)

    cr = sub.add_parser("clear-reservation")
    cr.add_argument("file")
    cr.add_argument("--id", required=True)
    cr.set_defaults(func=clear_reservation)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
