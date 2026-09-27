#!/usr/bin/env python3
"""Eval harness for the docs-only N/A verdict (verify-build S 1.2 + audit-skips).

THE BUG IT PINS
---------------
On a docs-only PR from a toolchain-less host, flow produced a pull request that could not
be merged through any sanctioned path. Measured on health-tracker#118, which was stuck
there: `verify-build` could not build, so it emitted a toolchain skip; `/flow:audit-skips`
filed a `toolchain` manifest entry; `manifest-triage.CHECK_ONLY` makes that kind never
waivable-to-ready and never subtracted from the residual -- and the entry's own re-check
could never pass, because a docs-only diff contains no behaviour for any build to
exercise. Verdict stayed BLOCKED forever. The skill's own remediation text told the human
to mark the PR ready and merge it themselves: flow instructing the user to bypass flow.

The fix is a SEMANTIC distinction, not a new flag (FB-0121's class): "there is nothing to
verify" is not the same claim as "I could not verify". The first is N/A and costs the PR
nothing; only the second is a blocker. `CHECK_ONLY` is correct and deliberately untouched
-- this harness asserts that it survives, because weakening it would let a real failed
build reach READY, which is the opposite bug.

WHY EACH ASSERTION IS PAIRED (.claude/rules/general.md item 3)
-------------------------------------------------------------
A docs-only exit is a check satisfiable by skipping verification, so proving it FIRES is
worth nothing on its own. Every positive here has its negative: it fires on a genuinely
docs-only diff, and it does NOT fire when exactly one source file is added -- including a
`.json`, because that is the case the whole counter-argument turns on (a config-driven
behaviour toggle in a non-code file), and including a `.html`, which is in
`uiFilePatterns` but NOT in `sourceFilePatterns` and so is the case where a
source-only predicate would diverge from the consumer's union.

And the end-to-end pair, which is the property that was actually broken: a docs-only diff
must reach a merge-ready verdict, and a source-touching diff with an absent toolchain must
still not. Asserting only that the entry is absent would be a negative alone.

Stdlib only. Run:
    python3 plugins/flow/evals/run_docs_only_evals.py
"""

from __future__ import annotations

import json
import os
import shutil
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).parent
PLUGIN = HERE.parent
SKILLS = PLUGIN / "skills"
sys.path.insert(0, str(HERE))
from eval_utils import git_repo  # noqa: E402  the shared hoist target

_failures: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> bool:
    if cond:
        print(f"  PASS  {name}")
    else:
        print(f"  FAIL  {name}" + (f"\n          {detail}" if detail else ""))
        _failures.append(name)
    return bool(cond)


# ------------------------------------------------------- extract the shipped S 1.2 block
# EXTRACTED, never restated: a harness that re-types the predicate tests its own copy and
# lets the shipped shell drift away underneath it.
def section_shell(skill: Path, heading: str) -> str:
    text = skill.read_text(encoding="utf-8")
    start = text.index(heading)
    nxt = text.find("\n### ", start + len(heading))
    body = text[start: nxt if nxt != -1 else len(text)]
    blocks = re.findall(r"^```sh\n(.*?)^```$", body, re.S | re.M)
    if not blocks:
        raise AssertionError(f"no ```sh block under {heading!r}")
    return "\n".join(blocks)


VB_12 = section_shell(SKILLS / "verify-build" / "SKILL.md", "### 1.2. Skip-path checks")

check("the shipped S 1.2 block was extracted (not restated here)",
      "docs-only diff" in VB_12 and "cannot build the" in VB_12,
      "extraction returned a block without the docs-only exit or the toolchain exit; the "
      "cases below would then prove nothing about shipped behaviour")
# ORDER IS THE FIX. If the toolchain exit came first, a toolchain-less host would claim a
# docs-only diff before the N/A exit ran -- which is the deadlock, restored.
check("the docs-only exit precedes the toolchain exit in the shipped block",
      VB_12.index("docs-only diff") < VB_12.index("cannot build the"),
      "the toolchain exit would claim a docs-only diff first and file a never-clearable entry")


