#!/usr/bin/env python3
"""Insert one curated entry into the durable visual record (visual-history.html).

Part of /flow:ship's distill step (§ 5c). The AGENT decides *which* visual decision
is load-bearing and supplies its content (the curation — FB-0042(d)); this helper
renders that content into the fixed entry structure and inserts it, so the durable
record's disciplines (reverse-chronological, no italic headings, consistent markup,
anchor-link TOC) are MECHANICAL, not dependent on author memory (the FB-0010
"consistency depends on author memory" class). Mirrors the render-test-plan.py /
render-report.py lib family: structured input -> deterministic HTML.

Usage:
    insert-visual-history.py --target <path/to/visual-history.html> \
        --entry <path/to/entry.json | -> read JSON from stdin> \
        [--skeleton <path/to/visual-history-skeleton.html>]

Behavior:
    1. Seed: if --target does not exist, create it from --skeleton (default: the
       bundled skeleton next to this script). Non-UI projects never reach this step
       (the ship distill gate self-skips on uiSurface:false), so seeding only ever
       happens for a real UI consumer's first qualifying ship.
    2. Render the entry JSON into an <article class="vh-entry"> block.
    3. Prepend it as the FIRST child of the entries region (reverse-chronological).
    4. Regenerate the TOC from every entry's <h2 id=...> anchor.
    5. Write the file back. Print the resolved target path + anchor on success.

stdlib-only (no external deps). Graceful: a missing skeleton, a malformed target
(markers absent), or a malformed entry JSON each print a loud error to stderr and
exit non-zero WITHOUT writing a partial file — never a silent no-op, never a crash
that loses the existing record (the target is rewritten atomically only after a
fully successful render).

Entry JSON shape (all keys are strings unless noted):
    {
      "title": "Empty-state for the activity feed",   # required; becomes <h2> + anchor
      "date":  "2026-06-16",                           # required (YYYY-MM-DD)
      "pr":    "#51",                                  # optional
      "branch":"claude/v3b-visual-history",            # optional
      "grounding": {                                   # optional but recommended
        "type": "need|design-language|craft-commitment|open-question",
        "statement": "Why the surface looks/behaves this way.",
        "decision_test": "How we'd know it's right.",  # optional
        "citations": ["spec §3.1", "design-language: motion"]   # optional list
      },
      "before_after": [                                # optional list; each item is
        {"label": "Before", "src": "visual-history-assets/x-before.png", "alt": "..."},
        {"label": "After",  "html": "<svg ...>...</svg>", "recon": true}  # CSS/SVG fallback
      ],
      "questions_carried": ["Should the empty state offer a sample-data CTA?"]  # optional list
    }

For before_after items: provide EITHER "src" (a committed lean asset ref, preferred)
OR "html" (an inline CSS/SVG reconstruction — the honest fallback when capture isn't
available). An item with "recon": true is labelled as a reconstruction.
"""

import argparse
import html
import json
import os
import re
import sys

TOC_START = "<!-- vh:toc-start -->"
TOC_END = "<!-- vh:toc-end -->"
ENTRIES_START = "<!-- vh:entries-start -->"
ENTRIES_END = "<!-- vh:entries-end -->"

GROUNDING_LABEL = {
    "need": "User need",
    "design-language": "Design language",
    "craft-commitment": "Craft commitment",
    "open-question": "Open question",
}


def die(msg):
    """Loud failure to stderr, non-zero exit, no partial write."""
    sys.stderr.write("⚠️  insert-visual-history: " + msg + "\n")
    sys.exit(1)


def esc(s):
    return html.escape(str(s), quote=True)


def strip_emphasis(s):
    """Defend FB-0042(d) 'no italic headings' mechanically.

    Remove markdown emphasis wrappers (*x*, _x_) and any <em>/<i> tags from a
    heading string, keeping the inner text. Returns (clean_text, had_emphasis).
    """
    original = s
    # Strip <em>/<i> tags (keep inner text).
    s = re.sub(r"</?(?:em|i)\b[^>]*>", "", s, flags=re.IGNORECASE)
    # Strip *bold/italic* and _italic_ markdown wrappers (non-greedy, paired).
    s = re.sub(r"(?<!\w)[*_]{1,3}(.+?)[*_]{1,3}(?!\w)", r"\1", s)
    return s.strip(), (s.strip() != original.strip())


