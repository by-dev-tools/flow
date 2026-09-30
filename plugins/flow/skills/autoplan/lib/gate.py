#!/usr/bin/env python3
"""
Deterministic engine behind `/flow:autoplan` — D1 Phase 3
(`dev-docs/handoffs/d1-prototype-first-gate.md` § Phase 3; gated on § 9.3,
resolved MIXED by #153).

D1 Phase 2 moved a UI change's first human gate from the plan to a prototype.
Phase 3 is the other half: after that gate, the technical plan is auto-written
against the approved prototype and reviewed by MACHINE rather than by a human.

  depth             Resolve union depth from `trigger`'s resolved PATH, and the
                    honesty string that must accompany it.
  arm-a             Criterion quality. Deterministic, hard gate. Reads the two
                    tools' OUTPUT, never their exit status.
  union             Union N coverage passes, dedupe by cited symbol. The finder
                    wins; nothing averages.
  gate              The combination rule. Green requires every arm to have RUN.
  render-decisions  The `[decision-required]` escalation, in FB-0075's shape.

THE RULE THE WHOLE FILE EXISTS TO HOLD, stated once:

    A GREEN verdict requires every arm to have RUN, evidenced, and returned
    nothing. Absence of findings is NEVER by itself a pass.

`/flow:audit-coverage` has perfect precision across every measured run and
recall between 60% and 100% (#160: source-mode single-run mean 82%, union of 4
= 100%). So a flag is reliable evidence and SILENCE IS EVIDENCE OF NOTHING. A
gate keyed on "the reviewer found nothing" would report clean over exactly the
half of the surface nobody declared — the failure this engine is organised
against, and the reason every "did not run" path below keeps a reason distinct
from "ran and found nothing" rather than collapsing into one falsy check.

That distinction is FB-0121's contract (*a stage that did not run is red, not
clean*) arriving from a different direction, and it is why `ran` is a required
field rather than an inference from an empty `findings` list.
"""
from __future__ import annotations

import json
import subprocess
import sys
import textwrap
from pathlib import Path

SCHEMA_VERSION = 1

# The escalation header. It is the SHIPPED wording, copied deliberately from
# `skills/ship/lib/manifest-triage.py::render_decisions`, whose emitted header is
# `**Decisions for you** — answer by number.` Two spellings of one user-facing
# contract is the fan-out class (.claude/rules/general.md § Consistency item 2), so
# `evals/run_autoplan_evals.py::test_escalation_header_matches_shipped` READS that
# file and asserts equality rather than restating the string here a second time.
#
# The trailing clause differs on purpose and must not be unified: the shipped one
# promises this "takes the PR closer to ready", and at this gate NO PR EXISTS YET.
# Reusing `render_decisions` itself was considered and rejected — it consumes a draft
# manifest (`result["residual"]`, `class in {ask,auto,blocked}`, `kind` against
# KIND_COPY) that has no meaning before a PR. Unifying the two engines behind one
# entry shape is roadmap D1f; unifying the WORDING is free and is done here.
# The trailing clause is NOT part of the constant: whether anything else is blocked
# is a property of the run, and baking "Nothing else is blocked." in here is how the
# header came to promise that while blockers sat listed above it.
DECISION_HEADER = (
    "**Decisions for you** — answer by number. I apply your answer and re-run the\n"
    "check; if it passes, Execute starts."
)

# Depth keys on `trigger`'s resolved PATH, never on `Mode`. Keying on Mode opens two
# holes /flow:critique-plan found: `Mode: spike` resolves to no declared depth at all,
# and a `Mode: feature` change the trigger sends to `classic` would claim depth 2 while
# Arm B has no prototype source to read. An undeclared depth is precisely the "ran and
# found nothing" vs "did not run" ambiguity this file forbids, reintroduced through the
# routing table.
#
# Only ONE path runs Phase 3, and that is the honest shape: the machine gate is the
# counterpart of the MOVED human gate, one for one. `collapsed` and `classic` both keep
# `pre_execution_gate: "plan"` — the human still gates that plan — so there is nothing
# for a machine gate to replace, and no approved prototype for Arm B to read either way.
_DEPTH_BY_PATH = {
    "prototype-first": 2,
    "collapsed": None,
    "classic": None,
}

# Stated whenever depth is reported. Only 1 and 4 are measured; 2 is interpolation
# chosen to buy most of the curve at half the cost. The output never claims a figure
# for a depth nobody measured, so a wrong default misstates nothing.
_DEPTH_HONESTY = (
    "2 passes unioned. Measured basis: 1 pass ≈ 82%, 4 passes = 100% on the "
    "reference case; 2 is between and unmeasured."
)

_NOT_APPLICABLE = (
    "No approved prototype exists, so there is no source to read, and the human "
    "still gates this plan."
)


class SecurityRefusal(Exception):
    """A path refused by `_safe_path`. Surfaced as a clean refusal, never a traceback."""


# Bidi controls reorder the VISUAL rendering of everything after them — Trojan Source,
# CVE-2021-42574 — so they forge a rendered line without emitting a single escape byte.
# A C0/C1 filter alone misses them entirely, which left the scrubber at roughly 80% of
# its own stated goal: `\x1b[2K` erases the line, `\u202e` rewrites it in place and the
# three escape-byte assertions never fire. U+2028/U+2029 are line/paragraph separators
# that some renderers treat as breaks, so they go too.
_BIDI = frozenset(
    [0x200E, 0x200F, 0x2028, 0x2029] + list(range(0x202A, 0x202F)) + list(range(0x2066, 0x206A))
)


