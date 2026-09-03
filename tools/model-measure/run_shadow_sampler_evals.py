#!/usr/bin/env python3
"""Eval harness for shadow_sampler.py (roadmap item M, Step 3, FB-0083).

Dev tooling, not a shipped plugin eval -- runs in its own CI job (see
.github/workflows/ci.yml). Pins recommend_model's default-to-Opus behavior,
record_sample's reuse of model_measure's sidecar attribution, aggregate()'s
bucketing, --dry-run's zero-live-call shape, and the two structural
guarantees that keep this an opt-in tool rather than a routing mechanism:
nothing under plugins/flow/ references it, and the log path it writes to is
already covered by the repo's blanket `tools/` gitignore.

Stdlib only. Run:
    python3 tools/model-measure/run_shadow_sampler_evals.py
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import shadow_sampler as ss  # noqa: E402
import run_model_measure_evals as rmme  # noqa: E402  (reuse TempSession, record helpers, check/_failures)

check = rmme.check


class FakeRng:
    """Deterministic stand-in for random.Random -- avoids depending on the
    Mersenne Twister's exact output sequence for a given seed."""

    def __init__(self, values: list[float]) -> None:
        self._values = list(values)

    def random(self) -> float:
        return self._values.pop(0)


# ---------------------------------------------------------------- recommend_model


def test_recommend_model_below_threshold_is_sonnet() -> None:
    result = ss.recommend_model(sonnet_rate=0.1, rng=FakeRng([0.05]))
    check("recommend_model: draw below sonnet_rate -> sonnet", result == "sonnet", result)


def test_recommend_model_above_threshold_is_opus() -> None:
    result = ss.recommend_model(sonnet_rate=0.1, rng=FakeRng([0.5]))
    check("recommend_model: draw above sonnet_rate -> opus", result == "opus", result)


def test_recommend_model_default_rate_favors_opus_statistically() -> None:
    import random
    rng = random.Random(42)
    draws = [ss.recommend_model(rng=rng) for _ in range(2000)]
    sonnet_fraction = draws.count("sonnet") / len(draws)
    # Default sonnet_rate is 0.1; a 2000-draw sample should land well within
    # [0.05, 0.15] with overwhelming probability -- a real statistical check,
    # not pinned to the Mersenne Twister's exact sequence.
    check("recommend_model: default rate keeps Opus the overwhelming majority assignment",
          0.05 <= sonnet_fraction <= 0.15, f"sonnet_fraction={sonnet_fraction}")


# ---------------------------------------------------------------- record_sample


def test_record_sample_reuses_sidecar_attribution() -> None:
    with rmme.TempSession() as s:
        s.write_main([rmme.assistant_record("m1", "claude-sonnet-5", rmme.usage(input_tokens=1))])
        s.write_subagent("a1", "auditor", "toolu_1", [
            rmme.assistant_record("sm1", "claude-opus-5", rmme.usage(input_tokens=10, output_tokens=20)),
        ])
        log_path = s.dir / "samples.jsonl"
        record = ss.record_sample(
            log_path, agent_type="auditor", model="opus",
            session_transcript_path=str(s.session_path), tool_use_id="toolu_1",
        )
        check("record_sample: totals match model_measure's sidecar attribution",
              record["totals"] == rmme.usage(input_tokens=10, output_tokens=20), record)
        check("record_sample: observed_models reflects the transcript's actual model",
              record["observed_models"] == ["claude-opus-5"], record)
        lines = log_path.read_text(encoding="utf-8").splitlines()
        check("record_sample: appends exactly one JSONL line", len(lines) == 1, lines)
        check("record_sample: written line round-trips through json.loads",
              json.loads(lines[0]) == record)


def test_record_sample_unknown_tool_use_id_totals_none() -> None:
    with rmme.TempSession() as s:
        s.write_main([rmme.assistant_record("m1", "claude-sonnet-5", rmme.usage(input_tokens=1))])
        s.write_subagent("a1", "auditor", "toolu_1", [
            rmme.assistant_record("sm1", "claude-opus-5", rmme.usage(input_tokens=10)),
        ])
        log_path = s.dir / "samples.jsonl"
        record = ss.record_sample(
            log_path, agent_type="auditor", model="opus",
            session_transcript_path=str(s.session_path), tool_use_id="toolu_does_not_exist",
        )
        check("record_sample: unmatched tool_use_id yields totals=None, not a crash",
              record["totals"] is None, record)


