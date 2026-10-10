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
CI_GATE = PLUGIN / "skills" / "ship" / "lib" / "ci-gate.sh"
SPIKE_SKILL = PLUGIN / "skills" / "ship-spike" / "SKILL.md"
FIX = HERE / "fixtures" / "ship-readiness"

fails = 0
ran = 0

# Read each skill ONCE. These are large files (ship/SKILL.md is ~204 KB) and were
# previously re-read at five separate sites, including twice inside one boolean
# expression and once per iteration of two loops.
SHIP_SRC = SHIP_SKILL.read_text()
SPIKE_SRC = SPIKE_SKILL.read_text()
GATE_SRC = CI_GATE.read_text()
def code_only(text: str) -> str:
    """Strip `#` comment lines.

    Shared because this trap bit THREE times in one PR: these files' comments EXPLAIN
    what they deliberately no longer do ("dragged in a mkdir", "an earlier cut `exit
    1`'d here"), so a substring test over the whole text reads a file's own rationale as
    the behaviour it forbids — and reports a regression that is actually a changelog.
    `.github/workflows/ci.yml`'s harness-join step scopes itself the same way, for the
    same reason, and says so in a comment this one is modelled on.
    """
    return "\n".join(ln for ln in text.splitlines() if not ln.lstrip().startswith("#"))


GATE_CODE = code_only(GATE_SRC)


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


# Loaded once, here rather than inside a later section: an assertion in § 4 reads the
# merge-state gloss, and the definition used to sit further down the file than its use.
_MERGE_GLOSS = _engine()._MERGE_STATE_MEANING


_CLI_CACHE: dict[tuple[str, ...], dict] = {}


def ci_cli(*args: str) -> dict:
    """Drive the engine through its CLI, not its functions.

    Deliberate: the shipped skill calls the CLI, so an in-process-only harness
    would pin a surface nothing invokes. `.claude/rules/general.md` item 4's
    third corollary -- pin the claim at the layer where it is CLAIMED.
    """
    # Memoized on the arg tuple. EVERY DISTINCT arg-vector still crosses the CLI
    # boundary exactly once, so this does not weaken the surface-layer property above —
    # it only removes re-running the identical command. 13 of 41 spawns were duplicates.
    if args in _CLI_CACHE:
        return _CLI_CACHE[args]
    out = subprocess.run(
        [sys.executable, str(ENGINE), "ci", *args],
        capture_output=True, text=True,
    )
    assert out.returncode == 0, f"engine exited {out.returncode}: {out.stderr}"
    parsed = json.loads(out.stdout)
    _CLI_CACHE[args] = parsed
    return parsed


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
# Reuses `gh_absent` from above rather than re-spawning: `ci_cli` already asserts
# returncode == 0, so the "does not halt" arm is proved by that call having returned.
check("test_absent_gh_degrades_not_halts",
      gh_absent["kind"] == "ci-unknown"
      and "gh is not installed" in GATE_SRC
      and "NOT a passing CI" in GATE_SRC,
      json.dumps(gh_absent))

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
# 2b. The conclusion vocabulary — the table that decides shippability.
# =========================================================================
print("\n[conclusion vocabulary — one fixture per class]")

# Exercised only at SUCCESS/FAILURE before, so a wrong membership was invisible to every
# declared criterion: CANCELLED in the pending set would hang the blocking wait to
# `ciWaitSeconds` on every cancelled run, and a required-but-SKIPPED check would read as
# green. `_bucket` has no default-to-pass branch, which is what makes the last two arms
# below safe by construction rather than by enumeration.
_VOCAB = [
    ("ci-vocab-pass-neutral.json", "PASS", None),
    ("ci-vocab-pass-skipped.json", "PASS", None),
    ("ci-vocab-fail-cancelled.json", "FAIL", "ci-failing"),
    ("ci-vocab-fail-stale.json", "FAIL", "ci-failing"),
    ("ci-vocab-fail-timed-out.json", "FAIL", "ci-failing"),
    ("ci-vocab-fail-action-required.json", "FAIL", "ci-failing"),
    ("ci-vocab-fail-startup-failure.json", "FAIL", "ci-failing"),
    ("ci-vocab-pending-queued.json", "UNDECLARED", "ci-pending"),
    ("ci-vocab-unknown-empty-conclusion.json", "UNDECLARED", "ci-unknown"),
]
for _fx, _want_v, _want_k in _VOCAB:
    _r = ci_fixture(_fx)
    check(f"test_conclusion_vocabulary[{_fx.replace('ci-vocab-', '').replace('.json', '')}]",
          _r["verdict"] == _want_v and _r["kind"] == _want_k,
          f"got {_r['verdict']}/{_r['kind']}, want {_want_v}/{_want_k}")
