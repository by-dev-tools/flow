#!/usr/bin/env python3
"""Render a /flow:verify-build findings buffer into one self-contained ephemeral HTML report.

This is the V3a renderer of the Deliverable-quality track. It reads the JSON buffer
written by verify-build Step 8 (schema: lib/findings-schema.json) and emits a single
HTML file — the artifact the human opens at the merge gate. Its job is to surface the
real decisions/tradeoffs that need human input (the "Open questions for you" block),
backed by exhaustive evidence, so the human's job is *thinking*, not rubber-stamping
(FB-0040). The report is EPHEMERAL — written to a temp path (flow.config.json.verifyReportPath),
never committed.

Constraints (flow quality bar):
- Python stdlib ONLY. No Pillow / jinja / markdown. (Image resizing is the CAPTURE
  step's responsibility — frames are persisted pre-sized ~460-620px; this renderer
  base64-inlines them as-is and caps display width via CSS. A large file emits a warning.)
- Zero project-specific tokens. Neutral default theme; semantic colors only.
- Graceful on malformed / partial buffers: a missing optional field renders an honest
  gap, never a crash.

Usage:
    python3 render-report.py <buffer.json> [--out <report.html>] [--assets-dir <dir>]

If --out is omitted, writes alongside the buffer as <buffer-stem>.html and prints the path.
--assets-dir is the base for relative screenshot paths in observations[].content
(defaults to the buffer's directory).
"""

import argparse
import base64
import html
import json
import mimetypes
import os
import sys

# ---------------------------------------------------------------------------
# Semantic palette (neutral, no brand tokens). Verdicts + the four grounding types.
# ---------------------------------------------------------------------------
VERDICT_COLOR = {"PASS": "#1a7f37", "FAIL": "#b3261e", "Unknown": "#9a6700"}
GROUNDING_LABEL = {
    "need": "Relates to a need",
    "design-language": "Design language",
    "craft-commitment": "Craft commitment",
    "open-question": "Open question",
}
GROUNDING_COLOR = {
    "need": "#0a5fb0",
    "design-language": "#6f42c1",
    "craft-commitment": "#1a7f37",
    "open-question": "#9a6700",
}
ROUTING_LABEL = {"this-iteration": "this iteration", "future-planning": "future planning"}
LARGE_IMAGE_WARN_BYTES = 500_000

