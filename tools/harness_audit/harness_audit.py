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
                                      auto-loading .claude/rules/*.md, and the
                                      aggregate of every registered skill's
                                      and agent's frontmatter `description:`,
                                      which is what actually renders into
                                      every session's system reminder). The
                                      consumer-facing `docs/workflow.md` is
                                      NOT in this list -- nothing `@`-imports
                                      or auto-loads it; it is an invoked-per-
                                      use reference doc a skill may point a
                                      human at, not a Class A surface (see
                                      dev-docs/roadmap.md AB Step 1b, the
                                      2026-09 live-bug entry this fixes).
                  invoked-per-use -- paid only when that skill is invoked
                                      (the full body of every shipped
                                      plugins/flow/skills/*/SKILL.md --
                                      e.g. ship/SKILL.md, the heaviest single
                                      prompt in the repo, IS the context
                                      window for the duration of /flow:ship).
  --split       per-skill prose/shell/comment char split for every Class B
                (invoked-per-use) skill, using the counting rule: shell =
                content inside ```sh / ```bash fences (fence lines excluded);
                untagged and ```markdown fences count as prose. comment is
                the subset of shell chars whose line (stripped) starts with
                `#`.
  --ship-sections  per-`## `-section char split of ship/SKILL.md, each
                section classified PURE (reads, judges, reports -- forkable)
                / IMPURE (git commit/push, `gh pr create`, body/draft
                writes, the Step 8 human hand-off -- must stay in the
                parent) / AMBIGUOUS (a real mix, called out rather than
                forced into a bucket) / META (reference material, not a
                pipeline step). Feeds the Phase 4 fork-boundary decision in
                dev-docs/handoffs/session-efficiency-program.md -- this
                script does not make that decision, it only measures the
                pure/impure token split so a human can.

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


# ---------------------------------------------------------------- prose/shell/comment split
#
# Counting rule (dev-docs/handoffs/session-efficiency-program.md "Measurements",
# stated there because an earlier revision got it wrong and it moved two
# numbers): shell = content inside ```sh / ```bash fences, FENCE LINES
# EXCLUDED. Untagged fences and ```markdown fences count as PROSE -- counting
# any fence as shell inflated ship's shell share from 29% to 34%, because it
# carries three ```markdown PR-body templates and five untagged output
# samples that are prose (illustrative text), not shell.

_FENCE_LINE_RE = re.compile(r"^[ \t]*```(.*)$")
_SHELL_LANGS = frozenset({"sh", "bash"})


def compute_prose_shell_split(text: str) -> dict:
    """Returns char counts for the whole document: total, shell (inside
    sh/bash fences, fence delimiter lines excluded), prose (everything
    else -- including untagged/markdown fences and their delimiter lines),
    comment (the subset of shell chars whose stripped line starts with
    `#`), and warning (a loud note, or '', if the fence markers don't
    pair up -- see below).

    Markdown fences don't nest, so fence-marker lines (any line starting,
    after leading whitespace, with 3+ backticks) alternate open/close in
    document order -- paired positionally rather than with a single
    open...close regex, because this repo's prose is not always clean
    CommonMark (a closing ``` can carry trailing prose on the same line,
    e.g. ship/SKILL.md's Step 7a.5 block; a regex anchored on the closer
    being alone on its line silently drops that pair and any content
    between it and the next real close).

    An ODD total fence-marker count means an unclosed fence somewhere --
    `zip(fence_idx[0::2], fence_idx[1::2])` would then silently drop the
    trailing unpaired marker (and, worse, silently flip open/close parity
    for everything after an earlier unclosed one). Every shipped SKILL.md
    pairs evenly today, but a future edit that breaks a fence must surface
    loudly here rather than quietly mis-measuring (FB-0010 silent-skip
    class), so this is asserted, not merely hoped for."""
    total = len(text)
    lines = text.splitlines(keepends=True)
    fence_idx = [i for i, line in enumerate(lines) if _FENCE_LINE_RE.match(line)]

    warning = ""
    if len(fence_idx) % 2:
        warning = (
            f"odd number of fence-marker lines ({len(fence_idx)}) -- an unclosed "
            "``` fence exists; the trailing marker (and anything after an earlier "
            "unclosed one) was dropped from this split, not silently included"
        )

    shell = 0
    comment = 0
    for open_i, close_i in zip(fence_idx[0::2], fence_idx[1::2]):
        lang = _FENCE_LINE_RE.match(lines[open_i]).group(1).strip().lower()
        if lang not in _SHELL_LANGS:
            continue
        content_lines = lines[open_i + 1:close_i]
        shell += sum(len(line) for line in content_lines)
        comment += sum(len(line) for line in content_lines if line.strip().startswith("#"))
    prose = total - shell
    return {"total": total, "prose": prose, "shell": shell, "comment": comment, "warning": warning}


