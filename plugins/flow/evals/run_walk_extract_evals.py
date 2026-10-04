#!/usr/bin/env python3
"""
Regression eval for the `*-walk` plan parsers (V2.1 hardening).

Pins the contract for `walk_extract.extract_block` and the two CLI parsers
(`extract-criteria.py`, `extract-visual-states.py`):

  1. Robust heading match — canonical, qualified, and markdown-heading forms.
  2. First (active) block scoping — multi-block plans extract ONLY the first,
     with a loud warning naming the others.
  3. Decoupling — a Visual-walk block is found even when the Spec-walk heading
     is malformed (the silent-skip routing fix).
  4. Graceful degradation — no block → empty + warning + exit 0; malformed
     checkboxes warn but don't crash; missing file → exit 1.

Stdlib only. No network, no third-party deps. Run:
    python3 plugins/flow/evals/run_walk_extract_evals.py
Exits non-zero on any failure (CI gate).
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

LIB = Path(__file__).resolve().parent.parent / "skills" / "verify-build" / "lib"
sys.path.insert(0, str(LIB))

from walk_extract import extract_block, heading_declares_na, heading_re, is_terminator  # noqa: E402

CRITERIA = LIB / "extract-criteria.py"
VISUAL = LIB / "extract-visual-states.py"

_failures: list[str] = []
_passes = 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global _passes
    if cond:
        _passes += 1
    else:
        _failures.append(f"{name}: {detail}")


def run_cli(script: Path, plan_text: str) -> tuple[int, dict]:
    """Write plan_text to a temp file, run the CLI, return (exit, parsed-json)."""
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as fh:
        fh.write(plan_text)
        path = fh.name
    try:
        proc = subprocess.run(
            [sys.executable, str(script), path],
            capture_output=True,
            text=True,
        )
        stream = proc.stdout if proc.returncode == 0 else (proc.stdout or proc.stderr)
        try:
            parsed = json.loads(stream) if stream.strip() else {}
        except json.JSONDecodeError:
            parsed = {}
        return proc.returncode, parsed
    finally:
        Path(path).unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# 1. Heading-match robustness (walk_extract unit level)
# ---------------------------------------------------------------------------

def test_heading_forms() -> None:
    spec = heading_re("Spec-walk")
    for good in [
        "**Spec-walk:**",
        "**Spec-walk**:",
        "  **Spec-walk:**  ",
        "**Spec-walk (PR 1c — shipped):**",
        "**Spec-walk (each → criterion):**",
        "## Spec-walk",
        "### Spec-walk",
        "### Spec-walk (active PR)",
    ]:
        check("heading-spec-good", bool(spec.match(good)), f"should match: {good!r}")
    for bad in [
        "- [ ] Spec-walk happens here",   # checkbox, not a heading
        "We will write a Spec-walk soon",  # prose
        "**Visual-walk:**",                # different label
    ]:
        check("heading-spec-bad", not spec.match(bad), f"should NOT match: {bad!r}")

    vis = heading_re("Visual-walk")
    for good in [
        "**Visual-walk:**",
        "**Visual-walk** *(UI changes only)*:",
        "**Visual-walk** *(UI only — when uiSurface is true)*:",
        "### Visual-walk",
    ]:
        check("heading-vis-good", bool(vis.match(good)), f"should match: {good!r}")
    check("heading-vis-cross", not vis.match("**Spec-walk:**"), "label isolation")


def test_terminators() -> None:
    for t in ["## Heading", "**Confidence verdicts:**", "**Visual-walk** *(x)*:", "### Files"]:
        check("terminator-yes", is_terminator(t), f"should terminate: {t!r}")
    for nt in ["- [ ] a criterion", "just some prose", "**Note:** inline bold prose here"]:
        check("terminator-no", not is_terminator(nt), f"should NOT terminate: {nt!r}")


# ---------------------------------------------------------------------------
# 2. First (active) block scoping
# ---------------------------------------------------------------------------

MULTI_BLOCK = """# Plan

## Active PR

**Spec-walk:**
- [ ] active criterion one
- [ ] active criterion two

**Confidence verdicts:** none.

## Shipped PR (retained)

