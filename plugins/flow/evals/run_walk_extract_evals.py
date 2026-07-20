#!/usr/bin/env python3
"""
Regression eval for the `*-walk` plan parsers (V2.1 hardening).

Pins the contract for `walk_extract.extract_block` and the two CLI parsers
(`extract-criteria.py`, `extract-visual-states.py`):

  1. Robust heading match — canonical, qualified, and markdown-heading forms.
  2. First (active) block scoping — multi-block plans extract ONLY the first,
     with a loud warning naming the others.
  3. Decoupling — a Visual-walk block is found even when the Spec-walk heading
     is malformed (the silent-skip routing fix).
  4. Graceful degradation — no block → empty + warning + exit 0; malformed
     checkboxes warn but don't crash; missing file → exit 1.

Stdlib only. No network, no third-party deps. Run:
    python3 plugins/flow/evals/run_walk_extract_evals.py
Exits non-zero on any failure (CI gate).
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

LIB = Path(__file__).resolve().parent.parent / "skills" / "verify-build" / "lib"
sys.path.insert(0, str(LIB))

from walk_extract import extract_block, heading_re, is_terminator  # noqa: E402

CRITERIA = LIB / "extract-criteria.py"
VISUAL = LIB / "extract-visual-states.py"

_failures: list[str] = []
_passes = 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global _passes
    if cond:
        _passes += 1
    else:
        _failures.append(f"{name}: {detail}")


def run_cli(script: Path, plan_text: str) -> tuple[int, dict]:
    """Write plan_text to a temp file, run the CLI, return (exit, parsed-json)."""
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as fh:
        fh.write(plan_text)
        path = fh.name
    try:
        proc = subprocess.run(
            [sys.executable, str(script), path],
            capture_output=True,
            text=True,
        )
        stream = proc.stdout if proc.returncode == 0 else (proc.stdout or proc.stderr)
        try:
            parsed = json.loads(stream) if stream.strip() else {}
        except json.JSONDecodeError:
            parsed = {}
        return proc.returncode, parsed
    finally:
        Path(path).unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# 1. Heading-match robustness (walk_extract unit level)
# ---------------------------------------------------------------------------

def test_heading_forms() -> None:
    spec = heading_re("Spec-walk")
    for good in [
        "**Spec-walk:**",
        "**Spec-walk**:",
        "  **Spec-walk:**  ",
        "**Spec-walk (PR 1c — shipped):**",
        "**Spec-walk (each → criterion):**",
        "## Spec-walk",
        "### Spec-walk",
        "### Spec-walk (active PR)",
    ]:
        check("heading-spec-good", bool(spec.match(good)), f"should match: {good!r}")
    for bad in [
        "- [ ] Spec-walk happens here",   # checkbox, not a heading
        "We will write a Spec-walk soon",  # prose
        "**Visual-walk:**",                # different label
    ]:
        check("heading-spec-bad", not spec.match(bad), f"should NOT match: {bad!r}")

    vis = heading_re("Visual-walk")
    for good in [
        "**Visual-walk:**",
        "**Visual-walk** *(UI changes only)*:",
        "**Visual-walk** *(UI only — when uiSurface is true)*:",
        "### Visual-walk",
    ]:
        check("heading-vis-good", bool(vis.match(good)), f"should match: {good!r}")
    check("heading-vis-cross", not vis.match("**Spec-walk:**"), "label isolation")


def test_terminators() -> None:
    for t in ["## Heading", "**Confidence verdicts:**", "**Visual-walk** *(x)*:", "### Files"]:
        check("terminator-yes", is_terminator(t), f"should terminate: {t!r}")
    for nt in ["- [ ] a criterion", "just some prose", "**Note:** inline bold prose here"]:
        check("terminator-no", not is_terminator(nt), f"should NOT terminate: {nt!r}")


# ---------------------------------------------------------------------------
# 2. First (active) block scoping
# ---------------------------------------------------------------------------

MULTI_BLOCK = """# Plan

## Active PR

**Spec-walk:**
- [ ] active criterion one
- [ ] active criterion two

**Confidence verdicts:** none.

## Shipped PR (retained)

