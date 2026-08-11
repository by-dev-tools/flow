#!/usr/bin/env python3
"""Deterministic draft-manifest triage engine (FB-0075).

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
    init-run       --branch B          (truncate the manifest for a fresh run)
    manifest-path  --branch B
    init-state     --branch B [--path PATH]
    record-attempt --branch B --kind K --finding F [--path PATH]
    waive          --branch B --kind K --finding F [--path PATH]
    state          --branch B [--path PATH] [--body-file PATH]

Exit codes are the contract the shell keys on; keep them stable:

    0  success
    2  malformed input (unparseable entries, unknown kind/verb on `add-entry`,
       an unwritable MANIFEST path on `init-run`)
    3  `waive` only: the waiver WAS recorded, but its (kind, finding) fingerprint
       matches no entry on the current manifest -- including when no manifest
       exists at all (usually a mistyped --finding, or the wrong --branch) -- so
       it will subtract nothing. Distinct from 2 because the write succeeded:
       this is a "check the finding text" signal, not a failure. Callers that
       chain off `waive` should treat 3 as a warning, not an abort.

Anything else is an uncaught exception exiting 1 -- e.g. a missing --body-file on
`parse`, or an unwritable state path. Treat any exit outside {0, 2, 3} as failure.
(Closing that set properly means a top-level OSError handler + an eval; tracked in
the roadmap rather than widened here.)

`classify` always exits 0 -- the verdict is the signal.
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
        "waive_cost": "this code merges without a deep review of its final version",
        "why": "re-running it is quick and tells us whether anything was actually missed",
    },
    "security": {
        "clears_when": "re-run /flow:security-review and confirm the BLOCKER is gone",
        "means": "The security review found something it will not fix on its own because more than one fix is defensible.",
        "blocked_means": "The security review found something only you can act on outside this session.",
        "needs_you": "Pick a fix, or tell me to ship as-is and accept it.",
        "blocked_needs_you": "Rotate the affected secret (or replace the dependency), then tell me and I re-check.",
        "why": "more than one fix is defensible here, so picking one is a judgement call rather than a lookup",
    },
    "a11y": {
        "clears_when": "re-run /flow:accessibility-review and confirm the BLOCKER is gone",
        "means": "The accessibility review found something it will not fix on its own because more than one fix is defensible.",
        "blocked_means": "The accessibility review found something only you can act on outside this session.",
        "needs_you": "Pick a fix, or tell me to ship as-is and accept it.",
        "blocked_needs_you": "Do the change on your side, then tell me and I re-check.",
        "waive_cost": "the accessibility problem ships as-is",
        "why": "more than one fix is defensible here, so picking one is a judgement call rather than a lookup",
    },
    "verify-build": {
        "clears_when": "re-run /flow:verify-build and confirm overall_verdict is PASS",
        "means": "The app was built and exercised, and it did not demonstrably do what the plan said it would.",
        "needs_you": "Tell me how to get a passing build, or that you accept it failing — I won't call a failing build shippable.",
        "why": "I already tried the automatic fix and it did not hold, so the next attempt needs a different angle",
        "then": ("I apply your answer and re-run the build check. A failing build never becomes a "
                 "ready PR automatically — if you accept the risk, you mark it ready yourself."),
    },
    "coverage": {
        "clears_when": "declare the criterion in the plan's Spec-walk block, then re-run /flow:audit-coverage clean",
        "means": "This change alters behavior that no declared test criterion covers, so nothing verified it.",
        "needs_you": "Approve the criterion I drafted, or tell me to ship without covering it.",
        "waive_cost": "this behavior ships with nothing verifying it",
        "why": "I can write the test criterion, but declaring my own work covered is me grading my own homework",
    },
    "skip-audit": {
        "clears_when": "re-run the named stage, then re-run /flow:audit-skips and confirm LEGITIMATE",
        "means": "A pipeline stage was skipped, and the skip could not be justified against the actual diff.",
        "needs_you": "Approve running the stage, or tell me the skip is fine.",
        "waive_cost": "that check stays un-run for this change",
        "why": "the skip may well be fine — I just can't confirm it from the change itself",
    },
    "status-surface": {
        "clears_when": "reconcile or declare+fence the surface, then re-run the ship 5a.5 scan clean",
        "means": "A document that orients future sessions still describes shipped work as upcoming.",
        "needs_you": "Approve the corrected wording I drafted, or tell me to leave the document alone.",
        "waive_cost": "the document keeps telling future sessions this work is still upcoming",
        "why": "it's your document, so I won't silently rewrite it",
    },
    "visual-deliverable": {
        "clears_when": ("re-assert ship 7a: a fresh verify-build buffer for this HEAD with >=1 frame, "
                        "plus a visual-history entry"),
        "means": "This change is visual, but the visual walkthrough or its durable record is missing.",
        "needs_you": "Approve capturing the walkthrough, or tell me to ship without it.",
        "waive_cost": "this change ships with no visual record, so the next visual change has nothing to compare against",
        "why": "without it nobody can see what the change actually looks like before merging",
    },
}

KINDS = tuple(KIND_COPY)

DEFAULT_THEN = "I apply it, re-run the check that raised this, and mark the PR ready once it passes."
BLOCKED_THEN = "Once you have done it outside this session, tell me and I re-check."


def _copy(kind: str, field: str, fallback: str = "") -> str:
    return KIND_COPY.get(kind, {}).get(field, fallback)


def _needs_you(kind: str, cls: str) -> str:
    if cls == "blocked":
        blocked = _copy(kind, "blocked_needs_you")
        if blocked:
            return blocked
    return _copy(kind, "needs_you", "A decision on how to proceed.")


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


def _repo_scratch(name: str) -> str:
    """Repo-local scratch path (FB-0078), replacing the old global /tmp default.

    The manifest is not a cache: producers append to it and `classify` reads it to decide
    draft-vs-ready. `/tmp/flow-manifest-<branch>.md` is ONE filename shared by every project
    on a same-named branch, and verify-build entries are never subtractable — so a single
    foreign entry would permanently draft an unrelated clean PR. Repo-local is unique per
    worktree by construction. Falls back to a tempdir only when there is no worktree at all.
    """
    import subprocess
    import tempfile
    try:
        out = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                             capture_output=True, text=True, timeout=10)
        root = out.stdout.strip() if out.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        root = ""
    if not root:
        return str(Path(tempfile.gettempdir()) / "flow-detached" / name)
    d = Path(root) / ".flow"
    # CWE-59: never write scratch through a symlink (same refusal as the shell sites).
    if d.is_symlink():
        raise SystemExit(f"BLOCKER: {d} is a symlink -- refusing to write flow scratch through it.")
    d.mkdir(parents=True, exist_ok=True)
    ign = d / ".gitignore"
    if not ign.exists():
        ign.write_text("# Created by flow. Ephemeral scratch; never committed.\n*\n", encoding="utf-8")
    return str(d / name)


def _default_state_path(branch: str) -> str:
    return _repo_scratch(f"ship-state-{_slug(branch)}.json")


def _default_manifest_path(branch: str) -> str:
    """Branch-scoped, like the state file. A single fixed name outlives the run,
    the branch and the worktree, so the next ship would re-read the previous
    one's entries — and a `verify-build` entry among them is never subtractable,
    permanently drafting a PR over a blocker from another branch."""
    return _repo_scratch(f"manifest-{_slug(branch)}.md")


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
    except FileNotFoundError:
        data = _empty_state(branch, "present")
    except (OSError, ValueError) as exc:
        # Never silently discard recorded waivers/attempts — the PR body is the
        # durable backstop, but the operator needs to know the cache was lost.
        print(f"⚠️ [manifest-triage] state file {p} unreadable ({exc}); reinitializing. "
              "Recorded waivers will be recovered from the PR body if available.", file=sys.stderr)
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
        # Invariant 4 applies HERE most of all: this is the only kind that can
        # return `auto`, and §7c rebuilds entries by parsing a live PR body a
        # human can edit. An off-vocabulary verb must become a question, never a
        # silent re-run→commit→push.
        # Only this kind's OWN verbs may trigger the auto attempt. An
        # off-vocabulary verb, or an in-vocabulary verb belonging to some other
        # kind (a hand-edited PR body at §7c can produce either), becomes a
        # question — never a silent re-run→commit→push.
        if verb not in ("re-run", "hand-author"):
            return "ask", "resolution verb doesn't match this check — not re-attempting on a line I can't read"
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
        lines.append(f"  - **What I need from you:** {_needs_you(kind, e['class'])}")
        then = _then(e)
        # Only state it per-entry when it DIFFERS from the default — otherwise six
        # of eight entries repeat one sentence verbatim, and the repetition (not
        # the nesting) is what turns this into a wall at 6+ entries.
        if then != DEFAULT_THEN:
            lines.append(f"  - **What happens then:** {then}")
    lines.append(
        "> **What happens when you answer:** " + DEFAULT_THEN + " Items that say otherwise "
        "above are the exceptions. You do not have to edit anything here — just tell me. "
        "Do not merge while this block is present."
    )
    lines.append(MANIFEST_CLOSE)
    return "\n".join(lines)


def _then(entry: dict[str, Any]) -> str:
    if entry["class"] == "blocked":
        return BLOCKED_THEN
    return _copy(entry["kind"], "then", DEFAULT_THEN)


def render_decisions(result: dict[str, Any]) -> str:
    """The Step 8 hand-off. Questions first, never a bare PR URL."""
    residual = result.get("residual", [])
    # A residual `auto` entry should not normally exist — §7a.5 attempts it and
    # demotes to `ask` on failure. If one reaches here anyway (the attempt step
    # was skipped), render it as a question rather than dropping it: an unanswered
    # item the human never sees is the failure mode this whole change exists to
    # remove. It carries no waive option (waivable is ask-only), which is correct
    # — the agent has not yet tried, so "waive" is not the honest next move.
    asks = [e for e in residual if e["class"] in ("ask", "auto")]
    blocked = [e for e in residual if e["class"] == "blocked"]
    if not asks and not blocked:
        return ""

    out: list[str] = []
    if asks:
        # Do NOT promise "and mark the PR ready" — a verify-build entry renders in
        # this same list and by rule cannot reach ready this way. A header that
        # overpromises is the thing this whole change exists to stop doing.
        out.append("**Decisions for you** — answer by number. I apply your answer and re-run "
                   "the check; if it passes, that takes the PR closer to ready.")
        out.append("")
        for i, e in enumerate(asks, 1):
            kind = e["kind"]
            out.append(f"{i}. {e['finding']}")
            out.append(f"   - What this means: {_means(kind, e['class'])}")
            if e.get("already_attempted"):
                out.append("   - Already tried: I attempted this once and it did not clear.")

            options: list[str] = []
            rec = e.get("drafted_resolution", "")
            if rec:
                why = _copy(kind, "why")
                out.append(f"   - **My recommendation: {rec}**" + (f" — {why}." if why else ""))
                options.append("do that (recommended)")
            else:
                # No proposal means no "[a] do that" to point at. Asking someone to
                # approve a placeholder is the round-trip this exists to remove.
                out.append("   - I don't have a fix to propose for this one.")

            if e.get("waivable"):
                cost = _copy(kind, "waive_cost")
                options.append("waive it and ship as-is" + (f" — {cost}" if cost else ""))
            elif kind in CHECK_ONLY:
                options.append("leave it — I won't mark a failing build ready; you can do that "
                               "yourself on GitHub if you accept the risk")
            options.append("something else — tell me")
            out.append("   - Options:")
            for opt in options:
                out.append(f"     - {opt}")
            out.append("")
    if blocked:
        out.append("**Needs you outside this session** — I can't do these, and they can't be waived:")
        out.append("")
        for e in blocked:
            out.append(f"- {e['finding']}")
            out.append(f"  - What this means: {_means(e['kind'], 'blocked')}")
            out.append(f"  - What I need from you: {_needs_you(e['kind'], 'blocked')}")
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
    # A missing manifest file is the COMMON case — no producer fired, so there is
    # nothing to triage. That is an empty manifest, not an error. (`parse` keeps
    # failing loud on a missing file; the two commands have different contracts.)
    if path != "-" and not Path(path).exists():
        return []
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

    p = sub.add_parser("manifest-path")
    p.add_argument("--branch", required=True)

    p = sub.add_parser("state-path")
    p.add_argument("--branch", required=True)

    p = sub.add_parser("init-run")
    p.add_argument("--branch", required=True)

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

    if args.cmd == "manifest-path":
        print(_default_manifest_path(args.branch))
        return 0

    if args.cmd == "state-path":
        # Resolve WITHOUT creating. Readers (§7a.6 render, §8 hand-off, §7c
        # reconcile) must use this, never `init-state`: materializing an empty
        # record makes a LOST state look `present`, which re-enables `auto` and
        # silently defeats invariant 5 on exactly the cross-session/fresh-host
        # reconcile it exists to protect. Only a fresh run (§7a.5) may init.
        print(_default_state_path(args.branch))
        return 0

    if args.cmd == "init-run":
        # Truncate the manifest for a FRESH run. Called once at pre-flight, before
        # any producer appends. Deliberately separate from `init-state`, which is
        # called again later and must preserve recorded waivers/attempts.
        mp = _default_manifest_path(args.branch)
        try:
            open(mp, "w", encoding="utf-8").close()
        except OSError as exc:
            print(f"⚠️ [manifest-triage] could not reset {mp}: {exc}", file=sys.stderr)
            return 2
        print(mp)
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
        if args.cmd == "waive":
            # A waiver keyed to a finding that is not on the current manifest can
            # never subtract anything (invariant 6). Fail-safe, but the caller
            # deserves a signal rather than a silent no-op + a still-drafted PR.
            mp = _default_manifest_path(args.branch)
            # An ABSENT manifest has zero entries, so it matches nothing — the same
            # signal, not a reason to stay silent. The likeliest real trigger is a
            # wrong --branch (which resolves a different manifest path), and exiting
            # 0 there is the FB-0010 silent-skip shape.
            if Path(mp).exists():
                fps = {e["fingerprint"] for e in parse_entries(_read(mp))}
                missing_note = ""
            else:
                fps = set()
                missing_note = " (no manifest file at that path — check --branch)"
            if rec["fingerprint"] not in fps:
                print(f"⚠️ [manifest-triage] no entry on {mp} matches [{args.kind}] "
                      f"{args.finding!r}{missing_note} — the waiver was recorded but will "
                      "subtract nothing. Check the finding text matches verbatim.",
                      file=sys.stderr)
                return 3
        return 0

    if args.cmd == "state":
        body = _read(args.body_file) if args.body_file else None
        print(json.dumps(load_state(args.branch, args.path, body), indent=2))
        return 0

    # Unreachable: the subparser is required and every command is handled above.


if __name__ == "__main__":
    raise SystemExit(main())