**Spec-walk (PR 1c — shipped):**
- [x] old criterion A
- [x] old criterion B
- [x] old criterion C
"""


def test_first_block_only() -> None:
    block = extract_block(MULTI_BLOCK, "Spec-walk")
    check("multi-count", block["block_count"] == 2, f"got {block['block_count']}")
    check(
        "multi-items",
        block["items"] == ["active criterion one", "active criterion two"],
        f"got {block['items']}",
    )
    check(
        "multi-warns",
        any("2 Spec-walk blocks found" in w for w in block["warnings"]),
        f"warnings: {block['warnings']}",
    )
    check(
        "multi-no-stale",
        all("old criterion" not in c for c in block["items"]),
        "stale retained criteria leaked",
    )


def test_terminates_at_confidence() -> None:
    # The active block must stop at **Confidence verdicts:**, not swallow it.
    block = extract_block(MULTI_BLOCK, "Spec-walk")
    check("term-len", len(block["items"]) == 2, f"got {block['items']}")


# ---------------------------------------------------------------------------
# 3. Decoupling — Visual-walk found despite a malformed Spec-walk heading
# ---------------------------------------------------------------------------

MALFORMED_SPEC_WITH_VISUAL = """# Plan

## Active PR

### Spec-walk (each → criterion)
- [ ] behavioral criterion one

**Visual-walk** *(UI changes only)*:
- [ ] [state: empty / loading / error renders, not a blank panel]
- [ ] [token / motion: primary button uses the accent token; enter ≤ 200ms]
- [ ] [interaction / a11y: focus enters dialog and Esc closes it]
"""


def test_visual_decoupled() -> None:
    # Even though the Spec-walk heading is the non-canonical h3 form, both
    # parsers now find their respective blocks independently.
    spec = extract_block(MALFORMED_SPEC_WITH_VISUAL, "Spec-walk")
    check("decouple-spec", spec["items"] == ["behavioral criterion one"], f"got {spec['items']}")

    vis = extract_block(MALFORMED_SPEC_WITH_VISUAL, "Visual-walk")
    check("decouple-vis-count", len(vis["items"]) == 3, f"got {vis['items']}")
    check(
        "decouple-vis-head",
        vis["first_heading"].startswith("**Visual-walk**"),
        f"got {vis['first_heading']!r}",
    )


def test_visual_category_parse() -> None:
    rc, out = run_cli(VISUAL, MALFORMED_SPEC_WITH_VISUAL)
    check("vis-cli-exit", rc == 0, f"exit {rc}")
    cats = [a["category"] for a in out.get("assertions", [])]
    check("vis-cli-cats", cats == ["state", "token / motion", "interaction / a11y"], f"got {cats}")


# ---------------------------------------------------------------------------
# 4. Graceful degradation
# ---------------------------------------------------------------------------

NO_SPEC = """# Plan

## A PR with no spec-walk

Just prose, no checkboxes.
"""

MALFORMED_CB = """# Plan

**Spec-walk:**
- [ ] good criterion
- [] malformed no-space
- [?] malformed marker
"""


def test_empty_and_warns() -> None:
    rc, out = run_cli(CRITERIA, NO_SPEC)
    check("empty-exit", rc == 0, f"exit {rc}")
    check("empty-criteria", out.get("criteria") == [], f"got {out.get('criteria')}")
    check("empty-count", out.get("block_count") == 0, f"got {out.get('block_count')}")
    check("empty-warn", bool(out.get("warnings")), "expected a warning")

    rc2, out2 = run_cli(CRITERIA, MALFORMED_CB)
    check("malformed-exit", rc2 == 0, f"exit {rc2}")
    check("malformed-keeps-good", out2.get("criteria") == ["good criterion"], f"got {out2.get('criteria')}")
    check(
        "malformed-warns",
        any("malformed" in w for w in out2.get("warnings", [])),
        f"warnings: {out2.get('warnings')}",
    )


def test_missing_file_exits_1() -> None:
    proc = subprocess.run(
        [sys.executable, str(CRITERIA), "/nonexistent/path/plan.md"],
        capture_output=True,
        text=True,
    )
    check("missing-exit", proc.returncode == 1, f"exit {proc.returncode}")


def test_cli_backward_compat_keys() -> None:
    # The audit-coverage + verify-build consumers read .criteria and .warnings;
    # keep them present (additive-only change).
    rc, out = run_cli(CRITERIA, MULTI_BLOCK)
    check("compat-exit", rc == 0, f"exit {rc}")
    for key in ("criteria", "source_path", "source_heading", "warnings", "block_count"):
        check(f"compat-key-{key}", key in out, f"missing {key}")


# ---------------------------------------------------------------------------
# 5. Anchor co-location — the silent cross-PR grab
#
# Per-label first-block scoping is INDEPENDENT across labels, so an active PR
# that declares a Spec-walk but NO Visual-walk used to silently inherit a
# retained PR's Visual-walk block: only one Visual-walk block exists in the
# file, so `block_count == 1` and the multi-block WARN never fires. A
# backend-only PR would then be handed another PR's capture state-set (and a
# forced `visual_significant`) with zero warnings. Reported from two
# independent projects before it was fixed.
# ---------------------------------------------------------------------------

ACTIVE_WITHOUT_VISUAL = """# Plan

