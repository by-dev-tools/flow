#!/usr/bin/env python3
"""Eval harness for /flow:verify-build's frame-integrity pass (FB-0066).

The frame-integrity VERDICT itself is VLM judgment (a cold judge reading captured frames
against lib/frame-integrity-checklist.md) and can't run deterministically in CI. So this
harness pins the two deterministic surfaces that make that judgment gate-blocking and
visible, plus the spec-conformance of the fixed checklist:

  render  — a buffer whose frame_integrity[] carries a FAIL entry (the known-bad frame:
            white safe-area band / broken background) renders a visible "Frame integrity"
            section with the FAIL verdict, its failing checklist items, and the described
            per-edge evidence. A clean buffer (known-good frame) renders PASS and NO
            "Failing checks:" block. This is the acceptance's "bad ⇒ FAIL, clean ⇒ PASS"
            pinned against real code-under-test (render-report.py).
  checklist — the fixed must-pass checklist ships all six items, the FAIL-not-Unknown
              verdict rule, and the describe-edges-before-verdict discipline.
  wiring    — rubric.md + SKILL.md + the schema actually reference the frame-integrity
              pass (a dangling checklist nobody spawns is a silent no-op — FB-0010).
  schema    — the schema declares the top-level frame_integrity array, and the canonical
              findings-example.json carries a valid frame_integrity entry.

Renders to a temp file, reads the HTML back, asserts substrings. Stdlib only.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).parent
LIB = HERE.parent / "skills" / "verify-build" / "lib"
RENDER = LIB / "render-report.py"
CHECKLIST = LIB / "frame-integrity-checklist.md"
RUBRIC = LIB / "rubric.md"
SCHEMA = LIB / "findings-schema.json"
EXAMPLE = LIB / "findings-example.json"
SKILL = HERE.parent / "skills" / "verify-build" / "SKILL.md"
FIX = HERE / "fixtures" / "frame-integrity"


def render(buffer: Path) -> str:
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "report.html"
        proc = subprocess.run(
            [sys.executable, str(RENDER), str(buffer), "--out", str(out),
             "--assets-dir", str(buffer.parent)],
            capture_output=True, text=True, check=False,
        )
        if proc.returncode != 0:
            return f"<<non-zero exit {proc.returncode}>>\n{proc.stderr}"
        return out.read_text(encoding="utf-8")


def main() -> int:
    fails = 0
    total = 0

    def check(label, cond, detail=""):
        nonlocal fails, total
        total += 1
        if cond:
            print(f"PASS  [{label}]")
        else:
            fails += 1
            print(f"FAIL  [{label}] {detail}")

    # --- render: known-bad frame ⇒ visible FAIL with failing items + described edges ---
    bad = render(FIX / "badframe.json")
    check("render-bad-has-section", "Frame integrity" in bad, "no Frame integrity section")
    check("render-bad-verdict-fail", ">FAIL<" in bad, "no FAIL verdict rendered")
    check("render-bad-failing-checks", "Failing checks:" in bad, "no failing-checks block")
    check("render-bad-band-item", "white/black/wrong-gradient band" in bad,
          "the failing checklist item text is not surfaced")
    check("render-bad-edge-evidence", "flat white" in bad,
          "the described per-edge evidence is not surfaced")

    # --- render: known-good frame ⇒ PASS, no failing-checks block ---
    clean = render(FIX / "cleanframe.json")
    check("render-clean-has-section", "Frame integrity" in clean, "no Frame integrity section")
    check("render-clean-verdict-pass", ">PASS<" in clean, "no PASS verdict rendered")
    check("render-clean-no-fails", "Failing checks:" not in clean,
          "clean frame wrongly rendered a failing-checks block")

    # --- checklist spec-conformance: all six items + rules present ---
    cl = CHECKLIST.read_text(encoding="utf-8")
    item_markers = [
        "Edge-to-edge background", "No seam", "No clipped text", "No collisions",
        "Palette fidelity", "Safe-area respect",
    ]
    missing_items = [m for m in item_markers if m not in cl]
    check("checklist-six-items", not missing_items, f"missing: {missing_items}")
    check("checklist-fail-not-unknown",
          "Any failing item ⇒ `FAIL`" in cl and "never Unknown" in cl.replace("`", ""),
          "the FAIL-not-Unknown verdict rule is not stated")
    check("checklist-describe-first",
          "anti-glance" in cl.lower() and "before" in cl.lower(),
          "the describe-before-verdict discipline is not stated")

    # --- wiring: the pass is actually referenced by rubric + skill + schema ---
    rubric = RUBRIC.read_text(encoding="utf-8")
    check("wiring-rubric", "Frame-integrity pre-pass" in rubric,
          "rubric.md VLM section does not describe the frame-integrity pre-pass")
    skill = SKILL.read_text(encoding="utf-8")
    check("wiring-skill-pass", "frame-integrity` pass" in skill or "frame-integrity pass" in skill,
          "SKILL.md §6 does not spawn the frame-integrity pass")
    check("wiring-skill-aggregation", "frame_integrity[] entry returns FAIL" in skill,
          "SKILL.md §7 does not aggregate a frame-integrity FAIL to gate-blocking")
    check("wiring-skill-buffer", "frame_integrity[]`**" in skill,
          "SKILL.md §8 does not document the frame_integrity buffer field")

    # --- schema + canonical example ---
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    fi = schema.get("properties", {}).get("frame_integrity", {})
    check("schema-declares-array", fi.get("type") == "array", "frame_integrity not an array property")
    req = set((fi.get("items") or {}).get("required") or [])
    check("schema-requires-evidence",
          {"frame", "edges", "corners", "background_continuity", "verdict"} <= req,
          f"item required set is {sorted(req)}")
    check("schema-version-unbumped", schema.get("properties", {}).get("schema_version", {}).get("const") == "1.0",
          "frame_integrity is additive — schema_version must stay 1.0")

    example = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    ex_fi = example.get("frame_integrity") or []
    check("example-carries-entry",
          len(ex_fi) >= 1 and ex_fi[0].get("verdict") == "PASS"
          and ex_fi[0].get("edges", {}).get("top"),
          "findings-example.json does not carry a valid frame_integrity entry")

    print(f"\n{total - fails} passed, {fails} failed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
