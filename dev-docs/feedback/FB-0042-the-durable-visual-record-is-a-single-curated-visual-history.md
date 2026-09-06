### FB-0042: The durable visual record is a single curated `visual-history.html` — the picture companion to the existing history core doc; lean committed screenshot assets (CSS/SVG reconstruction as the honest fallback), reverse-chronological, decision-centric, no italic headings
**Date:** 2026-06-04 (reconciled 2026-06-05 against merged health-tracker #10 + flow #37)
**Source:** user direction (reversed a "skip it" recommendation; then reconciled to the merged reference implementation)

**What was said:** The user directed adding a durable visual record as a Flow core doc (reversing the blueprint's § 4 "skip it"), then — reviewing #36 alongside flow #37 and the **merged** health-tracker **PR #10** — asked to ensure the best aspects of each land with no drift. #10 is the reference implementation of the durable record + the two-artifact model; this entry is aligned to what #10 actually shipped, not the earlier `.md`+`.html` / "schematic-only" sketch.

**Synthesized rule:** Flow's consumer scaffolding gains an opt-in durable visual record, serving the FB-0040 + FB-0041 (#37) north stars as the **V3 distillation target** of the Deliverable-quality track. Five disciplines, taken from #10's merged shape:

```
(a) Two CO-EQUAL artifacts, never conflated. The per-run verify-build report
    (O8 / the Deliverable-quality track's V3 renderer) is EPHEMERAL — the
    human-FEEDBACK surface: exhaustive evidence across the full declared
    Visual-walk state set PLUS the "open questions for you" (the decisions/
    tradeoffs needing human input), opened at the merge gate, then discarded.
    The visual record is DURABLE — the curated visual subset (only decisions
    that changed the user's read of a surface), committed, grown over the
    project's life. The ephemeral report is not an afterthought; it FEEDS the
    record: at /flow:ship the load-bearing visual decisions (the grounding that
    changed the user's read + the this-iteration questions the human resolved)
    are distilled into one entry, then the report is thrown away. Both must be
    built — the ephemeral renderer AND the durable record AND the distill bridge
    (see the contract table in the blueprint § 4).

(b) A SINGLE curated `visual-history.html`, the PICTURE companion to the
    EXISTING history core doc (flow.config.json.historyPath). NOT a new
    `visual-history.md`, NOT a `.md`+`.html` pair — the written timeline is
    already history.md; this is its visual sibling. (Corrects the earlier
    sketch: #10 has no separate `.md`; it `git mv`'d case-study.html →
    visual-history.html as the one durable visual record.)

(c) Lean COMMITTED screenshot assets, NOT schematic/screenshot-free. Real
    captures preferred — resized keeper images (~≤720px) on relative paths in
    a `visual-history-assets/` dir, write-once + curated (churny galleries
    stay in the ephemeral report). A faithful CSS/SVG reconstruction is the
    HONEST fallback when capture isn't available (e.g. a no-simulator Linux/
    web container), labelled as such, using real values. NOT base64-embedded
    (that's the ephemeral report's mechanism; the durable record references
    assets so git stays healthy). (Corrects the earlier "schematic, zero PNGs"
    rule — #10 commits lean JPEGs; the underlying intent was repo-health, which
    lean assets serve better than schematic-only.)

(d) Curated + decision-centric, reverse-chronological, no italic headings.
    Newest entry at the top (reviewable without scrolling); an interactive
    anchor-link TOC. Each entry is a prominent DECISION (not a PR dump),
    carrying PR#/date/branch metadata, grounding (the user need + decision
    test, or the design-language / craft-commitment rationale), a key
    before/after, and questions carried forward. NO italics in headings
    (health-tracker FB-0006 — applies to authored artifacts, not just app UI).

(e) uiSurface-gated, opt-in. Created only for uiSurface=true projects —
    non-UI consumers (FB-0007) don't get an empty doc. Visual-scoped, not
    generalized to ADR-style decision-history.
    [MECHANISM UPDATED by FB-0053, v1.8.0]: the original "scaffold into
    template/base/core-docs via bootstrap" wording was reversed to
    CREATED-ON-FIRST-WRITE by the /flow:ship Step 5c distill step (seeded
    from a lib skeleton). bootstrap.sh runs before flow.config.json exists,
    so it can't gate on uiSurface; create-on-first-write moves the gate to
    where uiSurface is known. Intent (uiSurface-gated, no empty doc)
    unchanged.
```

Citations resolve from `specPath` / `designLanguagePath` slots — never hardcoded project doc names (project-agnostic quality bar). New slot: `visualHistoryPath` (the `.html` companion to `historyPath`). The grounding + "open questions" disciplines this record distills are the same ones #10 keeps as prose in its `visual-walkthroughs.md` and that #36's blueprint encodes as the verify-build buffer's `grounding` + `open_questions` fields.

**Relationship to the other in-flight work:**
- **#37 (FB-0041)** is the umbrella — the autonomous-deliverable north star whose chain is V1 `Visual-walk` plan field → V2 rendered capture → V3 HTML walkthrough → V4 proactive-error loop. FB-0042 is the *durable-record* half of V3 (the ephemeral renderer is the other half). FB-0042 was renumbered from a colliding FB-0041 to sit above #37's.
- **#10 (merged, health-tracker)** is the reference implementation this entry mirrors. flow's version is the project-agnostic generalization.

**Encoding constraints:**
- FB-0003 (schema-without-implementation): don't land `visualHistoryPath` / the template file until a producer writes the record and `/flow:ship`'s distill step reads it — same PR.
- FB-0016 (re-test new capability on UI before generalizing): land it against a real UI surface (health-tracker is the available fixture) before declaring the entry shape stable.

**Applies to:** `template/base/core-docs/`, `flow.config.json` slots (`visualHistoryPath`), `/flow:ship` distill step, the roadmap "Deliverable-quality track" V3 + the O8 entry, the future renderer PR, the two-gate model (durable record written at ship; FB-0035 visual sign-off folds into merge).

**Origin:** the visual-verification blueprint (`dev-docs/research/visual-verification-blueprint-2026-06.md`). Reversal of § 4's "skip it" recorded 2026-06-04; reconciled to #10's merged shape + #37's track 2026-06-05.
