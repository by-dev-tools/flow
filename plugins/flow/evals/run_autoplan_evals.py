#!/usr/bin/env python3
"""
Regression eval for D1 Phase 3 — the auto-written technical plan and its MACHINE
gate (`dev-docs/handoffs/d1-prototype-first-gate.md` § Phase 3; gated on § 9.3,
resolved MIXED by #153).

Groups, in the order the plan's Spec-walk declares them:

  1. auto-write   The deliverable every other group assumes exists, plus the two
                  D1 header markers without which `gate-execute` fails OPEN.
  2. gate-level   The pass condition, stated once for all three arms: GREEN
                  requires each arm to have RUN, evidenced, and returned nothing.
  3. arm A        Criterion quality. Deterministic, and read from OUTPUT rather
                  than exit status — both tools exit 0 on every verdict, so an
                  exit-code gate is green on all input.
  4. arm B        Completeness. Depth, honesty, and never passing on silence.
  5. union        The finder wins; nothing averages; dedupe by symbol.
  6. arm C        `/flow:review-brief` generalized, and its partial-return case.
  7. routing      Which path runs at all, and the escalation's shape.
  8. docs         The fan-out this PR is most exposed to, checked at the join
                  rather than by author memory.

Two disciplines from `.claude/rules/general.md` § Consistency run throughout:

  item 3 — every prohibition is paired with the positive it protects, so the
           check cannot be satisfied by deleting the protected thing. The
           call-site checks are the sharpest instance: "the hand-write sentence
           is gone" passes equally if the hand-off were deleted, so the
           invocation is asserted POSITIVELY and a mutation fixture proves the
           assertion can go red.
  item 4 — a measurement that can only return "clean" is not a measurement.
           `test_arm_a_ignores_exit_status` exists because the first draft of
           this feature cited `walk-pin-lint.py … → exit 0` as evidence the
           lint worked, on a file carrying 591 unpinned checkboxes.

Stdlib only. No network. Run:
    python3 plugins/flow/evals/run_autoplan_evals.py
Exits non-zero on any failure (CI gate).
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENGINE = ROOT / "skills" / "autoplan" / "lib" / "gate.py"
SKILL = ROOT / "skills" / "autoplan" / "SKILL.md"
PROTOTYPE = ROOT / "skills" / "prototype" / "SKILL.md"
REVIEW_BRIEF = ROOT / "skills" / "review-brief" / "SKILL.md"
WORKFLOW = ROOT / "docs" / "workflow.md"
WORKFLOW_HELP = ROOT / "skills" / "workflow-help" / "SKILL.md"
MANIFEST_TRIAGE = ROOT / "skills" / "ship" / "lib" / "manifest-triage.py"
REPO = ROOT.parent.parent

_fails: list = []
_passes = 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global _passes
    if cond:
        _passes += 1
    else:
        _fails.append(f"{name}: {detail}")


def run(*args, stdin=None):
    proc = subprocess.run(
        [sys.executable, str(ENGINE), *args],
        capture_output=True, text=True, input=stdin,
    )
    try:
        return json.loads(proc.stdout), proc
    except ValueError:
        return None, proc


def gate_state(tmp: Path, state: dict):
    f = tmp / "state.json"
    f.write_text(json.dumps(state), encoding="utf-8")
    out, _ = run("gate", "--state-file", str(f))
    return out


def _arms(a=True, b=True, c=True, **over):
    """Three arms that all ran clean, so each test mutates exactly one thing."""
    base = [
        {"arm": "A", "ran": a, "evidence": "ran"},
        {"arm": "B", "ran": b, "evidence": "ran"},
        {"arm": "C", "ran": c, "evidence": "ran",
         "reviewers": {"auditor": "returned", "plan-critic": "returned",
                       "lens-experience": "returned"}},
    ]
    for arm in base:
        if arm["arm"] in over:
            arm.update(over[arm["arm"]])
    return base


def plan_doc(criteria, heading="**Spec-walk:**", preamble="", retained=""):
    body = preamble + heading + "\n\n"
    body += "".join(f"- [ ] {c}\n" for c in criteria)
    return body + retained


# ============================================================ 1. auto-write

def test_autoplan_produces_a_plan() -> None:
    """The skill must state that it writes a plan, and refuse to guess the path.

    Both polarities: "wrote nothing" must not read as success, and the skill must
    not silently invent a target when handed no argument.
    """
    t = SKILL.read_text(encoding="utf-8")
    check("autoplan-writes-a-plan", "Write the plan" in t or "Write the technical plan" in t,
          "the skill must own the auto-write, not assume a plan appears")
    check("autoplan-refuses-to-guess-the-path",
          "no session-mode fallback" in t and "may guess" in t,
          "a skill that writes a file must never guess which file")
    check("autoplan-requires-spec-walk-block", "**Spec-walk:**" in t)
    check("autoplan-places-block-first", "placed FIRST" in t or "placed first" in t)


def test_autoplan_writes_the_gate_markers_above_the_walk() -> None:
    """Both D1 markers, and ABOVE the block's own heading — the region `gate-execute` reads."""
    t = SKILL.read_text(encoding="utf-8")
    check("autoplan-names-gate-marker", "**Pre-execution gate:** prototype" in t)
    check("autoplan-names-digest-marker", "**Prototype approved:**" in t)
    check("autoplan-states-markers-go-above-the-walk",
          "ABOVE the block's own" in t,
          "placement is the whole point: `_active_region` reads above the FIRST heading")
    check("autoplan-states-the-failure-direction",
          "ok: true" in t and "asserted **nothing**" in t,
          "must state that a missing marker makes gate-execute pass having asserted nothing")


