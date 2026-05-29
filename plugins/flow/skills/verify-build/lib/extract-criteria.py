#!/usr/bin/env python3
"""
Extract acceptance criteria from the current PR's plan.

Reads a plan file (default: dev-docs/plan.md) and emits one criterion
per `- [ ]` checkbox under a `**Spec-walk:**` heading. Used by
`/flow:verify-build` Step 3 to feed criteria to bundled `/verify`.

Contract:
- Input: plan file path (absolute or repo-relative).
- Output: JSON to stdout with shape:
    {
      "criteria": ["<criterion 1>", "<criterion 2>", ...],
      "source_path": "<plan path>",
      "source_heading": "<the Spec-walk heading line, for traceability>",
      "warnings": ["..."]
    }
- Exit codes:
    0  — parsed successfully (criteria may be empty list with warning).
    1  — fatal: plan file does not exist, or unreadable.
    2  — fatal: malformed CLI args.

Graceful-degradation behavior (FB-0010 silent-skip defense):
- No `**Spec-walk:**` heading found → emit empty criteria + warning + exit 0.
  Calling skill detects empty list and falls back to spike mode rather
  than running on hallucinated criteria.
- Malformed checkboxes (`- [X]` mid-sentence, `- []` no space) → ignored
  with a warning naming the line; valid checkboxes still extracted.
- Multiple Spec-walk blocks → all are extracted, in document order.
  PR plans can have nested per-phase Spec-walks; we collect all of them.

Stdlib only. Python 3.7+.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# Spec-walk heading: matches lines like `**Spec-walk:**` or `**Spec-walk**:`
# at the start of a line (after optional whitespace). Plans in flow's own
# dev-docs always use unindented bold-headings; if a consumer's plan nests
# the heading under a list marker (`- **Spec-walk:**`) this regex won't
# match — by design, since the canonical per-PR shape is unindented.
SPEC_WALK_HEADING_RE = re.compile(
    r"^\s*\*\*Spec-walk:?\*\*:?\s*$",
    re.IGNORECASE,
)

# Checkbox line: `- [ ] <criterion text>` or `- [x] <criterion text>`.
# We accept both unchecked (` `) and checked (`x` / `X`) — checkboxes
# may be ticked off by the implementing agent during execution; the
# criterion is still the verification target.
CHECKBOX_RE = re.compile(
    r"^\s*-\s+\[(?P<state>[ xX])\]\s+(?P<text>.+?)\s*$",
)

# Markdown heading line: `## ...` or `### ...` — used to detect the end
# of a Spec-walk block. A new heading (any level) terminates extraction.
HEADING_RE = re.compile(r"^\s*#{1,6}\s+\S")

# Bold heading line: `**...:**` — also terminates a Spec-walk block.
# (e.g. `**Confidence verdicts:**` after `**Spec-walk:**`.)
BOLD_HEADING_RE = re.compile(r"^\s*\*\*[^*]+:?\*\*:?\s*$")


def extract_criteria(plan_text: str) -> tuple[list[str], list[str], str | None]:
    """
    Parse plan_text. Returns (criteria, warnings, first_heading_line).

    `first_heading_line` is the literal text of the first `**Spec-walk:**`
    line found (for traceability); None if no Spec-walk block.
    """
    criteria: list[str] = []
    warnings: list[str] = []
    first_heading: str | None = None

    in_spec_walk = False
    lines = plan_text.splitlines()

    for lineno, line in enumerate(lines, start=1):
        if SPEC_WALK_HEADING_RE.match(line):
            in_spec_walk = True
            if first_heading is None:
                first_heading = line.strip()
            continue

        if not in_spec_walk:
            continue

        # Inside a Spec-walk block — collect checkboxes until next heading.
        checkbox_match = CHECKBOX_RE.match(line)
        if checkbox_match:
            text = checkbox_match.group("text").strip()
            if not text:
                warnings.append(f"line {lineno}: empty checkbox text; skipped")
                continue
            criteria.append(text)
            continue

        # Heading or bold-heading terminates the block.
        if HEADING_RE.match(line) or BOLD_HEADING_RE.match(line):
            in_spec_walk = False
            continue

        # Lines like `- [X] something` with a capital X aren't malformed —
        # already captured above. Lines like `- [] no-space` ARE malformed
        # and worth warning about so the consumer notices.
        if re.match(r"^\s*-\s+\[\s*[^\] xX]?\s*\]", line):
            warnings.append(
                f"line {lineno}: looks like a malformed checkbox "
                f"(expected `- [ ]` or `- [x]`); skipped: {line.rstrip()[:80]}"
            )

    return criteria, warnings, first_heading


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

    criteria, warnings, first_heading = extract_criteria(text)

    if not criteria:
        warnings.append(
            "no criteria extracted — plan may lack a `**Spec-walk:**` block, "
            "or all checkboxes are malformed. Calling skill should fall back "
            "to spike mode."
        )

    output = {
        "criteria": criteria,
        "source_path": str(plan_path),
        "source_heading": first_heading,
        "warnings": warnings,
    }
    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