## PR B — active (top), backend only, declares NO Visual-walk

**Spec-walk:**
- [ ] ACTIVE: token refresh retries 3x on 401

## PR C — retained from an earlier shipped visual spike

**Spec-walk:**
- [ ] STALE: settings sheet lists all toggles

**Visual-walk:**
- [ ] [state: empty] STALE: empty settings sheet renders placeholder
"""

# Regression guard: a Visual-walk authored ABOVE its sibling Spec-walk inside
# the active section is still the active PR's — co-location is section-scoped
# (everything before the SECOND anchor heading), not "after the anchor".
VISUAL_BEFORE_SPEC = """# Plan

## PR A — active

**Visual-walk:**
- [ ] [state: empty] ACTIVE empty state renders

**Spec-walk:**
- [ ] ACTIVE criterion

## PR Z — retained

**Spec-walk:**
- [ ] STALE criterion
"""


def test_anchor_co_location() -> None:
    # THE BUG: the lone Visual-walk block belongs to a retained section.
    blk = extract_block(ACTIVE_WITHOUT_VISUAL, "Visual-walk", anchor_label="Spec-walk")
    check("coloc-empty", blk["items"] == [], f"stale items leaked: {blk['items']}")
    check("coloc-false", blk["co_located"] is False, f"got {blk['co_located']}")
    check(
        "coloc-warns",
        any("retained" in w for w in blk["warnings"]),
        f"warnings: {blk['warnings']}",
    )
    # The single-block case is exactly the one the multi-block WARN cannot see.
    check("coloc-block-count", blk["block_count"] == 1, f"got {blk['block_count']}")

    # Unanchored call keeps the legacy behavior (opt-in change, not a silent one).
    legacy = extract_block(ACTIVE_WITHOUT_VISUAL, "Visual-walk")
    check("coloc-legacy-unscoped", len(legacy["items"]) == 1, f"got {legacy['items']}")
    check("coloc-legacy-none", legacy["co_located"] is None, f"got {legacy['co_located']}")


def test_anchor_co_location_regression_guards() -> None:
    # Visual-walk above its sibling Spec-walk in the active section → still active.
    blk = extract_block(VISUAL_BEFORE_SPEC, "Visual-walk", anchor_label="Spec-walk")
    check("coloc-before-ok", blk["items"] == ["[state: empty] ACTIVE empty state renders"],
          f"got {blk['items']}")
    check("coloc-before-true", blk["co_located"] is True, f"got {blk['co_located']}")

    # Single-PR plan (<2 anchor headings) → trivially active, unchanged behavior.
    single = extract_block(MALFORMED_SPEC_WITH_VISUAL, "Visual-walk", anchor_label="Spec-walk")
    check("coloc-single-pr", len(single["items"]) == 3, f"got {single['items']}")
    check("coloc-single-true", single["co_located"] is True, f"got {single['co_located']}")

    # No anchor heading at all → co-location undefined, items still extracted.
    no_anchor = extract_block(
        "**Visual-walk:**\n- [ ] only a visual block\n", "Visual-walk", anchor_label="Spec-walk"
    )
    check("coloc-no-anchor", no_anchor["items"] == ["only a visual block"], f"got {no_anchor['items']}")
    check("coloc-no-anchor-none", no_anchor["co_located"] is None, f"got {no_anchor['co_located']}")


# KNOWN LIMITATIONS, pinned deliberately. Anchoring closes ONE of three
# degenerate shapes; these two defeat the "second anchor heading" proxy and still
# adopt a retained block silently. Both are pre-existing — anchoring did not
# introduce either and strictly improves the feature-mode shape that was actually
# reported. These tests assert the CURRENT behavior so the gaps stay visible; when
# a universal per-PR boundary marker lands, both should flip to items == [].
#
# Shape 1: the ACTIVE PR contributes no anchor (`tiny` omits Spec-walk; a
# non-visual `spike` replaces it), so anchor_idxs[0] lands in the first RETAINED
# section and a retained Visual-walk between anchors 0 and 1 reads as active.
TINY_ACTIVE_NO_SPEC = """# Plan

## PR D — active, tiny mode (no Spec-walk per plan-discipline.md)

**Mode:** tiny
**Goal:** bump the retry constant from 3 to 5.

## PR C — retained (shipped visual work)

**Spec-walk:**
- [ ] STALE: settings sheet lists all toggles

**Visual-walk:**
- [ ] [state: empty] STALE: empty settings sheet renders placeholder

## PR B — retained (older)

