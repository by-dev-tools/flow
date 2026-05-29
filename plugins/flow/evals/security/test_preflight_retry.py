#!/usr/bin/env python3
"""PR-H2 fixture: bounded-retry preflight contract for /flow:ship Step 1c.

The retry contract is prompt-driven (Claude follows N=3 in natural language)
not shell-driven, so end-to-end iteration behavior is non-deterministic by
construction. This fixture asserts the SHAPE of the contract that the agent
reads:

  (a) `preflightCmd` slot validates against the schema.
  (b) Unset slot path emits the loud-warning string (never silent no-op).
  (c) Malicious `preflightCmd` value READ via jq is opaque string (no exec).
  (d) `sh -c "$PREFLIGHT_CMD"` IS shell-eval — documented trust model
      paralleling typecheckCmd. Asserts the behavior matches docs.
  (e) Each SKILL.md (ship + ship-spike) contains the load-bearing contract
      language: N=3 cap, oscillation detection via diff-hash, fail-fast on
      exit 127, the do-not-disable-tests rule, and the do-not-add-suppressors
      rule. Text-grep against the SKILL.md, not runtime.

Run standalone: python3 plugins/flow/evals/security/test_preflight_retry.py

Exit code 0 if all asserts pass; 1 if any assert fails.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

# PLUGIN_ROOT = .../plugins/flow/ — matches test_cwd_constraint.py convention
PLUGIN_ROOT = Path(__file__).resolve().parent.parent.parent
SHIP_SKILL = PLUGIN_ROOT / "skills" / "ship" / "SKILL.md"
SHIP_SPIKE_SKILL = PLUGIN_ROOT / "skills" / "ship-spike" / "SKILL.md"
SCHEMA = PLUGIN_ROOT / "schema" / "flow.config.schema.json"


def test_schema_declares_preflightCmd() -> None:
    """The slot must exist with description + examples (FB-0003 pair-slot-with-consumer satisfaction)."""
    data = json.loads(SCHEMA.read_text())
    assert "preflightCmd" in data["properties"], (
        "schema does not declare preflightCmd slot — FB-0003 violation"
    )
    slot = data["properties"]["preflightCmd"]
    assert slot["type"] == "string", "preflightCmd must be a string"
    assert "description" in slot and len(slot["description"]) > 100, (
        "preflightCmd description too short — needs trust-boundary + retry-contract details"
    )
    assert "examples" in slot and len(slot["examples"]) >= 2, (
        "preflightCmd needs ≥2 examples for consumer guidance"
    )
    # Description must name the bounded-retry behavior (load-bearing contract surface)
    desc = slot["description"]
    for marker in ("bounded-retry", "N=3", "oscillation", "sh -c", "loud"):
        assert marker.lower() in desc.lower(), (
            f"preflightCmd description missing load-bearing marker {marker!r}"
        )
    print("  [PASS] schema declares preflightCmd with full description + examples")


def test_unset_slot_emits_loud_warning_text() -> None:
    """When preflightCmd is unset, both SKILL.md bodies emit the documented warning string."""
    for skill_path in (SHIP_SKILL, SHIP_SPIKE_SKILL):
        body = skill_path.read_text()
        # The warning must include the slot name, the 'not set' phrase, AND
        # name the affected skill (so users can grep for it).
        assert "flow.config.json.preflightCmd not set" in body, (
            f"{skill_path.name}: missing loud-warning emission for unset slot"
        )
        # Per FB-0006/0007 lineage: never silently no-op
        assert "skipping mechanical preflight" in body, (
            f"{skill_path.name}: missing 'skipping mechanical preflight' guidance text"
        )
    print("  [PASS] unset preflightCmd emits loud warning in ship + ship-spike (FB-0006/0007 lineage)")


def test_malicious_preflightCmd_jq_read_is_safe() -> None:
    """Reading preflightCmd via `jq -r '.preflightCmd // empty'` is string-only (no exec)."""
    with tempfile.TemporaryDirectory() as td:
        cwd = Path(td)
        marker = cwd / "PWNED_PREFLIGHT"
        cfg = {
            "preflightCmd": f"echo preflight; touch {marker}; echo pwned",
        }
        (cwd / "flow.config.json").write_text(json.dumps(cfg))
        result = subprocess.run(
            ["jq", "-r", ".preflightCmd // empty", "flow.config.json"],
            cwd=cwd, capture_output=True, text=True, timeout=5,
        )
        assert result.returncode == 0, f"jq read failed: {result.stderr}"
        assert not marker.exists(), (
            f"Command execution detected: marker {marker} was created by jq read"
        )
        assert "touch" in result.stdout, (
            f"Expected literal string in jq output; got: {result.stdout!r}"
        )
    print("  [PASS] jq -r '.preflightCmd' read is string-only (no exec)")


def test_sh_c_preflightCmd_executes_as_documented() -> None:
    """`sh -c "$PREFLIGHT_CMD"` IS shell-eval — this is the documented trust model.

    Parallels test_malicious_config.py::test_sh_c_with_jq_output_is_safe_for_intended_use.
    The test confirms behavior matches docs (project owns the slot at typecheckCmd-tier
    trust), not that it's somehow safe to put untrusted content in flow.config.json.
    """
    with tempfile.TemporaryDirectory() as td:
        cwd = Path(td)
        marker = cwd / "PWNED_INTENDED_PREFLIGHT"
        cfg = {"preflightCmd": f"touch {marker}; echo ran"}
        (cwd / "flow.config.json").write_text(json.dumps(cfg))
        # Mimic Step 1c's sh -c invocation
        result = subprocess.run(
            ["sh", "-c",
             'PREFLIGHT_CMD=$(jq -r ".preflightCmd // empty" flow.config.json); '
             'if [ -n "$PREFLIGHT_CMD" ]; then sh -c "$PREFLIGHT_CMD"; fi'],
            cwd=cwd, capture_output=True, text=True, timeout=5,
        )
        assert marker.exists(), (
            f"Expected preflightCmd to execute per documented trust model; marker not created.\n"
            f"STDOUT: {result.stdout}\nSTDERR: {result.stderr}"
        )
        assert "ran" in result.stdout, f"Expected end-to-end execution; got: {result.stdout!r}"
    print("  [PASS] sh -c \"$PREFLIGHT_CMD\" executes as documented (intentional trust model)")


def test_ship_skill_contains_load_bearing_contract_language() -> None:
    """The retry contract is prompt-driven — the SKILL.md text IS the contract.

    Each load-bearing element must appear in the SKILL.md body. A future edit that
    silently drops one of these is the FB-0010 silent-skip class — caught here.
    """
    for skill_path in (SHIP_SKILL, SHIP_SPIKE_SKILL):
        body = skill_path.read_text()
        contract_markers = {
            # The cap (N=3 total invocations)
            "N=3 cap": r"N\s*[≤=]?\s*3|3 attempts|attempt\s+\d+\s+of\s+3|1\.\.3",
            # Oscillation detection via diff-hash
            "diff-hash oscillation": r"oscillation|sha256sum.*git diff|diff.*hash",
            # Fail-fast on exit 127 (command not found, distinct from test failures)
            "exit 127 fail-fast": r"exit\s+127|command\s+not\s+found",
            # The reward-hacking guard: do not disable/modify tests to silence preflight
            # Broadened regex (push-further NIT) — accepts "do not", "don't", "never",
            # "must not" + modify/disable/stub/skip/silence + test forms, so future
            # tightening like "Never disable tests" or "Tests must not be modified" still
            # matches. The brittleness of the original regex was a real risk.
            "do-not-disable-tests rule": r"(?i)(do not|don.t|never|must not).+(modify|disable|stub|skip|silenc).+tests?|tests?.+(must not|cannot|never).+(be )?(disabled|modified|stubbed|skipped)",
            # The reward-hacking guard: no suppressor insertions. Expanded set per
            # push-further NIT — covers TS / Python (flake8 + mypy/pyright) / ESLint /
            # Biome (rising ESLint replacement) / Rust / Java conventions.
            "do-not-add-suppressors rule": r"@ts-ignore|noqa|type:\s*ignore|eslint-disable|biome-ignore|#\[allow|SuppressWarnings",
            # The reviewer-non-loop principle (load-bearing design call)
            "reviewers-stay-single-pass": r"(?i)single[- ]pass|never iterate on reviewer",
            # The docs-only early-exit (PR D lineage)
            "docs-only early-exit": r"docs[- ]only|no source files in diff",
        }
        for label, pattern in contract_markers.items():
            assert re.search(pattern, body), (
                f"{skill_path.name}: contract language missing for {label!r} "
                f"(regex: {pattern})"
            )
    print("  [PASS] ship + ship-spike SKILL.md contain all 7 load-bearing contract markers")


def test_default_branch_fallback_chain_present_in_step_1c() -> None:
    """Step 1c needs to re-resolve DEFAULT_BRANCH because Bash invocations don't share scope.

    Asserting this here protects against a future edit that drops the 3-tier
    fallback chain in Step 1c (which would silently degrade to literal 'main'
    on first-clone repos — exactly the FB-0008 stale-base failure mode).
    """
    for skill_path in (SHIP_SKILL, SHIP_SPIKE_SKILL):
        body = skill_path.read_text()
        # Extract Step 1c block (between "### 1c." and the next "###" or "## ")
        m = re.search(r"### 1c\..*?(?=\n###\s|\n##\s)", body, re.DOTALL)
        assert m, f"{skill_path.name}: Step 1c section not found"
        step_1c = m.group(0)
        # 3-tier fallback: git symbolic-ref → jq .defaultBranch → literal main
        assert "git symbolic-ref" in step_1c, (
            f"{skill_path.name}: Step 1c missing git symbolic-ref (tier 1 of FB-0008 chain)"
        )
        assert "defaultBranch" in step_1c, (
            f"{skill_path.name}: Step 1c missing defaultBranch fallback (tier 2)"
        )
        assert "DEFAULT_BRANCH=main" in step_1c or "=main\n" in step_1c, (
            f"{skill_path.name}: Step 1c missing literal 'main' fallback (tier 3)"
        )
    print("  [PASS] Step 1c re-resolves DEFAULT_BRANCH via the full 3-tier FB-0008 chain")


def main() -> int:
    print("Security/contract test: /flow:ship + ship-spike Step 1c bounded-retry preflight")
    failed = 0
    for fn in (
        test_schema_declares_preflightCmd,
        test_unset_slot_emits_loud_warning_text,
        test_malicious_preflightCmd_jq_read_is_safe,
        test_sh_c_preflightCmd_executes_as_documented,
        test_ship_skill_contains_load_bearing_contract_language,
        test_default_branch_fallback_chain_present_in_step_1c,
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
    print("\nAll preflight-retry contract tests passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
