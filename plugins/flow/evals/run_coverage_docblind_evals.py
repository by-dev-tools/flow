#!/usr/bin/env python3
"""CV1 — behaviour-bearing prose reaches /flow:audit-coverage, and the blindness is stated.

THE BUG IT PINS. Flow ships PROMPTS: a SKILL.md is deployed surface by CLAUDE.md's own rule that
prompt changes are code changes. But `.md` never matched `sourceFilePatterns`, so the behaviour
diff never contained one. Measured: on #159 all five undeclared behaviours were added in
`audit-coverage/SKILL.md`, which the diff excluded -- the recorded `0-of-5` was never a judgment
failure, and no prompt change could ever have moved it.

THREE PARTS, and only one changes what the gate reads:

  A  SAY IT   -- a `WEAKENED · DOC-BLIND` line naming the doc-shaped files that were dropped.
                 Fires whether or not the slot is set; changes no verdict. This is the half that
                 serves a consumer who never opts in: a stated blind spot instead of a clean pass.
  B  SEE IT   -- `behaviorBearingDocPatterns`, DEFAULT EMPTY, adds matching paths to the diff.
                 Empty by default because sourceFilePatterns/EXCL are a contract every consumer
                 inherits; widening what a gate reads must be opted into, never applied silently.
  C  FIT IT   -- fair-share allocation of the evidence cap (see lib/evidence-budget.py), because
                 `head -c` on a concatenation made files late in the alphabet entirely invisible.

EVERY NEGATIVE IS PAIRED (general.md item 3). "DOC-BLIND does not fire" is satisfiable by never
emitting it at all, so it is paired with a case where it must fire. "The file list is unchanged
with the slot unset" is satisfiable by B not working, so it is paired with the slot-set case.

WHAT THIS HARNESS DOES NOT MEASURE, stated so its green is not over-read: whether the reviewer
*finds* the gaps once it can see them is LLM judgment, measured separately by
`tools/coverage-recall/` against the #159 case. This harness proves the file REACHES the
reviewer; that tool proves the recall number moves. Conflating them is how a file-filter result
got recorded as a judgment result for two releases.

Stdlib only. Run:
    python3 plugins/flow/evals/run_coverage_docblind_evals.py
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).parent
PLUGIN = HERE.parent
SKILLS = PLUGIN / "skills"
sys.path.insert(0, str(HERE))
from eval_utils import bang_blocks, commit, git_repo  # noqa: E402  the shared hoist target

_failures: list = []
BUILTIN = r"(^|/)(skills|agents|rules)/.*\.md$"


def check(name, cond, detail=""):
    if cond:
        print(f"  PASS  {name}")
    else:
        print(f"  FAIL  {name}" + (f"\n          {detail}" if detail else ""))
        _failures.append(name)
    return bool(cond)


# The shipped evidence block, EXTRACTED rather than restated -- a harness that re-types the
# shell tests its own copy and lets the artifact drift underneath it.
def evidence_block() -> str:
    t = (SKILLS / "audit-coverage" / "SKILL.md").read_text(encoding="utf-8")
    # Shared extractor, NOT a fifth local spelling: this file originally carried a looser regex
    # that disagreed with the other four about what a span is (see eval_utils.bang_blocks).
    # Selection stays by CONTENT rather than by index -- an inline span added above this one
    # would silently shift a positional `blocks[1]`.
    cand = [b for b in bang_blocks(t) if "Behavior-bearing files changed" in b]
    assert cand, "could not extract the evidence block"
    return cand[0]


BLOCK = evidence_block()
check("the shipped evidence block was extracted, not restated",
      "DOC-BLIND" in BLOCK and "evidence-budget.py" in BLOCK,
      "extraction returned a block without A or C; every case below would prove nothing")


def scenario(tmp, label, added, cfg_extra=None, base_files=None):
    files = {"plan.md": "# Plan\n\n**Spec-walk:**\n\n- [ ] a thing\n"}
    files.update(base_files or {})
    cfg = {"defaultBranch": "main", "planPath": "plan.md"}
    cfg.update(cfg_extra or {})
    files["flow.config.json"] = json.dumps(cfg)
    repo = git_repo(tmp / label, files)
    for c in (["git", "remote", "add", "origin", str(repo)],
              ["git", "update-ref", "refs/remotes/origin/main", "main"],
              ["git", "checkout", "-q", "-b", "work"]):
        subprocess.run(c, cwd=str(repo), capture_output=True)
    commit(repo, added, label)
    env = dict(os.environ)
    env["CLAUDE_PLUGIN_ROOT"] = str(PLUGIN)
    p = subprocess.run(["sh", "-c", BLOCK], cwd=str(repo), env=env,
                       capture_output=True, text=True, timeout=90)
    return p.stdout + p.stderr


def files_line(out: str) -> str:
    for ln in out.splitlines():
        if ln.startswith("Behavior-bearing files changed:"):
            return ln.split(":", 1)[1].strip()
    return ""


def main() -> int:
    print("CV1 docs-blindness evals (audit-coverage A/B/C)")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        SKILL = {"plugins/flow/skills/x/SKILL.md": "# x\n\nnew behaviour\n"}
        SRC = {"app.py": "print(1)\n"}

        print("\n1. A — SAY IT: the blindness is stated, and only when there is one")
        out = scenario(tmp, "a-fires", {**SKILL, **SRC})
        check("A fires on a dropped doc-shaped file and NAMES it",
              "WEAKENED · DOC-BLIND" in out and "skills/x/SKILL.md" in out, out[:240])
        check("A says WHICH predicate matched (suggestion vs the project's own slot)",
              "a built-in suggestion, not your project's declaration" in out, out[:240])
        check("A changes no verdict — the file list is unchanged by A",
              files_line(out) == "app.py", f"files={files_line(out)!r}")
        # PAIRED NEGATIVE: a diff with no doc-shaped file must not carry the line, or it becomes
        # noise on every PR and the token stops distinguishing anything.
        out_src = scenario(tmp, "a-silent", SRC)
        check("A does NOT fire when no doc-shaped file was dropped",
              "DOC-BLIND" not in out_src, out_src[:200])
        # ...and the pair's own positive: this scenario still produced a real file list, so the
        # silence is pre-emption rather than a block that did nothing.
        check("...and that scenario still audited something (silence is not emptiness)",
              files_line(out_src) == "app.py", f"files={files_line(out_src)!r}")

        print("\n2. B — SEE IT: opt-in, and it actually opts in")
        # NEGATIVE: unset slot must leave the file list exactly as it is today.
        check("slot UNSET: the doc file is NOT read (no consumer's gate changes)",
              "SKILL.md" not in files_line(out), f"files={files_line(out)!r}")
        out_set = scenario(tmp, "b-set", {**SKILL, **SRC},
                           cfg_extra={"behaviorBearingDocPatterns": BUILTIN})
        # PAIRED POSITIVE: with the slot set the same file IS read.
        check("slot SET: the doc file IS read",
              "plugins/flow/skills/x/SKILL.md" in files_line(out_set),
              f"files={files_line(out_set)!r}")
        check("slot SET: A goes silent — nothing was dropped to warn about",
              "DOC-BLIND" not in out_set, out_set[:240])
        # A test/fixture SKILL.md is not deployed surface and must stay out even when set.
        out_fix = scenario(tmp, "b-fixture", {"evals/fixtures/skills/y/SKILL.md": "# y\n", **SRC},
                           cfg_extra={"behaviorBearingDocPatterns": BUILTIN})
        check("slot SET: a fixture SKILL.md is still excluded",
              "fixtures" not in files_line(out_fix), f"files={files_line(out_fix)!r}")
        # TWO measured classes of bad slot, because one guard does not catch both. `[` is a
        # malformed ERE and grep exits 2; `(?i)\.md$` is a PCRE-ism that grep TOLERATES --
        # it warns and exits 1, i.e. "no match" -- so the exit-code guard misses it and the
        # project silently reads FEWER files. Validity is caught by exit code, vacuity by outcome.
        out_malformed = scenario(tmp, "b-malformed", {**SKILL, **SRC},
                                 cfg_extra={"behaviorBearingDocPatterns": "["})
        check("a MALFORMED slot emits DOC-PATTERN-INVALID and falls back",
              "DOC-PATTERN-INVALID" in out_malformed, out_malformed[:280])
        # A VALID-but-vacuous slot is caught by OUTCOME, not by a second bespoke check: every
        # doc-shaped file it failed to select is simply DROPPED, so DOC-BLIND names them. An
        # earlier version emitted a separate "matched NONE of the N" line under the
        # DOC-PATTERN-INVALID token -- two meanings for one token, and it covered only the
        # all-or-nothing corner. `(?i)\.md$` is a PCRE-ism grep TOLERATES (warns, exits 1 = "no
        # match"), so the exit-code guard above cannot see it; this is the arm that does.
        out_vacuous = scenario(tmp, "b-vacuous", {**SKILL, **SRC},
                               cfg_extra={"behaviorBearingDocPatterns": "(?i)\\.md$"})
        check("a VALID-but-vacuous slot is caught by outcome: DOC-BLIND NAMES the unread file",
              "DOC-BLIND" in out_vacuous
              and "plugins/flow/skills/x/SKILL.md" in out_vacuous,
              "a slot that compiles and matches nothing reads fewer files while looking "
              f"healthy — the unsafe direction: {out_vacuous[:320]!r}")
        check("...and it is NOT reported as a malformed pattern (the token means one thing)",
              "DOC-PATTERN-INVALID" not in out_vacuous, out_vacuous[:280])

        # THE PARTIAL-COVERAGE CASE — the regression this section exists for, found by
        # /simplify's altitude lens and reproduced before it was fixed. A hand-written slot that
        # covers skills/ but forgets agents/ is the REALISTIC consumer mistake, and the earlier
        # implementation was structurally silent about it: DOC-BLIND was keyed on the EFFECTIVE
        # pattern, so every file the slot matched was in $FILES by construction and $DROPPED
        # could only ever be empty. No warning of any kind on a changed, unread agents/*.md.
        # Invisible to dogfooding too: flow's own slot value is byte-identical to DOC_BUILTIN,
        # so both code paths agree in this repo forever.
        out_partial = scenario(tmp, "b-partial",
                               {"plugins/flow/skills/x/SKILL.md": "# x\n",
                                "plugins/flow/agents/auditor.md": "# auditor\n", **SRC},
                               cfg_extra={"behaviorBearingDocPatterns":
                                          "(^|/)skills/.*\\.md$"})
        check("a PARTIAL slot: the file it covers IS read",
              "plugins/flow/skills/x/SKILL.md" in files_line(out_partial),
              f"files={files_line(out_partial)!r}")
        check("...and the one it MISSES is named by DOC-BLIND, not silently dropped",
              "DOC-BLIND" in out_partial
              and "plugins/flow/agents/auditor.md" in out_partial,
              "this is the silence the line exists to prevent: doc-shaped, changed, unread, "
              f"unmentioned — {out_partial[:400]!r}")
        check("...and the warning tells the consumer it is THEIR slot that missed it",
              "behaviorBearingDocPatterns did not select them" in out_partial,
              "with the slot set, blaming a 'built-in suggestion' misdirects the fix: the "
              f"actionable fact is that their own pattern is too narrow — {out_partial[:400]!r}")
        # PAIRED NEGATIVE: a slot that covers everything doc-shaped stays silent, or the three
        # checks above are satisfied by a line that always fires.
        check("a CORRECT slot is silent (the pair's negative)",
              "DOC-BLIND" not in out_set and "DOC-PATTERN-INVALID" not in out_set,
              out_set[:240])

        # FAN-OUT GUARD (general.md item 2). The doc branch reuses $TESTDIRS and EXCL is now
        # COMPOSED from it, so the alternation exists once in this block instead of three times.
        # Assert the composition rather than trusting it: if someone re-inlines either copy, the
        # source filter and the doc filter can disagree about what a test path is, and the
        # failure direction is quiet (a fixture SKILL.md enters the behaviour diff).
        check("the test-dir alternation is spelled ONCE and both consumers compose from it",
              BLOCK.count("(^|/)(test|tests|__tests__|__fixtures__|fixtures|evals|spec|specs)/") == 1
              and 'EXCL="$TESTDIRS"' in BLOCK          # the behaviour diff's exclusion
              and '\'"$TESTDIRS"\'' in BLOCK           # source mode's walk exclusion (SEXCL)
              and 'grep -vE "$TESTDIRS"' in BLOCK,     # the doc branch's
              "three expressions needed this alternation and each carried its own copy; the next "
              "test dir added to one and not the others makes the source filter and the doc filter "
              "disagree about what a test path is, quietly (a fixture SKILL.md enters the diff)")

        print("\n3. C — FIT IT: no file is entirely invisible when the cap binds")
        # Genuinely OVER the 60,000-byte cap: the first fixture was ~32 KB, so nothing truncated
        # and the "names the cut files" check passed vacuously for want of a cut.
        # Each file opens with a UNIQUE marker, so "contributed evidence" is checked on the
        # file's CONTENT rather than on its name. The earlier form tested `f in out_big`, and
        # the file list names every SELECTED file regardless of how many bytes the allocator
        # gave it -- so a file allocated ZERO bytes still satisfied it. Measured: swapping the
        # allocator for greedy first-fit, the exact regression this section exists to catch,
        # left this check green. A marker on line 1 is inside any non-zero allocation.
        big = {f"src/f{i}.py": (f"MARK{i}_FIRSTLINE = 1\n" + ("x = %d\n" % i) * 4000)
               for i in range(6)}
        out_big = scenario(tmp, "c-cap", big)
        contributed = [i for i in range(len(big)) if f"MARK{i}_FIRSTLINE" in out_big]
        check("every file over the cap still contributes evidence (content, not filename)",
              len(contributed) == len(big),
              f"only {len(contributed)} of {len(big)} contributed any content: "
              f"{contributed} — a file named in the index with zero bytes read is invisible "
              "to the reviewer while looking accounted-for")
        check("the truncation line NAMES the cut files, not just the fact",
              ("WEAKENED · TRUNCATED" in out_big and " of " in out_big
               and any(f"{f} (" in out_big for f in big)),
              "a generic cap warning leaves the reviewer unable to tell a fully-read file "
              f"from an unread one: {out_big[-400:]!r}")
        # PAIRED NEGATIVE: under the cap nothing is truncated and no weakening token appears --
        # otherwise C would be reporting partial evidence on every healthy run.
        out_small = scenario(tmp, "c-under", SRC)
        check("under the cap: no TRUNCATED token at all",
              "TRUNCATED" not in out_small, out_small[:200])

    print()
    if _failures:
        print(f"FAILED: {len(_failures)} eval(s): {', '.join(_failures)}")
        return 1
    print("All CV1 docs-blindness evals passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
