#!/usr/bin/env python3
"""Eval harness for FB-0098 (doctor slot-coverage honesty + design-language template).

Pins three things the FB-0098 PR changed:

  template  — `template/base/core-docs/design-language.md` exists, carries the
              five shape-rule headings (Axioms, Anti-patterns, Priority order,
              Tokens, Coverage gaps) the spike
              (`dev-docs/research/2026-09-design-md-investigation.md` §5a S3)
              recommended, contains no project-token-shaped strings (the
              project-agnostic quality bar), and lives where
              `template/base/bootstrap.sh`'s `core-docs/*.md` glob copies it.
  doctor    — Check 2.4 (`plugins/flow/skills/doctor/SKILL.md`) now includes
              `designLanguagePath`, gated on `uiSurface`, WARN not FAIL; and
              its unset-slot fallback resolves to `dev-docs/<slot>.md` —
              matching the schema's own declared per-slot `default` — not the
              `core-docs/` literal that was the PR's actual root cause (doctor
              was the one outlier against 16 other call sites + the schema).
              These are EXECUTED (the real extracted shell block, via
              `eval_utils.fenced_block`), not grepped — a check whose text
              merely mentions the right thing is not the same as a check that
              DOES the right thing (the same principle `run_role_slot_evals.py`
              already applies to Check 2.11).
  honesty   — doctor's frontmatter no longer claims "all 33 slots have
              sensible values" bare; it cites every check number the slot
              classification in Check 2.4's own prose assigns a slot to. This
              is the fan-out-omission class the PR exists to fix, so the
              expected check-citation set below must be kept in sync BY HAND
              with Check 2.4's classification prose if either changes — there
              is no single source of truth to derive it from mechanically
              (unlike the schema-driven default checks above, which read the
              schema directly rather than duplicating its values here).

Stdlib only. Run:
    python3 plugins/flow/evals/run_design_language_scaffold_evals.py
"""

from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from eval_utils import fenced_block

HERE = Path(__file__).parent
PLUGIN_ROOT = HERE.parent
REPO_ROOT = PLUGIN_ROOT.parent.parent
SCHEMA = PLUGIN_ROOT / "schema" / "flow.config.schema.json"
DOCTOR_SKILL = PLUGIN_ROOT / "skills" / "doctor" / "SKILL.md"
TEMPLATE = REPO_ROOT / "template" / "base" / "core-docs" / "design-language.md"
BOOTSTRAP = REPO_ROOT / "template" / "base" / "bootstrap.sh"
LINT_SCRIPT = PLUGIN_ROOT / "skills" / "doctor" / "lib" / "skill-composition-lint.py"

_LINT_MODULE = None


def _frontmatter_of(text: str) -> str:
    """Reuse skill-composition-lint.py's frontmatter parser (same helper
    run_review_brief_evals.py / run_skill_composition_evals.py import), rather
    than a second, subtly different hand-rolled split."""
    global _LINT_MODULE
    if _LINT_MODULE is None:
        spec = importlib.util.spec_from_file_location("skill_composition_lint", LINT_SCRIPT)
        _LINT_MODULE = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_LINT_MODULE)
    return _LINT_MODULE._frontmatter(text)

# The six doc-path slots Check 2.4 loops over as of FB-0098.
DOC_PATH_SLOTS = [
    "planPath", "specPath", "roadmapPath",
    "historyPath", "feedbackPath", "designLanguagePath",
]

# Every check number Check 2.4's own "deliberately not exhaustive" prose
# assigns a slot to, as of FB-0098 — see the module docstring's "honesty" note
# on why this can't be derived mechanically.
EXPECTED_CITED_CHECKS = ["2.3", "2.4", "2.7", "2.8", "2.9", "2.11"]

# Project-token-shaped strings the project-agnostic quality bar (CLAUDE.md)
# forbids in shipped plugin/template artifacts.
BANNED_TOKENS = ["md-manager", "pattaya", "sand-", "--space-", "geist", " mini "]

fails = 0


def check(cid, ok, detail=""):
    global fails
    if ok:
        print(f"PASS  [{cid}]")
    else:
        fails += 1
        print(f"FAIL  [{cid}]" + (f" — {detail}" if detail else ""))


def run_block(block, cwd, config):
    """Execute Check 2.4's real extracted shell block against a real temp repo."""
    (Path(cwd) / "flow.config.json").write_text(json.dumps(config))
    proc = subprocess.run(["sh", "-c", block], cwd=cwd,
                           capture_output=True, text=True, timeout=10)
    return proc.stdout


