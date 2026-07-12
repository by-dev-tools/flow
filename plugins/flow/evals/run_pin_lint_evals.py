#!/usr/bin/env python3
"""
Regression eval for the Spec-walk pinning lint (walk-pin-lint.py).

Pins the deterministic contract the /flow:critique-plan preamble depends on:

  1. Mixed block — reports EXACTLY the checkboxes that name no pinning test
     or verification artifact; a named test (bare or backticked) OR a pin
     marker (→ / pinned by / verify:) followed by a concrete artifact counts
     as pinned.
  2. All-pinned block — reports `clean`.
  3. Qualified heading (`**Spec-walk (queued — hoist to bare on activation):**`)
     is still linted (heading tolerance inherited from the shared walk_extract
     matcher).
  4. No block / no checkboxes — loud note, exit 0 (absence of a plan block is
     the reviewers' business, not the lint's).
  5. Multiple blocks in one document — all linted (a standalone plan document
     may legitimately carry several), with a note.

The lint is advisory: exit code is 0 for every lint verdict. This harness
asserts on the rendered report text, not the exit code (except the crash-grade
paths).

Stdlib only. No network, no third-party deps. Run:
    python3 plugins/flow/evals/run_pin_lint_evals.py
Exits non-zero on any failure (CI gate).
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIXTURES = HERE / "fixtures" / "pin-lint"
LINT = HERE.parent / "skills" / "critique-plan" / "lib" / "walk-pin-lint.py"

_failures: list[str] = []
_passes = 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global _passes
    if cond:
        _passes += 1
    else:
        _failures.append(f"{name}: {detail}")


def run_lint(fixture: str) -> tuple[int, str]:
    proc = subprocess.run(
        [sys.executable, str(LINT), str(FIXTURES / fixture)],
        capture_output=True,
        text=True,
    )
    return proc.returncode, proc.stdout


def test_mixed_pins() -> None:
    rc, out = run_lint("mixed_pins.md")
    check("mixed-exit", rc == 0, f"exit {rc}")
    check("mixed-count", "3/5 checkboxes carry a named pin" in out, out)
    check("mixed-flags-rate-limit", "UNPINNED: Rate limiting works correctly" in out, out)
    check("mixed-flags-middleware", "UNPINNED: Middleware ordering is preserved" in out, out)
    # The three pinned ones (named test, backticked test, → verify: doc-diff)
    # must NOT be flagged.
    check("mixed-no-backoff", "UNPINNED: Retries back off" not in out, out)
    check("mixed-no-fifo", "UNPINNED: Queue drains FIFO" not in out, out)
    check("mixed-no-config", "UNPINNED: Config table documents" not in out, out)


def test_all_pinned() -> None:
    rc, out = run_lint("all_pinned.md")
    check("allpinned-exit", rc == 0, f"exit {rc}")
    check("allpinned-clean", "PIN LINT: clean — 3/3" in out, out)
    check("allpinned-no-unpinned", "UNPINNED" not in out, out)


def test_qualified_heading() -> None:
    # A queued plan's non-bare heading is still linted.
    rc, out = run_lint("qualified_heading.md")
    check("qualified-exit", rc == 0, f"exit {rc}")
    check("qualified-count", "1/2 checkboxes carry a named pin" in out, out)
    check("qualified-flags-toast", "UNPINNED: Sync failures surface a retry toast" in out, out)
    check("qualified-no-cap", "UNPINNED: Backoff caps" not in out, out)


def test_no_block() -> None:
    rc, out = run_lint("no_block.md")
    check("noblock-exit", rc == 0, f"exit {rc}")
    check("noblock-note", "no Spec-walk block found" in out, out)
    check("noblock-loud", "⚠️" in out, out)


def test_multi_blocks() -> None:
    rc, out = run_lint("multi_blocks.md")
    check("multi-exit", rc == 0, f"exit {rc}")
    check("multi-note", "2 Spec-walk blocks found" in out, out)
    # Second block's unpinned checkbox is caught (proves all blocks linted).
    check("multi-flags-second", "UNPINNED: Old criterion with no pin" in out, out)
    check("multi-count", "1/2 checkboxes carry a named pin" in out, out)


def test_usage_error() -> None:
    # Too many args → nonzero (crash-grade usage error, not a lint verdict).
    proc = subprocess.run(
        [sys.executable, str(LINT), "a.md", "b.md"],
        capture_output=True,
        text=True,
    )
    check("usage-exit", proc.returncode == 2, f"exit {proc.returncode}")


def test_missing_file() -> None:
    # A path UNDER cwd that doesn't exist hits the read-error branch (nonzero).
    proc = subprocess.run(
        [sys.executable, str(LINT), "no-such-plan-xyz.md"],
        capture_output=True,
        text=True,
    )
    check("missing-exit", proc.returncode == 1, f"exit {proc.returncode}")
    check("missing-loud", "⚠️" in proc.stderr and "cannot read" in proc.stderr, proc.stderr)


def test_external_path_rejected() -> None:
    # An out-of-cwd path is rejected by the containment guard (mirrors
    # load_plan_file), since the lint report feeds the reviewer prompt.
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as fh:
        fh.write("**Spec-walk:**\n- [ ] unpinned\n")
        outside = fh.name  # /tmp/... — outside the repo cwd
    try:
        proc = subprocess.run(
            [sys.executable, str(LINT), outside],
            capture_output=True, text=True, cwd=str(HERE.parent.parent.parent),
        )
        check("external-exit", proc.returncode == 1, f"exit {proc.returncode}")
        check("external-loud", "rejecting plan file outside cwd" in proc.stderr, proc.stderr)
    finally:
        Path(outside).unlink(missing_ok=True)


def main() -> int:
    for fn in [
        test_mixed_pins,
        test_all_pinned,
        test_qualified_heading,
        test_no_block,
        test_multi_blocks,
        test_usage_error,
        test_missing_file,
        test_external_path_rejected,
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
