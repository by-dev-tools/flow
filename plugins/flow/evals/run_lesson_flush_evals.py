#!/usr/bin/env python3
"""Regression evals for `harvest_lesson.py flush` (FB-0102).

The flush exists because the contribution queue lives in user-scope storage that
does NOT survive an ephemeral cloud workspace. These checks pin the properties
that make it safe to run inside the ship pipeline:

  1. It never crashes the ship on a missing/empty/corrupt queue.
  2. It writes FULL records to the repo-local out-dir (no size ceiling there).
  3. The PR-body manifest stays BOUNDED -- the whole point of the split, since
     inline full records overflow GitHub's 65,536-char body cap at ~37 records.
  4. It redacts the absolute window path (a machine path) and never emits the
     raw transcript window.

Each negative assertion is paired with the positive assertion of the thing it
protects, per .claude/rules/general.md § "Prohibition satisfiable by deletion".
"""
import json
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "scripts", "harvest_lesson.py")
FLUSH_BEGIN = "<!-- flow:lesson-flush:begin -->"
FLUSH_END = "<!-- flow:lesson-flush:end -->"
BODY_LIMIT = 65536  # GitHub PR body cap (documented)
# A real body is NOT empty when the manifest lands -- PR #140's was 5,534 B before any
# manifest (dev-docs/history.md). Assert against realistic headroom, not the bare cap.
BODY_HEADROOM = BODY_LIMIT - 8192

FAILURES = []


def check(name, cond, detail=""):
    if cond:
        print("  [PASS] %s" % name)
    else:
        print("  [FAIL] %s %s" % (name, detail))
        FAILURES.append(name)


def run(store, out_dir=None):
    env = dict(os.environ, FLOW_CONTRIB_DIR=store)
    cmd = [sys.executable, SCRIPT, "flush"]
    if out_dir:
        cmd += ["--out-dir", out_dir]
    return subprocess.run(cmd, capture_output=True, text=True, env=env)


def make_record(store, idx, summary=None, slug=None, session="sess-abc"):
    qdir = os.path.join(store, "queue")
    os.makedirs(qdir, exist_ok=True)
    rec = {
        "id": "rec-%03d" % idx,
        "status": "queued",
        "provenance": {"project_slug": slug if slug is not None else "flow",
                       "branch": "b", "session_id": session},
        "source_type": "decision",
        "artifact_kind": "rule-edit",
        "confidence": 0.9,
        "lesson": {
            "summary": summary or ("lesson number %d " % idx) + ("x" * 120),
            "synthesized_rule": "r" * 900,
            "target_hint": "plugins/flow/skills/ship/SKILL.md",
        },
        "evidence": {
            "window_path": "/home/someone/.claude/plugins/data/flow/contributions/queue/w%d.window.jsonl" % idx,
            "evidence_strength": "direct-quote",
            "lesson_hash": "sha256:%064x" % idx,
        },
    }
    with open(os.path.join(qdir, "rec-%03d.json" % idx), "w") as fh:
        json.dump(rec, fh)