def main():
    # --- template: file exists, has the five shape headings --------------------
    check("template-1-exists", TEMPLATE.is_file(),
          f"{TEMPLATE} does not exist")
    if not TEMPLATE.is_file():
        print(f"\nFAILED: {fails} failing check(s)")
        return 1

    tmpl = TEMPLATE.read_text()
    for heading in ("Axioms", "Anti-patterns", "Priority order", "Tokens", "Coverage gaps"):
        check(f"template-2-heading-{heading.lower().replace(' ', '-')}",
              re.search(rf"^##\s+{re.escape(heading)}\b", tmpl, re.MULTILINE) is not None,
              f"missing '## {heading}' heading")

    check("template-3-authoring-rule",
          "observable" in tmpl.lower(),
          "missing the 'write corrections as observable decisions' authoring rule")

    lowered = tmpl.lower()
    leaked = [t for t in BANNED_TOKENS if t.lower() in lowered]
    check("template-4-no-project-tokens", not leaked,
          f"found project-token-shaped strings: {leaked}")

    # --- template: bootstrap.sh's core-docs/*.md glob would pick it up ---------
    check("template-5-location-matches-glob",
          TEMPLATE.parent.name == "core-docs" and TEMPLATE.suffix == ".md",
          "template must live at template/base/core-docs/*.md to be scaffolded")
    if BOOTSTRAP.is_file():
        bootstrap_text = BOOTSTRAP.read_text()
        check("template-6-bootstrap-globs-core-docs",
              'template/base/core-docs/' in bootstrap_text and '*.md' in bootstrap_text,
              "bootstrap.sh no longer globs template/base/core-docs/*.md")

    # --- doctor: Check 2.4's block, extracted and EXECUTED ---------------------
    doctor_full = DOCTOR_SKILL.read_text()
    block = fenced_block(doctor_full, "Check 2.4 —")
    check("doctor-1-block-extractable", block is not None,
          "could not extract Check 2.4's executable shell block")
    if block is None:
        print(f"\nFAILED: {fails} failing check(s)")
        return 1

    check("doctor-2-mentions-designLanguagePath", "designLanguagePath" in block)
    check("doctor-3-gated-on-uiSurface", "uiSurface" in block)
    check("doctor-4-no-core-docs-default-literal",
          'P="core-docs/' not in block,
          "the unset-slot default assignment must not hardcode core-docs/ — "
          "that was the PR's actual root cause (an outlier against the "
          "schema's own declared default and 16 other call sites)")
    check("doctor-5-dev-docs-default-literal",
          'P="dev-docs/' in block,
          "the unset-slot default assignment must build a dev-docs/ path, "
          "matching the schema's declared default")

    # --- doctor: unset-slot default matches the SCHEMA's own declared default --
    # Read the schema BEFORE exec-2 below, so exec-2's fixture filenames come
    # from the schema's own declared defaults rather than a second, independent
    # implementation of the slot -> filename transform (the shell block already
    # has the one real implementation; a Python re-derivation would let the
    # test silently validate its own logic instead of the actual contract).
    try:
        schema = json.loads(SCHEMA.read_text())
    except (OSError, ValueError) as e:
        check("join-1-schema-parses", False, str(e))
        schema = {}
    else:
        check("join-1-schema-parses", True)

    # uiSurface: true, nothing on disk — every slot (incl. designLanguagePath)
    # WARNs, AND each WARN's path matches the schema's own declared default.
    # One run serves both assertions (exec-1 + the former join-2) — no reason
    # to spawn two identical subprocesses for the same scenario.
    with tempfile.TemporaryDirectory() as td:
        out = run_block(block, td, {"uiSurface": True})
        warn_paths = dict(re.findall(r"\[WARN\] (\w+): (\S+) does not exist yet", out))
        for slot in DOC_PATH_SLOTS:
            check(f"exec-1-warn-missing-{slot}",
                  f"[WARN] {slot}:" in out,
                  f"expected a WARN for {slot} with nothing scaffolded; got:\n{out}")
            expected = schema.get("properties", {}).get(slot, {}).get("default")
            actual = warn_paths.get(slot)
            check(f"join-2-default-matches-schema-{slot}",
                  actual == expected,
                  f"schema declares default {expected!r} for {slot}, but Check "
                  f"2.4's own unset-slot fallback resolved to {actual!r}")

    # uiSurface: true, all six files present — every slot PASSes. Fixture
    # filenames come from the schema's own declared defaults (read above),
    # not a re-derivation of the slot -> filename transform.
    with tempfile.TemporaryDirectory() as td:
        for slot in DOC_PATH_SLOTS:
            default_path = schema.get("properties", {}).get(slot, {}).get("default")
            (Path(td) / default_path).parent.mkdir(parents=True, exist_ok=True)
            (Path(td) / default_path).write_text("stub")
        out = run_block(block, td, {"uiSurface": True})
        for slot in DOC_PATH_SLOTS:
            check(f"exec-2-pass-present-{slot}",
                  f"[PASS] {slot}:" in out,
                  f"expected a PASS for {slot} with dev-docs/ scaffolded; got:\n{out}")

    # uiSurface: false — designLanguagePath is explicitly N/A, not WARNed, and
    # not required (no dev-docs/design-language.md on disk in this temp repo).
    with tempfile.TemporaryDirectory() as td:
        out = run_block(block, td, {"uiSurface": False})
        check("exec-3-designLanguagePath-not-required-when-no-ui",
              "[WARN] designLanguagePath:" not in out,
              f"designLanguagePath must not WARN when uiSurface is false; got:\n{out}")
        check("exec-4-designLanguagePath-explicit-pass-when-no-ui",
              "designLanguagePath" in out and "uiSurface is false" in out,
              f"expected an explicit PASS explaining why designLanguagePath is "
              f"skipped, not silence; got:\n{out}")

    # --- honesty: frontmatter no longer over-promises, and cites every check ---
    frontmatter = _frontmatter_of(doctor_full)

    # The specific bad phrase (contiguous, whitespace-tolerant since the YAML
    # `>` block scalar folds newlines to spaces at parse time but the raw text
    # here still has them) — NOT a bare "33" anywhere, since the honest
    # replacement legitimately says "not all 33 of the schema's slots".
    check("honesty-1-no-bare-all-33-claim",
          re.search(r"all 33\s+slots have sensible values", frontmatter) is None,
          "frontmatter must not claim 'all 33 slots have sensible values' bare")
    for num in EXPECTED_CITED_CHECKS:
        check(f"honesty-2-cites-check-{num}",
              num in frontmatter,
              f"frontmatter must cite Check {num} — it's one of the checks the "
              f"slot classification assigns coverage to")

    total_marker = "passed" if fails == 0 else "FAILED"
    print(f"\n{total_marker}: {fails} failing check(s)")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