**Spec-walk:**
- [ ] STALE-B: older criterion
"""


# Shape 2: a RETAINED section authored Visual-walk-above-Spec-walk. That block
# precedes its own section's anchor (anchor_idxs[1]) so it falls inside the
# computed region. Indistinguishable by order alone from the legitimate active
# case VISUAL_BEFORE_SPEC pins above — which is precisely why the proxy fails.
RETAINED_VISUAL_FIRST = """# Plan

## PR B — active, backend only, NO Visual-walk

**Spec-walk:**
- [ ] ACTIVE: token refresh retries 3x on 401

## PR C — retained, authored visual-first

**Visual-walk:**
- [ ] [state: empty] STALE: settings sheet placeholder

**Spec-walk:**
- [ ] STALE: settings sheet lists toggles
"""


def test_anchor_known_limitation_tiny_mode() -> None:
    blk = extract_block(TINY_ACTIVE_NO_SPEC, "Visual-walk", anchor_label="Spec-walk")
    # Documents the gap: the active tiny PR has no anchor, so a retained block
    # still reads as co-located. Flip both assertions when the gap is closed.
    check("coloc-tiny-known-gap", len(blk["items"]) == 1,
          f"behavior changed — if this now returns [], the limitation is FIXED: "
          f"update this test + the walk_extract docstring. got {blk['items']}")
    check("coloc-tiny-known-gap-flag", blk["co_located"] is True,
          f"got {blk['co_located']}")


def test_anchor_known_limitation_retained_visual_first() -> None:
    blk = extract_block(RETAINED_VISUAL_FIRST, "Visual-walk", anchor_label="Spec-walk")
    check("coloc-retained-visual-first-gap", len(blk["items"]) == 1,
          f"behavior changed — if this now returns [], the limitation is FIXED: "
          f"update this test + the walk_extract docstring. got {blk['items']}")
    check("coloc-retained-visual-first-flag", blk["co_located"] is True,
          f"got {blk['co_located']}")


def test_anchor_co_location_cli() -> None:
    # The shipped CLI anchors by default — end-to-end, not just the unit.
    rc, out = run_cli(VISUAL, ACTIVE_WITHOUT_VISUAL)
    check("coloc-cli-exit", rc == 0, f"exit {rc}")
    check("coloc-cli-empty", out.get("assertions") == [], f"got {out.get('assertions')}")
    check("coloc-cli-flag", out.get("co_located") is False, f"got {out.get('co_located')}")
    # Spec-walk extraction is unanchored and must stay unaffected.
    rc_c, out_c = run_cli(CRITERIA, ACTIVE_WITHOUT_VISUAL)
    check("coloc-cli-spec-intact",
          out_c.get("criteria") == ["ACTIVE: token refresh retries 3x on 401"],
          f"got {out_c.get('criteria')}")



# ---------------------------------------------------------------------------
# 6. All-demoted detection — every matched heading is qualified as already-
#    shipped, so there is no active block at all. Distinct from block_count==0
#    (no heading whatsoever): a post-merge hygiene / doc-reconcile PR that
#    legitimately declares no Spec-walk of its own must not silently inherit
#    the last-merged PR's (still-present, still heading-matching) criteria.
# ---------------------------------------------------------------------------

ALL_DEMOTED = """# Plan

## Hygiene PR — active, declares no Spec-walk of its own

**Mode:** tiny
**Goal:** reconcile forward docs after merge.

## Shipped PR A (retained)

**Spec-walk (PR 1c — shipped):**
- [x] old criterion A

## Shipped PR B (retained)

