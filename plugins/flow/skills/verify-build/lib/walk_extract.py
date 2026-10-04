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

- **All-demoted detection.** A heading may carry a demote qualifier — `(shipped)`,
  `(merged …)`, `(demoted)` — already recognized by the heading regex but, until
  now, not given any meaning: "first heading found" won a plan even when that
  heading was qualified as already-shipped. When EVERY matched heading for a
  label is qualified this way, there is no active block at all — a PR with
  legitimately no `Spec-walk`/`Visual-walk` of its own (post-merge hygiene, a
  doc reconcile) must not be silently hidden behind the last-merged PR's
  criteria. `extract_block` now skips demoted headings when choosing the
  active one, and reports `all_demoted: True` (with `items: []`) instead of
  quietly returning a demoted heading's stale checkboxes. This is distinct
  from `block_count == 0` (no heading at all) — callers should not conflate
  the two when deciding whether to fall back to spike mode.

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

# A heading qualifier marking a block as already-shipped/merged/demoted, e.g.
# `**Spec-walk (PR 1c — shipped):**`, `**Spec-walk (merged #86):**`. Matched
# against the heading LINE (not just the parenthetical), so it fires wherever
# the qualifier word appears inside any parens on that line.
_DEMOTED_QUALIFIER_RE = re.compile(
    r"\([^)]*\b(?:shipped|merged|demoted)\b[^)]*\)", re.IGNORECASE
)


# A heading that DECLARES non-applicability: `**Visual-walk:** N/A — no UI here`.
#
# Matched against the heading's TAIL (what follows the label and its punctuation),
# anchored at the start, against a CLOSED token set. Two properties make this safe
# where the roadmap entry feared a string match would not be:
#
#   * It is only ever consulted when the block parsed ZERO assertions, so a miss
#     fails SAFE — the caller keeps today's behaviour, which is to force. The
#     fragile direction would be a match that suppresses something real; this
#     cannot, because there is nothing declared to suppress.
#   * Anchoring means it recognises a CONVENTION rather than interpreting prose. A
#     heading whose tail is a sentence that happens to contain "none" somewhere does
#     not match; `**Visual-walk:** N/A — …` does.
#
# The trailing guard requires the token to END the tail or be followed by a
# SEPARATOR — not merely by a non-alphanumeric.
#
# The first cut used `(?![A-Za-z0-9])`, which accepts whitespace, so
# `**Visual-walk:** None yet, will fill in` and `**Visual-walk:** None of the states
# change` both matched and would have SUPPRESSED the override. That is the dangerous
# direction and the one the "a miss fails safe" argument does not cover: failing safe
# protects against missed denials, not against invented ones — and "None yet" is
# precisely the author-forgot reading this predicate must not adopt. Found by
# /simplify's altitude lens.
#
# The accepted tradeoff: `N/A for this PR` now misses, so that heading keeps forcing
# and the author clears a waivable manifest entry. That is the right way round — a
# false force costs a waiver, a false suppression ships an unseen UI with a green
# report. Measured on flow's own history, the dominant form is `N/A — <reason>`
# (19 Visual-walk headings, all denials, 17 of them the identical boilerplate), so
# the narrower guard matches what authors actually write.
_NA_TAIL_RE = re.compile(
    r"^(?:not\s+applicable|n\s*/\s*a|n\.\s*a\.?|none|nil|na)"
    r"(?=\s*(?:$|[\u2014\u2013:.,;(\-]))",
    re.IGNORECASE,
)

