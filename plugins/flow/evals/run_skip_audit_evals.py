#!/usr/bin/env python3
"""Eval harness for skip-audit-checks.py — the mechanical ground-truth engine
behind /flow:audit-skips (Feature 2).

Pins the five acceptance cases from the task spec (mechanical layer):

  case1-ready        — visually-significant PR, fresh buffer w/ frames + PASS +
                       a visual-history entry → every audited stage LEGITIMATE.
  case2-shortcircuit — SAME PR but verify-build asserted PASS with NO fresh buffer
                       for HEAD → verify-build SHOULD-RE-RUN; visual-verification
                       SHOULD-RE-RUN (missing walkthrough).
  case3-docsonly     — docs-only PR: verify-build + a11y + security skips all
                       LEGITIMATE; no visual gate (no false positives).
  case4-library      — platform:library: verify-build skip LEGITIMATE; not visual.
  case5-nosim        — visually-significant on a no-sim host: verify-build ran with
                       an honest Unknown + 0 frames → LEGITIMATE; visual-verification
                       SHOULD-RE-RUN (frames uncapturable).

Plus targeted contradiction checks (a skip whose reason the diff/config refutes).
Explicit (--files-from/--head-sha/--branch + temp buffers/config) so there is no
git-state dependency. Stdlib only.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).parent
SCRIPT = HERE.parent / "skills" / "audit-skips" / "lib" / "skip-audit-checks.py"

BRANCH = "claude/visual-feature"
SHA = "abc1234"

REAL_TSX_DIFF = """\
diff --git a/src/Button.tsx b/src/Button.tsx
--- a/src/Button.tsx
+++ b/src/Button.tsx
@@ -1,3 +1,3 @@
-  return <button>{label}</button>;
+  return <button className="primary" aria-label={label}>{label}</button>;
"""


def make_buffer(path, *, branch, sha, verdict, frames, visual_significant=True):
    crit = {
        "text": "Empty state renders",
        "provenance": "adversarial-judged",
        "adversarial_cases": [],
        "observations": [{"type": "screenshot", "content": f"assets/s{i}.png"} for i in range(frames)],
        "verdicts": {
            "correctness": {"verdict": verdict, "evidence": ["a", "b"], "notes": ""},
            "regression": {"verdict": "PASS", "evidence": ["a", "b"], "notes": ""},
            "scope-creep": {"verdict": "PASS", "evidence": ["a", "b"], "notes": ""},
        },
        "aggregated_verdict": verdict,
    }
    buf = {
        "schema_version": "1.0",
        "metadata": {"branch": branch, "head_sha_short": sha, "plugin_version": "test",
                     "platform_hint": "web", "visual_significant": visual_significant},
        "overall_verdict": verdict,
        "exit_code": 0 if verdict == "PASS" else 1,
        "criteria": [crit],
        "not_tested": [],
    }
    Path(path).write_text(json.dumps(buf), encoding="utf-8")


def run(tmp, *, config, report, files, diff=None, vh_text=None):
    d = Path(tmp)
    cfg_p = d / "flow.config.json"
    cfg_p.write_text(json.dumps(config), encoding="utf-8")
    rep_p = d / "report.json"
    rep_p.write_text(json.dumps(report), encoding="utf-8")
    files_p = d / "files.txt"
    files_p.write_text(files, encoding="utf-8")
    argv = [sys.executable, str(SCRIPT), "--report", str(rep_p), "--config", str(cfg_p),
            "--head-sha", SHA, "--branch", BRANCH, "--files-from", str(files_p)]
    if diff is not None:
        diff_p = d / "diff.txt"
        diff_p.write_text(diff, encoding="utf-8")
        argv += ["--diff-from", str(diff_p)]
    proc = subprocess.run(argv, capture_output=True, text=True, check=False)
    try:
        out = json.loads(proc.stdout)
    except ValueError:
        out = {"_parse_error": proc.stdout, "_stderr": proc.stderr}
    return out


def verdict_of(result, name):
    for s in result.get("stages", []):
        if s.get("name") == name:
            return s.get("mechanical")
    return None


def main() -> int:
    fails = 0
    total = 0

    def check(label, cond, detail=""):
        nonlocal fails, total
        total += 1
        print(f"{'PASS' if cond else 'FAIL'}  [{label}]" + ("" if cond else f" {detail}"))
        if not cond:
            fails += 1

    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        buf_path = str(d / "findings.json")
        vh_path = str(d / "visual-history.html")
        ui_cfg = {"uiSurface": True, "verifyFindingsPath": buf_path, "visualHistoryPath": vh_path}

        # --- case 1: ready (all LEGITIMATE) ---
        make_buffer(buf_path, branch=BRANCH, sha=SHA, verdict="PASS", frames=2)
        Path(vh_path).write_text(f"<html>entry on branch {BRANCH}</html>", encoding="utf-8")
        report = {"stages": [
            {"name": "verify-build", "status": "ran", "verdict": "PASS"},
            {"name": "security", "status": "ran"},
            {"name": "accessibility", "status": "ran"},
            {"name": "audit-coverage", "status": "ran"},
            {"name": "visual-verification", "status": "ran"},
        ]}
        r = run(tmp, config=ui_cfg, report=report, files="M\tsrc/Button.tsx", diff=REAL_TSX_DIFF)
        check("case1-visual-significant", r.get("context", {}).get("visual_significant") is True, f"{r.get('context')}")
        check("case1-all-legitimate", r.get("summary", {}).get("should_re_run") == 0, f"{r.get('summary')}")
        check("case1-verify-legit", verdict_of(r, "verify-build") == "LEGITIMATE", f"{verdict_of(r,'verify-build')}")
        check("case1-visual-legit", verdict_of(r, "visual-verification") == "LEGITIMATE")

        # --- case 2: verify-build short-circuited (PASS asserted, stale/absent buffer) ---
        make_buffer(buf_path, branch=BRANCH, sha="old9999", verdict="PASS", frames=2)  # stale sha
        r = run(tmp, config=ui_cfg, report=report, files="M\tsrc/Button.tsx", diff=REAL_TSX_DIFF)
        check("case2-verify-rerun", verdict_of(r, "verify-build") == "SHOULD-RE-RUN", f"{r.get('stages')}")
        check("case2-visual-rerun", verdict_of(r, "visual-verification") == "SHOULD-RE-RUN")
        # missing buffer entirely is also SHOULD-RE-RUN
        Path(buf_path).unlink()
        r2 = run(tmp, config=ui_cfg, report=report, files="M\tsrc/Button.tsx", diff=REAL_TSX_DIFF)
        check("case2-no-buffer-rerun", verdict_of(r2, "verify-build") == "SHOULD-RE-RUN", f"{verdict_of(r2,'verify-build')}")

        # --- case 3: docs-only (no false positives) ---
        report3 = {"stages": [
            {"name": "verify-build", "status": "skipped", "skip_reason": "doc-only"},
            {"name": "security", "status": "skipped", "skip_reason": "doc-only"},
            {"name": "accessibility", "status": "skipped", "skip_reason": "no UI in diff"},
            {"name": "audit-coverage", "status": "skipped", "skip_reason": "no behavior in diff"},
            {"name": "visual-verification", "status": "skipped"},
        ]}
        r = run(tmp, config=ui_cfg, report=report3, files="M\tREADME.md\nM\tdocs/x.md")
        check("case3-not-visual", r.get("context", {}).get("visual_significant") is False)
        check("case3-all-legit", r.get("summary", {}).get("should_re_run") == 0, f"{r.get('summary')} {r.get('stages')}")
        check("case3-visual-legit", verdict_of(r, "visual-verification") == "LEGITIMATE")

        # --- case 4: backend/library ---
        lib_cfg = {"uiSurface": True, "platform": "library", "verifyFindingsPath": buf_path, "visualHistoryPath": vh_path}
        report4 = {"stages": [
            {"name": "verify-build", "status": "skipped", "skip_reason": "platform library"},
            {"name": "security", "status": "ran"},
            {"name": "audit-coverage", "status": "ran"},
        ]}
        r = run(tmp, config=lib_cfg, report=report4, files="M\tsrc/server.py")
        check("case4-not-visual", r.get("context", {}).get("visual_significant") is False)
        check("case4-verify-legit", verdict_of(r, "verify-build") == "LEGITIMATE", f"{verdict_of(r,'verify-build')}")

        # --- case 5: visually-significant on a no-sim host (honest Unknown, 0 frames) ---
        make_buffer(buf_path, branch=BRANCH, sha=SHA, verdict="Unknown", frames=0)
        report5 = {"stages": [
            {"name": "verify-build", "status": "ran", "verdict": "Unknown"},
            {"name": "visual-verification", "status": "ran"},
        ]}
        r = run(tmp, config=ui_cfg, report=report5, files="M\tsrc/Button.tsx", diff=REAL_TSX_DIFF)
        check("case5-verify-legit", verdict_of(r, "verify-build") == "LEGITIMATE",
              f"honest Unknown should not be flagged: {verdict_of(r,'verify-build')}")
        check("case5-visual-rerun", verdict_of(r, "visual-verification") == "SHOULD-RE-RUN")

        # --- contradiction checks ---
        # a11y skip claims uiSurface:false but config says true.
        rc = run(tmp, config={"uiSurface": True, "verifyFindingsPath": buf_path, "visualHistoryPath": vh_path},
                 report={"stages": [{"name": "accessibility", "status": "skipped", "skip_reason": "uiSurface:false"}]},
                 files="M\tsrc/App.tsx", diff=REAL_TSX_DIFF)
        check("contradiction-a11y", verdict_of(rc, "accessibility") == "SHOULD-RE-RUN", f"{rc.get('stages')}")
        # security skip claims doc-only but the diff touches source.
        rc = run(tmp, config={"uiSurface": True, "verifyFindingsPath": buf_path, "visualHistoryPath": vh_path},
                 report={"stages": [{"name": "security", "status": "skipped", "skip_reason": "doc-only"}]},
                 files="M\tsrc/api.py")
        check("contradiction-security", verdict_of(rc, "security") == "SHOULD-RE-RUN", f"{rc.get('stages')}")
        # verify-build PASS with a fresh buffer but ZERO frames on a visually-significant change.
        make_buffer(buf_path, branch=BRANCH, sha=SHA, verdict="PASS", frames=0)
        rc = run(tmp, config=ui_cfg,
                 report={"stages": [{"name": "verify-build", "status": "ran", "verdict": "PASS"}]},
                 files="M\tsrc/Button.tsx", diff=REAL_TSX_DIFF)
        check("zero-frames-visual-pass", verdict_of(rc, "verify-build") == "SHOULD-RE-RUN", f"{verdict_of(rc,'verify-build')}")

    print(f"\n{total - fails}/{total} checks passed.")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