def slugify(title, existing):
    """Stable, collision-free anchor from a title."""
    base = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-") or "decision"
    base = base[:60].strip("-")
    slug, n = base, 2
    while slug in existing:
        slug = "%s-%d" % (base, n)
        n += 1
    return slug


def render_grounding(g):
    if not isinstance(g, dict) or not g.get("statement"):
        return ""
    gtype = g.get("type", "")
    label = GROUNDING_LABEL.get(gtype, gtype or "Grounding")
    parts = ['<div class="grounding">']
    parts.append('<span class="gtype">%s</span>' % esc(label))
    parts.append("<p>%s</p>" % esc(g["statement"]))
    if g.get("decision_test"):
        parts.append('<p class="test"><strong>Decision test:</strong> %s</p>' % esc(g["decision_test"]))
    cites = g.get("citations") or []
    if isinstance(cites, list) and cites:
        parts.append('<p class="cites">Grounded in: %s</p>' % esc(" · ".join(str(c) for c in cites)))
    parts.append("</div>")
    return "".join(parts)


def render_before_after(items):
    if not isinstance(items, list) or not items:
        return ""
    figs = []
    for it in items:
        if not isinstance(it, dict):
            continue
        cap = esc(it.get("label", ""))
        if it.get("src"):
            if not it.get("alt"):
                sys.stderr.write(
                    "ℹ️  insert-visual-history: before/after frame %r has no alt text — "
                    "add 'alt' so the committed, human-read record is screen-reader-legible.\n"
                    % it["src"]
                )
            body = '<img src="%s" alt="%s">' % (esc(it["src"]), esc(it.get("alt", "")))
        elif it.get("html"):
            # Inline CSS/SVG reconstruction — the honest fallback. NOT escaped: the
            # agent authored it as markup. Labelled as a reconstruction so the reader
            # knows it isn't a real capture.
            note = '<div class="recon-note">Reconstruction (capture unavailable)</div>' if it.get("recon") else ""
            body = '<div class="recon">%s%s</div>' % (it["html"], note)
        else:
            continue
        figs.append("<figure><figcaption>%s</figcaption>%s</figure>" % (cap, body))
    if not figs:
        return ""
    return '<div class="ba">%s</div>' % "".join(figs)


def render_carried(qs):
    if not isinstance(qs, list) or not qs:
        return ""
    lis = "".join("<li>%s</li>" % esc(q) for q in qs)
    return ('<div class="carried"><span class="clabel">Questions carried forward</span>'
            '<ul>%s</ul></div>') % lis


def render_entry(entry, existing_slugs):
    if not isinstance(entry, dict):
        die("entry JSON must be an object")
    title_raw = entry.get("title")
    if not title_raw or not str(title_raw).strip():
        die("entry.title is required")
    date = entry.get("date")
    if not date or not re.match(r"^\d{4}-\d{2}-\d{2}$", str(date)):
        die("entry.date is required and must be YYYY-MM-DD (got: %r)" % date)

    title, had_emph = strip_emphasis(str(title_raw))
    if had_emph:
        sys.stderr.write(
            "ℹ️  insert-visual-history: stripped emphasis from heading "
            "(FB-0042 no-italic-headings) -> %r\n" % title
        )
    slug = slugify(title, existing_slugs)

    meta_bits = []
    if entry.get("pr"):
        meta_bits.append(esc(entry["pr"]))
    meta_bits.append(esc(date))
    if entry.get("branch"):
        meta_bits.append("<code>%s</code>" % esc(entry["branch"]))
    meta = ('<span class="sep">·</span>').join(meta_bits)

    blocks = [
        '<article class="vh-entry" id="%s">' % slug,
        "<h2 id=\"%s\">%s</h2>" % (slug, esc(title)),
        '<div class="meta">%s</div>' % meta,
        render_grounding(entry.get("grounding")),
        render_before_after(entry.get("before_after")),
        render_carried(entry.get("questions_carried")),
        "</article>",
    ]
    return slug, title, "\n".join(b for b in blocks if b)


