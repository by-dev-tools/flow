#!/usr/bin/env python3
"""Is this diff DOCS-ONLY — i.e. is there nothing for a build to verify?

ONE predicate, because the hand-rolled shell version this replaces diverged from the Python
one three separate ways, each of them a failure. Reviewers measured all three:

  1. **Two-dot vs three-dot.** `git diff origin/main..HEAD` includes files from commits on
     `main` that the branch lacks, so the moment `main` moves -- the normal case during a PR
     -- a docs-only branch picks up someone else's `.py` and is classified source-touching.
     The fix that motivated this module then missed most real instances of the bug it was
     written for. `{base}...HEAD` is the correct form and is what the engine already used.
  2. **A different UI ruler.** `file_patterns.resolve()` is
     `visualFilePatterns -> uiFilePatterns -> DEFAULT_UI_PATTERN`; the shell read only
     `uiFilePatterns`, with no default. On a project that sets neither, a CSS/HTML/Vue-only
     change was classified docs-only and skipped the behavioural gate entirely -- a
     failure-OPEN on a source change, worse than the deadlock being fixed.
  3. **An unresolvable base read as "nothing there".** `2>/dev/null` on the committed arm made
     "I could not look" indistinguishable from "no committed changes" -- the exact FB-0121
     conflation the docs-only verdict exists to separate, reproduced inside it.

So the rulers come from `file_patterns` (the eval-pinned resolver) and the base resolution
fails CLOSED. Anything this module cannot determine is `undetermined`, never `docs-only`.

EXIT CODES are the contract the shell keys on; keep them stable:

    0  docs-only      -- nothing a build could exercise. Safe to return N/A.
    1  source-touching -- run the gate.
    2  undetermined   -- the base did not resolve, or a pattern could not be compiled.
                         NOT docs-only. The caller must fall through and say so out loud;
                         treating 2 as 0 is the failure-open this module exists to prevent.

`--json` prints the evidence (base, counts, which slot supplied each ruler) so an operator who
believes source changed has something to reconcile against rather than a bare verdict.

NOTE on duplication that remains, stated rather than hidden: `visual-significance.py` has its
own `resolve_base` + `collect_changes_git`, and this module deliberately does not import them
because that file's name is hyphenated and therefore not importable. Hoisting them here is
routed in the roadmap; until then `run_docs_only_evals.py` pins the two against each other.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import file_patterns  # noqa: E402  (sibling-lib import, house pattern)

# Mirrors the schema default for `sourceFilePatterns`. json/ya?ml/toml are LOAD-BEARING here:
# they are what makes "a config-driven behaviour toggle in a non-code file" impossible to
# classify as docs-only. Narrowing them re-opens that hole (see the slot's own description).
DEFAULT_SOURCE_PATTERN = (
    r"\.(ts|tsx|js|jsx|mjs|cjs|py|rs|swift|go|rb|java|kt|sh|bash|tf|tfvars|sql|proto|graphql|gql)$"
    r"|\.(json|ya?ml|toml)$|(^|/)(Dockerfile|Makefile)(\.|$)"
)

# THE DOCS ALLOWLIST, and the polarity here is the whole correctness argument.
#
# The first version of this module decided docs-only as "nothing matched `sourceFilePatterns`".
# That is an allowlist of SOURCE used as a denylist of everything else, and a security review
# measured what it costs: on `platform: ios` -- the platform this fix was motivated on --
# `Info.plist`, `project.pbxproj`, `*.xcconfig`, `*.storyboard`, `Package.resolved`,
# `Podfile.lock`, and also `.c`, `.m`, `.cpp`, `.gradle`, `go.mod`, `go.sum`, `yarn.lock`,
# `Cargo.lock`, `requirements.txt`, `pom.xml`, `CMakeLists.txt`, `.env`, `.gitmodules` and a
# bare submodule pointer ALL fell through as docs-only. A dependency bump or an iOS
# build-setting flip would have skipped the behavioural gate entirely -- a gate that ran
# before this fix existed. `sourceFilePatterns` was authored to scope a *review* early-exit,
# where a false docs-only costs a skipped read; reusing it to decide whether a BUILD runs
# needs the opposite polarity, because the costs are not symmetric.
#
# So: docs-only iff EVERY changed path matches this allowlist. Anything unrecognised is
# source-touching. An unfamiliar extension now runs the gate instead of skipping it, which is
# the direction that can only waste time rather than ship unverified behaviour.
#
# Deliberately NOT configurable. A slot here would let a project widen its way back into the
# bug, and the one legitimate need -- "my docs live somewhere unusual" -- is served by the
# directory arms below. Deliberately NOT including bare `.txt`: `requirements.txt` is a
# dependency manifest, and a lockfile is exactly the behaviour-bearing change this must catch.
DOCS_ONLY_PATTERN = (
    r"\.(md|mdx|markdown|rst|adoc)$"
    r"|^(docs|dev-docs|doc)/"
    r"|^changelog/"
    r"|(^|/)(LICENSE|COPYING|NOTICE|AUTHORS|CONTRIBUTORS|CODEOWNERS|CHANGELOG)(\.(md|txt|rst))?$"
)

DOCS_ONLY, SOURCE_TOUCHING, UNDETERMINED = 0, 1, 2


def _git(args):
    try:
        p = subprocess.run(["git", "-c", "core.quotePath=false", *args],
                           capture_output=True, text=True)
    except OSError:
        return None
    return p.stdout if p.returncode == 0 else None


def resolve_base(cfg, explicit=None):
    """`origin/<branch>` preferred, local `<branch>` as fallback, else None (fail closed).

    Returning None is the point: a caller that cannot name a base has not established that
    the diff is empty, only that it could not look. `visual-significance.resolve_base` returns
    `origin/<branch>` unverified in that case because its caller treats a failed diff as a
    signal; here the same guess would license a skip, so it is refused instead.
    """
    branch = explicit or (cfg.get("defaultBranch") if isinstance(cfg, dict) else None)
    if not branch:
        ref = (_git(["symbolic-ref", "refs/remotes/origin/HEAD"]) or "").strip()
        branch = ref[len("refs/remotes/origin/"):] if ref.startswith("refs/remotes/origin/") else "main"
    cands = [branch] if branch.startswith("origin/") else [f"origin/{branch}", branch]
    for cand in cands:
        if (_git(["rev-parse", "--verify", "--quiet", cand]) or "").strip():
            return cand
    return None


def changed_files(base):
    """Three-dot committed diff + uncommitted + untracked. None if any arm could not run."""
    out = []
    # THREE dots: `A...B` is B-since-the-merge-base, so commits that landed on the base after
    # the branch started are excluded. Two dots would attribute them to this diff.
    # `-z` + NUL split, not `--name-only` + splitlines: `core.quotePath=false` fixes non-ASCII
    # but git STILL C-quotes a path containing `"` or a control char, so `src/a"b.py` arrives as
    # `"src/a\"b.py"` and misses a `$`-anchored pattern -> classified docs (measured by review).
    for args in (["diff", "-z", f"{base}...HEAD", "--name-only"],
                 ["diff", "-z", "HEAD", "--name-only"],
                 ["ls-files", "-z", "--others", "--exclude-standard"]):
        got = _git(args)
        if got is None:
            return None            # could not look -> undetermined, never docs-only
        out.extend(p for p in got.split("\0") if p.strip())
    return sorted(set(out))


def _compile(pattern, label, warnings):
    try:
        return re.compile(pattern)
    except re.error as e:
        warnings.append(f"{label} is not a valid regex ({e}); falling back to the built-in default")
        return None


def classify(cfg, explicit_base=None):
    """Return a dict with `verdict` in {docs-only, source-touching, undetermined} + evidence."""
    warnings: list = []
    base = resolve_base(cfg, explicit_base)
    if base is None:
        return {"verdict": "undetermined", "base": None, "files": [], "matched": [],
                "reason": "no base ref resolved (neither origin/<branch> nor <branch> verifies)",
                "warnings": warnings, "rulers": {}}
    files = changed_files(base)
    if files is None:
        return {"verdict": "undetermined", "base": base, "files": [], "matched": [],
                "reason": "a git enumeration command failed", "warnings": warnings, "rulers": {}}

    # BLOCKER (measured): an EMPTY changed-file set was returning docs-only. A branch under
    # review always has changes, so "looked and saw nothing" is proof the base is wrong, not
    # proof of docs-only -- the FB-0121 conflation, one line after the arm that guards it.
    # Measured escapes: defaultBranch "@" and defaultBranch=<this branch> both gave 0 files.
    if not files:
        return {"verdict": "undetermined", "base": base, "files": [], "matched": [],
                "reason": (f"no changed files vs {base} — a branch under review always has "
                           "some, so the base is wrong rather than the diff empty"),
                "warnings": warnings, "rulers": {}}

    docs_re = re.compile(DOCS_ONLY_PATTERN)
    # SECONDARY guard, kept even though the docs allowlist alone decides the positive: if a path
    # matches a declared source/visual/a11y ruler it is source-touching no matter what, so a
    # project that puts UI under `docs/` cannot buy a skip. Union the resolved UI pattern WITH
    # the built-in default rather than substituting it -- a project narrowing
    # `visualFilePatterns` to `\.tsx$` would otherwise re-open the css/vue divergence inside
    # this very union (measured by review).
    src_pat = cfg.get("sourceFilePatterns") if isinstance(cfg, dict) else None
    src_src = "sourceFilePatterns"
    if not (isinstance(src_pat, str) and src_pat.strip()):
        src_pat, src_src = DEFAULT_SOURCE_PATTERN, file_patterns.DEFAULT_SOURCE
    src_re = _compile(src_pat, "sourceFilePatterns", warnings)
    if src_re is None:
        src_re, src_src = re.compile(DEFAULT_SOURCE_PATTERN), file_patterns.DEFAULT_SOURCE
    vis_re, vis_src, vw = file_patterns.compile_for(cfg, file_patterns.VISUAL)
    a11y_re, a11y_src, aw = file_patterns.compile_for(cfg, file_patterns.A11Y)
    warnings.extend(vw or []); warnings.extend(aw or [])
    ui_default = re.compile(file_patterns.DEFAULT_UI_PATTERN)

    def is_source(f):
        return bool(src_re.search(f) or vis_re.search(f) or a11y_re.search(f)
                    or ui_default.search(f))

    # docs-only iff EVERY path is recognisably docs AND none trips a source/UI ruler.
    not_docs = [f for f in files if not docs_re.search(f)]
    tripped = [f for f in files if is_source(f)]
    if not_docs or tripped:
        return {"verdict": "source-touching", "base": base, "files": files,
                "matched": sorted(set(tripped + not_docs)), "reason": None,
                "warnings": warnings,
                "rulers": {"source": src_src, "visual": vis_src, "a11y": a11y_src,
                           "docs": "built-in docs allowlist"}}
    return {"verdict": "docs-only", "base": base, "files": files, "matched": [],
            "reason": None, "warnings": warnings,
            "rulers": {"source": src_src, "visual": vis_src, "a11y": a11y_src,
                       "docs": "built-in docs allowlist"}}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", default="flow.config.json")
    ap.add_argument("--base", default=None)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    try:
        cfg = json.loads(Path(args.config).read_text(encoding="utf-8"))
        if not isinstance(cfg, dict):
            cfg = {}
    except (OSError, ValueError):
        cfg = {}          # a missing/!dict config means "no overrides", not "undetermined"
    r = classify(cfg, args.base)
    if args.json:
        print(json.dumps(r, indent=2))
    else:
        for w in r["warnings"]:
            sys.stderr.write(f"[diff-scope] WARN {w}\n")
        if r["verdict"] == "docs-only":
            print(f"docs-only ({len(r['files'])} file(s) changed vs {r['base']}, "
                  f"none matching source/visual/a11y patterns)")
        elif r["verdict"] == "source-touching":
            print(f"source-touching ({len(r['matched'])} of {len(r['files'])} file(s) match; "
                  f"first: {r['matched'][0]})")
        else:
            print(f"undetermined — {r['reason']}")
    return {"docs-only": DOCS_ONLY, "source-touching": SOURCE_TOUCHING}.get(
        r["verdict"], UNDETERMINED)


if __name__ == "__main__":
    raise SystemExit(main())
