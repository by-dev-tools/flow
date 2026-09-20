#!/usr/bin/env python3
"""
Regression eval for D1 Phase 2 — the prototype phase, human gate 1, and the
loop re-order (`dev-docs/handoffs/d1-prototype-first-gate.md` § Phase 2;
FB-0081 / FB-0113 / FB-0114).

Groups, in the order the plan's Spec-walk declares them:

  1. trigger        The three paths + the invariant. Every fixture row is
                    asserted on BOTH `path` and `pre_execution_gate`, because
                    `collapsed` and `classic` both emit gate `plan` — a
                    gate-only assertion would leave the proportionality
                    collapse pinned by nothing.
  2. contract       § 9.4's feasibility read, defined as the COMPLEMENT of
                    `platform: web` and swept over the whole enum plus unset.
  3. approve/verify Gate-1 capture, its three refusals, and post-approval drift.
  4. gate-execute   "A plan always exists", reading committed state only.
  5. present        Byte-identical to input + the annotation partial.
  6. docs           The fan-out this PR is most exposed to, checked at the join
                    rather than by author memory.

Two disciplines from `.claude/rules/general.md` § Consistency run throughout:

  item 3 — every prohibition is paired with the positive it protects, so the
           check cannot be satisfied by deleting the protected thing.
  item 4 — every "returns clean" measurement is first run against a KNOWN
           POSITIVE, and sweeps key on `git grep`'s EXIT CODE rather than a
           count of its output. A detector validated only on quiet inputs
           cannot be distinguished from a broken one.

Stdlib only. No network. Run:
    python3 plugins/flow/evals/run_prototype_gate_evals.py
Exits non-zero on any failure (CI gate).
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent                      # plugins/flow
ROOT = REPO.parent.parent               # repo root
FIX = HERE / "fixtures" / "prototype-gate"
ENGINE = REPO / "skills" / "prototype" / "lib" / "prototype-gate.py"
SKILL = REPO / "skills" / "prototype" / "SKILL.md"
REVIEW_BRIEF = REPO / "skills" / "review-brief" / "SKILL.md"
WORKFLOW = REPO / "docs" / "workflow.md"
WORKFLOW_HELP = REPO / "skills" / "workflow-help" / "SKILL.md"
GENERAL = REPO / "skills" / "general" / "SKILL.md"
PLAN_DISCIPLINE = REPO / "skills" / "plan-discipline" / "SKILL.md"
PLANNER = REPO / "agents" / "planner.md"
DOCTOR = REPO / "skills" / "doctor" / "SKILL.md"
LENS_DE = REPO / "agents" / "lens-design-engineer.md"
LENS_UX = REPO / "agents" / "lens-ux-designer.md"
LENS_EXP = REPO / "agents" / "lens-experience.md"
LAYER = REPO / "skills" / "verify-build" / "lib" / "annotation-layer.html"
SCRATCH_EVALS = HERE / "run_scratch_isolation_evals.py"
JQ_EVALS = HERE / "run_jq_guard_evals.py"

# The "Phase 2 is unbuilt" claim family. Scoped to phrases that ASSERT
# unbuilt-ness: a bare "D1 Phase 2" also matches legitimate citations (including
# the ones this PR adds), and a pattern that flags correct prose trains its
# reader to ignore it.
PHASE2_PAT = (
    r"not wired into the (live )?loop"
    r"|not yet consumed by"
    r"|no skill reads"
    r"|prototype phase[^.]{0,60}(not yet built|does not exist yet|doesn.t exist yet)"
    r"|(not yet built|isn.t shipped)[^.]{0,30}(D1 )?Phase 2"
    r"|those are D1 Phase 2"
    r"|that.s Phase 2"
)
GATE_PAT = (
    r"Plan approval|human-gated at Plan|two load-bearing"
    r"|wait for (the )?(user )?approval|approval before executing"
)
# Pre-merge snapshot: the files that carried Phase-2-unbuilt claims when this PR
# was planned. A TEST INPUT, frozen, not a live derivation — deriving this domain
# from the post-merge tree makes it self-emptying (the negative requires zero
# matches, so the domain is empty exactly when the positive would matter).
PHASE2_DOMAIN = [
    REPO / "docs" / "workflow.md",
    REPO / "skills" / "review-brief" / "SKILL.md",
]
# Verdicted exemptions for the gate sweep: real hits that assert no pre-execution
# gate. Recorded here rather than excluded silently.
GATE_EXEMPT = {
    "plugins/flow/skills/critique-plan/SKILL.md",   # a comment about its own output
    ".claude/skills/ship/SKILL.md",                 # "wait for user approval" on a merge conflict
}

_fails: list[str] = []
_passes = 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global _passes
    if cond:
        _passes += 1
    else:
        _fails.append(f"{name}: {detail}")


def run(*args, cwd=None):
    proc = subprocess.run([sys.executable, str(ENGINE), *args],
                          capture_output=True, text=True, cwd=cwd)
    try:
        return proc.returncode, json.loads(proc.stdout), proc.stderr
    except ValueError:
        return proc.returncode, None, proc.stderr


def fx(name: str) -> str:
    return str(FIX / name)


# ------------------------------------------------------------------ 1. trigger

TRIGGER_MATRIX = [
    # (label, brief, config, expected path, expected gate)
    ("designer-feature",     "brief-visual-feature.md",   "cfg-designer.json",           "prototype-first", "prototype"),
    ("declared-visual",      "brief-visual-feature.md",   "cfg-unset-platform.json",     "prototype-first", "prototype"),
    ("designer-no-surface",  "brief-no-surface.md",       "cfg-designer.json",           "prototype-first", "prototype"),
    ("tiny-collapses",       "brief-visual-tiny.md",      "cfg-designer.json",           "collapsed",       "plan"),
    ("spike-classic",        "brief-visual-spike.md",     "cfg-designer.json",           "classic",         "plan"),
    ("declared-non-visual",  "brief-nonvisual-feature.md","cfg-unset-platform.json",     "classic",         "plan"),
    ("engineer-non-visual",  "brief-nonvisual-feature.md","cfg-engineer.json",           "classic",         "plan"),
    ("no-surface-unset-role","brief-no-surface.md",       "cfg-unset-platform.json",     "classic",         "plan"),
    # The veto, tested against the HARD case: role: designer present and overridden.
    ("uisurface-false-veto", "brief-visual-feature.md",   "cfg-nosurface-designer.json", "classic",         "plan"),
    ("brief-malformed",      "brief-malformed.md",        "cfg-designer.json",           "classic",         "plan"),
    ("brief-absent",         "__absent__.md",             "cfg-designer.json",           "classic",         "plan"),
    ("config-malformed",     "brief-visual-feature.md",   "cfg-malformed.json",          "classic",         "plan"),
]


def test_trigger_matrix():
    seen_gates, seen_paths = set(), set()
    for label, brief, cfg, want_path, want_gate in TRIGGER_MATRIX:
        rc, out, err = run("trigger", "--brief", fx(brief), "--config", fx(cfg))
        check(f"trigger-{label}-json", out is not None, f"non-JSON stdout; stderr={err[:200]}")
        if out is None:
            continue
        check(f"trigger-{label}-path", out["path"] == want_path,
              f"expected path {want_path!r}, got {out['path']!r}")
        check(f"trigger-{label}-gate", out["pre_execution_gate"] == want_gate,
              f"expected gate {want_gate!r}, got {out['pre_execution_gate']!r}")
        # THE invariant, per row: exactly one gate value, always present.
        check(f"trigger-{label}-exactly-one-gate",
              out.get("pre_execution_gate") in ("prototype", "plan"),
              f"gate must be exactly one of prototype|plan, got {out.get('pre_execution_gate')!r}")
        check(f"trigger-{label}-has-reasons", bool(out.get("reasons")),
              "every verdict must say WHY — a gate that moves without a reason is unauditable")
        seen_gates.add(out["pre_execution_gate"])
        seen_paths.add(out["path"])
    # Positive half: BOTH gate values and ALL THREE paths must actually occur,
    # so the invariant is not satisfiable by deleting a branch (item 3).
    check("trigger-both-gate-values-occur", seen_gates == {"prototype", "plan"},
          f"matrix only produced {sorted(seen_gates)} — a one-sided matrix proves nothing")
    check("trigger-all-three-paths-occur",
          seen_paths == {"prototype-first", "collapsed", "classic"},
          f"matrix only produced {sorted(seen_paths)}")


def test_trigger_degradation_reasons_are_distinct():
    """absent != malformed. Both route to classic, but collapsing the diagnosis
    would train a reader to ignore the warning — `trigger` runs only AFTER
    /flow:prototype writes the brief, so absent means the write failed."""
    _, absent, _ = run("trigger", "--brief", fx("__absent__.md"), "--config", fx("cfg-designer.json"))
    _, bad, _ = run("trigger", "--brief", fx("brief-malformed.md"), "--config", fx("cfg-designer.json"))
    check("trigger-absent-state", absent and absent.get("brief_state") == "absent")
    check("trigger-malformed-state", bad and bad.get("brief_state") == "malformed")
    check("trigger-states-distinct",
          absent and bad and absent["brief_state"] != bad["brief_state"],
          "absent and malformed must not collapse into one state")


def test_suppression_is_recorded():
    """role: designer under uiSurface: false is SUPPRESSED, never silently
    dropped — same shape and resolution as visual-significance.py's gate 1."""
    _, out, _ = run("trigger", "--brief", fx("brief-visual-feature.md"),
                    "--config", fx("cfg-nosurface-designer.json"))
    joined = " ".join(out.get("reasons", [])) if out else ""
    check("suppression-recorded", "SUPPRESSED" in joined,
          "a designer whose role is overridden must be TOLD, not silently reclassified")


