#!/usr/bin/env python3
"""statusSurfaceCandidates helper — DISCOVER undeclared status-bearing surfaces.

Companion to `status-docs.py` (which handles DECLARED surfaces — Tier 2). This
script handles DISCOVERY (Tier 1): the well-known agent-orientation files that
auto-load into a fresh session and commonly carry forward-looking status
(CLAUDE.md, AGENTS.md, README.md, …) but that a project never opted into
`statusDocs`. An undeclared orientation doc is invisible to the whole
doc-currency pipeline — Step 5a touches nothing, Step 5b prints "none declared",
doctor 2.7 has nothing to check — so its status line silently rots after a merge
(the dogfood: a merged sub-PR left CLAUDE.md reading "3c is next (not started)").

This is the MECHANICAL half. It emits the candidate files that EXIST and are NOT
already declared in `statusDocs`, plus a bounded status-bearing SLICE of each so
the `/flow:ship` Step 5a.5 LLM judge gets a small window (not the whole file) to
decide drift. It never edits anything and never judges drift itself — the
best-effort drift call (backstopped by the human at the merge gate) is the
agent's, per the same route-to-draft discipline as `/flow:audit-coverage`.

Git operations stay in the calling shell (as in status-docs.py); this script is
pure text so it is unit-testable (evals/run_status_surface_evals.py).

Default candidate list (schema `statusSurfaceCandidates`, overridable per
project) — conservative, well-known auto-loading orientation files only:

    CLAUDE.md, AGENTS.md, README.md, GEMINI.md, .cursorrules,
    .github/copilot-instructions.md

The drift check (LLM, Step 5a.5), NOT the file list, is what holds false
positives down — keep the list to files that genuinely auto-orient an agent.

Subcommands (stdlib only):

    status-surface-scan.py candidates <config.json>
        Print one path per line: each `statusSurfaceCandidates` entry that
        EXISTS on disk and is NOT already declared in `statusDocs` (declared
        surfaces are Tier 2 — handled by Step 5a, never re-discovered here).
        No candidates → no output, exit 0. Malformed config → loud stderr,
        exit 1 (never a silent skip — the FB-0010 class this closes).

    status-surface-scan.py slice <file>
        Print a bounded, line-numbered slice of the status-bearing lines in
        <file> (keyword-matched lines + a little context, merged + capped) so a
        drift judge reads a small window and can quote verbatim. `file` may be
        "-" for stdin. A file with no status-looking lines → empty output,
        exit 0.

    status-surface-scan.py scan <config.json>
        The Step 5a.5 driver. Prints a header line naming the N undeclared
        candidates present, then one delimited block per candidate carrying its
        slice. N may be 0 (header only). Malformed config → loud stderr, exit 1.

Exit codes are the contract the shell keys on; keep them stable.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# Conservative default — mirrors schema `statusSurfaceCandidates.default`. Kept
# in sync deliberately (FB-0010 fan-out: the eval asserts parity with the schema).
DEFAULT_CANDIDATES = [
    "CLAUDE.md",
    "AGENTS.md",
    "README.md",
    "GEMINI.md",
    ".cursorrules",
    ".github/copilot-instructions.md",
]

# Words that mark a line as *forward-looking status* worth a drift look. The
# extractor is deliberately broad (recall over precision) — it only BOUNDS the
# slice; the LLM judge decides drift. Matched case-insensitively on word
# boundaries, plus the "▶" next-pointer glyph used across flow's own docs.
STATUS_KEYWORDS = [
    r"next", r"upcoming", r"in[\s-]?progress", r"not[\s-]?started", r"todo",
    r"current(?:ly)?", r"phase", r"now", r"shipped", r"wip", r"underway",
    r"planned", r"roadmap", r"milestone", r"status", r"focus", r"in[\s-]?flight",
]
_KW_RE = re.compile(r"(?i)\b(?:" + "|".join(STATUS_KEYWORDS) + r")\b")
_GLYPH_RE = re.compile(r"[▶►▷]")

CONTEXT = 1        # lines of context kept around each matched line
MAX_SLICE_LINES = 60   # per-file cap on emitted slice lines (bounded window)


def _is_status_line(line: str) -> bool:
    return bool(_KW_RE.search(line) or _GLYPH_RE.search(line))


def load_declared_paths(cfg: dict) -> set[str]:
    """Return the set of `statusDocs[].path` values (the Tier-2 surfaces).

    Reuses no state from status-docs.py to stay independent, but mirrors its
    tolerance: a malformed statusDocs raises so the caller surfaces it loudly
    rather than under-counting declared surfaces (which would re-discover a
    surface that is actually declared).
    """
    sd = cfg.get("statusDocs", [])
    if sd is None:
        return set()
    if not isinstance(sd, list):
        raise ValueError(f"statusDocs must be an array (got {type(sd).__name__})")
    out = set()
    for i, entry in enumerate(sd):
        if not isinstance(entry, dict):
            raise ValueError(f"statusDocs[{i}] must be an object with a 'path'")
        path = entry.get("path")
        if not path or not isinstance(path, str):
            raise ValueError(f"statusDocs[{i}] is missing a string 'path'")
        out.add(path)
    return out


def load_candidate_list(cfg: dict) -> list[str]:
    """Resolve the candidate globs/paths: config override else the default list.

    An explicit empty array is honored (a project may opt out of discovery). A
    non-array is loud (never a silent fall-through to the default, which would
    mask a config typo).
    """
    ssc = cfg.get("statusSurfaceCandidates")
    if ssc is None:
        return list(DEFAULT_CANDIDATES)
    if not isinstance(ssc, list):
        raise ValueError(
            f"statusSurfaceCandidates must be an array (got {type(ssc).__name__})")
    out = []
    for i, entry in enumerate(ssc):
        if not isinstance(entry, str) or not entry:
            raise ValueError(
                f"statusSurfaceCandidates[{i}] must be a non-empty string")
        out.append(entry)
    return out


def _load_config(config_path: str) -> dict:
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
    return cfg


def undeclared_candidates(config_path: str) -> list[str]:
    """Candidates that EXIST on disk and are NOT declared in statusDocs.

    Paths resolve relative to the current working directory (repo root, where
    /flow:ship runs). Order follows the candidate list for stable output.
    """
    cfg = _load_config(config_path)
    declared = load_declared_paths(cfg)
    out = []
    for cand in load_candidate_list(cfg):
        if cand in declared:
            continue
        if Path(cand).is_file():
            out.append(cand)
    return out


def status_slice(text: str) -> list[str]:
    """Bounded, line-numbered slice of the status-bearing lines of `text`.

    Keeps each keyword/glyph-matched line plus CONTEXT lines around it, merges
    overlapping windows, preserves file order, and caps at MAX_SLICE_LINES so a
    huge README can't blow the judge's window. Returns "<n>: <line>" strings
    (1-based line numbers) so the judge can quote the stale claim verbatim.
    """
    lines = text.splitlines()
    keep = [False] * len(lines)
    for idx, line in enumerate(lines):
        if _is_status_line(line):
            lo = max(0, idx - CONTEXT)
            hi = min(len(lines), idx + CONTEXT + 1)
            for j in range(lo, hi):
                keep[j] = True
    out = []
    for idx, flag in enumerate(keep):
        if not flag:
            continue
        out.append(f"{idx + 1}: {lines[idx]}")
        if len(out) >= MAX_SLICE_LINES:
            out.append(f"… (slice capped at {MAX_SLICE_LINES} lines; "
                       "open the file for the rest)")
            break
    return out


def _read_file_or_stdin(path: str) -> str:
    if path == "-":
        return sys.stdin.read()
    return Path(path).read_text()


def cmd_candidates(config_path: str) -> int:
    for p in undeclared_candidates(config_path):
        print(p)
    return 0


def cmd_slice(file_path: str) -> int:
    try:
        text = _read_file_or_stdin(file_path)
    except OSError as e:
        print(f"[status-surface] cannot read {file_path}: {e}", file=sys.stderr)
        return 2
    for line in status_slice(text):
        print(line)
    return 0


def cmd_scan(config_path: str) -> int:
    cands = undeclared_candidates(config_path)
    if not cands:
        print("[status-surface] 0 undeclared candidate(s) present — "
              "nothing to scan.")
        return 0
    print(f"[status-surface] {len(cands)} undeclared candidate(s) present: "
          + ", ".join(cands))
    for cand in cands:
        try:
            text = Path(cand).read_text()
        except OSError as e:
            print(f"----- status-surface candidate: {cand} -----")
            print(f"[status-surface] cannot read {cand}: {e}", file=sys.stderr)
            continue
        sl = status_slice(text)
        print(f"----- status-surface candidate: {cand} -----")
        if sl:
            print("\n".join(sl))
        else:
            print("(no status-looking lines found — likely nothing to reconcile)")
    return 0


USAGE = (
    "usage: status-surface-scan.py candidates <config.json>\n"
    "       status-surface-scan.py slice <file|->\n"
    "       status-surface-scan.py scan <config.json>"
)


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(USAGE, file=sys.stderr)
        return 64
    sub = argv[1]
    try:
        if sub == "candidates" and len(argv) == 3:
            return cmd_candidates(argv[2])
        if sub == "slice" and len(argv) == 3:
            return cmd_slice(argv[2])
        if sub == "scan" and len(argv) == 3:
            return cmd_scan(argv[2])
    except ValueError as e:
        print(f"[status-surface] {e}", file=sys.stderr)
        return 1
    print(USAGE, file=sys.stderr)
    return 64


if __name__ == "__main__":
    sys.exit(main(sys.argv))
