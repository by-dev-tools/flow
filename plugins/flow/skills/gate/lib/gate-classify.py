#!/usr/bin/env python3
"""The §4.8 gate-delegation policy, as a truth table rather than a paragraph.

Canonical cloud-workflow plan §4.8 says the orchestrator may approve a worker's
plan iff **all four** axes are green — stakes low, reversible yes, confidence
high, taste low — with an always-human carve-out when a prototype is attached.
The merge gate keys on a stricter thing (explicit verifiability) because a merge
writes to `main`.

That policy is prose everywhere it is currently written down, and prose is the
wrong medium for it: **a wrong answer here fails silently.** An axis mis-read as
green auto-approves a plan that should have escalated, and nothing downstream
reports it — the work simply proceeds with one fewer human in the loop than the
policy promised. FB-0018's rule ("a positive PASS, not the absence of failure")
applied to the gate policy itself is what this module is.

What is mechanical here and what is not, deliberately:

  - **stakes** is computed, from the changed-file set × `sensitivePaths`
    (`plugins/flow/lib/sensitive_paths.py` — shared with `/flow:spawn`'s routing
    floor, one definition, two readers).
  - **reversible / taste** are *declared by the agent*. They are genuine
    judgment ("would a plain `git revert` fully undo this?", "is there a correct
    answer, or is this a product call?") and §4.10's anti-bloat guardrail says
    the judgment stays the agent's. This module takes them as inputs and refuses
    to guess.
  - **confidence** is *reused*, not invented: the plan's own HIGH/MEDIUM/LOW
    verdict plus `/flow:critique-plan`'s APPROVED. §4.8 is explicit that this
    axis introduces no new signal.
  - **the combination rule** is code. That is the part a human re-derives
    slightly differently every time, and the part whose failure is invisible.

**Every unknown escalates.** There is no input value that means "I could not
tell, proceed anyway": an absent, empty or unrecognised axis is treated as red.
This is the same fail-safe direction `sensitive_paths.py` takes and for the same
reason — a wrong escalation costs one human decision, a wrong approval costs the
gate.

**This module never merges, and could not.** It classifies and formats. There is
no code path here that calls a VCS or a forge; `/flow:gate` composes it and does
not add one. At the crawl rung of §4.8's rollout the merge verdict is
hard-wired to `human` with no config slot to flip it, because the walk rung is
gated on a GitHub App identity that does not exist yet — a switch that could
delegate merges *before* that identity exists would let an agent merge under the
human's own credential and destroy the only provenance §4.8 requires
(`merged_by`).

**Deletion criterion (FB-0088):** delete with `/flow:gate`, or earlier if the
combination rule collapses to a single mechanical predicate (all four axes
computable from the diff), at which point it belongs in `pr-coherence.py`
beside the other deterministic gate checks rather than standing alone.

Stdlib only. No network, no side effects on import. Python 3.7+.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Import the shared stakes predicate. `plugins/flow/lib/` is two levels up from
# `skills/gate/lib/`; resolve by path so this works from any cwd.
_LIB = Path(__file__).resolve().parents[3] / "lib"
if str(_LIB) not in sys.path:
    sys.path.insert(0, str(_LIB))
try:
    import sensitive_paths  # type: ignore
except ImportError as exc:  # pragma: no cover - exercised by the broken-install eval
    print(
        f"[gate-classify] ⚠️ BLOCKER: could not import the shared sensitivePaths predicate "
        f"from {_LIB} ({exc}). The stakes axis cannot be computed, so NO gate verdict is "
        f"available — this is not an approval. Reinstall the flow plugin.",
        file=sys.stderr,
    )
    sys.exit(2)

PREFIX = "[gate-classify]"

# §4.8 rollout, step 1 of 3. Not a config slot, deliberately — see the module
# docstring. Widening to "walk" is a later PR that ships together with the App
# identity, and it is a code change so that it is reviewable.
ROLLOUT_RUNG = "crawl"

_YES = {"yes", "y", "true"}
_NO = {"no", "n", "false"}


def _tri(value):
    """Normalise a yes/no axis to `green` / `red` / `unknown`.

    `unknown` is returned for anything not explicitly recognised, including
    None, the empty string and non-string types. Callers treat `unknown`
    exactly like `red`; it is kept distinct only so the report can say *why*
    an axis is red.

    There is deliberately no polarity flag. `ships_or_paperwork` is the one
    caller that looks like it wants inversion, and it cannot use one — it needs
    `unknown ⇒ ships`, which a polarity flag cannot express — so the flag would
    have had no reachable call site.
    """
    if value is None:
        return "unknown"
    v = str(value).strip().lower()
    if not v:
        return "unknown"
    if v in _YES:
        return "green"
    if v in _NO:
        return "red"
    return "unknown"


def _declared_axis(value, green_vocab, red_vocab, whys):
    """One shape for 'normalise an agent-declared axis, attach a per-state why'.

    Written once because there were two of them twenty lines apart in the same
    function, in two different spellings — a third axis would otherwise force
    the author to guess which one to copy.
    """
    v = str(value or "").strip().lower()
    state = "green" if v in green_vocab else "red" if v in red_vocab else "unknown"
    why = whys[state].format(value=repr(value)) if state == "unknown" else whys[state]
    return {"state": state, "why": why}


def _confidence_axis(confidence, critique_verdict):
    """§4.8: HIGH confidence **and** critique APPROVED with no open MEDIUM/LOW."""
    # `str()` before `.strip()`: a caller passing a non-string (a JSON number, a
    # list from a malformed findings buffer) must not crash the classifier. A gate
    # that raises is a gate that did not run, and the surrounding skill would be
    # left reporting nothing rather than escalating. Coerced, these fall through to
    # `unknown`, which escalates — the correct answer for input we cannot read.
    c = str(confidence or "").strip().lower()
    q = str(critique_verdict or "").strip().lower()
    if c not in {"high", "medium", "low"}:
        return "unknown", f"plan confidence not stated (got {confidence!r})"
    if q not in {"approved", "redirect", "findings"}:
        return "unknown", f"/flow:critique-plan verdict not stated (got {critique_verdict!r})"
    if c != "high":
        return "red", f"plan confidence is {c.upper()}, not HIGH"
    if q != "approved":
        return "red", f"/flow:critique-plan returned {q.upper()}, not APPROVED"
    return "green", "confidence HIGH and critique APPROVED"


def classify_plan(
    changed_files,
    reversible=None,
    confidence=None,
    critique_verdict=None,
    taste=None,
    prototype_attached=False,
    config_path="flow.config.json",
):
    """The four-axis plan-gate classification. Returns a dict; never raises."""
    patterns, source, warnings = sensitive_paths.load_patterns(config_path)
    stakes_raw = sensitive_paths.classify(changed_files, patterns)

    axes = {}
    # Stakes — computed, not declared.
    if not changed_files:
        # No file list is not "nothing is sensitive"; it is "we do not know".
        axes["stakes"] = {
            "state": "unknown",
            "why": "no changed-file list supplied, so sensitivePaths could not be evaluated",
        }
    elif stakes_raw["sensitive"]:
        names = sorted({m["pattern"] for m in stakes_raw["matches"]})
        axes["stakes"] = {
            "state": "red",
            # `sensitive_paths.classify()` returns only sensitive/matches — a
            # "reason" is set exclusively by its CLI fail-safe paths, which this
            # function never calls. An `or stakes_raw.get("reason")` here would
            # read as a connected wire and never carry anything.
            "why": f"diff touches sensitivePaths ({', '.join(names)})",
            "matches": stakes_raw["matches"],
        }
    else:
        axes["stakes"] = {"state": "green", "why": "diff touches no sensitivePaths entry"}

    axes["reversible"] = _declared_axis(reversible, _YES, _NO, {
        "green": "a plain `git revert` fully undoes this — no migration, no external side effect",
        "red": "declared NOT two-way-door (migration, released artifact, or other external side effect)",
        "unknown": "reversibility not declared (got {value})",
    })

    cstate, cwhy = _confidence_axis(confidence, critique_verdict)
    axes["confidence"] = {"state": cstate, "why": cwhy}

    # `taste` is stated as low/high; low is the green one.
    axes["taste"] = _declared_axis(taste, {"low"}, {"high"}, {
        "green": "a correct answer exists and is checkable by tests/critique",
        "red": "this is a visual / UX / product call",
        "unknown": "taste not declared (got {value})",
    })

    reds = [k for k, v in axes.items() if v["state"] != "green"]

    carve_out = None
    if prototype_attached:
        carve_out = (
            "prototype attached (§4.8 carve-out) — the prototype IS the high-taste artifact, "
            "so this plan gate is always human regardless of the other four axes"
        )

    approved = (not reds) and carve_out is None
    result = {
        "gate": "plan",
        "verdict": "approve" if approved else "escalate",
        "axes": axes,
        "red_axes": reds,
        "carve_out": carve_out,
        "pattern_source": source,
        "rollout_rung": ROLLOUT_RUNG,
        "warnings": warnings,
    }
    result["audit_line"] = render_audit_line(result)
    return result


def classify_merge(
    diff_class=None,
    verify_verdict=None,
    confidence=None,
    plan_axes_green=None,
):
    """The merge gate. **Always returns `human` at the crawl rung** — and still
    reports which of §4.8's three branches the change falls into, because the
    classification is the audit trail the rollout is earned with."""
    d = str(diff_class or "").strip().lower()
    v = str(verify_verdict or "").strip().lower()
    c = str(confidence or "").strip().lower()
    green = _tri(plan_axes_green)

    if d == "docs-only":
        branch = "docs-only"
        would_delegate = True
        why = "docs-only — no behavior to get wrong"
    elif d == "code" and v == "pass" and c in {"high", "extremely-high"} and green == "green":
        branch = "verified-code"
        would_delegate = True
        why = (
            "code with a real end-to-end verification (verify-build PASS), extremely-high "
            "confidence, and still in the plan-gate green quadrant — the green run is the proof"
        )
    else:
        branch = "anything-else"
        would_delegate = False
        bits = []
        if d not in {"docs-only", "code"}:
            bits.append(f"diff class not stated (got {diff_class!r})")
        if d == "code" and v != "pass":
            bits.append(f"verify-build is {v or 'unstated'}, not PASS — no behavioral proof")
        if d == "code" and c not in {"high", "extremely-high"}:
            bits.append(f"confidence is {c or 'unstated'}, not extremely-high")
        if d == "code" and green != "green":
            bits.append("not in the plan-gate green quadrant")
        why = "; ".join(bits) or "does not meet either delegable branch"

    result = {
        "gate": "merge",
        # Hard-wired. There is no input that makes this "orchestrator".
        "verdict": "human",
        "rollout_rung": ROLLOUT_RUNG,
        "classification": branch,
        "would_delegate_at_walk_rung": would_delegate,
        "why": why,
        "note": (
            "§4.8 rollout step 1 (crawl): every merge stays human and each classification is "
            "logged. Step 2 (walk) delegates docs-only and verified-code merges ONLY under the "
            "GitHub App identity, so that `merged_by` records who merged. That identity does not "
            "exist yet, so this verdict is not configurable."
        ),
    }
    # No stakes axis here, deliberately: the merge gate keys on explicit
    # VERIFIABILITY, and `plan_axes_green` already carries whether the change sat
    # in the plan-gate green quadrant — which is where stakes was evaluated. A
    # stakes block here had no caller: no SKILL.md passed a file list, `main()`
    # passed [], and no eval asserted it. A promise with no call site is dead code.
    result["audit_line"] = render_audit_line(result)
    return result


def ships_or_paperwork(changes_behavior=None, changes_consumer_surface=None, changes_gate_verdict=None):
    """§4.8 rule 7 / FB-0106, run BEFORE any escalation is formatted.

    If the code is identical either way and the question is documentation
    placement or wording, it is the orchestrator's call and escalating spends
    the human's attention on a null result. Unknown counts as "ships" — the
    asymmetry is stated in FB-0106: guessing paperwork wrongly is still
    catchable at the merge gate, guessing ships wrongly only costs a round trip.
    """
    axes = {
        "changes_behavior": _tri(changes_behavior),
        "changes_consumer_surface": _tri(changes_consumer_surface),
        "changes_gate_verdict": _tri(changes_gate_verdict),
    }
    # `green` here means "yes, it changes this" — so any yes/unknown ⇒ ships.
    ships = any(v in {"green", "unknown"} for v in axes.values())
    return {
        "classification": "ships" if ships else "paperwork",
        "axes": axes,
        "action": (
            "escalation is legitimate — this changes behaviour, a consumer surface, or a gate verdict"
            if ships
            else "RESOLVE IT YOURSELF. The diff is identical either way; this is documentation "
                 "placement or wording, which is the orchestrator's call (§4.8 rule 7, FB-0106). "
                 "Decide, act, and mention the call in one line."
        ),
    }


def render_audit_line(result) -> str:
    """One line per gate call, for the §4.8 crawl-rung audit log.

    It goes into the PR block in the project's plan doc — git-durable, with no
    new maintained ledger (§4.6 deletes ledger state-tracking by name).
    """
    if result.get("gate") == "merge":
        return (
            f"GATE merge · verdict=human (crawl rung) · classified={result['classification']} · "
            f"would-delegate-at-walk={str(result['would_delegate_at_walk_rung']).lower()} · {result['why']}"
        )
    axes = result.get("axes", {})
    states = " ".join(f"{k}={axes[k]['state']}" for k in ("stakes", "reversible", "confidence", "taste") if k in axes)
    tail = result.get("carve_out") or (
        "all four axes green" if result["verdict"] == "approve" else "; ".join(
            axes[k]["why"] for k in result.get("red_axes", []) if k in axes
        )
    )
    return f"GATE plan · verdict={result['verdict']} · {states} · {tail}"


def format_escalation(decision) -> str:
    """Render one escalation per FB-0090 + §4.8 rules 3/4/5.

    Refuses (returns a BLOCKER string) when `originating_session` is absent,
    because rule 5's return leg has nowhere to go: the orchestrator seat is the
    single human-facing decision surface **in both directions**, so an
    escalation is not finished when it is presented — it is finished when the
    answer has been relayed back to the worker that raised it. An escalation
    with no return address silently becomes "the human opens the worker
    workspace", which is the exact attention cost the seat exists to remove.
    """
    missing = [k for k in ("recommendation", "confidence", "justification") if not str(decision.get(k, "")).strip()]
    if missing:
        return (
            f"{PREFIX} ⚠️ BLOCKER: cannot format an escalation missing {', '.join(missing)}. "
            f"FB-0090 requires the recommendation / confidence / justification triple by default — "
            f"the human should never have to ask for the confidence or the why."
        )
    if not str(decision.get("originating_session", "")).strip():
        return (
            f"{PREFIX} ⚠️ BLOCKER: no originating_session. §4.8 rule 5 makes the seat the single "
            f"human-facing decision surface IN BOTH DIRECTIONS — without a return address the "
            f"human's answer cannot be relayed back and they end up opening the worker workspace "
            f"themselves, which is the cost the seat exists to remove."
        )
    conf = str(decision["confidence"]).strip().lower()
    if conf not in {"high", "medium", "low"}:
        return (
            f"{PREFIX} ⚠️ BLOCKER: confidence must be high / medium / low (got "
            f"{decision['confidence']!r}). A confidence the reader has to interpret is not one."
        )
    lines = []
    title = str(decision.get("title", "")).strip() or "Decision needed"
    # Rule 3, progressive disclosure: lead with the decision, not the context.
    lines.append(f"**{title}**")
    lines.append("")
    lines.append(f"- **Recommendation:** {str(decision['recommendation']).strip()}")
    lines.append(f"- **Confidence:** {conf}")
    lines.append(f"- **Why:** {str(decision['justification']).strip()}")
    others = [str(o).strip() for o in (decision.get("other_threads") or []) if str(o).strip()]
    if others:
        # Rule 4: one decision at a time, plus a one-line lay-of-the-land — never
        # a flat dump of unrelated asks, and never silent about parallel threads.
        lines.append("")
        lines.append(f"Also live ({len(others)}), nothing needed from you on these: " + "; ".join(others) + ".")
    lines.append("")
    lines.append(
        f"_Answer here and it goes back to the worker ({str(decision['originating_session']).strip()}) "
        f"from this seat — you never need to open its workspace._"
    )
    return "\n".join(lines)


def _read_files(path):
    if not path:
        return []
    try:
        return [ln for ln in Path(path).read_text(encoding="utf-8").splitlines() if ln.strip()]
    except OSError as exc:
        print(
            f"{PREFIX} ⚠️ could not read --files-file ({exc}); the stakes axis will be UNKNOWN, "
            f"which escalates. This is not an approval.",
            file=sys.stderr,
        )
        return []


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="gate-classify.py", description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("plan", help="four-axis plan-gate classification (§4.8)")
    p.add_argument("--files-file", help="newline-delimited changed-file list (a FILE, not argv — FB-0108)")
    p.add_argument("--reversible", help="yes | no")
    p.add_argument("--confidence", help="high | medium | low (the plan's own verdict)")
    p.add_argument("--critique-verdict", help="approved | redirect | findings")
    p.add_argument("--taste", help="low | high")
    p.add_argument("--prototype-attached", action="store_true")
    p.add_argument("--config", default="flow.config.json")

    m = sub.add_parser("merge", help="merge-gate classification (§4.8) — always `human` at the crawl rung")
    m.add_argument("--diff-class", help="docs-only | code")
    m.add_argument("--verify-verdict", help="pass | fail | unknown | skipped")
    m.add_argument("--confidence", help="extremely-high | high | medium | low")
    m.add_argument("--plan-axes-green", help="yes | no — is this still in the plan-gate green quadrant?")
    m.add_argument(
        "--plan-result",
        help="path to the JSON `gate-classify.py plan` already emitted for this change. "
             "Preferred over --plan-axes-green: retyping a verdict this same module computed "
             "minutes earlier is an agent-authored string standing in for an artifact that "
             "exists, inside a module whose whole thesis is that a wrong answer fails silently.",
    )

    s = sub.add_parser("ships-or-paperwork", help="§4.8 rule 7 / FB-0106 pre-check, run BEFORE escalating")
    s.add_argument("--changes-behavior", help="yes | no")
    s.add_argument("--changes-consumer-surface", help="yes | no")
    s.add_argument("--changes-gate-verdict", help="yes | no")

    f = sub.add_parser("format", help="render one escalation per FB-0090 + §4.8 rules 3/4/5")
    f.add_argument(
        "--decision-file", required=True,
        help="JSON: title, recommendation, confidence, justification, originating_session, "
             "other_threads[]. A FILE because the justification is agent-composed prose and "
             "routinely contains backticks (field manual T6).",
    )

    args = ap.parse_args(argv)

    if args.cmd == "plan":
        out = classify_plan(
            _read_files(args.files_file),
            reversible=args.reversible,
            confidence=args.confidence,
            critique_verdict=args.critique_verdict,
            taste=args.taste,
            prototype_attached=args.prototype_attached,
            config_path=args.config,
        )
        for w in out.get("warnings", []):
            print(w, file=sys.stderr)
        print(json.dumps(out, indent=2))
        return 0

    if args.cmd == "merge":
        plan_green = args.plan_axes_green
        if args.plan_result:
            try:
                prior = json.loads(Path(args.plan_result).read_text(encoding="utf-8"))
                # Read the artifact, not the retyped claim. A malformed or
                # non-plan file leaves plan_green as `None` ⇒ `unknown` ⇒ the
                # non-delegable branch, which is the safe direction.
                if isinstance(prior, dict) and prior.get("gate") == "plan":
                    plan_green = "yes" if prior.get("verdict") == "approve" else "no"
                else:
                    print(f"{PREFIX} ⚠️ --plan-result is not a plan-gate result; ignoring it.", file=sys.stderr)
            except (OSError, ValueError) as exc:
                print(f"{PREFIX} ⚠️ could not read --plan-result ({exc}); ignoring it.", file=sys.stderr)
        print(json.dumps(classify_merge(
            diff_class=args.diff_class,
            verify_verdict=args.verify_verdict,
            confidence=args.confidence,
            plan_axes_green=plan_green,
        ), indent=2))
        return 0

    if args.cmd == "ships-or-paperwork":
        print(json.dumps(ships_or_paperwork(
            args.changes_behavior, args.changes_consumer_surface, args.changes_gate_verdict
        ), indent=2))
        return 0

    if args.cmd == "format":
        try:
            decision = json.loads(Path(args.decision_file).read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            print(f"{PREFIX} ⚠️ BLOCKER: could not read --decision-file ({exc}).", file=sys.stderr)
            return 2
        rendered = format_escalation(decision if isinstance(decision, dict) else {})
        print(rendered)
        return 1 if "BLOCKER" in rendered else 0

    # No trailing `return 2`: `add_subparsers(..., required=True)` makes argparse
    # exit 2 itself before reaching here, so a fallback would be unreachable.
    raise AssertionError(f"unhandled subcommand {args.cmd!r}")  # pragma: no cover


if __name__ == "__main__":
    sys.exit(main())