CSS = """
:root { color-scheme: light dark; }
* { box-sizing: border-box; }
body { margin: 0; font: 15px/1.55 -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
  color: #1c1c1e; background: #f6f6f7; }
main { max-width: 880px; margin: 0 auto; padding: 32px 20px 96px; }
a { color: inherit; }
.eyebrow { font-size: 12px; letter-spacing: .06em; text-transform: uppercase; color: #6b6b70; margin: 0 0 6px; }
h1 { font-size: 30px; line-height: 1.15; margin: 0 0 10px; }
.lede { font-size: 17px; color: #46464b; margin: 0 0 18px; }
.pills { display: flex; flex-wrap: wrap; gap: 8px; margin: 0 0 28px; }
.pill { display: inline-flex; align-items: center; gap: 6px; padding: 4px 11px; border-radius: 999px;
  font-size: 13px; font-weight: 600; background: #ececee; color: #1c1c1e; }
.pill .dot { width: 9px; height: 9px; border-radius: 50%; }
.card { background: #fff; border: 1px solid #e3e3e6; border-radius: 12px; padding: 18px 20px; margin: 0 0 16px; }
.legend { display: flex; flex-wrap: wrap; gap: 8px 16px; font-size: 13px; }
.legend .item { display: inline-flex; align-items: center; gap: 6px; }
.chip { display: inline-block; padding: 2px 9px; border-radius: 6px; font-size: 12px; font-weight: 600; color: #fff; }
nav.toc ol { margin: 6px 0 0; padding-left: 20px; }
nav.toc li { margin: 3px 0; }
section.criterion { scroll-margin-top: 16px; }
h2 { font-size: 20px; margin: 30px 0 8px; }
.grounding { border-left: 4px solid #e3e3e6; padding: 8px 14px; margin: 12px 0; background: #f6f6f7; border-radius: 0 8px 8px 0; }
.grounding .gtype { font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: .04em; }
.grounding .cites { font-size: 12px; color: #6b6b70; margin-top: 4px; }
.timeline { list-style: none; margin: 10px 0; padding: 0; }
.obs { border: 1px solid #e3e3e6; border-radius: 8px; padding: 10px 12px; margin: 8px 0; }
.obs .meta { font-size: 11px; color: #6b6b70; text-transform: uppercase; letter-spacing: .04em; margin-bottom: 4px; }
.obs img { max-width: 600px; width: 100%; height: auto; border: 1px solid #e3e3e6; border-radius: 6px; display: block; }
.obs pre { margin: 0; white-space: pre-wrap; word-break: break-word; font: 12.5px/1.5 ui-monospace, Menlo, monospace; }
.missing { color: #b3261e; font-style: italic; font-size: 13px; }
.adversarial { font-size: 13.5px; }
.adversarial ul { margin: 4px 0 0; padding-left: 20px; }
.verdicts { display: grid; gap: 10px; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); margin-top: 12px; }
.vcard { border: 1px solid #e3e3e6; border-radius: 8px; padding: 10px 12px; }
.vcard .vhead { display: flex; align-items: center; gap: 8px; font-weight: 600; margin-bottom: 6px; }
.vcard blockquote { margin: 4px 0; padding-left: 10px; border-left: 3px solid #e3e3e6; font-size: 12.5px; color: #46464b; }
.vcard .notes { font-size: 12.5px; color: #6b6b70; margin-top: 4px; }
.oq { counter-reset: oq; }
.oq .q { border: 1px solid #e3e3e6; border-radius: 10px; padding: 14px 16px; margin: 0 0 12px; }
.oq .q h3 { margin: 0 0 6px; font-size: 16px; }
.oq .q h3::before { counter-increment: oq; content: counter(oq) ". "; color: #6b6b70; }
.oq .meta-row { font-size: 13px; margin: 3px 0; }
.oq .meta-row b { color: #46464b; }
.routing { font-size: 11px; font-weight: 700; padding: 2px 8px; border-radius: 6px; }
.routing.this-iteration { background: #fde7c7; color: #7a4d00; }
.routing.future-planning { background: #e4e4e7; color: #46464b; }
table.nt { width: 100%; border-collapse: collapse; font-size: 13.5px; }
table.nt td { padding: 5px 8px; border-bottom: 1px solid #e3e3e6; }
table.nt td.mark { width: 28px; text-align: center; }
footer { margin-top: 40px; font-size: 12.5px; color: #6b6b70; border-top: 1px solid #e3e3e6; padding-top: 14px; }
@media (prefers-color-scheme: dark) {
  body { color: #e6e6ea; background: #161618; }
  .card, .vcard, .obs, .oq .q { background: #1f1f22; border-color: #34343a; }
  .grounding { background: #232327; }
  .lede, .vcard blockquote, .oq .meta-row b { color: #b7b7bd; }
  .pill { background: #2b2b30; color: #e6e6ea; }
  .routing.this-iteration { background: #4a3a1a; color: #f0d9a8; }
  .routing.future-planning { background: #2b2b30; color: #b7b7bd; }
}
"""


def esc(s):
    return html.escape("" if s is None else str(s))


def verdict_dot(v):
    return f'<span class="dot" style="background:{VERDICT_COLOR.get(v, "#888")}"></span>'