# A DEFERRAL is not a denial, and separating the two is the whole difficulty.
#
# The guard above went through two wrong versions before this one, and the second is
# the instructive failure. v1 used `(?![A-Za-z0-9])`, which accepts whitespace, so
# `None yet, will fill in` matched. v2 "fixed" it by requiring a separator — and a
# deferral is spelled with separators too, so `None, will fill in later`,
# `N/A - to be filled in at Step 8`, `NA: pending the prototype`, `None (TBD)` and
# `none. TODO before the gate` all still matched. `None yet, will fill in` was
# rejected only because the word `yet` happened to sit between `None` and the comma;
# reorder the same sentence and it suppressed again. The 22-row table pinned the three
# shapes its author happened to write, not the class. Found by /flow:staff-review.
#
# So the boundary is not where the discrimination lives. What distinguishes the two is
# that a deferral says WHEN rather than WHY: it carries a forward-looking marker. This
# rejects on that marker instead of trying to spell the separator set correctly.
# Checked against every accept row — `nothing visual`, `backend only`, `no file
# matching uiFilePatterns is in scope` carry none of these.
# TWO rejection intents, one regex, because both are the tail UN-DENYING what the
# token denied — and in both the consequence is identical: a visual surface exists
# and suppressing the override would hide it.
#
#   DEFERRAL — "later". `None, will fill in later` · `N/A - to be filled in at
#   Step 8` · `NA: pending the prototype` · `None (TBD)`.
#
#   REDIRECTION — "elsewhere". `Not applicable, see the prototype for frames`. This
#   one is the subtler of the two and it is a plausible authoring on D1's
#   prototype-first path, where frames really were reviewed at gate 1. It is still
#   rejected, because the sentence asserts that visual artifacts EXIST; whether the
#   review already happened is the human's call at the merge gate, not something a
#   parser should infer from prose. The author who means it can omit the block.
#
# Deliberately NOT keyed on the word "visual": `N/A — nothing visual` is a genuine
# denial and an accept row. The markers below name artifacts that EXIST, not the
# adjective.
_UNDENIAL_RE = re.compile(
    r"\b(?:yet|tbd|todo|pending|will\s|to\s+be\b|coming|later|for\s+now|"
    r"not\s+done|unfilled|fill\s+in|filled\s+in|"
    r"frames?|screenshots?|prototype|walkthrough|recording|capture[sd]?)",
    re.IGNORECASE,
)


def heading_declares_na(line: str, label: str) -> bool:
    """True if `line` is a `<label>` heading whose tail opens with a denial token.

    Strips markdown decoration first so one rule covers all three heading forms
    (`**Label:** N/A`, `**Label** *(UI only)*: N/A`, `### Label — N/A`).
    """
    bare = re.sub(r"[*_#`]+", " ", line)
    m = re.search(re.escape(label) + r"\b", bare, re.IGNORECASE)
    if not m:
        return False
    tail = bare[m.end():]
    tail = re.sub(r"^\s*\([^)]*\)", "", tail)      # a parenthetical qualifier
    tail = tail.lstrip()
    # One strip, not two: the class below already contains `:`, so the separate
    # colon-drop that used to sit here was dead on every input (/simplify's reuse
    # lens; verified across the pinned accept/reject table plus four extra shapes —
    # no case behaved differently with it removed). This also covers the separator an
    # author puts between the label and the reason.
    tail = tail.lstrip(" \t:\u2013\u2014-.")
    if not _NA_TAIL_RE.match(tail):
        return False
    # A denial that defers or redirects is not a denial. Checked on the WHOLE tail,
    # so the marker is found wherever in the reason it appears: `N/A - to be filled
    # in at Step 8` denies and then un-denies, and the un-denial is what matters.
    return not _UNDENIAL_RE.search(tail)


def _is_demoted_heading(line: str) -> bool:
    """True if `line` is a walk heading qualified as already-shipped."""
    return bool(_DEMOTED_QUALIFIER_RE.search(line))


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


