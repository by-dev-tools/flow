#!/usr/bin/env python3
"""Per-subagent token + model attribution report (roadmap item M, Step 1, FB-0089).

Dev tooling, not a shipped plugin artifact -- see CLAUDE.md § 3 "Project-dev
infrastructure". Reads a Claude Code session transcript and reports, per
subagent invocation, how many tokens were used and which model ran, plus a
"main" bucket for the orchestrating thread's own turns. Measurement only:
this script never recommends or applies a model swap (FB-0083).

Usage:
    python3 model_measure.py [--session-file PATH]

Without --session-file, resolves the current session the same way
extract_session.py does (CLAUDE_CODE_SESSION_ID, then a cwd-derived
~/.claude/projects/<slug>/ lookup).

Transcript shapes supported (live-verified 2026-08-25, see dev-docs/plan.md
"PR -- Model-measurement harness, Step 1" for the verification narrative):

  1. Sidecar format (primary): subagent invocations live in
     <session-dir>/subagents/agent-<id>.jsonl with a companion
     agent-<id>.meta.json (same stem, same prefix) carrying {"agentType",
     "toolUseId", "spawnDepth"}. This is the format directly observed in
     this development environment.

  2. Legacy inline format (fallback): no subagents/ directory; subagent
     turns are interleaved in the main transcript as isSidechain: true
     records, bracketed between a Task/Agent tool_use and its tool_result.
     Not reproducible in this sandbox -- built to extract_session.py's
     pre-existing isSidechain-skip assumption, fixtured, and gracefully
     degrading (an ambiguous overlap -- concurrent spawns -- reports as
     "unattributed" rather than a guess).

Load-bearing assumption: JSONL records sharing one assistant message.id
carry an IDENTICAL, complete `usage` snapshot (not incremental per-record
deltas) -- confirmed live in this session (a message.id repeated 4 times
had byte-identical output_tokens on every repeat). Summing every record
naively overcounts by roughly that many times; this script dedupes by
message.id before summing, keeping the last occurrence. If a future Claude
Code release makes usage incremental instead, this assumption needs
re-checking (see the Confidence verdict in dev-docs/plan.md).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPTS_DIR = _REPO_ROOT / "plugins" / "flow" / "scripts"
sys.path.insert(0, str(_SCRIPTS_DIR))
from extract_session import find_session_file, load_session  # noqa: E402


USAGE_FIELDS = (
    "input_tokens",
    "output_tokens",
    "cache_creation_input_tokens",
    "cache_read_input_tokens",
)
SPAWN_TOOL_NAMES = {"Task", "Agent"}


def _empty_totals() -> dict:
    return {field: 0 for field in USAGE_FIELDS}


def _load_json_file(path: Path):
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def dedupe_assistant_usage(records: list[dict]) -> list[tuple[str | None, dict]]:
    """Assistant records collapse to one (model, usage) pair per message.id --
    see the module docstring's load-bearing assumption. Records with no id
    (malformed) are each kept as their own entry rather than merged. Dict
    insertion order (3.7+) already tracks first-seen id order; a repeat only
    overwrites an existing key's value, so no separate order list is needed."""
    by_id: dict = {}
    for r in records:
        if r.get("type") != "assistant":
            continue
        msg = r.get("message")
        if not isinstance(msg, dict):
            continue
        mid = msg.get("id")
        if mid is None:
            mid = id(r)
        usage = msg.get("usage")
        by_id[mid] = (msg.get("model"), usage if isinstance(usage, dict) else {})
    return list(by_id.values())


def _add_totals(dst: dict, src: dict) -> None:
    for field in USAGE_FIELDS:
        value = src.get(field)
        if isinstance(value, (int, float)):
            dst[field] += value


def sum_usage(entries: list[tuple[str | None, dict]]) -> tuple[dict, set]:
    totals = _empty_totals()
    models: set = set()
    for model, usage in entries:
        if isinstance(model, str) and model:
            models.add(model)
        _add_totals(totals, usage)
    return totals, models


