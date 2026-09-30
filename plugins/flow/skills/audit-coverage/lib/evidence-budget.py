#!/usr/bin/env python3
"""Allocate the evidence cap across the changed files, instead of `head -c` on a concatenation.

WHY THIS EXISTS (CV1)
---------------------
The diff block used to build one string of every file's diff, in `sort -u` order, and cut it
with `head -c $CAP`. Two consequences, both measured, neither stated anywhere:

  * Files late in the alphabet can be **entirely invisible**. On #158's post-fix shape
    (15 files, 103,785 B against a 60,000 B cap) `review-brief/SKILL.md` and
    `workflow-help/SKILL.md` contributed ZERO bytes -- not because they were unimportant but
    because `r` and `w` sort after `p`. Coverage decided by filename.
  * The single `WEAKENED · TRUNCATED` line says the cap was hit. It does not say WHICH files
    were cut, so a reviewer cannot tell a fully-read file from an unread one, and the
    "nothing there vs I could not see" distinction collapses inside the evidence itself.

WATER-FILLING, and why not a flat per-file cap. A flat `cap/N` wastes the unused share of every
small file: on #158, twelve of fifteen files are under a 4,000 B share and together leave
~24 KB unclaimed, which is exactly the budget the three large files need. So: give every file
its full size if it fits within the current fair share, return the remainder to the pool, and
repeat; whatever is still over-share at the end splits what is left, equally. That is
max-min fairness -- no file is starved to feed a larger one, and no budget is left on the table.

The allocation is deterministic and order-independent: the same file set and cap always produce
the same per-file budget regardless of `sort` order, which is the property the old form lacked.

Exit codes: 0 always (this shapes evidence, it never decides a verdict). Diagnostics that MUST
reach the reviewer are printed as `[audit-coverage]` control lines on stdout, because that is
the channel the prose rule reads.
"""

from __future__ import annotations

import argparse
import subprocess
import sys


# One `git diff` per ARM, not per file. The shell loop this replaced spawned 2 per file, and the
# rewrite into Python kept that shape out of habit; measured on a 26-file diff, 52 spawns = 229 ms
# against 2 spawns = 35 ms, and a 200-file PR goes from ~1.8 s to ~35 ms. Chunked because
# `git diff` has no `--pathspec-from-file`, so the path list rides in argv and must respect
# ARG_MAX. Output is asserted byte-identical to the per-file concatenation by the evals.
_CHUNK = 400


def _diff_all(base: str, paths: list) -> dict:
    """{path: diff bytes} for both arms, in `paths` order, batched."""
    out = {f: b"" for f in paths}
    for arm in ([f"{base}..HEAD", "--"], ["HEAD", "--"]):
        for i in range(0, len(paths), _CHUNK):
            chunk = paths[i:i + _CHUNK]
            try:
                p = subprocess.run(["git", "diff", *arm, *chunk],
                                   capture_output=True, timeout=120)
            except (OSError, subprocess.SubprocessError):
                continue
            if p.returncode != 0:
                continue
            # Split on the per-file header git emits, and key each part back by its `b/<path>`.
            # A path absent from the output simply contributes nothing, exactly as before.
            for part in p.stdout.split(b"\ndiff --git "):
                if not part:
                    continue
                if not part.startswith(b"diff --git "):
                    part = b"diff --git " + part
                head = part.split(b"\n", 1)[0]
                for f in chunk:
                    if head.endswith(b" b/" + f.encode()):
                        out[f] += part if part.endswith(b"\n") else part + b"\n"
                        break
    return out


def allocate(sizes: dict, cap: int) -> dict:
    """Max-min fair allocation of `cap` bytes across `sizes`. Returns {path: budget}."""
    alloc, pending, remaining = {}, dict(sizes), cap
    while pending:
        share = remaining // len(pending)
        # Files that fit inside the current fair share take exactly what they need and free
        # the rest. If none fits, everyone left is over-share and splits the remainder.
        small = [f for f, s in pending.items() if s <= share]
        if not small:
            for f in pending:
                alloc[f] = share
            break
        for f in small:
            alloc[f] = pending[f]
            remaining -= pending[f]
            del pending[f]
    return alloc


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base", required=True)
    ap.add_argument("--cap", type=int, required=True)
    args = ap.parse_args(argv)

    files = [ln.strip() for ln in sys.stdin.read().splitlines() if ln.strip()]
    if not files:
        return 0
    blobs = _diff_all(args.base, files)
    sizes = {f: len(b) for f, b in blobs.items()}
    total = sum(sizes.values())

    if total <= args.cap:
        # UNDER THE CAP THE OUTPUT IS BYTE-IDENTICAL TO THE OLD FORM. The common case must not
        # be reflowed by a change that exists for the uncommon one -- otherwise every eval that
        # pins the ordinary evidence shape churns for no behavioural reason.
        sys.stdout.write("".join(blobs[f].decode("utf-8", "replace") for f in files))
        return 0

    alloc = allocate(sizes, args.cap)
    cut = []
    for f in files:
        budget = alloc.get(f, 0)
        if sizes[f] > budget:
            cut.append((f, sizes[f], budget))
        sys.stdout.write(blobs[f][:budget].decode("utf-8", "replace"))
        if sizes[f] > budget:
            # Marked AT the cut, not only summarised at the end: a reviewer reading a file's
            # hunks needs to know the file stops here, at the point where it stops.
            sys.stdout.write(
                f"\n[audit-coverage] ... {f} truncated at {budget} of {sizes[f]} bytes ...\n")
    # ONE control line naming EVERY cut file. The old single line said the cap was hit and left
    # the reviewer to guess which evidence was partial.
    names = ", ".join(f"{f} ({b} of {s} B)" for f, s, b in cut)
    print(f"[audit-coverage] WEAKENED · TRUNCATED — the {args.cap}-byte evidence cap was shared "
          f"across {len(files)} file(s); {len(cut)} were cut: {names}. Every file contributed at "
          f"least its fair share, so none is silently absent — but behavior past each cut was "
          f"NOT read. A clean result here is PARTIAL for those files: say so, and recommend "
          f"splitting the PR or auditing the remainder.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
