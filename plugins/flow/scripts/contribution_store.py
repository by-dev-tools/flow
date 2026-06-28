#!/usr/bin/env python3
"""Queue + dedup + confidence engine for the flow lesson-contribution loop.

A session at /flow:ship time may surface a *generalizable* lesson — a reviewer
false-positive, a gate that misfired, a taste call the human overruled — that
belongs back in the flow plugin, not just this project's local docs. Harvest
(skills/ship Step 4c, via harvest_lesson.py) enqueues those candidates here, to
user-scope cross-project storage. /flow:contribute later drains the queue from
the flow checkout, sanitizes, and opens a draft PR.

This module is the mechanical spine: it owns the storage layout, the dedup key,
and the DETERMINISTIC confidence score (so a future auto-merge gate can be a
pure predicate over recorded sub-signals — never an LLM free-hand number).

Storage (all under ~/.claude/plugins/data/flow/contributions/):
    queue/<ts>-<slug>.json   one queued lesson each (status: queued|...)
    dismissed.json           {schema_version, dismissed: [...]} — never re-propose
    feedback_signals.json    {schema_version, events: [...]} — calibration log
    known_tokens.json        {schema_version, tokens: [...]} — union of origin
                             project tokens, scrubbed against at contribute time

All reads are graceful (malformed JSON → treated as empty/default, with a
stderr note — never a crash, never a silent wrong-answer). All writes are
atomic (temp file + os.replace).

CLI subcommands: enqueue, list, dedup, score, dismiss, calibrate, known-tokens.
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import sys
from pathlib import Path

SCHEMA_VERSION = 1

# Storage root. Overridable via FLOW_CONTRIB_DIR (used by the eval harness and
# any headless test so they never touch real user-scope data); defaults to the
# user-scope location that mirrors the disagreements store.
CONTRIB_DIR = Path(
    os.environ.get("FLOW_CONTRIB_DIR")
    or (Path.home() / ".claude" / "plugins" / "data" / "flow" / "contributions")
)
QUEUE_DIR = CONTRIB_DIR / "queue"
DISMISSED_PATH = CONTRIB_DIR / "dismissed.json"
SIGNALS_PATH = CONTRIB_DIR / "feedback_signals.json"
KNOWN_TOKENS_PATH = CONTRIB_DIR / "known_tokens.json"

# --- confidence sub-signal weights (the deterministic spine) -----------------
# Taste/decision lessons (where the human overruled or stated a preference) are
# the highest-value harvest — that is the point of the feature. Bugs/errors and
# endorsed reviewer feedback weigh less.
SOURCE_WEIGHT = {
    "taste": 0.9,
    "decision": 0.9,
    "correction": 0.8,
    "error": 0.6,
    "feedback": 0.5,
}
EVIDENCE_WEIGHT = {
    "direct-quote": 1.0,
    "paraphrase": 0.6,
    "inferred": 0.3,
}
SOURCE_TYPES = tuple(SOURCE_WEIGHT)
ARTIFACT_KINDS = (
    "rule-edit", "reviewer-prompt", "eval-fixture", "new-check", "fb-entry",
)
EVIDENCE_STRENGTHS = tuple(EVIDENCE_WEIGHT)


def _now_utc() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _utc_stamp() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S")


def slugify(s: str) -> str:
    out = []
    for ch in (s or "").lower():
        if ch.isalnum():
            out.append(ch)
        elif ch in (" ", "-", "_"):
            out.append("-")
    slug = "".join(out).strip("-")
    while "--" in slug:
        slug = slug.replace("--", "-")
    return (slug or "untitled")[:48]


def lesson_hash(summary: str, synthesized_rule: str, artifact_kind: str) -> str:
    """Dedup key over the lesson's *meaning*, not its provenance. Two harvests
    of the same rule (different sessions/projects) collide here so we count
    recurrence instead of re-proposing."""
    basis = " ".join([
        (synthesized_rule or "").strip().lower(),
        artifact_kind or "",
    ])
    return "sha256:" + hashlib.sha256(basis.encode("utf-8")).hexdigest()


# --- graceful IO -------------------------------------------------------------


def _read_json(path: Path, default):
    if not path.is_file():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        sys.stderr.write(
            f"contribution_store: ⚠️ {path.name} is unreadable/malformed "
            f"({e}); treating as empty. Fix or delete it to clear this warning.\n"
        )
        return default


def _atomic_write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def _load_dismissed() -> dict:
    d = _read_json(DISMISSED_PATH, {"schema_version": SCHEMA_VERSION, "dismissed": []})
    if not isinstance(d, dict) or not isinstance(d.get("dismissed"), list):
        return {"schema_version": SCHEMA_VERSION, "dismissed": []}
    return d


def _load_signals() -> dict:
    d = _read_json(SIGNALS_PATH, {"schema_version": SCHEMA_VERSION, "events": []})
    if not isinstance(d, dict) or not isinstance(d.get("events"), list):
        return {"schema_version": SCHEMA_VERSION, "events": []}
    return d


def _iter_queue() -> list[tuple[Path, dict]]:
    out = []
    if not QUEUE_DIR.is_dir():
        return out
    for p in sorted(QUEUE_DIR.glob("*.json")):
        entry = _read_json(p, None)
        if isinstance(entry, dict):
            out.append((p, entry))
    return out


# --- confidence --------------------------------------------------------------


def compute_confidence(signals: dict) -> float:
    """Deterministic confidence in [0,1] from recorded sub-signals.

        base       = source_weight * evidence_weight
        recurrence = min(0.2, 0.1 * (recurrence_count - 1))
        penalty    = 0.5 when sanitization_clean is explicitly False, else 0.0
        confidence = round(min(1.0, max(0.0, (base + recurrence) * (1 - penalty))), 3)

    sanitization_clean is None until the contribute drain runs its scan; an
    un-scanned entry is NOT penalized (penalty applies only to a proven-dirty
    entry), so harvest-time scores are comparable. A failed scan halves trust.
    """
    sw = SOURCE_WEIGHT.get(signals.get("source_type", ""),
                           signals.get("source_weight", 0.0) or 0.0)
    ew = EVIDENCE_WEIGHT.get(signals.get("evidence_strength", ""),
                             signals.get("evidence_weight", 0.0) or 0.0)
    base = float(sw) * float(ew)
    recurrence_count = int(signals.get("recurrence_count", 1) or 1)
    recurrence = min(0.2, 0.1 * (recurrence_count - 1))
    clean = signals.get("sanitization_clean", None)
    penalty = 0.5 if clean is False else 0.0
    return round(min(1.0, max(0.0, (base + recurrence) * (1 - penalty))), 3)


def _signals_from_entry(entry: dict) -> dict:
    sig = dict(entry.get("signals") or {})
    sig.setdefault("source_type", entry.get("source_type", ""))
    sig.setdefault("evidence_strength",
                   (entry.get("evidence") or {}).get("evidence_strength", ""))
    return sig


# --- subcommands -------------------------------------------------------------


def cmd_enqueue(args) -> int:
    if args.source_type not in SOURCE_TYPES:
        sys.stderr.write(f"enqueue: --source-type must be one of {SOURCE_TYPES}\n")
        return 2
    if args.artifact_kind not in ARTIFACT_KINDS:
        sys.stderr.write(f"enqueue: --artifact-kind must be one of {ARTIFACT_KINDS}\n")
        return 2
    if args.evidence_strength not in EVIDENCE_STRENGTHS:
        sys.stderr.write(
            f"enqueue: --evidence-strength must be one of {EVIDENCE_STRENGTHS}\n")
        return 2

    lhash = lesson_hash(args.summary, args.rule, args.artifact_kind)

    # Idempotency / recurrence: if a QUEUED entry already carries this lesson
    # hash, bump its recurrence_count + re-score instead of writing a duplicate.
    # (Same session re-shipping, or a sibling lesson from another project.)
    for path, entry in _iter_queue():
        if entry.get("status") != "queued":
            continue
        if (entry.get("evidence") or {}).get("lesson_hash") == lhash:
            sig = entry.setdefault("signals", {})
            same_session = (entry.get("provenance") or {}).get(
                "session_id") == args.session_id
            if not same_session:
                sig["recurrence_count"] = int(sig.get("recurrence_count", 1)) + 1
            entry["confidence"] = compute_confidence(_signals_from_entry(entry))
            _atomic_write_json(path, entry)
            sys.stdout.write(
                f"{'recurrence' if not same_session else 'idempotent'} "
                f"{path}\n")
            return 0

    sig = {
        "source_type": args.source_type,
        "source_weight": SOURCE_WEIGHT[args.source_type],
        "evidence_strength": args.evidence_strength,
        "evidence_weight": EVIDENCE_WEIGHT[args.evidence_strength],
        "recurrence_count": 1,
        "sanitization_clean": None,
    }
    eid = f"{_utc_stamp()}-{args.artifact_kind}-{slugify(args.summary)}"
    entry = {
        "id": eid,
        "schema_version": SCHEMA_VERSION,
        "created_utc": _now_utc(),
        "status": "queued",
        "provenance": {
            "project_slug": args.project_slug or "",
            "pr": args.pr or "",
            "branch": args.branch or "",
            "session_id": args.session_id or "",
        },
        "source_type": args.source_type,
        "artifact_kind": args.artifact_kind,
        "lesson": {
            "summary": args.summary,
            "synthesized_rule": args.rule,
            "target_hint": args.target_hint or "",
        },
        "evidence": {
            "window_path": args.evidence_file or "",
            "evidence_strength": args.evidence_strength,
            "lesson_hash": lhash,
        },
        "signals": sig,
        "confidence": compute_confidence(sig),
    }
    out_path = QUEUE_DIR / f"{eid}.json"
    _atomic_write_json(out_path, entry)
    sys.stdout.write(f"enqueued {out_path}\n")
    return 0


def cmd_list(args) -> int:
    entries = [e for _, e in _iter_queue()
               if e.get("status", "queued") == "queued"]
    entries.sort(key=lambda e: e.get("confidence", 0.0), reverse=True)
    sys.stdout.write(json.dumps(entries, indent=2) + "\n")
    return 0


def cmd_dedup(args) -> int:
    """Exit 0 if the lesson hash is novel; exit 3 if it is already dismissed or
    already queued (with a stderr note saying which)."""
    lhash = args.lesson_hash
    for rec in _load_dismissed()["dismissed"]:
        if rec.get("lesson_hash") == lhash:
            sys.stderr.write(f"duplicate: dismissed ({rec.get('reason','')})\n")
            return 3
    for _, entry in _iter_queue():
        if (entry.get("evidence") or {}).get("lesson_hash") == lhash:
            sys.stderr.write("duplicate: already queued\n")
            return 3
    sys.stdout.write("novel\n")
    return 0


def cmd_score(args) -> int:
    entry = _read_json(Path(args.entry), None)
    if not isinstance(entry, dict):
        sys.stderr.write(f"score: cannot read entry at {args.entry}\n")
        return 2
    conf = compute_confidence(_signals_from_entry(entry))
    if args.write:
        entry["confidence"] = conf
        _atomic_write_json(Path(args.entry), entry)
    sys.stdout.write(f"{conf}\n")
    return 0


def cmd_set_status(args) -> int:
    """Flip a queued entry's status (e.g. queued → proposed once it lands in a
    draft PR) so it stops re-draining. cmd_list only emits status==queued, so a
    `proposed` entry won't be re-included on the next /flow:contribute run."""
    found = None
    for path, entry in _iter_queue():
        if entry.get("id") == args.id:
            found = (path, entry)
            break
    if found is None:
        sys.stderr.write(f"set-status: no queued entry with id {args.id}\n")
        return 3
    path, entry = found
    entry["status"] = args.status
    _atomic_write_json(path, entry)
    sys.stdout.write(f"{args.id} → {args.status}\n")
    return 0


