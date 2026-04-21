#!/usr/bin/env python3
"""Eval harness for the assumption-auditor.

Reads evals/ground_truth.yaml, invokes the auditor against each fixture,
checks each `required` element with substring/regex matching, reports
pass/fail. Imperfect matching is fine for v1 — the point is regression
detection across prompt edits.

Auditor invocation is left as a pluggable step (`run_auditor`) so the
harness can be wired up to a local Claude Code CLI, the Anthropic SDK, or
a recorded-output cache as the project matures. The default
implementation reads recorded auditor outputs from
`fixtures/<case_id>.expected.txt` so the harness can run offline as a
spec-conformance check.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path


HERE = Path(__file__).parent


# ----------------------------------------------------------------- yaml lite

def _parse_scalar(s: str):
    s = s.strip()
    if s.startswith('"') and s.endswith('"'):
        return s[1:-1]
    if s.startswith("'") and s.endswith("'"):
        return s[1:-1]
    if s in ("true", "True"):
        return True
    if s in ("false", "False"):
        return False
    if s in ("null", "None", "~", ""):
        return None
    if s.startswith("[") and s.endswith("]"):
        inner = s[1:-1].strip()
        if not inner:
            return []
        return [_parse_scalar(x) for x in _split_top(inner, ",")]
    try:
        return int(s)
    except ValueError:
        pass
    try:
        return float(s)
    except ValueError:
        pass
    return s


def _split_top(s: str, sep: str) -> list[str]:
    out, buf, depth = [], [], 0
    for ch in s:
        if ch in "[{(":
            depth += 1
        elif ch in "]})":
            depth -= 1
        if ch == sep and depth == 0:
            out.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    if buf:
        out.append("".join(buf))
    return out


def load_ground_truth(path: Path) -> list[dict]:
    """Tiny indent-aware YAML reader sufficient for ground_truth.yaml's shape.

    Supports: top-level list of dicts, nested `required:` list whose items are
    inline `key: value` mappings, and inline JSON-style lists for values.
    """
    cases: list[dict] = []
    cur: dict | None = None
    cur_required: list | None = None
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        stripped = line.lstrip()
        indent = len(line) - len(stripped)
        if indent == 0 and stripped.startswith("- "):
            if cur is not None:
                cases.append(cur)
            cur = {}
            cur_required = None
            kv = stripped[2:]
            if ":" in kv:
                k, _, v = kv.partition(":")
                cur[k.strip()] = _parse_scalar(v)
            continue
        if cur is None:
            continue
        if stripped.endswith(":") and indent == 2:
            key = stripped[:-1].strip()
            if key == "required":
                cur_required = []
                cur[key] = cur_required
            else:
                cur[key] = None
            continue
        if indent == 2 and ":" in stripped and not stripped.startswith("- "):
            k, _, v = stripped.partition(":")
            cur[k.strip()] = _parse_scalar(v)
            continue
        if cur_required is not None and stripped.startswith("- "):
            kv = stripped[2:]
            k, _, v = kv.partition(":")
            cur_required.append({k.strip(): _parse_scalar(v)})
            continue
    if cur is not None:
        cases.append(cur)
    return cases


# ----------------------------------------------------------------- checks

@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str = ""


def check_required(elem: dict, output: str) -> CheckResult:
    if not elem:
        return CheckResult("empty", True)
    key, value = next(iter(elem.items()))
    text = output.lower()
    if key == "category":
        target = str(value)
        ok = target.lower() in text
        return CheckResult(f"category={target}", ok)
    if key == "claim_contains":
        target = str(value)
        ok = target.lower() in text
        return CheckResult(f"claim_contains={target!r}", ok)
    if key == "gap_mentions":
        terms = value if isinstance(value, list) else [value]
        ok = any(str(t).lower() in text for t in terms)
        return CheckResult(f"gap_mentions any of {terms}", ok)
    if key == "falsifier_present":
        ok = bool(value) == ("falsifier:" in text)
        return CheckResult("falsifier_present", ok)
    if key == "verification_checks_include_behavioral":
        behavioral = ("test", "render", "reproduce", "console", "fetch", "page")
        ok = "verification checks" in text and any(b in text for b in behavioral)
        return CheckResult("verification_checks_include_behavioral", ok)
    if key == "source_identified":
        ok = "source of premise:" in text
        return CheckResult("source_identified", ok)
    return CheckResult(f"unknown={key}", False, "no rule wired up for this required key")


# ----------------------------------------------------------------- auditor i/o


def run_auditor(case: dict) -> str:
    """Default offline runner: read pre-recorded output for the fixture.

    Wire this up to an actual auditor invocation (Anthropic SDK, Claude Code
    CLI, etc.) when ready. Until then, this lets the harness exercise its
    matching logic against expected outputs the maintainer has hand-written.
    """
    fixture = case.get("fixture", "")
    if not fixture:
        return ""
    expected = HERE / fixture
    expected = expected.with_suffix(".expected.txt")
    if expected.exists():
        return expected.read_text(encoding="utf-8")
    return ""


# ----------------------------------------------------------------- main

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--ground-truth",
        default=str(HERE / "ground_truth.yaml"),
        help="path to ground truth YAML",
    )
    ap.add_argument("--case", help="run only this case_id")
    ap.add_argument("--json", action="store_true", help="emit machine-readable summary")
    args = ap.parse_args()

    cases = load_ground_truth(Path(args.ground_truth))
    if args.case:
        cases = [c for c in cases if c.get("case_id") == args.case]

    summary = []
    pass_total = fail_total = skip_total = 0
    for case in cases:
        output = run_auditor(case)
        if not output:
            skip_total += 1
            summary.append({"case_id": case.get("case_id"), "status": "skipped"})
            if not args.json:
                print(f"SKIP  {case.get('case_id')}  (no recorded output)")
            continue
        results = [check_required(elem, output) for elem in case.get("required") or []]
        all_pass = all(r.passed for r in results)
        if all_pass:
            pass_total += 1
            if not args.json:
                print(f"PASS  {case.get('case_id')}")
        else:
            fail_total += 1
            if not args.json:
                print(f"FAIL  {case.get('case_id')}")
                for r in results:
                    if not r.passed:
                        print(f"        - {r.name}{(': ' + r.detail) if r.detail else ''}")
        summary.append({
            "case_id": case.get("case_id"),
            "status": "pass" if all_pass else "fail",
            "checks": [{"name": r.name, "passed": r.passed} for r in results],
        })

    if args.json:
        print(json.dumps({
            "totals": {"pass": pass_total, "fail": fail_total, "skipped": skip_total},
            "cases": summary,
        }, indent=2))
    else:
        print(f"\n{pass_total} passed, {fail_total} failed, {skip_total} skipped")
    return 0 if fail_total == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
