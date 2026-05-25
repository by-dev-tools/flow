#!/usr/bin/env python3
"""Security eval runner — runs every test under plugins/flow/evals/security/.

Companion to plugins/flow/evals/run_evals.py (which covers the auditor +
plan-critic regression fixtures). This runner covers security-class tests
that don't fit the rendered-context-against-required-text shape:

- plugins/flow/evals/security/test_cwd_constraint.py (PR 2 FOLLOW-UP #1)
- plugins/flow/evals/security/test_malicious_config.py (PR 2 FOLLOW-UP #2)

Each test file is a standalone Python script with `main() -> int` returning
0 on pass / 1 on fail. This runner discovers them by filename pattern
(test_*.py), invokes each, and aggregates exit codes.

Run: python3 plugins/flow/evals/run_security_evals.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SECURITY_DIR = HERE / "security"


def main() -> int:
    test_files = sorted(SECURITY_DIR.glob("test_*.py"))
    if not test_files:
        print(f"No test_*.py files found under {SECURITY_DIR}", file=sys.stderr)
        return 2

    failed = []
    for tf in test_files:
        print(f"\n=== {tf.name} ===")
        result = subprocess.run(["python3", str(tf)], capture_output=False)
        if result.returncode != 0:
            failed.append(tf.name)

    print("\n" + "=" * 60)
    if failed:
        print(f"FAILED ({len(failed)}/{len(test_files)}):")
        for name in failed:
            print(f"  - {name}")
        return 1
    print(f"All {len(test_files)} security test files passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
