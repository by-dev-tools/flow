#!/usr/bin/env python3
"""Is every reference in this succession brief reachable from a *different* sandbox?

Canonical cloud-workflow plan §4.9 states the disposability invariant: the
orchestrator must hold no state that isn't recoverable from git hosting + the
dispatch backend's API (or already delivered to the human). The spec then says
it twice more, because it is the step that actually failed in practice —

    "Every reference in the brief must point at a location the successor can
    actually reach — GitHub, the backend API, or 'handed to the human' — never a
    path in the outgoing sandbox. The successor is a *different* sandbox; a
    `/home/…` path from the old one is unreachable and gone the moment it is
    archived."

with the dogfood recorded beside it: "the first real succession pointed the
successor at a sandbox-local report path it could not reach; the report survived
only because it had already been surfaced to the human."

So this is a rule that has already been broken once, by an author who had just
written it down. That is the signature of something that belongs in code rather
than in a checklist, and it has a fully decidable output shape, so it gets
fixtures on both sides.

**Two assertions, paired on purpose.** `.claude/rules/general.md` § Consistency
rule 3 — "never ship a negative assertion alone", because a prohibition is
satisfiable by deletion:

  - NEGATIVE: the brief names no path in the outgoing sandbox.
  - POSITIVE: the brief carries the §4.9 wind-down step 4 re-address
    instruction, and points at least once at a durable location.

A brief that said nothing at all would pass the negative check perfectly. The
positive half is what makes an empty brief a failure instead of a clean pass —
and it guards the one instruction §4.9 says "cannot be left to inference,
because nothing about the successor's environment reveals that the channel is
stale."

**Deletion criterion (FB-0088):** delete when a brief can no longer name an
unreachable path — e.g. the backend delivers briefs by structured reference
rather than free text, or succession stops crossing sandboxes.

Stdlib only. No network. Python 3.7+.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

PREFIX = "[brief-check]"

# Absolute filesystem paths. Every one of these is sandbox-local: a successor
# runs in a different sandbox, so the path resolves to nothing (or, worse, to
# something else). `~` is included because it expands per-machine.
SANDBOX_PATH_RES = [
    (re.compile(r"(?<![\w/])/(?:home|Users)/[^\s`\"'|)\],]+"), "home directory of the outgoing sandbox"),
    (re.compile(r"(?<![\w/])/(?:tmp|var|private)/[^\s`\"'|)\],]+"), "scratch/temp path, deleted with the sandbox"),
    (re.compile(r"(?<![\w])~/[^\s`\"'|)\],]+"), "`~`-relative path, which expands per-machine"),
]

# Evidence that the brief points somewhere a different sandbox can reach.
#
# `dispatchBackend` / `listWorkers` / `re-derive` were here and were REMOVED, because
# the shipped brief template hardcodes "Re-derive: run the backend's listWorkers verb"
# into every brief it produces — so the positive half was satisfied by the INSTRUCTIONS
# rather than by any content, and a skeleton with every slot left unfilled passed clean.
# That is this repo's own Consistency rule 3 one turn further on: the rule says a
# NEGATIVE assertion alone passes in two opposite worlds, and the positive paired with
# it had the same defect — "the brief points somewhere reachable" or "the brief contains
# the word re-derive", indistinguishable. A runnable instruction is not a pointer.
DURABLE_RES = [
    (re.compile(r"https?://", re.I), "a URL"),
    (re.compile(r"\b(?:github|gh pr|gh issue|origin/|git ls-remote)\b", re.I), "GitHub / git remote state"),
    (re.compile(r"\b(?:delivered to the human|handed to the human|already surfaced|pasted to)\b", re.I),
     "content already delivered to the human"),
]

# §4.9 wind-down step 4. The successor's FIRST action is to broadcast its own
# session id to every live worker, because the outgoing seat's id dies with it
# and pings then go nowhere — a failure that is invisible from both ends.
READDRESS_RES = [
    re.compile(r"re-?address", re.I),
    re.compile(r"broadcast .{0,40}session", re.I),
    re.compile(r"\bping channel\b", re.I),
]


def check(text: str) -> dict:
    findings = []

    # NEGATIVE — no outgoing-sandbox paths.
    sandbox_hits = []
    for rx, why in SANDBOX_PATH_RES:
        for m in rx.finditer(text):
            sandbox_hits.append({"match": m.group(0), "why": why})
    if sandbox_hits:
        findings.append({
            "id": "sandbox-local-reference",
            "severity": "reject",
            "detail": (
                "the brief names path(s) in the outgoing sandbox, which the successor cannot reach "
                "(§4.9). Externalize each first — commit it if it is repo content, or hand its "
                "contents to the human if it is not — then reference the durable location."
            ),
            "hits": sandbox_hits,
        })

    # POSITIVE — points at something durable.
    durable = [why for rx, why in DURABLE_RES if rx.search(text)]
    if not durable:
        findings.append({
            "id": "no-durable-reference",
            "severity": "reject",
            "detail": (
                "the brief points at nothing a different sandbox can reach — no URL, no GitHub or "
                "git-remote state, no live backend query, no 'delivered to the human'. An empty or "
                "purely narrative brief passes the sandbox-path check trivially, which is why this "
                "positive half exists (general.md § Consistency rule 3)."
            ),
        })

    # POSITIVE — carries the re-address instruction.
    if not any(rx.search(text) for rx in READDRESS_RES):
        findings.append({
            "id": "missing-readdress-instruction",
            "severity": "reject",
            "detail": (
                "the brief does not instruct the successor to re-address the ping channel. §4.9 "
                "wind-down step 4 makes this the successor's FIRST action and says explicitly that "
                "it cannot be left to inference: every live worker is pinging the outgoing seat's "
                "session id, that id dies with the seat, and the resulting silence is "
                "indistinguishable from 'nothing needs me' (FB-0105)."
            ),
        })

    if not text.strip():
        findings.append({
            "id": "empty-brief",
            "severity": "reject",
            "detail": "the brief is empty. §4.9 allows a successor to boot with no brief at all, "
                      "but an empty brief that is nonetheless *delivered* is worse than none: it "
                      "reads as 'nothing is in flight'.",
        })

    return {
        "ok": not findings,
        "findings": findings,
        "durable_references": durable,
        "sandbox_reference_count": len(sandbox_hits),
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="brief-check.py", description=__doc__.split("\n")[0])
    ap.add_argument(
        "--brief-file", required=True,
        help="path to the rendered succession brief. A FILE, never argv — the brief is "
             "agent-composed prose and routinely contains backticks (field manual T6).",
    )
    args = ap.parse_args(argv)
    try:
        text = Path(args.brief_file).read_text(encoding="utf-8")
    except OSError as exc:
        print(
            f"{PREFIX} ⚠️ could not read --brief-file ({exc}). Treated as a REJECT: a brief that "
            f"cannot be read cannot be verified, and handing one over unchecked is the failure "
            f"§4.9 records.",
            file=sys.stderr,
        )
        print(json.dumps({"ok": False, "findings": [{"id": "unreadable-brief", "severity": "reject",
                                                     "detail": str(exc)}]}, indent=2))
        return 1
    result = check(text)
    print(json.dumps(result, indent=2))
    if not result["ok"]:
        print(
            f"{PREFIX} ⚠️ brief REJECTED ({len(result['findings'])} finding(s)). Do not hand this "
            f"over — fix it first.",
            file=sys.stderr,
        )
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
