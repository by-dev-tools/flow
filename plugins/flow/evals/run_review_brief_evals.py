#!/usr/bin/env python3
"""
Regression eval for D1 Phase 1 — the lens-experience agent + the
/flow:review-brief pre-prototype orchestrator (dev-docs/handoffs/
d1-prototype-first-gate.md, FB-0081/FB-0046).

Three surfaces, three check groups. All offline / stdlib-only: this harness
does not invoke a live subagent (matches the existing convention in
run_evals.py, whose default `run_auditor()` reads a recorded `.expected.txt`
rather than calling out to a model — the goal is regression detection on the
prompt contract, not benchmark-grade scoring of live judgment).

  1. Extraction (mechanical, exercises real code) — extract_session.py
     --mode plan --plan-file <brief> renders the plan-file heading + the
     brief's own content for each fixture under fixtures/review-brief/.
     No changes to extract_session.py; this only pins that the D1
     orchestrator's reuse of --plan-file against a brief still works.

  2. Lens contract (structural, against the hand-authored .expected.txt
     fixtures) — pins the two cases the handoff's Phase 1 checklist calls
     out by name: a conformant-but-low-ambition brief must carry an
     Ambition-ceiling finding; a genuinely-tight brief must render both
     clean states ("Ambition bar met." + "Nothing to push..."). Also pins
     the shared contract every lens-experience.md output must satisfy
     (both section headers present, the standard reviewer footer verbatim).

  3. Orchestrator composition (grep-based, positive assertions per
     FB-0010's "pair every prohibition with what it protects") —
     review-brief/SKILL.md actually names all three reviewer
     subagent_types, and both triage outcomes (decision-required routing
     to a question list, and the clean-pass proceed line) are present, not
     just one of the two. Also pins the six design-brief field names into
     workflow.md's template section, so the doc and the fixtures can't
     silently drift apart (FB-0010 fan-out class).

Stdlib only. No network. Run:
    python3 plugins/flow/evals/run_review_brief_evals.py
Exits non-zero on any failure (CI gate).
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent  # plugins/flow
FIXTURES = HERE / "fixtures" / "review-brief"
EXTRACT = REPO / "scripts" / "extract_session.py"
LENS = REPO / "agents" / "lens-experience.md"
SKILL = REPO / "skills" / "review-brief" / "SKILL.md"
WORKFLOW = REPO / "docs" / "workflow.md"
LINT_SCRIPT = REPO / "skills" / "doctor" / "lib" / "skill-composition-lint.py"

_LINT_MODULE = None


def _frontmatter_of(path: Path) -> str:
    """Reuse skill-composition-lint.py's frontmatter parser (same helper
    run_skill_composition_evals.py imports), rather than a second, subtly
    different hand-rolled split — the exact drift class that lint's own
    docstring warns against."""
    global _LINT_MODULE
    if _LINT_MODULE is None:
        spec = importlib.util.spec_from_file_location("skill_composition_lint", LINT_SCRIPT)
        _LINT_MODULE = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_LINT_MODULE)
    return _LINT_MODULE._frontmatter(path.read_text(encoding="utf-8"))

FOOTER = "If a finding is wrong, just say so. Your pushback will be logged for prompt tuning."

_failures: list[str] = []
_passes = 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global _passes
    if cond:
        _passes += 1
    else:
        _failures.append(f"{name}: {detail}")


def run_extract(*args: str) -> tuple[int, str, str]:
    proc = subprocess.run(
        [sys.executable, str(EXTRACT), *args],
        capture_output=True,
        text=True,
    )
    return proc.returncode, proc.stdout, proc.stderr


# ------------------------------------------------------------- 1. extraction

def test_extraction(fixture_stem: str, distinctive_text: str) -> None:
    brief = FIXTURES / f"{fixture_stem}.md"
    rc, out, err = run_extract(
        "--mode", "plan",
        "--plan-file", str(brief),
        "--allow-external-paths",
    )
    check(f"extract-{fixture_stem}-exit0", rc == 0, f"stderr: {err[:300]}")
    # extract_session.py legitimately relativizes the displayed path to cwd when
    # possible (load_plan_file's `resolved.relative_to(cwd)`), so check for the
    # fixture's own filename rather than requiring the absolute path verbatim.
    check(
        f"extract-{fixture_stem}-heading",
        "## Plan under review (from file:" in out and brief.name in out,
        "missing the plan-file heading with the brief's own filename",
    )
    check(
        f"extract-{fixture_stem}-content",
        distinctive_text in out,
        f"extracted context missing distinctive brief text {distinctive_text!r}",
    )


# ------------------------------------------------------------- 2. lens contract

def test_lens_contract(fixture_stem: str, required_substrings: list[str]) -> None:
    expected = FIXTURES / f"{fixture_stem}.expected.txt"
    check(f"lens-{fixture_stem}-file-exists", expected.is_file())
    if not expected.is_file():
        return
    text = expected.read_text(encoding="utf-8")
    check(f"lens-{fixture_stem}-has-experience-header", "EXPERIENCE LENS" in text)
    check(
        f"lens-{fixture_stem}-has-pushfurther-header",
        "PUSH-FURTHER (quality, not scope)" in text,
    )
    check(f"lens-{fixture_stem}-has-footer", FOOTER in text)
    for s in required_substrings:
        check(f"lens-{fixture_stem}-contains {s!r}", s in text, f"missing {s!r}")


def test_lens_agent_frontmatter() -> None:
    check("lens-file-exists", LENS.is_file())
    if not LENS.is_file():
        return
    fm = _frontmatter_of(LENS)
    check("lens-frontmatter-name", "name: lens-experience" in fm)
    check(
        "lens-frontmatter-tools-match-family",
        "tools: Read, Grep, Glob, Bash" in fm,
        "should match the lens-*.md sibling family's tool grant exactly",
    )


# ------------------------------------------------------- 3. orchestrator + docs

def test_orchestrator_composition() -> None:
    check("skill-file-exists", SKILL.is_file())
    if not SKILL.is_file():
        return
    text = SKILL.read_text(encoding="utf-8")
    for subagent in ("flow:auditor", "flow:plan-critic", "flow:lens-experience"):
        check(f"skill-names-{subagent}", subagent in text, f"missing {subagent} subagent_type")
    # Positive-pair the two triage outcomes (FB-0010): a skill that only ever
    # escalates, or only ever proceeds, is not doing triage.
    check("skill-has-decision-required-routing", "decision-required" in text)
    check(
        "skill-has-proceed-verdict",
        "proceed to the prototype phase" in text,
        "clean-pass proceed language must be present, not just the escalation path",
    )
    check(
        "skill-single-tool-message",
        "single tool message" in text,
        "must state the one-extraction/one-message fan-out guarantee (handoff §5)",
    )


def test_workflow_template_fields() -> None:
    check("workflow-file-exists", WORKFLOW.is_file())
    if not WORKFLOW.is_file():
        return
    text = WORKFLOW.read_text(encoding="utf-8")
    check("workflow-has-template-section", "D1 design-brief template" in text)
    for field in (
        "**Problem**",
        "**Whose moment**",
        "**Constraints**",
        "**Intended scope**",
        "**Deliberately excluded**",
        "**Where this pushes past the literal request**",
    ):
        check(f"workflow-template-field {field!r}", field in text, f"missing field {field!r}")
    check(
        "workflow-lists-review-brief-skill",
        "/flow:review-brief" in text,
        "workflow.md's skills cheat sheet / shipped-surface list must name the new skill",
    )


# ----------------------------------------------------------------------- main

def main() -> int:
    test_extraction(
        "brief_low_ambition",
        'Add an "Undo" text link that appears for 5 seconds after a delete',
    )
    test_extraction(
        "brief_tight_scope",
        "Expand the tappable hit area to 44×44pt via padding",
    )
    test_lens_contract(
        "brief_low_ambition",
        ["Ambition ceiling", "REDIRECT"],
    )
    test_lens_contract(
        "brief_tight_scope",
        ["Ambition bar met.", "Nothing to push — surface at ceiling for its scope."],
    )
    test_lens_agent_frontmatter()
    test_orchestrator_composition()
    test_workflow_template_fields()

    for f in _failures:
        print(f"FAIL  {f}")
    total = _passes + len(_failures)
    print(f"\n{_passes}/{total} checks passed")
    return 0 if not _failures else 1


if __name__ == "__main__":
    sys.exit(main())