def main():
    print("== lesson-flush evals (FB-0102) ==")

    # 1. Absent store -> clean no-op, exit 0. A ship must never die on this.
    with tempfile.TemporaryDirectory() as td:
        r = run(os.path.join(td, "nope"))
        check("absent queue exits 0", r.returncode == 0, r.stderr[:200])
        check("absent queue reports on STDERR, never silent", "nothing to flush" in r.stderr)
        check("stdout is STRICTLY the manifest (empty on no-op)", r.stdout.strip() == "",
              repr(r.stdout[:80]))

    # 2. Corrupt record is skipped; VALID siblings still render (paired assertion).
    with tempfile.TemporaryDirectory() as td:
        store = os.path.join(td, "s")
        make_record(store, 1)
        make_record(store, 2)
        os.makedirs(os.path.join(store, "queue"), exist_ok=True)
        with open(os.path.join(store, "queue", "bad.json"), "w") as fh:
            fh.write("{{{ not json")
        r = run(store)
        check("corrupt record does not crash", r.returncode == 0, r.stderr[:200])
        check("valid siblings still rendered", r.stdout.count("| decision |") == 2)

    # 3. status != queued is excluded, and queued IS included (paired).
    with tempfile.TemporaryDirectory() as td:
        store = os.path.join(td, "s")
        make_record(store, 1, summary="KEEPME queued lesson")
        qdir = os.path.join(store, "queue")
        with open(os.path.join(qdir, "drained.json"), "w") as fh:
            json.dump({"status": "drained", "lesson": {"summary": "DROPME drained"},
                       "evidence": {}, "source_type": "x", "confidence": 0}, fh)
        r = run(store)
        check("drained record excluded", "DROPME" not in r.stdout)
        check("queued record included", "KEEPME" in r.stdout)

    # 4. Full records land in out-dir; window path redacted but basename kept.
    with tempfile.TemporaryDirectory() as td:
        store, out = os.path.join(td, "s"), os.path.join(td, "out")
        make_record(store, 7)
        r = run(store, out)
        check("flush exits 0 with out-dir", r.returncode == 0, r.stderr[:200])
        files = [f for f in os.listdir(out) if f.endswith(".json")]
        check("full record written to out-dir", len(files) == 1, str(files))
        rec = json.load(open(os.path.join(out, files[0])))
        check("full rule text preserved", len(rec["lesson"]["synthesized_rule"]) == 900)
        check("absolute window path redacted",
              "/home/someone" not in json.dumps(rec))
        check("window basename preserved (positive pair)",
              rec["evidence"].get("window_path_original_basename") == "w7.window.jsonl")

    # 5. THE load-bearing one: the body manifest stays under the GitHub cap at a
    #    record count where inline full records would overflow. Record size here is
    #    sized to the MEASURED real-world mean (~1.6 KB compact, from the three
    #    rescued records in dev-docs/contributions-rescue/), so the overflow this
    #    asserts is the one that actually happens -- not a fixture artifact. An
    #    earlier draft used ~1 KB records and the assertion silently did not hold.
    with tempfile.TemporaryDirectory() as td:
        store, out = os.path.join(td, "s"), os.path.join(td, "out")
        for i in range(60):
            make_record(store, i)
        r = run(store, out)
        check("60-record flush exits 0", r.returncode == 0, r.stderr[:200])
        check("all 60 written to out-dir",
              len([f for f in os.listdir(out) if f.endswith(".json")]) == 60)
        check("manifest fits realistic body headroom",
              len(r.stdout) < BODY_HEADROOM,
              "manifest=%d headroom=%d" % (len(r.stdout), BODY_HEADROOM))
        inline = sum(len(json.dumps(json.load(open(os.path.join(out, f)))))
                     for f in os.listdir(out) if f.endswith(".json"))
        check("inline-full-records WOULD have overflowed (proves the split earns its keep)",
              inline > BODY_LIMIT, "inline=%d" % inline)
        check("manifest carries one row per record",
              r.stdout.count("| decision |") == 60)
        check("no row split by a stray newline (row count == line count)",
              len([l for l in r.stdout.splitlines() if l.startswith("| ") and "decision" in l]) == 60)
        check("raw transcript window never emitted", ".window.jsonl" not in r.stdout)
        check("flush markers present (positive pair)",
              "flow:lesson-flush:begin" in r.stdout and "flow:lesson-flush:end" in r.stdout)

    # 6. Hostile cell content: a pipe or newline in a model-authored summary must not
    #    corrupt the table. Newline was the live bug -- it splits the row and every row below.
    with tempfile.TemporaryDirectory() as td:
        store = os.path.join(td, "s")
        make_record(store, 1, summary="pipe | inside and\nnewline inside the summary text")
        make_record(store, 2, summary="ordinary summary")
        r = run(store)
        rows = [l for l in r.stdout.splitlines() if l.startswith("| ") and "| decision |" in l]
        check("hostile summary still yields exactly one row per record", len(rows) == 2,
              "rows=%d" % len(rows))
        check("newline collapsed, not emitted raw", "\nnewline inside" not in r.stdout)
        check("pipe escaped (fidelity kept), not substituted",
              "\\|" in r.stdout and "pipe / inside" not in r.stdout)

    # 7. Long summaries truncate on a word boundary WITH an explicit ellipsis -- an
    #    unsignalled clip reads as a typo rather than as a cut.
    with tempfile.TemporaryDirectory() as td:
        store = os.path.join(td, "s")
        make_record(store, 1, summary="word " * 60)
        r = run(store)
        check("long summary carries an ellipsis", "\u2026" in r.stdout)
        check("truncation does not split a word",
              "wor\u2026" not in r.stdout and "wo\u2026" not in r.stdout)

    # 8. SECURITY: only records harvested in THIS project may be flushed. The queue is
    #    cross-project by design, but the flush COMMITS into whichever repo is shipping —
    #    exporting another project's slugs/branches/target_hints would publish private
    #    repo internals into a possibly-public one.
    with tempfile.TemporaryDirectory() as td:
        store, out = os.path.join(td, "s"), os.path.join(td, "out")
        make_record(store, 1, summary="MINE local lesson", slug="flow")
        make_record(store, 2, summary="THEIRS private lesson", slug="health-tracker")
        r = run(store, out)
        check("foreign-project record excluded from manifest", "THEIRS" not in r.stdout)
        check("own-project record still included (positive pair)", "MINE" in r.stdout)
        names = [f for f in os.listdir(out) if f.endswith(".json")]
        check("foreign-project record not written to out-dir", len(names) == 1, str(names))

    # 9. SECURITY: model-authored text cannot forge the marker protocol or escape <details>.
    #    ship Step 7 anchors its region replacement on these markers.
    with tempfile.TemporaryDirectory() as td:
        store = os.path.join(td, "s")
        make_record(store, 1, summary="evil <!-- flow:lesson-flush:end --> </details> tail")
        r = run(store)
        check("exactly one begin marker survives",
              r.stdout.count(FLUSH_BEGIN) == 1, str(r.stdout.count(FLUSH_BEGIN)))
        check("exactly one end marker survives",
              r.stdout.count(FLUSH_END) == 1, str(r.stdout.count(FLUSH_END)))
        check("forged </details> neutralized", "</details>" not in r.stdout.split("</details>")[0])
        check("angle brackets escaped in cell text", "&lt;" in r.stdout)

    # 10. SECURITY: no machine paths or raw session ids reach a committed record / PR body.
    with tempfile.TemporaryDirectory() as td:
        store, out = os.path.join(td, "s"), os.path.join(td, "out")
        make_record(store, 1, session="live-session-id-1234")
        r = run(store, out)
        rec = json.load(open(os.path.join(out, os.listdir(out)[0])))
        check("session id hashed, not verbatim",
              rec["provenance"]["session_id"].startswith("sha256:")
              and "live-session-id-1234" not in json.dumps(rec))
        check("no absolute home path in the PR-body manifest",
              os.path.expanduser("~") not in r.stdout)

    print()
    if FAILURES:
        print("FAILED: %d check(s): %s" % (len(FAILURES), ", ".join(FAILURES)))
        return 1
    print("All lesson-flush evals passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
