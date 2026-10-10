### FB-0136: a detector validated only against its own vocabulary cannot find anything outside it

**Date:** 2026-10-05 · **Source:** v1.62.0 (#183), four `/flow:staff-review` + two `/flow:security-review` + five `/flow:audit-coverage` rounds on one branch

**What happened.** Three separate defects in one release shared a single shape, and all three
passed every test that existed:

1. `_UNDENIAL_RE`'s accept/reject table had 33 rows and did not contain the word `deferred` — the
   word whose dictionary definition *is* the class the guard is named after. Every reject row in
   the table hit a marker the regex already contained, so the table had only ever been exercised
   against the vocabulary it was built from. `N/A — deferred` suppressed the visual gate.
2. `evals/security/test_plan_text_not_quoted.py` had two assertions. Its mutation selftest
   validated **one** of them, so the other — the one that generalizes to warnings nobody has
   written yet — was dead on half its inputs and the harness still printed `selftest: OK`.
3. The same file's allow-list exempted one warning by **substring**, so a plan could mint an
   exempt warning by writing the allowed text into its own payload.

**The rule.** `.claude/rules/general.md` § Consistency discipline item 4 already says "before
trusting an instrument's negative result, run it against a case you KNOW is positive." That is
necessary and it was satisfied in all three cases above. The sharpening:

**The known positive must come from OUTSIDE the instrument's own enumeration.** A detector built
from a list, validated on inputs drawn from that list, is tested for transcription accuracy — not
for coverage. Both hypotheses ("the list is complete" and "the list is missing a whole class")
predict identical output on in-list inputs, which is item 4's own argument applied one level up.

**How to apply.**
- When a detector is a list (regex alternation, token set, allow-list, pattern array), at least one
  test case must share **no token** with any entry in that list. If you cannot write one, you do
  not yet know what the list is for. The 22 rows added in v1.62.0 were chosen on exactly that
  criterion and are the only rows that could have caught the bug.
- When a test carries N assertions, the mutation that validates it must show **each** of them going
  red. "The suite went red" is not evidence that the assertion you care about is alive. Name them
  individually in the selftest's failure message.
- An allow-list over text an attacker influences must match by **equality against a shared
  constant**, never by substring, or the attacker writes the key into the payload.

**Why this needed its own number.** Item 4 is about remembering to run the instrument. This is about
where the validating input comes from — and it is the failure that survives after someone has
diligently followed item 4. In this release it cost four rounds of review on one guard, with each
round finding a real defect the previous round's tests had been green over. Links:
[[FB-0131-a-self-updater-that-asks-the-artifact-whether-to-update]] (an instrument that cannot
report the one state it exists to detect), [[FB-0138-a-gate-that-reads-a-declaration-s-presence-not-its-content]]
(the gate this all hangs off).

**Structural note, not a lesson:** all four leaks in that guard were the same polarity — a
**blacklist** on the dangerous side, so unenumerated input defaults to "suppress". No amount of
vocabulary auditing fixes that; the inversion is filed in `dev-docs/roadmap.md` § Next. When a
detector leaks repeatedly despite good tests, check whether the *default* is on the expensive side
before adding more entries.
