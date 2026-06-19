#!/usr/bin/env python3
"""Eval harness for the durable visual record (Deliverable-quality track V3b).

Pins the load-bearing behaviors of `skills/ship/lib/insert-visual-history.py` (the
distill bridge's mechanical half) + the `/flow:ship` §5c gate contract + the schema
slot. Assertion-based (substring must / must-not + exit-code), not golden-diff:
robust to cosmetic wording tweaks while pinning what matters. Stdlib only.

Run: python3 plugins/flow/evals/run_visual_history_evals.py

What it covers (roadmap § Next PR-2 acceptance: "covers the gated scaffold + the
distill output shape"):
  insert 1 — seed-from-skeleton on first write (file created, markers intact).
  insert 2 — REVERSE-CHRONOLOGICAL prepend (newest entry's <article> appears first).
  insert 3 — TOC regenerated from entry anchors, in document order; empty-placeholder gone.
  insert 4 — no-italic-headings enforced (markdown emphasis stripped from the title).
  insert 5 — distill output shape: grounding (type/statement/decision_test/citations),
             lean asset src ref, CSS/SVG reconstruction fallback (labelled), questions carried.
  fail  1 — missing title / bad date / malformed target → non-zero exit, NO partial write.
  gate  1 — §5c gate contract present in ship/SKILL.md (uiSurface:false skip,
             no-load-bearing-decision skip, created-on-first-write, never base64).
  slot  1 — visualHistoryPath exists in the schema with a default.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).parent
FIX = HERE / "fixtures" / "visual-history"
LIB = HERE.parent / "skills" / "ship" / "lib"
SCRIPT = LIB / "insert-visual-history.py"
SKELETON = LIB / "visual-history-skeleton.html"
SHIP_SKILL = HERE.parent / "skills" / "ship" / "SKILL.md"
SCHEMA = HERE.parent / "schema" / "flow.config.schema.json"

fails = 0


def check(cid, ok, detail=""):
    global fails
    if ok:
        print(f"PASS  [{cid}]")
    else:
        fails += 1
        print(f"FAIL  [{cid}]" + (f"  — {detail}" if detail else ""))


def run_insert(target: Path, entry_fixture: str):
    """Run the helper with an entry fixture; return (returncode, stdout, stderr)."""
    raw = (FIX / entry_fixture).read_text()
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--target", str(target)],
        input=raw, capture_output=True, text=True, check=False,
    )
    return proc.returncode, proc.stdout, proc.stderr


def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        target = Path(td) / "visual-history.html"

        # --- insert 1: seed-from-skeleton on first write -----------------------
        rc, _, err = run_insert(target, "entry-full.json")
        check("insert-1-seed", rc == 0 and target.exists(),
              f"rc={rc} exists={target.exists()} err={err.strip()}")
        doc = target.read_text() if target.exists() else ""
        check("insert-1-markers",
              all(m in doc for m in ("vh:toc-start", "vh:toc-end",
                                     "vh:entries-start", "vh:entries-end")),
              "skeleton marker comments must survive seeding")

        # --- insert 2 + 3 + 4: prepend reverse-chron, TOC, emphasis strip ------
        rc2, _, _ = run_insert(target, "entry-newer-emphasis.json")
        doc = target.read_text()
        check("insert-2-second-ok", rc2 == 0)

        # entries appear in reverse-chronological insertion order (newest first):
        order = re.findall(r'<article class="vh-entry" id="([^"]+)"', doc)
        check("insert-2-reverse-chron",
              order[:2] == ["tightened-the-card-spacing",
                            "empty-state-for-the-activity-feed"],
              f"order={order}")

        # TOC regenerated, same order, and the empty placeholder is gone:
        toc = doc[doc.index("vh:toc-start"):doc.index("vh:toc-end")]
        toc_anchors = re.findall(r'href="#([^"]+)"', toc)
        check("insert-3-toc-order",
              toc_anchors[:2] == ["tightened-the-card-spacing",
                                  "empty-state-for-the-activity-feed"],
              f"toc={toc_anchors}")
        check("insert-3-no-empty-placeholder", "No entries yet" not in toc)

        # no-italic-headings: the *the* emphasis is stripped from the rendered <h2>.
        check("insert-4-emphasis-stripped",
              "Tightened the card spacing" in doc and "*the*" not in doc,
              "markdown emphasis must be removed from headings (FB-0042)")

        # --- insert 5: distill output shape (the full entry) -------------------
        shape = {
            "grounding-type": "User need" in doc,
            "grounding-statement": "assumed the app had failed to load" in doc,
            "decision-test": "Decision test" in doc and "nothing here yet" in doc,
            "citations": "spec §3.1 first-run" in doc,
            "asset-src-ref": 'src="visual-history-assets/feed-empty-before.png"' in doc,
            "recon-fallback": "Reconstruction (capture unavailable)" in doc and "<svg" in doc,
            "questions-carried": "Questions carried forward" in doc
                                 and "sample-data CTA" in doc,
            "meta-line": "#48" in doc and "2026-06-14" in doc
                         and "claude/feed-empty-state" in doc,
        }
        for k, ok in shape.items():
            check(f"insert-5-{k}", ok)

        # --- fail 1: invalid entries / malformed target → loud fail, no write --
        rc_nt, _, _ = run_insert(target, "entry-no-title.json")
        check("fail-1-missing-title", rc_nt != 0)
        rc_bd, _, _ = run_insert(target, "entry-bad-date.json")
        check("fail-1-bad-date", rc_bd != 0)

        # malformed target (no markers) must fail WITHOUT corrupting it:
        bad = Path(td) / "bad.html"
        bad.write_text("<html>not a flow visual record</html>")
        rc_bad, _, _ = run_insert(bad, "entry-newer-emphasis.json")
        check("fail-1-malformed-target",
              rc_bad != 0 and bad.read_text() == "<html>not a flow visual record</html>",
              "malformed target must fail and stay untouched")

    # --- gate 1: §5c contract present in ship/SKILL.md -------------------------
    skill = SHIP_SKILL.read_text()
    gate = {
        "section": "### 5c. Distill the durable visual record" in skill,
        "uisurface-skip": "skipped (uiSurface:false)" in skill,
        "no-decision-skip": "no load-bearing visual decision" in skill,
        "first-write": "created-on-first-write" in skill or "first write" in skill,
        "never-base64": "Never base64-embed" in skill,
        "helper-call": "insert-visual-history.py" in skill,
    }
    for k, ok in gate.items():
        check(f"gate-1-{k}", ok)

    # --- gate 2: §5c asset-copy resolves against the report dir, no doubled "assets/" ---
    # The dogfound v1.8.0 bug: §5c set ASSETS_SRC="$(dirname REPORT)/assets" then copied
    # "$ASSETS_SRC/<content>" where <content> already began "assets/" → /tmp/assets/assets/...
    # → broken <img> refs. Pin the fix so a future edit can't reintroduce the doubling.
    asset = {
        "uses-report-dir": "$REPORT_DIR" in skill or "REPORT_DIR=" in skill,
        "copies-by-basename": 'basename "$content"' in skill or "basename" in skill,
        "no-doubling-var": "ASSETS_SRC" not in skill,           # the doubling source is gone
        "warns-on-doubling": "assets/assets" in skill,           # the explicit trap note survives
    }
    for k, ok in asset.items():
        check(f"gate-2-asset-{k}", ok)

    # --- contrast 1: skeleton text colors meet WCAG AA (4.5:1) ----------------
    # Both the UX and design-engineer lenses caught contrast failures that were
    # only visible in a real browser (the #49 annotation-layer lesson; roadmap V3a
    # follow-up #2). Pin the documented default text colors so a future palette
    # tweak can't silently drop a text pair below AA. Each pair also asserts the fg
    # hex is actually present in the skeleton, so a color change forces re-review.
    def _lum(hexcolor):
        c = hexcolor.lstrip("#")
        ch = [int(c[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]
        ch = [(v / 12.92) if v <= 0.03928 else (((v + 0.055) / 1.055) ** 2.4) for v in ch]
        return 0.2126 * ch[0] + 0.7152 * ch[1] + 0.0722 * ch[2]

    def _ratio(fg, bg):
        a, b = _lum(fg), _lum(bg)
        hi, lo = max(a, b), min(a, b)
        return (hi + 0.05) / (lo + 0.05)

    skel = SKELETON.read_text()
    # (fg, bg, min-ratio, label) — bg values are the documented surfaces in the skeleton.
    contrast_pairs = [
        ("#6b6b71", "#ffffff", 4.5, "empty-placeholder-on-toc"),     # light
        ("#6b6b71", "#f6f6f7", 4.5, "footer-on-body"),               # light
        ("#7a4d00", "#fafafb", 4.5, "recon-note-light"),             # light
        ("#0a5fb0", "#ffffff", 4.5, "toc-link-on-card"),             # light
        ("#e0b86a", "#1a1a1d", 4.5, "recon-note-dark"),              # dark
        ("#5b9fe0", "#232327", 4.5, "grounding-gtype-dark"),         # dark
    ]
    for fg, bg, minr, label in contrast_pairs:
        r = _ratio(fg, bg)
        check(f"contrast-{label}", fg in skel and r >= minr,
              f"{fg} on {bg} = {r:.2f}:1 (need {minr}); fg-in-skeleton={fg in skel}")

    # --- slot 1: visualHistoryPath in the schema ------------------------------
    try:
        schema = json.loads(SCHEMA.read_text())
        slot = schema["properties"].get("visualHistoryPath", {})
        check("slot-1-present", bool(slot) and "default" in slot,
              "visualHistoryPath must exist with a default")
    except (OSError, ValueError, KeyError) as e:
        check("slot-1-present", False, str(e))

    total_marker = "passed" if fails == 0 else "FAILED"
    print(f"\n{total_marker}: {fails} failing check(s)")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
