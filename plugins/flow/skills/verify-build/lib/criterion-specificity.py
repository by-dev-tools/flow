#!/usr/bin/env python3
"""
Deterministic criterion-specificity heuristic for /flow:verify-build.

`/flow:audit-coverage` closes UNDER-declaration (a behavior change with no
criterion at all). It leaves the sibling OVER-BROAD-declaration seam open: an
agent can dodge coverage by declaring a criterion so vague it plausibly maps
to the changed hunk — coverage stays silent, and /flow:verify-build then
judges the vague criterion PASS against equally vague narration. The two
compose to bless a change whose only declared bar is untestably vague (the
FB-0047/0048 self-attestation escape, one level up: you cannot show a
criterion green without a PASS, but you CAN author one so empty that PASS is
meaningless).

This is deliberately NOT an LLM judgment. A downstream bounded-retry loop
needs a mechanical signal to retry against — reward-hackable judge prose
would defeat the loop's whole purpose.

Distinct from `skills/critique-plan/lib/walk-pin-lint.py` (FB-0068, SHIPPED):
that lint asks, at PLAN-CRITIQUE time over the WHOLE plan document, "does
this checkbox name a verification METHOD (a test id, or a pin-marker +
artifact noun)?" This script asks, at EXTRACTION time over the ACTIVE block
only (the same scope `extract-criteria.py` already uses), "does the
criterion's own TEXT name an observable predicate — output, state, value, or
error path — that a verifier could check?" They are complementary, not
overlapping: "Rate limiting works correctly -> verify: manual QA" is PINNED
(walk-pin-lint passes) but still VACUOUS (this script fires); "Retries back
off exponentially, capped at 5 attempts" is UNPINNED (walk-pin-lint flags it)
but NOT vacuous (this script does not fire).

Input: the JSON `extract-criteria.py` already emits (`{"criteria": [...]}"`),
via stdin or a file-path argument — this literally IS "the extract-criteria.py
consumer path," so no plan-parsing logic is duplicated here.

Output: deterministic JSON to stdout:
    {
      "total": <int>,
      "vacuous": [{"criterion": "...", "reason": "..."}, ...],
      "specific_count": <int>
    }

Exit codes:
    0  parsed successfully (a lint verdict, not pass/fail — "0 vacuous" is a
       valid, clean result, mirroring walk-pin-lint.py's exit-0-always
       contract for lint verdicts).
    1  crash-grade input error (malformed JSON, missing "criteria" key of the
       wrong type).
    2  malformed CLI usage (too many args).

Precision/recall posture: conservative toward precision. A missed vacuous
criterion is an accepted residual; a false positive on a genuinely specific
criterion is what gets a gate routed around. See the two-part heuristic below.

Stdlib only. Python 3.7+.
"""

from __future__ import annotations

import json
import re
import sys

# Trailing-clause match: a generic success-predicate verb, optionally followed
# by a generic adverb, anchored to the END of the (stripped) criterion. This
# mirrors the roadmap's own named vocabulary ("works"/"correctly"/"as
# expected") with a small, bounded generalization (functions/behaves/performs;
# properly/as intended) -- narrow enough that CONCRETE_SIGNAL_RE, not
# vocabulary breadth, is what actually protects precision.
_VACUOUS_PREDICATE_RE = re.compile(
    r"\b(works|functions|behaves|performs)\b"
    r"(\s+(correctly|properly|as\s+expected|as\s+intended))?"
    r"\s*\.?\s*$",
    re.IGNORECASE,
)

# A second small pattern for the "is/remains/stays correct" phrasing family
# ("Login is correct"), same end-anchoring.
_CORRECTNESS_ONLY_RE = re.compile(
    r"\b(is|remains|stays)\s+(correct|accurate|valid|fine|ok|okay)\s*\.?\s*$",
    re.IGNORECASE,
)

# Escape hatch: ANY of these, matched ANYWHERE in the criterion, suppresses
# the flag -- a quoted/backticked literal, a digit, a pin-marker arrow, or a
# named-observable verb/noun. Any one of these signals a concrete, checkable
# predicate even when the sentence also happens to end in a generic phrase
# (e.g. "Returns a session token and works correctly").
_CONCRETE_SIGNAL_RE = re.compile(
    r"`[^`]+`"
    r"|\"[^\"]+\"|'[^']+'"
    r"|\d"
    r"|→|->"
    r"|\b(returns?|throws?|raises?|logs?|displays?|renders?|shows?|equals?"
    r"|matches?|contains?|rejects?|redirects?|status\s*code|exception|error"
    r"|null|true|false)\b",
    re.IGNORECASE,
)


def is_vacuous(criterion: str) -> tuple[bool, str]:
    """Return (flagged, reason). Reason is empty when not flagged."""
    text = (criterion or "").strip()
    if not text:
        return False, ""
    if _CONCRETE_SIGNAL_RE.search(text):
        return False, ""
    if _VACUOUS_PREDICATE_RE.search(text) or _CORRECTNESS_ONLY_RE.search(text):
        return True, (
            "no observable predicate -- no named output, state, value, or "
            "error path, just a generic success claim"
        )
    return False, ""


def lint(criteria: list) -> dict:
    vacuous = []
    for c in criteria:
        text = c if isinstance(c, str) else str(c)
        flagged, reason = is_vacuous(text)
        if flagged:
            vacuous.append({"criterion": text, "reason": reason})
    return {
        "total": len(criteria),
        "vacuous": vacuous,
        "specific_count": len(criteria) - len(vacuous),
    }


def _read(path: str | None) -> str:
    if path is None or path == "-":
        return sys.stdin.read()
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def main(argv: list[str]) -> int:
    if len(argv) > 2:
        sys.stderr.write(
            f"usage: {argv[0]} [<criteria-json-path>]   "
            "(or extract-criteria.py's JSON on stdin)\n"
        )
        return 2

    path = argv[1] if len(argv) == 2 else None
    try:
        raw = _read(path)
    except OSError as e:
        sys.stderr.write(f"criterion-specificity: ⚠️ cannot read input: {e}\n")
        return 1

    try:
        data = json.loads(raw) if raw.strip() else {"criteria": []}
    except ValueError as e:
        sys.stderr.write(f"criterion-specificity: ⚠️ malformed JSON input: {e}\n")
        return 1

    if not isinstance(data, dict) or not isinstance(data.get("criteria", []), list):
        sys.stderr.write(
            "criterion-specificity: ⚠️ expected {\"criteria\": [...]} "
            "(extract-criteria.py's own output shape)\n"
        )
        return 1

    result = lint(data.get("criteria", []))
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
