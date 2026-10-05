#!/usr/bin/env python3
"""Markdown-safety policy for machine-extracted text pasted into a PR body.

ONE policy, two readers — `render-test-plan.py` (criterion text, judge notes,
not_tested items) and `artifact-handoff.py` (figcaptions, alt text, frame paths
read out of the committed visual-history record). Both paste text they do not
control into the body a human reviews at the merge gate, and both previously
would have carried their own copy.

They did not merely duplicate: the second copy was WEAKER. It substituted three
characters (`` ` ``, `[`, `]`) and passed `<` — the HTML-comment opener — straight
through, so the same PR body neutralized a crafted `<!--` in its `## Test plan`
section and did not in its `## Before / after` section. One body, two escaping
policies, and the difference invisible unless you read both files. That is the
fan-out class `.claude/rules/general.md` Consistency item 2 describes, and the
reason this module exists rather than a second set of helpers.

Lives in its own underscore-free, importable module because the scripts that need
it are hyphenated and cannot be imported — the same reason, and the same shape, as
`manifest_contract.py` beside it.
"""

from __future__ import annotations

import re

# Markdown metacharacters that let extracted text break out into a link, emphasis,
# inline code, or an HTML comment in the rendered PR body. Escaping the opener of
# each vector is sufficient: `\` (escape), backtick (code), `*`/`_` (emphasis),
# `[`/`]` (link text), `<` (HTML/comment opener). `>` is omitted deliberately — it
# is only a blockquote at line-start, and rendered text never starts a line (every
# line is prefixed `- ` / `  ↳ ` / `**`), so escaping it would only add noise to the
# common `>1 viewport`-style items.
MD_ACTIVE = frozenset("\\`*_[]<")

_COLLAPSE = re.compile(r"\s+")


def md_escape(text) -> str:
    """Neutralize Markdown-active characters, losslessly (backslash, not substitution).

    Crafted content from an app-under-test that a judge narrates verbatim — or a
    figcaption in a committed visual-history record — cannot then inject links,
    emphasis, or hidden HTML comments into the PR body. Evidence-style strings use
    `code_span` instead: a literal observation reads better as a code span, which
    also neutralizes.
    """
    return "".join("\\" + ch if ch in MD_ACTIVE else ch for ch in str(text))


def code_span(text) -> str:
    """Wrap extracted text in a backtick code span, widening the fence as needed.

    Neutralizes by containment rather than by escaping, so the reader sees the
    literal bytes. Use for paths and observed values.
    """
    s = str(text).strip()
    fence = "`"
    while fence in s:
        fence += "`"
    pad = " " if (s.startswith("`") or s.endswith("`")) else ""
    return "%s%s%s%s%s" % (fence, pad, s, pad, fence)


def one_line(text, limit: int = 200) -> str:
    """Single line, length-capped, NOT escaped. Pair with `code_span`.

    Split from `inline` because the two neutralizing strategies do not compose:
    `code_span` neutralizes by CONTAINMENT, and inside a code span a backslash is a
    literal character — so `code_span(inline(x))` shows the reader
    `` `frames/\[a\]_b` `` instead of the path. Escape for a text position; contain
    for a code position; never both.

    Lossy on length by design — an unbounded figcaption or path would push the frames
    off the reader's screen, which is the problem the section exists to solve.
    """
    t = _COLLAPSE.sub(" ", str(text or "")).strip()
    if len(t) > limit:
        t = t[:limit - 1].rstrip() + "…"
    return t


def inline(text, limit: int = 200) -> str:
    """One escaped, single-line, length-capped string fit for a TEXT position.

    `md_escape` alone is not enough where the destination is a single-line construct
    (`![alt](url)`, `[text](url)`, a table cell): a newline in the source ends the
    construct even though every character in it is escaped.

    `limit` bounds the SOURCE text, not the result: escaping runs after the cut, so a
    pathological all-metacharacter string can come back at up to `2 * limit`. That
    order is deliberate and is the safer of the two — capping AFTER escaping can slice
    a `\\x` pair in half and leave a dangling backslash, which would then escape the
    construct's own closing bracket. The 2x bound still serves the cap's purpose
    (keep a runaway caption from pushing the frames off the reader's screen), and
    `run_artifact_handoff_evals.py::test_md_safety_layering` pins the no-dangling-escape
    property directly.
    """
    return md_escape(one_line(text, limit))
