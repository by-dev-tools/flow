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