def test_record_sample_carries_lookup_warnings() -> None:
    # Regression case (staff-engineer lens): a matching-but-malformed meta
    # file must surface a warning on the record, not disappear silently.
    with rmme.TempSession() as s:
        s.write_main([rmme.assistant_record("m1", "claude-sonnet-5", rmme.usage(input_tokens=1))])
        subdir = s.session_dir / "subagents"
        subdir.mkdir(parents=True, exist_ok=True)
        (subdir / "agent-bad.meta.json").write_text(
            json.dumps({"toolUseId": "toolu_1"}), encoding="utf-8",  # missing agentType
        )
        log_path = s.dir / "samples.jsonl"
        record = ss.record_sample(
            log_path, agent_type="auditor", model="opus",
            session_transcript_path=str(s.session_path), tool_use_id="toolu_1",
        )
        check("record_sample: a matching-but-malformed meta file surfaces a warning, not a bare null",
              record["totals"] is None and len(record["warnings"]) == 1, record)


# ---------------------------------------------------------------- aggregate


def test_aggregate_buckets_by_agent_type_and_model() -> None:
    tmp = Path(tempfile.mkdtemp(prefix="shadow-sampler-agg-"))
    try:
        log_path = tmp / "samples.jsonl"
        rows = [
            {"agent_type": "auditor", "model": "opus", "totals": {"output_tokens": 100}},
            {"agent_type": "auditor", "model": "opus", "totals": {"output_tokens": 200}},
            {"agent_type": "auditor", "model": "sonnet", "totals": {"output_tokens": 50}},
            {"agent_type": "plan-critic", "model": "opus", "totals": {"output_tokens": 10}},
        ]
        with log_path.open("w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r) + "\n")
        result = ss.aggregate(log_path)
        check("aggregate: auditor/opus count=2, mean_output_tokens=150",
              result["auditor"]["opus"] == {"count": 2, "mean_output_tokens": 150.0}, result)
        check("aggregate: auditor/sonnet count=1, mean_output_tokens=50",
              result["auditor"]["sonnet"] == {"count": 1, "mean_output_tokens": 50.0}, result)
        check("aggregate: distinct agent_type stays in its own bucket",
              result["plan-critic"]["opus"] == {"count": 1, "mean_output_tokens": 10.0}, result)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_aggregate_excludes_unmatched_from_mean() -> None:
    # Regression case (staff-engineer lens): a totals=None sample (failed
    # lookup) must NOT be folded into count/mean as a zero-token observation.
    tmp = Path(tempfile.mkdtemp(prefix="shadow-sampler-agg-unmatched-"))
    try:
        log_path = tmp / "samples.jsonl"
        rows = [
            {"agent_type": "auditor", "model": "opus", "totals": {"output_tokens": 300}},
            {"agent_type": "auditor", "model": "opus", "totals": None},
        ]
        with log_path.open("w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r) + "\n")
        result = ss.aggregate(log_path)
        check("aggregate: unmatched sample excluded from count/mean (not counted as a zero-token sample)",
              result["auditor"]["opus"]["count"] == 1
              and result["auditor"]["opus"]["mean_output_tokens"] == 300.0, result)
        check("aggregate: unmatched sample reported separately, not silently dropped",
              result["auditor"]["opus"].get("unmatched") == 1, result)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_aggregate_all_unmatched_still_surfaces_bucket() -> None:
    tmp = Path(tempfile.mkdtemp(prefix="shadow-sampler-agg-allunmatched-"))
    try:
        log_path = tmp / "samples.jsonl"
        log_path.write_text(json.dumps({"agent_type": "auditor", "model": "sonnet", "totals": None}) + "\n",
                             encoding="utf-8")
        result = ss.aggregate(log_path)
        check("aggregate: a bucket with only unmatched samples still surfaces (count=0, unmatched=1)",
              result["auditor"]["sonnet"] == {"count": 0, "mean_output_tokens": 0, "unmatched": 1}, result)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_aggregate_missing_log_returns_empty() -> None:
    missing = Path(tempfile.gettempdir()) / "shadow-sampler-does-not-exist.jsonl"
    check("aggregate: missing log file returns {}, no crash", ss.aggregate(missing) == {})


def test_aggregate_malformed_line_skipped() -> None:
    tmp = Path(tempfile.mkdtemp(prefix="shadow-sampler-agg-bad-"))
    try:
        log_path = tmp / "samples.jsonl"
        log_path.write_text(
            "{not json\n" + json.dumps({"agent_type": "auditor", "model": "opus", "totals": {"output_tokens": 5}}) + "\n",
            encoding="utf-8",
        )
        result = ss.aggregate(log_path)
        check("aggregate: malformed line skipped, well-formed line still counted",
              result["auditor"]["opus"]["count"] == 1, result)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------- --dry-run


def test_dry_run_cli_no_live_call() -> None:
    proc = subprocess.run(
        [sys.executable, str(HERE / "shadow_sampler.py"), "--dry-run"],
        capture_output=True, text=True, check=False,
    )
    check("--dry-run: exits 0", proc.returncode == 0, proc.stderr)
    record = json.loads(proc.stdout)
    check("--dry-run: record has the sample shape",
          set(record) == {"agent_type", "model", "tool_use_id", "totals", "observed_models", "warnings"}, record)
    check("--dry-run: totals attributed via the synthetic sidecar transcript",
          record["totals"] == {"input_tokens": 10, "output_tokens": 20,
                                "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0}, record)


def test_aggregate_cli_flag() -> None:
    tmp = Path(tempfile.mkdtemp(prefix="shadow-sampler-agg-cli-"))
    try:
        log_path = tmp / "samples.jsonl"
        log_path.write_text(
            json.dumps({"agent_type": "auditor", "model": "opus", "totals": {"output_tokens": 42}}) + "\n",
            encoding="utf-8",
        )
        proc = subprocess.run(
            [sys.executable, str(HERE / "shadow_sampler.py"), "--aggregate", str(log_path)],
            capture_output=True, text=True, check=False,
        )
        check("--aggregate: exits 0", proc.returncode == 0, proc.stderr)
        result = json.loads(proc.stdout)
        check("--aggregate: prints the same shape aggregate() returns",
              result["auditor"]["opus"] == {"count": 1, "mean_output_tokens": 42.0}, result)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_no_network_imports() -> None:
    src = (HERE / "shadow_sampler.py").read_text(encoding="utf-8")
    forbidden = ("urllib", "requests", "httpx", "socket", "http.client")
    hits = [name for name in forbidden if name in src]
    check("shadow_sampler.py imports no networking module (no live/API call possible)",
          hits == [], hits)


# ---------------------------------------------------------------- structural guarantees


def test_not_referenced_by_shipped_plugin() -> None:
    proc = subprocess.run(
        ["git", "grep", "-l", "shadow_sampler"],
        cwd=str(REPO_ROOT), capture_output=True, text=True, check=False,
    )
    hits = [line for line in proc.stdout.splitlines() if line.startswith("plugins/flow/")]
    check("shadow_sampler is not referenced anywhere under plugins/flow/ (opt-in only, never shipped dispatch)",
          hits == [], hits)


def test_log_path_covered_by_existing_gitignore() -> None:
    candidate = REPO_ROOT / "tools" / "model-measure" / "samples" / "shadow.jsonl"
    proc = subprocess.run(
        ["git", "check-ignore", "-q", str(candidate)],
        cwd=str(REPO_ROOT), check=False,
    )
    check("a sample log path under tools/model-measure/ is already gitignored (no new ignore rule needed)",
          proc.returncode == 0, f"git check-ignore exit code {proc.returncode}")


TESTS = [
    test_recommend_model_below_threshold_is_sonnet,
    test_recommend_model_above_threshold_is_opus,
    test_recommend_model_default_rate_favors_opus_statistically,
    test_record_sample_reuses_sidecar_attribution,
    test_record_sample_unknown_tool_use_id_totals_none,
    test_record_sample_carries_lookup_warnings,
    test_aggregate_buckets_by_agent_type_and_model,
    test_aggregate_excludes_unmatched_from_mean,
    test_aggregate_all_unmatched_still_surfaces_bucket,
    test_aggregate_missing_log_returns_empty,
    test_aggregate_malformed_line_skipped,
    test_dry_run_cli_no_live_call,
    test_aggregate_cli_flag,
    test_no_network_imports,
    test_not_referenced_by_shipped_plugin,
    test_log_path_covered_by_existing_gitignore,
]


def main() -> int:
    for test in TESTS:
        print(f"-- {test.__name__}")
        test()
    print()
    if rmme._failures:
        print(f"FAILED: {len(rmme._failures)} eval(s): {', '.join(rmme._failures)}")
        return 1
    print(f"All {len(TESTS)} shadow_sampler evals passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
