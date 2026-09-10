#!/usr/bin/env python3
"""Eval harness for /flow:land (post-merge doc-currency, FB-0061).

Pins the deterministic helper `skills/land/lib/land-helpers.py` (changelog-check,
file- and directory-valued) plus the load-bearing SKILL.md contract prose. The narrative
reconciliation (Step 3 status-flips) is agent judgment — like /flow:ship Step 5a it
has no helper and isn't unit-tested; what IS pinned here is the mechanical core and
the contract that the safety steps (merged-gate, no-match WARN, §5c reuse, never
gh pr edit) stay present. Assertion-based (exit-code + stdout/stderr substring),
stdlib only.

Run: python3 plugins/flow/evals/run_land_evals.py

Covers:
  cc 1 — changelog-check: present version → exit 0.
  cc 2 — changelog-check: absent version → exit 1 + WARN.
  cc 3 — changelog-check: prefix version (v1.10) does NOT match v1.10.1 → exit 1.
  cc 4 — changelog-check: missing file → exit 2 (distinct from absent-entry).
  cd 1 — changelog-check: DIRECTORY-valued changelogPath produces a verdict.
  cd 2 — changelog-check: absent version in a directory corpus → exit 1.
  cd 3 — changelog-check: prefix anchoring holds for directories too.
  cd 4 — changelog-check: EMPTY directory → exit 2, distinct from absent-entry.
  cr-removed 1 — clear-reservation subcommand is gone (v1.40.0), helper still runs.
  skill 1 — SKILL.md: merged-state gate is BLOCKING + fail-loud, edits nothing.
  skill 2 — SKILL.md: no-match discovery is a WARN, not a silent no-op.
  skill 3 — SKILL.md: late visual-history distill reuses §5c / insert-visual-history.py.
  skill 4 — SKILL.md: never merges; uses REST PR-body form, never `gh pr edit --body`.
  skill 5 — SKILL.md: disable-model-invocation: FALSE (FB-0077 — model-invocable so
           /flow:post-merge §3 can call it); 5b — §0 carries the never-auto-fire intent.
  reg 1 — workflow-help + docs/workflow.md reference /flow:land.
          (This previously also asserted the manifest `description` fields listed the
          skill. Dropped in FB-0078: the /plugin UI generates the component inventory
          from disk — Discover's "Will install", the Installed detail view — so a
          hand-maintained catalog in `description` was redundant and staleable. The
          consumer-facing catalog sites are the docs, which is what this now checks.)
  ci  1 — run_land_evals.py is wired into .github/workflows/ci.yml (not orphaned).
"""

from __future__ import annotations

import importlib.util
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).parent
ROOT = HERE.parent.parent.parent  # repo root
HELPER = HERE.parent / "skills" / "land" / "lib" / "land-helpers.py"
SKILL = HERE.parent / "skills" / "land" / "SKILL.md"
WORKFLOW_HELP = HERE.parent / "skills" / "workflow-help" / "SKILL.md"
WORKFLOW_DOC = HERE.parent / "docs" / "workflow.md"
CI = ROOT / ".github" / "workflows" / "ci.yml"

fails = 0


def check(cid, ok, detail=""):
    global fails
    if ok:
        print(f"PASS  [{cid}]")
    else:
        fails += 1
        print(f"FAIL  [{cid}]" + (f"  — {detail}" if detail else ""))


def run(*args):
    proc = subprocess.run(
        [sys.executable, str(HELPER), *args],
        capture_output=True, text=True, check=False,
    )
    return proc.returncode, proc.stdout, proc.stderr


def read(p: Path) -> str:
    return p.read_text() if p.is_file() else ""


