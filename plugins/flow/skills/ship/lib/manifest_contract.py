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
    (`<repo-root>/.flow/<thing>-<branch-slug>.json` since FB-0082 — repo-local, not the
    older global `/tmp` form, which collided across projects on same-named branches).
    """
    return re.sub(r"[^A-Za-z0-9_.-]", "-", branch or "detached")


def _fence_bounds(lines: list[str]) -> tuple[int | None, int | None]:
    """Indices of the OPEN fence line and the LAST CLOSE fence line after it.

    A fence counts only when it is ALONE ON ITS OWN LINE, which is exactly how
    the emitter writes it (`manifest-triage.py` builds the block as a list of
    lines with the two fences as their own elements). Matching the marker as a
    bare substring instead is what made the region truncatable from inside an
    entry — see `extract_manifest_region` below.

    **LAST close, not first.** With first-close, a doc-style example that quotes
    both markers on their own lines *above* the real manifest captures the region
    and the real entries vanish — fewer entries, the unsafe direction. Taking the
    last close can only ever widen the region, so the parser sees more candidate
    entries, never fewer. Measured both ways; first-close erased a live
    `[verify-build]` blocker in that arrangement.
    """
    open_i: int | None = None
    close_i: int | None = None
    for i, raw in enumerate(lines):
        stripped = raw.strip()
        if open_i is None:
            if stripped == MANIFEST_OPEN:
                open_i = i
        elif stripped == MANIFEST_CLOSE:
            close_i = i
    return open_i, close_i


def extract_manifest_region(text: str) -> str:
    """Return the text between the manifest fences, or the whole text if the
    fences are absent.

    Scoping to the fences is what keeps prose elsewhere in a PR body — a
    changelog bullet, a quoted example — from being read as a live entry.

    **The fences are matched line-anchored, and that is load-bearing.** This
    previously did `text.split(MANIFEST_OPEN, 1)[1].split(MANIFEST_CLOSE, 1)[0]`
    — take everything up to the FIRST closing marker anywhere in the text. An
    entry whose *finding text* contained the closing marker therefore ended the
    region early, and every entry after it vanished from the parse. Measured on
    the pre-fix tree: a body carrying one marker-bearing entry followed by a real
    `[verify-build]` blocker parsed with the verify-build blocker **absent**, so
    a NOT-READY PR read as READY and shipped with no behavioural gate. That is
    the precise outcome this whole mechanism exists to prevent.

    **Reachability, stated precisely** (an earlier framing of this overstated it
    and was corrected by measurement). `[status-surface]` findings quote a
    verbatim line from a *scanned candidate* — `CLAUDE.md`, `AGENTS.md`,
    `README.md`, `GEMINI.md`, `.cursorrules`,
    `.github/copilot-instructions.md`. None of those carries the marker today, so
    the self-trigger does **not** fire on the current tree. `dev-docs/roadmap.md`
    does carry the literal marker in prose, but it is the *reference* the scan
    compares against, not a scanned candidate.

    So: **a latent self-trigger, one docs commit from live** — `README.md`
    already discusses the not-ready manifest, so a README that gains the literal
    marker while documenting the sentinel arms it with no adversary involved.
    Stronger than "crafted payload", weaker than "reachable now".

    **Honest boundary.** Line-anchoring closes the mid-line case, which is the
    reachable one: a marker quoted inside prose is never alone on its line. It
    does NOT by itself close a finding that embeds a real `\n` followed by a bare
    marker. That half is closed at WRITE time by `add-entry`'s newline collapse
    and marker defang (FB-0108, v1.42.0), which is merged and sits below this
    module in the same tree — measured end to end, not inferred from the sibling
    branch: a finding of `"drifted\n<close-marker>\ntail"` written through
    `add-entry` emits one physical line with the marker rewritten to an inert
    token, and a following `[verify-build]` blocker still parses.

    So the two layers together cover the reachable paths, with one honest gap:
    a body that did NOT come through `add-entry` — hand-edited on GitHub, or
    assembled from sections the write guard never touched. For those, line
    anchoring is the only layer, and a real newline before a bare marker still
    ends the region early. Naming that precisely is the point; "closed" without
    the qualifier would be the same overclaim this entry exists to record.

    Two earlier revisions of this docstring got the residual wrong, in the same
    direction, and both were caught by review rather than by the author:

    1. It claimed a newline was the **only** residual. `splitlines()` treats eight
       further code points as line boundaries, and all eight defeated the fix.
       Hence `split("\n")` above.
    2. It claimed `pr-coherence.py` "already split on `\n`", i.e. that this had
       diverged from a correct in-repo precedent. Measured, that module is MIXED:
       one `split("\n")` site and two `splitlines()` sites. The generalization
       was drawn from one of three call sites.

    The lesson is the one this repo keeps re-learning — a boundary claim is only
    as narrow as the API you used to compute it, and "only X remains" is a
    measurement, not a reading. Both revisions above were readings.

    **The consumer wants the OPPOSITE rule, and that is not drift.** `split("\n")`
    is right *here* because a narrower line definition finds FEWER fences, which
    widens the region. It is wrong in `parse_entries`, where a narrower line
    definition finds FEWER entries — two entries joined by one of the eight code
    points are read as a single line and the second is swallowed, blocker and all.
    That parser therefore takes the UNION of both splits. Same mechanism, opposite
    direction, because both layers are steering toward "more blockers, never
    fewer"; see the comment there before making the two "consistent."

    **Failure direction is deliberate.** If the fences are not found
    line-anchored, this returns the whole text — the same as "fences absent" —
    so the parser sees MORE candidate entries, never fewer. Degrading toward
    not-ready is the safe direction for a merge gate.
    """
    # split("\n") — NEVER str.splitlines(). splitlines() breaks on EIGHT more
    # boundaries (\x0b \x0c \x1c \x1d \x1e \x85 \u2028 \u2029), so a finding
    # carrying any of them around a bare marker still truncated the region and
    # still erased a live [verify-build] blocker — measured, all eight. No
    # "newline collapse" at write time strips \u2028 or \x0c, so the write-side
    # NEWLINE collapse alone missed them (its sibling marker-defang does cover
    # them, which is why the merged pair holds end to end).
    #
    # NOTE the asymmetry with `parse_entries`, which takes the UNION of this split
    # and `splitlines()`. Narrow is safe HERE (fewer fences found => wider region)
    # and unsafe THERE (fewer lines found => fewer blockers). Do not "unify" them.
    lines = text.replace("\r\n", "\n").split("\n")
    open_i, close_i = _fence_bounds(lines)
    if open_i is not None and close_i is not None:
        return "\n".join(lines[open_i + 1 : close_i])
    return text