def _pct(part: int, total: int) -> float:
    return round(100.0 * part / total, 1) if total else 0.0


def resolve_invoked_surface_splits(repo_root: Path = _REPO_ROOT) -> tuple[list[dict], list[str]]:
    """Per-skill prose/shell/comment split for every Class B (invoked-per-use)
    surface -- the reproducible replacement for hand-run `wc -c`. Returns
    (entries, warnings); entries carry chars + percentages so the ±2% band
    in the session-efficiency plan's Spec-walk can be checked mechanically."""
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
        split = compute_prose_shell_split(text)
        if split["warning"]:
            warnings.append(f"{path.relative_to(repo_root)}: {split['warning']}")
        entries.append({
            "path": str(path.relative_to(repo_root)),
            "chars": split["total"],
            "prose_chars": split["prose"],
            "shell_chars": split["shell"],
            "comment_chars": split["comment"],
            "prose_pct": _pct(split["prose"], split["total"]),
            "shell_pct": _pct(split["shell"], split["total"]),
            "comment_pct_of_shell": _pct(split["comment"], split["shell"]),
        })
    return entries, warnings


def render_split_report(repo_root: Path = _REPO_ROOT) -> str:
    entries, warnings = resolve_invoked_surface_splits(repo_root)
    lines = ["Harness-weight audit -- per-skill prose/shell/comment split", ""]
    for e in sorted(entries, key=lambda e: -e["chars"]):
        lines.append(
            f"  {e['path']}: {e['chars']:,} chars -- "
            f"prose {e['prose_pct']}% ({e['prose_chars']:,}), "
            f"shell {e['shell_pct']}% ({e['shell_chars']:,}), "
            f"of which comment {e['comment_pct_of_shell']}% of shell ({e['comment_chars']:,})"
        )
    if warnings:
        lines.append("")
        lines.append(f"WARNING: {len(warnings)} surface(s) unreadable or empty:")
        for w in warnings:
            lines.append(f"  - {w}")
    return "\n".join(lines)


