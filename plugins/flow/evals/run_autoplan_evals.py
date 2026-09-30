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

import contextlib
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from eval_utils import git_repo  # noqa: E402 - path set immediately above

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


def run(*args, stdin=None, cwd=None):
    """Drive the engine through its CLI, from `cwd`.

    `cwd` is not incidental. `gate.py` confines every path it reads to the repository
    the PROCESS is running in, so a fixture written to a temp dir is correctly refused
    unless the engine is run from there. Passing the temp dir is also the honest
    invocation: it is what a consumer repo looks like from the engine's point of view.
    """
    proc = subprocess.run(
        [sys.executable, str(ENGINE), *args],
        capture_output=True, text=True, input=stdin, cwd=cwd,
    )
    try:
        return json.loads(proc.stdout), proc
    except ValueError:
        return None, proc


@contextlib.contextmanager
def _scratch():
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


def gate_state(state: dict):
    """One gate run against one fixture, managing its own scratch.

    Previously took a caller-supplied `tmp`, which forced nine tests to open a
    `TemporaryDirectory` they used for nothing else — two lines of prologue and a
    level of indentation each, for a directory only this helper touched.
    """
    with _scratch() as tmp:
        f = tmp / "state.json"
        f.write_text(json.dumps(state), encoding="utf-8")
        out, _ = run("gate", "--state-file", str(f), cwd=str(tmp))
        return out


def depth_of(trigger: dict):
    with _scratch() as tmp:
        f = tmp / "trigger.json"
        f.write_text(json.dumps(trigger), encoding="utf-8")
        out, _ = run("depth", "--trigger-file", str(f), cwd=str(tmp))
        return out


def render_of(entries: list):
    """Returns the rendered escalation TEXT (not JSON) — the layer a human reads."""
    with _scratch() as tmp:
        f = tmp / "entries.json"
        f.write_text(json.dumps(entries), encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, str(ENGINE), "render-decisions", "--entries-file", str(f)],
            capture_output=True, text=True, cwd=str(tmp))
        return proc


def union_of(passes: list):
    with _scratch() as tmp:
        f = tmp / "passes.json"
        f.write_text(json.dumps(passes), encoding="utf-8")
        out, _ = run("union", "--passes-file", str(f), cwd=str(tmp))
        return out


def _arms(**over):
    """Three arms that all ran clean, so each test mutates exactly one thing.

    Mutate through `**over` only. Boolean `a`/`b`/`c` params also existed and were
    two-thirds dead — `_arms(B={"ran": False})` and `_arms(B={"ran": False})` did the same
    thing, which a reader had to work out.
    """
    base = [
        {"arm": "A", "ran": True, "evidence": "ran"},
        {"arm": "B", "ran": True, "evidence": "ran"},
        {"arm": "C", "ran": True, "evidence": "ran",
         "reviewers": {"auditor": "returned", "plan-critic": "returned",
                       "lens-experience": "returned"}},
    ]
    for arm in base:
        if arm["arm"] in over:
            arm.update(over[arm["arm"]])
    return base


def plan_doc(criteria, retained=""):
    body = "**Spec-walk:**\n\n"
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


def test_autoplan_plan_is_well_formed() -> None:
    """The required plan-discipline fields, plus both D1 header markers."""
    t = SKILL.read_text(encoding="utf-8")
    for field in ("Mode", "Goal", "Scope in/out", "Spec-walk", "confidence verdicts",
                  "risks", "Files touched"):
        check(f"autoplan-requires-{field.replace(' ', '-').replace('/', '-')}",
              field in t, f"every downstream consumer anchors to that shape; {field} missing")
    check("autoplan-names-gate-marker", "**Pre-execution gate:** prototype" in t)
    check("autoplan-names-digest-marker", "**Prototype approved:**" in t)


def test_autoplan_writes_the_gate_markers_above_the_walk() -> None:
    """PLACEMENT, which is a separate criterion from presence and fails differently.

    Presence without placement still fails open: `_active_region` reads everything
    above the FIRST `Spec-walk` heading, so a marker below it is invisible to the guard.
    """
    t = SKILL.read_text(encoding="utf-8")
    check("autoplan-states-markers-go-above-the-walk",
          "ABOVE the block's own" in t,
          "placement is the whole point: `_active_region` reads above the FIRST heading")
    check("autoplan-states-the-failure-direction",
          "ok: true" in t and "asserted **nothing**" in t,
          "must state that a missing marker makes gate-execute pass having asserted nothing")
    check("autoplan-explains-why-first-placement-causes-it",
          "makes *its* header the region that guard reads" in t,
          "the hazard is caused by the block being first, which this skill requires")