def test_config_not_an_object_fails_closed():
    """A JSON document that PARSES but is not an object (`[]`, `"x"`) is malformed
    for this purpose. Found by the /simplify reuse pass: without an isinstance
    guard, `_ui_surface` raised AttributeError and the process exited 1 with a
    traceback and NO JSON — violating the module docstring's promise that every
    subcommand emits a parseable verdict. `toolchain.py` already carries this
    guard; this reader shipped without it."""
    for cfg in ("cfg-not-an-object.json", "cfg-json-string.json"):
        rc, out, err = run("arming", "--config", fx(cfg))
        check(f"config-nonobject-{cfg}-emits-json", out is not None,
              f"must emit a parseable verdict, not a traceback; stderr={err[:160]}")
        check(f"config-nonobject-{cfg}-exit0", rc == 0, f"exit {rc}")
        check(f"config-nonobject-{cfg}-fails-closed", out and out.get("armed") is False,
              "unreadable config means uiSurface is UNKNOWN — the D1 branch must not be "
              "taken on a guess")
        _, trg, _ = run("trigger", "--brief", fx("brief-visual-feature.md"), "--config", fx(cfg))
        check(f"config-nonobject-{cfg}-trigger-classic",
              trg and trg["path"] == "classic" and trg["pre_execution_gate"] == "plan",
              "trigger and arming must not disagree about the same config")


def test_stamp_helpers_are_reused_not_reimplemented():
    """flow_scratch.current_stamp()/check_stamp() are the canonical pair (FB-0082).
    An earlier draft hand-rolled both, strictly worse: 3 git subprocesses instead of
    2, and a verify comparison on `branch` ALONE — so the same branch name in a
    different clone verified clean, and a symlinked worktree was a false mismatch."""
    src = ENGINE.read_text(encoding="utf-8")
    check("engine-imports-flow-scratch", "import flow_scratch" in src)
    check("engine-uses-current-stamp", "current_stamp(" in src)
    check("engine-uses-check-stamp", "check_stamp(" in src,
          "verify must delegate the comparison, not re-compare fields locally")
    # Paired negative: the private re-implementation must be gone, or both exist
    # and the reuse is decorative.
    check("engine-has-no-private-git-helper",
          "def _git(" not in src,
          "the hand-rolled _git/_stamp pair must be REMOVED, not merely shadowed")