def _scrub(text) -> str:
    """Strip terminal control characters from text that will be PRINTED to a human.

    The escalation's fields (`finding`, `drafted_resolution`, `why`, `provenance`)
    originate in a JSON file whose contents can come from a reviewer reading an
    untrusted branch's source — an Arm B finding keys on a `symbol` lifted out of
    that code. An embedded `\r` or CSI sequence can erase or overwrite lines in the
    rendered block, which is precisely the text a human is being asked to make a
    decision from: forging the question is at least as useful to an attacker as
    forging the answer.

    Keeps `\n` and `\t` (the renderer's own structure) and drops the rest of C0/C1.
    `ship/lib/manifest-triage.py` has the same exposure and no such filter; this is
    the narrow fix for the surface this PR adds, and the shared helper is filed with
    the `_safe_path` hoist rather than done here mid-ship.
    """
    if not isinstance(text, str):
        text = "" if text is None else str(text)
    return "".join(
        ch for ch in text
        if ch in "\n\t"
        or (ord(ch) >= 0x20 and not 0x7F <= ord(ch) <= 0x9F and ord(ch) not in _BIDI)
    )


def _clip(text: str, n: int) -> str:
    """Truncate with a marker. A criterion cut mid-word at 60 chars reads as a
    malformed criterion rather than a truncated one."""
    text = text or ""
    return text if len(text) <= n else text[: n - 1].rstrip() + "…"


