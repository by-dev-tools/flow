#!/usr/bin/env python3
"""Assert every point-in-time doc is indexed in dev-docs/README.md and carries a status line.

Why this exists (FB-0085): `dev-docs/README.md` was added because point-in-time docs under
`research/` and `handoffs/` were invisible to anything orienting from `CLAUDE.md`. But an index
maintained by discipline is the same shape as the bug that motivated it — a rule that is
load-bearing in prose and mechanical nowhere. On the PR that introduced the index, three
successive rebases each pulled in docs the index did not list (9 -> 14 -> 15), caught only
because a human re-ran the check by hand every time.

Two assertions, mirroring the "every eval harness is wired into this workflow (and vice versa)"
meta-check already in .github/workflows/ci.yml:

  1. INDEXED   — every doc under the scanned dirs is referenced by filename in README.md.
  2. STATUS    — every such doc carries a status-ish marker in its header (first HEADER_LINES).

Deliberately NOT asserted: that the status text is *accurate*. No script can check that; it is
the human's job, and pretending otherwise would be the failure-open this repo keeps fixing.

Stdlib only (repo rule). Exit 0 = clean, 1 = violations found, 2 = the check itself broke.
"""

import os
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX = os.path.join(REPO_ROOT, "dev-docs", "README.md")

# Dirs whose *.md are point-in-time docs. `research/` at the repo root is a second, deliberately
# quarantined location (#104) — indexed so it is findable, though not governed by README's Rules.
SCAN_DIRS = [
    os.path.join("dev-docs", "research"),
    os.path.join("dev-docs", "handoffs"),
    "research",
]

# A header must carry one of these. Broad on purpose: the point is that SOMETHING declares the
# doc's current standing, not that it uses one blessed word.
STATUS_MARKERS = re.compile(
    r"status|superseded|historical record|foreign repo|parked|preserved|do not build",
    re.IGNORECASE,
)
HEADER_LINES = 12


def fail(msg):
    print(f"[dev-docs-index] ERROR: {msg}", file=sys.stderr)
    sys.exit(2)


def main():
    if not os.path.isfile(INDEX):
        fail(f"index not found at {INDEX}")
    try:
        index_text = open(INDEX, encoding="utf-8").read()
    except OSError as e:
        fail(f"cannot read {INDEX}: {e}")

    docs = []
    for rel in SCAN_DIRS:
        d = os.path.join(REPO_ROOT, rel)
        if not os.path.isdir(d):
            continue  # a scanned dir may legitimately not exist yet
        for name in sorted(os.listdir(d)):
            if name.endswith(".md") and name != "README.md":
                docs.append((rel, name, os.path.join(d, name)))

    if not docs:
        print("[dev-docs-index] no point-in-time docs found — nothing to check.")
        return 0

    unindexed, statusless, unreadable = [], [], []
    for rel, name, path in docs:
        if name not in index_text:
            unindexed.append(f"{rel}/{name}")
        try:
            with open(path, encoding="utf-8") as fh:
                header = "".join(next(fh, "") for _ in range(HEADER_LINES))
        except OSError as e:
            unreadable.append(f"{rel}/{name} ({e})")
            continue
        if not STATUS_MARKERS.search(header):
            statusless.append(f"{rel}/{name}")

    if unreadable:
        fail("unreadable doc(s): " + ", ".join(unreadable))

    if unindexed or statusless:
        print("[dev-docs-index] FAIL", file=sys.stderr)
        if unindexed:
            print(
                "\n  Not listed in dev-docs/README.md (an unindexed point-in-time doc is a buried doc):",
                file=sys.stderr,
            )
            for d in unindexed:
                print(f"    - {d}", file=sys.stderr)
            print(
                "  Fix: add a row to the matching table in dev-docs/README.md, in THIS PR.",
                file=sys.stderr,
            )
        if statusless:
            print(
                f"\n  No status marker in the first {HEADER_LINES} lines (a stale 'in progress' is"
                " indistinguishable from a current one):",
                file=sys.stderr,
            )
            for d in statusless:
                print(f"    - {d}", file=sys.stderr)
            print(
                "  Fix: add a `**Status:**` line to the doc header stating what is true NOW.",
                file=sys.stderr,
            )
        print(
            "\n  See dev-docs/README.md § Rules. Do not delete a doc to satisfy this check.",
            file=sys.stderr,
        )
        return 1

    print(f"[dev-docs-index] PASS — {len(docs)} point-in-time docs indexed and status-lined.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