def test_missing_gate_marker_makes_gate_execute_red() -> None:
    """The failing direction, run against the SHIPPED guard rather than described.

    A plan whose active block carries no gate declaration must not read as approved.
    This is the Phase 2 bypass from the other side: not a retained digest satisfying
    a later gate, but a new first block carrying no digest at all.
    """
    guard = ROOT / "skills" / "prototype" / "lib" / "prototype-gate.py"
    if not guard.exists():
        return
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        subprocess.run(["git", "init", "-q", "-b", "main", str(tmp)], check=False)
        bare = tmp / "plan-no-markers.md"
        bare.write_text(plan_doc(["alpha emits X. → `test_a`"]), encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, str(guard), "gate-execute", "--plan", str(bare)],
            capture_output=True, text=True, cwd=str(tmp),
        )
        try:
            out = json.loads(proc.stdout)
        except ValueError:
            out = {}
        # The guard's own documented behaviour on an undeclared gate is ok:true
        # ("classic path, nothing to assert"). That is CORRECT in isolation and is
        # exactly why the auto-write must emit the markers -- this check pins the
        # hazard so a future reader cannot mistake the pass for an approval.
        check("gate-execute-without-markers-asserts-nothing",
              out.get("gate") != "prototype",
              "a plan with no gate declaration must not resolve as a prototype gate")
        check("autoplan-skill-owns-that-hazard",
              "declares no prototype gate" in SKILL.read_text(encoding="utf-8")
              or "asserted **nothing**" in SKILL.read_text(encoding="utf-8"),
              "the skill must name the fail-open it is responsible for closing")


# ============================================================ 2. gate-level

def test_pass_requires_evidence_of_running_all_arms() -> None:
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        green = gate_state(tmp, {"arms": _arms()})
        check("all-arms-ran-clean-is-green", green["verdict"] == "GREEN", str(green))
        for missing in ("A", "B", "C"):
            arms = [a for a in _arms() if a["arm"] != missing]
            out = gate_state(tmp, {"arms": arms})
            check(f"absent-arm-{missing}-is-red", out["verdict"] == "RED")
            check(f"absent-arm-{missing}-says-why",
                  any("never reported" in b for b in out["blockers"]))
        # An arm that ran but produced no evidence is not a pass either.
        out = gate_state(tmp, {"arms": _arms(A={"evidence": ""})})
        check("arm-without-evidence-is-red", out["verdict"] == "RED")


def test_arm_did_not_run_is_distinct_from_found_nothing() -> None:
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        ran = gate_state(tmp, {"arms": _arms()})
        not_run = gate_state(tmp, {"arms": _arms(b=False)})
        check("arm-b-not-run-is-red", not_run["verdict"] == "RED")
        check("arm-b-not-run-has-its-own-reason",
              any("DID NOT RUN" in b for b in not_run["blockers"]),
              "must not collapse into the same message as a clean pass")
        check("the-two-outcomes-differ", ran["verdict"] != not_run["verdict"],
              "ran-and-clean and did-not-run must not produce the same verdict")


def test_errored_reviewer_is_not_a_clean_pass() -> None:
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        out = gate_state(tmp, {"arms": _arms(B={"error": "HTTP 429"})})
        check("errored-arm-is-red", out["verdict"] == "RED")
        check("errored-arm-is-classified-as-did-not-run",
              any("DID NOT RUN" in b for b in out["blockers"]),
              "a 429 is an absence of a review, never a review that came back clean")


