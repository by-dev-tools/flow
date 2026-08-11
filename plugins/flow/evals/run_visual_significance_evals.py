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
              any("touches visualFilePatterns:" in s for s in o.get("visual_signals", [])),
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
