# Visual-verification → Flow blueprint (learning from health-tracker)

**Date:** 2026-06-04
**Branch:** `claude/flow-visual-verification-blueprint-DBWxo`
**Source:** analysis of `byamron/health-tracker` visual-verification work, mapped onto Flow's shipped `/flow:verify-build` (v1.3.0) + the roadmap "Verify-build HTML case-study report" vision (O8).

---

## 0. Provenance note — the referenced prior work landed mid-task (via #35)

This blueprint was first drafted against a `main` that did **not** yet contain the prior-work artifacts the commissioning task referenced, so the original draft flagged them as absent. **They landed on `main` via PR #35 ("dynamic-workflows alignment report + adoption direction") while this task was in flight**; this doc has since been rebased onto and reconciled with them. They are now the canonical anchors:

| Referenced by the task | Status now (post-#35) |
|---|---|
| `dev-docs/research/dynamic-workflows-alignment-2026-06.md` (the "alignment report", O1–O8) | **Present** (#35). The umbrella analysis this blueprint plugs into. |
| `dev-docs/feedback.md` → FB-0037 / FB-0038 / FB-0039 / FB-0040 | **Present** (#35). FB-0040 = the human-review north star; FB-0037 = designer-lens preservation; FB-0038 = cost-aware use; FB-0039 = preserve the review/learning artifacts. |
| `roadmap.md` → "Dynamic-workflows adoption: segment-bounded fan-out between gates" | **Present** (#35), § Exploration. The segment-bounded doctrine (a workflow owns fan-out *between* gates, never spans one). |
| `roadmap.md` → "Verify-build HTML case-study report" (O8) | **Present** (pre-existing). The anchor this blueprint concretizes into a spec. |

How this blueprint relates to #35:

- **It is the O8 / FB-0039(b) deep-dive.** #35 names the companion HTML case-study + visual history as load-bearing artifacts to preserve (FB-0039) but marks them **ASPIRATIONAL / not-yet-shipped**; this blueprint is the concrete spec for building them from verify-build's buffer.
- **The north star is FB-0040, not a reconstruction.** Where the first draft said "Flow has no equivalent FB yet," FB-0040 now *is* that equivalent. health-tracker's FB-0006 is the same principle proven on a UI surface; this blueprint operationalizes FB-0040 into buffer fields (`grounding`, `open_questions`) + the rendered report.
- **Segment-bounded gate placement (§ 5)** is #35's roadmap doctrine, not a paraphrase: the visual segment lives inside **Segment B** (Execute→Present) and folds into the merge gate (FB-0035) — never a new gate.
- **FB-0042** (this blueprint's capture; renumbered from a colliding FB-0041 — see § 7) *serves* FB-0040 and #37's FB-0041, scoping the durable-visual-record decision (§ 4). #37's FB-0041 is the autonomous-deliverable umbrella whose V3 this blueprint specs.
- **Cost-aware use (FB-0038)** is already partly shipped: `verifyBudgetCalls` cap (verify-build §5), FB-0006/FB-0007 per-diff early-exits, health-tracker's "3–6 questions" calibration.
- **Also reconciled (2026-06-05) with two later artifacts:** flow **#37** (the "Deliverable-quality track" — its `Visual-walk` plan field is V1, this blueprint's renderer + durable record are V2/V3; resolved a shared FB-0041 collision by renumbering this capture to **FB-0042**), and **merged health-tracker #10** (the reference implementation of the durable record — corrected § 4 to a single curated `visual-history.html` with lean screenshot assets). See § 1, § 4, § 7.

The blueprint below is reconciled with #35, #37, and merged health-tracker #10 throughout.

---

## 1. What health-tracker actually built (the prior art)

Phases 0a/0b + the visual-verification work produced a coherent *method*, documented in `workflow/visual-walkthroughs.md`. It **merged as PR #10**, which `git mv`'d `craft/case-study.html` → a single **`craft/visual-history.html`** (the durable visual record) + a `visual-history-assets/` dir of lean screenshots, and **absorbed a parallel jtbd-grounding PR (#9)** into one consolidated model — so the merged reality is a *single* `.html` companion to the written `HISTORY.md`, not the `.md`+`.html` pair an earlier branch had explored. (An earlier draft of this blueprint modelled that interim pair; § 4 + FB-0042 are corrected to #10's merged shape.)

The load-bearing ideas, in Flow-relevant terms:

1. **The review is not a show-and-approve.** Its three jobs, in order: (a) prove the surface renders what we think (screenshots, not success messages — "the API and the build can both lie"); (b) show *why* each visual looks the way it does, traced to a user need **or honestly** to the design language; (c) raise the questions only the human can answer. "A review where every annotation is a confident assertion and there are no open questions is a review that has hidden its judgment calls."

2. **Grounding discipline — four rationale types, no fifth.** Every annotated visual is tagged exactly one of: **Relates to a need** (cite the job + the decision test) · **Design language** (name the system rule it follows) · **Craft commitment** (the one-sentence stance defense) · **Open question** (no cohesive rationale yet → raised, never papered over). The explicit anti-pattern: *don't manufacture a user-need to launder a styling call*, and *don't ship a choice with no stated reason*.

3. **Questions discipline.** 3–6 substantive questions (zero = hidden judgment; twenty = offloaded the thinking). Each carries: answerable phrasing with options · our rationale + a **recommended default** · the user-need lens · a routing tag — **`[this iteration]`** (a "this is wrong" re-enters **Execute**; never ship over it) or **`[future planning]`** (routes to the roadmap / open-questions).

4. **Two-tier persistence.** The rendered review HTML is **ephemeral** (lives on `~/Desktop`, can be huge/image-heavy, never committed). What *persists* is the distilled decision record: `visual-history.md` (tracked, diff-friendly) + `visual-history.html` (committed rendered companion). This keeps evidence-weight out of the repo while preserving the *decision-making*.

5. **Gate placement.** The review is the **Present-step** artifact; iteration happens there, before the ship decision. This is exactly FB-0035.

The rendered HTML structure (from `visual-history.html` + `case-study.html`): **hero + lede + meta pills** → **legend** ("how a decision earns its place" — the four rationale chips) → **per-entry article**: id + title + **grounding callout** (rationale type + citations) + **before/after visual block** + **two-pane grid** (explorations / outcome+impact) + **questions-carried-forward** block. The case study adds a **TOC** and a per-section **question / what we explored / what we learned** triad.

---

## 2. CAPTURE → the verify-build findings buffer

**Question posed: is verify-build's buffer already a superset of what the HTML report needs?**

**Answer: it is a superset for the *evidence + verdict* layer, and a complete blank for the *rationale + human-questions* layer.** The HTML report health-tracker actually opens before merge needs both. Concretely:

### Already covered (no change needed)
The buffer (`lib/findings-schema.json`, `schema_version 1.0`) already carries everything the *evidence* half of the report needs:

- `criteria[].text` — the criterion (health-tracker: the surface being reviewed).
- `criteria[].adversarial_cases[]` — the adversarial cases pane.
- `criteria[].observations[]` with a `type` discriminator (`screenshot | a11y_snapshot | network | console | log | stdout | exit_code | narrative`) and `timestamp_offset_ms` — directly maps to health-tracker's "screenshot on the left, what-it-proves on the right," and the timeline ordering the renderer wants.
- `criteria[].verdicts.{correctness,regression,scope-creep}` each with **exactly-2-citation** `evidence` + `notes` — maps to the per-dimension PASS/FAIL/Unknown verdict.
- `not_tested[]` — the closing "what we did NOT test" checklist, already closed-form per platform.
- `metadata.platform_hint` — abstracts away iOS/web/etc. so the renderer (and the capture layer) stay project-agnostic.

This validates the PR Q forward-compat call: the evidence buffer **is** a superset and needs **no migration** for the evidence panes.

### The two gaps (additive fields — `schema_version` stays `1.0` per the schema's own additive-vs-breaking rule)

1. **Grounding / rationale is absent.** verify-build judges *correctness/regression/scope-creep* — it never captures *why a visual looks the way it does*. health-tracker's whole north star is that column. Proposed additive field, per criterion:

   ```jsonc
   "grounding": {
     "type": "need | design-language | craft-commitment | open-question",
     "statement": "one-line rationale",
     "citations": ["<resolved from config: specPath/designLanguagePath/plan Spec-walk>", "..."],
     "decision_test": "optional — the named test run in-annotation, with its result"
   }
   ```
   `open-question` here is the bridge to gap 2. This field is how **FB-0040** ('rationale carried') + **FB-0037** ('designer-lens') get operationalized into the buffer — the one column verify-build lacks today.

2. **Human-facing subjective questions are absent — and distinct from `Unknown`.** A `verdicts.*.verdict = "Unknown"` is *epistemic* ("I couldn't exercise this path"). A health-tracker **question** is *subjective* ("this is a taste/priority call only you should make"). They are not the same and must not be collapsed. Proposed additive **top-level** field:

   ```jsonc
   "open_questions": [{
     "question": "specific, answerable, with options",
     "rationale": "our view + why",
     "recommended_default": "keeps the loop moving if half-glancing",
     "user_need_lens": "which job/persona it's about",
     "routing": "this-iteration | future-planning"
   }]
   ```
   `this-iteration` is the mechanical hook the gate needs (§ 5): a present `this-iteration` question is a **blocker on auto-advance** until the human answers, mirroring an unresolved MEDIUM assumption in `workflow.md` Step 8.

Both are additive object/array fields → existing consumers (ship Step 4a, evals) ignore them; `schema_version` does not bump. **Caveat (FB-0003 schema-without-implementation):** do not land these slots until a producer writes them and a consumer reads them in the same PR.

**Capture depth — the V1→V2 contract, made explicit for implementation.** The buffer's `observations[]` must cover the **full declared `Visual-walk` state set** (#37's V1 plan field — empty / loading / error / interaction / a11y, not just the happy-path look), not only the criteria the judges happened to score. This is what makes the *ephemeral* review genuinely **exhaustive** rather than a thin per-criterion sample. The contract:

- Capture is **driven by the declared `Visual-walk` states** — verify-build (via bundled `/verify`/`/run`, #37's V2) exercises each declared state and writes an observation for it.
- A declared state with **no captured observation is itself a finding**: it renders in the report's "what we did NOT test" list, and its criterion resolves to `Unknown` — which (per § 5) blocks a confident visual PASS / auto-advance. Coverage is therefore *asserted by the renderer against the declared set*, never assumed.
- This is the seam where "the buffer is a superset" stops being free: the *schema* is a superset (§ 2 above), but *exhaustiveness* is a capture-depth requirement that V2 owns. The renderer (V3) can only show what V2 captured.

---

## 3. RENDER → the HTML case-study report (roadmap O8)

The report is **the file the human opens before clicking merge — the human-*feedback* artifact, not a show-and-approve.** Its job is to surface the real decisions and tradeoffs that need human input (the "Open questions for you" block), backed by exhaustive evidence across the full declared state set — so the human's job is *thinking*, not rubber-stamping (FB-0040). Structure, synthesized from both health-tracker HTMLs and driven entirely off the buffer:

```
┌ Hero ─────────────────────────────────────────────────────────┐
│ eyebrow (project · branch · short-sha) · H1 · lede             │
│ verdict pills:  overall_verdict · exit_code · budget_used      │  ← metadata.*
├ Legend ("how a verdict / a choice earns its place") ───────────┤
│ PASS · FAIL · Unknown chips  +  need/design-language/craft/Q   │
├ TOC ──────────────────────── one entry per criterion ──────────┤
├ Per-criterion section (article) ───────────────────────────────┤
│  • criterion text  (criteria[].text)                           │
│  • grounding callout  (criteria[].grounding — § 2 gap 1)       │
│  • evidence block: screenshots / a11y-tree / network / console │
│      laid out on a timeline (observations[].type + offset_ms)  │
│  • adversarial cases pane  (adversarial_cases[])               │
│  • per-dimension verdict cards: PASS/FAIL/Unknown +            │
│      the two-citation evidence verbatim  (verdicts.*)          │
├ "Open questions for you" (standalone, numbered) ───────────────┤
│  each: question · recommended default · user-need lens ·       │
│        [this iteration] / [future planning]  (open_questions)  │
├ "What we did NOT test" checklist  (not_tested[]) ──────────────┤
└ Footer: branch state · next steps ─────────────────────────────┘
```

Design rules carried over from health-tracker, made generic:

- **What-it-proves, not what-it-is**, on every evidence item (the renderer can't write this; the agent supplies it as the observation's narrative companion — another reason `narrative` is a first-class observation `type`).
- **Questions collected, not buried** — a standalone block, so the human answers them as a set rather than meeting rhetorical questions inside annotations.
- **Self-contained** — base64-inline the screenshots (health-tracker's resize-before-encode discipline: ~460–620px wide, not 2.5 MB retina PNGs, and never paste base64 into the working context).
- **Ephemeral by default** — write to a temp/desktop path, *not* the repo (see § 4). This is the cost-aware lever: the heavy artifact never bloats the tree.
- **Cover the full declared state set.** Every `Visual-walk` assertion (#37 V1) gets either an evidence item or an explicit "not captured" line. The report makes its own coverage legible against the declared set, so "exhaustive" is *verifiable*, not assumed — and an uncaptured declared state visibly drives back to V2 capture rather than silently disappearing.

A renderer is a stdlib-only Python script reading the buffer JSON and emitting one HTML file — no new dependency (quality bar). It needs a `dev-docs/design-language.md` for the report itself (report typography, PASS/FAIL/Unknown semantic colors, timeline conventions) — already flagged in `plan.md` item 10.

---

## 4. DOCUMENT / RATIONALE → the north star + the feedback pipeline

health-tracker's FB-0006 is the north star Flow should adopt: **the review exists to make the human's job *thinking*, not *approving*.** Three pieces, mapped to Flow:

1. **Assumptions explicit** → `not_tested[]` (shipped) + `Unknown` verdicts with their honest notes (shipped).
2. **Subjective questions surfaced** → the `open_questions` field (§ 2 gap 2) rendered as the standalone block (§ 3).
3. **Rationale carried** → the `grounding` field (§ 2 gap 1).

### The two artifacts, as a contract pair (implementation-ready)

The model is **two co-equal artifacts**, not one durable record with the review as an afterthought. The ephemeral review is the human-feedback surface; the durable record is the catalogue of what came out of those cycles. Both must be built; they have distinct contracts:

| | **Ephemeral review report** | **Durable visual record** |
|---|---|---|
| Path / slot | `verifyReportPath` (temp; **not committed**) | `visualHistoryPath` → `visual-history.html` (**committed**) |
| Lifecycle | per run; **regenerated every iteration**; discarded after merge | append-only; grows over the project's life |
| Scope | **exhaustive** — every `observations[]` item across the full declared `Visual-walk` state set | **curated** — only decisions that changed the user's read; one entry per significant decision |
| Decisions/tradeoffs for human input | **yes — the "Open questions for you" block** (`open_questions[]`: question + rationale + recommended default + user-need lens + routing). This is the feedback ask. | the *resolved* outcome of those questions, carried as "questions carried forward" |
| Produced by | the **O8/V3 renderer**, from the buffer | **distilled at `/flow:ship`** from the ephemeral report (curated/authored, not auto-rendered) |
| Screenshots | base64-inlined (self-contained) | lean asset refs in `visual-history-assets/`; CSS/SVG reconstruction fallback |
| Consumer | the **human at the merge gate** (gives feedback; a `this-iteration` answer re-enters Execute) | future sessions/phases + the human (lineage) |
| FB anchor | the O8 entry / Deliverable-quality track **V3** (#37 FB-0041) | **FB-0042** |

The **distill step is the bridge**: at `/flow:ship`, the load-bearing visual decisions in that run's ephemeral report (the `grounding` entries that changed the user's read, plus any `open_questions` the human resolved `this-iteration`) become **one** curated `visual-history.html` entry; then the ephemeral report is discarded. Implementing V3 means building *both* ends plus this bridge — not just the renderer.

**Feedback-pipeline integration (the persistence half).** ship Step 4a already reads the buffer and, for each `FAIL/Unknown` criterion, derives a candidate `FB-XXXX` whose "What was said" cites the criterion + evidence quotes, leaving the synthesized rule for the human (Step 4a "does not invent prose for FB entries"). Two extensions:

- Step 4a should also derive candidates from `open_questions[routing = this-iteration]` that the human answered with a correction — that *is* a user correction, the canonical FB source.
- **The two-tier persistence: SETTLED — Flow ships a durable `visual-history.html` (FB-0042, reversing this section's original "skip it"; reconciled to merged health-tracker #10).** The per-run report is ephemeral; without a durable target the *decision-making* in each report dies (the "nothing reads the per-run artifacts back" gap the roadmap's "Cross-run aggregation" entry names). #10 is the reference implementation — and it corrects two details of the original sketch:
  - **Two artifacts, never conflated.** Ephemeral report (exhaustive evidence, opened at the merge gate, discarded) **feeds** the durable record (curated subset, committed) via a distill step at `/flow:ship`. ✓ unchanged.
  - **A single curated `visual-history.html`, the picture companion to the existing `historyPath` core doc** — *not* a new `.md`, *not* a `.md`+`.html` pair. #10 has no separate `.md`; the written timeline is already `history.md`. (Corrects the earlier "doc pair" sketch.)
  - **Lean committed screenshot assets, not schematic/screenshot-free.** Real captures preferred — resized keepers on relative paths in `visual-history-assets/`; a CSS/SVG reconstruction is the *honest fallback* when capture isn't available (e.g. a no-simulator container). Not base64-embedded. (Corrects the earlier "schematic, zero PNGs" rule — #10 commits lean JPEGs; repo-health was the real intent, and lean assets serve it better.)
  - **Curated + decision-centric, reverse-chronological, no italic headings, anchor-link TOC** (#10's conventions, FB-0006/FB-0007). **`uiSurface`-gated, opt-in** (FB-0007) — non-UI consumers don't get an empty doc.

  New slot `visualHistoryPath` (companion to `historyPath`); citations resolve from `specPath` / `designLanguagePath` (no hardcoded project doc names). Don't land slot + template until producer + `/flow:ship` consumer ship together (FB-0003). Full shape: **FB-0042**.

---

## 5. GATE PLACEMENT → segment-bounded (FB-0035), no third gate

This is the cleanest mapping and needs no new doctrine — health-tracker's flow already *is* FB-0035:

- **Discovery + iteration happen at Present (Step 8/9), before the ship decision.** health-tracker: the review is produced at Present; a `[this iteration]` "this is wrong" re-enters Execute (fix → re-run preflight → **re-render the review proving the fix** → re-confirm → *then* ship). Flow: identical to FB-0035's "anything that can produce *iteration* runs before the ship decision."
- **The authoritative human look folds into the existing merge gate.** The HTML report is the file opened before clicking merge — it does not introduce a human stop of its own. This is FB-0035 verbatim: "visual sign-off folds into the merge gate … never a third human gate."
- **A workflow owns the fan-out *between* gates, never across one.** The capture→render→present arc lives entirely inside the Plan-approval → Merge segment. (This is the doctrine the task calls "segment-bounded / O4.")
- **The mechanical hook:** an unanswered `open_questions[routing = this-iteration]` blocks Step 8 auto-advance, exactly as an unresolved MEDIUM assumption does today (`workflow.md` Step 8). A `FAIL`/non-converging-`Unknown` at ship's confirmation re-run routes to a **draft PR + manifest** (FB-0034) — the escalation lands *in* the merge gate, never as a new one.

No change to the two-gate model. The report is an *artifact* of the merge gate, not a gate.

---

## 6. GENERIC vs PROJECT-SPECIFIC — the de-tokenization ledger

Flow artifacts must carry **zero** project-specific tokens (quality bar). Everything health-tracker-shaped that must be stripped or config-sourced before it can live in a Flow artifact:

| health-tracker token / assumption | Why it can't ship in Flow | Generic Flow form |
|---|---|---|
| `xcrun simctl`, `xcodebuild`, `iPhone 17`, `DerivedData`, `com.healthtracker.app`, `ContentView.swift`, `.xcresult`, gallery-swap | iOS/Xcode capture recipe | **Don't reimplement.** Capture is delegated to bundled `/verify` + `/run` (per FB-0015 — never wrap a bundled skill). `metadata.platform_hint` already abstracts the platform. |
| "warm cream", "sage / clay / gold", per-mode diurnal gradient, `Geist Mono` | project brand palette/typography | Renderer ships a **neutral default theme**; optional theming via a config slot or the project's own tokens. Zero brand tokens in the artifact. |
| `user-needs.md §3.1/§3.3/§3.6`, `§7` decision tests (seconds/voice/trust/persona), `decisions/design-language.md`, `craft/case-study.html`, `D1–D5`, "craft commitment" | health-tracker doc structure + product vocabulary | The `grounding.citations` resolve from **config slots** (`specPath`, `designLanguagePath`) + the plan's `**Spec-walk:**`. The *concept* (rationale-type tag + citation) is generic; the *targets* come from `flow.config.json`. "Craft commitment" generalizes to "a stated design stance"; keep the rationale-type enum, drop the project word if it reads as branded. |
| `visual-history.md` / `VH-IDs`, `design-review-lessons.md` / `L4.x`, health-tracker `FB-0004`/`FB-0005`/`FB-0006` | project doc names + IDs | Persistence via Flow's **feedback pipeline + roadmap** (§ 4). No generic `visual-history` artifact unless a consumer opts in by slot. |
| `~/Desktop/<feature>-review.html` | macOS path | `verifyFindingsPath`-adjacent slot (e.g. a `verifyReportPath`, default a temp dir) — same pattern as the existing buffer path slot. |

The two tags health-tracker uses — `[this iteration]` / `[future planning]` — **are** generic and map cleanly onto Flow's "re-enter Execute" + "route to roadmap" doctrine. Keep them.

---

## 7. What folds where (the concrete spec, offered — not yet applied)

If the user approves, this blueprint folds into existing surfaces as follows. **Nothing below is applied yet** beyond this research doc:

1. **`roadmap.md` O8 entry → applied.** Concretized vision → spec (the two additive buffer fields, the renderer + report structure, the `verifyReportPath` slot, FB-0035 gate placement), and **reframed as V3 of #37's "Deliverable-quality track."**
2. **`dev-docs/research/` cross-link → applied.** This doc is the analysis; the roadmap O8 entry is the spec. (The umbrella `dynamic-workflows-alignment-2026-06.md` now exists — it merged via #35 — and this blueprint is its O8 / FB-0039(b) deep-dive.)
3. **FB-0042 — captured & reconciled.** Drafted 2026-06-04 as FB-0041; **renumbered → FB-0042 on 2026-06-05** to resolve a collision with #37's FB-0041 (the autonomous-deliverable umbrella). FB-0042 is the durable-record decision, serving FB-0040 + #37/FB-0041, aligned to merged #10.

### Resolved with the user
- **Durable visual record: SHIP it** (reversed from the earlier "skip"). As an **opt-in, uiSurface-gated** single curated `visual-history.html` — the picture companion to the existing `historyPath` core doc, with **lean committed screenshot assets + CSS/SVG reconstruction fallback** (corrected from "schematic/screenshot-free" to match merged #10). See FB-0042 + § 4.
- **FB numbering:** **FB-0042** (mine renumbered to cede 0041 to #37's umbrella). 0037–0040 are #35's; 0041 is #37's; 0042 is this.
- **#36 ↔ #37 reconciliation:** they are one pipeline — #37 = V1 `Visual-walk` (declared criteria, the input) + the umbrella; #36 = V2/V3 (capture fields + renderer) + the durable record. The O8 entry is now explicitly V3 of #37's track.

### Tightened for implementation (2026-06-05)
- **Ephemeral review pinned co-equal** to the durable record — its human-feedback purpose ("open questions for you" = decisions/tradeoffs needing input) is stated in § 3 + § 4's contract-pair table + FB-0042(a).
- **Capture depth is now an explicit V1→V2 contract** (§ 2, § 3, roadmap V2): the ephemeral report must cover the full declared `Visual-walk` state set; an uncaptured declared state is a finding (`Unknown` + "not tested"), never a silent gap.
- **Per-PR acceptance criteria** added to the roadmap — **PR-1** = track V2 (capture) + V3a (renderer), coupled by FB-0003; **PR-2** = track V3b (durable record) — so the track is build-ready.

### Still open
- **Capture additive fields (`grounding`, `open_questions`) now or after a UI-bearing dogfood?** FB-0016: prove on a UI surface (health-tracker is the available fixture) before declaring the shape stable.
- **Residual #36/#37 textual overlap** in `roadmap.md` / `history.md` / `reserved-feedback-numbers.md`: both edit the O8 entry and append entries. The FB-number collision is resolved (0042 vs 0041); whichever PR merges second resolves the remaining textual conflict toward the reconciled state recorded here + in the history entry.