def test_arming_is_config_only():
    """The arming check must answer without a brief — that is the whole reason
    it is split out of `trigger`. A single combined predicate could never decide
    whether to take the D1 branch without already being on it."""
    rc, out, err = run("arming", "--config", fx("cfg-designer.json"))
    check("arming-no-brief-needed", out is not None and out.get("armed") is True,
          f"arming must resolve with no brief argument at all; stderr={err[:160]}")
    _, off, _ = run("arming", "--config", fx("cfg-nosurface-designer.json"))
    check("arming-uisurface-false", off is not None and off.get("armed") is False)
    check("arming-suppression-recorded",
          off is not None and any("SUPPRESS" in r.upper() for r in off.get("reasons", [])))
    # Paired positive: both polarities occur, so "armed" is not hardcoded either way.
    check("arming-both-polarities", out and off and out["armed"] != off["armed"])


# ----------------------------------------------------------------- 2. contract

def _proto_dir(tmp, feasibility=None, html="prototype-minimal.html"):
    d = Path(tmp) / "proto"
    d.mkdir(parents=True, exist_ok=True)
    shutil.copy(FIX / html, d / "prototype.html")
    if feasibility:
        shutil.copy(FIX / feasibility, d / "feasibility.md")
    return d


# The rule is the COMPLEMENT of `web`, not a hand-kept list of native platforms.
# Swept over the whole enum PLUS unset, because unset is the documented default
# and therefore the configuration an iOS consumer most commonly ships — the case
# an enumeration silently exempts.
NON_WEB_CONFIGS = ["cfg-unset-platform.json", "cfg-ios.json", "cfg-android.json",
                   "cfg-tauri.json", "cfg-cli.json", "cfg-library.json", "cfg-none.json"]


def test_contract_web_exempt():
    with tempfile.TemporaryDirectory() as tmp:
        d = _proto_dir(tmp)
        _, out, _ = run("contract", "--dir", str(d), "--config", fx("cfg-web.json"))
        check("contract-web-exempt", out and out["ok"] is True,
              "platform: web is the single exempt value — there the prototype IS the medium")
        check("contract-web-not-required", out and out["feasibility_required"] is False)


def test_contract_requires_feasibility_unless_web():
    with tempfile.TemporaryDirectory() as tmp:
        d = _proto_dir(tmp)  # no feasibility.md
        for cfg in NON_WEB_CONFIGS:
            _, out, _ = run("contract", "--dir", str(d), "--config", fx(cfg))
            check(f"contract-requires-{cfg}", out and out["ok"] is False,
                  f"{cfg}: non-web with no feasibility read must NOT pass")


def test_contract_unset_platform_message():
    """CLAUDE.md: never silently no-op on an absent slot. Both remedies named."""
    with tempfile.TemporaryDirectory() as tmp:
        d = _proto_dir(tmp)
        _, out, _ = run("contract", "--dir", str(d), "--config", fx("cfg-unset-platform.json"))
        blob = " ".join(out.get("reasons", []) + out.get("problems", [])) if out else ""
        check("contract-unset-names-platform-remedy", "platform" in blob.lower())
        check("contract-unset-names-declare-remedy", "declare" in blob.lower())
        check("contract-unset-says-unset", "unset" in blob.lower())


def test_contract_rows_need_verdicts():
    with tempfile.TemporaryDirectory() as tmp:
        d = _proto_dir(tmp, "feas-unverdicted-ios.md")
        _, out, _ = run("contract", "--dir", str(d), "--config", fx("cfg-ios.json"))
        check("contract-unverdicted-row-fails", out and out["ok"] is False)
        check("contract-unverdicted-names-it",
              out and any("no verdict" in p for p in out.get("problems", [])))


def test_contract_requires_proxy_disclosure():
    with tempfile.TemporaryDirectory() as tmp:
        d = _proto_dir(tmp, "feas-no-disclosure-ios.md")
        _, out, _ = run("contract", "--dir", str(d), "--config", fx("cfg-ios.json"))
        check("contract-no-disclosure-fails", out and out["ok"] is False)
        check("contract-no-disclosure-names-it",
              out and any("proxy disclosure" in p for p in out.get("problems", [])))


def test_contract_native_complete():
    with tempfile.TemporaryDirectory() as tmp:
        d = _proto_dir(tmp, "feas-full-ios.md")
        _, out, _ = run("contract", "--dir", str(d), "--config", fx("cfg-ios.json"))
        check("contract-native-complete-ok", out and out["ok"] is True,
              f"problems: {out.get('problems') if out else '-'}")
        # must_surface is what stops the gate-1 message omitting the expensive rows.
        ms = out.get("must_surface", []) if out else []
        check("contract-must-surface-count", len(ms) == 2,
              f"expected the 2 non-native-standard rows, got {len(ms)}")
        check("contract-must-surface-excludes-standard",
              all("native-standard" not in r for r in ms))


def test_contract_browser_delivery_one_liner():
    """flow's OWN config: platform library + uiSurface true, shipping browser UI.
    Defining the exemption as `platform == web` alone would make gate 1
    UNREACHABLE in this very repo — the block would demand native-mechanism rows
    for a platform that has none, and `approve` refuses on a failed contract."""
    with tempfile.TemporaryDirectory() as tmp:
        d = _proto_dir(tmp, "feas-browser-oneline.md")
        for cfg in ("cfg-library.json", "cfg-none.json", "cfg-cli.json", "cfg-tauri.json"):
            _, out, _ = run("contract", "--dir", str(d), "--config", fx(cfg))
            check(f"contract-browser-oneline-{cfg}", out and out["ok"] is True,
                  f"{cfg}: one declaration line must satisfy a browser-delivered surface; "
                  f"problems={out.get('problems') if out else '-'}")


def test_contract_native_cannot_take_one_liner():
    """The one-line exit is CLOSED to unambiguously-proxied platforms, or § 9.4's
    only guard could be declared away by the author it constrains."""
    with tempfile.TemporaryDirectory() as tmp:
        d = _proto_dir(tmp, "feas-browser-oneline.md")
        for cfg in ("cfg-ios.json", "cfg-android.json"):
            _, out, _ = run("contract", "--dir", str(d), "--config", fx(cfg))
            check(f"contract-native-refuses-oneline-{cfg}", out and out["ok"] is False)
            check(f"contract-native-refuses-oneline-{cfg}-reason",
                  out and any("NOT available" in p for p in out.get("problems", [])))


