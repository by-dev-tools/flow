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

`--is-draft` / `--want-draft` take the literal strings `true`/`false` (gh's JSON
boolean, lower-cased). Body is read from --body-file, or from stdin when the path
is `-`. Always prints a single human-readable verdict line. Stdlib only, 3.7+.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Canonical manifest markers — keep in lockstep with the block ship Step 7 writes.
MANIFEST_MARKER = "<!-- flow:not-ready-manifest -->"
MANIFEST_HEADING = "🚫 NOT READY TO MERGE"


def has_manifest(body: str) -> bool:
    """True iff the body carries the NOT-READY manifest (marker OR heading)."""
    return MANIFEST_MARKER in body or MANIFEST_HEADING in body


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

    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
