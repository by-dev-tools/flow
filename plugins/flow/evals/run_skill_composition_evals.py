#!/usr/bin/env python3
"""Eval harness for skill-composition-lint.py (FB-0074).

The bug it pins: a SKILL.md instructing `Skill("flow:land")` where `land` sets
`disable-model-invocation: true`. That flag blocks *programmatic* invocation, so the
call is rejected at runtime and the composition silently degrades to its fallback on
every run — with the two halves of the contract (call site, flag) in different files,
nothing could catch it.

Two layers:
  1. Synthetic fixtures built on disk — the violation, the clean case, the prose-only
     false-positive case, unknown targets, self-calls, absent-flag default.
  2. A live assertion over flow's OWN skills directory, so the repo can never
     reintroduce the shape the lint exists to forbid.

Stdlib only. No network. Run:
    python3 plugins/flow/evals/run_skill_composition_evals.py
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).parent
SCRIPT = HERE.parent / "skills" / "doctor" / "lib" / "skill-composition-lint.py"
FLOW_SKILLS = HERE.parent / "skills"

_failures: list[str] = []


def expect(name, got, want, out=""):
    if got == want:
        print(f"  PASS  {name}")
    else:
        print(f"  FAIL  {name}: exit {got}, wanted {want}\n        output: {out.strip()}")
        _failures.append(name)


def lint(path) -> tuple:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), str(path)], capture_output=True, text=True
    )
    return proc.returncode, proc.stdout + proc.stderr


def make_skill(root: Path, name: str, disabled: bool, body: str = "") -> None:
    d = root / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "SKILL.md").write_text(
        f"---\nname: {name}\n"
        f"disable-model-invocation: {'true' if disabled else 'false'}\n"
        f"---\n\n{body}\n",
        encoding="utf-8",
    )


FENCED = '```\nSkill("{target}")\n```'


def main() -> int:
    print("skill-composition-lint evals (FB-0074)")

    if not SCRIPT.is_file():
        print(f"  FAIL  lint script missing at {SCRIPT}")
        return 1

    with tempfile.TemporaryDirectory() as td:
        # --- 1. the reported violation ---------------------------------------
        root = Path(td) / "violation"
        make_skill(root, "land", disabled=True)
        make_skill(root, "post-merge", disabled=True, body=FENCED.format(target="flow:land"))
        rc, out = lint(root)
        expect("caller invokes a disable-model-invocation skill ⇒ FAIL", rc, 1, out)
        expect(
            "violation message names the callee",
            0 if "'land' sets disable-model-invocation: true" in out else 1, 0, out)

        # --- 2. clean: callee is model-invocable ------------------------------
        root = Path(td) / "clean"
        make_skill(root, "verify-build", disabled=False)
        make_skill(root, "ship", disabled=False, body=FENCED.format(target="flow:verify-build"))
        rc, out = lint(root)
        expect("caller invokes a model-invocable skill ⇒ PASS", rc, 0, out)

        # --- 3. the false positive that bit this lint on its first run --------
        # Prose *documenting* the anti-pattern uses the literal call syntax in inline
        # backticks. Only fenced blocks are executable; flagging prose would make the
        # lint fail on the very docs that warn against the bug.
        root = Path(td) / "prose"
        make_skill(root, "land", disabled=True)
        make_skill(
            root, "post-merge", disabled=True,
            body='Do NOT emit `Skill("flow:land")` — it is rejected at runtime.')
        rc, out = lint(root)
        expect("inline-backtick prose mention is NOT a call ⇒ PASS", rc, 0, out)

        # --- 4. unknown target = cross-plugin call, not a violation -----------
        root = Path(td) / "unknown"
        make_skill(root, "verify-build", disabled=False, body=FENCED.format(target="verify"))
        rc, out = lint(root)
        expect("call to a skill outside the scanned dir ⇒ PASS (UNKNOWN, not FAIL)", rc, 0, out)
        expect("unknown target is still reported",
               0 if "UNKNOWN" in out else 1, 0, out)

        # --- 5. self-call is not a violation ---------------------------------
        root = Path(td) / "selfcall"
        make_skill(root, "ship", disabled=True, body=FENCED.format(target="flow:ship"))
        rc, out = lint(root)
        expect("self-referential call ⇒ PASS (a skill documenting its own name)", rc, 0, out)

        # --- 6. absent flag defaults to false (Claude Code's documented default)
        root = Path(td) / "absentflag"
        (root / "callee").mkdir(parents=True)
        (root / "callee" / "SKILL.md").write_text(
            "---\nname: callee\n---\n\nno flag declared\n", encoding="utf-8")
        make_skill(root, "caller", disabled=False, body=FENCED.format(target="callee"))
        rc, out = lint(root)
        expect("callee with no flag ⇒ PASS (default is invocable)", rc, 0, out)

        # --- 7. namespace-prefixed and bare targets resolve alike -------------
        root = Path(td) / "bare"
        make_skill(root, "land", disabled=True)
        make_skill(root, "caller", disabled=False, body=FENCED.format(target="land"))
        rc, out = lint(root)
        expect("bare (unprefixed) target still resolves ⇒ FAIL", rc, 1, out)

        # --- 8. empty dir degrades gracefully, never a crash ------------------
        root = Path(td) / "empty"
        root.mkdir()
        rc, out = lint(root)
        expect("empty skills dir ⇒ exit 0 with a note (no crash)", rc, 0, out)

        rc, out = lint(Path(td) / "does-not-exist")
        expect("nonexistent dir ⇒ exit 2 (never a false PASS)", rc, 2, out)

    # --- 9. live: flow's own skills must stay clean --------------------------
    rc, out = lint(FLOW_SKILLS)
    expect("flow's own skills/ carry no disabled-target Skill() call", rc, 0, out)

    print()
    if _failures:
        print(f"FAILED: {len(_failures)} eval(s): {', '.join(_failures)}")
        return 1
    print("All skill-composition evals passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