# ---------------------------------------------------------------- ship/SKILL.md pure/impure sections
#
# Precondition A of dev-docs/handoffs/session-efficiency-program.md Phase 4:
# nobody has inventoried which of ship's `## `-level steps CAN cross a fork
# boundary (PURE -- reads, judges, reports) vs. which carry side effects the
# parent must own (IMPURE -- git commit/push, `gh pr create`, PR body/draft
# writes, the Step 8 human hand-off). This is a curated classification, not a
# keyword heuristic: getting the pure fraction wrong sends that decision the
# wrong way, and a regex over "git commit" would both over- and under-fire
# (e.g. Step 2a's manifest writer touches git-adjacent scratch files but
# never commits). A heading not in the table is UNCLASSIFIED, loudly, rather
# than silently guessed at -- the FB-0010 fan-out shape applied to a curated
# table instead of a hardcoded list.
#
# Classified by reading plugins/flow/skills/ship/SKILL.md in full (2026-09,
# this PR), one entry per `## `-level (h2) heading -- `resolve_ship_section_breakdown`
# only extracts h2s, so an h3 sub-step's content and char count are folded into
# its parent h2's entry, not classified independently. Two sections are
# AMBIGUOUS on purpose rather than forced into a bucket:
#   - "1. Pre-flight" runs `git checkout -b` (creates/switches the branch --
#     a shared git-ref mutation, not a read) and the Step 1c mechanical
#     fix-and-retry loop (edits real files to make preflight pass). Both are
#     real side effects, just not ones named in the IMPURE example list.
#   - "2. Final-pass reviews" folds in its h3 sub-step "### 2a. Skip-legitimacy
#     audit" (line 356) -- fresh-context read-only, writes only to the
#     repo-local .flow/ scratch handoff, so it doesn't change the parent's
#     PURE label, but it is real content this classification silently
#     absorbs rather than vets independently. (An earlier revision of this
#     table carried a separate "2a. ..." key expecting it to match as its
#     own h2 entry; it never did -- `_H2_RE` doesn't see h3s -- so the key
#     was permanently dead code. Removed; noted here instead, the way 4c.iv
#     is noted on "4." below, so the same mistake isn't repeated.)
#   - "4. Synthesize session feedback (two layers)" is mostly judgment + local
#     doc/memory writes (PURE-shaped), but its h3 sub-step Step 4c.iv stages
#     the lesson-flush directory with `git add` -- a git-index mutation
#     embedded in an otherwise-forkable section.
# "Gotchas" and "Config slots" are reference material, not pipeline steps --
# labeled META and excluded from the pure/impure totals so they can't dilute
# the ratio the Phase 4 decision depends on.

_H2_RE = re.compile(r"^## (.+)$", re.MULTILINE)

SHIP_SECTION_CLASSIFICATION: dict[str, tuple[str, str]] = {
    "Project context (resolved at invocation)": (
        "PURE", "reads local repo/config state only (cat, git symbolic-ref, git branch --show-current)",
    ),
    "1. Pre-flight": (
        "AMBIGUOUS", "mixes read-only gates with `git checkout -b` and the Step 1c fix-and-retry file edits",
    ),
    "2. Final-pass reviews": (
        "PURE",
        "invokes the four reviewer skills and routes their findings; no git/gh side effects "
        "(includes the h3 sub-step 2a Skip-legitimacy audit, also PURE -- see comment above)",
    ),
    "3. Route follow-ups": (
        "PURE", "routes findings into plan/roadmap doc edits + a read-only typecheck re-run",
    ),
    "4. Synthesize session feedback (two layers)": (
        "AMBIGUOUS", "mostly judgment + local doc/memory writes, but Step 4c.iv runs `git add` to stage the lesson flush",
    ),
    "5. Update project docs": (
        "PURE", "doc edits + the 5b doc-currency gate; no git commit/push/gh calls",
    ),
    "6. Commit": ("IMPURE", "runs `git commit`"),
    "7. Push and PR": ("IMPURE", "runs `git push` and `gh pr create`/`gh pr edit`, writes the PR body/draft state"),
    "8. Hand off": ("IMPURE", "the human hand-off boundary; never forkable by definition"),
    "Gotchas": ("META", "reference notes, not a pipeline step"),
    "Config slots (narrative — JSON Schema lands PR 2)": ("META", "reference table, not a pipeline step"),
}