**Spec-walk (merged #86):**
- [x] old criterion B
"""

# Regression guard: a demoted heading placed BEFORE the real active one (a
# mis-ordered plan) must not win "first" just by position — the parser should
# skip demoted headings when picking the active block.
DEMOTED_BEFORE_ACTIVE = """# Plan

## Shipped PR (retained, mis-ordered above the active PR)

**Spec-walk (shipped):**
- [x] STALE: already shipped criterion

## Active PR

**Spec-walk:**
- [ ] ACTIVE: real criterion
"""


def test_all_demoted() -> None:
    blk = extract_block(ALL_DEMOTED, "Spec-walk")
    check("all-demoted-items", blk["items"] == [], f"stale items leaked: {blk['items']}")
    check("all-demoted-flag", blk["all_demoted"] is True, f"got {blk['all_demoted']}")
    check("all-demoted-count", blk["block_count"] == 2, f"got {blk['block_count']}")
    check("all-demoted-heading", blk["first_heading"] is None, f"got {blk['first_heading']}")
    check(
        "all-demoted-warns",
        any("qualified as already-shipped" in w for w in blk["warnings"]),
        f"warnings: {blk['warnings']}",
    )

    # Not all-demoted (block_count==0, no heading at all) must NOT set the flag.
    none_at_all = extract_block(NO_SPEC, "Spec-walk")
    check("not-all-demoted-when-no-heading", none_at_all["all_demoted"] is False,
          f"got {none_at_all['all_demoted']}")

    # A normal single-active-block plan must not be flagged all_demoted either.
    normal = extract_block(MULTI_BLOCK, "Spec-walk")
    check("not-all-demoted-normal", normal["all_demoted"] is False,
          f"got {normal['all_demoted']}")


def test_demoted_heading_skipped_regardless_of_order() -> None:
    blk = extract_block(DEMOTED_BEFORE_ACTIVE, "Spec-walk")
    check(
        "demoted-order-items",
        blk["items"] == ["ACTIVE: real criterion"],
        f"got {blk['items']} — a demoted heading placed first must not win",
    )
    check("demoted-order-not-all-demoted", blk["all_demoted"] is False, f"got {blk['all_demoted']}")
    check(
        "demoted-order-heading",
        blk["first_heading"] == "**Spec-walk:**",
        f"got {blk['first_heading']!r}",
    )


def test_all_demoted_cli() -> None:
    rc, out = run_cli(CRITERIA, ALL_DEMOTED)
    check("all-demoted-cli-exit", rc == 0, f"exit {rc}")
    check("all-demoted-cli-criteria", out.get("criteria") == [], f"got {out.get('criteria')}")
    check("all-demoted-cli-flag", out.get("all_demoted") is True, f"got {out.get('all_demoted')}")



# ---------------------------------------------------------------- CV1 follow-up, item 3
# FIXTURES FIRST. Three defects, each with its own paired test, written before any fix so each
# one is observed failing. All three make a gate read LESS than it reports, with nothing said.

# A plan whose SECOND criterion carries a continuation line opening with a bold span. Nothing
# about it looks wrong to an author; `**A bolded note.**` indented under a bullet is ordinary
# prose. Measured before the fix: 1 of 3 extracted, 0 warnings.
_BOLD_CONT = """# Plan

**Spec-walk:**

- [ ] first criterion *Pinned by:* the `run_a_evals.py` eval
- [ ] second criterion *Pinned by:* the `run_b_evals.py` eval
      **A bolded note that is a continuation line, not a heading.**
- [ ] third criterion *Pinned by:* the `run_c_evals.py` eval
"""

# The same shape for the OTHER front-end, since both share one loop.
_BOLD_CONT_VISUAL = _BOLD_CONT.replace("**Spec-walk:**", "**Visual-walk** *(UI only)*:")

# A plan whose pin sits on the bullet's SECOND physical line. The block is not cut short here —
# all three criteria are extracted — but each arrives truncated to its first line, so the pin is
# invisible to any consumer. This is the half that made #171's gate report "name no verification
# artifact" over criteria that were all pinned.
_PIN_ON_LINE_2 = """# Plan

**Spec-walk:**

- [ ] first criterion
      *Pinned by:* the `run_a_evals.py` eval
- [ ] second criterion
      *Pinned by:* the `run_b_evals.py` eval
"""

# A heading that matches and yields NOTHING: the one close shape worth a warning. An author who
# leaves a stray heading between the walk heading and its checkboxes gets zero criteria, and
# before the fix that rendered identically to a plan with no criteria at all.
_EMPTY_BLOCK = """# Plan

**Spec-walk:**

### Coordination

- [ ] this belongs to another block and must NOT be collected
"""

# A GENUINE bold-label heading, which must still terminate the block. Without this the fix is
# satisfiable by never terminating, which breaks every multi-block plan this repo has.
_GENUINE_TERMINATOR = """# Plan

**Spec-walk:**

- [ ] first criterion *Pinned by:* the `run_a_evals.py` eval

**Confidence verdicts:**

- [ ] not a criterion, and must NOT be extracted
"""


def test_bold_continuation_keeps_every_criterion() -> None:
    """A continuation line opening with `**` must not end the block (both front-ends)."""
    for label, text, script in (
        ("Spec-walk", _BOLD_CONT, "extract-criteria.py"),
        ("Visual-walk", _BOLD_CONT_VISUAL, "extract-visual-states.py"),
    ):
        code, out = run_cli(LIB / script, text)
        # Derive the list key from the output instead of guessing it. Each front-end emits
        # exactly one non-warnings list key -- `criteria` here, `assertions` for the visual
        # front-end -- and guessing the latter as `visual_states` read a missing key as "0
        # extracted" when the measured figure is 2 of 3. A test that misstates the magnitude of
        # what it caught is its own small version of the truncation this fixture exists to catch.
        # Paired control (continuation line removed): both front-ends give 3 of 3.
        key = next(k for k, v in out.items() if isinstance(v, list) and k != "warnings")
        got = len(out.get(key, []))
        check(f"{label}: a bold continuation line keeps all 3 criteria",
              got == 3,
              f"extracted {got} of 3 — a continuation line was read as a block terminator, so "
              f"every later criterion vanished with no warning: {out.get(key)}")


def test_genuine_bold_heading_still_terminates() -> None:
    """The paired negative: a real bold-label heading must still end the block."""
    code, out = run_cli(LIB / "extract-criteria.py", _GENUINE_TERMINATOR)
    got = out.get("criteria", [])
    check("a genuine bold-label heading still terminates the block",
          len(got) == 1,
          f"extracted {len(got)}, expected 1 — if the fix stopped terminating at real headings it "
          f"would merge every block in a multi-block plan: {got}")


def test_early_end_is_announced() -> None:
    """A SUSPICIOUS close warns; a normal one reports where it stopped and stays quiet.

    The first version of this test demanded a warning on EVERY terminator close, and the
    implementation obliged. Both were wrong, and a review lens caught it at the ship gate:
    `extract_block` is first-active-block-only by design, so a terminator is how nearly every
    real plan's block ends -- it fired on this repo's own healthy plan. Before the fix truncation
    was silent; after it, truncation and success emitted the same sentence. Still
    non-discriminating, now with added noise, which is the failure `rigor-marker.py` names in its
    own comment one file away: a gate that always fires is one people learn to click past.

    The corrected contract splits the two jobs. `ended_at_line` is PROVENANCE and is always
    reported, so "how far did you read?" is answerable on every call (FB-0121). The WARNING fires
    only when the close looks wrong -- a heading that matched with nothing under it.
    """
    # A healthy block that ends at a real terminator: provenance, no alarm.
    code, out = run_cli(LIB / "extract-criteria.py", _GENUINE_TERMINATOR)
    warns = " ".join(out.get("warnings", []))
    check("a NORMAL terminator close does not warn",
          "ended at line" not in warns,
          f"warning on the healthy path is noise, and it makes the signal unreadable on the "
          f"truncated one: {out.get('warnings')}")
    check("...but it still reports WHERE the read stopped (provenance, not silence)",
          isinstance(out.get("ended_at_line"), int) and out["ended_at_line"] > 1,
          f"nothing says how far the read got, so a truncated read and a complete one are "
          f"indistinguishable again: ended_at_line={out.get('ended_at_line')!r}")

    # A block that runs to EOF has no terminator to report.
    code, out_eof = run_cli(LIB / "extract-criteria.py", _BOLD_CONT)
    check("a block that runs to EOF reports no terminator",
          out_eof.get("ended_at_line") is None,
          f"got {out_eof.get('ended_at_line')!r}, expected None")

    # THE SUSPICIOUS CLOSE: a heading matched and nothing came out from under it.
    code, out_empty = run_cli(LIB / "extract-criteria.py", _EMPTY_BLOCK)
    w2 = " ".join(out_empty.get("warnings", []))
    check("a zero-item close IS announced",
          "NO items" in w2 and "ended at line" in w2,
          f"the heading matched and nothing was read under it, and nothing said so — which "
          f"renders as a clean empty plan downstream: {out_empty.get('warnings')}")
    check("...and it is not reported as an empty plan",
          out_empty.get("block_count", 0) >= 1 and out_empty.get("criteria") == [],
          f"block_count={out_empty.get('block_count')!r} criteria={out_empty.get('criteria')!r}")


def test_pin_reaches_the_consumer_on_a_continuation_line() -> None:
    """The one-physical-line half: a pin on line 2 must still reach the consumer."""
    code, out = run_cli(LIB / "extract-criteria.py", _PIN_ON_LINE_2)
    crit = out.get("criteria", [])
    check("a pin written on a continuation line reaches the consumer",
          len(crit) == 2 and all("Pinned by" in c for c in crit),
          f"the reader keeps only each bullet's first physical line, so a pin on line 2 is "
          f"invisible and an all-pinned plan reads as unpinned: {crit}")


def test_is_pinned_accepts_an_evals_filename() -> None:
    """`ARTIFACT_RE`'s word boundary: `run_X_evals.py` must count as naming an artifact."""
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent
                          / "skills" / "critique-plan" / "lib"))
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "wpl", Path(__file__).resolve().parent.parent
        / "skills" / "critique-plan" / "lib" / "walk-pin-lint.py")
    wpl = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(wpl)
    check("a bare run_*_evals.py filename counts as a named artifact",
          wpl.is_pinned("**X.** *Pinned by:* `run_coverage_docblind_evals.py`"),
          "`\\beval\\b` cannot match across the underscore in `_evals`, so every eval filename in "
          "the repo's own naming convention reads as unpinned — the second cause of #171's red gate")
    # PAIRED NEGATIVE: widening must not make everything pinned.
    check("...and a criterion naming NO artifact is still unpinned",
          not wpl.is_pinned("**X.** it works correctly and the behaviour is obviously right"),
          "if the widened pattern accepts prose with no artifact, the lint stops distinguishing "
          "anything and every plan reads as fully pinned")

    # And pin the DECISION, not just the two examples: the widening is confined to underscore
    # adjacency. Replay the OLD `\b`-bounded pattern beside the shipped one over a corpus that
    # straddles the boundary, and assert the set they disagree on is exactly the `_`-adjacent
    # cases. Without this, a later "widen it a bit more" that starts matching `evaluate` or
    # `different` passes both checks above while quietly making every plan read as pinned.
    import re as _re
    old = _re.compile(r"\b(grep|frame|on-sim|simulator|screenshot|doc-diff|diff|report|eval|"
                      r"snapshot|fixture|walkthrough|recording)s?\b", _re.IGNORECASE)
    corpus = {
        "run_coverage_docblind_evals.py": True,    # `_`-adjacent: the case this fix exists for
        "a_report_b": True,                        # `_`-adjacent on both sides
        "the eval": False,                         # already matched; unchanged
        "eval-driven": False,                      # `-` was already a boundary
        "re-evaluate the tradeoff": False,         # longer WORD: must stay unmatched
        "indifferent": False,                      # `diff` inside a word: must stay unmatched
        "eval2": False,                            # digit-adjacent: must stay unmatched
        "frames/0001.png": False,                  # `/`-adjacent; already matched
    }
    disagreed = {s for s in corpus if bool(old.search(s)) != bool(wpl.ARTIFACT_RE.search(s))}
    expected = {s for s, differs in corpus.items() if differs}
    check("the widening is confined to underscore adjacency",
          disagreed == expected,
          f"old and new patterns disagree on {sorted(disagreed)}, expected exactly "
          f"{sorted(expected)} — anything else means the boundary change reaches further than "
          f"`_` and the lint's discrimination moved with it")


