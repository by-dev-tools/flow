#!/usr/bin/env python3
"""Eval harness for the Step 8 ship-readiness predicate + CI gate (FB-0131, FB-0137).

Pins `skills/ship/lib/ship-readiness.py` and the three `ci-*` manifest kinds that
carry its verdict to the human.

EVERY CI STATE IS PINNED AS A PAIR, and that is the organising principle rather
than a stylistic preference. The defect this release fixes reads "nothing has
failed yet" as "everything passed", and a one-armed assertion cannot tell a
working checker from that bug: both predict "not FAIL" on a pending fixture. So
`ci-pending` is pinned against `ci-passing` on fixtures differing in exactly ONE
field, `ci-unknown` is pinned against a successful read, and the no-checks case
is pinned in both of its two worlds.

THE KNOWN-POSITIVE (`.claude/rules/general.md` item 4). `test_pr176_regression`
replays the measured state flow actually shipped green -- six checks, five
passing, `evals` red, GitHub reporting BLOCKED -- so this harness has
demonstrated it can return NOT-READY before any of its READY results are
trusted. A suite that has only ever returned "ready" has produced no evidence.

Stdlib only. Run:
    python3 plugins/flow/evals/run_ship_readiness_evals.py
"""

from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).parent
PLUGIN = HERE.parent
ENGINE = PLUGIN / "skills" / "ship" / "lib" / "ship-readiness.py"
TRIAGE = PLUGIN / "skills" / "ship" / "lib" / "manifest-triage.py"
SHIP_SKILL = PLUGIN / "skills" / "ship" / "SKILL.md"
SPIKE_SKILL = PLUGIN / "skills" / "ship-spike" / "SKILL.md"
FIX = HERE / "fixtures" / "ship-readiness"

fails = 0
ran = 0


def check(name: str, ok: bool, detail: str = "") -> None:
    global fails, ran
    ran += 1
    if ok:
        print(f"  PASS  {name}")
    else:
        fails += 1
        print(f"  FAIL  {name}{(': ' + detail) if detail else ''}")