# A terminal-but-not-passing conclusion must be FAILING, never pending: pending would make
# the blocking wait sit until its ceiling on a run that is already over.
check("test_terminal_non_pass_is_not_pending",
      all(ci_fixture(f)["kind"] != "ci-pending"
          for f, v, k in _VOCAB if v == "FAIL"),
      "a terminal non-passing conclusion was classified pending — the wait would hang")

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
check("test_gate_performs_the_settle_reread",
      "no-checks-unsettled" in GATE_SRC and "--settled" in GATE_SRC,
      "ci-gate.sh never re-reads with --settled, so the empty-rollup pass is unreachable")

# =========================================================================
# 4. mergeStateStatus is a cross-check, never the sole source.
# =========================================================================
print("\n[mergeStateStatus cross-check]")

# The cross-check that REMAINS after BLOCKED was removed from the blocking set: a branch
# that conflicts with its base cannot mean "waiting for a human", so all-green + DIRTY is
# still correctly not-ready. This is the positive half that keeps the removal above from
# being a silent weakening — delete the cross-check entirely and this fails.
dirty_pass = ci_cli("--blob", str(FIX / "ci-passing-but-dirty.json"), "--settled")
check("test_passing_checks_but_branch_conflicts",
      dirty_pass["verdict"] == "UNDECLARED" and dirty_pass["kind"] == "ci-unknown"
      and "DIRTY" in dirty_pass["reason"],
      json.dumps(dirty_pass))
# BLOCKED must NOT draft an all-green PR. GitHub returns it both for a missing required
# CHECK and for a missing required REVIEW, and cannot distinguish them — so on a
# branch-protected repo it is the ordinary state of every fresh PR, i.e. the state at the
# moment 7a.7 runs. Treating it as "CI not green" drafted every such PR. Paired with
# DIRTY, which cannot mean "waiting for a human", so the cross-check still does its job.
_blk = ci_cli("--blob", str(FIX / "ci-passing-but-blocked.json"), "--settled")  # the regression fixture
check("test_blocked_does_not_draft_an_all_green_pr",
      _blk["verdict"] == "PASS",
      "an all-green PR awaiting its required review is reported not-ready and drafted")
check("test_dirty_still_blocks_an_all_green_pr",
      ci_cli("--blob", str(FIX / "ci-no-checks-dirty.json"), "--settled")["kind"] == "ci-unknown"
      and "DIRTY" in _MERGE_GLOSS,
      "the merge-state cross-check no longer catches anything")
# And the #176 regression must not depend on that cross-check at all: its fixture carries
# BLOCKED, so if `failing` did not win the precedence ladder first, removing BLOCKED from
# the blocking set would have silently weakened the one case this release exists to catch.
check("test_pr176_does_not_depend_on_the_merge_cross_check",
      json.loads((FIX / "ci-failing-pr176.json").read_text())["mergeStateStatus"] == "BLOCKED"
      and failing["verdict"] == "FAIL" and failing["kind"] == "ci-failing",
      "#176's shape no longer resolves via the failing-check path")

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
# The boundary value, paired. MEASURED: `timeout 0` disables the timeout, so the slot's
# documented "read once, do not wait" would become an UNBOUNDED wait if the guard were
# dropped. The negative alone (no unguarded call) would pass if the whole wait were
# deleted, so assert BOTH that the guard exists and that the `timeout` call it guards is
# still there (general.md item 3).
check("test_zero_wait_skips_the_blocking_call[guard]",
      '[ "$_wait" -gt 0 ]' in GATE_SRC,
      "ciWaitSeconds:0 reaches `timeout 0`, which DISABLES the timeout — unbounded wait")
