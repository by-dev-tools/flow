#!/usr/bin/env python3
"""Eval harness for harness_audit.py (roadmap item AB, Step 1, FB-0095).

Dev tooling, not a shipped plugin eval -- runs in its own CI job (see
.github/workflows/ci.yml), not folded into the plugins/flow/evals/ FB-0074
harness/CI join-check, which is scoped to shipped-plugin regression tests.

Covers only the MECHANICAL parts of the audit: cadence math, marker
resolution, surface-list resolution, and graceful handling of a missing or
empty surface. The audit-agent's actual "does this still earn its cost"
judgment is best-effort LLM work (like the auditor/plan-critic) and is not
something a deterministic eval can grade.

Stdlib only. Run:
    python3 tools/harness_audit/run_harness_audit_evals.py
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import harness_audit as ha  # noqa: E402

_failures: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    if ok:
        print(f"  PASS  {name}")
    else:
        print(f"  FAIL  {name}\n        {detail}")
        _failures.append(name)


# ---------------------------------------------------------------- fixture helpers


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True)


def make_fixture_repo(tmp: Path) -> Path:
    """A minimal real git repo (not a flow checkout) with an origin/main
    ref, so audit_due's git plumbing has something real to walk."""
    repo = tmp / "fixture-repo"
    repo.mkdir(parents=True)
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")
    (repo / "README.md").write_text("hello\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-q", "-m", "init")
    _git(repo, "branch", "-m", "main")
    # Fake a remote-tracking ref without a real remote: audit_due tries
    # origin/main first, falling back to local main -- exercise the fallback
    # path here since it's simpler than standing up a real remote.
    return repo


def add_commits(repo: Path, n: int) -> None:
    for i in range(n):
        (repo / f"file{i}.txt").write_text(str(i), encoding="utf-8")
        _git(repo, "add", ".")
        _git(repo, "commit", "-q", "-m", f"commit {i}")


def make_surface_fixture(tmp: Path) -> Path:
    """A minimal repo-root-shaped tree for resolve_*_surfaces to walk."""
    root = tmp / "fixture-surfaces"
    (root / "plugins" / "flow" / "skills" / "ship").mkdir(parents=True)
    (root / "plugins" / "flow" / "skills" / "no-description").mkdir(parents=True)
    (root / "plugins" / "flow" / "agents").mkdir(parents=True)
    (root / "plugins" / "flow" / "docs").mkdir(parents=True)
    (root / ".claude" / "rules").mkdir(parents=True)
    (root / ".claude" / "skills").mkdir(parents=True)
    (root / ".claude" / "agents").mkdir(parents=True)

    (root / "CLAUDE.md").write_text("# CLAUDE\nsome project rules\n", encoding="utf-8")
    (root / "plugins" / "flow" / "docs" / "workflow.md").write_text("# Workflow\nbody\n", encoding="utf-8")
    (root / ".claude" / "rules" / "safety.md").write_text("# Safety\nrules\n", encoding="utf-8")

    (root / "plugins" / "flow" / "skills" / "ship" / "SKILL.md").write_text(
        "---\nname: ship\ndescription: >\n  Ship completed work end to end.\n"
        "allowed-tools: Read\n---\n\nBody of the ship skill, quite long in the real repo.\n",
        encoding="utf-8",
    )
    (root / "plugins" / "flow" / "skills" / "no-description" / "SKILL.md").write_text(
        "---\nname: no-description\nallowed-tools: Read\n---\n\nBody with no description field.\n",
        encoding="utf-8",
    )
    (root / "plugins" / "flow" / "agents" / "auditor.md").write_text(
        "---\nname: auditor\ndescription: Audits things.\n---\n\nSystem prompt body.\n",
        encoding="utf-8",
    )
    return root


# ---------------------------------------------------------------- audit_due


def test_audit_due_first_run(tmp: Path) -> None:
    repo = make_fixture_repo(tmp / "t1")
    marker = tmp / "t1" / ".last-audit"
    due, msg = ha.audit_due(repo_root=repo, marker_path=marker)
    check("first run (no marker) is due", due is True, msg)
    check("first run writes a marker file", marker.is_file())


def test_audit_due_below_interval(tmp: Path) -> None:
    repo = make_fixture_repo(tmp / "t2")
    marker = tmp / "t2" / ".last-audit"
    ha.audit_due(repo_root=repo, marker_path=marker)  # seeds the marker at current HEAD
    add_commits(repo, ha.AUDIT_INTERVAL - 1)
    due, msg = ha.audit_due(repo_root=repo, marker_path=marker)
    check(f"not due below interval ({ha.AUDIT_INTERVAL - 1} commits)", due is False, msg)


