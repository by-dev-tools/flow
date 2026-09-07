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
  join 1  — the pinned prelude list equals what is actually SHIPPED AND EXECUTING
            (both directions; anchored on the `!` marker, so commenting a prelude out
            fails the join rather than passing as "documentation")
  neg 3   — no SKILL.md carries an inert (non-`!`) copy of a resolver prelude
  pos 1-N — each pinned context prelude calls resolve-doc-slot.sh for its slot
  loud-fallback — every prelude is loud when the resolver itself is missing
  schema-default-pin — each prelude's default argument matches the schema default
  state 1 — resolver on a DIRECTORY: reports the count + the read command, and does
            NOT emit a "no ... doc" phrase
  state 2 — resolver on a FILE: unchanged legacy behaviour
  state 3 — resolver on an EXPLICITLY SET missing path: loud
  state 4 — resolver on an EMPTY directory: loud, and distinct from missing
  state 6 — resolver on a SCAFFOLDED directory (README only) is QUIET
  state 7b— resolver on a SET slot pointing at a ZERO-BYTE file is LOUD
  state 5 — resolver on an UNSET slot + absent default: quiet (the one ambiguous case)
  state 7 — the functional (argv-construction) readers are loud on a missing plan
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
# The PINNED set of doc-slot context preludes. Hand-written on purpose: a derived
# list cannot detect deletion, because deleting a prelude would shrink the derived
# list and the check would pass. The `join` assertion below then guarantees the pin
# stays complete — same two-sided shape ci.yml uses for the eval-harness list.
#
# This pin previously covered 8 of the 11 real preludes, so `land`'s two and
# `ship-spike`'s one could be deleted with CI still green — the exact
# negative-satisfiable-by-deletion hole this harness exists to close, inside the
# harness itself. The join is what makes the pin self-maintaining.
EXPECTED = [
    ("security-review", "specPath"),
    ("security-review", "feedbackPath"),
    ("accessibility-review", "designLanguagePath"),
    ("accessibility-review", "feedbackPath"),
    ("staff-review", "specPath"),
    ("staff-review", "designLanguagePath"),
    ("staff-review", "feedbackPath"),
    ("verify-build", "planPath"),
    ("land", "historyPath"),
    ("land", "changelogPath"),
    ("ship-spike", "historyPath"),
]

# Captures (slot, default). The optional trailing group is the resolver's third
# argument, an entry glob -- /flow:land passes 'v*.md' for changelogPath so the read
# hint offers `ls -v` rather than a lexical sort that puts v1.10.0 before v1.9.0.
# Without the optional group the glob was captured AS the default and join 1 failed,
# which is the join doing its job on a real change of shape.
PRELUDE_RX = re.compile(r"""!`[^`\n]*sh "\$R" (\w+) (\S+?)(?: '[^']*')? \|\|""")


def on_disk_preludes():
    found = []
    for f in shipped_skills():
        for m in PRELUDE_RX.finditer(f.read_text(encoding="utf-8")):
            found.append((f.parent.name, m.group(1), m.group(2)))
    return found


DISK = on_disk_preludes()

# A resolver call OUTSIDE an `!`-span is inert: it renders as prose and never runs.
# Paired with join 1 (which now only counts executing ones), this closes the
# de-activation route in both directions -- you can neither disarm a prelude nor
# reintroduce a disarmed copy alongside a live one.
INERT_RX = re.compile(r'(?<!!)`[^`\n]*sh "\$R" \w+ ')
inert = []
for f in shipped_skills():
    for n, line in enumerate(f.read_text(encoding="utf-8").split("\n"), 1):
        if INERT_RX.search(line):
            inert.append(f"{f.relative_to(ROOT)}:{n}")
check("neg 3", not inert,
      f"resolver prelude(s) present but NOT executing (missing the leading `!`): {inert}")

# join — the pin must equal what is actually shipped, in BOTH directions.
check("join 1", sorted({(a, b) for a, b, _ in DISK}) == sorted(set(EXPECTED)),
      f"pinned preludes != shipped preludes.\n"
      f"  only pinned: {sorted(set(EXPECTED) - {(a, b) for a, b, _ in DISK})}\n"
      f"  only shipped: {sorted({(a, b) for a, b, _ in DISK} - set(EXPECTED))}")

for i, (skill, slot) in enumerate(EXPECTED, 1):
    f = PLUGIN / "skills" / skill / "SKILL.md"
    text = f.read_text(encoding="utf-8") if f.is_file() else ""
    ok = bool(re.search(r'resolve-doc-slot\.sh[^\n`]*\b' + re.escape(slot) + r'\b', text))
    check(f"pos {i}", ok, f"{skill}/SKILL.md must resolve {slot} via resolve-doc-slot.sh")