def session_dir_for(session_path: Path) -> Path:
    return session_path.parent / session_path.stem


def _make_invocation(agent_type: str, tool_use_id, spawn_depth: int, records: list[dict]) -> dict:
    totals, models = sum_usage(dedupe_assistant_usage(records))
    return {
        "agent_type": agent_type,
        "tool_use_id": tool_use_id,
        "spawn_depth": spawn_depth,
        "totals": totals,
        "models": models,
    }


def read_sidecar_subagents(session_dir: Path) -> tuple[list[dict], list[str]]:
    """Primary path: <session_dir>/subagents/*.meta.json + agent-*.jsonl.

    Returns (invocations, warnings). A malformed/incomplete meta.json, or one
    whose matching transcript file is missing, is skipped and counted in
    warnings -- never silently dropped with no trace (FB-0010 silent-skip)."""
    subdir = session_dir / "subagents"
    invocations: list[dict] = []
    warnings: list[str] = []
    if not subdir.is_dir():
        return invocations, warnings
    for meta_path in sorted(subdir.glob("*.meta.json")):
        meta = _load_json_file(meta_path)
        if not isinstance(meta, dict) or not meta.get("agentType"):
            warnings.append(f"unreadable or incomplete meta file: {meta_path.name}")
            continue
        stem = meta_path.name[: -len(".meta.json")]
        jsonl_path = subdir / f"{stem}.jsonl"
        if not jsonl_path.is_file():
            warnings.append(
                f"meta file {meta_path.name} references a missing transcript "
                f"{jsonl_path.name}"
            )
            continue
        records = load_session(jsonl_path)
        invocations.append(_make_invocation(
            meta.get("agentType"), meta.get("toolUseId"), meta.get("spawnDepth", 1), records,
        ))
    return invocations, warnings


def has_inline_sidechains(records: list[dict]) -> bool:
    return any(r.get("isSidechain") for r in records)


def attribute_inline_sidechains(records: list[dict]) -> tuple[list[dict], dict]:
    """Fallback path: bracket each isSidechain run between the Task/Agent
    tool_use that opened it and the tool_result that closed it (matched by
    tool_use_id). A run that closes while zero or more-than-one spawn is
    open cannot be unambiguously attributed and is bucketed as
    unattributed rather than guessed."""
    open_spawns: list[dict] = []
    invocations: list[dict] = []
    unattributed_records: list[dict] = []
    pending: list[dict] = []

    def flush() -> None:
        nonlocal pending
        if not pending:
            return
        if len(open_spawns) == 1:
            spawn = open_spawns[0]
            invocations.append(_make_invocation(
                spawn["subagent_type"] or "unknown", spawn["tool_use_id"], 1, pending,
            ))
        else:
            unattributed_records.extend(pending)
        pending = []

    for r in records:
        if r.get("isSidechain"):
            pending.append(r)
            continue
        flush()
        msg = r.get("message") or {}
        content = msg.get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "tool_use" and block.get("name") in SPAWN_TOOL_NAMES:
                open_spawns.append({
                    "tool_use_id": block.get("id"),
                    "subagent_type": (block.get("input") or {}).get("subagent_type"),
                })
            elif block.get("type") == "tool_result":
                tid = block.get("tool_use_id")
                open_spawns[:] = [s for s in open_spawns if s["tool_use_id"] != tid]
    flush()

    unattributed_totals, _ = sum_usage(dedupe_assistant_usage(unattributed_records))
    return invocations, unattributed_totals


def aggregate_by_type(invocations: list[dict]) -> dict:
    agg: dict = {}
    for inv in invocations:
        bucket = agg.setdefault(inv["agent_type"], {
            "invocations": 0,
            "totals": _empty_totals(),
            "models": set(),
        })
        bucket["invocations"] += 1
        _add_totals(bucket["totals"], inv["totals"])
        bucket["models"] |= inv["models"]
    return agg