def run_12(repo: Path, config: dict) -> str:
    # The config is written and COMMITTED by `scenario()` as part of the baseline, never
    # left dirty here. `flow.config.json` is itself `.json`, which `sourceFilePatterns`
    # classifies as SOURCE -- an uncommitted config made every scenario source-touching and
    # the docs-only exit correctly never fired. The harness was wrong, not the predicate,
    # and it is worth the comment because the same trap catches a real repo: a PR that
    # edits flow.config.json is NOT docs-only, by design.
    env = dict(os.environ)
    env.pop("CLAUDE_PLUGIN_ROOT", None)          # force the in-repo helper path
    env["PATH"] = env.get("PATH", "")
    p = subprocess.run(["sh", "-c", VB_12], cwd=str(repo), env=env,
                       capture_output=True, text=True, timeout=60)
    return p.stdout + p.stderr


IOS = {"platform": "ios", "defaultBranch": "main",
       "uiFilePatterns": r"(^|/)[^/]*\.(html|css)$"}


def scenario(tmp: Path, label: str, added: dict) -> str:
    """A repo whose committed diff vs origin/main adds exactly `added`."""
    repo = git_repo(tmp / label,
                    {"README.md": "# r\n", "flow.config.json": json.dumps(IOS)})
    # Make the in-repo toolchain helper REACHABLE. Without it S 1.2's toolchain exit cannot
    # fire, and then "did not take the docs-only exit" would pass for the wrong reason -- the
    # negative half would prove only that one exit was missed, not that the blocking exit is
    # still reached. With it, this host is a genuine toolchain-less ios host: the exact
    # health-tracker#118 shape, and the known positive this harness needs (item 4).
    lib = repo / "plugins" / "flow" / "skills" / "verify-build" / "lib"
    lib.mkdir(parents=True, exist_ok=True)
    shutil.copy(PLUGIN / "skills" / "verify-build" / "lib" / "toolchain.py", lib / "toolchain.py")
    subprocess.run(["git", "add", "-A"], cwd=str(repo), capture_output=True)
    subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "helper"],
                   cwd=str(repo), capture_output=True)
    subprocess.run(["git", "branch", "-f", "main"], cwd=str(repo), capture_output=True)
    subprocess.run(["git", "remote", "add", "origin", str(repo)], cwd=str(repo), capture_output=True)
    subprocess.run(["git", "update-ref", "refs/remotes/origin/main", "main"],
                   cwd=str(repo), capture_output=True)
    subprocess.run(["git", "checkout", "-q", "-b", "work"], cwd=str(repo), capture_output=True)
    for rel, body in added.items():
        f = repo / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(body, encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=str(repo), capture_output=True)
    subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", label],
                   cwd=str(repo), capture_output=True)
    return run_12(repo, IOS)


