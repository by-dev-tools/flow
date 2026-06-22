#!/usr/bin/env python3
"""
Extract the declared visual capture-targets from the current PR's plan.

Reads a plan file (default: dev-docs/plan.md) and emits one capture-target per
`- [ ]` checkbox under the **active** `**Visual-walk:**` heading. Used by
`/flow:verify-build` Step 5a to drive a11y-gated screenshot capture from a
*deterministic* list, instead of each cold agent re-enumerating the state set
from prose differently (the cold-run non-determinism this closes).

The Visual-walk block (V1) is a list of checkable visual *assertions*
("empty/loading/error state renders", "primary button uses the accent token",
"enter motion ≤ 200ms", "focus moves into the dialog and Esc closes it"). This
parser is deliberately **1:1 per declared assertion** — it does NOT invent a
deduplicated app-state taxonomy from prose. §5a maps each assertion to the app
state it names/implies at capture time, but now works from a fixed, parsed
list rather than re-deriving the list itself. An optional leading
`[category: …]` tag (the planner template's `[state: …]` / `[token / motion:
…]` / `[interaction / a11y: …]` convention) is surfaced when present.

Contract:
- Input: plan file path (absolute or repo-relative).
- Output: JSON to stdout with shape:
    {
      "assertions": [
        {"text": "<full assertion text>", "category": "state" | null},
        ...
      ],
      "source_path": "<plan path>",
      "source_heading": "<the active Visual-walk heading line>",
      "block_count": <how many Visual-walk blocks exist in the file>,
      "warnings": ["..."]
    }
- Exit codes:
    0  — parsed successfully (assertions may be empty list with warning).
    1  — fatal: plan file does not exist, or unreadable.
    2  — fatal: malformed CLI args.

Routing behavior (V2.1 hardening — see walk_extract.py):
- **Decoupled from Spec-walk.** §5a calls this independently of behavioral
  criteria extraction, so a malformed `**Spec-walk:**` heading (which sends
  behavioral judging to spike mode) no longer silently skips visual capture.
  If a Visual-walk block exists on a uiSurface project, capture runs.
- **Robust heading match + first (active) block only**, identical to
  extract-criteria.py — the Visual-walk heading is `**Visual-walk** *(UI
  only…)*:` (trailing italic qualifier), which the old strict matcher missed.

Graceful-degradation (FB-0010 silent-skip defense):
- No Visual-walk block → empty assertions + warning + exit 0. §5a then captures
  the primary/launch state only and marks the rest not_tested — an explicit,
  visible gap, never a silent skip.

Stdlib only. Python 3.7+.
"""

from __future__ import annotations

import re
import sys

# Sibling import: lib dir is sys.path[0] when run as a script.
from walk_extract import cli_main

LABEL = "Visual-walk"

# Optional leading category tag inside an assertion, e.g.
# `[state: empty / loading / error renders]` or `[interaction / a11y: …]`.
# Captures the part before the first colon as the category hint. Only `cat` is
# consumed; the rest of the bracket is left in the verbatim `text`.
_CATEGORY_RE = re.compile(r"^\[(?P<cat>[^\]:]+):")

EMPTY_WARNING = (
    "no Visual-walk assertions extracted — plan may lack a `**Visual-walk:**` "
    "block (non-UI change, or UI plan that omitted it). §5a should capture the "
    "primary/launch state only and mark the rest not_tested; never invent a "
    "richer state set."
)


def parse_assertion(text: str) -> dict:
    """Split an optional leading `[category: …]` tag off an assertion line."""
    m = _CATEGORY_RE.match(text)
    category = m.group("cat").strip().lower() if m else None
    return {"text": text, "category": category}


if __name__ == "__main__":
    sys.exit(
        cli_main(
            sys.argv,
            label=LABEL,
            items_key="assertions",
            transform_item=parse_assertion,
            empty_warning=EMPTY_WARNING,
        )
    )