def test_missing_gate_marker_makes_gate_execute_red() -> None:
    """The failing direction, run against the SHIPPED guard rather than described.

    A plan whose active block carries no gate declaration must not read as approved.
    This is the Phase 2 bypass from the other side: not a retained digest satisfying
    a later gate, but a new first block carrying no digest at all.
    """
    guard = ROOT / "skills" / "prototype" / "lib" / "prototype-gate.py"
    if not guard.exists():
        return
    with _scratch() as tmp:
        # eval_utils.git_repo, not a hand-rolled `git init`. Its docstring records that
        # five harnesses each grew their own copy and asks new ones to import instead,
        # "so the eventual hoist is a deletion instead of a rewrite" — this would have
        # been the sixth. It also commits, which the local version did not.
        git_repo(tmp, {"plan-no-markers.md": plan_doc(["alpha emits X. → `test_a`"])})
        bare = tmp / "plan-no-markers.md"
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
        # Paired with `ok is True`: on unparseable stdout `out` is {}, so the
        # inequality alone was green whether the guard behaved or died.
        check("gate-execute-without-markers-asserts-nothing",
              out.get("ok") is True and out.get("gate") != "prototype",
              "a plan with no gate declaration must not resolve as a prototype gate")
        check("autoplan-skill-owns-that-hazard",
              "declares no prototype gate" in SKILL.read_text(encoding="utf-8")
              or "asserted **nothing**" in SKILL.read_text(encoding="utf-8"),
              "the skill must name the fail-open it is responsible for closing")


# ============================================================ 2. gate-level

def test_pass_requires_evidence_of_running_all_arms() -> None:
    green = gate_state({"arms": _arms()})
    check("all-arms-ran-clean-is-green", green["verdict"] == "GREEN", str(green))
    for missing in ("A", "B", "C"):
        arms = [a for a in _arms() if a["arm"] != missing]
        out = gate_state({"arms": arms})
        check(f"absent-arm-{missing}-is-red", out["verdict"] == "RED")
        check(f"absent-arm-{missing}-says-why",
              any("never reported" in b for b in out["blockers"]))
    # An arm that ran but produced no evidence is not a pass either.
    out = gate_state({"arms": _arms(A={"evidence": ""})})
    check("arm-without-evidence-is-red", out["verdict"] == "RED")


def test_arm_b_not_run_is_red() -> None:
    ran = gate_state({"arms": _arms()})
    not_run = gate_state({"arms": _arms(B={"ran": False})})
    check("arm-b-not-run-is-red", not_run["verdict"] == "RED")
    check("arm-b-not-run-has-its-own-reason",
          any("DID NOT RUN" in b for b in not_run["blockers"]),
          "must not collapse into the same message as a clean pass")
    check("the-two-outcomes-differ", ran["verdict"] != not_run["verdict"],
          "ran-and-clean and did-not-run must not produce the same verdict")


def test_errored_reviewer_is_not_a_clean_pass() -> None:
    out = gate_state({"arms": _arms(B={"error": "HTTP 429"})})
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
    out = gate_state({"arms": _arms(C={"document_blind": True})})
    check("document-blind-arm-is-red", out["verdict"] == "RED")
    check("document-blind-names-the-category-it-cannot-clear",
          any("Spec-violation" in b for b in out["blockers"]))
    sighted = gate_state({"arms": _arms(C={"document_blind": False})})
    check("sighted-arm-is-green", sighted["verdict"] == "GREEN",
          "the positive half: blindness must be what makes it red, not arm C itself")


def test_low_verdict_routes_to_decision_required() -> None:
    """D1 moves PLAN APPROVAL. It does not move flow's third gate."""
    low = gate_state({"arms": _arms(),
                           "confidence_verdicts": [{"assumption": "depth 2", "confidence": "LOW"}]})
    check("low-verdict-is-red", low["verdict"] == "RED")
    check("low-verdict-is-a-decision-not-a-blocker",
          any("LOW" in (x.get("finding") or "") for x in low["decisions"]),
          "LOW escalates as an answerable question, it does not merely fail")
    check("low-verdict-cites-the-shipped-rule",
          any("cannot proceed" in (x.get("why") or "") for x in low["decisions"]))


def test_medium_verdict_proceeds() -> None:
    for level in ("MEDIUM", "HIGH", "MEDIUM-HIGH"):
        out = gate_state({"arms": _arms(),
                               "confidence_verdicts": [{"assumption": "x", "confidence": level}]})
        check(f"{level}-verdict-proceeds", out["verdict"] == "GREEN",
              "only LOW is an automatic gate; the others must not block")


