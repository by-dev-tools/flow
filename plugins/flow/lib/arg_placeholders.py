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
    can look like a working one. Measured: 3 of 5 payloads escape.)
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
HOST_PLACEHOLDER = re.compile(
    r"(?<!\\)\$(?:ARGUMENTS\[\d+\]|ARGUMENTS|\d+(?![0-9A-Za-z_]))"
)

# The host's own bang-command extractors, transcribed:
#   Lno = /```!\s*\n?([\s\S]*?)\n?```/g
#   Nno = /(?<=^|\s)!`([^`]+)`/gm
# Note `[^`]+`: a `!`-span cannot contain a backtick, which is why several shipped
# blocks carry a "no backticks anywhere in this block" warning.
BANG_FENCE = re.compile(r"```!\s*\n?([\s\S]*?)\n?```")
# Python's `re` rejects the host's variable-width `(?<=^|\s)` lookbehind, so it is
# spelled as an equivalent alternation of `^` (under re.M) and a fixed-width lookbehind.
BANG_SPAN = re.compile(r"(?:^|(?<=\s))!`([^`]+)`", re.M)

_FENCE_LINE = re.compile(r"^(?:```|~~~)", re.M)


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
    body = re.sub(r"\$ARGUMENTS\[(\d+)\]",
                  lambda m: xS(tokens[int(m.group(1))])
                  if int(m.group(1)) < len(tokens) else m.group(0), body)
    body = re.sub(r"\$(\d+)(?![0-9A-Za-z_])", positional, body)
    body = body.replace("$ARGUMENTS", esc)
    return body.replace(SENTINEL, "$")
