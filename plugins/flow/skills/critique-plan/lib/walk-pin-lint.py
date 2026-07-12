#!/usr/bin/env python3
"""
Deterministic Spec-walk pinning lint for /flow:critique-plan.

Dogfooding queued plan documents surfaced a gap class neither reviewer's
categories catch: Spec-walk checkboxes that name NO pinning test or
verification artifact ("Rate limiting works correctly" — verified by what?).
Per flow's "narrow scope beats wide scope" principle this is a deterministic
engine feeding the plan-critic, not a new reviewer category: the lint reports,
the critic assigns severity (and only where the project's own reference docs
require pinning — see the skill instructions).

Input: plan text on stdin, or a file path as the single argument. A path
argument is cwd-containment-guarded (out-of-cwd reads rejected, mirroring
extract_session.load_plan_file — the report feeds the reviewer prompt); stdin is
unguarded by design (the caller owns that trust boundary).

Block parsing REUSES the shared parser primitives in
`skills/verify-build/lib/walk_extract.py` (heading_re / CHECKBOX_RE /
is_terminator) — the established cross-skill lib precedent
(visual-significance.py, pr-coherence.py) — so "what counts as a walk block"
has one source of truth. One deliberate difference from
`walk_extract.extract_block`: that function scopes to the FIRST block (the
active-PR convention in a living plan.md, with a loud multi-block warning);
a standalone plan DOCUMENT may legitimately carry several Spec-walk blocks,
so this lint walks ALL of them — cheap with the shared primitives — and says
so with a note. Heading tolerance is inherited from `heading_re`: bold
(`**Spec-walk:**`), qualified (`**Spec-walk (queued — hoist to bare on
activation):**`), and markdown (`### Spec-walk`) forms all match.

Output: a deterministic plain-text report —
    PIN LINT: N/M checkboxes carry a named pin — K unpinned:
      - UNPINNED: <verbatim checkbox text, truncated>
or `PIN LINT: clean — M/M checkboxes carry a named pin.` when all pinned.
No Spec-walk block / no checkboxes → a loud note (absence of a plan block is
the reviewers' business, not the lint's).

Exit codes: 0 for every lint verdict (advisory — the critic assigns severity);
nonzero only on crash-grade input errors (unreadable file, bad usage).

Stdlib only. Python 3.7+.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

_WALK_LIB = Path(__file__).resolve().parents[2] / "verify-build" / "lib"
sys.path.insert(0, str(_WALK_LIB))
try:
    from walk_extract import CHECKBOX_RE, heading_re, is_terminator  # noqa: E402
except ImportError as e:  # loud, not silent — the SKILL preamble catches this
    sys.stderr.write(
        f"walk-pin-lint: ⚠️ cannot import shared walk_extract from {_WALK_LIB} "
        f"({e}) — pinning lint unavailable.\n"
    )
    sys.exit(1)

LABEL = "Spec-walk"

# A pin is EITHER a named test...
TEST_ID_RE = re.compile(r"\btest[A-Z]\w+")          # testRateLimitExceeded
BACKTICK_TEST_RE = re.compile(r"`[Tt]est[^`]*`|`[\w.]*[._][Tt]est[^`]*`")

# ...or an explicit non-test artifact pin: a pin marker followed by a concrete
# verification artifact.
PIN_MARKERS = ("→", "->", "pinned by", "verify:", "verified by")
ARTIFACT_RE = re.compile(
    r"\b(grep|frame|on-sim|simulator|screenshot|doc-diff|diff|report|eval|"
    r"snapshot|fixture|walkthrough|recording)s?\b",
    re.IGNORECASE,
)

TRUNCATE_AT = 160


def is_pinned(text: str) -> bool:
    if TEST_ID_RE.search(text) or BACKTICK_TEST_RE.search(text):
        return True
    low = text.lower()
    for marker in PIN_MARKERS:
        idx = low.find(marker)
        while idx != -1:
            if ARTIFACT_RE.search(text[idx + len(marker):]):
                return True
            idx = low.find(marker, idx + 1)
    return False


def collect_spec_walk_blocks(text: str) -> list[tuple[str, list[str]]]:
    """All (heading, checkbox-texts) Spec-walk blocks in document order, using
    the shared walk_extract primitives for heading match, checkbox shape, and
    block termination."""
    hre = heading_re(LABEL)
    lines = text.splitlines()
    blocks: list[tuple[str, list[str]]] = []
    for i, line in enumerate(lines):
        if not hre.match(line):
            continue
        items: list[str] = []
        for j in range(i + 1, len(lines)):
            cb = CHECKBOX_RE.match(lines[j])
            if cb:
                item_text = cb.group("text").strip()
                if item_text:
                    items.append(item_text)
                continue
            if is_terminator(lines[j]):
                break
        blocks.append((line.strip(), items))
    return blocks


def _read_plan_arg(path_str: str) -> str:
    """Read a plan file named as the CLI argument, with the same cwd-containment
    guard load_plan_file (extract_session.py) enforces — the lint's report feeds
    the reviewer subagent's prompt, so an out-of-cwd path is a host-file read into
    that context. `resolve()` canonicalizes symlinks + `..` BEFORE the
    relative_to check, so a symlink under cwd pointing outside is still rejected.
    Out-of-cwd → loud stderr + nonzero exit, never read. (stdin is intentionally
    unguarded: the caller — e.g. extract_session, itself guarded — owns that
    trust boundary; pipe text in for a deliberate out-of-tree lint.)"""
    cwd = Path.cwd().resolve()
    raw = Path(path_str).expanduser()
    candidate = raw if raw.is_absolute() else (cwd / raw)
    try:
        resolved = candidate.resolve()
    except (OSError, RuntimeError) as e:
        sys.stderr.write(f"walk-pin-lint: ⚠️ cannot resolve plan file {path_str!r}: {e}\n")
        raise SystemExit(1)
    try:
        resolved.relative_to(cwd)
    except ValueError:
        sys.stderr.write(
            f"walk-pin-lint: ⚠️ rejecting plan file outside cwd: {resolved}\n"
            f"  (pipe the text on stdin if an out-of-tree lint is intentional.)\n"
        )
        raise SystemExit(1)
    try:
        return resolved.read_text(encoding="utf-8")
    except OSError as e:
        sys.stderr.write(f"walk-pin-lint: ⚠️ cannot read plan file {resolved}: {e}\n")
        raise SystemExit(1)


def main(argv: list[str]) -> int:
    if len(argv) > 2:
        sys.stderr.write(
            f"usage: {Path(argv[0]).name} [<plan-path>]   (or plan text on stdin)\n"
        )
        return 2
    if len(argv) == 2:
        text = _read_plan_arg(argv[1])
    else:
        text = sys.stdin.read()

    blocks = collect_spec_walk_blocks(text)
    if not blocks:
        print(
            "PIN LINT: ⚠️ no Spec-walk block found in the plan text — nothing to "
            "lint. (Whether the plan NEEDS a Spec-walk block is the reviewers' "
            "business, not this lint's.)"
        )
        return 0

    if len(blocks) > 1:
        print(
            f"PIN LINT: note — {len(blocks)} Spec-walk blocks found; linting all "
            "of them (a standalone plan document may legitimately carry several)."
        )

    checkboxes = [item for _, items in blocks for item in items]
    if not checkboxes:
        print(
            "PIN LINT: ⚠️ Spec-walk block(s) found but no checkboxes under them — "
            "nothing to lint. (Missing checkboxes are the reviewers' business.)"
        )
        return 0

    unpinned = [c for c in checkboxes if not is_pinned(c)]
    total = len(checkboxes)
    if not unpinned:
        print(f"PIN LINT: clean — {total}/{total} checkboxes carry a named pin.")
        return 0

    print(
        f"PIN LINT: {total - len(unpinned)}/{total} checkboxes carry a named pin "
        f"— {len(unpinned)} unpinned:"
    )
    for c in unpinned:
        shown = c if len(c) <= TRUNCATE_AT else c[:TRUNCATE_AT - 3] + "..."
        print(f"  - UNPINNED: {shown}")
    print(
        "(Advisory: an unpinned checkbox names no test or verification artifact. "
        "Severity is the plan-critic's call.)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
