#!/usr/bin/env python3
"""Capture an audit-finding disagreement for prompt-tuning input.

Invoked from skills/log-disagreement when the user pushes back on a finding
from /audit-plan, /audit-completion, or /critique-plan.

Writes two paired files to user-scope storage so the maintainer can review
accumulated disagreements when tuning prompts:

    ~/.claude/plugins/data/flow/disagreements/
        <timestamp>-<reviewer>-<category>.jsonl   session window
        <timestamp>-<reviewer>-<category>.meta.json  dispute metadata

The .jsonl is a slice of the current session — the last few turns containing
the audit output and the user's disagreement — so it can become an eval
fixture skeleton with minimal hand-editing.
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from extract_session import find_session_file, load_session


DISAGREEMENT_DIR = (
    Path.home()
    / ".claude" / "plugins" / "data" / "flow" / "disagreements"
)

# Turns to capture before the disagreement. Enough to cover the user request,
# the plan/completion, the audit output, and the user's pushback. Hand-tuned.
SESSION_CAPTURE_WINDOW = 12

# Markers in assistant text that identify an audit/critique output.
AUDIT_OUTPUT_MARKERS = (
    "AUDIT SUMMARY",
    "CRITIQUE SUMMARY",
    "ISSUE ·",
    "No issues flagged",
    "APPROVED",
)


def find_recent_audit_record_idx(records: list[dict]) -> int | None:
    """Walk records back-to-front, return index of the most recent assistant
    turn whose text content looks like an audit output. None if not found."""
    for i in range(len(records) - 1, -1, -1):
        r = records[i]
        if r.get("type") != "assistant" or r.get("isSidechain"):
            continue
        msg = r.get("message") or {}
        content = msg.get("content")
        if isinstance(content, list):
            text = "\n".join(
                b.get("text", "")
                for b in content
                if isinstance(b, dict) and b.get("type") == "text"
            )
        elif isinstance(content, str):
            text = content
        else:
            continue
        if any(m in text for m in AUDIT_OUTPUT_MARKERS):
            return i
    return None


def slugify(s: str) -> str:
    out = []
    for ch in s.lower():
        if ch.isalnum():
            out.append(ch)
        elif ch in (" ", "-", "_"):
            out.append("-")
    slug = "".join(out).strip("-")
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug or "untitled"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reviewer", required=True,
                    choices=("auditor", "plan-critic"))
    ap.add_argument("--category", required=True)
    ap.add_argument("--severity", default="")
    ap.add_argument("--claim", required=True)
    ap.add_argument("--reason", required=True)
    args = ap.parse_args()

    DISAGREEMENT_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S")
    stem = f"{timestamp}-{args.reviewer}-{slugify(args.category)}"
    jsonl_path = DISAGREEMENT_DIR / f"{stem}.jsonl"
    meta_path = DISAGREEMENT_DIR / f"{stem}.meta.json"

    session_path = find_session_file()
    session_captured = False
    if session_path is not None:
        records = load_session(session_path)
        if records:
            audit_idx = find_recent_audit_record_idx(records)
            if audit_idx is not None:
                start = max(0, audit_idx - SESSION_CAPTURE_WINDOW // 2)
                window = records[start:]
                with jsonl_path.open("w", encoding="utf-8") as f:
                    for r in window:
                        f.write(json.dumps(r) + "\n")
                session_captured = True

    meta = {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat() + "Z",
        "cwd": os.getcwd(),
        "reviewer": args.reviewer,
        "category": args.category,
        "severity": args.severity,
        "disputed_claim": args.claim[:500],
        "user_reason": args.reason[:500],
        "session_file": str(session_path) if session_path else None,
        "session_window_captured": session_captured,
        "session_window_path": str(jsonl_path) if session_captured else None,
    }
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    # The skill instructs the model to echo the printed path back to the user.
    if session_captured:
        sys.stdout.write(str(jsonl_path) + "\n")
    else:
        sys.stdout.write(str(meta_path) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
