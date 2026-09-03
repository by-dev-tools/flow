#!/usr/bin/env python3
"""Randomized/shadow sampler: recommend + log real-invocation samples
(roadmap item M, Step 3, FB-0083).

Dev tooling, not a shipped plugin artifact -- see CLAUDE.md § 3 "Project-dev
infrastructure". Nothing in `plugins/flow/` imports or calls this file (see
run_shadow_sampler_evals.py's git-grep check); no shipped `/flow:*` skill
routes any real invocation through it.

WHAT THIS IS, PRECISELY: a recommendation + logging utility a developer may
*choose* to consult while doing real work that happens to spawn one of
flow's reviewer agent types (e.g. an orchestrator session spawning
`auditor`/`plan-critic` for its own sessions) -- occasionally recommending
Sonnet, at low weight, so real paired-ish samples accumulate over time
without doubling the cost of every invocation (single-assignment, per the
plan's own "not double-cost" note; contrast with ab_eval.py's Step 2, which
deliberately pays double per fixture for a precise paired comparison on a
small held-out set).

WHAT THIS IS NOT: an interception of any shipped flow-skill's subagent
dispatch, and not a routing mechanism. Opus stays the overwhelming default
by construction (recommend_model's default sonnet_rate is 10%); this file
never changes what model a shipped `/flow:*` skill actually spawns.

Usage:
    python3 shadow_sampler.py --dry-run
    python3 shadow_sampler.py --aggregate PATH/TO/samples.jsonl
"""

from __future__ import annotations

import argparse
import json
import random
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import model_measure as mm  # noqa: E402


def recommend_model(sonnet_rate: float = 0.1, rng: random.Random | None = None) -> str:
    """Weighted random pick; Opus is the overwhelming default.

    `rng` is injectable (anything with a `.random() -> float` method) for
    deterministic tests; real callers should pass nothing and get a fresh
    `random.Random()`.
    """
    rng = rng if rng is not None else random.Random()
    return "sonnet" if rng.random() < sonnet_rate else "opus"


def token_totals_for_invocation(session_path: Path, tool_use_id: str) -> tuple[dict | None, set, list[str]]:
    """Look up ONE subagent invocation's totals + models by tool_use_id.

    Uses model_measure's targeted single-invocation lookup rather than the
    full-session sidecar scan -- record_sample is called once per real
    invocation over a session's life, so scanning (and re-parsing) every
    other already-logged transcript on each call would turn linear
    per-session logging into quadratic work. Warnings from the lookup (e.g. a
    matching-but-malformed meta file) are returned, not discarded -- a failed
    lookup should leave a diagnostic trail, not a bare `totals: null`.
    """
    session_dir = mm.session_dir_for(Path(session_path))
    inv, warnings = mm.find_sidecar_invocation(session_dir, tool_use_id)
    if inv is None:
        return None, set(), warnings
    return inv["totals"], inv["models"], warnings


def record_sample(
    log_path: Path, *, agent_type: str, model: str, session_transcript_path: str, tool_use_id: str,
) -> dict:
    """Append one JSONL sample line; return the record written."""
    totals, observed_models, warnings = token_totals_for_invocation(Path(session_transcript_path), tool_use_id)
    record = {
        "agent_type": agent_type,
        "model": model,
        "tool_use_id": tool_use_id,
        "totals": totals,
        "observed_models": sorted(observed_models),
        "warnings": warnings,
    }
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")
    return record


def load_samples(log_path: Path) -> list[dict]:
    if not log_path.is_file():
        return []
    samples = []
    for line in log_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            samples.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return samples


def aggregate(log_path: Path) -> dict:
    """Per (agent_type, model): sample count + mean output tokens.

    A sample whose `totals` is None (the lookup failed to find the
    invocation -- see record_sample) is excluded from count/mean rather than
    folded in as a zero-token observation, which would silently corrupt the
    exact number this function exists to produce. Excluded samples are
    reported separately via `unmatched`, never dropped without a trace.
    """
    buckets: dict = {}
    unmatched: dict = {}
    for s in load_samples(log_path):
        key = (s.get("agent_type"), s.get("model"))
        totals = s.get("totals")
        if totals is None:
            unmatched[key] = unmatched.get(key, 0) + 1
            continue
        bucket = buckets.setdefault(key, {"count": 0, "total_output_tokens": 0})
        bucket["count"] += 1
        bucket["total_output_tokens"] += totals.get("output_tokens", 0) or 0

    result: dict = {}
    for (agent_type, model), bucket in buckets.items():
        count = bucket["count"]
        result.setdefault(agent_type, {})[model] = {
            "count": count,
            "mean_output_tokens": (bucket["total_output_tokens"] / count) if count else 0,
        }
    for (agent_type, model), n in unmatched.items():
        entry = result.setdefault(agent_type, {}).setdefault(model, {"count": 0, "mean_output_tokens": 0})
        entry["unmatched"] = n
    return result


def _dry_run() -> dict:
    """Fabricate one end-to-end sample against a synthetic transcript with a
    fixed rng seed and a scratch log path -- proves the log-line shape and
    that Opus stays the default assignment, with zero live invocation and
    zero network/API call."""
    tmp = Path(tempfile.mkdtemp(prefix="shadow-sampler-dry-run-"))
    try:
        session_path = tmp / "session.jsonl"
        session_path.write_text("", encoding="utf-8")
        subdir = tmp / "session" / "subagents"
        subdir.mkdir(parents=True)
        (subdir / "agent-dry.jsonl").write_text(
            json.dumps({
                "type": "assistant",
                "isSidechain": False,
                "message": {
                    "role": "assistant", "id": "dry-1", "model": "claude-sonnet-5",
                    "usage": {
                        "input_tokens": 10, "output_tokens": 20,
                        "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0,
                    },
                    "content": [{"type": "text", "text": "x"}],
                },
            }) + "\n",
            encoding="utf-8",
        )
        (subdir / "agent-dry.meta.json").write_text(
            json.dumps({"agentType": "auditor", "toolUseId": "toolu_dry", "spawnDepth": 1}),
            encoding="utf-8",
        )
        model = recommend_model(rng=random.Random(0))
        log_path = tmp / "samples.jsonl"
        return record_sample(
            log_path, agent_type="auditor", model=model,
            session_transcript_path=str(session_path), tool_use_id="toolu_dry",
        )
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--dry-run", action="store_true",
        help="fabricate one end-to-end sample against a synthetic transcript; no live invocation",
    )
    parser.add_argument(
        "--aggregate", metavar="LOG_PATH",
        help="print aggregate() over a real samples log -- the accumulated read this tool exists to serve",
    )
    args = parser.parse_args(argv)
    if args.dry_run:
        print(json.dumps(_dry_run(), indent=2))
        return 0
    if args.aggregate:
        print(json.dumps(aggregate(Path(args.aggregate)), indent=2))
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
