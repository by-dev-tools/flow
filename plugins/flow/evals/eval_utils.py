#!/usr/bin/env python3
"""Shared helpers for eval harnesses that need to extract and execute a SKILL.md's
fenced shell blocks (as opposed to grepping its prose). Hoisted out of
`run_role_slot_evals.py` when `run_merge_status_evals.py` needed the identical
helper — two eval harnesses independently defining the same parser is the exact
FB-0010 fan-out class this repo's own consistency rule names, so it gets one home
like every other shared predicate in this codebase (`_lint()` / `skill-composition-lint.py`,
`slot_count_scan.py`).

Also home to `git_repo()` / `commit()`, the throwaway-repo builders. Those are the
HOIST TARGET for a debt this repo has recorded rather than paid: five eval harnesses each
define their own temp-git-repo helper (`run_coverage_source_mode_evals.py` added the fifth
and said so in its PR rather than quietly fanning out a sixth). Deleting those five copies
touches four harnesses outside any one PR's scope, so the copies stay for now -- but new
harnesses import from here, so the eventual hoist is a deletion instead of a rewrite.

Stdlib only.
"""

from __future__ import annotations

import re
import subprocess


def rest_from(text, heading_substr):
    """Slice `text` from `heading_substr` onward, or None if absent."""
    idx = text.find(heading_substr)
    return None if idx == -1 else text[idx:]


def fenced_block(text, heading_substr):
    """The first ```sh fenced block after `heading_substr` — the executable shell,
    not the surrounding prose. Used to actually RUN a doctor check rather than grep
    its text (a check whose text merely mentions the right thing is not the same as
    a check that DOES the right thing)."""
    rest = rest_from(text, heading_substr)
    if rest is None:
        return None
    m = re.search(r"```sh\n(.*?)\n```", rest, re.DOTALL)
    return m.group(1) if m else None


def git_repo(path, files, branch="main"):
    """A throwaway git repo with one commit. Returns `path`."""
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", "-b", branch], cwd=path, capture_output=True)
    return commit(path, files, "init")


def commit(path, files, message):
    """Write `files` into `path` and commit them. Returns `path`.

    Separate from `git_repo` because a single-commit repo cannot exercise anything that
    depends on commit ORDER -- and the ordering of plan edits against source edits is
    exactly what `change-inventory.py`'s POST-PLAN tier is computed from. A helper that
    can only build one commit forces a harness to either shell out by hand or skip the
    case, and skipping it is how the tier would have shipped unmeasured.
    """
    for rel, body in files.items():
        f = path / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(body, encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=path, capture_output=True)
    subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t",
                    "commit", "-qm", message], cwd=path, capture_output=True)
    return path