def _load(path: Path, mod: str):
    spec = importlib.util.spec_from_file_location(mod, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _engine():
    return _load(ENGINE, "ship_readiness")


def ci_cli(*args: str) -> dict:
    """Drive the engine through its CLI, not its functions.

    Deliberate: the shipped skill calls the CLI, so an in-process-only harness
    would pin a surface nothing invokes. `.claude/rules/general.md` item 4's
    third corollary -- pin the claim at the layer where it is CLAIMED.
    """
    out = subprocess.run(
        [sys.executable, str(ENGINE), "ci", *args],
        capture_output=True, text=True,
    )
    assert out.returncode == 0, f"engine exited {out.returncode}: {out.stderr}"
    return json.loads(out.stdout)


def ci_fixture(name: str) -> dict:
    return ci_cli("--blob", str(FIX / name))


# =========================================================================
# 1. The three CI states, each paired.
# =========================================================================
print("\n[ci states — each pinned as a pair]")

passing = ci_fixture("ci-passing.json")
check("test_ci_passing", passing["state"] == "passing" and passing["verdict"] == "PASS",
      json.dumps(passing))
check("test_ci_passing_names_no_kind", passing["kind"] is None, str(passing["kind"]))

failing = ci_fixture("ci-failing-pr176.json")
check("test_ci_failing_names_the_check",
      failing["verdict"] == "FAIL"
      and failing["kind"] == "ci-failing"
      and [f["name"] for f in failing["failing"]] == ["evals"]
      and "evals" in failing["reason"],
      json.dumps(failing))

# THE PAIR. These two fixtures differ in exactly one field (`evals`.status), and
# they must land on OPPOSITE verdicts. One arm alone proves nothing: a checker
# that reads "no failures" as "passed" also passes a pending-only assertion that
# merely asserts "not FAIL".
pending = ci_fixture("ci-pending.json")
check("test_pending_is_not_passing",
      pending["verdict"] == "UNDECLARED"
      and pending["state"] == "pending"
      and pending["kind"] == "ci-pending"
      and passing["verdict"] == "PASS",
      f"pending={pending['verdict']} passing={passing['verdict']}")
check("test_pending_is_not_called_failing", pending["failing"] == [], json.dumps(pending["failing"]))
check("test_pending_reason_says_pending",
      "pending" in pending["reason"].lower() and "not passing" in pending["reason"].lower(),
      pending["reason"])

# The one-field-apart property is itself asserted, so a future edit that makes the
# two fixtures differ in more than the check's status cannot quietly weaken the pair.
_p = json.loads((FIX / "ci-passing.json").read_text())
_q = json.loads((FIX / "ci-pending.json").read_text())


def _diff_fields(a, b, path="") -> list[str]:
    if isinstance(a, dict) and isinstance(b, dict):
        out = []
        for k in set(a) | set(b):
            out += _diff_fields(a.get(k), b.get(k), f"{path}.{k}")
        return out
    if isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        out = []
        for i, (x, y) in enumerate(zip(a, b)):
            out += _diff_fields(x, y, f"{path}[{i}]")
        return out
    return [] if a == b else [path]


_d = sorted(_diff_fields(_p, _q))
check("test_pending_pair_differs_only_in_check_state",
      all(f.endswith((".status", ".conclusion", ".completedAt")) for f in _d) and _d,
      f"differing fields: {_d}")

# =========================================================================
# 2. "Could not see" is never "nothing there" (FB-0121) — also paired.
# =========================================================================
print("\n[unknown — paired with a successful read]")

gh_absent = ci_cli("--gh-failed")
check("test_unknown_requires_both_arms",
      gh_absent["verdict"] == "UNDECLARED"
      and gh_absent["kind"] == "ci-unknown"
      and passing["verdict"] == "PASS",
      f"absent={gh_absent['verdict']} present={passing['verdict']}")
check("test_gh_absent_reason_is_not_a_pass",
      "unknown" in gh_absent["reason"].lower() and "not evidence" in gh_absent["reason"].lower(),
      gh_absent["reason"])

# The degrade contract, pinned because a Spec-walk box claimed it: gh absent must yield a
# verdict (never a crash, never a halt) AND the skills must warn loudly rather than
# proceeding quietly. Paired: the warn text must exist in the prose, and the engine must
# still exit 0 so the pipeline reaches the PR step instead of dying.
_absent = subprocess.run([sys.executable, str(ENGINE), "ci", "--gh-failed"],
                         capture_output=True, text=True)
check("test_absent_gh_degrades_not_halts",
      _absent.returncode == 0
      and json.loads(_absent.stdout)["kind"] == "ci-unknown"
      and "gh is not installed" in SHIP_SKILL.read_text()
      and "NOT a passing CI" in SHIP_SKILL.read_text(),
      f"rc={_absent.returncode}")

empty = subprocess.run([sys.executable, str(ENGINE), "ci"], input="",
                       capture_output=True, text=True)
check("test_empty_stdin_is_unknown_not_clean",
      empty.returncode == 0 and json.loads(empty.stdout)["kind"] == "ci-unknown",
      empty.stdout[:160])

garbage = subprocess.run([sys.executable, str(ENGINE), "ci"], input="not json at all",
                         capture_output=True, text=True)
check("test_unparseable_output_is_unknown_not_clean",
      garbage.returncode == 0 and json.loads(garbage.stdout)["kind"] == "ci-unknown",
      garbage.stdout[:160])

# A vocabulary GitHub adds tomorrow must arrive as "I could not classify this".
for fx in ("ci-unmapped-conclusion.json", "ci-unknown-node-type.json"):
    r = ci_fixture(fx)
    check(f"test_unmapped_state_is_unknown[{fx}]",
          r["verdict"] == "UNDECLARED" and r["kind"] == "ci-unknown" and r["unmapped"],
          json.dumps(r))

# =========================================================================
# 3. The no-checks case is TWO different worlds (#183, measured).
# =========================================================================
print("\n[no checks reported — both arms]")

# `--settled` because that is what the shipped shell does on this branch: it looks once,
# sees `no-checks-unsettled`, waits for checks to register, and looks again. The
# unsettled-vs-settled pair is pinned separately above; this arm is about the SECOND look
# genuinely distinguishing "no CI configured" from a blocked PR.
clean = ci_cli("--blob", str(FIX / "ci-no-checks-clean.json"), "--settled")
check("test_no_checks_is_two_different_worlds[clean]",
      clean["verdict"] == "PASS" and clean["state"] == "no-checks-clean"
      and "no checks are configured" in clean["reason"],
      json.dumps(clean))
# The dirty arm takes --settled too, so the ONLY difference between the two arms is the
# merge state. Without that, this pair would be confounded by the settle flag and would
# "disagree" for the wrong reason — a green test measuring something else.
dirty = ci_cli("--blob", str(FIX / "ci-no-checks-dirty.json"), "--settled")
check("test_no_checks_is_two_different_worlds[dirty]",
      dirty["verdict"] == "UNDECLARED" and dirty["kind"] == "ci-unknown"
      and "DIRTY" in dirty["reason"],
      json.dumps(dirty))
check("test_no_checks_arms_disagree", clean["verdict"] != dirty["verdict"],
      "both arms returned the same verdict — the disambiguation is not happening")

# An empty rollup with a CLEAN merge state is the ONE branch where PASS would come from an
# absence, and ship 7a.7 runs in exactly the window where a brand-new PR looks like that.
# Found by review and reproduced before fixing; pinned as a pair, because the whole point
# is that the two reads of the SAME blob must disagree.
_unsettled = ci_fixture("ci-no-checks-clean.json")
_settled = ci_cli("--blob", str(FIX / "ci-no-checks-clean.json"), "--settled")
check("test_empty_rollup_is_not_a_pass_until_settled",
      _unsettled["verdict"] == "UNDECLARED"
      and _unsettled["state"] == "no-checks-unsettled"
      and _unsettled["kind"] == "ci-unknown"
      and _settled["verdict"] == "PASS",
      f"unsettled={_unsettled['verdict']} settled={_settled['verdict']}")
check("test_settle_flag_changes_only_the_empty_clean_branch",
      ci_cli("--blob", str(FIX / "ci-failing-pr176.json"), "--settled")["verdict"] == "FAIL"
      and ci_cli("--blob", str(FIX / "ci-pending.json"), "--settled")["kind"] == "ci-pending"
      and ci_cli("--blob", str(FIX / "ci-passing.json"), "--settled")["verdict"] == "PASS",
      "--settled altered a verdict outside the empty-rollup branch")
# And the shell must actually perform the second look — a flag no caller passes is a gate
# that never closes (the FB-0074 unwired-composition shape).
for _label, _src in (("ship", SHIP_SKILL.read_text()), ("ship-spike", SPIKE_SKILL.read_text())):
    check(f"test_skill_performs_the_settle_reread[{_label}]",
          "no-checks-unsettled" in _src and "--settled" in _src,
          "the skill never re-reads with --settled, so the empty-rollup pass is unreachable")

# =========================================================================
# 4. mergeStateStatus is a cross-check, never the sole source.
# =========================================================================
print("\n[mergeStateStatus cross-check]")

blocked = ci_fixture("ci-passing-but-blocked.json")
check("test_passing_checks_but_github_blocks",
      blocked["verdict"] == "UNDECLARED" and blocked["kind"] == "ci-unknown"
      and "BLOCKED" in blocked["reason"],
      json.dumps(blocked))
# DRAFT must NOT be read as blocking: flow drafts PRs, so DRAFT is the expected
# state for exactly the PRs this engine is asked about. Reading it as a block
# would wedge every re-ship of a drafted PR.
draft = ci_fixture("ci-passing-draft.json")
check("test_draft_merge_state_is_not_a_block",
      draft["verdict"] == "PASS" and draft["state"] == "passing",
      json.dumps(draft))

# =========================================================================
# 5. Non-Actions CI (StatusContext) is mapped, not invisible.
# =========================================================================
print("\n[StatusContext — non-Actions CI]")

sc_fail = ci_fixture("ci-status-context-failing.json")
check("test_status_context_failing_is_mapped",
      sc_fail["verdict"] == "FAIL" and "ci/circleci: test" in sc_fail["reason"],
      json.dumps(sc_fail))
sc_pend = ci_fixture("ci-status-context-pending.json")
check("test_status_context_pending_is_mapped",
      sc_pend["verdict"] == "UNDECLARED" and sc_pend["kind"] == "ci-pending",
      json.dumps(sc_pend))
# THE PASSING ARM. Without it, the only StatusContext assertions were "does not pass" —
# and a mapper whose `_PASSING_STATES` was simply wrong would satisfy both of them. That
# is general.md item 4 (a detector validated only where it should stay quiet), and it
# lands hardest here, on the one family whose field names are transcribed from GitHub's
# documented schema rather than measured.
sc_pass = ci_fixture("ci-status-context-passing.json")
check("test_status_context_passing_is_mapped",
      sc_pass["verdict"] == "PASS" and sc_pass["state"] == "passing",
      json.dumps(sc_pass))
_sd = sorted(_diff_fields(
    json.loads((FIX / "ci-status-context-passing.json").read_text()),
    json.loads((FIX / "ci-status-context-pending.json").read_text())))
check("test_status_context_pair_differs_only_in_state",
      _sd and all(f.endswith(".state") for f in _sd), f"differing fields: {_sd}")

# =========================================================================
# 6. The timeout reports pending, and is never upgraded to a pass.
# =========================================================================
print("\n[timeout]")

t_out = ci_cli("--timed-out", "600")
check("test_timeout_reports_pending",
      t_out["verdict"] == "UNDECLARED" and t_out["kind"] == "ci-pending",
      json.dumps(t_out))
check("test_timeout_matches_observed_pending_verdict",
      (t_out["verdict"], t_out["kind"]) == (pending["verdict"], pending["kind"]),
      f"{t_out['kind']} vs {pending['kind']}")
check("test_timeout_names_the_budget",
      "600" in t_out["reason"] and "ciWaitSeconds" in t_out["reason"], t_out["reason"])

# =========================================================================
# 7. THE KNOWN-POSITIVE: #176's measured shape (general.md item 4).
# =========================================================================
print("\n[#176 regression — the known-positive that validates this harness]")

eng = _engine()
with tempfile.TemporaryDirectory() as d:
    d = Path(d)
    # Every ARTIFACT-side condition is deliberately green, exactly as it was on
    # #176: the plan fully checked, verify-build PASS, no open questions. The
    # ONLY red signal is CI. If the checker reports ready here, it has reproduced
    # the shipped defect.
    plan = d / "plan.md"
    plan.write_text(
        "# Plan\n\n### Spec-walk\n\n"
        "- [x] **A thing.** *Verify:* an eval. *Pinned by:* `run_x_evals.py::test_a`.\n"
        "- [x] **Another thing.** *Verify:* a grep. *Pinned by:* `run_x_evals.py::test_b`.\n\n"
        "**Confidence: HIGH.**\n"
    )
    findings = d / "verify-findings.json"
    findings.write_text(json.dumps({"overall_verdict": "PASS", "open_questions": []}))
    blockers = d / "blockers.json"
    blockers.write_text(json.dumps({"open_blockers": []}))

    out = subprocess.run(
        [sys.executable, str(ENGINE), "check", "--plan", str(plan), "--findings", str(findings),
         "--blockers-file", str(blockers), "--ci-blob", str(FIX / "ci-failing-pr176.json")],
        capture_output=True, text=True,
    )
    res = json.loads(out.stdout)
    check("test_pr176_regression",
          res["ready"] is False and res["failed"] == ["ci"],
          json.dumps({"ready": res["ready"], "failed": res["failed"], "undeclared": res["undeclared"]}))
    check("test_pr176_regression_names_evals",
          any("evals" in c["reason"] for c in res["conditions"] if c["id"] == "ci"),
          json.dumps([c for c in res["conditions"] if c["id"] == "ci"]))
    # The paired positive: the SAME artifacts with a green CI blob must be ready.
    # Without this arm, a checker hardwired to NOT-READY would pass the test above.
    out2 = subprocess.run(
        [sys.executable, str(ENGINE), "check", "--plan", str(plan), "--findings", str(findings),
         "--blockers-file", str(blockers), "--ci-blob", str(FIX / "ci-passing.json")],
        capture_output=True, text=True,
    )
    res2 = json.loads(out2.stdout)
    check("test_pr176_pair_green_ci_is_ready",
          res2["ready"] is True and not res2["failed"] and not res2["undeclared"],
          json.dumps({"ready": res2["ready"], "failed": res2["failed"],
                      "undeclared": res2["undeclared"]}))

    # =====================================================================
    # 8. UNDECLARED never passes, and says something different from a failure.
    # =====================================================================
    print("\n[UNDECLARED is not a pass]")

    out3 = subprocess.run(
        [sys.executable, str(ENGINE), "check", "--plan", str(plan),
         "--findings", str(d / "absent.json"), "--blockers-file", str(blockers),
         "--ci-blob", str(FIX / "ci-passing.json")],
        capture_output=True, text=True,
    )
    res3 = json.loads(out3.stdout)
    vb = [c for c in res3["conditions"] if c["id"] == "verify-build"][0]
    check("test_undeclared_is_not_a_pass",
          res3["ready"] is False and "verify-build" in res3["undeclared"]
          and vb["verdict"] == "UNDECLARED",
          json.dumps(res3["undeclared"]))
    # The wording matters: a reader told "the build failed" debugs code that never
    # ran. FB-0121's distinction has to survive into the prose, not just the enum.
    check("test_missing_buffer_is_not_worded_as_a_failure",
          "NOT a failing build" in vb["reason"] and "nothing was exercised" in vb["reason"],
          vb["reason"])

    # Condition 2 is UNDECLARED BY CONSTRUCTION with no artifact, and it must name
    # the gap rather than shrug. This is R1's predicted finding, pinned so a future
    # edit cannot silently turn it into a pass.
    out4 = subprocess.run(
        [sys.executable, str(ENGINE), "check", "--plan", str(plan), "--findings", str(findings),
         "--ci-blob", str(FIX / "ci-passing.json")],
        capture_output=True, text=True,
    )
    res4 = json.loads(out4.stdout)
    nb = [c for c in res4["conditions"] if c["id"] == "no-blocker"][0]
    check("test_no_blocker_is_undeclared_by_construction",
          nb["verdict"] == "UNDECLARED" and res4["ready"] is False
          and "rigor-marker" in nb["reason"] and "not assumed clean" in nb["reason"],
          nb["reason"])

    # An unchecked Spec-walk box is a FAIL (a declared criterion nobody satisfied),
    # distinct from UNDECLARED (no criteria to read at all).
    plan2 = d / "plan2.md"
    plan2.write_text(
        "# Plan\n\n### Spec-walk\n\n"
        "- [x] **Done.** *Verify:* an eval. *Pinned by:* `run_x_evals.py::test_a`.\n"
        "- [ ] **Not done.** *Verify:* an eval. *Pinned by:* `run_x_evals.py::test_b`.\n"
    )
    out5 = subprocess.run(
        [sys.executable, str(ENGINE), "check", "--plan", str(plan2), "--findings", str(findings),
         "--blockers-file", str(blockers), "--ci-blob", str(FIX / "ci-passing.json")],
        capture_output=True, text=True,
    )
    res5 = json.loads(out5.stdout)
    sw = [c for c in res5["conditions"] if c["id"] == "spec-walk"][0]
    check("test_unchecked_criterion_fails_not_undeclared",
          sw["verdict"] == "FAIL" and "Not done" in sw["reason"],
          json.dumps(sw))

    # =====================================================================
    # 9. The verdict names which condition failed, and only that one.
    # =====================================================================
    print("\n[the verdict names the failing condition]")

    check("test_verdict_names_the_failing_condition",
          res["failed"] == ["ci"]
          and sorted(c["id"] for c in res["conditions"]) == sorted(eng.CONDITION_ORDER)
          and all(c["verdict"] == "PASS" for c in res["conditions"] if c["id"] != "ci"),
          json.dumps([(c["id"], c["verdict"]) for c in res["conditions"]]))
    check("test_all_six_conditions_are_always_reported",
          len(res["conditions"]) == 6 and len(eng.CONDITION_ORDER) == 6,
          str([c["id"] for c in res["conditions"]]))

    rendered = subprocess.run(
        [sys.executable, str(ENGINE), "check", "--plan", str(plan), "--findings", str(findings),
         "--blockers-file", str(blockers), "--ci-blob", str(FIX / "ci-failing-pr176.json"),
         "--render"], capture_output=True, text=True).stdout
    check("test_render_states_not_ready_and_the_reason",
          "NOT READY" in rendered and "evals" in rendered, rendered[:200])

# A no-PR run must be UNDECLARED on ci, not PASS: flow's CI fires on
# pull_request, so "no checks exist yet" is the normal pre-PR state.
no_pr = subprocess.run([sys.executable, str(ENGINE), "check"], capture_output=True, text=True)
res6 = json.loads(no_pr.stdout)
check("test_no_pr_yet_is_undeclared_not_ready",
      res6["ready"] is False and "ci" in res6["undeclared"],
      json.dumps(res6["undeclared"]))

# =========================================================================
# 10. combine()'s rule: every arm must PASS, not merely "not FAIL".
# =========================================================================
print("\n[combine — a missing arm is not a pass]")

check("test_combine_requires_every_arm_to_have_run",
      eng.combine([{"id": "spec-walk", "verdict": "PASS", "reason": "x"}])["ready"] is False,
      "a single-condition input was called ready")
check("test_combine_all_pass_is_ready",
      eng.combine([{"id": c, "verdict": "PASS", "reason": "x"} for c in eng.CONDITION_ORDER])["ready"]
      is True,
      "an all-PASS input was not called ready")
check("test_combine_undeclared_blocks",
      eng.combine(
          [{"id": c, "verdict": "PASS" if c != "ci" else "UNDECLARED", "reason": "x"}
           for c in eng.CONDITION_ORDER])["ready"] is False,
      "an UNDECLARED arm did not block")

# =========================================================================
# 11. The three manifest kinds, and the CHECK_ONLY property.
# =========================================================================
print("\n[manifest kinds]")

mt = _load(TRIAGE, "manifest_triage")
CI_KINDS = ("ci-failing", "ci-pending", "ci-unknown")
for k in CI_KINDS:
    check(f"test_three_ci_kinds_are_check_only[{k}]",
          k in mt.KIND_COPY and k in mt.CHECK_ONLY, f"{k} missing from KIND_COPY or CHECK_ONLY")
    # CHECK_ONLY kinds are never offered "waive and ship as-is", so a waive_cost
    # would be dead copy that a renderer could still reach.
    check(f"test_ci_kind_offers_no_waive[{k}]",
          "waive_cost" not in mt.KIND_COPY.get(k, {}), "carries a waive_cost")

# The per-kind CHECK_ONLY option, paired: the three CI kinds must each carry their own,
# and `verify-build` must still fall through to the shared default. Without the second
# half, deleting the default would pass.
for k in CI_KINDS:
    check(f"test_ci_kind_has_its_own_check_only_option[{k}]",
          "check_only_option" in mt.KIND_COPY[k]
          and "failing build" not in mt.KIND_COPY[k]["check_only_option"],
          "missing, or still says 'failing build' for a non-failing state")
check("test_verify_build_keeps_the_default_check_only_option",
      "check_only_option" not in mt.KIND_COPY["verify-build"],
      "verify-build grew its own option; the shared default is now unreachable for it")

# Non-generic copy, PAIRED with the positive that the records exist at all. A
# "copy is not generic" assertion alone passes if the kind is deleted.
generic = {mt.KIND_COPY[k]["means"] for k in CI_KINDS}
check("test_ci_kinds_have_distinct_means_copy", len(generic) == 3, str(sorted(generic)))
check("test_ci_kinds_mention_their_own_state",
      "failing" in mt.KIND_COPY["ci-failing"]["means"].lower()
      and "not finish" in mt.KIND_COPY["ci-pending"]["means"].lower()
      and "could not confirm" in mt.KIND_COPY["ci-unknown"]["means"].lower(),
      "a kind's plain-language copy does not describe its own state")

# The engine's `kind` field must only ever emit kinds the manifest actually knows.
# This is the join that would otherwise be spelled in two files with nothing
# checking it (general.md item 2).
emitted = set()
for fx in sorted(FIX.glob("ci-*.json")):
    k = ci_fixture(fx.name)["kind"]
    if k:
        emitted.add(k)
check("test_every_emitted_kind_is_a_known_manifest_kind",
      emitted and emitted <= set(mt.KINDS), f"emitted={sorted(emitted)}")
check("test_engine_can_emit_all_three_kinds", emitted == set(CI_KINDS), f"emitted={sorted(emitted)}")

# =========================================================================
# 12. The skill contract: blocking wait, paired positive + negative.
# =========================================================================
print("\n[skill contract]")

ship_src = SHIP_SKILL.read_text()
spike_src = SPIKE_SKILL.read_text()

for label, src in (("ship", ship_src), ("ship-spike", spike_src)):
    # POSITIVE first. A negative-only assertion ("contains no poll loop") passes
    # if the whole wait is deleted -- general.md item 3's prohibition-satisfiable-
    # by-deletion shape, which this repo has shipped twice.
    check(f"test_wait_is_blocking_not_polled[{label}:positive]",
          "--watch" in src and re.search(r"timeout\s+\"\$CI_WAIT\"\s+gh pr checks", src) is not None,
          "no `timeout \"$CI_WAIT\" gh pr checks … --watch` found")
    # NEGATIVE: no sleep-poll loop around a checks call.
    check(f"test_wait_is_blocking_not_polled[{label}:negative]",
          not re.search(r"(while|until)\b[^\n]*\n(?:[^\n]*\n){0,6}?[^\n]*\bsleep\b", src),
          "a sleep-poll loop appears in the skill")
    check(f"test_ci_gate_resolves_the_engine[{label}]",
          "ship-readiness.py" in src and "CLAUDE_PLUGIN_ROOT" in src,
          "the CI gate does not resolve ship-readiness.py with a plugin-root fallback")
    # The RC-capture bug this release caught in its own first draft: `|| true`
    # followed by `$?` captures `true`, so a timeout reads as success.
    check(f"test_rc_capture_is_not_clobbered[{label}]",
          "|| RC_WATCH=$?" in src and not re.search(r"--fail-fast[^\n]*\|\|\s*true", src),
          "RC capture uses `|| true` before reading $?, which captures `true`")
    check(f"test_ci_wait_slot_is_read_with_a_default[{label}]",
          ".ciWaitSeconds // 600" in src, "ciWaitSeconds is not read with a documented default")

# ship names all three kinds at real add-entry sites; ship-spike deliberately
# drafts on ci-failing ONLY (Decision 2) and must NOT import the manifest.
for k in CI_KINDS:
    check(f"test_ship_prescribes_add_entry[{k}]",
          f"--kind {k} " in ship_src, f"no add-entry site for {k}")
check("test_spike_drafts_only_on_failing",
      "ci-failing" in spike_src and "draft" in spike_src.lower()
      and "do not draft" in spike_src.lower(),
      "ship-spike does not state the narrower rule")
check("test_spike_never_claims_pending_is_ready",
      re.search(r"never say \"ready\"", spike_src) is not None,
      "ship-spike does not forbid calling an unconfirmed state ready")

# The honest-window disclosure: the step must SAY the PR is created before CI is
# readable, rather than implying the gate runs first.
check("test_ship_discloses_the_post_create_window",
      "before the PR exists there are zero checks" in ship_src
      and "window closes before Step 8" in ship_src,
      "7a.7 does not disclose the post-create window")

# =========================================================================
# 13. Schema: the slot exists, with the documented default and the swept count.
# =========================================================================
print("\n[schema]")

schema = json.loads((PLUGIN / "schema" / "flow.config.schema.json").read_text())
props = schema["properties"]
check("test_ci_wait_slot_declared", "ciWaitSeconds" in props, "slot missing from the schema")
check("test_ci_wait_slot_default_is_600", props.get("ciWaitSeconds", {}).get("default") == 600,
      str(props.get("ciWaitSeconds", {}).get("default")))
check("test_ci_wait_slot_is_a_non_negative_integer",
      props.get("ciWaitSeconds", {}).get("type") == "integer"
      and props.get("ciWaitSeconds", {}).get("minimum") == 0,
      json.dumps(props.get("ciWaitSeconds", {})))
check("test_ci_wait_description_says_timeout_is_not_a_pass",
      "never a pass" in props.get("ciWaitSeconds", {}).get("description", ""),
      "the slot description does not state that a timeout is not a pass")

# The fan-out: the shipped surfaces must agree with the live count. Delegated to
# the shared wrap-tolerant scanner, not a local line-oriented grep (FB-0079).
scan = _load(PLUGIN / "skills" / "doctor" / "lib" / "slot_count_scan.py", "slot_count_scan")
root = PLUGIN.parent.parent
stale, scanned = scan.scan_paths(
    [root / "plugins", root / "template", root / "README.md"], expected=len(props),
    exclude_substrings=("evals/", "plan-critic.md"), root=root)
check("test_slot_count_sweep_measured_something", scanned > 0,
      f"the sweep scanned {scanned} files — it measured nothing")
check("test_no_stale_slot_count_after_adding_ci_wait", not stale, "; ".join(stale))

print(f"\n{ran - fails}/{ran} checks passed")
if fails:
    print(f"\nFAILED: {fails} check(s)")
    sys.exit(1)
print("\nAll ship-readiness evals passed.")