def _emit(obj) -> int:
    obj.setdefault("schema", SCHEMA_VERSION)
    json.dump(obj, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


def _repo_root(start: Path) -> Path:
    """The repository containing `start`, or its directory if there is no repo.

    The confinement boundary has to be a real one. An earlier draft derived it as
    `path.resolve().parent`, which makes the containment test true by construction --
    a resolved path is always relative to its own parent -- so the traversal half of
    this guard was a no-op that could only ever pass, while the docstring claimed it
    stopped `../../..`. Caught by `/simplify`'s reuse lens. A check that cannot fail
    is not a check (`.claude/rules/general.md` § Consistency item 4), and writing one
    into the security guard of the gate built to catch that class is the version of
    the mistake worth recording rather than quietly correcting.
    """
    try:
        out = subprocess.run(
            ["git", "-C", str(start), "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=10,
        )
        if out.returncode == 0 and out.stdout.strip():
            return Path(out.stdout.strip()).resolve()
    except (OSError, subprocess.SubprocessError):
        pass
    return start.resolve()


def _safe_path(path: Path, what: str) -> Path:
    """Refuse a symlink, a symlinked ancestor, and a path outside the repository.

    CWE-59, the same guard `prototype-gate.py` and `ship/lib/manifest-triage.py`
    already hold for their producer files -- not a new invention. Every input this
    engine reads is a path some caller supplied, and under the #165/FB-0116 idiom a
    caller's path can originate in `$ARGUMENTS`, i.e. in text this process does not
    control. So the boundary is the REPOSITORY, matching the rule `/flow:review-brief`
    states in prose: refuse "a path that is absolute and outside the repository, or
    contains `..`".

    Outside a repo the boundary degrades to the path's own directory, which confines
    nothing -- stated rather than implied, because the alternative (hardcoding an
    absolute `.flow/`) is what made an earlier draft of the sibling refuse every
    legitimate run outside a repo: a gate failing closed on its own users.

    NOT hoisted to `plugins/flow/lib/` in this PR, though that is where it belongs and
    where `sensitive_paths.py` set the one-definition-two-readers precedent. This is
    the third copy in the tree and they have already drifted; unifying them edits a
    second shipped engine and its 277-check harness mid-ship. Filed as a follow-up.
    """
    if path.is_symlink():
        raise SecurityRefusal(
            "%s is a symlink (%s) — refusing to follow it, because a read through it "
            "returns whatever the link points at rather than what you named (CWE-59). "
            "→ Pass the real file instead of the link, or replace the link with the "
            "file itself. If you meant to review the link's target, name that target "
            "directly so the path you get is the path you asked for." % (what, path)
        )
    # Anchored on the process's OWN repository, never derived from the path under
    # test. Deriving it from the argument is how this guard was wrong twice: first as
    # `path.resolve().parent` (tautology), then as `_repo_root(path.parent)`, which
    # "confined" /etc/hostname to /etc and accepted it. A boundary computed from the
    # thing it is supposed to bound is not a boundary. Both were caught by running the
    # guard against a path that MUST be refused, which is the only reason either was
    # visible -- neither showed up as a failing test, because both versions passed.
    base = _repo_root(Path.cwd())
    # Resolve ONCE. The earlier version called path.resolve() again inside the
    # except-handler while formatting its message — so a path that cannot resolve at
    # all (an embedded NUL) raised a SECOND time from the error path and escaped as a
    # traceback with no JSON on stdout, breaking this file's stated contract twice
    # over ("a clean refusal, never a traceback"). Only reachable since --plan-from:
    # execve forbids NUL in argv, so before the file channel no caller could deliver
    # one. An error handler that can itself fail is not an error handler.
    try:
        resolved = path.resolve()
    except (ValueError, OSError) as exc:
        raise SecurityRefusal(
            "%s is not a resolvable path (%s) — refusing rather than acting on it. "
            "→ Check the value for stray bytes (a NUL or a truncated write is the "
            "usual cause) and re-write the argument file with the plain path."
            % (what, exc))
    try:
        resolved.relative_to(base)
    except ValueError:
        raise SecurityRefusal(
            "%s resolves to %s, which is outside %s — refusing, because this engine "
            "reads and executes only within the repository it is run from, and a path "
            "that escapes it is either a mistake or an attempt to steer the gate at "
            "someone else's files. → Either pass a path inside that repository, or "
            "re-run the gate from the repository the file actually belongs to (the "
            "boundary is taken from your current directory, not from the path)."
            % (what, resolved, base)
        )
    except SecurityRefusal:
        raise
    except Exception:  # noqa: BLE001 - an unresolvable path must not fail OPEN
        raise SecurityRefusal(
            "%s could not be confined to %s — refusing rather than acting on an "
            "unverified path. → Re-run from inside the repository that holds the file." % (what, base)
        )
    # No symlinked-ancestor loop here, deliberately, and the reason is worth keeping:
    # there WAS one, over `resolved.parents`, and `Path.resolve()` has already
    # collapsed every symlink by that point, so `parent.is_symlink()` was constantly
    # False. That made it the THIRD tautology found in this one function — after
    # `base = path.resolve().parent` and `_repo_root(path.parent)` — each of which
    # passed every test it had. An ancestor symlink that escapes the repository is
    # caught by the `relative_to(base)` check above, on the RESOLVED path, which is
    # the guard that actually does this work; one that stays inside the repository
    # lands somewhere the caller already controls. A loop that cannot fire is worse
    # than no loop: it reads as defence and provides none.
    return path


def _read_json(path: Path, what: str):
    """Read a JSON input file, failing CLOSED with a reason rather than a traceback."""
    _safe_path(path, what)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise SecurityRefusal("%s could not be read as JSON (%s): %s. → Check the file exists and parses "
            "(`python3 -m json.tool <path>`); the producer may have written a partial file."
            % (what, path, exc))


# --------------------------------------------------------------- depth


def resolve_depth(trigger: dict) -> dict:
    """Union depth from the trigger's RESOLVED path.

    An unrecognized path is not given a default. A depth nobody declared is the
    ambiguity this engine exists to forbid, so an unknown path refuses.
    """
    path = trigger.get("path")
    if path not in _DEPTH_BY_PATH:
        return {
            "ok": False,
            "path": path,
            "depth": None,
            "applies": False,
            "reasons": [
                "trigger resolved no recognized path (got %r) — refusing to assume a "
                "depth. A depth nobody declared cannot be distinguished later from a "
                "procedure that did not run." % (path,)
            ],
        }
    depth = _DEPTH_BY_PATH[path]
    if depth is None:
        return {
            "ok": True,
            "path": path,
            "depth": None,
            "applies": False,
            "reasons": [
                "Phase 3 does not apply on the %s path: it keeps "
                "pre_execution_gate='plan'. %s" % (path, _NOT_APPLICABLE)
            ],
        }
    return {
        "ok": True,
        "path": path,
        "depth": depth,
        "applies": True,
        "honesty": _DEPTH_HONESTY,
        "reasons": [],
    }


# --------------------------------------------------------------- Arm A


def _run(cmd, stdin_text=None):
    try:
        proc = subprocess.run(
            cmd, input=stdin_text, capture_output=True, text=True, timeout=120
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return None, "could not run %s: %s" % (cmd[:2], exc)
    return proc, None


def _a_did_not_run(msg: str) -> dict:
    """The one place Arm A's `ran: False` ⇒ `verdict: RED` invariant is written.

    It was re-typed at seven return sites, which is the fan-out class this file's own
    docstring is organised against: an eighth branch could get it wrong silently.
    """
    return {"arm": "A", "ran": False, "verdict": "RED", "reasons": [msg]}


def _load_is_pinned(lib_root: Path):
    """Import `walk-pin-lint.py`'s own `is_pinned` predicate.

    ONE definition of "what counts as a pin", not two. An earlier draft spawned the
    lint as a subprocess, fed it a SYNTHETIC single-block document, and screen-scraped
    an integer out of its human-readable stdout. That paid a prose coupling for a
    function call: the parser keyed on the substring "carry a named pin" and an
    em-dash-delimited number, so rewording one sentence in the lint would have turned
    Arm A RED with "DID NOT RUN" on every plan. It also bought nothing from the
    subprocess, because feeding a synthetic doc already bypassed every part of the
    lint except this predicate.

    The same rationale `walk-pin-lint.py` itself gives for importing `walk_extract`
    rather than re-implementing block parsing, and the one `CLAUDE.md` gives for
    `visual-significance.py` and `manifest_contract.py`: one definition, N readers.
    The shipped CLI and `/flow:critique-plan` are untouched — this reads the module,
    it does not change it.

    `importlib` rather than `import`, because the filename is hyphenated.
    """
    import importlib.util

    target = lib_root / "critique-plan" / "lib" / "walk-pin-lint.py"
    if not target.exists():
        raise SecurityRefusal("walk-pin-lint.py not found at %s. → Point --lib-root at a tree containing "
                              "critique-plan/lib/, or drop the flag to use the installed plugin." % target)
    spec = importlib.util.spec_from_file_location("_walk_pin_lint", target)
    if spec is None or spec.loader is None:
        raise SecurityRefusal("walk-pin-lint.py at %s could not be loaded. → It must be importable Python; "
                              "check it parses before pointing the gate at it." % target)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    fn = getattr(mod, "is_pinned", None)
    if not callable(fn):
        raise SecurityRefusal(
            "walk-pin-lint.py at %s exposes no is_pinned() predicate — refusing to "
            "guess what counts as a pin. → Use a tree whose walk-pin-lint.py "
            "still defines is_pinned(), or drop --lib-root." % target
        )
    return fn


def arm_a(plan_path: Path, expect_line=None, lib_root: Path | None = None) -> dict:
    """Criterion quality. Deterministic hard gate.

    Reads each tool's OUTPUT, never its exit status, and that is load-bearing rather
    than stylistic. Measured: `criterion-specificity.py` exits 0 while reporting a
    vacuous criterion, and `walk-pin-lint.py` documents "Exit codes: 0 for every lint
    verdict (advisory — the critic assigns severity); nonzero only on crash-grade
    input errors." Neither has a red channel in `$?`, so an exit-code gate would be
    green on every input — a measurement that can only return "clean" is not a
    measurement (`.claude/rules/general.md` § Consistency item 4).

    The pinning half is scoped to the ACTIVE block, which falls out of asking the
    predicate about the extracted criteria directly: `walk-pin-lint.py`'s CLI is
    all-blocks by design ("a standalone plan DOCUMENT may legitimately carry
    several"), while `extract-criteria.py` is first-block-only. Unscoped, this arm
    fails every run in any repo that retains shipped blocks — measured on flow's own
    plan.md: 591 unpinned checkboxes across 71 blocks, none of them the author's to
    fix. A gate that is red for reasons nobody can fix is a gate that gets ignored.

    `lib_root` exists so the suite can point this at a stub tree and prove the
    fail-closed paths behaviourally. Without it the only way to test them is to grep
    this file for its own error strings, which passes if the sentence survives in a
    comment after the branch is deleted.
    """
    root = lib_root or Path(__file__).resolve().parent.parent.parent
    extract = root / "verify-build" / "lib" / "extract-criteria.py"
    specificity = root / "verify-build" / "lib" / "criterion-specificity.py"

    for tool in (extract, specificity):
        if not tool.exists():
            return _a_did_not_run(
                "Arm A tool missing: %s. The arm DID NOT RUN — this is distinct from "
                "running and finding nothing." % tool
            )

    proc, err = _run([sys.executable, str(extract), str(plan_path)])
    if err or proc.returncode != 0:
        return _a_did_not_run(
            "extract-criteria.py did not complete (%s). The arm DID NOT RUN."
            % (err or _clip((proc.stderr or "").strip(), 200))
        )
    try:
        extracted = json.loads(proc.stdout)
    except ValueError:
        return _a_did_not_run(
            "extract-criteria.py emitted unparseable JSON. The arm DID NOT RUN."
        )

    reasons: list[str] = []
    criteria = extracted.get("criteria") or []
    got_line = extracted.get("source_heading_line")

    # Which block did I grade? Keyed on the heading's LINE, the only field in the
    # extractor's contract that varies per block: in a plan retaining shipped blocks
    # every unqualified heading is the identical string `**Spec-walk:**` and
    # `block_count` is a file-wide total, so an assertion on those passes whether or
    # not the property holds — the "satisfiable by deletion" shape one step over.
    if expect_line is not None and got_line != expect_line:
        reasons.append(
            "Arm A graded the block at line %s, but the plan under review was "
            "recorded at line %s. A gate that cannot prove which document it graded "
            "is not a gate." % (got_line, expect_line)
        )

    if extracted.get("all_demoted"):
        reasons.append(
            "every Spec-walk block in the plan is qualified as already-shipped — "
            "there is no ACTIVE block, which is not the same as a plan with no "
            "criteria."
        )
    if not criteria and not extracted.get("all_demoted"):
        reasons.append("the active Spec-walk block declares no criteria.")

    # Vacuity — parsed from the pipe's JSON, not from its exit status. `proc.stdout`
    # is already exactly the bytes the consumer wants, so it is passed through rather
    # than re-serialized from the dict it was parsed into.
    vacuous: list = []
    unpinned: list = []
    if criteria:
        proc2, err2 = _run([sys.executable, str(specificity)], stdin_text=proc.stdout)
        if err2 or proc2.returncode != 0:
            return _a_did_not_run(
                "criterion-specificity.py did not complete. The arm DID NOT RUN."
            )
        try:
            vacuous = (json.loads(proc2.stdout) or {}).get("vacuous") or []
        except ValueError:
            return _a_did_not_run(
                "criterion-specificity.py emitted unparseable JSON. The arm DID NOT RUN."
            )
        if vacuous:
            reasons.append(
                "%d vacuous criterion/criteria: %s"
                % (len(vacuous), "; ".join(_clip(v.get("criterion", "?"), 60) for v in vacuous))
            )

        try:
            is_pinned = _load_is_pinned(root)
        except SecurityRefusal as exc:
            return _a_did_not_run(
                "the pinning predicate could not be loaded (%s) — the pinning check "
                "DID NOT RUN. Treating an unloadable predicate as zero unpinned would "
                "report clean over a measurement that never happened." % exc
            )
        unpinned = [c for c in criteria if not is_pinned(c)]
        if unpinned:
            reasons.append(
                "%d criterion/criteria in the ACTIVE block name no verification "
                "artifact." % len(unpinned)
            )

    return {
        "arm": "A",
        "ran": True,
        "verdict": "RED" if reasons else "GREEN",
        "criteria_count": len(criteria),
        "vacuous_count": len(vacuous),
        "unpinned_count": len(unpinned),
        "graded_line": got_line,
        "expected_line": expect_line,
        "reasons": reasons,
    }


# --------------------------------------------------------------- Arm B union


def union_passes(passes: list) -> dict:
    """Union N coverage passes, deduped by cited symbol. The finder wins.

    Given precision unblemished on every measured case, a disagreement between two
    passes has exactly ONE reading: the finder is right and the miss is a recall
    event, not counter-evidence.

    THE SCOPE OF THAT LICENCE, stated here because this is where a future author
    decides whether the union rule still holds: every measured case CONTAINED REAL
    GAPS. Precision on an input where silence is the correct answer has never been
    measured (`dev-docs/roadmap.md` § "Precision has never been measured on a case
    whose correct answer is silence"). That is the gate's MODAL input — a competently
    auto-written plan — and it is the case where one phantom finding would RED-gate a
    good plan with no human gate behind it. Agreement between passes is not
    independent corroboration either: both share the unmeasured axis. So this unions, never intersects, and never averages
    to "maybe". A finding present in 1 of 2 passes carries IDENTICAL standing to one
    present in 2 of 2 — same severity, same routing, same resolution requirement.
    `seen_in` is recorded as provenance and never touches the verdict.

    Unioning is only safe BECAUSE of the precision record; without it the same
    technique amplifies noise. The licence is the measurement, not the technique.
    """
    by_symbol: dict = {}
    order: list = []
    for i, p in enumerate(passes, 1):
        for f in p.get("findings") or []:
            symbol = (f.get("symbol") or f.get("finding") or "").strip()
            if not symbol:
                continue
            if symbol not in by_symbol:
                by_symbol[symbol] = dict(f)
                by_symbol[symbol]["seen_in"] = []
                order.append(symbol)
            by_symbol[symbol]["seen_in"].append(i)
    findings = [by_symbol[s] for s in order]
    for f in findings:
        n, total = len(f["seen_in"]), len(passes)
        f["provenance"] = (
            "Found by %d of %d coverage passes. That is not weaker evidence — on "
            "every case measured so far this reviewer has not reported a gap that "
            "was not real, so the other pass simply missed it. (Scope, stated "
            "because the bare claim overstates it: every measured case contained "
            "real gaps, so precision on an input where silence is the right answer "
            "is UNMEASURED.)" % (n, total)
            if n < total
            else "Found by all %d coverage passes — which is agreement, not "
                 "independent corroboration: both passes share the same unmeasured "
                 "axis (precision where silence is correct)." % total
        )
    return {"findings": findings, "passes": len(passes)}


# --------------------------------------------------------------- the gate


def _why_arm_cannot_pass(arm: dict) -> str | None:
    """Why this arm cannot count as a pass — or None if it genuinely ran.

    Every branch here keeps a DISTINCT reason. Collapsing "errored", "absent
    reviewer" and "document-blind" into one falsy check is what turns three
    different failures into the same silent clean.
    """
    name = arm.get("arm", "?")
    # An arm that reported its OWN verdict as RED. This is first because it was
    # missing entirely, and its absence was the worst defect in the first draft:
    # `arm-a` emits {arm, ran: true, verdict: "RED", reasons: [...]} and NO
    # `findings`, while this function read only ran/error/document_blind/reviewers
    # and the caller read only `findings`. So the one DETERMINISTIC arm — the only
    # one whose result the gate can trust without a model in the loop — reported RED
    # and the gate returned GREEN with "every arm ran, was evidenced, and returned
    # nothing". Reproduced end to end before fixing, and pinned by a test that feeds
    # `arm-a`'s literal output into `gate`, which is the composition the two
    # subcommands of this one engine previously had no test for.
    if str(arm.get("verdict", "")).upper() == "RED":
        why = "; ".join(arm.get("reasons") or []) or "no reason given"
        return (
            "Arm %s reported verdict RED — %s. An arm's own verdict is authoritative; "
            "the gate never overrides it. → Fix what it names, then re-run this arm."
            % (name, why)
        )
    if arm.get("error"):
        return (
            "Arm %s ERRORED (%s) — classified as DID NOT RUN, never as found nothing. "
            "A 429, a tool failure and an empty output are all absences of a review, "
            "not reviews that came back clean. → Re-run this arm; nothing about the plan has been judged yet." % (name, _clip(str(arm["error"]), 160))
        )
    if not arm.get("ran"):
        return (
            "Arm %s DID NOT RUN. This is distinct from running and finding nothing, and "
            "the two never collapse. → Run it, then re-run the gate." % name
        )
    if arm.get("document_blind"):
        return (
            "Arm %s ran DOCUMENT-BLIND — its reference-document load resolved zero "
            "documents, so it could not quote a project rule and cannot clear the "
            "Spec-violation category. A reviewer that cannot read the rules has not "
            "reviewed. → Fix the reference-document load (usually `referenceGlob`) "
            "and re-run this arm." % name
        )
    reviewers = arm.get("reviewers") or {}
    # An ABSENT roster is not an implicit pass. `if reviewers:` alone made "no record
    # of the fan-out" indistinguishable from "all three returned" — the same ambiguity
    # this module exists to forbid, and the likeliest way a dead spawn disappears,
    # since a model writes this file and an omitted key is the cheapest omission.
    # The sibling rule one function up already says an arm missing from the list
    # cannot have run; this is that rule applied one level down.
    if name == "C" and not reviewers:
        return (
            "Arm C reported no reviewer roster. Three dead spawns and three clean "
            "spawns produce the same zero findings, so an absent record is RED, not "
            "a pass. → Re-run Arm C and record each reviewer's outcome."
        )
    if reviewers:
        missing = sorted(k for k, v in reviewers.items() if v != "returned")
        if missing:
            return (
                "Arm %s is incomplete: %s did not return (%s). Three dead spawns and "
                "three clean spawns produce the same zero findings, so a partial "
                "fan-out is RED, not a pass. → Re-spawn the reviewer(s) that did not "
                "return; the others need not re-run."
                % (name, ", ".join(missing), ", ".join("%s=%s" % (k, reviewers[k]) for k in missing))
            )
    if not arm.get("evidence"):
        return (
            "Arm %s reported no evidence that it ran. GREEN requires the procedure to "
            "be evidenced, not asserted. → Record what proves this arm ran, or run it." % name
        )
    return None


def combine(state: dict) -> dict:
    """The combination rule. GREEN requires every arm to have RUN, evidenced.

    Findings route by tier: `auto-fixable` is fixed and re-reviewed ONCE; a finding
    that SURVIVES that single retry becomes `decision-required` — never "proceed",
    and never a second retry. A `LOW` confidence verdict in the plan is also
    `decision-required`: on the prototype-first path D1 moves PLAN APPROVAL to the
    prototype, and leaves untouched the third gate
    `plan-discipline/SKILL.md` states as "LOW — automatic human gate. The plan cannot
    proceed." Nothing in the three arms reads a verdict, so without this the gate
    would delete a shipped gate by omission.
    """
    blockers: list[str] = []
    decisions: list[dict] = []

    arms = state.get("arms") or []
    seen = {a.get("arm") for a in arms}
    for required in ("A", "B", "C"):
        if required not in seen:
            blockers.append(
                "Arm %s is absent from the gate state entirely — an arm that was never "
                "reported cannot have run." % required
            )

    for arm in arms:
        why = _why_arm_cannot_pass(arm)
        if why:
            blockers.append(why)
            continue
        for f in arm.get("findings") or []:
            tier = (f.get("tier") or "decision-required").strip()
            if tier == "auto-fixable" and not f.get("survived_retry"):
                continue  # fixed and re-reviewed clean; nothing to escalate
            entry = dict(f)
            if tier == "auto-fixable" and f.get("survived_retry"):
                entry["why"] = (
                    "This was auto-fixable and the one retry did not clear it. A "
                    "finding that survives the single retry escalates; it never "
                    "proceeds and never gets a second retry."
                )
            entry["arm"] = arm.get("arm")
            decisions.append(entry)

    for v in state.get("confidence_verdicts") or []:
        if str(v.get("confidence", "")).strip().upper() == "LOW":
            decisions.append({
                "arm": "plan",
                "finding": "A load-bearing assumption is rated LOW: %s"
                           % (v.get("assumption") or v.get("name") or "unnamed"),
                "drafted_resolution": v.get("mitigation") or "",
                "why": "LOW is an automatic human gate in the shipped loop "
                       "(plan-discipline: \"The plan cannot proceed\"). D1 moved plan "
                       "approval; it did not move this gate.",
            })

    verdict = "RED" if (blockers or decisions) else "GREEN"
    return {
        "verdict": verdict,
        "blockers": blockers,
        "decisions": decisions,
        "reasons": (
            ["every arm ran, was evidenced, and returned nothing"]
            if verdict == "GREEN"
            else []
        ),
    }


# --------------------------------------------------------------- escalation


def render_decisions(decisions: list, blockers: list | None = None) -> str:
    """The human-facing output when the gate is RED — answerable, not a document.

    Three properties make a decision answerable: the resolution is DRAFTED rather
    than requested, the ask is yes/no, and the pass-provenance is stated WITH its
    interpretation so the reader is not left to discount 1-of-2 alone.

    BLOCKERS are rendered too, and that was missing. `combine` produces RED from two
    independent lists, so an arm that did not run yielded `blockers` populated,
    `decisions` empty, and an escalation of `""` — nothing at all for the human, in
    the single MOST LIKELY red (a 429, a tool failure, a missing reviewer). The
    header also closed with "Nothing else is blocked" while blockers sat unmentioned,
    so answering the one rendered question could not start Execute. Both were found by
    running the engine rather than reading it.

    Blockers are deliberately NOT numbered alongside decisions: there is nothing to
    answer: they must clear first. Each carries an action clause instead of a draft.
    """
    blockers = blockers or []
    if not decisions and not blockers:
        return ""

    def wrap(text, indent="   ", first=None):
        # break_long_words/break_on_hyphens are off because this block's payload is,
        # by construction, cited symbols and file paths — Arm B findings key on
        # `symbol`. With the defaults, `manifest-triage` split across a line break.
        return textwrap.fill(
            text, width=76,
            initial_indent=indent if first is None else first,
            subsequent_indent=indent,
            break_long_words=False, break_on_hyphens=False,
        )

    out: list[str] = []

    if blockers:
        out.append(textwrap.fill(
            "**Blockers** — nothing to answer here; these must clear before the "
            "gate can pass.", width=76,
            break_long_words=False, break_on_hyphens=False))
        out.append("")
        for b in blockers:
            out.append(wrap(_scrub(str(b)), indent="  ", first="- "))
            out.append("")

    if decisions:
        # The closing clause is conditional: promising "Nothing else is blocked"
        # while blockers are listed above is a promise the same output invalidates.
        clause = (
            "Nothing else is blocked."
            if not blockers
            else "**%d blocker(s) above must clear too**, so answering these is "
                 "necessary but not sufficient." % len(blockers)
        )
        # Wrapped as one paragraph rather than concatenated onto the constant's
        # second line, which produced a 150-column line in exactly the block whose
        # whole point is that it stays readable.
        out.append(textwrap.fill(
            DECISION_HEADER.replace("\n", " ") + " " + clause,
            width=76, break_long_words=False, break_on_hyphens=False))
        out.append("")
        for i, d in enumerate(decisions, 1):
            marker = "%d. " % i
            # Indent width is derived, not hardcoded to 3: at item 10 the marker is
            # four characters and every sub-field silently stopped aligning.
            pad = " " * len(marker)
            out.append(wrap(_scrub(d.get("finding") or d.get("symbol") or "unnamed finding"),
                            indent=pad, first=marker))
            if d.get("why"):
                out.append("")
                out.append(wrap("Why this is blocking: %s" % _scrub(d["why"]), indent=pad))
            drafted = _scrub(d.get("drafted_resolution") or "").strip()
            if drafted:
                out.append("")
                if "\n" in drafted:
                    # A multi-line draft is structured on purpose (a criterion, a
                    # snippet). Filling it collapses that structure into prose, and
                    # the thing the human must say yes to is what degrades most.
                    out.append(wrap("What I'd do:", indent=pad))
                    out.append(textwrap.indent(drafted, pad + "  "))
                else:
                    out.append(wrap("What I'd do: %s" % drafted, indent=pad))
            out.append("")
            if drafted:
                out.append(wrap(
                    "What I need from you: yes (I apply it and re-run the check), or "
                    "tell me it is out of scope and I record that instead.", indent=pad))
            else:
                # No draft means yes/no is the wrong shape — "yes" would refer to
                # nothing. This is the LOW-confidence path, which the engine
                # generates itself and which therefore cannot be assumed to carry a
                # mitigation; asking an open question is the honest form.
                out.append(wrap(
                    "What I need from you: I have no resolution to propose here. "
                    "Tell me how you would de-risk this, or that you accept the risk "
                    "as stated and I record that instead.", indent=pad))
            if d.get("provenance"):
                out.append("")
                out.append(wrap(_scrub(d["provenance"]), indent=pad))
            out.append("")
    return "\n".join(out).rstrip() + "\n"


# --------------------------------------------------------------- CLI


def _arg(argv, flag, required=True):
    if flag in argv:
        i = argv.index(flag)
        if i + 1 < len(argv):
            val = argv[i + 1]
            # A value that looks like a flag is a mis-parse, not a value. `_arg` scans
            # for the flag anywhere in argv and takes the NEXT token, so a word-split
            # argument (`p.md --lib-root /tmp/evil`) would otherwise bind silently —
            # and `--lib-root` is the tree this engine EXECUTES from. Refuse instead.
            if isinstance(val, str) and val.startswith("--"):
                raise SecurityRefusal(
                    "%s was followed by %r, which looks like another flag — refusing "
                    "rather than binding a mis-parsed value. → Give %s a value, or "
                    "remove it." % (flag, val, flag))
            return val
        # Flag present with nothing after it. Reporting "missing required argument
        # --plan" to someone who typed `--plan-from` names the wrong flag.
        raise SecurityRefusal("%s was given with no value after it. → Supply its value, or remove the flag." % flag)
    if required:
        raise SecurityRefusal("missing required argument %s. → Pass it, or use --plan-from to read the "
                              "path from a stamped argument file." % flag)
    return None


def _path_from_file(arg_file: Path, what: str) -> Path:
    """Read a path out of a stamped argument FILE — the #165/FB-0108 Tier-2 channel.

    The path never appears as a token in a shell command, because `$ARGUMENTS` is
    substituted into a skill body before any shell parses it: a placeholder inside a
    fenced block is executable code, and no quoting convention fixes that, because
    substitution precedes parsing. `/flow:review-brief` reaches its extractor exactly
    this way; this is the same channel, not a new one.

    A multi-line value is REFUSED rather than truncated to line 1 — a path has no
    second line, so a second line is an injection attempt against the caller.
    """
    _safe_path(arg_file, "%s argument file" % what)
    try:
        raw = arg_file.read_text(encoding="utf-8")
    except OSError as exc:
        raise SecurityRefusal("%s argument file could not be read (%s): %s. → Write the path to that file "
                              "with the Write tool first (see the skill's ## Argument)." % (what, arg_file, exc))
    lines = [ln for ln in raw.splitlines() if ln.strip()]
    if not lines:
        raise SecurityRefusal("%s argument file %s is empty. → Write the plan path into it, one line, "
                              "nothing else." % (what, arg_file))
    if "\x00" in lines[0]:
        raise SecurityRefusal(
            "%s argument file %s contains a NUL byte — refusing. A path cannot hold "
            "one, and it is the one byte argv could never have carried here. → Re-write "
            "the file with the plain path." % (what, arg_file))
    if len(lines) > 1:
        raise SecurityRefusal(
            "%s argument file %s carries %d non-blank lines; a path has exactly one. "
            "Refusing rather than taking the first. → Write exactly the path and "
            "nothing else; a second line is treated as an injection attempt against "
            "the caller, not as extra context." % (what, arg_file, len(lines)))
    return Path(lines[0].strip())


def main(argv: list) -> int:
    # The escalation carries em-dashes and arrows, and `render-decisions` is the one
    # subcommand that writes text rather than going through `_emit`'s ensure_ascii
    # JSON. Under LC_ALL=C or PYTHONIOENCODING=ascii — a plain container, a CI box —
    # it died with a UnicodeEncodeError traceback instead of printing the decision a
    # human is being asked to make, which also broke this file's stated contract that
    # a refusal is "surfaced as a clean refusal, never a traceback".
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    except (AttributeError, ValueError):  # pragma: no cover - <3.7 or a non-tty sink
        pass
    if len(argv) < 2:
        sys.stderr.write(
            "usage: gate.py <depth|arm-a|union|gate|render-decisions> [options]\n"
        )
        return 2
    cmd, rest = argv[1], argv[2:]
    try:
        if cmd == "depth":
            trigger = _read_json(Path(_arg(rest, "--trigger-file")), "trigger file")
            return _emit(resolve_depth(trigger))
        if cmd == "arm-a":
            # Prefer the Tier-2 channel: the caller writes the path to a stamped file
            # and passes that file's FIXED LITERAL name, so no caller-supplied path is
            # ever a token in a shell command (#165/FB-0116). `--plan` is retained for
            # direct human/CI use where argv is not attacker-influenced.
            plan_from = _arg(rest, "--plan-from", required=False)
            if plan_from and "--plan" in rest:
                # Silent precedence is an ambiguity, not a convenience: the caller gets
                # no signal about which of the two paths was graded.
                raise SecurityRefusal(
                    "--plan and --plan-from were both given; refusing rather than "
                    "silently picking one. → Pass exactly one: --plan-from for the "
                    "stamped-file channel, --plan for direct CI use.")
            plan = (_path_from_file(Path(plan_from), "plan") if plan_from
                    else Path(_arg(rest, "--plan")))
            _safe_path(plan, "plan file")
            expect = _arg(rest, "--expect-line", required=False)
            # `--lib-root` is a TEST SEAM, and it earns its place by converting the
            # only source-grep assertion in this suite into a behavioural one: point
            # it at a stub tree and the fail-closed paths can be exercised for real,
            # rather than by grepping this file for its own error strings (which
            # passes if the sentence survives in a comment after the branch is gone).
            lib = _arg(rest, "--lib-root", required=False)
            try:
                expect_n = int(expect) if expect is not None else None
            except (TypeError, ValueError):
                raise SecurityRefusal(
                    "--expect-line must be an integer line number, got %r. → Pass "
                    "the 1-indexed line of the plan's active Spec-walk heading, or "
                    "omit the flag." % expect)
            # `--lib-root` is confined like every other input. It is the tree the
            # engine IMPORTS and SUBPROCESSES from, so guarding the read-only --plan
            # while leaving this open had the threat model inverted: it is not
            # independently reachable (it needs argv control), but it turns any argv
            # foothold into arbitrary code execution.
            lib_root = None
            if lib:
                lib_root = Path(lib)
                _safe_path(lib_root, "lib root")
            return _emit(arm_a(plan, expect_n, lib_root=lib_root))
        if cmd == "union":
            data = _read_json(Path(_arg(rest, "--passes-file")), "passes file")
            passes = data if isinstance(data, list) else data.get("passes")
            if not isinstance(passes, list):
                # Feeding `union`'s own output back in yields an int here, which used
                # to raise TypeError with no JSON on stdout — the same exit code as a
                # clean refusal, so a caller parsing the output got nothing.
                raise SecurityRefusal(
                    "passes file must be a list of pass results (or an object with a "
                    "`passes` list), got %s. → Pass the list of per-pass results; "
                    "feeding `union`'s own output back in is the usual cause."
                    % type(passes).__name__)
            return _emit(union_passes(passes))
        if cmd == "gate":
            state = _read_json(Path(_arg(rest, "--state-file")), "gate state file")
            result = combine(state)
            result["escalation"] = render_decisions(result["decisions"],
                                                 result["blockers"])
            return _emit(result)
        if cmd == "render-decisions":
            data = _read_json(Path(_arg(rest, "--entries-file")), "entries file")
            entries = data if isinstance(data, list) else data.get("decisions") or []
            sys.stdout.write(render_decisions(entries))
            return 0
    except SecurityRefusal as exc:
        _emit({"ok": False, "verdict": "RED", "reasons": [str(exc)]})
        return 1
    sys.stderr.write("[autoplan-gate] unknown subcommand: %s\n" % cmd)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