def test_zero_reference_docs_is_red() -> None:
    """A reviewer that could not read the project's rules has not reviewed.

    Not hypothetical: measured on this repo 2026-09-27, the installed plugin
    (1.29.0) could not comma-split `referenceGlob`, so every critique round on the
    Phase 3 plan itself ran document-blind.
    """
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        out = gate_state(tmp, {"arms": _arms(C={"document_blind": True})})
        check("document-blind-arm-is-red", out["verdict"] == "RED")
        check("document-blind-names-the-category-it-cannot-clear",
              any("Spec-violation" in b for b in out["blockers"]))
        sighted = gate_state(tmp, {"arms": _arms(C={"document_blind": False})})
        check("sighted-arm-is-green", sighted["verdict"] == "GREEN",
              "the positive half: blindness must be what makes it red, not arm C itself")


def test_low_verdict_routes_to_decision_required() -> None:
    """D1 moves PLAN APPROVAL. It does not move flow's third gate."""
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        low = gate_state(tmp, {"arms": _arms(),
                               "confidence_verdicts": [{"assumption": "depth 2", "confidence": "LOW"}]})
        check("low-verdict-is-red", low["verdict"] == "RED")
        check("low-verdict-is-a-decision-not-a-blocker",
              any("LOW" in (x.get("finding") or "") for x in low["decisions"]),
              "LOW escalates as an answerable question, it does not merely fail")
        check("low-verdict-cites-the-shipped-rule",
              any("cannot proceed" in (x.get("why") or "") for x in low["decisions"]))


def test_medium_verdict_proceeds() -> None:
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        for level in ("MEDIUM", "HIGH", "MEDIUM-HIGH"):
            out = gate_state(tmp, {"arms": _arms(),
                                   "confidence_verdicts": [{"assumption": "x", "confidence": level}]})
            check(f"{level}-verdict-proceeds", out["verdict"] == "GREEN",
                  "only LOW is an automatic gate; the others must not block")


def test_surviving_finding_escalates() -> None:
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        cleared = gate_state(tmp, {"arms": _arms(
            A={"findings": [{"tier": "auto-fixable", "survived_retry": False, "finding": "fixed"}]})})
        check("auto-fixable-that-cleared-proceeds", cleared["verdict"] == "GREEN")
        survived = gate_state(tmp, {"arms": _arms(
            A={"findings": [{"tier": "auto-fixable", "survived_retry": True, "finding": "still vacuous"}]})})
        check("auto-fixable-that-survived-escalates", survived["verdict"] == "RED")
        check("survivor-becomes-a-decision-not-a-second-retry",
              survived["decisions"] and "never gets a second retry"
              in (survived["decisions"][0].get("why") or ""))


def test_auto_fixable_single_retry() -> None:
    t = SKILL.read_text(encoding="utf-8")
    check("skill-states-one-retry", "re-review **once**" in t)
    check("skill-forbids-a-second-retry", "never a second retry" in t)
    check("skill-states-the-survivor-route", "becomes `[decision-required]`" in t)


# ============================================================ 3. arm A

def _arm_a(tmp: Path, criteria, expect_line=None, retained=""):
    p = tmp / "plan.md"
    p.write_text(plan_doc(criteria, retained=retained), encoding="utf-8")
    args = ["arm-a", "--plan", str(p)]
    if expect_line is not None:
        args += ["--expect-line", str(expect_line)]
    out, _ = run(*args)
    return out


def test_arm_a_vacuity_both_polarities() -> None:
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        vague = _arm_a(tmp, ["it works"])
        check("vacuous-criterion-is-red", vague["verdict"] == "RED", str(vague))
        check("vacuous-criterion-is-named", vague["vacuous_count"] >= 1)
        sharp = _arm_a(tmp, ["`depth` resolves to 2 on prototype-first. → `test_depth`"])
        check("sharpened-criterion-is-green", sharp["verdict"] == "GREEN", str(sharp))


def test_arm_a_pinning_both_polarities() -> None:
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        unpinned = _arm_a(tmp, ["`depth` resolves to 2 on the prototype-first path."])
        check("unpinned-criterion-is-red", unpinned["verdict"] == "RED", str(unpinned))
        check("unpinned-count-is-reported", unpinned["unpinned_count"] >= 1)
        pinned = _arm_a(tmp, ["`depth` resolves to 2 on prototype-first. → `test_depth`"])
        check("pinned-criterion-is-green", pinned["verdict"] == "GREEN", str(pinned))
        check("pinned-count-is-zero", pinned["unpinned_count"] == 0)


