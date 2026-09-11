### Research — visual-verification blueprint (learning from health-tracker)
**Date:** 2026-06-04
**Branch:** `claude/flow-visual-verification-blueprint-DBWxo` (SHA filled at squash-merge)

**What was done:**
Added `dev-docs/research/visual-verification-blueprint-2026-06.md` — an analysis of `byamron/health-tracker`'s visual-verification method (the `visual-walkthroughs.md` discipline + `craft/visual-history.{md,html}`), mapped onto Flow's shipped `/flow:verify-build` findings buffer and the roadmap O8 "Verify-build HTML case-study report" vision. Research/spec doc only; no plugin artifacts touched.

**Why:**
To turn health-tracker's prior art into a concrete, project-agnostic spec for the future HTML-report PR, and to settle whether verify-build's buffer is already a superset of what the report needs.

**Key findings:**
- The buffer **is** a superset for the *evidence + verdict* layer (observations with `type` discriminator + timeline offset, adversarial cases, two-citation per-dimension verdicts, `not_tested`) — validates PR Q's forward-compat call; no migration needed there.
- It is a **blank** for the *rationale* layer (why a visual looks the way it does) and for *subjective human questions* (distinct from epistemic `Unknown`). Proposed two **additive** fields (`criteria[].grounding`, top-level `open_questions`) — `schema_version` stays `1.0`.
- Gate placement maps cleanly to **FB-0035** (sign-off folds into the merge gate; no third gate) + **FB-0034** (escalation routes into a gate). An unanswered `this-iteration` question is the mechanical block on Step 8 auto-advance, mirroring an unresolved MEDIUM assumption.
- Produced a de-tokenization ledger: every health-tracker token (iOS/Xcode capture, brand palette, project doc IDs) → its generic config-sourced Flow form.

**Design decisions:**
- Initially recommended **not** inventing a generic `visual-history` artifact (persist via feedback + roadmap). **User reversed this** — see Follow-up below; the settled call is a uiSurface-gated core doc.

**Tradeoffs discussed:**
- FB numbering: used the next-free **FB-0041** rather than the task-implied 0037–0040 — which turned out correct, since #35 (below) claimed 0037–0040 for the dynamic-workflows direction; FB-0041 serves FB-0040 without collision.

**Provenance note (reconciled with #35):**
The task's referenced prior work (alignment report, FB-0037–0040, the segment-bounded roadmap entry) was absent from `main` at first draft but **landed via PR #35 mid-task**. This branch was rebased onto #35; blueprint § 0 + cross-refs reconciled. The blueprint is the O8 / FB-0039(b) deep-dive #35 left aspirational.

**Status:** Research complete; FB-0042 captured (below); roadmap O8 entry concretized from vision → spec (the two additive buffer fields, the renderer + report structure, the visual-history durable record, FB-0035 gate placement).

**Reconciliation with flow #37 + merged health-tracker #10 (2026-06-05):**
A review of the two open flow PRs (#36 this one, #37) + the merged health-tracker #10 (the original visual-verification use case) surfaced two things to fix:
- **FB-0041 collision with #37.** #37 independently claimed FB-0041 for the *autonomous high-quality deliverable* north-star (the umbrella "Deliverable-quality track": V1 `Visual-walk` plan field → V2 rendered capture → V3 HTML walkthrough → V4 proactive-error loop). #36 had claimed FB-0041 for the visual-history record. Resolved by **renumbering #36's → FB-0042** (the durable-record decision serving #37's umbrella) and recording both in `reserved-feedback-numbers.md`. #36's O8 work is now framed explicitly as **V2/V3 of #37's track** — they are one pipeline, not competitors. Residual textual overlap (both edit the O8 roadmap entry + append entries) is left for whichever PR merges second to resolve toward this reconciled state.
- **Drift from #10 (corrected in FB-0042 + blueprint § 4).** #10 shipped (a) a *single* curated `visual-history.html` as the picture companion to the existing `HISTORY.md` — **no separate `.md`** (the earlier sketch's `.md`+`.html` pair was wrong); and (b) **lean committed JPEG screenshot assets** with CSS/SVG reconstruction as an honest fallback — **not** the "schematic/screenshot-free" rule the earlier AskUserQuestion settled on (that was an over-constraint; #10 serves the repo-health intent better with lean assets). Also adopted #10's conventions: reverse-chronological, decision-centric entries, no italic headings (health-tracker FB-0006), anchor-link TOC.

**Review fix:** removed stray `</content></invoke>` tags accidentally left at the end of the blueprint file by the original Write.

**Tightening pass for implementation (2026-06-05):** at the user's direction (preparing to move toward implementation), pinned the **ephemeral review report co-equal** to the durable record — it is the human-*feedback* surface (exhaustive evidence + the "open questions for you" decisions/tradeoffs needing input), not an afterthought (blueprint § 3 + a new § 4 two-artifact contract table + FB-0042(a)). Made **capture depth an explicit V1→V2 contract** (§ 2/§ 3/roadmap V2): the report must cover the full declared `Visual-walk` state set, and an uncaptured declared state is a finding (`Unknown` + "not tested"), never a silent gap — closing the "exhaustiveness is bounded by capture, not render" caveat. Added **per-PR acceptance criteria** to the roadmap (V2/V3a + V3b) so the track is build-ready.

**Follow-up (2026-06-04, later revised — see the Reconciliation block above):** User reversed the § 4 "skip a generic visual-history" recommendation — directed that the project-evolution companion become an **opt-in, uiSurface-gated core doc** Flow ships. Initially captured as **FB-0041** with a "schematic/screenshot-free" committed `.html`. **Both were revised on 2026-06-05:** renumbered → **FB-0042** (FB-0041 collision with #37) and the screenshot rule corrected to **lean committed assets + CSS/SVG-reconstruction fallback** to match merged health-tracker #10 (the "schematic-only" call was an over-constraint; lean assets serve the repo-health intent better). The `uiSurface`-gated, opt-in scaffolding stands. Implementation still deferred to the future renderer PR (FB-0003: don't land the `visualHistoryPath` slot + template until a producer + `/flow:ship` consumer ship together).