def build_report(session_path: Path, records: list[dict]) -> dict:
    main_records = [r for r in records if not r.get("isSidechain")]
    main_totals, main_models = sum_usage(dedupe_assistant_usage(main_records))

    session_dir = session_dir_for(session_path)
    sidecar_invocations, warnings = read_sidecar_subagents(session_dir)

    unattributed_totals = None
    if sidecar_invocations or warnings:
        fmt = "sidecar"
        agg = aggregate_by_type(sidecar_invocations)
    elif has_inline_sidechains(records):
        fmt = "inline"
        invocations, unattributed_totals = attribute_inline_sidechains(records)
        agg = aggregate_by_type(invocations)
    else:
        fmt = "none"
        agg = {}

    return {
        "format": fmt,
        "main": {"totals": main_totals, "models": main_models},
        "subagents": agg,
        "unattributed": unattributed_totals,
        "warnings": warnings,
    }


# Widths verified against realistic content, not guessed: NAME_WIDTH covers the longest
# label this module itself emits ("unattributed (ambiguous concurrent spawn)", 41 chars);
# MODEL_WIDTH comfortably fits two comma-joined full model ids (e.g. "claude-sonnet-5,
# claude-opus-4-6-20250929" style names run 25+ chars each). Neither is truncated, so an
# unexpectedly long value still overflows -- the " | " delimiters below keep an overflow
# ragged in the text columns instead of shoving the numeric columns out of alignment.
NAME_WIDTH = 44
MODEL_WIDTH = 40


def _row(name: str, invocations, models: set, totals: dict) -> str:
    model_str = ",".join(sorted(models)) if models else "-"
    return (
        f"{name:<{NAME_WIDTH}}{str(invocations):>8} | {model_str:<{MODEL_WIDTH}} | "
        f"{totals['input_tokens']:>10,}{totals['output_tokens']:>10,}"
        f"{totals['cache_read_input_tokens']:>12,}{totals['cache_creation_input_tokens']:>14,}"
    )


def _header_row() -> str:
    return (
        f"{'Subagent':<{NAME_WIDTH}}{'Invoc.':>8} | {'Model(s)':<{MODEL_WIDTH}} | "
        f"{'Input':>10}{'Output':>10}{'CacheRead':>12}{'CacheCreate':>14}"
    )


def render_report(data: dict) -> str:
    lines = [
        f"Model-measurement report (subagent transcript format: {data['format']})",
        "",
        _header_row(),
        _row("main", "-", data["main"]["models"], data["main"]["totals"]),
    ]
    for agent_type in sorted(data["subagents"]):
        bucket = data["subagents"][agent_type]
        lines.append(_row(agent_type, bucket["invocations"], bucket["models"], bucket["totals"]))
    if data["unattributed"] and any(data["unattributed"].values()):
        lines.append(_row("unattributed (ambiguous concurrent spawn)", "-", set(), data["unattributed"]))
    if data["format"] == "none":
        lines.append("")
        lines.append("No subagent invocations detected in this transcript.")
    if data["warnings"]:
        lines.append("")
        lines.append(f"WARNING: {len(data['warnings'])} subagent record(s) unreadable:")
        for w in data["warnings"]:
            lines.append(f"  - {w}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    # Exit 0 on every branch below, including "no data" -- this is an informational
    # report, not a gate. A future caller that wants to distinguish "ran, found nothing"
    # from "ran, found data" needs to parse stdout; the exit code alone doesn't carry it.
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session-file", default=None)
    args = parser.parse_args(argv)

    session_path = find_session_file(args.session_file)
    if session_path is None:
        print("model_measure: no session transcript found -- nothing to report.")
        return 0

    records = load_session(session_path)
    if not records:
        print(f"model_measure: session transcript at {session_path} is empty or unreadable -- nothing to report.")
        return 0

    print(render_report(build_report(session_path, records)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
