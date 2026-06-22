#!/usr/bin/env python3
"""Eval harness for `/flow:verify-build`'s render-report.py (the ephemeral HTML walkthrough).

render-report.py had ZERO eval coverage before the provenance fix; this harness pins the
load-bearing provenance behavior (and a couple of baseline invariants so the renderer can't
silently break) without a brittle golden-diff:

  provenance — a buffer with ANY hand-authored / un-stamped criterion renders the
               self-report warning banner + a `self-reported` chip on that criterion,
               and the JUDGED criterion in the same buffer carries NO chip.
  judged     — a fully adversarial-judged buffer (the canonical findings-example.json)
               renders NO self-report banner and NO `self-reported` chip.

Renders to a temp file, reads the HTML back, asserts substrings. Stdlib only.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).parent
SCRIPT = HERE.parent / "skills" / "verify-build" / "lib" / "render-report.py"
REPORT_FIX = HERE / "fixtures" / "report-render"
# The judged buffer is the canonical example shipped next to the schema.
JUDGED = HERE.parent / "skills" / "verify-build" / "lib" / "findings-example.json"

# (id, buffer_path, must_contain[], must_not_contain[])
CASES = [
    # NB: the bare class name `.selfreport-banner` is ALWAYS in the <style> block, so
    # assert on the rendered `<div class="selfreport-banner">` to detect the actual banner.
    ("self-report-banner-and-chip", REPORT_FIX / "self-reported.json",
     ['class="selfreport-banner"', "implementer self-report", "self-reported</span>",
      "Home page renders the reworked hero layout."],
     []),
    ("judged-has-no-banner", JUDGED,
     ["Verify-build walkthrough"],
     ['class="selfreport-banner"', "self-reported</span>", "implementer self-report"]),
]


def render(buffer: Path) -> str:
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "report.html"
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), str(buffer), "--out", str(out),
             "--assets-dir", str(buffer.parent)],
            capture_output=True, text=True, check=False,
        )
        if proc.returncode != 0:
            return f"<<non-zero exit {proc.returncode}>>\n{proc.stderr}"
        return out.read_text(encoding="utf-8")


def chip_count(html: str) -> int:
    return html.count('chip selfreport">self-reported</span>')


def main() -> int:
    fails = 0
    for cid, buf, must, must_not in CASES:
        html = render(buf)
        missing = [s for s in must if s not in html]
        present = [s for s in must_not if s in html]
        # Extra invariant for the provenance case: exactly ONE criterion is chipped
        # (the hand-authored one), not the judged sibling.
        if cid == "self-report-banner-and-chip" and chip_count(html) != 2:
            # 2 = one in the banner legend + one on the single hand-authored criterion.
            present.append(f"<<expected exactly 2 'self-reported' chips, got {chip_count(html)}>>")
        if missing or present:
            fails += 1
            print(f"FAIL  [{cid}]")
            for s in missing:
                print(f"        missing: {s!r}")
            for s in present:
                print(f"        unexpected: {s!r}")
        else:
            print(f"PASS  [{cid}]")
    total = len(CASES)
    print(f"\n{total - fails} passed, {fails} failed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
