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


def run(tmp, *, config, report, files, diff=None, vh_text=None, plan=None):
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
    if plan is not None:
        plan_p = d / "plan.md"
        plan_p.write_text(plan, encoding="utf-8")
        argv += ["--plan", str(plan_p)]
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

        # --- substring-needle false positive (_reason_has word-boundary regression) ---
        # "nonetheless" contains "none"; "interlibrary" contains "library". A skip
        # reason that merely happens to contain one of those words as a SUBSTRING
        # must NOT be misread as a "platform library/none" claim — the honest
        # outcome for an unrecognized reason is NEEDS-JUDGMENT, never a
        # confidently-wrong SHOULD-RE-RUN.
        web_cfg = {"uiSurface": True, "platform": "web", "verifyFindingsPath": buf_path, "visualHistoryPath": vh_path}
        report_substr = {"stages": [
            {"name": "verify-build", "status": "skipped",
             "skip_reason": "reviewer decided nonetheless to skip, no further action needed"},
        ]}
        r = run(tmp, config=web_cfg, report=report_substr, files="M\tsrc/server.py")
        check(
            "substring-needle-not-mismatched",
            verdict_of(r, "verify-build") == "NEEDS-JUDGMENT",
            f"got {verdict_of(r, 'verify-build')!r} — 'nonetheless'/'none' substring must not "
            f"be read as a platform-library/none claim: {r.get('stages')}",
        )

        report_substr2 = {"stages": [
            {"name": "verify-build", "status": "skipped",
             "skip_reason": "the interlibrary loan importer is unrelated to this change"},
        ]}
        r2 = run(tmp, config=web_cfg, report=report_substr2, files="M\tsrc/server.py")
        check(
            "substring-needle-interlibrary-not-mismatched",
            verdict_of(r2, "verify-build") == "NEEDS-JUDGMENT",
            f"got {verdict_of(r2, 'verify-build')!r}: {r2.get('stages')}",
        )

        # The genuine multi-word phrase must still match (regression guard for the fix itself).
        report_genuine = {"stages": [
            {"name": "verify-build", "status": "skipped", "skip_reason": "platform library"},
        ]}
        r3 = run(tmp, config=lib_cfg, report=report_genuine, files="M\tsrc/server.py")
        check(
            "genuine-platform-library-still-legit",
            verdict_of(r3, "verify-build") == "LEGITIMATE",
            f"got {verdict_of(r3, 'verify-build')!r}",
        )

    # A present-but-MALFORMED report must EXIT NON-ZERO with a stderr diagnostic and clean
    # stdout — so the audit-skips SKILL / ship Step 2a can tell an engine failure apart from an
    # absent handoff and surface it loudly, instead of the old `return 0` + `{"...","stages":[]}`
    # that collapsed a failure into a silent "nothing to audit" no-op.
    # --- FB-0079: each reviewer is audited against the pattern IT used ---------
    # `touches_ui` used to back both the a11y-skip check and the verify-build
    # doc-only check, so once visualFilePatterns and a11yFilePatterns can disagree,
    # a merged field would confirm or refute an a11y skip with the VISUAL ruler.
    # Every case below is constructed so the two patterns disagree about the file —
    # which is exactly when the pre-split engine returns the opposite verdict.
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        base = {"uiSurface": True,
                "verifyFindingsPath": str(d / "nope.json"),
                "visualHistoryPath": str(d / "vh.html")}

        # 1. A file WITH an a11y surface that the visual pattern excludes. The a11y
        #    review should have run, so its "no UI in diff" skip is illegitimate.
        #    Pre-split (uiFilePatterns scoped for visual) touches_ui is False and
        #    this wrongly reads LEGITIMATE.
        cfg = dict(base, uiFilePatterns=r"(^|/)(Views|Data)/.*\.swift$",
                   visualFilePatterns=r"(^|/)(Views|Data)/.*\.swift$",
                   a11yFilePatterns=r"(^|/)(Views|Insight)/.*\.swift$")
        r = run(tmp, config=cfg,
                report={"stages": [{"name": "accessibility", "status": "skipped",
                                    "skip_reason": "no UI in diff"}]},
                files="M\tInsight/InsightCacheStore.swift")
        check("fb78-a11y-skip-refused-when-a11y-pattern-matches",
              verdict_of(r, "accessibility") == "SHOULD-RE-RUN",
              f"a11y skip must be refused against a11yFilePatterns, not the visual one: {r}")

        # 2. The mirror: a render-only file the a11y pattern excludes. The a11y
        #    review legitimately skipped. Pre-split (uiFilePatterns widened to cover
        #    Data/ for visual reasons) touches_ui is True and this wrongly reads
        #    SHOULD-RE-RUN — a re-run demanded of a review with nothing to review.
        cfg = dict(base, uiFilePatterns=r"(^|/)(Views|Insight|Data)/.*\.swift$",
                   visualFilePatterns=r"(^|/)(Views|Data)/.*\.swift$",
                   a11yFilePatterns=r"(^|/)(Views|Insight)/.*\.swift$")
        r = run(tmp, config=cfg,
                report={"stages": [{"name": "accessibility", "status": "skipped",
                                    "skip_reason": "no UI in diff"}]},
                files="M\tData/MockSleep.swift")
        check("fb78-a11y-skip-legit-when-a11y-pattern-excludes",
              verdict_of(r, "accessibility") == "LEGITIMATE",
              f"a11y skip must be confirmed against a11yFilePatterns: {r}")

        # 3. The doc-only check takes the UNION. A template with an a11y surface but
        #    no render path and no source extension: pre-split, touches_ui is False
        #    and touches_source is False, so "doc-only" reads LEGITIMATE — buying a
        #    verify-build skip for a diff that changes announced text.
        cfg = dict(base, uiFilePatterns=r"(^|/)(Views|Data)/.*\.swift$",
                   visualFilePatterns=r"(^|/)(Views|Data)/.*\.swift$",
                   a11yFilePatterns=r"\.hbs$")
        r = run(tmp, config=cfg,
                report={"stages": [{"name": "verify-build", "status": "skipped",
                                    "skip_reason": "doc-only diff, no behavior change"}]},
                files="M\ttemplates/aria-labels.hbs")
        check("fb78-doc-only-refused-when-only-a11y-surface-touched",
              verdict_of(r, "verify-build") == "SHOULD-RE-RUN",
              f"doc-only must be refused if EITHER UI surface is touched: {r}")

        # 4. The emitted contract carries both fields and no merged survivor —
        #    a consumer reading `touches_ui` would be reading a field whose meaning
        #    silently changed.
        diff_obj = (r.get("context") or {}).get("diff") or {}
        check("fb78-emits-split-diff-fields",
              set(diff_obj) == {"touches_source", "touches_visual", "touches_a11y"},
              f"expected exactly the split fields, got {sorted(diff_obj)}")

        # 5. Back-compat: with ONLY uiFilePatterns set, both consumers resolve to it,
        #    so the pre-split verdicts stand unchanged.
        cfg = dict(base, uiFilePatterns=r"(^|/)(Views|Insight)/.*\.swift$")
        r = run(tmp, config=cfg,
                report={"stages": [{"name": "accessibility", "status": "skipped",
                                    "skip_reason": "no UI in diff"}]},
                files="M\tInsight/InsightCacheStore.swift")
        check("fb78-backcompat-shared-slot-refuses",
              verdict_of(r, "accessibility") == "SHOULD-RE-RUN", f"{r}")
        r = run(tmp, config=cfg,
                report={"stages": [{"name": "accessibility", "status": "skipped",
                                    "skip_reason": "no UI in diff"}]},
                files="M\tData/MockSleep.swift")
        check("fb78-backcompat-shared-slot-confirms",
              verdict_of(r, "accessibility") == "LEGITIMATE", f"{r}")

        # 7. An unusable a11yFilePatterns must SURFACE, not silently fall back. Without
        #    this the audit confirms an a11y skip against the built-in default while
        #    reporting a confident verdict — measured with a ruler nobody chose.
        cfg = dict(base, a11yFilePatterns="([unclosed")
        r = run(tmp, config=cfg,
                report={"stages": [{"name": "accessibility", "status": "skipped",
                                    "skip_reason": "no UI in diff"}]},
                files="M\tsrc/Button.tsx")
        warns = (r.get("context") or {}).get("pattern_warnings") or []
        check("fb79-invalid-slot-surfaces-in-report",
              any("a11yFilePatterns" in w and "[WARN]" in w for w in warns),
              f"expected a pattern_warnings entry naming a11yFilePatterns, got {warns}")
        # 7b. A NON-STRING slot must also surface. This is the shape that motivated
        #     pattern_warnings in the first place, and the isinstance() filter added
        #     to fix a cross-runtime divergence briefly made it SILENT — the value was
        #     skipped before it could reach re.compile, so the loud path disappeared.
        cfg = dict(base, a11yFilePatterns=["(^|/)Views/.*"])
        r = run(tmp, config=cfg,
                report={"stages": [{"name": "accessibility", "status": "skipped",
                                    "skip_reason": "no UI in diff"}]},
                files="M\tsrc/Button.tsx")
        warns = (r.get("context") or {}).get("pattern_warnings") or []
        check("fb79-non-string-slot-surfaces",
              any("a11yFilePatterns" in w and "must be a string" in w for w in warns),
              f"a non-string slot must be reported, not silently skipped: {warns}")

        # And the SKILL must be told to print it — an emitted-but-unrendered field is
        # the same silent-skip one layer up (this is why three review lenses flagged it).
        skill = (Path(__file__).parent.parent / "skills" / "audit-skips" / "SKILL.md").read_text()
        check("fb79-skill-renders-pattern-warnings",
              "pattern_warnings" in skill and "PATTERN-WARNING" in skill,
              "audit-skips/SKILL.md must instruct the agent to surface pattern_warnings")

        # Walk-parser lifecycle leak: an all-DEMOTED Spec-walk must not read as an
        # active block. A docs-only post-merge PR whose plan carries only demoted
        # headings (qualified "(merged #N)") has block_count >= 1 but NO active block,
        # so audit-coverage's "no Spec-walk" skip is LEGITIMATE. Pre-fix, skip-audit
        # read block_count and flagged SHOULD-RE-RUN ("plan has 1 block") — a false
        # positive routing a clean docs PR to the draft manifest.
        demoted_plan = "## Recently Completed\n\n### PR #99\n\n**Spec-walk (merged #99):**\n- [x] the button renders\n"
        r = run(tmp, config={"uiSurface": True},
                report={"stages": [{"name": "audit-coverage", "status": "skipped",
                                    "skip_reason": "no Spec-walk"}]},
                files="M\tdev-docs/history.md", plan=demoted_plan)
        check("all-demoted-spec-walk-skip-legit",
              verdict_of(r, "audit-coverage") == "LEGITIMATE",
              f"demoted-only plan has no active Spec-walk; skip must be LEGITIMATE, got {verdict_of(r,'audit-coverage')}: {r.get('stages')}")
        # Regression control: an ACTIVE (bare) Spec-walk with the SAME skip is still refused.
        active_plan = "## Current Focus\n\n**Spec-walk:**\n- [ ] the button renders\n"
        r2 = run(tmp, config={"uiSurface": True},
                 report={"stages": [{"name": "audit-coverage", "status": "skipped",
                                     "skip_reason": "no Spec-walk"}]},
                 files="M\tdev-docs/history.md", plan=active_plan)
        check("active-spec-walk-skip-refused",
              verdict_of(r2, "audit-coverage") == "SHOULD-RE-RUN",
              f"active Spec-walk contradicts a no-Spec-walk skip, got {verdict_of(r2,'audit-coverage')}: {r2.get('stages')}")

    with tempfile.TemporaryDirectory() as tmp:
        bad = Path(tmp) / "bad.json"
        bad.write_text("this is not json\n", encoding="utf-8")
        proc = subprocess.run([sys.executable, str(SCRIPT), "--report", str(bad)],
                              capture_output=True, text=True, check=False)
        check("malformed-report-exits-nonzero", proc.returncode != 0, f"rc={proc.returncode}")
        check("malformed-report-stdout-clean", proc.stdout.strip() == "", f"stdout={proc.stdout!r}")
        check("malformed-report-stderr-diagnostic",
              "cannot read stages report" in proc.stderr, f"stderr={proc.stderr!r}")
        # A VALID but empty report is NOT an error — must still exit 0 (an honest no-op audit).
        okp = Path(tmp) / "empty.json"
        okp.write_text('{"stages": []}', encoding="utf-8")
        proc2 = subprocess.run([sys.executable, str(SCRIPT), "--report", str(okp)],
                               capture_output=True, text=True, check=False)
        check("valid-empty-report-exits-zero", proc2.returncode == 0, f"rc={proc2.returncode}")

    print(f"\n{total - fails}/{total} checks passed.")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
