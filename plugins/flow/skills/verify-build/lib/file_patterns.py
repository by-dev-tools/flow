#!/usr/bin/env python3
"""
Shared UI-file-pattern resolution for the flow reviewers (FB-0079).

ONE source of truth for the question *"which files does THIS reviewer care
about?"* — imported by `visual-significance.py` (same dir) and by
`audit-skips/lib/skip-audit-checks.py`, which already puts this directory on
`sys.path` for `walk_extract`. The underscore filename is deliberate: a module
named `visual-significance.py` is not importable, which is why the constant this
module now owns used to exist as a hand-synced copy in both consumers — exactly
the FB-0010 fan-out class.

WHY TWO SLOTS AND NOT ONE
-------------------------
Two reviewers gate on file patterns, and they ask **different questions** of the
same diff:

  visual  — /flow:verify-build's visual-significance predicate asks
            "does this change what the app DRAWS?"
  a11y    — /flow:accessibility-review's per-diff early exit asks
            "does this change something with an ACCESSIBILITY SURFACE?"

Those sets overlap heavily but are not equal, so a single `uiFilePatterns` slot
forces the consumer to pick which reviewer to answer wrongly. Measured on an
iOS/SwiftUI consumer: a directory that builds the string VoiceOver reads must be
INCLUDED for a11y, which then over-flags its pure-persistence neighbours as
visual; a mock-data file that decides what a chart looks like must be EXCLUDED
for a11y, which then under-flags a real render delta. Neither is expressible
with one slot.

RESOLUTION CHAIN (back-compatible by construction)
--------------------------------------------------
    visualFilePatterns  →  uiFilePatterns  →  DEFAULT_UI_PATTERN
    a11yFilePatterns    →  uiFilePatterns  →  DEFAULT_UI_PATTERN

A project that sets only `uiFilePatterns` — or neither slot — resolves to
exactly what it resolved to before the split, for both consumers. The
per-consumer slots are purely additive; no existing project's behavior changes
without an explicit opt-in.

The shell mirror of this chain lives in `accessibility-review/SKILL.md` (see the
NOTE above its `UI_PATTERN` assignment for why the jq form is the long one and
not the obvious `.a // .b // empty`).

That mirror is a genuine cross-runtime fan-out — one contract, two languages —
so it is checked mechanically rather than by comment: `run_visual_significance_evals.py`
extracts the live jq expression from the SKILL and asserts it agrees with
`resolve()` across every config shape. This docstring deliberately does NOT
transcribe the jq, because the first version of it did, transcribed the rejected
form, and shipped a "single source of truth" that contradicted itself in the same
commit. A comment saying "keep these in sync" is the failure mode, not the fix.

Stdlib only. Python 3.7+.
"""

from __future__ import annotations

import re

# Consumer identifiers. Use the constants, not bare strings, so a typo is an
# AttributeError at import rather than a silent fallback to the shared slot.
VISUAL = "visual"
A11Y = "a11y"

#: Per-consumer override slot names.
CONSUMER_SLOT = {VISUAL: "visualFilePatterns", A11Y: "a11yFilePatterns"}

#: The shared fallback slot both consumers honor when their own slot is unset.
SHARED_SLOT = "uiFilePatterns"

#: Reported as the `source` when neither slot supplied a pattern.
DEFAULT_SOURCE = "built-in default"

# MUST stay in sync with the `UI_PATTERN` default literal in
# accessibility-review/SKILL.md and the `uiFilePatterns` / `visualFilePatterns` /
# `a11yFilePatterns` defaults in schema/flow.config.schema.json (FB-0010).
DEFAULT_UI_PATTERN = r"\.(tsx|jsx|vue|svelte|astro|mdx|css|scss|sass|less|html|njk|hbs|ejs)$"


def resolve(cfg, consumer):
    """Resolve `consumer`'s pattern from `cfg`.

    Returns `(pattern, source)` where `source` names whichever slot supplied the
    value (or `DEFAULT_SOURCE`) — callers surface it in their signals so an
    operator can see *which* slot produced the scoping they are looking at.

    Truthiness (not `is not None`) decides, matching the pre-split
    `cfg.get("uiFilePatterns") or DEFAULT_UI_PATTERN` idiom exactly: an empty
    string falls through to the next link rather than compiling to a
    match-everything regex.
    """
    cfg = cfg or {}
    own = CONSUMER_SLOT[consumer]
    for slot in (own, SHARED_SLOT):
        val = cfg.get(slot)
        if val:
            return val, slot
    return DEFAULT_UI_PATTERN, DEFAULT_SOURCE


def compile_for(cfg, consumer):
    """Resolve + compile `consumer`'s pattern.

    Returns `(compiled_regex, source, warnings)`. An unusable pattern degrades to
    `DEFAULT_UI_PATTERN` with a `[WARN]` that NAMES the offending slot — with two
    override slots plus a shared fallback, "uiFilePatterns is invalid" would point
    at the wrong line as often as the right one.

    `TypeError` is caught alongside `re.error` because a slot holding a non-string
    (an array — a shape the schema forbids but a hand-edited config can still
    carry) raises `TypeError` from `re.compile`, which the pre-split callers did
    not catch and crashed on.
    """
    pattern, source = resolve(cfg, consumer)
    try:
        return re.compile(pattern), source, []
    except (re.error, TypeError) as exc:
        return (
            re.compile(DEFAULT_UI_PATTERN),
            DEFAULT_SOURCE,
            [f"[WARN] {source} is not a usable extended regex ({pattern!r}: {exc}); "
             f"falling back to the built-in default UI pattern"],
        )
