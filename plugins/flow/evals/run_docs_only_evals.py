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
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).parent
PLUGIN = HERE.parent
SKILLS = PLUGIN / "skills"
sys.path.insert(0, str(HERE))
from eval_utils import commit, git_repo  # noqa: E402  the shared hoist target
sys.path.insert(0, str(PLUGIN / 'skills' / 'verify-build' / 'lib'))
from diff_scope import DOCS_ONLY, SOURCE_TOUCHING, UNDETERMINED  # noqa: E402

_failures: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> bool:
    if cond:
        print(f"  PASS  {name}")
    else:
        print(f"  FAIL  {name}" + (f"\n          {detail}" if detail else ""))
        _failures.append(name)
    return bool(cond)


# ------------------------------------------------------- the shipped S 1.2 wiring, asserted
# The PREDICATE is `lib/diff_scope.py` (a program), not shell. The first cut of this fix
# hand-rolled it in shell and diverged from the engine three ways -- two-dot diff, a UI ruler
# missing `visualFilePatterns` + the built-in default, and a `2>/dev/null` that made an
# unresolvable base look like an empty diff. Each is a regression case in section 1 below.
#
# What is still asserted about the SHELL is only its wiring: that it calls the helper, keys on
# the three exit codes, and puts the docs-only exit BEFORE the toolchain check. Ordering is the
# fix; if the toolchain exit ran first a toolchain-less host would claim a docs-only diff again.
VB_SKILL = (SKILLS / "verify-build" / "SKILL.md").read_text(encoding="utf-8")

check("S 1.2 calls the shared predicate rather than re-deriving it in shell",
      "diff_scope.py" in VB_SKILL and "VB_HITS" not in VB_SKILL,
      "a second hand-rolled predicate diverges from the engine that validates its claim")
check("the docs-only exit precedes the toolchain exit",
      VB_SKILL.index("docs-only diff — no behavior to verify")
      < VB_SKILL.index("cannot build the"),
      "the toolchain exit would claim a docs-only diff first and file a never-clearable entry")
check("all three exit codes are handled, and UNDETERMINED is not treated as docs-only",
      "DS_RC" in VB_SKILL and "UNCHECKED here, not clean" in VB_SKILL,
      "exit 2 must fall through loudly; collapsing it into 0 is the failure-open")
check("an unreachable helper warns rather than silently skipping the check",
      "diff_scope.py not reachable" in VB_SKILL)

DS = SKILLS / "verify-build" / "lib" / "diff_scope.py"


def repo_with(tmp, label, cfg, committed=None, base_extra=None, untracked=None, no_origin=False):
    """A repo whose branch `work` adds `committed`, with `base_extra` landing on main AFTER."""
    repo = git_repo(tmp / label, {"README.md": "# r\n", "flow.config.json": json.dumps(cfg)})
    if not no_origin:
        subprocess.run(["git", "remote", "add", "origin", str(repo)], cwd=str(repo), capture_output=True)
        subprocess.run(["git", "update-ref", "refs/remotes/origin/main", "main"],
                       cwd=str(repo), capture_output=True)
    subprocess.run(["git", "checkout", "-q", "-b", "work"], cwd=str(repo), capture_output=True)
    if committed:
        commit(repo, committed, label)
    if base_extra:
        subprocess.run(["git", "checkout", "-q", "main"], cwd=str(repo), capture_output=True)
        commit(repo, base_extra, "base-moved")
        if not no_origin:
            subprocess.run(["git", "update-ref", "refs/remotes/origin/main", "main"],
                           cwd=str(repo), capture_output=True)
        subprocess.run(["git", "checkout", "-q", "work"], cwd=str(repo), capture_output=True)
    if no_origin:
        # resolve_base falls back origin/<b> -> <b>, correctly. To exercise "neither resolves"
        # the local branch has to go too, or this fixture tests the fallback, not the failure.
        subprocess.run(["git", "branch", "-D", "main"], cwd=str(repo), capture_output=True)
    for rel, body in (untracked or {}).items():
        f = repo / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(body, encoding="utf-8")
    return repo