def test_retained_blocks_do_not_turn_arm_a_red() -> None:
    """The failing direction: unscoped, this arm is red forever on any repo that
    retains shipped blocks (measured on flow's own plan: 591 unpinned / 71 blocks)."""
    retained = (
        "\n\n### Old PR (shipped — merged as v1.0.0, #1)\n\n"
        "**Spec-walk:**\n\n- [ ] something nobody pinned\n- [ ] another unpinned thing\n"
    )
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        out = _arm_a(tmp, ["`depth` resolves to 2 on prototype-first. → `test_depth`"],
                     retained=retained)
        check("retained-unpinned-blocks-do-not-turn-arm-a-red",
              out["verdict"] == "GREEN",
              f"pinning must be scoped to the ACTIVE block; got {out}")
        check("retained-blocks-are-not-counted",
              out["unpinned_count"] == 0 and out["criteria_count"] == 1,
              "the arm must grade one block, not the whole document")


def test_arm_a_ignores_exit_status() -> None:
    """Both tools exit 0 on every verdict, so an exit-code gate is green on all input.

    Validated against a KNOWN POSITIVE first (item 4): the tools are confirmed to
    exit 0 while reporting a defect, and only then is the arm asserted RED on that
    same input. Without the first half, the second proves nothing.
    """
    spec = ROOT / "skills" / "verify-build" / "lib" / "criterion-specificity.py"
    extract = ROOT / "skills" / "verify-build" / "lib" / "extract-criteria.py"
    lint = ROOT / "skills" / "critique-plan" / "lib" / "walk-pin-lint.py"
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        p = tmp / "vague.md"
        p.write_text(plan_doc(["it works"]), encoding="utf-8")
        ex = subprocess.run([sys.executable, str(extract), str(p)],
                            capture_output=True, text=True)
        sp = subprocess.run([sys.executable, str(spec)], input=ex.stdout,
                            capture_output=True, text=True)
        check("known-positive: specificity REPORTS the defect",
              json.loads(sp.stdout).get("vacuous"),
              "if this is empty the rest of this test proves nothing")
        check("known-positive: specificity still exits 0",
              sp.returncode == 0,
              "the premise of the whole check: exit status carries no verdict")
        li = subprocess.run([sys.executable, str(lint)],
                            input=plan_doc(["it works"]), capture_output=True, text=True)
        check("known-positive: pin lint REPORTS unpinned", "unpinned" in li.stdout)
        check("known-positive: pin lint still exits 0", li.returncode == 0)
        out = _arm_a(tmp, ["it works"])
        check("arm-a-is-red-despite-both-tools-exiting-0", out["verdict"] == "RED",
              "the arm must read output, never $?")


def test_arm_a_proves_which_block_it_graded() -> None:
    """Keyed on the heading's LINE, the only field that varies per block.

    The fixture's two blocks carry IDENTICAL bare `**Spec-walk:**` headings, because
    that is the case that passes green under a `source_heading` assertion.
    """
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        p = tmp / "plan.md"
        p.write_text(
            "# Plan\n\n**Spec-walk:**\n\n- [ ] alpha emits X. → `test_a`\n"
            "\n### Retained (shipped — merged as v1.0.0, #1)\n\n"
            "**Spec-walk:**\n\n- [ ] beta emits Y. → `test_b`\n",
            encoding="utf-8")
        out, _ = run("arm-a", "--plan", str(p), "--expect-line", "3")
        check("arm-a-green-when-it-graded-the-expected-block", out["verdict"] == "GREEN", str(out))
        check("arm-a-reports-the-line-it-graded", out["graded_line"] == 3, str(out))
        wrong, _ = run("arm-a", "--plan", str(p), "--expect-line", "9")
        check("arm-a-red-when-it-graded-a-different-block", wrong["verdict"] == "RED")
        check("arm-a-says-which-block-it-graded",
              any("cannot prove which document" in r for r in wrong["reasons"]), str(wrong))
        # The discredited alternative, pinned so it cannot quietly come back: both
        # headings are the same string, so an assertion on `source_heading` could not
        # have told these two fixtures apart.
        ex = subprocess.run(
            [sys.executable, str(ROOT / "skills" / "verify-build" / "lib" / "extract-criteria.py"),
             str(p)], capture_output=True, text=True)
        data = json.loads(ex.stdout)
        check("source_heading-cannot-discriminate-blocks",
              data["source_heading"] == "**Spec-walk:**" and data["block_count"] == 2,
              "the premise for keying on the line number instead")
        check("extractor-surfaces-the-line", data.get("source_heading_line") == 3)