def test_contract_deletion_not_green():
    """item 3: the presence assertion is paired with row-validity, so REMOVING
    the block fails rather than passing."""
    with tempfile.TemporaryDirectory() as tmp:
        d = _proto_dir(tmp, "feas-full-ios.md")
        _, before, _ = run("contract", "--dir", str(d), "--config", fx("cfg-ios.json"))
        (d / "feasibility.md").unlink()
        _, after, _ = run("contract", "--dir", str(d), "--config", fx("cfg-ios.json"))
        check("contract-deletion-flips-to-red",
              before and after and before["ok"] is True and after["ok"] is False,
              "deleting the feasibility block must turn the check RED, never green")


# ---------------------------------------------------------- 3. approve / verify

def test_approve_requires_quote():
    with tempfile.TemporaryDirectory() as tmp:
        d = _proto_dir(tmp, "feas-full-ios.md")
        missing = Path(tmp) / "nope.txt"
        proc = subprocess.run([sys.executable, str(ENGINE), "approve", "--dir", str(d),
                               "--quote-file", str(missing), "--config", fx("cfg-ios.json")],
                              capture_output=True, text=True)
        check("approve-refuses-missing-quote", proc.returncode != 0)
        check("approve-no-record-on-missing-quote", not (d / "approval.json").exists(),
              "a refusal must write NO record — a partial record is worse than none")
        for blank in ("", "   \n\t  \n"):
            q = Path(tmp) / "q.txt"
            q.write_text(blank, encoding="utf-8")
            proc = subprocess.run([sys.executable, str(ENGINE), "approve", "--dir", str(d),
                                   "--quote-file", str(q), "--config", fx("cfg-ios.json")],
                                  capture_output=True, text=True)
            check(f"approve-refuses-blank-quote-{len(blank)}", proc.returncode != 0)
            check(f"approve-no-record-blank-{len(blank)}", not (d / "approval.json").exists())


def test_approve_requires_contract():
    """This is what makes § 9.4 ASSERTED rather than advisory: a native prototype
    with no feasibility read cannot reach gate 1 at all."""
    with tempfile.TemporaryDirectory() as tmp:
        d = _proto_dir(tmp)  # no feasibility.md, platform ios
        q = Path(tmp) / "q.txt"
        q.write_text("yes, approved", encoding="utf-8")
        proc = subprocess.run([sys.executable, str(ENGINE), "approve", "--dir", str(d),
                               "--quote-file", str(q), "--config", fx("cfg-ios.json")],
                              capture_output=True, text=True)
        check("approve-refuses-failed-contract", proc.returncode != 0)
        check("approve-no-record-on-failed-contract", not (d / "approval.json").exists())
        # Paired positive: the SAME call succeeds once the contract passes, so the
        # refusal is about the contract and not about something incidental.
        shutil.copy(FIX / "feas-full-ios.md", d / "feasibility.md")
        rc, out, err = run("approve", "--dir", str(d), "--quote-file", str(q),
                           "--config", fx("cfg-ios.json"))
        check("approve-succeeds-once-contract-passes", out and out.get("ok") is True,
              f"stderr={err[:200]}")


def test_approve_record_shape():
    with tempfile.TemporaryDirectory() as tmp:
        d = _proto_dir(tmp, "feas-full-ios.md")
        q = Path(tmp) / "q.txt"
        q.write_text("Yes — approved, ship this look.", encoding="utf-8")
        rc, out, _ = run("approve", "--dir", str(d), "--quote-file", str(q), "--config", fx("cfg-ios.json"))
        rec_path = d / "approval.json"
        check("approve-writes-record", rec_path.is_file())
        if not rec_path.is_file():
            return
        rec = json.loads(rec_path.read_text(encoding="utf-8"))
        for field in ("sha256", "stamp", "platform", "contract_ok", "approved_by_human_quote"):
            check(f"approve-record-has-{field}", field in rec)
        check("approve-record-quote-verbatim",
              rec["approved_by_human_quote"] == "Yes — approved, ship this look.")
        check("approve-record-carries-must-surface", rec.get("must_surface"),
              "the expensive rows must ride along, so the gate-1 message cannot omit them")
        check("approve-emits-digest-line", out and "Prototype approved:" in out.get("digest_line", ""))
        # The digest is what gets COMMITTED; it must not mangle the human's words.
        check("approve-digest-not-ascii-escaped", out and "\\u2014" not in out.get("digest_line", ""),
              "the committed digest must render the quote readably, not JSON-escaped")


def test_verify_detects_drift():
    with tempfile.TemporaryDirectory() as tmp:
        d = _proto_dir(tmp, "feas-full-ios.md")
        q = Path(tmp) / "q.txt"
        q.write_text("approved", encoding="utf-8")
        run("approve", "--dir", str(d), "--quote-file", str(q), "--config", fx("cfg-ios.json"))
        _, clean, _ = run("verify", "--dir", str(d))
        check("verify-clean", clean and clean["ok"] is True)
        with (d / "prototype.html").open("a", encoding="utf-8") as fh:
            fh.write("<!-- edited after approval -->\n")
        _, drifted, _ = run("verify", "--dir", str(d))
        check("verify-detects-post-approval-edit", drifted and drifted["ok"] is False)
        check("verify-names-sha-mismatch",
              drifted and any("sha256" in p.lower() for p in drifted.get("problems", [])),
              "the sha mismatch must be named distinctly, not collapsed into a generic failure")


def test_quote_file_only():
    """FB-0108: untrusted text arrives as a file path, never argv. Asserted on
    BOTH halves — a missing `--quote` flag alone would also 'pass' if the whole
    subcommand were deleted."""
    proc = subprocess.run([sys.executable, str(ENGINE), "approve", "--help"],
                          capture_output=True, text=True)
    help_text = proc.stdout
    check("approve-has-quote-file-flag", "--quote-file" in help_text,
          "the positive half: the file-path interface must exist and be the ingestion route")
    check("approve-has-no-quote-string-flag", not re.search(r"--quote(?![-\w])", help_text),
          "a raw --quote string flag would re-open the door FB-0108 closed")


