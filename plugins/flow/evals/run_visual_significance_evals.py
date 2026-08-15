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
