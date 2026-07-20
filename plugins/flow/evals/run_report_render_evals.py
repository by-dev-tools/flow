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
  annotation — (FB-0071) the injected annotation layer is DOM-general: its picker/anchor/
               export contract is present, the embedded-browser-hostile patterns (native
               modals, async clipboard) are ABSENT, and render-report.py injects the layer
               on EVERY rendered report — a frameless (text-only) report is annotatable too.

Renders to a temp file, reads the HTML back, asserts substrings. Stdlib only.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).parent
SCRIPT = HERE.parent / "skills" / "verify-build" / "lib" / "render-report.py"
REPORT_FIX = HERE / "fixtures" / "report-render"
# The judged buffer is the canonical example shipped next to the schema.
JUDGED = HERE.parent / "skills" / "verify-build" / "lib" / "findings-example.json"
# The annotation layer partial (single source of truth, injected before </body>).
LAYER = HERE.parent / "skills" / "verify-build" / "lib" / "annotation-layer.html"

# FB-0071 contract for the DOM-general annotation layer. The picker/traversal/anchor/
# export shape must be present; the embedded-browser-hostile call forms must be ABSENT.
LAYER_MUST = [
    "elementFromPoint",        # picker: raw point → element
    "pickTarget",              # walk-up to a sane target
    "getBoundingClientRect",   # outline snaps to the element rect
    'id="annot-pick"',         # explicit pick-mode toggle
    "ArrowUp", "ArrowDown",    # keyboard parent/child traversal
    "parentElement",           # ArrowUp target
    "data-pin-id",             # stable-identity anchor opt-in
    "nearestHeading",          # content-derived anchor fallback
    "function descriptor",     # export is a location descriptor…
    "execCommand",             # …copied via hidden-textarea + execCommand
    "Confirm clear",           # two-step inline Clear (no native confirm)
    "localStorage",            # persistence retained
]
# Native modals + async clipboard are suppressed in the embedded browser → forbidden.
# Comments in the partial are worded to avoid these literal call sequences, so a hit is
# a real regression, not prose.
LAYER_MUST_NOT = [
    "navigator.clipboard",
    "confirm(", "alert(", "prompt(",
    "SHOT_SELECTOR", "shotIndex", "imageOrder",  # the FB-0051 image-index anchoring is gone
]

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


FRAMELESS_BUFFER = {
    "schema_version": "1.0",
    "metadata": {"branch": "b", "head_sha_short": "s", "plugin_version": "0.0.0", "platform_hint": "web"},
    "overall_verdict": "Unknown", "exit_code": 1,
    "criteria": [{
        "text": "a text-only criterion", "adversarial_cases": [], "observations": [],
        "verdicts": {d: {"verdict": "Unknown", "evidence": ["a", "b"], "notes": "x"}
                     for d in ("correctness", "regression", "scope-creep")},
        "aggregated_verdict": "Unknown",
    }],
    "not_tested": [],
}


def check_layer_contract() -> list[str]:
    """Grep the annotation-layer partial directly for the FB-0071 contract (independent of
    injection): picker/traversal/anchor/export present, native-modal + async-clipboard absent."""
    problems = []
    text = LAYER.read_text(encoding="utf-8")
    for s in LAYER_MUST:
        if s not in text:
            problems.append(f"layer missing required contract token: {s!r}")
    for s in LAYER_MUST_NOT:
        if s in text:
            problems.append(f"layer contains forbidden (embedded-browser-hostile) token: {s!r}")
    return problems


def check_always_injected() -> list[str]:
    """render-report.py must inject the layer on EVERY rendered report — including a
    frameless (text-only) one, which is annotatable now that the picker anchors to any
    element. Proven by the toolbar id + the persistence-key prefix appearing in the HTML."""
    problems = []
    with tempfile.TemporaryDirectory() as tmp:
        bp = Path(tmp) / "frameless.json"
        bp.write_text(json.dumps(FRAMELESS_BUFFER), encoding="utf-8")
        html = render(bp)
    if 'class="annot-shot"' in html:
        problems.append("frameless buffer should render no captured frame")
    for s in ('id="annot-bar"', 'id="annot-pick"', "flow-annot:", "elementFromPoint"):
        if s not in html:
            problems.append(f"frameless report did not inject the annotation layer (missing {s!r})")
    return problems


def main() -> int:
    fails = 0
    for cid, extra in (("layer-contract", check_layer_contract), ("always-injected", check_always_injected)):
        problems = extra()
        if problems:
            fails += 1
            print(f"FAIL  [{cid}]")
            for p in problems:
                print(f"        {p}")
        else:
            print(f"PASS  [{cid}]")
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
    total = len(CASES) + 2  # + layer-contract + always-injected
    print(f"\n{total - fails} passed, {fails} failed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