# ------------------------------------------------------------ 4. gate-execute

def test_gate_execute_reads_committed_state_only():
    """No `trigger` call, no `.flow/` read. An earlier design armed this guard on
    a live trigger — which reads the brief, which lives in gitignored `.flow/` —
    so wiping the workspace dropped it to ok:true VACUOUSLY. Run here with no
    `.flow/` in existence at all."""
    with tempfile.TemporaryDirectory() as tmp:
        plan = Path(tmp) / "plan.md"
        shutil.copy(FIX / "plan-prototype-ok.md", plan)
        rc, out, err = run("gate-execute", "--plan", str(plan), cwd=tmp)
        check("gate-execute-no-flow-dir-needed", out is not None and out["ok"] is True,
              f"must resolve from the plan doc alone; stderr={err[:200]}")


def test_gate_execute_blocks_missing_plan():
    with tempfile.TemporaryDirectory() as tmp:
        plan = Path(tmp) / "plan.md"
        shutil.copy(FIX / "plan-prototype-noplan.md", plan)
        _, out, _ = run("gate-execute", "--plan", str(plan))
        check("gate-execute-blocks-no-spec-walk", out and out["ok"] is False)
        check("gate-execute-names-the-plan-gap",
              out and any("Spec-walk" in p for p in out.get("problems", [])))


def test_gate_execute_blocks_missing_digest():
    """The resumed-workspace case. The fixture is RED, which the earlier design
    could not be: it armed on a live trigger that the same wipe turned to
    `classic`, so the guard reported ok:true on a branch with no human approval."""
    with tempfile.TemporaryDirectory() as tmp:
        plan = Path(tmp) / "plan.md"
        shutil.copy(FIX / "plan-prototype-nodigest.md", plan)
        _, out, _ = run("gate-execute", "--plan", str(plan), cwd=tmp)
        check("gate-execute-blocks-no-digest", out and out["ok"] is False,
              "a prototype-gated plan with no approval digest must be RED")
        check("gate-execute-names-digest-gap",
              out and any("digest" in p.lower() for p in out.get("problems", [])))


def test_gate_execute_passes_with_both():
    with tempfile.TemporaryDirectory() as tmp:
        plan = Path(tmp) / "plan.md"
        shutil.copy(FIX / "plan-prototype-ok.md", plan)
        _, out, _ = run("gate-execute", "--plan", str(plan))
        check("gate-execute-ok-with-both", out and out["ok"] is True,
              f"problems: {out.get('problems') if out else '-'}")
        check("gate-execute-counts-items", out and out.get("spec_walk_items") == 1)


def test_gate_execute_classic_noop():
    with tempfile.TemporaryDirectory() as tmp:
        plan = Path(tmp) / "plan.md"
        shutil.copy(FIX / "plan-classic.md", plan)
        _, out, _ = run("gate-execute", "--plan", str(plan))
        check("gate-execute-classic-ok", out and out["ok"] is True)
        check("gate-execute-classic-no-gate", out and out.get("gate") is None,
              "the classic path must cost nothing and require no digest")


def test_gate_execute_all_demoted():
    """The v1.30.0 all_demoted lifecycle bug, in a fifth consumer: a plan doc
    whose every block belongs to a merged PR has no ACTIVE plan, only history."""
    with tempfile.TemporaryDirectory() as tmp:
        plan = Path(tmp) / "plan.md"
        shutil.copy(FIX / "plan-all-demoted.md", plan)
        _, out, _ = run("gate-execute", "--plan", str(plan))
        check("gate-execute-all-demoted-blocks", out and out["ok"] is False,
              "an all-demoted plan doc must not read as an active plan")


def test_gate_execute_uses_shared_parser():
    src = ENGINE.read_text(encoding="utf-8")
    check("gate-execute-imports-walk-extract", "import walk_extract" in src,
          "must reuse the parser its four sibling consumers use, not a private copy")
    check("gate-execute-bare-label", 'extract_block(text, "Spec-walk")' in src,
          "heading_re() adds the **…:** wrapper itself; passing the bold form matches "
          "nothing and silently reports zero criteria")


# ---------------------------------------------------------------- 5. present

def test_present_authors_no_markup():
    """The byte-diff pin. If `present` rendered flow-authored chrome, this engine
    would be a SECOND browser-UI emitter alongside render-report.py — which sits
    inside uiFilePatterns precisely because it emits browser UI — and shipping it
    outside that pattern would exclude it from flow's own visual and a11y gates."""
    with tempfile.TemporaryDirectory() as tmp:
        f = Path(tmp) / "prototype.html"
        shutil.copy(FIX / "prototype-minimal.html", f)
        before = f.read_text(encoding="utf-8")
        _, out, _ = run("present", "--file", str(f))
        check("present-injects", out and out["injected"] is True)
        presented = f.with_suffix(".presented.html")
        check("present-writes-separate-file", presented.is_file(),
              "present must not mutate the source: `approve` hashes prototype.html, so "
              "injecting in place made the recorded sha cover prototype+layer")
        check("present-source-unmodified", f.read_text(encoding="utf-8") == before,
              "the source is the thing the human approved — it stays byte-identical")
        after = presented.read_text(encoding="utf-8")
        layer = LAYER.read_text(encoding="utf-8")
        i = before.rfind("</body>")
        expected = before[:i] + layer + before[i:]
        check("present-byte-identical-to-input-plus-partial", after == expected,
              "output must be EXACTLY input + the partial — no flow-authored markup")


def test_present_single_source():
    src = ENGINE.read_text(encoding="utf-8")
    check("present-reads-canonical-layer",
          '"verify-build" / "lib" / "annotation-layer.html"' in src,
          "must read the ONE source file, never a copy")
    with tempfile.TemporaryDirectory() as tmp:
        f = Path(tmp) / "prototype.html"
        shutil.copy(FIX / "prototype-minimal.html", f)
        run("present", "--file", str(f))
        first = f.with_suffix(".presented.html").read_text(encoding="utf-8")
        _, again, _ = run("present", "--file", str(f))
        second = f.with_suffix(".presented.html").read_text(encoding="utf-8")
        check("present-idempotent", first == second,
              "a second present must produce the same bytes — idempotent BY CONSTRUCTION "
              "now (it re-derives from an unmutated source), not by sniffing for an "
              "already-injected layer, which was a bandaid for mutating in place")


