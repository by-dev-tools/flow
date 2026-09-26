#!/usr/bin/env python3
"""Where Claude Code substitutes a slash-command argument, and where that is safe.

ONE definition, several readers (`evals/run_arg_safety_evals.py` today; `/flow:doctor`
if it ever grows an install-time lint). The FB-0010 fan-out class says a contract
spelled out in N files is held together by author memory, so the regexes below are
written once, here, and transcribed from the shipped Claude Code bundle rather than
inferred from observed behaviour.

WHY THIS FILE EXISTS (FB-0116)
------------------------------
`$ARGUMENTS` is not a shell variable. The host substitutes it **textually into the
whole skill body before anything parses it**, via (bundle, minified):

    e = e.replace(/\\$ARGUMENTS\\[(\\d+)\\]/g, ...)
    e = e.replace(/\\$(\\d+)(?!\\w)/g, ...)
    e = e.replaceAll("$ARGUMENTS", () => h(n))

`replaceAll` over `e` -- the ENTIRE body. There is no notion of "inside a shell
block" versus "in prose": prose, fenced blocks and `` !` `` spans are all just text
to it. The only escaper applied on the plugin-skill path is

    cde(Ln, ir, !0, De, xS)          // xS = the escaper argument

and `xS` neutralises **bang-command syntax only**:

    xS = e => e.replace(/`!/g,"` !").replace(/!`/g,"! `").replace(/(^|\\s)!/gm,"$1\\\\!")

It performs NO shell escaping. The bundle states this in its own words, in the
refusal it prints when asked to import a Gemini command:

    "Gemini shell-escapes `{{args}}` inside `!{...}`, Claude Code's `$ARGUMENTS`
     substitution doesn't, so importing would let typed arguments inject shell
     commands. Port it manually."

Substitution runs BEFORE the host extracts bang commands, so by the time a shell
sees the text the argument is already code. Therefore:

  * quoting cannot help  -- `"$ARGUMENTS"` still admits `$(...)`, a backtick, and a
    closing `"`. (It DOES contain `;` and a newline; that is why a partial mitigation
    can look like a working one. Measured against the real pre-fix block, a majority of
    the payload set escapes; the set and the per-payload result live in
    `evals/run_arg_safety_evals.py` rather than as a count here, because a number
    duplicated into prose is the one that goes stale.)
  * no delimiter can help -- a heredoc terminator is a published literal that can
    appear on line 2 of the payload (FB-0108 rule 2, and v1.41.0 shipped exactly
    that and was defeated).

The only fix is for the argument never to enter shell source. See
`docs/workflow.md` S "Skill arguments: the prose rule".

THREE PLACEHOLDER FAMILIES, not one
-----------------------------------
`$ARGUMENTS` is the famous one; it is not the only one. `$0`-`$9` are substituted by
the same pass, which means **every shell positional parameter and every awk field
reference in a skill body is a placeholder**. `$0` maps to the first whitespace-
separated token, so it fires on ANY argument at all -- `awk 'index($0,H)'` inside a
skill body is rewritten the moment the skill is invoked with one. `$ARGUMENTS[n]` is
the third family.

`${1}` and `${0}` are NOT matched (`$` is followed by `{`, so `(\\d+)` fails), which
makes brace form the drop-in safe spelling for a genuine shell positional.

A backslash escapes the placeholder: `\\$ARGUMENTS` renders as a literal
`$ARGUMENTS` and is never substituted (the host's `(?<!\\\\)\\\\\\$` arm). The
pattern below mirrors that lookbehind, so escaped occurrences are correctly NOT
reported -- a lint that flagged them would push authors toward pointless churn.
"""

from __future__ import annotations

import re

# Mirrors the host's three substitution arms. `ARGUMENTS\[\d+\]` MUST precede the
# bare `ARGUMENTS` alternative or the indexed form matches as a bare one.
#
# `[0-9A-Za-z_]` is spelled out rather than `\w` deliberately: JavaScript's `\w` is
# ASCII-only, Python's is Unicode-aware by default, so `\w` here would diverge from
# the host on non-ASCII input -- the FB-0109 class (two definitions of one boundary).
#
# NOTE the escape rule is NOT a simple `(?<!\\)` lookbehind, and getting that wrong is a
# lint gap that CERTIFIES a live hole. The host's escape arm is
#
#     e.replace(/(?<!\\)\\\$(?=\d|ARGUMENTS|...)/g, SENTINEL)
#
# i.e. it consumes a `\$` only when that backslash is itself NOT preceded by a backslash.
# So with TWO preceding backslashes the escape does not fire, the `$…` survives, and
# `replaceAll` substitutes it. Worked through:
#
#     $ARGUMENTS       0 backslashes  -> substituted
#     \$ARGUMENTS      1 backslash    -> escaped, NOT substituted
#     \\$ARGUMENTS     2 backslashes  -> SUBSTITUTED (the lookbehind kills the escape)
#     \\\$ARGUMENTS    3 backslashes  -> SUBSTITUTED (same reason)
#
# The rule is therefore: **live iff the run of backslashes immediately before `$` is not
# exactly one.** A naive `(?<!\\)` matches only the 0-backslash case and silently passes
# every run of 2+ — measured against this exact table, which is why it is now pinned by
# `evals/run_arg_safety_evals.py::test_host_agreement` rather than trusted.
_PLACEHOLDER_BODY = r"\$(?:ARGUMENTS\[\d+\]|ARGUMENTS|\d+(?![0-9A-Za-z_]))"
_RAW_PLACEHOLDER = re.compile(_PLACEHOLDER_BODY)


