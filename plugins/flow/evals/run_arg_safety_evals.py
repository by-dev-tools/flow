#!/usr/bin/env python3
"""Eval harness for the skill-argument prose rule (FB-0116, FB-0117).

THE BUG IT PINS
---------------
`$ARGUMENTS` is substituted textually into the WHOLE skill body before anything
parses it, and is not shell-escaped. A `` !` `` span containing it therefore
executes attacker-chosen commands at render time, with no interactive permission
prompt. `$0`-`$9` are substituted by the same pass, so every shell positional and
every awk field reference in a skill body is a placeholder too.

Full mechanism, transcribed from the shipped host bundle: `../lib/arg_placeholders.py`.

WHY THIS HARNESS IS SHAPED THE WAY IT IS
----------------------------------------
`.claude/rules/general.md` S Consistency item 4 -- a measurement that can only
return "clean" is not a measurement. The immediate ancestor of this file certified
this exact live RCE as SAFE, because it modelled the argument as `env["ARGUMENTS"]`
(one quoted word the shell can never re-parse) instead of as substitution. Under the
env model every payload is inert and the test is green forever, against a bug that
was live the whole time.

So this harness does three things in order, and the order is the point:

  1. VALIDATE THE INSTRUMENT ON A KNOWN POSITIVE (`test_instrument_*`). Render the
     HISTORICAL vulnerable form -- the verbatim pre-fix `audit-plan:13` -- and assert
     the canary IS created. If that assertion fails the harness ABORTS instead of
     continuing, because every later "no canary" result would be unfalsifiable.
  2. Assert the fix textually, over the live shipped files (`test_lint_*`).
  3. Assert the fix behaviourally, by rendering the live `` !` `` spans with payloads
     and checking the canary stays absent (`test_live_*`).

The canary is a FILESYSTEM ARTIFACT, never a string search. A refusal message that
echoes the payload back contains every literal an output-matching assertion would
look for, so string matching cannot distinguish "refused" from "executed, then
printed a refusal" -- which is precisely how v1.41.0's heredoc fix read clean while
executing (FB-0108 rule 3, and the reason `assert on what would leak` is FB-0004).

PAIRED POSITIVES (item 3)
-------------------------
"No placeholder in an executable context" is satisfiable by deleting the argument
feature outright. Every negative here is therefore paired with a positive that the
skill STILL accepts and still acts on its argument (`test_positive_*`), so removing
the feature turns this harness RED rather than green.

Stdlib only. Run:
    python3 plugins/flow/evals/run_arg_safety_evals.py
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).parent
SKILLS = HERE.parent / "skills"
sys.path.insert(0, str(HERE.parent / "lib"))
import arg_placeholders as AP  # noqa: E402  (sibling-lib import, house pattern)
from eval_utils import git_repo  # noqa: E402  the shared hoist target

_failures: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> bool:
    if cond:
        print(f"  PASS  {name}")
    else:
        print(f"  FAIL  {name}" + (f"\n          {detail}" if detail else ""))
        _failures.append(name)
    return bool(cond)


# ------------------------------------------------------------------ the payloads
# Mechanism-specific, per FB-0108 rule 3: each one attacks a DIFFERENT feature of
# the substitution sink rather than being a generic round-trip.
def payloads(canary: Path) -> dict:
    return {
        "double-quote break":   f'p.md"; touch {canary}; :"',
        "command substitution": f"$(touch {canary})p.md",
        "backtick":             f"p.md`touch {canary}`",
        "semicolon chain":      f"p.md; touch {canary}",
        "newline second line":  f"p.md\ntouch {canary}\n",
        # The delimiter-collision payload that defeated v1.41.0's heredoc fix. Kept
        # even though no delimiter scheme survives here, so a future author who
        # reintroduces one is met by the payload that already refuted it.
        "heredoc delimiter":    f"p.md\nFLOW_ARG_CAPTURE_9f3a2c7e\ntouch {canary}\n",
        # Forged bang-command: would the argument create a NEW render-time block?
        # The host's own `xS` escaper should neutralise this; assert it, don't hope.
        "forged bang span":     f"p.md\n!`touch {canary}`\n",
    }


def run_block(block: str, cwd: Path) -> None:
    """Execute a rendered `!`-span the way the host would: sh -c, no ARGUMENTS in env."""
    env = dict(os.environ)
    env.pop("ARGUMENTS", None)
    env.pop("CLAUDE_PROJECT_DIR", None)
    env["CLAUDE_PLUGIN_ROOT"] = str(HERE.parent)
    try:
        subprocess.run(["sh", "-c", block], cwd=str(cwd), env=env,
                       capture_output=True, text=True, timeout=30)
    except subprocess.TimeoutExpired:
        pass


# Fixture via the shared hoist target, not a seventh local copy. eval_utils' own docstring
# names itself the home for this and states the rule: "new harnesses import from here, so the
# eventual hoist is a deletion instead of a rewrite."
FIXTURE = {
    "flow.config.json": '{"referenceGlob": "docs/*.md"}\n',
    "p.md": "# Plan\n\n- [ ] Spec-walk: a thing\n",
}


# =============================================================== 1. THE INSTRUMENT
# The verbatim pre-fix audit-plan:13, reconstructed. `$ARGUMENTS` is assembled at
# runtime so THIS FILE is not itself a substitution site if it is ever read as a
# skill body, and so a grep for the token does not hit the harness that removed it.
TOK = "$" + "ARGUMENTS"
HISTORICAL_VULNERABLE = (
    'if [ -n "' + TOK + '" ]; then python3 ${CLAUDE_PLUGIN_ROOT}/scripts/extract_session.py '
    '--mode plan --plan-file "' + TOK + '"; else '
    'python3 ${CLAUDE_PLUGIN_ROOT}/scripts/extract_session.py --mode plan; fi'
)


def test_instrument(tmp: Path) -> bool:
    """Known-positive validation. If this does not fire, nothing below means anything."""
    print("\n1. INSTRUMENT VALIDATION -- the unfixed form must still execute")
    repo = git_repo(tmp / "instr", FIXTURE)
    # ONE definition of the canary path. It was spelled twice -- once for the payload that
    # WRITES it, once for the assertion that WATCHES it -- and two literals for one value means
    # editing either leaves the harness watching a file nothing creates, i.e. permanently and
    # silently green, in the one section whose job is to prove the instrument fires.
    canary = tmp / "canary-instr"
    executed = []
    for label, payload in payloads(canary).items():
        canary.unlink(missing_ok=True)
        run_block(AP.render(HISTORICAL_VULNERABLE, payload), repo)
        if canary.exists():
            executed.append(label)
            canary.unlink(missing_ok=True)
    ok = check(
        "instrument reproduces RCE against the UNFIXED form",
        len(executed) >= 3,
        f"only {len(executed)} payload(s) executed ({executed}). The emulation of the "
        "host's substitution is wrong, or the payloads no longer attack it -- either "
        "way every 'no canary' result in this file is unfalsifiable. Fix this FIRST.",
    )
    print(f"        executed under the old form: {', '.join(executed)}")
    # The negative control: the SAME payloads against a block with no placeholder.
    # Distinguishes "my payloads are inert" from "the block is safe".
    # NEGATIVE CONTROL, in two halves. The claim is "with no placeholder in the block, the
    # payload cannot reach the shell" -- and the FIRST half states that more strongly than
    # running it: render is the IDENTITY function, so there is no route at all. Asserting the
    # identity beats executing the same unchanged command once per payload (which is what this
    # did, 7 times, for 0.4s of nothing).
    CLEAN_BLOCK = "python3 ${CLAUDE_PLUGIN_ROOT}/scripts/extract_session.py --mode plan"
    not_identity = [lbl for lbl, pl in payloads(canary).items()
                    if AP.render(CLEAN_BLOCK, pl) != CLEAN_BLOCK]
    check("negative control: with no placeholder, render is the identity for every payload",
          not not_identity,
          f"render altered the block for {not_identity} — a block containing no placeholder "
          "must be returned byte-identical, or the emulation is substituting somewhere it "
          "should not and every canary result here is measured through that error")
    # ...and the second half still EXECUTES it once, because an identity claim about the
    # renderer says nothing about whether the payload can reach the shell by another route.
    canary.unlink(missing_ok=True)
    run_block(AP.render(CLEAN_BLOCK, next(iter(payloads(canary).values()))), repo)
    check("negative control: the clean block does not create the canary when executed",
          not canary.exists(),
          "the harness is leaking execution from somewhere other than substitution")
    canary.unlink(missing_ok=True)
    return ok


# ====================================================================== 2. THE LINT
ARG_SKILLS = {
    # skill -> (prose phrase proving it still ACCEPTS an argument,
    #           phrase proving it still ACTS on it)
    "audit-plan":     ("## Argument", "plan-file"),
    "critique-plan":  ("## Argument", "plan-file"),
    "review-brief":   ("## Argument", "brief-file"),
    "audit-coverage": ("## Argument", "source"),
}


def test_lint() -> None:
    print("\n2. LINT -- no host placeholder in any executable context, every shipped skill")
    offenders = []
    for skill_md in sorted(SKILLS.glob("*/SKILL.md")):
        bad = AP.unsafe(skill_md.read_text(encoding="utf-8"))
        for f in bad:
            offenders.append(f"{skill_md.parent.name}:{f['line']} {f['placeholder']} ({f['context']})")
    check("no shipped SKILL.md interpolates a host placeholder into shell",
          not offenders,
          "executable-context placeholders found:\n          " + "\n          ".join(offenders)
          + "\n          Fix: move the placeholder into prose under '## Argument' and let the "
            "agent Read it (Tier 1), or have the model Write it to a fixed scratch path the "
            "block reads (Tier 2). For a genuine shell positional, spell it ${1}. "
            "See docs/workflow.md S 'Skill arguments: the prose rule'.")

    # The placeholder must still be PRESENT in prose -- the paired positive. Without
    # this, deleting the argument feature satisfies the lint above.
    for skill, (accepts, acts) in sorted(ARG_SKILLS.items()):
        t = (SKILLS / skill / "SKILL.md").read_text(encoding="utf-8")
        found = AP.classify(t)
        check(f"positive: {skill} still declares its argument in prose",
              any(f["context"] == "prose" and "ARGUMENTS" in f["placeholder"] for f in found),
              "no prose placeholder -- the argument feature may have been deleted to "
              "satisfy the negative above (general.md S Consistency item 3)")
        check(f"positive: {skill} still documents acting on it ({accepts!r}, {acts!r})",
              accepts in t and acts in t,
              f"expected both {accepts!r} and {acts!r} in the skill body")


# ============================================================ 3. THE LIVE ARTEFACTS
def test_live_blocks(tmp: Path) -> None:
    print("\n3. LIVE BLOCKS -- render every shipped `!`-span with payloads; canary must stay absent")
    canary = tmp / "canary-live"
    for skill in sorted(ARG_SKILLS):
        md = (SKILLS / skill / "SKILL.md").read_text(encoding="utf-8")
        # Both kinds of executable block, because the two tiers use different ones: the
        # fork-context skills run `!`-spans at render time, review-brief runs a ```sh fence
        # via the Bash tool. A skill with NEITHER would mean extraction broke, which is the
        # failure this positive guards against -- an empty span list makes every payload
        # below vacuously pass.
        spans = [m.group(1) for m in AP.BANG_SPAN.finditer(md)] \
            + [m.group(1) for m in AP.BANG_FENCE.finditer(md)] \
            + [m.group(1) for m in re.finditer(r"```(?:sh|bash)\n([\s\S]*?)```", md)]
        check(f"{skill}: has at least one executable block to test",
              bool(spans), "no `!`-span and no ```sh fence found; block extraction has "
                           "silently broken, so the payload checks below prove nothing")
        fired = []
        # Fixture hoisted: it depends on neither the payload nor the span, and rebuilding it
        # inside both loops ran `git init`+`add`+`commit` 63 times to produce 4 identical repos.
        repo = git_repo(tmp / f"live-{skill}", FIXTURE)
        for label, payload in payloads(canary).items():
            for span in spans:
                canary.unlink(missing_ok=True)
                run_block(AP.render(span, payload), repo)
                if canary.exists():
                    fired.append(f"{label}")
                    canary.unlink()
        check(f"{skill}: no payload executes at render time",
              not fired, f"EXECUTED via: {sorted(set(fired))}")


# ================================================= 4. ${N} REMEDIATION, BEHAVIOURAL
def test_brace_positionals() -> None:
    print("\n4. ${N} -- shell positionals survive being invoked WITH arguments")
    # The bug: `/flow:ship <any argument>` rewrote `$0` inside ship's own provenance
    # awk to the first argument token, corrupting the one artefact CLAUDE.md tells
    # every session to read before trusting a green pipeline. Asserted behaviourally
    # -- the function is extracted from the live skill and RUN, both bare and under a
    # 3-token argument, and the two results must agree.
    for skill in ("ship", "doctor"):   # both grep for sect(); no second value to carry
        md = (SKILLS / skill / "SKILL.md").read_text(encoding="utf-8")
        line = next((l for l in md.splitlines() if l.strip().startswith("sect()")), None)
        if not check(f"{skill}: sect() still present", line is not None,
                     "the function this test protects is gone -- deletion is not a fix"):
            continue
        with tempfile.TemporaryDirectory() as td:
            doc = Path(td) / "d.md"
            doc.write_text("## Flow run\nrow-one\n## Next\nother\n")
            script = line.strip() + f'\nsect "## Flow run" {doc}\n'
            bare = subprocess.run(["sh", "-c", script], capture_output=True, text=True)
            rendered = AP.render(script, "alpha beta gamma")
            witharg = subprocess.run(["sh", "-c", rendered], capture_output=True, text=True)
            check(f"{skill}: sect() output identical bare vs 3-token argument",
                  bare.stdout == witharg.stdout and "row-one" in bare.stdout,
                  f"bare={bare.stdout!r} with-arg={witharg.stdout!r} -- a $N or $0 in this "
                  "function is being rewritten by the host. Spell positionals ${N}.")


# ======================================================= 5. THE PROSE CHANNEL IS SAFE
def test_prose_channel_safe() -> None:
    print("\n5. PROSE CHANNEL -- the host's own escaper makes prose non-executable")
    # The idiom rests on this: an argument substituted into PROSE cannot forge a new
    # render-time block, because `xS` breaks bang-command syntax. Asserted against
    # the host's extractors, not assumed.
    body = "The argument is: $ARGUMENTS\n"
    hostile = "x\n!`touch /tmp/should-never-run`\n```!\ntouch /tmp/nor-this\n```\n"
    rendered = AP.render(body, hostile)
    check("a forged `!`-span in the argument is not extractable as a bang command",
          not AP.BANG_SPAN.search(rendered) and not AP.BANG_FENCE.search(rendered),
          f"rendered prose still yields an executable span: {rendered!r}")
    check("classify() reports the prose placeholder as prose, not bang",
          [f["context"] for f in AP.classify(body)] == ["prose"])
    # ...and the escape hatch behaves, so docs can spell the token without becoming a site.
    check(r"\$ARGUMENTS renders literal and is not reported as a placeholder",
          AP.render(r"\$ARGUMENTS", "payload") == "$ARGUMENTS"
          and AP.classify(r"\$ARGUMENTS") == [])


# ============================================ 6. THE DOC ANCHOR CITED FROM CODE RESOLVES
SECTION = "Skill arguments: the prose rule"


def test_idiom_documented() -> None:
    print("\n6. DOC ANCHOR -- every code citation of the idiom section resolves")
    wf = HERE.parent / "docs" / "workflow.md"
    body = wf.read_text(encoding="utf-8")
    check("workflow.md carries the canonical idiom section",
          f"## {SECTION}" in body,
          f"comments in four skills and this harness cite '{SECTION}' by name. A citation that "
          "resolves only to its own obituary is the FB-0010 fan-out class (general.md S "
          "Consistency item 2).")
    # The section has to actually carry the rule, not just the heading -- a heading alone would
    # satisfy the check above while documenting nothing.
    for required in ("## Argument", "Tier 1", "Tier 2", "${1}", "$(0)", "run_arg_safety_evals.py"):
        check(f"idiom section states {required!r}", required in body)
    # And every citer is real: assert the string is cited from the artifacts that claim to cite it.
    citers = ["skills/audit-plan/SKILL.md", "skills/critique-plan/SKILL.md",
              "skills/review-brief/SKILL.md", "skills/audit-coverage/SKILL.md"]
    missing = [c for c in citers
               if "workflow.md" not in (HERE.parent / c).read_text(encoding="utf-8")]
    check("each converted skill points a reader at the canonical section",
          not missing, f"no workflow.md pointer in: {missing}")


# ================================== 7. THE LINT AGREES WITH THE HOST (escape-rule table)
# A lint with a gap is WORSE than no lint, because it certifies. This table is the host's
# substitution contract, worked out from the shipped bundle's three replace arms plus its
# escape arm, and it is asserted in BOTH directions: a miss is a certified live hole, an
# over-match is noise that trains authors to ignore the lint.
#
# The `\\$ARGUMENTS` row is the one that caught a real gap in the first version of this
# matcher. The host's escape arm is `(?<!\\)\\\$`, so it consumes `\$` only when that
# backslash is not itself preceded by one -- meaning TWO backslashes leave the placeholder
# LIVE. A naive `(?<!\\)` lookbehind (which is what shipped first) silently passed every
# run of 2+ backslashes.
HOST_TABLE = [
    ("$ARGUMENTS",      True,  "bare"),
    ("$ARGUMENTS0",     True,  "replaceAll is substring-based, so the prefix still goes"),
    ("${ARGUMENTS}",    False, "no brace arm exists in the host"),
    ("$ARGUMENTS[0]",   True,  "indexed arm"),
    ("$ARGUMENTS[10]",  True,  "indexed arm, two digits"),
    ("$0",              True,  "positional -> FIRST argument token"),
    ("$9",              True,  "positional"),
    ("$10",             True,  r"\d+ is greedy, so the host reads index 10"),
    ("$1a",             False, r"(?!\w) blocks it"),
    ("$1_",             False, r"(?!\w) blocks it"),
    ("${1}",            False, "brace form -- the safe shell spelling"),
    ("$(0)",            False, "paren form -- the safe awk spelling"),
    (r"\$ARGUMENTS",    False, "exactly one backslash -> escaped"),
    (r"\\$ARGUMENTS",   True,  "TWO backslashes -> escape arm's lookbehind fails -> LIVE"),
    (r"\\\$ARGUMENTS",  True,  "three -> same reason -> LIVE"),
]


def test_host_agreement() -> None:
    print("\n7. HOST AGREEMENT -- the matcher's escape rule matches the host's, both directions")
    for text, host_substitutes, why in HOST_TABLE:
        lint_flags = bool(AP.HOST_PLACEHOLDER.search(text))
        if host_substitutes:
            check(f"lint FLAGS {text!r} (host substitutes it: {why})", lint_flags,
                  "LINT GAP — the host substitutes this and the lint does not flag it, so a "
                  "skill containing it would be certified clean over a live injection site")
        else:
            check(f"lint IGNORES {text!r} ({why})", not lint_flags,
                  "over-match — this is a safe spelling; flagging it trains authors to ignore "
                  "the lint, and pushes them off the spelling we want them to use")
    # The matcher and the render emulation are two independent definitions of one boundary.
    # FB-0109: when two definitions of the same boundary drift, one of them is silently wrong.
    # So assert they agree on every row rather than trusting they were written together.
    #
    # ASSERT ON WHAT WOULD LEAK, NOT ON A PROXY (FB-0004). The first version of this loop used
    # `rendered != text` -- "the text moved" -- and that proxy is wrong in two ways at once:
    # consuming the `\$` escape moves the text WITHOUT substituting anything, and `$9`/`$10`
    # do not move at all unless the argument actually has a token at that index. Both produced
    # false failures against correct code. The honest oracle is whether the PAYLOAD TOKEN
    # reaches the output, so the argument below carries a distinct marker per index.
    TOKENS = [f"TOK{i}zz" for i in range(12)]
    ARG = " ".join(TOKENS)
    for text, host_substitutes, why in HOST_TABLE:
        rendered = AP.render(text, ARG)
        leaked = any(tok in rendered for tok in TOKENS)
        check(f"render() agrees with the matcher on {text!r}",
              leaked == host_substitutes,
              f"render({text!r}) -> {rendered!r}: payload reached output = {leaked}, but the "
              f"table says the host substitutes = {host_substitutes} ({why}). The matcher and "
              "the emulation disagree, so one of them is wrong — and every canary result in "
              "this file is measured through the emulation.")
    # ...and the escape genuinely yields the LITERAL token, with no payload anywhere near it.
    esc = AP.render(r"\$ARGUMENTS", ARG)
    check(r"the \$ escape renders a literal $ARGUMENTS and leaks no payload",
          esc == "$ARGUMENTS",
          f"got {esc!r} — docs and comments rely on this spelling to NAME the placeholder "
          "without becoming a substitution site")


def main() -> int:
    print("Skill-argument prose-rule evals (FB-0116, FB-0117)")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        if not test_instrument(tmp):
            print("\nABORTED: the instrument could not reproduce the known-positive RCE. "
                  "Every later result would be unfalsifiable, so they were not run.")
            return 1
        test_lint()
        test_live_blocks(tmp)
        test_brace_positionals()
        test_prose_channel_safe()
        test_idiom_documented()
        test_host_agreement()
    print()
    if _failures:
        print(f"FAILED: {len(_failures)} eval(s): {', '.join(_failures)}")
        return 1
    print("All skill-argument safety evals passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
