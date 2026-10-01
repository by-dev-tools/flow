#!/usr/bin/env python3
"""Render the paired prose discriminator for /flow:audit-coverage's PRECISION axis.

Recall asks "did it find the gaps?"; this asks the opposite question, and the CV1 follow-up is
the PR that made it answerable. Until then the reviewer was told doc changes are not behaviours,
so a prose-only diff returned `No issues flagged.` for a reason that had nothing to do with
judgment -- the suppression fired before any discrimination happened. CV1's history entry read
that silence as precision held; it was not evidence either way. With the DOC-SURFACE exemption
live, the suppression no longer answers for the reviewer, so silence on a wording-only change is
a judgment and worth measuring.

TWO ARMS, ONE VARIABLE: whether the prose change ADDS A RULE or only rewords. Same file, same
plan, same criteria, same render path, same cap -- so a difference in verdict is attributable to
the change under test. Both arms land on the PLAN-PREDATES-BRANCH tier, which tells the reviewer
no declared criterion CAN cover anything, i.e. the arms are rendered under the condition most
biased TOWARD flagging. A clean negative there is the strong form of the result.

The positive arm is not decoration. A negative arm alone cannot distinguish a reviewer that is
discriminating from one that has simply stopped looking at prose: both return "no issues". The
pair is the instrument (general.md item 4 -- validate on a known positive before trusting a
negative).

Usage:
    python3 tools/coverage-recall/precision_pair.py --out tools/coverage-recall/runs/precision

Writes prompt.negative.md and prompt.positive.md. Hand each to an independent reviewer spawn and
score by hand: the negative must return `No issues flagged.`, the positive must flag the added
rule. Dev tooling; needs a live reviewer, so it cannot be CI-wired.
"""
import argparse
import difflib
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools" / "coverage-recall"))
sys.path.insert(0, str(REPO / "plugins" / "flow" / "evals"))
import recall
from eval_utils import git_repo, commit

BASE_SKILL = """---
name: throttle
description: Rate-limit outbound requests.
---

# /app:throttle

Limits how fast the worker issues outbound requests, so a burst of queued jobs cannot
exhaust a downstream API's quota.

## How it decides

Read `throttle.config.json` from the repo root. The `perMinute` slot caps requests per
minute; it defaults to 60 when the slot is absent.

A request that would exceed the cap waits until the next window opens. The worker logs
one line per wait, naming the request id and the remaining window in seconds, so an
operator can tell a throttled run from a stalled one.

## What it does not do

It does not retry a failed request. A request that fails after being admitted is the
caller's problem; this skill only decides when a request may start.

## Exit codes

- `0` -- every request was admitted, with or without waiting.
- `1` -- the config file exists but could not be parsed.
"""

# NEGATIVE ARM: wording only. Two sentences reflowed, one typo-grade rewrite, one heading
# reworded. Nothing a user could observe changes: same cap, same default, same log line, same
# exit codes.
WORDING_ONLY = BASE_SKILL.replace(
    "Limits how fast the worker issues outbound requests, so a burst of queued jobs cannot\n"
    "exhaust a downstream API's quota.",
    "Limits the rate at which the worker issues outbound requests, so that a burst of\nqueued jobs cannot exhaust a downstream API's quota.",
).replace("## How it decides", "## How the decision is made").replace(
    "A request that would exceed the cap waits until the next window opens.",
    "A request that would take the worker over the cap waits for the next window to open.",
)

# POSITIVE ARM: the same wording changes PLUS one added rule -- an observable new behaviour
# (a new refusal, a new exit code, a new output line) that no criterion declares.
ADDED_RULE = WORDING_ONLY.replace(
    "## Exit codes",
    "If `perMinute` is set to 0, the skill refuses to run: it prints\n"
    "`throttle: REFUSED — perMinute is 0, which would admit nothing` and exits 3 without\n"
    "issuing any request. A zero cap is almost always a mis-edit rather than an intent to\n"
    "halt the worker, and silently admitting nothing looks identical to a hung queue.\n\n"
    "## Exit codes",
).replace(
    "- `1` -- the config file exists but could not be parsed.",
    "- `1` -- the config file exists but could not be parsed.\n- `3` -- `perMinute` is 0.",
)

