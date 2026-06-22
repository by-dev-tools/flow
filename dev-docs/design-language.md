# Report design language — the verify-build HTML walkthrough

Scope: this doc governs the **visual language of the `/flow:verify-build` HTML report** emitted by `plugins/flow/skills/verify-build/lib/render-report.py` (V3a). It is **not** a UI surface of the flow plugin itself — flow is a library (`uiSurface: false`). It exists so the renderer's embedded CSS is a deliberate, documented system rather than ad-hoc styling, and so a future change to the report stays coherent.

The report's job (FB-0040): make the human's merge-gate task *thinking*, not rubber-stamping. The design serves legibility of **evidence** and **decisions that need input** — never decoration.

## Principles

1. **Neutral, zero brand tokens.** The report ships to any consumer project; it must carry no project palette/typography. System font stack, neutral greys, semantic accent colors only. A consumer's own brand never leaks in, and the report never imposes one.
2. **Semantic color is reserved for meaning.** Color encodes verdict and rationale-type — nothing else. Decorative color is disallowed (it would dilute the one signal color carries).
3. **Self-contained + ephemeral.** One HTML file, screenshots base64-inlined, no external assets or network. It is regenerated every iteration and discarded after merge (the durable record is V3b's `visual-history.html`).
4. **Evidence is exhaustive; chrome is minimal.** Every observation and every declared `Visual-walk` state is shown (evidence-or-"not captured"). Layout furniture stays quiet so evidence dominates.

## Tokens (as embedded in `render-report.py`)

**Verdict colors** (the only verdict signal — paired with a text label, never color-alone, for accessibility):
- PASS `#1a7f37` (green) · FAIL `#b3261e` (red) · Unknown `#9a6700` (amber)

**Grounding-type chips** (rationale taxonomy):
- need `#0a5fb0` · design-language `#6f42c1` · craft-commitment `#1a7f37` · open-question `#9a6700`

**Routing tags** (open questions): `this iteration` = amber fill (it blocks auto-advance) · `future planning` = neutral grey.

**Provenance warning** (a verdict the implementer self-reported rather than a judge producing it — distinct from any verdict token): banner fill `#fdeecd` (light) / `#3a2a14` (dark), warning rail `#b3261e` left-border, chip `#8a1c12` (light) / `#c4533f` (dark). The chip deliberately does NOT reuse the FAIL verdict red (`#b3261e`) — it sits inline beside a verdict dot, so a FAIL-hue chip would read as a verdict. A self-reported criterion's verdict dot also renders hollow (ring, no fill) so the skim surfaces (heading / TOC / Overall pill) don't read a solid green pass.

**Neutrals:** text `#1c1c1e`, muted `#6b6b70`, surface `#fff`, page `#f6f6f7`, hairline `#e3e3e6`. Radius 8–12px; one card idiom.

**Type:** system stack; H1 30px, H2 20px, body 15px/1.55, meta 11–13px. Monospace (`ui-monospace`) only for observation content (log/network/stdout) and verbatim evidence quotes.

## Accessibility / robustness

- **Never color-alone.** Verdicts pair a colored dot with the verdict word; routing tags carry text. (Contrast-checked against both light and dark surfaces.)
- **Dark mode** via `prefers-color-scheme` — surfaces and hairlines invert; semantic accents hold.
- **Reduced motion:** the report has no animation by design (nothing to suppress).
- **Graceful degradation:** a missing screenshot renders an explicit "not captured" line (red, italic), not a broken image; a malformed/partial buffer renders honest gaps, never a crash.
- **Screenshots:** capped at 600px display width; the *capture* step resizes frames (~460–620px) before persisting — the stdlib renderer does not resize, and a frame over ~500KB emits a build warning.

## Structure (per the blueprint §3)

Hero + verdict pills → legend (verdict + grounding chips) → TOC → per-criterion section (text → grounding callout → evidence timeline → adversarial pane → per-dimension verdict cards with verbatim two-citation evidence) → standalone **"Open questions for you"** → **"What we did NOT test"** → footer.

The standalone questions block is load-bearing: questions are *collected*, not buried inside annotations, so the human answers them as a set (FB-0040).