def ds_verdict(repo) -> tuple:
    p = subprocess.run(["python3", str(DS), "--config", "flow.config.json"],
                       cwd=str(repo), capture_output=True, text=True)
    return p.returncode, (p.stdout + p.stderr).strip()


IOS = {"platform": "ios", "defaultBranch": "main"}
WEB = {"platform": "web", "defaultBranch": "main"}


def main() -> int:
    print("Docs-only N/A verdict evals (verify-build S 1.2 + audit-skips)")
    rc = 0
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)

        print("\n1. DOCS-ONLY verdicts, including the three measured regressions")
        cases = [
            # (label, cfg, committed, base_extra, untracked, want_rc, why)
            ("md-only", IOS, {"docs/g.md": "x\n"}, None, None, DOCS_ONLY,
             "a plain docs diff"),
            ("many-docs", IOS, {"a.md": "a\n", "LICENSE": "x\n"}, None, None, DOCS_ONLY,
             "several docs files"),
            # REGRESSION 1 -- two-dot vs three-dot. `main` advancing with a .py must not make a
            # docs-only branch source-touching; two-dot did exactly that, so the original fix
            # missed the common case (main moves during every real PR).
            ("base-moved", IOS, {"docs/g.md": "x\n"}, {"other.py": "print(1)\n"}, None,
             DOCS_ONLY, "main advanced with a .py after the branch started"),
            # REGRESSION 2 -- the UI ruler. With NO ui/a11y slots set, the built-in default must
            # still classify css/html/vue as UI. The shell read only `uiFilePatterns` and had no
            # default, so these were called docs-only and skipped the gate: failure-OPEN.
            ("css-no-slots", WEB, {"styles/app.css": "a{}\n"}, None, None, SOURCE_TOUCHING,
             "css with no uiFilePatterns set — the default ruler must still catch it"),
            ("html-no-slots", WEB, {"index.html": "<b>x</b>\n"}, None, None, SOURCE_TOUCHING,
             "html with no slots set"),
            ("vue-no-slots", WEB, {"Card.vue": "<template/>\n"}, None, None, SOURCE_TOUCHING,
             "vue with no slots set"),
            # REGRESSION 3 -- an unresolvable base is UNDETERMINED, never docs-only. Previously
            # `2>/dev/null` made it read as "no committed changes" and an untracked docs file
            # was enough to buy the N/A exit on a repo containing committed source.
            ("no-base", IOS, {"app.py": "print(1)\n"}, None, {"notes.md": "n\n"},
             UNDETERMINED, "no origin/main and no local main to fall back to"),
            # The counter-argument cases: config-as-source. These are why json/ya?ml/toml in the
            # default matter, and they are the pair for every docs-only row above.
            ("one-json", IOS, {"flags.json": '{"a":1}\n'}, None, None, SOURCE_TOUCHING, ".json is SOURCE"),
            ("one-yaml", IOS, {"c/app.yaml": "x: 1\n"}, None, None, SOURCE_TOUCHING, ".yaml is SOURCE"),
            ("one-toml", IOS, {"s.toml": "x = 1\n"}, None, None, SOURCE_TOUCHING, ".toml is SOURCE"),
            ("one-py", IOS, {"app.py": "print(1)\n"}, None, None, SOURCE_TOUCHING, "plain source"),
            ("docs+src", IOS, {"a.md": "a\n", "app.py": "p\n"}, None, None, SOURCE_TOUCHING,
             "one source file among docs is still source-touching"),
            ("untracked-src", IOS, {"a.md": "a\n"}, None, {"new.py": "p\n"}, SOURCE_TOUCHING,
             "an UNTRACKED source file counts — the iterate-then-ship loop"),
            ("uncommitted-src", IOS, {"a.md": "a\n"}, None, None, SOURCE_TOUCHING, ""),
            # An invalid pattern must fall back to the default, never fail open into docs-only.
            ("bad-regex", dict(IOS, sourceFilePatterns="(?i)\\.py$"), {"app.py": "p\n"},
             None, None, SOURCE_TOUCHING, "an invalid regex falls back, never opens"),
            ("non-ascii", IOS, {"caf\u00e9.py": "p\n"}, None, None, SOURCE_TOUCHING,
             "quotePath=false so a non-ASCII source name still matches"),
        ]
        NAMES = {DOCS_ONLY: "docs-only", SOURCE_TOUCHING: "source-touching",
                 UNDETERMINED: "undetermined"}
        for label, cfg, committed, base_extra, untracked, want, why in cases:
            repo = repo_with(tmp, label, cfg, committed, base_extra, untracked,
                             no_origin=(label == "no-base"))
            if label == "uncommitted-src":
                (repo / "mod.py").write_text("p\n", encoding="utf-8")
                subprocess.run(["git", "add", "-A"], cwd=str(repo), capture_output=True)
            got, out = ds_verdict(repo)
            check(f"{label}: {NAMES[want]}" + (f" ({why})" if why else ""),
                  got == want, f"got {NAMES.get(got, got)} — {out[:200]}")

        print("\n2. THE PREDICATE AGREES WITH THE ENGINE THAT VALIDATES ITS CLAIM")
        # The producer's verdict and the consumer's `touches_*` union are two readers of one
        # boundary. Pinning them SEPARATELY is what let three divergences ship, so they are
        # compared here per shape -- general.md item 4's corollary, pointed at this PR's own
        # "the two predicates agree by construction" claim.
        sys.path.insert(0, str(SKILLS / "audit-skips" / "lib"))
        import importlib.util, re as _re
        spec = importlib.util.spec_from_file_location(
            "sac", str(SKILLS / "audit-skips" / "lib" / "skip-audit-checks.py"))
        sac = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(sac)
        import diff_scope as ds
        import file_patterns as fp

        # The ONE genuine duplication between the two readers is the source default; the UI
        # rulers already come from the same `file_patterns.compile_for` on both sides. Assert
        # the duplicate is byte-identical rather than trusting it was copied correctly.
        check("the source-pattern default is byte-identical in producer and engine",
              ds.DEFAULT_SOURCE_PATTERN == sac.DEFAULT_SOURCE_PATTERN,
              "the two readers would classify a config-only diff differently:\n"
              f"          producer={ds.DEFAULT_SOURCE_PATTERN!r}\n"
              f"          engine  ={sac.DEFAULT_SOURCE_PATTERN!r}")
        check("both readers take their UI rulers from file_patterns.compile_for",
              "compile_for" in (SKILLS / "audit-skips" / "lib" / "skip-audit-checks.py")
              .read_text(encoding="utf-8")
              and "file_patterns.compile_for" in DS.read_text(encoding="utf-8"),
              "a local jq/regex read instead of the shared resolver is how the css-only "
              "divergence shipped")

        def engine_touches(cfg, files):
            src = _re.compile(cfg.get("sourceFilePatterns") or sac.DEFAULT_SOURCE_PATTERN)
            vis, _, _ = sac.compile_for(cfg, sac.VISUAL)
            a11y, _, _ = sac.compile_for(cfg, sac.A11Y)
            return any(src.search(f) or vis.search(f) or a11y.search(f) for f in files)

        def producer_touches(cfg, files):
            src = ds._compile(cfg.get("sourceFilePatterns") or ds.DEFAULT_SOURCE_PATTERN, "s", [])
            vis, _, _ = fp.compile_for(cfg, fp.VISUAL)
            a11y, _, _ = fp.compile_for(cfg, fp.A11Y)
            return any(src.search(f) or vis.search(f) or a11y.search(f) for f in files)

        for label, cfg, files in [
            ("md-only",       IOS, ["docs/g.md"]),
            ("css-no-slots",  WEB, ["styles/app.css"]),
            ("html-no-slots", WEB, ["index.html"]),
            ("mdx-visualonly", dict(WEB, visualFilePatterns=r"\.mdx$"), ["docs/p.mdx"]),
            ("json",          IOS, ["flags.json"]),
            ("py",            IOS, ["app.py"]),
        ]:
            pt, et = producer_touches(cfg, files), engine_touches(cfg, files)
            check(f"agreement[{label}]: producer and engine classify identically",
                  pt == et, f"producer touches={pt} engine touches={et} for {files} cfg={cfg}")

        print("\n2b. THE SHELL ACTUALLY TAKES THE EXIT (composed layer, not just the predicate)")
        # Mutation-found gap: every other section tests the PREDICATE or greps the skill TEXT,
        # so disabling the whole exit (`if [ -n "$DS" ]` -> `if false`) left the harness green.
        # A check that cannot fail when the feature is removed is not a check (item 4), and the
        # claim being made is about /flow:verify-build's behaviour, not about diff_scope's --
        # item 4's corollary: pin it at the layer where it is claimed. So: extract the shipped
        # S 1.2 block and RUN it, with the helpers reachable, over both verdicts.
        import re as _re2
        vb = VB_SKILL
        sect = vb[vb.index("### 1.2. Skip-path checks"):]
        sect = sect[:sect.index("\n### ")] if "\n### " in sect else sect
        blocks = _re2.findall(r"^```sh\n(.*?)^```$", sect, _re2.S | _re2.M)
        check("S 1.2's shell block is extractable", bool(blocks),
              "cannot run what cannot be extracted; the checks below would be vacuous")
        shell = "\n".join(blocks)

        def run_12(repo):
            # Reach the helpers via CLAUDE_PLUGIN_ROOT, NOT by copying them into the fixture.
            # Copying put three untracked `.py` files in the repo, which the predicate then
            # correctly counted as source -- the fixture defeated its own docs-only case and
            # reported a deadlock that was not there. (Same shape as leaving flow.config.json
            # uncommitted: the harness's own artifacts are part of the diff it measures.)
            # It also exercises the plugin-root-first resolution branch production uses.
            env = dict(os.environ)
            env["CLAUDE_PLUGIN_ROOT"] = str(PLUGIN)
            pr = subprocess.run(["sh", "-c", shell], cwd=str(repo), env=env,
                                capture_output=True, text=True, timeout=60)
            return pr.stdout + pr.stderr

        docs_repo = repo_with(tmp, "run12-docs", IOS, {"docs/g.md": "x\n"})
        out = run_12(docs_repo)
        check("running S 1.2 on a docs-only diff emits the N/A skip",
              "docs-only diff — no behavior to verify" in out, f"got: {out[:220]!r}")
        check("...and does NOT emit the toolchain blocker",
              "cannot build the" not in out,
              "the toolchain exit claimed a docs-only diff — the deadlock, restored")
        # UNDETERMINED at the composed layer. Mutation-found: with no fixture producing exit 2,
        # rewriting the `*)` arm to `exit 0` escaped every other check -- i.e. the single
        # failure-open this whole fix exists to prevent was the one state nothing exercised.
        und_repo = repo_with(tmp, "run12-undet", IOS, {"app.py": "print(1)\n"},
                             untracked={"notes.md": "n\n"}, no_origin=True)
        out3 = run_12(und_repo)
        check("an UNDETERMINED diff does NOT take the N/A exit",
              "docs-only diff — no behavior to verify" not in out3,
              "\"I could not look\" bought a clean skip — the FB-0121 conflation, reintroduced")
        check("...and says so out loud (UNCHECKED, not clean)",
              "UNCHECKED here, not clean" in out3, f"got: {out3[:220]!r}")

        src_repo = repo_with(tmp, "run12-src", IOS, {"app.py": "print(1)\n"})
        out2 = run_12(src_repo)
        check("running S 1.2 on a source diff does NOT emit the N/A skip",
              "docs-only diff — no behavior to verify" not in out2, f"got: {out2[:220]!r}")
        check("...and DOES reach the toolchain blocker (the exit is live on this fixture)",
              "cannot build the" in out2,
              "neither exit fired, so the assertion above proved nothing")

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
        # Membership, not the literal source line: reordering the frozenset or adding a
        # legitimate third kind would redden CI over a green contract. §3 already proves the
        # behaviour; this pins the SET so a silent removal of "toolchain" is still caught.
        m_ck = _re.search(r"CHECK_ONLY\s*=\s*frozenset\(\{([^}]*)\}\)", mt)
        members = set(_re.findall(r'"([^"]+)"', m_ck.group(1))) if m_ck else set()
        check("CHECK_ONLY still holds both verify-build and toolchain",
              {"verify-build", "toolchain"} <= members,
              f"members={sorted(members)} — the fix must not widen what can reach READY")

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
