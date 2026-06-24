#!/usr/bin/env python3
"""Eval harness for `/flow:ship`'s render-test-plan.py.

Runs the renderer against fixture buffers under fixtures/test-plan-render/ with
pinned --branch/--head-sha (so output is deterministic) and asserts the
load-bearing behaviors from plan § "PR TP" Spec-walk + the staff-review fixes:

  crit 1 — all criteria render (PASS *and* Unknown), with evidence.
  crit 2 — verdict drives checkbox state, unforgeably (PASS→[x]; else [ ]).
  crit 3 — not_tested[] renders into the body (as plain bullets, NOT checkboxes —
           so a `[ ]` only ever means an unverified criterion).
  crit 4 — skip / no-buffer / stale-buffer / unconfirmable-freshness / malformed
           → honest fallback, never a stale or crashed render.
  crit 5 — spike-mode renders only `correctness`; no placeholder regression/scope-creep gaps.
  + scannable one-line headline verdict; empty-criteria + no-notes-FAIL honesty.

Assertion-based (substring must/​must-not), not golden-diff: robust to cosmetic
wording tweaks while still pinning the behaviors that matter. Stdlib only.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
FIX = HERE / "fixtures" / "test-plan-render"
SCRIPT = HERE.parent / "skills" / "ship" / "lib" / "render-test-plan.py"

def case(cid, crit, fixture, must, must_not, *, branch="test-branch", sha=None, skipped=None):
    """Build a case tuple. `fixture` is a stem under FIX/ (use a non-existent stem
    to exercise the no-buffer path). `skipped` forces the --skipped fallback and
    suppresses branch/sha (the renderer never reads the buffer on that path)."""
    argv = [str(FIX / f"{fixture}.json")]
    if skipped is not None:
        argv += ["--skipped", skipped]
    else:
        argv += ["--branch", branch] + (["--head-sha", sha] if sha else [])
    return (cid, crit, argv, must, must_not)


# (id, crit, argv-after-script, must_contain[], must_not_contain[])
CASES = [
    case("all-pass-headline", "2", "all-pass",
         ["[x] Launches and renders", "[x] Submits the form",
          "2/2 declared criteria passed", "confirm and merge"],
         # a fully adversarial-judged buffer keeps the machine attribution and NEVER
         # shows the hand-authored banner or the [~] self-report state (the inverse of
         # the provenance fix — guards against a regression that flags judged buffers).
         ["No behavioral gate ran", "unresolved", "[ ] Launches",
          "Self-reported", "[~]", "(self-reported)"],
         sha="abc1234"),
    # provenance forgery defense: a hand-authored buffer (one criterion stamped
    # `hand-authored`, one with provenance ABSENT — the untrusting default) can NEVER
    # render `[x]` or claim a machine verdict. Both PASS criteria render `[~]`, the
    # headline withholds "confirm and merge", and the banner names the self-report state.
    case("hand-authored-no-machine-verdict", "P", "hand-authored",
         ["[~] Home page renders", "[~] Tapping a card",
          "Self-reported — not independently judged", "(self-reported)",
          "marked passing by the implementer alone"],
         ["[x] Home page", "[x] Tapping a card", "Checkbox state is the machine verdict",
          "confirm and merge", "2/2 declared criteria passed"],
         sha="abc1234"),
    case("mixed-renders-all", "1", "mixed",
         ["[x] User can submit", "[ ] Form validation rejects", "**Unknown** (not verified)",
          "empty-required-field path is not observable",
          "1/2 declared criteria passed", "1 unresolved"],
         ["No behavioral gate ran"],
         sha="abc1234"),
    case("mixed-not-tested-plain-bullets", "3", "mixed",
         ["What we did NOT test", "- >1 browser engine", "unresolved verification gap"],
         # not_tested renders as a plain bullet, NEVER a checkbox (so `[ ]` only
         # ever means an unverified criterion):
         ["[ ] >1 browser engine", "[x] >1 browser engine"],
         sha="abc1234"),
    case("spike-correctness-only", "5", "spike",
         ["Spike smoke check", "[x] Launch: the built artifact starts", "1/1 smoke checks passed"],
         ["regression:", "scope-creep:", "dimension not applicable"],
         branch="spike-branch", sha="5p1ke00"),
    case("stale-buffer-fallback", "4", "mixed",
         ["No behavioral gate ran", "stale buffer", "manual"],
         ["[x] User can submit"],
         sha="deadbee"),
    case("skipped-fallback", "4", "mixed",
         ["No behavioral gate ran", "verify-build skipped: platform library"],
         ["[x] User can submit"],
         skipped="platform library"),
    case("no-buffer-fallback", "4", "__absent__",
         ["No behavioral gate ran", "no findings buffer"],
         ["[x]"],
         branch="x", sha="y"),
    case("malformed-buffer-fallback", "4", "malformed",
         # passes the top guard (dict + 'criteria') but a criterion's `verdicts`
         # is a string → must fall back, NEVER crash to empty stdout (BLOCKER).
         ["No behavioral gate ran", "structurally malformed"],
         ["[x] Structurally broken"],
         sha="abc1234"),
    case("empty-criteria-honest", "4", "empty-criteria",
         ["no `**Spec-walk:**` criteria", "verify manually"],
         ["[x]", "✅", "confirm and merge"],
         sha="abc1234"),
    case("no-notes-fail-actionable", "1", "no-notes",
         ["[ ] Thing works end to end", "**FAIL**", "no reason recorded in the buffer"],
         ["✅"],
         sha="abc1234"),
    # security: buffer strings (criterion text, judge notes, not_tested items) are
    # Markdown-escaped so app-under-test content the judge narrates can't inject a
    # link / emphasis / hidden HTML comment into the PR body (security-review finding).
    case("markdown-injection-neutralized", "2", "malicious-content",
         [r"\[admin\]", r"\*bold\*", r"\<!-- hide approval", r"not\_tested"],
         ["[admin](https://evil.example)", "*bold*"],  # working link / emphasis forms must NOT survive
         sha="abc1234"),
]

# Raw case: empty current git context (both --branch and --head-sha empty) must
# NOT render a buffer-with-identity as fresh — the freshness invariant must not
# invert (staff-engineer finding). case() drops an empty --head-sha, so build it raw.
CASES.append((
    "unconfirmable-freshness-fallback", "4",
    [str(FIX / "mixed.json"), "--branch", "", "--head-sha", ""],
    ["No behavioral gate ran", "cannot confirm buffer freshness"],
    ["[x] User can submit"],
))


def run(argv: list[str]) -> str:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), *argv],
        capture_output=True, text=True, check=False,
    )
    if proc.returncode != 0:
        return f"<<non-zero exit {proc.returncode}>>\n{proc.stderr}"
    return proc.stdout


def main() -> int:
    fails = 0
    for cid, crit, argv, must, must_not in CASES:
        out = run(argv)
        missing = [s for s in must if s not in out]
        present = [s for s in must_not if s in out]
        if missing or present:
            fails += 1
            print(f"FAIL  [{cid}] (crit {crit})")
            for s in missing:
                print(f"        missing: {s!r}")
            for s in present:
                print(f"        unexpected: {s!r}")
        else:
            print(f"PASS  [{cid}] (crit {crit})")
    total = len(CASES)
    print(f"\n{total - fails} passed, {fails} failed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
