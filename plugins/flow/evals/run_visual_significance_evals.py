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