# ------------------------------------------------------------------- 6. docs

def _grep_hits(pattern, paths):
    """git grep, keyed on EXIT CODE (general.md item 4's corollary): `grep -c`
    returning 0 is ambiguous between 'no matches' and 'my pattern is wrong'."""
    proc = subprocess.run(["git", "grep", "-nIiE", pattern, "--", *paths],
                          cwd=ROOT, capture_output=True, text=True)
    if proc.returncode == 1:
        return []                      # exit 1 == no matches, per git grep's contract
    if proc.returncode != 0:
        raise RuntimeError(f"git grep failed ({proc.returncode}): {proc.stderr[:200]}")
    return [l for l in proc.stdout.splitlines() if l.strip()]


def test_sweep_patterns_are_not_vacuous():
    """item 4: run each detector against a case KNOWN to be positive before
    trusting its negative. A detector validated only on quiet inputs cannot be
    distinguished from a broken one — both predict the same output."""
    seeds = [("phase2", PHASE2_PAT, FIX / "seed-phase2-survivor.md"),
             ("gate", GATE_PAT, FIX / "seed-gate-survivor.md")]
    for label, pat, seed in seeds:
        hits = _grep_hits(pat, [str(seed.relative_to(ROOT))])
        check(f"sweep-{label}-pattern-fires-on-known-positive", len(hits) >= 1,
              f"the {label} pattern matched NOTHING on a seeded survivor — it is broken, "
              f"and every 'zero survivors' result it produces is meaningless")


def test_no_phase2_unbuilt_survivors():
    # `:!` excludes the evals tree: run_role_slot_evals.py ASSERTS the absence of
    # these phrases, so it necessarily contains them as string literals. A
    # detector quoting what it forbids is not a claim that the thing is true.
    hits = _grep_hits(PHASE2_PAT, ["plugins/", "README.md", ":!plugins/flow/evals/"])
    check("no-phase2-unbuilt-survivors", not hits,
          "Phase 1 honestly recorded that Phase 2 was unbuilt; this PR IS Phase 2, so every "
          f"such claim is now false. Survivors:\n  " + "\n  ".join(hits[:8]))


def test_phase2_positive_replacements():
    """The positive half, over a PRE-MERGE snapshot domain. Deriving the domain
    from the post-merge tree makes it self-emptying — the negative requires zero
    matches, so the domain is empty exactly when the positive would matter, and
    deletion becomes the cheapest green."""
    for f in PHASE2_DOMAIN:
        txt = f.read_text(encoding="utf-8")
        check(f"phase2-positive-{f.name}", "/flow:prototype" in txt,
              f"{f.name} retired its Phase-2-unbuilt claims but never names the shipped "
              "surface — satisfying the negative by deletion")


def test_gate_language_fanout():
    """One contract in several files, checked at the join rather than by author
    memory. Every hit is verdicted: corrected, or an explicitly recorded
    exemption — never bare enumeration."""
    # `:!fixtures/` excludes test DATA. The seed survivor in there exists precisely
    # to prove this pattern fires (item 4); sweeping it would make the corpus check
    # permanently red over its own instrument-validation input.
    # `:!` excludes test DATA and this harness itself. The seed survivor exists to
    # prove the pattern fires (item 4); this file DEFINES the pattern and names the
    # exemptions, so it necessarily contains the phrases. A detector quoting what it
    # searches for is not a claim that a gate is unconditional.
    hits = _grep_hits(GATE_PAT, ["plugins/", "README.md", ".claude/", "CLAUDE.md",
                                 ":!plugins/flow/evals/fixtures/",
                                 ":!plugins/flow/evals/run_prototype_gate_evals.py"])
    check("gate-sweep-found-something", len(hits) > 0,
          "a gate sweep returning nothing means the pattern broke, not that the corpus is clean")
    # Verdict at HIT granularity, not file granularity. The earlier predicate was
    # `"prototype" not in <whole file>`, so any file that mentioned prototype ANYWHERE
    # passed — even if the matched sentence still read "human-gated at Plan and Merge".
    # That is not "checked at the join", which is what this test claims to do.
    unverdicted = []
    _cache = {}
    for line in hits:
        path, lineno = line.split(":", 2)[0], int(line.split(":", 2)[1])
        if path in GATE_EXEMPT:
            continue
        lines = _cache.setdefault(path, (ROOT / path).read_text(encoding="utf-8").splitlines())
        # The matched line plus its immediate neighbours — a sentence asserting a gate
        # must account for BOTH shapes within its own paragraph, not three screens away.
        lo, hi = max(0, lineno - 2), min(len(lines), lineno + 2)
        para = " ".join(lines[lo:hi]).lower()
        if "prototype" not in para:
            unverdicted.append(line)
    check("gate-language-all-verdicted", not unverdicted,
          "every file asserting a pre-execution gate must account for BOTH shapes "
          f"(or be a recorded exemption). Unverdicted:\n  " + "\n  ".join(unverdicted[:8]))


def test_gate_exemptions_still_exist():
    """An exemption list is a contract too: if a path disappears, the exemption
    is silently protecting nothing and should be pruned rather than left to rot."""
    for rel in GATE_EXEMPT:
        check(f"gate-exemption-exists-{Path(rel).name}", (ROOT / rel).is_file(),
              f"{rel} is exempted but does not exist — stale exemption")


def test_workflow_step2_fork():
    t = WORKFLOW.read_text(encoding="utf-8")
    check("workflow-step2-renamed", "## 2. Pre-execution gate" in t)
    for needle, why in (
        ("Prototype-first", "the fork's second path must be named"),
        ("exactly one pre-execution human gate", "the invariant must be stated"),
        ("Never both, never neither", "both failure directions, not just one"),
        ("/flow:prototype", "the skill that owns the path"),
        ("gate-execute", "Step 3's call site for the plan-exists guard"),
    ):
        check(f"workflow-step2-{needle[:28]}", needle in t, why)
    # Step numbering must NOT have shifted: "Step 8" is a named contract in a
    # dozen places, and renumbering would be the largest fan-out this repo has shipped.
    for heading in ("## 3. Execute", "## 8. Present (conditional gate)", "## 10. /flow:ship", "## 11. STOP"):
        check(f"workflow-numbering-{heading[:14]}", heading in t,
              "the loop must NOT be renumbered — the fork lands inside Step 2")


