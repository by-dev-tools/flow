#!/usr/bin/env python3
r"""Which doc-shaped paths carry deployed BEHAVIOUR — one definition, several readers.

Prose is deployed surface in a flow-shaped repo: a skill's SKILL.md and an agent's system
prompt ARE the product, and `CLAUDE.md` says so outright ("Prompt changes are code changes").
But `sourceFilePatterns` — the ruler every source-sensitive gate uses — matches no `.md` path
at all, by design: it is what keeps a docs-only PR from tripping the source-touching branches
of `/flow:ship`. So "is this file source?" and "does this file carry behaviour?" are two
different questions, and this module owns the second one.

Two readers today, which is the whole reason it exists as a module (`general.md` item 2 — a
contract spelled in two places where a change touches one):

  - `/flow:audit-coverage`'s evidence block, which unions doc matches back into the file list
    after the source filter so behaviour-bearing prose reaches the reviewer (CV1, v1.55.0).
    That reader is a shell block and keeps its own `DOC_BUILTIN=` literal, with
    `evals/run_rigor_marker_evals.py` asserting the two are byte-identical. **The reason is
    fail-safe direction, not inability** -- that block already invokes `python3` twice, and the
    sibling `sensitive_paths.py` ships a `--print-defaults` CLI for exactly this. But a shelled-out
    read degrades to an EMPTY pattern when python3 is missing, and `grep -E ""` matches every line,
    so the gate would announce every changed file as deployed prose. The literal fails safe where
    a subprocess fails open; that is why it is duplicated rather than fetched.
  - `/flow:ship`'s rigor fingerprint via `skills/ship/lib/rigor-marker.py` (CV1 follow-up),
    which was computed through `sourceFilePatterns` alone — so on #172, 0 of 13 changed `.md`
    files were in it and both changed SKILL.md files could have been rewritten after
    staff-review with the gate still reading "ok".

**What `DOC_BUILTIN` does and does not mean — measured, because the name oversells it.** It is
three directory NAMES matched anywhere in a path, not "every shipped prose surface". On #172's
13 changed `.md` files the union covers 3, and the boundary is ragged in both directions:

  - it MISSES `plugins/flow/docs/workflow.md`, which is shipped consumer documentation, and
    `README.md`, which is the marketplace page. Under-inclusion is the unsafe direction: those
    files can still change after staff-review without moving the fingerprint.
  - it MATCHES `.claude/rules/general.md` and would match `.claude/skills/*/SKILL.md` — this
    repo's project-dev infra, which is not shipped at all. Over-inclusion only costs an extra
    human decision at the gate, so it is the safe direction, and a rule file genuinely does
    change how sessions behave even when it ships to nobody.

Widening it is a live decision, deliberately NOT taken here: `docs/` would pull in every
consumer's `docs/` tree, and the right boundary is a config question rather than a guess. That
is what `behaviorBearingDocPatterns` is for, and a consumer who needs `docs/` can say so today.

**Deletion criterion (FB-0088):** delete when it has fewer than two readers — fold the
constant back into whichever one survives rather than keeping a shared module for a single
caller. Today: two (the coverage block's literal, pinned byte-identical; the rigor fingerprint).

Stdlib only. Python 3.7+.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

# Byte-identical to the `DOC_BUILTIN=` literal in audit-coverage/SKILL.md's evidence block.
# Valid in BOTH POSIX ERE (grep -E) and Python re, and meaning the same thing in each: keep it
# that way, because the two readers are a shell block and this module. Pinned by an eval.
DOC_BUILTIN = r"(^|/)(skills|agents|rules)/.*\.md$"

# The consumer-configurable extension. Empty by default (CV1): a repo whose prose is not
# behaviour-bearing pays nothing, and a repo whose prose is says where it lives.
SLOT = "behaviorBearingDocPatterns"

# Warning prefix, matching the sibling shared lib in this directory (`sensitive_paths.py`'s
# `PREFIX`) so two libs doing the same slot-reading job do not grow two warning vocabularies.
# The `⚠️` is required by CLAUDE.md for a config-slot degrade, not decoration.
PREFIX = "[doc-patterns]"

# Guard against a pasted essay rather than a pattern. Long ERE alternations are legitimate, so
# this is deliberately generous; it exists so a corrupt config cannot be compiled at all.
MAX_SLOT_LEN = 2000


def repo_root(default: str = ".") -> str:
    """Worktree root, or `default` when there is no enclosing git repo."""
    try:
        out = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                             capture_output=True, text=True, timeout=15)
        root = out.stdout.strip() if out.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        root = ""
    return root or default


def _refuse(reason: str) -> "tuple[str, list[str]]":
    """One refusal shape: ("", [one warning]).

    Five branches below used to spell the prefix, the sigil and the consequence clause
    themselves, and the fifth had ALREADY drifted ("doc coverage is the builtin set only" vs
    "falls back to the built-in set (<value>) only") — four copies of a sentence and one of them
    wrong, in the module whose whole purpose is to stop a contract being spelled twice. Each
    branch now supplies only its distinguishing clause.
    """
    return "", [f"{PREFIX} [WARN] ⚠️ {reason} — it was NOT applied, so doc coverage falls back "
                f"to the built-in set ({DOC_BUILTIN}) only."]


def read_slot(root: str | None = None) -> "tuple[str, list[str]]":
    """Read `behaviorBearingDocPatterns` from flow.config.json. Returns (pattern, warnings).

    An absent file or absent slot is the documented default and warns about nothing — that is
    the common case and a warning there would be noise. Every OTHER failure warns: a config
    that exists but cannot be parsed, a slot that is not a string, one that is absurdly long,
    and one that is not a valid regex. The fingerprint stays computable in all of those (the
    builtin half survives), so a config typo must never be allowed to quietly restore the
    doc-blind gate it was supposed to close (`general.md` item 1 — pair every fallback with a
    loud branch).
    """
    cfg = Path(root if root is not None else repo_root()) / "flow.config.json"
    if not cfg.is_file():
        return "", []
    try:
        data = json.loads(cfg.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        return _refuse(f"flow.config.json is unreadable or not valid JSON ({e})")
    if not isinstance(data, dict):
        return _refuse("flow.config.json is not a JSON object")

    raw = data.get(SLOT, "")
    if raw in ("", None):
        return "", []
    if not isinstance(raw, str):
        return _refuse(f"{SLOT} is {type(raw).__name__}, not a string")
    try:
        re.compile(raw)
    except re.error as e:
        # Kept even though the effective-union compile in `doc_pattern` would also reject this:
        # the slot-alone error names the position in the VALUE the operator wrote, where the
        # union's error points into a concatenation they never typed.
        return _refuse(f"{SLOT} is not a valid regex ({e}); pattern was {raw[:120]!r}")
    return raw, []


# Nested quantifier shapes -- `(a+)+`, `(x*)*` -- are the classic catastrophic-backtracking
# trigger. The SHELL side bounds the identical hazard with `timeout 5`, and GNU grep's DFA is
# immune anyway, so this Python reader is the only unbounded one. A heuristic, and labelled as
# one: a cheap refusal of the known-bad shape, not a proof of termination.
_NESTED_QUANTIFIER = re.compile(r"\([^()]*[+*][^()]*\)\s*[+*]")


def doc_patterns_list(
    slot: str | None = None, root: str | None = None
) -> "tuple[list, list[str]]":
    """The built-in set plus the configured slot, as SEPARATELY COMPILED patterns.

    Returns `(patterns, warnings)`; match with `any(p.search(path) for p in patterns)`.

    **Separate compiles, not a union string, and that is the whole design.** The first version
    returned one concatenated expression, and every hazard it then had to refuse came from the
    concatenation itself: an inline `(?i)` is legal mid-pattern alone but mid-UNION it either
    raises (Python 3.11+) or — measured on 3.9 — applies to every other clause, so a slot could
    silently make the consumer's whole `sourceFilePatterns` case-insensitive. Compiled on its own,
    that same `(?i)` scopes to its own pattern and does exactly what the consumer asked for. So
    the inline-flag refusal and the union-compile refusal are both GONE rather than hardened,
    and a caller can no longer build a third expression nobody validated.

    This also makes the Python reader structurally match the shell one in
    `audit-coverage/SKILL.md`, which has always applied `DOC_BUILTIN` and the slot as separate
    `grep -E` invocations.

    The nested-quantifier refusal stays: it is about unbounded backtracking in THIS reader
    (which has no match timeout, where the shell side has `timeout 5`), not about concatenation.
    """
    warnings: list[str] = []
    if slot is None:
        slot, warnings = read_slot(root)
    # VALUE-SHAPE refusals live here, not in `read_slot`, so they apply on BOTH entry paths.
    # The length cap used to sit on the config path only, so a caller passing `slot=` directly
    # bypassed it -- an asymmetry found by the eval written for this very ladder, after
    # /flow:audit-coverage flagged the ladder as undeclared at this PR's merge gate.
    if slot and len(slot) > MAX_SLOT_LEN:
        slot, extra = _refuse(f"{SLOT} is {len(slot)} chars (cap {MAX_SLOT_LEN})")
        warnings.extend(extra)
    if slot and _NESTED_QUANTIFIER.search(slot):
        m = _NESTED_QUANTIFIER.search(slot)
        slot, extra = _refuse(
            f"{SLOT} contains a nested quantifier ({m.group(0)}); this reader has no match "
            f"timeout and that shape can backtrack unboundedly")
        warnings.extend(extra)

    pats = [re.compile(DOC_BUILTIN)]
    if slot:
        try:
            pats.append(re.compile(slot))
        except re.error as e:  # pragma: no cover - read_slot already compiled it
            _, extra = _refuse(f"{SLOT} failed to compile ({e})")
            warnings.extend(extra)
    return pats, warnings
