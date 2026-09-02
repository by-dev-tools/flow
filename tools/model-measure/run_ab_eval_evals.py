#!/usr/bin/env python3
"""Eval harness for ab_eval.py (roadmap item M, Step 2, FB-0083).

Dev tooling, not a shipped plugin eval -- runs in its own CI job (see
.github/workflows/ci.yml), same non-shipped status as run_model_measure_evals.py.

Pins ab_eval.py's SCORING LOGIC against synthetic saved-output fixtures and a
synthetic sidecar transcript -- no live model call, no network, no API key.
The live A/B run itself (spawning real Opus/Sonnet subagents) is a separate,
deliberate, cost-incurring action documented in ab_eval.py's module
docstring; this harness never attempts it.

Stdlib only. Run:
    python3 tools/model-measure/run_ab_eval_evals.py
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import ab_eval  # noqa: E402
import run_model_measure_evals as rmme  # noqa: E402  (reuse TempSession, record helpers, check/_failures)

check = rmme.check


# ---------------------------------------------------------------- parse_issues


def test_parse_issues_auditor_no_severity() -> None:
    output = "ISSUE · Unverified assumption\n\nClaim:\n> x\n"
    issues = ab_eval.parse_issues(output)
    check("parse_issues: auditor header (no severity) extracted",
          issues == [{"severity": None, "category": "Unverified assumption"}], issues)


def test_parse_issues_plan_critic_with_severity() -> None:
    output = "ISSUE · BLOCKER · Scope drift\n\nClaim:\n> x\n"
    issues = ab_eval.parse_issues(output)
    check("parse_issues: plan-critic header (severity) extracted",
          issues == [{"severity": "BLOCKER", "category": "Scope drift"}], issues)


def test_parse_issues_numbered_multiple() -> None:
    output = (
        "AUDIT SUMMARY\n2 issues flagged\n\n---\n\n"
        "ISSUE 1 · Unverified assumption\nblock\n\n---\n\n"
        "ISSUE 2 · Unverified recall\nblock\n"
    )
    issues = ab_eval.parse_issues(output)
    check("parse_issues: numbered multi-issue output extracts both, in order",
          issues == [
              {"severity": None, "category": "Unverified assumption"},
              {"severity": None, "category": "Unverified recall"},
          ], issues)


def test_parse_issues_no_issues_flagged() -> None:
    output = "No issues flagged.\nNote: passive audit only checks stated evidence.\n"
    check("parse_issues: 'No issues flagged' yields empty list", ab_eval.parse_issues(output) == [])


# ---------------------------------------------------------------- finding_overlap


def test_finding_overlap_identical() -> None:
    a = [{"severity": None, "category": "Unverified assumption"}]
    b = [{"severity": None, "category": "unverified assumption"}]
    check("finding_overlap: identical categories (case-insensitive) == 1.0",
          ab_eval.finding_overlap(a, b) == 1.0)


def test_finding_overlap_disjoint() -> None:
    a = [{"severity": None, "category": "Unverified assumption"}]
    b = [{"severity": None, "category": "Scope drift"}]
    check("finding_overlap: disjoint categories == 0.0", ab_eval.finding_overlap(a, b) == 0.0)


def test_finding_overlap_both_empty() -> None:
    check("finding_overlap: both empty == 1.0 (full agreement on nothing found)",
          ab_eval.finding_overlap([], []) == 1.0)


def test_finding_overlap_partial() -> None:
    a = [{"severity": None, "category": "X"}, {"severity": None, "category": "Y"}]
    b = [{"severity": None, "category": "X"}, {"severity": None, "category": "Z"}]
    # Dice: common=1 (X), total=4 -> 2*1/4 = 0.5
    check("finding_overlap: partial overlap computes Dice coefficient exactly",
          ab_eval.finding_overlap(a, b) == 0.5, ab_eval.finding_overlap(a, b))


# ---------------------------------------------------------------- false_positive_rate


def test_fp_rate_no_expected_categories_returns_none() -> None:
    issues = [{"severity": None, "category": "Anything"}]
    check("false_positive_rate: no expected categories -> None, not 0.0 (nothing to measure against)",
          ab_eval.false_positive_rate(issues, set()) is None)


def test_fp_rate_all_matched() -> None:
    issues = [{"severity": None, "category": "Scope drift"}]
    check("false_positive_rate: all issues match expected -> 0.0",
          ab_eval.false_positive_rate(issues, {"scope drift"}) == 0.0)


def test_fp_rate_one_unmatched() -> None:
    issues = [
        {"severity": None, "category": "Scope drift"},
        {"severity": None, "category": "Bogus category"},
    ]
    check("false_positive_rate: one of two issues unmatched -> 0.5",
          ab_eval.false_positive_rate(issues, {"scope drift"}) == 0.5)


def test_fp_rate_no_issues_raised() -> None:
    check("false_positive_rate: no issues raised, expected non-empty -> 0.0",
          ab_eval.false_positive_rate([], {"scope drift"}) == 0.0)


# ---------------------------------------------------------------- score_case


def test_score_case_integrates_ground_truth_and_overlap() -> None:
    case = {
        "case_id": "synthetic",
        "required": [{"category": "Unverified assumption"}],
    }
    opus_output = "ISSUE · Unverified assumption\n\nClaim:\n> x\n"
    sonnet_output = "No issues flagged.\n"
    result = ab_eval.score_case(case, opus_output, sonnet_output)
    check("score_case: opus ground-truth check (category present) passes",
          result["opus_ground_truth_pass"] is True, result)
    check("score_case: sonnet ground-truth check (category absent) fails",
          result["sonnet_ground_truth_pass"] is False, result)
    check("score_case: finding_overlap reflects the disagreement (0.0)",
          result["finding_overlap"] == 0.0, result)
    check("score_case: opus_issue_count / sonnet_issue_count exact",
          result["opus_issue_count"] == 1 and result["sonnet_issue_count"] == 0, result)


# ---------------------------------------------------------------- token_cost_by_model


def test_token_cost_by_model_reuses_sidecar_attribution() -> None:
    with rmme.TempSession() as s:
        s.write_main([rmme.assistant_record("m1", "claude-sonnet-5", rmme.usage(input_tokens=1))])
        s.write_subagent("a1", "auditor", "toolu_1", [
            rmme.assistant_record("sm1", "claude-opus-5", rmme.usage(input_tokens=10, output_tokens=20)),
        ])
        s.write_subagent("a2", "auditor", "toolu_2", [
            rmme.assistant_record("sm2", "claude-sonnet-5", rmme.usage(input_tokens=5, output_tokens=7)),
        ])
        by_model, warnings = ab_eval.token_cost_by_model(s.session_path)
        check("token_cost_by_model: opus bucket exact",
              by_model.get("claude-opus-5") == rmme.usage(input_tokens=10, output_tokens=20), by_model)
        check("token_cost_by_model: sonnet bucket exact",
              by_model.get("claude-sonnet-5") == rmme.usage(input_tokens=5, output_tokens=7), by_model)
        check("token_cost_by_model: no warnings on a clean transcript", warnings == [], warnings)


def test_token_cost_by_model_multi_model_invocation_sums_once() -> None:
    # Regression test for the double-counting bug the altitude review caught:
    # an invocation whose `models` set has >1 entry must be summed ONCE, under
    # a composite key -- never added into every observed model's bucket.
    with rmme.TempSession() as s:
        s.write_main([rmme.assistant_record("m1", "claude-sonnet-5", rmme.usage(input_tokens=1))])
        s.write_subagent("a1", "auditor", "toolu_1", [
            rmme.assistant_record("sm1", "claude-opus-5", rmme.usage(input_tokens=10, output_tokens=1)),
            rmme.assistant_record("sm2", "claude-sonnet-5", rmme.usage(input_tokens=5, output_tokens=1)),
        ])
        by_model, _warnings = ab_eval.token_cost_by_model(s.session_path)
        check("token_cost_by_model: multi-model invocation keyed under a composite, not either model alone",
              "claude-opus-5" not in by_model and "claude-sonnet-5" not in by_model
              and "claude-opus-5+claude-sonnet-5" in by_model, by_model)
        check("token_cost_by_model: multi-model invocation's totals summed exactly once (not doubled)",
              by_model.get("claude-opus-5+claude-sonnet-5") == rmme.usage(input_tokens=15, output_tokens=2), by_model)


def test_token_cost_by_model_missing_transcript_no_crash() -> None:
    missing = Path(tempfile.gettempdir()) / "ab-eval-does-not-exist.jsonl"
    by_model, warnings = ab_eval.token_cost_by_model(missing)
    check("token_cost_by_model: missing transcript returns empty, no crash",
          by_model == {} and warnings == [])


# ---------------------------------------------------------------- summarize / render_summary


def test_summarize_aggregates_correctly() -> None:
    rows = [
        {"opus_ground_truth_pass": True, "sonnet_ground_truth_pass": False,
         "finding_overlap": 1.0, "opus_fp_rate": 0.0, "sonnet_fp_rate": 0.5},
        {"opus_ground_truth_pass": True, "sonnet_ground_truth_pass": True,
         "finding_overlap": 0.0, "opus_fp_rate": None, "sonnet_fp_rate": 0.0},
    ]
    summary = ab_eval.summarize(rows, {})
    check("summarize: cases + mean_finding_overlap exact",
          summary["cases"] == 2 and summary["mean_finding_overlap"] == 0.5, summary)
    check("summarize: ground-truth pass counts exact",
          summary["opus_ground_truth_pass"] == 2 and summary["sonnet_ground_truth_pass"] == 1, summary)
    check("summarize: mean FP rate excludes None (opus_fp mean over 1 value, not 2)",
          summary["opus_mean_fp_rate"] == 0.0 and summary["sonnet_mean_fp_rate"] == 0.25, summary)
    check("summarize: no token fields when token_costs is empty",
          "opus_output_tokens" not in summary, summary)


def test_summarize_includes_token_delta_when_costs_given() -> None:
    rows = [{"opus_ground_truth_pass": True, "sonnet_ground_truth_pass": True,
             "finding_overlap": 1.0, "opus_fp_rate": 0.0, "sonnet_fp_rate": 0.0}]
    token_costs = {"claude-opus-5": {"output_tokens": 500}, "claude-sonnet-5": {"output_tokens": 300}}
    summary = ab_eval.summarize(rows, token_costs)
    check("summarize: token totals + delta computed from token_costs",
          summary["opus_output_tokens"] == 500 and summary["sonnet_output_tokens"] == 300
          and summary["token_delta_sonnet_minus_opus"] == -200, summary)


def test_summarize_empty_rows_returns_empty() -> None:
    check("summarize: no rows -> empty summary, no crash", ab_eval.summarize([], {}) == {})


# ---------------------------------------------------------------- run() / main() end-to-end


def _write_ground_truth(path: Path) -> None:
    path.write_text(
        "- case_id: synthetic_case\n"
        "  fixture: fixtures/does_not_matter.jsonl\n"
        "  required:\n"
        "    - category: Unverified assumption\n",
        encoding="utf-8",
    )


def test_run_scores_case_with_both_outputs_present() -> None:
    tmp = Path(tempfile.mkdtemp(prefix="ab-eval-run-"))
    try:
        gt = tmp / "ground_truth.yaml"
        _write_ground_truth(gt)
        (tmp / "synthetic_case.opus.txt").write_text("ISSUE · Unverified assumption\n\nClaim:\n> x\n", encoding="utf-8")
        (tmp / "synthetic_case.sonnet.txt").write_text("No issues flagged.\n", encoding="utf-8")
        rows, skipped = ab_eval.run(gt, tmp)
        check("run: one case scored, none skipped", len(rows) == 1 and skipped == [], (rows, skipped))
        check("run: scored case_id matches", rows[0]["case_id"] == "synthetic_case", rows)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_run_skips_case_missing_one_output_file() -> None:
    tmp = Path(tempfile.mkdtemp(prefix="ab-eval-run-"))
    try:
        gt = tmp / "ground_truth.yaml"
        _write_ground_truth(gt)
        (tmp / "synthetic_case.opus.txt").write_text("No issues flagged.\n", encoding="utf-8")
        # sonnet output intentionally absent
        rows, skipped = ab_eval.run(gt, tmp)
        check("run: case with only one output file present is skipped, not scored with a blank",
              rows == [] and skipped == ["synthetic_case"], (rows, skipped))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_main_cli_smoke_json() -> None:
    tmp = Path(tempfile.mkdtemp(prefix="ab-eval-cli-"))
    try:
        gt = tmp / "ground_truth.yaml"
        _write_ground_truth(gt)
        (tmp / "synthetic_case.opus.txt").write_text("ISSUE · Unverified assumption\n\nClaim:\n> x\n", encoding="utf-8")
        (tmp / "synthetic_case.sonnet.txt").write_text("No issues flagged.\n", encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, str(HERE / "ab_eval.py"),
             "--ground-truth", str(gt), "--outputs-dir", str(tmp), "--json"],
            capture_output=True, text=True, check=False,
        )
        check("main: CLI exits 0", proc.returncode == 0, proc.stderr)
        data = json.loads(proc.stdout)
        check("main: JSON output has one scored case", len(data.get("cases", [])) == 1, data)
        check("main: JSON output includes warnings + summary keys (UX-designer regression)",
              "warnings" in data and "summary" in data, data)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_main_cli_text_mode_includes_summary_line() -> None:
    tmp = Path(tempfile.mkdtemp(prefix="ab-eval-cli-text-"))
    try:
        gt = tmp / "ground_truth.yaml"
        _write_ground_truth(gt)
        (tmp / "synthetic_case.opus.txt").write_text("ISSUE · Unverified assumption\n\nClaim:\n> x\n", encoding="utf-8")
        (tmp / "synthetic_case.sonnet.txt").write_text("No issues flagged.\n", encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, str(HERE / "ab_eval.py"), "--ground-truth", str(gt), "--outputs-dir", str(tmp)],
            capture_output=True, text=True, check=False,
        )
        check("main: text mode exits 0", proc.returncode == 0, proc.stderr)
        check("main: text-mode output includes the aggregate summary the eval exists to answer",
              "Summary across 1 case" in proc.stdout, proc.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_main_cli_session_file_yields_nothing_prints_note() -> None:
    # Regression case (UX-designer lens): a --session-file that resolves but
    # has no matching subagent invocations must not silently omit the section.
    tmp = Path(tempfile.mkdtemp(prefix="ab-eval-cli-session-"))
    try:
        gt = tmp / "ground_truth.yaml"
        _write_ground_truth(gt)
        (tmp / "synthetic_case.opus.txt").write_text("No issues flagged.\n", encoding="utf-8")
        (tmp / "synthetic_case.sonnet.txt").write_text("No issues flagged.\n", encoding="utf-8")
        session_path = tmp / "session.jsonl"
        session_path.write_text(json.dumps({
            "type": "assistant", "isSidechain": False,
            "message": {"role": "assistant", "id": "m1", "model": "claude-sonnet-5",
                        "usage": {"input_tokens": 1, "output_tokens": 1,
                                  "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0},
                        "content": [{"type": "text", "text": "x"}]},
        }) + "\n", encoding="utf-8")
        # No subagents/ directory at all -- a session with zero subagent invocations.
        proc = subprocess.run(
            [sys.executable, str(HERE / "ab_eval.py"), "--ground-truth", str(gt),
             "--outputs-dir", str(tmp), "--session-file", str(session_path)],
            capture_output=True, text=True, check=False,
        )
        check("main: exits 0", proc.returncode == 0, proc.stderr)
        check("main: an empty --session-file result is explicitly noted, not silently omitted",
              "NOTE:" in proc.stdout and "yielded no subagent invocations" in proc.stdout, proc.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_main_cli_no_outputs_dir_no_crash() -> None:
    tmp = Path(tempfile.mkdtemp(prefix="ab-eval-cli-empty-"))
    try:
        gt = tmp / "ground_truth.yaml"
        _write_ground_truth(gt)
        outputs = tmp / "outputs"
        outputs.mkdir()
        proc = subprocess.run(
            [sys.executable, str(HERE / "ab_eval.py"),
             "--ground-truth", str(gt), "--outputs-dir", str(outputs)],
            capture_output=True, text=True, check=False,
        )
        check("main: no output files present -> exits 0, no crash", proc.returncode == 0, proc.stderr)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


TESTS = [
    test_parse_issues_auditor_no_severity,
    test_parse_issues_plan_critic_with_severity,
    test_parse_issues_numbered_multiple,
    test_parse_issues_no_issues_flagged,
    test_finding_overlap_identical,
    test_finding_overlap_disjoint,
    test_finding_overlap_both_empty,
    test_finding_overlap_partial,
    test_fp_rate_no_expected_categories_returns_none,
    test_fp_rate_all_matched,
    test_fp_rate_one_unmatched,
    test_fp_rate_no_issues_raised,
    test_score_case_integrates_ground_truth_and_overlap,
    test_token_cost_by_model_reuses_sidecar_attribution,
    test_token_cost_by_model_multi_model_invocation_sums_once,
    test_token_cost_by_model_missing_transcript_no_crash,
    test_summarize_aggregates_correctly,
    test_summarize_includes_token_delta_when_costs_given,
    test_summarize_empty_rows_returns_empty,
    test_run_scores_case_with_both_outputs_present,
    test_run_skips_case_missing_one_output_file,
    test_main_cli_smoke_json,
    test_main_cli_text_mode_includes_summary_line,
    test_main_cli_session_file_yields_nothing_prints_note,
    test_main_cli_no_outputs_dir_no_crash,
]


def main() -> int:
    for test in TESTS:
        print(f"-- {test.__name__}")
        test()
    print()
    if rmme._failures:
        print(f"FAILED: {len(rmme._failures)} eval(s): {', '.join(rmme._failures)}")
        return 1
    print(f"All {len(TESTS)} ab_eval evals passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
