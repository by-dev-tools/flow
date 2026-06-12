#!/usr/bin/env python3
"""
Render the PR `## Test plan` section from the /flow:verify-build findings buffer.

The Test plan is a NON-FORGEABLE projection of the machine buffer, not
hand-authored prose: checkbox state = the buffer's per-criterion
`aggregated_verdict`, never the ship agent's say-so. A criterion can only
render `[x]` when an adversarial fresh-context judge returned PASS for it
(verify-build Step 6/7). This is the enforcement half of "the human verifies
testing was done, then quick-merges" — the agent cannot show green without a
real PASS in the buffer. Checkboxes are reserved EXCLUSIVELY for machine
verdicts; the "what we did NOT test" list renders as plain bullets so a `[ ]`
always means exactly one thing (an unverified criterion).

Used by `/flow:ship` Step 7: the agent runs this script and pastes stdout
verbatim as the PR body's `## Test plan` section.

Contract
--------
- Input (positional): buffer path (default flow.config.json.verifyFindingsPath
  → /tmp/flow-verify-findings.json; resolved by the caller, passed here).
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
import json
import subprocess
import sys
from pathlib import Path

RENDERED_MARKER = (
    "<!-- Test plan rendered from the /flow:verify-build findings buffer; "
    "checkbox state = machine verdict, not self-report. Do not hand-edit "
    "criterion checkboxes. -->"
)
FALLBACK_MARKER = (
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


def _checkbox(aggregated_verdict: str) -> str:
    # Only a positive PASS earns a checked box. FAIL / Unknown / anything else
    # stays unchecked — absence-of-failure is NOT a pass (FB-0018).
    return "[x]" if aggregated_verdict == "PASS" else "[ ]"


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
    verdicts = crit.get("verdicts") or {}

    line = f"- {_checkbox(agg)} {text} — {_verdict_badge(agg)}"

    sub = ""
    if agg == "PASS":
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


def _headline(n_pass: int, n: int, spike: bool) -> str:
    """One-line scannable verdict so the human can confirm-and-merge at a glance
    (push-further finding). A pure count over the criteria — no new trust
    surface, just a faster read of the verdicts already rendered below."""
    noun = "smoke checks" if spike else "declared criteria"
    if n_pass == n:
        return f"> ✅ {n}/{n} {noun} passed — confirm and merge."
    return (
        f"> ⚠️ {n_pass}/{n} {noun} passed; {n - n_pass} unresolved "
        "(unchecked below — resolve before merging, do not merge as-is)."
    )


def fallback_block(reason: str) -> str:
    return "\n".join(
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
            FALLBACK_MARKER,
        ]
    )


def empty_criteria_block(not_tested: list) -> str:
    parts = [
        "## Test plan",
        "",
        "> ⚠️ verify-build ran but extracted **no `**Spec-walk:**` criteria** to "
        "verify — nothing was behaviorally gated. Declare acceptance criteria in "
        "the plan's `**Spec-walk:**` block, or verify manually before merging.",
        "",
        "- [ ] <no declared criteria — verify manually per the change>",
    ]
    nt = render_not_tested(not_tested)
    if nt:
        parts.append(nt)
    parts.append("")
    parts.append(RENDERED_MARKER)
    return "\n".join(parts)


def rendered_block(findings: dict, branch: str, sha: str) -> str:
    meta = findings.get("metadata") or {}
    spike = bool(meta.get("spike_mode"))
    criteria = [c for c in (findings.get("criteria") or []) if isinstance(c, dict)]

    if not criteria:
        return empty_criteria_block(findings.get("not_tested") or [])

    n = len(criteria)
    n_pass = sum(1 for c in criteria if str(c.get("aggregated_verdict")) == "PASS")

    label = "Spike smoke check" if spike else "Behavioral verification"
    attribution = (
        f"{label} by `/flow:verify-build` — `{branch}` @ `{sha}`. Checkbox state "
        "is the machine verdict from an adversarial fresh-context judge, not "
        "self-report."
    )

    body = [render_criterion(c, spike) for c in criteria]

    parts = ["## Test plan", "", _headline(n_pass, n, spike), "", attribution, "", "\n".join(body)]

    nt = render_not_tested(findings.get("not_tested") or [])
    if nt:
        parts.append(nt)

    if n_pass < n:
        parts.append(
            "\n> An unchecked box above is a real, unresolved verification gap. "
            "If this PR is a draft, resolve via the `🚫 NOT READY TO MERGE` "
            "manifest, not here."
        )

    parts.append("")
    parts.append(RENDERED_MARKER)
    return "\n".join(parts)


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
