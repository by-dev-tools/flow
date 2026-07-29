#!/usr/bin/env python3
"""Deterministic PR body↔draft-state coherence + read-back engine (FB-0067).

The `🚫 NOT READY TO MERGE` manifest is a flow-authored artifact: `/flow:ship`
writes it into a PR body when the draft manifest is non-empty (a decision-required
blocker exists) and scrubs it once the manifest empties. That lifecycle is correct
only if the write actually lands AND if nothing ever leaves the two facts out of
sync. Two failure modes this module pins down deterministically:

  1. A PR-body write that silently no-ops (e.g. `gh pr edit … | tail -1 && gh pr
     ready` — the pipe makes the pipeline exit status `tail`'s 0, masking gh's
     non-zero) leaves a stale body and reports success. `readback` re-checks that
     the intended substrings are present/absent and the draft state matches intent.

  2. A PR that is NOT a draft but whose body still carries the manifest — the exact
     recurring bug. `coherence` asserts the invariant:

         NOT isDraft  ⇒  body does NOT contain the NOT-READY manifest
         (contrapositive: manifest present  ⇒  isDraft)

     Draft-with-manifest is correct (PASS); draft-without-manifest is fine too (a PR
     can be a draft for other reasons); ready-with-manifest is the violation (FAIL).

Manifest detection is the single source of truth for every caller (ship, doctor,
land, ship-spike, staff-review). A body "carries the manifest" iff it contains the
canonical marker comment OR the human-readable heading — either one is enough, so a
hand-edit that stripped one but not the other still trips the check.

Subcommands:
  coherence  --body-file PATH|-  --is-draft {true,false}
             exit 0 PASS (coherent), 1 FAIL (ready PR carries the manifest), 2 usage.

  readback   --body-file PATH|-  --is-draft {true,false}
             [--expect SUBSTR ...] [--forbid SUBSTR ...] [--want-draft {true,false}]
             Post-write verification. Asserts every --expect substring is present,
             every --forbid substring is absent, isDraft matches --want-draft when
             given, AND the coherence invariant holds. exit 0 PASS, 1 FAIL, 2 usage.

  test-plan-provenance  --body-file PATH|-
             Third failure mode (FB-0074): the "## Test plan" is *specified* as a
             non-forgeable projection of the verify-build buffer, but nothing ever
             checked that a published block came from the renderer — so an agent
             could hand-write it and hand-tick the boxes, silently converting a
             mechanical gate into a self-assertion. `render-test-plan.py` stamps
             every path it emits (including the no-buffer fallback) with
             PROVENANCE_MARKER **plus a digest over the checkbox states**, so two
             forgeries are caught: a hand-written block (no stamp), and a rendered
             block whose boxes were flipped afterwards (digest mismatch). The digest
             deliberately excludes criterion prose — ship Step 7 tells the agent to
             fill in the fallback's `<how to verify>` text.
             exit 0 PASS/N-A, 1 FAIL (forged), 2 usage.

`--is-draft` / `--want-draft` take the literal strings `true`/`false` (gh's JSON
boolean, lower-cased). Body is read from --body-file, or from stdin when the path
is `-`. Always prints a single human-readable verdict line. Stdlib only, 3.7+.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path

# Canonical manifest markers — keep in lockstep with the block ship Step 7 writes.
MANIFEST_MARKER = "<!-- flow:not-ready-manifest -->"
MANIFEST_HEADING = "🚫 NOT READY TO MERGE"

# Canonical Test-plan provenance stamp — keep in lockstep with
# `ship/lib/render-test-plan.py::PROVENANCE_MARKER` (FB-0010 fan-out).
PROVENANCE_MARKER = "<!-- flow:test-plan-rendered -->"
PROVENANCE_DIGEST_PREFIX = "<!-- flow:test-plan-digest "
TEST_PLAN_HEADING = "## Test plan"

# Must match `render-test-plan.py::_CHECKBOX_RE` / `checkbox_digest` exactly.
_CHECKBOX_RE = re.compile(r"^\s*-\s\[([ x~])\]\s?(.*)$")
_DIGEST_RE = re.compile(re.escape(PROVENANCE_DIGEST_PREFIX) + r"([0-9a-f]+) -->")


def checkbox_digest(block: str) -> str:
    """Recompute the renderer's digest over ORDERED checkbox STATES.

    Must stay byte-identical to `render-test-plan.py::checkbox_digest` (FB-0010
    fan-out). States only, not criterion text — see that docstring for why.
    """
    states = [
        m.group(1)
        for m in (_CHECKBOX_RE.match(raw) for raw in block.replace("\r\n", "\n").split("\n"))
        if m
    ]
    payload = f"{len(states)}:" + "".join(states)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def has_manifest(body: str) -> bool:
    """True iff the body carries the NOT-READY manifest (marker OR heading)."""
    return MANIFEST_MARKER in body or MANIFEST_HEADING in body


def strip_fenced(body: str) -> tuple:
    """(unfenced_text, unclosed_fence) — drop fenced code blocks (``` and ~~~).

    A PR body that *documents* the Test-plan format carries a fenced example
    containing a literal `## Test plan` and no stamp. Counting that as a real
    section would fail a PR whose actual Test plan is fine, and Step 7b exits 1,
    so that false positive would hard-block a good ship. Only unfenced text is
    the real body structure.

    Two hardenings, both from a red-team pass that turned this parser into a
    bypass of the gate it feeds:

    - **A fence opener must be indented < 4 spaces.** CommonMark (and GitHub)
      render 4-space-indented ``` as an *indented code block*, not a fence. A
      parser that treats it as a fence swallows the rest of the body while the
      reader sees normal markdown — so `    ``` ` above a forged Test plan made
      the section vanish and the check return N/A + exit 0.
    - **An unclosed fence is reported, never silently swallowed.** Otherwise the
      remainder of the body disappears from the parser's view and every
      downstream question answers "not present" — the "I never looked" reading
      that FB-0074 exists to eliminate. The caller fails closed on it.

    Tracks the opening delimiter so a ``` inside a ~~~ block (or vice versa)
    doesn't close it early.
    """
    out, fence = [], None
    for line in body.splitlines():
        indent = len(line) - len(line.lstrip())
        stripped = line.lstrip()
        opener = indent < 4 and (stripped.startswith("```") or stripped.startswith("~~~"))
        if fence is None:
            if opener:
                fence = stripped[:3]
                continue
            out.append(line)
        elif opener and stripped.startswith(fence):
            fence = None
    return "\n".join(out), fence is not None


def test_plan_sections(body: str) -> tuple:
    """(sections, unclosed_fence) — EVERY unfenced `## Test plan` section.

    A section runs heading → next sibling `## ` heading (or EOF); `###` subsections
    stay inside it. Scope matters: the renderer digests ONLY its own block, so the
    verifier must too — digesting the whole body would fold in every unrelated
    `- [ ]` a human put in the PR description and hard-fail a good ship.

    Returns ALL matches, not the first. Verifying only the first is a bypass: keep
    the honest stamped block and append a second all-ticked `## Test plan`, and the
    gate validates the one nobody reads while the reviewer reads the other.
    """
    needle = TEST_PLAN_HEADING.lower()
    text, unclosed = strip_fenced(body)
    lines = text.splitlines()
    starts = [
        i for i, ln in enumerate(lines)
        if ln.strip().lower().startswith(needle)
    ]
    sections = []
    for start in starts:
        end = len(lines)
        for j in range(start + 1, len(lines)):
            s = lines[j].lstrip()
            if s.startswith("## ") and not s.startswith("### "):
                end = j
                break
        sections.append("\n".join(lines[start:end]))
    return sections, unclosed


def _read_body(path: str) -> str:
    if path == "-":
        return sys.stdin.read()
    p = Path(path)
    if not p.is_file():
        sys.stderr.write(f"[pr-coherence] body file not found: {path}\n")
        raise SystemExit(2)
    return p.read_text(encoding="utf-8")


def _parse_bool(val: str, label: str) -> bool:
    v = val.strip().lower()
    if v in ("true", "1", "yes"):
        return True
    if v in ("false", "0", "no"):
        return False
    sys.stderr.write(f"[pr-coherence] {label} must be true|false (got: {val!r})\n")
    raise SystemExit(2)


def _coherence_violation(body: str, is_draft: bool) -> str | None:
    """Return a failure message if the invariant is violated, else None."""
    if has_manifest(body) and not is_draft:
        return (
            "PR is NOT a draft but its body still carries the "
            f'"{MANIFEST_HEADING}" manifest — a ready PR that contradicts its own '
            "state. Scrub the manifest from the body and re-verify (see /flow:ship "
            "§7c for the no-reviewer reconcile path), or convert the PR back to a draft."
        )
    return None


def cmd_coherence(args) -> int:
    body = _read_body(args.body_file)
    is_draft = _parse_bool(args.is_draft, "--is-draft")
    violation = _coherence_violation(body, is_draft)
    if violation is None:
        state = "draft" if is_draft else "ready"
        carries = "carries" if has_manifest(body) else "no"
        print(f"[pr-coherence] PASS — {state} PR, {carries} manifest: coherent.")
        return 0
    print(f"[pr-coherence] FAIL — {violation}")
    return 1


def cmd_readback(args) -> int:
    body = _read_body(args.body_file)
    is_draft = _parse_bool(args.is_draft, "--is-draft")
    failures: list[str] = []

    for substr in args.expect or []:
        if substr not in body:
            failures.append(f"expected substring absent from body: {substr!r}")
    for substr in args.forbid or []:
        if substr in body:
            failures.append(f"forbidden substring present in body: {substr!r}")
    if args.want_draft is not None:
        want = _parse_bool(args.want_draft, "--want-draft")
        if is_draft != want:
            failures.append(
                f"draft state mismatch: PR isDraft={str(is_draft).lower()}, "
                f"intended isDraft={str(want).lower()}"
            )
    # A read-back can never pass on an incoherent state, even if the caller forgot
    # to forbid the manifest explicitly.
    violation = _coherence_violation(body, is_draft)
    if violation is not None:
        failures.append(violation)

    if not failures:
        print("[pr-coherence] readback PASS — the write took; body + draft state match intent.")
        return 0
    print("[pr-coherence] readback FAIL — the intended write did not land:")
    for f in failures:
        print(f"  - {f}")
    return 1


def cmd_test_plan_provenance(args) -> int:
    body = _read_body(args.body_file)

    # One parse. `test_plan_sections` fence-strips and scopes to the section(s) —
    # the same scope the renderer digests (see its docstring).
    sections, unclosed = test_plan_sections(body)

    if unclosed:
        # Fail closed. An unclosed fence hides the rest of the body from this parser,
        # so every question below would answer "not present" — and a body crafted with
        # one was the way to make a forged Test plan read as N/A.
        print(
            "[pr-coherence] test-plan-provenance FAIL — the body has an unclosed code "
            "fence, so its structure cannot be parsed reliably. Everything after the "
            "opener is invisible to this check, which means a Test plan there would go "
            "unverified.\n"
            "  Fix: close the fence in the PR body, then re-run."
        )
        return 1

    if len(sections) > 1:
        # Verifying only the first section is a bypass: keep the honest stamped block,
        # append a second all-ticked one, and the reviewer reads the section the gate
        # never looked at.
        print(
            f"[pr-coherence] test-plan-provenance FAIL — {len(sections)} '## Test plan' "
            "sections in one body; exactly one is allowed. Verifying one while a reader "
            "sees another is precisely the ambiguity this gate exists to remove.\n"
            "  Fix: delete the extra section(s) and keep the single rendered block."
        )
        return 1

    if not sections:
        # Standalone use may legitimately have no Test plan; `/flow:ship` always writes
        # one, so there it means something went wrong — ship passes --require-section
        # so absence routes to the failure path instead of a clean exit.
        if getattr(args, "require_section", False):
            print(
                "[pr-coherence] test-plan-provenance FAIL — no '## Test plan' section in "
                "the body, but one was required. /flow:ship Step 7 writes a Test plan on "
                "every PR, so its absence means the write did not land (or was removed) — "
                "not that the PR needs no verification.\n"
                "  Fix: re-render with ship/lib/render-test-plan.py and re-publish the body."
            )
            return 1
        print("[pr-coherence] test-plan-provenance N/A — body declares no '## Test plan' section.")
        return 0

    section = sections[0]

    # Match the stamp OUTSIDE fences too, for the mirror reason: a doc example that
    # quotes the marker inside a fence must not launder a hand-authored Test plan.
    if PROVENANCE_MARKER not in section:
        print(
            "[pr-coherence] test-plan-provenance FAIL — '## Test plan' present without the "
            f"renderer stamp ({PROVENANCE_MARKER}), so its checkboxes are self-assertion, "
            "not machine verdicts.\n"
            "  Fix: re-render with ship/lib/render-test-plan.py (it stamps every path, "
            "including the no-buffer fallback) and re-publish.\n"
            "  Note: filling in the fallback's `<how to verify>` text is fine — the stamp "
            "covers checkbox STATE, not the surrounding prose. Re-typing the block is not."
        )
        return 1

    # The marker alone proves only that the renderer ran at some point. The realistic
    # forgery is flipping `[ ]` → `[x]` on a genuinely-rendered block and leaving the
    # comment intact — so verify the content digest too.
    m = _DIGEST_RE.search(section)
    if not m:
        print(
            "[pr-coherence] test-plan-provenance FAIL — the Test plan carries the renderer "
            f"stamp but no content digest ({PROVENANCE_DIGEST_PREFIX}…). Either it was "
            "rendered by a pre-v1.22.0 renderer (re-render to upgrade it) or the digest "
            "line was stripped. A stamp without a digest attests nothing about checkbox state."
        )
        return 1

    want, got = m.group(1), checkbox_digest(section)
    if want != got:
        print(
            "[pr-coherence] test-plan-provenance FAIL — checkbox state does NOT match the "
            f"renderer's digest (stamped {want}, body hashes to {got}). A criterion box was "
            "edited after rendering, which converts a machine verdict into a self-assertion "
            "— the exact forgery this gate exists to catch.\n"
            "  Fix: re-run /flow:verify-build so the buffer reflects reality, then re-render "
            "with ship/lib/render-test-plan.py. Never hand-tick a criterion box."
        )
        return 1

    print(
        "[pr-coherence] test-plan-provenance PASS — Test plan carries the renderer stamp "
        f"and its checkbox state matches the rendered digest ({want})."
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pr-coherence.py")
    sub = parser.add_subparsers(dest="cmd", required=True)

    co = sub.add_parser("coherence", help="assert the body↔draft invariant")
    co.add_argument("--body-file", required=True, help="path to the PR body, or - for stdin")
    co.add_argument("--is-draft", required=True, help="true|false (gh isDraft)")
    co.set_defaults(func=cmd_coherence)

    rb = sub.add_parser("readback", help="verify a PR-body write took")
    rb.add_argument("--body-file", required=True, help="path to the re-fetched PR body, or - for stdin")
    rb.add_argument("--is-draft", required=True, help="true|false (re-fetched isDraft)")
    rb.add_argument("--expect", action="append", default=[], help="substring that MUST be present (repeatable)")
    rb.add_argument("--forbid", action="append", default=[], help="substring that must be ABSENT (repeatable)")
    rb.add_argument("--want-draft", default=None, help="true|false the draft state should now be")
    rb.set_defaults(func=cmd_readback)

    tp = sub.add_parser(
        "test-plan-provenance",
        help="assert a published '## Test plan' carries the renderer stamp (not hand-authored)",
    )
    tp.add_argument("--body-file", required=True, help="path to the PR body, or - for stdin")
    tp.add_argument(
        "--require-section", action="store_true",
        help="treat a missing '## Test plan' as FAIL (ship always writes one, so its "
             "absence there means the write did not land — not that none was needed)",
    )
    tp.set_defaults(func=cmd_test_plan_provenance)

    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
