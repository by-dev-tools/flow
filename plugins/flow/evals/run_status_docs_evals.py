#!/usr/bin/env python3
"""Eval harness for the statusDocs doc-currency mechanism (FB-0054).

Pins the load-bearing behaviors of `skills/ship/lib/status-docs.py` (the shared
helper that Step 5b + doctor Check 2.7 call) plus the SKILL/doctor/schema
contract. Assertion-based (stdout substring + exit-code), stdlib only.

Run: python3 plugins/flow/evals/run_status_docs_evals.py

What it covers:
  entries 1 — parse a 2-entry statusDocs, default marker applied to the
              marker-less entry.
  entries 2 — empty/absent statusDocs → no output, exit 0 (backward-compat).
  entries 3 — malformed JSON / non-array statusDocs / entry missing path →
              loud stderr + exit 1 (never a silent skip).
  region  1 — extract the fenced region (file + stdin parity).
  region  2 — missing open OR close fence → exit 2.
  check   1 — all-fenced → exit 0; missing file / unfenced → exit 1 with the
              right per-entry line.
  changed 1 — region text differs vs a base revision (the 5b "did you reconcile"
              signal); identical region → no diff.
  ship    1 — Step 5a reconcile loop + Step 5b marker-coverage gate contract
              present in ship/SKILL.md (manifest-independent, blocks on
              un-touched region, empty-skip).
  doctor  1 — Check 2.7 present in doctor/SKILL.md and calls the helper.
  slot    1 — statusDocs in the schema (array, default []).
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).parent
LIB = HERE.parent / "skills" / "ship" / "lib"
SCRIPT = LIB / "status-docs.py"
SHIP_SKILL = HERE.parent / "skills" / "ship" / "SKILL.md"
DOCTOR_SKILL = HERE.parent / "skills" / "doctor" / "SKILL.md"
SCHEMA = HERE.parent / "schema" / "flow.config.schema.json"

fails = 0


def check(cid, ok, detail=""):
    global fails
    if ok:
        print(f"PASS  [{cid}]")
    else:
        fails += 1
        print(f"FAIL  [{cid}]" + (f"  — {detail}" if detail else ""))


def run(args, stdin=None, cwd=None):
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        input=stdin, capture_output=True, text=True, check=False, cwd=cwd,
    )
    return proc.returncode, proc.stdout, proc.stderr


def write(p: Path, text: str):
    p.write_text(text)
    return p


FENCED = (
    "# Project\nintro\n"
    "<!-- flow:status -->\n"
    "Phase 2 — sub-PRs 1-2 merged; HealthKit next.\n"
    "<!-- /flow:status -->\n"
    "tail\n"
)


def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)

        # --- entries 1: two entries, default marker on the marker-less one -----
        cfg2 = write(d / "two.json", json.dumps({"statusDocs": [
            {"path": "CLAUDE.md", "marker": "flow:status"},
            {"path": "README.md"},
        ]}))
        rc, out, _ = run(["entries", str(cfg2)])
        lines = out.strip().splitlines()
        check("entries-1-parse", rc == 0 and lines == [
            "flow:status\tCLAUDE.md", "flow:status\tREADME.md"],
            f"rc={rc} out={lines!r}")

        # --- entries 2: empty / absent → no output, exit 0 --------------------
        cfg_empty = write(d / "empty.json", json.dumps({}))
        rc, out, _ = run(["entries", str(cfg_empty)])
        check("entries-2-empty", rc == 0 and out.strip() == "",
              f"rc={rc} out={out!r}")
        cfg_explicit = write(d / "explicit-empty.json",
                             json.dumps({"statusDocs": []}))
        rc, out, _ = run(["entries", str(cfg_explicit)])
        check("entries-2-explicit-empty", rc == 0 and out.strip() == "")

        # --- entries 3: malformed → loud fail, never silent -------------------
        bad_json = write(d / "bad.json", "{not json")
        rc, _, err = run(["entries", str(bad_json)])
        check("entries-3-malformed-json", rc == 1 and "status-docs" in err)
        non_array = write(d / "nonarray.json",
                          json.dumps({"statusDocs": {"path": "x"}}))
        rc, _, err = run(["entries", str(non_array)])
        check("entries-3-non-array", rc == 1 and "array" in err)
        no_path = write(d / "nopath.json",
                       json.dumps({"statusDocs": [{"marker": "m"}]}))
        rc, _, err = run(["entries", str(no_path)])
        check("entries-3-missing-path", rc == 1 and "path" in err)

        # --- region 1: extract, file + stdin parity ---------------------------
        cm = write(d / "CLAUDE.md", FENCED)
        rc, out_file, _ = run(["region", "flow:status", str(cm)])
        rc2, out_stdin, _ = run(["region", "flow:status", "-"], stdin=FENCED)
        expect = "Phase 2 — sub-PRs 1-2 merged; HealthKit next.\n"
        check("region-1-extract", rc == 0 and out_file == expect,
              f"rc={rc} out={out_file!r}")
        check("region-1-stdin-parity", rc2 == 0 and out_stdin == out_file)

        # --- region 2: missing fence → exit 2 ---------------------------------
        nofence = write(d / "nofence.md", "no fences here\n")
        rc, _, err = run(["region", "flow:status", str(nofence)])
        check("region-2-missing-both", rc == 2 and "not found" in err)
        open_only = write(d / "openonly.md",
                         "<!-- flow:status -->\nunterminated\n")
        rc, _, _ = run(["region", "flow:status", str(open_only)])
        check("region-2-missing-close", rc == 2)

        # --- section: extract under a heading up to the next "## " ------------
        doc = ("# Plan\n\n## Current Focus\n\nPhase 2 underway.\nLine two.\n"
               "\n## Handoff Notes\n\nstuff\n")
        _, sec, _ = run(["section", "## Current Focus", "-"], stdin=doc)
        check("section-extract",
              sec == "\nPhase 2 underway.\nLine two.\n",
              f"sec={sec!r}")
        _, absent, _ = run(["section", "## Nonexistent", "-"], stdin=doc)
        check("section-absent-empty", absent == "")
        # The section diff is what drives STATUS_MOVED in 5b:
        moved_doc = doc.replace("Phase 2 underway", "Phase 3 underway")
        _, sec_a, _ = run(["section", "## Current Focus", "-"], stdin=doc)
        _, sec_b, _ = run(["section", "## Current Focus", "-"], stdin=moved_doc)
        check("section-moved-differs", sec_a != sec_b)

        # --- check 1: OK / MISSING-FILE / MISSING-MARKER ----------------------
        # cfg2 declares CLAUDE.md (fenced, present) + README.md (absent). Run
        # with cwd=d so the relative paths resolve.
        rc, out, _ = run(["check", "two.json"], cwd=str(d))
        check("check-1-mixed",
              rc == 1 and "OK CLAUDE.md" in out and "MISSING-FILE README.md" in out,
              f"rc={rc} out={out!r}")
        # README present but unfenced → MISSING-MARKER.
        write(d / "README.md", "# readme, no status fence\n")
        rc, out, _ = run(["check", "two.json"], cwd=str(d))
        check("check-1-unfenced",
              rc == 1 and "MISSING-MARKER README.md (flow:status)" in out)
        # Both fenced → exit 0.
        write(d / "README.md", FENCED)
        rc, out, _ = run(["check", "two.json"], cwd=str(d))
        check("check-1-all-ok", rc == 0 and "MISSING" not in out, f"out={out!r}")
        # No statusDocs declared → clean PASS.
        rc, out, _ = run(["check", str(cfg_empty)])
        check("check-1-none", rc == 0 and "no statusDocs declared" in out)

        # --- changed 1: region differs vs a base revision ---------------------
        # This is the comparison the 5b gate performs (base vs working region).
        base = FENCED
        moved = FENCED.replace("HealthKit next", "HealthKit shipped; Sleep next")
        _, base_region, _ = run(["region", "flow:status", "-"], stdin=base)
        _, moved_region, _ = run(["region", "flow:status", "-"], stdin=moved)
        check("changed-1-differs", base_region != moved_region)
        _, same_region, _ = run(["region", "flow:status", "-"], stdin=base)
        check("changed-1-identical", base_region == same_region)

    # --- ship 1: Step 5a + 5b contract in ship/SKILL.md -----------------------
    skill = SHIP_SKILL.read_text()
    ship = {
        "5a-loop": "statusDocs" in skill and "reconcile" in skill.lower(),
        "5b-marker-coverage": "marker-coverage" in skill
                              or "marker region" in skill.lower(),
        "5b-manifest-independent": "no versioned manifest" in skill
                                   or "version-manifest-independent" in skill
                                   or "independent of a version manifest" in skill.lower(),
        "helper-call": "status-docs.py" in skill,
        "empty-skip": "statusDocs" in skill and "none declared" in skill.lower()
                      or "no statusDocs" in skill.lower(),
    }
    for k, ok in ship.items():
        check(f"ship-1-{k}", ok)

    # --- doctor 1: Check 2.7 present + calls helper ---------------------------
    doctor = DOCTOR_SKILL.read_text()
    check("doctor-1-check-2.7", "2.7" in doctor and "statusDocs" in doctor)
    check("doctor-1-helper-call", "status-docs.py" in doctor)

    # --- slot 1: statusDocs in the schema -------------------------------------
    try:
        schema = json.loads(SCHEMA.read_text())
        slot = schema["properties"].get("statusDocs", {})
        check("slot-1-present",
              slot.get("type") == "array" and slot.get("default") == [],
              "statusDocs must be an array with default []")
    except (OSError, ValueError, KeyError) as e:
        check("slot-1-present", False, str(e))

    total_marker = "passed" if fails == 0 else "FAILED"
    print(f"\n{total_marker}: {fails} failing check(s)")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