def collect_items(
    lines: list[str], start: int, end: int | None = None
) -> "tuple[list[str], list[str], int | None]":
    """Collect ONE block's checkbox items, scanning from just after heading index `start`.

    Returns `(items, warnings, ended_at)`, where `ended_at` is the 0-indexed line of the
    terminator that closed the block, or `None` if the scan ran to `end`/EOF.

    This exists because "what a block contains" was written TWICE -- here and in
    `critique-plan/lib/walk-pin-lint.py`, which imported the primitives and re-scanned
    because it needs every block rather than the first. Both copies took only each
    bullet's first physical line, and both ended the block on an indented continuation
    line; fixing one would have left `/flow:critique-plan` reading a fraction of the plan
    and reporting clean (general.md item 2 -- a contract spelled in two places where a
    change touches one). One definition, two readers.

    Two behaviours worth naming, because each was a silent defect:

    - **An indented, non-checkbox line under an item is part of that item**, which is what
      markdown says it is. Previously it fell through to `is_terminator`, and a
      continuation line opening with a bold span (`      **A note.**`) matched the
      bold-label heading pattern and ENDED the block -- every later criterion vanished
      with nothing said. Measured on #159's plan: 12 criteria whose 67-line block carries
      52 continuation lines reached a reviewer as 1,143 of ~5,850 characters.
    - **A block that ends at a terminator says so.** A truncated read and a complete one
      must not look alike to a consumer (FB-0121). Running to EOF is silent: there is
      nothing to disclose, and a warning on every clean block would be noise.

    Known limit, deliberate: a continuation must be INDENTED. Markdown also permits a
    "lazy" flush-left continuation, but a flush-left line is genuinely ambiguous with a
    new paragraph or heading, and resolving it the other way would merge real blocks.
    """
    stop = len(lines) if end is None else end
    items: list[str] = []
    warnings: list[str] = []
    ended_at: int | None = None
    in_item = False

    for j in range(start + 1, stop):
        line = lines[j]

        cb = CHECKBOX_RE.match(line)
        if cb:
            item_text = cb.group("text").strip()
            if item_text:
                items.append(item_text)
                in_item = True
            else:
                warnings.append(f"line {j + 1}: empty checkbox text; skipped")
                in_item = False
            continue

        if not line.strip():
            # A blank line closes the item: what follows is a new paragraph, not a wrap.
            in_item = False
            continue

        # Checked BEFORE the continuation fold, so a malformed checkbox still warns when it
        # is indented under an item instead of being quietly folded into the text above it.
        if _MALFORMED_CB_RE.match(line):
            warnings.append(
                f"line {j + 1}: looks like a malformed checkbox "
                f"(expected `- [ ]` or `- [x]`); skipped: {line.rstrip()[:80]}"
            )
            in_item = False
            continue

        # `in_item` is set True only on the line after an append, so it implies a non-empty
        # `items`; an `and items` conjunct here could never be the deciding term and only
        # made a reader prove that for themselves.
        if in_item and line[:1].isspace():
            items[-1] = f"{items[-1]} {line.strip()}"
            continue

        # The next heading (markdown, bold label, or the next walk heading of any label)
        # ends the active block.
        if is_terminator(line):
            ended_at = j
            # WARN ONLY WHEN THE CLOSE LOOKS WRONG. The first version of this warned on EVERY
            # terminator close, which a review lens correctly called out: `extract_block` is
            # first-active-block-only by design, so a terminator is the NORMAL way nearly every
            # real plan's block ends. It fired on this repo's own healthy plan. Before, truncation
            # was silent; after, truncation and success emitted the same sentence -- still
            # non-discriminating, now with added noise. That is the failure `rigor-marker.py` in
            # this same change warns about in its own comment: a gate that always fires is one
            # people learn to click past. A zero-item close is the signal worth a warning: the
            # heading matched and nothing came out of it. Where the read STOPPED is provenance,
            # not an alarm, so it is returned as `ended_at` and surfaced as `ended_at_line`.
            if not items:
                warnings.append(
                    f"the block ended at line {j + 1} ({line.strip()[:60]!r}) having collected "
                    f"NO items — the heading matched but nothing was read under it. This is not "
                    f"an empty plan: check for a blank line or a stray heading between the "
                    f"heading and its checkboxes."
                )
            break

    return items, warnings, ended_at


