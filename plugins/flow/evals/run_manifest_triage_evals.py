#!/usr/bin/env python3
"""Eval harness for manifest-triage.py — the deterministic draft-manifest triage
engine behind FB-0075 (a draft PR is a last resort, not a deliverable).

Pins the classification table and, more importantly, the six safety invariants
the plan gates hammered out. Several of these exist because a plan revision got
them WRONG and /flow:critique-plan or /flow:audit-plan caught it:

  * residual is the uncleared set minus honored waivers — never a class filter
    (a class filter let a failed visual-deliverable attempt reach a ready PR)
  * a verify-build entry is never subtracted by a waiver and never waivable to
    ready (SKILL.md:308,310 is unqualified — no merge-ready PR on a non-PASS build)
  * an auto entry that already attempted demotes to ask, and the demotion is
    persisted (an in-session-only demotion evaporated at the §7c recompute)
  * state that cannot be recovered never yields auto (a /tmp record fails OPEN
    across a cross-session §7c; the rigor-marker precedent fails CLOSED)
  * a waiver is honored only on an exact fingerprint match (an over-greedy body
    reconstruction could otherwise subtract a real blocker)
  * an unrecognized verb goes blocked for security/a11y, ask elsewhere, auto never

Also pins the producer-line contract: every one of the 10 producer sites' real
prescribed line must round-trip through `parse` yielding a kind, an in-vocabulary
verb, and a confidence value — and the rendered manifest must stay coherent with
lib/pr-coherence.py (the FB-0067 invariant this must not disturb).

Stdlib only. No git/gh dependency.
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
SCRIPT = HERE.parent / "skills" / "ship" / "lib" / "manifest-triage.py"
COHERENCE = HERE.parent / "skills" / "ship" / "lib" / "pr-coherence.py"
SHIP_SKILL = HERE.parent / "skills" / "ship" / "SKILL.md"
SEC_SKILL = HERE.parent / "skills" / "security-review" / "SKILL.md"
A11Y_SKILL = HERE.parent / "skills" / "accessibility-review" / "SKILL.md"
FIXTURE = HERE / "fixtures" / "resolution-confidence-routing" / "expected" / "ship-routing.md"

_failures: list[str] = []


def _load_triage():
    """Load manifest-triage.py by path (hyphenated name isn't importable).

    Reused so the KIND_COPY/KINDS count assertion below reads the SAME table the
    engine actually runs against, not a hand-copied literal that could silently
    diverge from it.
    """
    spec = importlib.util.spec_from_file_location("manifest_triage", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def expect(label: str, got, want, ctx: str = "") -> None:
    if got == want:
        print(f"  PASS  {label}")
    else:
        print(f"  FAIL  {label}\n        got={got!r} want={want!r}\n        {ctx[:400]}")
        _failures.append(label)


def expect_true(label: str, cond: bool, ctx: str = "") -> None:
    expect(label, bool(cond), True, ctx)


# ONE temp dir for the whole run, not one per call: `mkdtemp()` per call leaked a
# directory at each of the call sites below and the counter was redundant with it.
_TXT_DIR = Path(tempfile.mkdtemp(prefix="flow-eval-fields-"))
_TXT_N = 0


def txt(content: str) -> str:
    """Write a free-text field to a real file and return its path (FB-0108).

    `add-entry`/`record-attempt`/`waive` take --finding-file/--resolution-file, not raw
    argv. These calls go through subprocess with a LIST argv, so they never had shell
    exposure -- but they are migrated anyway, deliberately: an eval that exercises a
    path production no longer uses is a weaker eval, and the argv flags are gone.
    """
    global _TXT_N
    _TXT_N += 1
    f = _TXT_DIR / f"field-{_TXT_N}.txt"
    f.write_text(content, encoding="utf-8")
    return str(f)


def run(args: list[str]) -> tuple[int, str]:
    proc = subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True)
    return proc.returncode, proc.stdout + proc.stderr


# The engine under test, loaded ONCE via the existing `_load_triage` (a second loader
# exec'd it under a second module name, so KINDS/KIND_COPY existed as two independent
# objects and `_load_triage`'s "the SAME table the engine runs against" promise was only
# half-true). Assertions below deliberately use the engine's OWN normaliser rather than a
# hand-typed expectation — a parallel Python twin is how an earlier harness here passed
# while production was broken.
_ENGINE = _load_triage()
MANIFEST_CLOSE = _ENGINE.MANIFEST_CLOSE
_collapse = _ENGINE._collapse_newlines


def _fingerprint_of(kind: str, finding: str) -> str:
    return _ENGINE._fingerprint(kind, finding)


def line(kind: str, finding: str, needs: str, conf: str = "decision-required",
         res: str = "do the thing") -> str:
    return (f"- [{kind}] {finding} — needs: {needs} — confidence: {conf}"
            f" — candidate resolutions: {res}")


def body(*lines: str) -> str:
    return ("## 🚫 NOT READY TO MERGE — unresolved blockers\n"
            "<!-- flow:not-ready-manifest -->\n" + "\n".join(lines) +
            "\n<!-- /flow:not-ready-manifest -->\n")


def classify(entries_text: str, state_path: Path | None = None,
             body_path: Path | None = None, branch: str = "evalbranch") -> dict:
    with tempfile.TemporaryDirectory() as td:
        ef = Path(td) / "entries.md"
        ef.write_text(entries_text, encoding="utf-8")
        args = ["classify", "--entries-file", str(ef), "--branch", branch]
        # A path that does not exist means "state lost" — the fail-safe case.
        args += ["--state-file", str(state_path) if state_path else str(Path(td) / "missing.json")]
        if body_path:
            args += ["--body-file", str(body_path)]
        rc, out = run(args)
        if rc != 0:
            raise AssertionError(f"classify exited {rc}: {out}")
        return json.loads(out)


def by_kind(result: dict, kind: str) -> dict:
    for e in result["entries"]:
        if e["kind"] == kind:
            return e
    raise AssertionError(f"no {kind} entry in {[e['kind'] for e in result['entries']]}")


def fresh_state(td: str, branch: str = "evalbranch") -> Path:
    # Per-branch filename: a shared path would leak one test's waivers into the next.
    p = Path(td) / f"state-{branch}.json"
    if p.exists():
        p.unlink()
    rc, out = run(["init-state", "--branch", branch, "--path", str(p)])
    assert rc == 0, out
    return p


# --------------------------------------------------------------------------
# 1. The classification table — one case per row.
# --------------------------------------------------------------------------

TABLE_CASES = [
    # (kind, verb, expected class, note)
    ("visual-deliverable", "re-run", "auto", "the only auto row"),
    ("visual-deliverable", "hand-author", "auto", "authoring is agent work too"),
    ("rigor", "re-run", "ask", "1.0a already re-ran (#81); the entry IS the residue"),
    ("skip-audit", "re-run", "ask", "2a already re-ran + re-audited once"),
    ("verify-build", "regression fix", "ask", "FB-0012's bounded retry already spent"),
    ("verify-build", "declare + fence", "ask", "no_plan_fallback: agent must not self-declare"),
    ("coverage", "declare + fence", "ask", "never auto-add the criterion (SKILL.md:272)"),
    ("vacuous-criterion", "declare + fence", "ask", "never self-declare the rewrite specific enough — coverage's self-grading problem, one level up"),
    ("status-surface", "reconcile", "ask", "never silently rewrite an un-fenced doc (SKILL.md:585)"),
    ("security", "design decision", "ask", "competing valid fixes escalate (FB-0011)"),
    ("a11y", "design decision", "ask", "competing valid fixes escalate (FB-0011)"),
    ("security", "secret rotation", "blocked", "out-of-session human action"),
    ("security", "dep vetting", "blocked", "out-of-session human action"),
    ("a11y", "dep vetting", "blocked", "out-of-session human action"),
    # Verb-independent: no resolution verb makes a missing toolchain answerable
    # in-session, so unlike security/a11y there is no verb sub-split to test.
    ("toolchain", "re-run", "blocked", "the machine lacks the toolchain — out-of-session by nature"),
]


def test_table(td: str) -> None:
    print("\n[table] classification, one case per row")
    st = fresh_state(td)
    seen: dict[str, str] = {}
    for kind, verb, want, note in TABLE_CASES:
        r = classify(body(line(kind, "some finding", verb)), st)
        cls = by_kind(r, kind)["class"]
        seen[kind] = cls
        expect(f"{kind} + '{verb}' ⇒ {want}  ({note})", cls, want)
    # The "only one auto row" claim belongs next to the table it is a claim about
    # — and reusing the results above avoids re-running the same 14 classifications.
    expect("visual-deliverable is the ONLY auto-class kind",
           {k for k, c in seen.items() if c == "auto"}, {"visual-deliverable"})


def test_failsafes(td: str) -> None:
    print("\n[fail-safe] unrecognized verb never yields auto")
    st = fresh_state(td)
    r = classify(body(line("security", "odd finding", "frobnicate")), st)
    expect("security + off-vocabulary verb ⇒ blocked (the dangerous mis-class)",
           by_kind(r, "security")["class"], "blocked")
    r = classify(body(line("a11y", "odd finding", "frobnicate")), st)
    expect("a11y + off-vocabulary verb ⇒ blocked", by_kind(r, "a11y")["class"], "blocked")
    r = classify(body(line("visual-deliverable", "odd finding", "frobnicate")), st)
    expect("visual-deliverable + off-vocabulary verb ⇒ ask, NOT auto "
           "(the one kind that can go auto — §7c rebuilds entries from a human-editable PR body)",
           by_kind(r, "visual-deliverable")["class"], "ask")
    r = classify(body(line("visual-deliverable", "odd finding", "secret rotation")), st)
    expect("visual-deliverable + a wrong-but-in-vocabulary verb still ⇒ auto only via its own verbs",
           by_kind(r, "visual-deliverable")["class"], "ask")
    r = classify(body(line("coverage", "odd finding", "frobnicate")), st)
    expect("coverage + off-vocabulary verb ⇒ ask (never blocked, never auto)",
           by_kind(r, "coverage")["class"], "ask")
    r = classify(body(line("made-up-kind", "odd finding", "re-run")), st)
    expect("unrecognized KIND ⇒ ask, never auto, never dropped",
           by_kind(r, "made-up-kind")["class"], "ask")
    expect("unrecognized kind is still counted", len(r["entries"]), 1)


def test_add_entry(td: str) -> None:
    print("\n[writer] add-entry owns the line shape and validates at write time")
    rc, out = run(["add-entry", "--kind", "coverage", "--finding-file", txt("5 undeclared behaviors"),
                   "--needs", "declare + fence",
                   "--resolution-file", txt("declare each in the Spec-walk block")])
    expect("add-entry exits 0 on a valid entry", rc, 0, out)
    with tempfile.TemporaryDirectory() as td2:
        f = Path(td2) / "l.md"
        f.write_text(out, encoding="utf-8")
        rc2, parsed = run(["parse", "--body-file", str(f)])
    e = json.loads(parsed)["entries"][0]
    expect("its output round-trips through parse", (e["kind"], e["needs"]), ("coverage", "declare + fence"))
    expect_true("and carries the drafted resolution", "Spec-walk" in e["drafted_resolution"], parsed)

    rc, out = run(["add-entry", "--kind", "bogus", "--finding-file", txt("x"), "--needs", "re-run"])
    expect("an unknown kind is rejected at WRITE time, not fail-safed at classify", rc, 2, out)
    rc, out = run(["add-entry", "--kind", "coverage", "--finding-file", txt("x"), "--needs", "frobnicate"])
    expect("an off-vocabulary needs verb is rejected at write time", rc, 2, out)

    rc, out = run(["add-entry", "--kind", "visual-deliverable", "--finding-file", txt("missing walkthrough"),
                   "--needs", "re-run", "--attempted"])
    expect_true("--attempted stamps the marker so the demotion survives a re-render",
                "already-attempted" in out, out)


def test_manifest_lifecycle(td: str) -> None:
    print("\n[lifecycle] the manifest file is branch-scoped and a missing one is EMPTY, not an error")
    rc, out = run(["manifest-path", "--branch", "feature/a"])
    rc2, out2 = run(["manifest-path", "--branch", "feature/b"])
    expect("manifest-path exits 0", rc, 0, out)
    expect_true("two branches resolve to DIFFERENT manifest files (a fixed name leaked "
                "one branch's entries into the next run)", out.strip() != out2.strip(), out + out2)

    st = fresh_state(td, "life")
    missing = str(Path(td) / "no-such-manifest.md")
    with tempfile.TemporaryDirectory() as td2:
        args = ["classify", "--entries-file", missing, "--state-file", str(st), "--branch", "life"]
        rc, out = run(args)
    expect("a MISSING manifest file classifies cleanly — this is the common no-blockers path, "
           "and it used to crash every clean ship run", rc, 0, out)
    r = json.loads(out)
    expect("…and yields zero entries", len(r["entries"]), 0)
    expect("…with verdict READY", r["verdict"], "READY")

    rc, out = run(["init-run", "--branch", "life-reset"])
    expect("init-run exits 0 and prints the path it reset", rc, 0, out)
    p = Path(out.strip())
    p.write_text("- [coverage] stale entry — needs: declare + fence — confidence: decision-required\n",
                 encoding="utf-8")
    run(["init-run", "--branch", "life-reset"])
    expect("init-run TRUNCATES a stale manifest (a survivor from a prior run is "
           "un-subtractable if it is verify-build)", p.read_text(encoding="utf-8").strip(), "")
    p.unlink(missing_ok=True)


def test_prescribed_sequence(td: str) -> None:
    print("\n[prescribed] the SKILL's own call sequence must not defeat invariant 5")
    # The engine-level state-unavailable test passed while the PIPELINE re-enabled
    # `auto`: the prescribed blocks called `init-state` before classify, which
    # materializes an empty record, so a LOST state read back as `present`.
    # Readers must resolve the path without creating it.
    rc, out = run(["state-path", "--branch", "freshhost"])
    expect("state-path exits 0", rc, 0, out)
    p = Path(out.strip())
    expect_true("state-path does NOT create the record (init-state's job, once per run)",
                not p.exists(), f"{p} was created by a read-only resolve")

    b = body(line("visual-deliverable", "missing walkthrough", "re-run"))
    r = classify(b, p, branch="freshhost")
    expect("resolving-without-creating keeps a lost state UNAVAILABLE ⇒ ask, never auto",
           by_kind(r, "visual-deliverable")["class"], "ask")
    expect("…and reports it honestly", r["state_status"], "unavailable")

    # Contract-grep: no reader site may call init-state.
    src = SHIP_SKILL.read_text(encoding="utf-8")
    for marker in ("render-manifest", "render-decisions"):
        i = src.index(f'"$TRIAGE" {marker}')
        window = src[max(0, i - 700):i]
        # Match the INVOCATION, not the word — the block deliberately mentions
        # init-state in a comment explaining why readers must not call it.
        expect_true(f"the {marker} block resolves the state path without INVOKING init-state",
                    'state-path --branch' in window
                    and '"$TRIAGE" init-state' not in window, window[-250:])
    expect_true("the render-decisions block passes --body-file so PR-body waivers "
                "reconstruct when the /tmp cache is gone",
                "--body-file" in src[src.index('"$TRIAGE" render-decisions') - 900:
                                     src.index('"$TRIAGE" render-decisions') + 200],
                "no --body-file at the render-decisions site")


def test_auto_renders_as_question(td: str) -> None:
    print("\n[render] a residual auto entry is still shown to the human")
    # It should not normally exist (§7a.5 attempts then demotes), but if the
    # attempt step is skipped it must not vanish — an item the human never sees
    # is the exact failure this change exists to remove. It carries no waive
    # option: the agent has not tried yet, so "waive" is not the honest move.
    st = fresh_state(td, "autorender")
    b = body(line("visual-deliverable", "missing walkthrough", "re-run"))
    r = classify(b, st, branch="autorender")
    expect("precondition: it classifies auto", by_kind(r, "visual-deliverable")["class"], "auto")
    with tempfile.TemporaryDirectory() as td2:
        ef = Path(td2) / "e.md"
        ef.write_text(b, encoding="utf-8")
        rc, out = run(["render-decisions", "--entries-file", str(ef),
                       "--state-file", str(st), "--branch", "autorender"])
    expect("render-decisions exits 0", rc, 0, out)
    expect_true("an auto entry renders as a numbered question, not dropped", "1." in out, out)
    expect_true("…with no waive option (the agent has not attempted it yet)",
                "waive it and ship as-is" not in out, out)


def test_state_durability(td: str) -> None:
    print("\n[invariant 5] state that cannot be recovered never yields auto")
    st = fresh_state(td)
    b = body(line("visual-deliverable", "missing walkthrough", "re-run"))
    expect("state present + no attempt ⇒ auto", by_kind(classify(b, st), "visual-deliverable")["class"], "auto")

    r = classify(b, None)  # state file path that does not exist
    expect("state UNAVAILABLE ⇒ ask, never auto (a /tmp record fails open)",
           by_kind(r, "visual-deliverable")["class"], "ask")
    expect("state_status reports unavailable", r["state_status"], "unavailable")

    # Reconstructed from the PR body only: waivers honored, auto still refused.
    with tempfile.TemporaryDirectory() as td2:
        bp = Path(td2) / "body.md"
        bp.write_text(b, encoding="utf-8")
        r = classify(b, None, body_path=bp)
        expect("state RECONSTRUCTED from body ⇒ still ask, never auto",
               by_kind(r, "visual-deliverable")["class"], "ask")
        expect("state_status reports reconstructed", r["state_status"], "reconstructed")


def test_attempt_demotion(td: str) -> None:
    print("\n[invariant] a failed auto attempt demotes to ask, and the demotion persists")
    st = fresh_state(td, "demote")
    b = body(line("visual-deliverable", "missing walkthrough", "re-run"))
    expect("before the attempt ⇒ auto", by_kind(classify(b, st, branch="demote"), "visual-deliverable")["class"], "auto")

    rc, out = run(["record-attempt", "--branch", "demote", "--path", str(st),
                   "--kind", "visual-deliverable", "--finding-file", txt("missing walkthrough")])
    expect("record-attempt exits 0", rc, 0, out)

    r = classify(b, st, branch="demote")
    e = by_kind(r, "visual-deliverable")
    expect("after the attempt ⇒ ask (persisted, survives a fresh recompute)", e["class"], "ask")
    expect("the entry stays in the residual set — it does NOT vanish", e["in_residual"], True)
    expect("verdict is not READY while it is unresolved", r["verdict"], "DECIDE")

    # And it must still render as an answerable question, not an inert residue.
    with tempfile.TemporaryDirectory() as td2:
        ef = Path(td2) / "e.md"
        ef.write_text(b, encoding="utf-8")
        rc, out = run(["render-decisions", "--entries-file", str(ef),
                       "--state-file", str(st), "--branch", "demote"])
        expect_true("a demoted entry renders as a numbered question", "1." in out, out)
        expect_true("and says it was already tried", "Already tried" in out, out)


def test_residual_definition(td: str) -> None:
    print("\n[invariant 2] residual = uncleared minus honored waivers, never a class filter")
    st = fresh_state(td, "resid")
    b = body(
        line("visual-deliverable", "missing walkthrough", "re-run"),   # auto
        line("coverage", "5 undeclared behaviors", "declare + fence"),  # ask, waivable
        line("security", "leaked token", "secret rotation"),            # blocked
        line("verify-build", "criterion 3 FAIL", "regression fix"),     # ask, never waivable
    )
    r = classify(b, st, branch="resid")
    expect("all three classes present, none cleared ⇒ all in residual", len(r["residual"]), 4)
    expect("verdict BLOCKED when a blocked entry is present", r["verdict"], "BLOCKED")

    # Waive the waivable one — it leaves the residual set.
    run(["waive", "--branch", "resid", "--path", str(st),
         "--kind", "coverage", "--finding-file", txt("5 undeclared behaviors")])
    r = classify(b, st, branch="resid")
    expect("a waived, waivable entry leaves the residual set", len(r["residual"]), 3)
    expect("and is reported as waived (never silently dropped)", len(r["waived"]), 1)
    expect_true("the waived entry keeps its identity for the body section",
                r["waived"][0]["kind"] == "coverage", json.dumps(r["waived"]))


def test_verify_build_invariant(td: str) -> None:
    print("\n[invariant 3] no merge-ready PR on a non-PASS build — unqualified")
    st = fresh_state(td, "vb")
    b = body(line("verify-build", "criterion 3 FAIL", "regression fix"))
    r = classify(b, st, branch="vb")
    e = by_kind(r, "verify-build")
    expect("a verify-build entry is not waivable", e["waivable"], False)

    run(["waive", "--branch", "vb", "--path", str(st),
         "--kind", "verify-build", "--finding-file", txt("criterion 3 FAIL")])
    r = classify(b, st, branch="vb")
    e = by_kind(r, "verify-build")
    expect("waiving it is RECORDED", e["waived"], True)
    expect("but it is NEVER subtracted from the residual set", e["in_residual"], True)
    expect("so the verdict can never be READY", r["verdict"], "DECIDE")
    expect("residual still holds it after the waiver", len(r["residual"]), 1)

    with tempfile.TemporaryDirectory() as td2:
        ef = Path(td2) / "e.md"
        ef.write_text(b, encoding="utf-8")
        rc, out = run(["render-decisions", "--entries-file", str(ef),
                       "--state-file", str(st), "--branch", "vb"])
        expect_true("render-decisions offers NO 'waive and ship as-is' on verify-build",
                    "waive it and ship as-is" not in out, out)
        expect_true("it offers the honest action instead (you mark it ready, not the agent)",
                    "you can do that yourself on GitHub" in out, out)


def test_waiver_fingerprint(td: str) -> None:
    print("\n[invariant 6] a waiver is honored only on an exact fingerprint match")
    st = fresh_state(td, "fp")
    b = body(line("coverage", "5 undeclared behaviors", "declare + fence"))
    run(["waive", "--branch", "fp", "--path", str(st),
         "--kind", "coverage", "--finding-file", txt("5 undeclared behaviors")])
    r = classify(b, st, branch="fp")
    expect("exact match ⇒ subtracted", len(r["residual"]), 0)
    expect("and the verdict is READY once nothing uncleared remains", r["verdict"], "READY")

    # The finding changed since the waiver was given: the waiver must lapse.
    b2 = body(line("coverage", "7 undeclared behaviors", "declare + fence"))
    r = classify(b2, st, branch="fp")
    expect("a mutated finding ⇒ the waiver lapses and the entry re-appears", len(r["residual"]), 1)

    # A waiver reconstructed from the body that matches nothing must not subtract.
    with tempfile.TemporaryDirectory() as td2:
        bp = Path(td2) / "body.md"
        bp.write_text(b2 + "\n## Waived at ship\n- [coverage] something else entirely\n",
                      encoding="utf-8")
        r = classify(b2, None, body_path=bp)
        expect("an un-matched reconstructed waiver leaves the entry in residual "
               "(over-greedy reconstruction cannot subtract a real blocker)",
               len(r["residual"]), 1)

        bp.write_text(b2 + "\n## Waived at ship\n- [coverage] 7 undeclared behaviors\n",
                      encoding="utf-8")
        r = classify(b2, None, body_path=bp)
        expect("an exactly-matching reconstructed waiver IS honored across a cross-session §7c",
               len(r["residual"]), 0)


def test_clears_when(td: str) -> None:
    print("\n[invariant 1] clearing is not this engine's job")
    st = fresh_state(td)
    b = body(*[line(k, "f", "re-run") for k in
               ("rigor", "security", "a11y", "verify-build", "coverage",
                "skip-audit", "status-surface", "visual-deliverable", "toolchain",
                "vacuous-criterion")])
    r = classify(b, st)
    expect("every kind carries a clears_when re-check",
           all(e.get("clears_when") for e in r["entries"]), True)
    expect_true("no output field can express 'cleared'",
                "cleared" not in json.dumps(r), "found a 'cleared' key/value in classify output")


def test_toolchain_kind(td: str) -> None:
    """The `toolchain` kind: blocked, un-waivable, and it drafts the PR.

    This is the kind that says "verifiable in principle, just not on this host".
    It exists so an honest skip on a toolchain-less machine can be recorded through
    flow's non-forgeable manifest path instead of a hand-written PR-body note.
    """
    print("\n[toolchain] the kind that means 'not on this machine'")
    st = fresh_state(td, branch="toolchainbranch")
    b = body(line("toolchain", "verify-build could not run: no Apple toolchain here", "re-run"))

    r = classify(b, st, branch="toolchainbranch")
    e = by_kind(r, "toolchain")
    # `class == blocked` is TABLE_CASES' job (same kind, same verb, same path) and
    # `clears_when` is test_clears_when's; asserting either again here would pin one
    # contract in two places, which is how the two copies come to disagree.
    expect("a blocked toolchain entry is never waivable", e["waivable"], False)
    expect("it stays in the residual set", len(r["residual"]), 1)
    # The whole point: an honest skip still cannot produce a merge-ready PR.
    expect("verdict is not READY — the PR opens as a draft", r["verdict"], "BLOCKED")

    # CHECK_ONLY: a human's say-so cannot clear it — only a passing check can.
    rc, _ = run(["waive", "--branch", "toolchainbranch", "--kind", "toolchain",
                 "--finding-file", txt("verify-build could not run: no Apple toolchain here"),
                 "--path", str(st)])
    r = classify(b, st, branch="toolchainbranch")
    e = by_kind(r, "toolchain")
    expect("a recorded waiver is NOT subtracted (CHECK_ONLY, same as verify-build)",
           len(r["residual"]), 1)
    expect("the waiver is still recorded, just not honored", e["waived"], True)
    expect("and the verdict still is not READY", r["verdict"], "BLOCKED")

    # add-entry accepts it at WRITE time (the kind is in the allow-list), and the
    # line it writes round-trips through the strict parser.
    rc, out = run(["add-entry", "--kind", "toolchain",
                   "--finding-file", txt("verify-build could not run: no Apple toolchain here"),
                   "--needs", "re-run", "--confidence", "decision-required",
                   "--resolution-file", txt("re-run on a machine that has the toolchain")])
    expect("add-entry --kind toolchain is accepted at write time", rc, 0, out)
    with tempfile.TemporaryDirectory() as td2:
        f = Path(td2) / "l.md"
        f.write_text(out, encoding="utf-8")
        rc2, parsed = run(["parse", "--body-file", str(f)])
    expect("its output round-trips through parse", rc2, 0, parsed)
    expect("with kind == toolchain", json.loads(parsed)["entries"][0]["kind"], "toolchain")

    # The human-facing copy must not point at machinery that does not exist yet
    # (the `needs-mac-verify` label + /verify-queue are a later step).
    ef = Path(td) / "toolchain-entries.md"
    ef.write_text(b, encoding="utf-8")
    rc, rendered = run(["render-manifest", "--entries-file", str(ef),
                        "--state-file", str(st), "--branch", "toolchainbranch"])
    expect("render-manifest exits 0", rc, 0, rendered)
    expect_true("it renders under the blocked surface with plain-language copy",
                "What this means" in rendered and "toolchain" in rendered, rendered)
    expect_true("the copy promises no queue that does not exist yet",
                "queue" not in rendered.lower(), rendered)

    # The rendered block must still satisfy pr-coherence in both directions.
    rp = Path(td) / "toolchain-rendered.md"
    rp.write_text(rendered, encoding="utf-8")
    for is_draft, want in (("true", 0), ("false", 1)):
        proc = subprocess.run(
            [sys.executable, str(COHERENCE), "coherence", "--body-file", str(rp),
             "--is-draft", is_draft], capture_output=True, text=True)
        expect(f"pr-coherence on the toolchain block, --is-draft {is_draft} ⇒ exit {want}",
               proc.returncode, want, proc.stdout + proc.stderr)


# A producer block is a fenced ```sh block. That IS the real boundary, so the checks below
# scope to it instead of guessing a character window around a match. Three earlier helpers
# (_APPEND_RE / _manifest_appends / _is_subcommand_produced) and a hand-maintained count
# lived here and were deleted, because they were BROKEN in a way worth recording:
#
#   Every producer's redirect is the byte-identical string `>> "$MANIFEST"`, so
#   `src.find(snippet)` returned the SAME index for all 16 of them -- every "universal"
#   assertion re-inspected the first block, 15 were vacuous, and a hand-composed
#   `echo "[coverage] ... " >> "$MANIFEST"` block passed the allowlist outright. Only the
#   hardcoded count noticed, and a count is not the check. Measured, not supposed.
#
# That is the same shape this PR exists to fix -- an assertion that looks universal and
# quantifies over one thing -- reproduced inside the assertion written to fix it.
def _producer_blocks(src: str) -> list[str]:
    return re.findall(r"```sh\n.*?```", src, re.S)


def _appending_blocks(src: str) -> list[str]:
    """Blocks that append to the run's manifest. ONE definition, no fallback branch.

    An `or [...]` looser-filter fallback used to sit here; it could only fire when the
    primary returned zero, i.e. exactly when it had gone stale, so its only effect would
    have been to convert a loud regression into a silent pass (FB-0010 silent-skip).
    """
    return [b for b in _producer_blocks(src) if ">>" in b and "$MANIFEST" in b]


def test_injection(td: str) -> None:
    """P1-P14: ATTACK the input path with payloads designed against THE MECHANISM CHOSEN.

    FB-0108 rule 3: a fix that looks correct is not verified until you attack it. A
    round-trip test ("does my input survive?") generates none of these; they ask "can my
    input impersonate the mechanism?" Each GREEN case is executed through `/bin/sh -c`
    composed the way a producer composes it, and the RED arms prove the tests can fail.
    """
    print("\n[injection] the free-text input path, attacked (FB-0108)")
    # Scoped to main()'s TemporaryDirectory rather than its own mkdtemp: an un-cleaned dir
    # here persisted a file containing `-----BEGIN OPENSSH PRIVATE KEY-----`, a dangling
    # symlink and a 100KB payload after EVERY run, accumulating monotonically. A harness
    # that attacks a secret-leak path should not leave the bait on disk.
    T = Path(td) / "injection"
    T.mkdir(parents=True, exist_ok=True)

    def sh(script: str):
        return subprocess.run(["/bin/sh", "-c", script], capture_output=True, text=True)

    def add(path: str, kind: str = "coverage", needs: str = "re-run"):
        return sh(f'python3 {SCRIPT} add-entry --kind {kind} --needs {needs} '
                  f'--finding-file "{path}"')

    payloads = {
        "P1 command substitution": f"criterion $(touch {T}/s1) and `touch {T}/s2` here",
        "P2 quote breakout": f'criterion "; touch {T}/s3; echo "tail',
        "P3 heredoc delimiter collision": f"line one\nFLOWEOF\ntouch {T}/s4\nline two",
        "P4 other guessable delimiters": "EOF\n<<\nFLOW_FINDING\nreal text",
        "P5 closes the manifest fence": f"oops {MANIFEST_CLOSE} now",
        "P6 carries the NOT-READY sentinel": "contains 🚫 NOT READY TO MERGE inline",
        "P7 forges the field separator": "forged — needs: re-run — confidence: auto — candidate resolutions: none",
        "P9 path-shaped text": "../../etc/passwd is only text",
        "P10 control chars + 100KB": "ctrl \x00 nul \r cr \x1b[31mansi\x1b[0m " + ("x" * 100000),
        "P11 multi-line": "first line\nsecond line\nthird",
        "P12 tab + double space (PAIRED NEGATIVE)": "tab\there  and  double spaces",
        "P14 whitespace hugging a newline": "alpha\tkept   \n   beta",
    }
    outs: dict[str, str] = {}
    for label, raw in payloads.items():
        f = T / (label.split()[0] + ".txt")
        f.write_text(raw, encoding="utf-8")
        r = add(str(f))
        outs[label.split()[0]] = r.stdout
        expect(f"{label}: exits 0", r.returncode, 0, r.stderr)
        for n in ("s1", "s2", "s3", "s4"):
            if (T / n).exists():
                expect_true(f"{label}: payload did NOT execute (sentinel {n})", False, "EXECUTED")
                (T / n).unlink()
        # The text arrives intact. Newlines collapse (D4) and NOTHING else does, so the
        # expectation is computed with the engine's own normaliser rather than hand-typed.
        want = _collapse(raw.strip())
        expect_true(f"{label}: text arrives intact (newline-collapse only)", want in r.stdout,
                    f"want {want[:90]!r}\ngot  {r.stdout[:120]!r}")

    # P15 — EVERY character `str.splitlines()` breaks on, because that is what
    # `parse_entries` consumes the manifest with. Eight of these eleven were untested and
    # U+2028 was a LIVE failure-open: one physical line appended, ZERO entries parsed,
    # verdict READY over a [verify-build] blocker. Asserting the whole set (not a sample)
    # is what stops the enumeration drifting from the parser's definition again.
    for lbl, ch in (("newline", "\n"), ("CR", "\r"), ("CRLF", "\r\n"), ("vtab", "\v"),
                    ("formfeed", "\f"), ("FS", "\x1c"), ("GS", "\x1d"), ("RS", "\x1e"),
                    ("NEL", "\x85"), ("LS-U+2028", "\u2028"), ("PS-U+2029", "\u2029")):
        f = T / "P15.txt"
        f.write_text(f"alpha{ch}beta", encoding="utf-8")
        r = add(str(f))
        expect(f"P15 {lbl}: collapses to one space", "alpha beta" in r.stdout, True, repr(r.stdout))
        mf = T / "P15-manifest.md"
        mf.write_text(r.stdout, encoding="utf-8")
        _rc, parsed = run(["parse", "--body-file", str(mf)])
        expect(f"P15 {lbl}: the entry still PARSES (a break here erased it before)",
               len(json.loads(parsed)["entries"]), 1, parsed)

    # P12's whole purpose is that D4 did NOT over-collapse: tabs and double spaces are
    # byte-identical. Asserted explicitly, because "want in stdout" above would also pass
    # for an implementation that normalised both sides the same wrong way.
    # Assert against the stdout the loop already captured — re-running `add` here spawned
    # the identical command twice. The cached output came from the same `/bin/sh -c` run.
    expect_true("P12: a tab and a double space survive BYTE-IDENTICALLY (D4 is newline-only)",
                "tab\there  and  double spaces" in outs["P12"], repr(outs["P12"]))
    expect_true("P14: newline-hugging whitespace -> exactly ONE space, mid-line tab intact",
                "alpha\tkept beta" in outs["P14"], repr(outs["P14"]))

    # ---- RED ARMS: one per hazard, each matched to the composition that CARRIES it ----
    # P3's hazard is a HEREDOC collision; a bare FLOWEOF line inside a double-quoted argv
    # string is inert, so an argv red arm for P3 would assert a sentinel that cannot
    # appear. Matching each red arm to its own composition is the point.
    raw1 = payloads["P1 command substitution"]
    sh(f'python3 {SCRIPT} add-entry --kind coverage --needs re-run --finding "{raw1}" 2>/dev/null')
    expect_true("RED (argv): P1's $(...) and backticks DID execute — the test can fail",
                (T / "s1").exists() and (T / "s2").exists())
    for n in ("s1", "s2"):
        (T / n).unlink(missing_ok=True)
    raw2 = payloads["P2 quote breakout"]
    sh(f'python3 {SCRIPT} add-entry --kind coverage --needs re-run --finding "{raw2}" 2>/dev/null')
    expect_true("RED (argv): P2's quote breakout DID execute", (T / "s3").exists())
    (T / "s3").unlink(missing_ok=True)
    sh("cat <<'FLOWEOF'\n" + payloads["P3 heredoc delimiter collision"].replace("\\n", "\n") + "\nFLOWEOF\n")
    expect_true("RED (heredoc): P3's delimiter collision DID execute — v1.41.0's own first-attempt bug",
                (T / "s4").exists())
    (T / "s4").unlink(missing_ok=True)

    # ---- P8: assert on what a real LEAK would emit, never on a proxy (FB-0004) ----
    secret = T / "secret"
    secret.write_text("-----BEGIN OPENSSH PRIVATE KEY-----\nAAAAsecret\n", encoding="utf-8")
    link = T / "P8link"
    link.symlink_to(secret)
    r = add(str(link))
    expect("P8 symlink: exits 2", r.returncode, 2, r.stderr)
    expect_true("P8 symlink: the KEY SENTINEL appears in neither stdout nor stderr "
                "(an exit-code assertion is a proxy — a read-then-check impl would pass it)",
                "BEGIN OPENSSH PRIVATE KEY" not in (r.stdout + r.stderr), r.stdout + r.stderr)
    expect("P8 symlink: no manifest line emitted at all", r.stdout.strip(), "")

    # ---- the engine-side guard: the Write tool never ran (FB-0062) ----
    empty = T / "empty.txt"
    empty.write_text("", encoding="utf-8")
    r = add(str(empty))
    expect("an EMPTY finding file exits 2 (the Write never ran)", r.returncode, 2, r.stderr)
    expect("...and emits no manifest line", r.stdout.strip(), "")
    r = add(str(T / "does-not-exist.txt"))
    expect("a MISSING finding file exits 2", r.returncode, 2, r.stderr)
    r = add(str(T))
    expect("a DIRECTORY as --finding-file exits 2", r.returncode, 2, r.stderr)

    # ---- the removed argv flags: closed door, not an equal-status path ----
    for cmd, extra in (("add-entry --kind coverage --needs re-run", "--finding x"),
                       ("add-entry --kind coverage --needs re-run", "--resolution x"),
                       ("record-attempt --branch b --kind coverage", "--finding x"),
                       ("waive --branch b --kind coverage", "--finding x")):
        r = sh(f"python3 {SCRIPT} {cmd} {extra}")
        flag = extra.split()[0]
        expect(f"`{flag}` is REMOVED: {cmd.split()[0]} exits 2", r.returncode, 2, r.stdout + r.stderr)
        expect_true(f"...and the message names the replacement `{flag}-file`",
                    f"{flag}-file" in (r.stdout + r.stderr), r.stdout + r.stderr)

    # ---- P13: WRITE-side CWE-59. scratch-path unlinks rather than writing through ----
    victim = T / "victim"
    victim.write_text("DO NOT CLOBBER", encoding="utf-8")
    root = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                          capture_output=True, text=True).stdout.strip()
    planted = Path(root) / ".flow" / "evaltest-p13.txt"
    planted.parent.mkdir(parents=True, exist_ok=True)
    if planted.exists() or planted.is_symlink():
        planted.unlink()
    planted.symlink_to(victim)
    r = sh(f"python3 {SCRIPT} scratch-path --name evaltest-p13.txt")
    expect("P13 scratch-path: exits 0", r.returncode, 0, r.stderr)
    expect_true("P13: the planted SYMLINK is gone — unlinked, not written through",
                not planted.is_symlink())
    expect("P13: the victim file is BYTE-UNCHANGED", victim.read_text(), "DO NOT CLOBBER")
    expect("P13: the printed path is the engine-computed scratch path",
           r.stdout.strip(), str(planted))
    planted.unlink(missing_ok=True)
    r = sh(f"python3 {SCRIPT} scratch-path --name ../escape.txt")
    expect("scratch-path refuses a path-shaped --name", r.returncode, 2, r.stdout + r.stderr)

    # ---- waiver continuity: a waiver given BEFORE this change must still subtract ----
    # Pinned against a literal hex captured from the PRE-change tree. The argv form exits
    # 2 now, so it cannot be the live comparison target.
    expect("the canonical visual-deliverable fingerprint is UNCHANGED by this refactor",
           _fingerprint_of("visual-deliverable", "missing walkthrough"), "49070d421e4345de")
    expect("fingerprints are newline- and case-insensitive, so D4's collapse cannot move one",
           _fingerprint_of("coverage", "a b"), _fingerprint_of("coverage", "A\nB"))

def test_producer_lines() -> None:
    print("\n[contract] every producer prescribes the VALIDATED add-entry form — no templates")
    src = SHIP_SKILL.read_text(encoding="utf-8")

    # TIGHTENED (v1.42.0). This check used to accept EITHER an inline-code line template
    # or an `add-entry --kind X` invocation, "by design", with the conversion left as a
    # roadmap follow-up. Accepting both was the defect: Step 2's prose says "never
    # hand-compose the line" while the prescribed EXAMPLES showed a hand-composable line,
    # and the examples are what an agent copies (FB-0075 / FB-0074, two-places-one-contract).
    # All 13 template sites are now invocations, so the template form is FORBIDDEN outright.
    templates = re.findall(r"`(\[[a-z0-9|-]+\][^\n`]*?—\s*needs:[^\n`]*)`", src)
    expect("NEGATIVE: no producer prescribes a hand-composable manifest LINE any more",
           templates, [],
           "a rendered `[kind] … — needs: …` example is a line an agent will compose by "
           "hand — which bypasses --kind/--needs validation AND puts untrusted text back "
           "in a shell word. Prescribe `add-entry` instead.")

    # PAIRED with that negative (general.md rule 3): forbidding templates is satisfiable by
    # deleting every producer, so the positive half asserts the invocations exist, number
    # what they should, and cover every kind in the closed vocabulary.
    kinds_seen = set(re.findall(r"add-entry --kind ([a-z0-9-]+)", src))
    expect_true("POSITIVE: the producer invocations exist (the negative above is vacuous "
                "without this — deleting every producer would satisfy it)",
                len(re.findall(r"add-entry --kind", src)) >= 10,
                str(sorted(kinds_seen)))
    # Sourced from the ENGINE, never a hand-copied literal: `_load_triage`'s docstring
    # promises exactly this ("the SAME table the engine actually runs against"), and an
    # earlier revision of this check had pasted the 10 names in by hand — the drift this
    # whole PR is about, in the assertion policing it.
    expect("POSITIVE: every kind in the engine's KINDS is prescribed by an add-entry site",
           sorted(k for k in kinds_seen if not k.startswith("<")),
           sorted(_ENGINE.KINDS))

    # Every producer block must RESOLVE $TRIAGE. A skill `sh` block is potentially its own
    # Bash call, and an unset $TRIAGE expands to empty -> `python3 "" add-entry` -> the
    # entry is silently lost, which is the FB-0009 unset-is-fatal / FB-0010 silent-skip
    # shape at 16 new sites.
    for blk in re.findall(r"```sh\n.*?```", src, re.S):
        if '"$TRIAGE"' in blk:
            expect_true("every sh block using $TRIAGE also RESOLVES it (unset expands to "
                        "empty and the entry is silently lost)",
                        "TRIAGE=" in blk, blk[:200])

    # ============================ THE ALLOWLIST (FB-0100) ============================
    # BOTH HALVES, ONE CHECK, and now block-scoped so the universal actually quantifies
    # over every site. The universal alone is vacuously true at zero append sites, so on
    # its own DELETING THE PRODUCERS turns it green -- the FB-0077 shape. The positive half
    # is what makes it a check.
    #
    # An ALLOWLIST and not a denylist of bad spellings: assertions keyed on `--finding "`,
    # `--resolution "` or `<<` all pass for a hand-composed
    # `echo "[security] ... " >> "$MANIFEST"`, which is the actual residual hazard. Keying
    # on "what produces the append" fails closed on anything added later.
    #
    # SCOPE, stated because it is easy to over-read: a STATIC TEXT check over ship/SKILL.md
    # only. It cannot see an append composed in another file, one emitted by a script
    # SKILL.md invokes, or one built from a runtime variable. The class is closed for
    # ship/SKILL.md and nowhere else (roadmap § Next carries the widening).
    appending = _appending_blocks(src)
    expect_true("POSITIVE: at least one block appends to the manifest (the universal below "
                "is vacuous without this -- deleting every producer would satisfy it)",
                len(appending) >= 1, f"found {len(appending)}")
    for i, blk in enumerate(appending):
        kinds = re.findall(r"add-entry --kind ([a-z0-9<>-]+)", blk) or ["?"]
        expect_true(f"UNIVERSAL: the append in the `{kinds[0]}` block is produced by a "
                    f"manifest-triage subcommand (block {i + 1}/{len(appending)})",
                    bool(re.search(r'"\$TRIAGE" (?:add-entry|record-attempt|waive)', blk)),
                    "every block appending to the manifest path must be fed by "
                    "`manifest-triage.py <subcommand>` -- a hand-composed "
                    "`echo \"[kind] ...\" >>` bypasses --kind/--needs validation AND "
                    "re-opens the shell-injection path:\n" + blk[:300])

    # Per-block contract, all on the SAME boundary (three earlier loops each guessed a
    # different character window -- 600-back/900-fwd, 700-fwd, 900-back/500-fwd -- around
    # the same thing). The fence is the boundary; stop guessing.
    for blk in _producer_blocks(src):
        if not re.search(r'"\$TRIAGE" (?:add-entry|record-attempt|waive)', blk):
            continue
        cmd = re.search(r'"\$TRIAGE" (add-entry|record-attempt|waive)', blk).group(1)
        label = (re.findall(r"--kind ([a-z0-9<>-]+)", blk) or [cmd])[0]
        # `add-entry` PRINTS the line; it does not write it. A producer whose append is not
        # wired to the resolved manifest path emits to stdout, Step 7a.5 classifies an EMPTY
        # manifest, and the PR opens READY -- the precise failure every producer prevents.
        if cmd == "add-entry":
            expect_true(f"[{label}] the add-entry block redirects into the manifest file",
                        "manifest-path" in blk or "$MANIFEST" in blk, blk[:220])
        # FB-0062: a producer that cannot record its entry must STOP. add-entry exits 2 on
        # an unknown kind/verb, a missing/empty finding file (the Write never ran) or a
        # symlinked one; unchecked, the append silently does nothing.
        expect_true(f"[{label}] the {cmd} call checks its exit status (FB-0062 failure-open)",
                    "|| exit 1" in blk or "|| {" in blk or "exit 3 is NOT a failure" in blk,
                    blk[:220])
        # FB-0108: free text arrives as a path, and no heredoc -- a payload containing the
        # delimiter escapes it (v1.41.0's measured first-attempt failure).
        expect_true(f"[{label}] the {cmd} call names a --finding-file", "--finding-file" in blk,
                    blk[:220])
        expect(f"[{label}] no heredoc in this producer block (delimiter collision)",
               re.findall(r"<<-?'?\w", blk), [])
        # Every block that uses $TRIAGE must RESOLVE it: a skill `sh` block is potentially
        # its own Bash call, and an unset $TRIAGE expands to empty -> `python3 "" add-entry`
        # -> the entry is silently lost (FB-0009 unset-is-fatal at every new site).
        expect_true(f"[{label}] the block RESOLVES $TRIAGE (unset expands empty, entry lost)",
                    "TRIAGE=" in blk, blk[:220])

    # E: the allowlist's sub-case (a) — an append in ANOTHER file — is NOT beyond a static
    # check, so it should not be filed under "honest limit". Sweep every shipped SKILL.md
    # and assert ship/SKILL.md is the only one that appends to a manifest. Fails closed the
    # day a second producer file appears; the plan's stated reason for deferring it
    # ("ship-spike has no manifest today, grepped") is the author-memory grep general.md
    # § Consistency item 2 forbids relying on. Correct today is the point.
    skills_dir = HERE.parent / "skills"
    appenders = sorted(
        str(f.relative_to(HERE.parent))
        for f in skills_dir.rglob("SKILL.md")
        if _appending_blocks(f.read_text(encoding="utf-8"))
    )
    expect("ship/SKILL.md is the ONLY shipped skill that appends to the manifest "
           "(a second one would be outside the allowlist's reach)",
           appenders, ["skills/ship/SKILL.md"],
           "a new appending skill must either be added to this assertion WITH its own "
           "allowlist coverage, or it ships unguarded")

    # Every placeholder path a producer passes must be one `scratch-path --name` actually
    # RESOLVES. Not cosmetic: 12 of the converted blocks shipped referencing a bare
    # relative filename with no resolution call, so an agent copying the block verbatim
    # writes `security-finding.txt` into CWD (the repo root) — which (a) bypasses
    # `scratch-path`'s pre-Write unlink, the CWE-59 write-side defense a read-time check
    # provably cannot reach, and (b) lands OUTSIDE `.flow/.gitignore`, so Step 6's "stage
    # code + docs together" could COMMIT a raw reviewer finding. This turns "remember to
    # go run CALL 1" into a CI failure.
    ph = set(re.findall(r'--(?:finding|resolution)-file "<([a-z0-9-]+\.txt)>"', src))
    nm = set(re.findall(r"--name ([a-z0-9-]+\.txt)", src))
    expect_true("POSITIVE: producer blocks reference scratch placeholders at all",
                len(ph) >= 1, str(sorted(ph)))
    expect("every --finding-file/--resolution-file placeholder is resolved by a "
           "`scratch-path --name` in the same file", sorted(ph - nm), [],
           "an unresolved placeholder is a bare relative path: it lands in CWD, skips the "
           "write-side symlink unlink, and is not gitignored")
    # The resolution must be ADJACENT to the call that consumes it — the CALL 1 block that
    # `--name`s a slug must be one of the two blocks immediately preceding the CALL 2 block
    # that passes it. NOT "in the same block": the Write tool runs between them and a Write
    # cannot happen inside a shell block, so a single-block form can never succeed (it
    # shipped that way for one revision and the extracted-execution test in
    # run_scratch_isolation_evals.py caught it). Adjacency is the real contract — it is what
    # keeps the resolution out of a distant template (FB-0075) without demanding an
    # impossible shape.
    blks = _producer_blocks(src)
    for i, blk in enumerate(blks):
        blk_ph = re.findall(r'--(?:finding|resolution)-file "<([a-z0-9-]+\.txt)>"', blk)
        if not blk_ph:
            continue
        near = set()
        for prev in blks[max(0, i - 2):i + 1]:
            near |= set(re.findall(r"--name ([a-z0-9-]+\.txt)", prev))
        label = (re.findall(r"--kind ([a-z0-9<>-]+)", blk) or ["?"])[0]
        expect(f"[{label}] its scratch paths are resolved in an ADJACENT CALL-1 block, not a "
               f"distant template", sorted(set(blk_ph) - near), [], blk[:260])

    # Distinct scratch slugs. `record-attempt` and `add-entry` at the visual-deliverable
    # site pass deliberately DIFFERENT text whose fingerprints must not collapse —
    # classify() reads `fp in attempted_fps` to pick the entry's class, so one shared
    # path would silently change a verdict.
    slugs = re.findall(r"--name ([a-z0-9-]+\.txt)", src)
    expect_true("POSITIVE: producer sites request scratch paths by slug", len(slugs) >= 1, str(slugs))
    expect("no two producer sites share a scratch slug (fingerprint collapse)",
           sorted(set(slugs)), sorted(slugs), str(slugs))

    expect_true("the toolchain producer prescribes the VALIDATED write path, not a template line",
                "add-entry --kind toolchain" in src,
                "Step 2a.3 must spell the literal `add-entry --kind toolchain`")

    # The anchored grep the plan gates demanded: no prescribed manifest line may
    # still OPEN with the confidence axis where the kind token belongs. A bare
    # grep for [decision-required] always returns axis-prose survivors, so it can
    # only be adjudicated by author memory — this one can actually fail.
    bad = re.findall(r"^\s*`?- \[decision-required\]", src, re.M)
    expect("no producer line still opens with [decision-required] where a kind belongs",
           bad, [])
    bad2 = re.findall(r"`\[decision-required\][^\n`]*—\s*needs:", src)
    expect("no inline template opens with [decision-required] either", bad2, [])


def test_skill_contract() -> None:
    print("\n[contract] the ship SKILL prescribes the step, the ordering, and the surfaces")
    src = SHIP_SKILL.read_text(encoding="utf-8")

    i_7a = src.index("### 7a. Visual-deliverable gate")
    i_745 = src.index("### 7a.5. Manifest triage")
    i_draft = src.index("**Draft decision (mechanical):**")
    i_7b = src.index("### 7b.")
    expect_true("§7a.5 exists and sits between §7a and §7b", i_7a < i_745 < i_7b, "section order")
    expect_true("the draft decision comes after §7a.5's classification", i_745 < i_draft, "draft decision order")
    window = src[i_draft:i_draft + 700]
    expect_true("the draft decision keys on the triage verdict, not manifest emptiness",
                "verdict" in window and "not manifest emptiness" in window, window[:300])
    # The predicate is restated at the two create/re-ship sites; both must key on
    # the verdict too (FB-0010 — a predicate asserted in prose at four sites is
    # how two of them get migrated and two do not).
    # Broad enough to actually fail: any prose in the create / read-back /
    # PR-OPEN region that gates draft state on the manifest being (non-)empty.
    # The previous version pinned two exact literals — the two already fixed —
    # and therefore passed vacuously against four survivors.
    region = src[src.index("### 7a.6. Create the PR"):src.index("### 7b.")]
    bad = re.findall(r"(?:manifest (?:is )?(?:now )?(?:still )?(?:non-)?empty|"
                     r"\(empty manifest\)|\(non-empty manifest\))", region)
    expect("no site in the create/read-back/PR-OPEN region gates draft state on manifest emptiness",
           [b for b in bad if "not on manifest emptiness" not in region[max(0, region.find(b) - 90):region.find(b) + 90]],
           [])

    # §7a's ordered sequence: apply -> commit -> push -> re-run -> re-apply accounting -> re-assert
    seq = src[i_7a:i_745]
    order = [seq.index(tok) for tok in ("**Apply**", "**Commit**", "**Push**", "**Re-run**",
                                        "**Re-apply Step 2's verify-build accounting",
                                        "**Re-assert**")]
    expect("§7a's resolution sequence is apply→commit→push→re-run→re-account→re-assert",
           order, sorted(order), seq[:200])
    expect_true("§7a re-applies the verdict accounting (its own assertion is artifact-shaped)",
                "never reads `overall_verdict`" in seq, "missing the artifact-shaped warning")
    expect_true("§7a's attempt is bounded to one", "**Attempt ONCE.**" in seq, seq[:200])
    expect_true("a failed attempt demotes to ask, not to a silent draft",
                "demotes to `ask`" in src[i_745:i_7b], "missing demote-to-ask")

    # No halt before the PR (FB-0034 / FB-0044).
    triage = src[i_745:i_7b]
    expect_true("§7a.5 states it never halts before the PR",
                "NEVER halts before the PR" in triage, triage[:200])
    expect_true("and cites the two-gate doctrine it is preserving",
                "FB-0034" in triage and "FB-0044" in triage, triage[:200])

    # §7c: step 0 body read precedes the recompute and the body write.
    i_7c = src.index("### 7c. Reconcile-only fast-path")
    i_8 = src.index("## 8. Hand off")
    rec = src[i_7c:i_8]
    i_step0 = rec.index("0. **Fetch and parse the live PR body FIRST**")
    i_step1 = rec.index("1. Recompute the draft manifest")
    i_step2 = rec.index("2. Re-render the body")
    expect_true("§7c step 0 (body fetch) precedes the recompute and the body write",
                i_step0 < i_step1 < i_step2, "7c step order")
    expect_true("§7c step 1 subtracts recorded waivers", "subtract recorded waivers" in rec, rec[:200])
    expect_true("§7c step 1 requires an exact fingerprint match",
                "exact `(kind, finding)` fingerprint match" in rec, rec[:200])
    expect_true("§7c step 3 keys the ready-flip on the VERDICT, not manifest emptiness",
                "keyed on the triage `verdict`, not on manifest emptiness" in rec, rec[:200])
    expect_true("§7c step 5 re-emits the decision list on a partial answer",
                "re-emit the decision list" in rec, rec[:200])

    # Step 8: decisions lead, and answering routes through 7c.
    handoff = src[i_8:i_8 + 3000]
    expect_true("Step 8 leads with the decisions, never a bare PR URL",
                "LEAD WITH THE DECISIONS — never a bare PR URL" in handoff, handoff[:200])
    expect_true("Step 8 routes an answer through the Step 7c reconcile fast-path",
                "Step 7c reconcile fast-path" in handoff, handoff[:200])

    # The waived-at-ship section has a producer.
    expect_true("the body template prescribes a `## Waived at ship` section",
                "## Waived at ship" in src, "no Waived at ship section in SKILL.md")
    expect_true("the manifest block is rendered, not hand-authored",
                "Do NOT hand-author this block — render it" in src, "manifest block still hand-authored")


def test_reviewer_prose() -> None:
    print("\n[contract] the two reviewer skills route to triage, and 149 keeps its invariant")
    sec = SEC_SKILL.read_text(encoding="utf-8")
    a11y = A11Y_SKILL.read_text(encoding="utf-8")
    # The clause a naive find/replace would have deleted — it is the FB-0034
    # invariant this PR pledges to preserve.
    expect_true("security-review keeps '; ship never silently proceeds past it and never hard-halts the loop'",
                "ship never silently proceeds past it and never hard-halts the loop" in sec,
                "the FB-0034 invariant clause was dropped from security-review/SKILL.md")
    for name, txt in (("security-review", sec), ("accessibility-review", a11y)):
        expect_true(f"{name} routes to the triage step, not 'consumed at Step 7'",
                    "Step 7a.5" in txt and "consumed at Step 7." not in txt, txt[:200])


def test_sibling_dependency(td: str) -> None:
    print("\n[dependency] a missing manifest_contract.py is DETECTED, not crashed on")
    # pr-coherence.py now imports manifest_contract. On a stale/partial plugin dir
    # (every consumer, until they update) the import fails -- and land/doctor
    # redirect stderr, so a bare crash would read as "manifest present" and produce
    # a false merged-in-a-not-ready-state BLOCKER. verify-pr-body.sh's resolver
    # therefore requires the sibling before it will name pr-coherence.py at all.
    lib = Path(td) / "lib"
    lib.mkdir(exist_ok=True)
    (lib / "pr-coherence.py").write_text(
        (HERE.parent / "skills" / "ship" / "lib" / "pr-coherence.py").read_text(encoding="utf-8"),
        encoding="utf-8")
    body = Path(td) / "b.md"
    body.write_text("## Summary\nclean\n", encoding="utf-8")

    proc = subprocess.run(
        [sys.executable, str(lib / "pr-coherence.py"), "coherence",
         "--body-file", str(body), "--is-draft", "false"],
        capture_output=True, text=True)
    expect_true("without the sibling, pr-coherence.py fails LOUD (non-zero) rather than "
                "silently reporting a verdict", proc.returncode != 0,
                proc.stdout + proc.stderr)
    expect_true("…and names the missing module so the cause is diagnosable",
                "manifest_contract" in (proc.stdout + proc.stderr), proc.stdout + proc.stderr)

    sh = (HERE.parent / "skills" / "ship" / "lib" / "verify-pr-body.sh").read_text(encoding="utf-8")
    # Assert each GUARD branch, not a raw occurrence count: the count includes the
    # explanatory comment, so `>= 2` stayed green if you deleted the
    # CLAUDE_PLUGIN_ROOT guard — the exact branch a consumer install depends on.
    guards = re.findall(r'\[ -f "[^"]*manifest_contract\.py" \]', sh)
    expect("verify-pr-body.sh guards BOTH resolution branches on manifest_contract.py "
           "(plugin-installed and in-repo), so a partial install is 'unresolvable' "
           "rather than read as 'manifest present'", len(guards), 2, "\n".join(guards))


def test_render_coherence(td: str) -> None:
    print("\n[FB-0067] the rendered manifest stays coherent with pr-coherence.py")
    st = fresh_state(td, "coh")
    b = body(line("coverage", "5 undeclared behaviors", "declare + fence"))
    ef = Path(td) / "e.md"
    ef.write_text(b, encoding="utf-8")
    rc, out = run(["render-manifest", "--entries-file", str(ef),
                   "--state-file", str(st), "--branch", "coh"])
    expect("render-manifest exits 0", rc, 0, out)
    expect_true("the 🚫 sentinel is byte-preserved", "🚫 NOT READY TO MERGE" in out, out)
    expect_true("both fences are byte-preserved",
                "<!-- flow:not-ready-manifest -->" in out and "<!-- /flow:not-ready-manifest -->" in out, out)
    expect_true("the machine `confidence:` axis is NOT printed at the human",
                "confidence:" not in out, out)
    expect_true("the plain-language framing is present per entry",
                all(t in out for t in ("What this means", "What I need from you")), out)
    # "What happens then" is stated once in the trailer and per-entry ONLY where it
    # differs from the default — most kinds share one sentence, and
    # repeating it verbatim is what made the block a wall at scale.
    expect("the default 'what happens then' is stated exactly once",
           out.count("What happens when you answer"), 1)

    rendered = Path(td) / "rendered.md"
    rendered.write_text(out, encoding="utf-8")
    for is_draft, want in (("true", 0), ("false", 1)):
        proc = subprocess.run(
            [sys.executable, str(COHERENCE), "coherence", "--body-file", str(rendered),
             "--is-draft", is_draft], capture_output=True, text=True)
        expect(f"pr-coherence on the rendered block, --is-draft {is_draft} ⇒ exit {want}",
               proc.returncode, want, proc.stdout + proc.stderr)


def test_fixture_normalized() -> None:
    print("\n[fixture] resolution-confidence-routing pins the NORMALIZED line shape")
    if not FIXTURE.exists():
        expect("the routing fixture exists", False, True, str(FIXTURE))
        return
    text = FIXTURE.read_text(encoding="utf-8")
    with tempfile.TemporaryDirectory() as td:
        f = Path(td) / "fx.md"
        f.write_text(text, encoding="utf-8")
        rc, out = run(["parse", "--body-file", str(f)])
    expect("the fixture's manifest block parses", rc, 0, out)
    entries = json.loads(out)["entries"]
    expect_true("it yields at least one entry", len(entries) >= 1, out)
    for e in entries:
        expect_true(f"fixture entry [{e['kind']}] carries an in-vocabulary needs verb",
                    e["needs"] in (
                        "secret rotation", "design decision", "dep vetting", "regression fix",
                        "re-run", "reconcile", "declare + fence", "hand-author", "human-waive"),
                    json.dumps(e))
    # The fixture pins BOTH shapes, and they legitimately differ: the manifest
    # *file* line carries the machine `confidence:` axis; the rendered PR-body
    # block does not (it is metadata, and printing it at the reader is the jargon
    # this block removes). Assert each where it belongs.
    # `parse` deliberately scopes to the fences, so it sees only the rendered
    # PR-body block; the manifest-FILE line sits outside them. Assert that one on
    # the text.
    expect_true("the manifest-file line carries the machine confidence axis",
                re.search(r"^- \[[a-z-]+\].*— confidence: (auto-fixable|decision-required)", text, re.M)
                is not None, text[:300])
    expect_true("the rendered PR-body block carries the plain-language framing instead",
                "**What this means:**" in text and "**What I need from you:**" in text, text[:300])


def test_malformed() -> None:
    print("\n[robustness] malformed input never yields a false clean")
    rc, out = run(["parse", "--body-file", "/no/such/file.md"])
    expect_true("a missing body file is a loud failure, not an empty parse", rc != 0, out)
    with tempfile.TemporaryDirectory() as td:
        f = Path(td) / "empty.md"
        f.write_text("", encoding="utf-8")
        rc, out = run(["parse", "--body-file", str(f)])
        expect("an empty body parses to zero entries without crashing", rc, 0, out)
        expect("zero entries", json.loads(out)["entries"], [])
        f.write_text("just some prose with no manifest at all\n", encoding="utf-8")
        rc, out = run(["parse", "--body-file", str(f)])
        expect("prose with no manifest ⇒ zero entries", json.loads(out)["entries"], [])


def main() -> int:
    print("manifest-triage evals (FB-0075)")
    with tempfile.TemporaryDirectory() as td:
        test_table(td)
        test_failsafes(td)
        test_add_entry(td)
        test_injection(td)
        test_manifest_lifecycle(td)
        test_prescribed_sequence(td)
        test_auto_renders_as_question(td)
        test_state_durability(td)
        test_attempt_demotion(td)
        test_residual_definition(td)
        test_verify_build_invariant(td)
        test_waiver_fingerprint(td)
        test_clears_when(td)
        test_render_coherence(td)
        test_sibling_dependency(td)
        test_toolchain_kind(td)
    test_producer_lines()
    test_skill_contract()
    test_reviewer_prose()
    test_fixture_normalized()
    test_malformed()

    print()
    if _failures:
        print(f"FAILED: {len(_failures)} eval(s): {', '.join(_failures)}")
        return 1
    print("All manifest-triage evals passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
