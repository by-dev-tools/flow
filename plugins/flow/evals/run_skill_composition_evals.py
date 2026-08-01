#!/usr/bin/env python3
"""Eval harness for skill-composition-lint.py (FB-0074).

The bug it pins: a SKILL.md instructing `Skill("flow:land")` where `land` sets
`disable-model-invocation: true`. That flag blocks *programmatic* invocation, so the
call is rejected at runtime and the composition silently degrades to its fallback on
every run — with the two halves of the contract (call site, flag) in different files,
nothing could catch it.

Three layers:
  1. Synthetic fixtures built on disk — the violation, the clean case, the prose-only
     false-positive case, unknown targets, self-calls, absent-flag default.
  2. A live assertion over flow's OWN skills directory, so the repo can never
     reintroduce the shape the lint exists to forbid.
  3. Live assertions that the post-merge → land composition is INTACT (FB-0077).
     Layer 2 passes two opposite ways — the composition is legal, or the call was
     deleted — and the lint cannot tell them apart. That ambiguity is how FB-0074
     "fixed" this defect by conceding it, leaving /flow:post-merge a reminder to run
     another command. Layer 3 pins the composition positively from both ends.

Stdlib only. No network. Run:
    python3 plugins/flow/evals/run_skill_composition_evals.py
"""

from __future__ import annotations

import importlib.util
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).parent
SCRIPT = HERE.parent / "skills" / "doctor" / "lib" / "skill-composition-lint.py"
FLOW_SKILLS = HERE.parent / "skills"

_failures: list[str] = []
_MODULE = None


def _lint_module():
    """Import the lint as a module so §10 can reuse its parser.

    The filename is hyphenated, so it is not importable by name — load it by path.
    Cached: scan() re-reads every SKILL.md, and §10 calls this more than once.
    """
    global _MODULE
    if _MODULE is None:
        spec = importlib.util.spec_from_file_location("skill_composition_lint", SCRIPT)
        _MODULE = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_MODULE)
    return _MODULE


def _frontmatter_of(path: Path) -> str:
    return _lint_module()._frontmatter(path.read_text(encoding="utf-8"))


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

        # --- 3b. fence-delimiter variants (self-found false NEGATIVES) --------
        # The dangerous direction: a real call the lint fails to see. The first
        # implementation toggled on "```" only, so a CommonMark `~~~` fence hid an
        # executable call completely. Each variant below must still FAIL.
        for label, body in [
            ("tilde", '~~~\nSkill("flow:land")\n~~~'),
            ("info-string", '```sh\nSkill("flow:land")\n```'),
            ("indented", '  ```\n  Skill("flow:land")\n  ```'),
            # A ``` line inside a ~~~ block must not close it early — tracking the
            # opening delimiter, not a boolean, is what makes this hold.
            ("nested-delims", '~~~\nnot a fence: ```\nSkill("flow:land")\n~~~'),
        ]:
            root = Path(td) / f"fence-{label}"
            make_skill(root, "land", disabled=True)
            make_skill(root, "post-merge", disabled=True, body=body)
            rc, out = lint(root)
            expect(f"fence variant '{label}' still catches the call ⇒ FAIL", rc, 1, out)

        # --- 3c. fail-open paths must WARN, never pass silently ---------------
        # Both of these previously defaulted to "nothing to see", which inverts the
        # lint's job without saying so (FB-0010 silent-skip class).
        root = Path(td) / "unclosed-fence"
        make_skill(root, "land", disabled=True)
        make_skill(root, "post-merge", disabled=True,
                   body='```\nunclosed fence\n\nSkill("flow:land")')
        rc, out = lint(root)
        expect("unclosed fence ⇒ WARN emitted", 0 if "WARN" in out and "unclosed" in out else 1, 0, out)

        root = Path(td) / "no-frontmatter"
        (root / "x").mkdir(parents=True)
        (root / "x" / "SKILL.md").write_text("no frontmatter at all\n", encoding="utf-8")
        rc, out = lint(root)
        expect("unparseable frontmatter ⇒ WARN emitted (not a silent 'invocable')",
               0 if "WARN" in out and "frontmatter" in out else 1, 0, out)

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

    # --- 10. live: the post-merge → land composition is INTACT (FB-0077) -----
    # The lint above passes two ways: the composition is legal, or the call was
    # deleted. Those are opposite outcomes and it cannot tell them apart — which is
    # how FB-0074 "fixed" this defect by conceding it, leaving /flow:post-merge a
    # reminder to run another command. So assert the composition positively, from
    # both ends. Deleting either half must fail CI, not quietly satisfy the lint.
    # Reuse the lint's OWN parser rather than hand-rolling a second one here. A
    # duplicate fence/frontmatter parser in the eval could drift from the one under
    # test and start agreeing with itself — the FB-0010 fan-out class this very lint
    # exists to catch.
    table = _lint_module().scan(FLOW_SKILLS)
    bare = _lint_module()._bare

    expect(
        "land is model-invocable (FB-0077) — the flag is redundant with its §1a merged-PR gate",
        0 if table["skills"].get("land", {}).get("disabled") is False else 1, 0,
        f"land entry: {table['skills'].get('land')}")

    # Declared explicitly, not merely absent: an absent flag also parses as invocable,
    # so a deletion would satisfy the check above while losing the deliberate
    # declaration that records the FB-0077 decision.
    land_fm = _frontmatter_of(FLOW_SKILLS / "land" / "SKILL.md")
    expect(
        "land declares the flag explicitly rather than relying on the default",
        0 if re.search(r"^disable-model-invocation:\s*false\s*$", land_fm, re.M) else 1,
        0, land_fm)

    pm_calls = [c for c in table["calls"]
                if c["caller"] == "post-merge" and bare(c["target"]) == "land"]
    expect(
        'post-merge §3 emits a fenced Skill("flow:land") call — the composition, not a hand-off',
        0 if pm_calls else 1, 0,
        "no fenced Skill() call naming land found in post-merge/SKILL.md")

    # post-merge must itself stay human-gated: it is the human gate above land now
    # that land's own flag is gone. Losing BOTH flags is the state nothing guards.
    expect(
        "post-merge stays disable-model-invocation: true — the human gate above land",
        0 if table["skills"].get("post-merge", {}).get("disabled") is True else 1, 0,
        f"post-merge entry: {table['skills'].get('post-merge')}")

    # land's §1a gate is what makes clearing the flag safe. If it ever stops refusing
    # unmerged PRs, the flag's removal becomes unsafe retroactively.
    land_text = (FLOW_SKILLS / "land" / "SKILL.md").read_text(encoding="utf-8")
    expect(
        "land keeps its §1a merged-PR gate — the guard the cleared flag now leans on",
        0 if re.search(r"^### 1a\. Verify the PR is actually MERGED", land_text, re.M) else 1,
        0,
        "land/SKILL.md no longer declares the §1a BLOCKING merged-PR gate")

    print()
    if _failures:
        print(f"FAILED: {len(_failures)} eval(s): {', '.join(_failures)}")
        return 1
    print("All skill-composition evals passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