def test_arm_a_invokes_the_lint_directly() -> None:
    t = SKILL.read_text(encoding="utf-8")
    check("arm-a-calls-the-lint-directly", "walk-pin-lint.py" in t)
    check("arm-a-does-not-route-through-critique-plan",
          "not through `/flow:critique-plan`" in t,
          "a named plan file routes to UNCHECKED through critique-plan post-#165")
    engine = ENGINE.read_text(encoding="utf-8")
    check("engine-calls-all-three-tools",
          all(x in engine for x in ("extract-criteria.py", "criterion-specificity.py",
                                    "walk-pin-lint.py")))


def test_arm_a_unparseable_lint_is_not_clean() -> None:
    """A verdict line that does not parse is a failure to measure, not zero unpinned."""
    engine = ENGINE.read_text(encoding="utf-8")
    check("engine-fails-closed-on-unparseable-lint",
          "no parseable verdict line" in engine and '"ran": False' in engine,
          "defaulting to 0 unpinned would make a broken lint look like a clean plan")


# ============================================================ 4. arm B

def test_arm_b_depth_honesty() -> None:
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        f = tmp / "t.json"
        f.write_text(json.dumps({"path": "prototype-first"}), encoding="utf-8")
        out, _ = run("depth", "--trigger-file", str(f))
        check("prototype-first-resolves-depth-2", out["depth"] == 2, str(out))
        check("depth-states-what-it-is-worth", "unmeasured" in out.get("honesty", ""),
              "must never claim a figure for a depth nobody measured")
        check("depth-does-not-claim-100-percent", "100%" in out["honesty"]
              and "2 is between and unmeasured" in out["honesty"])


def test_depth_provenance_both_polarities() -> None:
    """'At declared depth' is half the pass condition; without this only what the
    output SAYS about depth is checked."""
    engine = ENGINE.read_text(encoding="utf-8")
    check("union-records-per-pass-provenance", "seen_in" in engine)
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        f = tmp / "p.json"
        f.write_text(json.dumps([
            {"findings": [{"symbol": "a", "finding": "A"}]},
            {"findings": [{"symbol": "a", "finding": "A"}]},
        ]), encoding="utf-8")
        out, _ = run("union", "--passes-file", str(f))
        check("union-reports-the-pass-count", out["passes"] == 2, str(out))
        check("union-records-which-passes-saw-it",
              out["findings"][0]["seen_in"] == [1, 2])
        f.write_text(json.dumps([{"findings": [{"symbol": "a", "finding": "A"}]}]),
                     encoding="utf-8")
        one, _ = run("union", "--passes-file", str(f))
        check("union-reports-a-smaller-recorded-depth", one["passes"] == 1,
              "recorded passes must be visible so a caller can compare to the declared depth")


def test_arm_b_writes_the_stamped_arg_file() -> None:
    t = SKILL.read_text(encoding="utf-8")
    check("arm-b-writes-the-arg-file", "--arg-path audit-coverage" in t)
    check("arm-b-asserts-no-WEAKENED", "WEAKENED" in t,
          "path 2 measures a different procedure from the one the honesty string describes")
    check("arm-b-states-the-figures-were-measured-on-path-1",
          "measured on path 1" in t or "were measured on path 1" in t)


def test_arm_b_never_passes_on_silence() -> None:
    t = SKILL.read_text(encoding="utf-8")
    check("skill-states-the-pass-condition-once",
          "Absence of findings is **never by itself a pass.**" in t)
    check("skill-states-silence-is-not-evidence",
          "silence is evidence of nothing" in t)


# ============================================================ 5. union

def test_union_never_averages() -> None:
    """A finding in 1 of 2 carries identical standing to one in 2 of 2."""
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        f = tmp / "p.json"
        f.write_text(json.dumps([
            {"findings": [{"symbol": "both", "finding": "seen twice"}]},
            {"findings": [{"symbol": "both", "finding": "seen twice"},
                          {"symbol": "once", "finding": "seen once"}]},
        ]), encoding="utf-8")
        out, _ = run("union", "--passes-file", str(f))
        by = {x["symbol"]: x for x in out["findings"]}
        check("both-findings-survive-the-union", set(by) == {"both", "once"}, str(out))
        check("neither-finding-is-downgraded",
              by["once"].get("severity") == by["both"].get("severity"),
              "a 1-of-2 finding must not be weakened relative to a 2-of-2 one")
        check("provenance-carries-its-interpretation",
              "not weaker evidence" in by["once"]["provenance"],
              "the reader must not be left to discount 1-of-2 on their own")
        # The gate must route them identically too, not merely record them alike.
        g = gate_state(tmp, {"arms": _arms(B={"findings": [by["once"], by["both"]]})})
        check("gate-routes-both-findings", len(g["decisions"]) == 2, str(g))
        check("gate-is-red-for-either", g["verdict"] == "RED")


