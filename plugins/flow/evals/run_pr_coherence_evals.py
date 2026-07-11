#!/usr/bin/env python3
"""Eval harness for pr-coherence.py — the deterministic body↔draft coherence +
read-back engine behind FB-0067 (stale NOT-READY manifest on a ready PR).

Pins the coherence invariant the acceptance criteria name:

  manifest-present-on-ready-PR  ⇒ FAIL   (the recurring bug)
  manifest-absent-on-ready-PR   ⇒ PASS
  manifest-present-on-draft     ⇒ PASS

plus marker/heading detection parity (either token trips it), and the read-back
subcommand (expect present, forbid absent, draft-state match, coherence backstop).

Explicit body strings + --is-draft flags — no git/gh dependency. Stdlib only.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).parent
SCRIPT = HERE.parent / "skills" / "ship" / "lib" / "pr-coherence.py"

MARKER = "<!-- flow:not-ready-manifest -->"
HEADING = "🚫 NOT READY TO MERGE"

READY_WITH_MANIFEST = f"""## {HEADING} — unresolved blockers
{MARKER}
- [security] leaked token — needs: secret rotation
<!-- /flow:not-ready-manifest -->

## Summary
- does a thing
"""

READY_CLEAN = """## Summary
- does a thing

## Test plan
- [x] it works
"""

DRAFT_WITH_MANIFEST = READY_WITH_MANIFEST  # same body, but the PR IS a draft
HEADING_ONLY_READY = f"## {HEADING} — unresolved blockers\n\n## Summary\n- x\n"
MARKER_ONLY_READY = f"{MARKER}\n\n## Summary\n- x\n"

_failures: list[str] = []


def run(subcmd, body, extra_args):
    """Run pr-coherence.py <subcmd> with body written to a temp file. Returns exit code + stdout."""
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write(body)
        path = f.name
    try:
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), subcmd, "--body-file", path, *extra_args],
            capture_output=True, text=True,
        )
        return proc.returncode, proc.stdout + proc.stderr
    finally:
        Path(path).unlink(missing_ok=True)


def expect(name, got_rc, want_rc, out):
    if got_rc == want_rc:
        print(f"  PASS  {name}")
    else:
        print(f"  FAIL  {name}: exit {got_rc}, wanted {want_rc}\n        output: {out.strip()}")
        _failures.append(name)


def main() -> int:
    print("pr-coherence evals (FB-0067)")

    # --- coherence: the three acceptance cases ---------------------------------
    rc, out = run("coherence", READY_WITH_MANIFEST, ["--is-draft", "false"])
    expect("manifest-present-on-ready-PR ⇒ FAIL", rc, 1, out)

    rc, out = run("coherence", READY_CLEAN, ["--is-draft", "false"])
    expect("manifest-absent-on-ready-PR ⇒ PASS", rc, 0, out)

    rc, out = run("coherence", DRAFT_WITH_MANIFEST, ["--is-draft", "true"])
    expect("manifest-present-on-draft ⇒ PASS", rc, 0, out)

    rc, out = run("coherence", READY_CLEAN, ["--is-draft", "true"])
    expect("manifest-absent-on-draft ⇒ PASS", rc, 0, out)

    # --- marker/heading detection parity (either token is enough) --------------
    rc, out = run("coherence", HEADING_ONLY_READY, ["--is-draft", "false"])
    expect("heading-only-on-ready ⇒ FAIL (marker stripped, heading remains)", rc, 1, out)

    rc, out = run("coherence", MARKER_ONLY_READY, ["--is-draft", "false"])
    expect("marker-only-on-ready ⇒ FAIL (heading stripped, marker remains)", rc, 1, out)

    # --- readback: the post-write verification path ----------------------------
    rc, out = run("readback", READY_CLEAN, [
        "--is-draft", "false", "--expect", "## Summary", "--forbid", HEADING, "--want-draft", "false"])
    expect("readback: expect present + forbid absent + coherent ⇒ PASS", rc, 0, out)

    rc, out = run("readback", READY_CLEAN, [
        "--is-draft", "false", "--expect", "## Nonexistent Section"])
    expect("readback: expected substring missing ⇒ FAIL", rc, 1, out)

    rc, out = run("readback", READY_WITH_MANIFEST, [
        "--is-draft", "false", "--forbid", HEADING])
    expect("readback: forbidden substring present ⇒ FAIL", rc, 1, out)

    rc, out = run("readback", READY_CLEAN, [
        "--is-draft", "false", "--want-draft", "true"])
    expect("readback: draft-state mismatch ⇒ FAIL", rc, 1, out)

    # The load-bearing backstop: readback FAILS on an incoherent state even when the
    # caller forgot to --forbid the manifest — this is what catches the silent write.
    rc, out = run("readback", READY_WITH_MANIFEST, ["--is-draft", "false"])
    expect("readback: incoherent (ready+manifest) with no explicit forbid ⇒ FAIL", rc, 1, out)

    # --- usage: missing body file exits 2, never a false PASS ------------------
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "coherence", "--body-file", "/no/such/file.md", "--is-draft", "false"],
        capture_output=True, text=True)
    expect("missing body file ⇒ exit 2 (never a false PASS)", proc.returncode, 2, proc.stdout + proc.stderr)

    print()
    if _failures:
        print(f"FAILED: {len(_failures)} eval(s): {', '.join(_failures)}")
        return 1
    print("All pr-coherence evals passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