**Spec-walk (PR 1c — shipped):**
- [x] old criterion A
- [x] old criterion B
- [x] old criterion C
"""


def test_first_block_only() -> None:
    block = extract_block(MULTI_BLOCK, "Spec-walk")
    check("multi-count", block["block_count"] == 2, f"got {block['block_count']}")
    check(
        "multi-items",
        block["items"] == ["active criterion one", "active criterion two"],
        f"got {block['items']}",
    )
    check(
        "multi-warns",
        any("2 Spec-walk blocks found" in w for w in block["warnings"]),
        f"warnings: {block['warnings']}",
    )
    check(
        "multi-no-stale",
        all("old criterion" not in c for c in block["items"]),
        "stale retained criteria leaked",
    )


def test_terminates_at_confidence() -> None:
    # The active block must stop at **Confidence verdicts:**, not swallow it.
    block = extract_block(MULTI_BLOCK, "Spec-walk")
    check("term-len", len(block["items"]) == 2, f"got {block['items']}")


# ---------------------------------------------------------------------------
# 3. Decoupling — Visual-walk found despite a malformed Spec-walk heading
# ---------------------------------------------------------------------------

MALFORMED_SPEC_WITH_VISUAL = """# Plan

## Active PR

### Spec-walk (each → criterion)
- [ ] behavioral criterion one

**Visual-walk** *(UI changes only)*:
- [ ] [state: empty / loading / error renders, not a blank panel]
- [ ] [token / motion: primary button uses the accent token; enter ≤ 200ms]
- [ ] [interaction / a11y: focus enters dialog and Esc closes it]
"""


def test_visual_decoupled() -> None:
    # Even though the Spec-walk heading is the non-canonical h3 form, both
    # parsers now find their respective blocks independently.
    spec = extract_block(MALFORMED_SPEC_WITH_VISUAL, "Spec-walk")
    check("decouple-spec", spec["items"] == ["behavioral criterion one"], f"got {spec['items']}")

    vis = extract_block(MALFORMED_SPEC_WITH_VISUAL, "Visual-walk")
    check("decouple-vis-count", len(vis["items"]) == 3, f"got {vis['items']}")
    check(
        "decouple-vis-head",
        vis["first_heading"].startswith("**Visual-walk**"),
        f"got {vis['first_heading']!r}",
    )


def test_visual_category_parse() -> None:
    rc, out = run_cli(VISUAL, MALFORMED_SPEC_WITH_VISUAL)
    check("vis-cli-exit", rc == 0, f"exit {rc}")
    cats = [a["category"] for a in out.get("assertions", [])]
    check("vis-cli-cats", cats == ["state", "token / motion", "interaction / a11y"], f"got {cats}")


# ---------------------------------------------------------------------------
# 4. Graceful degradation
# ---------------------------------------------------------------------------

NO_SPEC = """# Plan

## A PR with no spec-walk

Just prose, no checkboxes.
"""

MALFORMED_CB = """# Plan

**Spec-walk:**
- [ ] good criterion
- [] malformed no-space
- [?] malformed marker
"""


def test_empty_and_warns() -> None:
    rc, out = run_cli(CRITERIA, NO_SPEC)
    check("empty-exit", rc == 0, f"exit {rc}")
    check("empty-criteria", out.get("criteria") == [], f"got {out.get('criteria')}")
    check("empty-count", out.get("block_count") == 0, f"got {out.get('block_count')}")
    check("empty-warn", bool(out.get("warnings")), "expected a warning")

    rc2, out2 = run_cli(CRITERIA, MALFORMED_CB)
    check("malformed-exit", rc2 == 0, f"exit {rc2}")
    check("malformed-keeps-good", out2.get("criteria") == ["good criterion"], f"got {out2.get('criteria')}")
    check(
        "malformed-warns",
        any("malformed" in w for w in out2.get("warnings", [])),
        f"warnings: {out2.get('warnings')}",
    )


def test_missing_file_exits_1() -> None:
    proc = subprocess.run(
        [sys.executable, str(CRITERIA), "/nonexistent/path/plan.md"],
        capture_output=True,
        text=True,
    )
    check("missing-exit", proc.returncode == 1, f"exit {proc.returncode}")


def test_cli_backward_compat_keys() -> None:
    # The audit-coverage + verify-build consumers read .criteria and .warnings;
    # keep them present (additive-only change).
    rc, out = run_cli(CRITERIA, MULTI_BLOCK)
    check("compat-exit", rc == 0, f"exit {rc}")
    for key in ("criteria", "source_path", "source_heading", "warnings", "block_count"):
        check(f"compat-key-{key}", key in out, f"missing {key}")


# ---------------------------------------------------------------------------
# 5. Anchor co-location — the silent cross-PR grab
#
# Per-label first-block scoping is INDEPENDENT across labels, so an active PR
# that declares a Spec-walk but NO Visual-walk used to silently inherit a
# retained PR's Visual-walk block: only one Visual-walk block exists in the
# file, so `block_count == 1` and the multi-block WARN never fires. A
# backend-only PR would then be handed another PR's capture state-set (and a
# forced `visual_significant`) with zero warnings. Reported from two
# independent projects before it was fixed.
# ---------------------------------------------------------------------------

ACTIVE_WITHOUT_VISUAL = """# Plan