def test_union_dedupes_by_symbol() -> None:
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        f = tmp / "p.json"
        f.write_text(json.dumps([
            {"findings": [{"symbol": "same", "finding": "x"}]},
            {"findings": [{"symbol": "same", "finding": "x restated differently"}]},
        ]), encoding="utf-8")
        out, _ = run("union", "--passes-file", str(f))
        check("same-gap-found-twice-is-one-item", len(out["findings"]) == 1, str(out))
        check("dedupe-records-both-sightings", out["findings"][0]["seen_in"] == [1, 2])


# ============================================================ 6. arm C

def test_arm_c_partial_return_is_red() -> None:
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        partial = gate_state(tmp, {"arms": _arms(C={"reviewers": {
            "auditor": "returned", "plan-critic": "errored: HTTP 429",
            "lens-experience": "returned"}})})
        check("arm-c-partial-fanout-is-red", partial["verdict"] == "RED")
        check("arm-c-names-the-missing-reviewer",
              any("plan-critic" in b for b in partial["blockers"]), str(partial))
        check("arm-c-explains-why-silence-is-ambiguous",
              any("three clean spawns" in b for b in partial["blockers"]))


def test_arm_c_all_clean_is_green() -> None:
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        out = gate_state(tmp, {"arms": _arms()})
        check("arm-c-all-three-returned-is-green", out["verdict"] == "GREEN", str(out))


def test_arm_c_is_review_brief_not_a_rebuild() -> None:
    t = SKILL.read_text(encoding="utf-8")
    check("arm-c-composes-review-brief", 'Skill("flow:review-brief")' in t)
    check("arm-c-says-it-is-not-new", "not new machinery" in t.lower())
    check("arm-c-does-not-reimplement-the-fanout",
          "auditor" in t and "re-implement" not in t.replace("Building it again", ""),
          "the fan-out must be composed, not rebuilt beside itself")


def test_review_brief_next_step_is_call_site_supplied() -> None:
    t = REVIEW_BRIEF.read_text(encoding="utf-8")
    check("review-brief-has-a-call-context-section", "## Call context" in t)
    check("review-brief-next-step-is-caller-supplied",
          "proceed to <the next step your caller named>" in t)
    check("review-brief-forbids-an-unnamed-next-step",
          "Never emit a next step your caller did not name" in t)
    check("review-brief-documents-a-default",
          "default to *design brief*" in t,
          "a direct human invocation must still get a sane, stated default")
    check("review-brief-reports-a-missing-reviewer", "DID NOT RETURN" in t)


def test_phase_3_verdict_does_not_name_prototype() -> None:
    """At Arm C the prototype phase is already complete; a verdict naming it is false."""
    t = REVIEW_BRIEF.read_text(encoding="utf-8")
    check("review-brief-verdict-is-not-hardcoded-to-the-prototype-phase",
          "VERDICT: [proceed to the prototype phase (/flow:prototype)" not in t)
    check("autoplan-names-its-own-next-step",
          "Execute" in SKILL.read_text(encoding="utf-8"))
    check("autoplan-forbids-a-prototype-verdict",
          "already complete when Arm C runs" in SKILL.read_text(encoding="utf-8"))


def test_review_brief_is_artifact_neutral() -> None:
    t = REVIEW_BRIEF.read_text(encoding="utf-8")
    check("review-brief-names-both-call-sites",
          "/flow:prototype" in t and "/flow:autoplan" in t)
    check("review-brief-generalized-its-noun",
          "the artifact under review" in t or "the document under review" in t)
    check("review-brief-keeps-its-name",
          "name: review-brief" in t,
          "renaming a shipped model-invocable skill breaks consumers for a cosmetic gain")


# ============================================================ 7. routing

def test_autoplan_runs_only_on_prototype_first() -> None:
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        f = tmp / "t.json"
        for path, applies in (("prototype-first", True), ("collapsed", False), ("classic", False)):
            f.write_text(json.dumps({"path": path}), encoding="utf-8")
            out, _ = run("depth", "--trigger-file", str(f))
            check(f"{path}-applies-{applies}", out["applies"] is applies, str(out))
            check(f"{path}-is-a-clean-outcome", out["ok"] is True,
                  "not applying is a correct result, never an error")
        for path in ("collapsed", "classic"):
            f.write_text(json.dumps({"path": path}), encoding="utf-8")
            out, _ = run("depth", "--trigger-file", str(f))
            check(f"{path}-explains-the-human-still-gates",
                  any("human" in r and "gates" in r for r in out["reasons"]), str(out))