def test_audit_due_at_interval(tmp: Path) -> None:
    repo = make_fixture_repo(tmp / "t3")
    marker = tmp / "t3" / ".last-audit"
    ha.audit_due(repo_root=repo, marker_path=marker)
    add_commits(repo, ha.AUDIT_INTERVAL)
    due, msg = ha.audit_due(repo_root=repo, marker_path=marker)
    check(f"due at exactly the interval ({ha.AUDIT_INTERVAL} commits)", due is True, msg)


def test_audit_due_advances_marker(tmp: Path) -> None:
    repo = make_fixture_repo(tmp / "t4")
    marker = tmp / "t4" / ".last-audit"
    ha.audit_due(repo_root=repo, marker_path=marker)
    add_commits(repo, ha.AUDIT_INTERVAL)
    ha.audit_due(repo_root=repo, marker_path=marker)  # this run should fire + advance
    due_again, msg = ha.audit_due(repo_root=repo, marker_path=marker)
    check("marker advances after a due run (immediately re-checking is not due)", due_again is False, msg)


def test_audit_due_empty_marker_treated_as_first_run(tmp: Path) -> None:
    repo = make_fixture_repo(tmp / "t5")
    marker = tmp / "t5" / ".last-audit"
    marker.write_text("", encoding="utf-8")
    due, msg = ha.audit_due(repo_root=repo, marker_path=marker)
    check("empty marker file treated as first run, not a crash", due is True, msg)


def test_audit_due_no_git_repo_degrades_gracefully(tmp: Path) -> None:
    not_a_repo = tmp / "t6-not-a-repo"
    not_a_repo.mkdir()
    marker = tmp / "t6-not-a-repo" / ".last-audit"
    due, msg = ha.audit_due(repo_root=not_a_repo, marker_path=marker)
    check("no git repo -> not due, loud message, no crash", due is False and "cannot determine cadence" in msg, msg)
    check("no git repo -> no marker file written", not marker.is_file())


def test_audit_due_unreachable_marker_sha_degrades_gracefully(tmp: Path) -> None:
    repo = make_fixture_repo(tmp / "t7")
    marker = tmp / "t7" / ".last-audit"
    marker.write_text("0" * 40 + "\n", encoding="utf-8")  # syntactically valid, unreachable SHA
    due, msg = ha.audit_due(repo_root=repo, marker_path=marker)
    check("unreachable marker SHA -> not due, loud message, no crash", due is False and "cannot determine cadence" in msg, msg)


# ---------------------------------------------------------------- surface resolution


def test_always_loaded_includes_static_docs(root: Path) -> None:
    entries, warnings = ha.resolve_always_loaded_surfaces(repo_root=root)
    paths = {e["path"] for e in entries}
    check("CLAUDE.md present in Class A", "CLAUDE.md" in paths, paths)
    check("workflow.md present in Class A", "plugins/flow/docs/workflow.md" in paths, paths)
    check(".claude/rules/safety.md present in Class A", ".claude/rules/safety.md" in paths, paths)


def test_always_loaded_extracts_folded_description_only(root: Path) -> None:
    entries, _ = ha.resolve_always_loaded_surfaces(repo_root=root)
    ship_desc = next((e for e in entries if e["path"].startswith("plugins/flow/skills/ship/SKILL.md")), None)
    check("ship SKILL.md contributes a description-only entry to Class A", ship_desc is not None)
    if ship_desc is not None:
        check(
            "description-only entry is far smaller than the full SKILL.md body",
            ship_desc["chars"] < 100,
            ship_desc,
        )


def test_always_loaded_agent_description_extracted(root: Path) -> None:
    entries, _ = ha.resolve_always_loaded_surfaces(repo_root=root)
    auditor = next((e for e in entries if "agents/auditor.md" in e["path"]), None)
    check("agent description extracted into Class A", auditor is not None and auditor["chars"] > 0, auditor)


def test_always_loaded_missing_description_warns_not_crashes(root: Path) -> None:
    entries, warnings = ha.resolve_always_loaded_surfaces(repo_root=root)
    paths = {e["path"] for e in entries}
    check(
        "SKILL.md with no description contributes no Class A entry",
        not any("no-description" in p for p in paths),
    )
    check(
        "missing description is a loud warning, not a silent drop",
        any("no-description" in w for w in warnings),
        warnings,
    )