def test_surviving_finding_escalates() -> None:
    cleared = gate_state({"arms": _arms(
        A={"findings": [{"tier": "auto-fixable", "survived_retry": False, "finding": "fixed"}]})})
    check("auto-fixable-that-cleared-proceeds", cleared["verdict"] == "GREEN")
    survived = gate_state({"arms": _arms(
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
    out, _ = run(*args, cwd=str(tmp))
    return out


def test_arm_a_vacuous_both_polarities() -> None:
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
        out, _ = run("arm-a", "--plan", str(p), "--expect-line", "3", cwd=str(tmp))
        check("arm-a-green-when-it-graded-the-expected-block", out["verdict"] == "GREEN", str(out))
        check("arm-a-reports-the-line-it-graded", out["graded_line"] == 3, str(out))
        wrong, _ = run("arm-a", "--plan", str(p), "--expect-line", "9", cwd=str(tmp))
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


def test_arm_a_owns_its_pinning() -> None:
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
    """A pinning predicate that cannot be loaded is a failure to MEASURE, not zero
    unpinned — asserted behaviourally against a stub tree, not by grepping this
    engine for its own error strings.

    The grep version passed if the sentence existed anywhere in `gate.py`, including
    in a comment, and would have kept passing if the branch were deleted and the
    comment left behind. That is the same defect `test_escalation_header_matches_shipped`
    diagnosed in itself. The `--lib-root` seam exists to make this one real.
    """
    real = ROOT / "skills"
    with _scratch() as tmp:
        stub = tmp / "libs"
        (stub / "verify-build" / "lib").mkdir(parents=True)
        (stub / "critique-plan" / "lib").mkdir(parents=True)
        for f in (real / "verify-build" / "lib").glob("*.py"):
            (stub / "verify-build" / "lib" / f.name).write_text(
                f.read_text(encoding="utf-8"), encoding="utf-8")
        # A lint module that loads fine but exposes no predicate.
        (stub / "critique-plan" / "lib" / "walk-pin-lint.py").write_text(
            '"""stub: no is_pinned"""\n', encoding="utf-8")
        plan = tmp / "plan.md"
        plan.write_text(plan_doc(["alpha emits X. \u2192 `test_a`"]), encoding="utf-8")

        out, _ = run("arm-a", "--plan", str(plan), "--lib-root", str(stub), cwd=str(tmp))
        check("unloadable-predicate-is-red", out["verdict"] == "RED", str(out))
        check("unloadable-predicate-is-did-not-run", out["ran"] is False,
              "it must not report a verdict it never measured")
        check("unloadable-predicate-says-so",
              any("DID NOT RUN" in r for r in out["reasons"]), str(out))
    # The positive half runs entirely inside the flow repo, because `--lib-root` is now
    # confined to the cwd's repository — pointing it at this checkout from a tempdir is
    # exactly the traversal the guard exists to refuse, so the positive must not ask for
    # it. (The staff-engineer lens predicted this collision when it proposed confining
    # --lib-root; keeping the stub NEGATIVE in a temp repo and the POSITIVE in the real
    # one satisfies both.)
    repo = ROOT.parent.parent
    ok, _ = run("arm-a", "--plan", "dev-docs/plan.md",
                "--lib-root", "plugins/flow/skills", cwd=str(repo))
    check("real-predicate-tree-is-green", ok.get("verdict") == "GREEN", str(ok))
    check("real-predicate-tree-ran", ok.get("ran") is True, str(ok))


# ============================================================ 4. arm B

def test_arm_b_depth_honesty() -> None:
    out = depth_of({"path": "prototype-first"})
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
    out = union_of([
        {"findings": [{"symbol": "a", "finding": "A"}]},
        {"findings": [{"symbol": "a", "finding": "A"}]},
    ])
    check("union-reports-the-pass-count", out["passes"] == 2, str(out))
    check("union-records-which-passes-saw-it",
          out["findings"][0]["seen_in"] == [1, 2])
    one = union_of([{"findings": [{"symbol": "a", "finding": "A"}]}])
    check("union-reports-a-smaller-recorded-depth", one["passes"] == 1,
          "recorded passes must be visible so a caller can compare to the declared depth")


def test_arm_b_uses_the_filtered_path() -> None:
    t = SKILL.read_text(encoding="utf-8")
    check("arm-b-writes-the-arg-file", "--arg-path audit-coverage" in t)
    check("arm-b-asserts-no-WEAKENED", "WEAKENED" in t,
          "path 2 measures a different procedure from the one the honesty string describes")
    check("arm-b-states-the-figures-were-measured-on-path-1",
          "measured on path 1" in t or "were measured on path 1" in t)


def test_arm_b_silence_is_not_a_pass() -> None:
    t = SKILL.read_text(encoding="utf-8")
    check("skill-states-the-pass-condition-once",
          "Absence of findings is **never by itself a pass.**" in t)
    check("skill-states-silence-is-not-evidence",
          "silence is evidence of nothing" in t)


# ============================================================ 5. union

def test_union_never_averages() -> None:
    """A finding in 1 of 2 carries identical standing to one in 2 of 2."""
    out = union_of([
        {"findings": [{"symbol": "both", "finding": "seen twice"}]},
        {"findings": [{"symbol": "both", "finding": "seen twice"},
                      {"symbol": "once", "finding": "seen once"}]},
    ])
    by = {x["symbol"]: x for x in out["findings"]}
    check("both-findings-survive-the-union", set(by) == {"both", "once"}, str(out))
    check("neither-finding-is-downgraded",
          by["once"].get("severity") == by["both"].get("severity"),
          "a 1-of-2 finding must not be weakened relative to a 2-of-2 one")
    check("provenance-carries-its-interpretation",
          "not weaker evidence" in by["once"]["provenance"],
          "the reader must not be left to discount 1-of-2 on their own")
    # The gate must route them identically too, not merely record them alike.
    g = gate_state({"arms": _arms(B={"findings": [by["once"], by["both"]]})})
    check("gate-routes-both-findings", len(g["decisions"]) == 2, str(g))
    check("gate-is-red-for-either", g["verdict"] == "RED")


def test_union_dedupes_by_symbol() -> None:
    out = union_of([
        {"findings": [{"symbol": "same", "finding": "x"}]},
        {"findings": [{"symbol": "same", "finding": "x restated differently"}]},
    ])
    check("same-gap-found-twice-is-one-item", len(out["findings"]) == 1, str(out))
    check("dedupe-records-both-sightings", out["findings"][0]["seen_in"] == [1, 2])


# ============================================================ 6. arm C

def test_arm_c_partial_return_is_red() -> None:
    partial = gate_state({"arms": _arms(C={"reviewers": {
        "auditor": "returned", "plan-critic": "errored: HTTP 429",
        "lens-experience": "returned"}})})
    check("arm-c-partial-fanout-is-red", partial["verdict"] == "RED")
    check("arm-c-names-the-missing-reviewer",
          any("plan-critic" in b for b in partial["blockers"]), str(partial))
    check("arm-c-explains-why-silence-is-ambiguous",
          any("three clean spawns" in b for b in partial["blockers"]))


def test_arm_c_all_clean_is_green() -> None:
    out = gate_state({"arms": _arms()})
    check("arm-c-all-three-returned-is-green", out["verdict"] == "GREEN", str(out))


def test_arm_c_reuses_review_brief() -> None:
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
    check("review-brief-default-next-step-is-inert",
          "unspecified — my caller did not name one" in t,
          "an unnamed next step must default to nothing, not to a phase: defaulting "
          "to the prototype phase is right at one call site and wrong at the other, "
          "and a silently-half-right default is the harder failure to notice")
    check("review-brief-announces-the-default",
          "Say plainly that you took the default" in t)
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

def test_autoplan_runs_only_where_the_human_gate_moved() -> None:
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        f = tmp / "t.json"
        for path, applies in (("prototype-first", True), ("collapsed", False), ("classic", False)):
            out = depth_of({"path": path})
            check(f"{path}-applies-{applies}", out["applies"] is applies, str(out))
            check(f"{path}-is-a-clean-outcome", out["ok"] is True,
                  "not applying is a correct result, never an error")
        for path in ("collapsed", "classic"):
            out = depth_of({"path": path})
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
            out = depth_of({"path": bogus})
            check(f"unrecognized-path-{bogus!r}-refuses", out["ok"] is False, str(out))
            check(f"unrecognized-path-{bogus!r}-has-no-depth", out["depth"] is None)


def test_decision_required_shape() -> None:
    out = render_of([{
        "finding": "Esc closes the editor but leaves the pin",
        "drafted_resolution": "add a criterion covering Esc twice",
        "provenance": "Found by 1 of 2 coverage passes. That is not weaker evidence — "
                      "this reviewer has never reported a gap that was not real.",
    }]).stdout
    check("escalation-is-numbered", re.search(r"^1\. ", out, re.M) is not None, out)
    check("escalation-drafts-the-resolution", "What I'd do:" in out,
          "the resolution is drafted, not requested")
    check("escalation-asks-a-yes-no", "What I need from you: yes" in out)
    check("escalation-states-provenance-with-its-interpretation",
          "not weaker evidence" in out)
    # No `or True`: the first draft of this check was `X or True`, which can only
    # pass. A check that cannot fail is not a check -- the same class this harness
    # exists to enforce, committed inside the harness itself.
    blank = render_of([])
    check("empty-entries-render-nothing", blank.stdout.strip() == "",
          f"expected no escalation for zero decisions, got {blank.stdout!r}")
    check("empty-entries-still-exit-clean", blank.returncode == 0,
          "nothing to escalate is a normal outcome, not an error")


def test_escalation_header_matches_shipped() -> None:
    """One user-facing contract, one spelling. Detection, not prevention — the
    drift-proof fix is a shared constant, deferred to roadmap D1f."""
    # NOT a bare `if not exists(): return` — that made this whole drift test green if
    # the sibling engine were renamed or moved, which is the satisfiable-by-deletion
    # shape (rules item 3) inside a test written to defend against fan-out (item 2).
    check("sibling-engine-still-exists", MANIFEST_TRIAGE.exists(),
          f"{MANIFEST_TRIAGE} is gone — the header this test pins has no source of truth")
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
    rendered = render_of([{"finding": "x"}]).stdout
    shipped_first_sentence = m.group(1).split(".")[0] + "."
    check("autoplan-header-matches-the-shipped-one",
          shipped_first_sentence in rendered,
          f"expected {shipped_first_sentence!r} in the RENDERED escalation")
    check("autoplan-header-diverges-only-in-the-trailing-clause",
          "Execute starts" in rendered and "closer to ready" not in rendered,
          "no PR exists at this gate, so the shipped trailing promise would be false")


def test_autoplan_derives_from_the_approved_prototype() -> None:
    """The digest is what makes "against a design that survived contact" checkable."""
    t = SKILL.read_text(encoding="utf-8")
    check("skill-derives-criteria-from-the-prototype",
          "Derive the criteria from the approved prototype" in t)
    check("skill-refuses-on-a-digest-mismatch",
          "does not match the prototype the criteria describe, stop" in t,
          "a recorded sha that disagrees with the artifact is a wrong input, not a warning")
    check("skill-does-not-derive-from-the-session",
          "not from the conversation" in t,
          "the session is what the prototype gate exists to stop trusting")


def test_autoplan_output_survives_arm_a() -> None:
    """A plan this skill produced that would fail the gate it then runs is a
    contradiction the gate must surface, not absorb."""
    t = SKILL.read_text(encoding="utf-8")
    check("skill-runs-arm-a-over-its-own-output", "--expect-line" in t and "arm-a" in t)
    # Run it for real: the shape the skill tells the model to write must pass Arm A.
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        p2 = tmp / "plan.md"
        p2.write_text(
            "# Plan\n\n**Pre-execution gate:** prototype\n"
            "**Prototype approved:** `abc1234` · 2026-09-29\n\n"
            "**Spec-walk:**\n\n- [ ] `depth` resolves to 2 on prototype-first. \u2192 `test_depth`\n",
            encoding="utf-8")
        out, _ = run("arm-a", "--plan", str(p2), cwd=str(tmp))
        check("the-shape-the-skill-prescribes-passes-arm-a",
              out["verdict"] == "GREEN", str(out))


def test_no_path_is_interpolated_into_shell() -> None:
    """#165/FB-0116: substitution precedes parsing, so a placeholder in a shell block
    is code. Delegated to the shipped predicate rather than re-implemented here."""
    sys.path.insert(0, str(ROOT / "lib"))
    import arg_placeholders as AP
    for skill in ("autoplan", "review-brief", "audit-coverage", "prototype"):
        f = ROOT / "skills" / skill / "SKILL.md"
        if not f.exists():
            continue
        bad = AP.unsafe(f.read_text(encoding="utf-8"))
        check(f"{skill}-interpolates-no-placeholder-into-shell", not bad,
              f"executable-context placeholders: {bad}")
    t = SKILL.read_text(encoding="utf-8")
    check("autoplan-declares-its-argument-in-prose", "## Argument" in t)
    check("autoplan-uses-the-write-then-path-tier",
          "--arg-path autoplan" in t and "`Write` the path" in t,
          "the positive half: the lint above is satisfiable by removing the argument")


def test_arm_b_input_is_stated() -> None:
    """Arm B reads the prototype's SOURCE; Arm C's three read the plan. The
    one-extraction guarantee is Arm C's and is not claimed for Arm B."""
    t = SKILL.read_text(encoding="utf-8")
    check("skill-states-arm-b-reads-the-prototype-source",
          "Arm B reads the *prototype's source*" in t)
    check("skill-scopes-the-one-extraction-guarantee-to-arm-c",
          "is Arm C's, and is **not** claimed for Arm B" in t)


def test_workflow_states_the_gate_contract() -> None:
    t = WORKFLOW.read_text(encoding="utf-8")
    check("workflow-names-autoplan", "/flow:autoplan" in t)
    check("workflow-states-green-requires-running",
          "GREEN only when every arm RAN" in t,
          "the loop doc must carry the rule, not just the skill")
    # Was `"machine-reviewed" not in t or "MACHINE" in t` — a disjunct satisfied by
    # either half, so it could not distinguish the two states it named. Replaced with
    # the thing actually worth asserting: the loop doc names the arms, not just the fact
    # that something reviews.
    check("workflow-names-the-three-arms",
          all(a in t for a in ("quality", "completeness", "conformance")),
          "the loop doc must say WHAT reviews the plan, not merely that a machine does")


def test_arm_a_red_composes_into_the_gate() -> None:
    """`arm-a`'s own output, fed to `gate`, must stay RED.

    The two subcommands of this one engine had NO test that composed them, and that
    gap hid the worst defect in the first draft: `arm-a` emits
    {arm, ran: true, verdict: "RED", reasons: [...]} with no `findings`, while
    `combine` read only `findings`. So the DETERMINISTIC arm — the only one whose
    result the gate can trust without a model in the loop — reported RED and the gate
    returned GREEN with "every arm ran, was evidenced, and returned nothing".

    This drives the real `arm-a` rather than a hand-written fixture, so the two
    contracts cannot drift apart again without turning this red.
    """
    with _scratch() as tmp:
        plan = tmp / "plan.md"
        plan.write_text(plan_doc(["it works"]), encoding="utf-8")  # vacuous AND unpinned
        a, _ = run("arm-a", "--plan", str(plan), cwd=str(tmp))
        check("known-positive: arm-a itself is RED", a["verdict"] == "RED", str(a))
        check("known-positive: arm-a emits no findings key",
              not a.get("findings"),
              "if arm-a grew a findings list this test no longer covers the gap it was written for")
        arm = dict(a)
        arm["evidence"] = "ran"          # what the SKILL tells the model to supply
        out = gate_state({"arms": [arm,
                                   {"arm": "B", "ran": True, "evidence": "ran"},
                                   {"arm": "C", "ran": True, "evidence": "ran",
                                    "reviewers": {"auditor": "returned",
                                                  "plan-critic": "returned",
                                                  "lens-experience": "returned"}}]})
        check("arm-a-RED-makes-the-gate-RED", out["verdict"] == "RED", str(out))
        check("gate-surfaces-arm-a's-own-reason",
              any("verdict RED" in b for b in out["blockers"]), str(out))
        # The positive half, same composition: a GREEN arm-a must not block.
        plan.write_text(plan_doc(["`depth` resolves to 2 on prototype-first. \u2192 `test_depth`"]),
                        encoding="utf-8")
        g, _ = run("arm-a", "--plan", str(plan), cwd=str(tmp))
        check("known-positive: arm-a is GREEN on a good plan", g["verdict"] == "GREEN", str(g))
        gg = dict(g); gg["evidence"] = "ran"
        out2 = gate_state({"arms": [gg,
                                    {"arm": "B", "ran": True, "evidence": "ran"},
                                    {"arm": "C", "ran": True, "evidence": "ran",
                                     "reviewers": {"auditor": "returned",
                                                   "plan-critic": "returned",
                                                   "lens-experience": "returned"}}]})
        check("arm-a-GREEN-composes-to-GREEN", out2["verdict"] == "GREEN", str(out2))


def test_arm_c_absent_roster_is_red() -> None:
    """An ABSENT reviewer roster is not an implicit pass.

    `if reviewers:` made "no record of the fan-out" indistinguishable from "all three
    returned" — the ambiguity this engine exists to forbid, and the likeliest way a
    dead spawn disappears, since a model writes this file and an omitted key is the
    cheapest possible omission.
    """
    out = gate_state({"arms": [{"arm": "A", "ran": True, "evidence": "x"},
                               {"arm": "B", "ran": True, "evidence": "x"},
                               {"arm": "C", "ran": True, "evidence": "x"}]})
    check("arm-c-with-no-roster-is-red", out["verdict"] == "RED", str(out))
    check("arm-c-absent-roster-says-why",
          any("no reviewer roster" in b for b in out["blockers"]), str(out))
    check("arm-c-with-a-full-roster-is-green", gate_state({"arms": _arms()})["verdict"] == "GREEN")


def test_blockers_are_rendered_for_a_human() -> None:
    """A RED caused only by blockers must not render an empty escalation.

    This is the MOST LIKELY red in practice — a 429, a tool failure, a missing
    reviewer — and it produced `escalation: ""`, so the output template printed
    "blocked on 0 decision(s) below" followed by nothing.
    """
    out = gate_state({"arms": _arms(B={"ran": False})})
    check("blockers-only-is-red", out["verdict"] == "RED")
    check("blockers-only-still-renders-text", out["escalation"].strip() != "",
          "the most likely RED must not be the one with no human-facing output")
    check("blockers-section-says-there-is-nothing-to-answer",
          "nothing to answer here" in out["escalation"], out["escalation"])
    check("blocker-names-an-action", "→" in out["escalation"],
          "a blocker must say what would clear it, not only what went wrong")
    # Header must not promise "nothing else is blocked" while blockers are listed.
    both = gate_state({"arms": _arms(B={"ran": False}),
                       "confidence_verdicts": [{"assumption": "x", "confidence": "LOW"}]})
    check("header-does-not-overpromise-when-blockers-exist",
          "Nothing else is blocked" not in both["escalation"]
          and "must clear too" in both["escalation"], both["escalation"])
    # ...and it must still make the plain promise when they genuinely do not.
    clean = gate_state({"arms": _arms(),
                        "confidence_verdicts": [{"assumption": "x", "confidence": "LOW"}]})
    check("header-does-promise-when-nothing-else-is-blocked",
          "Nothing else is blocked" in clean["escalation"], clean["escalation"])


def test_escalation_is_readable() -> None:
    """Typesetting the engine claims: 76 columns, derived indents, no broken symbols."""
    long_finding = ("the annotation dock never takes keyboard focus when the panel "
                    "opens, so a keyboard user lands on the document body instead")
    out = render_of([{"finding": long_finding,
                      "drafted_resolution": "add a criterion covering focus on open",
                      # Realistic prose, not an unbreakable 200-char token: with
                      # break_long_words=False a single huge token MUST overflow, and
                      # that is the deliberate trade (never split an identifier). The
                      # first draft of this check asserted the impossible and failed.
                      "provenance": "Found by 1 of 2 coverage passes. That is not "
                                    "weaker evidence, and the reason is worth stating "
                                    "in full so the reader is not left to discount a "
                                    "single sighting on their own judgement."}]).stdout
    widest = max(len(l) for l in out.splitlines())
    check("escalation-wraps-at-76", widest <= 76, f"widest line was {widest} cols")
    check("the-numbered-line-is-wrapped-too",
          not any(l.startswith("1. ") and len(l) > 76 for l in out.splitlines()),
          "the headline is the line a reader scans first and was the only unwrapped one")
    # Item 10's marker is 4 chars; a hardcoded 3-space indent stops aligning there.
    ten = render_of([{"finding": "f%d needs enough text that it wraps onto a second line here" % i,
                      "drafted_resolution": "do it"} for i in range(1, 11)]).stdout
    lines = ten.splitlines()
    i10 = next(n for n, l in enumerate(lines) if l.startswith("10. "))
    check("item-10-sub-fields-align-under-the-text",
          lines[i10 + 2].startswith("    What"), repr(lines[i10 + 2][:20]))
    # Identifiers must not be split mid-token.
    sym = render_of([{"finding": "`manifest-triage.py::render_decisions` disagrees with "
                                 "the autoplan renderer about the sub-field idiom used"}]).stdout
    check("identifiers-are-not-broken-across-lines",
          "manifest-\n" not in sym and "render_\n" not in sym, sym)


def test_low_verdict_without_a_draft_asks_an_open_question() -> None:
    """Yes/no is the wrong shape when there is nothing drafted to say yes to.

    The LOW path is generated by the engine itself from a confidence verdict, so it
    cannot be assumed to carry a mitigation — and it rendered "What I need from you:
    yes (I apply it...)" referring to nothing.
    """
    out = gate_state({"arms": _arms(),
                      "confidence_verdicts": [{"assumption": "depth 2", "confidence": "LOW"}]})
    esc = out["escalation"]
    check("no-draft-does-not-ask-yes", "from you: yes" not in esc, esc)
    check("no-draft-asks-an-open-question", "no resolution to propose" in esc, esc)
    # With a mitigation present, the yes/no form is correct and must come back.
    out2 = gate_state({"arms": _arms(),
                       "confidence_verdicts": [{"assumption": "depth 2", "confidence": "LOW",
                                                "mitigation": "declare depth as a constant"}]})
    check("a-drafted-resolution-does-ask-yes",
          "from you: yes" in out2["escalation"], out2["escalation"])


def test_escalation_survives_a_non_utf8_stdout() -> None:
    """`render-decisions` is the one subcommand that writes text rather than going
    through `_emit`'s ensure_ascii JSON. Under LC_ALL=C it died with a traceback —
    breaking this file's own contract that a refusal is never a traceback."""
    import os
    with _scratch() as tmp:
        f = tmp / "e.json"
        f.write_text(json.dumps([{"finding": "an em-dash — and an arrow \u2192 here"}]),
                     encoding="utf-8")
        env = dict(os.environ, PYTHONIOENCODING="ascii")
        proc = subprocess.run([sys.executable, str(ENGINE), "render-decisions",
                               "--entries-file", str(f)],
                              capture_output=True, text=True, cwd=str(tmp), env=env)
        check("ascii-stdout-does-not-traceback", proc.returncode == 0, proc.stderr[-200:])
        check("ascii-stdout-still-renders-the-decision",
              "Decisions for you" in proc.stdout, proc.stdout[:120])


def test_path_confinement_refuses_and_accepts() -> None:
    """The CWE-59 guard, exercised against paths that MUST be refused.

    This guard shipped wrong TWICE in this PR and both versions passed every test
    that existed, because every test fed it a legitimate path. `base` was first
    `path.resolve().parent` (containment true by construction) and then
    `_repo_root(path.parent)` (which "confined" /etc/hostname to /etc and accepted
    it). A guard validated only on inputs it should accept cannot be distinguished
    from no guard at all — rules item 4. So: known positives first.
    """
    import os
    with _scratch() as tmp:
        git_repo(tmp, {"ok.json": json.dumps({"arms": []})})
        # NEGATIVE HALF — each of these must be REFUSED.
        outside = Path(os.sep) / "etc" / "hostname"
        out, _ = run("gate", "--state-file", str(outside), cwd=str(tmp))
        check("absolute-path-outside-the-repo-is-refused",
              out["verdict"] == "RED" and any("outside" in r for r in out["reasons"]),
              str(out))
        traversal = tmp / ".." / "escaped.json"
        out, _ = run("gate", "--state-file", str(traversal), cwd=str(tmp))
        check("dot-dot-traversal-is-refused",
              out["verdict"] == "RED" and any("outside" in r for r in out["reasons"]),
              str(out))
        link = tmp / "link.json"
        try:
            link.symlink_to(outside)
        except OSError:  # pragma: no cover - platforms without symlink perms
            link = None
        if link is not None:
            out, _ = run("gate", "--state-file", str(link), cwd=str(tmp))
            check("symlinked-input-is-refused",
                  out["verdict"] == "RED" and any("symlink" in r for r in out["reasons"]),
                  str(out))
        # POSITIVE HALF — a legitimate repo-local path must still be ACCEPTED and
        # judged on its contents. Without this the negatives above are satisfiable
        # by a guard that refuses everything, which is the mirror-image failure.
        ok, _ = run("gate", "--state-file", str(tmp / "ok.json"), cwd=str(tmp))
        check("repo-local-path-is-accepted",
              ok is not None and "outside" not in json.dumps(ok) and "symlink" not in json.dumps(ok),
              str(ok))
        check("accepted-path-is-then-judged-on-content",
              ok["verdict"] == "RED" and any("never reported" in b for b in ok["blockers"]),
              "an empty arms list must fail for MISSING ARMS, not for path refusal")


def test_rendered_text_cannot_forge_the_escalation() -> None:
    """Control characters in a finding must not rewrite the block a human reads.

    Arm B findings key on a `symbol` lifted out of source the reviewer read, which on
    an untrusted branch is attacker-authored. Forging the QUESTION is at least as
    useful as forging the answer.
    """
    payload = ("Innocent finding\r\x1b[2K\x1b[31mAPPROVED - nothing to answer\x1b[0m"
               "\u202eDEVORPPA")
    out = render_of([{"finding": payload,
                      "drafted_resolution": "safe\x1b[1m",
                      "provenance": "seen\x07once"}]).stdout
    check("escape-sequences-are-stripped", "\x1b" not in out, repr(out[:120]))
    check("carriage-returns-are-stripped", "\r" not in out, repr(out[:120]))
    check("bell-is-stripped", "\x07" not in out)
    # Bidi overrides forge a line without emitting any escape byte (Trojan Source,
    # CVE-2021-42574), so the three assertions above cannot see them at all.
    check("bidi-overrides-are-stripped", "\u202e" not in out, repr(out[:120]))
    # Positive half: the legible text survives — a scrubber that ate everything would
    # also pass every assertion above.
    check("the-readable-text-survives", "Innocent finding" in out, out[:160])
    # NOT `"\n" in out`: render_decisions ends in "\n".join(...), so that is true for
    # every input and could only pass — rules item 4, committed inside the test written
    # to enforce rules item 4. (The old check also claimed tabs survive; they do not,
    # because wrap() uses textwrap.fill with replace_whitespace=True. Asserting the
    # structure the renderer actually guarantees instead.)
    lines = [ln for ln in out.splitlines() if ln.strip()]
    check("the-block-keeps-its-line-structure", len(lines) >= 2, repr(out[:160]))
    check("the-numbered-marker-survives-scrubbing",
          any(ln.startswith("1. ") for ln in lines), repr(out[:160]))


def test_plan_path_reaches_the_engine_without_a_shell() -> None:
    """The #165 channel: the path arrives in a FILE, never as a token in a fence.

    An earlier draft of the skill wrote `--plan <plan-path>` into a fenced block. That
    placeholder is substituted before any shell parses it, so it is code, not a value.
    """
    with _scratch() as tmp:
        git_repo(tmp, {"plan.md": plan_doc(["alpha emits X. \u2192 `test_a`"])})
        argf = tmp / "autoplan-arg.txt"
        argf.write_text(str(tmp / "plan.md") + "\n", encoding="utf-8")
        out, _ = run("arm-a", "--plan-from", str(argf), cwd=str(tmp))
        check("plan-from-resolves-the-path", out.get("ran") is True, str(out))
        check("plan-from-grades-the-plan", out.get("criteria_count") == 1, str(out))
        # A path has one line. A second is an injection attempt, not a value to trim.
        argf.write_text(str(tmp / "plan.md") + "\nrm -rf /\n", encoding="utf-8")
        bad, _ = run("arm-a", "--plan-from", str(argf), cwd=str(tmp))
        check("multi-line-arg-file-is-refused",
              bad["verdict"] == "RED" and any("one" in r for r in bad["reasons"]), str(bad))
        argf.write_text("\n", encoding="utf-8")
        empty, _ = run("arm-a", "--plan-from", str(argf), cwd=str(tmp))
        check("empty-arg-file-is-refused",
              empty["verdict"] == "RED" and any("empty" in r for r in empty["reasons"]))
    # The shipped skill must use the safe channel, not the placeholder form.
    t = SKILL.read_text(encoding="utf-8")
    # The literal invocation, not merely the token: `"--plan-from" in t` is satisfied
    # by the explanatory paragraph alone, so deleting the whole sh block would leave
    # this and its sibling green (rules item 3).
    check("skill-uses-plan-from", 'arm-a --plan-from "$ARGF"' in t,
          "assert the shipped invocation, not a word that also appears in prose")
    check("skill-does-not-interpolate-a-plan-path",
          "arm-a --plan <plan-path>" not in t,
          "a placeholder inside a fenced block is executable code (#165/FB-0116)")


def test_lib_root_is_confined() -> None:
    """The tree the engine EXECUTES from is confined like the one it reads.

    Not independently reachable — it needs argv control — but it upgrades any argv
    foothold into arbitrary code execution, so the read-only --plan being guarded
    while this was not had the threat model inverted.
    """
    with _scratch() as tmp:
        git_repo(tmp, {"plan.md": plan_doc(["alpha emits X. \u2192 `test_a`"])})
        out, _ = run("arm-a", "--plan", str(tmp / "plan.md"),
                     "--lib-root", "/tmp/attacker-tree", cwd=str(tmp))
        check("lib-root-outside-the-repo-is-refused",
              out["verdict"] == "RED" and any("outside" in r for r in out["reasons"]),
              str(out))
    # Positive: an in-repo lib-root still loads, so the refusal is about LOCATION and
    # not about the flag being wired off. Run wholly inside the flow repo.
    repo = ROOT.parent.parent
    ok, _ = run("arm-a", "--plan", "dev-docs/plan.md",
                "--lib-root", "plugins/flow/skills", cwd=str(repo))
    check("real-lib-root-still-loads", ok.get("ran") is True, str(ok))


def test_a_flag_shaped_value_is_refused() -> None:
    """`_arg` takes the token after a flag, so a word-split argument could bind
    `--lib-root` silently — pointing the engine's exec at an attacker's tree."""
    out, _ = run("arm-a", "--plan", "--lib-root")
    check("flag-shaped-value-is-refused",
          out["verdict"] == "RED" and any("looks like another flag" in r for r in out["reasons"]),
          str(out))
    # Positive half, for bar-consistency with its neighbours: an ordinary value still
    # binds, so the refusal is about the value's SHAPE and not about --plan being off.
    ok, _ = run("arm-a", "--plan", "dev-docs/plan.md", cwd=str(ROOT.parent.parent))
    check("an-ordinary-value-still-binds", ok.get("ran") is True, str(ok))
    # A flag given with nothing after it names ITSELF, not some other flag.
    empty, _ = run("arm-a", "--plan-from")
    check("a-valueless-flag-names-itself",
          any("--plan-from was given with no value" in r for r in empty["reasons"]), str(empty))
    # Both channels at once is an ambiguity, not a convenience.
    both, _ = run("arm-a", "--plan", "dev-docs/plan.md", "--plan-from", "x.txt",
                  cwd=str(ROOT.parent.parent))
    check("both-plan-channels-is-refused",
          any("both given" in r for r in both["reasons"]), str(both))


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
