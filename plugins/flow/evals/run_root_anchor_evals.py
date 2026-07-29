#!/usr/bin/env python3
"""Eval harness for the forked-skill root anchor (FB-0074).

The bug it pins: a `context: fork` skill inherits the SESSION cwd, which is not
necessarily the repo under review. Every relative read (`flow.config.json`, bare
`git diff`) then resolves against the wrong place — and, worst of all, silently:
"I could not locate the repo" rendered byte-identically to "there is nothing to
audit", so a source-touching PR passed a gate that never looked at it. Failure-open
on a gate whose entire job is to refuse exactly that (FB-0062).

Rather than restate the guard here — which would let the eval pass while the shipped
shell drifted — this harness EXTRACTS the guard from the live SKILL.md preambles and
runs it, so the fixture and the artifact cannot disagree.

Scenarios, per skill:
  1. non-repo cwd, no CLAUDE_PROJECT_DIR  ⇒ a DISTINCT unresolved line (the fix)
  2. real repo, no env                    ⇒ resolves + names the root (happy path)
  3. real repo cwd + conflicting CLAUDE_PROJECT_DIR ⇒ the CWD's git root wins
     (env-first would break git worktrees — see the inline note at the case)
  4. non-repo cwd, CLAUDE_PROJECT_DIR set ⇒ env is the fallback

Also asserts the distinctness invariant directly: the unresolved output must NOT be
confusable with the clean-skip output.

Stdlib only, POSIX sh. Run:
    python3 plugins/flow/evals/run_root_anchor_evals.py
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).parent
SKILLS = HERE.parent / "skills"

# The guard is the contiguous run of lines from the ROOT= assignment through the
# `fi` that closes its unresolved branch. Anchored on the assignment so a reworded
# comment doesn't break extraction.
_GUARD_RE = re.compile(
    r"^(ROOT=\$\(git rev-parse --show-toplevel.*?^fi$)",
    re.MULTILINE | re.DOTALL,
)

TARGETS = [
    ("audit-coverage", SKILLS / "audit-coverage" / "SKILL.md"),
    ("audit-skips", SKILLS / "audit-skips" / "SKILL.md"),
    # Same failure-open, and it gates plan approval: with no reference docs the critic
    # structurally cannot flag a spec violation, so it returns APPROVED.
    ("critique-plan", SKILLS / "critique-plan" / "SKILL.md"),
]

# Guards expected per skill — an exact count, not a floor. A floor (>= 2) lets a future
# third relative-reading preamble be added WITHOUT a guard and still pass.
EXPECTED_GUARDS = {"audit-coverage": 2, "audit-skips": 2, "critique-plan": 1}

_failures: list[str] = []


def check(name, ok, detail=""):
    if ok:
        print(f"  PASS  {name}")
    else:
        print(f"  FAIL  {name}\n        {detail}")
        _failures.append(name)


def extract_guards(path: Path) -> list:
    return _GUARD_RE.findall(path.read_text(encoding="utf-8"))


def run_guard(guard: str, cwd: Path, project_dir=None) -> str:
    env = dict(os.environ)
    env.pop("CLAUDE_PROJECT_DIR", None)
    if project_dir is not None:
        env["CLAUDE_PROJECT_DIR"] = str(project_dir)
    proc = subprocess.run(
        ["sh", "-c", guard], cwd=str(cwd), env=env,
        capture_output=True, text=True, timeout=20,
    )
    return (proc.stdout + proc.stderr).strip()


def git_repo(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q"], cwd=path, capture_output=True)
    (path / "app.py").write_text("x = 1\n", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=path, capture_output=True)
    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "init"],
        cwd=path, capture_output=True,
    )
    return path


UNRESOLVED_TOKENS = ("ROOT-UNRESOLVED", "root_error")


def main() -> int:
    print("root-anchor evals (FB-0074)")

    real_repo = Path(__file__).resolve().parents[3]

    with tempfile.TemporaryDirectory() as td:
        nonrepo = Path(td) / "nonrepo"
        nonrepo.mkdir()
        foreign = git_repo(Path(td) / "foreign")

        for skill, path in TARGETS:
            if not path.is_file():
                check(f"{skill}: SKILL.md present", False, f"missing {path}")
                continue

            guards = extract_guards(path)
            want = EXPECTED_GUARDS[skill]
            check(f"{skill}: exactly {want} root guard(s), one per relative-reading preamble",
                  len(guards) == want,
                  f"found {len(guards)}, expected {want} — a preamble was added or lost a guard")
            if not guards:
                continue

            # Every guard is executed, not just the first: they emit DIFFERENT payloads
            # (JSON warnings / JSON root_error / bracketed text), so the untested branch
            # is exactly the one whose divergence could be wrong.
            for gi, g in enumerate(guards):

                tag = f"{skill}[guard {gi + 1}]"

                # 1. THE BUG: non-repo cwd must be distinctly unresolved, not a clean skip.
                out = run_guard(g, nonrepo)
                check(f"{tag}: non-repo cwd ⇒ distinct unresolved signal",
                      any(t in out for t in UNRESOLVED_TOKENS), f"got: {out!r}")
                check(f"{tag}: unresolved output is NOT the clean-skip line",
                      "SKIPPED" not in out and '"note"' not in out, f"got: {out!r}")

                # 2. happy path unchanged.
                out = run_guard(g, real_repo)
                check(f"{tag}: real repo ⇒ resolves (no unresolved signal)",
                      not any(t in out for t in UNRESOLVED_TOKENS), f"got: {out!r}")

                # 3. PRECEDENCE — cwd's git root WINS over CLAUDE_PROJECT_DIR.
                #    This repo's own loop runs from linked worktrees: a session started
                #    in the parent repo exports CLAUDE_PROJECT_DIR pointing THERE, while
                #    the PR lives in a worktree on a different branch. Env-first would
                #    audit the parent tree and see none of the changes — the same
                #    failure-open this guard exists to close. Pinned so a future
                #    "env is more authoritative" refactor can't silently reintroduce it.
                out = run_guard(g, real_repo, project_dir=foreign)
                check(f"{tag}: cwd git root WINS over a conflicting CLAUDE_PROJECT_DIR",
                      str(foreign) not in out, f"env leaked into the resolved root: {out!r}")

                # 4. env is the FALLBACK — used only when cwd is not inside a repo.
                out = run_guard(g, nonrepo, project_dir=real_repo)
                check(f"{tag}: CLAUDE_PROJECT_DIR resolves from a non-repo cwd (fallback)",
                      not any(t in out for t in UNRESOLVED_TOKENS), f"got: {out!r}")

    # The routing half: an unresolved root is worthless unless the prose refuses to
    # collapse it into the clean skip.
    cov = (SKILLS / "audit-coverage" / "SKILL.md").read_text(encoding="utf-8")
    check("audit-coverage prose: ROOT-UNRESOLVED is explicitly NOT the skip case",
          "ROOT-UNRESOLVED` is NOT the skip case" in cov or
          "ROOT-UNRESOLVED** is NOT the skip case" in cov,
          "the skill must tell the agent not to emit the SKIPPED line on an unresolved root")

    skips = (SKILLS / "audit-skips" / "SKILL.md").read_text(encoding="utf-8")
    check("audit-skips prose: root_error routed like engine_error",
          "root_error" in skips and "not a clean pass" in skips,
          "root_error must route to the draft manifest, never a silent proceed")

    ship = (SKILLS / "ship" / "SKILL.md").read_text(encoding="utf-8")
    check("ship Step 2a: routes root_error to decision-required",
          "root_error" in ship and "decision-required" in ship,
          "ship must treat an unresolved-root audit as decision-required, never a clean pass")

    print()
    if _failures:
        print(f"FAILED: {len(_failures)} eval(s): {', '.join(_failures)}")
        return 1
    print("All root-anchor evals passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
