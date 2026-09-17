#!/usr/bin/env python3
"""Is this changed-file set gate machinery? One predicate, two readers.

Canonical cloud-workflow plan §4.8 makes "stakes" the first of four axes on the
plan gate: a diff that touches `sensitivePaths` stays human because a wrong
version there fails *silently*, is *exploitable*, or is a *one-way door*. The
`/flow:spawn`'s routing table names the identical set as the one hard floor on
model routing — "gate machinery does not get routed down" — and says "deliberately"
about the reuse. (That argument originated in the orchestrator field manual § 6,
which this suite discharged on 2026-09-17 by making the procedure executable; the
floor now lives in the skill rather than in a doc a seat had to remember.)

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
cannot be read, an EMPTY input on either side ("asked about nothing" is not
"nothing is sensitive"), **and an owned glob that matches nothing yet *and
names a sensitive area*** (the greenfield one-way-door case — a worker dispatched to
*create* migrations or auth owns a glob with no matches today, and that is
precisely when the floor matters most). Note the qualifier: a `docs/**` that does
not exist yet is genuinely low-stakes, and escalating the whole greenfield class
would be the over-spending failure the routing policy names as explicitly as it
names under-dispatching. A malformed or empty `sensitivePaths` slot falls back to the
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

Fixtures live in `evals/run_handoff_brief_evals.py` §§4–8 (both entry points, the
routing floor and its negative, the fail-safe directions, and the project-agnosticism
of the defaults) — named for its sibling subject, so look there rather than for a
harness named after this file.

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
    # The policy's own surface. Without these, the diff that WEAKENS the gate is
    # itself low-stakes and therefore auto-approvable — a single green plan gate
    # could edit the list that decides which plan gates are green. Self-protection
    # is not paranoia here; it is the one entry whose absence makes every other
    # entry optional.
    "**/flow.config.json",
    # Note `**/.flow/**` does its work through the GLOB entry point rather than the file
    # one: a project that gitignores `.flow/` (flow's own scaffolding does) never sees it
    # in a changed-file list. It still matters for a consumer who does not, and for any
    # worker whose owned paths name it.
    "**/.flow/**",
]


# Bounds on a consumer-supplied glob. These are ReDoS guards, not style limits: the
# translated regex is matched against every candidate path, and repo-controlled input
# reaches it. `*a*a*a…b` (nested quantifier alternation) did not terminate in 25s on a
# 50-char path; ten adjacent `**/` groups took 1.3s and grow exponentially. A gate that
# hangs is a gate that never returns a verdict, which is worse than either answer.
_MAX_PATTERN_LEN = 200
# Measured on a 40-char path, `*a*a*…*b`: 8 wildcards 0.41s, 9 → 1.70s, 10 → 6.08s,
# 11 → 19.3s, 12 → 54.9s (~3.5× per wildcard). A limit of 12 therefore ADMITTED the
# exact shape this guard exists to refuse — the bound was set by eyeballing rather than
# by measuring, and the eval now pins a wall-clock ceiling so it cannot drift back up.
# 6 measures at ~0.02s and is far above any legitimate policy glob (the 18 defaults use
# at most 3).
_MAX_WILDCARDS = 6


def _glob_to_regex(pattern: str) -> str:
    """Translate a slash-aware glob to a regex anchored at both ends.

    `fnmatch` is not usable here: its `*` crosses `/`, so `**/auth/**` and
    `*.sql` would both match far more than intended, and the over-match would be
    invisible (it errs toward "sensitive", so nothing would look broken — it
    would just escalate everything and quietly make the gate useless).

    Supported: `**` (any number of path segments, including none), `*` (anything
    except `/`), `?` (one character except `/`). Everything else is literal.
    """
    # Collapse runs of `**/` to one: `**/**/x` and `**/x` admit the same paths, but the
    # first compiles to adjacent `(?:[^/]+/)*` groups whose backtracking multiplies.
    pattern = re.sub(r"(?:\*\*/)+", "**/", pattern)
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


def _pattern_is_safe(pattern: str):
    """(ok, reason). Refuse a pattern that could make matching pathological."""
    if len(pattern) > _MAX_PATTERN_LEN:
        return False, f"longer than {_MAX_PATTERN_LEN} chars"
    wild = pattern.count("*") + pattern.count("?")
    if wild > _MAX_WILDCARDS:
        return False, f"contains {wild} wildcards (limit {_MAX_WILDCARDS})"
    return True, ""


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
    if cleaned:
        # MERGE, do not replace. The defaults are a FLOOR, not a suggestion. Replacing
        # them meant a consumer who added one project entry silently lost all sixteen
        # shape-based protections — `.env`, auth, migrations, CI — and the gate's stakes
        # axis then read green on an auth diff. That is the one silent-narrowing path in
        # a module whose entire stated thesis is that every uncertain path escalates, and
        # documenting it in the schema (the first attempt) does not make it safe: nobody
        # reads a slot description while deleting a line from an array.
        #
        # Narrowing is not a capability worth having here. Over-flagging costs one
        # unnecessary human decision; under-flagging costs the gate, silently. A project
        # that genuinely wants a default relaxed can say so at the gate, where a human
        # sees it, rather than by quietly shrinking a list.
        merged = list(DEFAULT_SENSITIVE_PATHS)
        merged.extend(p for p in cleaned if p not in merged)
        return merged, "config+defaults", warnings
    else:
        warnings.append(
            f"{PREFIX} ⚠️ flow.config.json.sensitivePaths is present but empty. An empty list "
            f"would classify EVERY diff as low-stakes, so it is treated as unset and the "
            f"documented defaults apply. If you meant 'nothing is sensitive here', say so in "
            f"the plan and waive at the gate — do not express it as an empty slot."
        )
        return list(DEFAULT_SENSITIVE_PATHS), "default-after-error", warnings


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
        ng = _normalize(g)
        # Same directory rule as the intensional probe: a bare `src/auth` owns
        # `src/auth/**`, and matching it literally would find nothing (a directory is
        # not a tracked path) and report the glob as empty.
        if ng and not ng.endswith(("*", "?")):
            ng = ng.rstrip("/") + "/**"
        rx = re.compile(_glob_to_regex(ng))
        hits = [t for t in norm_tracked if rx.match(t)]
        if hits:
            matched.extend(hits)
        else:
            empty.append(g)
    return sorted(set(matched)), empty


def glob_names_sensitive_area(glob: str, patterns) -> bool:
    """Does this owned glob, *as declared*, name a sensitive area?

    The greenfield question needs a real answer, not a blunt one. A worker dispatched
    to CREATE files owns a glob matching nothing today, so the extensional check
    ("what does it own now?") cannot see the work — but answering a flat "sensitive"
    for every such glob floors *all* greenfield work to the top tier, which is the
    over-spending failure the routing policy names as explicitly as under-dispatching.
    `docs/**` and `db/migrations/**` are both empty on a fresh tree; they are not the
    same question.

    So the probe substitutes a NEUTRAL filler for each wildcard and asks whether the
    resulting path is sensitive. `db/migrations/**` → `db/migrations/x` → sensitive.
    `docs/**` → `docs/x` → not. This tests the glob's own literal structure, which is
    exactly what `sensitivePaths` asks of a path.

    **The deliberate residual, stated rather than hidden:** a broad glob like `src/**`
    answers False even though a worker could later create `src/auth/`. Substituting
    sensitive segments INTO wildcards instead would answer True for `src/**` — and
    also for `docs/**`, and for every other `**` glob, because `**` admits any
    segment. That check would be indistinguishable from the flat rule it replaced.
    The residual is bounded rather than open: the plan gate's stakes axis re-evaluates
    against the ACTUAL changed files before anything merges, so an over-broad
    declaration that turns out to touch gate machinery is caught there. Routing is
    the cheaper, earlier signal; the gate is the one that must not be wrong.
    """
    g = _normalize(glob)
    if not g or not g.strip("*?/"):
        # An empty glob, or one made only of wildcards, names the WHOLE TREE — which
        # necessarily includes every sensitive area. Owning the entire repository is the
        # least low-stakes ownership there is.
        return True

    # Two spellings of one scope. `src/auth` and `src/auth/**` name identical ownership,
    # and the bare form is the one a human writes by hand — without it `src/auth`,
    # `db/migrations`, `secrets` and `.github/workflows` all answered False, because
    # `**/auth/**` compiles to `(?:[^/]+/)*auth/.*` and needs a trailing segment. Those
    # directories are live and populated, and `expand_globs` misses them too (a directory
    # is not itself a tracked path), so both checks said "not sensitive."
    #
    # But a bare form is not always a directory: `config/*.sql` is a file pattern. So both
    # candidates are generated and **each is matched against its OWN regex**. Deriving one
    # regex and probing the other is what broke `config/*.sql` — it was compiled as
    # `config/*.sql/**`, which its own probe could never satisfy.
    candidates = {g}
    if not g.endswith(("*", "?")):
        candidates.add(g.rstrip("/") + "/**")

    compiled_pats = [re.compile(_glob_to_regex(_normalize(pat))) for pat in patterns]
    for c in candidates:
        crx = re.compile(_glob_to_regex(c))
        for depth in (1, 2):
            probe = c.replace("**", "/".join(["x"] * depth))
            probe = probe.replace("*", "x").replace("?", "x")
            probe = re.sub(r"/+", "/", probe).strip("/")
            if not probe or not crx.match(probe):
                continue
            if any(prx.match(probe) for prx in compiled_pats):
                return True
    return False


def classify(paths, patterns) -> dict:
    """Return {'sensitive': bool, 'matches': [{'path','pattern'}...]}.

    A path is sensitive if ANY pattern matches it. Every match is reported, not
    just the first, because the escalation text has to name *why* a diff is
    high-stakes and one reason is rarely the whole story.
    """
    # No try/except on compile: every character outside the three wildcards is escaped,
    # so translation cannot produce an INVALID pattern. What it can produce is a
    # pathological one, which is what `_pattern_is_safe` refuses — and refusing is the
    # escalating direction, consistent with the rest of the module.
    compiled = []
    unsafe = []
    for pat in patterns:
        ok, reason = _pattern_is_safe(pat)
        if not ok:
            unsafe.append({"pattern": pat, "reason": reason})
            continue
        compiled.append((pat, re.compile(_glob_to_regex(pat))))
    matches = []
    for raw in paths:
        norm = _normalize(raw)
        if not norm:
            continue
        for pat, rx in compiled:
            if rx.match(norm):
                matches.append({"path": norm, "pattern": pat})
    result = {"sensitive": bool(matches), "matches": matches}
    if unsafe:
        # A refused pattern might have been the one protecting this diff, so the only
        # honest answer is sensitive — and say which, so it can be fixed rather than
        # silently tolerated.
        result["sensitive"] = True
        result["unsafe_patterns"] = unsafe
        result["reason"] = (
            "one or more sensitivePaths patterns were refused as pathological ("
            + "; ".join(f"{u['pattern']!r}: {u['reason']}" for u in unsafe[:3])
            + ") — classified sensitive rather than matched against a pattern that could hang the gate"
        )
    return result


def _failsafe(source, reason):
    """The one shape every degraded path emits. Written once because it was written
    out three times and a fourth was about to be added."""
    return {"sensitive": True, "matches": [], "pattern_source": source, "reason": reason}


def _failsafe_msg(what):
    return f"{PREFIX} ⚠️ {what}; classified SENSITIVE rather than guessed."


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
            print(json.dumps(_failsafe(source, "owned-glob list unreadable"), indent=2))
            return 0
        import subprocess  # local: this is the only path that needs the repo index
        try:
            proc = subprocess.run(
                ["git", "ls-files"], capture_output=True, text=True, timeout=60
            )
            # A non-zero exit does NOT raise, and the failure modes are quiet ones:
            # not a repo, a dubious-ownership refusal, an unreadable index. Left
            # unchecked, stdout is empty, every owned glob "matches nothing", and
            # classify([]) returns sensitive:false — the module's stated fail-safe
            # direction inverted, on the one path that feeds /flow:spawn's routing
            # floor. Treat it exactly like the OSError below.
            if proc.returncode != 0:
                raise OSError(
                    f"git ls-files exited {proc.returncode}: "
                    f"{(proc.stderr or '').strip()[:200] or 'no stderr'}"
                )
            tracked = proc.stdout.splitlines()
        except (OSError, subprocess.SubprocessError) as exc:
            print(
                f"{PREFIX} ⚠️ could not enumerate tracked files ({exc}); owned globs cannot be "
                f"expanded, so this is classified SENSITIVE rather than guessed.",
                file=sys.stderr,
            )
            print(json.dumps(_failsafe(source, "git ls-files unavailable"), indent=2))
            return 0
        if not globs:
            # An EMPTY owned-glob set is not "this worker owns nothing sensitive" — it is
            # "nobody told me what this worker owns." /flow:spawn's template writes the file
            # with a `printf` whose substitution may not have happened, producing exactly
            # this, and the result would route a worker with UNDECLARED scope down a tier.
            # `gate-classify` already handles the sibling case correctly in-process ("no
            # file list is not 'nothing is sensitive'"); the CLI must agree.
            print(_failsafe_msg("owned-glob list is empty"), file=sys.stderr)
            print(json.dumps(_failsafe(source, "owned-glob list is empty — asked about nothing, "
                                              "classified sensitive rather than guessed"), indent=2))
            return 0
        expanded, empty = expand_globs(globs, tracked)
        result = classify(expanded, patterns)
        result["pattern_source"] = source
        result["expanded_from_globs"] = len(expanded)
        result["globs_matching_nothing"] = empty
        # Only the unmatched globs that could REACH a sensitive pattern escalate.
        # A `docs/**` that does not exist yet is genuinely low-stakes; a
        # `db/migrations/**` that does not exist yet is the one-way door.
        reaching = [g for g in empty if glob_names_sensitive_area(g, patterns)]
        result["globs_matching_nothing_but_sensitive_shaped"] = reaching
        if reaching and not result["sensitive"]:
            # A glob matching nothing TODAY is the greenfield case, and it is the
            # single likeliest way this predicate is asked about one-way-door work:
            # a worker dispatched to CREATE `db/migrations/**` or `src/auth/**` owns
            # a glob that matches no tracked file yet. Answering `false` there is the
            # one fail-OPEN this module would otherwise have — and `/flow:spawn`'s
            # floor reads the machine-readable field, not the stderr line, so a
            # warning alone would leave the guarantee resting on someone remembering.
            #
            # `expand_globs` silently converts spawn's INTENSIONAL question ("could
            # this worker touch gate machinery?") into an extensional one ("what does
            # it own today?"). When the two can diverge, say so instead of returning
            # the weaker answer under the stronger question's name.
            result["sensitive"] = True
            result["reason"] = (
                f"{len(reaching)} owned glob(s) match no tracked file yet but COULD admit a "
                f"sensitive path ({', '.join(reaching[:5])}) — the work may CREATE files under "
                f"them, which cannot be evaluated from the current tree. Classified sensitive "
                f"rather than guessed."
            )
            print(f"{PREFIX} ⚠️ {result['reason']}", file=sys.stderr)
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
        print(json.dumps(_failsafe(source, "changed-file list unreadable"), indent=2))
        return 0

    files = [ln for ln in raw.splitlines() if ln.strip()]
    if not files:
        # Same rule on the files side: an empty changed-file list means the caller could
        # not tell us what changed, not that nothing sensitive changed.
        print(_failsafe_msg("changed-file list is empty"), file=sys.stderr)
        print(json.dumps(_failsafe(source, "changed-file list is empty — asked about nothing, "
                                           "classified sensitive rather than guessed"), indent=2))
        return 0
    result = classify(files, patterns)
    result["pattern_source"] = source
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