def test_second_scan_site_also_keeps_criteria() -> None:
    """walk-pin-lint re-implements the scan, so a fix in extract_block does not reach it."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "wpl2", Path(__file__).resolve().parent.parent
        / "skills" / "critique-plan" / "lib" / "walk-pin-lint.py")
    wpl = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(wpl)
    blocks = wpl.collect_spec_walk_blocks(_BOLD_CONT)
    items = blocks[0][1] if blocks else []
    check("walk-pin-lint's own scan keeps all 3 criteria past a bold continuation",
          len(items) == 3,
          f"it collected {len(items)} of 3 — this file imports only the primitives and re-scans, "
          f"so /flow:critique-plan's lint reads a fraction of the plan and reports clean: {items}")


# ---------------------------------------------------------------- FB-0132: declared_na

_NA_PLAN = """# Plan

**Visual-walk:** N/A — no file matching `uiFilePatterns` is in scope.

**Spec-walk:**
- [ ] a criterion *Pinned by:* the `run_a_evals.py` eval
"""

_NA_WITH_ITEMS = """# Plan

**Visual-walk:** N/A — no UI
- [ ] empty state renders centered

**Spec-walk:**
- [ ] a criterion *Pinned by:* the `run_a_evals.py` eval
"""

_BARE_EMPTY = """# Plan