## PR B — active (top), backend only, declares NO Visual-walk

**Spec-walk:**
- [ ] ACTIVE: token refresh retries 3x on 401

## PR C — retained from an earlier shipped visual spike

**Spec-walk:**
- [ ] STALE: settings sheet lists all toggles

**Visual-walk:**
- [ ] [state: empty] STALE: empty settings sheet renders placeholder
"""

# Regression guard: a Visual-walk authored ABOVE its sibling Spec-walk inside
# the active section is still the active PR's — co-location is section-scoped
# (everything before the SECOND anchor heading), not "after the anchor".
VISUAL_BEFORE_SPEC = """# Plan

## PR A — active

**Visual-walk:**
- [ ] [state: empty] ACTIVE empty state renders

**Spec-walk:**
- [ ] ACTIVE criterion

## PR Z — retained

**Spec-walk:**
- [ ] STALE criterion
"""


def test_anchor_co_location() -> None:
    # THE BUG: the lone Visual-walk block belongs to a retained section.
    blk = extract_block(ACTIVE_WITHOUT_VISUAL, "Visual-walk", anchor_label="Spec-walk")
    check("coloc-empty", blk["items"] == [], f"stale items leaked: {blk['items']}")
    check("coloc-false", blk["co_located"] is False, f"got {blk['co_located']}")
    check(
        "coloc-warns",
        any("retained" in w for w in blk["warnings"]),
        f"warnings: {blk['warnings']}",
    )
    # The single-block case is exactly the one the multi-block WARN cannot see.
    check("coloc-block-count", blk["block_count"] == 1, f"got {blk['block_count']}")

    # Unanchored call keeps the legacy behavior (opt-in change, not a silent one).
    legacy = extract_block(ACTIVE_WITHOUT_VISUAL, "Visual-walk")
    check("coloc-legacy-unscoped", len(legacy["items"]) == 1, f"got {legacy['items']}")
    check("coloc-legacy-none", legacy["co_located"] is None, f"got {legacy['co_located']}")


def test_anchor_co_location_regression_guards() -> None:
    # Visual-walk above its sibling Spec-walk in the active section → still active.
    blk = extract_block(VISUAL_BEFORE_SPEC, "Visual-walk", anchor_label="Spec-walk")
    check("coloc-before-ok", blk["items"] == ["[state: empty] ACTIVE empty state renders"],
          f"got {blk['items']}")
    check("coloc-before-true", blk["co_located"] is True, f"got {blk['co_located']}")

    # Single-PR plan (<2 anchor headings) → trivially active, unchanged behavior.
    single = extract_block(MALFORMED_SPEC_WITH_VISUAL, "Visual-walk", anchor_label="Spec-walk")
    check("coloc-single-pr", len(single["items"]) == 3, f"got {single['items']}")
    check("coloc-single-true", single["co_located"] is True, f"got {single['co_located']}")

    # No anchor heading at all → co-location undefined, items still extracted.
    no_anchor = extract_block(
        "**Visual-walk:**\n- [ ] only a visual block\n", "Visual-walk", anchor_label="Spec-walk"
    )
    check("coloc-no-anchor", no_anchor["items"] == ["only a visual block"], f"got {no_anchor['items']}")
    check("coloc-no-anchor-none", no_anchor["co_located"] is None, f"got {no_anchor['co_located']}")


# KNOWN LIMITATIONS, pinned deliberately. Anchoring closes ONE of three
# degenerate shapes; these two defeat the "second anchor heading" proxy and still
# adopt a retained block silently. Both are pre-existing — anchoring did not
# introduce either and strictly improves the feature-mode shape that was actually
# reported. These tests assert the CURRENT behavior so the gaps stay visible; when
# a universal per-PR boundary marker lands, both should flip to items == [].
#
# Shape 1: the ACTIVE PR contributes no anchor (`tiny` omits Spec-walk; a
# non-visual `spike` replaces it), so anchor_idxs[0] lands in the first RETAINED
# section and a retained Visual-walk between anchors 0 and 1 reads as active.
TINY_ACTIVE_NO_SPEC = """# Plan

