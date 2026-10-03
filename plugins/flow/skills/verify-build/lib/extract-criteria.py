#!/usr/bin/env python3
"""
Extract acceptance criteria from the current PR's plan.

Reads a plan file (default: dev-docs/plan.md) and emits one criterion per
`- [ ]` checkbox under the **active** `**Spec-walk:**` heading. Used by
`/flow:verify-build` Step 3 to feed criteria to bundled `/verify`, and by
`/flow:audit-coverage` to read the declared-criteria set.

Contract:
- Input: plan file path (absolute or repo-relative).
- Output: JSON to stdout with shape:
    {
      "criteria": ["<criterion 1>", "<criterion 2>", ...],
      "source_path": "<plan path>",
      "source_heading": "<the active Spec-walk heading line, for traceability>",
      "source_heading_line": <1-indexed line of that heading, or null>,
      "ended_at_line": <1-indexed line of the terminator that CLOSED the block, or
                        null when it ran to end-of-file. Provenance, present on EVERY
                        call: it answers "how far did you read?" without warning on
                        the healthy path, which is how a truncated read is told apart
                        from a complete one (FB-0121). A terminator close that
                        collected items does NOT warn -- only a zero-item close does>,
      "block_count": <how many Spec-walk blocks exist in the file>,
      "all_demoted": <true iff block_count > 0 but every one is qualified
                      shipped/merged/demoted — no active block, distinct from
                      block_count == 0 (no heading at all)>,
      "warnings": ["..."]
    }
- Exit codes:
    0  — parsed successfully (criteria may be empty list with warning).
    1  — fatal: plan file does not exist, or unreadable.
    2  — fatal: malformed CLI args.

Routing behavior (V2.1 hardening — see walk_extract.py for the rationale):
- **Robust heading match.** Recognizes the canonical `**Spec-walk:**`, a
  qualified `**Spec-walk (PR 1c — shipped):**`, and a markdown `### Spec-walk`.
  The old strict matcher silently missed non-canonical *active* headings → 0
  criteria → silent spike fallback (and, downstream, silently-skipped visual
  capture). That silent-skip is the bug this closes.
- **First (active) block only.** When several Spec-walk blocks exist (flow's own
  multi-PR plan.md; a consumer retaining shipped blocks), only the first is
  extracted, with a loud warning naming the others. Convention: author the
  active PR's plan at the top. This replaces the old "qualify retained headings
  so they self-exclude" convention (which depended on author memory — the
  FB-0010 smell).

Graceful-degradation behavior (FB-0010 silent-skip defense):
- No Spec-walk heading found → empty criteria + warning + exit 0. Calling skill
  detects the empty list and falls back to spike mode rather than running on
  hallucinated criteria.
- Malformed checkboxes (`- []` no space) → ignored with a warning naming the
  line; valid checkboxes still extracted.

Stdlib only. Python 3.7+.
"""

from __future__ import annotations

import sys

# Sibling import: when run as `python3 .../lib/extract-criteria.py`, the lib
# dir is sys.path[0], so the shared helper resolves without packaging.
from walk_extract import cli_main

LABEL = "Spec-walk"

EMPTY_WARNING = (
    "no criteria extracted — plan may lack a `**Spec-walk:**` block, or all "
    "checkboxes are malformed. Calling skill should fall back to spike mode."
)


if __name__ == "__main__":
    sys.exit(
        cli_main(
            sys.argv,
            label=LABEL,
            items_key="criteria",
            empty_warning=EMPTY_WARNING,
        )
    )