**Visual-walk:**

**Spec-walk:**
- [ ] a criterion *Pinned by:* the `run_a_evals.py` eval
"""


def test_declared_na() -> None:
    """`declared_na` means the heading DENIES a visual surface and lists nothing.

    Both halves are folded into the field so a consumer reads one boolean and
    cannot forget the items check — which is the direction the roadmap's option (a)
    got wrong. It proposed suppressing on "zero parsed assertions" alone, but
    `verify-build/SKILL.md` §5a assigns a bare 0-assertion block its own meaning
    ("capture the primary/launch state only"), so emptiness-keyed suppression would
    retire a documented behaviour by reinterpreting it.
    """
    b = extract_block(_NA_PLAN, "Visual-walk", anchor_label="Spec-walk")
    check("declared-na-true", b["declared_na"] is True, f"got {b['declared_na']}")
    check("declared-na-items-empty", b["items"] == [], f"got {b['items']}")
    check("declared-na-block-counted", b["block_count"] == 1, f"got {b['block_count']}")

    # PAIRED: assertions present ⇒ NOT a denial, whatever the heading says.
    b = extract_block(_NA_WITH_ITEMS, "Visual-walk", anchor_label="Spec-walk")
    check("declared-na-false-with-items", b["declared_na"] is False,
          f"a block that lists assertions is not a denial; got {b['declared_na']}")

    # PAIRED: a BARE empty block is not a denial either — it is §5a's launch-state
    # shape. This is the assertion that stops a future "simplification" to plain
    # zero-assertion from landing silently.
    b = extract_block(_BARE_EMPTY, "Visual-walk", anchor_label="Spec-walk")
    check("declared-na-false-when-bare", b["declared_na"] is False,
          f"a bare 0-assertion block means 'states unenumerated', not 'no visual "
          f"surface'; got {b['declared_na']}")

    # And the sibling field is unaffected in all three.
    for label, txt in (("na", _NA_PLAN), ("items", _NA_WITH_ITEMS), ("bare", _BARE_EMPTY)):
        b = extract_block(txt, "Visual-walk", anchor_label="Spec-walk")
        check(f"declared-na-{label}-not-demoted", b["all_demoted"] is False,
              f"got {b['all_demoted']}")


def test_na_token_set_is_anchored() -> None:
    """The denial match is a CLOSED set anchored at the heading tail, not a search.

    The roadmap entry's objection to a string match was that `n/a`, `none`,
    `not applicable` and a prose sentence are all plausible. Anchoring is what makes
    it recognise a convention instead of interpreting prose: a tail that merely
    CONTAINS a denial word does not match. Paired in both directions, because an
    accept-everything matcher and a reject-everything matcher each pass one half.
    """
    accept = [
        "**Visual-walk:** N/A",
        "**Visual-walk:** N/A — no file matching `uiFilePatterns` is in scope.",
        "**Visual-walk:** n/a - nothing visual",
        "**Visual-walk:** None — backend only",
        "**Visual-walk:** not applicable",
        "**Visual-walk:** N.A.",
        "**Visual-walk:** nil",
        "**Visual-walk** *(UI only)*: N/A",
        "### Visual-walk — N/A",
    ]
    reject = [
        "**Visual-walk:**",                                   # bare
        "**Visual-walk:** native rendering is unchanged",      # `na` prefix of a word
        "**Visual-walk:** nonetheless we captured frames",     # `none` prefix of a word
        "**Visual-walk:** the empty state renders centered",   # a real assertion inline
        "**Visual-walk:** there is none of this in scope",     # denial word, not anchored
        "**Spec-walk:** N/A",                                  # wrong label
    ]
    for line in accept:
        check(f"na-accept::{line[:44]}", heading_declares_na(line, "Visual-walk"),
              "should be read as a denial")
    for line in reject:
        check(f"na-reject::{line[:44]}", not heading_declares_na(line, "Visual-walk"),
              "should NOT be read as a denial")


def test_declared_na_cli() -> None:
    """Both consumers carry the field — `cli_main` is shared, so adding a key for one
    silently changes the other's output contract (the FB-0125 lesson, same shape)."""
    rc, out = run_cli(VISUAL, _NA_PLAN)
    check("declared-na-cli-exit", rc == 0, f"exit {rc}")
    check("declared-na-cli-flag", out.get("declared_na") is True, f"got {out.get('declared_na')}")
    check("declared-na-cli-assertions", out.get("assertions") == [], f"got {out.get('assertions')}")
    # The Spec-walk consumer emits the key too, and for ITS block it is false.
    rc, out = run_cli(CRITERIA, _NA_PLAN)
    check("declared-na-cli-criteria-exit", rc == 0, f"exit {rc}")
    check("declared-na-cli-criteria-flag", out.get("declared_na") is False,
          f"the Spec-walk block is not a denial; got {out.get('declared_na')}")


def main() -> int:
    for fn in [
        test_heading_forms,
        test_terminators,
        test_first_block_only,
        test_terminates_at_confidence,
        test_visual_decoupled,
        test_visual_category_parse,
        test_empty_and_warns,
        test_missing_file_exits_1,
        test_cli_backward_compat_keys,
        test_anchor_co_location,
        test_anchor_co_location_regression_guards,
        test_anchor_known_limitation_tiny_mode,
        test_anchor_known_limitation_retained_visual_first,
        test_bold_continuation_keeps_every_criterion,
        test_genuine_bold_heading_still_terminates,
        test_early_end_is_announced,
        test_pin_reaches_the_consumer_on_a_continuation_line,
        test_is_pinned_accepts_an_evals_filename,
        test_second_scan_site_also_keeps_criteria,
        test_anchor_co_location_cli,
        test_all_demoted,
        test_demoted_heading_skipped_regardless_of_order,
        test_all_demoted_cli,
        test_declared_na,
        test_na_token_set_is_anchored,
        test_declared_na_cli,
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
