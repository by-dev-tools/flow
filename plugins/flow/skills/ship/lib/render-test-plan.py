#!/usr/bin/env python3
"""
Render the PR `## Test plan` section from the /flow:verify-build findings buffer.

The Test plan is a NON-FORGEABLE projection of the machine buffer, not
hand-authored prose: checkbox state = the buffer's per-criterion
`aggregated_verdict` AND its `provenance`, never the ship agent's say-so. A
criterion renders `[x]` only when it BOTH passed AND a fresh-context judge
produced that verdict (provenance `adversarial-judged` / `spike-rubric` —
verify-build Step 6/7). A criterion the implementing agent wrote by hand
(provenance `hand-authored`, or absent — the untrusting default) renders `[~]`
(a distinct self-report state) plus a visible "not adversarially judged" banner,
NEVER `[x]`: the renderer cannot be tricked into stamping a hand-authored buffer
as a machine verdict (the dogfound forgery hole). This is the enforcement half of
"the human verifies testing was done, then quick-merges" — the agent cannot show
a real green without a real PASS from a real judge. `[x]`/`[~]`/`[ ]` are reserved
EXCLUSIVELY for criterion states; the "what we did NOT test" list renders as plain
bullets so a box always means exactly one thing.

Used by `/flow:ship` Step 7: the agent runs this script and pastes stdout
verbatim as the PR body's `## Test plan` section.

Contract
--------
- Input (positional): buffer path (default flow.config.json.verifyFindingsPath
  → .flow/verify-findings.json; resolved by the caller, passed here).
- Flags:
    --branch <name>      current git branch (default: `git branch --show-current`)
    --head-sha <short>   current short HEAD sha (default: `git rev-parse --short HEAD`)
    --skipped <reason>   verify-build was skipped this run (e.g. "platform library");
                         forces the manual-verification fallback without reading the buffer.
- Output: a complete `## Test plan` markdown block to stdout. ALWAYS emits a
  valid, self-describing block (rendered or fallback) and ALWAYS exits 0, so the
  caller can paste it unconditionally. A one-line note on which path was taken
  goes to stderr (for the ship log).

Two render paths
----------------
1. RENDERED   — buffer present, fresh (branch + head_sha_short match current),
                parseable: a one-line headline verdict, one line per criterion
                with verdict + evidence, plus the `not_tested[]` list.
2. FALLBACK   — verify-build skipped (--skipped), no buffer, a STALE buffer
                (branch/sha mismatch — a prior run's artifact), a buffer whose
                freshness can't be confirmed (current git context unavailable),
                or a malformed/structurally-broken buffer. Renders an honest
                "no behavioral gate ran (<reason>); manual verification
                required" block. Never renders a stale buffer as if current
                (the freshness guard — see plan PR TP crit. 4).

Graceful-degradation (FB-0010 silent-skip defense): any read/parse/shape
failure falls through to the FALLBACK path with a named reason on stderr —
never a crash, never a silently-empty section.

Stdlib only. Python 3.7+.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

# Canonical provenance stamp (FB-0074). Every block this renderer emits carries it, and
# NOTHING else does — so its presence in a published PR body is the only evidence that the
# "## Test plan" came from this renderer rather than an agent's keyboard. The prose markers
# below tell a human not to hand-edit; this one lets a machine check whether they did.
# Consumed by `ship/lib/pr-coherence.py test-plan-provenance` at the Step 7 read-back.
# Keep in lockstep with PROVENANCE_MARKER there (FB-0010 fan-out).
PROVENANCE_MARKER = "<!-- flow:test-plan-rendered -->"

# The stamp above proves only that the renderer RAN. The realistic forgery is subtler:
# let ship render the section, then flip `[ ]` → `[x]` and leave the comment intact.
# So the stamp is also CONTENT-BOUND — it carries a digest over the criterion checkbox
# lines, which is exactly the payload that must not be editable. Deliberately scoped to
# those lines (not the whole block): surrounding prose is the human's to edit, and a
# whole-block hash would false-fail on a legitimate edit — and Step 7b exits 1, so a
# brittle digest would hard-block a good ship.
PROVENANCE_DIGEST_PREFIX = "<!-- flow:test-plan-digest "

# A criterion line: `- [x] …` / `- [ ] …` / `- [~] …` (the three renderable states).
_CHECKBOX_RE = re.compile(r"^\s*-\s\[([ x~])\]\s?(.*)$")


def checkbox_digest(block: str) -> str:
    """sha256 over the ORDERED checkbox STATES of a Test-plan block.

    Scope is deliberate: the states (and their count/order), NOT the criterion text.
    That is exactly what the contract protects — "checkbox state = machine verdict" —
    so flipping `[ ]`→`[x]`, or adding/removing a criterion line, changes the digest.
    Criterion TEXT is excluded because ship Step 7 explicitly instructs the agent to
    fill in the fallback block's `- [ ] <how to verify — fill in per the change>` line;
    hashing that text would make the documented happy path fail its own gate, and Step
    7b exits 1 — every `platform: library` PR (including flow's own) would be unshippable.
    A narrower true guarantee beats a wider one that has to be waived in practice.

    Shared by the renderer (writes) and pr-coherence.py (verifies) — keep the two in
    lockstep (FB-0010 fan-out); an eval asserts they agree on real renderer output.
    """
    states = [
        m.group(1)
        for m in (_CHECKBOX_RE.match(raw) for raw in block.replace("\r\n", "\n").split("\n"))
        if m
    ]
    payload = f"{len(states)}:" + "".join(states)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def stamp(block: str, marker: str) -> str:
    """Append the provenance marker + a content-bound digest of the block's checkboxes."""
    return f"{block}\n{marker}\n{PROVENANCE_DIGEST_PREFIX}{checkbox_digest(block)} -->"

RENDERED_MARKER = (
    PROVENANCE_MARKER + "\n"
    "<!-- Test plan rendered from the /flow:verify-build findings buffer; "
    "checkbox state = machine verdict, not self-report. Do not hand-edit "
    "criterion checkboxes. -->"
)
SELF_REPORT_MARKER = (
    PROVENANCE_MARKER + "\n"
    "<!-- Test plan rendered from the /flow:verify-build findings buffer; one or "
    "more criteria are HAND-AUTHORED (provenance != adversarial-judged/spike-rubric) "
    "and render [~] = implementer self-report, NOT a machine verdict. Do not hand-edit "
    "criterion checkboxes. -->"
)

# Provenance values that mean "a fresh-context judge produced this verdict" — the only
# states that earn a machine `[x]`. Everything else (including absent/unknown — the
# untrusting default) is implementer self-report and renders `[~]`.
_MACHINE_JUDGED = {"adversarial-judged", "spike-rubric"}


def _provenance(crit: dict) -> str:
    """Normalize a criterion's provenance. Absent/unrecognized ⇒ `hand-authored`
    (the load-bearing untrusting default — an un-stamped buffer reads as un-judged)."""
    p = str(crit.get("provenance", "") or "").strip()
    return p if p in _MACHINE_JUDGED or p == "hand-authored" else "hand-authored"


def _is_self_reported(prov: str) -> bool:
    return prov not in _MACHINE_JUDGED
FALLBACK_MARKER = (
    PROVENANCE_MARKER + "\n"
    "<!-- verify-build produced no current buffer; Test plan is manual. "
    "checkbox stays unchecked until a human verifies. -->"
)


def _git(args: list[str]) -> str:
    """Best-effort git read; empty string on any failure (caller handles)."""
    try:
        out = subprocess.run(
            ["git", *args],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return out.stdout.strip() if out.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def _verdict_badge(verdict: str) -> str:
    return {
        "PASS": "**PASS**",
        "FAIL": "**FAIL**",
        "Unknown": "**Unknown** (not verified)",
    }.get(verdict, f"**{verdict}**")


def _checkbox(aggregated_verdict: str, provenance: str) -> str:
    # A machine `[x]` requires BOTH a positive PASS AND a fresh-context-judge provenance.
    # FAIL / Unknown / anything else → `[ ]` (absence-of-failure is NOT a pass — FB-0018).
    # A hand-authored PASS → `[~]`: it passed by the implementer's own say-so, never judged,
    # so it must NOT masquerade as a machine verdict (the dogfound forgery hole).
    if aggregated_verdict != "PASS":
        return "[ ]"
    return "[x]" if provenance in _MACHINE_JUDGED else "[~]"


# Markdown metacharacters that let buffer text break out into a link, emphasis,
# inline code, or an HTML comment in the rendered PR body. Escaping the opener of
# each vector is sufficient: `\` (escape), backtick (code), `*`/`_` (emphasis),
# `[`/`]` (link text), `<` (HTML/comment opener). `>` is omitted deliberately — it
# is only a blockquote at line-start, and rendered buffer text never starts a line
# (every line is prefixed `- ` / `  ↳ `), so escaping it would only add noise to the
# common `>1 viewport`-style not_tested items.
_MD_ACTIVE = set("\\`*_[]<")


def _md_escape(text: str) -> str:
    """Neutralize Markdown-active characters in machine-extracted buffer strings
    (criterion text, judge notes, not_tested items) so crafted content from an
    app-under-test that the judge narrates verbatim cannot inject links, emphasis,
    or hidden HTML comments into the PR body a human reviews at the merge gate.
    Evidence uses _code_span instead — a literal observation reads better as a code
    span, which also neutralizes."""
    return "".join("\\" + ch if ch in _MD_ACTIVE else ch for ch in str(text))


def _code_span(text: str) -> str:
    """Wrap machine-extracted text in a backtick code span so Markdown-active
    characters in it (``*`` ``_`` ``#`` ``>``) can't reflow the PR body. Use a
    longer fence if the text itself contains a backtick."""
    s = str(text).strip()
    fence = "`"
    while fence in s:
        fence += "`"
    pad = " " if (s.startswith("`") or s.endswith("`")) else ""
    return f"{fence}{pad}{s}{pad}{fence}"


def _first_evidence(dimension: dict) -> str:
    ev = dimension.get("evidence") or []
    return str(ev[0]).strip() if ev else ""


def render_criterion(crit: dict, spike: bool) -> str:
    """One Test-plan line (plus an evidence/why sub-line) for a criterion."""
    text = _md_escape(str(crit.get("text", "(missing criterion text)")).strip())
    agg = str(crit.get("aggregated_verdict", "Unknown"))
    prov = _provenance(crit)
    verdicts = crit.get("verdicts") or {}

    badge = _verdict_badge(agg)
    if agg == "PASS" and _is_self_reported(prov):
        badge = "**PASS** (self-reported)"
    line = f"- {_checkbox(agg, prov)} {text} — {badge}"

    sub = ""
    if agg == "PASS":
        if _is_self_reported(prov):
            # A hand-authored green: name it loudly, then show the implementer's stated
            # evidence (labelled as a CLAIM, not a judged observation) if present.
            sub = ("\n  ↳ ⚠️ self-reported — marked by the implementing agent, "
                   "not checked by an independent judge that ran the app")
            ev = _first_evidence(verdicts.get("correctness") or {})
            if ev:
                sub += f"\n  ↳ stated evidence (unverified): {_code_span(ev)}"
        else:
            # Surface the observation that backs the pass (correctness evidence #1).
            ev = _first_evidence(verdicts.get("correctness") or {})
            if ev:
                sub = f"\n  ↳ evidence: {_code_span(ev)}"
    else:
        # Not green: surface WHY, per non-PASS dimension. In spike mode only
        # `correctness` is meaningful (regression/scope-creep are placeholder
        # Unknowns — verify-build/SKILL.md:165), so don't list them as real gaps.
        dims = ["correctness"] if spike else ["correctness", "regression", "scope-creep"]
        reasons = []
        for d in dims:
            dv = verdicts.get(d) or {}
            if dv.get("verdict") != "PASS":
                note = str(dv.get("notes", "")).strip()
                if note:
                    reasons.append(f"{d}: {_md_escape(note)}")
        if reasons:
            sub = "".join(f"\n  ↳ {r}" for r in reasons)
        else:
            # A red box with no recorded reason is unactionable — say so loudly
            # rather than leaving a bare unchecked line (ux-designer finding).
            sub = (
                f"\n  ↳ {agg}: no reason recorded in the buffer — "
                "inspect the verify-build run before merging"
            )
    return line + sub


def render_not_tested(not_tested: list) -> str:
    """Render the 'what we did NOT test' surface as PLAIN BULLETS (never
    checkboxes): these are out-of-scope residue the gate does not block on, and
    `tested` is agent-self-reported — keeping `[ ]`/`[x]` exclusive to machine
    verdicts means a checkbox always carries exactly one meaning."""
    if not not_tested:
        return ""
    lines = [
        "",
        "**What we did NOT test** (out of scope of the gate — do a real-world "
        "check if any of these matter before merging):",
    ]
    for entry in not_tested:
        if not isinstance(entry, dict):
            continue
        item = str(entry.get("item", "")).strip()
        if not item:
            continue
        prefix = "✓ tested — " if entry.get("tested") else ""
        rationale = str(entry.get("rationale", "")).strip()
        suffix = f" — {_md_escape(rationale)}" if rationale else ""
        lines.append(f"- {prefix}{_md_escape(item)}{suffix}")
    return "\n".join(lines)


def render_frame_integrity_failures(frame_integrity: list) -> str:
    """Plain-bullet surface for FB-0066 frame-integrity FAILs — never a checkbox
    (checkbox state is exclusively per-criterion machine verdict; see module
    docstring). Frame-integrity is criterion-independent (a property of the
    frame, not a declared assertion — SKILL.md), so it has no natural home in
    `render_criterion` and needs its own short section instead of silently
    living only in the ephemeral HTML report the human might not open."""
    fails = [f for f in frame_integrity if isinstance(f, dict) and str(f.get("verdict")) == "FAIL"]
    if not fails:
        return ""
    lines = [
        "",
        "**🚫 Frame integrity FAILED** (must-pass checklist on captured screenshots, "
        "independent of the declared criteria above — see the verify-build report for "
        "full edge-by-edge evidence):",
    ]
    for f in fails:
        label = str(f.get("state") or f.get("frame") or "captured frame").strip()
        items = [str(i).strip() for i in (f.get("failing_items") or []) if str(i).strip()]
        detail = f" — {_md_escape('; '.join(items))}" if items else ""
        lines.append(f"- {_md_escape(label)}{detail}")
        # Surface one line of the judge's own described evidence inline (not just the
        # checklist-item names) so the committed PR body is legible on its own, without
        # requiring the human to open the separate ephemeral HTML report to see WHY
        # (ux-designer finding: the checklist-item names alone don't explain the defect).
        evidence = str(f.get("background_continuity") or "").strip()
        if evidence:
            lines.append(f"  ↳ {_md_escape(evidence)}")
    return "\n".join(lines)


def _headline(n_pass: int, n: int, spike: bool, n_self_pass: int, frame_fail: bool = False) -> str:
    """One-line scannable verdict so the human can confirm-and-merge at a glance
    (push-further finding). A pure count over the criteria — no new trust
    surface, just a faster read of the verdicts already rendered below.

    `n_self_pass` = criteria that PASSED but on the implementer's own say-so
    (provenance not machine-judged → rendered `[~]`). When any are present the
    headline NEVER offers "confirm and merge" — a self-reported pass is an
    unverified claim. A self-reported FAIL/Unknown renders `[ ]` like any other
    unresolved criterion, so it's counted only in the `unresolved` tail.

    `frame_fail` = the buffer's `frame_integrity[]` carries a FAIL (FB-0066).
    This is checked FIRST and unconditionally overrides "confirm and merge" —
    frame-integrity is independent of the per-criterion verdicts (SKILL.md Step
    7: any frame_integrity FAIL forces overall_verdict FAIL regardless of
    criteria), so an all-criteria-PASS run must not headline green when a
    captured screenshot failed the must-pass visual checklist. Without this,
    render-test-plan.py — the one surface explicitly built to be non-forgeable —
    would print '✅ N/N passed — confirm and merge' next to a FAIL verdict
    elsewhere in the same PR body (the exact Potemkin-success class the plugin
    exists to prevent)."""
    noun = "smoke checks" if spike else "declared criteria"
    if frame_fail:
        crit_summary = (
            f"{n_pass}/{n} {noun} passed" if n_pass == n
            else f"{n_pass}/{n} {noun} passed, {n - n_pass} unresolved"
        )
        return (
            f"> 🚫 {crit_summary}, but a captured screenshot **FAILED the frame-integrity "
            'check** (see "Frame integrity" below). Do NOT merge — resolve the visual '
            "defect, then re-run `/flow:verify-build`."
        )
    if n_self_pass:
        unresolved = n - n_pass
        tail = f"; the remaining {unresolved} failed or are unverified" if unresolved else ""
        return (
            f"> ⚠️ {n_self_pass}/{n} {noun} are marked passing by the implementer alone "
            f"(`[~]` — not checked by an independent judge that ran the app){tail}. "
            "Do NOT treat as confirmed — re-run `/flow:verify-build` against a plan, "
            "or verify manually, before merging."
        )
    if n_pass == n:
        return f"> ✅ {n}/{n} {noun} passed — confirm and merge."
    return (
        f"> ⚠️ {n_pass}/{n} {noun} passed; {n - n_pass} unresolved "
        "(unchecked below — resolve before merging, do not merge as-is)."
    )


def fallback_block(reason: str) -> str:
    block = "\n".join(
        [
            "## Test plan",
            "",
            f"> ⚠️ **No behavioral gate ran** ({reason}). The verify-build findings "
            "buffer is not available for this PR, so the Test plan is **manual** — "
            "checkboxes stay unchecked until a human verifies. Confirm the change "
            "behaves as intended before merging.",
            "",
            "- [ ] <how to verify — fill in per the change>",
            "",
        ]
    )
    return stamp(block, FALLBACK_MARKER)


def empty_criteria_block(not_tested: list, frame_integrity: list | None = None) -> str:
    # A no-criteria run can still have captured + judged frames (§5a's capture gate is
    # decoupled from Spec-walk extraction — a Visual-walk block with no/malformed
    # Spec-walk still captures). A frame-integrity FAIL must not be silently dropped
    # just because there were no criteria to attach it to (staff-engineer finding).
    fi = render_frame_integrity_failures(frame_integrity or [])
    warn = (
        "> 🚫 verify-build extracted **no `**Spec-walk:**` criteria**, AND a captured "
        "screenshot **FAILED the frame-integrity check** (see below). Do NOT merge — "
        "resolve the visual defect, then re-run `/flow:verify-build`."
        if fi else
        "> ⚠️ verify-build ran but extracted **no `**Spec-walk:**` criteria** to "
        "verify — nothing was behaviorally gated. Declare acceptance criteria in "
        "the plan's `**Spec-walk:**` block, or verify manually before merging."
    )
    parts = [
        "## Test plan",
        "",
        warn,
        "",
        "- [ ] <no declared criteria — verify manually per the change>",
    ]
    if fi:
        parts.append(fi)
    nt = render_not_tested(not_tested)
    if nt:
        parts.append(nt)
    parts.append("")
    return stamp("\n".join(parts), RENDERED_MARKER)


def rendered_block(findings: dict, branch: str, sha: str) -> str:
    meta = findings.get("metadata") or {}
    spike = bool(meta.get("spike_mode"))
    criteria = [c for c in (findings.get("criteria") or []) if isinstance(c, dict)]

    if not criteria:
        return empty_criteria_block(findings.get("not_tested") or [], findings.get("frame_integrity"))

    n = len(criteria)
    n_pass = sum(1 for c in criteria if str(c.get("aggregated_verdict")) == "PASS")
    n_self_pass = sum(
        1 for c in criteria
        if _is_self_reported(_provenance(c)) and str(c.get("aggregated_verdict")) == "PASS"
    )
    any_self_reported = any(_is_self_reported(_provenance(c)) for c in criteria)
    frame_integrity = [f for f in (findings.get("frame_integrity") or []) if isinstance(f, dict)]
    frame_fail = any(str(f.get("verdict")) == "FAIL" for f in frame_integrity)

    label = "Spike smoke check" if spike else "Behavioral verification"
    context = f"`/flow:verify-build` — `{branch}` @ `{sha}`."
    if any_self_reported:
        # The forgery-defense banner: a hand-authored buffer can never claim "machine
        # verdict, not self-report." Name the [~] state so the reviewer reads it right.
        # Human-facing noun is "self-reported" everywhere (HTML report matches);
        # "hand-authored" stays an internal provenance token only.
        attribution = (
            f"⚠️ **Self-reported — not independently judged.** {context} One or more "
            "verdicts below were marked by the implementing agent itself, NOT by a "
            "fresh-context judge that actually ran the app and tried to break the claim. "
            "A self-reported criterion renders `[~]` (never `[x]`); treat it as an "
            "unverified claim, not a confirmed pass. "
            "`[x]` = independently-verified PASS · `[~]` = self-reported · `[ ]` = unverified/failed."
        )
    else:
        attribution = (
            f"{label} by {context} Checkbox state is the machine verdict from a "
            "fresh-context judge, not self-report."
        )

    body = [render_criterion(c, spike) for c in criteria]

    parts = ["## Test plan", "", _headline(n_pass, n, spike, n_self_pass, frame_fail), "", attribution, "", "\n".join(body)]

    fi = render_frame_integrity_failures(frame_integrity)
    if fi:
        parts.append(fi)

    nt = render_not_tested(findings.get("not_tested") or [])
    if nt:
        parts.append(nt)

    if n_pass < n:
        parts.append(
            "\n> An unchecked box above is a real, unresolved verification gap. "
            "If this PR is a draft, resolve it through the not-ready manifest "
            "in the PR body, not here."
        )

    parts.append("")
    return stamp("\n".join(parts), SELF_REPORT_MARKER if any_self_reported else RENDERED_MARKER)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Render PR Test plan from verify-build buffer.")
    parser.add_argument("buffer_path", help="path to the verify-build findings buffer JSON")
    parser.add_argument("--branch", default=None, help="current git branch (default: git branch --show-current)")
    parser.add_argument("--head-sha", default=None, help="current short HEAD sha (default: git rev-parse --short HEAD)")
    parser.add_argument("--skipped", default=None, help="verify-build skip reason; forces the manual fallback")
    args = parser.parse_args(argv[1:])

    def emit_fallback(reason: str, log: str) -> int:
        print(fallback_block(reason))
        print(f"[render-test-plan] FALLBACK — {log}", file=sys.stderr)
        return 0

    # Explicit skip signal from the caller (verify-build self-skipped at ship Step 2).
    if args.skipped:
        return emit_fallback(f"verify-build skipped: {args.skipped}", f"verify-build skipped: {args.skipped}")

    cur_branch = args.branch if args.branch is not None else _git(["branch", "--show-current"])
    cur_sha = args.head_sha if args.head_sha is not None else _git(["rev-parse", "--short", "HEAD"])

    buf = Path(args.buffer_path)
    if not buf.exists():
        return emit_fallback(f"no findings buffer at {buf}", f"no buffer at {buf}")

    try:
        findings = json.loads(buf.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return emit_fallback(f"findings buffer at {buf} is unreadable/malformed", f"buffer read/parse error: {exc}")

    if not isinstance(findings, dict) or "criteria" not in findings:
        return emit_fallback(f"findings buffer at {buf} is missing required fields", "buffer missing required fields")

    # Freshness guard (plan PR TP crit. 4). A buffer from a prior run on a
    # different branch/commit must NEVER be rendered as if it verified THIS PR.
    meta = findings.get("metadata") or {}
    buf_branch = str(meta.get("branch", ""))
    buf_sha = str(meta.get("head_sha_short", ""))
    buf_has_id = bool(buf_branch) or bool(buf_sha)
    have_current = bool(cur_branch) or bool(cur_sha)
    # If the buffer carries an identity but we cannot establish the current
    # branch/sha to compare against, we CANNOT prove freshness — fall back
    # rather than silently rendering a possibly-stale buffer as current
    # (staff-engineer finding: the invariant must not invert on empty git context).
    if buf_has_id and not have_current:
        return emit_fallback(
            "cannot confirm buffer freshness — current git context unavailable",
            "current branch/sha unavailable; refusing to render a possibly-stale buffer",
        )
    branch_mismatch = bool(cur_branch) and bool(buf_branch) and buf_branch != cur_branch
    sha_mismatch = bool(cur_sha) and bool(buf_sha) and buf_sha != cur_sha
    if branch_mismatch or sha_mismatch:
        reason = (
            f"stale buffer — it verified `{buf_branch or '?'}`@`{buf_sha or '?'}`, "
            f"but HEAD is `{cur_branch or '?'}`@`{cur_sha or '?'}`"
        )
        return emit_fallback(reason, reason)

    # Any structural surprise past the guards (a criteria entry that's the wrong
    # shape, a non-dict not_tested entry, etc.) routes to FALLBACK, never a crash
    # — the caller pastes stdout verbatim, so an exception (empty stdout) would
    # silently break the non-forgeability contract (staff-engineer BLOCKER).
    try:
        print(rendered_block(findings, cur_branch or buf_branch or "?", cur_sha or buf_sha or "?"))
    except Exception as exc:  # noqa: BLE001 — deliberate catch-all: fail to fallback, never crash
        return emit_fallback(f"findings buffer at {buf} is structurally malformed", f"render error: {exc}")

    print(
        f"[render-test-plan] RENDERED — {len(findings.get('criteria') or [])} criteria",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
