#!/usr/bin/env python3
"""Shared helpers for eval harnesses that need to extract and execute a SKILL.md's
fenced shell blocks (as opposed to grepping its prose). Hoisted out of
`run_role_slot_evals.py` when `run_merge_status_evals.py` needed the identical
helper — two eval harnesses independently defining the same parser is the exact
FB-0010 fan-out class this repo's own consistency rule names, so it gets one home
like every other shared predicate in this codebase (`_lint()` / `skill-composition-lint.py`,
`slot_count_scan.py`).

Stdlib only.
"""

from __future__ import annotations

import re


def rest_from(text, heading_substr):
    """Slice `text` from `heading_substr` onward, or None if absent."""
    idx = text.find(heading_substr)
    return None if idx == -1 else text[idx:]


def fenced_block(text, heading_substr):
    """The first ```sh fenced block after `heading_substr` — the executable shell,
    not the surrounding prose. Used to actually RUN a doctor check rather than grep
    its text (a check whose text merely mentions the right thing is not the same as
    a check that DOES the right thing)."""
    rest = rest_from(text, heading_substr)
    if rest is None:
        return None
    m = re.search(r"```sh\n(.*?)\n```", rest, re.DOTALL)
    return m.group(1) if m else None