check("test_zero_wait_skips_the_blocking_call[call-still-there]",
      'timeout "$_wait" gh pr checks' in GATE_SRC,
      "the guard is present but the timeout call it guards is gone")

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
# REQUIRED for every CHECK_ONLY kind, with no shared default. Applied to only the three
# new kinds, it left `toolchain` printing "I won't mark a failing build ready" on a kind
# where nothing was built — the hazard that kind's own comment already named. A fallback
# is what let that be silently wrong, so there isn't one.
for k in sorted(mt.CHECK_ONLY):
    check(f"test_every_check_only_kind_has_its_own_option[{k}]",
          "check_only_option" in mt.KIND_COPY[k],
          "a CHECK_ONLY kind with no option line — _copy() would return the generic "
          "schema backstop, which says nothing a reader can act on")
check("test_check_only_options_are_all_distinct",
      len({mt.KIND_COPY[k]["check_only_option"] for k in mt.CHECK_ONLY}) == len(mt.CHECK_ONLY),
      "two CHECK_ONLY kinds share an option line, so one of them is describing the other")
check("test_only_the_build_kind_mentions_a_failing_build",
      [k for k in sorted(mt.CHECK_ONLY)
       if "failing build" in mt.KIND_COPY[k]["check_only_option"]] == ["verify-build"],
      "a non-build kind tells the reader the refusal is about a failing build")

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

ship_src = SHIP_SRC
spike_src = SPIKE_SRC

# THE MECHANISM lives in ci-gate.sh now; the skills COMPOSE it. Assert each where it is
# made — a mechanism assertion aimed at the skills would pass on prose that merely
# mentions the helper.
# POSITIVE first. A negative-only assertion ("contains no poll loop") passes if the whole
# wait is deleted — general.md item 3's prohibition-satisfiable-by-deletion shape, which
# this repo has shipped twice.
check("test_wait_is_blocking_not_polled[positive]",
      "--watch" in GATE_SRC
      and re.search(r'timeout\s+"\$_wait"\s+gh pr checks', GATE_SRC) is not None,
      'no `timeout "$_wait" gh pr checks … --watch` found in ci-gate.sh')
# NEGATIVE: no sleep-poll loop around a checks call. The settle re-read is a single
# guarded `sleep`, not a loop, so this must still hold.
check("test_wait_is_blocking_not_polled[negative]",
      not re.search(r"(while|until)\b[^\n]*\n(?:[^\n]*\n){0,6}?[^\n]*\bsleep\b", GATE_SRC),
      "a sleep-poll loop appears in ci-gate.sh")
check("test_gate_resolves_the_engine",
      "ship-readiness.py" in GATE_SRC and "CLAUDE_PLUGIN_ROOT" in GATE_SRC,
      "ci-gate.sh does not resolve ship-readiness.py with a plugin-root fallback")
# The RC-capture bug this release caught in its own first draft: `|| true` followed by
# `$?` captures `true`, so a timeout reads as success.
check("test_rc_capture_is_not_clobbered",
      "|| _rc=$?" in GATE_SRC
      and not re.search(r"--fail-fast[^\n]*\|\|\s*true", GATE_SRC),
      "RC capture uses `|| true` before reading $?, which captures `true`")
check("test_ci_wait_slot_is_read_from_the_repo_root",
      '"$_root/flow.config.json"' in GATE_SRC,
      "the slot is read CWD-relative, so running from a subdirectory silently reverts it "
      "to the default — which is the drift that motivated this shared helper")
check("test_ci_wait_slot_is_read_with_a_default",
      ".ciWaitSeconds // 600" in GATE_SRC,
      "ciWaitSeconds is not read with a documented default")
check("test_settle_seconds_has_one_definition",
      GATE_SRC.count("FLOW_CI_SETTLE_SECONDS:=20") == 1
      and "sleep 20" not in SHIP_SRC and "sleep 20" not in SPIKE_SRC,
      "the settle delay is a literal in more than one place")