def _load_lint():
    """Load skill-composition-lint.py by path (hyphenated name isn't importable).

    Reused rather than re-implemented so the frontmatter parse has ONE definition —
    a second copy here could drift from the shipped one and start agreeing with
    itself (the FB-0010 fan-out class, inside the evals meant to catch it).
    """
    spec = importlib.util.spec_from_file_location(
        "skill_composition_lint",
        HERE.parent / "skills" / "doctor" / "lib" / "skill-composition-lint.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---- changelog-check ----
with tempfile.TemporaryDirectory() as d:
    cl = Path(d) / "CHANGELOG.md"
    cl.write_text("# Changelog\n\n## v1.10.1 — 2026-06-24\n- a\n\n## v1.9.0 — 2026-06-19\n- b\n")
    rc, out, err = run("changelog-check", str(cl), "--version", "1.10.1")
    check("cc 1", rc == 0 and "PASS" in out, f"rc={rc} out={out!r}")
    rc, out, err = run("changelog-check", str(cl), "--version", "9.9.9")
    check("cc 2", rc == 1 and "WARN" in err, f"rc={rc} err={err!r}")
    rc, out, err = run("changelog-check", str(cl), "--version", "1.10")
    check("cc 3", rc == 1, f"prefix v1.10 wrongly matched v1.10.1 (rc={rc})")
    rc, out, err = run("changelog-check", str(Path(d) / "nope.md"), "--version", "1.0.0")
    check("cc 4", rc == 2, f"missing file should be exit 2 (rc={rc})")

# ---- changelog-check against a FRAGMENTED (directory) changelogPath ----
# FB-0101: `changelogPath` may point at a DIRECTORY of one-file-per-release
# fragments. The SKILL used to guard this whole check with `[ -f "$CHANGELOG" ]`,
# which is FALSE on a directory — so the currency check became a silent no-op that
# never ran and never said so. These are POSITIVE assertions (a verdict is produced
# from a directory), deliberately paired with the negative in
# run_doc_slot_resolution_evals.py: a negative alone would pass if the call site
# were simply deleted.
with tempfile.TemporaryDirectory() as d:
    cldir = Path(d) / "changelog"
    cldir.mkdir()
    (cldir / "v1.10.1.md").write_text("## v1.10.1 — 2026-01-01\n\n- a thing\n")
    (cldir / "v1.11.0.md").write_text("## v1.11.0 — 2026-01-02\n\n- another\n")
    (cldir / "README.md").write_text("# Changelog\n\nNot a release fragment.\n")

    rc, out, err = run("changelog-check", str(cldir), "--version", "1.10.1")
    check("cd 1", rc == 0 and "PASS" in out,
          f"a directory-valued changelogPath must PRODUCE A VERDICT, not silently skip (rc={rc} out={out!r})")

    rc, out, err = run("changelog-check", str(cldir), "--version", "9.9.9")
    check("cd 2", rc == 1, f"absent version in a directory corpus should be exit 1 (rc={rc})")

    # Prefix anchoring must survive the directory path too.
    rc, out, err = run("changelog-check", str(cldir), "--version", "1.10")
    check("cd 3", rc == 1, f"v1.10 must NOT be satisfied by v1.10.1 in a directory (rc={rc})")

    # An EMPTY directory is exit 2 (broken migration), NOT exit 1 (missing entry).
    # Conflating them would send the reader to write an entry when the real fault is
    # that there are no entries at all.
    empty = Path(d) / "empty-changelog"
    empty.mkdir()
    rc, out, err = run("changelog-check", str(empty), "--version", "1.0.0")
    check("cd 4", rc == 2, f"empty directory must be exit 2, distinct from absent-entry (rc={rc})")

# ---- clear-reservation is GONE (v1.40.0) ----
# Paired assertion, per .claude/rules/general.md item 3: asserting only that the
# subcommand is absent would also pass if the whole helper were deleted. Assert the
# removal AND that the helper still works.
rc, out, err = run("clear-reservation", "whatever", "--id", "FB-0001")
check("cr-removed 1", rc != 0 and "invalid choice" in (out + err),
      f"clear-reservation must be rejected — reserved-feedback-numbers.md no longer exists (rc={rc})")

# ---- SKILL.md contract prose ----
skill = read(SKILL)
_frontmatter = _load_lint()._frontmatter
check("skill 1",
      "Verify the PR is actually MERGED" in skill and "BLOCKING" in skill
      and "fail loudly, edit nothing" in skill and '!= "MERGED"' in skill,
      "merged-state gate must be BLOCKING + fail-loud + edit nothing")
check("skill 2", "WARN" in skill and "silent no-op" in skill.lower(),
      "no-match discovery must WARN, never silent no-op")
check("skill 3", "insert-visual-history.py" in skill and "§5c" in skill,
      "late distill must reuse §5c / insert-visual-history.py")
check("skill 4",
      "Do not merge" in skill and "gh pr edit --body" in skill and "gh api -X PATCH" in skill,
      "must never merge; must use REST PR-body form not gh pr edit")
# FB-0077 flipped this: land is model-invocable so /flow:post-merge §3 can call it.
# Anchored to the FRONTMATTER block, not a bare substring — the previous form
# (`"disable-model-invocation: true" in skill`) kept passing after the flag was
# flipped, because §0's prose quotes the old value while explaining the change. A
# whole-file substring check cannot tell a declaration from a mention of one.
# Use the lint's _frontmatter (fail-CLOSED: returns "" when the file has no leading
# `---`). A local `skill.split("\n---", 1)[0]` fails OPEN on that same input — it
# returns the entire file, silently restoring the whole-file substring search this
# check was rewritten to eliminate.
check("skill 5",
      bool(re.search(r"^disable-model-invocation:\s*false\s*$",
                     _frontmatter(skill), re.M)),
      "land must be model-invocable (disable-model-invocation: false, FB-0077) so "
      "/flow:post-merge §3 can call it; the never-auto-fire guard is its §1a merged-PR gate")
check("skill 5b", "## 0. Invocation precondition" in skill and "§1a" in skill,
      "land must state the never-auto-fire precondition in prose (§0), since the "
      "frontmatter flag no longer carries that intent")
# Guard the two staff-review BLOCKERs so they can't regress green:
check("skill 6", '[ -n "$HEADREF" ] && PAT=' in skill and 'HEADREF=$(gh pr view' in skill,
      "Step 2 discovery must assign HEADREF + guard the empty alternative (no `#N|` match-all)")
check("skill 7", 'git show-ref --verify --quiet' in skill and "reusing existing branch" in skill,
      "Step 1b branch creation must be idempotent (reuse existing land branch on re-run)")

# ---- registration fan-out ----
check("reg 1", "/flow:land" in read(WORKFLOW_HELP) and "/flow:land" in read(WORKFLOW_DOC),
      "/flow:land must be in workflow-help + docs/workflow.md")

# ---- CI wiring (the orphaned-eval guard, FB-0056 lesson) ----
check("ci 1", "run_land_evals.py" in read(CI),
      "run_land_evals.py must be wired into ci.yml (an unwired harness gives 0 protection)")

print()
if fails:
    print(f"{fails} FAILED")
    sys.exit(1)
print("all land evals passed")
