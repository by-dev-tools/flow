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

# Trailing-clause match, anchored to the END of the (stripped) criterion: either
# a generic success-predicate verb with an optional generic adverb ("works
# correctly"), or the "is/remains/stays correct" phrasing family ("Login is
# correct"). One alternation, one end-anchor, so the anchor logic (and any
# future change to it) lives in exactly one place. Mirrors the roadmap's own
# named vocabulary ("works"/"correctly"/"as expected") with a small, bounded
# generalization -- narrow enough that CONCRETE_SIGNAL_RE, not vocabulary
# breadth, is what actually protects precision.
_VACUOUS_PREDICATE_RE = re.compile(
    r"\b(?:"
    r"(?:works|functions|behaves|performs)(?:\s+(?:correctly|properly|as\s+expected|as\s+intended))?"
    r"|(?:is|remains|stays)\s+(?:correct|accurate|valid|fine|ok|okay)"
    r")\s*\.?\s*$",
    re.IGNORECASE,
)

# Escape hatch: ANY of these, matched ANYWHERE in the criterion's CLAIM portion
# (see _strip_pin_suffix below), suppresses the flag -- a quoted/backticked
# literal, a digit, or a named-observable verb/noun. Any one of these signals a
# concrete, checkable predicate even when the sentence also happens to end in a
# generic phrase (e.g. "Returns a session token and works correctly").
#
# Deliberately does NOT include the pin-marker arrow (-> / →). An earlier
# draft did, reasoning "an arrow points at a concrete artifact" -- but this
# repo's OWN Spec-walk convention (FB-0068, walk-pin-lint.py's PIN_MARKERS)
# appends a pin annotation AFTER the claim ("Rate limiting works correctly ->
# verify: manual QA"), so the arrow is a VERIFICATION-METHOD marker, not a
# claim-specificity signal -- and every pinned criterion in this repo, the
# dominant real-world population, would have silently defeated the checker.
# Caught by /flow:staff-review's staff-engineer lens against the checker's own
# documented counter-example. See _strip_pin_suffix for the actual fix: the pin
# suffix is removed before either regex runs, so the CLAIM alone is judged --
# consistent with the walk-pin-lint split (that script judges the method; this
# one judges the claim).
_CONCRETE_SIGNAL_RE = re.compile(
    r"`[^`]+`"
    r"|\"[^\"]+\"|'[^']+'"
    r"|\d"
    r"|\b(returns?|throws?|raises?|logs?|displays?|renders?|shows?|equals?"
    r"|matches?|contains?|rejects?|redirects?|status\s*code|exception|error"
    r"|null|true|false)\b",
    re.IGNORECASE,
)

# A pin-marker suffix, per walk-pin-lint.py's PIN_MARKERS vocabulary (not
# imported -- that script has no shared-library shape, unlike walk_extract.py;
# keep the two lists in sync by hand if either changes). Matched from the
# FIRST occurrence onward and stripped, so "<claim> -> verify: <method>"
# judges only "<claim>". Accepted residual: a marker word used mid-sentence
# ahead of more genuine claim text (rare; the observed convention places the
# marker at the very end) would over-strip -- same precision-over-recall
# posture as the rest of this heuristic.
_PIN_SUFFIX_RE = re.compile(
    r"\s*(?:→|->|\bpinned\s+by\b|\bverify:|\bverified\s+by\b)\s*.*$",
    re.IGNORECASE,
)


def _strip_pin_suffix(text: str) -> str:
    """Remove a trailing pin-marker annotation so the heuristic judges the
    CLAIM, not the verification method appended after it. Also strips the
    separator punctuation typically left dangling right before the marker
    ("...correct — verified by QA", "...expected, pinned by testFoo") --
    without this, the leftover comma/dash defeats the end-anchored predicate
    regex just as surely as the un-stripped suffix did."""
    claim = _PIN_SUFFIX_RE.sub("", text)
    return claim.strip(" \t,;:—–-")


def is_vacuous(criterion: str) -> tuple[bool, str]:
    """Return (flagged, reason). Reason is empty when not flagged."""
    text = (criterion or "").strip()
    if not text:
        return False, ""
    claim = _strip_pin_suffix(text)
    if not claim:
        # The whole criterion WAS a pin marker with no claim before it --
        # degenerate input; nothing to judge, so don't flag.
        return False, ""
    if _CONCRETE_SIGNAL_RE.search(claim):
        return False, ""
    m = _VACUOUS_PREDICATE_RE.search(claim)
    if m:
        return True, (
            f"no observable predicate -- matched generic phrase "
            f"{m.group(0).strip()!r}; name an output, state, value, or "
            f"error path instead"
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
