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
      "source_heading_line": <1-indexed line of that heading, or null>,
      "ended_at_line": <1-indexed line of the terminator that CLOSED the block, or
                        null when it ran to end-of-file. Provenance, present on EVERY
                        call: it answers "how far did you read?" without warning on
                        the healthy path, which is how a truncated read is told apart
                        from a complete one (FB-0121). A terminator close that
                        collected items does NOT warn -- only a zero-item close does>,
      "block_count": <how many Visual-walk blocks exist in the file>,
      "declared_na": <true iff the heading declares non-applicability AND zero
                      assertions — the author declared this change has NO visual
                      surface. §5a skips capture on it (and `warnings` then carries
                      the skip note, not the capture nudge);
                      `visual-significance.py` suppresses the override. The token
                      set and the deferral/redirection exclusions have ONE
                      definition, in `walk_extract.heading_declares_na`; the
                      author-facing statement of the convention is
                      `skills/plan-discipline/SKILL.md` field 8>,
      "all_demoted": <true iff block_count > 0 but every one is qualified
                      shipped/merged/demoted — no active block>,
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


# The DECLARED-N/A counterpart. `EMPTY_WARNING` above is correct for a bare empty
# block ("a visual surface, states unenumerated" — capture the launch state), and
# actively wrong for a declared denial, where §5a skips. §5a is agent-executed from
# this script's JSON, so emitting the capture nudge there made the primary data source
# contradict `verify-build/SKILL.md` §5a's own skip line (v1.62.0 staff-review).
EMPTY_WARNING_NA = (
    "the Visual-walk heading DECLARES non-applicability and the block lists no "
    "assertions — §5a skips capture for this plan (`[§5a] skipped: Visual-walk "
    "declared N/A`) and no frames are expected. Do NOT capture a launch state here; "
    "that is the bare-empty-block case, which is a different shape."
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
            # Scope to the active PR's section: a shared multi-PR plan whose
            # ACTIVE block declares no Visual-walk must not silently inherit a
            # retained PR's block (block_count==1 ⇒ no multi-block WARN fires).
            anchor_label="Spec-walk",
            transform_item=parse_assertion,
            empty_warning=EMPTY_WARNING,
            empty_warning_na=EMPTY_WARNING_NA,
        )
    )
