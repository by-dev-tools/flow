#!/usr/bin/env python3
"""Harvest generalizable lessons from a session at /flow:ship time (Step 4c).

Two roles:
  prescan   the ~free deterministic COST GATE. Scans the dialogue since the
            last harvest for any candidate signal (a correction, a symptom, a
            human overruling the agent, an endorsed reviewer finding). Exit 0 if
            signal present (ship spends LLM tokens on classification), exit 1 if
            none (ship short-circuits — the common clean-PR case costs nothing).
  enqueue   the mechanical write path. Captures the dialogue evidence window,
            records provenance + the origin project's token, and enqueues the
            (LLM-classified) lesson via contribution_store. Classification —
            project-local vs flow-generalizable, source_type — stays in the ship
            agent's prompt; this script does the non-judgment parts only.
  mark      advance the per-session lastHarvested watermark (called once by ship
            after Step 4c, so re-shipping a branch doesn't re-harvest old turns).

The watermark file maps session_id → record count already harvested. A fresh
session starts at 0 (whole session); re-ship advances past prior turns.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from extract_session import (
    find_session_file, load_session, harvest_dialogue, render_harvest_window,
)
from bounding_logic import SYMPTOM_WORDS
import contribution_store as store

# Correction / preference markers — borrowed from the forge/noticed transcript
# analyzer. Presence of any of these (or a symptom word, or an overrule) means
# the session MIGHT carry a lesson; absence means it almost certainly does not.
CORRECTION_MARKERS = (
    "actually", "instead", "not quite", "that's wrong", "thats wrong",
    "no,", "nope", "don't ", "do not ", "should be", "i told you",
    "we use", "rather than", "prefer", "scratch that", "let's not",
    "lets not", "redo", "revert", "you misunderstood", "wrong place",
)
# Markers that an agent proposal was redirected (taste / decision signal).
OVERRULE_MARKERS = (
    "let's go with", "lets go with", "use the", "i'd rather", "id rather",
    "go with option", "the other one", "not that one", "change it to",
)
# Markers that a flow reviewer finding was endorsed as generally true.
ENDORSED_MARKERS = (
    "good catch", "you're right", "youre right", "fair point", "valid finding",
    "agreed", "yes fix", "yeah fix",
)

DEFAULT_MARKER_PATH = store.CONTRIB_DIR / "last_harvested.json"


def _marker_path(args) -> Path:
    return Path(args.marker_file) if args.marker_file else DEFAULT_MARKER_PATH


def _session_id(session_file: str = "") -> str:
    if session_file:
        return Path(session_file).stem
    sid = os.environ.get("CLAUDE_CODE_SESSION_ID", "").strip()
    if sid:
        return sid
    p = find_session_file()
    return p.stem if p else "unknown-session"


def _load_marker(path: Path) -> dict:
    return store._read_json(path, {}) or {}


def _window_start(marker: dict, session_id: str) -> int:
    try:
        return int(marker.get(session_id, 0))
    except (TypeError, ValueError):
        return 0


def _project_slug(explicit: str) -> str:
    if explicit:
        return explicit
    # Best-effort: the working-directory basename is the project's name.
    return Path(os.getcwd()).name or ""


def _scan_signal(text: str) -> list[str]:
    low = text.lower()
    hits = []
    if any(m in low for m in CORRECTION_MARKERS):
        hits.append("correction")
    if any(w in low for w in SYMPTOM_WORDS):
        hits.append("symptom")
    if any(m in low for m in OVERRULE_MARKERS):
        hits.append("overrule")
    if any(m in low for m in ENDORSED_MARKERS):
        hits.append("endorsed")
    return sorted(set(hits))


def _records_window(marker_path: Path, session_file: str = ""):
    session_id = _session_id(session_file)
    sp = find_session_file(session_file or None)
    if sp is None:
        return None, session_id, 0, []
    records = load_session(sp)
    start = _window_start(_load_marker(marker_path), session_id)
    return records, session_id, start, harvest_dialogue(records, start)


def cmd_prescan(args) -> int:
    marker_path = _marker_path(args)
    records, _sid, _start, turns = _records_window(marker_path, args.session_file)
    if records is None:
        # No session file: can't prescan. Treat as no-signal (skip) but say so —
        # never a hard error that would block ship.
        sys.stdout.write("prescan: signal=no (no session file found)\n")
        return 1
    text = render_harvest_window(turns)
    hits = _scan_signal(text)
    if hits:
        sys.stdout.write(f"prescan: signal=yes types={','.join(hits)}\n")
        return 0
    sys.stdout.write("prescan: signal=no\n")
    return 1


def cmd_enqueue(args) -> int:
    marker_path = _marker_path(args)
    records, session_id, start, turns = _records_window(marker_path, args.session_file)
    project_slug = _project_slug(args.project_slug)

    # Capture the dialogue evidence window to a jsonl alongside the queue entry,
    # so contribute can sanitize + reuse it as a fixture skeleton.
    evidence_path = ""
    if records is not None:
        store.QUEUE_DIR.mkdir(parents=True, exist_ok=True)
        ev = store.QUEUE_DIR / f"{store._utc_stamp()}-{store.slugify(args.summary)}.window.jsonl"
        with ev.open("w", encoding="utf-8") as f:
            for t in turns:
                f.write(json.dumps({"role": t.role, "content": t.content}) + "\n")
        evidence_path = str(ev)

    # Record the origin project's token so /flow:contribute scrubs it from the
    # public PR (the project slug is the most reliable leak vector).
    if project_slug:
        store.cmd_known_tokens(argparse.Namespace(add=[project_slug]))

    # Delegate the validated entry write to contribution_store.
    ns = argparse.Namespace(
        session_id=session_id,
        project_slug=project_slug,
        pr=args.pr,
        branch=args.branch,
        source_type=args.source_type,
        artifact_kind=args.artifact_kind,
        summary=args.summary,
        rule=args.rule,
        target_hint=args.target_hint,
        evidence_strength=args.evidence_strength,
        evidence_file=evidence_path,
    )
    return store.cmd_enqueue(ns)


def cmd_mark(args) -> int:
    marker_path = _marker_path(args)
    session_id = _session_id(args.session_file)
    sp = find_session_file(args.session_file or None)
    n = len(load_session(sp)) if sp is not None else 0
    marker = _load_marker(marker_path)
    marker[session_id] = n
    store._atomic_write_json(marker_path, marker)
    sys.stdout.write(f"marked {session_id}@{n}\n")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="flow lesson harvest (ship Step 4c)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("prescan")
    p.add_argument("--marker-file", default="")
    p.add_argument("--session-file", default="")
    p.set_defaults(fn=cmd_prescan)

    e = sub.add_parser("enqueue")
    e.add_argument("--marker-file", default="")
    e.add_argument("--session-file", default="")
    e.add_argument("--project-slug", default="")
    e.add_argument("--pr", default="")
    e.add_argument("--branch", default="")
    e.add_argument("--source-type", required=True)
    e.add_argument("--artifact-kind", required=True)
    e.add_argument("--summary", required=True)
    e.add_argument("--rule", required=True)
    e.add_argument("--target-hint", default="")
    e.add_argument("--evidence-strength", default="paraphrase")
    e.set_defaults(fn=cmd_enqueue)

    m = sub.add_parser("mark")
    m.add_argument("--marker-file", default="")
    m.add_argument("--session-file", default="")
    m.set_defaults(fn=cmd_mark)

    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
