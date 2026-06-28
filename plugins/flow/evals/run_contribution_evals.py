#!/usr/bin/env python3
"""Eval harness for the lesson-harvest + contribute-back-to-flow loop (FB-0059).

Pins the DETERMINISTIC behaviors of the contribution scripts plus the
SKILL/ship/schema contracts. The analyzer's routing (project-local vs
flow-generalizable) and noise judgment are best-effort LLM work — NOT pinned
here; only the prescan cost-gate, the score math, the dedup/idempotency, the
fail-closed sanitizer, and the prose contracts are deterministic. Assertion-
based (exit-code + stdout/stderr substring), stdlib only.

Run: python3 plugins/flow/evals/run_contribution_evals.py

Storage is redirected to a tempdir via FLOW_CONTRIB_DIR so the harness never
touches real user-scope data.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).parent
SCRIPTS = HERE.parent / "scripts"
STORE = SCRIPTS / "contribution_store.py"
SANITIZE = SCRIPTS / "sanitize_tokens.py"
HARVEST = SCRIPTS / "harvest_lesson.py"
SHIP_SKILL = HERE.parent / "skills" / "ship" / "SKILL.md"
CONTRIB_SKILL = HERE.parent / "skills" / "contribute" / "SKILL.md"
DOCTOR_SKILL = HERE.parent / "skills" / "doctor" / "SKILL.md"
SCHEMA = HERE.parent / "schema" / "flow.config.schema.json"
EXTRACT = SCRIPTS / "extract_session.py"
FIX = HERE / "fixtures"

# Import the store in-process to compute hashes / scores deterministically.
sys.path.insert(0, str(SCRIPTS))
import contribution_store as store  # noqa: E402

fails = 0


def check(cid, ok, detail=""):
    global fails
    if ok:
        print(f"PASS  [{cid}]")
    else:
        fails += 1
        print(f"FAIL  [{cid}]" + (f"  — {detail}" if detail else ""))


def run(script, args, env_dir, stdin=None, cwd=None):
    env = dict(os.environ)
    env["FLOW_CONTRIB_DIR"] = str(env_dir)
    proc = subprocess.run(
        [sys.executable, str(script), *args],
        input=stdin, capture_output=True, text=True, check=False,
        cwd=cwd, env=env,
    )
    return proc.returncode, proc.stdout, proc.stderr


def enqueue(env_dir, session, summary, rule, src="taste",
            kind="reviewer-prompt", ev="direct-quote", project="acme",
            marker=None):
    return run(HARVEST, [
        "enqueue", "--session-file", str(session),
        "--marker-file", str(marker or (env_dir / "mark.json")),
        "--project-slug", project, "--source-type", src,
        "--artifact-kind", kind, "--summary", summary, "--rule", rule,
        "--evidence-strength", ev,
    ], env_dir)


def main() -> int:
    # ---------- script behaviors (subprocess, redirected storage) ----------
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)

        # --- prescan 1: cost gate trips on signal, clean on noise ----------
        rc, out, _ = run(HARVEST, [
            "prescan", "--session-file", str(FIX / "contribution_flow_generalizable.jsonl"),
            "--marker-file", str(d / "m_fg.json")], d / "c1")
        check("prescan-1-signal", rc == 0 and "signal=yes" in out, f"rc={rc} out={out!r}")
        rc, out, _ = run(HARVEST, [
            "prescan", "--session-file", str(FIX / "contribution_noise.jsonl"),
            "--marker-file", str(d / "m_noise.json")], d / "c2")
        check("prescan-2-noise", rc == 1 and "signal=no" in out, f"rc={rc} out={out!r}")
        # project-local fixture still has signal (routing is LLM, not pinned here)
        rc, out, _ = run(HARVEST, [
            "prescan", "--session-file", str(FIX / "contribution_project_local.jsonl"),
            "--marker-file", str(d / "m_pl.json")], d / "c3")
        check("prescan-3-local-has-signal", rc == 0 and "signal=yes" in out)

        # --- enqueue 1: idempotency on same (session, lesson) --------------
        env1 = d / "e1"
        s = FIX / "contribution_flow_generalizable.jsonl"
        enqueue(env1, s, "plan-critic over-flags renames", "rename fan-out is not scope drift")
        enqueue(env1, s, "plan-critic over-flags renames", "rename fan-out is not scope drift")
        rc, out, _ = run(STORE, ["list"], env1)
        entries = json.loads(out)
        check("enqueue-1-idempotent", rc == 0 and len(entries) == 1,
              f"expected 1 entry, got {len(entries)}")
        check("enqueue-1-recurrence-same-session",
              entries and entries[0]["signals"]["recurrence_count"] == 1,
              "same session must NOT bump recurrence")

        # --- enqueue 2: recurrence across different sessions ---------------
        env2 = d / "e2"
        s2 = d / "other_session.jsonl"
        s2.write_text(s.read_text())  # same content, different filename → diff session id
        enqueue(env2, s, "plan-critic over-flags renames", "rename fan-out is not scope drift")
        enqueue(env2, s2, "plan-critic over-flags renames", "rename fan-out is not scope drift")
        rc, out, _ = run(STORE, ["list"], env2)
        entries = json.loads(out)
        check("enqueue-2-recurrence-cross-session",
              len(entries) == 1 and entries[0]["signals"]["recurrence_count"] == 2,
              f"expected 1 entry w/ recurrence 2, got {entries!r}")

        # --- set-status: a proposed entry drops out of the drain -----------
        env_ss = d / "ess"
        enqueue(env_ss, s, "lesson ss", "rule ss")
        eid = json.loads(run(STORE, ["list"], env_ss)[1])[0]["id"]
        run(STORE, ["set-status", "--id", eid, "--status", "proposed"], env_ss)
        rc, out, _ = run(STORE, ["list"], env_ss)
        check("set-status-1-drops-from-drain", json.loads(out) == [],
              "a proposed entry must not appear in the drain list")

        # --- dedup: dismissed hash → exit 3; novel → exit 0 ----------------
        env3 = d / "e3"
        lh = store.lesson_hash("x", "some rule", "fb-entry")
        run(STORE, ["dismiss", "--lesson-hash", lh, "--reason", "already-encoded"], env3)
        rc, _, err = run(STORE, ["dedup", "--lesson-hash", lh], env3)
        check("dedup-1-dismissed", rc == 3 and "dismissed" in err, f"rc={rc} err={err!r}")
        rc, out, _ = run(STORE, ["dedup", "--lesson-hash", "sha256:nope"], env3)
        check("dedup-2-novel", rc == 0 and "novel" in out)

        # --- calibrate: appends an event the auto-merge gate trains on -----
        env4 = d / "e4"
        run(STORE, ["calibrate", "--lesson-hash", lh, "--confidence", "0.9",
                    "--decision", "approved", "--artifact-kind", "fb-entry"], env4)
        sig = json.loads((env4 / "feedback_signals.json").read_text())
        check("calibrate-1-event",
              len(sig["events"]) == 1 and sig["events"][0]["human_decision"] == "approved")

        # --- known-tokens: harvest records origin tokens for scrubbing -----
        env5 = d / "e5"
        enqueue(env5, s, "lesson five", "rule five", project="pattaya")
        rc, out, _ = run(STORE, ["known-tokens"], env5)
        check("known-tokens-1-recorded", "pattaya" in out)

        # --- sanitize: scan catches each class; scrub neutralizes ----------
        dirty = (FIX / "contribution_dirty_window.jsonl").read_text()
        rc, _, err = run(SANITIZE, ["scan", "--project-token", "pattaya"], d, stdin=dirty)
        leak_classes = {"home-path", "url", "email", "design-token", "project-token"}
        check("sanitize-1-scan-fails-closed",
              rc == 1 and any(c in err for c in leak_classes), f"rc={rc} err={err!r}")
        rc, scrubbed, _ = run(SANITIZE, ["scrub", "--project-token", "pattaya"], d, stdin=dirty)
        rc2, out2, _ = run(SANITIZE, ["scan", "--project-token", "pattaya"], d, stdin=scrubbed)
        check("sanitize-2-scrub-then-clean", rc2 == 0 and "clean" in out2,
              f"rc2={rc2} scrubbed={scrubbed!r}")
        # derived/compound identifier from a slug must be caught (security BLOCKER, FB-0059)
        derived = 'I updated HealthPulseCore and healthpulse_db init'
        rc, _, err = run(SANITIZE, ["scan", "--project-token", "healthpulse"], d, stdin=derived)
        check("sanitize-4-derived-identifier-caught", rc == 1 and "project-token" in err,
              f"a 'healthpulse' slug must flag 'HealthPulseCore' (substring); rc={rc} err={err!r}")
        rc, scrub2, _ = run(SANITIZE, ["scrub", "--project-token", "healthpulse"], d, stdin=derived)
        check("sanitize-4-derived-scrubbed",
              "HealthPulse" not in scrub2 and "healthpulse" not in scrub2.lower(),
              f"derived forms must be scrubbed; got {scrub2!r}")

        check("sanitize-3-no-brand-literals-shipped",
              "pattaya" not in SANITIZE.read_text() and "Geist" not in SANITIZE.read_text()
              and "sand-" not in SANITIZE.read_text(),
              "sanitize_tokens.py must embed no project/brand literals (CLAUDE.md:126)")

    # ---------- score math (in-process, deterministic) ----------
    lo = store.compute_confidence({"source_type": "feedback", "evidence_strength": "inferred"})
    hi = store.compute_confidence({"source_type": "taste", "evidence_strength": "direct-quote",
                                   "recurrence_count": 3})
    check("score-1-monotonic", lo < hi, f"lo={lo} hi={hi}")
    check("score-2-bounded", 0.0 <= lo <= 1.0 and 0.0 <= hi <= 1.0, f"lo={lo} hi={hi}")
    check("score-3-below-threshold-not-promoted", lo < 0.6,
          f"a weak (feedback/inferred) lesson must fall below a default 0.6 bar; lo={lo}")
    dirty_s = store.compute_confidence({"source_type": "taste", "evidence_strength": "direct-quote",
                                        "sanitization_clean": False})
    clean_s = store.compute_confidence({"source_type": "taste", "evidence_strength": "direct-quote",
                                        "sanitization_clean": True})
    check("score-4-dirty-penalized", dirty_s < clean_s, f"dirty={dirty_s} clean={clean_s}")

    # ---------- contract checks (read deployed surfaces) ----------
    ship = SHIP_SKILL.read_text()
    check("ship-1-step-4c", "4c" in ship and "harvest" in ship.lower())
    check("ship-1-prescan-gate", "prescan" in ship and "harvest_lesson.py" in ship)
    check("ship-1-routing-contract",
          "flow-generalizable" in ship.lower() and "project-local" in ship.lower())
    check("ship-1-noise-filter", "noise" in ship.lower() and "confidence" in ship.lower())

    if CONTRIB_SKILL.is_file():
        cs = CONTRIB_SKILL.read_text()
        check("contribute-1-drains-both",
              "disagreement" in cs.lower() and "queue" in cs.lower(),
              "must drain BOTH the queue and the existing disagreements store")
        check("contribute-2-sanitize-failclosed",
              "sanitize_tokens.py" in cs and "needs-manual-scrub" in cs.lower()
              or "needs human" in cs.lower())
        check("contribute-3-draft-pr", "draft" in cs.lower() and "never merge" in cs.lower())
        check("contribute-4-calibrate-from-pr",
              "calibrate" in cs.lower() and ("merged" in cs.lower() or "outcome" in cs.lower()))
        check("contribute-5-flow-repo-guard", "flowRepoPath" in cs)
    else:
        check("contribute-1-skill-exists", False, f"{CONTRIB_SKILL} missing")

    # doctor: contribution slot check present
    if DOCTOR_SKILL.is_file():
        doc = DOCTOR_SKILL.read_text()
        check("doctor-1-contribution-check",
              "flowRepoPath" in doc and "contribution" in doc.lower())

    # schema: the 4 new slots
    try:
        schema = json.loads(SCHEMA.read_text())
        props = schema["properties"]
        for slot in ("flowRepoPath", "contributionsQueuePath", "lastHarvestedPath",
                     "contributionThreshold"):
            check(f"slot-{slot}", slot in props, f"{slot} missing from schema")
    except (OSError, ValueError, KeyError) as e:
        check("slot-schema", False, str(e))

    # extract_session: harvest helper added; --mode CLI contract unchanged
    es = EXTRACT.read_text()
    check("extract-1-harvest-helper", "harvest_dialogue" in es)
    rc = subprocess.run([sys.executable, str(EXTRACT), "--mode", "harvest"],
                        capture_output=True, text=True).returncode
    check("extract-2-mode-contract-unchanged", rc != 0,
          "--mode harvest must NOT be accepted (plan|completion CLI is untouched)")

    total_marker = "passed" if fails == 0 else "FAILED"
    print(f"\n{total_marker}: {fails} failing check(s)")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
