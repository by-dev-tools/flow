#!/usr/bin/env python3
"""Deterministic draft-manifest triage engine (FB-0074).

`/flow:ship` accumulates a draft manifest from 8 producer sites, and its draft
decision was unconditional: manifest non-empty => `gh pr create --draft`. Three
unlike populations therefore reached the human identically -- items the agent
could resolve itself, genuine decisions written in engineer shorthand, and items
blocked on an out-of-session human action. Only the third deserves a draft.

This engine is the mechanical half of the fix. It parses the normalized manifest
line, classifies each entry, and renders both the PR-body block and the Step 8
hand-off decision list. The classification is a fixed table keyed on `kind` (with
one verb sub-split), NOT model judgment -- so the pass cannot be skipped by
routing everything to draft.

    class `auto`    -- a resolution is prescribed and has not been attempted yet.
                       Only `visual-deliverable` qualifies: every other producer
                       already makes its own bounded attempt before it writes an
                       entry (rigor re-runs at 1.0a per #81, skip-audit re-runs
                       at 2a, verify-build spends FB-0012's bounded retry), or is
                       doctrinally barred from one (coverage must not self-declare
                       a criterion; status-surface must not silently rewrite an
                       un-fenced human doc).
    class `ask`     -- a decision the human can answer now. The agent drafts the
                       resolution; the human supplies only the approval.
    class `blocked` -- needs an out-of-session human action (rotate a leaked
                       secret, vet a dependency). The one class a draft PR
                       genuinely exists for.

Safety invariants encoded here (each has an eval case in
`evals/run_manifest_triage_evals.py`):

  1. Clearing is NOT this engine's job. Every entry carries `clears_when` naming
     the re-check that must pass; no output shape can express "cleared". An entry
     leaves the manifest only when the check that produced it re-runs clean
     (FB-0062: a verdict is trusted only if its artifact exists and matches HEAD).
  2. `residual` = every entry whose `clears_when` re-check has not passed, minus
     recorded waivers -- EXCEPT `verify-build`, which is never subtracted. Never a
     class filter: keying the draft decision on class is how a failed
     `visual-deliverable` attempt could vanish into a ready PR (SKILL.md:843).
  3. No merge-ready PR on a non-PASS build (SKILL.md:308,310 -- unqualified). A
     `verify-build` entry is never waivable-to-ready and never subtracted, so
     `verdict` can never be READY while one is present.
  4. Fail-safe direction is toward the human: an unrecognized verb classifies
     `blocked` for security/a11y (their out-of-session modes are the dangerous
     ones to mis-class) and `ask` for every other kind. Never `auto`.
  5. State that cannot be recovered never yields `auto`. `/tmp` is a same-session
     cache; the PR body is the durable record. A missing state file means state
     was LOST (Step 7a.5 initializes it), so `auto` downgrades to `ask` -- a
     question is the safe direction, a silent re-attempt is not.
  6. A waiver is honored only on an exact (kind, finding) fingerprint match
     against an entry present in the same recompute. Ambiguity => not subtracted,
     so an over-greedy body reconstruction cannot remove a real blocker.

Subcommands (stdlib only):

    add-entry      --kind K --finding F --needs V [--resolution R] [--attempted]
    parse          --body-file PATH|-
    classify       --entries-file PATH|-  [--state-file PATH] [--body-file PATH]
    render-manifest  --entries-file PATH|-
    render-decisions --entries-file PATH|-
    init-state     --branch B [--path PATH]
    record-attempt --branch B --kind K --finding F [--path PATH]
    waive          --branch B --kind K --finding F [--path PATH]
    state          --branch B [--path PATH] [--body-file PATH]

Exit codes are the contract the shell keys on; keep them stable. 0 = success,
2 = malformed input. `classify` always exits 0 -- the verdict is the signal.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from manifest_contract import (  # noqa: E402  (sibling-module import, house pattern)
    MANIFEST_CLOSE,
    MANIFEST_HEADING,
    MANIFEST_OPEN,
    extract_manifest_region,
    slug as _slug,
)

# --------------------------------------------------------------------------
# Contract vocabulary. Both lists are closed; drift is caught by the fail-safe
# in `classify`, never by trusting the producer.
# --------------------------------------------------------------------------

KINDS = (
    "rigor",
    "security",
    "a11y",
    "verify-build",
    "coverage",
    "skip-audit",
    "status-surface",
    "visual-deliverable",
)

VERBS = (
    "secret rotation",
    "design decision",
    "dep vetting",
    "regression fix",
    "re-run",
    "reconcile",
    "declare + fence",
    "hand-author",
    "human-waive",
)

# Verbs that mean "a human must act outside this session". Only meaningful for
# security/a11y -- the two kinds whose findings can require out-of-repo action.
OUT_OF_SESSION_VERBS = ("secret rotation", "dep vetting")

WAIVED_HEADING = "## Waived at ship"
ATTEMPTED_MARKER = "already-attempted"

# Kinds whose blocker a human's assertion CANNOT clear — only a passing check can.
# Declared once here rather than spelled out as inline `kind == "verify-build"`
# comparisons at every decision point: the property is real and will recur (a
# "CI red" kind, a "migration not applied" kind have identical semantics), and
# four coincidental string compares is how the next one gets added in three
# places and forgotten in a fourth.
#
# For these kinds: a waiver is RECORDED but never subtracted from the residual
# set, and "waive and ship as-is" is never offered — because it would be a lie,
# the PR stays a draft either way. SKILL.md:308,310 is unqualified: no
# merge-ready PR on a non-PASS build.
CHECK_ONLY = frozenset({"verify-build"})

# Everything kind-specific in ONE record per kind, so adding a kind is one edit
# and a missing field is visible at a glance (every read site is a .get() with a
# fallback, so a forgotten entry degrades silently to generic prose otherwise).
#
#   clears_when -- the re-check that must pass before the entry may be removed.
#                  This engine NAMES it; it never performs or asserts it.
#   means       -- plain language: what actually did not pass. The engineer
#                  shorthand this replaces is what made these unanswerable.
#   blocked_means -- override when the entry is `blocked`: it is blocked because
#                  the action is outside this session, NOT because the fix is
#                  ambiguous. Saying the latter would be wrong to the reader.
#   needs_you   -- the one decision, phrased so it is answerable in a word.
#   then        -- what the agent does with the answer.
KIND_COPY: dict[str, dict[str, str]] = {
    "rigor": {
        "clears_when": "re-read the /flow:staff-review rigor marker for the current source (ship 1.0a)",
        "means": "The deep code review either did not run on the final version of this code, or its record went stale.",
        "needs_you": "Either let me re-run the review, or tell me to ship without it.",
    },
    "security": {
        "clears_when": "re-run /flow:security-review and confirm the BLOCKER is gone",
        "means": "The security review found something it will not fix on its own because more than one fix is defensible.",
        "blocked_means": "The security review found something only you can act on outside this session.",
        "needs_you": "Pick a fix, or — if it needs rotating a secret or vetting a dependency — do that, then tell me.",
    },
    "a11y": {
        "clears_when": "re-run /flow:accessibility-review and confirm the BLOCKER is gone",
        "means": "The accessibility review found something it will not fix on its own because more than one fix is defensible.",
        "blocked_means": "The accessibility review found something only you can act on outside this session.",
        "needs_you": "Pick a fix, or tell me to ship as-is and accept it.",
    },
    "verify-build": {
        "clears_when": "re-run /flow:verify-build and confirm overall_verdict is PASS",
        "means": "The app was built and exercised, and it did not demonstrably do what the plan said it would.",
        "needs_you": "A decision on how to get a passing build — I will not call a failing one shippable.",
        "then": ("I apply your answer and re-run the build check. A failing build never becomes a "
                 "ready PR automatically — if you accept the risk, you mark it ready yourself."),
    },
    "coverage": {
        "clears_when": "declare the criterion in the plan's Spec-walk block, then re-run /flow:audit-coverage clean",
        "means": "This change alters behavior that no declared test criterion covers, so nothing verified it.",
        "needs_you": "Approve the criterion I drafted, or tell me to ship without covering it.",
    },
    "skip-audit": {
        "clears_when": "re-run the named stage, then re-run /flow:audit-skips and confirm LEGITIMATE",
        "means": "A pipeline stage was skipped, and the skip could not be justified against the actual diff.",
        "needs_you": "Approve running the stage, or tell me the skip is fine.",
    },
    "status-surface": {
        "clears_when": "reconcile or declare+fence the surface, then re-run the ship 5a.5 scan clean",
        "means": "A document that orients future sessions still describes shipped work as upcoming.",
        "needs_you": "Approve the corrected wording I drafted, or tell me to leave the document alone.",
    },
    "visual-deliverable": {
        "clears_when": ("re-assert ship 7a: a fresh verify-build buffer for this HEAD with >=1 frame, "
                        "plus a visual-history entry"),
        "means": "This change is visual, but the visual walkthrough or its durable record is missing.",
        "needs_you": "Approve capturing the walkthrough, or tell me to ship without it.",
    },
}

KINDS = tuple(KIND_COPY)

DEFAULT_THEN = "I apply it, re-run the check that raised this, and mark the PR ready once it passes."
BLOCKED_THEN = "once you have done it outside this session, tell me and I re-check and mark the PR ready."


def _copy(kind: str, field: str, fallback: str = "") -> str:
    return KIND_COPY.get(kind, {}).get(field, fallback)


def _means(kind: str, cls: str) -> str:
    if cls == "blocked":
        blocked = _copy(kind, "blocked_means")
        if blocked:
            return blocked
    return _copy(kind, "means", "A ship gate did not pass.")


def _fingerprint(kind: str, finding: str) -> str:
    """Stable id for one entry. Whitespace-normalized so a re-render that rewraps
    the line still matches, but content-sensitive so an edited finding does NOT
    (invariant 6: a waiver lapses when the finding it was given for changes)."""
    norm = re.sub(r"\s+", " ", (finding or "").strip()).lower()
    return hashlib.sha256(f"{kind}\x00{norm}".encode("utf-8")).hexdigest()[:16]


def _default_state_path(branch: str) -> str:
    return f"/tmp/flow-ship-state-{_slug(branch)}.json"


# --------------------------------------------------------------------------
# parse
# --------------------------------------------------------------------------

# `- [kind] finding -- needs: verb -- confidence: axis -- candidate resolutions: ...`
# Em-dash separated, matching the Step 7 body template. The finding is
# non-greedy up to the first ` -- needs:` so an em dash inside the finding is safe.
_LINE_RE = re.compile(
    r"^\s*-\s*\[(?P<kind>[a-z0-9-]+)\]\s*"
    r"(?P<finding>.+?)"
    r"\s+—\s*needs:\s*(?P<needs>[^—]+?)"
    r"(?:\s+—\s*confidence:\s*(?P<confidence>[^—]+?))?"
    r"(?:\s+—\s*candidate resolutions?:\s*(?P<resolution>.+?))?"
    r"\s*$"
)


def parse_entries(body: str) -> list[dict[str, Any]]:
    """Extract manifest entries from a PR body (or a bare list of lines).

    Reads only within the manifest fences when they are present, so prose
    elsewhere in the body that happens to look like an entry is never picked up.
    """
    text = extract_manifest_region(body or "")

    entries: list[dict[str, Any]] = []
    for raw in text.splitlines():
        m = _LINE_RE.match(raw)
        if not m:
            continue
        kind = m.group("kind").strip()
        finding = m.group("finding").strip()
        # A rendered entry carries its already-attempted marker inline; strip it
        # back out of the finding so the fingerprint is stable across renders.
        attempted = ATTEMPTED_MARKER in finding
        finding = re.sub(r"\s*\(" + ATTEMPTED_MARKER + r"[^)]*\)\s*", " ", finding).strip()
        entries.append(
            {
                "kind": kind,
                "finding": finding,
                "needs": (m.group("needs") or "").strip(),
                "confidence": (m.group("confidence") or "").strip(),
                "drafted_resolution": (m.group("resolution") or "").strip(),
                "already_attempted": attempted,
                "fingerprint": _fingerprint(kind, finding),
            }
        )
    return entries


# --------------------------------------------------------------------------
# state -- waivers + recorded attempts
# --------------------------------------------------------------------------


def _empty_state(branch: str, status: str = "unavailable") -> dict[str, Any]:
    """`status` is derived from WHERE the state came from and is never persisted —
    `load_state` stamps it at each of its three exits."""
    return {"branch": branch, "status": status, "waivers": [], "attempts": []}


def load_state(branch: str, path: str | None, body: str | None) -> dict[str, Any]:
    """Load ship state.

    `/tmp` is a same-session cache; the PR body is the durable record (Step 7c
    reads the body BEFORE its recompute overwrites it). Status is load-bearing:

      present       -- the cache was read. `auto` is permitted.
      reconstructed -- rebuilt from the PR body only. Waivers are honored;
                       `auto` is NOT permitted (we cannot prove no attempt was
                       made, and invariant 5 fails toward a question).
      unavailable   -- neither surface. Waivers empty, `auto` not permitted.
    """
    p = path or _default_state_path(branch)
    try:
        with open(p, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if isinstance(data, dict):
            data.setdefault("waivers", [])
            data.setdefault("attempts", [])
            data["status"] = "present"
            return data
    except (OSError, ValueError):
        pass

    if body:
        st = _empty_state(branch, "reconstructed")
        st["waivers"] = _waivers_from_body(body)
        st["attempts"] = [
            {"fingerprint": e["fingerprint"], "kind": e["kind"], "finding": e["finding"]}
            for e in parse_entries(body)
            if e["already_attempted"]
        ]
        return st

    return _empty_state(branch, "unavailable")


def _waivers_from_body(body: str) -> list[dict[str, Any]]:
    """Parse the `## Waived at ship` section. Best-effort by nature -- which is
    why invariant 6 requires an exact fingerprint match downstream, and why an
    unmatched waiver leaves its entry in the residual set rather than removing it.
    """
    if WAIVED_HEADING not in body:
        return []
    tail = body.split(WAIVED_HEADING, 1)[1]
    # Stop at the next H2 so a later section can't leak entries in.
    section = re.split(r"\n##\s", tail, maxsplit=1)[0]
    out = []
    for raw in section.splitlines():
        m = re.match(r"^\s*-\s*\[(?P<kind>[a-z0-9-]+)\]\s*(?P<finding>.+?)\s*$", raw)
        if not m:
            continue
        kind = m.group("kind").strip()
        finding = re.sub(r"\s+—\s*waived by .*$", "", m.group("finding")).strip()
        out.append(
            {"fingerprint": _fingerprint(kind, finding), "kind": kind, "finding": finding}
        )
    return out


def _write_state(branch: str, path: str | None, mutate) -> str:
    p = path or _default_state_path(branch)
    try:
        with open(p, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, dict):
            data = _empty_state(branch, "present")
    except (OSError, ValueError):
        data = _empty_state(branch, "present")
    data.setdefault("waivers", [])
    data.setdefault("attempts", [])
    data["branch"] = branch
    data.pop("status", None)
    mutate(data)
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, sort_keys=True)
    return p


# --------------------------------------------------------------------------
# classify
# --------------------------------------------------------------------------


def _class_for(kind: str, needs: str, attempted: bool, auto_allowed: bool) -> tuple[str, str]:
    """The table. Returns (class, action).

    Keyed on `kind`, with one verb sub-split for security/a11y. Every kind other
    than `visual-deliverable` already made its bounded attempt at its producer
    site, or is doctrinally barred from making one -- so re-running here would
    either loop or overrule a rule that exists for a reason.
    """
    verb = (needs or "").strip().lower()

    if kind in ("security", "a11y"):
        if verb in OUT_OF_SESSION_VERBS:
            return "blocked", "needs an action outside this session"
        if verb not in VERBS:
            # Fail-safe: for these two kinds the dangerous mis-class is treating
            # an out-of-session item as one-word-dismissible. Default to blocked.
            return "blocked", "unrecognized resolution verb on a security/a11y finding"
        return "ask", "pick a fix, or accept it as-is"

    if kind == "visual-deliverable":
        if attempted:
            return "ask", "the one bounded attempt already ran and did not clear it"
        if not auto_allowed:
            # Invariant 5: state lost => cannot prove no attempt was made.
            return "ask", "no recoverable record of a prior attempt; not re-attempting blind"
        return "auto", "capture the walkthrough and author the visual-history entry, once"

    if kind in KINDS:
        return "ask", "already attempted at its producer, or the agent must not decide it"

    # Unknown kind: never auto, never silently dropped.
    return "ask", "unrecognized manifest kind"


def classify(entries: list[dict[str, Any]], state: dict[str, Any]) -> dict[str, Any]:
    auto_allowed = state.get("status") == "present"
    attempted_fps = {a.get("fingerprint") for a in state.get("attempts", [])}
    waived_fps = {w.get("fingerprint") for w in state.get("waivers", [])}

    out: list[dict[str, Any]] = []
    for e in entries:
        kind = e["kind"]
        fp = e["fingerprint"]
        attempted = bool(e.get("already_attempted")) or fp in attempted_fps
        cls, action = _class_for(kind, e.get("needs", ""), attempted, auto_allowed)

        # Invariant 6: exact fingerprint match only.
        waived = fp in waived_fps
        # Invariant 3: a CHECK_ONLY kind's waiver is recorded, never subtracted.
        subtracted = waived and kind not in CHECK_ONLY

        out.append(
            {
                **e,
                "class": cls,
                "action": action,
                "clears_when": _copy(kind, "clears_when", "re-run the check that produced this entry"),
                "already_attempted": attempted,
                "waived": waived,
                "waivable": cls == "ask" and kind not in CHECK_ONLY,
                "in_residual": not subtracted,
            }
        )

    # Invariant 2: residual is the uncleared set minus honored waivers -- not a
    # class filter. Nothing here can mark an entry cleared (invariant 1).
    residual = [e for e in out if e["in_residual"]]
    waived_out = [e for e in out if not e["in_residual"]]

    if not residual:
        verdict = "READY"
    elif any(e["class"] == "blocked" for e in residual):
        verdict = "BLOCKED"
    else:
        verdict = "DECIDE"

    return {
        "verdict": verdict,
        "state_status": state.get("status", "unavailable"),
        "entries": out,
        "residual": residual,
        "waived": waived_out,
        "counts": {
            "auto": sum(1 for e in residual if e["class"] == "auto"),
            "ask": sum(1 for e in residual if e["class"] == "ask"),
            "blocked": sum(1 for e in residual if e["class"] == "blocked"),
            "waived": len(waived_out),
        },
    }


# --------------------------------------------------------------------------
# render
# --------------------------------------------------------------------------


def render_manifest(result: dict[str, Any]) -> str:
    """The PR-body NOT-READY block.

    The sentinel and both fences are byte-preserved so `lib/pr-coherence.py`,
    `/flow:doctor` Check 2.10, and `/flow:land`'s pre-merge check keep matching.
    """
    residual = result.get("residual", [])
    if not residual:
        return ""
    lines = [f"## {MANIFEST_HEADING} — unresolved blockers", MANIFEST_OPEN]
    for e in residual:
        kind = e["kind"]
        attempted = f" ({ATTEMPTED_MARKER})" if e.get("already_attempted") else ""
        lines.append(f"- [{kind}] {e['finding']}{attempted} — needs: {e.get('needs','')}"
                     f" — candidate resolutions: {e.get('drafted_resolution') or '(none drafted)'}")
        lines.append(f"  - **What this means:** {_means(kind, e['class'])}")
        lines.append(f"  - **What I need from you:** {_copy(kind, 'needs_you', 'A decision on how to proceed.')}")
        lines.append(f"  - **What happens then:** {_then(e)}")
    lines.append(MANIFEST_CLOSE)
    lines.append(
        "> Answer the items above and I apply them and mark this ready — you do not have to "
        "edit anything here. Do not merge while this block is present."
    )
    return "\n".join(lines)


def _then(entry: dict[str, Any]) -> str:
    if entry["class"] == "blocked":
        return BLOCKED_THEN
    return _copy(entry["kind"], "then", DEFAULT_THEN)


def render_decisions(result: dict[str, Any]) -> str:
    """The Step 8 hand-off. Questions first, never a bare PR URL."""
    residual = result.get("residual", [])
    asks = [e for e in residual if e["class"] in ("ask", "auto")]
    blocked = [e for e in residual if e["class"] == "blocked"]
    if not asks and not blocked:
        return ""

    out: list[str] = []
    if asks:
        out.append("**Decisions for you** — answer by number; I apply it and mark the PR ready.")
        out.append("")
        for i, e in enumerate(asks, 1):
            out.append(f"{i}. {_means(e['kind'], e['class'])}")
            out.append(f"   - Detail: {e['finding']}")
            if e.get("already_attempted"):
                out.append("   - Already tried: I attempted this once and it did not clear.")
            rec = e.get("drafted_resolution") or "no automatic fix available"
            out.append(f"   - **My recommendation: {rec}** — {e.get('action','')}.")
            opts = ["[a] do that (recommended)"]
            if e.get("waivable"):
                opts.append("[b] waive it and ship as-is")
            elif e["kind"] == "verify-build":
                opts.append(
                    "[b] leave it — I will not mark a failing build ready; you can do that "
                    "yourself on GitHub if you accept the risk"
                )
            opts.append("[c] something else — tell me")
            out.append(f"   - Options: {'  '.join(opts)}")
            out.append("")
    if blocked:
        out.append("**Needs you outside this session** — I cannot do these, and they are not waivable:")
        out.append("")
        for e in blocked:
            why = e.get("action", "")
            out.append(f"- {e['finding']} — {_means(e['kind'], 'blocked')}"
                       + (f" ({why})" if why else ""))
        out.append("")
    return "\n".join(out).rstrip() + "\n"


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def _read(path: str) -> str:
    if path == "-":
        return sys.stdin.read()
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def _load_entries(path: str) -> list[dict[str, Any]]:
    raw = _read(path)
    try:
        data = json.loads(raw)
    except ValueError:
        return parse_entries(raw)
    if isinstance(data, dict):
        data = data.get("entries", [])
    if not isinstance(data, list):
        print("malformed entries input", file=sys.stderr)
        raise SystemExit(2)
    for e in data:
        e.setdefault("fingerprint", _fingerprint(e.get("kind", ""), e.get("finding", "")))
        e.setdefault("already_attempted", False)
    return data


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("parse")
    p.add_argument("--body-file", required=True)

    for name in ("classify", "render-manifest", "render-decisions"):
        p = sub.add_parser(name)
        p.add_argument("--entries-file", required=True)
        p.add_argument("--state-file")
        p.add_argument("--body-file")
        p.add_argument("--branch", default="")

    p = sub.add_parser("init-state")
    p.add_argument("--branch", required=True)
    p.add_argument("--path")

    for name in ("record-attempt", "waive"):
        p = sub.add_parser(name)
        p.add_argument("--branch", required=True)
        p.add_argument("--kind", required=True)
        p.add_argument("--finding", required=True)
        p.add_argument("--path")

    p = sub.add_parser("add-entry")
    p.add_argument("--kind", required=True)
    p.add_argument("--finding", required=True)
    p.add_argument("--needs", required=True)
    p.add_argument("--resolution", default="")
    p.add_argument("--confidence", default="decision-required")
    p.add_argument("--attempted", action="store_true")

    p = sub.add_parser("state")
    p.add_argument("--branch", required=True)
    p.add_argument("--path")
    p.add_argument("--body-file")

    args = ap.parse_args(argv)

    if args.cmd == "add-entry":
        # One place owns the line shape. Producers name their values; they never
        # hand-compose the em-dash format, so there is nothing for a parser to
        # defensively un-mangle later. Validate against the closed vocabularies
        # at WRITE time rather than fail-safing at classify time.
        if args.kind not in KINDS:
            print(f"unknown kind {args.kind!r}; expected one of {', '.join(KINDS)}", file=sys.stderr)
            return 2
        if args.needs not in VERBS:
            print(f"unknown needs verb {args.needs!r}; expected one of {', '.join(VERBS)}", file=sys.stderr)
            return 2
        finding = args.finding.strip()
        if args.attempted:
            finding = f"{finding} ({ATTEMPTED_MARKER})"
        print(f"- [{args.kind}] {finding} — needs: {args.needs}"
              f" — confidence: {args.confidence}"
              f" — candidate resolutions: {args.resolution or '(none drafted)'}")
        return 0

    if args.cmd == "parse":
        print(json.dumps({"entries": parse_entries(_read(args.body_file))}, indent=2))
        return 0

    if args.cmd in ("classify", "render-manifest", "render-decisions"):
        entries = _load_entries(args.entries_file)
        body = _read(args.body_file) if args.body_file else None
        state = load_state(args.branch, args.state_file, body)
        result = classify(entries, state)
        if args.cmd == "classify":
            print(json.dumps(result, indent=2))
        elif args.cmd == "render-manifest":
            print(render_manifest(result))
        else:
            print(render_decisions(result))
        return 0

    if args.cmd == "init-state":
        path = _write_state(args.branch, args.path, lambda d: None)
        print(path)
        return 0

    if args.cmd in ("record-attempt", "waive"):
        rec = {
            "fingerprint": _fingerprint(args.kind, args.finding),
            "kind": args.kind,
            "finding": args.finding,
        }
        key = "attempts" if args.cmd == "record-attempt" else "waivers"

        def mutate(d, rec=rec, key=key):
            if not any(x.get("fingerprint") == rec["fingerprint"] for x in d[key]):
                d[key].append(rec)

        path = _write_state(args.branch, args.path, mutate)
        print(path)
        return 0

    if args.cmd == "state":
        body = _read(args.body_file) if args.body_file else None
        print(json.dumps(load_state(args.branch, args.path, body), indent=2))
        return 0

    # Unreachable: the subparser is required and every command is handled above.


if __name__ == "__main__":
    raise SystemExit(main())