def test_invoked_surfaces_includes_full_skill_body(root: Path) -> None:
    entries, _ = ha.resolve_invoked_surfaces(repo_root=root)
    ship = next((e for e in entries if e["path"] == "plugins/flow/skills/ship/SKILL.md"), None)
    check("ship SKILL.md full body present in Class B", ship is not None)
    if ship is not None:
        check("Class B entry carries the FULL body, not just the description", ship["chars"] > 100, ship)


def test_report_separates_classes_and_never_sums_them(root: Path) -> None:
    report = ha.render_surfaces_report(repo_root=root)
    check("report names Class A", "Class A" in report)
    check("report names Class B", "Class B" in report)
    check("report states the two classes are never summed", "never summed" in report, report)


# The tests above only READ the fixture tree (resolve_*_surfaces takes no
# mutation path), so they share ONE tree instead of each paying to rebuild an
# identical seven-directory fixture. Tests that need to MUTATE a tree (add a
# file, start from empty) build their own below -- sharing would make their
# assertions depend on run order.
READ_ONLY_SURFACE_TESTS = [
    test_always_loaded_includes_static_docs,
    test_always_loaded_extracts_folded_description_only,
    test_always_loaded_agent_description_extracted,
    test_always_loaded_missing_description_warns_not_crashes,
    test_invoked_surfaces_includes_full_skill_body,
    test_report_separates_classes_and_never_sums_them,
]


def test_invoked_surfaces_excludes_project_dev_skills(tmp: Path) -> None:
    root = make_surface_fixture(tmp / "s-preship")
    (root / ".claude" / "skills" / "preship").mkdir(parents=True)
    (root / ".claude" / "skills" / "preship" / "SKILL.md").write_text(
        "---\nname: preship\ndescription: dev-only.\n---\n\nbody\n", encoding="utf-8",
    )
    entries, _ = ha.resolve_invoked_surfaces(repo_root=root)
    paths = {e["path"] for e in entries}
    check("project-dev skill body excluded from Class B (not shipped)", not any("preship" in p for p in paths), paths)


def test_missing_surfaces_directory_warns_not_crashes(tmp: Path) -> None:
    root = tmp / "s-empty"
    root.mkdir()
    entries, warnings = ha.resolve_invoked_surfaces(repo_root=root)
    check("missing skills dir -> zero entries, no crash", entries == [])
    check("missing skills dir -> loud warning", len(warnings) == 1 and "missing shipped skills directory" in warnings[0], warnings)


# --------------------------------------------------- audit-agent prompt guardrails


def test_audit_agent_prompt_protects_footgun_curated_safety(_tmp: Path) -> None:
    """Spec-walk item 3: the guardrail protecting FB-0010 footgun comments,
    curated canonical examples, and SAFETY markers must exist verbatim in
    the shipped audit-agent prompt doc -- not just asserted in this PR's
    plan text. Pins the actual prompt, so a future edit that drops the
    guardrail is caught here, not discovered live during an audit run."""
    doc_path = Path(__file__).resolve().parents[2] / "dev-docs" / "workflow.md"
    text = doc_path.read_text(encoding="utf-8")
    check(
        "FB-0010 footgun/incident-comment protection present",
        "footgun" in text and "FB-0010" in text,
    )
    check("curated canonical example protection present", "curated canonical example" in text)
    check("SAFETY marker protection present", "SAFETY" in text and "safety.md" in text)
    check("minimal-not-short guardrail present", "not \"short.\"" in text or "not \"short\"" in text)


# ---------------------------------------------------------------- runner


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="harness-audit-evals-") as tmp_str:
        tmp = Path(tmp_str)
        mutating_tests = [
            test_audit_due_first_run,
            test_audit_due_below_interval,
            test_audit_due_at_interval,
            test_audit_due_advances_marker,
            test_audit_due_empty_marker_treated_as_first_run,
            test_audit_due_no_git_repo_degrades_gracefully,
            test_audit_due_unreachable_marker_sha_degrades_gracefully,
            test_invoked_surfaces_excludes_project_dev_skills,
            test_missing_surfaces_directory_warns_not_crashes,
            test_audit_agent_prompt_protects_footgun_curated_safety,
        ]
        for test in mutating_tests:
            print(f"{test.__name__}:")
            test(tmp)

        # Read-only surface tests share ONE fixture tree -- see the comment on
        # READ_ONLY_SURFACE_TESTS above.
        shared_root = make_surface_fixture(tmp / "shared-surfaces")
        for test in READ_ONLY_SURFACE_TESTS:
            print(f"{test.__name__}:")
            test(shared_root)

    print()
    if _failures:
        print(f"{len(_failures)} FAILURE(S): {', '.join(_failures)}")
        return 1
    print("All harness_audit.py checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
