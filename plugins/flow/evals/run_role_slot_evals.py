#!/usr/bin/env python3
"""Eval harness for the `role` config slot (D1 Phase 0, FB-0081).

Pins the shape of the Phase-0 slice of the D1 "prototype-first gate" track
(`dev-docs/handoffs/d1-prototype-first-gate.md` § Phase 0): an optional `role`
enum in `flow.config.schema.json`, a `/flow:doctor` check that reports its
resolved value, and `workflow.md` documentation of the slot. This PR wires NO
trigger and NO behavior change — later D1 phases are the consumer. What this
harness pins is narrower and mechanical:

  shape     — the schema property is a string enum of exactly
              ["designer", "engineer"], with no "default" key (unset must
              stay a distinct, valid state from either enum value, not
              silently coerced to one role).
  roundtrip — a REAL flow.config.json file on disk with role unset /
              "designer" / "engineer" round-trips through json.load unchanged
              and, when present, is a member of the schema's own (live-read)
              enum; an out-of-enum value round-trips too but is detected as
              NOT a member — the same distinction doctor's check must make.
  doctor    — Check 2.11 exists, reads `.role`, and reports all three states
              (unset / designer / engineer) plus a WARN (not a silent PASS)
              for an unrecognized value. Check 2.11's own jq-absence SKIP
              behavior is exercised live (not just grepped) by
              `run_jq_guard_evals.py`, which this harness does not duplicate.
  docs      — workflow.md documents the `role` slot and states it is not yet
              consumed by any skill. The cross-file "N slots" literal
              consistency (workflow.md, doctor's frontmatter,
              template/base/CLAUDE.md.template) is NOT re-checked here — that
              is already the job of `run_merge_status_evals.py`'s
              `schema-slot-count-N` + `no-stale-slot-count-in-shipped-surfaces`
              tripwire, which scans `plugins/` + `template/` for any "N slots"
              literal that disagrees with the live schema count. Duplicating
              that sweep here would be a second, weaker implementation of the
              same FB-0010 fan-out check that could silently drift from it.

Stdlib only. Run:
    python3 plugins/flow/evals/run_role_slot_evals.py
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from eval_utils import fenced_block, rest_from as _rest_from  # noqa: F401 (fenced_block used below)

HERE = Path(__file__).parent
SCHEMA = HERE.parent / "schema" / "flow.config.schema.json"
DOCTOR_SKILL = HERE.parent / "skills" / "doctor" / "SKILL.md"
WORKFLOW_DOC = HERE.parent / "docs" / "workflow.md"

fails = 0


def section_after(text, heading_substr):
    """The text from `heading_substr` up to (not including) the next '**Check' or
    '### ' heading — scopes a check to Check 2.11's own block rather than the
    whole SKILL.md, so an unrelated mention elsewhere in the file can't make a
    check pass vacuously (staff-review NIT)."""
    rest = _rest_from(text, heading_substr)
    if rest is None:
        return None
    m = re.search(r"\n(?:\*\*Check |### )", rest[1:])
    return rest[:m.start() + 1] if m else rest


def check(cid, ok, detail=""):
    global fails
    if ok:
        print(f"PASS  [{cid}]")
    else:
        fails += 1
        print(f"FAIL  [{cid}]" + (f" — {detail}" if detail else ""))


def main():
    # --- shape: the schema property itself ------------------------------------
    try:
        schema = json.loads(SCHEMA.read_text())
    except (OSError, ValueError) as e:
        check("shape-1-schema-parses", False, str(e))
        print(f"\nFAILED: {fails} failing check(s)")
        return 1
    check("shape-1-schema-parses", True)

    role_slot = schema.get("properties", {}).get("role")
    check("shape-2-slot-present", role_slot is not None,
          "flow.config.schema.json has no 'role' property")

    if role_slot is None:
        print(f"\nFAILED: {fails} failing check(s)")
        return 1

    check("shape-3-type-string", role_slot.get("type") == "string",
          f"expected type 'string', got {role_slot.get('type')!r}")
    check("shape-4-enum-exact",
          role_slot.get("enum") == ["designer", "engineer"],
          f"expected enum ['designer', 'engineer'], got {role_slot.get('enum')!r}")
    check("shape-5-no-default", "default" not in role_slot,
          "role must have no 'default' key — unset must stay distinct "
          "from either enum value, not silently coerced to one")

    live_enum = role_slot.get("enum", [])

    # --- roundtrip: real files on disk, checked against the SCHEMA's own enum -
    with tempfile.TemporaryDirectory() as td:
        cfg_path = Path(td) / "flow.config.json"
        for value in (None, "designer", "engineer", "product-manager"):
            cfg = {"defaultBranch": "main"}
            if value is not None:
                cfg["role"] = value
            cfg_path.write_text(json.dumps(cfg))
            resolved = json.loads(cfg_path.read_text()).get("role")

            label = value or "unset"
            check(f"roundtrip-1-{label}", resolved == value,
                  f"expected {value!r} back from disk, got {resolved!r}")

            is_valid = resolved is None or resolved in live_enum
            expect_valid = value != "product-manager"
            check(f"roundtrip-2-{label}-enum-membership", is_valid == expect_valid,
                  f"{resolved!r} membership in schema enum {live_enum} "
                  f"was {is_valid}, expected {expect_valid}")

    # --- doctor: the new check exists and covers all states -------------------
    # Scoped to Check 2.11's own block (section_after), not the whole SKILL.md —
    # an unrelated "2.11" or "designer"/"engineer" mention elsewhere in the file
    # must not make these pass vacuously if Check 2.11 itself regresses.
    doctor_full = DOCTOR_SKILL.read_text()
    doctor = section_after(doctor_full, "Check 2.11 —")
    check("doctor-1-check-present", doctor is not None,
          "Check 2.11 not found in doctor/SKILL.md")
    doctor = doctor or ""
    check("doctor-2-reads-role-slot", ".role // empty" in doctor)
    check("doctor-3-unset-message",
          "classic plan gate" in doctor.lower())
    check("doctor-4-designer-engineer-states",
          "designer|engineer" in doctor or ("designer" in doctor and "engineer" in doctor))
    check("doctor-5-warn-on-invalid",
          "[WARN] role:" in doctor,
          "an out-of-enum role value must WARN, not silently PASS")

    # --- security: a shell-metacharacter-laden role value must never execute --
    # (flow:security-review NIT on the D1 Phase 0 PR): this ACTUALLY RUNS the
    # extracted Check 2.11 shell block (not a grep) against a crafted
    # flow.config.json whose role value contains a command-substitution
    # payload, and asserts the payload never executed. Note what this does
    # and does NOT prove (staff-review correction): `$ROLE` is captured once
    # via command substitution and never re-parsed for shell metacharacters
    # afterward, so this stays inert whether or not `$ROLE`'s later uses are
    # quoted — POSIX shells only re-interpret a variable's contents as code
    # via `eval` or an equivalent re-invocation, neither of which Check 2.11
    # does. This test proves that invariant holds *today*; it would only go
    # red if a future edit introduced `eval`/`sh -c "$ROLE"` or similar, not
    # from merely dropping a quote around an existing `$ROLE` use.
    block = fenced_block(doctor_full, "Check 2.11 —")
    check("security-1-block-extractable", block is not None,
          "could not extract Check 2.11's executable shell block")
    if block:
        with tempfile.TemporaryDirectory() as td:
            canary = Path(td) / "pwned"
            payload = f'$(touch {canary})'
            cfg_path = Path(td) / "flow.config.json"
            cfg_path.write_text(json.dumps({"role": payload}))
            try:
                proc = subprocess.run(["sh", "-c", block], cwd=td,
                                       capture_output=True, text=True, timeout=10)
                stdout = proc.stdout
            except subprocess.TimeoutExpired:
                check("security-2-no-command-injection", False,
                      "Check 2.11's shell block did not terminate within 10s")
                check("security-3-value-echoed-inert", False, "block timed out")
                stdout = None
            if stdout is not None:
                check("security-2-no-command-injection", not canary.exists(),
                      "the canary file was created — $ROLE's command-substitution "
                      "payload EXECUTED (Check 2.11 must not pipe $ROLE through "
                      "eval or an equivalent re-invocation)")
                check("security-3-value-echoed-inert", payload in stdout,
                      f"expected the payload to be echoed verbatim (inert) in "
                      f"stdout, got: {stdout!r}")

    # --- docs: workflow.md documents the slot ----------------------------------
    workflow = WORKFLOW_DOC.read_text()
    check("docs-1-slot-documented", "`role`" in workflow and "designer" in workflow
          and "engineer" in workflow)
    check("docs-2-no-active-consumer-disclaimer",
          "no skill reads" in workflow.lower() or "not yet consumed" in workflow.lower(),
          "workflow.md must not imply the D1 trigger is already wired")

    total_marker = "passed" if fails == 0 else "FAILED"
    print(f"\n{total_marker}: {fails} failing check(s)")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
