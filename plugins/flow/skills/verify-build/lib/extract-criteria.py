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
      "block_count": <how many Spec-walk blocks exist in the file>,
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

import json
import sys
from pathlib import Path

# Sibling import: when run as `python3 .../lib/extract-criteria.py`, the lib
# dir is sys.path[0], so the shared helper resolves without packaging.
from walk_extract import extract_block

LABEL = "Spec-walk"


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(
            json.dumps(
                {
                    "error": "usage: extract-criteria.py <plan-path>",
                    "criteria": [],
                    "warnings": [],
                }
            ),
            file=sys.stderr,
        )
        return 2

    plan_path = Path(argv[1])

    if not plan_path.exists():
        print(
            json.dumps(
                {
                    "error": f"plan file not found: {plan_path}",
                    "criteria": [],
                    "warnings": [f"plan file not found: {plan_path}"],
                    "source_path": str(plan_path),
                }
            ),
            file=sys.stderr,
        )
        return 1

    try:
        text = plan_path.read_text(encoding="utf-8")
    except OSError as exc:
        print(
            json.dumps(
                {
                    "error": f"could not read plan file {plan_path}: {exc}",
                    "criteria": [],
                    "warnings": [f"read error: {exc}"],
                    "source_path": str(plan_path),
                }
            ),
            file=sys.stderr,
        )
        return 1

    block = extract_block(text, LABEL)
    criteria = block["items"]
    warnings = list(block["warnings"])

    if not criteria:
        warnings.append(
            "no criteria extracted — plan may lack a `**Spec-walk:**` block, "
            "or all checkboxes are malformed. Calling skill should fall back "
            "to spike mode."
        )

    output = {
        "criteria": criteria,
        "source_path": str(plan_path),
        "source_heading": block["first_heading"],
        "block_count": block["block_count"],
        "warnings": warnings,
    }
    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