# THE COMPOSITION: both skills must SOURCE the helper and act on its verdict. A skill that
# merely names the file would satisfy a substring test, so assert the call too.
for label, src in (("ship", ship_src), ("ship-spike", spike_src)):
    check(f"test_skill_sources_the_shared_gate[{label}]",
          "ci-gate.sh" in src and "flow_ci_status" in src and ". \"$CG\"" in src,
          "the skill does not source ci-gate.sh and call flow_ci_status")
    # PAIRED: it must say so loudly, AND it must not halt. The gate runs after the PR
    # exists and before §7b reconciles it, so an exit there leaves an open PR whose body
    # was never matched to a verdict — and would invert criterion 6 for a neighbouring
    # branch of the same gate.
    # Boundary is the OUTER else's body (`. "$CG"`), not the first `else` — this branch
    # contains an inner if/else, so splitting on "else" cut it in half and lost the
    # fallback that the assertion is looking for.
    _branch = code_only(
        src.split('if [ ! -f "$CG" ]; then')[1].split('. "$CG"')[0]
    )
    check(f"test_skill_refuses_when_the_gate_is_absent[{label}:loud]",
          "ci-gate.sh not found" in src and "NOT confirmed green" in src,
          "a missing helper degrades silently — an unreadable gate is not a passing gate")
    check(f"test_skill_refuses_when_the_gate_is_absent[{label}:degrades-not-halts]",
          "exit 1" not in _branch and "ci-unknown" in _branch,
          "the missing-helper branch halts instead of degrading to ci-unknown, leaving an "
          "open PR whose body was never reconciled to a verdict")

# The gate writes NO scratch files, which is why it needs no CWE-59 preamble. Paired: the
# absence of file writes AND the presence of the variable that replaced them, so this
# cannot be satisfied by deleting the acquisition entirely.
check("test_gate_writes_no_scratch_files",
      "FLOW_SCRATCH" not in GATE_CODE and "mkdir" not in GATE_CODE
      and ".gitignore" not in GATE_CODE,
      "the gate stages status through a file again, which re-introduces the CWE-59 surface "
      "that deleting the file removed")
check("test_gate_still_captures_the_status",
      "FLOW_CI_JSON=" in GATE_CODE and "_raw=$(gh pr view" in GATE_CODE,
      "the acquisition is gone, so the assertion above protects nothing")

# ship names all three kinds at real add-entry sites; ship-spike deliberately
# drafts on ci-failing ONLY (Decision 2) and must NOT import the manifest.
for k in CI_KINDS:
    check(f"test_ship_prescribes_add_entry[{k}]",
          f"--kind {k} " in ship_src, f"no add-entry site for {k}")
check("test_spike_drafts_only_on_failing",
      "ci-failing" in spike_src and "draft" in spike_src.lower()
      and "do not draft" in spike_src.lower(),
      "ship-spike does not state the narrower rule")
# The third arm my manifest resolution promised: the three-state ACTION table, not just
# the draft-on-red half. ship-spike has no manifest, so nothing else in this harness
# would notice if its pending/unknown branch silently started drafting (or stopped
# reporting) -- it is the one place in this change where a PR whose checks are not green
# is deliberately left un-drafted, which is exactly why it needs a declared criterion.
check("test_spike_three_state_action_table",
      all(k in spike_src for k in ("ci-failing", "ci-pending", "ci-unknown"))
      and "report it, do not draft" in spike_src
      and "halt-and-adjudicate" in spike_src
      # NEGATIVE half: spike must not import the draft manifest it does not have.
      and "add-entry" not in spike_src.split("### CI gate")[1].split("The PR title MUST")[0],
      "ship-spike's CI policy does not name all three states with their distinct actions, "
      "or it reaches for the draft manifest it deliberately has none of")

check("test_spike_never_claims_pending_is_ready",
      re.search(r"never say \"ready\"", spike_src) is not None,
      "ship-spike does not forbid calling an unconfirmed state ready")

