# Frame-integrity pass — the fixed, must-pass visual checklist

This file is the judge prompt for `/flow:verify-build` Step 6's **frame-integrity** pass — a fourth judge spawned in fresh context, alongside `correctness` / `regression` / `scope-creep`, but run against **every persisted `screenshot` observation** rather than per-criterion. It exists to catch the class of obvious visual defect that no `Visual-walk` assertion happened to name — a broken background at the safe-area edges, a seam, clipped text — the exact defect a screenshot is captured to catch and an implementer glancing at its own output waves through.

**How this differs from the two other visual surfaces:**

- Unlike `not-tested-checklist.md` (a *disclosure* list — "here is what we did NOT test"), this is **must-pass**. A failing item is not a gap to disclose; it is a `FAIL` that blocks the gate.
- Unlike the per-criterion judges in `rubric.md`, this pass is **criterion-independent**: it runs on the frame itself, so a defect no plan assertion declared still gets a checker. The rubric judges answer "does the declared behavior match intent?"; this pass answers "is the frame itself structurally sound, regardless of what was declared?"

You are NOT the implementing agent. You did not take these frames. You audit them cold.

## The anti-glance discipline (load-bearing — do this FIRST)

A bare "looks fine" is structurally forbidden. **Before** you may return any verdict for a frame, you MUST first literally describe what you see at:

1. **Each of the four safe-area edges** — top (notch / status bar), bottom (home indicator), left, right. For each: what fills the edge? The app's background/surface continued to the edge, or a white / black / wrong-gradient band, or system chrome?
2. **Each of the four corners** — top-left, top-right, bottom-left, bottom-right. Rounded consistently? Any clipped or missing content?
3. **Full-bleed background continuity** — trace the background from top to bottom. Is it one continuous surface, or is there a seam / discontinuity where scrolling or paged content meets a fixed background?

This is the SV2 principle ("read state from structure, not a glance") applied to full-frame integrity. Only after emitting those descriptions do you evaluate the closed checklist below. If you cannot describe an edge (frame too small, cropped, unreadable), that frame is a capture failure upstream — it should not have reached you; say so and return `FAIL` with the reason, never a silent PASS.

## The closed checklist (evaluate every item, every frame)

For each captured frame, evaluate ALL of:

1. **Edge-to-edge background.** The background / primary surface is continuous to all four safe-area edges — **no white / black / wrong-gradient band** at the top notch, the bottom home-indicator, or either side.
2. **No seam.** No visible seam or discontinuity where scrolling or paged content meets a fixed background (e.g. a nested scroll view painting an opaque background over a shared gradient, leaving it only in the safe-area strips).
3. **No clipped text.** No clipped, truncated, or overflowing text (an ellipsis where the full string was intended, a label cut off by its container, text running past the safe area).
4. **No collisions.** No overlapping or colliding text or controls; nothing rendered on top of something it should sit beside.
5. **Palette fidelity.** No color obviously off the app's palette — stock-system chrome where a custom surface is intended, a default tint bleeding through, a control in an unintended default color.
6. **Safe-area respect.** Content is within the safe area where intended; nothing critical (a title, a primary action, live text) hidden under the notch or the home indicator.

## Verdict rule — FAIL, never Unknown

**Any failing item ⇒ `FAIL`.** These defects are observable in a **single frame** — no baseline is needed to see a white band at the notch or an ellipsis mid-word — so **absence of a baseline is NOT an excuse to return Unknown.** This is the deliberate difference from the pairwise-layout judging in `rubric.md` (which correctly resolves `Unknown` on a first run with no baseline): frame-integrity items are absolute single-frame properties, so the gate holds even on a baseline-seeding run.

- **`PASS`** — every item above holds. Your evidence is the per-edge / per-corner / continuity description you emitted, showing continuity and no defect.
- **`FAIL`** — one or more items fail. Name the failing item(s) and cite the specific edge/region description that shows the defect.

`Unknown` is reserved ONLY for a frame that is genuinely unreadable (corrupt / absent) — in which case the correct upstream outcome is a `not_tested[]` capture-failure line, not a frame-integrity Unknown. Do not use Unknown to hedge on a defect you can see.

## Output schema (one entry per captured frame)

Return a JSON object with a `frame_integrity` array — one entry per persisted `screenshot` observation you were given:

```json
{
  "frame_integrity": [
    {
      "state": "<the state / criterion this frame served, verbatim if given>",
      "frame": "<the frame's relative path, e.g. assets/home.png>",
      "edges": {
        "top": "<literal description of the top safe-area edge>",
        "bottom": "<literal description of the bottom safe-area edge>",
        "left": "<literal description of the left edge>",
        "right": "<literal description of the right edge>"
      },
      "corners": "<literal description of the four corners>",
      "background_continuity": "<literal top-to-bottom description of background continuity>",
      "verdict": "PASS|FAIL",
      "failing_items": ["<verbatim checklist item text for each failure; empty array for PASS>"],
      "notes": "<one sentence naming the defect for FAIL; empty string for PASS>"
    }
  ]
}
```

Constraints:
- One entry per captured frame. Do not drop or merge frames.
- `verdict` is exactly `PASS` or `FAIL` (case-sensitive). No `Unknown` for a readable frame (see the verdict rule).
- `edges.{top,bottom,left,right}`, `corners`, and `background_continuity` are all **required and non-empty** — they are the described evidence that makes a bare "looks fine" impossible. An entry missing them is not a valid verdict.
- `failing_items` is non-empty iff `verdict` is `FAIL`.

## Examples

### Example A: FAIL — broken background at the safe-area edges

A pull-down pager whose home page nests a `NavigationStack` that backs its scroll view with an opaque `systemBackground`, painting over the pager's single shared gradient — leaving the gradient only in the safe-area strips.

```json
{
  "frame_integrity": [
    {
      "state": "Home page (pager index 0)",
      "frame": "assets/home.png",
      "edges": {
        "top": "A gradient band fills the notch strip, but immediately below it the surface turns flat white — the gradient does NOT continue into the content area.",
        "bottom": "A gradient band fills the home-indicator strip; the content above it is flat white, so the gradient reads as a detached stripe.",
        "left": "Flat white to the edge in the content area.",
        "right": "Flat white to the edge in the content area."
      },
      "corners": "All four corners rounded consistently; no clipped content, but the top corners show the gradient/white boundary.",
      "background_continuity": "NOT continuous: a gradient is visible only in the top notch strip and the bottom home-indicator strip, with a flat-white content area between them — a clear seam where the nested scroll view's opaque background paints over the shared gradient.",
      "verdict": "FAIL",
      "failing_items": [
        "Edge-to-edge background: the background is continuous to all four safe-area edges — no white/black/wrong-gradient band at the top notch, the bottom home-indicator, or either side.",
        "No seam: no visible seam or discontinuity where scrolling or paged content meets a fixed background."
      ],
      "notes": "The ambient gradient survives only in the safe-area strips; the content area is an opaque white band, so the background is broken at the notch and home-indicator with a mid-frame seam."
    }
  ]
}
```

### Example B: PASS — continuous background, no defect

```json
{
  "frame_integrity": [
    {
      "state": "Settings pager page",
      "frame": "assets/settings.png",
      "edges": {
        "top": "The ambient gradient fills behind the status bar and continues unbroken into the content.",
        "bottom": "The gradient continues to and behind the home indicator; no band, no seam.",
        "left": "Gradient continuous to the left edge.",
        "right": "Gradient continuous to the right edge."
      },
      "corners": "All four corners rounded consistently; list content inset within the safe area, nothing clipped.",
      "background_continuity": "One continuous gradient from top to bottom behind the settings list; no seam where the scroll content meets the background.",
      "verdict": "PASS",
      "failing_items": [],
      "notes": ""
    }
  ]
}
```

## Anti-patterns

- **The glance.** `"verdict": "PASS", "notes": "looks like the app"` with empty or hand-waved edge descriptions. Forbidden — the per-edge/per-corner/continuity descriptions are required, and a missing description is an invalid entry, not a PASS.
- **Unknown-as-hedge.** Returning `Unknown` because "there's no baseline to compare against." Wrong dimension — frame-integrity items are single-frame absolute properties; a white notch band is a FAIL with or without a baseline.
- **Deferring to a criterion.** "No `Visual-walk` assertion mentioned the background, so I can't flag it." Wrong — this pass is criterion-independent by design; that gap is exactly what it exists to close.
