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

import re
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


def run(tmp, *, config, report, files, diff=None, vh_text=None, plan=None, which=None):
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
    if which is not None:
        # Eval determinism: CI runners have no Apple toolchain, so without an
        # explicit "treat these as present" list the toolchain-PRESENT cases below
        # could never run — and a red case that never executes is not a red case.
        w = d / "which.txt"
        w.write_text("\n".join(which), encoding="utf-8")
        argv += ["--which-from", str(w)]
    proc = subprocess.run(argv, capture_output=True, text=True, check=False)
    try:
        out = json.loads(proc.stdout)
    except ValueError:
        out = {"_parse_error": proc.stdout, "_stderr": proc.stderr}
    return out


def stage_of(result, name):
    for s in result.get("stages", []):
        if s.get("name") == name:
            return s
    return {}


def kind_of(result, name):
    return stage_of(result, name).get("manifest_kind")


def reason_of(result, name):
    return stage_of(result, name).get("reason", "")


def verdict_of(result, name):
    return stage_of(result, name).get("mechanical")


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


        # --- TOOLCHAIN: "verifiable in principle, just not on THIS host" ---------
        #
        # The gate this closes: a Linux cloud workspace on a `platform: ios`
        # project cannot build the target at all. Before this branch existed its
        # only honest skip was mechanically refused ("skip claims platform
        # library/none but platform='ios'"), so the session either burned a launch
        # attempt to reach Unknown or fought the auditor.
        #
        # The rule is a CONJUNCTION, deliberately, and the four cases below are
        # the four corners of it: a toolchain-shaped REASON plus a HOST that
        # actually lacks the toolchain. Reason alone is free text the claimant
        # writes; host alone would have the skip auditor — whose whole job is
        # contesting skips — excuse any skip at all on an under-equipped machine.
        ios_cfg = {"uiSurface": True, "platform": "ios",
                   "verifyFindingsPath": buf_path, "visualHistoryPath": vh_path}
        TC_REASON = "toolchain absent: xcodebuild, xcrun not on PATH"
        tc_report = {"stages": [
            {"name": "verify-build", "status": "skipped", "skip_reason": TC_REASON},
        ]}
        SRC = "M\tsrc/ContentView.swift"

        # GREEN — reason names it AND the host confirms it (nothing on PATH).
        # Hoisted: four later cases need this exact engine result, and re-running it
        # four times cost three subprocesses and made the reader diff long call lines
        # to discover they were identical.
        r_green = run(tmp, config=ios_cfg, report=tc_report, files=SRC, which=[])
        r = r_green
        check("toolchain-green-legitimate", verdict_of(r, "verify-build") == "LEGITIMATE",
              f"got {verdict_of(r, 'verify-build')!r}: {r.get('stages')}")
        # The verdict alone is not the point. LEGITIMATE means "the skip was
        # honest", never "the check may be forgotten" — the manifest_kind is what
        # holds those apart, and ship Step 2a.3 routes the PR to draft on it.
        # Without this assertion the branch would be a licence to ship un-verified.
        check("toolchain-green-owes-the-manifest", kind_of(r, "verify-build") == "toolchain",
              f"manifest_kind={kind_of(r, 'verify-build')!r} — a LEGITIMATE that owes nothing is a ready PR with no behavioral gate")
        check("toolchain-green-reason-names-the-host-fact",
              "not on PATH" in reason_of(r, "verify-build"),
              reason_of(r, "verify-build"))

        # RED — identical claim, identical config, host that HAS the toolchain.
        r = run(tmp, config=ios_cfg, report=tc_report, files=SRC, which=["xcodebuild", "xcrun"])
        check("toolchain-red-should-re-run", verdict_of(r, "verify-build") == "SHOULD-RE-RUN",
              f"got {verdict_of(r, 'verify-build')!r}: {r.get('stages')}")
        check("toolchain-red-names-the-binary-it-found",
              "xcodebuild is on PATH" in reason_of(r, "verify-build"),
              f"a verdict that is right for the wrong reason still misleads: {reason_of(r, 'verify-build')!r}")
        check("toolchain-red-owes-no-manifest-entry", kind_of(r, "verify-build") is None,
              f"manifest_kind={kind_of(r, 'verify-build')!r}")

        # PARTIAL toolchain — Xcode present, xcrun off PATH. `absent()` is False,
        # so the gate must RUN, not be suppressed. This is why the predicate is
        # "every binary missing" and not "any binary missing": erring toward
        # running is recoverable, erring toward skipping silently drops the gate.
        r = run(tmp, config=ios_cfg, report=tc_report, files=SRC, which=["xcodebuild"])
        check("toolchain-partial-is-not-absent", verdict_of(r, "verify-build") == "SHOULD-RE-RUN",
              f"a partially-equipped host must not buy the skip: {verdict_of(r, 'verify-build')!r}")
        check("toolchain-partial-owes-no-manifest-entry", kind_of(r, "verify-build") is None)

        # DECISION B — the host fact ALONE never earns LEGITIMATE. Same
        # toolchain-less host as the green case; only the wording differs.
        for label, reason in (("unrelated-reason", "ran out of time"), ("null-reason", None)):
            r = run(tmp, config=ios_cfg, files=SRC, which=[],
                    report={"stages": [{"name": "verify-build", "status": "skipped",
                                        "skip_reason": reason}]})
            check(f"toolchain-hostfact-alone-{label}-needs-judgment",
                  verdict_of(r, "verify-build") == "NEEDS-JUDGMENT",
                  f"got {verdict_of(r, 'verify-build')!r} — a skip that never claimed a toolchain "
                  f"problem must not be excused just because the host lacks one")
            check(f"toolchain-hostfact-alone-{label}-owes-no-entry",
                  kind_of(r, "verify-build") is None)

        # ...and the REASON alone never earns it either, on a platform flow does
        # not model as toolchain-gated. Honest NEEDS-JUDGMENT, never a confident
        # verdict in either direction.
        for label, plat in (("web", "web"), ("unset", None)):
            cfg = {"uiSurface": True, "verifyFindingsPath": buf_path, "visualHistoryPath": vh_path}
            if plat:
                cfg["platform"] = plat
            r = run(tmp, config=cfg, report=tc_report, files=SRC, which=[])
            check(f"toolchain-ungated-platform-{label}-needs-judgment",
                  verdict_of(r, "verify-build") == "NEEDS-JUDGMENT",
                  f"got {verdict_of(r, 'verify-build')!r}")
            check(f"toolchain-ungated-platform-{label}-owes-no-entry",
                  kind_of(r, "verify-build") is None)

        # PAIRED POSITIVES (.claude/rules/general.md rule 3). The new branch sits
        # AFTER these; if a future edit lets it consume their reasons, or if
        # someone "simplifies" by deleting them, these fail. Both must also carry
        # a null manifest_kind — an over-firing branch would draft every library PR.
        r = run(tmp, config=lib_cfg, files="M\tsrc/server.py",
                report={"stages": [{"name": "verify-build", "status": "skipped",
                                    "skip_reason": "platform library"}]})
        check("paired-positive-platform-library-still-legit",
              verdict_of(r, "verify-build") == "LEGITIMATE" and kind_of(r, "verify-build") is None,
              f"{verdict_of(r, 'verify-build')!r} / {kind_of(r, 'verify-build')!r}")
        # ...including when its reason happens to mention a toolchain. flow's OWN
        # repo is platform: library, and this reason is one a human would write.
        r = run(tmp, config=lib_cfg, files="M\tsrc/server.py",
                report={"stages": [{"name": "verify-build", "status": "skipped",
                                    "skip_reason": "platform library — no toolchain to build"}]})
        check("paired-positive-library-reason-mentioning-toolchain-still-legit",
              verdict_of(r, "verify-build") == "LEGITIMATE" and kind_of(r, "verify-build") is None,
              f"the toolchain branch must not consume an un-gated platform's skip: "
              f"{verdict_of(r, 'verify-build')!r} / {kind_of(r, 'verify-build')!r}")
        ve_cfg = {"uiSurface": True, "platform": "ios", "verifyEnabled": False,
                  "verifyFindingsPath": buf_path, "visualHistoryPath": vh_path}
        r = run(tmp, config=ve_cfg, files=SRC, which=[],
                report={"stages": [{"name": "verify-build", "status": "skipped",
                                    "skip_reason": "verifyEnabled:false"}]})
        check("paired-positive-verifyEnabled-false-still-legit",
              verdict_of(r, "verify-build") == "LEGITIMATE" and kind_of(r, "verify-build") is None,
              f"{verdict_of(r, 'verify-build')!r} / {kind_of(r, 'verify-build')!r}")

        # ACCEPTED RESIDUAL, pinned so a future reorder is a visible decision.
        # A toolchain reason containing the bare word "none" matches the
        # library/none branch FIRST and gets a misquoting refutation. Unhelpful,
        # but safe AND self-healing: verify-build is auto-resolvable, so ship
        # re-invokes it, the producer writes the canonical reason, and the single
        # re-audit lands on the toolchain branch. Both hops end in a draft.
        r = run(tmp, config=ios_cfg, files=SRC, which=[],
                report={"stages": [{"name": "verify-build", "status": "skipped",
                                    "skip_reason": "toolchain absent — none of the Apple tools are present"}]})
        check("residual-none-in-reason-is-safe-not-clean",
              verdict_of(r, "verify-build") == "SHOULD-RE-RUN" and kind_of(r, "verify-build") is None,
              f"{verdict_of(r, 'verify-build')!r} — must never be a clean pass")
        # ...and the second hop — the report the producer writes on re-run — IS the
        # GREEN case above (same config, same canonical reason), so it needs no
        # separate assertion; `toolchain-green-*` already pins that terminal state.

        # THE FORK BOUNDARY (FB-0074: a contract whose halves live in two files is
        # broken until something mechanical checks the join). The engine computes
        # manifest_kind, but /flow:ship only ever sees the forked skill's SUMMARY
        # text — so if the SKILL's Output block has no field for it, the emitter is
        # unreachable while every assertion above stays green. Asserted in BOTH
        # directions so deleting either half fails.
        as_skill = (HERE.parent / "skills" / "audit-skips" / "SKILL.md").read_text(encoding="utf-8")
        check("fork-join-engine-emits-the-key", "manifest_kind" in stage_of(r_green, "verify-build"),
              f"engine stage keys: {sorted(stage_of(r_green, 'verify-build'))}")
        check("fork-join-skill-output-block-names-it", "manifest: <kind>" in as_skill,
              "audit-skips/SKILL.md's ## Output block must carry the field, or the "
              "ship agent never sees it and Step 2a.3 can never fire")
        check("fork-join-skill-resolution-can-say-it", "owe the manifest" in as_skill,
              "the RESOLUTION: vocabulary must be able to express 'all LEGITIMATE, K owe the manifest'")

        # SPIKE MODE HAS NO OTHER NET. /flow:ship turns a toolchain-absent skip into a
        # draft via audit-skips + the manifest; ship-spike invokes NEITHER (0 audit-skips
        # calls, and its PR is explicitly not manifest-gated), so before this kind existed
        # its only gate on a toolchain-less host was verify-build running, failing to
        # launch, and judging Unknown. A silent exit-0 self-skip would turn that halt into
        # a clean pass — strictly LESS gated than before, on exactly the hosts this
        # program targets, and a direct contradiction of the plan's stated invariant.
        spike_skill = (HERE.parent / "skills" / "ship-spike" / "SKILL.md").read_text(encoding="utf-8")
        check("ship-spike-does-not-silently-pass-a-toolchain-skip",
              "NOT a pass in spike mode" in spike_skill,
              "ship-spike must adjudicate a toolchain-absent skip the way it adjudicates "
              "Unknown, or the new self-skip removes its only behavioral gate")
        # INVERTED AT FB-0100, deliberately — read this before "fixing" it.
        #
        # This assertion used to read `'Skill("flow:audit-skips")' not in spike_skill`,
        # with a note that "if ship-spike ever gains an audit-skips invocation … [it]
        # should be revisited". It has been. That negative pin was accurate about the
        # tree and wrong about the product: it encoded "spike mode has no skip audit"
        # as an invariant to PROTECT, when it was a defect to fix — spike mode is the
        # path that produces the most skips, so it is the path that most needs the
        # gate (FB-0100). ship-spike now invokes it at Step 2a.
        #
        # Pinned POSITIVELY from both ends, per FB-0077: a bare "the call exists" check
        # and a bare "the note exists" check each go green in two opposite worlds, and
        # the pair below cannot. Count INVOCATIONS, not mentions — ship-spike's prose
        # necessarily names the skill it is describing.
        check("ship-spike-invokes-audit-skips",
              'Skill("flow:audit-skips")' in spike_skill,
              "ship-spike must actually CALL /flow:audit-skips (FB-0100) — a spike PR is "
              "the skip-heaviest path in the workflow, and through v1.37.0 it was the one "
              "path that audited none of them")
        check("ship-spike-declares-the-Skill-tool",
              re.search(r"^allowed-tools:.*\bSkill\b", spike_skill, re.M) is not None,
              "ship-spike's frontmatter must declare the Skill tool, or every Skill() call "
              "in it is a composition the runtime can reject — an inert gate, FB-0082's shape")
        # Spike PRs are not manifest-gated, so the ONE outcome ship routes to a draft
        # (a LEGITIMATE that still owes an entry) has to land somewhere here instead.
        # Without this, adding the audit would produce a gate that reports and proceeds.
        check("ship-spike-adjudicates-the-manifest-kind-it-cannot-file",
              "manifest: <kind>" in spike_skill and "no draft manifest" in spike_skill,
              "ship-spike Step 2a.3 must say what happens to a `LEGITIMATE · manifest:` "
              "verdict it has no manifest to file — otherwise the honest-but-unverified "
              "skip is reported and then silently proceeds past")

        # THE SHARED MODULE, DRIVEN DIRECTLY. Everything above exercises toolchain.py
        # THROUGH skip-audit-checks.py; these drive its own CLI, which is what the
        # producer runs. Without them `--which-from` and `load_present` have no caller
        # on that side, and the `absent()` predicate rests on a one-off manual run.
        TCPY = HERE.parent / "skills" / "verify-build" / "lib" / "toolchain.py"

        def tc(*args, present=None):
            argv = [sys.executable, str(TCPY), *args, "--platform", "ios"]
            if present is not None:
                w = Path(tmp) / "tc-which.txt"
                w.write_text("\n".join(present), encoding="utf-8")
                argv += ["--which-from", str(w)]
            pr = subprocess.run(argv, capture_output=True, text=True)
            return pr.returncode, pr.stdout.strip()

        # `absent` means EVERY binary missing — not "any". The middle case is the whole
        # reason for that choice: a host with Xcode but no xcrun on PATH must RUN the
        # gate, not be let off it. Erring toward running costs a failed build; erring
        # toward skipping silently drops the change's only behavioral gate.
        rc, out = tc("skip-reason", present=[])
        check("toolchain-cli-all-absent-emits-the-sentence",
              rc == 0 and "xcodebuild" in out and "xcrun" in out, f"rc={rc} out={out!r}")
        rc, out = tc("skip-reason", present=["xcodebuild", "xcrun"])
        check("toolchain-cli-fully-equipped-host-does-not-skip", rc == 1 and out == "", f"rc={rc} out={out!r}")
        rc, out = tc("skip-reason", present=["xcodebuild"])
        check("toolchain-cli-partial-toolchain-does-not-skip", rc == 1 and out == "",
              f"rc={rc} out={out!r} — a partially-equipped host must run the gate, so `absent` "
              f"must mean every binary missing, never merely some")
        rc, out = subprocess.run(
            [sys.executable, str(TCPY), "skip-reason", "--platform", "web"],
            capture_output=True, text=True).returncode, ""
        check("toolchain-cli-ungated-platform-never-skips", rc == 1, f"rc={rc}")

        # "Could not answer" must never wear the same exit code as "the answer is no".
        # `json.loads("[]")` parses and then explodes on `.get`, and an uncaught
        # exception exits 1 — indistinguishable from "toolchain present", so the caller
        # would run a build it cannot run and file the failure as a regression.
        bad = Path(tmp) / "bad-flow.config.json"
        for label, body in (("not-an-object", "[]"), ("not-json", "{ nope")):
            bad.write_text(body, encoding="utf-8")
            pr = subprocess.run([sys.executable, str(TCPY), "skip-reason", "--config", str(bad)],
                                capture_output=True, text=True)
            check(f"toolchain-cli-malformed-config-{label}-exits-2",
                  pr.returncode == 2,
                  f"rc={pr.returncode} — a config it cannot read must be distinguishable "
                  f"from 'the toolchain is present' (exit 1), or the caller silently "
                  f"proceeds to a build that cannot succeed")
            check(f"toolchain-cli-malformed-config-{label}-says-why",
                  "toolchain:" in pr.stderr and "Traceback" not in pr.stderr,
                  f"stderr={pr.stderr!r} — a traceback is not a diagnostic")
        # An ABSENT config is a normal condition, not an error: no config, no declared
        # platform, run the build. Paired with the two above so neither can be
        # satisfied by collapsing all three cases onto one code.
        pr = subprocess.run([sys.executable, str(TCPY), "skip-reason",
                             "--config", str(Path(tmp) / "definitely-not-here.json")],
                            capture_output=True, text=True)
        check("toolchain-cli-absent-config-is-not-an-error", pr.returncode == 1,
              f"rc={pr.returncode} — a missing config means 'no declared platform', not 'broken'")

        # THE PRODUCER↔AUDITOR CONTRACT, tested end to end rather than against a third
        # hardcoded string. The producer's sentence must satisfy the auditor's OWN
        # predicate — otherwise flow's own emitted skip would fall through to
        # NEEDS-JUDGMENT and the whole path would quietly never fire.
        _, sentence = tc("skip-reason", present=[])
        contract_report = {"stages": [
            {"name": "verify-build", "status": "skipped", "skip_reason": sentence},
        ]}
        r_contract = run(tmp, config=ios_cfg, report=contract_report, files=SRC, which=[])
        check("producer-sentence-satisfies-the-auditor-predicate",
              verdict_of(r_contract, "verify-build") == "LEGITIMATE"
              and kind_of(r_contract, "verify-build") == "toolchain",
              f"the producer emitted {sentence!r} and the auditor answered "
              f"{verdict_of(r_contract, 'verify-build')!r} — the two halves of the contract "
              f"have drifted; both import toolchain.REASON_NEEDLES for exactly this reason")

        # THE PRODUCER (/flow:verify-build § 1.2). Without it nothing inside flow
        # ever emits this skip, so the branch above would classify a skip that
        # never occurs. Paired positive: the two PRE-EXISTING self-skip cases must
        # still be there, so the third cannot be added by replacing one of them.
        vb_skill = (HERE.parent / "skills" / "verify-build" / "SKILL.md").read_text(encoding="utf-8")
        check("producer-case-exists", "skip-reason --platform" in vb_skill,
              "verify-build § 1.2 must self-skip when the toolchain is absent")
        # THE THREE-OUTCOME CONTRACT. Two lenses independently found that a bare
        # `2>/dev/null` + conditional folds "the check could not run" into "the
        # toolchain is present" — which silently restores the launch→Unknown→
        # filed-as-a-regression path this whole case exists to delete. Nothing
        # discriminated exit 1 from exit 2 before this assertion existed.
        check("producer-distinguishes-broken-check-from-present-toolchain",
              "TC_RC" in vb_skill and "could not run" in vb_skill,
              "§ 1.2 must branch on the exit status and WARN when the probe itself failed, "
              "rather than treating every non-zero exit as 'toolchain present'")
        check("producer-does-not-swallow-the-probes-diagnostic",
              "skip-reason --platform \"$PLATFORM\" 2>&1" in vb_skill,
              "the probe's stderr must be captured for the warning, not sent to /dev/null")
        check("producer-skips-the-spawn-on-an-undeclared-platform", '[ -n "$PLATFORM" ]' in vb_skill,
              "an undeclared platform can never be toolchain-gated, so it must not pay the interpreter spawn")
        check("producer-keeps-verifyEnabled-case", 'VERIFY_ENABLED" = "false"' in vb_skill)
        check("producer-keeps-library-none-case", "library|none)" in vb_skill)
        # The producer no longer PHRASES the reason — it echoes what toolchain.py emits,
        # so the assertion moves to the module that owns the sentence (see the
        # producer↔auditor contract case below, which feeds one through the other).
        check("producer-echoes-the-modules-sentence", "$TC_REASON" in vb_skill,
              "the SKILL must echo toolchain.py's sentence, not compose its own")

        # END-TO-END: the engine's manifest_kind, fed to the triage engine, must
        # yield a non-READY verdict. This pins the ENGINE-COMPOSITION half of
        # "honest skip still drafts"; the Step 2a.3 invocation itself is prose,
        # pinned by run_manifest_triage_evals.py's add-entry assertion.
        mt = HERE.parent / "skills" / "ship" / "lib" / "manifest-triage.py"
        e2e_kind = kind_of(r_green, "verify-build")
        # One if/else, not a sentinel: on a pre-change tree there is no manifest_kind
        # to route, and the red-verify must print clean FAILs rather than raising
        # mid-harness (which would hide every later case) or spawning three
        # subprocesses whose output is discarded.
        if e2e_kind is None:
            check("end-to-end-add-entry-accepted", False,
                  "no manifest_kind to route — the engine did not classify the skip")
            check("end-to-end-honest-skip-still-drafts", False, "no manifest_kind to route")
        else:
            e2e = Path(tmp) / "e2e-entries.md"
            add = subprocess.run([sys.executable, str(mt), "add-entry",
                                  "--kind", e2e_kind,
                                  "--finding", "verify-build could not run on this host",
                                  "--needs", "re-run", "--confidence", "decision-required",
                                  "--resolution", "re-run where the toolchain exists"],
                                 capture_output=True, text=True)
            e2e.write_text(add.stdout, encoding="utf-8")
            st_p = Path(tmp) / "e2e-state.json"
            subprocess.run([sys.executable, str(mt), "init-state", "--branch", "e2e",
                            "--path", str(st_p)], capture_output=True, text=True)
            cls = subprocess.run([sys.executable, str(mt), "classify", "--entries-file", str(e2e),
                                  "--state-file", str(st_p), "--branch", "e2e"],
                                 capture_output=True, text=True)
            check("end-to-end-add-entry-accepted", add.returncode == 0, add.stdout + add.stderr)
            e2e_verdict = json.loads(cls.stdout).get("verdict") if cls.returncode == 0 else None
            check("end-to-end-honest-skip-still-drafts", e2e_verdict not in (None, "READY"),
                  f"verdict={e2e_verdict!r} — an honest toolchain skip must never produce a ready PR")

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

        # --- SPIKE MODE (FB-0100) -------------------------------------------
        # /flow:ship-spike now writes a handoff and runs this engine. Two opposite
        # failure modes have to be pinned TOGETHER, because a fix for either one
        # alone is a plausible-looking change that breaks the other:
        #
        #   too loose — "spike" excuses any stage, so the skip-heaviest path in the
        #               workflow self-certifies (the defect FB-0100 closes);
        #   too tight — a spike's own declared mode routes it to SHOULD-RE-RUN, so
        #               every spike fights its own mode and spike mode is unusable
        #               (a WORSE bug than the one being fixed).
        spike_plan = "## Current Focus\n\n### PR — my spike\n**Mode:** spike\n**Research question:** does X work?\n"

        # LOOSE side: the two stages disposability actually reaches stay NEEDS-JUDGMENT.
        # NOT SHOULD-RE-RUN — mode is a plan declaration, so the engine hands these to
        # the fork agent with plan_mode evidence rather than pretending to decide them.
        r = run(tmp, config={"uiSurface": True},
                report={"stages": [{"name": "simplify", "status": "skipped", "skip_reason": "spike"},
                                   {"name": "staff-review", "status": "skipped", "skip_reason": "spike"}]},
                files="M\tdev-docs/history.md", plan=spike_plan)
        for st in ("simplify", "staff-review"):
            check(f"spike-{st}-stays-needs-judgment",
                  verdict_of(r, st) == "NEEDS-JUDGMENT",
                  f"a declared spike skip of {st} must NOT become SHOULD-RE-RUN — that would "
                  f"make every spike draft over its own mode; got {verdict_of(r, st)}")

        # TIGHT side: the three stages disposability does NOT reach are refused a
        # mode-based excuse outright, and the refusal is auto-resolvable (just run it).
        for st, alias in (("security", "security"), ("accessibility", "accessibility"),
                          ("audit-coverage", "audit-coverage")):
            r = run(tmp, config={"uiSurface": True},
                    report={"stages": [{"name": st, "status": "skipped", "skip_reason": "spike"}]},
                    files="M\tsrc/Button.tsx", diff=REAL_TSX_DIFF, plan=spike_plan)
            check(f"spike-is-no-excuse-for-{alias}",
                  verdict_of(r, st) == "SHOULD-RE-RUN",
                  f"'spike' must not excuse {st}: the code is disposable, the commit is not, "
                  f"and an approved prototype's pattern outlives its code; got {verdict_of(r, st)}")
            check(f"spike-refusal-for-{alias}-is-auto-resolvable",
                  stage_of(r, st).get("auto_resolvable") is True,
                  "the remedy is 'just run the reviewer', so this must never route to a "
                  "decision the human has to answer")
        # 'tiny' is the same class and must not be a loophole for the same three.
        r = run(tmp, config={"uiSurface": True},
                report={"stages": [{"name": "security", "status": "skipped", "skip_reason": "tiny mode"}]},
                files="M\tsrc/Button.tsx", diff=REAL_TSX_DIFF)
        check("tiny-is-no-excuse-for-security", verdict_of(r, "security") == "SHOULD-RE-RUN",
              f"got {verdict_of(r,'security')}")
        # CONTROL: the same three stages keep their real, checkable skips. Without this,
        # the two checks above are satisfiable by refusing every skip these stages make.
        r = run(tmp, config={"uiSurface": True},
                report={"stages": [{"name": "security", "status": "skipped", "skip_reason": "doc-only"},
                                   {"name": "accessibility", "status": "skipped", "skip_reason": "no UI in diff"},
                                   {"name": "audit-coverage", "status": "skipped", "skip_reason": "no Spec-walk"}]},
                files="M\tdev-docs/history.md", plan=spike_plan)
        for st in ("security", "accessibility", "audit-coverage"):
            check(f"docs-only-spike-{st}-still-legit", verdict_of(r, st) == "LEGITIMATE",
                  f"a docs-only spike must still rule clean for {st} — the audit validates "
                  f"skips, it does not ban them; got {verdict_of(r, st)}")

        # plan_mode EVIDENCE (never a verdict input). The fork agent resolves the
        # NEEDS-JUDGMENT rows against this; before it existed, the one fact the rule
        # turns on was a file the agent had to go find on its own.
        r = run(tmp, config={"uiSurface": True},
                report={"stages": [{"name": "simplify", "status": "skipped", "skip_reason": "spike"}]},
                files="M\tdev-docs/history.md", plan=spike_plan)
        pm = r.get("context", {}).get("plan_mode", {})
        check("plan-mode-evidence-emitted", pm.get("first_mode_line", "").startswith("spike"), f"{pm}")
        check("plan-mode-not-ambiguous-when-single", pm.get("ambiguous") is False, f"{pm}")
        # A multi-block plan (flow's own carries 53 Mode lines) must report ambiguity
        # rather than quietly presenting a retained block's mode as fact.
        multi_plan = spike_plan + "\n### PR — an older, shipped one\n**Mode:** feature\n"
        r = run(tmp, config={"uiSurface": True},
                report={"stages": [{"name": "simplify", "status": "skipped", "skip_reason": "spike"}]},
                files="M\tdev-docs/history.md", plan=multi_plan)
        pm = r.get("context", {}).get("plan_mode", {})
        check("plan-mode-flags-ambiguity", pm.get("ambiguous") is True and pm.get("occurrences") == 2, f"{pm}")
        check("plan-mode-still-not-a-verdict",
              verdict_of(r, "simplify") == "NEEDS-JUDGMENT",
              "plan_mode is evidence for the agent, never a mechanical verdict — a "
              "first-match read of a 50-block plan can be confidently wrong failure-open")
        # A plan that declares NO mode at all: evidence says so plainly (occurrences 0),
        # which is what lets the agent refuse an unbacked spike claim.
        r = run(tmp, config={"uiSurface": True},
                report={"stages": [{"name": "simplify", "status": "skipped", "skip_reason": "spike"}]},
                files="M\tdev-docs/history.md", plan="## Current Focus\n\nNo mode here.\n")
        pm = r.get("context", {}).get("plan_mode", {})
        check("plan-mode-absent-is-visible",
              pm.get("occurrences") == 0 and pm.get("first_mode_line") is None, f"{pm}")

        # --- preflight stage (FB-0100) --------------------------------------
        # One of the five stages PR #140 skipped with nothing auditing it. Both of its
        # skip conditions are config/diff facts, which is exactly why it earns a row.
        r = run(tmp, config={"uiSurface": True, "preflightCmd": ""},
                report={"stages": [{"name": "preflight", "status": "skipped",
                                    "skip_reason": "preflightCmd not set"}]},
                files="M\tdev-docs/history.md")
        check("preflight-unset-slot-legit", verdict_of(r, "preflight") == "LEGITIMATE",
              f"{r.get('stages')}")
        r = run(tmp, config={"uiSurface": True, "preflightCmd": "npm run check"},
                report={"stages": [{"name": "preflight", "status": "skipped",
                                    "skip_reason": "preflightCmd not set"}]},
                files="M\tsrc/Button.tsx", diff=REAL_TSX_DIFF)
        check("preflight-claimed-unset-but-set-refused",
              verdict_of(r, "preflight") == "SHOULD-RE-RUN", f"{r.get('stages')}")
        check("preflight-refusal-auto-resolvable",
              stage_of(r, "preflight").get("auto_resolvable") is True,
              "re-running preflightCmd is cheap and mechanical — never a human decision")
        r = run(tmp, config={"uiSurface": True, "preflightCmd": "npm run check"},
                report={"stages": [{"name": "preflight", "status": "skipped",
                                    "skip_reason": "doc-only"}]},
                files="M\tsrc/Button.tsx", diff=REAL_TSX_DIFF)
        check("preflight-docs-only-claim-refuted-by-source",
              verdict_of(r, "preflight") == "SHOULD-RE-RUN", f"{r.get('stages')}")
        # It must be a KNOWN stage, not the `unknown stage` fallback — that fallback is
        # indistinguishable from a typo and gives the agent nothing to check against.
        check("preflight-is-a-known-stage",
              "unknown stage" not in reason_of(r, "preflight"), f"{reason_of(r,'preflight')}")

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
