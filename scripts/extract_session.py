#!/usr/bin/env python3
"""Extract preprocessed session context for the auditor subagent.

Invoked from a SKILL.md via:
    !`python3 ${CLAUDE_PLUGIN_ROOT}/scripts/extract_session.py --mode plan`
    !`python3 ${CLAUDE_PLUGIN_ROOT}/scripts/extract_session.py --mode completion`

stdout is substituted into the SKILL.md body before dispatch to the
auditor subagent. Output must be plain-text labeled sections matching the
contract documented in the build handoff.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bounding_logic import Turn, find_bounding_message


TOOL_CALL_CAP = 50

# Reference-doc support (plan-critic). Opt-in via --reference-paths /
# --reference-glob; existing audit-plan / audit-completion flows are unaffected.
REFERENCE_DOC_CHAR_CAP = 12000
DEFAULT_REFERENCE_SKIP_NAMES = {
    # decision log and work trackers, not sources of truth for new plans
    "history.md",
    "plan.md",
    "roadmap.md",
}

ARTIFACT_EXTENSIONS = (
    "md", "py", "ts", "tsx", "js", "jsx", "swift", "go", "rs",
    "json", "yaml", "yml", "toml", "css", "scss", "html",
    "sh", "bash", "zsh", "rb", "java", "kt", "c", "cc", "cpp", "h", "hpp",
    "sql", "txt",
)
ARTIFACT_PATTERN = re.compile(
    r"(?<![\w/])([\w./\-]*[\w\-]+\.(?:" + "|".join(ARTIFACT_EXTENSIONS) + r"))(?![\w])"
)

PLAN_HINTS = (
    "## plan",
    "# plan",
    "**plan**",
    "plan:",
    "here's the plan",
    "here is the plan",
    "proposed plan",
)
NUMBERED_STEP_RE = re.compile(r"(?m)^\s*\d+\.\s+\S")

COMPLETION_WORD_RE = re.compile(
    r"(?<![.\w])(fixed|done|implemented|completed|shipped|ready|complete)(?![.\w])",
    re.IGNORECASE,
)
COMPLETION_PHRASES = ("all set", "working now", "should now work", "now works")


# ---------------------------------------------------------------- session io


def slugify_cwd(cwd: str) -> str:
    """Replace `/` with `-`, strip leading `-`, matching Claude Code convention."""
    return cwd.replace("/", "-").lstrip("-")


def find_session_file(explicit: str | None = None) -> Path | None:
    if explicit:
        p = Path(explicit).expanduser().resolve()
        return p if p.is_file() else None
    cwd = os.getcwd()
    slug = slugify_cwd(cwd)
    projects_dir = Path.home() / ".claude" / "projects" / f"-{slug}"
    if not projects_dir.is_dir():
        return None
    candidates = sorted(
        projects_dir.glob("*.jsonl"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else None


def load_session(path: Path) -> list[dict]:
    records = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return records


# ---------------------------------------------------------------- normalize


def _content_to_text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        out = []
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "text":
                out.append(block.get("text", ""))
            elif block.get("type") == "tool_use":
                out.append(f"[tool_use {block.get('name', '?')}]")
            elif block.get("type") == "tool_result":
                inner = block.get("content", "")
                if isinstance(inner, list):
                    for sub in inner:
                        if isinstance(sub, dict) and sub.get("type") == "text":
                            out.append(sub.get("text", ""))
                elif isinstance(inner, str):
                    out.append(inner)
        return "\n".join(out)
    return ""


def normalize_turns(records: list[dict]) -> list[Turn]:
    """Reduce raw session records to ordered (role, content) turns.

    Skips meta records (summary, sidechain notes, etc.) and tool_result-only
    user records — only user *messages* count for bounding."""
    turns = []
    for r in records:
        rtype = r.get("type")
        if rtype not in ("user", "assistant"):
            continue
        if r.get("isSidechain"):
            continue
        msg = r.get("message") or {}
        role = msg.get("role") or rtype
        content = _content_to_text(msg.get("content"))
        if rtype == "user":
            inner = msg.get("content")
            if isinstance(inner, list) and all(
                isinstance(b, dict) and b.get("type") == "tool_result"
                for b in inner
            ):
                continue
        turns.append(Turn(role=role, content=content))
    return turns


# ---------------------------------------------------------------- tool calls


def extract_tool_calls(records: list[dict], start_record_idx: int) -> list[dict]:
    """Walk records from start_record_idx forward, return tool_use entries paired
    with their tool_result text (best effort by tool_use_id)."""
    results_by_id: dict[str, str] = {}
    tool_uses: list[dict] = []
    for r in records[start_record_idx:]:
        if r.get("isSidechain"):
            continue
        msg = r.get("message") or {}
        content = msg.get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "tool_use":
                tool_uses.append({
                    "id": block.get("id", ""),
                    "name": block.get("name", "?"),
                    "input": block.get("input", {}),
                })
            elif block.get("type") == "tool_result":
                tid = block.get("tool_use_id", "")
                inner = block.get("content", "")
                text = ""
                if isinstance(inner, list):
                    for sub in inner:
                        if isinstance(sub, dict) and sub.get("type") == "text":
                            text += sub.get("text", "")
                elif isinstance(inner, str):
                    text = inner
                results_by_id[tid] = text
    for tu in tool_uses:
        tu["result"] = results_by_id.get(tu["id"], "")
    return tool_uses


def _summarize_input(name: str, inp: dict) -> str:
    if not isinstance(inp, dict):
        return ""
    keys_priority = ("file_path", "path", "pattern", "command", "url", "query")
    for k in keys_priority:
        if k in inp:
            v = str(inp[k])
            return f"{k}={v[:120]}"
    if inp:
        first_k = next(iter(inp))
        v = str(inp[first_k])
        return f"{first_k}={v[:120]}"
    return ""


def _summarize_result(text: str) -> str:
    if not text:
        return "(no result captured)"
    snippet = text.strip().splitlines()[0] if text.strip() else ""
    snippet = snippet[:160]
    line_count = text.count("\n") + 1
    if line_count > 1:
        return f"{snippet} (+{line_count - 1} more lines)"
    return snippet


def render_tool_call_history(tool_calls: list[dict]) -> str:
    if not tool_calls:
        return "- (no tool calls in window)"
    truncated_note = ""
    if len(tool_calls) > TOOL_CALL_CAP:
        omitted = len(tool_calls) - TOOL_CALL_CAP
        tool_calls = tool_calls[-TOOL_CALL_CAP:]
        truncated_note = f"\n(truncated, {omitted} more calls omitted)"
    lines = []
    for tc in tool_calls:
        args = _summarize_input(tc["name"], tc.get("input", {}))
        result = _summarize_result(tc.get("result", ""))
        head = f"- [{tc['name']}]"
        if args:
            head += f" {args}"
        lines.append(f"{head} -> {result}")
    return "\n".join(lines) + truncated_note


# ---------------------------------------------------------------- artifacts


def find_referenced_artifacts(text: str) -> list[str]:
    found = []
    seen = set()
    for m in ARTIFACT_PATTERN.finditer(text or ""):
        path = m.group(1)
        if path in seen:
            continue
        seen.add(path)
        found.append(path)
    return found


def artifact_was_read(path: str, tool_calls: list[dict]) -> bool:
    for tc in tool_calls:
        name = tc.get("name", "")
        inp = tc.get("input", {}) or {}
        if name in ("Read", "NotebookRead"):
            target = inp.get("file_path") or inp.get("notebook_path") or ""
            if target and (target.endswith(path) or path in target):
                return True
        elif name == "Grep":
            grep_path = inp.get("path", "")
            if grep_path and (grep_path.endswith(path) or path in grep_path):
                return True
        elif name in ("Bash",):
            cmd = inp.get("command", "")
            if path in cmd and any(t in cmd for t in ("cat ", "less ", "head ", "tail ", "open ")):
                return True
    return False


def render_artifacts(paths: list[str], tool_calls: list[dict]) -> str:
    if not paths:
        return "- (none detected)"
    lines = []
    for p in paths:
        status = "READ" if artifact_was_read(p, tool_calls) else "UNREAD"
        lines.append(f"- {p} - {status}")
    return "\n".join(lines)


# ---------------------------------------------------------------- references


def gather_reference_docs(
    paths: list[str],
    globs: list[str],
    skip_names: set[str],
) -> list[tuple[str, str]]:
    """Return ordered (display_path, contents) tuples for reference docs.

    Resolution is relative to CWD. Missing files are silently skipped (same
    grace as session loading). Files whose basename is in skip_names are
    excluded. Each doc is truncated to REFERENCE_DOC_CHAR_CAP with a marker.
    Duplicate paths (same resolved location) are de-duplicated, preserving the
    first occurrence.
    """
    cwd = Path.cwd()
    candidates: list[Path] = []
    for p in paths:
        candidates.append((cwd / p) if not Path(p).is_absolute() else Path(p))
    for g in globs:
        candidates.extend(sorted(cwd.glob(g)))

    seen: set[Path] = set()
    docs: list[tuple[str, str]] = []
    for raw in candidates:
        try:
            resolved = raw.resolve()
        except (OSError, RuntimeError):
            continue
        if resolved in seen:
            continue
        seen.add(resolved)
        if resolved.name in skip_names:
            continue
        if not resolved.is_file():
            continue
        try:
            text = resolved.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        try:
            display = str(resolved.relative_to(cwd))
        except ValueError:
            display = str(resolved)
        if len(text) > REFERENCE_DOC_CHAR_CAP:
            original = len(text)
            text = (
                text[:REFERENCE_DOC_CHAR_CAP]
                + f"\n\n... (truncated; original {original} chars)"
            )
        docs.append((display, text))
    return docs


def render_reference_section(docs: list[tuple[str, str]]) -> str:
    if not docs:
        return ""
    parts = [
        "## Reference documents",
        "",
        "Sources of truth for plan critique. Quote rules from here with the "
        "source path when flagging spec violations.",
        "",
    ]
    for display, text in docs:
        parts.append(f"### {display}")
        parts.append("")
        parts.append(text.rstrip())
        parts.append("")
    return "\n".join(parts) + "\n"


# ---------------------------------------------------------------- mode detect


def looks_like_plan(text: str) -> bool:
    if not text:
        return False
    low = text.lower()
    if any(h in low for h in PLAN_HINTS):
        return True
    matches = NUMBERED_STEP_RE.findall(text)
    return len(matches) >= 3


def looks_like_completion(text: str) -> bool:
    if not text:
        return False
    if COMPLETION_WORD_RE.search(text):
        return True
    low = text.lower()
    return any(p in low for p in COMPLETION_PHRASES)


def followed_by_change_tools(records: list[dict], turn_record_idx: int) -> bool:
    """Whether mutation tools (Edit/Write/NotebookEdit) appear in the window
    leading up to and including this assistant turn record."""
    window_start = max(0, turn_record_idx - 50)
    for r in records[window_start:turn_record_idx + 1]:
        msg = r.get("message") or {}
        content = msg.get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if isinstance(block, dict) and block.get("type") == "tool_use":
                if block.get("name") in ("Edit", "Write", "NotebookEdit", "MultiEdit"):
                    return True
    return False


# ---------------------------------------------------------------- output


def emit_cannot_audit(reason: str) -> str:
    return (
        "Audit could not be performed.\n"
        f"Reason: {reason}\n"
    )


def render_plan_context(plan_text: str, user_request: str,
                        tool_calls: list[dict], artifact_paths: list[str]) -> str:
    return (
        "## Plan\n"
        f"{plan_text.strip()}\n\n"
        "## User request\n"
        f"{user_request.strip()}\n\n"
        "## Tool call history\n"
        f"{render_tool_call_history(tool_calls)}\n\n"
        "## Referenced artifacts\n"
        f"{render_artifacts(artifact_paths, tool_calls)}\n"
    )


def render_completion_context(completion_text: str, user_request: str,
                              tool_calls: list[dict], artifact_paths: list[str]) -> str:
    return (
        "## Completion message\n"
        f"{completion_text.strip()}\n\n"
        "## Most recent user request\n"
        f"{user_request.strip()}\n\n"
        "## Tool call history since request\n"
        f"{render_tool_call_history(tool_calls)}\n\n"
        "## Referenced artifacts\n"
        f"{render_artifacts(artifact_paths, tool_calls)}\n"
    )


# ---------------------------------------------------------------- main


def run(
    mode: str,
    session_file: str | None = None,
    reference_paths: list[str] | None = None,
    reference_globs: list[str] | None = None,
) -> str:
    session_path = find_session_file(session_file)
    if session_path is None:
        if session_file:
            return emit_cannot_audit(f"Session file not found at {session_file}.")
        return emit_cannot_audit("Session file not found for this working directory.")

    records = load_session(session_path)
    if not records:
        return emit_cannot_audit("Session file is empty.")

    turns = normalize_turns(records)
    if not turns:
        return emit_cannot_audit("No user/assistant turns in session.")

    last_assistant_idx = None
    for i in range(len(turns) - 1, -1, -1):
        if turns[i].role != "assistant":
            continue
        text = (turns[i].content or "").strip()
        if not text:
            continue
        if text.startswith("[tool_use ") and text.endswith("]") and "\n" not in text:
            continue
        last_assistant_idx = i
        break
    if last_assistant_idx is None:
        return emit_cannot_audit("No assistant turn with text content to audit.")

    last_assistant_text = turns[last_assistant_idx].content

    last_assistant_record_idx = None
    seen_assistants = 0
    target_count = sum(1 for t in turns[:last_assistant_idx + 1] if t.role == "assistant")
    for ridx, r in enumerate(records):
        if r.get("type") == "assistant" and not r.get("isSidechain"):
            seen_assistants += 1
            if seen_assistants == target_count:
                last_assistant_record_idx = ridx
                break

    if mode == "plan":
        if looks_like_completion(last_assistant_text) and not looks_like_plan(last_assistant_text):
            return emit_cannot_audit(
                "No plan detected; most recent assistant turn appears to be a "
                "completion claim. Did you mean /audit-completion?"
            )
        if not looks_like_plan(last_assistant_text):
            sys.stderr.write("[extract_session] note: no strong plan signal; "
                             "auditing the most recent assistant turn anyway.\n")
    elif mode == "completion":
        if looks_like_plan(last_assistant_text) and not looks_like_completion(last_assistant_text):
            return emit_cannot_audit(
                "No completion claim detected; most recent assistant turn appears "
                "to be a plan. Did you mean /audit-plan?"
            )
        if (not looks_like_completion(last_assistant_text)
                and last_assistant_record_idx is not None
                and not followed_by_change_tools(records, last_assistant_record_idx)):
            sys.stderr.write("[extract_session] note: no strong completion signal; "
                             "auditing the most recent assistant turn anyway.\n")

    bounding_idx = find_bounding_message(turns[:last_assistant_idx])
    user_request = turns[bounding_idx].content if turns else ""

    bounding_record_idx = 0
    seen_users = 0
    target_users = sum(1 for t in turns[:bounding_idx + 1] if t.role == "user")
    if target_users:
        for ridx, r in enumerate(records):
            if r.get("type") == "user" and not r.get("isSidechain"):
                msg = r.get("message") or {}
                inner = msg.get("content")
                if isinstance(inner, list) and all(
                    isinstance(b, dict) and b.get("type") == "tool_result"
                    for b in inner
                ):
                    continue
                seen_users += 1
                if seen_users == target_users:
                    bounding_record_idx = ridx
                    break

    tool_calls = extract_tool_calls(records, bounding_record_idx)

    ref_docs: list[tuple[str, str]] = []
    if reference_paths or reference_globs:
        ref_docs = gather_reference_docs(
            reference_paths or [],
            reference_globs or [],
            DEFAULT_REFERENCE_SKIP_NAMES,
        )
    ref_section = render_reference_section(ref_docs)

    artifacts = find_referenced_artifacts(last_assistant_text)
    if mode == "plan":
        body = render_plan_context(last_assistant_text, user_request, tool_calls, artifacts)
    else:
        body = render_completion_context(last_assistant_text, user_request, tool_calls, artifacts)
    return ref_section + body


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=("plan", "completion"), required=True)
    ap.add_argument(
        "--session-file",
        default=None,
        help="explicit session jsonl path (overrides CWD-based discovery, used by eval harness)",
    )
    ap.add_argument(
        "--reference-paths",
        default="",
        help="comma-separated reference doc paths to include in plan-critic context",
    )
    ap.add_argument(
        "--reference-glob",
        action="append",
        default=[],
        help="glob pattern for reference docs (can be repeated, e.g. core-docs/*.md)",
    )
    args = ap.parse_args()
    ref_paths = [p.strip() for p in args.reference_paths.split(",") if p.strip()]
    sys.stdout.write(run(args.mode, args.session_file, ref_paths, args.reference_glob))
    return 0


if __name__ == "__main__":
    sys.exit(main())