def between(text, start, end, what):
    i = text.find(start)
    j = text.find(end)
    if i == -1 or j == -1 or j < i:
        die("target file is malformed: missing/!ordered %s markers (%s ... %s). "
            "Is it a flow visual-history.html?" % (what, start, end))
    return i + len(start), j


def rebuild_toc(entries_html):
    """Regenerate the TOC <ul> from every entry's <h2 id=...> in document order."""
    items = re.findall(
        r'<h2\s+id="([^"]+)"\s*>(.*?)</h2>', entries_html, flags=re.DOTALL
    )
    if not items:
        return '<ul><li class="empty">No entries yet — the first distilled decision will appear here.</li></ul>'
    lis = []
    for anchor, label in items:
        # label is already-escaped HTML text from the rendered entry; flatten any tags.
        text = re.sub(r"<[^>]+>", "", label).strip()
        lis.append('<li><a href="#%s">%s</a></li>' % (anchor, text))
    return "<ul>%s</ul>" % "".join(lis)


def existing_slugs(entries_html):
    return set(re.findall(r'<article class="vh-entry" id="([^"]+)"', entries_html))


def main():
    ap = argparse.ArgumentParser(description="Insert one entry into visual-history.html")
    ap.add_argument("--target", required=True, help="path to the project's visual-history.html")
    ap.add_argument("--entry", help="path to entry JSON; omit to read JSON from stdin")
    ap.add_argument("--skeleton", help="path to the skeleton (default: alongside this script)")
    args = ap.parse_args()

    # Load entry JSON.
    try:
        raw = open(args.entry, encoding="utf-8").read() if args.entry else sys.stdin.read()
    except OSError as e:
        die("cannot read entry JSON: %s" % e)
    try:
        entry = json.loads(raw)
    except ValueError as e:
        die("entry is not valid JSON: %s" % e)

    # Resolve / seed the target.
    skeleton = args.skeleton or os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                             "visual-history-skeleton.html")
    if os.path.exists(args.target):
        try:
            doc = open(args.target, encoding="utf-8").read()
        except OSError as e:
            die("cannot read target %s: %s" % (args.target, e))
    else:
        try:
            doc = open(skeleton, encoding="utf-8").read()
        except OSError as e:
            die("target does not exist and skeleton is unreadable (%s): %s" % (skeleton, e))
        tdir = os.path.dirname(os.path.abspath(args.target))
        try:
            os.makedirs(tdir, exist_ok=True)
        except OSError as e:
            die("cannot create target directory %s: %s" % (tdir, e))

    # Validate markers up front (fail before rendering if the doc is malformed).
    e_lo, e_hi = between(doc, ENTRIES_START, ENTRIES_END, "entries")
    entries_region = doc[e_lo:e_hi]

    # Render the new entry, then prepend (reverse-chronological: newest first).
    slug, title, entry_html = render_entry(entry, existing_slugs(entries_region))
    new_entries = "\n" + entry_html + "\n" + entries_region.lstrip("\n")

    # Splice entries, then regenerate the TOC from the updated entries region.
    doc = doc[:e_lo] + new_entries + doc[e_hi:]
    e_lo, e_hi = between(doc, ENTRIES_START, ENTRIES_END, "entries")
    toc_html = rebuild_toc(doc[e_lo:e_hi])
    t_lo, t_hi = between(doc, TOC_START, TOC_END, "toc")
    doc = doc[:t_lo] + "\n" + toc_html + "\n" + doc[t_hi:]

    # Atomic write (temp file + os.replace) so a kill/disk-full mid-write can never
    # truncate the existing durable record — the rename is atomic on POSIX + Windows.
    tmp = args.target + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(doc)
        os.replace(tmp, args.target)
    except OSError as e:
        try:
            os.remove(tmp)
        except OSError:
            pass
        die("cannot write target %s: %s" % (args.target, e))

    sys.stdout.write("%s\t#%s\t%s\n" % (args.target, slug, title))


if __name__ == "__main__":
    main()
