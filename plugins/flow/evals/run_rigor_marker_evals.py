#!/usr/bin/env python3
"""Eval harness for /flow:ship's rigor-marker.py (the simplify+staff-review evidence marker).

Pins the contract /flow:ship Step 1.0 keys on:

  write→check ok    — a marker written with (branch, source_sha) passes check with the same pair.
  branch-mismatch   — same source_sha, different branch → exit 1 + "branch-mismatch".
  source-drift      — same branch, different source_sha → exit 1 + "source-drift".
  missing           — no marker file → exit 1 + "missing".
  source-sha stable — `source-sha` is deterministic (two calls agree) and a 64-char hex digest.

Uses an explicit --path in a temp dir (no /tmp pollution, no reliance on the default
branch-slug path). Stdlib only.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).parent
SCRIPT = HERE.parent / "skills" / "ship" / "lib" / "rigor-marker.py"


def run(argv: list[str], cwd=None) -> tuple[int, str]:
    proc = subprocess.run([sys.executable, str(SCRIPT), *argv],
                          capture_output=True, text=True, check=False, cwd=cwd)
    return proc.returncode, (proc.stdout + proc.stderr)


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

    with tempfile.TemporaryDirectory() as tmp:
        marker = str(Path(tmp) / "marker.json")
        SHA = "a" * 64

        rc, _ = run(["write", "--branch", "feature/x", "--source-sha", SHA, "--path", marker])
        check("write-ok", rc == 0, f"write rc={rc}")

        rc, out = run(["check", "--branch", "feature/x", "--source-sha", SHA, "--path", marker])
        check("check-ok", rc == 0 and "ok" in out, f"rc={rc} out={out!r}")

        rc, out = run(["check", "--branch", "feature/OTHER", "--source-sha", SHA, "--path", marker])
        check("branch-mismatch", rc == 1 and "branch-mismatch" in out, f"rc={rc} out={out!r}")

        rc, out = run(["check", "--branch", "feature/x", "--source-sha", "b" * 64, "--path", marker])
        check("source-drift", rc == 1 and "source-drift" in out, f"rc={rc} out={out!r}")

        rc, out = run(["check", "--branch", "feature/x", "--source-sha", SHA,
                       "--path", str(Path(tmp) / "nope.json")])
        check("missing", rc == 1 and "missing" in out, f"rc={rc} out={out!r}")

    # source-sha determinism + shape (runs against this repo's real git state).
    rc1, o1 = run(["source-sha"])
    rc2, o2 = run(["source-sha"])
    d1, d2 = o1.strip(), o2.strip()
    check("source-sha-deterministic", rc1 == 0 and rc2 == 0 and d1 == d2, f"{d1!r} vs {d2!r}")
    check("source-sha-is-hex64", len(d1) == 64 and all(c in "0123456789abcdef" for c in d1), f"{d1!r}")

    # Meaningful diff-hashing test: a SEEDED temp git repo with an origin/main ref, so the
    # real `git diff origin/main` path is exercised even under CI's depth-1 checkout (where
    # the in-repo run above degrades to the empty-input hash). A tracked source change MUST
    # move the fingerprint; commit-invariance MUST hold (committing the change keeps it).
    def git(repo, *a):
        subprocess.run(["git", "-C", repo, *a], check=True, capture_output=True)
    with tempfile.TemporaryDirectory() as repo:
        git(repo, "init", "-q")
        git(repo, "config", "user.email", "t@t"); git(repo, "config", "user.name", "t")
        (Path(repo) / "a.py").write_text("x = 1\n")
        git(repo, "add", "-A"); git(repo, "commit", "-q", "-m", "base")
        git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")  # fake remote-tracking ref
        _, h_base = run(["source-sha", "--default-branch", "main"], cwd=repo)
        (Path(repo) / "a.py").write_text("x = 2\n")  # uncommitted tracked source change
        _, h_dirty = run(["source-sha", "--default-branch", "main"], cwd=repo)
        check("source-sha-detects-source-change", h_base.strip() != h_dirty.strip(),
              f"{h_base.strip()!r} vs {h_dirty.strip()!r}")
        git(repo, "add", "-A"); git(repo, "commit", "-q", "-m", "change")  # commit it
        _, h_committed = run(["source-sha", "--default-branch", "main"], cwd=repo)
        check("source-sha-commit-invariant", h_committed.strip() == h_dirty.strip(),
              f"committed {h_committed.strip()!r} != dirty {h_dirty.strip()!r}")

    print(f"\n{total - fails} passed, {fails} failed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