def resolve_ship_section_breakdown(repo_root: Path = _REPO_ROOT) -> tuple[list[dict], list[str]]:
    """Per-`## `-section char count + PURE/IMPURE/AMBIGUOUS/META classification
    for plugins/flow/skills/ship/SKILL.md. Returns (entries, warnings). A
    heading with no entry in SHIP_SECTION_CLASSIFICATION is classified
    UNCLASSIFIED with a loud warning -- never silently folded into PURE or
    IMPURE (FB-0010 fan-out shape)."""
    path = repo_root / "plugins" / "flow" / "skills" / "ship" / "SKILL.md"
    text = _read_text(path)
    if text is None:
        return [], [f"missing or unreadable ship skill: {path}"]

    headings = list(_H2_RE.finditer(text))
    entries: list[dict] = []
    warnings: list[str] = []
    for i, m in enumerate(headings):
        heading = m.group(1).strip()
        start = m.start()
        end = headings[i + 1].start() if i + 1 < len(headings) else len(text)
        section_text = text[start:end]
        label, rationale = SHIP_SECTION_CLASSIFICATION.get(
            heading, ("UNCLASSIFIED", "new/renamed heading not in the curated classification table -- flag for manual review")
        )
        if label == "UNCLASSIFIED":
            warnings.append(f"unclassified ship section heading (needs manual classification): {heading!r}")
        entries.append({"heading": heading, "chars": len(section_text), "label": label, "rationale": rationale})

    # The inverse of the UNCLASSIFIED check above: a table key that matched no
    # extracted heading is dead code silently providing no coverage (e.g. a
    # stale key left behind after a heading rename, or one that was never
    # reachable in the first place -- this is exactly how an earlier revision
    # of this table carried an orphaned "2a. ..." key expecting to match an
    # h3 sub-heading _H2_RE can't see). Flag it the same way: loudly, not
    # silently dropped.
    matched_headings = {e["heading"] for e in entries}
    orphaned = sorted(set(SHIP_SECTION_CLASSIFICATION) - matched_headings)
    for key in orphaned:
        warnings.append(f"orphaned classification-table entry (matches no heading in the file): {key!r}")
    return entries, warnings


def render_ship_sections_report(repo_root: Path = _REPO_ROOT) -> str:
    entries, warnings = resolve_ship_section_breakdown(repo_root)
    lines = ["Harness-weight audit -- ship/SKILL.md pure/impure section breakdown", ""]
    for e in entries:
        lines.append(f"  {e['chars']:>8,} chars  [{e['label']:>12}]  ## {e['heading']}  -- {e['rationale']}")

    totals: dict[str, int] = {}
    for e in entries:
        totals[e["label"]] = totals.get(e["label"], 0) + e["chars"]
    graded_total = sum(v for k, v in totals.items() if k != "META")
    lines.append("")
    for label in ("PURE", "IMPURE", "AMBIGUOUS", "UNCLASSIFIED", "META"):
        if label not in totals:
            continue
        chars = totals[label]
        if label == "META":
            lines.append(f"  {label}: {chars:,} chars (excluded from the pure/impure ratio)")
        else:
            lines.append(f"  {label}: {chars:,} chars ({_pct(chars, graded_total)}% of graded total)")
    lines.append("")
    lines.append(
        f"  Graded total (excludes META): {graded_total:,} chars. "
        "This ratio is the input to the Phase 4 fork-boundary decision "
        "(dev-docs/handoffs/session-efficiency-program.md Precondition A) -- "
        "this script measures it, it does not decide it."
    )

    if warnings:
        lines.append("")
        lines.append(f"WARNING: {len(warnings)} issue(s):")
        for w in warnings:
            lines.append(f"  - {w}")
    return "\n".join(lines)


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
    group.add_argument("--split", action="store_true", help="print the per-skill prose/shell/comment char split")
    group.add_argument(
        "--ship-sections", action="store_true",
        help="print ship/SKILL.md's per-section char counts + PURE/IMPURE/AMBIGUOUS/META classification",
    )
    args = parser.parse_args(argv)

    if args.audit_due:
        due, message = audit_due()
        print(message)
        return 1 if due else 0

    if args.split:
        print(render_split_report())
        return 0

    if args.ship_sections:
        print(render_ship_sections_report())
        return 0

    print(render_surfaces_report())
    return 0


if __name__ == "__main__":
    sys.exit(main())