def render_hero(meta, overall, exit_code, baseline_seeding=False):
    eyebrow = " · ".join(
        x for x in [meta.get("branch"), meta.get("head_sha_short"),
                    meta.get("platform_hint"), f'flow {meta.get("plugin_version", "?")}'] if x
    )
    budget = meta.get("verify_budget_calls_used")
    pills = [
        f'<span class="pill">{verdict_dot(overall)}Overall: {esc(overall)}</span>',
        f'<span class="pill">verify exit code: {esc(exit_code)}</span>',
    ]
    if budget is not None:
        over = " (overrun)" if meta.get("verify_budget_overrun") else ""
        pills.append(f'<span class="pill">{esc(budget)} verify calls{over}</span>')
    if meta.get("spike_mode"):
        pills.append('<span class="pill">spike mode</span>')
    lede = ("What the running app actually did, judged against the plan's acceptance criteria — "
            "and the decisions that still need your call.")
    if baseline_seeding:
        lede += (" This is a baseline-seeding run — visual-layout verdicts are Unknown by design until "
                 "the next run compares against the frames captured here; that is expected, not a failure.")
    return (f'<p class="eyebrow">{esc(eyebrow)}</p>'
            f'<h1>Verify-build walkthrough</h1>'
            f'<p class="lede">{esc(lede)}</p>'
            f'<div class="pills">{"".join(pills)}</div>')


def render_legend():
    verdict_items = "".join(
        f'<span class="item">{verdict_dot(v)}{v}</span>' for v in ("PASS", "FAIL", "Unknown")
    )
    grounding_items = "".join(
        f'<span class="item"><span class="chip" style="background:{GROUNDING_COLOR[k]}">{esc(GROUNDING_LABEL[k])}</span></span>'
        for k in GROUNDING_LABEL
    )
    return (f'<div class="card legend"><strong style="width:100%">How a verdict / a choice earns its place</strong>'
            f'{verdict_items}{grounding_items}</div>')


def slug(i):
    return f"criterion-{i}"


def render_toc(criteria):
    items = "".join(
        f'<li><a href="#{slug(i)}">{verdict_dot(c.get("aggregated_verdict", "Unknown"))} {esc(c.get("text", "(untitled)"))}</a></li>'
        for i, c in enumerate(criteria)
    )
    return f'<nav class="toc card"><strong>Criteria</strong><ol>{items}</ol></nav>'


def render_grounding(g):
    if not g:
        return ""
    gtype = g.get("type", "open-question")
    color = GROUNDING_COLOR.get(gtype, "#888")
    cites = g.get("citations") or []
    cite_html = (f'<div class="cites">Grounded in: {esc(", ".join(cites))}</div>' if cites else "")
    dtest = (f'<div class="cites">Decision test: {esc(g["decision_test"])}</div>'
             if g.get("decision_test") else "")
    return (f'<div class="grounding" style="border-left-color:{color}">'
            f'<div class="gtype" style="color:{color}">{esc(GROUNDING_LABEL.get(gtype, gtype))}</div>'
            f'<div>{esc(g.get("statement", ""))}</div>{cite_html}{dtest}</div>')


def render_observation(obs, assets_dir, warnings, label):
    otype = obs.get("type", "narrative")
    content = obs.get("content", "")
    off = obs.get("timestamp_offset_ms")
    meta = otype + (f" · +{off}ms" if off is not None else "")
    if otype == "screenshot":
        body = render_screenshot(content, assets_dir, warnings, label)
    else:
        body = f"<pre>{esc(content)}</pre>"
    return f'<li class="obs"><div class="meta">{esc(meta)}</div>{body}</li>'


