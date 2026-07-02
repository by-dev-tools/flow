#!/usr/bin/env python3
"""Eval harness for the statusSurfaceCandidates discovery mechanism (FB-0064).

Pins the load-bearing behaviors of `skills/ship/lib/status-surface-scan.py` (the
helper that /flow:ship Step 5a.5 + doctor Check 2.9 call to DISCOVER undeclared
status surfaces) plus the SKILL/doctor/schema/example contract. Assertion-based
(stdout substring + exit-code), stdlib only.

Run: python3 plugins/flow/evals/run_status_surface_evals.py

The three scenario fixtures the task calls for are the mechanical half of a
best-effort-LLM feature — the drift *judgment* is the agent's (Step 5a.5), the
same way /flow:audit-coverage's judgment isn't unit-tested. So each fixture pins
what is mechanically assertable — that the scan surfaces the right candidates and
the right verbatim slice for the judge — and the drift decision itself is pinned
by the SKILL's false-positive-discipline prose (checked in the contract section):

  positive (dogfood) — an UNDECLARED CLAUDE.md reading "3c is next (not started)"
      is scanned AND its slice carries the verbatim stale line the judge quotes.
  negative           — the SAME CLAUDE.md, DECLARED in statusDocs, is excluded
      from candidates (Tier 2 — reconciled by Step 5a, never re-discovered).
  false-positive     — a CLAUDE.md that mentions "Phase 3c" but makes NO stale
      "next / not started" claim is still scanned (it's undeclared), and its
      slice contains "Phase 3c" but none of the stale forward-looking phrasing,
      so the judge has nothing to quote → no flag.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).parent
LIB = HERE.parent / "skills" / "ship" / "lib"
SCRIPT = LIB / "status-surface-scan.py"
SHIP_SKILL = HERE.parent / "skills" / "ship" / "SKILL.md"
DOCTOR_SKILL = HERE.parent / "skills" / "doctor" / "SKILL.md"
SCHEMA = HERE.parent / "schema" / "flow.config.schema.json"
CONFIG_EXAMPLE = (HERE.parent.parent.parent / "template" / "base"
                  / "flow.config.json.example")

fails = 0


def check(cid, ok, detail=""):
    global fails
    if ok:
        print(f"PASS  [{cid}]")
    else:
        fails += 1
        print(f"FAIL  [{cid}]" + (f"  — {detail}" if detail else ""))


def run(args, cwd=None, stdin=None):
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        input=stdin, capture_output=True, text=True, check=False, cwd=cwd,
    )
    return proc.returncode, proc.stdout, proc.stderr


def write(p: Path, text: str):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)
    return p


# The dogfood: a CLAUDE.md whose status paragraph describes just-shipped 3c₁ as
# upcoming — the exact drift a separate hand PR (#53) had to fix.
STALE_CLAUDE = (
    "# my-app\n\nA local-first notes app.\n\n"
    "## Current status\n\n"
    "Phase 3 underway. Sub-PR 3c is next (not started); 3b merged last week.\n"
    "▶ Next up: land 3c, then start phase 4.\n\n"
    "## Architecture\n\nStuff that is not status.\n"
)

# Same file but with no stale forward-looking claim — mentions the phase as
# historical context only. The keyword "Phase" is present (so it's sliced), but
# nothing says it is "next / not started", so the judge has nothing to quote.
NEUTRAL_CLAUDE = (
    "# my-app\n\nA local-first notes app.\n\n"
    "## Architecture\n\n"
    "The Phase 3c indexer lives in src/index.ts; it was rewritten in the 3c work.\n"
    "See history.md for the rationale.\n"
)


def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)

        # === positive (dogfood): undeclared CLAUDE.md w/ stale status ==========
        write(d / "CLAUDE.md", STALE_CLAUDE)
        cfg_default = write(d / "flow.config.json", json.dumps({}))  # default list
        rc, out, _ = run(["candidates", "flow.config.json"], cwd=str(d))
        check("pos-1-candidate-listed",
              rc == 0 and "CLAUDE.md" in out.splitlines(),
              f"rc={rc} out={out!r}")
        rc, out, _ = run(["scan", "flow.config.json"], cwd=str(d))
        check("pos-2-scan-header",
              rc == 0 and "1 undeclared candidate(s) present: CLAUDE.md" in out,
              f"out={out!r}")
        check("pos-3-verbatim-quote-in-slice",
              "3c is next (not started)" in out,
              "slice must carry the verbatim stale line for the judge to quote")
        check("pos-4-glyph-line-sliced", "▶ Next up: land 3c" in out)

        # === negative: DECLARED + fenced → excluded from candidates ============
        cfg_declared = write(d / "declared.json", json.dumps({
            "statusDocs": [{"path": "CLAUDE.md", "marker": "flow:status"}],
        }))
        rc, out, _ = run(["candidates", "declared.json"], cwd=str(d))
        check("neg-1-declared-excluded",
              rc == 0 and "CLAUDE.md" not in out.splitlines(),
              f"a declared surface is Tier 2, never re-discovered; out={out!r}")
        rc, out, _ = run(["scan", "declared.json"], cwd=str(d))
        check("neg-2-scan-skips-declared",
              rc == 0 and "0 undeclared candidate(s)" in out,
              f"out={out!r}")

        # === false-positive: undeclared, mentions phase, no stale claim ========
        with tempfile.TemporaryDirectory() as td2:
            d2 = Path(td2)
            write(d2 / "CLAUDE.md", NEUTRAL_CLAUDE)
            write(d2 / "flow.config.json", json.dumps({}))
            rc, out, _ = run(["scan", "flow.config.json"], cwd=str(d2))
            check("fp-1-still-scanned",
                  rc == 0 and "CLAUDE.md" in out,
                  "an undeclared file is scanned regardless — the JUDGE filters it")
            check("fp-2-phase-mention-present", "Phase 3c" in out)
            check("fp-3-no-stale-phrasing",
                  "is next" not in out and "not started" not in out,
                  "the slice must carry no forward-looking stale phrasing to quote")

        # === candidate resolution: default list, existing-only, undeclared =====
        # Only CLAUDE.md exists in `d`; the other defaults (AGENTS.md, README.md…)
        # do not → candidates must be exactly [CLAUDE.md].
        rc, out, _ = run(["candidates", "flow.config.json"], cwd=str(d))
        check("cand-1-existing-only",
              out.splitlines() == ["CLAUDE.md"],
              f"only existing candidates returned; out={out!r}")
        # Add README.md (also a default) → both surface, in list order.
        write(d / "README.md", "# readme\n\n## Status\nphase 3 now\n")
        rc, out, _ = run(["candidates", "flow.config.json"], cwd=str(d))
        check("cand-2-order",
              out.splitlines() == ["CLAUDE.md", "README.md"],
              f"default-list order preserved; out={out!r}")
        # Override list narrows discovery.
        cfg_override = write(d / "override.json",
                             json.dumps({"statusSurfaceCandidates": ["README.md"]}))
        rc, out, _ = run(["candidates", "override.json"], cwd=str(d))
        check("cand-3-override",
              out.splitlines() == ["README.md"], f"out={out!r}")
        # Empty override → opt out of discovery entirely.
        cfg_optout = write(d / "optout.json",
                           json.dumps({"statusSurfaceCandidates": []}))
        rc, out, _ = run(["candidates", "optout.json"], cwd=str(d))
        check("cand-4-optout-empty", rc == 0 and out.strip() == "")

        # === slice: bounded window + line numbers =============================
        rc, out, _ = run(["slice", "CLAUDE.md"], cwd=str(d))
        import re as _re
        numbered = [l for l in out.splitlines()
                    if l and not l.startswith("…")]
        check("slice-1-line-numbered",
              rc == 0 and numbered
              and all(_re.match(r"^\d+: ", l) for l in numbered),
              f"every slice line must carry an <n>: prefix; out={out!r}")
        # Non-status file → empty slice (no keyword/glyph anywhere).
        write(d / "plain.md", "# just a title\n\nJust prose about apples and oranges.\n")
        rc, out, _ = run(["slice", "plain.md"], cwd=str(d))
        check("slice-2-non-status-empty", rc == 0 and out.strip() == "")

        # === malformed config → loud, never silent ============================
        bad_json = write(d / "bad.json", "{not json")
        rc, _, err = run(["candidates", "bad.json"], cwd=str(d))
        check("mal-1-bad-json", rc == 1 and "status-surface" in err)
        non_array = write(d / "nonarray.json",
                          json.dumps({"statusSurfaceCandidates": "CLAUDE.md"}))
        rc, _, err = run(["candidates", "nonarray.json"], cwd=str(d))
        check("mal-2-non-array", rc == 1 and "array" in err)
        bad_entry = write(d / "badentry.json",
                          json.dumps({"statusSurfaceCandidates": ["", 3]}))
        rc, _, err = run(["candidates", "badentry.json"], cwd=str(d))
        check("mal-3-bad-entry", rc == 1 and "non-empty string" in err)
        # A malformed statusDocs (used to compute the exclusion set) is also loud.
        bad_sd = write(d / "badsd.json",
                       json.dumps({"statusDocs": {"path": "x"}}))
        rc, _, err = run(["candidates", "badsd.json"], cwd=str(d))
        check("mal-4-bad-statusdocs", rc == 1 and "array" in err)

    # === schema slot ==========================================================
    schema = json.loads(SCHEMA.read_text())
    slot = schema["properties"].get("statusSurfaceCandidates", {})
    schema_default = slot.get("default")
    check("slot-1-present",
          slot.get("type") == "array" and isinstance(schema_default, list)
          and "CLAUDE.md" in (schema_default or []),
          f"statusSurfaceCandidates must be an array w/ CLAUDE.md default; got {slot!r}")

    # === default-list parity: helper DEFAULT_CANDIDATES == schema default =====
    # FB-0010 fan-out: the two lists must not drift. Import the helper by path.
    import importlib.util
    spec = importlib.util.spec_from_file_location("sss", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    check("slot-2-default-parity",
          mod.DEFAULT_CANDIDATES == schema_default,
          f"helper {mod.DEFAULT_CANDIDATES} != schema {schema_default}")

    # === ship SKILL Step 5a.5 contract ========================================
    skill = SHIP_SKILL.read_text()
    ship = {
        "5a.5-present": "5a.5" in skill and "status-surface" in skill,
        "status-moved-gate": "STATUS_MOVED" in skill
                             and "status unchanged this ship" in skill,
        "helper-call": "status-surface-scan.py" in skill,
        "draft-route": "[status-surface]" in skill
                       and ("draft-manifest" in skill.lower()
                            or "draft manifest" in skill.lower()),
        "verbatim-discipline": "verbatim" in skill.lower()
                               and "can't quote" in skill.lower(),
        "no-silent-edit": "never" in skill.lower()
                          and "silently rewrite" in skill.lower(),
        "skip-line": "none drifted" in skill,
        "manifest-tag": "status-surface>" in skill or "|status-surface]" in skill,
        "flow-run-row": "Status surface (§5a.5)" in skill,
    }
    for k, ok in ship.items():
        check(f"ship-{k}", ok)

    # === doctor Check 2.9 contract ============================================
    doctor = DOCTOR_SKILL.read_text()
    check("doctor-1-check-2.9", "2.9" in doctor and "statusSurfaceCandidates" in doctor)
    check("doctor-2-helper-call", "status-surface-scan.py" in doctor)
    check("doctor-3-warn-only",
          "[WARN]" in doctor and "Warn-only" in doctor)

    # === config example: seeded statusDocs + candidate comment ================
    if CONFIG_EXAMPLE.is_file():
        ex = CONFIG_EXAMPLE.read_text()
        check("example-1-seeded-claude",
              '"path": "CLAUDE.md"' in ex and '"statusDocs"' in ex,
              "scaffolded config should seed CLAUDE.md into statusDocs (Tier 2 default)")
        check("example-2-candidate-comment",
              "statusSurfaceCandidates" in ex)
    else:
        check("example-1-seeded-claude", False, f"missing {CONFIG_EXAMPLE}")

    total_marker = "passed" if fails == 0 else "FAILED"
    print(f"\n{total_marker}: {fails} failing check(s)")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
