#!/usr/bin/env python3
"""Eval harness for manifest-triage.py — the deterministic draft-manifest triage
engine behind FB-0074 (a draft PR is a last resort, not a deliverable).

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

Also pins the producer-line contract: every one of the 8 producer sites' real
prescribed line must round-trip through `parse` yielding a kind, an in-vocabulary
verb, and a confidence value — and the rendered manifest must stay coherent with
lib/pr-coherence.py (the FB-0067 invariant this must not disturb).

Stdlib only. No git/gh dependency.
"""

from __future__ import annotations

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


def expect(label: str, got, want, ctx: str = "") -> None:
    if got == want:
        print(f"  PASS  {label}")
    else:
        print(f"  FAIL  {label}\n        got={got!r} want={want!r}\n        {ctx[:400]}")
        _failures.append(label)


def expect_true(label: str, cond: bool, ctx: str = "") -> None:
    expect(label, bool(cond), True, ctx)


def run(args: list[str]) -> tuple[int, str]:
    proc = subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True)
    return proc.returncode, proc.stdout + proc.stderr


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
    ("status-surface", "reconcile", "ask", "never silently rewrite an un-fenced doc (SKILL.md:585)"),
    ("security", "design decision", "ask", "competing valid fixes escalate (FB-0011)"),
    ("a11y", "design decision", "ask", "competing valid fixes escalate (FB-0011)"),
    ("security", "secret rotation", "blocked", "out-of-session human action"),
    ("security", "dep vetting", "blocked", "out-of-session human action"),
    ("a11y", "dep vetting", "blocked", "out-of-session human action"),
]


def test_table(td: str) -> None:
    print("\n[table] classification, one case per row")
    st = fresh_state(td)
    for kind, verb, want, note in TABLE_CASES:
        r = classify(body(line(kind, "some finding", verb)), st)
        expect(f"{kind} + '{verb}' ⇒ {want}  ({note})", by_kind(r, kind)["class"], want)


def test_failsafes(td: str) -> None:
    print("\n[fail-safe] unrecognized verb never yields auto")
    st = fresh_state(td)
    r = classify(body(line("security", "odd finding", "frobnicate")), st)
    expect("security + off-vocabulary verb ⇒ blocked (the dangerous mis-class)",
           by_kind(r, "security")["class"], "blocked")
    r = classify(body(line("a11y", "odd finding", "frobnicate")), st)
    expect("a11y + off-vocabulary verb ⇒ blocked", by_kind(r, "a11y")["class"], "blocked")
    r = classify(body(line("coverage", "odd finding", "frobnicate")), st)
    expect("coverage + off-vocabulary verb ⇒ ask (never blocked, never auto)",
           by_kind(r, "coverage")["class"], "ask")
    r = classify(body(line("made-up-kind", "odd finding", "re-run")), st)
    expect("unrecognized KIND ⇒ ask, never auto, never dropped",
           by_kind(r, "made-up-kind")["class"], "ask")
    expect("unrecognized kind is still counted", len(r["entries"]), 1)
    # No case anywhere may produce auto for a non-visual-deliverable kind.
    autos = set()
    for kind, verb, _, _ in TABLE_CASES:
        r = classify(body(line(kind, "f", verb)), st)
        if by_kind(r, kind)["class"] == "auto":
            autos.add(kind)
    expect("visual-deliverable is the ONLY auto-class kind", autos, {"visual-deliverable"})


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
                   "--kind", "visual-deliverable", "--finding", "missing walkthrough"])
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
         "--kind", "coverage", "--finding", "5 undeclared behaviors"])
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
         "--kind", "verify-build", "--finding", "criterion 3 FAIL"])
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
         "--kind", "coverage", "--finding", "5 undeclared behaviors"])
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
                "skip-audit", "status-surface", "visual-deliverable")])
    r = classify(b, st)
    expect("every kind carries a clears_when re-check",
           all(e.get("clears_when") for e in r["entries"]), True)
    expect_true("no output field can express 'cleared'",
                "cleared" not in json.dumps(r), "found a 'cleared' key/value in classify output")


def test_producer_lines() -> None:
    print("\n[contract] all 8 producer sites round-trip through parse")
    src = SHIP_SKILL.read_text(encoding="utf-8")
    # Producer sites write the line as an inline-code TEMPLATE (no leading "- ");
    # the dash appears when it is rendered into the PR body. Normalize the template
    # to a rendered line so the strict parser is exercised on the real text.
    templates = re.findall(r"`(\[[a-z0-9|-]+\][^\n`]*?—\s*needs:[^\n`]*)`", src)
    expect_true("at least 8 prescribed producer lines found in SKILL.md",
                len(templates) >= 8, f"found {len(templates)}")

    kinds_seen: set[str] = set()
    for tpl in templates:
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "l.md"
            f.write_text("- " + tpl, encoding="utf-8")
            rc, out = run(["parse", "--body-file", str(f)])
        expect_true(f"prescribed line parses: {tpl[:48]}…", rc == 0, out)
        for e in json.loads(out)["entries"]:
            # A template may name an alternation, e.g. [security|a11y].
            for k in e["kind"].split("|"):
                kinds_seen.add(k)
            expect_true(f"[{e['kind']}] template carries a confidence slot",
                        bool(e["confidence"]), json.dumps(e))

    expect("every one of the 8 kinds is prescribed by a producer site",
           sorted(kinds_seen),
           ["a11y", "coverage", "rigor", "security", "skip-audit",
            "status-surface", "verify-build", "visual-deliverable"])

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
    i_7b = src.index("### 7b. Body↔draft coherence invariant")
    expect_true("§7a.5 exists and sits between §7a and §7b", i_7a < i_745 < i_7b, "section order")
    expect_true("the draft decision comes after §7a.5's classification", i_745 < i_draft, "draft decision order")
    expect_true("the draft decision reads the RESIDUAL set, not the raw manifest",
                "residual" in src[i_draft:i_draft + 400], src[i_draft:i_draft + 300])

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
    expect_true("the plain-language triple is present",
                all(s in out for s in ("What this means", "What I need from you", "What happens then")), out)

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
        expect_true(f"fixture entry [{e['kind']}] carries a confidence value",
                    e["confidence"] in ("auto-fixable", "decision-required"), json.dumps(e))


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
    print("manifest-triage evals (FB-0074)")
    with tempfile.TemporaryDirectory() as td:
        test_table(td)
        test_failsafes(td)
        test_state_durability(td)
        test_attempt_demotion(td)
        test_residual_definition(td)
        test_verify_build_invariant(td)
        test_waiver_fingerprint(td)
        test_clears_when(td)
        test_render_coherence(td)
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