# Every prelude must be LOUD when the resolver itself cannot be found — otherwise a
# missing helper is indistinguishable from a resolved slot, which is the same
# silent-degradation this whole harness is about, one level up.
quiet_fallback = [
    f"{sk}:{slot}" for sk, slot, _ in DISK
    if not re.search(
        r'sh "\$R" ' + re.escape(slot) + r'[^`]*?NO ' + re.escape(slot) + r' context',
        (PLUGIN / "skills" / sk / "SKILL.md").read_text(encoding="utf-8"))
]
check("loud-fallback", not quiet_fallback,
      f"prelude(s) whose resolver-not-found branch omits the 'NO <slot> context' clause: {quiet_fallback}")

# Each prelude passes the schema default as argv[2]. #141's entire root cause was ONE
# default literal drifting from the schema across 17 call sites; this PR added eleven
# more, so pin them to the schema rather than to author memory.
_schema = json.loads((PLUGIN / "schema" / "flow.config.schema.json").read_text(encoding="utf-8"))
drifted = [
    f"{sk}:{slot} passes {default!r}, schema default is {_schema['properties'].get(slot, {}).get('default')!r}"
    for sk, slot, default in DISK
    if slot in _schema["properties"] and _schema["properties"][slot].get("default") != default
]
check("schema-default-pin", not drifted, f"prelude default(s) drifted from the schema: {drifted}")

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
    check("state 1", out.startswith("DIR ") and "(3 entries" in out
          and "cat docs/feedback/*.md" in out and "no feedbackPath doc" not in out
          and "browse:" in out,
          f"directory resolution wrong (README must not count): {out!r}")

    out = run_resolver(w, "specPath", "docs/spec.md")
    check("state 2", out.startswith("FILE docs/spec.md"), f"file resolution wrong: {out!r}")

    out = run_resolver(w, "historyPath", "docs/history.md")
    check("state 3", "⚠️" in out and "MISSING" in out and "historyPath" in out,
          f"an explicitly-SET missing path must be LOUD: {out!r}")

    out = run_resolver(w, "designLanguagePath", "docs/design-language.md")
    check("state 4", "⚠️" in out and "EMPTY" in out and "MISSING" not in out,
          f"an EMPTY directory must be loud AND distinct from missing: {out!r}")

    # state 6 — SCAFFOLDED: a directory holding only its README. This is the CORRECT
    # state on day one of every new project, so it must be QUIET. It had no test until
    # the push-further lens pointed out that deleting the resolver's README arm left the
    # whole suite green while every correct fresh install started warning -- the exact
    # false alarm the resolver's longest comment exists to prevent. Paired: the quiet
    # marker must be absent AND the scaffolded wording present.
    sc = w / "docs" / "scaffolded"; sc.mkdir()
    (sc / "README.md").write_text("# just the readme\n")
    (w / "flow.config.json").write_text(json.dumps({
        "feedbackPath": "docs/feedback", "specPath": "docs/spec.md",
        "historyPath": "docs/nowhere", "designLanguagePath": "docs/empty",
        "visualHistoryPath": "docs/scaffolded", "planPath": "docs/truncated.md",
    }))
    out = run_resolver(w, "visualHistoryPath", "docs/visual-history.md")
    check("state 6", "⚠️" not in out and "scaffolded" in out and out.startswith("DIR "),
          f"a scaffolded-but-empty directory must resolve QUIETLY: {out!r}")

    # state 7 — a SET slot pointing at a ZERO-BYTE file. Loud, for the same reason the
    # empty directory is loud: the slot resolves to no context. This is the state every
    # un-migrated consumer sits in (the schema defaults are single files), and FB-0101's
    # thesis is that a merge can silently empty a doc.
    (w / "docs" / "truncated.md").write_text("")
    out = run_resolver(w, "planPath", "docs/plan.md")
    check("state 7b", "⚠️" in out and "EMPTY" in out,
          f"a SET slot pointing at a zero-byte file must be LOUD: {out!r}")

    # The quiet cases: unset slot, default path, nothing there. Quiet because it
    # is genuinely ambiguous with "this project has none" -- and ONLY because of that.
    out = run_resolver(w, "roadmapPath", "docs/roadmap.md")
    check("state 5", "⚠️" not in out and out.startswith("(no roadmapPath doc"),
          f"unset slot + absent default should stay quiet: {out!r}")

# --------------------------------------------------------------------------
# POSITIVE — the functional (argv-construction) readers are loud
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
check("state 7", not missing_loud, f"functional readers still silent: {missing_loud}")

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
check("ref 1", r.returncode == 0 and r.stdout.count("### dev-docs/feedback/FB-") > 10,
      f"fragmented feedbackPath must still populate the reference set "
      f"(got {r.stdout.count('### dev-docs/feedback/FB-')})")

r2 = subprocess.run(
    [sys.executable, str(extract), "--mode", "plan",
     "--plan-file", "dev-docs/plan.md",
     "--reference-glob", "dev-docs/history/*.md"],
    capture_output=True, text=True, cwd=ROOT,
)
check("ref 2", r2.returncode == 0 and "### dev-docs/history/" not in r2.stdout,
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
