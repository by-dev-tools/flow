#!/usr/bin/env python3
"""The rule-skill roster and contract -- one definition, four readers (FB-0124).

A **rule-skill** is background knowledge Claude loads by judgment from its description,
not a command anyone invokes by name. A Claude Code plugin cannot ship `.claude/rules/*.md`
at all (`rules/` is not a plugin component), so this is the only mechanism available for
plugin-shipped rules. The contract that makes it work:

  POSITIVE  a non-empty `description:`            -- the description IS the trigger
  POSITIVE  `user-invocable: false`               -- "Description always in context,
                                                     full skill loads when invoked"
  NEGATIVE  no `paths:`                           -- it LIMITS a description-driven
                                                     activation, so it can only gate the
                                                     trigger, never create one
  NEGATIVE  no `disable-model-invocation: true`   -- "Description not in context" would
                                                     forbid the only path that works
  NEGATIVE  no suppressant text in the description -- "Not user-invocable -- path-activated
                                                     only." told the model the skill was not
                                                     its to invoke, for 17 releases

**Why this file exists rather than five copies.** Before it, the roster was hardcoded in
`run_plugin_desc_evals.py`, `run_plugin_provenance_evals.py`, and twice in
`doctor/SKILL.md`, and the predicate was expressed independently in Python (the eval), in
shell (doctor's Check 3.2), and partially in `plugin-provenance.py:_is_rule_skill`. Adding
or renaming a rule-skill meant edits in five places with nothing to catch a miss -- the
FB-0010 item-2 fan-out class, reproduced inside the PR written to fix an instance of it.
Both `/simplify` cleanup lenses flagged it independently.

It also fixes a subtler defect the simplification lens named: the eval was pinning a
*reimplementation* of doctor's claim rather than the code doctor runs, so a divergence
between them would have been invisible. That is `.claude/rules/general.md` item 4's
corollary -- pin a claim at the layer where it is CLAIMED -- and this module is the layer.

Readers: `skills/ship/lib/plugin-provenance.py`, `evals/run_plugin_desc_evals.py`,
`evals/run_plugin_provenance_evals.py`, and `skills/doctor/SKILL.md` Check 3.2 (via the
`check` CLI below). Stdlib only.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

#: The four portable rule-skills flow ships. Adding one means adding it HERE, once.
RULE_SKILLS: tuple[str, ...] = ("general", "plan-discipline", "documentation", "exploration")

#: The marker that identifies a rule-skill. Also what `plugin-provenance.py` classifies by:
#: a rule-skill and a command skill fail DIFFERENTLY when absent from the installed tree,
#: and attaching the command consequence to a rule-skill states something untrue of it.
MARKER = re.compile(r"^user-invocable:\s*false\b", re.MULTILINE)

#: The sentence that suppressed the trigger from v1.33.0 to v1.49.0.
SUPPRESSANT = re.compile(r"path-activated|Not user-invocable", re.IGNORECASE)

_PATHS = re.compile(r"^\s*paths\s*:", re.MULTILINE)
_DMI = re.compile(r"^disable-model-invocation:\s*true\b", re.MULTILINE)
_DESC = re.compile(r"^description:", re.MULTILINE)

#: A description must say WHEN to use the skill, not only what it does -- the docs'
#: § "Writing effective descriptions" requires both halves.
TRIGGER_CLAUSE = re.compile(r"\bUse (when|before|at)\b|\bLoad (when|before)\b", re.IGNORECASE)

#: Two documented caps, two different mechanisms, both binding:
#:   1,024 -- hard validation on `description` alone (Agent Skills spec, platform.claude.com
#:            .../agent-skills/best-practices)
#:   1,536 -- truncation of `description` + `when_to_use` in the skill LISTING
#:            (code.claude.com/docs/en/skills § Frontmatter reference)
DESC_HARD_CAP = 1024
LISTING_CAP = 1536


def frontmatter(text: str) -> str | None:
    """The frontmatter block of a SKILL.md, or None when there isn't a well-formed one.

    Returns everything above the closing fence, so a `paths:` or `user-invocable`
    mentioned in PROSE cannot promote a command skill.

    An UNTERMINATED fence returns None, not the whole file. Returning the file voided that
    guarantee in exactly the case where the file is broken: body prose could then supply a
    `paths:` (false FAIL) or a malformed skill could read compliant (false PASS). `None`
    surfaces as `no-frontmatter`, which is the honest answer.
    """
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    return text[:end] if end != -1 else None


def scalar(fm: str, key: str) -> str | None:
    """A frontmatter scalar, folding the `key: >-` / `key: >` block form onto one line.

    Tolerates any block-scalar indicator and any indent, because hardcoding `>-` plus a
    two-space indent silently yielded the indicator itself as the value.
    """
    # `[-+0-9]*` not `[-+]?[0-9]*`: YAML allows indent-then-chomp (`>2-`) as well as
    # `>-2`, and the narrower form returned the literal indicator as the value.
    # `(?:[ \t]*\n)*` inside the continuation allows blank lines within a folded block,
    # which otherwise truncated the value at the first paragraph break and under-counted
    # both caps.
    m = re.search(
        rf"^{re.escape(key)}:[ \t]*[>|][-+0-9]*[ \t]*\n((?:(?:[ \t]+\S.*|[ \t]*)\n?)+?)"
        rf"(?=^\S|\Z)",
        fm + "\n", re.MULTILINE)
    if m:
        return " ".join(line.strip() for line in m.group(1).splitlines() if line.strip())
    m = re.search(rf"^{re.escape(key)}:[ \t]*(.+)$", fm, re.MULTILINE)
    return m.group(1).strip() if m else None


def is_rule_skill(name: str) -> bool:
    """True when `name` is one of flow's rule-skills. The ROSTER is the definition.

    Deliberately NOT a frontmatter test. Keying this on `MARKER` would relocate the exact
    fragility FB-0124 removed rather than fixing it: if a roster member lost
    `user-invocable: false`, `violations()` would correctly report
    `not-user-invocable-false` (a FAIL) while a marker-keyed classifier silently returned
    False and `plugin-provenance.py` printed the COMMAND-skill consequence — "a model asked
    to run one would wrongly conclude it does not exist" — which its own docstring calls
    "something simply untrue of it". Two definitions of rule-skill-hood that agree only
    while the flag happens to be set is the `paths:` bug with a new marker.

    So: the roster defines membership, and `MARKER` is one of the things `violations()`
    asserts ABOUT a member. One definition, and no frontmatter edit can reclassify a skill
    behind the reporter's back. (Flagged by /simplify's altitude lens.)
    """
    return name in RULE_SKILLS


def violations(text: str | None) -> list[str]:
    """Every way this SKILL.md breaks the rule-skill contract. Empty list == compliant.

    Each NEGATIVE is paired with a POSITIVE, because a prohibition satisfiable by deletion
    is not a check (`.claude/rules/general.md` item 3): "no suppressant in the description"
    passes just as well when the description, or the whole file, is gone. `missing` and
    `no-description` are what give the negatives meaning.
    """
    if text is None:
        return ["missing"]
    fm = frontmatter(text)
    if fm is None:
        return ["no-frontmatter"]
    out: list[str] = []
    if not _DESC.search(fm):
        out.append("no-description")
    if not MARKER.search(fm):
        out.append("not-user-invocable-false")
    if _PATHS.search(fm):
        out.append("has-paths")
    if _DMI.search(fm):
        out.append("disable-model-invocation")
    desc, wtu = scalar(fm, "description"), scalar(fm, "when_to_use")
    if desc and SUPPRESSANT.search(desc):
        out.append("suppressant-in-description")
    if desc and not TRIGGER_CLAUSE.search(f"{desc} {wtu or ''}"):
        out.append("no-trigger-clause")
    if desc and len(desc) > DESC_HARD_CAP:
        out.append(f"description-over-{DESC_HARD_CAP}")
    if len(desc or "") + len(wtu or "") > LISTING_CAP:
        out.append(f"listing-over-{LISTING_CAP}")
    return out


def audit(skills_dir: Path) -> dict[str, list[str]]:
    """{skill: violations} for every rule-skill in a skills/ tree. Values may be empty."""
    out = {}
    for name in RULE_SKILLS:
        f = skills_dir / name / "SKILL.md"
        try:
            text = f.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            text = None
        out[name] = violations(text)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("command", choices=["check", "roster"])
    ap.add_argument("--skills-dir", help="a plugin's skills/ directory")
    a = ap.parse_args()
    if a.command == "roster":
        print(" ".join(RULE_SKILLS))
        return 0
    if not a.skills_dir:
        print("check needs --skills-dir", file=sys.stderr)
        return 2
    d = Path(a.skills_dir)
    if not d.is_dir():
        print(f"not a directory: {d}", file=sys.stderr)
        return 2
    bad = {k: v for k, v in audit(d).items() if v}
    if bad:
        for name, vs in sorted(bad.items()):
            print(f"{name}: {','.join(vs)}")
        return 1
    print(f"all {len(RULE_SKILLS)} rule-skills satisfy the contract")
    return 0


if __name__ == "__main__":
    sys.exit(main())
