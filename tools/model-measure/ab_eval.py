#!/usr/bin/env python3
"""Offline Opus-vs-Sonnet A/B scorer for flow's fixtured reviewers (roadmap
item M, Step 2, FB-0083/FB-0089).

Dev tooling, not a shipped plugin artifact -- see CLAUDE.md § 3 "Project-dev
infrastructure". Measurement only: this script never recommends or applies a
model swap, and it never spawns a live model call itself.

Why it can't spawn the live calls: `tools/model-measure/` is stdlib Python
with no Anthropic API key and no SDK dependency (CLAUDE.md tech stack: flow
"delegates to Claude Code subagents... no direct API calls"). Only a Claude
Code session can invoke `auditor` / `plan-critic` on a specific model, via
the Agent/Task tool's `model` override. So this script is the second half of
a two-part harness, same shape as `plugins/flow/evals/run_evals.py`'s
existing pluggable `run_auditor()`:

  1. A HUMAN OR ORCHESTRATING SESSION produces two raw text files per
     ground_truth.yaml case:
       <outputs-dir>/<case_id>.opus.txt
       <outputs-dir>/<case_id>.sonnet.txt
     by, for each case: rendering its context with
     `plugins/flow/evals/run_evals.render_context(case)`, then spawning the
     agent named by the fixture's own reviewer (auditor for plan/completion
     fixtures, plan-critic for scope/spec/coherence fixtures -- see each
     agent's own .md for its system prompt) once with model: opus and once
     with model: sonnet, giving it that rendered context as its task input,
     and saving its raw text response verbatim to the path above.
  2. THIS SCRIPT scores the two saved outputs: ground-truth pass/fail per
     model (reusing run_evals.check_required, not a forked copy), a
     finding-overlap metric between the two outputs, and a false-positive
     rate per model. If a --session-file is given (the transcript recorded
     while step 1 ran), it also reports token cost per model by reusing
     model_measure's already-proven sidecar attribution.

No live A/B sweep is triggered by running this file -- it only ever reads
files already on disk. Running step 1 for real is a separate, deliberate,
cost-incurring action (real Agent-tool invocations), left to whoever decides
to spend that cost.

Usage:
    python3 ab_eval.py --outputs-dir DIR [--session-file PATH] [--json]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_EVALS_DIR = _REPO_ROOT / "plugins" / "flow" / "evals"
sys.path.insert(0, str(_EVALS_DIR))
import run_evals  # noqa: E402

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import model_measure as mm  # noqa: E402


# ----------------------------------------------------------------- issue parsing

_ISSUE_HEADER_RE = re.compile(r"^ISSUE(?:\s+\d+)?\s*·\s*(.+)$")


def parse_issues(output: str) -> list[dict]:
    """Extract (severity, category) per `ISSUE` header line.

    Auditor headers carry no severity (`ISSUE · Unverified assumption`);
    plan-critic headers do (`ISSUE · BLOCKER · Scope drift`); both forms may
    be numbered (`ISSUE 2 · ...`). Splitting the header's remainder on the
    literal `·` delimiter (schema-fixed per each agent's Output format
    section) handles all four shapes without a severity-aware regex.
    """
    issues: list[dict] = []
    for line in output.splitlines():
        m = _ISSUE_HEADER_RE.match(line.strip())
        if not m:
            continue
        rest = [p.strip() for p in m.group(1).split("·") if p.strip()]
        if len(rest) >= 2:
            severity, category = rest[0], rest[1]
        elif len(rest) == 1:
            severity, category = None, rest[0]
        else:
            continue
        issues.append({"severity": severity, "category": category})
    return issues


def expected_categories(case: dict) -> set[str]:
    return {str(elem["category"]).lower() for elem in (case.get("required") or []) if "category" in elem}


def finding_overlap(issues_a: list[dict], issues_b: list[dict]) -> float:
    """Dice coefficient over issue categories (case-insensitive multiset).

    1.0 when both outputs raise the identical multiset of categories (incl.
    both empty); 0.0 when they share none. Category-only, not claim-text
    similarity -- cheap and deterministic, no LLM grading required.
    """
    ca = Counter(i["category"].lower() for i in issues_a)
    cb = Counter(i["category"].lower() for i in issues_b)
    common = sum((ca & cb).values())
    total = sum(ca.values()) + sum(cb.values())
    if total == 0:
        return 1.0
    return 2.0 * common / total


def false_positive_rate(issues: list[dict], expected_cats: set[str]) -> float | None:
    """Fraction of raised issues matching no expected category.

    Returns None (not 0.0) when the fixture declares no `category` check --
    there is nothing to measure a false positive against, and reporting 0.0
    would silently overstate confidence for those cases.
    """
    if not expected_cats:
        return None
    if not issues:
        return 0.0
    fp = sum(1 for i in issues if i["category"].lower() not in expected_cats)
    return fp / len(issues)


# ----------------------------------------------------------------- token cost


def token_cost_by_model(session_path: Path) -> tuple[dict, list[str]]:
    """Per-model token totals for one session transcript.

    Reuses model_measure's sidecar attribution (already proven against
    concurrent/nested spawns, see run_model_measure_evals.py) rather than
    re-deriving it; only re-buckets by *model* instead of by *agent type*,
    since an A/B run spawns the same agent type under two different models.

    Sums each invocation's totals exactly ONCE, mirroring model_measure's own
    aggregate_by_type -- an invocation whose `models` set has more than one
    entry (e.g. thinking + tool_use turns under different models mid-spawn)
    is bucketed once under a composite key, never added into every observed
    model's bucket (which would multi-count its tokens).
    """
    session_dir = mm.session_dir_for(session_path)
    invocations, warnings = mm.read_sidecar_subagents(session_dir)
    by_model: dict = {}
    for inv in invocations:
        models = inv["models"]
        if len(models) == 1:
            key = next(iter(models))
        elif not models:
            key = "unknown"
        else:
            key = "+".join(sorted(models))
        bucket = by_model.setdefault(key, {f: 0 for f in mm.USAGE_FIELDS})
        for field in mm.USAGE_FIELDS:
            bucket[field] += inv["totals"].get(field, 0)
    return by_model, warnings


# ----------------------------------------------------------------- scoring


def score_case(case: dict, opus_output: str, sonnet_output: str) -> dict:
    required = case.get("required") or []
    opus_checks = [run_evals.check_required(elem, opus_output) for elem in required]
    sonnet_checks = [run_evals.check_required(elem, sonnet_output) for elem in required]
    opus_issues = parse_issues(opus_output)
    sonnet_issues = parse_issues(sonnet_output)
    expected = expected_categories(case)
    return {
        "case_id": case.get("case_id"),
        "opus_ground_truth_pass": all(r.passed for r in opus_checks) if opus_checks else None,
        "sonnet_ground_truth_pass": all(r.passed for r in sonnet_checks) if sonnet_checks else None,
        "finding_overlap": finding_overlap(opus_issues, sonnet_issues),
        "opus_issue_count": len(opus_issues),
        "sonnet_issue_count": len(sonnet_issues),
        "opus_fp_rate": false_positive_rate(opus_issues, expected),
        "sonnet_fp_rate": false_positive_rate(sonnet_issues, expected),
    }


def _fmt(value) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, bool):
        return "PASS" if value else "FAIL"
    if isinstance(value, float):
        return f"{value:.0%}"
    return str(value)


def render_table(rows: list[dict]) -> str:
    header = (
        f"{'case_id':<40}{'opus_gt':>8}{'sonnet_gt':>10}{'overlap':>9}"
        f"{'opus_fp':>9}{'sonnet_fp':>10}{'opus_#':>7}{'sonnet_#':>9}"
    )
    lines = [header]
    for r in rows:
        lines.append(
            f"{r['case_id']:<40}{_fmt(r['opus_ground_truth_pass']):>8}"
            f"{_fmt(r['sonnet_ground_truth_pass']):>10}{_fmt(r['finding_overlap']):>9}"
            f"{_fmt(r['opus_fp_rate']):>9}{_fmt(r['sonnet_fp_rate']):>10}"
            f"{r['opus_issue_count']:>7}{r['sonnet_issue_count']:>9}"
        )
    return "\n".join(lines)


def summarize(rows: list[dict], token_costs: dict) -> dict:
    """Aggregate the per-case rows into the one number the eval exists to
    answer -- does Sonnet look comparable to Opus across the fixture set --
    rather than leaving a reader to eyeball and average N rows by hand.
    """
    n = len(rows)
    if n == 0:
        return {}
    opus_fp = [r["opus_fp_rate"] for r in rows if r["opus_fp_rate"] is not None]
    sonnet_fp = [r["sonnet_fp_rate"] for r in rows if r["sonnet_fp_rate"] is not None]
    summary = {
        "cases": n,
        "mean_finding_overlap": sum(r["finding_overlap"] for r in rows) / n,
        "opus_ground_truth_pass": sum(1 for r in rows if r["opus_ground_truth_pass"]),
        "sonnet_ground_truth_pass": sum(1 for r in rows if r["sonnet_ground_truth_pass"]),
        "opus_mean_fp_rate": (sum(opus_fp) / len(opus_fp)) if opus_fp else None,
        "sonnet_mean_fp_rate": (sum(sonnet_fp) / len(sonnet_fp)) if sonnet_fp else None,
    }
    if token_costs:
        # Model keys are real model ids (e.g. "claude-opus-5") or a composite
        # "model_a+model_b" -- substring match is sufficient and avoids
        # hardcoding a specific id string that would go stale on a rename.
        opus_tokens = sum(v.get("output_tokens", 0) for k, v in token_costs.items() if "opus" in k.lower())
        sonnet_tokens = sum(v.get("output_tokens", 0) for k, v in token_costs.items() if "sonnet" in k.lower())
        summary["opus_output_tokens"] = opus_tokens
        summary["sonnet_output_tokens"] = sonnet_tokens
        summary["token_delta_sonnet_minus_opus"] = sonnet_tokens - opus_tokens
    return summary


def render_summary(summary: dict) -> str:
    if not summary:
        return ""
    lines = [
        f"\nSummary across {summary['cases']} case(s):",
        f"  mean finding overlap: {summary['mean_finding_overlap']:.0%}",
        f"  ground-truth pass:    opus {summary['opus_ground_truth_pass']}/{summary['cases']}"
        f"  |  sonnet {summary['sonnet_ground_truth_pass']}/{summary['cases']}",
        f"  mean FP rate:         opus {_fmt(summary['opus_mean_fp_rate'])}"
        f"  |  sonnet {_fmt(summary['sonnet_mean_fp_rate'])}",
    ]
    if "opus_output_tokens" in summary:
        lines.append(
            f"  output tokens:        opus {summary['opus_output_tokens']:,}"
            f"  |  sonnet {summary['sonnet_output_tokens']:,}"
            f"  |  delta (sonnet-opus) {summary['token_delta_sonnet_minus_opus']:+,}"
        )
    return "\n".join(lines)


# ----------------------------------------------------------------- main


def run(ground_truth_path: Path, outputs_dir: Path) -> tuple[list[dict], list[str]]:
    cases = run_evals.load_ground_truth(ground_truth_path)
    rows: list[dict] = []
    skipped: list[str] = []
    for case in cases:
        case_id = case.get("case_id")
        opus_path = outputs_dir / f"{case_id}.opus.txt"
        sonnet_path = outputs_dir / f"{case_id}.sonnet.txt"
        if not (opus_path.is_file() and sonnet_path.is_file()):
            skipped.append(case_id)
            continue
        rows.append(score_case(
            case,
            opus_path.read_text(encoding="utf-8"),
            sonnet_path.read_text(encoding="utf-8"),
        ))
    return rows, skipped


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--ground-truth", default=str(_EVALS_DIR / "ground_truth.yaml"))
    parser.add_argument(
        "--outputs-dir", required=True,
        help="directory containing <case_id>.opus.txt / <case_id>.sonnet.txt pairs",
    )
    parser.add_argument("--session-file", default=None, help="transcript recorded while producing the outputs")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    outputs_dir = Path(args.outputs_dir)
    rows, skipped = run(Path(args.ground_truth), outputs_dir)

    token_costs, warnings = ({}, [])
    session_yielded_nothing = False
    if args.session_file:
        token_costs, warnings = token_cost_by_model(Path(args.session_file))
        session_yielded_nothing = not token_costs and not warnings

    summary = summarize(rows, token_costs)

    if args.json:
        print(json.dumps({
            "cases": rows, "skipped": skipped, "token_cost_by_model": token_costs,
            "warnings": warnings, "summary": summary,
        }, indent=2))
        return 0

    if rows:
        print(render_table(rows))
        summary_text = render_summary(summary)
        if summary_text:
            print(summary_text)
    else:
        print("ab_eval: no case has both <case_id>.opus.txt and <case_id>.sonnet.txt -- nothing to score.")
    if skipped:
        print(f"\nSKIPPED ({len(skipped)} case(s) missing one or both output files): {', '.join(skipped)}")
    if token_costs:
        print("\nToken cost by model (from --session-file):")
        for model, totals in sorted(token_costs.items()):
            print(f"  {model}: {totals}")
    if warnings:
        print(f"\nWARNING: {len(warnings)} subagent record(s) unreadable in --session-file:")
        for w in warnings:
            print(f"  - {w}")
    if session_yielded_nothing:
        print(f"\nNOTE: --session-file {args.session_file} yielded no subagent invocations -- token cost by model omitted.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