def extract_block(text: str, label: str, anchor_label: str | None = None) -> dict:
    """
    Extract the FIRST (active) `<label>` block's checkbox items from `text`.

    Returns a dict:
      {
        "items":         [<checkbox text>, ...],   # first ACTIVE block only
        "block_count":   <int>,                    # how many label blocks exist
        "first_heading": "<heading line>" | None,  # the selected heading
        "first_heading_line": <int> | None,        # 1-indexed line of that heading
        "co_located":    True | False | None,      # vs anchor_label's active region
        "all_demoted":   True | False,              # every block is qualified shipped/merged/demoted
        "declared_na":   True | False,              # heading declares N/A AND zero assertions
                                                    # (meaningful for Visual-walk only — see below)
        "warnings":      ["..."],
      }

    `block_count == 0` means no label block at all (caller falls back / skips
    with an explicit reason — never a silent gap). `all_demoted == True` is a
    DIFFERENT empty-items case: `block_count > 0`, but every matched heading is
    qualified as already-shipped — there is no active block, not "no heading at
    all". Callers must not conflate the two.

    When `anchor_label` is given, the matched block must fall inside the ACTIVE
    region — every line before the SECOND `anchor_label` heading — or it is
    treated as belonging to a retained PR: `items` is emptied and a loud warning
    is emitted (`co_located=False`). This closes the silent cross-PR grab that
    per-label first-block scoping cannot see; see the module docstring.
    `co_located` is `None` when co-location is undefined (no `anchor_label`
    passed, no anchor heading present, or no block of `label` at all).

    `declared_na` is computed for whatever `label` is passed, but it is only
    MEANINGFUL for `Visual-walk`: it answers "did the author declare there is no
    visual surface?", and no consumer asks that of a `Spec-walk` block. A
    `**Spec-walk:** N/A` heading with no checkboxes will set it true on
    `extract-criteria.py`'s output, where nothing reads it. Said here rather than
    special-cased, because a label check inside the parser would be a second place
    that knows which labels exist (/simplify's altitude lens flagged the latent
    misread).
    """
    lines = text.splitlines()
    warnings: list[str] = []

    heading_idxs = _heading_indices(lines, label)
    if not heading_idxs:
        return {
            "items": [],
            "block_count": 0,
            "first_heading": None,
            "first_heading_line": None,
            "co_located": None,
            "all_demoted": False,
            "declared_na": False,
            "warnings": warnings,
        }

    active_idxs = [i for i in heading_idxs if not _is_demoted_heading(lines[i])]
    if not active_idxs:
        at = ", ".join(str(i + 1) for i in heading_idxs)
        warnings.append(
            f"every {label} block found (lines {at}) is qualified as already-"
            f"shipped/merged/demoted — the active section declares NO {label} "
            f"of its own. This is NOT the same as no {label} heading at all "
            f"(block_count=0); do not silently borrow a demoted block's stale "
            f"checkboxes."
        )
        return {
            "items": [],
            "block_count": len(heading_idxs),
            "first_heading": None,
            "first_heading_line": None,
            "co_located": None,
            "all_demoted": True,
            "declared_na": False,
            "warnings": warnings,
        }

    first = active_idxs[0]
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

    items, item_warnings, ended_at = collect_items(lines, first, scan_end)
    warnings.extend(item_warnings)

    return {
        "items": items,
        "block_count": len(heading_idxs),
        "first_heading": first_heading,
        # 1-indexed line of the SELECTED heading. Surfaced as a field because it is the
        # only value in this contract that distinguishes WHICH block was read: in a plan
        # retaining shipped blocks every unqualified heading is the identical string
        # `**Spec-walk:**`, and `block_count` is a file-wide total. `/flow:autoplan`'s
        # Arm A asserts it graded the plan it was handed, and the alternative was scraping
        # the line number back out of the warning prose above -- an instrument that breaks
        # the next time that sentence is reworded.
        "first_heading_line": first + 1,
        # 1-indexed line of the terminator that CLOSED the block, or None when it ran to EOF.
        # Provenance, deliberately not a warning: it answers "how far did you read?" on every
        # call, including the healthy ones, which is what distinguishes a truncated read from a
        # complete one (FB-0121) without making every clean block shout.
        "ended_at_line": (ended_at + 1) if ended_at is not None else None,
        "co_located": co_located,
        "all_demoted": False,
        # DECLARED non-applicability: the heading says N/A **and** the block parsed
        # zero assertions. Both halves are folded in here on purpose, so a consumer
        # reads one boolean and cannot forget the items check — the direction the
        # roadmap's option (a) got wrong was exactly "zero assertions" without a
        # declaration. Sibling of `all_demoted`: both mean "this block declares
        # nothing active", for different reasons.
        # `co_located is not False` is part of the conjunction, not an afterthought.
        # When the match is non-co-located, `scan_end` force-empties `items`, so
        # `not items` is VACUOUSLY true and a retained PR's `**Visual-walk:** N/A`
        # carrying two real assertions returned `declared_na: True` — contradicting
        # this field's own documented meaning ("declares N/A AND zero assertions").
        # Not live, because both readers conjoin with `co_located` themselves, but a
        # field whose docstring is false is a trap for the next reader
        # (/flow:staff-review).
        "declared_na": bool(co_located is not False and not items
                            and heading_declares_na(first_heading, label)),
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
                "source_heading_line": block["first_heading_line"],
                # Carried through to the COMPOSED surface, not just the library result. The
                # first version of this field existed only on `extract_block`'s dict, which no
                # consumer reads -- every one of them shells out to this CLI. A contract that is
                # correct one layer below the surface it describes is the claim-layer mismatch
                # `general.md` item 4 names, and it was reproduced here while fixing an instance
                # of it: `extract_block` said 196, the JSON said nothing at all.
                "ended_at_line": block.get("ended_at_line"),
                "block_count": block["block_count"],
                "co_located": block["co_located"],
                "all_demoted": block["all_demoted"],
                "declared_na": block["declared_na"],
                "warnings": warnings,
            },
            indent=2,
        )
    )
    return 0