def test_not_a_third_gate_rewrite():
    t = WORKFLOW.read_text(encoding="utf-8")
    # Positive: the replacement argument is actually made.
    check("third-gate-replacement-argued",
          "replacement, not exception" in t,
          "FB-0081's point is that the objection is answered by REPLACEMENT")
    check("third-gate-still-two", "Two gates, both paths" in t)
    # Negative, paired: the old unconditional claim is gone. Alone this would
    # pass on a deleted paragraph, which is why the positives above come first.
    check("third-gate-old-claim-retired",
          "Visual sign-off folds into the merge gate, not a third gate:" not in t,
          "the unconditional form must be retired, not merely supplemented")


def test_plan_surfaces_moved_gate():
    """A one-sided pin on a two-sided duplication is not a pin (FB-0100)."""
    for f in (PLAN_DISCIPLINE, PLANNER):
        t = f.read_text(encoding="utf-8")
        check(f"moved-gate-{f.name}-named", "prototype" in t.lower())
        check(f"moved-gate-{f.name}-no-second-gate",
              "second human gate" in t.lower() or "no second" in t.lower(),
              "both files must state that the post-gate-1 plan gets no second human gate")
        check(f"moved-gate-{f.name}-anchors-to-approval",
              "Prototype approved" in t or "approval record" in t.lower())


def test_brief_mode_scoping_fanout():
    for f in (WORKFLOW, PLAN_DISCIPLINE, PLANNER):
        t = f.read_text(encoding="utf-8")
        check(f"brief-mode-scoping-{f.name}",
              "not inherited" in t.lower() or "scopes" in t.lower(),
              "all three files a plan author reads must state that a brief's Mode scopes "
              "the pre-prototype phase only")


def test_tiny_definition_not_loosened():
    """The positive that pairs with making `tiny` reachable: nothing about the
    shipped definition gets looser anywhere. Sites are DERIVED by grepping the
    two literals, with a floor — a derivation with no floor finds zero sites when
    its pattern breaks and then asserts nothing at all (item 4)."""
    bar = _grep_hits(r"1–3 line|1-3 line", ["plugins/"])
    rarely = _grep_hits(r"Rarely the right call", ["plugins/"])
    check("tiny-bar-floor", len(bar) >= 5,
          f"expected >=5 sites carrying the 1–3-line bar, derived {len(bar)} — either the "
          "definition was loosened, or the pattern broke")
    check("tiny-rarely-floor", len(rarely) >= 2,
          f"expected >=2 sites carrying 'Rarely the right call', derived {len(rarely)}")


def test_tiny_delegation_preserved():
    """plan-discipline and planner.md DELEGATE the definition rather than
    carrying it. The scoping edit must not quietly turn one definition into a
    three-way duplication — the repo's dominant bug class."""
    for f in (PLAN_DISCIPLINE, PLANNER):
        t = f.read_text(encoding="utf-8")
        check(f"tiny-delegation-{f.name}", "1–3 line" not in t and "1-3 line" not in t,
              f"{f.name} must keep delegating the `tiny` definition, not restate it")


def test_lens_inputs_generalized():
    for f in (LENS_DE, LENS_UX):
        t = f.read_text(encoding="utf-8")
        check(f"lens-{f.name}-accepts-artifact", "RENDERED ARTIFACT" in t,
              "spawned by /flow:prototype the input is a prototype file, not a diff")
        check(f"lens-{f.name}-keeps-identity-rule", "Workspace identity" in t,
              "FB-0082's workspace-identity rule must survive the generalization")


def test_lens_experience_untouched():
    """Cut at the plan gate: the accessibility/timing question is a feature
    addition, not a claim this PR falsifies. Scope discipline."""
    proc = subprocess.run(["git", "diff", "--stat", "origin/main...HEAD", "--",
                           str(LENS_EXP.relative_to(ROOT))],
                          cwd=ROOT, capture_output=True, text=True)
    check("lens-experience-untouched", not proc.stdout.strip(),
          f"lens-experience.md must be unchanged; diff:\n{proc.stdout[:200]}")


def test_skill_composition():
    t = SKILL.read_text(encoding="utf-8")
    for sa in ("flow:lens-design-engineer", "flow:lens-ux-designer"):
        check(f"skill-names-{sa}", sa in t)
    check("skill-one-tool-message", "one tool message" in t.lower())
    check("skill-names-layer-source", "annotation layer" in t.lower())


def test_composes_review_brief():
    t = SKILL.read_text(encoding="utf-8")
    check("skill-calls-review-brief", 'Skill("flow:review-brief")' in t)
    check("skill-passes-brief-path", "Pass the path explicitly" in t,
          "the call alone would silently take review-brief's no-argument transcript branch")


def test_skill_produces_brief():
    t = SKILL.read_text(encoding="utf-8")
    check("skill-writes-brief", "brief.md" in t,
          "the brief must be PRODUCED by the loop, not assumed to exist")
    check("skill-accepts-brief-arg", "$ARGUMENTS" in t)


def test_brief_path_join():
    """Pin the JOIN rather than re-hardcoding the literal a third time — the
    `_extract_jq_src()` shape."""
    skill_t = SKILL.read_text(encoding="utf-8")
    m = re.search(r"\.flow/prototypes/[^\s`\"']+/brief\.md", skill_t)
    check("brief-path-declared-in-skill", m is not None,
          "the skill must name the canonical brief path")
    check("brief-path-under-prototypes-dir",
          m is not None and "prototypes/" in m.group(0),
          "brief and prototype must share one scratch home so one path resolves both")


def test_skill_never_self_approves():
    t = SKILL.read_text(encoding="utf-8")
    check("skill-forbids-self-approval",
          "may not approve on their behalf" in t or "not approve on the human's behalf" in t.lower())
    # Paired positive: the capture step that IS the legitimate route.
    check("skill-has-capture-step", "--quote-file" in t,
          "the prohibition needs its positive — the real way approval gets recorded")


