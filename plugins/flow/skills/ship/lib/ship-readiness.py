#!/usr/bin/env python3
"""
Deterministic engine behind the Step 8 ship-readiness predicate and the
`/flow:ship` ready/draft decision (roadmap R1 +
`dev-docs/research/2026-10-agentic-graphs.md` R1; FB-0131 corollary 3; FB-0137).

    ci       Map a `gh pr view --json` blob to the CI condition's state.
             Tri-state by construction: passing / failing / PENDING.
    check    The six-condition Step 8 predicate. Every condition is evaluated
             and the verdict NAMES the ones that did not pass.
    render   The human-readable verdict line.

THE RULE THE WHOLE FILE EXISTS TO HOLD, stated once:

    "Nothing has failed yet" is NOT "everything passed", and "I could not
    look" is NOT "there was nothing there". Neither is ever `ready`.

That is FB-0121's contract, and it is the entire reason this engine is keyed on
a three-valued per-condition verdict (`PASS` / `FAIL` / `UNDECLARED`) rather
than a boolean. A boolean has nowhere to put "I could not tell", so every
implementation of it eventually puts that case in `True` -- which is precisely
the defect measured on #176: four pushes, six red CI runs, every flow gate
green, the manifest READY, the PR body saying "ready", and GitHub reporting
`BLOCKED`.

WHY THE EXIT CODE IS NOT THE INSTRUMENT (measured, 2026-10-05, gh 2.100.0).

`.claude/rules/general.md` item 4's corollary says to prefer a tool's own exit
code over a grep of its output, and that corollary is right in general. It does
not apply to `gh pr checks`, because that command's exit code is STRICTLY LESS
informative than its structured output -- measured, exit 1 is returned for at
least three unlike worlds:

    a failing check         (#176's shape)
    no checks reported      (#183 -- and it emits no JSON at all, even with --json)
    the PR does not exist   (#99999 -- a GraphQL error)

Collapsing those into one value is how "pending" becomes "passing". So this
engine reads the STRUCTURED rollup, which gh's authors maintain against their
own schema, and uses process failure only to separate "I read it" from "I could
not look". The exit code is still preferred for every OTHER tool in the
pipeline; this is a measured exception, not a licence.

WHY ONE `gh pr view` CALL AND NOT `gh pr checks` (measured).

`gh pr checks --json` fails outright (exit 1, no JSON) when a PR has no checks,
so the no-checks case would arrive as a parse error indistinguishable from a
network failure. `gh pr view --json statusCheckRollup,mergeStateStatus,isDraft`
always yields valid JSON for an existing PR -- an empty rollup is `[]`, which is
a readable fact rather than an error -- and carries `mergeStateStatus` in the
same call, which is GitHub's OWN answer to "would this be blocked".

TWO DECISIONS, ONE ENGINE -- and conflating them would break the pipeline.

`check` and `ci` feed DIFFERENT gates, and the difference is load-bearing:

  * `ci` gates the PR's ready/draft state at ship 7a.7. Only CI states gate
    here, because the human has already said "ship it" -- an `UNDECLARED`
    artifact condition must not silently draft a PR they explicitly asked for.
  * `check` is the Step 8 AUTO-ADVANCE predicate (`docs/workflow.md` Step 8).
    There, `UNDECLARED` correctly means "do not auto-advance, present to the
    human" -- which is the loop's existing conservative default and costs
    nothing but an explicit "ship it".

If `check`'s `UNDECLARED` conditions also drafted PRs, every ship would draft,
because two of the six conditions have no artifact to read (see CONDITIONS
below). Keeping the two decisions distinct is what makes an honest
`UNDECLARED` usable instead of fatal.

CONDITIONS, and which ones the artifacts can actually answer today.

R1 predicted that re-deriving the prose predicate would reveal which
sub-conditions the artifacts do not yet carry, and that this would itself be
useful signal. It did. Two of the six cannot be answered:

    1 spec-walk    ANSWERABLE -- the plan's checkbox state.
    2 no-blocker   UNDECLARED BY CONSTRUCTION. No artifact carries a BLOCKER
                   count. `rigor-marker.py check` answers whether staff-review
                   RAN against the current source, never what it FOUND.
    3 confidence   UNDECLARED when any MEDIUM/LOW verdict is present: nothing
                   records that the gate resolved it. The verdicts themselves
                   ARE readable, so this reports them rather than shrugging.
    4 verify-build ANSWERABLE -- the findings buffer's `overall_verdict`.
    5 open-qs      ANSWERABLE -- `open_questions[].routing == this-iteration`.
    6 ci           ANSWERABLE, live -- this file's `ci` verb.

Those two gaps are named in the output, not papered over, and are filed as
roadmap follow-ups. A checker that silently passed them would be a worse
instrument than the prose it replaced.

Stdlib only.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Shared contracts, imported rather than restated.
# ---------------------------------------------------------------------------
# `CHECKBOX_RE` and `extract_block` are the SAME definitions `/flow:verify-build`
# and `/flow:critique-plan` read. Condition 1 needs the checkbox STATE, which
# `collect_items` discards (it returns item text only) -- so this module reuses
# `extract_block` for the block's extent and re-matches the shared regex inside
# that range. It does NOT re-implement either. A second copy of "where does a
# Spec-walk block end" is the exact defect `walk_extract.collect_items`'
# docstring records having already shipped twice.
_WALK_LIB = Path(__file__).resolve().parent.parent.parent / "verify-build" / "lib"


def _load_walk():
    if str(_WALK_LIB) not in sys.path:
        sys.path.insert(0, str(_WALK_LIB))
    try:
        import walk_extract  # type: ignore
    except Exception as exc:  # pragma: no cover - install-shape failure
        raise RuntimeError(
            f"cannot import shared walk_extract from {_WALK_LIB} ({exc}) -- "
            "refusing to re-implement Spec-walk parsing locally. Check the plugin install."
        ) from exc
    return walk_extract


# ---------------------------------------------------------------------------
# The CI condition.
# ---------------------------------------------------------------------------
# gh's rollup carries TWO node types and they do not share field names. Handling
# only `CheckRun` would make every non-Actions CI (CircleCI, Buildkite, any
# commit-status reporter) read as "no checks" -- which, combined with a CLEAN
# merge state, would resolve to "nothing to check, go ahead". That is the
# measured `#183` trap arriving by a second route, so both are mapped.
#
# `CheckRun` is measured (this repo, 6 checks). `StatusContext` field names are
# transcribed from GitHub's documented GraphQL schema and are NOT measured here --
# this repo has no non-Actions CI to produce one. The fixtures exercise this
# mapper's handling of that shape; they cannot and do not prove GitHub emits it.
# Flagged rather than implied, per FB-0131.

# Terminal conclusions that mean "this check is content". NEUTRAL and SKIPPED are
# passes: a skipped required check is GitHub's business, not flow's, and gh's own
# `pr checks` buckets both as non-failing.
_PASSING_CONCLUSIONS = frozenset({"SUCCESS", "NEUTRAL", "SKIPPED"})
# CANCELLED and STALE are deliberately FAILING, not pending: they are terminal
# (nothing further will arrive) and they are not a pass. Calling them pending
# would make the blocking wait hang until timeout on a cancelled run; calling
# them passing is the bug this file exists to prevent.
_FAILING_CONCLUSIONS = frozenset(
    {"FAILURE", "TIMED_OUT", "ACTION_REQUIRED", "STARTUP_FAILURE", "CANCELLED", "STALE"}
)
_PASSING_STATES = frozenset({"SUCCESS"})
_PENDING_STATES = frozenset({"PENDING", "EXPECTED"})
_FAILING_STATES = frozenset({"FAILURE", "ERROR"})

# Merge states that mean GitHub itself would stand in the way. `DRAFT` is NOT
# here and must never be: flow drafts PRs, so `DRAFT` is the expected state for
# exactly the PRs this engine is asked about, and it says nothing about checks.
# `UNKNOWN` means GitHub has not finished computing mergeability -- transient, and
# deliberately NOT a block: when every reported check has passed, an un-computed
# mergeability is no reason to withhold ready. It only ever withholds a pass on the
# EMPTY-rollup path, where it is handled as "could not confirm" (see `ci_condition`).
_BLOCKING_MERGE_STATES = frozenset({"BLOCKED", "DIRTY", "BEHIND"})
_MERGE_STATE_MEANING = {
    "BLOCKED": "GitHub reports the PR as BLOCKED (a required check or review is not satisfied)",
    "DIRTY": "GitHub reports the PR as DIRTY (it conflicts with the base branch, so checks may never run)",
    "BEHIND": "GitHub reports the PR as BEHIND (the base branch moved and an update is required)",
    # UNKNOWN is glossed even though it is NOT in _BLOCKING_MERGE_STATES, and that is the
    # point: ship 7a.7 runs immediately after the PR is created, which is precisely when
    # the rollup is empty and GitHub has not finished computing mergeability. So this is
    # the most likely `ci-unknown` a consumer ever sees, and it renders as the first line
    # of a numbered question. Leaving it to the fallback leaked a raw GraphQL field name
    # into that line.
    "UNKNOWN": "GitHub has not finished working out whether this PR can merge",
}

KIND_FAILING = "ci-failing"
KIND_PENDING = "ci-pending"
KIND_UNKNOWN = "ci-unknown"


def _bucket(node: dict) -> tuple[str, str]:
    """One rollup node -> (bucket, display-name).

    Buckets: pass / fail / pending / unknown. An unrecognised node type, status,
    or conclusion returns `unknown` -- never `pass`. There is no default-to-fine
    branch in this function on purpose: a vocabulary GitHub adds tomorrow must
    arrive as "I could not classify this", which blocks, rather than as silence.
    """
    typename = node.get("__typename") or ""
    if typename == "CheckRun":
        name = node.get("name") or "(unnamed check)"
        status = (node.get("status") or "").upper()
        if status != "COMPLETED":
            # QUEUED / IN_PROGRESS / WAITING / PENDING / REQUESTED -- all "not yet".
            return "pending", name
        conclusion = (node.get("conclusion") or "").upper()
        if conclusion in _PASSING_CONCLUSIONS:
            return "pass", name
        if conclusion in _FAILING_CONCLUSIONS:
            return "fail", name
        # COMPLETED with an empty or unrecognised conclusion: not classifiable.
        return "unknown", name
    if typename == "StatusContext":
        name = node.get("context") or "(unnamed status)"
        state = (node.get("state") or "").upper()
        if state in _PASSING_STATES:
            return "pass", name
        if state in _PENDING_STATES:
            return "pending", name
        if state in _FAILING_STATES:
            return "fail", name
        return "unknown", name
    return "unknown", node.get("name") or node.get("context") or f"(unknown node type {typename!r})"


def _node_url(node: dict) -> str:
    return node.get("detailsUrl") or node.get("targetUrl") or ""


def ci_condition(
    blob: dict | None,
    *,
    unreadable_reason: str | None = None,
    settled: bool = False,
) -> dict:
    """The CI condition, as a pure function of a `gh pr view --json` blob.

    `blob is None` means the call could not be made or its output could not be
    parsed -- `gh` absent, unauthenticated, offline, PR missing. That is
    `UNDECLARED`/`ci-unknown`, never `PASS`. FB-0121: "couldn't see" is not
    "nothing there".

    `settled` is the caller's POSITIVE ASSERTION that it gave checks a chance to
    appear before this read. It gates exactly one branch -- empty rollup with a
    `CLEAN` merge state -- and defaults to False, because that branch is the only
    place in this engine where `PASS` is derived from an ABSENCE.

    Why it has to exist (found by review, reproduced before fixing). Ship 7a.7 runs
    immediately after `gh pr create`, and `gh pr checks --watch` does NOT wait for
    checks to *appear* -- with zero checks reported it exits at once. So for the
    seconds between creating a PR and Actions registering its run, the rollup is
    `[]`; and on a repo with no branch protection `mergeStateStatus` is already
    `CLEAN`. Without this flag the engine answered `PASS` / "no checks are
    configured" there -- #176's exact shape ("nothing has failed") re-entering
    through the one branch that reasons from absence of evidence. Flow's own repo
    masked it, because required checks make a fresh PR `BLOCKED`.

    So "this project has no CI" and "this PR is two seconds old" are two states, and
    only a caller that waited can tell them apart. Same rule as
    `autoplan/lib/gate.py`: a green verdict requires the arm to have RUN.
    """
    if blob is None:
        return {
            "state": "unknown",
            "verdict": "UNDECLARED",
            "kind": KIND_UNKNOWN,
            "failing": [],
            "pending": [],
            "unmapped": [],
            "merge_state": None,
            "counts": {"pass": 0, "fail": 0, "pending": 0, "unknown": 0},
            "reason": unreadable_reason or "CI status unknown — could not read it from GitHub.",
        }

    rollup = blob.get("statusCheckRollup")
    if rollup is None:
        rollup = []
    merge_state = (blob.get("mergeStateStatus") or "").upper() or None

    counts = {"pass": 0, "fail": 0, "pending": 0, "unknown": 0}
    failing: list[dict] = []
    pending: list[str] = []
    unmapped: list[str] = []
    for node in rollup:
        if not isinstance(node, dict):
            counts["unknown"] += 1
            unmapped.append("(malformed rollup entry)")
            continue
        bucket, name = _bucket(node)
        counts[bucket] += 1
        if bucket == "fail":
            failing.append({"name": name, "url": _node_url(node)})
        elif bucket == "pending":
            pending.append(name)
        elif bucket == "unknown":
            unmapped.append(name)

    result = {
        "failing": failing,
        "pending": pending,
        "unmapped": unmapped,
        "merge_state": merge_state,
        "counts": counts,
    }

    # Precedence is deliberate and is the heart of the tri-state:
    #   fail > pending > unknown > pass
    # `pass` is LAST, so it is reachable only when nothing else is outstanding.
    # Any other order lets "nothing has failed yet" win.
    if failing:
        names = ", ".join(f["name"] for f in failing)
        result.update(
            state="failing",
            verdict="FAIL",
            kind=KIND_FAILING,
            reason=f"CI is failing: {names}.",
        )
        return result

    if pending:
        result.update(
            state="pending",
            verdict="UNDECLARED",
            kind=KIND_PENDING,
            reason=(
                f"checks pending ({len(pending)} of {len(rollup)} still running: "
                f"{', '.join(pending)}). Not failing — not passing either."
            ),
        )
        return result

    if unmapped:
        result.update(
            state="unknown",
            verdict="UNDECLARED",
            kind=KIND_UNKNOWN,
            reason=(
                f"CI status unknown — {len(unmapped)} check(s) reported a state this "
                f"version of flow cannot classify: {', '.join(unmapped)}."
            ),
        )
        return result

    if not rollup:
        # The #183 disambiguation. An empty rollup is TWO different worlds, and
        # the difference is not in the rollup -- it is in whether GitHub itself
        # considers the PR blocked. Measured: #183 is an open PR with an empty
        # rollup and DIRTY, where `pull_request` checks will never arrive.
        if merge_state == "CLEAN":
            if not settled:
                # The caller has not asserted it waited, so this is indistinguishable
                # from a PR created moments ago whose checks have not registered yet.
                # Not a pass. The caller re-reads once with `--settled` after giving
                # them a chance to appear; only then is the absence evidence.
                result.update(
                    state="no-checks-unsettled",
                    verdict="UNDECLARED",
                    kind=KIND_UNKNOWN,
                    reason=(
                        "no checks have been reported yet. GitHub reports the PR as CLEAN, "
                        "but a PR created moments ago looks exactly like a project with no "
                        "CI at all — so this is not yet evidence that there is nothing to "
                        "wait for."
                    ),
                )
                return result
            result.update(
                state="no-checks-clean",
                verdict="PASS",
                kind=None,
                reason=(
                    "no checks are configured or required for this PR, and GitHub reports "
                    "it as CLEAN after a second look — nothing to wait for."
                ),
            )
            return result
        detail = _MERGE_STATE_MEANING.get(
            merge_state or "",
            "GitHub did not report whether this PR can merge",
        )
        result.update(
            state="unknown",
            verdict="UNDECLARED",
            kind=KIND_UNKNOWN,
            reason=(
                f"CI status unknown — no checks have been reported, and {detail}. "
                "An absent check is not a passing check."
            ),
        )
        return result

    # Every check passed. One last cross-check against GitHub's own verdict: if
    # it still reports the PR as blocked, something outside the check list does
    # (a required review, a conflict). `DRAFT` is excluded by construction --
    # see `_BLOCKING_MERGE_STATES`.
    if merge_state in _BLOCKING_MERGE_STATES:
        detail = _MERGE_STATE_MEANING.get(merge_state, f"mergeStateStatus={merge_state}")
        result.update(
            state="unknown",
            verdict="UNDECLARED",
            kind=KIND_UNKNOWN,
            reason=(
                f"every reported check passed, but {detail}. Flow will not call a PR "
                "ready while GitHub says otherwise."
            ),
        )
        return result

    result.update(
        state="passing",
        verdict="PASS",
        kind=None,
        reason=f"all {counts['pass']} reported check(s) passed.",
    )
    return result


def ci_timeout_condition(waited_seconds: int) -> dict:
    """A blocking wait that hit its ceiling reports PENDING, never a pass.

    The budget exists to bound wall-clock, not to manufacture a verdict. This is
    a separate entry point so the timeout path cannot accidentally fall through
    to the all-passing branch above.
    """
    return {
        "state": "pending",
        "verdict": "UNDECLARED",
        "kind": KIND_PENDING,
        "failing": [],
        "pending": [],
        "unmapped": [],
        "merge_state": None,
        "counts": {"pass": 0, "fail": 0, "pending": 0, "unknown": 0},
        "reason": (
            f"checks pending — stopped waiting after {waited_seconds}s (the ciWaitSeconds "
            "setting in flow.config.json). Still running is not passing."
        ),
    }


# ---------------------------------------------------------------------------
# Conditions 1-5.
# ---------------------------------------------------------------------------
_CONFIDENCE_RE = re.compile(
    r"\*{0,2}confidence\*{0,2}\s*[:=]\s*\*{0,2}(HIGH|MEDIUM|LOW)\*{0,2}",
    re.IGNORECASE,
)


def spec_walk_condition(plan_path: str | None) -> dict:
    """Condition 1 -- every Spec-walk checkbox in the ACTIVE block is checked."""
    if not plan_path:
        return _cond("spec-walk", "UNDECLARED", "no plan path was given, so no criteria were read.")
    p = Path(plan_path)
    if not p.is_file():
        return _cond("spec-walk", "UNDECLARED", f"plan file not found at {plan_path}.")
    try:
        walk = _load_walk()
        text = p.read_text(encoding="utf-8", errors="replace")
        block = walk.extract_block(text, "Spec-walk")
    except Exception as exc:
        return _cond("spec-walk", "UNDECLARED", f"could not parse the plan's Spec-walk block ({exc}).")

    # `extract_block` (the LIBRARY) returns `first_heading_line`/`items`; the
    # `extract-criteria.py` CLI renames those to `source_heading_line`/`criteria`
    # on the way out. Reading the CLI's names off the library's return value is a
    # silent `None`, which this module would then report as "no Spec-walk block" --
    # a green-looking UNDECLARED over a plan that is fully declared. Pinned by
    # `run_ship_readiness_evals.py::test_unchecked_criterion_fails_not_undeclared`,
    # which caught exactly that during this change.
    # `all_demoted` is a DIFFERENT empty-items case from "there is no block", and
    # `walk_extract.extract_block`'s docstring explicitly tells callers not to conflate
    # them. Same UNDECLARED verdict, but the reason must not send a reader off to write a
    # Spec-walk block that already exists and is merely marked shipped.
    if block.get("all_demoted"):
        return _cond(
            "spec-walk",
            "UNDECLARED",
            "every Spec-walk block in the plan is demoted (marked merged/shipped), so the "
            "active plan section declares none — expected just after a demote-at-merge.",
        )
    start = block.get("first_heading_line")
    if not start:
        return _cond("spec-walk", "UNDECLARED", "the plan declares no Spec-walk block.")
    end = block.get("ended_at_line")
    lines = text.splitlines()
    lo = start  # 1-indexed heading line -> 0-indexed line after it
    hi = (end - 1) if end else len(lines)
    total = checked = 0
    unchecked: list[str] = []
    for raw in lines[lo:hi]:
        m = walk.CHECKBOX_RE.match(raw)
        if not m:
            continue
        total += 1
        if m.group("state").lower() == "x":
            checked += 1
        else:
            unchecked.append(m.group("text")[:70])
    if total == 0:
        return _cond("spec-walk", "UNDECLARED", "the active Spec-walk block contains no criteria.")
    # Carry the parser's own warnings + the line it graded. On a multi-PR plan
    # `extract_block` grades the first active block and warns about the rest; dropping
    # that left the reason unable to say WHICH block it read (FB-0131: a clean parse is
    # not evidence the right block was selected).
    where = f" [graded the block at line {start}]"
    warns = block.get("warnings") or []
    if warns:
        where += " " + " ".join(f"[WARN] {w}" for w in warns)
    if unchecked:
        # Name a few, then count the rest. The full list is the plan itself; a reason
        # line that prints fifteen 70-character criteria is not read by anyone, which
        # makes the verdict's own output the place the signal gets lost.
        shown = "; ".join(unchecked[:3])
        more = f" (and {len(unchecked) - 3} more)" if len(unchecked) > 3 else ""
        return _cond(
            "spec-walk",
            "FAIL",
            f"{len(unchecked)} of {total} Spec-walk criteria are still unchecked: {shown}{more}{where}",
        )
    return _cond("spec-walk", "PASS", f"all {total} Spec-walk criteria are checked.{where}")


def no_blocker_condition(blockers_file: str | None) -> dict:
    """Condition 2 -- no open BLOCKER from `/simplify` or `/flow:staff-review`.

    UNDECLARED BY CONSTRUCTION unless an artifact is supplied. This is R1's
    predicted finding and it is reported as a gap rather than assumed clean:
    `rigor-marker.py check` answers whether staff-review ran against the current
    source, not what it found, so nothing in the repo today carries a BLOCKER
    count. The parameter exists so the condition becomes answerable the day that
    artifact lands, without a second engine.
    """
    if not blockers_file:
        return _cond(
            "no-blocker",
            "UNDECLARED",
            "no artifact records the /simplify + staff-review BLOCKER count "
            "(rigor-marker.py records that the review RAN, never what it FOUND), "
            "so this condition cannot be re-derived — it is not assumed clean.",
        )
    p = Path(blockers_file)
    if not p.is_file():
        return _cond("no-blocker", "UNDECLARED", f"blocker artifact not found at {blockers_file}.")
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception as exc:
        return _cond("no-blocker", "UNDECLARED", f"blocker artifact at {blockers_file} is unreadable ({exc}).")
    open_blockers = data.get("open_blockers")
    if open_blockers is None:
        return _cond("no-blocker", "UNDECLARED", "the blocker artifact declares no `open_blockers` field.")
    try:
        count = len(open_blockers) if isinstance(open_blockers, list) else int(open_blockers)
    except Exception:
        return _cond("no-blocker", "UNDECLARED", "the blocker artifact's `open_blockers` field is not countable.")
    if count:
        return _cond("no-blocker", "FAIL", f"{count} open BLOCKER(s) from /simplify or /flow:staff-review.")
    return _cond("no-blocker", "PASS", "no open BLOCKER from /simplify or /flow:staff-review.")


def confidence_condition(plan_path: str | None) -> dict:
    """Condition 3 -- no load-bearing assumption unresolved at MEDIUM or LOW.

    The verdicts are readable; their RESOLUTION is not. Nothing in a plan records
    "the gate considered this MEDIUM and accepted it", so a present MEDIUM/LOW is
    reported as UNDECLARED with its count rather than guessed either way. An
    all-HIGH plan is a genuine PASS, which is what keeps this from being a
    constant UNDECLARED that teaches readers to ignore it.
    """
    if not plan_path or not Path(plan_path).is_file():
        return _cond("confidence", "UNDECLARED", "no plan file was read, so no confidence verdicts were seen.")
    text = Path(plan_path).read_text(encoding="utf-8", errors="replace")
    found = [m.group(1).upper() for m in _CONFIDENCE_RE.finditer(text)]
    if not found:
        return _cond("confidence", "UNDECLARED", "the plan declares no confidence verdicts.")
    soft = [v for v in found if v in ("MEDIUM", "LOW")]
    if soft:
        return _cond(
            "confidence",
            "UNDECLARED",
            f"{len(soft)} MEDIUM/LOW confidence verdict(s) present ({', '.join(sorted(set(soft)))}) "
            "and no artifact records whether the gate resolved them.",
        )
    return _cond("confidence", "PASS", f"all {len(found)} confidence verdicts are HIGH.")


def verify_build_condition(findings_path: str | None) -> dict:
    """Condition 4 -- a behavioral gate EXISTS and returns PASS.

    Three outcomes that a boolean would flatten into two: PASS, an explicit
    non-PASS verdict, and no buffer at all. The third is FB-0018's case --
    skipped is not ready, because there is no behavioral gate to have passed.
    Its reason is deliberately worded so it cannot be misread as "the build
    failed", which would send a reader to debug code that never ran.
    """
    if not findings_path:
        return _cond("verify-build", "UNDECLARED", "no verify-build findings path was given.")
    p = Path(findings_path)
    if not p.is_file():
        return _cond(
            "verify-build",
            "UNDECLARED",
            f"no behavioral gate ran — there is no verify-build buffer at {findings_path}. "
            "This is NOT a failing build; nothing was exercised.",
        )
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception as exc:
        return _cond("verify-build", "UNDECLARED", f"the verify-build buffer is unreadable ({exc}).")
    verdict = data.get("overall_verdict")
    if verdict == "PASS":
        return _cond("verify-build", "PASS", "the behavioral gate ran and passed.")
    if verdict == "FAIL":
        return _cond("verify-build", "FAIL", "the behavioral gate ran and failed.")
    if verdict == "Unknown":
        # UNDECLARED, not FAIL. Both block `ready`, but this file's whole thesis is that
        # "it did not pass" and "I could not tell" are different facts, and verify-build's
        # `Unknown` is literally the second one. Putting it in `failed` would send a reader
        # to debug a failure that was never observed.
        return _cond(
            "verify-build",
            "UNDECLARED",
            "the behavioral gate ran but could not certify the result (Unknown) — not a "
            "failure, and not a pass.",
        )
    return _cond(
        "verify-build",
        "UNDECLARED",
        f"the verify-build buffer declares no recognised overall_verdict (got {verdict!r}).",
    )


def open_questions_condition(findings_path: str | None) -> dict:
    """Condition 5 -- no unanswered `this-iteration` open question."""
    if not findings_path or not Path(findings_path).is_file():
        return _cond(
            "open-questions",
            "UNDECLARED",
            "no verify-build buffer was read, so its open_questions could not be checked.",
        )
    try:
        data = json.loads(Path(findings_path).read_text(encoding="utf-8"))
    except Exception as exc:
        return _cond("open-questions", "UNDECLARED", f"the verify-build buffer is unreadable ({exc}).")
    qs = data.get("open_questions") or []
    this_iter = [
        q.get("question", "(unstated)")
        for q in qs
        if isinstance(q, dict) and q.get("routing") == "this-iteration"
    ]
    if this_iter:
        return _cond(
            "open-questions",
            "FAIL",
            f"{len(this_iter)} unanswered this-iteration open question(s): " + "; ".join(this_iter),
        )
    return _cond("open-questions", "PASS", "no unanswered this-iteration open question.")


def _cond(cid: str, verdict: str, reason: str) -> dict:
    return {"id": cid, "verdict": verdict, "reason": reason}


# ---------------------------------------------------------------------------
# The combination rule.
# ---------------------------------------------------------------------------
CONDITION_ORDER = (
    "spec-walk",
    "no-blocker",
    "confidence",
    "verify-build",
    "open-questions",
    "ci",
)


def combine(conditions: list[dict]) -> dict:
    """`ready` iff EVERY condition is PASS. UNDECLARED is not a pass.

    Stated as "every condition PASSed" rather than "no condition FAILed" on
    purpose: the second formulation is satisfied by a condition that never ran,
    which is `.claude/rules/general.md` item 3's prohibition-satisfiable-by-
    deletion shape and `autoplan/lib/gate.py`'s rule ("GREEN requires every arm
    to have RUN"). Same rule, second surface.
    """
    seen = {c["id"] for c in conditions}
    missing = [cid for cid in CONDITION_ORDER if cid not in seen]
    for cid in missing:
        conditions.append(_cond(cid, "UNDECLARED", "this condition was not evaluated."))
    order = {cid: i for i, cid in enumerate(CONDITION_ORDER)}
    conditions.sort(key=lambda c: order.get(c["id"], len(order)))
    failed = [c["id"] for c in conditions if c["verdict"] == "FAIL"]
    undeclared = [c["id"] for c in conditions if c["verdict"] == "UNDECLARED"]
    return {
        "ready": not failed and not undeclared,
        "conditions": conditions,
        "failed": failed,
        "undeclared": undeclared,
    }


def render(result: dict) -> str:
    lines: list[str] = []
    verdict = "READY" if result["ready"] else "NOT READY"
    lines.append(f"[ship-readiness] {verdict}")
    for c in result["conditions"]:
        mark = {"PASS": "PASS", "FAIL": "FAIL", "UNDECLARED": "UNDECLARED"}[c["verdict"]]
        lines.append(f"  {mark:<10} {c['id']:<15} {c['reason']}")
    if result["failed"]:
        lines.append(f"  → failed: {', '.join(result['failed'])}")
    if result["undeclared"]:
        lines.append(
            f"  → could not confirm: {', '.join(result['undeclared'])} "
            "(not a pass — see each reason above)"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _read_blob(path: str | None) -> tuple[dict | None, str | None]:
    """Read a `gh pr view --json` blob from a file or stdin.

    Returns `(blob, unreadable_reason)`. Unparseable input is NOT an exception --
    it is the `ci-unknown` state, which is the whole point.
    """
    try:
        raw = sys.stdin.read() if not path or path == "-" else Path(path).read_text(encoding="utf-8")
    except Exception as exc:
        return None, f"CI status unknown — could not read the gh output ({exc})."
    if not raw.strip():
        return None, (
            "CI status unknown — gh produced no output. Measured: `gh pr checks` emits "
            "nothing parseable when a PR has no checks, and an empty read is also what a "
            "missing or unauthenticated gh looks like."
        )
    try:
        blob = json.loads(raw)
    except Exception as exc:
        return None, f"CI status unknown — gh output was not valid JSON ({exc})."
    if not isinstance(blob, dict):
        return None, "CI status unknown — gh output was not a JSON object."
    return blob, None


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Step 8 ship-readiness predicate (R1, FB-0131, FB-0137).")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_ci = sub.add_parser("ci", help="gh pr view --json blob (stdin) -> the CI condition")
    p_ci.add_argument("--blob", help="path to the blob; default stdin")
    p_ci.add_argument("--gh-failed", action="store_true", help="gh could not be run at all")
    p_ci.add_argument("--timed-out", type=int, metavar="SECONDS", help="the blocking wait hit its ceiling")
    p_ci.add_argument(
        "--settled",
        action="store_true",
        help="assert the caller gave checks a chance to appear before this read; "
             "required before an EMPTY check list may count as 'no CI configured'",
    )

    p_check = sub.add_parser("check", help="the six-condition Step 8 predicate")
    p_check.add_argument("--plan")
    p_check.add_argument("--findings")
    p_check.add_argument("--blockers-file")
    p_check.add_argument("--ci-blob", help="path to a gh pr view --json blob; omit if no PR exists yet")
    p_check.add_argument("--gh-failed", action="store_true")
    p_check.add_argument("--ci-settled", action="store_true")
    p_check.add_argument("--render", action="store_true", help="human-readable instead of JSON")

    args = ap.parse_args(argv)

    if args.cmd == "ci":
        if args.timed_out is not None:
            out = ci_timeout_condition(args.timed_out)
        elif args.gh_failed:
            out = ci_condition(
                None,
                unreadable_reason=(
                    "CI status unknown — gh could not be run (absent, unauthenticated, or "
                    "offline). This is not evidence that checks pass."
                ),
            )
        else:
            blob, why = _read_blob(args.blob)
            out = ci_condition(blob, unreadable_reason=why, settled=args.settled)
        print(json.dumps(out, indent=2, sort_keys=True))
        # Exit 0 whenever the mapping SUCCEEDED, whatever it concluded. The caller
        # reads `verdict`; a non-zero exit here would be indistinguishable from the
        # engine itself failing -- the exact ambiguity this file was written to avoid.
        return 0

    conditions = [
        spec_walk_condition(args.plan),
        no_blocker_condition(args.blockers_file),
        confidence_condition(args.plan),
        verify_build_condition(args.findings),
        open_questions_condition(args.findings),
    ]
    if args.gh_failed:
        ci = ci_condition(None, unreadable_reason="CI status unknown — gh could not be run.")
    elif args.ci_blob:
        blob, why = _read_blob(args.ci_blob)
        ci = ci_condition(blob, unreadable_reason=why, settled=args.ci_settled)
    else:
        ci = ci_condition(
            None,
            unreadable_reason=(
                "CI status unknown — no PR has been opened yet, so no checks exist to read. "
                "Flow's own CI triggers on pull_request."
            ),
        )
    conditions.append({"id": "ci", "verdict": ci["verdict"], "reason": ci["reason"]})
    result = combine(conditions)
    result["ci"] = ci
    print(render(result) if args.render else json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
