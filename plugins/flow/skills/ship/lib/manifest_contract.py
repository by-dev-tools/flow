#!/usr/bin/env python3
"""Shared constants for the NOT-READY manifest — the bytes the producer and the
detector must agree on, defined once.

`pr-coherence.py` is the *detector* (it decides whether a PR body carries the
manifest, and enforces the body↔draft invariant for ship, doctor, land,
ship-spike and staff-review). `manifest-triage.py` is the *emitter* (it renders
the block). Before this module they held independent copies of the same literal,
written in two different forms (`"\\U0001f6ab NOT READY TO MERGE"` vs the raw
emoji) — a rename or a stray edit would silently split emitter from detector, and
the only thing standing between that and a broken merge gate was a comment asking
future maintainers to remember. That is the FB-0010 fan-out class this repo's
rules say to fix at the contract change, not after it.

Underscore-named so it is importable as a bare sibling module — the same house
pattern as `verify-build/lib/walk_extract.py`, which `extract-criteria.py`,
`extract-visual-states.py`, `walk-pin-lint.py` and `skip-audit-checks.py` all
import. Hyphenated scripts in this directory cannot be imported, which is exactly
why the shared piece gets its own underscore module rather than living in one of
them.

Stdlib only. No side effects on import.
"""

from __future__ import annotations

import re

# The block a not-ready PR carries. `MANIFEST_HEADING` is the human-visible
# sentinel; the two fences delimit the machine-readable entry list.
#
# Written as the literal emoji (not an escape) so a grep for the string in this
# file matches what a grep of a PR body matches. Both forms are byte-identical;
# having two spellings across two files was itself part of the drift risk.
MANIFEST_HEADING = "🚫 NOT READY TO MERGE"
MANIFEST_OPEN = "<!-- flow:not-ready-manifest -->"
MANIFEST_CLOSE = "<!-- /flow:not-ready-manifest -->"

# Either token is sufficient to detect the manifest: a body that carries the
# fence but lost its heading (or vice versa) is still a not-ready body.
MANIFEST_TOKENS = (MANIFEST_OPEN, MANIFEST_HEADING)


def slug(branch: str) -> str:
    """Filesystem-safe form of a branch name, for per-branch scratch files.

    Matches the convention `rigor-marker.py` established
    (`/tmp/flow-<thing>-<branch-slug>.json`).
    """
    return re.sub(r"[^A-Za-z0-9_.-]", "-", branch or "detached")


def extract_manifest_region(text: str) -> str:
    """Return the text between the manifest fences, or the whole text if the
    fences are absent.

    Scoping to the fences is what keeps prose elsewhere in a PR body — a
    changelog bullet, a quoted example — from being read as a live entry.
    """
    if MANIFEST_OPEN in text and MANIFEST_CLOSE in text:
        return text.split(MANIFEST_OPEN, 1)[1].split(MANIFEST_CLOSE, 1)[0]
    return text
