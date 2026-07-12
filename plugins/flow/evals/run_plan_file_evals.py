#!/usr/bin/env python3
"""
Regression eval for extract_session.py --plan-file (queued-plan-document review).

The plan reviewers (/flow:critique-plan, /flow:audit-plan) preprocess with
extract_session.py --mode plan, which extracts "the most recent plan" from the
live session transcript — so a queued plan DOCUMENT on disk (e.g. a consumer's
plans/ directory) can't be targeted. `--plan-file` closes that: the plan under
review comes from the named file, session context becomes best-effort, and
reference docs still load.

Pins the contract:

  1. Plan-file render — the rendered context carries the
     `## Plan under review (from file: <path>)` heading and the file's
     distinctive content; reference-glob docs still load.
  2. No-transcript degradation — when no session transcript is discoverable
     (here forced with an explicit nonexistent --session-file), the render
     emits the loud standalone-review note and exits 0, and artifact status is
     UNKNOWN (never UNREAD), so the auditor can't mint false unverified-recall
     findings from a merely-absent transcript.
  3. Path safety — a --plan-file outside cwd is rejected (nonzero) unless
     --allow-external-paths, mirroring the reference-doc trust boundary.
  4. Mode guard — --plan-file with --mode completion is a loud usage error.
  5. Missing/empty plan file is fatal (nonzero), unlike a missing reference doc
     (skip-and-continue) — the plan file is the review SUBJECT.

Stdlib only. No network. Run:
    python3 plugins/flow/evals/run_plan_file_evals.py
Exits non-zero on any failure (CI gate).
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIXTURES = HERE / "fixtures" / "plan-file"
EXTRACT = HERE.parent / "scripts" / "extract_session.py"

PLAN = FIXTURES / "queued_plan.md"
SESSION = FIXTURES / "session.jsonl"
REFDOC = FIXTURES / "team_conventions.md"

MISSING_SESSION = "/nonexistent/no-such-session.jsonl"

_failures: list[str] = []
_passes = 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global _passes
    if cond:
        _passes += 1
    else:
        _failures.append(f"{name}: {detail}")


def run_extract(*args: str) -> tuple[int, str, str]:
    proc = subprocess.run(
        [sys.executable, str(EXTRACT), *args],
        capture_output=True,
        text=True,
    )
    return proc.returncode, proc.stdout, proc.stderr


def test_plan_file_render() -> None:
    # Explicit session fixture → transcript-found branch; plan + reference load.
    # --allow-external-paths + absolute fixture paths so the eval is
    # cwd-independent (the harness's own convention for tree-external fixtures).
    rc, out, _ = run_extract(
        "--mode", "plan",
        "--plan-file", str(PLAN),
        "--session-file", str(SESSION),
        "--reference-paths", str(REFDOC),
        "--allow-external-paths",
    )
    check("render-exit", rc == 0, f"exit {rc}")
    check(
        "render-heading",
        "## Plan under review (from file:" in out and "queued_plan.md)" in out,
        out[:200],
    )
    check("render-plan-marker", "jittered-backoff-rollout-marker-7f3a" in out, "plan content missing")
    check("render-ref-marker", "retry-conventions-2a9c" in out, "reference doc not loaded")
    check("render-user-request", "## User request" in out, "expected user-request section")


def test_no_transcript_degrades() -> None:
    # Nonexistent explicit session → no-transcript branch (deterministic).
    rc, out, err = run_extract(
        "--mode", "plan",
        "--plan-file", str(PLAN),
        "--session-file", MISSING_SESSION,
    )
    check("notrans-exit", rc == 0, f"exit {rc}")
    check("notrans-note", "No session transcript was found" in out, "standalone note missing")
    check("notrans-plan-still-there", "jittered-backoff-rollout-marker-7f3a" in out, "plan dropped")
    check(
        "notrans-request-unavailable",
        "(unavailable — no session transcript found" in out,
        "user request should degrade explicitly",
    )
    check("notrans-loud-stderr", "⚠️" in err and "standalone plan review" in err, err)


def test_no_false_unread_status() -> None:
    # A plan that references an artifact, no transcript: status must be UNKNOWN,
    # never UNREAD (the false-unverified-recall guard). queued_plan.md references
    # no external artifact path, so assert the branch's rendering shape directly:
    # the artifacts section says either "(none detected)" or "UNKNOWN", never
    # "UNREAD".
    _, out, _ = run_extract(
        "--mode", "plan",
        "--plan-file", str(PLAN),
        "--session-file", MISSING_SESSION,
    )
    check("no-unread", "UNREAD" not in out, "no-transcript render must not claim UNREAD")


def test_external_path_rejected() -> None:
    # Run from a temp cwd so the fixture (under the flow repo) is "external".
    with tempfile.TemporaryDirectory() as td:
        proc = subprocess.run(
            [sys.executable, str(EXTRACT), "--mode", "plan", "--plan-file", str(PLAN)],
            capture_output=True, text=True, cwd=td,
        )
        check("external-exit", proc.returncode == 1, f"exit {proc.returncode}")
        check("external-loud", "rejecting --plan-file outside cwd" in proc.stderr, proc.stderr)
        # And accepted WITH the flag.
        proc2 = subprocess.run(
            [sys.executable, str(EXTRACT), "--mode", "plan",
             "--plan-file", str(PLAN), "--allow-external-paths",
             "--session-file", MISSING_SESSION],
            capture_output=True, text=True, cwd=td,
        )
        check("external-flag-exit", proc2.returncode == 0, f"exit {proc2.returncode}")
        check("external-flag-render", "jittered-backoff-rollout-marker-7f3a" in proc2.stdout, "plan missing")


def test_mode_guard() -> None:
    rc, _, err = run_extract("--mode", "completion", "--plan-file", str(PLAN))
    check("modeguard-exit", rc == 2, f"exit {rc}")
    check("modeguard-loud", "only valid with --mode plan" in err, err)


def test_missing_plan_file_fatal() -> None:
    # A path UNDER cwd that doesn't exist hits the not-found branch (a path
    # OUTSIDE cwd is caught earlier by the external-path guard — covered above).
    rc, _, err = run_extract("--mode", "plan", "--plan-file", "no-such-queued-plan-xyz.md")
    check("missing-exit", rc == 1, f"exit {rc}")
    check("missing-loud", "--plan-file not found" in err, err)


def test_empty_plan_file_fatal() -> None:
    with tempfile.NamedTemporaryFile("w", suffix=".md", dir=Path.cwd(), delete=False) as fh:
        empty = Path(fh.name)
    try:
        rc, _, err = run_extract("--mode", "plan", "--plan-file", empty.name)
        check("empty-exit", rc == 1, f"exit {rc}")
        check("empty-loud", "is empty" in err, err)
    finally:
        empty.unlink(missing_ok=True)


def main() -> int:
    for fn in [
        test_plan_file_render,
        test_no_transcript_degrades,
        test_no_false_unread_status,
        test_external_path_rejected,
        test_mode_guard,
        test_missing_plan_file_fatal,
        test_empty_plan_file_fatal,
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
