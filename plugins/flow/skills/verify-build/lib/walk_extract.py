#!/usr/bin/env python3
"""
Shared `*-walk` block extraction for /flow:verify-build.

Both `extract-criteria.py` (behavioral **Spec-walk**) and
`extract-visual-states.py` (visual **Visual-walk**) parse the same document
shape: a labeled heading followed by `- [ ]` checkbox lines, terminated by the
next heading. This module owns the heading-matching + first-(active-)block
scoping + checkbox collection so the two parsers cannot drift (FB-0010 fan-out
defense — one source of truth for the contract value "what counts as a walk
block").

Design (V2.1 hardening, 2026-06-21 — closes the two cold-gate routing
follow-ups):

- **Robust heading match.** A label heading is recognized whether written as a
  bold label (`**Spec-walk:**`, `**Spec-walk (PR 1c — shipped):**`,
  `**Visual-walk** *(UI only)*:`) OR a markdown heading (`### Spec-walk`). The
  old strict `^\\*\\*Label:?\\*\\*:?$` form silently missed every
  non-canonical *active* heading → 0 items → silent spike fallback → visual
  capture skipped. That silent-skip is the bug this fixes.

- **Scope to the FIRST (active) block only.** Loosening the match would
  otherwise re-include every retained/historical block: under the old strict
  regex those self-excluded *because* their qualified `(…)` headings failed to
  match, so they were never aggregated. Loosening the match and scoping to the
  active block are therefore co-dependent — you cannot safely do one without the
  other. The convention is: the active PR's plan goes at the TOP; retained
  blocks below are ignored and need no heading qualification (this removes the
  FB-0010 "consistency depends on author memory" smell the interim
  qualify-your-headings convention carried).

- **Loud multi-block WARN.** When >1 block matches the label, emit a warning
  naming every match line + the selected heading, so the silent wrong-block
  grab the cold-run hit becomes visible rather than a guess.

Stdlib only. Python 3.7+.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# Checkbox line: `- [ ] <text>` or `- [x] <text>` (also `*`/`+` bullet markers).
# Accept both unchecked (` `) and checked (`x`/`X`) — checkboxes get ticked off
# during execution; the item is still the verification target.
CHECKBOX_RE = re.compile(
    r"^\s*[-*+]\s+\[(?P<state>[ xX])\]\s+(?P<text>.+?)\s*$",
)

# Markdown ATX heading: `## ...` / `### ...`. Terminates a block.
_MD_HEADING_RE = re.compile(r"^\s*#{1,6}\s+\S")

# Bold-label heading line, e.g. `**Confidence verdicts:**`, `**Spec-walk:**`,
# `**Visual-walk** *(UI only)*:`. Tight enough not to fire on an in-line bold
# inside prose (`**Note:** some sentence` is NOT matched — no trailing colon /
# italic-only tail). Terminates a block.
_BOLD_LABEL_RE = re.compile(r"^\s*\*\*[^*]+\*\*(?:\s*\*[^*]+\*)?\s*:?\s*$")

# Malformed checkbox: `- []` (no space) / `- [?]` — worth a warning so the
# author notices, since it silently drops a would-be criterion otherwise.
_MALFORMED_CB_RE = re.compile(r"^\s*[-*+]\s+\[\s*[^\] xX]?\s*\]")


def heading_re(label: str) -> "re.Pattern[str]":
    """Compiled, case-insensitive matcher for a `<label>` walk heading.

    Matches the bold form (`**Label:**`, `**Label (qualifier):**`,
    `**Label** *(italic qualifier)*:`) and the markdown-heading form
    (`## Label`, `### Label (qualifier)`).
    """
    esc = re.escape(label)
    return re.compile(
        r"^\s*(?:"
        r"#{1,6}\s+" + esc + r"\b.*"        # ## Label / ### Label (…)
        r"|"
        r"\*\*\s*" + esc + r"\b.*?\*\*.*"   # **Label:** / **Label** *(…)*:
        r")$",
        re.IGNORECASE,
    )


def is_terminator(line: str) -> bool:
    """True if `line` ends a walk block (any markdown or bold-label heading)."""
    return bool(_MD_HEADING_RE.match(line) or _BOLD_LABEL_RE.match(line))


def extract_block(text: str, label: str) -> dict:
    """
    Extract the FIRST (active) `<label>` block's checkbox items from `text`.

    Returns a dict:
      {
        "items":         [<checkbox text>, ...],   # first block only
        "block_count":   <int>,                    # how many label blocks exist
        "first_heading": "<heading line>" | None,  # the selected heading
        "warnings":      ["..."],
      }

    `block_count == 0` means no label block at all (caller falls back / skips
    with an explicit reason — never a silent gap).
    """
    hre = heading_re(label)
    lines = text.splitlines()
    warnings: list[str] = []

    heading_idxs = [i for i, ln in enumerate(lines) if hre.match(ln)]
    if not heading_idxs:
        return {
            "items": [],
            "block_count": 0,
            "first_heading": None,
            "warnings": warnings,
        }

    first = heading_idxs[0]
    first_heading = lines[first].strip()

    if len(heading_idxs) > 1:
        at = ", ".join(str(i + 1) for i in heading_idxs)
        warnings.append(
            f"{len(heading_idxs)} {label} blocks found (lines {at}); extracted "
            f"ONLY the first — line {first + 1}: {first_heading!r}. Other blocks "
            f"are ignored. If the active block is not first, move it to the top "
            f"of the plan (retained blocks need no heading qualification)."
        )

    items: list[str] = []
    for j in range(first + 1, len(lines)):
        line = lines[j]

        cb = CHECKBOX_RE.match(line)
        if cb:
            item_text = cb.group("text").strip()
            if item_text:
                items.append(item_text)
            else:
                warnings.append(f"line {j + 1}: empty checkbox text; skipped")
            continue

        # The next heading (markdown, bold label, or the next walk heading of
        # any label) ends the active block.
        if is_terminator(line):
            break

        if _MALFORMED_CB_RE.match(line):
            warnings.append(
                f"line {j + 1}: looks like a malformed checkbox "
                f"(expected `- [ ]` or `- [x]`); skipped: {line.rstrip()[:80]}"
            )

    return {
        "items": items,
        "block_count": len(heading_idxs),
        "first_heading": first_heading,
        "warnings": warnings,
    }


def cli_main(
    argv: list[str],
    *,
    label: str,
    items_key: str,
    transform_item=None,
    empty_warning: str = "",
) -> int:
    """
    Shared CLI entry point for the `*-walk` extractors.

    Owns arg parsing, file existence / read-error handling (each emitting the
    standard JSON error shape to stderr), the `extract_block` call, and the JSON
    output — so `extract-criteria.py` and `extract-visual-states.py` cannot drift
    on the contract (FB-0010 fan-out defense). Callers supply only what differs:

    - `label`         — `"Spec-walk"` / `"Visual-walk"`.
    - `items_key`     — output key for the extracted list (`"criteria"` /
                        `"assertions"`).
    - `transform_item`— maps each raw checkbox string to its output shape
                        (default: identity — emit the string as-is).
    - `empty_warning` — appended when no items were extracted (the
                        spike-fallback / capture-primary-only nudge).

    Exit codes: 0 ok, 1 fatal file error, 2 malformed args.
    """
    prog = Path(argv[0]).name if argv else "extract"

    if len(argv) != 2:
        print(
            json.dumps(
                {"error": f"usage: {prog} <plan-path>", items_key: [], "warnings": []}
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
                    items_key: [],
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
                    items_key: [],
                    "warnings": [f"read error: {exc}"],
                    "source_path": str(plan_path),
                }
            ),
            file=sys.stderr,
        )
        return 1

    block = extract_block(text, label)
    transform = transform_item or (lambda s: s)
    items = [transform(s) for s in block["items"]]
    warnings = list(block["warnings"])

    if not items and empty_warning:
        warnings.append(empty_warning)

    print(
        json.dumps(
            {
                items_key: items,
                "source_path": str(plan_path),
                "source_heading": block["first_heading"],
                "block_count": block["block_count"],
                "warnings": warnings,
            },
            indent=2,
        )
    )
    return 0