PLAN = """# Plan

**Spec-walk:**

- [ ] `perMinute` absent from the config falls back to 60 requests per minute
      *Pinned by:* `test_default_cap` in `tests/test_throttle.py`
- [ ] a request that would exceed the cap waits for the next window rather than failing
      *Pinned by:* `test_waits_for_window`
- [ ] each wait emits one log line naming the request id and the remaining seconds
      *Pinned by:* `test_wait_log_shape`
- [ ] an unparseable config file exits 1
      *Pinned by:* `test_bad_config_exit_1`

**Confidence verdicts:**

- [ ] HIGH — the cap arithmetic is covered by the three tests above
"""

CFG = ('{"defaultBranch": "main", "planPath": "plan.md", '
       '"behaviorBearingDocPatterns": "(^|/)(skills|agents|rules)/.*[.]md$"}')


def build(arm: str, new_skill: str, out: Path, scratch: Path):
    work = scratch / arm
    if work.exists():
        shutil.rmtree(work)
    repo = git_repo(work, {
        "skills/throttle/SKILL.md": BASE_SKILL,
        "plan.md": PLAN,
        "flow.config.json": CFG,
        "worker.py": "def run():\n    return 0\n",
    })
    for c in (["git", "remote", "add", "origin", str(repo)],
              ["git", "update-ref", "refs/remotes/origin/main", "main"],
              ["git", "checkout", "-q", "-b", "work"]):
        subprocess.run(c, cwd=str(repo), capture_output=True)
    commit(repo, {"skills/throttle/SKILL.md": new_skill}, arm)
    body = recall.render("pr159", False, Path(repo))   # case only supplies `argument` (None)
    out.write_text(body, encoding="utf-8")
    print(f"{arm:14s} -> {out} ({len(body)} bytes)")
    return body


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, help="directory to write the two prompts into")
    ap.add_argument("--scratch", default=tempfile.mkdtemp(prefix="precision-pair-"),
                    help="where the throwaway git repos are built")
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    scratch = Path(a.scratch)
    n = build("negative", WORDING_ONLY, out / "prompt.negative.md", scratch)
    p = build("positive", ADDED_RULE, out / "prompt.positive.md", scratch)

    # ASSERT THE ARMS DIFFER BY ONE THING. A pair whose prompts drifted in some other way
    # measures that drift instead, and the difference is 22 lines of which 20 are the added
    # rule plus the mechanical consequences (repo path, blob index, hunk count). Checked here
    # rather than by eye, because "same except for X" is exactly the claim a reader cannot
    # verify from the output.
    diff = [l for l in difflib.unified_diff(n.splitlines(), p.splitlines(), lineterm="", n=0)
            if l[:1] in "+-" and l[:3] not in ("+++", "---")]
    rule_lines = [l for l in diff if "perMinute is 0" in l or "exits 3" in l
                  or "REFUSED" in l or "mis-edit" in l or "halt the worker" in l]
    if not rule_lines:
        raise SystemExit("[precision-pair] REFUSING: the positive arm's added rule is not in "
                         "the rendered difference. The evidence cap or the source filter dropped "
                         "it, so the positive arm cannot test anything.")
    for label, b in (("negative", n), ("positive", p)):
        if "DOC-SURFACE" not in b:
            raise SystemExit(f"[precision-pair] REFUSING: the {label} arm carries no DOC-SURFACE "
                             f"line, so the reviewer will apply the doc suppression and both arms "
                             f"will return 'no issues' for a reason that is not judgment.")
        print(f"  {label}: {len(b)} bytes, DOC-SURFACE present, "
              f"SKILL.md in evidence={'skills/throttle/SKILL.md' in b}")
    print(f"  rendered difference: {len(diff)} lines, {len(rule_lines)} of them the added rule")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
