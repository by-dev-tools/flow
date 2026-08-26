#!/usr/bin/env python3
"""Eval harness for model_measure.py (roadmap item M, Step 1, FB-0089).

Dev tooling, not a shipped plugin eval -- runs in its own CI job (see
.github/workflows/ci.yml), not folded into the plugins/flow/evals/ FB-0074
harness/CI join-check, which is scoped to shipped-plugin regression tests.

Pins the behavior established live in this session (dev-docs/plan.md "PR --
Model-measurement harness, Step 1"): the sidecar subagents/*.jsonl +
.meta.json format, the message.id usage-repeat dedup requirement, the
legacy inline isSidechain fallback (including its honest "unattributed"
degradation on ambiguous concurrent spawns), and graceful handling of
missing/empty/malformed transcripts.

Stdlib only. Run:
    python3 tools/model-measure/run_model_measure_evals.py
"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import model_measure as mm  # noqa: E402

_failures: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    if ok:
        print(f"  PASS  {name}")
    else:
        print(f"  FAIL  {name}\n        {detail}")
        _failures.append(name)


# ---------------------------------------------------------------- fixture helpers


def usage(input_tokens=0, output_tokens=0, cache_creation_input_tokens=0, cache_read_input_tokens=0) -> dict:
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cache_creation_input_tokens": cache_creation_input_tokens,
        "cache_read_input_tokens": cache_read_input_tokens,
    }


def assistant_record(mid, model, usage_dict, sidechain=False) -> dict:
    return {
        "type": "assistant",
        "isSidechain": sidechain,
        "message": {
            "role": "assistant",
            "id": mid,
            "model": model,
            "usage": usage_dict,
            "content": [{"type": "text", "text": "x"}],
        },
    }


def tool_use_record(tool_id, name, subagent_type) -> dict:
    return {
        "type": "assistant",
        "isSidechain": False,
        "message": {
            "role": "assistant",
            "content": [{
                "type": "tool_use", "id": tool_id, "name": name,
                "input": {"subagent_type": subagent_type},
            }],
        },
    }


def tool_result_record(tool_id) -> dict:
    return {
        "type": "user",
        "isSidechain": False,
        "message": {
            "role": "user",
            "content": [{"type": "tool_result", "tool_use_id": tool_id, "content": "ok"}],
        },
    }


def write_jsonl(path: Path, records: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")


class TempSession:
    """A scratch <tmp>/session.jsonl + <tmp>/session/subagents/ layout."""

    def __init__(self):
        self.dir = Path(tempfile.mkdtemp(prefix="model-measure-eval-"))
        self.session_path = self.dir / "session.jsonl"
        self.session_dir = self.dir / "session"

    def write_main(self, records: list[dict]) -> None:
        write_jsonl(self.session_path, records)

    def write_subagent(self, agent_id: str, agent_type: str, tool_use_id: str,
                        records: list[dict], spawn_depth: int = 1,
                        write_meta: bool = True, write_transcript: bool = True) -> None:
        subdir = self.session_dir / "subagents"
        subdir.mkdir(parents=True, exist_ok=True)
        if write_transcript:
            write_jsonl(subdir / f"agent-{agent_id}.jsonl", records)
        if write_meta:
            meta = {"agentType": agent_type, "toolUseId": tool_use_id, "spawnDepth": spawn_depth}
            (subdir / f"agent-{agent_id}.meta.json").write_text(json.dumps(meta), encoding="utf-8")

    def cleanup(self) -> None:
        shutil.rmtree(self.dir, ignore_errors=True)

    def __enter__(self) -> "TempSession":
        return self

    def __exit__(self, *exc) -> None:
        self.cleanup()


# ---------------------------------------------------------------- sidecar-format cases


def test_sidecar_single_invocation() -> None:
    with TempSession() as s:
        s.write_main([assistant_record("m1", "claude-sonnet-5", usage(input_tokens=5, output_tokens=7))])
        s.write_subagent("a1", "Explore", "toolu_1", [
            assistant_record("sm1", "claude-sonnet-5", usage(input_tokens=10, output_tokens=20)),
        ])
        records = mm.load_session(s.session_path)
        data = mm.build_report(s.session_path, records)
        check("sidecar: format detected", data["format"] == "sidecar", data["format"])
        check("sidecar: single invocation totals exact",
              data["subagents"].get("Explore", {}).get("totals") == usage(input_tokens=10, output_tokens=20),
              data["subagents"].get("Explore"))
        check("sidecar: invocation count is 1",
              data["subagents"].get("Explore", {}).get("invocations") == 1)


def test_main_bucket_isolated_from_subagent() -> None:
    with TempSession() as s:
        s.write_main([assistant_record("m1", "claude-sonnet-5", usage(input_tokens=100, output_tokens=200))])
        s.write_subagent("a1", "Explore", "toolu_1", [
            assistant_record("sm1", "claude-sonnet-5", usage(input_tokens=10, output_tokens=20)),
        ])
        records = mm.load_session(s.session_path)
        data = mm.build_report(s.session_path, records)
        check("main bucket: matches known main-only total exactly",
              data["main"]["totals"] == usage(input_tokens=100, output_tokens=200),
              data["main"]["totals"])
        check("main bucket: disjoint from subagent total (no double count)",
              data["main"]["totals"] != data["subagents"]["Explore"]["totals"])


def test_multiple_invocations_aggregate_same_type_distinct_types() -> None:
    with TempSession() as s:
        s.write_main([assistant_record("m1", "claude-sonnet-5", usage(input_tokens=1))])
        s.write_subagent("a1", "Explore", "toolu_1", [
            assistant_record("sm1", "claude-sonnet-5", usage(input_tokens=10, output_tokens=10)),
        ])
        s.write_subagent("a2", "Explore", "toolu_2", [
            assistant_record("sm2", "claude-sonnet-5", usage(input_tokens=5, output_tokens=5)),
        ])
        s.write_subagent("a3", "flow:auditor", "toolu_3", [
            assistant_record("sm3", "claude-opus-5", usage(input_tokens=1, output_tokens=1)),
        ])
        records = mm.load_session(s.session_path)
        data = mm.build_report(s.session_path, records)
        explore = data["subagents"]["Explore"]
        check("aggregate: 2 invocations of same type summed",
              explore["invocations"] == 2 and explore["totals"] == usage(input_tokens=15, output_tokens=15),
              explore)
        check("aggregate: distinct type stays separate",
              data["subagents"]["flow:auditor"]["totals"] == usage(input_tokens=1, output_tokens=1))
        check("aggregate: model set is per-type, not merged across types",
              data["subagents"]["flow:auditor"]["models"] == {"claude-opus-5"}
              and explore["models"] == {"claude-sonnet-5"})


def test_nested_subagent_attributes_to_own_type() -> None:
    with TempSession() as s:
        s.write_main([assistant_record("m1", "claude-sonnet-5", usage(input_tokens=1))])
        s.write_subagent("a1", "planner", "toolu_1", [
            assistant_record("sm1", "claude-sonnet-5", usage(input_tokens=10)),
        ], spawn_depth=1)
        s.write_subagent("a2", "Explore", "toolu_2", [
            assistant_record("sm2", "claude-sonnet-5", usage(input_tokens=3)),
        ], spawn_depth=2)
        records = mm.load_session(s.session_path)
        data = mm.build_report(s.session_path, records)
        check("nested: depth-2 subagent keeps its own type bucket, not folded into parent",
              data["subagents"]["Explore"]["totals"] == usage(input_tokens=3)
              and data["subagents"]["planner"]["totals"] == usage(input_tokens=10))


def test_message_id_repeat_dedup() -> None:
    # Reproduces the exact shape observed live: one message.id appearing 4x
    # with an identical usage snapshot on every repeat (thinking + tool_use
    # content blocks emitted as separate records sharing one message).
    with TempSession() as s:
        repeated = usage(input_tokens=2, output_tokens=180, cache_creation_input_tokens=24440,
                          cache_read_input_tokens=24424)
        s.write_main([assistant_record("shared-id", "claude-sonnet-5", repeated) for _ in range(4)])
        records = mm.load_session(s.session_path)
        data = mm.build_report(s.session_path, records)
        check("dedup: 4 records sharing one message.id count once, not 4x",
              data["main"]["totals"] == repeated,
              f"expected {repeated}, got {data['main']['totals']} (naive summation would be 4x)")


def test_malformed_meta_json_warns() -> None:
    with TempSession() as s:
        s.write_main([assistant_record("m1", "claude-sonnet-5", usage(input_tokens=1))])
        subdir = s.session_dir / "subagents"
        subdir.mkdir(parents=True, exist_ok=True)
        (subdir / "agent-bad.meta.json").write_text("{not json", encoding="utf-8")
        records = mm.load_session(s.session_path)
        data = mm.build_report(s.session_path, records)
        check("malformed meta.json: counted in warnings, not silently dropped",
              len(data["warnings"]) == 1, data["warnings"])
        check("malformed meta.json: format still reports as sidecar (warnings alone trigger it)",
              data["format"] == "sidecar")


def test_meta_json_missing_transcript_warns() -> None:
    with TempSession() as s:
        s.write_main([assistant_record("m1", "claude-sonnet-5", usage(input_tokens=1))])
        s.write_subagent("a1", "Explore", "toolu_1", [], write_transcript=False)
        records = mm.load_session(s.session_path)
        data = mm.build_report(s.session_path, records)
        check("meta.json with missing transcript: counted in warnings",
              len(data["warnings"]) == 1, data["warnings"])


# ---------------------------------------------------------------- legacy inline-format cases


def test_inline_single_span_attributes() -> None:
    with TempSession() as s:
        records = [
            tool_use_record("toolu_1", "Task", "Explore"),
            assistant_record("sc1", "claude-sonnet-5", usage(input_tokens=10), sidechain=True),
            tool_result_record("toolu_1"),
            assistant_record("m1", "claude-sonnet-5", usage(input_tokens=1)),
        ]
        s.write_main(records)
        loaded = mm.load_session(s.session_path)
        data = mm.build_report(s.session_path, loaded)
        check("inline: format detected", data["format"] == "inline", data["format"])
        check("inline: single bracketed span attributes to its subagent_type",
              data["subagents"].get("Explore", {}).get("totals") == usage(input_tokens=10),
              data["subagents"].get("Explore"))
        check("inline: main bucket excludes the sidechain span",
              data["main"]["totals"] == usage(input_tokens=1), data["main"]["totals"])


def test_inline_two_sequential_spans() -> None:
    with TempSession() as s:
        records = [
            tool_use_record("toolu_1", "Task", "Explore"),
            assistant_record("sc1", "claude-sonnet-5", usage(input_tokens=10), sidechain=True),
            tool_result_record("toolu_1"),
            tool_use_record("toolu_2", "Task", "Explore"),
            assistant_record("sc2", "claude-sonnet-5", usage(input_tokens=5), sidechain=True),
            tool_result_record("toolu_2"),
        ]
        s.write_main(records)
        loaded = mm.load_session(s.session_path)
        data = mm.build_report(s.session_path, loaded)
        check("inline: two sequential spans of the same type aggregate",
              data["subagents"]["Explore"]["invocations"] == 2
              and data["subagents"]["Explore"]["totals"] == usage(input_tokens=15),
              data["subagents"]["Explore"])


def test_inline_ambiguous_overlap_is_unattributed() -> None:
    with TempSession() as s:
        records = [
            tool_use_record("toolu_1", "Task", "Explore"),
            tool_use_record("toolu_2", "Task", "flow:auditor"),
            assistant_record("sc1", "claude-sonnet-5", usage(input_tokens=10), sidechain=True),
            tool_result_record("toolu_1"),
            tool_result_record("toolu_2"),
        ]
        s.write_main(records)
        loaded = mm.load_session(s.session_path)
        data = mm.build_report(s.session_path, loaded)
        check("inline: two concurrently open spawns cannot be disambiguated -> unattributed",
              data["unattributed"] == usage(input_tokens=10), data["unattributed"])
        check("inline: ambiguous span is NOT guessed into either candidate subagent bucket",
              not data["subagents"], data["subagents"])


# ---------------------------------------------------------------- graceful degradation


def test_missing_transcript_no_crash() -> None:
    missing = Path(tempfile.gettempdir()) / "model-measure-does-not-exist.jsonl"
    session_path = mm.find_session_file(str(missing))
    check("missing transcript: find_session_file returns None, not an exception",
          session_path is None)
    rc = mm.main(["--session-file", str(missing)])
    check("missing transcript: main() exits 0", rc == 0)


def test_empty_transcript_no_crash() -> None:
    with TempSession() as s:
        s.session_path.write_text("", encoding="utf-8")
        rc = mm.main(["--session-file", str(s.session_path)])
        check("empty transcript: main() exits 0, no crash", rc == 0)


def test_malformed_jsonl_lines_no_crash() -> None:
    with TempSession() as s:
        with s.session_path.open("w", encoding="utf-8") as f:
            f.write("{not json at all\n")
            f.write(json.dumps(assistant_record("m1", "claude-sonnet-5", usage(input_tokens=1))) + "\n")
        records = mm.load_session(s.session_path)
        check("malformed JSONL: bad line skipped, good line survives", len(records) == 1)
        data = mm.build_report(s.session_path, records)
        check("malformed JSONL: report still builds", data["main"]["totals"] == usage(input_tokens=1))


def test_non_string_model_field_does_not_crash() -> None:
    # Regression test for the isinstance() guard in sum_usage -- a transcript's
    # message.model is normally a string, but the field comes from an untrusted
    # local file, and a list/dict there would raise TypeError on set.add() with
    # only a truthiness check (both are truthy). The malformed value must be
    # excluded from the models set, not crash the report.
    with TempSession() as s:
        s.write_main([assistant_record("m1", ["not", "a", "string"], usage(input_tokens=1))])
        records = mm.load_session(s.session_path)
        data = mm.build_report(s.session_path, records)
        check("non-string model field: report builds without raising, value excluded from models set",
              data["main"]["models"] == set() and data["main"]["totals"] == usage(input_tokens=1),
              data["main"])


TESTS = [
    test_sidecar_single_invocation,
    test_main_bucket_isolated_from_subagent,
    test_multiple_invocations_aggregate_same_type_distinct_types,
    test_nested_subagent_attributes_to_own_type,
    test_message_id_repeat_dedup,
    test_malformed_meta_json_warns,
    test_meta_json_missing_transcript_warns,
    test_inline_single_span_attributes,
    test_inline_two_sequential_spans,
    test_inline_ambiguous_overlap_is_unattributed,
    test_missing_transcript_no_crash,
    test_empty_transcript_no_crash,
    test_malformed_jsonl_lines_no_crash,
    test_non_string_model_field_does_not_crash,
]


def main() -> int:
    for test in TESTS:
        print(f"-- {test.__name__}")
        test()
    print()
    if _failures:
        print(f"FAILED: {len(_failures)} eval(s): {', '.join(_failures)}")
        return 1
    print(f"All {len(TESTS)} model_measure evals passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