def test_prototype_phase_runs_no_pipeline():
    """The PR's first declared deliverable, and the property that keeps the
    prototype phase from re-acquiring the ceremony D1 removes."""
    t = SKILL.read_text(encoding="utf-8")
    check("skill-states-no-pipeline",
          "no ship pipeline" in t.lower() and "no evals" in t.lower()
          and "no doc synthesis" in t.lower())
    for forbidden in ('Skill("flow:ship")', 'Skill("flow:ship-spike")', 'Skill("flow:staff-review")'):
        check(f"skill-does-not-call-{forbidden[7:-2]}", forbidden not in t)
    # Paired positive: the iterate-then-present loop is actually described, so
    # the prohibitions are not satisfiable by deleting the section.
    check("skill-describes-iteration", "Iterate freely" in t or "iteration is the point" in t.lower())


def test_review_brief_no_longer_unwired():
    t = REVIEW_BRIEF.read_text(encoding="utf-8")
    check("review-brief-names-caller", "/flow:prototype" in t,
          "positive replacement: the skill must name its in-loop caller")
    check("review-brief-verdict-string-fixed",
          "not yet built, D1 Phase 2" not in t,
          "the emitted VERDICT string would otherwise print 'not yet built' at the human "
          "from inside the phase that just invoked it")


def test_doctor_role_has_consumer():
    t = DOCTOR.read_text(encoding="utf-8")
    check("doctor-names-consumer", "/flow:prototype" in t)
    check("doctor-reports-path-liveness", "prototype-first path" in t,
          "'I set role: designer' and 'I can tell it's live' must not be two questions")
    check("doctor-reports-suppression", "SUPPRESSED" in t,
          "a designer overridden by uiSurface:false must be told, not silently reclassified")


def test_scratch_isolation_covers_prototype():
    """That harness hand-lists its sites (idiom_sites), so a new skill is NOT
    discovered. Without the edit, the scratch box passes while nothing ever reads
    prototype/SKILL.md."""
    t = SCRATCH_EVALS.read_text(encoding="utf-8")
    check("scratch-harness-lists-prototype", '"prototype"' in t,
          'append ("prototype", PROTOTYPE_SKILL) to idiom_sites — the list is hand-written')


def test_no_jq_dependency():
    """Measured, not assumed — the mistake two neighbouring boxes made, and the
    measurement changed the design. run_jq_guard_evals.py derives its targets by
    matching `jq -[re]` AND `flow.config.json` in a skill body. This skill matches
    NEITHER, because the engine parses config with Python's stdlib `json`. Rather
    than fake a jq call to land inside that harness, the skill declares no jq
    dependency and this box pins both halves."""
    src = SKILL.read_text(encoding="utf-8")
    check("prototype-skill-has-no-jq-read", re.search(r"jq -[re]", src) is None,
          "this skill reads no config in shell; a jq guard would imply a dependency it lacks")
    # Paired positive: the engine still refuses to guess at unreadable config.
    engine = ENGINE.read_text(encoding="utf-8")
    check("engine-fails-closed-on-malformed-config", '"malformed"' in engine
          and "config_malformed" in engine,
          "dropping the jq guard is only safe because the engine fails CLOSED on a config "
          "it cannot read — the positive that makes the absence defensible")


def test_root_anchor():
    """In THIS harness, not run_root_anchor_evals.py — that one derives from disk
    but filters to `context: fork` skills, and /flow:prototype fans out to Agent
    calls exactly like /flow:review-brief, so it would never be looked at."""
    t = SKILL.read_text(encoding="utf-8")
    check("root-anchor-present", "git rev-parse --show-toplevel" in t)
    check("root-anchor-bails-loudly", "ROOT-UNRESOLVED" in t,
          "a rootless run must not render byte-identically to a clean pass")
    check("root-anchor-symlink-refusal", "CWE-59" in t)


def test_dogfood_run_matches_engine():
    """A one-shot workspace observation, committed as a fixture — explicitly NOT
    a reviewer re-run (the shape run_plugin_provenance_evals.py uses).

    It pins the live path and the eval matrix to the SAME engine output rather
    than letting them agree by coincidence, and it records the case that
    corrected this PR's own analysis: flow is `uiSurface: true`, so its briefs
    DO clear the trigger. An earlier confidence verdict claimed Phase 2 was
    undogfoodable here and justified it with `platform` and `uiFilePatterns` —
    neither of which the trigger reads."""
    fixture = FIX / "this-workspace-20260920-trigger.json"
    check("dogfood-fixture-exists", fixture.is_file())
    if not fixture.is_file():
        return
    rec = json.loads(fixture.read_text(encoding="utf-8"))
    check("dogfood-reached-prototype-first", rec.get("path") == "prototype-first",
          f"flow's own repo must clear the trigger; got {rec.get('path')!r}")
    check("dogfood-gate-is-prototype", rec.get("pre_execution_gate") == "prototype")
    check("dogfood-config-was-readable", rec.get("config_state") == "ok")
    # Re-run the live engine against the same inputs and require the same verdict.
    brief = ROOT / ".flow" / "prototypes" / "dogfood" / "brief.md"
    if brief.is_file():
        _, live, _ = run("trigger", "--brief", str(brief), "--config", str(ROOT / "flow.config.json"))
        check("dogfood-live-matches-fixture",
              live and live.get("path") == rec.get("path")
              and live.get("pre_execution_gate") == rec.get("pre_execution_gate"),
              "the committed observation and the live engine must not have drifted apart")


# ----------------------------------------------------------------------- main

def main() -> int:
    for fn in [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]:
        try:
            fn()
        except Exception as exc:  # noqa: BLE001 - a harness crash must name its test
            _fails.append(f"{fn.__name__}: RAISED {exc.__class__.__name__}: {exc}")
    for f in _fails:
        print(f"FAIL  {f}")
    total = _passes + len(_fails)
    print(f"\n{_passes}/{total} checks passed")
    return 0 if not _fails else 1


if __name__ == "__main__":
    sys.exit(main())