## PR D — active, tiny mode (no Spec-walk per plan-discipline.md)

**Mode:** tiny
**Goal:** bump the retry constant from 3 to 5.

## PR C — retained (shipped visual work)

**Spec-walk:**
- [ ] STALE: settings sheet lists all toggles

**Visual-walk:**
- [ ] [state: empty] STALE: empty settings sheet renders placeholder

## PR B — retained (older)

**Spec-walk:**
- [ ] STALE-B: older criterion
"""


# Shape 2: a RETAINED section authored Visual-walk-above-Spec-walk. That block
# precedes its own section's anchor (anchor_idxs[1]) so it falls inside the
# computed region. Indistinguishable by order alone from the legitimate active
# case VISUAL_BEFORE_SPEC pins above — which is precisely why the proxy fails.
RETAINED_VISUAL_FIRST = """# Plan

## PR B — active, backend only, NO Visual-walk

**Spec-walk:**
- [ ] ACTIVE: token refresh retries 3x on 401

## PR C — retained, authored visual-first

**Visual-walk:**
- [ ] [state: empty] STALE: settings sheet placeholder

**Spec-walk:**
- [ ] STALE: settings sheet lists toggles
"""


def test_anchor_known_limitation_tiny_mode() -> None:
    blk = extract_block(TINY_ACTIVE_NO_SPEC, "Visual-walk", anchor_label="Spec-walk")
    # Documents the gap: the active tiny PR has no anchor, so a retained block
    # still reads as co-located. Flip both assertions when the gap is closed.
    check("coloc-tiny-known-gap", len(blk["items"]) == 1,
          f"behavior changed — if this now returns [], the limitation is FIXED: "
          f"update this test + the walk_extract docstring. got {blk['items']}")
    check("coloc-tiny-known-gap-flag", blk["co_located"] is True,
          f"got {blk['co_located']}")


def test_anchor_known_limitation_retained_visual_first() -> None:
    blk = extract_block(RETAINED_VISUAL_FIRST, "Visual-walk", anchor_label="Spec-walk")
    check("coloc-retained-visual-first-gap", len(blk["items"]) == 1,
          f"behavior changed — if this now returns [], the limitation is FIXED: "
          f"update this test + the walk_extract docstring. got {blk['items']}")
    check("coloc-retained-visual-first-flag", blk["co_located"] is True,
          f"got {blk['co_located']}")


def test_anchor_co_location_cli() -> None:
    # The shipped CLI anchors by default — end-to-end, not just the unit.
    rc, out = run_cli(VISUAL, ACTIVE_WITHOUT_VISUAL)
    check("coloc-cli-exit", rc == 0, f"exit {rc}")
    check("coloc-cli-empty", out.get("assertions") == [], f"got {out.get('assertions')}")
    check("coloc-cli-flag", out.get("co_located") is False, f"got {out.get('co_located')}")
    # Spec-walk extraction is unanchored and must stay unaffected.
    rc_c, out_c = run_cli(CRITERIA, ACTIVE_WITHOUT_VISUAL)
    check("coloc-cli-spec-intact",
          out_c.get("criteria") == ["ACTIVE: token refresh retries 3x on 401"],
          f"got {out_c.get('criteria')}")


def main() -> int:
    for fn in [
        test_heading_forms,
        test_terminators,
        test_first_block_only,
        test_terminates_at_confidence,
        test_visual_decoupled,
        test_visual_category_parse,
        test_empty_and_warns,
        test_missing_file_exits_1,
        test_cli_backward_compat_keys,
        test_anchor_co_location,
        test_anchor_co_location_regression_guards,
        test_anchor_known_limitation_tiny_mode,
        test_anchor_known_limitation_retained_visual_first,
        test_anchor_co_location_cli,
    ]:
        fn()

    total = _passes + len(_failures)
    if _failures:
        print(f"FAIL — {len(_failures)}/{total} checks failed:")
        for f in _failures:
            print(f"  ✗ {f}")
        return 1
    print(f"PASS — {_passes}/{total} checks green.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
