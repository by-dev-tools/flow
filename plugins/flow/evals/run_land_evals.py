#!/usr/bin/env python3
"""Eval harness for /flow:land (post-merge doc-currency, FB-0058).

Pins the deterministic helper `skills/land/lib/land-helpers.py` (changelog-check +
clear-reservation) plus the load-bearing SKILL.md contract prose. The narrative
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
  cr 1 — clear-reservation: removes the matching id, leaves others.
  cr 2 — clear-reservation: word-boundary — FB-001 does not strike FB-0014.
  cr 3 — clear-reservation: absent id → idempotent no-op, exit 0.
  cr 4 — clear-reservation: non FB/VH id rejected → exit 2, file untouched.
  cr 5 — clear-reservation: missing file → clean no-op, exit 0.
  skill 1 — SKILL.md: merged-state gate is BLOCKING + fail-loud, edits nothing.
  skill 2 — SKILL.md: no-match discovery is a WARN, not a silent no-op.
  skill 3 — SKILL.md: late visual-history distill reuses §5c / insert-visual-history.py.
  skill 4 — SKILL.md: never merges; uses REST PR-body form, never `gh pr edit --body`.
  skill 5 — SKILL.md: disable-model-invocation: true (human-only, never auto-fires).
  reg 1 — /flow:land is registered in plugin.json + marketplace.json skill lists.
  reg 2 — workflow-help + docs/workflow.md reference /flow:land.
  ci  1 — run_land_evals.py is wired into .github/workflows/ci.yml (not orphaned).
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).parent
ROOT = HERE.parent.parent.parent  # repo root
HELPER = HERE.parent / "skills" / "land" / "lib" / "land-helpers.py"
SKILL = HERE.parent / "skills" / "land" / "SKILL.md"
PLUGIN_JSON = HERE.parent / ".claude-plugin" / "plugin.json"
MARKETPLACE = ROOT / ".claude-plugin" / "marketplace.json"
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

# ---- clear-reservation ----
with tempfile.TemporaryDirectory() as d:
    resv = Path(d) / "resv.md"
    resv.write_text("- FB-001 (old)\n- FB-0013 (PR P)\n- FB-0014 (PR R)\n- VH-0008 (PR X)\n")
    rc, out, err = run("clear-reservation", str(resv), "--id", "FB-0013")
    check("cr 1", rc == 0 and "FB-0013" not in resv.read_text() and "FB-0014" in resv.read_text(),
          f"rc={rc} after={resv.read_text()!r}")
    # word boundary: --id FB-001 strikes the `FB-001` line but NOT `FB-0014` (positive
    # removal AND non-removal both asserted, so a match-nothing bug can't pass).
    rc, out, err = run("clear-reservation", str(resv), "--id", "FB-001")
    after = resv.read_text()
    check("cr 2", "FB-001 (old)" not in after and "FB-0014" in after,
          f"FB-001 must strike its own line, not FB-0014: {after!r}")
    rc, out, err = run("clear-reservation", str(resv), "--id", "FB-0099")
    check("cr 3", rc == 0 and "already clear" in out, f"rc={rc} out={out!r}")
    before = resv.read_text()
    rc, out, err = run("clear-reservation", str(resv), "--id", "ready")
    check("cr 4", rc == 2 and resv.read_text() == before, f"rc={rc} mutated={resv.read_text() != before}")
    rc, out, err = run("clear-reservation", str(Path(d) / "absent.md"), "--id", "FB-0001")
    check("cr 5", rc == 0, f"missing reservations file should be clean no-op (rc={rc})")

# ---- SKILL.md contract prose ----
skill = read(SKILL)
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
check("skill 5", "disable-model-invocation: true" in skill,
      "land must be human-only (disable-model-invocation: true)")
# Guard the two staff-review BLOCKERs so they can't regress green:
check("skill 6", '[ -n "$HEADREF" ] && PAT=' in skill and 'HEADREF=$(gh pr view' in skill,
      "Step 2 discovery must assign HEADREF + guard the empty alternative (no `#N|` match-all)")
check("skill 7", 'git show-ref --verify --quiet' in skill and "reusing existing branch" in skill,
      "Step 1b branch creation must be idempotent (reuse existing land branch on re-run)")

# ---- registration fan-out ----
pj = read(PLUGIN_JSON)
mk = read(MARKETPLACE)
check("reg 1", "/flow:land" in pj and "/flow:land" in mk,
      "/flow:land must be listed in plugin.json + marketplace.json")
check("reg 2", "/flow:land" in read(WORKFLOW_HELP) and "/flow:land" in read(WORKFLOW_DOC),
      "/flow:land must be in workflow-help + docs/workflow.md")

# ---- CI wiring (the orphaned-eval guard, FB-0056 lesson) ----
check("ci 1", "run_land_evals.py" in read(CI),
      "run_land_evals.py must be wired into ci.yml (an unwired harness gives 0 protection)")

print()
if fails:
    print(f"{fails} FAILED")
    sys.exit(1)
print("all land evals passed")
