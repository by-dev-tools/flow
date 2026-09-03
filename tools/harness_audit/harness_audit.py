#!/usr/bin/env python3
"""Harness-weight audit mechanism (roadmap item AB, Step 1, FB-0095).

Dev tooling, not a shipped plugin artifact -- see CLAUDE.md § 3 "Project-dev
infrastructure". This script does NOT judge whether a surface still earns its
token cost -- that is best-effort LLM work, done by a fresh-context Explore
agent per dev-docs/workflow.md's "Harness-weight audit" section. This script
provides the two mechanical pieces that judgment needs:

  --audit-due   a periodic cadence gate (parallel to
                plugins/flow/tools/memory/check.mjs --audit-due), so the audit
                runs regularly without being forgotten.
  --surfaces    the resolved, inspectable list of surfaces to audit, split
                into two cost classes that must never be summed together:

                  always-loaded   -- paid every session (CLAUDE.md, the
                                      auto-loading .claude/rules/*.md, the
                                      consumer-facing workflow.md, and the
                                      aggregate of every registered skill's
                                      and agent's frontmatter `description:`,
                                      which is what actually renders into
                                      every session's system reminder).
                  invoked-per-use -- paid only when that skill is invoked
                                      (the full body of every shipped
                                      plugins/flow/skills/*/SKILL.md --
                                      e.g. ship/SKILL.md, the heaviest single
                                      prompt in the repo, IS the context
                                      window for the duration of /flow:ship).

Explicitly out of scope for this script (see dev-docs/plan.md "PR -- AB Step
1" Scope-out): actual token counting (roadmap item AB.3 builds a real
context-budget report; the "chars"/"lines" columns here are a cheap size
proxy for triage, not a token estimate), any pruning of flagged content, and
any judgment about ship-pipeline gates/steps (deferred to AB.1b -- gates need
per-gate regression evidence a generic surface scan can't provide).

Deletion criterion (FB-0088): retire this script if a later PR promotes the
capability into a shipped /flow:* mechanism, or if three consecutive audits
find nothing actionable.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_MARKER_PATH = Path(__file__).resolve().parent / ".last-audit"
AUDIT_INTERVAL = 5  # merged PRs to origin/main between audits. Same NAME and
                     # value as plugins/flow/tools/memory/check.mjs's
                     # AUDIT_INTERVAL, but NOT the same measurement -- that one
                     # counts ship-skill invocations, this one counts git
                     # commits. Two independent constants that happen to agree
                     # today; nothing enforces they stay in sync if either is
                     # retuned.

_FRONTMATTER_DESC_RE = re.compile(
    r'^description:\s*(?:[>|][-+]?\s*\n((?:^\s{2,}.+\n?)+)|(.*))', re.MULTILINE
)


def _run_git(args: list[str], repo_root: Path) -> tuple[str | None, str]:
    """Returns (stdout-on-success-or-None, a one-line reason for a human to
    debug a degraded cadence check with -- the process's stderr, or the
    exception text if git itself couldn't be invoked)."""
    try:
        result = subprocess.run(
            ["git", *args], cwd=repo_root, capture_output=True, text=True, timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return None, str(exc)
    if result.returncode != 0:
        return None, result.stderr.strip().splitlines()[-1] if result.stderr.strip() else f"git exited {result.returncode}"
    return result.stdout.strip(), ""


def _current_main_sha(repo_root: Path) -> tuple[str | None, str]:
    sha, reason = _run_git(["rev-parse", "origin/main"], repo_root)
    if sha:
        return sha, ""
    return _run_git(["rev-parse", "main"], repo_root)


def audit_due(repo_root: Path = _REPO_ROOT, marker_path: Path = _MARKER_PATH) -> tuple[bool, str]:
    """Returns (due, message). Never raises -- a git failure degrades to a
    loud 'cannot determine cadence' message and NOT due, rather than either
    crashing or silently claiming a false due/not-due (FB-0010 silent-skip).
    repo_root/marker_path are parameterized so the eval harness can point
    this at a throwaway fixture repo instead of mutating the real marker."""
    current_sha, reason = _current_main_sha(repo_root)
    if current_sha is None:
        return False, f"cannot determine cadence -- no git repo / no origin/main reachable ({reason}); skipping audit-due check"

    if not marker_path.is_file():
        marker_path.write_text(current_sha + "\n", encoding="utf-8")
        return True, "audit due (first run -- no prior marker)"

    marker_sha = marker_path.read_text(encoding="utf-8").strip()
    if not marker_sha:
        marker_path.write_text(current_sha + "\n", encoding="utf-8")
        return True, "audit due (empty marker file, treated as first run)"

    count_str, reason = _run_git(["rev-list", "--count", f"{marker_sha}..{current_sha}"], repo_root)
    if count_str is None:
        return False, f"cannot determine cadence -- marker SHA {marker_sha[:12]} not reachable from current history ({reason}); skipping audit-due check"

    count = int(count_str)
    if count >= AUDIT_INTERVAL:
        marker_path.write_text(current_sha + "\n", encoding="utf-8")
        return True, f"audit due ({count} commits since last audit, interval {AUDIT_INTERVAL})"
    return False, f"audit not due ({count}/{AUDIT_INTERVAL} commits since last audit)"


def _read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def _extract_frontmatter_description(text: str) -> str:
    """Pull the `description:` value out of a SKILL.md/agent .md frontmatter
    block. Handles both the plain `description: one line` form and the
    folded-block `description: >` / `description: >-` form used by several
    flow skills. Returns '' (not None) on no match -- an empty description
    contributes zero chars, which is honest, rather than a crash."""
    match = _FRONTMATTER_DESC_RE.search(text)
    if not match:
        return ""
    block, inline = match.groups()
    if block is not None:
        return " ".join(line.strip() for line in block.splitlines() if line.strip())
    return (inline or "").strip()


def _surface_entry(path: Path, text: str, repo_root: Path) -> dict:
    return {
        "path": str(path.relative_to(repo_root)),
        "chars": len(text),
        "lines": text.count("\n") + 1,
    }


def resolve_always_loaded_surfaces(repo_root: Path = _REPO_ROOT) -> tuple[list[dict], list[str]]:
    """Class A: paid every session. Static docs read whole; skills/agents
    contribute only their frontmatter `description:` (the part that actually
    renders into every session's system reminder -- see module docstring).
    Returns (entries, warnings) -- a missing file warns, never crashes."""
    entries: list[dict] = []
    warnings: list[str] = []

    static_paths = [
        repo_root / "CLAUDE.md",
        repo_root / "plugins" / "flow" / "docs" / "workflow.md",
        *sorted((repo_root / ".claude" / "rules").glob("*.md")),
    ]
    for path in static_paths:
        text = _read_text(path)
        if text is None:
            warnings.append(f"missing or unreadable always-loaded surface: {path}")
            continue
        entries.append(_surface_entry(path, text, repo_root))

    description_globs = [
        (repo_root / "plugins" / "flow" / "skills", "*/SKILL.md"),
        (repo_root / ".claude" / "skills", "*/SKILL.md"),
        (repo_root / "plugins" / "flow" / "agents", "*.md"),
        (repo_root / ".claude" / "agents", "*.md"),
    ]
    for base, subglob in description_globs:
        for path in sorted(base.glob(subglob)):
            text = _read_text(path)
            if text is None:
                warnings.append(f"missing or unreadable frontmatter source: {path}")
                continue
            desc = _extract_frontmatter_description(text)
            if not desc:
                warnings.append(f"no frontmatter description found (contributes 0 chars): {path}")
                continue
            label = path.relative_to(repo_root)
            entries.append({"path": f"{label} (description only)", "chars": len(desc), "lines": 1})

    return entries, warnings


def resolve_invoked_surfaces(repo_root: Path = _REPO_ROOT) -> tuple[list[dict], list[str]]:
    """Class B: paid only when that skill is invoked -- the full body of
    every shipped plugins/flow/skills/*/SKILL.md. Project-dev skills
    (.claude/skills/*) are excluded: they're not shipped to consumers, so
    they aren't part of flow's own harness weight in the sense this audit
    cares about. Returns (entries, warnings)."""
    entries: list[dict] = []
    warnings: list[str] = []
    skills_dir = repo_root / "plugins" / "flow" / "skills"
    if not skills_dir.is_dir():
        warnings.append(f"missing shipped skills directory: {skills_dir}")
        return entries, warnings
    for path in sorted(skills_dir.glob("*/SKILL.md")):
        text = _read_text(path)
        if text is None:
            warnings.append(f"missing or unreadable invoked-skill body: {path}")
            continue
        entries.append(_surface_entry(path, text, repo_root))
    return entries, warnings


def _render_class(header: str, entries: list[dict], total_label: str) -> list[str]:
    out = [header]
    for e in sorted(entries, key=lambda e: -e["chars"]):
        out.append(f"  {e['chars']:>8,} chars  {e['lines']:>6,} lines  {e['path']}")
    out.append(f"  {total_label}: {sum(e['chars'] for e in entries):,} chars across {len(entries)} entries")
    return out


def render_surfaces_report(repo_root: Path = _REPO_ROOT) -> str:
    always_loaded, warnings_a = resolve_always_loaded_surfaces(repo_root)
    invoked, warnings_b = resolve_invoked_surfaces(repo_root)

    lines = ["Harness-weight audit -- surface inventory (AB Step 1)", ""]
    lines += _render_class(
        "Class A -- always-loaded (paid every session):", always_loaded,
        total_label="Class A total (a real per-session cost -- these all load together)",
    )
    lines.append("")
    lines += _render_class(
        "Class B -- invoked-per-use (paid only when that skill runs):", invoked,
        total_label="Class B sum (NOT a real cost -- these load one at a time, never together)",
    )
    lines.append("")
    lines.append(
        "Class A and Class B are DIFFERENT cost models (per-session vs. "
        "per-invocation) and are never summed above -- see module docstring."
    )

    warnings = warnings_a + warnings_b
    if warnings:
        lines.append("")
        lines.append(f"WARNING: {len(warnings)} surface(s) unreadable or empty:")
        for w in warnings:
            lines.append(f"  - {w}")

    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--audit-due", action="store_true",
        help="check + advance the periodic cadence marker (mutating, not a peek); "
             "exit 1 = due, exit 0 = not due -- inverted from ordinary shell success",
    )
    group.add_argument("--surfaces", action="store_true", help="print the resolved surface inventory")
    args = parser.parse_args(argv)

    if args.audit_due:
        due, message = audit_due()
        print(message)
        return 1 if due else 0

    print(render_surfaces_report())
    return 0


if __name__ == "__main__":
    sys.exit(main())