def _escaped(text: str, at: int) -> bool:
    """Is the `$` at `at` escaped, per the host's actual escape arm?

    True only when the immediately-preceding run of backslashes has length exactly 1.
    """
    n = 0
    i = at - 1
    while i >= 0 and text[i] == "\\":
        n += 1
        i -= 1
    return n == 1


class _HostPlaceholder:
    """`re`-compatible surface (`finditer`/`search`) carrying the host's escape rule.

    A plain compiled pattern cannot express "the preceding backslash run is not exactly
    one" in a fixed-width lookbehind, and Python rejects a variable-width one -- so the
    rule lives in `_escaped` and this wrapper keeps every call site unchanged.
    """

    def finditer(self, text: str):
        for m in _RAW_PLACEHOLDER.finditer(text):
            if not _escaped(text, m.start()):
                yield m

    def search(self, text: str):
        return next(self.finditer(text), None)


HOST_PLACEHOLDER = _HostPlaceholder()

# The host's own bang-command extractors, transcribed:
#   Lno = /```!\s*\n?([\s\S]*?)\n?```/g
#   Nno = /(?<=^|\s)!`([^`]+)`/gm
# Note `[^`]+`: a `!`-span cannot contain a backtick, which is why several shipped
# blocks carry a "no backticks anywhere in this block" warning.
BANG_FENCE = re.compile(r"```!\s*\n?([\s\S]*?)\n?```")
# Python's `re` rejects the host's variable-width `(?<=^|\s)` lookbehind, so it is
# spelled as an equivalent alternation of `^` (under re.M) and a fixed-width lookbehind.
BANG_SPAN = re.compile(r"(?:^|(?<=\s))!`([^`]+)`", re.M)

# Leading whitespace is ALLOWED, deliberately. An anchored `^(?:```|~~~)` sees only
# column-0 fences, and this repo's skills indent fences constantly inside list items --
# `ship/SKILL.md` carries 34 indented fences and `log-disagreement/SKILL.md` carries 4
# indented and ZERO at column 0. Missing those inverts the open/close parity, so a real
# code fence can land OUTSIDE every computed region and be classified `prose`, i.e.
# certified safe. That is the "a lint with a gap certifies" class this whole file exists
# to avoid.
#
# The over-matching direction is the SAFE one here and that asymmetry is the design: a
# region wrongly treated as fenced makes the lint flag MORE (noise, caught in review),
# while a region wrongly treated as prose makes it flag LESS (a silent live sink). When
# only one direction can be wrong cheaply, pick that one.
_FENCE_LINE = re.compile(r"^[ \t]*(?:```|~~~)", re.M)


def _spans(pattern, text):
    return [(m.start(), m.end()) for m in pattern.finditer(text)]


def fenced_regions(text: str) -> list[tuple[int, int]]:
    """Char ranges of ``` / ~~~ fenced blocks, opener and closer inclusive."""
    out, open_at = [], None
    for m in _FENCE_LINE.finditer(text):
        if open_at is None:
            open_at = m.start()
        else:
            out.append((open_at, m.end()))
            open_at = None
    if open_at is not None:          # unterminated fence: treat to end of file
        out.append((open_at, len(text)))
    return out


def classify(text: str) -> list[dict]:
    """Every host placeholder in `text`, tagged with the context it lands in.

    context is one of:
      "bang"   -- inside a `` !` `` span or a ```!-fence. EXECUTES AT RENDER TIME,
                  with no interactive permission prompt. This is the RCE case.
      "fenced" -- inside an ordinary fenced block. Not executed at render time, but
                  the substituted text IS delivered (see module docstring: the
                  replace is over the whole body), and skills instruct the model to
                  run these via the Bash tool. Permission-checked, still injection.
      "prose"  -- body text. SAFE: never parsed by any interpreter, and the host's
                  `xS` escaper strips bang-command syntax out of the value, so a
                  payload cannot forge a new `` !` `` span here either.
    """
    bang = _spans(BANG_SPAN, text) + _spans(BANG_FENCE, text)
    fenced = fenced_regions(text)
    found = []
    for m in HOST_PLACEHOLDER.finditer(text):
        i = m.start()
        if any(a <= i < b for a, b in bang):
            ctx = "bang"
        elif any(a <= i < b for a, b in fenced):
            ctx = "fenced"
        else:
            ctx = "prose"
        found.append({
            "placeholder": m.group(0),
            "offset": i,
            "line": text.count("\n", 0, i) + 1,
            "context": ctx,
        })
    return found