# NOTE: the CWE-59 file-guard assertions that stood here are deliberately GONE, replaced
# by `test_gate_writes_no_scratch_files` above. The gate used to stage its status JSON
# through `.flow/`, which required a mkdir, a self-ignore write and three unlinks; the
# altitude review pointed out that nothing read the file after the block, so the whole
# surface was deleted rather than guarded. Asserting the guards now would pin machinery
# that should not exist.

# The gate PROPOSES a fix for a red check; it never applies one. Decided at the gate,
# 2026-10-09: a gate writing to the branch with no human in the loop is the
# permanence/risk category general.md § Autonomous work guardrails reserves for an
# explicit decision, and every other auto-fix in this pipeline is proposal-only.
#
# PAIRED, three ways, because each half alone is satisfiable the wrong way:
#   positive  -- the propose instruction must be present (a negative alone passes if the
#                whole red-check path is deleted; general.md item 3)
#   negative  -- the §7a.7 block must not instruct a commit/push on a red check
#   copy join -- the manifest kind the human actually READS must not promise a push the
#                skill no longer performs (the fan-out class, in user-facing copy)
_77_PROSE = ship_src[ship_src.index("### 7a.7."):ship_src.index("### 7b.")]
check("test_red_check_is_proposed_not_applied[positive]",
      "PROPOSE the fix — do not apply it" in _77_PROSE
      and "candidate resolutions:" in _77_PROSE,
      "the red-check path no longer tells the agent to draft the fix as a decision")
check("test_red_check_is_proposed_not_applied[negative]",
      not re.search(r"attempt \*\*once\*\*, commit, push", _77_PROSE)
      and "record-attempt --kind ci-failing" not in _77_PROSE,
      "the gate still instructs an unapproved commit/push on a red check")
check("test_red_check_copy_does_not_promise_a_push",
      "apply the fix you approved" in mt.KIND_COPY["ci-failing"]["then"]
      and "Approve the fix I drafted" in mt.KIND_COPY["ci-failing"]["needs_you"],
      "the ci-failing kind's copy promises to push a fix the skill will not push without "
      "approval — the human reads this, so it is the half that matters most")
# And the approved path must still exist: approval routes through the §7c reconcile, so
# "propose-only" must not have left the fix with nowhere to go.
check("test_approved_fix_still_has_a_route",
      "Step 7c reconcile fast-path" in _77_PROSE,
      "propose-only with no apply route — the human's approval would dead-end")

# The honest-window disclosure: the step must SAY the PR is created before CI is
# readable, rather than implying the gate runs first.
check("test_ship_discloses_the_post_create_window",
      "before the PR exists there are zero checks" in ship_src
      and "window closes before Step 8" in ship_src,
      "7a.7 does not disclose the post-create window")

# =========================================================================
# 12b. The prose predicate and the engine predicate must not drift apart.
# =========================================================================
print("\n[predicate join — prose vs engine]")

GENERAL = PLUGIN / "skills" / "general" / "SKILL.md"
WORKFLOW = PLUGIN / "docs" / "workflow.md"
_gen = GENERAL.read_text()
_wf = WORKFLOW.read_text()
# The engine ships six conditions. Both prose surfaces that state the auto-advance rule
# must mention CI, or an agent reads a five-condition predicate while the engine (and the
# changelog) claim six — the fan-out contradiction class, which this repo tracks as its
# most expensive recurring bug.
check("test_rule_skill_predicate_includes_ci",
      "CI checks observed green" in _gen,
      "general/SKILL.md's auto-advance predicate omits the CI condition the engine ships")
check("test_workflow_predicate_includes_ci",
      "CI checks are green" in _wf and "pending" in _wf,
      "workflow.md § Ship-readiness predicate omits the CI condition")
check("test_workflow_invokes_the_engine",
      "ship-readiness.py" in _wf and 'check --plan' in _wf,
      "workflow.md states the predicate but never invokes the engine that evaluates it — "
      "~250 shipped lines with no caller (the FB-0074 unwired-composition shape)")
check("test_engine_still_declares_six_conditions",
      len(eng.CONDITION_ORDER) == 6 and "ci" in eng.CONDITION_ORDER,
      f"CONDITION_ORDER = {eng.CONDITION_ORDER}")

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
