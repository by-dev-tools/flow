#!/usr/bin/env python3
"""The control-line VOCABULARY pin for /flow:audit-coverage (CV1).

THE BUG IT PINS, and it is a claim rather than a crash. `audit-coverage/SKILL.md`'s prose tells
the reviewer to quote any `WEAKENED ·` line verbatim, then ENUMERATES every instance by name --
and the enumeration carried a footnote saying "the list is now pinned by an eval rather than by
this sentence". **No such eval existed.** The list was complete by author memory, in the bullet
whose own text records that two instances had already shipped unnamed once.

That is the FB-0010 fan-out class with a false assurance attached, which is worse than the plain
version: a reader who checks finds a sentence claiming the check exists.

So this harness DERIVES the vocabulary from the shipped emitters -- the SKILL.md's own shell and
the two Python libs -- and asserts the prose enumerates every token. Adding a weakening instance
now costs one edit here, and forgetting it is red rather than invisible.

Stdlib only. Run:
    python3 plugins/flow/evals/run_coverage_vocab_evals.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).parent
SKILLS = HERE.parent / "skills"
AC = SKILLS / "audit-coverage"

_failures: list = []


def check(name, cond, detail=""):
    if cond:
        print(f"  PASS  {name}")
    else:
        print(f"  FAIL  {name}" + (f"\n          {detail}" if detail else ""))
        _failures.append(name)
    return bool(cond)


TOKEN = re.compile(r"WEAKENED\s*·\s*([A-Z][A-Z-]+)")

# The emitters: everything that can print a weakening control line at runtime.
EMITTERS = [AC / "SKILL.md", AC / "lib" / "change-inventory.py", AC / "lib" / "evidence-budget.py"]
# The enumeration the prose rule points the reviewer at.
PROSE = AC / "SKILL.md"


def main() -> int:
    print("audit-coverage control-line vocabulary evals (CV1)")
    skill = PROSE.read_text(encoding="utf-8")

    emitted = set()
    for f in EMITTERS:
        if not f.exists():
            check(f"emitter present: {f.name}", False, "cannot derive the vocabulary from a missing file")
            continue
        emitted |= set(TOKEN.findall(f.read_text(encoding="utf-8")))

    # The enumeration lives in the bullet that opens with this phrase. Anchored on the phrase,
    # not a line number, so re-wrapping the paragraph does not silently empty the check.
    i = skill.find("The instances today, all carrying the token")
    check("the prose enumeration is findable", i != -1,
          "the bullet this harness reads was renamed or removed; a vocabulary pin that cannot "
          "find the list it pins passes vacuously")
    listed = set(re.findall(r"`([A-Z][A-Z-]+)`", skill[i:i + 3000])) if i != -1 else set()

    # THE POSITIVE: every token an emitter can print is named in the prose.
    missing = sorted(emitted - listed)
    check("every emitted WEAKENED token is enumerated in the prose",
          not missing,
          f"emitted but NOT listed: {missing}. The reviewer is told to quote any WEAKENED line "
          "verbatim, so an unlisted instance is one the prose never taught it to expect.")

    # THE PAIRED NEGATIVE (general.md item 3): the check must be able to fail. A prose list that
    # named nothing would satisfy "no missing tokens" only if `emitted` were also empty -- so
    # assert both sets are non-trivially populated, or this whole harness is decorative.
    check("the derived vocabulary is non-empty (the instrument reads something)",
          len(emitted) >= 5, f"derived only {sorted(emitted)} — extraction is probably broken")
    check("the prose list is non-empty", len(listed) >= 5, f"listed only {sorted(listed)}")

    # SPELLING, not just completeness -- and this is the hole the floor above cannot see.
    # `emitted` is DERIVED by matching `WEAKENED ·`, so a separator typo on ONE emitter
    # (`WEAKENED - DOC-BLIND`, an ASCII hyphen for the U+00B7) removes that token from
    # `emitted` rather than adding it to `missing`: `emitted - listed` stays empty, the count
    # stays above the floor, and the eval passes GREEN while the consumer-side rule -- which
    # matches on the token, by design, so new instances are covered by construction -- silently
    # stops matching that one line. `change-inventory.py`'s docstring flags the separator in
    # capitals and asks the author to remember it; this checks it instead.
    #
    # Keyed on the EMITTER PREFIX, deliberately. Two classes of occurrence must not be flagged:
    # prose that quotes the bare token (`WEAKENED ·` followed by a backtick or a newline), and
    # -- the one that matters -- `change-inventory.py`'s docstring, which spells
    # `WEAKENED - FOO` ON PURPOSE as the counter-example teaching this very failure. A check
    # that flagged the lesson about the bug would be a check nobody keeps.
    EMIT = re.compile(r"\[audit-coverage\] WEAKENED(?! \u00b7)")
    prefixed = 0
    for f in EMITTERS:
        if not f.exists():
            continue
        body = f.read_text(encoding="utf-8")
        prefixed += body.count("[audit-coverage] WEAKENED")
        bad = [body[max(0, m.start() - 30):m.end() + 30] for m in EMIT.finditer(body)]
        check(f"{f.name}: every emitted WEAKENED carries the U+00B7 separator",
              not bad,
              f"{len(bad)} emission(s) use a near-miss separator: {bad}. Invisible to the "
              "derivation above AND to the shipped prose rule, so the weakening reaches nobody")
    # PAIRED POSITIVE: the loop above is a prohibition, and a prohibition over an empty set is
    # green. If the prefix ever changes, this fails instead of quietly checking nothing.
    check("...and there were emissions to check (the prohibition is not vacuous)",
          prefixed >= 5,
          f"only {prefixed} `[audit-coverage] WEAKENED` emission(s) found — the prefix changed, "
          "so the separator check above measured nothing")

    # CV1's three new instances specifically, named so a regression points at the right change.
    for tok in ("DOC-BLIND", "DOC-PATTERN-INVALID", "BUDGET-UNAVAILABLE"):
        check(f"CV1 instance {tok} is both emitted and enumerated",
              tok in emitted and tok in listed,
              f"emitted={tok in emitted} listed={tok in listed}")

    # ...and the superseded false claim is gone, paired with the positive that a true one replaced
    # it -- deleting the sentence entirely would satisfy a bare negative.
    check("the false 'pinned by an eval' claim is corrected, not merely deleted",
          "run_coverage_vocab_evals.py" in skill
          and "the list is now pinned by an eval rather than by this sentence.*" not in skill,
          "the bullet must name the harness that actually pins it")

    print()
    if _failures:
        print(f"FAILED: {len(_failures)} eval(s): {', '.join(_failures)}")
        return 1
    print("All control-line vocabulary evals passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
