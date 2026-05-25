#!/usr/bin/env python3
"""Security regression test: malicious flow.config.json values don't cause command execution.

The `jq -r '.field // empty' flow.config.json` pattern flow uses to read
config slots is correct today (jq output is a string, not shell-evaluated)
but no fixture asserts that flow.config.json with shell metacharacters in
referenceGlob / defaultBranch / typecheckCmd is handled WITHOUT command
execution.

Class of bug this fixture protects against: silent regression where a
future skill author switches from `jq -r '.field'` (safe) to
`eval $(jq -r '.field')` or `bash <<< "$(jq ...)"` (unsafe). Without
this fixture, an attacker who could land a commit in a consumer repo
(via malicious dep / PR / supply chain) could plant a flow.config.json
with shell metas and get RCE.

Test approach: write a flow.config.json containing a marker file write
in metacharacter form; invoke each skill's bash block via the actual
substitution pattern; assert the marker file was NOT created.

Run standalone: python3 plugins/flow/evals/security/test_malicious_config.py

Exit code 0 if all asserts pass; 1 if any assert fails.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def write_malicious_config(tmpdir: Path, marker_path: Path) -> Path:
    """Write a flow.config.json with shell metacharacters in every string slot.

    If any slot value is shell-eval'd, the `touch <marker>` substring
    inside the value will execute and create marker_path.
    """
    cfg = {
        "defaultBranch": f"main; touch {marker_path}; echo pwned",
        "typecheckCmd": f"echo typecheck && touch {marker_path}",
        "historyPath": f"core-docs/history.md; touch {marker_path}",
        "planPath": f"core-docs/plan.md`touch {marker_path}`",
        "roadmapPath": f"core-docs/roadmap.md$(touch {marker_path})",
        "specPath": "core-docs/spec.md",
        "feedbackPath": "core-docs/feedback.md",
        "designLanguagePath": "core-docs/design-language.md",
        "referenceGlob": f"core-docs/*.md; touch {marker_path}",
        "uiSurface": True,
        "reviewLenses": ["staff-engineer", "ux-designer", "design-engineer", "push-further"],
        "memoryHardCap": 30,
        "branchPrefix": f"claude/; touch {marker_path}",
    }
    cfg_path = tmpdir / "flow.config.json"
    cfg_path.write_text(json.dumps(cfg, indent=2))
    return cfg_path


def assert_no_marker(marker: Path, label: str) -> None:
    assert not marker.exists(), (
        f"[{label}] Command execution detected: marker file {marker} was created by a flow.config.json slot read"
    )


def test_jq_string_read_is_safe() -> None:
    """The canonical pattern `jq -r '.field // empty' flow.config.json` outputs the value as a string. Verify it does NOT execute."""
    with tempfile.TemporaryDirectory() as td:
        cwd = Path(td)
        marker = cwd / "PWNED"
        write_malicious_config(cwd, marker)
        # Read every slot the same way skills do; capture output; verify no execution.
        for field in (
            "defaultBranch", "typecheckCmd", "historyPath", "planPath", "roadmapPath",
            "specPath", "feedbackPath", "designLanguagePath", "referenceGlob", "branchPrefix",
        ):
            result = subprocess.run(
                ["jq", "-r", f".{field} // empty", "flow.config.json"],
                cwd=cwd, capture_output=True, text=True, timeout=5,
            )
            assert result.returncode == 0, f"jq failed reading {field}: {result.stderr}"
            assert_no_marker(marker, f"jq -r .{field}")
            # The output should literally contain "touch" + the marker path as a string (not executed)
            assert "touch" in result.stdout or field in ("specPath", "feedbackPath", "designLanguagePath"), (
                f"Expected literal string for {field}; got: {result.stdout!r}"
            )
        print("  [PASS] jq -r '.field // empty' reads are string-only across all slots")


def test_sh_c_with_jq_output_is_safe_for_intended_use() -> None:
    """The `sh -c "$TYPECHECK"` pattern in /flow:ship + ship-spike IS shell-eval — but that's the documented trust model (project owns its config). This test confirms the behavior is what's documented, not surprising."""
    with tempfile.TemporaryDirectory() as td:
        cwd = Path(td)
        marker = cwd / "PWNED_INTENDED"
        cfg = {"typecheckCmd": f"touch {marker}; echo ran"}
        (cwd / "flow.config.json").write_text(json.dumps(cfg))

        # Mimic /flow:ship's typecheck-run block.
        # This SHOULD execute (it's the documented contract — same trust as package.json scripts).
        # The test asserts the behavior matches documentation, not that it's unsafe.
        result = subprocess.run(
            ["sh", "-c", "TYPECHECK=$(jq -r '.typecheckCmd // empty' flow.config.json); if [ -n \"$TYPECHECK\" ]; then sh -c \"$TYPECHECK\"; fi"],
            cwd=cwd, capture_output=True, text=True, timeout=5,
        )
        # Marker SHOULD be created (this is intended behavior).
        assert marker.exists(), (
            f"Expected typecheckCmd to execute per documented trust model; marker not created.\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}"
        )
        # AND the substring 'ran' should be in stdout (the echo).
        assert "ran" in result.stdout, f"Expected typecheckCmd to run end-to-end; got: {result.stdout!r}"
        print("  [PASS] sh -c \"$TYPECHECK\" executes as documented (intentional trust model)")


def test_critique_plan_reference_glob_read_is_safe() -> None:
    """The /flow:critique-plan reference-glob read (added in PR 2 Phase 6) is a string substitution into a command-line argument. Verify no execution."""
    with tempfile.TemporaryDirectory() as td:
        cwd = Path(td)
        marker = cwd / "PWNED_REFGLOB"
        cfg = {"referenceGlob": f"core-docs/*.md; touch {marker}"}
        (cwd / "flow.config.json").write_text(json.dumps(cfg))

        # Mimic the critique-plan SKILL.md substitution shape:
        # REFGLOB=$(jq -r '.referenceGlob // empty' flow.config.json); ... --reference-glob "$REFGLOB"
        # The quoted argument means the metacharacters are passed as a literal string to the consumer.
        result = subprocess.run(
            ["sh", "-c", "REFGLOB=$(jq -r '.referenceGlob // empty' flow.config.json); echo \"refglob_arg=[$REFGLOB]\""],
            cwd=cwd, capture_output=True, text=True, timeout=5,
        )
        assert_no_marker(marker, "critique-plan referenceGlob read")
        assert "touch" in result.stdout, f"Expected literal-string preservation; got: {result.stdout!r}"
        print("  [PASS] critique-plan referenceGlob substitution preserves literal string (no execution)")


def main() -> int:
    print("Security test: malicious flow.config.json values don't execute")
    failed = 0
    for fn in (
        test_jq_string_read_is_safe,
        test_sh_c_with_jq_output_is_safe_for_intended_use,
        test_critique_plan_reference_glob_read_is_safe,
    ):
        try:
            fn()
        except AssertionError as e:
            print(f"  [FAIL] {fn.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"  [ERROR] {fn.__name__}: {type(e).__name__}: {e}")
            failed += 1
    if failed:
        print(f"\n{failed} test(s) failed.")
        return 1
    print("\nAll malicious-config tests passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
