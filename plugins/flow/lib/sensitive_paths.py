#!/usr/bin/env python3
"""Is this changed-file set gate machinery? One predicate, two readers.

Canonical cloud-workflow plan §4.8 makes "stakes" the first of four axes on the
plan gate: a diff that touches `sensitivePaths` stays human because a wrong
version there fails *silently*, is *exploitable*, or is a *one-way door*. The
orchestrator field manual § 6 then names the identical set as the one hard floor
on model routing — "gate machinery does not get routed down" — and says
"deliberately" about the reuse.

Two readers, therefore one definition:

  - `skills/gate/lib/gate-classify.py` — the stakes axis of the four-axis
    classification.
  - `/flow:spawn` — the routing floor. A dispatch whose owned paths are
    sensitive cannot be routed below the top tier, whatever job shape the agent
    picked from the table.

An earlier draft of this work put the predicate inside gate's private lib and
left spawn no way to reach it, which is the same shared-contract-in-one-copy
shape `.claude/rules/general.md` § Consistency calls fan-out contradiction. It
lives here, beside `resolve-doc-slot.sh`, because `plugins/flow/lib/` is already
the home for cross-skill contracts.

**Fail-safe direction is toward escalation, and that is not an accident.** Every
degraded path in this module returns *sensitive* rather than *not sensitive*: an
unreadable changed-file list, an unreadable owned-glob list, a repo whose index
cannot be read. A malformed or empty `sensitivePaths` slot falls back to the
documented defaults, loudly. A wrong "sensitive" costs one unnecessary human
decision; a wrong "not sensitive" auto-approves a plan that should have
escalated, or routes gate machinery to a cheap model — and both of those fail
without a symptom. The asymmetry is the whole reason this is code rather than a
sentence in a SKILL.md.

There is deliberately **no** "pattern failed to compile" fallback, because that
branch cannot be reached: `_glob_to_regex` `re.escape`s every character that is
not one of the three wildcards, so translation always yields a valid pattern.
An unreachable fail-safe is not a fail-safe — it is dead code that reads like
protection, and the eval harness pins the real property instead (arbitrary
pattern text is matched literally rather than crashing).

**Deletion criterion (FB-0088):** delete when it has fewer than two readers —
i.e. when `/flow:gate` and `/flow:spawn` are not both live. A shared lib with one
consumer is indirection, not sharing.

Underscore-named so it is importable as a bare module (the house pattern of
`ship/lib/manifest_contract.py` and `verify-build/lib/walk_extract.py`).

Stdlib only. No side effects on import. Python 3.7+.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

PREFIX = "[sensitive-paths]"

# Documented defaults (CLAUDE.md: never silently no-op on a missing slot; degrade
# to documented defaults OR warn loudly). These are deliberately *shape-based and
# project-agnostic* — the universal one-way-door / exploitable / silently-failing
# classes §4.8 names. A project's OWN gate machinery is project-shaped knowledge
# and belongs in its `flow.config.json`, not here: flow's own repo adds
# ship/manifest-triage/skip-audit/verify-build/pr-coherence that way. Hardcoding
# flow's filenames here would make the plugin's gate policy assume it was running
# on flow, which is exactly the bar the adapter design exists to hold.
DEFAULT_SENSITIVE_PATHS = [
    # Secrets and credentials — exploitable, and a leak is not revertible.
    "**/.env",
    "**/.env.*",
    "**/secrets/**",
    "**/*credentials*",
    "**/*.pem",
    "**/*.key",
    # AuthN / AuthZ — exploitable, and a wrong version fails open.
    "**/auth/**",
    "**/authentication/**",
    "**/authorization/**",
    # Persistence and migrations — one-way doors; `git revert` does not undo a
    # migration that already ran.
    "**/migrations/**",
    "**/migrate/**",
    "**/*.sql",
    # Published contracts consumers pin against — a breaking change is not
    # revertible once someone has pulled it.
    "**/schema/**",
    "**/*.schema.json",
    # CI / release machinery — a gate that mis-classifies lets bad work through,
    # and it does so without a symptom.
    ".github/workflows/**",
    ".github/actions/**",
]


def _glob_to_regex(pattern: str) -> str:
    """Translate a slash-aware glob to a regex anchored at both ends.

    `fnmatch` is not usable here: its `*` crosses `/`, so `**/auth/**` and
    `*.sql` would both match far more than intended, and the over-match would be
    invisible (it errs toward "sensitive", so nothing would look broken — it
    would just escalate everything and quietly make the gate useless).

    Supported: `**` (any number of path segments, including none), `*` (anything
    except `/`), `?` (one character except `/`). Everything else is literal.
    """
    out = []
    i = 0
    n = len(pattern)
    while i < n:
        c = pattern[i]
        if c == "*":
            if i + 1 < n and pattern[i + 1] == "*":
                # `**/` consumes zero-or-more leading segments, so `**/auth/**`
                # matches `auth/x` as well as `src/auth/x`. Without the
                # zero-segment case the most natural way to write a pattern
                # would silently miss repo-root matches.
                if i + 2 < n and pattern[i + 2] == "/":
                    out.append(r"(?:[^/]+/)*")
                    i += 3
                    continue
                out.append(r".*")
                i += 2
                continue
            out.append(r"[^/]*")
            i += 1
            continue
        if c == "?":
            out.append(r"[^/]")
            i += 1
            continue
        out.append(re.escape(c))
        i += 1
    return r"\A" + "".join(out) + r"\Z"


def _normalize(path: str) -> str:
    """Repo-relative POSIX form, so `./a/b`, `a/b` and `a\\b` compare equal."""
    p = path.strip().replace("\\", "/")
    while p.startswith("./"):
        p = p[2:]
    return p.lstrip("/")


def load_patterns(config_path: str = "flow.config.json") -> tuple[list[str], str, list[str]]:
    """Return (patterns, source, warnings).

    `source` is one of `config` / `default` / `default-after-error`. An absent
    slot is NOT a warning — the defaults are documented, which is the degrade
    CLAUDE.md permits. A slot that is *present and malformed* IS a warning,
    because the consumer believes they configured something and they have not.
    """
    warnings: list[str] = []
    p = Path(config_path)
    if not p.is_file():
        return list(DEFAULT_SENSITIVE_PATHS), "default", warnings
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        warnings.append(
            f"{PREFIX} ⚠️ {config_path} could not be read or parsed ({exc}); falling back to "
            f"the documented defaults. Every classification below therefore uses the default "
            f"pattern set, NOT this project's."
        )
        return list(DEFAULT_SENSITIVE_PATHS), "default-after-error", warnings
    if not isinstance(data, dict) or "sensitivePaths" not in data:
        return list(DEFAULT_SENSITIVE_PATHS), "default", warnings
    raw = data.get("sensitivePaths")
    if not isinstance(raw, list) or not all(isinstance(x, str) for x in raw):
        warnings.append(
            f"{PREFIX} ⚠️ flow.config.json.sensitivePaths is present but is not a list of "
            f"strings (got {type(raw).__name__}); falling back to the documented defaults. "
            f"Fix the slot — this project's own gate machinery is NOT being matched."
        )
        return list(DEFAULT_SENSITIVE_PATHS), "default-after-error", warnings
    cleaned = [s.strip() for s in raw if s.strip()]
    if not cleaned:
        warnings.append(
            f"{PREFIX} ⚠️ flow.config.json.sensitivePaths is present but empty. An empty list "
            f"would classify EVERY diff as low-stakes, so it is treated as unset and the "
            f"documented defaults apply. If you meant 'nothing is sensitive here', say so in "
            f"the plan and waive at the gate — do not express it as an empty slot."
        )
        return list(DEFAULT_SENSITIVE_PATHS), "default-after-error", warnings
    return cleaned, "config", warnings


def expand_globs(globs, tracked):
    """Turn an owned-GLOB set into the concrete path set it currently covers.

    The two readers do not naturally ask the same question. `/flow:gate` holds a
    changed-FILE list; `/flow:spawn` holds the owned-PATH GLOBS it is about to
    assign a worker. Matching a glob against a glob is a different operation from
    matching a path against a glob, and a slot asked two different questions has
    two correct answers — at which point one consumer is necessarily answered
    wrongly (FB-0079, which is exactly about a shared slot with two askers).

    So spawn's input is *normalised* rather than the predicate being overloaded:
    an owned glob is expanded against the repo's tracked files, and the result is
    the same path list `classify()` already takes. One question, two input
    adapters, and a glob that currently matches nothing is reported so it cannot
    be mistaken for "nothing sensitive here".
    """
    matched: list[str] = []
    empty: list[str] = []
    norm_tracked = [_normalize(t) for t in tracked]
    for g in globs:
        g = g.strip()
        if not g:
            continue
        rx = re.compile(_glob_to_regex(_normalize(g)))
        hits = [t for t in norm_tracked if rx.match(t)]
        if hits:
            matched.extend(hits)
        else:
            empty.append(g)
    return sorted(set(matched)), empty


def classify(paths, patterns) -> dict:
    """Return {'sensitive': bool, 'matches': [{'path','pattern'}...]}.

    A path is sensitive if ANY pattern matches it. Every match is reported, not
    just the first, because the escalation text has to name *why* a diff is
    high-stakes and one reason is rarely the whole story.
    """
    # No try/except: see the module docstring — every character outside the three
    # wildcards is escaped, so translation cannot produce an invalid pattern.
    compiled = [(pat, re.compile(_glob_to_regex(pat))) for pat in patterns]
    matches = []
    for raw in paths:
        norm = _normalize(raw)
        if not norm:
            continue
        for pat, rx in compiled:
            if rx.match(norm):
                matches.append({"path": norm, "pattern": pat})
    return {"sensitive": bool(matches), "matches": matches}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        prog="sensitive_paths.py",
        description="Classify a changed-file set against flow.config.json.sensitivePaths.",
    )
    ap.add_argument(
        "--files-file",
        help="path to a newline-delimited list of changed files. Deliberately a FILE and not "
             "a repeated argv value: a `git diff --name-only` list can be long and can contain "
             "characters a shell would re-interpret (field manual T6 / FB-0108).",
    )
    ap.add_argument("--config", default="flow.config.json")
    ap.add_argument(
        "--globs-file",
        help="path to a newline-delimited list of owned-path GLOBS (the /flow:spawn entry point). "
             "Expanded against the repo's tracked files first, so both readers end up asking the "
             "predicate the same path-shaped question (FB-0079).",
    )
    ap.add_argument(
        "--print-defaults", action="store_true",
        help="emit the documented default pattern set and exit (for docs + evals).",
    )
    args = ap.parse_args(argv)

    if args.print_defaults:
        print(json.dumps({"defaults": DEFAULT_SENSITIVE_PATHS}, indent=2))
        return 0

    patterns, source, warnings = load_patterns(args.config)
    for w in warnings:
        print(w, file=sys.stderr)

    if not args.files_file and not args.globs_file:
        print(
            f"{PREFIX} ⚠️ one of --files-file (a changed-file list) or --globs-file (an owned-glob "
            f"set) is required, or pass --print-defaults.",
            file=sys.stderr,
        )
        return 2

    if args.globs_file:
        try:
            globs = [ln for ln in Path(args.globs_file).read_text(encoding="utf-8").splitlines() if ln.strip()]
        except OSError as exc:
            print(
                f"{PREFIX} ⚠️ could not read --globs-file ({exc}); classified SENSITIVE so the "
                f"routing floor applies rather than defaulting to low-stakes.",
                file=sys.stderr,
            )
            print(json.dumps({"sensitive": True, "matches": [],
                              "pattern_source": source, "reason": "owned-glob list unreadable"}, indent=2))
            return 0
        import subprocess  # local: this is the only path that needs the repo index
        try:
            tracked = subprocess.run(
                ["git", "ls-files"], capture_output=True, text=True, timeout=60
            ).stdout.splitlines()
        except (OSError, subprocess.SubprocessError) as exc:
            print(
                f"{PREFIX} ⚠️ could not enumerate tracked files ({exc}); owned globs cannot be "
                f"expanded, so this is classified SENSITIVE rather than guessed.",
                file=sys.stderr,
            )
            print(json.dumps({"sensitive": True, "matches": [],
                              "pattern_source": source, "reason": "git ls-files unavailable"}, indent=2))
            return 0
        expanded, empty = expand_globs(globs, tracked)
        result = classify(expanded, patterns)
        result["pattern_source"] = source
        result["expanded_from_globs"] = len(expanded)
        result["globs_matching_nothing"] = empty
        if empty and not result["sensitive"]:
            # Loud, not silent: a glob that matches nothing today may be the one
            # that would have matched the sensitive file the worker is about to
            # create. Reporting "not sensitive" without saying this would be a
            # confident answer to a question we could not fully evaluate.
            print(
                f"{PREFIX} ⚠️ {len(empty)} owned glob(s) matched no tracked file "
                f"({', '.join(empty[:5])}). The verdict below covers only what exists today.",
                file=sys.stderr,
            )
        print(json.dumps(result, indent=2))
        return 0
    try:
        raw = Path(args.files_file).read_text(encoding="utf-8")
    except OSError as exc:
        # Fail-safe again: we were asked about a file set we cannot see.
        print(
            f"{PREFIX} ⚠️ could not read --files-file ({exc}); classified SENSITIVE so the "
            f"decision reaches a human rather than defaulting to low-stakes.",
            file=sys.stderr,
        )
        print(json.dumps({
            "sensitive": True,
            "matches": [],
            "pattern_source": source,
            "reason": "changed-file list unreadable",
        }, indent=2))
        return 0

    result = classify([ln for ln in raw.splitlines()], patterns)
    result["pattern_source"] = source
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
