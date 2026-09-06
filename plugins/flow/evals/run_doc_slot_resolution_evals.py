#!/usr/bin/env python3
"""Regression harness for doc-slot resolution (FB-0100).

THE BUG THIS PINS. Every doc-slot reader used to inline its own
`[ -f "$X" ] && echo "$X" || echo "(no ... doc at $X)"`. Three properties made that
a bug factory: `[ -f ]` is FALSE on a directory, so a fragmented doc silently reads
as absent; the fallback was SILENT, so a misconfiguration was indistinguishable from
"this project legitimately has none"; and it was duplicated per-site, so fixing one
fixed one. FB-0082 is the same class already shipped once (`/flow:critique-plan` went
document-blind when `referenceGlob` matched nothing, and reported a clean verdict it
had no basis for).

WHY BOTH DIRECTIONS ARE ASSERTED. `.claude/rules/general.md` § Consistency
discipline item 3: "never ship a negative assertion alone" — a check that only
forbids something passes in two opposite worlds, the contract honored OR the
contract deleted. `skill-does-not-CALL-land` was exactly that shape, and FB-0074
satisfied it by deleting the call site; CI stayed green over a feature that no
longer existed, for four releases (FB-0077). So every negative here is paired with
the positive assertion of the thing it protects:

  negative — no shipped SKILL.md still carries a SILENT doc-slot fallback
  positive — each known reader still RESOLVES its slot (deleting the line fails)
  positive — the resolver actually emits the right thing for each of five states

Checks:
  neg 1   — no silent `[ -f "$X" ] && echo ... || echo "(no` in any shipped SKILL.md
  neg 2   — every `[ -f "$<doc-slot var>"` in a shipped SKILL.md is on a line that
            also carries a loud marker or a resolver call (repo-wide, not
            prelude-scoped: a prelude-scoped check goes green over a repo that still
            degrades silently at the argv-construction sites)
  pos 1-8 — each of the 8 context preludes calls resolve-doc-slot.sh for its slot
  pos 9   — resolver on a DIRECTORY: reports the count + the read command, and does
            NOT emit a "no ... doc" phrase
  pos 10  — resolver on a FILE: unchanged legacy behaviour
  pos 11  — resolver on an EXPLICITLY SET missing path: loud
  pos 12  — resolver on an EMPTY directory: loud, and distinct from missing
  pos 13  — resolver on an UNSET slot + absent default: quiet (the one ambiguous case)
  pos 14  — the five functional readers are loud on a missing plan
  ref 1   — a fragmented feedbackPath still reaches the plan-critic's reference set
  ref 2   — history fragments are NOT dragged into the reference set
  slot 1  — changelogPath is declared in the schema (it was read-but-undeclared)
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PLUGIN = ROOT / "plugins" / "flow"
RESOLVER = PLUGIN / "lib" / "resolve-doc-slot.sh"

fails = 0


def check(cid: str, ok: bool, detail: str = "") -> None:
    global fails
    if ok:
        print(f"PASS  [{cid}]")
    else:
        fails += 1
        print(f"FAIL  [{cid}]" + (f"  — {detail}" if detail else ""))


def shipped_skills() -> list[Path]:
    return sorted(PLUGIN.glob("skills/*/SKILL.md"))


def executable_lines(f: Path):
    """Yield (lineno, line) for lines that could actually RUN.

    Comment lines are excluded. This is not a convenience: the skills legitimately
    *document* the forbidden pattern (`# NOT [ -f "$CHANGELOG" ] ...` in land, which
    explains why the fix is what it is), and a checker that cannot tell an
    explanation from an occurrence pressures the author to delete the explanation to
    turn CI green -- satisfying the detector rather than the contract, the exact
    inversion `.claude/rules/general.md` item 3 warns about. `ci.yml`'s harness-join
    check already scopes to executable step lines for the same reason.
    """
    for n, line in enumerate(f.read_text(encoding="utf-8").split("\n"), 1):
        if line.lstrip().startswith("#"):
            continue
        yield n, line


def run_resolver(cwd: Path, slot: str, default: str, glob: str = "*.md"):
    r = subprocess.run(
        ["sh", str(RESOLVER), slot, default, glob],
        capture_output=True, text=True, cwd=cwd,
    )
    return r.stdout.strip()


# --------------------------------------------------------------------------
# NEGATIVE — the silent pattern must not survive anywhere
# --------------------------------------------------------------------------
SILENT = re.compile(r'\[ -f "\$\w+" \]\s*&&\s*echo\s+"\$\w+"\s*\|\|\s*echo\s+"\(no ')
offenders = []
for f in shipped_skills():
    for n, line in executable_lines(f):
        if SILENT.search(line):
            offenders.append(f"{f.relative_to(ROOT)}:{n}")
check("neg 1", not offenders,
      f"silent doc-slot fallback survives at: {offenders}")

# Repo-wide: every doc-slot file test must be loud or resolver-backed.
DOC_VARS = ("PLAN", "PLAN_PATH", "PLAN_P", "FB", "SPEC", "DL", "CHANGELOG", "HISTORY", "RESV")
TEST = re.compile(r'\[ -f "\$(' + "|".join(DOC_VARS) + r')"')
quiet = []
for f in shipped_skills():
    for n, line in executable_lines(f):
        if TEST.search(line) and "⚠️" not in line and "resolve-doc-slot" not in line:
            quiet.append(f"{f.relative_to(ROOT)}:{n}")
check("neg 2", not quiet,
      f"doc-slot file test with no loud branch and no resolver at: {quiet}")

# --------------------------------------------------------------------------
# POSITIVE — the readers this protects must still resolve their slots.
# Paired with neg 1/neg 2: deleting a prelude satisfies the negatives but fails
# these, so "satisfy the detector by removing the feature" is not available.
# --------------------------------------------------------------------------
EXPECTED = [
    ("security-review", "specPath"),
    ("security-review", "feedbackPath"),
    ("accessibility-review", "designLanguagePath"),
    ("accessibility-review", "feedbackPath"),
    ("staff-review", "specPath"),
    ("staff-review", "designLanguagePath"),
    ("staff-review", "feedbackPath"),
    ("verify-build", "planPath"),
]
for i, (skill, slot) in enumerate(EXPECTED, 1):
    f = PLUGIN / "skills" / skill / "SKILL.md"
    text = f.read_text(encoding="utf-8") if f.is_file() else ""
    ok = bool(re.search(r'resolve-doc-slot\.sh[^\n`]*\b' + re.escape(slot) + r'\b', text))
    check(f"pos {i}", ok, f"{skill}/SKILL.md must resolve {slot} via resolve-doc-slot.sh")

# --------------------------------------------------------------------------
# POSITIVE, runtime — the five resolver states
# --------------------------------------------------------------------------
check("resolver-exists", RESOLVER.is_file(), f"{RESOLVER} missing")

with tempfile.TemporaryDirectory() as d:
    w = Path(d)
    (w / "flow.config.json").write_text(json.dumps({
        "feedbackPath": "docs/feedback",
        "specPath": "docs/spec.md",
        "historyPath": "docs/nowhere",
        "designLanguagePath": "docs/empty",
    }))
    fb = w / "docs" / "feedback"; fb.mkdir(parents=True)
    for k in range(3):
        (fb / f"FB-000{k+1}-x.md").write_text(f"### FB-000{k+1}: x\n")
    (fb / "README.md").write_text("# not an entry\n")
    (w / "docs" / "spec.md").write_text("# spec\n")
    (w / "docs" / "empty").mkdir()

    out = run_resolver(w, "feedbackPath", "docs/feedback.md")
    check("pos 9", out.startswith("DIR ") and "(3 entries)" in out
          and "cat docs/feedback/*.md" in out and "no feedbackPath doc" not in out,
          f"directory resolution wrong (README must not count): {out!r}")

    out = run_resolver(w, "specPath", "docs/spec.md")
    check("pos 10", out.startswith("FILE docs/spec.md"), f"file resolution wrong: {out!r}")

    out = run_resolver(w, "historyPath", "docs/history.md")
    check("pos 11", "⚠️" in out and "MISSING" in out and "historyPath" in out,
          f"an explicitly-SET missing path must be LOUD: {out!r}")

    out = run_resolver(w, "designLanguagePath", "docs/design-language.md")
    check("pos 12", "⚠️" in out and "EMPTY" in out and "MISSING" not in out,
          f"an EMPTY directory must be loud AND distinct from missing: {out!r}")

    # The one quiet case: unset slot, default path, nothing there. Quiet because it
    # is genuinely ambiguous with "this project has none" -- and ONLY because of that.
    out = run_resolver(w, "roadmapPath", "docs/roadmap.md")
    check("pos 13", "⚠️" not in out and out.startswith("(no roadmapPath doc"),
          f"unset slot + absent default should stay quiet: {out!r}")

# --------------------------------------------------------------------------
# POSITIVE — the five functional (argv-construction) readers are loud
# --------------------------------------------------------------------------
FUNCTIONAL = [
    ("verify-build", 'PLAN_ARG=""'),
    ("audit-skips", 'PLAN_ARG=""'),
    ("ship", 'PLAN_A=""'),
    ("audit-coverage", "no plan at"),
]
missing_loud = []
for skill, needle in FUNCTIONAL:
    text = (PLUGIN / "skills" / skill / "SKILL.md").read_text(encoding="utf-8")
    for line in text.split("\n"):
        if needle in line and "⚠️" not in line:
            missing_loud.append(f"{skill}: {line.strip()[:70]}")
check("pos 14", not missing_loud, f"functional readers still silent: {missing_loud}")

# --------------------------------------------------------------------------
# REFERENCE SET — a fragmented feedbackPath must still reach the plan-critic
# --------------------------------------------------------------------------
extract = PLUGIN / "scripts" / "extract_session.py"
r = subprocess.run(
    [sys.executable, str(extract), "--mode", "plan",
     "--plan-file", "dev-docs/plan.md",
     "--reference-glob", "dev-docs/*.md",
     "--reference-glob", "dev-docs/feedback/*.md"],
    capture_output=True, text=True, cwd=ROOT,
)
check("ref 1", r.stdout.count("### dev-docs/feedback/FB-") > 10,
      f"fragmented feedbackPath must still populate the reference set "
      f"(got {r.stdout.count('### dev-docs/feedback/FB-')})")

r2 = subprocess.run(
    [sys.executable, str(extract), "--mode", "plan",
     "--plan-file", "dev-docs/plan.md",
     "--reference-glob", "dev-docs/history/*.md"],
    capture_output=True, text=True, cwd=ROOT,
)
check("ref 2", "### dev-docs/history/" not in r2.stdout,
      "history fragments must stay OUT of the reference set (the name-based skip "
      "stops working once history.md becomes a directory)")

# --------------------------------------------------------------------------
# SCHEMA — changelogPath was read-but-undeclared for several releases
# --------------------------------------------------------------------------
schema = json.loads((PLUGIN / "schema" / "flow.config.schema.json").read_text(encoding="utf-8"))
check("slot 1", "changelogPath" in schema["properties"],
      "changelogPath is read by /flow:land; a slot consumers cannot discover from "
      "the schema silently falls back forever")

print()
if fails:
    print(f"{fails} FAILED")
    raise SystemExit(1)
print("all doc-slot resolution evals passed")
