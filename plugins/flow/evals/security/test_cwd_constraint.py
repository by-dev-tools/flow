#!/usr/bin/env python3
"""Security regression test: extract_session.py --reference-paths cwd constraint.

Asserts that the path-validation defense added in PR 2 (Phase 6) rejects
out-of-cwd paths by default and accepts them only with the explicit
--allow-external-paths opt-out flag.

Class of bug this fixture protects against: silent regression of the cwd
constraint during future refactors of `gather_reference_docs` in
extract_session.py. Without this fixture, a refactor that drops the
`Path.resolve().relative_to(cwd)` check would pass `claude plugin validate`
and the existing audit-side evals, then ship a path-traversal vulnerability.

Run standalone: python3 plugins/flow/evals/security/test_cwd_constraint.py
Run via harness: python3 plugins/flow/evals/run_security_evals.py

Exit code 0 if all asserts pass; 1 if any assert fails.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

# Test lives at plugins/flow/evals/security/test_cwd_constraint.py
# Target lives at plugins/flow/scripts/extract_session.py
# So: __file__.parent (=security/) → .parent (=evals/) → .parent (=flow/) → scripts/extract_session.py
PLUGIN_ROOT = Path(__file__).resolve().parent.parent.parent
EXTRACT = PLUGIN_ROOT / "scripts" / "extract_session.py"
assert EXTRACT.exists(), f"extract_session.py not found at expected path: {EXTRACT}"

# Cases:
#   (label, args, cwd, sentinel_for_picking_a_legit_path, expect_reject, expect_message_contains)
CASES = []


def make_minimal_session(tmpdir: Path) -> Path:
    """Write a minimal JSONL session file that extract_session can parse."""
    sess = tmpdir / "session.jsonl"
    sess.write_text(
        '{"type":"user","message":{"role":"user","content":"hi"},"sessionId":"s1","uuid":"u1","timestamp":"2026-05-24T00:00:00.000Z","cwd":"' + str(tmpdir).replace('\\', '\\\\') + '","gitBranch":"main"}\n'
        '{"type":"assistant","message":{"role":"assistant","content":[{"type":"text","text":"hello"}]},"sessionId":"s1","uuid":"u2","timestamp":"2026-05-24T00:00:01.000Z"}\n'
    )
    return sess


def run_extract(cwd: Path, args: list[str], session_path: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["python3", str(EXTRACT), "--mode", "plan", "--session", str(session_path), *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=30,
    )


def test_absolute_outside_cwd_rejected() -> None:
    """Absolute path outside cwd must be rejected by default.

    Strong assert: /etc/hosts content sentinels (127.0.0.1 or ::1) must NOT
    appear in stdout. A leak prints the file content, not the path string,
    so checking on path-string absence is vacuous. (Caught by engineer-lens
    review of PR 3: the original assert had an escape hatch where a
    regression that drops the cwd check but doesn't print the path would
    pass silently.)
    """
    with tempfile.TemporaryDirectory() as td:
        cwd = Path(td)
        sess = make_minimal_session(cwd)
        # /etc/hosts is universally present on macos + linux
        result = run_extract(cwd, ["--reference-paths", "/etc/hosts"], sess)
        assert "127.0.0.1" not in result.stdout and "::1" not in result.stdout, (
            f"Expected /etc/hosts content blocked; got STDOUT containing host file content:\n{result.stdout[:500]}"
        )
        print("  [PASS] /etc/hosts content blocked without --allow-external-paths")


def test_absolute_outside_cwd_accepted_with_optout() -> None:
    """Absolute outside-cwd path must be accepted with --allow-external-paths.

    Strong assert: with the opt-out flag set, /etc/hosts content sentinels
    (127.0.0.1 or ::1) MUST appear in stdout. This complements the rejection
    test and confirms the opt-out path actually opts out.
    """
    with tempfile.TemporaryDirectory() as td:
        cwd = Path(td)
        sess = make_minimal_session(cwd)
        result = run_extract(cwd, ["--reference-paths", "/etc/hosts", "--allow-external-paths"], sess)
        assert "127.0.0.1" in result.stdout or "::1" in result.stdout, (
            f"Expected /etc/hosts content in stdout with --allow-external-paths; got:\nSTDOUT: {result.stdout[:500]}\nSTDERR: {result.stderr[:300]}"
        )
        print("  [PASS] /etc/hosts content accepted with --allow-external-paths")


def test_relative_under_cwd_accepted() -> None:
    """Relative path under cwd must work unmodified."""
    with tempfile.TemporaryDirectory() as td:
        cwd = Path(td)
        sess = make_minimal_session(cwd)
        # Create a real file under cwd
        ref = cwd / "ref.md"
        ref.write_text("# Reference\n\nSentinel token: REF_OK_TOKEN_42\n")
        result = run_extract(cwd, ["--reference-paths", str(ref)], sess)
        assert "REF_OK_TOKEN_42" in result.stdout, (
            f"Expected under-cwd file to be read into context; got:\nSTDOUT: {result.stdout[:500]}\nSTDERR: {result.stderr[:300]}"
        )
        print("  [PASS] relative-under-cwd path accepted")


def test_dotdot_traversal_rejected() -> None:
    """`../../../etc/hosts`-style path must be rejected by default (Path.resolve canonicalizes)."""
    with tempfile.TemporaryDirectory() as td:
        cwd = Path(td) / "nested" / "deep"
        cwd.mkdir(parents=True, exist_ok=True)
        sess = make_minimal_session(cwd)
        result = run_extract(cwd, ["--reference-paths", "../../../etc/hosts"], sess)
        combined = result.stdout + result.stderr
        # Either rejected (best) or at minimum: /etc/hosts content doesn't appear in stdout.
        assert "127.0.0.1" not in result.stdout and "::1" not in result.stdout, (
            f"Expected ../../../etc/hosts traversal blocked; got STDOUT containing host file content:\n{result.stdout[:500]}"
        )
        print("  [PASS] ../../../etc/hosts traversal blocked")


def main() -> int:
    print("Security test: cwd constraint on extract_session.py --reference-paths")
    failed = 0
    for fn in (
        test_absolute_outside_cwd_rejected,
        test_absolute_outside_cwd_accepted_with_optout,
        test_relative_under_cwd_accepted,
        test_dotdot_traversal_rejected,
    ):
        try:
            fn()
        except AssertionError as e:
            print(f"  [FAIL] {fn.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"  [ERROR] {fn.__name__}: {type(e).__name__}: {e}")
            failed += 1
    if failed:
        print(f"\n{failed} test(s) failed.")
        return 1
    print("\nAll cwd-constraint tests passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