def render_screenshot(content, assets_dir, warnings, label):
    # `label` (the criterion text) is the alt text — a filename tells a screen-reader nothing.
    alt = esc(f"Captured frame: {label}")
    if isinstance(content, str) and content.startswith("data:"):
        # Allowlist raster image data URIs only. Reject data:image/svg+xml (SVG can carry
        # markup/handlers) and any non-image payload. SVG-in-<img> is already non-scripting
        # in browsers, but this is cheap defense-in-depth + aligns with "no base64 in context".
        mediatype = content[5:].split(",", 1)[0].split(";", 1)[0].lower().strip()
        if mediatype not in ("image/png", "image/jpeg", "image/jpg", "image/gif", "image/webp"):
            return (f'<p class="missing">Screenshot not inlined — data URI media type '
                    f'{esc(mediatype) or "(none)"} is not in the raster-image allowlist.</p>')
        return f'<img src="{esc(content)}" alt="{alt}" />'
    # Resolve relative to assets_dir and reject absolute paths or any path that escapes it
    # (the buffer is self-authored, but the renderer should not read arbitrary files).
    if not isinstance(content, str) or os.path.isabs(content):
        return f'<p class="missing">Screenshot not captured (absolute or invalid path rejected: {esc(content)})</p>'
    base = os.path.realpath(assets_dir)
    path = os.path.realpath(os.path.join(base, content))
    if path != base and not path.startswith(base + os.sep):
        return f'<p class="missing">Screenshot not captured (path escapes the assets dir: {esc(content)})</p>'
    if not os.path.isfile(path):
        return f'<p class="missing">Screenshot not captured (no file at {esc(content)})</p>'
    try:
        raw = open(path, "rb").read()
    except OSError as e:
        return f'<p class="missing">Could not read screenshot {esc(content)}: {esc(e)}</p>'
    if len(raw) > LARGE_IMAGE_WARN_BYTES:
        warnings.append(f"{content} is {len(raw)//1024}KB — capture should resize frames (~460-620px) before persisting.")
    mime = mimetypes.guess_type(path)[0] or "image/png"
    b64 = base64.b64encode(raw).decode("ascii")
    return f'<img src="data:{mime};base64,{b64}" alt="{alt}" />'


def render_observations(obs_list, assets_dir, warnings, label):
    if not obs_list:
        return '<p class="missing">No observations captured for this criterion — it was not exercised (see the coverage checklist below).</p>'
    items = "".join(render_observation(o, assets_dir, warnings, label) for o in obs_list)
    return f'<ul class="timeline">{items}</ul>'


def render_adversarial(cases):
    if not cases:
        return ""
    items = "".join(f"<li>{esc(c)}</li>" for c in cases)
    return f'<div class="adversarial card"><strong>Adversarial cases probed</strong><ul>{items}</ul></div>'


def render_verdict_cards(verdicts):
    cards = []
    for dim in ("correctness", "regression", "scope-creep"):
        v = (verdicts or {}).get(dim)
        if not v:
            continue
        verdict = v.get("verdict", "Unknown")
        ev = v.get("evidence") or []
        quotes = "".join(f"<blockquote>{esc(q)}</blockquote>" for q in ev)
        notes = f'<div class="notes">{esc(v["notes"])}</div>' if v.get("notes") else ""
        cards.append(
            f'<div class="vcard"><div class="vhead">{verdict_dot(verdict)}'
            f'<span style="color:{VERDICT_COLOR.get(verdict, "#888")}">{esc(verdict)}</span>'
            f'<span style="color:#6b6b70;font-weight:400">· {dim}</span></div>{quotes}{notes}</div>'
        )
    return f'<div class="verdicts">{"".join(cards)}</div>' if cards else ""


def render_criterion(i, c, assets_dir, warnings):
    return (
        f'<section class="criterion" id="{slug(i)}">'
        f'<h2>{verdict_dot(c.get("aggregated_verdict", "Unknown"))} {esc(c.get("text", "(untitled)"))}</h2>'
        f'{render_grounding(c.get("grounding"))}'
        f'{render_observations(c.get("observations"), assets_dir, warnings, c.get("text", "this criterion"))}'
        f'{render_adversarial(c.get("adversarial_cases"))}'
        f'{render_verdict_cards(c.get("verdicts"))}'
        f'</section>'
    )


