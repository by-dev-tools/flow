#!/usr/bin/env python3
"""V2/V3a contract fixture: rendered capture + ephemeral HTML walkthrough.

Asserts the SHAPE of the V2 capture + V3a renderer contract (the runtime capture
itself is prompt-driven + MCP-dependent, so this fixture pins the static contract
the agent + renderer depend on):

  (a) findings-schema.json declares `criteria[].grounding` + top-level `open_questions[]`,
      ADDITIVELY — schema_version still "1.0", top-level `required` unchanged (so existing
      buffers still validate).
  (b) findings-example.json validates against the schema and models both new fields +
      a path-referenced screenshot observation.
  (c) flow.config.json schema declares the `verifyReportPath` slot (FB-0003 pair-slot-with-consumer).
  (d) render-report.py (stdlib) turns the example buffer into one self-contained HTML file
      with every required section, degrades gracefully on a missing screenshot file, and
      base64-inlines nothing it cannot read.
  (e) verify-build/SKILL.md encodes capture-and-persist (§5a), the render step (§10), and the
      open_questions[this-iteration] gate; rubric.md is re-grounded on frames+baseline (no stale
      "may be removed" marker); workflow.md Step-8 predicate carries the open-questions condition.

Run standalone: python3 plugins/flow/evals/security/test_v2_capture_render.py
Exit 0 if all asserts pass; 1 otherwise.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent.parent
VB = PLUGIN_ROOT / "skills" / "verify-build"
SCHEMA = VB / "lib" / "findings-schema.json"
EXAMPLE = VB / "lib" / "findings-example.json"
RENDERER = VB / "lib" / "render-report.py"
RUBRIC = VB / "lib" / "rubric.md"
SKILL = VB / "SKILL.md"
CONFIG_SCHEMA = PLUGIN_ROOT / "schema" / "flow.config.schema.json"
WORKFLOW = PLUGIN_ROOT / "docs" / "workflow.md"


def test_schema_fields_additive() -> None:
    s = json.loads(SCHEMA.read_text())
    assert s["properties"]["schema_version"]["const"] == "1.0", "schema_version must stay 1.0 (additive change)"
    crit = s["properties"]["criteria"]["items"]["properties"]
    assert "grounding" in crit, "criteria[].grounding not declared"
    g = crit["grounding"]
    assert set(g["properties"]) >= {"type", "statement", "citations", "decision_test"}, "grounding shape incomplete"
    assert g["properties"]["type"]["enum"] == ["need", "design-language", "craft-commitment", "open-question"], (
        "grounding.type enum wrong"
    )
    oq = s["properties"].get("open_questions")
    assert oq is not None, "top-level open_questions not declared"
    oqi = oq["items"]["properties"]
    assert set(oqi) >= {"question", "rationale", "recommended_default", "user_need_lens", "routing"}, (
        "open_questions item shape incomplete"
    )
    assert oqi["routing"]["enum"] == ["this-iteration", "future-planning"], "open_questions.routing enum wrong"
    # Additive: grounding + open_questions must NOT be in any required list.
    assert "grounding" not in s["properties"]["criteria"]["items"].get("required", []), "grounding must be optional"
    assert "open_questions" not in s.get("required", []), "open_questions must be optional (top-level required unchanged)"
    assert s["required"] == ["schema_version", "metadata", "overall_verdict", "exit_code", "criteria", "not_tested"], (
        "top-level required changed — not additive"
    )


def test_example_validates() -> None:
    s = json.loads(SCHEMA.read_text())
    ex = json.loads(EXAMPLE.read_text())
    c0 = ex["criteria"][0]
    assert c0.get("grounding", {}).get("type") == "need", "example criterion[0] missing need-grounding"
    assert any(o["type"] == "screenshot" for o in c0["observations"]), "example missing a screenshot observation"
    routings = {q["routing"] for q in ex.get("open_questions", [])}
    assert routings == {"this-iteration", "future-planning"}, "example must model both open_question routings"
    try:
        import jsonschema  # type: ignore
        jsonschema.validate(ex, s)
    except ImportError:
        # stdlib-only env: structural check already done above.
        pass


def test_config_declares_report_slot() -> None:
    c = json.loads(CONFIG_SCHEMA.read_text())
    assert "verifyReportPath" in c["properties"], "verifyReportPath slot not declared (FB-0003)"
    assert c["properties"]["verifyReportPath"].get("default", "").endswith(".html"), "verifyReportPath default should be an .html temp path"


def test_renderer_emits_full_report() -> None:
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "report.html"
        r = subprocess.run(
            [sys.executable, str(RENDERER), str(EXAMPLE), "--out", str(out)],
            capture_output=True, text=True,
        )
        assert r.returncode == 0, f"renderer exited {r.returncode}: {r.stderr}"
        html = out.read_text()
    required = [
        "<!doctype html>",
        "Verify-build walkthrough",          # hero
        "How a verdict / a choice earns its place",  # legend
        'id="criterion-0"',                  # per-criterion anchor
        "Relates to a need",                 # grounding callout
        "Open questions for you",            # standalone question block
        "this iteration",                    # routing label
        "Coverage — what we did and did not test",  # coverage/not-tested section
        "Screenshot not captured",           # graceful missing-frame (example path doesn't exist)
    ]
    for needle in required:
        assert needle in html, f"rendered report missing required section/marker: {needle!r}"
    assert "{esc(" not in html, "template leak in output (f-string not interpolated)"


def test_data_uri_allowlist() -> None:
    """A data:image/svg+xml screenshot content must NOT reach an <img src>; raster data URIs may (FB-0004)."""
    buf = {
        "schema_version": "1.0",
        "metadata": {"branch": "b", "head_sha_short": "s", "plugin_version": "1.6.0", "platform_hint": "ios"},
        "overall_verdict": "Unknown", "exit_code": 1,
        "criteria": [{
            "text": "c", "adversarial_cases": [],
            "observations": [
                {"type": "screenshot", "content": "data:image/svg+xml;base64,PHN2ZyBvbmxvYWQ9YWxlcnQoMSk+"},
                {"type": "screenshot", "content": "data:image/png;base64,iVBORw0KGgo="},
            ],
            "verdicts": {
                "correctness": {"verdict": "Unknown", "evidence": ["a", "b"], "notes": "x"},
                "regression": {"verdict": "Unknown", "evidence": ["a", "b"], "notes": "x"},
                "scope-creep": {"verdict": "Unknown", "evidence": ["a", "b"], "notes": "x"},
            },
            "aggregated_verdict": "Unknown",
        }],
        "not_tested": [],
    }
    with tempfile.TemporaryDirectory() as td:
        bp = Path(td) / "b.json"
        bp.write_text(json.dumps(buf))
        out = Path(td) / "r.html"
        r = subprocess.run([sys.executable, str(RENDERER), str(bp), "--out", str(out)], capture_output=True, text=True)
        assert r.returncode == 0, f"renderer exited {r.returncode}: {r.stderr}"
        html = out.read_text()
    assert '<img src="data:image/svg' not in html, "svg+xml data URI reached an <img src> (the leak)"
    assert "not in the raster-image allowlist" in html, "svg data URI was not rejected by the allowlist"
    assert '<img src="data:image/png;base64,iVBORw0KGgo=' in html, "legit raster data URI should still inline as an img"


def test_skill_and_rubric_and_workflow_contract() -> None:
    skill = SKILL.read_text()
    assert "## 5a. Capture-and-persist" in skill, "SKILL.md missing the §5a capture-and-persist step"
    assert "flow owns capture" in skill.lower() or "flow owns capture-and-persist" in skill.lower(), (
        "SKILL.md §5a must state flow owns capture (not /verify)"
    )
    assert "## 10. Render" in skill, "SKILL.md missing the §10 render step"
    assert "render-report.py" in skill, "SKILL.md does not invoke the renderer"
    assert "this-iteration" in skill, "SKILL.md does not document the open_questions this-iteration gate signal"
    # Cold-gate hardening (FB-0048): capture must be a11y-state-gated BEFORE the screenshot, and the
    # "reach each state" step must name a drive ladder rather than assume drivability.
    assert "a11y tree BEFORE" in skill, "§5a must gate the screenshot on an a11y state-assertion (FB-0048)"
    assert "drive ladder" in skill, "§5a must name the drive ladder (UI-automation → launch/env → can't-reach⇒Unknown) (FB-0048)"
    assert "--assets-dir" in skill, "§10 must pass --assets-dir so screenshot content paths resolve (gap 5)"
    # No hardcoded single platform in the capture step — must name the per-platform MCPs generically.
    assert "XcodeBuildMCP" in skill and "browser mcp" in skill.lower() and "mobile-mcp" in skill, (
        "SKILL.md §5a should name per-platform screenshot MCPs generically (browser MCP/web, XcodeBuildMCP/ios, mobile-mcp/android)"
    )

    rubric = RUBRIC.read_text()
    assert "may be removed" not in rubric, "stale 'may be removed' VLM marker still present in rubric"
    assert "baseline" in rubric.lower(), "rubric VLM section must judge pairwise-vs-baseline"
    assert "a11y tree" in rubric.lower(), "rubric must read text from the a11y tree (SV2 finding)"

    wf = WORKFLOW.read_text()
    assert "this-iteration" in wf and "blocks Step 8 auto-advance" in wf.replace("\n", " "), (
        "workflow.md Step-8 predicate missing the open_questions[this-iteration] blocking condition"
    )


def main() -> int:
    print("Contract test: V2 rendered-capture + V3a HTML walkthrough")
    failed = 0
    for fn in (
        test_schema_fields_additive,
        test_example_validates,
        test_config_declares_report_slot,
        test_renderer_emits_full_report,
        test_data_uri_allowlist,
        test_skill_and_rubric_and_workflow_contract,
    ):
        try:
            fn()
            print(f"  [PASS] {fn.__name__}")
        except AssertionError as e:
            print(f"  [FAIL] {fn.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"  [ERROR] {fn.__name__}: {type(e).__name__}: {e}")
            failed += 1
    if failed:
        print(f"\n{failed} test(s) failed.")
        return 1
    print("\nAll V2 capture/render contract tests passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