def main() -> int:
    print("Docs-only N/A verdict evals (verify-build S 1.2 + audit-skips)")
    rc = 0
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)

        print("\n1. THE EXIT FIRES on a genuinely docs-only diff")
        for label, added in [
            ("md-only",   {"docs/guide.md": "hi\n"}),
            ("many-docs", {"a.md": "a\n", "b.txt": "b\n", "LICENSE": "x\n"}),
        ]:
            out = scenario(tmp, label, added)
            check(f"{label}: emits the docs-only N/A skip",
                  "docs-only diff — no behavior to verify" in out, f"got: {out[:240]!r}")
            check(f"{label}: does NOT emit the toolchain 'cannot build' skip",
                  "cannot build the" not in out,
                  "the toolchain exit claimed a docs-only diff — that is the deadlock. Note the "
                  "toolchain exit IS live on this fixture (section 2 proves it fires for a "
                  "source diff), so its absence here is pre-emption, not a dead check")
            check(f"{label}: hands ship a skip_reason carrying a needle audit-skips matches",
                  'skip_reason="docs-only diff' in out, f"got: {out[:240]!r}")

        print("\n2. THE EXIT DOES NOT FIRE when exactly one source file is added (the pair)")
        # .json is the case the counter-argument turns on; .html is in uiFilePatterns but NOT
        # in sourceFilePatterns, so a source-only predicate would wrongly call it docs-only.
        for label, added in [
            ("one-py",   {"app.py": "print(1)\n"}),
            ("one-json", {"feature-flags.json": '{"x":true}\n'}),
            ("one-yaml", {"config/app.yaml": "x: 1\n"}),
            ("one-toml", {"settings.toml": "x = 1\n"}),
            ("one-html", {"page.html": "<b>x</b>\n"}),
            ("docs+one-src", {"a.md": "a\n", "app.py": "print(1)\n"}),
        ]:
            out = scenario(tmp, label, added)
            check(f"{label}: does NOT take the docs-only exit",
                  "docs-only diff — no behavior to verify" not in out,
                  "a source/UI-touching diff bought a docs-only N/A it has not earned — "
                  f"got: {out[:240]!r}")
            # The POSITIVE half of the negative: on this toolchain-less ios host the diff must
            # still reach the toolchain exit. Asserting only the absence of the N/A line would
            # pass if BOTH exits silently stopped firing.
            check(f"{label}: still reaches the toolchain blocker (the exit is genuinely live)",
                  "cannot build the" in out,
                  "neither exit fired, so the previous assertion proved nothing — "
                  f"got: {out[:240]!r}")

        print("\n3. END TO END -- a docs-only PR reaches a MERGE-READY verdict")
        T = str(SKILLS / "ship" / "lib" / "manifest-triage.py")

        def verdict(entries: list, branch="work", cwd=None) -> dict:
            m = Path(cwd) / "manifest.md"
            m.write_text("".join(entries), encoding="utf-8")
            p = subprocess.run(["python3", T, "classify", "--entries-file", str(m),
                                "--branch", branch], cwd=cwd, capture_output=True, text=True)
            return json.loads(p.stdout)

        repo = git_repo(tmp / "e2e", {"flow.config.json": json.dumps(IOS)})
        # A docs-only run files NO entry, so the manifest is empty -> READY. That is the
        # property that was broken: previously a `toolchain` entry sat here permanently.
        v = verdict([], cwd=str(repo))
        check("docs-only (no entry filed) => verdict READY",
              v["verdict"] == "READY", f"got {v['verdict']} {v['counts']}")

        # ...and the NEGATIVE half: a real toolchain gap on a source-touching diff must still
        # block, and must still not be waivable to ready. Weakening that would be the opposite
        # bug, so it is asserted here rather than assumed.
        fp = subprocess.run(["python3", T, "scratch-path", "--name", "tc.txt"],
                            cwd=str(repo), capture_output=True, text=True).stdout.strip()
        Path(fp).parent.mkdir(parents=True, exist_ok=True)
        Path(fp).write_text("cannot build the ios target - xcrun absent", encoding="utf-8")
        entry = subprocess.run(["python3", T, "add-entry", "--kind", "toolchain",
                                "--needs", "human-waive", "--finding-file", fp,
                                "--resolution-file", fp],
                               cwd=str(repo), capture_output=True, text=True).stdout
        v2 = verdict([entry], cwd=str(repo))
        check("a real toolchain gap still does NOT reach READY",
              v2["verdict"] != "READY", f"got {v2['verdict']} — CHECK_ONLY must not be weakened")
        subprocess.run(["python3", T, "waive", "--branch", "work", "--kind", "toolchain",
                        "--finding-file", fp], cwd=str(repo), capture_output=True, text=True)
        v3 = verdict([entry], cwd=str(repo))
        check("...and waiving it STILL does not reach READY (CHECK_ONLY intact)",
              v3["verdict"] != "READY",
              f"got {v3['verdict']} — a waived toolchain entry must never be subtracted")

        print("\n4. CHECK_ONLY survives this change, asserted directly")
        mt = (SKILLS / "ship" / "lib" / "manifest-triage.py").read_text(encoding="utf-8")
        check('CHECK_ONLY still contains both "verify-build" and "toolchain"',
              'CHECK_ONLY = frozenset({"verify-build", "toolchain"})' in mt,
              "the fix must not widen what can reach READY; it removes the mis-routing instead")

        print("\n5. THE STALE PREMISE IS GONE -- and its replacement names a reversal condition")
        sac = (SKILLS / "audit-skips" / "lib" / "skip-audit-checks.py").read_text(encoding="utf-8")
        # Negative...
        check("the false 'No diff condition here, deliberately' premise is deleted",
              "No diff condition here, deliberately" not in sac)
        # ...paired with the positives, because deleting a comment is not fixing a premise.
        check("a diff condition is actually enforced for the toolchain arm",
              'not (diff["touches_source"] or diff["touches_visual"]' in sac,
              "the comment changed but the code did not")
        check("the replacement names the condition that would REVERSE the decision",
              "CONDITION THAT WOULD REVERSE THIS" in sac and "sourceFilePatterns" in sac,
              "a justification for an omitted check must name the premise that reinstates it")
        check("and records why grep cannot catch this class",
              "cannot find a premise that has merely become false" in sac)

    print()
    if _failures:
        print(f"FAILED: {len(_failures)} eval(s): {', '.join(_failures)}")
        rc = 1
    else:
        print("All docs-only N/A evals passed.")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
