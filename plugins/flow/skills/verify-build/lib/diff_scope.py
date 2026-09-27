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
    for args in (["diff", f"{base}...HEAD", "--name-only"],
                 ["diff", "HEAD", "--name-only"],
                 ["ls-files", "--others", "--exclude-standard"]):
        got = _git(args)
        if got is None:
            return None            # could not look -> undetermined, never docs-only
        out.extend(ln for ln in got.splitlines() if ln.strip())
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

    src_pat = cfg.get("sourceFilePatterns") if isinstance(cfg, dict) else None
    src_src = "sourceFilePatterns"
    if not (isinstance(src_pat, str) and src_pat.strip()):
        src_pat, src_src = DEFAULT_SOURCE_PATTERN, file_patterns.DEFAULT_SOURCE
    src_re = _compile(src_pat, "sourceFilePatterns", warnings)
    if src_re is None:
        src_re, src_src = re.compile(DEFAULT_SOURCE_PATTERN), file_patterns.DEFAULT_SOURCE

    # The UI rulers come from the eval-pinned resolver, NOT from a local jq read: its chain is
    # visualFilePatterns -> uiFilePatterns -> DEFAULT_UI_PATTERN, and skipping the default is
    # what made a css-only diff look docs-only.
    vis_re, vis_src, vw = file_patterns.compile_for(cfg, file_patterns.VISUAL)
    a11y_re, a11y_src, aw = file_patterns.compile_for(cfg, file_patterns.A11Y)
    warnings.extend(vw or []); warnings.extend(aw or [])

    matched = [f for f in files
               if src_re.search(f) or vis_re.search(f) or a11y_re.search(f)]
    return {
        "verdict": "docs-only" if not matched else "source-touching",
        "base": base, "files": files, "matched": matched, "reason": None, "warnings": warnings,
        "rulers": {"source": src_src, "visual": vis_src, "a11y": a11y_src},
    }


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
