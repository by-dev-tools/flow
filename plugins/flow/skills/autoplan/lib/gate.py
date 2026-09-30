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
DECISION_HEADER = (
    "**Decisions for you** — answer by number. I apply your answer and re-run the\n"
    "check; if it passes, Execute starts. Nothing else is blocked."
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
            "%s is a symlink (%s) — refusing to follow it; a read through it returns "
            "whatever the link points at (CWE-59)." % (what, path)
        )
    # Anchored on the process's OWN repository, never derived from the path under
    # test. Deriving it from the argument is how this guard was wrong twice: first as
    # `path.resolve().parent` (tautology), then as `_repo_root(path.parent)`, which
    # "confined" /etc/hostname to /etc and accepted it. A boundary computed from the
    # thing it is supposed to bound is not a boundary. Both were caught by running the
    # guard against a path that MUST be refused, which is the only reason either was
    # visible -- neither showed up as a failing test, because both versions passed.
    base = _repo_root(Path.cwd())
    try:
        resolved = path.resolve()
        resolved.relative_to(base)
    except ValueError:
        raise SecurityRefusal(
            "%s resolves to %s, outside %s — refusing to read a path outside the "
            "repository it belongs to." % (what, path.resolve(), base)
        )
    except SecurityRefusal:
        raise
    except Exception:  # noqa: BLE001 - an unresolvable path must not fail OPEN
        raise SecurityRefusal(
            "%s could not be confined to %s — refusing rather than acting on an "
            "unverified path." % (what, base)
        )
    # A symlinked ANCESTOR inside `base` defeats a leaf-only check. The earlier
    # draft iterated `resolved.parents` and broke on `parent == base`, which is the
    # first element when base is the leaf's own parent -- so this loop never ran.
    for parent in resolved.parents:
        if parent == base:
            break
        if parent.is_symlink():
            raise SecurityRefusal(
                "%s sits under a symlinked directory (%s) — refusing (CWE-59)."
                % (what, parent)
            )
    return path


def _read_json(path: Path, what: str):
    """Read a JSON input file, failing CLOSED with a reason rather than a traceback."""
    _safe_path(path, what)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise SecurityRefusal("%s could not be read as JSON (%s): %s" % (what, path, exc))


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
        raise SecurityRefusal("walk-pin-lint.py not found at %s" % target)
    spec = importlib.util.spec_from_file_location("_walk_pin_lint", target)
    if spec is None or spec.loader is None:
        raise SecurityRefusal("walk-pin-lint.py at %s could not be loaded" % target)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    fn = getattr(mod, "is_pinned", None)
    if not callable(fn):
        raise SecurityRefusal(
            "walk-pin-lint.py at %s exposes no is_pinned() predicate — refusing to "
            "guess what counts as a pin." % target
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
            % (err or (proc.stderr or "").strip()[:200])
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
                % (len(vacuous), "; ".join(v.get("criterion", "?")[:60] for v in vacuous))
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

    Given perfect precision across every measured run, a disagreement between two
    passes has exactly ONE reading: the finder is right and the miss is a recall
    event, not counter-evidence. So this unions, never intersects, and never averages
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
            "Found by %d of %d coverage passes. That is not weaker evidence — this "
            "reviewer has never reported a gap that was not real; the other pass "
            "simply missed it." % (n, total)
            if n < total
            else "Found by all %d coverage passes." % total
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
    if arm.get("error"):
        return (
            "Arm %s ERRORED (%s) — classified as DID NOT RUN, never as found nothing. "
            "A 429, a tool failure and an empty output are all absences of a review, "
            "not reviews that came back clean." % (name, str(arm["error"])[:160])
        )
    if not arm.get("ran"):
        return (
            "Arm %s DID NOT RUN. This is distinct from running and finding nothing, "
            "and the two never collapse." % name
        )
    if arm.get("document_blind"):
        return (
            "Arm %s ran DOCUMENT-BLIND — its reference-document load resolved zero "
            "documents, so it could not quote a project rule and cannot clear the "
            "Spec-violation category. A reviewer that cannot read the rules has not "
            "reviewed." % name
        )
    reviewers = arm.get("reviewers") or {}
    if reviewers:
        missing = sorted(k for k, v in reviewers.items() if v != "returned")
        if missing:
            return (
                "Arm %s is incomplete: %s did not return (%s). Three dead spawns and "
                "three clean spawns produce the same zero findings, so a partial "
                "fan-out is RED, not a pass."
                % (name, ", ".join(missing), ", ".join("%s=%s" % (k, reviewers[k]) for k in missing))
            )
    if not arm.get("evidence"):
        return (
            "Arm %s reported no evidence that it ran. GREEN requires the procedure to "
            "be evidenced, not asserted." % name
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


def render_decisions(decisions: list) -> str:
    """The `[decision-required]` escalation — an answerable question, not a document.

    Three properties make it answerable: the resolution is DRAFTED rather than
    requested, the ask is a yes/no, and the pass-provenance is stated WITH its
    interpretation so the reader is not left to discount 1-of-2 on their own.
    """
    if not decisions:
        return ""

    def wrap(text, indent="   "):
        # Hard-wrapped rather than left to the terminal: this block is read in a
        # transcript where a 300-column provenance sentence is the one line a human
        # skips, and the provenance is the part that stops them discounting a 1-of-2
        # finding as weak.
        return textwrap.fill(
            text, width=76, initial_indent=indent, subsequent_indent=indent
        )

    out = [DECISION_HEADER, ""]
    for i, d in enumerate(decisions, 1):
        out.append("%d. %s" % (i, d.get("finding") or d.get("symbol") or "unnamed finding"))
        if d.get("why"):
            out.append("")
            out.append(wrap("Why this is blocking: %s" % d["why"]))
        drafted = (d.get("drafted_resolution") or "").strip()
        if drafted:
            out.append("")
            out.append(wrap("What I'd do: %s" % drafted))
        out.append("")
        out.append(wrap("What I need from you: yes (I apply it and re-run the check), "
                        "or tell me it is out of scope and I record that instead."))
        if d.get("provenance"):
            out.append("")
            out.append(wrap(d["provenance"]))
        out.append("")
    return "\n".join(out).rstrip() + "\n"


# --------------------------------------------------------------- CLI


def _arg(argv, flag, required=True):
    if flag in argv:
        i = argv.index(flag)
        if i + 1 < len(argv):
            return argv[i + 1]
    if required:
        raise SecurityRefusal("missing required argument %s" % flag)
    return None


def main(argv: list) -> int:
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
            plan = Path(_arg(rest, "--plan"))
            _safe_path(plan, "plan file")
            expect = _arg(rest, "--expect-line", required=False)
            # `--lib-root` is a TEST SEAM, and it earns its place by converting the
            # only source-grep assertion in this suite into a behavioural one: point
            # it at a stub tree and the fail-closed paths can be exercised for real,
            # rather than by grepping this file for its own error strings (which
            # passes if the sentence survives in a comment after the branch is gone).
            lib = _arg(rest, "--lib-root", required=False)
            return _emit(arm_a(plan, int(expect) if expect is not None else None,
                               lib_root=Path(lib) if lib else None))
        if cmd == "union":
            data = _read_json(Path(_arg(rest, "--passes-file")), "passes file")
            passes = data if isinstance(data, list) else data.get("passes") or []
            return _emit(union_passes(passes))
        if cmd == "gate":
            state = _read_json(Path(_arg(rest, "--state-file")), "gate state file")
            result = combine(state)
            result["escalation"] = render_decisions(result["decisions"])
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
