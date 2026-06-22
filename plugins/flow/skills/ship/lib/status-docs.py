#!/usr/bin/env python3
"""statusDocs helper — pure-text operations on project-declared status surfaces.

Consumed by `/flow:ship` Step 5b (doc-currency marker-coverage gate) and
`/flow:doctor` Check 2.7. Keeps the marker-region logic in ONE place instead of
duplicating awk across 5a / 5b / doctor (the FB-0010 "consistency depends on
author memory" class). Git operations stay in the calling shell; this script is
pure text so it is unit-testable (evals/run_status_docs_evals.py).

A `statusDocs` entry declares a status-bearing surface and the marker that fences
the region to reconcile:

    { "path": "CLAUDE.md", "marker": "flow:status" }

The fenced region is the text between the HTML-comment fences
`<!-- {marker} -->` … `<!-- /{marker} -->`. `marker` is optional and defaults to
`flow:status`. HTML comments are invisible in rendered Markdown, so the fences do
not disturb a consumer's CLAUDE.md / README.

Subcommands (stdlib only):

    status-docs.py entries <config.json>
        For each entry in `.statusDocs` (default []), print "<marker>\\t<path>".
        Empty/absent statusDocs → no output, exit 0.
        Malformed JSON, non-array statusDocs, or an entry missing `path` →
        loud stderr + exit 1 (never a silent skip).

    status-docs.py region <marker> <file>
        Print the region between the marker fences (exclusive of the fence
        lines). `file` may be "-" to read stdin (used to diff a base revision
        piped via `git show`). Missing open OR close fence, or an unreadable
        file → stderr + exit 2.

    status-docs.py section <heading> <file>
        Print the lines under the first line CONTAINING <heading>, up to (but
        excluding) the next `## ` level-2 heading. `file` may be "-" for stdin.
        Heading absent → empty output, exit 0. This matches the `sect()` awk the
        Step 5b version-token gate uses, so Step 5b can detect "did the plan
        'Current Focus' / roadmap 'Now' section move?" through the same tested
        text path as the marker regions instead of a duplicated inline awk.

    status-docs.py check <config.json>
        For each entry assert the file exists AND both fences are present.
        Prints one line per entry: "OK <path>", "MISSING-FILE <path>", or
        "MISSING-MARKER <path> (<marker>)". Exit 0 iff all entries OK (or none
        declared); exit 1 if any problem.

Exit codes are the contract the shell keys on; keep them stable.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

DEFAULT_MARKER = "flow:status"


def _fences(marker: str) -> tuple[str, str]:
    return f"<!-- {marker} -->", f"<!-- /{marker} -->"


def load_entries(config_path: str) -> list[dict]:
    """Parse `.statusDocs` from a flow.config.json. Loud on malformed input.

    Returns a list of {"path": str, "marker": str} dicts (marker defaulted).
    Absent/empty statusDocs → []. Raises ValueError on anything malformed so the
    caller surfaces a BLOCKER rather than silently skipping the gate.
    """
    try:
        raw = Path(config_path).read_text()
    except OSError as e:
        raise ValueError(f"cannot read config {config_path}: {e}") from e
    try:
        cfg = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"{config_path} is not valid JSON: {e}") from e
    if not isinstance(cfg, dict):
        raise ValueError(f"{config_path} top level is not a JSON object")

    sd = cfg.get("statusDocs", [])
    if sd is None:
        return []
    if not isinstance(sd, list):
        raise ValueError("statusDocs must be an array (got "
                         f"{type(sd).__name__})")
    out = []
    for i, entry in enumerate(sd):
        if not isinstance(entry, dict):
            raise ValueError(f"statusDocs[{i}] must be an object with a 'path'")
        path = entry.get("path")
        if not path or not isinstance(path, str):
            raise ValueError(f"statusDocs[{i}] is missing a string 'path'")
        marker = entry.get("marker") or DEFAULT_MARKER
        if not isinstance(marker, str):
            raise ValueError(f"statusDocs[{i}].marker must be a string")
        out.append({"path": path, "marker": marker})
    return out


def extract_region(text: str, marker: str) -> str | None:
    """Return the text between the marker fences, or None if either is missing.

    Line-based: the open fence is the first line containing `<!-- {marker} -->`;
    the close fence is the first subsequent line containing `<!-- /{marker} -->`.
    The open-fence substring never matches the close-fence line (the close has a
    leading `/`), so the two are unambiguous.
    """
    open_f, close_f = _fences(marker)
    lines = text.splitlines()
    start = None
    for idx, line in enumerate(lines):
        if open_f in line:
            start = idx
            break
    if start is None:
        return None
    end = None
    for idx in range(start + 1, len(lines)):
        if close_f in lines[idx]:
            end = idx
            break
    if end is None:
        return None
    return "\n".join(lines[start + 1:end])


def extract_section(text: str, heading: str) -> str:
    """Return the lines under the first line containing `heading`, up to (but
    excluding) the next `## ` level-2 heading. Mirrors the `sect()` awk used by
    the version-token gate: `index($0,H){f=1;next} f&&/^## /{exit} f`. Heading
    absent → "".
    """
    out = []
    started = False
    for line in text.splitlines():
        if not started:
            if heading in line:
                started = True
            continue
        if line.startswith("## "):
            break
        out.append(line)
    return "\n".join(out)


def _read_file_or_stdin(path: str) -> str:
    if path == "-":
        return sys.stdin.read()
    return Path(path).read_text()


def cmd_entries(config_path: str) -> int:
    for e in load_entries(config_path):
        print(f"{e['marker']}\t{e['path']}")
    return 0


def cmd_region(marker: str, file_path: str) -> int:
    try:
        text = _read_file_or_stdin(file_path)
    except OSError as e:
        print(f"[status-docs] cannot read {file_path}: {e}", file=sys.stderr)
        return 2
    region = extract_region(text, marker)
    if region is None:
        print(f"[status-docs] marker fences <!-- {marker} --> … "
              f"<!-- /{marker} --> not found in {file_path}", file=sys.stderr)
        return 2
    # Print without an extra trailing newline beyond the region's own content,
    # so a byte-for-byte diff against a base revision is meaningful.
    sys.stdout.write(region)
    if region and not region.endswith("\n"):
        sys.stdout.write("\n")
    return 0


def cmd_section(heading: str, file_path: str) -> int:
    try:
        text = _read_file_or_stdin(file_path)
    except OSError as e:
        print(f"[status-docs] cannot read {file_path}: {e}", file=sys.stderr)
        return 2
    section = extract_section(text, heading)
    sys.stdout.write(section)
    if section and not section.endswith("\n"):
        sys.stdout.write("\n")
    return 0


def cmd_check(config_path: str) -> int:
    entries = load_entries(config_path)
    problems = 0
    if not entries:
        print("OK (no statusDocs declared)")
        return 0
    for e in entries:
        path, marker = e["path"], e["marker"]
        try:
            text = Path(path).read_text()
        except OSError:
            print(f"MISSING-FILE {path}")
            problems += 1
            continue
        if extract_region(text, marker) is None:
            print(f"MISSING-MARKER {path} ({marker})")
            problems += 1
        else:
            print(f"OK {path}")
    return 1 if problems else 0


USAGE = (
    "usage: status-docs.py entries <config.json>\n"
    "       status-docs.py region <marker> <file|->\n"
    "       status-docs.py section <heading> <file|->\n"
    "       status-docs.py check <config.json>"
)


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(USAGE, file=sys.stderr)
        return 64
    sub = argv[1]
    try:
        if sub == "entries" and len(argv) == 3:
            return cmd_entries(argv[2])
        if sub == "region" and len(argv) == 4:
            return cmd_region(argv[2], argv[3])
        if sub == "section" and len(argv) == 4:
            return cmd_section(argv[2], argv[3])
        if sub == "check" and len(argv) == 3:
            return cmd_check(argv[2])
    except ValueError as e:
        print(f"[status-docs] {e}", file=sys.stderr)
        return 1
    print(USAGE, file=sys.stderr)
    return 64


if __name__ == "__main__":
    sys.exit(main(sys.argv))
