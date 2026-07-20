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

- **Anchor co-location (`anchor_label`).** First-block scoping is per-label and
  therefore *independent* across labels — which opens a silent cross-PR hole the
  multi-block WARN cannot see. In a shared multi-PR plan where the ACTIVE PR
  declares a `Spec-walk` but NO `Visual-walk`, and a retained PR below declares
  both, the Visual-walk parser matches the retained block: `block_count == 1`, so
  no multi-block warning fires and the active PR silently inherits another PR's
  capture state-set (and a forced `visual_significant`). Passing
  `anchor_label="Spec-walk"` scopes the match to the **active region** — every
  line before the SECOND anchor heading, per the "active PR at the top"
  convention (`rules/plan-discipline.md`). A block outside that region yields
  `items == []` + a loud warning instead of stale items, so "this PR declared
  none" degrades honestly rather than silently borrowing. Deliberately inert on
  the common shapes: a plan with <2 anchor headings, or none at all, behaves
  exactly as before (`co_located` is then `True` / `None`), and a Visual-walk
  authored *above* its sibling Spec-walk in the same section still counts.

  **KNOWN LIMITATIONS — anchoring closes ONE of three degenerate shapes.** The
  region boundary is "the second anchor heading," which is only a proxy for
  "where the active PR's section ends." Two shapes defeat that proxy and still
  adopt a retained block silently (`co_located` reads `True`, no warning):

  1. **The active PR has no anchor.** `tiny` omits Spec-walk entirely and a
     non-visual `spike` replaces it with a Research-question line
     (`rules/plan-discipline.md` § Required plan fields). `anchor_idxs[0]` then
     lands in the first *retained* section, so a retained Visual-walk between
     anchors 0 and 1 reads as active.
  2. **A retained section is authored Visual-walk-above-Spec-walk.** That block
     sits before the retained section's own anchor — i.e. before
     `anchor_idxs[1]` — so it falls inside the computed region. Note this is the
     same authoring order the parser deliberately *supports* for the active
     section (a Visual-walk above its sibling Spec-walk still counts), so the
     two cannot be told apart by order alone.

  Both are **pre-existing, not introduced here** — before anchoring, both leaked
  identically — and anchoring is a strict improvement for the `feature`-mode
  shape that was actually reported. Closing them needs a genuinely universal
  per-PR boundary marker, which is a decision about the plan format rather than
  a parser tweak; tracked in the roadmap. `test_anchor_known_limitation_*` pin
  the current behavior of both so neither is rediscovered as a fresh bug.

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


def _heading_indices(lines: list[str], label: str) -> list[int]:
    """Line indices of every `<label>` walk heading. One compile, one pass."""
    hre = heading_re(label)
    return [i for i, ln in enumerate(lines) if hre.match(ln)]


def extract_block(text: str, label: str, anchor_label: str | None = None) -> dict:
    """
    Extract the FIRST (active) `<label>` block's checkbox items from `text`.

    Returns a dict:
      {
        "items":         [<checkbox text>, ...],   # first block only
        "block_count":   <int>,                    # how many label blocks exist
        "first_heading": "<heading line>" | None,  # the selected heading
        "co_located":    True | False | None,      # vs anchor_label's active region
        "warnings":      ["..."],
      }

    `block_count == 0` means no label block at all (caller falls back / skips
    with an explicit reason — never a silent gap).

    When `anchor_label` is given, the matched block must fall inside the ACTIVE
    region — every line before the SECOND `anchor_label` heading — or it is
    treated as belonging to a retained PR: `items` is emptied and a loud warning
    is emitted (`co_located=False`). This closes the silent cross-PR grab that
    per-label first-block scoping cannot see; see the module docstring.
    `co_located` is `None` when co-location is undefined (no `anchor_label`
    passed, no anchor heading present, or no block of `label` at all).
    """
    lines = text.splitlines()
    warnings: list[str] = []

    heading_idxs = _heading_indices(lines, label)
    if not heading_idxs:
        return {
            "items": [],
            "block_count": 0,
            "first_heading": None,
            "co_located": None,
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

    # Anchor co-location. The active region is everything before the SECOND
    # anchor heading ("active PR at the top" convention), so a `label` block
    # authored either side of its sibling anchor within that leading section
    # still counts. Fewer than 2 anchor headings ⇒ no retained section exists to
    # confuse, so the match is trivially active.
    co_located = None
    if anchor_label:
        anchor_idxs = _heading_indices(lines, anchor_label)
        if anchor_idxs:
            region_end = anchor_idxs[1] if len(anchor_idxs) > 1 else len(lines)
            co_located = first < region_end
            if not co_located:
                # Name the anchor the block actually sits under (the nearest one
                # ABOVE it), not anchor_idxs[1] — in a 4-PR plan those differ, and
                # pointing at the wrong section reads as a broken tool.
                owning = max(i for i in anchor_idxs if i < first)
                warnings.append(
                    f"the first {label} block (line {first + 1}: {first_heading!r}) "
                    f"sits BELOW the active PR's section — it belongs to the "
                    f"retained {anchor_label} block at line {owning + 1}. Treating "
                    f"the active PR as declaring NO {label} block rather than "
                    f"inheriting a stale one. If this PR really does declare "
                    f"{label} items, move them into the active PR's section at the "
                    f"top of the plan (above the {anchor_label} at line "
                    f"{anchor_idxs[1] + 1})."
                )

    # A non-co-located block collects nothing. Bound the scan instead of returning
    # early, so the result contract is written in exactly one place (FB-0010: a
    # duplicated return shape is a fan-out contradiction waiting to happen).
    scan_end = len(lines) if co_located is not False else first + 1

    items: list[str] = []
    for j in range(first + 1, scan_end):
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
        "co_located": co_located,
        "warnings": warnings,
    }


def cli_main(
    argv: list[str],
    *,
    label: str,
    items_key: str,
    transform_item=None,
    empty_warning: str = "",
    anchor_label: str | None = None,
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
    - `anchor_label`  — sibling label whose active region scopes this match
                        (`"Spec-walk"` for the Visual-walk parser); see
                        `extract_block`. Omitted ⇒ today's unscoped behavior.

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

    block = extract_block(text, label, anchor_label=anchor_label)
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
                "co_located": block["co_located"],
                "warnings": warnings,
            },
            indent=2,
        )
    )
    return 0
