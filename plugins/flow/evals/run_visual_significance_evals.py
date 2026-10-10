#!/usr/bin/env python3
"""Eval harness for visual-significance.py — the shared predicate that gates the
/flow:ship visual-deliverable requirement (Feature 1a).

Pins the contract verify-build + ship key on:

  significant         — uiSurface=true + a real render delta to a UI file → true.
  asset-only          — a new image/font asset with no source edit → true.
  docs-only           — no UI/asset files in the diff → false (no false positive).
  backend-only        — source change but no UI/asset files → false.
  ui-surface-false     — uiSurface:false → false even when UI files change.
  pure-refactor       — comment/whitespace-only change to a UI file → false.
  rename-only         — a UI file rename with no content → false.
  visual-walk-override — a plan Visual-walk block forces true (no UI files needed).
  override-suppressed  — uiSurface:false suppresses the override → false (recorded).
  agent-flag          — --flag-significant forces true.

Explicit (--files-from / --diff-from) mode so the change-set is synthetic +
deterministic — no git state dependency. Stdlib only.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).parent
SCRIPT = HERE.parent / "skills" / "verify-build" / "lib" / "visual-significance.py"


def run(tmp, *, config, files, diff=None, plan=None, extra=None):
    d = Path(tmp)
    cfg_p = d / "flow.config.json"
    cfg_p.write_text(json.dumps(config), encoding="utf-8")
    files_p = d / "files.txt"
    files_p.write_text(files, encoding="utf-8")
    argv = [sys.executable, str(SCRIPT), "--config", str(cfg_p), "--files-from", str(files_p)]
    if diff is not None:
        diff_p = d / "diff.txt"
        diff_p.write_text(diff, encoding="utf-8")
        argv += ["--diff-from", str(diff_p)]
    if plan is not None:
        plan_p = d / "plan.md"
        plan_p.write_text(plan, encoding="utf-8")
        argv += ["--plan", str(plan_p)]
    if extra:
        argv += extra
    proc = subprocess.run(argv, capture_output=True, text=True, check=False)
    try:
        out = json.loads(proc.stdout)
    except ValueError:
        out = {"_parse_error": proc.stdout, "_stderr": proc.stderr}
    return proc.returncode, out


# --- FB-0079 fixtures: the per-consumer pattern split -------------------------
# Modelled on the measured iOS/SwiftUI consumer where one slot could not answer
# both questions. `Insight/` had to be included for a11y (it builds the string
# VoiceOver reads), which dragged its pure-persistence neighbour into the VISUAL
# verdict; `Data/MockSleep.swift` had to be excluded for a11y (no a11y surface)
# even though it decides what the chart draws.
A11Y_ONLY_FILE = "Insight/InsightCacheStore.swift"     # a11y surface, no render path
VISUAL_ONLY_FILE = "Data/MockSleep.swift"              # render path, no a11y surface
VIEWS_FILE = "Views/HomeView.swift"                    # both

# `uiFilePatterns` here is the COMPROMISE the consumer was actually forced into
# pre-split: it had to include `Insight/` to make the a11y review fire, which is
# what dragged Insight's persistence files into the visual verdict. Keeping it in
# the fixture is what makes these cases RED against the pre-split resolver — drop
# it and the old code reaches the built-in default, which doesn't match `.swift`,
# and the assertions would pass for the wrong reason.
SPLIT_CFG = {
    "uiSurface": True,
    "uiFilePatterns": r"(^|/)(Views|Insight)/.*\.swift$",
    "a11yFilePatterns": r"(^|/)(Views|Insight)/.*\.swift$",
    "visualFilePatterns": r"(^|/)(Views|Data)/.*\.swift$",
}


A11Y_SKILL = HERE.parent / "skills" / "accessibility-review" / "SKILL.md"
SCHEMA = HERE.parent / "schema" / "flow.config.schema.json"
FP_LIB = HERE.parent / "skills" / "verify-build" / "lib"
sys.path.insert(0, str(FP_LIB))
from file_patterns import (  # type: ignore  # noqa: E402
    resolve as fp_resolve, A11Y as FP_A11Y, DEFAULT_SOURCE as FP_DEFAULT_SOURCE,
    DEFAULT_UI_PATTERN as FP_DEFAULT_UI_PATTERN)


def _extract_jq_src():
    """Pull the LIVE `UI_PATTERN_SRC=$(jq -r '<expr>' ...)` expression out of the
    a11y SKILL. Extracting beats hard-coding a copy here: a copy is a third
    implementation of the same chain, which is the fan-out the check exists to
    catch. Returns None if the line moved — the caller fails loudly rather than
    silently skipping (a vacuous pass is the FB-0010 silent-skip class)."""
    try:
        text = A11Y_SKILL.read_text(encoding="utf-8")
    except OSError:
        return None
    # Anchored on the `# flow:jq-slot-resolution` marker rather than the shell
    # variable name, so renaming the variable does not trip the guard — but deleting
    # the resolution line still does.
    m = re.search(r"#\s*flow:jq-slot-resolution\b.*?=\$\(jq -r '(.+?)' flow\.config\.json",
                  text, re.S)
    return m.group(1) if m else None


JQ_SRC_EXPR = _extract_jq_src()


def _extract_shell_defaults():
    """Every `UI_PATTERN='<literal>'` fallback assignment in the a11y SKILL. There
    are two (the unset branch and the invalid-regex branch) and BOTH must equal
    DEFAULT_UI_PATTERN — a fix applied to one and not the other is the fan-out."""
    try:
        text = A11Y_SKILL.read_text(encoding="utf-8")
    except OSError:
        return []
    return re.findall(r"UI_PATTERN='([^']+)'", text)


def _schema_default():
    try:
        props = json.loads(SCHEMA.read_text(encoding="utf-8"))["properties"]
    except (OSError, ValueError, KeyError):
        return None, None
    return (props.get("uiFilePatterns", {}).get("default"),
            {k: ("default" in props.get(k, {}))
             for k in ("visualFilePatterns", "a11yFilePatterns")})


def _have_jq():
    try:
        return subprocess.run(["jq", "--version"], capture_output=True).returncode == 0
    except OSError:
        return False


def _jq_source(tmp, expr, cfg):
    """Run the extracted jq expression over `cfg`; return the slot name it picks
    (mirroring the SKILL's own `[ -z ]` fallback to 'built-in default')."""
    p = Path(tmp) / "jqcfg.json"
    p.write_text(json.dumps(cfg), encoding="utf-8")
    out = subprocess.run(["jq", "-r", expr, str(p)], capture_output=True, text=True)
    val = out.stdout.strip()
    return val or FP_DEFAULT_SOURCE


def swift_diff(path):
    """A unified diff carrying a real (non-comment, non-whitespace) render delta."""
    return (f"diff --git a/{path} b/{path}\n"
            f"--- a/{path}\n"
            f"+++ b/{path}\n"
            "@@ -1,3 +1,3 @@\n"
            "-    let barHeight: CGFloat = 12\n"
            "+    let barHeight: CGFloat = 18\n")


REAL_TSX_DIFF = """\
diff --git a/src/Button.tsx b/src/Button.tsx
--- a/src/Button.tsx
+++ b/src/Button.tsx
@@ -1,3 +1,3 @@
-  return <button className="old">{label}</button>;
+  return <button className="primary" aria-label={label}>{label}</button>;
"""

COMMENT_ONLY_DIFF = """\
diff --git a/src/Button.css b/src/Button.css
--- a/src/Button.css
+++ b/src/Button.css
@@ -1,2 +1,2 @@
-/* old note */
+/* new note about the button */
"""

# A real content change, but entirely inside a `#if DEBUG` region — Release
# byte-identical. Needs a UI pattern that covers .swift (not in the default set).
DEBUG_ONLY_DIFF = """\
diff --git a/Sources/DebugOverlay.swift b/Sources/DebugOverlay.swift
--- a/Sources/DebugOverlay.swift
+++ b/Sources/DebugOverlay.swift
@@ -1,7 +1,7 @@
 struct DebugOverlay: View {
     var body: some View {
 #if DEBUG
-        Text("v1").font(.caption)
+        Text("v2 debug-only").font(.caption)
 #endif
         EmptyView()
     }
"""

# The #else branch of `#if DEBUG` is the RELEASE path — a change there ships
# and must still count as a real render delta.
DEBUG_ELSE_DIFF = """\
diff --git a/Sources/Badge.swift b/Sources/Badge.swift
--- a/Sources/Badge.swift
+++ b/Sources/Badge.swift
@@ -1,8 +1,8 @@
 struct Badge: View {
     var body: some View {
 #if DEBUG
         Text("debug badge")
 #else
-        Text("v1")
+        Text("v2 release label")
 #endif
     }
 }
"""

# One DEBUG-only hunk plus one real (non-DEBUG) hunk in the same file — the
# real hunk must still win (significant), with the DEBUG-only skip recorded
# as evidence rather than silently absorbed.
DEBUG_MIXED_DIFF = """\
diff --git a/Sources/Mixed.swift b/Sources/Mixed.swift
--- a/Sources/Mixed.swift
+++ b/Sources/Mixed.swift
@@ -1,6 +1,6 @@
 struct Mixed: View {
     var body: some View {
 #if DEBUG
-        Text("dbg1")
+        Text("dbg2")
 #endif
-        Text("shipped v1")
+        Text("shipped v2")
     }
 }
"""

SWIFT_CFG = {"uiSurface": True, "uiFilePatterns": r"\.swift$"}

# --- FB-0086 fixtures: a binary asset has NO `+++ b/<path>` header -------------
# Git emits only `Binary files a/… and b/… differ` for a binary change, so the
# header-based file tracking never sees it and the pure-refactor exclusion fires
# (health-tracker PR #100: an in-place font re-export read visual_significant:
# false). Fixtures span the distinguishing axis — binary × add / modify / delete —
# plus a non-asset control (FB-0079 corollary 2: pick fixtures by the axis, not
# the example in hand). `.ttf` matches DEFAULT_ASSET_PATTERN, so no uiFilePatterns
# is needed — this is the consumer's real, default-config shape.
BINARY_ASSET = "Sources/Views/Fonts/Fraunces.ttf"
BINARY_MODIFY_DIFF = (
    f"diff --git a/{BINARY_ASSET} b/{BINARY_ASSET}\n"
    "index 4472f17..ef9bf8d 100644\n"
    f"Binary files a/{BINARY_ASSET} and b/{BINARY_ASSET} differ\n")
# Add carries the path on the b/ side only (a/ is /dev/null).
BINARY_ADD_ASSET = "Sources/Views/Fonts/NewFont.ttf"
BINARY_ADD_DIFF = (
    f"diff --git a/{BINARY_ADD_ASSET} b/{BINARY_ADD_ASSET}\n"
    "new file mode 100644\n"
    "index 0000000..ef9bf8d 100644\n"
    f"Binary files /dev/null and b/{BINARY_ADD_ASSET} differ\n")
# Delete carries the path on the a/ side only (b/ is /dev/null).
BINARY_DELETE_DIFF = (
    f"diff --git a/{BINARY_ASSET} b/{BINARY_ASSET}\n"
    "deleted file mode 100644\n"
    "index 4472f17..0000000 100644\n"
    f"Binary files a/{BINARY_ASSET} and /dev/null differ\n")
# A binary file whose extension is outside the asset pattern (and no UI match) —
# proves the parser matches the path, it does not fire on every `Binary files` line.
BINARY_NONASSET = "src/data.pack"
BINARY_NONASSET_DIFF = (
    f"diff --git a/{BINARY_NONASSET} b/{BINARY_NONASSET}\n"
    "index 1111111..2222222 100644\n"
    f"Binary files a/{BINARY_NONASSET} and b/{BINARY_NONASSET} differ\n")
# Rename+modify of a binary: a NON-matching a/ path, a MATCHING b/ path. Isolates
# that BOTH sides are parsed — if the parser only inspected the a/ side (group 1),
# this would miss. The add case can't isolate this (its A-status hits the pre-
# existing new_files shortcut, so it is green with or without the parser); this
# is the b-side's real red-verify.
BINARY_RENAMED_TO_ASSET = "Sources/Views/Fonts/Fraunces.ttf"
BINARY_BOTH_SIDES_DIFF = (
    f"diff --git a/src/blob.pack b/{BINARY_RENAMED_TO_ASSET}\n"
    "similarity index 40%\n"
    "rename from src/blob.pack\n"
    f"rename to {BINARY_RENAMED_TO_ASSET}\n"
    "index 1111111..ef9bf8d 100644\n"
    f"Binary files a/src/blob.pack and b/{BINARY_RENAMED_TO_ASSET} differ\n")


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
        # 1. significant: real render delta to a UI file.
        rc, o = run(tmp, config={"uiSurface": True}, files="M\tsrc/Button.tsx", diff=REAL_TSX_DIFF)
        check("significant", rc == 0 and o.get("visual_significant") is True, f"{o}")

        # 2. asset-only: a new image asset, no source edit → significant.
        rc, o = run(tmp, config={"uiSurface": True}, files="A\tassets/logo.svg")
        check("asset-only", o.get("visual_significant") is True, f"{o}")

        # 3. docs-only: no UI/asset files → not significant (no false positive).
        rc, o = run(tmp, config={"uiSurface": True}, files="M\tREADME.md\nM\tdocs/guide.md")
        check("docs-only", o.get("visual_significant") is False, f"{o}")

        # 4. backend-only: source change, no UI/asset files → not significant.
        rc, o = run(tmp, config={"uiSurface": True, "platform": "library"},
                    files="M\tsrc/server.py\nM\tsrc/db.py")
        check("backend-only", o.get("visual_significant") is False, f"{o}")

        # 5. uiSurface:false → never significant, even with UI files in the diff.
        rc, o = run(tmp, config={"uiSurface": False}, files="M\tsrc/Button.tsx", diff=REAL_TSX_DIFF)
        check("ui-surface-false", o.get("visual_significant") is False and o.get("ui_surface") is False, f"{o}")

        # 6. pure refactor: comment-only change to a UI file → not significant.
        rc, o = run(tmp, config={"uiSurface": True}, files="M\tsrc/Button.css", diff=COMMENT_ONLY_DIFF)
        check("pure-refactor", o.get("visual_significant") is False, f"{o}")

        # 7. rename-only: a UI file rename with no content delta → not significant.
        rc, o = run(tmp, config={"uiSurface": True}, files="R\tsrc/Old.tsx\tsrc/New.tsx", diff="")
        check("rename-only", o.get("visual_significant") is False, f"{o}")

        # 8. Visual-walk override: plan declares a Visual-walk block → forces true
        #    even with NO UI files in the diff.
        plan = "## PR\n\n**Visual-walk:**\n- [ ] Empty state renders centered\n\n## Next\n"
        rc, o = run(tmp, config={"uiSurface": True}, files="M\tsrc/logic.py", plan=plan)
        check("visual-walk-override",
              o.get("visual_significant") is True and o.get("override") == "visual-walk-block", f"{o}")

        # 8b. All Visual-walk blocks demoted (qualified merged/shipped) → the active
        #     plan section declares none, so NO override even though block_count >= 1.
        #     A docs-only post-merge PR must NOT be forced visually significant off a
        #     retained block. Pre-fix, the override keyed on block_count and returned
        #     true here, routing a docs-only post-merge PR to the draft manifest.
        demoted_plan = (
            "## Recently Completed\n\n### PR #99\n\n"
            "**Spec-walk (merged #99):**\n- [x] the button renders\n\n"
            "**Visual-walk (merged #99):**\n- [ ] Empty state renders centered\n"
        )
        rc, o = run(tmp, config={"uiSurface": True}, files="M\tsrc/logic.py", plan=demoted_plan)
        demoted_warn = any("demoted" in s for s in o.get("visual_signals", []))
        check("visual-walk-all-demoted-no-override",
              o.get("visual_significant") is False and o.get("override") is None and demoted_warn, f"{o}")

        # --- FB-0138: an explicit N/A declaration must not force --------------
        #
        # Being conscientious was punished and being careless rewarded: the override
        # keyed on `block_count >= 1` and never read the block, so
        # `**Visual-walk:** N/A — no UI in this change` flipped `visual_significant`
        # to TRUE and ship §7a then demanded a walkthrough plus a visual-history
        # entry for a diff with no UI — artifacts that cannot be produced. Omitting
        # the block entirely gave the right verdict.
        #
        # FOUR cases, and they are a matrix rather than a case plus a sanity check.
        # Any one alone is satisfiable by a wrong implementation:
        #   - 8c alone  → passes on a predicate that never forces at all.
        #   - 8d alone  → passes on today's broken code.
        #   - 8e alone  → passes on a predicate keyed on emptiness, which would
        #                 retire §5a's launch-state behaviour (the roadmap's option
        #                 (a), deliberately NOT taken).
        #   - 8f alone  → passes on a predicate that ignores the plan entirely.
        na_plan = ("## PR\n\n**Visual-walk:** N/A — no UI in this change\n\n"
                   "**Spec-walk:**\n- [ ] the roadmap entry is corrected\n")
        rc, o = run(tmp, config={"uiSurface": True}, files="M\tdev-docs/roadmap.md",
                    plan=na_plan)
        na_warn = any("declares N/A" in s and "not an override" in s
                      for s in o.get("visual_signals", []))
        check("8c-na-block-does-not-force",
              o.get("visual_significant") is False and o.get("override") is None and na_warn,
              f"an explicit N/A with zero assertions must NOT force, and must SAY it "
              f"decided that (never a silent suppression): {o}")

        # 8d. PAIRED — N/A text WITH assertions still forces. Contradictory authoring;
        #     the assertions win, because the author named states to capture.
        na_items = ("## PR\n\n**Visual-walk:** N/A — no UI\n"
                    "- [ ] empty state renders centered\n\n"
                    "**Spec-walk:**\n- [ ] x\n")
        rc, o = run(tmp, config={"uiSurface": True}, files="M\tdev-docs/roadmap.md",
                    plan=na_items)
        contradiction_warn = any("declares non-applicability but" in s
                                 for s in o.get("visual_signals", []))
        check("8d-na-with-assertions-still-forces",
              o.get("visual_significant") is True and o.get("override") == "visual-walk-block",
              f"a block that lists assertions must force whatever its heading says: {o}")
        # The VERDICT alone is not the contract. A test asserting only
        # `visual_significant: true` passes whether or not the operator is told the
        # heading contradicted itself — including when the guarded `walk_extract`
        # import fell back to None. /flow:audit-coverage flagged the signal as
        # undeclared and unpinned; criterion 7 had scoped itself to the SUPPRESSED
        # branch only.
        check("8d-contradiction-is-reported",
              contradiction_warn,
              f"the contradiction must be NAMED to the operator, not silently resolved: {o}")

        # 8g. THE UN-DENIAL ARM — the one where a false match SUPPRESSES, which is the
        #     dangerous polarity. A deferral says WHEN and a redirection says ELSEWHERE;
        #     both assert a visual surface exists, so both must keep forcing. Three
        #     shapes, because the guard admitted a whole class twice before it worked.
        for label, heading in (
            ("deferral",    "**Visual-walk:** None, will fill in later"),
            ("deferral-tbd", "**Visual-walk:** N/A — TBD"),
            ("redirection", "**Visual-walk:** N/A, see the prototype for frames"),
        ):
            plan_u = (f"## PR\n\n{heading}\n\n**Spec-walk:**\n- [ ] x\n")
            rc, o = run(tmp, config={"uiSurface": True},
                        files="M\tdev-docs/roadmap.md", plan=plan_u)
            check(f"8g-{label}-still-forces",
                  o.get("visual_significant") is True
                  and o.get("override") == "visual-walk-block",
                  f"a denial that {label[:11]}s is not a denial — it asserts a visual "
                  f"surface exists, so it must keep forcing: {o}")
        # PAIRED against a genuine denial in the same block of assertions, or
        # "everything forces" would pass the three rows above.
        rc, o = run(tmp, config={"uiSurface": True}, files="M\tdev-docs/roadmap.md",
                    plan=na_plan)
        check("8g-paired-real-denial-still-suppresses",
              o.get("visual_significant") is False,
              f"and a real denial must still suppress, or the un-denial rows above are "
              f"satisfied by a predicate that never suppresses: {o}")

        # 8e. PAIRED — a BARE empty block still forces. verify-build §5a: "0 assertions
        #     in a present block → capture the primary/launch state only". That shape
        #     means "a visual surface, states unenumerated", not "no visual surface".
        #     Keying the fix on emptiness would retire that behaviour by reinterpreting
        #     it — the roadmap's option (a), rejected for this reason.
        bare_plan = "## PR\n\n**Visual-walk:**\n\n**Spec-walk:**\n- [ ] x\n"
        rc, o = run(tmp, config={"uiSurface": True}, files="M\tdev-docs/roadmap.md",
                    plan=bare_plan)
        check("8e-bare-empty-block-still-forces",
              o.get("visual_significant") is True and o.get("override") == "visual-walk-block",
              f"a bare 0-assertion block must STILL force — §5a gives it meaning, and a "
              f"false non-force ships an unseen UI with a green report: {o}")

        # 8f. PAIRED — an N/A declaration cannot suppress a REAL render delta. The
        #     file-pattern heuristic is the path that does not depend on the plan, and
        #     the fix must not have disabled it.
        rc, o = run(tmp, config={"uiSurface": True}, files="M\tsrc/Button.tsx",
                    diff=REAL_TSX_DIFF, plan=na_plan)
        check("8f-na-cannot-mask-a-real-ui-diff",
              o.get("visual_significant") is True,
              f"an N/A declaration must never suppress a genuine render delta — the "
              f"heuristic runs underneath the override: {o}")

        # 8h. THE SIGNAL BUDGET ON THE SUPPRESSION PATH. Two assertions, and they are
        #     a pair: the branch must stay SILENT about the parser's warnings (they
        #     carry plan text into the forked skip-auditor's prompt — see
        #     evals/security/test_plan_text_not_quoted.py, which owns that claim at the
        #     composed layer) while still reporting the one remedy it genuinely owes an
        #     author. A clean N/A therefore emits EXACTLY its declaration line.
        #
        #     The negative half matters because the first cut keyed the surviving
        #     report on `len(warnings)`, and `declared_na` requires `not items`, so the
        #     empty-assertions warning fires on every clean N/A FOREVER. That shipped
        #     as a permanent misleading [WARN] on the happy path in v1.57.0 (the ⚠️
        #     hedge) and must not recur: the count is keyed on `block_count`.
        rc, o = run(tmp, config={"uiSurface": True}, files="M\tdev-docs/roadmap.md",
                    plan=na_plan)
        na_warns = [x for x in o.get("visual_signals", []) if x.startswith("[WARN]")]
        # Tightened from `len(na_warns) == 1` when the declaration signal lost its
        # `[WARN]` prefix (push-further lens): ZERO warnings is the stronger claim, and
        # it is paired with the positive assertion below so the pair cannot be satisfied
        # by deleting the signal altogether (item 3). Still red under the
        # `len(warnings)` mutation, which is what 8h was written to catch.
        check("8h-clean-na-emits-no-warnings-at-all",
              not na_warns,
              f"a terminal-CORRECT reading must not warn — a [WARN] here is permanent "
              f"noise on the happy path for the life of the project: {na_warns}")
        decl = [x for x in o.get("visual_signals", []) if "declares N/A" in x]
        check("8h-clean-na-still-records-the-decision",
              len(decl) == 1 and not decl[0].startswith("[WARN]"),
              f"the decision must still be RECORDED, unprefixed — silence here would "
              f"satisfy the assertion above by deletion: {o.get('visual_signals')}")
        # Keyed on a marker only the PLAN carries, not on the absence of the string
        # "N/A" — the signal's own static prose says "an explicit N/A", so asserting
        # that was testing the message's wording rather than whether it quotes input.
        marked_na = ("## PR\n\n**Spec-walk:**\n- [ ] x\n\n"
                     "**Visual-walk:** N/A - ZZPLANMARKER no UI here\n")
        rc, o2 = run(tmp, config={"uiSurface": True}, files="M\tdev-docs/roadmap.md",
                     plan=marked_na)
        check("8h-clean-na-warn-names-a-line-number-not-the-heading",
              any("Visual-walk at line" in x for x in o2.get("visual_signals", []))
              and "ZZPLANMARKER" not in json.dumps(o2.get("visual_signals", [])),
              f"the signal must identify the block by LINE and carry no plan text: "
              f"{o2.get('visual_signals')}")

        # 8i. PAIRED with 8h — a SECOND Visual-walk block is the one case where the
        #     suppression path still owes the author a remedy: only the first block is
        #     read, so an author whose later block holds the real assertions would see
        #     silence. Reported as a COUNT (an int, non-forgeable), never as the text.
        two_block_na = (
            "## PR\n\n**Spec-walk:**\n- [ ] x\n\n**Visual-walk:** N/A - no UI\n\n"
            "## An older PR\n\n**Visual-walk:** N/A\n")
        rc, o = run(tmp, config={"uiSurface": True}, files="M\tdev-docs/roadmap.md",
                    plan=two_block_na)
        two_warns = [x for x in o.get("visual_signals", []) if x.startswith("[WARN]")]
        check("8i-two-block-na-adds-the-count-line",
              any("2 Visual-walk blocks are present" in x for x in two_warns),
              f"a second block must be reported, by count: {two_warns}")
        check("8i-two-block-na-still-suppresses",
              o.get("visual_significant") is False,
              f"the count is advisory — the declared N/A still governs the verdict: {o}")

        # 8j. THE DISCRIMINATING CASE, and it exists because 8h+8i did NOT catch the
        #     mutation they were written to catch. Re-keying the count on
        #     `len(blk["warnings"])` instead of `block_count` left BOTH green: 8h's
        #     clean plan carries 1 warning (`1 > 1` is false, so no line appears), and
        #     8i's two-block plan carries exactly 2 warnings, so the wrong key printed
        #     the RIGHT NUMBER by coincidence. Two assertions agreeing with a mutant is
        #     the "pin the DECISION, not a string that currently implies it" corollary.
        #
        #     This shape separates them: ONE Visual-walk block, TWO parser warnings.
        #     Correct code says nothing; the mutant claims "2 Visual-walk blocks are
        #     present" about a plan that has one — a false statement to an operator.
        one_block_two_warnings = (
            "**Spec-walk:**\n- [x] x\n\n**Visual-walk:** N/A - no UI\n"
            "- [] stray one\n- [] stray two\n")
        rc, o = run(tmp, config={"uiSurface": True}, files="M\tdev-docs/roadmap.md",
                    plan=one_block_two_warnings)
        check("8j-count-is-keyed-on-blocks-not-warnings",
              not any("Visual-walk blocks are present" in x
                      for x in o.get("visual_signals", [])),
              f"one block must never be reported as several — if this fires, the count "
              f"is keyed on the warning total: {o.get('visual_signals')}")
        check("8j-still-suppresses-with-malformed-lines",
              o.get("visual_significant") is False,
              f"malformed checkbox lines are not assertions, so the N/A still "
              f"governs: {o}")

        # 8k. THE POSITIVE HALF OF "the removal is SCOPED to the declared_na branch".
        #     Written because it was MISSING, and the plan criterion asserting it
        #     claimed the pairing existed (v1.62.0 staff-review). Measured: deleting
        #     BOTH surviving `signals.extend(... warnings ...)` lines left 74/74,
        #     166/166 and the security test all green — so the negative assertion
        #     ("the N/A branch forwards nothing") passed in two opposite worlds, the
        #     contract honoured AND the feature deleted. § Consistency discipline item
        #     3, in the criterion written to invoke item 3.
        #
        #     The two branches below are ABNORMAL plan states, and their warning text
        #     IS the operator's remedy — "the block sits below the active section, move
        #     it" cannot be replaced by a line number without losing the instruction.
        #     That is exactly why the N/A branch (a terminal CORRECT reading) drops its
        #     passthrough and these keep theirs, and why "scoped" is the claim rather
        #     than "removed".
        noncolocated = (
            "## Active PR\n\n**Spec-walk:**\n- [ ] x\n\n## Older PR\n\n"
            "**Spec-walk:**\n- [x] y\n\n**Visual-walk:**\n- [ ] the panel renders\n")
        rc, o = run(tmp, config={"uiSurface": True}, files="M\tdev-docs/roadmap.md",
                    plan=noncolocated)
        check("8k-noncolocated-still-forwards-the-remedy",
              any("sits BELOW the active PR's section" in x
                  for x in o.get("visual_signals", [])),
              f"the retained-block branch must still forward the parser warning that "
              f"tells the author to move it: {o.get('visual_signals')}")

        demoted_only = ("## PR\n\n**Spec-walk:**\n- [ ] x\n\n"
                        "**Visual-walk (merged #99):**\n- [ ] old\n")
        rc, o = run(tmp, config={"uiSurface": True}, files="M\tdev-docs/roadmap.md",
                    plan=demoted_only)
        check("8k-all-demoted-still-forwards-the-remedy",
              any("qualified as already-shipped/merged/demoted" in x
                  for x in o.get("visual_signals", [])),
              f"the all-demoted branch must still forward its parser warning: "
              f"{o.get('visual_signals')}")

        # 8l. THE NEAR-MISS SIGNAL AT THE COMPOSED LAYER. Added because mutating
        #     `na_near_miss` to always return None — i.e. restoring the exact silence
        #     the UX blocker described — reddened 9 checks in
        #     run_walk_extract_evals.py and left THIS suite at 76/76. The classifier
        #     was pinned; the thing an author actually sees was not. The claim is "the
        #     author is told", and that claim is made in `visual_signals`, not in a
        #     return value (§ Consistency discipline item 4's layer corollary).
        #     The PARENTHETICAL row is here because round 4's fix was pinned only at the
        #     unit layer (10 checks in run_walk_extract_evals.py) while the changelog
        #     makes a GATE claim — "both now force and say which reading they got".
        #     Measured: reverting that fix left THIS suite at 102/102. Same corollary
        #     this 8l block was written to apply, not applied to the next round's fix
        #     (/flow:staff-review, staff-engineer lens).
        for tail, want in (("N/A for this PR", "runs straight into prose"),
                           ("N/A — TBD", "says WHEN"),
                           ("N/A — see Figma", "an artifact noun is read as"),
                           ("(TBD):** N/A", "says WHEN")):
            if tail.startswith("("):
                near_plan = (f"## PR\n\n**Spec-walk:**\n- [ ] x\n\n"
                             f"**Visual-walk {tail}\n")
            else:
                near_plan = (f"## PR\n\n**Spec-walk:**\n- [ ] x\n\n"
                             f"**Visual-walk:** {tail}\n")
            rc, o = run(tmp, config={"uiSurface": True},
                        files="M\tdev-docs/roadmap.md", plan=near_plan)
            sig = o.get("visual_signals", [])
            check(f"8l-near-miss-is-reported::{tail[:22]}",
                  any("LOOKS like a denial but was NOT read as one" in x for x in sig),
                  f"a rejected denial must not be silent — this is the FB-0138 symptom "
                  f"on near-miss spellings: {sig}")
            check(f"8l-near-miss-names-the-reason::{tail[:22]}",
                  any(want in x for x in sig),
                  f"the signal must say WHICH reading it took (expected {want!r}): {sig}")
            check(f"8l-near-miss-does-not-quote-the-heading::{tail[:22]}",
                  not any(tail in x for x in sig),
                  f"CLASSIFY, never quote — this crosses into the forked "
                  f"skip-auditor's prompt: {sig}")
            # Paired: the verdict is unchanged by the new signal. A near miss still
            # forces, which is the behaviour the signal EXPLAINS rather than alters.
            check(f"8l-near-miss-still-forces::{tail[:22]}",
                  o.get("visual_significant") is True,
                  f"a rejected denial must still force: {o}")

        # 8m. THE NEAR-MISS SIGNAL ON A BLOCK THAT LISTS ASSERTIONS. All three 8l rows
        #     use zero-item blocks, so nothing exercised the authoring path where the
        #     remedy's claim is FALSE: "omit the block entirely — both give the same
        #     verdict" is true with no assertions and wrong with them, because omitting
        #     also drops §5a's per-assertion capture targets. Flagged by
        #     /flow:audit-coverage as an undeclared behaviour.
        #
        #     Note which branch this reaches: `N/A — TBD` is REJECTED by the un-denial
        #     guard, so `heading_declares_na` is false and the contradiction warning
        #     (8d) never fires — the near-miss warning is the only signal, which is why
        #     8d does not already cover it.
        na_with_items = ("## PR\n\n**Spec-walk:**\n- [ ] x\n\n"
                         "**Visual-walk:** N/A — TBD\n"
                         "- [ ] the empty state renders centered\n"
                         "- [ ] the error state is reachable\n")
        rc, o = run(tmp, config={"uiSurface": True}, files="M\tdev-docs/roadmap.md",
                    plan=na_with_items)
        near = [x for x in o.get("visual_signals", [])
                if "LOOKS like a denial but was NOT read as one" in x]
        check("8m-near-miss-fires-with-assertions", len(near) == 1,
              f"the near-miss signal must still fire: {o.get('visual_signals')}")
        check("8m-remedy-does-not-claim-omitting-is-equivalent",
              near and "gives the same verdict" not in near[0],
              f"with assertions present, omitting the block is NOT the same verdict — "
              f"it also drops §5a's capture targets: {near}")
        check("8m-remedy-says-the-assertions-are-used",
              near and "ARE being used" in near[0] and "2 listed assertions" in near[0],
              f"the remedy must tell the author their assertions are not lost: {near}")
        check("8m-still-forces", o.get("visual_significant") is True,
              f"a rejected denial with assertions must force: {o}")
        # PAIRED with 8l: the zero-item wording must still carry the equivalence claim,
        # or this assertion would pass by deleting the sentence from both branches.
        bare_na_tbd = "## PR\n\n**Spec-walk:**\n- [ ] x\n\n**Visual-walk:** N/A — TBD\n"
        rc, o = run(tmp, config={"uiSurface": True}, files="M\tdev-docs/roadmap.md",
                    plan=bare_na_tbd)
        near0 = [x for x in o.get("visual_signals", [])
                 if "LOOKS like a denial but was NOT read as one" in x]
        check("8m-paired-zero-item-keeps-the-equivalence-claim",
              near0 and "gives the same verdict" in near0[0],
              f"with no assertions, omitting the block IS equivalent and the copy must "
              f"still say so — otherwise 8m passes by deleting the sentence: {near0}")

        # 8n. THE OUTCOME CLAUSE MUST AGREE WITH THE VERDICT. Override detection runs
        #     BEFORE Gate 1, so both forcing-arm warnings used to assert "this change
        #     is therefore treated as visually significant" inside the same JSON that
        #     carried `visual_significant: false` and `override SUPPRESSED by
        #     uiSurface=false` — a signal list contradicting itself
        #     (/flow:audit-coverage). None of the 25 declared criteria exercised
        #     `uiSurface:false`, which is why nothing sent anyone here.
        #
        #     PAIRED across the config axis in BOTH branches: asserting only that the
        #     unconditional sentence is absent would pass if the clause were deleted
        #     entirely, so the uiSurface:true arm must still assert it.
        near_items = ("## PR\n\n**Spec-walk:**\n- [ ] x\n\n"
                      "**Visual-walk:** N/A for this PR\n- [ ] the panel renders\n")
        contra = ("## PR\n\n**Spec-walk:**\n- [ ] x\n\n"
                  "**Visual-walk:** N/A — backend only\n- [ ] the panel renders\n")
        for plan_label, plan_text, needle in (
                ("near-miss", near_items, "LOOKS like a denial"),
                ("contradiction", contra, "declares non-applicability but the block")):
            rc, o_off = run(tmp, config={"uiSurface": False},
                            files="M\tsrc/Button.tsx", diff=REAL_TSX_DIFF, plan=plan_text)
            rc, o_on = run(tmp, config={"uiSurface": True},
                           files="M\tsrc/Button.tsx", diff=REAL_TSX_DIFF, plan=plan_text)
            w_off = [x for x in o_off.get("visual_signals", []) if needle in x]
            w_on = [x for x in o_on.get("visual_signals", []) if needle in x]
            check(f"8n-{plan_label}-fires-on-both-configs",
                  len(w_off) == 1 and len(w_on) == 1,
                  f"the warning must be recorded either way: off={w_off} on={w_on}")
            check(f"8n-{plan_label}-no-false-significance-claim-when-uisurface-false",
                  w_off and "uiSurface:false" in w_off[0]
                  and "is therefore treated as visually significant" not in w_off[0],
                  f"on uiSurface:false the verdict is {o_off.get('visual_significant')}, "
                  f"so the warning must not assert significance: {w_off}")
            check(f"8n-{plan_label}-paired-claims-significance-when-uisurface-true",
                  w_on and "is therefore treated as visually significant" in w_on[0],
                  f"on uiSurface:true it must still say so — otherwise the assertion "
                  f"above passes by deleting the clause: {w_on}")
            check(f"8n-{plan_label}-verdict-matches-config",
                  o_off.get("visual_significant") is False
                  and o_on.get("visual_significant") is True,
                  f"off={o_off.get('visual_significant')} on={o_on.get('visual_significant')}")

        # Verb agreement on the items arm — the count is in hand, so use it.
        one_item = ("## PR\n\n**Spec-walk:**\n- [ ] x\n\n"
                    "**Visual-walk:** N/A for this PR\n- [ ] only one\n")
        rc, o = run(tmp, config={"uiSurface": True}, files="M\tdev-docs/roadmap.md",
                    plan=one_item)
        w = [x for x in o.get("visual_signals", []) if "LOOKS like a denial" in x]
        check("8n-singular-verb-agreement",
              w and "1 listed assertion IS being used" in w[0],
              f"singular must read 'assertion IS', not 'assertion ARE': {w}")

        # 8o. THE SUPPRESSING FLOOR NAMES WHAT DECIDED IT. PAIRED with the forcing
        #     branch, which already named `visual_src` — the suppressing one said only
        #     "diff touches no UI or asset files", reading as a measurement of the diff
        #     when it is a decision by an allow-list. On a project that has narrowed
        #     `uiFilePatterns` (flow's own names four files) a brand-new browser-UI file
        #     produces exactly that line. Absent-vs-no (FB-0082) on the expensive
        #     polarity, and it is the floor every non-forcing plan arm falls through to
        #     (/flow:staff-review, design-engineer lens).
        rc, o = run(tmp, config={"uiSurface": True}, files="M\tdev-docs/roadmap.md")
        floor = [x for x in o.get("visual_signals", []) if "touches no UI" in x]
        check("8o-suppressing-floor-names-its-pattern-source",
              floor and "pattern from" in floor[0] and "NOT examined" in floor[0],
              f"the suppressing floor must name the pattern that decided it: {floor}")
        rc, o = run(tmp, config={"uiSurface": True}, files="M\tsrc/Button.tsx",
                    diff=REAL_TSX_DIFF)
        forcing = [x for x in o.get("visual_signals", []) if "touches UI files" in x]
        check("8o-paired-forcing-branch-still-names-its-source",
              forcing and "pattern from" in forcing[0],
              f"the forcing branch must keep naming its source — otherwise 8o could be "
              f"satisfied by deleting the attribution from both: {forcing}")

        # 8p. A BROKEN PARSER IMPORT IS LOUD, not a silent false. With `walk_extract`
        #     unimportable the whole plan-override path vanishes, and it used to do so
        #     in total silence: `visual_significant: false`, `override: null`, exit 0,
        #     ZERO signals — "I could not look" rendered identically to "I looked and
        #     found nothing" (FB-0082), in a sensitivePaths gate. Run against a mirrored
        #     lib dir whose `walk_extract.py` raises, because the import is module-level
        #     and cannot be broken in-process after the fact.
        # `tmp` is a str in this harness, not a Path.
        tmpp = Path(tmp)
        broken = tmpp / "brokenlib"
        broken.mkdir(exist_ok=True)
        for f in SCRIPT.parent.glob("*.py"):
            (broken / f.name).write_text(f.read_text(encoding="utf-8"), encoding="utf-8")
        (broken / "walk_extract.py").write_text(
            'raise ImportError("simulated partial install")\n', encoding="utf-8")
        (tmpp / "broken-plan.md").write_text(
            "## PR\n\n**Spec-walk:**\n- [ ] x\n\n**Visual-walk:**\n- [ ] renders\n",
            encoding="utf-8")
        (tmpp / "broken-cfg.json").write_text(
            json.dumps({"uiSurface": True, "platform": "web"}), encoding="utf-8")
        (tmpp / "broken-files.txt").write_text("src/logic.py\n", encoding="utf-8")
        bp = subprocess.run(
            [sys.executable, str(broken / SCRIPT.name),
             "--config", str(tmpp / "broken-cfg.json"),
             "--plan", str(tmpp / "broken-plan.md"),
             "--files-from", str(tmpp / "broken-files.txt")],
            capture_output=True, text=True, timeout=60)
        try:
            bo = json.loads(bp.stdout)
        except ValueError:
            bo = {}
        bsig = bo.get("visual_signals", [])
        check("8p-broken-parser-import-is-reported",
              any("could not be imported" in x and "COULD NOT" in x for x in bsig),
              f"a gate that cannot read the plan must say so — a bare false here is "
              f"indistinguishable from 'the plan declared nothing': rc={bp.returncode} "
              f"signals={bsig}")
        # PAIRED: the healthy path must NOT carry that warning, or the assertion above
        # could be satisfied by emitting it unconditionally.
        rc, o = run(tmp, config={"uiSurface": True}, files="M\tsrc/logic.py")
        check("8p-paired-healthy-import-is-silent-about-it",
              not any("could not be imported" in x
                      for x in o.get("visual_signals", [])),
              f"the healthy path must not claim a broken import: {o.get('visual_signals')}")

        # 9. override suppressed by uiSurface:false (recorded, not honored).
        rc, o = run(tmp, config={"uiSurface": False}, files="M\tsrc/logic.py", plan=plan)
        sup = any("SUPPRESSED" in s for s in o.get("visual_signals", []))
        check("override-suppressed", o.get("visual_significant") is False and sup, f"{o}")

        # 10. agent flag forces true.
        rc, o = run(tmp, config={"uiSurface": True}, files="M\tsrc/logic.py",
                    extra=["--flag-significant", "--flag-reason", "canvas render changed"])
        check("agent-flag",
              o.get("visual_significant") is True and o.get("override") == "agent-flag", f"{o}")

        # 10b. DEBUG-only change to a matched .swift file → NOT significant
        #      (Release build is byte-identical).
        rc, o = run(tmp, config=SWIFT_CFG, files="M\tSources/DebugOverlay.swift", diff=DEBUG_ONLY_DIFF)
        check("debug-only-not-significant", o.get("visual_significant") is False, f"{o}")
        check(
            "debug-only-signal-recorded",
            any("#if DEBUG" in s for s in o.get("visual_signals", [])),
            f"{o}",
        )

        # --- FB-0079: the per-consumer pattern split -------------------------
        # 10b-1. BACK-COMPAT (the load-bearing one). A project that sets ONLY
        #        uiFilePatterns must behave exactly as it did pre-split: the
        #        shared slot still drives the VISUAL verdict, both ways.
        ui_only = {"uiSurface": True, "uiFilePatterns": r"(^|/)(Views|Insight)/.*\.swift$"}
        rc, o = run(tmp, config=ui_only, files=f"M\t{VIEWS_FILE}", diff=swift_diff(VIEWS_FILE))
        check("fb78-backcompat-ui-only-matches", o.get("visual_significant") is True, f"{o}")
        rc, o = run(tmp, config=ui_only, files=f"M\t{VISUAL_ONLY_FILE}",
                    diff=swift_diff(VISUAL_ONLY_FILE))
        check("fb78-backcompat-ui-only-excludes",
              o.get("visual_significant") is False,
              f"uiFilePatterns must still be the visual ruler when it is the only slot set: {o}")

        # 10b-2. The consumer's actual over-flagging bug. A file with an a11y
        #        surface but NO render path must NOT be visually significant once
        #        visualFilePatterns excludes it — even though a11yFilePatterns
        #        (correctly) includes it. Pre-split this was forced to true.
        rc, o = run(tmp, config=SPLIT_CFG, files=f"M\t{A11Y_ONLY_FILE}",
                    diff=swift_diff(A11Y_ONLY_FILE))
        check("fb78-a11y-only-file-not-visual",
              o.get("visual_significant") is False,
              f"a11y-surface-only file must not demand visual deliverables: {o}")

        # 10b-3. The mirror. A render-only file IS visually significant even
        #        though a11yFilePatterns excludes it — no Visual-walk workaround.
        rc, o = run(tmp, config=SPLIT_CFG, files=f"M\t{VISUAL_ONLY_FILE}",
                    diff=swift_diff(VISUAL_ONLY_FILE))
        check("fb78-visual-only-file-is-visual",
              o.get("visual_significant") is True,
              f"render-only file must be visually significant without a Visual-walk block: {o}")

        # 10b-4. a11yFilePatterns alone must have ZERO effect on the visual
        #        verdict — with no visual/ui slot set, the built-in default
        #        applies, and it does not match .swift.
        rc, o = run(tmp, config={"uiSurface": True,
                                 "a11yFilePatterns": r"(^|/)Insight/.*\.swift$"},
                    files=f"M\t{A11Y_ONLY_FILE}", diff=swift_diff(A11Y_ONLY_FILE))
        check("fb78-a11y-slot-does-not-leak-into-visual",
              o.get("visual_significant") is False,
              f"a11yFilePatterns must not widen the visual pattern: {o}")

        # 10b-5. visualFilePatterns WINS over uiFilePatterns when both are set.
        rc, o = run(tmp, config={"uiSurface": True,
                                 "uiFilePatterns": r"(^|/)Insight/.*\.swift$",
                                 "visualFilePatterns": r"(^|/)Data/.*\.swift$"},
                    files=f"M\t{A11Y_ONLY_FILE}", diff=swift_diff(A11Y_ONLY_FILE))
        check("fb78-visual-slot-overrides-shared",
              o.get("visual_significant") is False,
              f"visualFilePatterns must take precedence over uiFilePatterns: {o}")

        # 10b-6. The signal NAMES the slot that supplied the pattern — with three
        #        possible sources, "diff touches uiFilePatterns" would point at the
        #        wrong knob as often as the right one.
        rc, o = run(tmp, config=SPLIT_CFG, files=f"M\t{VIEWS_FILE}", diff=swift_diff(VIEWS_FILE))
        check("fb78-signal-names-source-slot",
              any("pattern from visualFilePatterns)" in s for s in o.get("visual_signals", [])),
              f"{o}")

        # 10b-7. An unusable pattern degrades to the default with a warning that
        #        names the OFFENDING slot, not a generic 'uiFilePatterns'.
        rc, o = run(tmp, config={"uiSurface": True, "visualFilePatterns": "([unclosed"},
                    files="M\tsrc/Button.tsx", diff=REAL_TSX_DIFF)
        check("fb78-invalid-slot-warns-by-name",
              o.get("visual_significant") is True
              and any("visualFilePatterns" in s and "[WARN]" in s
                      for s in o.get("visual_signals", [])),
              f"invalid visualFilePatterns must warn by name and fall back to the default: {o}")

        # 10b-8. CROSS-RUNTIME JOIN. The resolution chain is implemented twice, in
        #        two languages: file_patterns.resolve() in Python, and a jq
        #        expression in accessibility-review/SKILL.md. A "keep these in sync"
        #        comment is not a check — the first cut of file_patterns.py carried
        #        exactly such a comment and transcribed the REJECTED jq form, so the
        #        canonical module contradicted the shipped shell in the same commit.
        #        This extracts the LIVE expression from the SKILL and runs it.
        check("fb79-jq-mirror-extractable", JQ_SRC_EXPR is not None,
              f"could not extract UI_PATTERN_SRC's jq from {A11Y_SKILL}; if the line was "
              f"reworded, update _extract_jq_src — do not delete this check")
        # NON-STRING shapes are the point, not padding: jq counts [], {} and 0 as
        # non-empty while Python truthiness does not, so an un-guarded jq select makes
        # the a11y gate and the audit resolve DIFFERENT slots for the same config.
        # The schema forbids these values; a hand-edited config can still carry them,
        # which is why compile_for catches TypeError at all.
        if JQ_SRC_EXPR and _have_jq():
            for cfg in ({}, {"uiFilePatterns": "UI"}, {"a11yFilePatterns": "A11Y"},
                        {"uiFilePatterns": "UI", "a11yFilePatterns": "A11Y"},
                        {"a11yFilePatterns": "", "uiFilePatterns": "UI"},
                        {"uiFilePatterns": "", "a11yFilePatterns": ""},
                        {"a11yFilePatterns": [], "uiFilePatterns": "UI"},
                        {"a11yFilePatterns": {}, "uiFilePatterns": "UI"},
                        {"a11yFilePatterns": 0, "uiFilePatterns": "UI"},
                        {"a11yFilePatterns": False, "uiFilePatterns": "UI"},
                        {"a11yFilePatterns": None, "uiFilePatterns": "UI"},
                        # TRUTHY non-strings. The falsy ones above agree by accident
                        # (jq's `// ""` collapses them); these are the shapes that
                        # actually diverged under bare Python truthiness, and an array
                        # is the obvious hand-edit since most pattern knobs take lists.
                        {"a11yFilePatterns": ["\\.tsx$"], "uiFilePatterns": "UI"},
                        {"a11yFilePatterns": {"a": 1}, "uiFilePatterns": "UI"},
                        {"a11yFilePatterns": 1, "uiFilePatterns": "UI"},
                        {"a11yFilePatterns": True, "uiFilePatterns": "UI"},
                        {"visualFilePatterns": ["x"], "uiFilePatterns": "UI"}):
                shell_src = _jq_source(tmp, JQ_SRC_EXPR, cfg)
                _, py_src, _ = fp_resolve(cfg, FP_A11Y)
                check(f"fb79-jq-matches-python:{json.dumps(cfg, sort_keys=True)}",
                      shell_src == py_src,
                      f"shell resolved slot {shell_src!r}, Python resolved {py_src!r} — "
                      f"the a11y gate and the Python resolver disagree about which slot wins")
        elif JQ_SRC_EXPR:
            # NOT a vacuous pass: jq is a declared prerequisite of the whole pipeline
            # (/flow:ship Step 1.5 hard-blocks without it), so its absence here means
            # the environment changed — which is signal, not an exemption. A green
            # check name that measured nothing is the FB-0010 silent-skip class.
            check("fb79-jq-matches-python", False,
                  "jq not on PATH — cross-runtime parity is UNVERIFIED, not clean")

        # 10b-9. The DEFAULT literal is the other half of the cross-runtime contract.
        #        Parity on which SLOT wins is worthless if the two runtimes disagree
        #        about what the fallback pattern IS. Add an extension in one place and
        #        this fails, instead of CI staying green while the a11y gate and the
        #        visual predicate disagree about what a UI file is.
        shell_defaults = _extract_shell_defaults()
        check("fb79-shell-defaults-extractable", len(shell_defaults) >= 2,
              f"expected >=2 UI_PATTERN='...' fallbacks in {A11Y_SKILL}, found "
              f"{len(shell_defaults)} — if the shell was restructured, update "
              f"_extract_shell_defaults; do not delete this check")
        for i, lit in enumerate(shell_defaults):
            check(f"fb79-shell-default-matches-python:{i}", lit == FP_DEFAULT_UI_PATTERN,
                  f"shell fallback {lit!r} != DEFAULT_UI_PATTERN {FP_DEFAULT_UI_PATTERN!r}")
        schema_default, per_consumer_defaults = _schema_default()
        check("fb79-schema-default-matches-python", schema_default == FP_DEFAULT_UI_PATTERN,
              f"schema uiFilePatterns.default {schema_default!r} != {FP_DEFAULT_UI_PATTERN!r}")
        # The per-consumer slots must NOT declare a default — they fall back to
        # uiFilePatterns, and a stated default would contradict the chain.
        check("fb79-per-consumer-slots-have-no-default",
              per_consumer_defaults == {"visualFilePatterns": False, "a11yFilePatterns": False},
              f"per-consumer slots must have no schema default: {per_consumer_defaults}")

        # 10b-10. BROKEN INSTALL. No eval exercised the import-failure branch at all,
        #         so the one change on this branch that alters a SHIP-BLOCKING verdict
        #         was unpinned. Fails CLOSED on a UI project; still lets uiSurface:false
        #         win, because that gate is documented everywhere as unconditional.
        # Simulate the broken install on a COPY of the lib — never by mutating the
        # working tree. A try/finally restore is exception-safe but not signal-safe:
        # a cancelled CI run or SIGTERM between the move and the restore would leave
        # the checkout broken. Copy, delete from the copy, run the copied script.
        import shutil as _shutil
        broken_lib = Path(tmp) / "broken-lib"
        _shutil.copytree(str(FP_LIB), str(broken_lib))
        (broken_lib / "file_patterns.py").unlink()
        broken_script = broken_lib / "visual-significance.py"
        for cfg, want_sig in (({"uiSurface": True}, True), ({"uiSurface": False}, False)):
            label = "ui" if want_sig else "headless"
            d = Path(tmp) / f"bi-{label}"
            d.mkdir(exist_ok=True)
            (d / "flow.config.json").write_text(json.dumps(cfg), encoding="utf-8")
            (d / "files.txt").write_text("M\tsrc/Button.tsx", encoding="utf-8")
            proc = subprocess.run(
                [sys.executable, str(broken_script), "--config", str(d / "flow.config.json"),
                 "--files-from", str(d / "files.txt")],
                capture_output=True, text=True, check=False)
            try:
                o = json.loads(proc.stdout)
            except ValueError:
                o = {"_stdout": proc.stdout, "_stderr": proc.stderr}
            check(f"fb79-broken-install-fails-closed:{label}",
                  proc.returncode == 2 and o.get("visual_significant") is want_sig
                  and o.get("ui_surface") is want_sig,
                  f"expected rc=2 + visual_significant={want_sig}: rc={proc.returncode} {o}")
            check(f"fb79-broken-install-names-remedy:{label}",
                  any("Reinstall the plugin" in sig for sig in o.get("visual_signals", [])),
                  f"the warning must name the fix: {o.get('visual_signals')}")

        # 10c. A change in the #else (RELEASE) branch of `#if DEBUG` DOES ship —
        #      must still count as significant.
        rc, o = run(tmp, config=SWIFT_CFG, files="M\tSources/Badge.swift", diff=DEBUG_ELSE_DIFF)
        check("debug-else-branch-significant", o.get("visual_significant") is True, f"{o}")

        # 10d. Mixed: one DEBUG-only hunk + one real hunk in the same file — the
        #      real hunk must still win, with the DEBUG-only skip recorded too.
        rc, o = run(tmp, config=SWIFT_CFG, files="M\tSources/Mixed.swift", diff=DEBUG_MIXED_DIFF)
        check("debug-mixed-still-significant", o.get("visual_significant") is True, f"{o}")
        check(
            "debug-mixed-signal-recorded",
            any("#if DEBUG" in s for s in o.get("visual_signals", [])),
            f"{o}",
        )

        # --- FB-0086: binary assets have no `+++ b/<path>` header ------------
        # 10e. In-place binary MODIFY of a matched asset → significant. This is
        #      the reported bug: a font re-export at the same path read false.
        rc, o = run(tmp, config={"uiSurface": True}, files=f"M\t{BINARY_ASSET}",
                    diff=BINARY_MODIFY_DIFF)
        check("binary-modify-significant", o.get("visual_significant") is True,
              f"in-place binary asset re-export must be visually significant: {o}")

        # 10f. Binary ADD → significant. REGRESSION CONTROL, not a red-verify: an
        #      A-status file already hits the pre-existing `new_files` shortcut, so
        #      this stays green with OR without the parser. Kept to pin that a new
        #      binary asset carrying a `Binary files /dev/null and b/…` diff stays
        #      significant (the report's `A NewFont.ttf = True` baseline). The
        #      b-side parser's real red-verify is 10f-2 below.
        rc, o = run(tmp, config={"uiSurface": True}, files=f"A\t{BINARY_ADD_ASSET}",
                    diff=BINARY_ADD_DIFF)
        check("binary-add-significant", o.get("visual_significant") is True,
              f"a new binary asset must be visually significant: {o}")

        # 10f-2. Binary rename+modify: NON-matching a/ path, MATCHING b/ path, and
        #        status M (so new_files does NOT cover it). RED pre-fix, and it also
        #        fails if the parser inspects only the a/ side — the real proof that
        #        BOTH sides of the `Binary files … differ` line are parsed.
        rc, o = run(tmp, config={"uiSurface": True}, files=f"M\t{BINARY_RENAMED_TO_ASSET}",
                    diff=BINARY_BOTH_SIDES_DIFF)
        check("binary-both-sides-checked", o.get("visual_significant") is True,
              f"a matched path on the b/ side alone must be significant: {o}")

        # 10g. Binary DELETE, via the a-side (b/ is /dev/null). Deliberate call
        #      (see history): removing a rendered asset changes what draws →
        #      significant. RED pre-fix (D is excluded from new_files + diff blind).
        rc, o = run(tmp, config={"uiSurface": True}, files=f"D\t{BINARY_ASSET}",
                    diff=BINARY_DELETE_DIFF)
        check("binary-delete-significant", o.get("visual_significant") is True,
              f"deleting a rendered binary asset must be visually significant: {o}")

        # 10h. NON-asset binary change → not significant. The parser matches the
        #      path against the patterns; it does not fire on every Binary line.
        rc, o = run(tmp, config={"uiSurface": True}, files=f"M\t{BINARY_NONASSET}",
                    diff=BINARY_NONASSET_DIFF)
        check("binary-nonasset-not-significant", o.get("visual_significant") is False,
              f"a non-asset binary change must NOT be visually significant: {o}")

        # 11. malformed config degrades to uiSurface=true default (loud), never crash.
        d = Path(tmp)
        bad = d / "bad.json"
        bad.write_text("{not json", encoding="utf-8")
        files_p = d / "f2.txt"
        files_p.write_text("M\tsrc/Button.tsx", encoding="utf-8")
        diff_p = d / "d2.txt"
        diff_p.write_text(REAL_TSX_DIFF, encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), "--config", str(bad),
             "--files-from", str(files_p), "--diff-from", str(diff_p)],
            capture_output=True, text=True, check=False)
        ok = proc.returncode == 0 and '"visual_significant": true' in proc.stdout and "WARN" in proc.stdout
        check("malformed-config-degrades", ok, f"rc={proc.returncode} out={proc.stdout[:200]!r}")

    # 12. GIT MODE (no --files-from): seed a temp repo with an origin/main ref so the
    #     real `git diff origin/main...HEAD` path runs — covers the failure-open class
    #     where a stale/absent LOCAL main would diff against the wrong base (staff-review
    #     finding). A new .tsx on a feature branch must read visually significant.
    import os
    def git(args, cwd):
        env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t",
                   GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
        return subprocess.run(["git", *args], cwd=cwd, env=env, capture_output=True, text=True)
    with tempfile.TemporaryDirectory() as repo:
        git(["init", "-q", "-b", "main"], repo)
        (Path(repo) / "flow.config.json").write_text('{"uiSurface": true}', encoding="utf-8")
        (Path(repo) / "README.md").write_text("base\n", encoding="utf-8")
        git(["add", "-A"], repo); git(["commit", "-qm", "base"], repo)
        base_sha = git(["rev-parse", "HEAD"], repo).stdout.strip()
        # Synthesize the remote-tracking refs the helper prefers (origin/main + HEAD).
        git(["update-ref", "refs/remotes/origin/main", base_sha], repo)
        git(["symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/main"], repo)
        git(["checkout", "-q", "-b", "feature"], repo)
        (Path(repo) / "Button.tsx").write_text("export const B = () => <button/>;\n", encoding="utf-8")
        git(["add", "-A"], repo); git(["commit", "-qm", "ui"], repo)
        proc = subprocess.run([sys.executable, str(SCRIPT), "--config", "flow.config.json"],
                              cwd=repo, capture_output=True, text=True)
        try:
            o = json.loads(proc.stdout)
        except ValueError:
            o = {"_err": proc.stdout, "_stderr": proc.stderr}
        check("git-mode-significant", o.get("visual_significant") is True,
              f"new .tsx on feature branch should be significant in git mode: {o}")
        # A docs-only commit on top must NOT be significant (no false positive in git mode).
        (Path(repo) / "GUIDE.md").write_text("docs\n", encoding="utf-8")
        git(["add", "-A"], repo); git(["commit", "-qm", "docs"], repo)
        git(["update-ref", "refs/remotes/origin/main", git(["rev-parse", "HEAD~1"], repo).stdout.strip()], repo)
        # Re-point origin/main to the UI commit so the only delta vs base is the docs file.
        proc2 = subprocess.run([sys.executable, str(SCRIPT), "--config", "flow.config.json"],
                               cwd=repo, capture_output=True, text=True)
        o2 = json.loads(proc2.stdout) if proc2.stdout.strip().startswith("{") else {}
        check("git-mode-docs-only", o2.get("visual_significant") is False,
              f"docs-only delta vs base should not be significant: {o2}")

    print(f"\n{total - fails}/{total} checks passed.")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