def unsafe(text: str) -> list[dict]:
    """Placeholders in an executable context. Empty list == compliant."""
    return [f for f in classify(text) if f["context"] in ("bang", "fenced")]


# ---------------------------------------------------------------- host emulation
# Used by the eval to reproduce render faithfully. Kept here, beside the regexes it
# has to agree with, rather than in the eval -- so a future correction to the host
# model lands in one place.

def xS(value: str) -> str:
    """The host's escaper: neutralises bang-command syntax. NOT a shell escape."""
    value = value.replace("`!", "` !").replace("!`", "! `")
    return re.sub(r"(^|\s)!", r"\1\\!", value, flags=re.M)


def render(body: str, argument: str | None) -> str:
    """`cde()`: flat replaceAll over the whole body, bang-escaped, NOT shell-escaped.

    Covers the three placeholder families and the `\\$` escape. Deliberately does
    NOT implement the named-argument arm (`argNames`) -- no flow skill declares any,
    and emulating an unused arm would be untested code pretending to be a model.
    """
    if argument is None:
        return body
    tokens = argument.split()
    esc = xS(argument)

    def positional(m):
        i = int(m.group(1))
        return xS(tokens[i]) if i < len(tokens) else m.group(0)

    # `\$ARGUMENTS` -> literal, never substituted (host: the (?<!\\)\\\$ arm).
    SENTINEL = "￿"
    body = re.sub(r"(?<!\\)\\\$(?=ARGUMENTS|\d)", SENTINEL, body)
    # Same resolver as the positional arm -- group 1 is the digits in both patterns, and the
    # index/bounds rule is one rule. It was written twice, six lines apart, inside the function
    # whose stated job is being the single faithful model of the host.
    body = re.sub(r"\$ARGUMENTS\[(\d+)\]", positional, body)
    body = re.sub(r"\$(\d+)(?![0-9A-Za-z_])", positional, body)
    body = body.replace("$ARGUMENTS", esc)
    return body.replace(SENTINEL, "$")


# ------------------------------------------------------------------------ CLI
# A directory-scanning entrypoint so this predicate can be a `/flow:doctor` check and
# not only a CI eval. That distinction is the whole point: flow's CI glob covers flow's
# own skills, but flow's PRODUCT is a workflow for other people's repos -- a consumer who
# writes an argument-taking skill and interpolates the placeholder into a shell block gets
# render-time RCE, and flow's CI will never see their file. Doctor already scans a
# project's own `.claude/skills/` for exactly this reason (Check 1.4).
#
# Exit codes are the contract doctor keys on; keep them stable and distinguish them, so
# "the lint could not run" is never reported as "no violations" (failure-open) and never
# as a violation (a false accusation):
#     0  no placeholder in any executable context
#     1  at least one violation (the real finding)
#     2  could not scan (no such directory, unreadable)
def _main(argv: list) -> int:
    import sys as _sys
    from pathlib import Path as _Path

    if len(argv) != 1:
        _sys.stderr.write("usage: arg_placeholders.py <skills-dir>\n")
        return 2
    root = _Path(argv[0])
    if not root.is_dir():
        _sys.stderr.write(f"[arg-placeholders] not a directory: {root}\n")
        return 2
    skills = sorted(root.glob("*/SKILL.md"))
    if not skills:
        # Not a violation, and NOT silence: an empty scan that printed nothing would read
        # identically to a clean one (the FB-0062 failure-open shape).
        print(f"[arg-placeholders] no SKILL.md files under {root} — nothing to lint")
        return 0
    violations = 0
    for skill in skills:
        try:
            text = skill.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            _sys.stderr.write(f"[arg-placeholders] could not read {skill}: {e}\n")
            return 2
        for f in unsafe(text):
            violations += 1
            print(
                f"[arg-placeholders] FAIL {skill}:{f['line']} — {f['placeholder']} sits inside "
                f"a {'render-time !`…` block' if f['context'] == 'bang' else 'shell fence'}. "
                "The host substitutes it there BEFORE any shell parses it and does not "
                "shell-escape it, so a caller-supplied argument becomes code"
                + (" that runs with no permission prompt." if f["context"] == "bang" else ".")
            )
    if violations:
        print(
            f"[arg-placeholders] {violations} violation(s). Fix: move the placeholder into prose "
            "under a '## Argument' heading and let the agent Read it, or have the model Write it "
            "to a fixed scratch path the block reads. For a genuine shell positional write "
            "${1}; for an awk field write $(0). See flow's docs/workflow.md "
            "§ \"Skill arguments: the prose rule\"."
        )
        return 1
    print(f"[arg-placeholders] {len(skills)} skill(s) scanned, no placeholder in shell")
    return 0


if __name__ == "__main__":
    import sys

    raise SystemExit(_main(sys.argv[1:]))