def test_spike_has_no_undeclared_depth() -> None:
    """An unrecognized path refuses rather than defaulting.

    A depth nobody declared cannot later be distinguished from a procedure that
    did not run — the exact ambiguity this engine forbids, reintroduced via routing.
    """
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        f = tmp / "t.json"
        for bogus in ("spike", "", "unknown", None):
            f.write_text(json.dumps({"path": bogus}), encoding="utf-8")
            out, _ = run("depth", "--trigger-file", str(f))
            check(f"unrecognized-path-{bogus!r}-refuses", out["ok"] is False, str(out))
            check(f"unrecognized-path-{bogus!r}-has-no-depth", out["depth"] is None)


def test_decision_required_renders_an_answerable_question() -> None:
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        f = tmp / "e.json"
        f.write_text(json.dumps([{
            "finding": "Esc closes the editor but leaves the pin",
            "drafted_resolution": "add a criterion covering Esc twice",
            "provenance": "Found by 1 of 2 coverage passes. That is not weaker evidence — "
                          "this reviewer has never reported a gap that was not real.",
        }]), encoding="utf-8")
        proc = subprocess.run([sys.executable, str(ENGINE), "render-decisions",
                               "--entries-file", str(f)], capture_output=True, text=True)
        out = proc.stdout
        check("escalation-is-numbered", re.search(r"^1\. ", out, re.M) is not None, out)
        check("escalation-drafts-the-resolution", "What I'd do:" in out,
              "the resolution is drafted, not requested")
        check("escalation-asks-a-yes-no", "What I need from you: yes" in out)
        check("escalation-states-provenance-with-its-interpretation",
              "not weaker evidence" in out)
        # No `or True`: the first draft of this check was `X or True`, which can only
        # pass. A check that cannot fail is not a check -- the same class this harness
        # exists to enforce, committed inside the harness itself.
        empty = f.parent / "empty.json"
        empty.write_text("[]", encoding="utf-8")
        blank = subprocess.run([sys.executable, str(ENGINE), "render-decisions",
                                "--entries-file", str(empty)],
                               capture_output=True, text=True)
        check("empty-entries-render-nothing", blank.stdout.strip() == "",
              f"expected no escalation for zero decisions, got {blank.stdout!r}")
        check("empty-entries-still-exit-clean", blank.returncode == 0,
              "nothing to escalate is a normal outcome, not an error")


def test_escalation_header_matches_shipped() -> None:
    """One user-facing contract, one spelling. Detection, not prevention — the
    drift-proof fix is a shared constant, deferred to roadmap D1f."""
    if not MANIFEST_TRIAGE.exists():
        return
    ship = MANIFEST_TRIAGE.read_text(encoding="utf-8")
    m = re.search(r'"(\*\*Decisions for you\*\*[^"]*)"', ship)
    check("shipped-header-is-findable", m is not None,
          "if this fails the assertion below is vacuous, not passing")
    if not m:
        return
    # Asserted on RENDERED OUTPUT, not on the engine's source. A source grep here
    # matched this file's own explanatory comment about the shipped wording and passed
    # for the wrong reason -- the criterion belongs at the layer where it is CLAIMED
    # (the text a human reads), not one layer below it.
    with tempfile.TemporaryDirectory() as d:
        f = Path(d) / "e.json"
        f.write_text(json.dumps([{"finding": "x"}]), encoding="utf-8")
        rendered = subprocess.run(
            [sys.executable, str(ENGINE), "render-decisions", "--entries-file", str(f)],
            capture_output=True, text=True).stdout
    shipped_first_sentence = m.group(1).split(".")[0] + "."
    check("autoplan-header-matches-the-shipped-one",
          shipped_first_sentence in rendered,
          f"expected {shipped_first_sentence!r} in the RENDERED escalation")
    check("autoplan-header-diverges-only-in-the-trailing-clause",
          "Execute starts" in rendered and "closer to ready" not in rendered,
          "no PR exists at this gate, so the shipped trailing promise would be false")


# ============================================================ 8. docs

def test_hand_off_invokes_autoplan() -> None:
    """POSITIVE: the call must be present. 'The hand-write sentence is gone' passes
    equally if the hand-off were deleted (FB-0010 item 3)."""
    t = PROTOTYPE.read_text(encoding="utf-8")
    check("hand-off-invokes-autoplan", 'Skill("flow:autoplan")' in t,
          "without a call site the skill ships unreachable — the FB-0077 shape")
    check("hand-off-still-calls-gate-execute", "gate-execute" in t,
          "the positive half: the guard must not be deleted to satisfy the above")


