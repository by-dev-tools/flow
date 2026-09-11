#!/usr/bin/env python3
"""
Regression eval for the criterion-specificity heuristic (criterion-specificity.py).

Pins the deterministic contract /flow:verify-build Step 3 and /flow:ship
Step 2 depend on:

  1. Mixed fixture — flags EXACTLY the criteria with no observable predicate
     (a generic success verb, optionally a generic adverb, at the very end of
     the string) that ALSO carry no concrete-signal escape (a quoted/backticked
     literal, a digit, a pin-marker arrow, or a named-observable verb/noun).
  2. The AND-NOT branch is exercised, not just the vacuous-predicate branch in
     isolation: "Returns a session token and works correctly" DOES match the
     trailing vacuous-predicate pattern, and is correctly unflagged ONLY
     because the concrete-signal escape hatch also fires elsewhere in the
     string. The other four "not flagged" fixture cases never reach that
     branch at all (the predicate regex never matches them), so this is the
     one case that actually tests the mechanism the precision claim rests on
     — asserted explicitly, not just absent-by-omission from the flagged set.
  3. Empty criteria list -> 0 vacuous, exit 0, no crash.
  4. Malformed JSON / wrong shape -> loud stderr + exit 1 (crash-grade, not a
     lint verdict).
  5. Usage error (too many args) -> exit 2.

The lint is advisory for a clean result: exit code 0 covers both "0 vacuous"
and "N vacuous" (mirrors walk-pin-lint.py's exit-0-always contract for lint
verdicts); only crash-grade input errors are nonzero.

Stdlib only. No network, no third-party deps. Run:
    python3 plugins/flow/evals/run_criterion_specificity_evals.py
Exits non-zero on any failure (CI gate).
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIXTURES = HERE / "fixtures" / "criterion-specificity"
SCRIPT = HERE.parent / "skills" / "verify-build" / "lib" / "criterion-specificity.py"

_failures: list[str] = []
_passes = 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global _passes
    if cond:
        _passes += 1
    else:
        _failures.append(f"{name}: {detail}")


def run(args: list[str] | None = None, stdin: str | None = None) -> tuple[int, str, str]:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), *(args or [])],
        input=stdin,
        capture_output=True,
        text=True,
    )
    return proc.returncode, proc.stdout, proc.stderr


EXPECTED_VACUOUS = {
    "Rate limiting works correctly",
    "Search behaves as expected",
    "Auth flow works",
    "Login is correct",
}
EXPECTED_SPECIFIC = {
    "Returns 429 when rate limit exceeded",
    "Displays a retry toast on sync failure",
    "Retries back off exponentially, capped at 5 attempts",
    "Config table documents every flag",
    "`GET /users/:id` returns 404 for an unknown id",
    "Returns a session token and works correctly",
}
# The one case among EXPECTED_SPECIFIC that exercises the AND-NOT branch: its
# trailing clause DOES match the vacuous-predicate regex, and it's unflagged
# only because the concrete-signal escape hatch fires too.
AND_NOT_BRANCH_CASE = "Returns a session token and works correctly"


def test_mixed_fixture() -> None:
    rc, out, _ = run([str(FIXTURES / "mixed.json")])
    check("mixed-exit", rc == 0, f"exit {rc}")
    data = json.loads(out)
    check("mixed-total", data["total"] == 10, data)
    flagged = {v["criterion"] for v in data["vacuous"]}
    check("mixed-flagged-set", flagged == EXPECTED_VACUOUS,
          f"flagged={flagged} expected={EXPECTED_VACUOUS}")
    check("mixed-specific-count", data["specific_count"] == len(EXPECTED_SPECIFIC),
          data["specific_count"])
    for c in EXPECTED_SPECIFIC:
        check(f"not-flagged: {c[:40]}", c not in flagged, flagged)
    for c in EXPECTED_VACUOUS:
        check(f"flagged: {c[:40]}", c in flagged, flagged)
    for v in data["vacuous"]:
        check(f"reason-nonempty: {v['criterion'][:30]}", bool(v.get("reason")), v)


def test_and_not_branch_exercised() -> None:
    """The one fixture case that proves the escape hatch fires correctly,
    rather than the predicate regex simply never matching in the first place
    (as it doesn't for the other four "not flagged" cases)."""
    rc, out, _ = run(stdin=json.dumps({"criteria": [AND_NOT_BRANCH_CASE]}))
    check("and-not-exit", rc == 0, f"exit {rc}")
    data = json.loads(out)
    check("and-not-unflagged", data["vacuous"] == [], data)
    check("and-not-specific-count", data["specific_count"] == 1, data)


def test_empty_criteria() -> None:
    rc, out, _ = run(stdin=json.dumps({"criteria": []}))
    check("empty-exit", rc == 0, f"exit {rc}")
    data = json.loads(out)
    check("empty-total", data["total"] == 0, data)
    check("empty-vacuous", data["vacuous"] == [], data)


def test_empty_stdin() -> None:
    rc, out, _ = run(stdin="")
    check("empty-stdin-exit", rc == 0, f"exit {rc}")
    data = json.loads(out)
    check("empty-stdin-total", data["total"] == 0, data)


def test_malformed_json() -> None:
    rc, _, err = run(stdin="not json")
    check("malformed-exit", rc == 1, f"exit {rc}")
    check("malformed-loud", "malformed JSON" in err, err)


def test_wrong_shape() -> None:
    rc, _, err = run(stdin=json.dumps({"criteria": "not a list"}))
    check("wrong-shape-exit", rc == 1, f"exit {rc}")
    check("wrong-shape-loud", "criteria" in err, err)


def test_usage_error() -> None:
    rc, _, err = run(["a.json", "b.json"])
    check("usage-exit", rc == 2, f"exit {rc}")
    check("usage-loud", "usage:" in err, err)


def test_missing_file() -> None:
    rc, _, err = run(["/tmp/no-such-criteria-fixture-xyz.json"])
    check("missing-exit", rc == 1, f"exit {rc}")
    check("missing-loud", "⚠️" in err and "cannot read" in err, err)


def main() -> int:
    for fn in [
        test_mixed_fixture,
        test_and_not_branch_exercised,
        test_empty_criteria,
        test_empty_stdin,
        test_malformed_json,
        test_wrong_shape,
        test_usage_error,
        test_missing_file,
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