def cmd_dismiss(args) -> int:
    d = _load_dismissed()
    d["dismissed"].append({
        "lesson_hash": args.lesson_hash,
        "summary": args.summary,
        "dismissed_utc": _now_utc(),
        "reason": args.reason,
        "by": args.by,
    })
    _atomic_write_json(DISMISSED_PATH, d)
    sys.stdout.write(f"dismissed {args.lesson_hash}\n")
    return 0


def cmd_calibrate(args) -> int:
    if args.decision not in ("approved", "edited", "rejected"):
        sys.stderr.write("calibrate: --decision must be approved|edited|rejected\n")
        return 2
    s = _load_signals()
    s["events"].append({
        "utc": _now_utc(),
        "lesson_hash": args.lesson_hash,
        "confidence_at_decision": args.confidence,
        "human_decision": args.decision,
        "artifact_kind": args.artifact_kind,
    })
    _atomic_write_json(SIGNALS_PATH, s)
    sys.stdout.write(f"calibrated {args.decision}\n")
    return 0


def cmd_known_tokens(args) -> int:
    d = _read_json(KNOWN_TOKENS_PATH, {"schema_version": SCHEMA_VERSION, "tokens": []})
    if not isinstance(d, dict) or not isinstance(d.get("tokens"), list):
        d = {"schema_version": SCHEMA_VERSION, "tokens": []}
    if args.add:
        toks = set(d["tokens"])
        for t in args.add:
            t = t.strip()
            if t:
                toks.add(t)
        d["tokens"] = sorted(toks)
        _atomic_write_json(KNOWN_TOKENS_PATH, d)
    sys.stdout.write("\n".join(d["tokens"]) + ("\n" if d["tokens"] else ""))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="flow contribution queue store")
    sub = ap.add_subparsers(dest="cmd", required=True)

    e = sub.add_parser("enqueue")
    e.add_argument("--session-id", default="")
    e.add_argument("--project-slug", default="")
    e.add_argument("--pr", default="")
    e.add_argument("--branch", default="")
    e.add_argument("--source-type", required=True)
    e.add_argument("--artifact-kind", required=True)
    e.add_argument("--summary", required=True)
    e.add_argument("--rule", required=True)
    e.add_argument("--target-hint", default="")
    e.add_argument("--evidence-strength", default="paraphrase")
    e.add_argument("--evidence-file", default="")
    e.set_defaults(fn=cmd_enqueue)

    l = sub.add_parser("list")
    l.set_defaults(fn=cmd_list)

    d = sub.add_parser("dedup")
    d.add_argument("--lesson-hash", required=True)
    d.set_defaults(fn=cmd_dedup)

    s = sub.add_parser("score")
    s.add_argument("entry")
    s.add_argument("--write", action="store_true")
    s.set_defaults(fn=cmd_score)

    ss = sub.add_parser("set-status")
    ss.add_argument("--id", required=True)
    ss.add_argument("--status", required=True,
                    choices=("queued", "proposed", "dismissed"))
    ss.set_defaults(fn=cmd_set_status)

    di = sub.add_parser("dismiss")
    di.add_argument("--lesson-hash", required=True)
    di.add_argument("--summary", default="")
    di.add_argument("--reason", required=True)
    di.add_argument("--by", default="human-gate")
    di.set_defaults(fn=cmd_dismiss)

    c = sub.add_parser("calibrate")
    c.add_argument("--lesson-hash", required=True)
    c.add_argument("--confidence", type=float, default=0.0)
    c.add_argument("--decision", required=True)
    c.add_argument("--artifact-kind", default="")
    c.set_defaults(fn=cmd_calibrate)

    k = sub.add_parser("known-tokens")
    k.add_argument("--add", action="append", default=[])
    k.set_defaults(fn=cmd_known_tokens)

    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