def test_hand_off_order_is_autoplan_then_gate_execute() -> None:
    t = PROTOTYPE.read_text(encoding="utf-8")
    i_auto = t.find('Skill("flow:autoplan")')
    i_gate = t.find("gate-execute --plan")
    check("autoplan-precedes-gate-execute", -1 < i_auto < i_gate,
          "the guard reads above the FIRST Spec-walk heading, which autoplan writes")
    check("hand-off-states-why-the-order-matters", "order is load-bearing" in t)


def test_hand_off_missing_call_is_red() -> None:
    """The instrument, run against a known positive. An assertion that has never
    returned RED is not an assertion (FB-0010 item 4)."""
    t = PROTOTYPE.read_text(encoding="utf-8")
    mutated = t.replace('Skill("flow:autoplan")', "Write the technical plan by hand")
    check("mutation-actually-changed-the-fixture", mutated != t,
          "if this fails the check below proves nothing")
    check("reachability-check-goes-red-on-the-mutation",
          'Skill("flow:autoplan")' not in mutated,
          "the same predicate test_hand_off_invokes_autoplan uses must fail here")


def test_hand_off_names_the_shipped_review_set() -> None:
    t = PROTOTYPE.read_text(encoding="utf-8")
    for arm in ("Arm A", "Arm B", "Arm C"):
        check(f"hand-off-names-{arm.replace(' ', '-')}", arm in t)
    check("hand-off-ordinal-is-not-stale", "The third of those" not in t,
          "an ordinal into a three-skill list that is now three arms")
    check("hand-off-attributes-the-limitation-to-arm-b",
          "Arm B has a measured limitation" in t)


def test_autoplan_registered_at_three_sites() -> None:
    """The ship rule names three registration surfaces; the first draft listed one."""
    for label, path in (("README", REPO / "README.md"),
                        ("workflow", WORKFLOW),
                        ("workflow-help", WORKFLOW_HELP)):
        if not path.exists():
            continue
        check(f"autoplan-registered-in-{label}",
              "flow:autoplan" in path.read_text(encoding="utf-8"),
              f"a new skill must be registered in {path}")


def test_no_live_not_built_claim() -> None:
    """Retired everywhere live; `changelog/` is deliberately untouched — it records
    what was true at v1.48.0, and editing history to agree with the present is the
    wrong repair."""
    proc = subprocess.run(
        ["git", "grep", "-lEi", r"phase 3.{0,60}(not built|is gated)", "--",
         "plugins/", "README.md",
         # This harness DEFINES the pattern, so it necessarily contains it. A detector
         # quoting what it searches for is not a live claim (same exemption
         # run_prototype_gate_evals.py grants itself).
         ":!plugins/flow/evals/run_autoplan_evals.py"],
        capture_output=True, text=True, cwd=str(REPO))
    # `git grep -l` exits 1 when there are no matches: key on the EXIT CODE, not a
    # count of output (item 4's corollary).
    check("no-live-not-built-claim", proc.returncode == 1,
          f"still live in: {proc.stdout.strip()}")
    hist = subprocess.run(
        ["git", "grep", "-lEi", "not built yet", "--", "changelog/"],
        capture_output=True, text=True, cwd=str(REPO))
    check("changelog-history-is-preserved", hist.returncode == 0,
          "the v1.48.0 changelog must keep saying what was true then")


def test_review_brief_catalog_sweep_has_no_survivors() -> None:
    proc = subprocess.run(
        ["git", "grep", "-nEi", "pre-prototype review|reviews a brief|review of a design brief",
         "--", "README.md", "plugins/",
         ":!plugins/flow/evals/run_autoplan_evals.py"],
        capture_output=True, text=True, cwd=str(REPO))
    check("no-catalog-survivor-describes-review-brief-as-brief-only",
          proc.returncode == 1,
          f"survivors: {proc.stdout.strip()}")
    # Paired positive: the sweep must not have been satisfied by deleting the rows.
    rows = subprocess.run(["git", "grep", "-c", "review-brief", "--", "README.md"],
                          capture_output=True, text=True, cwd=str(REPO))
    check("review-brief-still-appears-in-the-README", rows.returncode == 0,
          "the sweep must generalize the rows, not remove them")


def test_skill_has_no_jq_dependency() -> None:
    t = SKILL.read_text(encoding="utf-8")
    check("skill-states-why-no-jq-guard", "No `jq` guard here" in t)
    check("skill-does-not-shell-out-to-jq", "jq -r" not in t,
          "config reads go through the engine's stdlib json, which fails closed")


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