def render_open_questions(questions):
    if not questions:
        return ('<section><h2>Open questions for you</h2>'
                '<p class="lede">None raised — the agent had no subjective/taste calls needing your input this run.</p></section>')
    # Blocking (this-iteration) questions first — those are what the human must act on to proceed.
    questions = sorted(questions, key=lambda q: 0 if q.get("routing") == "this-iteration" else 1)
    blocks = []
    for q in questions:
        routing = q.get("routing", "future-planning")
        rows = []
        if q.get("rationale"):
            rows.append(f'<div class="meta-row"><b>Our view:</b> {esc(q["rationale"])}</div>')
        if q.get("recommended_default"):
            rows.append(f'<div class="meta-row"><b>Recommended default:</b> {esc(q["recommended_default"])}</div>')
        if q.get("user_need_lens"):
            rows.append(f'<div class="meta-row"><b>User-need lens:</b> {esc(q["user_need_lens"])}</div>')
        blocks.append(
            f'<div class="q"><h3>{esc(q.get("question", ""))} '
            f'<span class="routing {esc(routing)}">{esc(ROUTING_LABEL.get(routing, routing))}</span></h3>'
            f'{"".join(rows)}</div>'
        )
    note = ('<p class="lede">A <b>this iteration</b> question blocks auto-advance until you answer — '
            'a "this is wrong" sends the work back through Execute. <b>Future planning</b> routes to the roadmap.</p>')
    return f'<section class="oq"><h2>Open questions for you</h2>{note}{"".join(blocks)}</section>'


def render_not_tested(items):
    if not items:
        return ""
    rows = "".join(
        f'<tr><td class="mark">{"✓" if it.get("tested") else "✗"}</td>'
        f'<td>{esc(it.get("item", ""))}'
        f'{(" — " + esc(it["rationale"])) if it.get("rationale") else ""}</td></tr>'
        for it in items
    )
    return f'<section><h2>Coverage — what we did and did not test</h2><div class="card"><table class="nt"><tbody>{rows}</tbody></table></div></section>'


def render(buffer, assets_dir):
    warnings = []
    meta = buffer.get("metadata", {})
    criteria = buffer.get("criteria", []) or []
    not_tested = buffer.get("not_tested") or []
    overall = buffer.get("overall_verdict", "Unknown")
    # Hospitality (FB-0040): if the only reason for an Unknown is "no baseline yet", say so up front
    # so the first glance isn't a quiet alarm for the expected baseline-seeding run.
    baseline_seeding = overall == "Unknown" and any(
        "baseline" in it.get("item", "").lower() and not it.get("tested") for it in not_tested
    )
    body = (
        render_hero(meta, overall, buffer.get("exit_code", 1), baseline_seeding)
        + render_legend()
        + render_toc(criteria)
        + "".join(render_criterion(i, c, assets_dir, warnings) for i, c in enumerate(criteria))
        + render_open_questions(buffer.get("open_questions"))
        + render_not_tested(buffer.get("not_tested"))
        + f'<footer>Ephemeral verify-build report · branch {esc(meta.get("branch", "?"))} '
          f'@ {esc(meta.get("head_sha_short", "?"))}. Not committed — regenerated every iteration. '
          f'The durable record lives in the project history.</footer>'
    )
    doc = (f'<!doctype html><html lang="en"><head><meta charset="utf-8">'
           f'<meta name="viewport" content="width=device-width, initial-scale=1">'
           f'<title>Verify-build walkthrough · {esc(meta.get("branch", ""))}</title>'
           f'<style>{CSS}</style></head><body><main>{body}</main></body></html>')
    return doc, warnings


def main(argv=None):
    ap = argparse.ArgumentParser(description="Render a verify-build findings buffer to a self-contained HTML report.")
    ap.add_argument("buffer", help="Path to the findings buffer JSON.")
    ap.add_argument("--out", help="Output HTML path (default: <buffer-stem>.html).")
    ap.add_argument("--assets-dir", help="Base dir for relative screenshot paths (default: buffer's dir).")
    args = ap.parse_args(argv)

    try:
        buffer = json.load(open(args.buffer))
    except (OSError, json.JSONDecodeError) as e:
        print(f"[render-report] cannot read buffer {args.buffer}: {e}", file=sys.stderr)
        return 2

    assets_dir = args.assets_dir or os.path.dirname(os.path.abspath(args.buffer))
    out = args.out or (os.path.splitext(args.buffer)[0] + ".html")
    doc, warnings = render(buffer, assets_dir)
    try:
        with open(out, "w", encoding="utf-8") as f:
            f.write(doc)
    except OSError as e:
        print(f"[render-report] cannot write report {out}: {e}", file=sys.stderr)
        return 2
    for w in warnings:
        print(f"[render-report] WARN: {w}", file=sys.stderr)
    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
