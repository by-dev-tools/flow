#!/usr/bin/env python3
"""Lint skill-to-skill composition against `disable-model-invocation` (FB-0074).

A skill can instruct the agent to invoke another skill — `Skill("flow:land")` — and
that is flow's documented "composition, not reimplementation" idiom. But Claude Code's
`disable-model-invocation: true` frontmatter flag *blocks programmatic invocation*: the
skill is removed from the model's context entirely, so a `Skill()` call naming it is
rejected. The composition does not error loudly at author time and does not error
visibly at run time — it degrades to whatever fallback the caller documented, on every
single run. Nothing in the repo could catch it, because the two halves of the contract
live in different files: the call site in one SKILL.md, the flag in another's
frontmatter. That is the FB-0010 "fan-out contradiction" class exactly.

This lint closes it mechanically: parse every SKILL.md's frontmatter for its `name` +
`disable-model-invocation`, parse every documented `Skill("...")` call out of the prose,
and report any call whose target is model-invocation-disabled.

Scoping notes (deliberate, to keep false positives at zero):
  - Only `Skill("...")` / `Skill('...')` call forms count. Prose mentions of a skill
    (`/flow:land`, "run land") are NOT calls and are ignored — a skill telling a HUMAN
    to run a disabled skill is correct usage, not a violation.
  - Targets are matched on the bare skill name, with or without a namespace prefix
    (`flow:land` and `land` both resolve to the `land` skill), since the prefix depends
    on install context.
  - A call naming a skill that is not in the scanned directory is UNKNOWN, not a
    violation — a consumer may legitimately call a skill from another plugin. Reported
    separately so a typo is still visible.
  - **Only fenced code blocks are scanned.** That is where an executable call lives; a
    `Skill("x")` inside inline backticks is prose *about* a call, not a call. Without
    this split the lint flags the documentation warning against the very anti-pattern it
    detects — which it did, on the first run against this repo.

Exit codes: 0 clean (or only UNKNOWNs), 1 at least one violation, 2 usage/IO error.
Stdlib only. Python 3.7+.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# `Skill("ns:name")` or `Skill('name')`. The call form is what the runtime executes;
# a bare prose mention is not.
_SKILL_CALL_RE = re.compile(r"""Skill\(\s*["']([A-Za-z0-9_:\-]+)["']\s*\)""")

# Frontmatter scalars we care about. Matched line-anchored inside the leading `---`
# block only, so a prose mention of the flag further down the file is not read as a
# declaration (this file itself would otherwise trip the lint).
_NAME_RE = re.compile(r"^name:\s*(\S+)\s*$", re.MULTILINE)
_DMI_RE = re.compile(r"^disable-model-invocation:\s*(true|false)\s*$", re.MULTILINE)


def _frontmatter(text: str) -> str:
    """Return the leading `---`-delimited frontmatter block, or '' if absent."""
    if not text.startswith("---"):
        return ""
    end = text.find("\n---", 3)
    return text[3:end] if end != -1 else ""


def _bare(target: str) -> str:
    """`flow:land` -> `land`; `land` -> `land`."""
    return target.split(":")[-1]


def scan(skills_dir: Path) -> dict:
    """Build the skill table and the call graph. Pure — no printing."""
    skills = {}
    for skill_md in sorted(skills_dir.glob("*/SKILL.md")):
        text = skill_md.read_text(encoding="utf-8", errors="replace")
        fm = _frontmatter(text)
        name_m = _NAME_RE.search(fm)
        dmi_m = _DMI_RE.search(fm)
        name = name_m.group(1) if name_m else skill_md.parent.name
        skills[name] = {
            "path": skill_md,
            # Absent flag defaults to false, matching Claude Code's documented default.
            "disabled": bool(dmi_m and dmi_m.group(1) == "true"),
        }

    calls = []
    for name, info in skills.items():
        text = info["path"].read_text(encoding="utf-8", errors="replace")
        in_fence = False
        for lineno, line in enumerate(text.splitlines(), 1):
            if line.lstrip().startswith("```"):
                in_fence = not in_fence
                continue
            if not in_fence:
                continue  # prose / inline-code mention, not an executable call
            for m in _SKILL_CALL_RE.finditer(line):
                calls.append(
                    {"caller": name, "target": m.group(1), "line": lineno, "path": info["path"]}
                )
    return {"skills": skills, "calls": calls}


def classify(table: dict) -> tuple:
    """Split calls into (violations, unknowns). Self-calls are ignored."""
    skills = table["skills"]
    violations, unknowns = [], []
    for call in table["calls"]:
        bare = _bare(call["target"])
        if bare == call["caller"]:
            continue
        target = skills.get(bare)
        if target is None:
            unknowns.append(call)
        elif target["disabled"]:
            violations.append(call)
    return violations, unknowns


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="skill-composition-lint.py")
    ap.add_argument(
        "skills_dir",
        help="directory containing <skill>/SKILL.md (e.g. plugins/flow/skills)",
    )
    ap.add_argument(
        "--quiet-unknown",
        action="store_true",
        help="suppress the UNKNOWN-target report (cross-plugin calls)",
    )
    args = ap.parse_args(argv)

    root = Path(args.skills_dir)
    if not root.is_dir():
        sys.stderr.write(f"[skill-composition-lint] not a directory: {root}\n")
        return 2

    table = scan(root)
    if not table["skills"]:
        print(f"[skill-composition-lint] no SKILL.md found under {root} — nothing to lint.")
        return 0

    violations, unknowns = classify(table)
    n_skills, n_calls = len(table["skills"]), len(table["calls"])

    if not args.quiet_unknown:
        for c in unknowns:
            print(
                f"[skill-composition-lint] UNKNOWN — {c['caller']} calls "
                f"Skill(\"{c['target']}\") ({c['path']}:{c['line']}); target not in {root}. "
                "Fine if it lives in another plugin; a typo otherwise."
            )

    if not violations:
        print(
            f"[skill-composition-lint] PASS — {n_calls} Skill() call(s) across "
            f"{n_skills} skill(s); every target is model-invocable."
        )
        return 0

    for c in violations:
        print(
            f"[skill-composition-lint] FAIL — {c['caller']} calls Skill(\"{c['target']}\") at "
            f"{c['path']}:{c['line']}, but '{_bare(c['target'])}' sets "
            "disable-model-invocation: true, which blocks programmatic invocation. "
            "The call is rejected at runtime, so this composition silently degrades to its "
            "fallback on EVERY run. Fix: clear the flag on the callee, give it a "
            "model-invocable entrypoint, inline the step, or hand the step to the human "
            "explicitly instead of pretending to call it."
        )
    print(
        f"[skill-composition-lint] {len(violations)} violation(s) across {n_calls} "
        f"Skill() call(s) in {n_skills} skill(s)."
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
