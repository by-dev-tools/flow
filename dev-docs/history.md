# History

Detailed record of shipped work. Reverse chronological (newest first). This is not a changelog -- it captures the **why**, **tradeoffs**, and **decisions** behind each change so future sessions have full context on how the project evolved.

---

## How to Write an Entry

```
### [Short title of what was shipped]
**Date:** YYYY-MM-DD
**Branch:** branch-name
**Commit:** [SHA or range]

**What was done:**
[Concrete deliverables -- what changed in user-facing terms.]

**Why:**
[The problem this solved or the goal it served.]

**Design decisions:**
- [UX or product choice + reasoning]

**Technical decisions:**
- [Implementation choice + reasoning]

**Tradeoffs discussed:**
- [Option A vs Option B -- why this one won]

**Lessons learned:**
- [What didn't work, what did, what to do differently]
```

Use the `SAFETY` marker on any entry that modifies error handling, persistence, data loss prevention, or fallback behavior.

---

## Entries

<!-- Add new entries below this line, newest first. -->

### Route two post-V3b follow-ups from the health-tracker cold-run pre-check (docs-only)
**Date:** 2026-06-16
**Branch:** claude/v3b-followups
**Commit:** [this PR]

**What was done:**
Captured two findings surfaced while prepping the FB-0016 health-tracker (iOS) cold-run that validates V3b's §5c distill step, as `dev-docs/roadmap.md` entries: (1) a roadmap-concrete item in the "V3b durable-record follow-ups" bundle — `insert-visual-history.py` keys on the skeleton's marker comments, so a consumer pointing `visualHistoryPath` at a *pre-existing, hand-authored* `visual-history.html` (health-tracker's `craft/visual-history.html`, the #10 reference) gets a fail-loud, not an adoption; they must use a fresh path. (2) a § Exploration entry — installed-plugin-version currency: the pre-check found the user-level flow install cached at v1.5.1 while `main` was v1.8.0, so a ship would run stale prose until `/plugin marketplace update`; nothing surfaces "your install is behind `main`."

**Why:**
The cold-run pre-check is the first time V3b met a real consumer's filesystem. Both findings are real friction a future session will hit; routing them to the roadmap (not just a chat message) is the canonical capture per the workflow's follow-up discipline.

**Design decisions:**
- The markerless-adoption finding is roadmap-concrete (it has a shape: `--migrate` mode / clearer diagnostic / document-the-constraint), so it lives in the V3b follow-ups bundle, not § Exploration.
- The version-currency finding has no clean shape yet (needs a "latest" reference + a non-annoying cadence; `autoUpdate` is the blunt alternative), so it's § Exploration with a `Surfaces when:` trigger on `/flow:doctor` / `docs/upgrade.md`.

**Tradeoffs discussed:**
- Live-confirmed the install-lag this session: even after the user updated the cache to 1.8.0, the running session's skill resolution stayed pinned to 1.5.1 (picks up 1.8.0 on restart) — so the validation cold-run must verify the installed version FIRST, which the health-tracker prompt now does. No code change here — pure routing so the findings aren't lost.

### Durable visual record (`visual-history.html`) + distill bridge — Deliverable-quality track V3b (v1.8.0) — SAFETY
**Date:** 2026-06-16
**Branch:** claude/v3b-visual-history
**Commit:** [this PR]

**What was done:**
Built the durable half of V3 — the committed, curated `visual-history.html` (the *picture* companion to `history.md`) and the distill bridge that fills it. The ephemeral per-run verify-build report (shipped v1.6.1/1.7.0) is regenerated every iteration and discarded; nothing read its decisions back. V3b adds: a `visualHistoryPath` schema slot (23 slots total); a stdlib `skills/ship/lib/insert-visual-history.py` helper + a `visual-history-skeleton.html` lib asset; a `/flow:ship` **Step 5c** distill step that, on UI projects with a load-bearing visual decision in the run's findings buffer, authors ONE curated reverse-chronological entry into `visual-history.html`; a Step 4a extension deriving a candidate FB from a human-corrected this-iteration open question; and `evals/run_visual_history_evals.py` (25 checks). The 22→23 slot-count fan-out was swept across 8 surfaces.

**Why:**
FB-0042 settles the two-artifact model: the ephemeral report is the human-feedback surface; the durable record is the curated catalogue of what came out of those cycles. Without the durable target, the *decision-making* in each report dies (the roadmap's "cross-run aggregation" gap). This completes the V1→V3 chain of the Deliverable-quality track (#37/FB-0041); only V4 (consumer-side proactive-error loop) remains.

**Design decisions:**
- **Agent curates content, helper enforces structure (Fork 1).** Curation — *which* decision is load-bearing — is judgment, so the agent authors the entry's content; the helper renders it into the fixed structure (reverse-chron prepend, anchor-TOC regen, no-italic-headings) so the FB-0042(d) disciplines are mechanical, not author-memory-dependent (the FB-0010 class). Mirrors the existing `render-test-plan.py` / `render-report.py` lib family.
- **Distill source = the findings buffer, not the rendered HTML.** The buffer (`verifyFindingsPath`) carries the structured `grounding` + `open_questions` the report renders from; Step 4a already reads it. Reading structured JSON beats re-parsing HTML. Reconciled in the plan against the blueprint's "from the ephemeral report" wording (same data, more robust path) — not a contract change (plan-critic Finding 2).
- **Heavily gated, curated not dumped.** Most ships skip §5c (explicit reason on `uiSurface:false` / skipped-verify / no-load-bearing-decision). The record holds only decisions that changed the user's read — never a per-PR dump (FB-0042).

**Technical decisions:**
- **SAFETY — created-on-first-write, not bootstrap-scaffolded (FB-0053, reverses FB-0042(e)'s mechanism).** `bootstrap.sh` *creates* `flow.config.json` and globs only `core-docs/*.md` — it runs before config is meaningful and can't read `uiSurface`, so an unconditional scaffold would seed an empty `.html` into non-UI consumers (violating FB-0007). Instead the distill step seeds the file from the bundled lib skeleton on the first qualifying ship. User-approved at the plan gate; FB-0042(e) + the roadmap acceptance updated same-PR (FB-0010 fan-out). Preserves FB-0042(e)'s intent (uiSurface-gated, opt-in, no empty doc).
- **SAFETY — graceful, no partial writes.** `insert-visual-history.py` validates the target's markers + the entry JSON *before* rendering; a malformed target or invalid entry fails loudly and writes nothing (the existing record is never corrupted). Missing title / bad date / absent markers / invalid JSON all exit non-zero with a clear message.
- **Lean committed assets, CSS/SVG reconstruction fallback.** The durable record references resized keeper frames under `visual-history-assets/` (not base64-embedded — that's the ephemeral report's mechanism); an inline CSS/SVG reconstruction is the honest, labelled fallback when capture isn't available (FB-0042(c)).

**Tradeoffs discussed:**
- **Shipping the capability without a live dogfood (Fork 3, FB-0016).** Flow's own repo is `uiSurface:false`/`platform:library` → its ship always self-skips §5c, and per the realistic-demos rule (FB-0052) we did **not** fabricate a `visual-history.html` for a non-visual repo. Correctness is pinned by evals over a synthetic buffer (legitimate test data); the live curated-entry validation is a tracked health-tracker (iOS) follow-up — exactly as #45's iOS cold run was. The entry *shape* is therefore provisional-pending-UI-dogfood (documented in §5c, roadmap, plan, CHANGELOG).
- **Description bloat.** The plugin/marketplace manifest descriptions gained another cumulative sentence (now well past the ~1500-char mark the "CHANGELOG extraction" Later item flags). Followed the established pattern rather than tackling the extraction here (out of scope).

**Lessons learned:**
- Verified PR #36 was docs-only (blueprint + FB-0042 entry, merged 2026-06-08) before building — no `visual-history` implementation existed on main, so V3b was genuinely unbuilt (the FB-0051 parallel-collision check, applied proactively).
- When a governing spec mandates scaffolding at a lifecycle point where the gating config doesn't yet exist, create-on-first-write at the first qualifying pipeline step is the clean resolution — and the mechanism reversal must update the governing FB + every cross-reference in the same PR.

### Two-way annotation layer — click-to-pin review surface on the verify-build report (v1.7.0) — SAFETY
**Date:** 2026-06-15
**Branch:** `claude/ecstatic-lumiere-b027f3`
**Commit:** 339e0d5

**What was done:**
Made the `/flow:verify-build` ephemeral HTML report a **two-way review surface**. `render-report.py` now injects a self-contained click-to-pin annotation overlay (`plugins/flow/skills/verify-build/lib/annotation-layer.html`) before `</body>` whenever the rendered buffer carries ≥1 captured frame, so the human leaves *located* feedback at the merge gate: click a screenshot to drop a pin, type a note, then "Copy notes" emits a structured per-screen block to paste back into the loop. Captured screenshot `<img>` tags gained `class="annot-shot"` so the layer can find and bind to them. Frameless (text-only / pre-capture) reports stay read-only — no toolbar, no overlay. An unreadable layer file warns and renders read-only, never crashes. No new slot, skill, or dependency. Version → v1.7.0.

**Why (SAFETY):** this changes `render-report.py`'s **rendered output** (a published, safety-relevant artifact — the merge-gate report the human trusts) and adds an **injection path** (read a layer file from disk, splice it into the HTML body) with its own read-failure fallback. Both touch the report's rendering + a new graceful-degradation branch, so the entry is SAFETY-marked per `.claude/rules/documentation.md`.

**The pivotal story (re-scope to the additive delta):**
This work began as a *standalone* feature: a new `/flow:walkthrough` skill, its own `annotation-layer.html`, a new `verifyReportPath` slot, the slot/skill-count fan-out, and ship Step-6b auto-invoke wiring — a full PR that passed two rounds of `/flow:staff-review`. At ship time the **stale-base gate caught that PR #45 ("V2/V3a rendered capture + ephemeral HTML walkthrough") had merged to main mid-session**, independently shipping ~70% of the same feature: the V2 capture, the V3a `render-report.py` renderer (read-only), the `verifyReportPath` slot (same name), the `grounding`/`open_questions` buffer fields, and the Step-8 gate. The **only** part #45 lacked was the two-way click-to-pin layer. The user chose to **re-scope (Option A): reset to main, discard the ~60% #45 already shipped, and contribute only the additive delta** — the annotation layer, layered onto #45's `render-report.py`. (Earlier in the same session the stale-base gate also caught PRs #47/#48 adding `/flow:audit-coverage`, forcing a first rebase.) Recorded as FB-0051.

**Design decisions:**
- **Ship the additive delta, not the duplicate.** The annotation layer is the genuinely-novel "two-way" half; everything else #45 already shipped. Building on #45's `render-report.py` (vs a parallel `/flow:walkthrough` skill) avoids two renderers, two slots, two architectures — the anti-duplication bar (FB-0010/FB-0015 lineage).
- **Inject only when a frame rendered** (`'class="annot-shot"' in body`). A text-only / pre-capture report has nothing to annotate, so the toolbar would be noise — frameless reports stay read-only.

**Technical decisions:**
- **Defer image SIZING to `render-report.py`'s own `.obs img` CSS; the layer only sets `display:block`.** An earlier attempt to override the image width inside the layer clobbered #45's `max-width:600px` cap — the body-injected `<style>` wins on equal specificity by source-order — and upscaled small frames.
- **Pin alignment via JS host-width sync, not CSS shrink-wrap.** An `inline-block` / `width:max-content` host wrapping a percentage-width image is a sizing cycle that collapses the box to ~0px; instead `syncHost()` sets `host.style.width` to the image's *measured rendered width* (re-run on resize + on image load). Caught in a real browser — a 320px frame had collapsed to 2px under the CSS-only approach.
- **Graceful injection (SAFETY).** `load_annotation_layer()` reads the layer from a fixed `__file__`-relative path; on read failure it warns and renders the report read-only — never crashes. Matches `render-report.py`'s existing graceful ethos.
- **Grounding / open-questions are NOT re-introduced as agent-authored.** #45 already added them as buffer fields the renderer consumes; the layer just makes the rendered report interactive, it does not re-author the data.

**Tradeoffs discussed:**
- **Standalone `/flow:walkthrough` skill + own renderer vs additive layer on #45's renderer.** The standalone version was already built + staff-reviewed, so "ship what we have" was tempting — but it would conflict with, duplicate, and compete against #45's merged renderer/slot. Re-scoping discarded ~60% of the session's work to avoid shipping a duplicate. The cost (thrown-away work) is exactly what FB-0051 says to pay rather than ship a competing renderer.
- **Override image width in the layer vs defer to the renderer's CSS.** Overriding gave the layer self-containment but clobbered #45's `max-width:600px` cap and upscaled small frames; deferring keeps a single source of truth for sizing at the cost of the layer depending on the renderer's CSS contract (`.obs img`).

**Lessons learned:** FB-0051 — when the stale-base gate (or a rebase) reveals a parallel branch shipped most of a roadmapped feature you're building, STOP and re-scope to the genuinely-additive delta; do not ship a duplicate renderer/skill/slot. CSS sizing for an injected overlay must be validated in a real browser (the 320px→2px collapse was invisible to static review and to the prose contract); pin-alignment is a measured-width JS problem, not a CSS shrink-wrap problem.

### Verify-build report copy-clarity pass (render-report.py) — plain language for the human reader
**Date:** 2026-06-15
**Branch / SHA:** `claude/verify-report-copy-clarity` / c0252a4, rebased onto `main` after #49 merged (v1.7.0); shipped as **v1.7.1**

**What:** A small, copy-only pass on the verify-build HTML report (`render-report.py`) so a human reading it to make the merge decision understands it at a glance. Lede plainer ("This is what the app actually did when we ran it — checked against what the plan asked for — plus the decisions that still need your call."); legend header "How a verdict / a choice earns its place" → "**Legend**" + a one-line gloss explaining the grounding tags; dropped the redundant jargon `verify exit code: N` pill (the Overall pill already encodes pass/fail) and its now-unused `exit_code` param; "N verify calls" → "N verification steps"; observation labels humanized via an `OBS_LABEL` map (`a11y_snapshot` → "Accessibility tree") and `timestamp_offset_ms` rendered as "1.2s in" instead of "+1200ms".

**Why:** User feedback (FB-0052) on the v1.7.0 two-way report demo — *"the copy isn't clear or really understandable."* Most of the unclear copy is the report *shell* (#45's renderer), not the annotation layer; this is the separate, focused follow-up the user chose over bundling it into the annotation PR (#49).

**Design/technical decisions:** (1) **Copy-only, no behavior change** — no buffer-shape, no schema, no logic touched; the renderer's graceful-degradation + security guards are untouched. (2) **Shipped as v1.7.1** — a patch on top of #49's merged v1.7.0; the PR was authored version-neutral *while #49 was still open* (two open PRs both bumping is the exact fan-out collision FB-0051 is about), then bumped at rebase once #49 merged. (3) Did **not** rename the grounding vocabulary (need / design-language / craft-commitment / open-question) — those are the established FB-0040 conceptual tags; glossed them instead of renaming. (4) Updated the one eval assertion (`test_v2_capture_render.py`) that pinned the old legend string.

**Tradeoffs:** Editing another author's just-merged renderer (#45) risks churn, so the pass is deliberately minimal — the genuinely-cryptic chrome only, not a redesign. Left `## Test plan`-style metrics (budget) in but de-jargoned rather than removing, to preserve the evidence trail.

### PR V2 + V3a — Rendered visual capture + ephemeral HTML walkthrough (v1.6.1) — SAFETY
**Date:** 2026-06-11
**Branch:** `claude/v2-rendered-capture`
**Commit:** [PR #45 — behavioral gate GREEN; marked ready, awaiting human merge]

**Cold-gate outcome (2026-06-11):** the flow-true gate — a cold, fresh-agent `/flow:verify-build` run following `§5a`/`§10` literally against health-tracker (iOS, XcodeBuildMCP) — ran in two rounds. **Round 1:** mechanism validated end-to-end (real build/frames/judges; the pairwise judge returned a true FAIL on a drifted frame), but caught **3 substantive `§5a` prose gaps** — (1) no a11y-gate before screenshot (which *caused* a wrong-state capture), (2) "drive to each state" assumed a UI-drive primitive the MCP may lack, (3) state-set derivation undocumented. Fixed in `839c986` (a11y-gated capture ordering, named drive ladder, explicit derivation + graceful degradation, `--assets-dir` alignment) + **FB-0050** + eval assertions; parser + Spec-walk routing fragility routed to V2.1. **Round 2:** GREEN — 6/6 captures a11y-gated, drive ladder honest, baseline second-run resolved a visual criterion to PASS (VLM-pairwise correctly ignored a non-deterministic status-bar clock; byte-`cmp` would have false-FAILed). This is the load-bearing validation FB-0049 demands, and it caught exactly what static tests + the author's hand-driving missed.

**What was done:**
Built the V2 (rendered capture) + V3a (ephemeral HTML walkthrough) link of the Deliverable-quality track for `/flow:verify-build`. `criteria[].grounding` + top-level `open_questions[]` added to the findings schema (additive; `schema_version` stays `1.0`; top-level `required` unchanged). SKILL §5a: flow now **owns capture-and-persist** — drives the platform's screenshot MCP per declared `Visual-walk` state, persists the frame, writes a path-referenced `screenshot` observation + an `a11y_snapshot` (text/status from the a11y tree, not pixels). SKILL §10 + a new stdlib `render-report.py`: the buffer renders to one self-contained ephemeral HTML report (`verifyReportPath` slot) — hero, legend, per-criterion evidence/grounding/verdict cards, a standalone "Open questions for you" block, and a coverage checklist. Rubric re-grounded on pairwise-vs-baseline (no baseline ⇒ Unknown). `open_questions[this-iteration]` blocks Step 8 auto-advance. Version 1.5.2 → 1.6.0; slot count 21 → 22.

**Why (SAFETY):** modifies the verify-build *gate* (a load-bearing safety surface), the findings *schema* (a consumed contract), and adds *frame persistence to disk* (file I/O + base64 inlining of buffer-referenced files) — all three are SAFETY-marked per `.claude/rules/documentation.md`.

**Design decisions:**
- **iOS-first, not web (mid-flight correction).** The roadmap/SV2 carried a "web-first against health-tracker" framing; health-tracker is an **iOS/SwiftUI app**, and the renderer's HTML is an *output format*, not the capture platform. Pivoted to capture-via-XcodeBuildMCP; the schema/renderer/gate/rubric stayed platform-agnostic (only the screenshot-drive seam is platform-specific). The Chrome-MCP "no path" persist risk (SV2) **dissolved** — XcodeBuildMCP returns a native, pre-optimized frame path.
- **Branch B (capture-and-persist owned by flow), per SV2.** Bundled `/verify` narrates frames to the judges; flow drives + persists them itself.
- **Stdlib renderer, honest-by-passthrough.** No new dependency; resize is the capture step's job; coverage is established by §5a's `not_tested` writes, not enforced by the renderer (corrected an overclaim at staff-review).

**Technical decisions:**
- Additive schema (no migration); `verifyReportPath` slot (default ephemeral temp path).
- Path-traversal hardening + raster-data-URI allowlist in the renderer (security-review).
- 6-assert contract eval fixture pins schema↔example↔renderer↔SKILL↔rubric↔workflow + the data-URI allowlist.

**Tradeoffs discussed (the load-bearing one — FB-0049):**
- **Validation depth: ship now vs do the flow-true behavioral gate.** Phase 0 + the capture→render chain were validated **live on iOS** (built+ran HealthTracker on the sim, real frame → real 41KB report). But the user's question — *"which is more true to flow's intention?"* — established that the rigorous gate is the **skill-driven** `/flow:verify-build` run (ideally cold), not static contract tests + hand-driven mechanism (which is the Potemkin self-validation verify-build exists to catch). That cold run is **session-bound to a health-tracker context**, so per FB-0034 this PR **opens as a DRAFT** with the behavioral gate in the NOT-READY manifest — discovery-before-merge preserved, no merge-ready PR on an unconfirmed gate.

**Lessons learned:** FB-0049 (a verification tool isn't validated until it RUNS against a real surface; don't conflate output-format with capture-platform). Staff-review caught a slot-count fan-out BLOCKER (flow's own doctor Check 2.5 would have flagged it) — grep-first discipline (FB-0010) applies to every count change.


### Docs-currency sweep — refresh the v1.6.0 handoff for a cold agent
**Date:** 2026-06-11
**Branch:** claude/docs-currency-v160-handoff (docs-only; SHA at commit time)

**What was done:** After PR TP (#46) + PR-2 (#47) merged, the plan's "Handoff Notes" + a few roadmap/plan cold-reader lines were stale: Handoff still read "v1.5.2" and listed the now-shipped PR-TP/PR-2 as "queued/staged", and several `this PR` references dangled post-merge. Refreshed Handoff to v1.6.0 + "Recently shipped (enforce-pair DONE)", and de-`this PR`'d the § Now / ▶ Next-up / Current Focus lines so a fresh agent lands on **▶ V2** cleanly (with the vacuous-criterion residual in roadmap § Next).

**Why / lesson:** This is the cleanup `/flow:ship` Step 5a (doc-currency reconciliation, shipped v1.5.2) does automatically — but the **dogfood install is flow 1.5.1**, which predates it, so the auto-sweep never ran across PR-TP + PR-2 and the staleness accumulated. Until the dogfood install updates to ≥ v1.5.2, forward-doc currency must be reconciled by hand at ship (or in a follow-up sweep like this). No code; reviewers + verify-build self-skipped (docs-only / platform library); no version bump.

### PR-2 — `/flow:audit-coverage`: close under-declaration (coverage audit) — `SAFETY`
**Date:** 2026-06-11
**Branch:** claude/flow-coverage-audit-fb0048 (v1.6.0; SHA at commit time)
**FB:** FB-0048 (this PR). Continues FB-0047 (PR TP). Roadmap follow-up filed: vacuous-criterion check.

**What was done:** New `/flow:audit-coverage` reviewer (13th user-visible skill) that closes the under-declaration hole PR-TP's Test-plan render left: it compares the workspace source diff against the declared `**Spec-walk:**` criteria and flags **user-perceptible behavior changes no criterion covers** — a behavior `/flow:verify-build` never tested, so the rendered Test plan would be honestly all-green while the change ships unverified. Each gap → `[decision-required]` → the existing draft manifest → the PR is mechanically NOT-READY until the criterion is declared + verified (re-run verify-build) or the human waives it. Wired in as the 4th `/flow:ship` Step 2 final-pass reviewer + at the Step 8 readiness boundary. v1.5.3→v1.6.0.

**Why:** FB-0047 made *declared* verification unforgeable; the residual hole was *completeness* — an agent omits a criterion for a behavior it changed and it ships unverified. The load-bearing other half of "enforce that the work was done correctly" (FB-0048).

**Design decisions:**
- **Reuse the `auditor` agent + add ONE category** ("Undeclared change", coverage mode only) — not a new agent. Follows the existing mode-selected-category-subset pattern (audit-plan → assumption+recall; audit-completion → diagnosis+completion+recall), avoiding duplication of the ~80 lines of safety-critical disprove/output discipline (FB-0010 fan-out). Coverage's evidence base is the diff + declared criteria (via reused `extract-criteria.py`), NOT the session transcript the other auditor modes use.
- **Surface → draft, not hard-gate, not auto-fix** (FB-0012: never hard-gate / iterate on LLM judgment; FB-0047: the agent declaring its own criterion would be grading its own homework — resolution routes through the gate). Runs on **all platforms** (under-declaration isn't platform-specific — unlike verify-build, does not skip on `platform: library|none`); self-skips on doc/test/refactor-only diffs or no Spec-walk.

**Technical decisions / SAFETY:**
- **`SAFETY` — `auditor.md` (reviewer prompt) + ship Step 2 (pipeline).** New category gated firmly to coverage mode (header parenthetical + the SKILL's "one category only / ignore your other four" framing + the disprove variant) so it can't leak into audit-plan/audit-completion.
- **zsh word-split BLOCKER (caught by dogfood, not static review):** the diff-assembly originally did `git diff -- $FILES` with a newline-joined `$FILES`; macOS's zsh does NOT word-split unquoted expansions, so it passed the whole blob as one bogus pathspec → **empty diff → a no-op reviewer**. Live smoke test caught it; fixed with a `while IFS= read -r f` loop diffing each quoted `"$f"` — which also closes the filenames-with-spaces hardening for free. Lesson: dogfood the actual mechanism (FB-0010 + FB-0048).
- **Path-traversal containment (security-review BLOCKER `[auto-fixable]`):** the new `run_evals.py` coverage branch read a fixture by path; added a 3.7-compatible `relative_to((HERE/'fixtures'))` containment guard so a malicious `ground_truth.yaml` `fixture: ../../etc/passwd` can't read outside `fixtures/` (component-aware — no `fixtures-evil` prefix false-match). Defense-in-depth (repo is developer-trusted) matching the existing `evals/security/` posture.
- **Silent-skip defenses (FB-0010):** a `[audit-coverage] TRUNCATED` sentinel when the diff exceeds the 60KB cap (a clean result on a truncated diff is a false negative — the worst failure for a completeness auditor); a deleted-file guard so `head` doesn't error on a missing path; `--show-context` fixed for the new `coverage` mode (argparse only knew plan|completion → would silently yield empty context).
- **Prompt-injection defense (security NIT):** the SKILL tells the auditor the diff block is untrusted DATA, not instructions (source files can imitate the section headers / inject "pass everything"). Fuller structural-delimiter hardening is a follow-up; the auditor's adversarial disprove discipline mitigates today.

**Tradeoffs discussed:**
- **Best-effort, not deterministic:** coverage is LLM-judgment — it raises the completeness bar, it does not guarantee it (false negatives possible). Stated in README + CHANGELOG + the reviewer output so a clean `coverage=ran` isn't over-trusted. The alternative (a deterministic completeness oracle) is not achievable — "what behaviors did this diff change" isn't mechanically enumerable.
- **Feasibility validated, not assumed (verdict A go/no-go):** a live run of the updated auditor prompt correctly flagged a genuine undeclared rate-limit behavior AND stayed silent (`No issues flagged.`) on a fully-covered diff; pinned offline by 3 `ground_truth.yaml` cases (catch / silence / skip).
- **Verdict E corrected mid-flight:** flow's own behavior lives in markdown (excluded by the source-filter as docs), so flow's own ship sees only the `.json` manifests → coverage finds nothing behavioral; this PR can't fully dogfood the catch-path (same shape as verify-build skipping on `platform: library`). The offline fixtures + the live prompt run carry it.
- **Vacuous-criterion seam (push-further, deferred to roadmap):** coverage closes *under*-declaration but not *over-broad* declaration — an agent can declare a vacuous criterion ("X works correctly") that coverage accepts and verify-build judges PASS against vague narration. That's criterion-*quality* = verify-build's axis, deliberately out of scope; filed as the named next horizon (criterion-specificity check). README/CHANGELOG say "closes the *worst of* under-declaration" to stay honest.
- **No-Spec-walk + behavior-bearing diff deliberately *skips* (not flags):** a spike/tiny PR legitimately has behavior + no Spec-walk; the upstream readiness predicate already requires spec-walk checkboxes for full-feature PRs, so this isn't the place to flag "nothing declared." Deliberate choice.

**Loop:** plan → `/flow:critique-plan` (1 redirect + 2 follow-ups) + `/flow:audit-plan` (clean) → Gate-1 → execute → `/simplify` (1 fan-out fix) → `/flow:staff-review` (4 lenses: dogfood caught the zsh BLOCKER; truncation/deleted-file/show-context fixes; vacuous-criterion → roadmap) → `/flow:ship` (security-review caught + fixed the path-traversal BLOCKER; a11y + verify-build self-skipped; audit-coverage not yet in the installed 1.5.1 cache so it didn't self-run).

### PR TP — PR `## Test plan` rendered from the verify-build findings buffer (non-forgeable) — `SAFETY`
**Date:** 2026-06-11
**Branch:** claude/lucid-driscoll-20ef29 (v1.5.3; SHA at commit time)
**FB:** FB-0047 (this PR). Staged follow-up: FB-0048 (PR-2, under-declaration coverage).

**What was done:** Replaced the hand-authored `## Test plan` placeholder (`- [ ] <how to verify>`) in the `/flow:ship` PR body with a mechanical render from the `/flow:verify-build` findings buffer. New `plugins/flow/skills/ship/lib/render-test-plan.py` (stdlib) reads the buffer JSON and emits the section: a one-line headline verdict (`✅ N/N declared criteria passed — confirm and merge` / `⚠️ M/N passed; K unresolved`), one line per criterion whose **checkbox state is the buffer's `aggregated_verdict`** (PASS→`[x]` + evidence; FAIL/Unknown→`[ ]` + the judge's reason), and the `not_tested[]` residue as plain bullets. Ship Step 7 runs it and pastes stdout verbatim. Honest fallback for skip / no-buffer / **stale** (buffer branch+sha ≠ HEAD) / malformed → `⚠️ no behavioral gate ran (<reason>); manual verification required`. Eval harness `evals/run_render_evals.py` (12 cases) + 6 fixtures. v1.5.2→v1.5.3 (manifests + CHANGELOG); fan-out swept (`workflow.md`, README, dogfood `.claude/skills/ship`).

**Why:** The unchecked `- [ ]` boxes arriving at the merge gate were either no-signal (empty) or, if hand-checked, self-report — the Potemkin class verify-build exists to kill (FB-0047). For "human confirms testing was done, then quick-merges" to hold, the green signal must be a mechanical function of an adversarial judge's verdict, not agent narration.

**Design decisions:**
- **Deterministic script, not agent prose** — makes the section a pure function of the machine buffer (the agent can't selectively check boxes) and golden-testable; matches flow's Python-for-mechanism pattern. (Alternative: format spec in Step-7 prose — lighter, weaker enforcement; rejected.)
- **Scope staged** at Gate-1 (user decision): PR-1 = render (unforgeable + visible); **PR-2 (FB-0048)** = close under-declaration (an agent omitting a Spec-walk criterion for a behavior it changed) by wiring `/flow:audit-completion` coverage into the readiness chain. Render alone makes *declared* verification unforgeable; it does not guarantee completeness — named as a known limitation in README + CHANGELOG.
- **Checkboxes reserved exclusively for machine verdicts** — `not_tested` renders as plain bullets (staff-review + push-further), so a `[ ]` always means exactly one thing: an unverified criterion. (`not_tested.tested` is agent-self-reported, so it must not look like a verdict box.)
- **Distinct from the V3 HTML case-study renderer** (roadmap § Exploration): that's standalone HTML + screenshots sequenced after V2; this renders PR-body markdown from verdict+evidence+not_tested text available today.

**Technical decisions / SAFETY:**
- Ship Step 4a's existing FAIL/Unknown buffer read (FB-synthesis) left **untouched** — the renderer is an additive, separate read (lower-risk than extending Step 4a).
- **Freshness guard (net-new):** a buffer whose `metadata.branch`/`head_sha_short` ≠ current HEAD → fallback, never rendered as current. If the buffer carries an identity but the current branch/sha can't be established (empty git context), fall back rather than silently render a possibly-stale buffer (staff-review: the invariant must not invert).
- **Fail-to-fallback, never crash:** every read/parse/shape error and any exception inside `rendered_block` routes to the fallback with a named stderr reason (FB-0010 silent-skip defense). The caller pastes stdout verbatim, so a crash (empty stdout) would silently break the non-forgeability contract — staff-review BLOCKER, fixed with a try/except + a `malformed.json` eval.
- **Markdown-escape machine-extracted strings** (criterion text, judge notes, not_tested items) so app-under-test content the judge narrates can't inject a link / emphasis / hidden HTML comment into the PR body (security-review BLOCKER `[auto-fixable]`, fixed in-tree + `malicious-content.json` eval). Evidence already used a backtick code-span.

**Tradeoffs discussed:**
- Flow's own repo is `platform: library`, so verify-build self-skips on flow's own ship → **this PR cannot dogfood-behaviorally-verify itself**; its own `## Test plan` renders the fallback, and the eval fixtures/golden assertions ARE the verification. Surfaced up front (verdict F) so the skipped verify-build reads as expected, not a gap. The "behavioral/text" honesty claim describes the *consumer* path, not flow's self-ship (critique-plan incoherence finding, reconciled).
- Attestation is **behavioral/text only**, not visual (bundled `/verify` narrates screenshots to the fresh-context judge rather than handing it pixels; SV2 spike) — rendered-visual judging is Deliverable-quality V2. Stated in README + the rendered attribution so a green Test plan isn't over-trusted.

**Loop:** plan → `/flow:critique-plan` + `/flow:audit-plan` (4 findings, all absorbed) → Gate-1 (scope approved: staged) → execute → `/simplify` (1 cleanup) → `/flow:staff-review` (1 BLOCKER + cheap NITs fixed inline: malformed-crash, freshness-inversion, not_tested-checkbox-collision, headline, empty-criteria/no-notes honesty, backtick-safe evidence) → `/flow:ship` (security-review caught + fixed the markdown-injection BLOCKER; a11y + verify-build self-skipped).

### Direction capture — agentic-iteration doctrine + plan-gate quality lenses (FB-0044/0045/0046)
**Date:** 2026-06-09
**Branch:** claude/happy-gates-b3cf0c
**Commit:** [this PR]

**What was done:**
Docs-only direction-capture from a design conversation about composing flow with two now-GA Claude primitives (`/goal`, dynamic workflows) and refining the autonomy loop. Three feedback entries + two roadmap entries:
- **FB-0044** — low confidence during Execute is a signal to *iterate*, not stop: the agent iterates against the plan's success criteria + craft bar until the design is genuinely good, then ships; only a genuine *preference fork* escalates. Splits FB-0011's escalation as **quality-gap → iterate** vs **preference-fork → escalate**; reserves stop-before-PR for one-way-doors, otherwise escalation routes into a draft PR (FB-0034).
- **FB-0045** — craft-iteration is a *permitted* judgment-loop under four guards (independent judge + declared criteria + real artifacts + bounded budget/merge backstop), refining FB-0012's correctness-only prohibition on iterate-to-approval. Guard #3 (real artifacts, not narration) is what V2 unlocks.
- **FB-0046** — experience + craft-ambition are first-class plan-gate quality gates: add a product-designer/experience lens + a push-further-on-quality (not scope) lens alongside the auditor + plan-critic. Corrects an earlier (wrong) dismissal of a plan-stage experience lens.
- **roadmap.md** — "Agentic-iteration doctrine" entry in the Deliverable-quality track (after V2, its precondition) + "Plan-gate quality lenses" entry under § Next (independent of the V-track).

**Why:**
The user's target loop: human approves a self-critiqued plan → agent executes, reviews, and *iterates against a strong craft/experience bar* autonomously → ships what it thinks is final (PR + eventual HTML walkthrough) → human merges or feeds back. The two load-bearing human gates (plan, merge) are preserved; the not-confident case must resolve by iteration, never a premature stop or draft. Capturing the doctrine before V2/V3 land so the implementation inherits it.

**Design decisions:**
- One FB per distinct rule, following the FB-0037 precedent (a lens-set bundles into one entry) — so FB-0046 carries both plan-gate lenses while FB-0044/0045 stay separate (loop behavior vs FB-0012 doctrine).
- Roadmap split: the iteration doctrine sequences against V2 (real-artifact dependency); the plan-gate lenses are V2-independent and can land anytime → placed in § Next, not the V-track.

**Technical decisions:**
- Direction-capture only — no plugin artifacts, no version bump (stays v1.5.2). FB numbers claimed via the reserved-numbers protocol (FB-0044/0045/0046), cleared at this ship.

**Tradeoffs discussed:**
- `/goal` vs a script-based Stop hook as the autonomous-convergence driver: the Stop hook is FB-0012-pure (deterministic on the verify-build exit code) and shippable in `default-hooks.json`; `/goal` is the ad-hoc, hooks-gated end-user alternative. Captured as direction, not yet built.

**Lessons learned:**
- The repo's research docs predate `/goal` (a real primitive, v2.1.139+) and call dynamic workflows "research preview" though they're now GA — flagged the stale `roadmap.md:242` line for a future touch. Flow's FB-0041 north-star nearly restates what `/goal` does natively; the design lesson is to compose with the primitive, not reinvent it in prose.

### SV2-spike handoff clarity — wire the resolved capture mechanism into the V2 acceptance checklist
**Date:** 2026-06-08
**Branch:** `claude/v2-handoff-clarity`
**Commit:** (this PR; squash SHA at merge) — base `f5d01cf`

**What was done:**
Tightened two `dev-docs` surfaces so a cold agent picking up V2 in a fresh session inherits the SV2-spike's conclusion without re-deriving it. (1) `roadmap.md`'s "PR-1 — track V2 (capture) + V3a" acceptance checklist: the capture checkbox previously read *"verify-build (via bundled `/verify`/`/run`) … writes an `observations[]` entry per state,"* wording that predates the spike and implies `/verify` captures structurally on its own. Rewrote it to name the **capture-and-persist** step explicitly (orchestrator drives the browser-MCP screenshot → persists each frame to a flow-controlled path → path-referenced `observations[]` entry; bundled `/verify` narrates to the orchestrator but does not hand frames to the fresh-context judges; read text from the a11y tree). (2) `plan.md` Handoff Notes: added a precise "▶ V2 handoff" pointer naming the read-order (roadmap ▶ Next-up → V2 § → PR-1 block → `history.md` SV2-spike) so the next session's first doc routes it to the spec. Docs-only; no `plugins/flow/*` change, no version bump.

**Why:**
The SV2 spike resolved the screenshot-structure question and recorded it in the roadmap ▶ Next-up + V2 § + the history entry — but the *acceptance checklist* a V2 agent turns into a spec-walk still carried the pre-spike wording. That's the FB-0010 fan-out class (a contract resolved in the narrative but not in every downstream reference) applied to a spike→feature handoff: an agent following the checklist rather than the prose would have been misled into assuming `/verify` produces structured frames. Closing it before archiving this workspace, per the user's "make sure docs are updated — we'll give this to another agent in a new session" direction (an application of FB-0043 doc-currency).

**Design decisions:**
- **Tighten the checklist, not just the prose.** The V2 § already carried the resolved mechanism; the gap was specifically the PR-1 checkbox. Fixed the exact line a cold agent acts on rather than adding more narrative.
- **No new FB-XXXX.** The session's direction is an instance of existing FB-0043 (doc-currency) + FB-0010 (fan-out), not a new rule — the quality bar favors a lean feedback corpus over a near-duplicate entry.

**Tradeoffs discussed:**
- **Ship a follow-up PR vs leave the checklist imperfect and archive.** The imperfection was non-blocking (the V2 § corrects it), but the user explicitly chose to fix it from this workspace and accept a short archive delay — a clean handoff is cheap insurance against a cold agent mis-reading the one line it acts on.

**Lessons learned:**
- A spike that resolves a question some downstream **acceptance checklist** depends on should sweep that checklist in the same handoff — not only the narrative that frames it. Same grep-first-edit-second discipline as FB-0010, applied across the spike→feature seam.

### SV2-spike — Does bundled `/verify` return screenshots structurally, or only narrate them? (Deliverable-quality track V2 prerequisite)
**Date:** 2026-06-08
**Branch:** `claude/recursing-mendeleev-41df4c`
**Commit:** (this spike PR; squash SHA at merge) — base `8eb867f`
**Mode:** spike (disposable; deliverable = this entry). No `plugins/flow/*` change, no schema change, no version bump.

**The question (from `verify-build/lib/rubric.md:68` + `SKILL.md:56-64`):** does bundled `/verify` return screenshots **structurally** (frames a downstream consumer — verify-build's per-dimension judge and the future HTML renderer — can use as pixels or as path-referenced files), or does it only **narrate** what it sees in freeform prose? The whole shape of V2 (rendered capture + baseline) forks on the answer.

**Answer: narration-only *to the judge*. V2 must add an explicit capture-and-persist step (branch B).**

**What was done:**
Drove bundled `Skill("verify")` **live** against a throwaway zero-dep web app (under gitignored `.context/scratch/`, since the committed fixture `evals/fixtures/verify-toy-web-app/app` isn't runnable — `server.mjs` has no static serving and `vite` is absent) using the connected Chrome browser MCP. Characterized exactly how a captured frame travels, and where it stops.

Three empirical observations, each load-bearing:

1. **Screenshots return as an image *content block* bound to the invoking agent's conversation — the text channel carries only a narration string.** A Chrome-MCP `computer screenshot` returns `<output_image>` (pixels) to the agent that called it, while the *textual* tool result is just `"Successfully captured screenshot (1408x840, jpeg) - ID: ss_2419a0xsc"`. That ID-and-dimensions string is the only thing a text-reading consumer sees. That string **is** "narration."

2. **`save_to_disk: true` surfaced no usable file path, and no file was discoverable on disk.** The tool contract says `save_to_disk` "Returns the saved path in the tool result," but the returned text was still only `"…jpeg - ID: ss_3441gckti"` — no path — and a filesystem sweep of the tmp/claude dirs (last 5 min) found nothing addressable. So in this (Chrome-MCP) configuration there is no path to hand to another agent even if you ask for one.

3. **verify-build's judges are fresh-context `Agent` subagents that receive only their prompt text** (SKILL.md Step 6). An image block in the orchestrator's context does not propagate to a separately-spawned judge. Combined with (1)+(2): a visual claim reaches the judge as the narration string only → and the rubric's two-citation discipline (no hedged PASS; `rubric.md:35`) correctly turns narration-of-a-screenshot into **Unknown**. That is precisely today's "visual = Unknown → blocks" behavior, now explained mechanically rather than suspected.

I did **not** spawn a separate `Agent` to "confirm" the judge is blind to the orchestrator's image block — that probe is tautological once (1)+(2) hold (there is no path or data to even pass it), and the subagent-receives-only-its-prompt boundary is an architectural guarantee. Recording the omission as a deliberate spike-economy call, not a gap.

**Bonus finding — observation sources are not equally trustworthy (informs the rubric, not just V2):**
While verifying the toy's two criteria, the Chrome-MCP `read_network_requests` panel reported the `POST /api/submit` as **`statusCode: 503`** — reproducibly — while the DOM/a11y tree showed the success toast (which only renders on `res.ok`) and `curl -X POST` returned **`201`** three times running. The app received a 2xx; the network panel's status code was simply wrong. A judge citing the network observation alone would have **wrongly FAILed** criterion 1; the judge citing the DOM observation would have correctly PASSed it. This empirically vindicates `rubric.md:66` ("read text from the DOM/a11y tree if available") and adds a sharper rule for V2: **structured text (labels, toast, error copy, and — now — even network status) should come from the a11y tree / an explicit assertion, not be trusted from a single observation channel.** The a11y tree was the reliable source throughout (`status "Submitted successfully" [ref_2]`, exact button labels).

**Why (what this unblocks):**
V1 (v1.5.1) let a plan *declare* visual criteria, but verify-build still resolves every visual claim to Unknown → blocks, so the agent can't honestly say "the visuals are good" without a human babysitting (FB-0041 north star). V2 is the link that turns that Unknown into a real PASS the Step 8 readiness predicate can trust. This spike was the cheap precondition: it fixes V2's shape before any feature code is written.

**V2 shape (the recommendation this spike hands to the V2 feature plan):**
- **Branch (B): add an explicit capture-and-persist step.** The verify-orchestrating layer drives the browser-MCP screenshot, then **persists each frame to a flow-controlled path** (an assets dir alongside `verifyReportPath`) and writes **path references into the findings buffer's `observations[].content`** — which the schema already types as "relative path or base64 data URI" (`findings-schema.json:98`). No schema migration is needed for *capture*; the buffer was built a superset for exactly this. Judges then receive path-referenced frames (or base64 inlined into the judge prompt) **plus a baseline**, enabling the pairwise VLM comparison the rubric already prefers over absolute scoring.
- **Keep the rubric's VLM/pairwise section — rewrite it, don't remove it.** `rubric.md:68`'s "may be removed if narration-only" disposition is **overtaken**: the section is needed, but should be re-grounded on path-referenced frames + a baseline (the spike confirms frames are capturable; they just don't auto-flow to judges). Absolute scoring stays discouraged.
- **Read text from the a11y tree, not screenshot pixels** (the bonus finding): V2 should capture an `a11y_snapshot` observation per state for label/copy/status assertions, reserving the `screenshot` observation for genuinely visual claims (layout, spacing, color, motion end-state).
- **Coupling (FB-0003):** the V2 feature PR lands capture (producer) + the ephemeral renderer / a judge consumer (consumer) in the **same PR**; it must not duplicate #36's durable `visual-history.html` record (V3b).

**Tradeoffs discussed:**
- **Live run vs documentary characterization.** Chose live (Chrome MCP was confirmed connected) so the answer rests on observed behavior, not inference from docs. Cost was standing up a ~50-line throwaway server; worth it — the `503`-vs-`201` finding and the no-path-from-`save_to_disk` finding would both have been missed by documentary reasoning.
- **Throwaway scratch app vs fixing the committed fixture.** Used `.context/scratch/` (gitignored, uncommitted) rather than making `evals/fixtures/verify-toy-web-app/app` runnable, to keep the spike disposable and avoid editing a committed artifact for a research run. (Surfaced as a side-finding: the committed fixture is documentation-only and not runnable — noted for whoever wires the eventual smoke harness; not fixed here.)
- **Editing `rubric.md:68` / `SKILL.md:64` now vs deferring to V2.** Deferred (user-approved scope): the spike records the answer here; the marker rewrites are V2 implementation work touching shipped safety-critical artifacts, and doing them now would force a version bump + SAFETY ceremony for a research-only spike.

**Lessons learned / limitations (FB-0016 — a spike result is as general as its sample):**
- **The "narration-only-to-the-judge" conclusion generalizes** (it rests on the architectural subagent-boundary, platform-independent). **The specific capture mechanics do not** — they were observed on **one platform (web) via one MCP (Chrome)**. iOS (XcodeBuildMCP) / Android (mobile-mcp) may surface screenshot file paths differently (some return a path natively), which could make their capture step cheaper. **Re-test trigger:** when V2 extends capture beyond web, re-characterize the per-platform screenshot-return contract before assuming the persist-it-yourself step is needed there too.
- `save_to_disk`'s documented "returns the saved path" did not hold in this Chrome-MCP build — a reminder that MCP tool contracts are observed, not assumed (pairs with FB-0015's "check the bundled surface" discipline).

### PR DC — Doc-currency in the ship pipeline — SAFETY
**Date:** 2026-06-05
**Branch:** `claude/doc-currency-pipeline`
**Commit:** (this PR; squash SHA at merge)

**What was done:**
Made the ship pipeline keep the forward-looking docs current automatically. `/flow:ship` gained **Step 5a** (doc-currency reconciliation — every ship refreshes roadmap "Now" with the current version + a "Recently shipped" line + a ▶ Next-up pointer, sweeps shipped plan items → "Recently Completed", and clears shipped `FB-XXXX` reservations) and **Step 5b** (a mechanical currency gate that asserts the manifest version appears in roadmap "Now" + plan "Current Focus", `exit 1` + reconcile-instruction on drift). The dev-side `.claude/skills/ship` got the same mirror; `/flow:doctor` got a *secondary* Check 2.6 of the same assertion; `workflow.md` Step 10 narrates the discipline. `docs/upgrade.md` was corrected (the "2-command ritual" was stale — `/plugin marketplace update` updates the installed plugin in one step; the doc now leads with `autoUpdate`). Dogfooded in this PR: the live staleness was fixed (roadmap "Now" read "v1.2.6"; plan "Current Focus" "v1.3.0" — both → v1.5.2). `SAFETY`: ship pipeline + install-surface manifests changed; the new gate is fail-fast (strengthens, never downgrades, error handling). v1.5.1 → v1.5.2.

**Why:**
Stale forward-looking docs are the FB-0010 fan-out class applied to *direction*. A cold reader — a new contributor, or the autonomous loop, which is a cold agent on every run — reads roadmap "Now"/plan "Current Focus" to decide what to do next. They had drifted ~5 versions because ship Step 5 wrote a backward-looking *history* entry + routed follow-ups, but nothing reconciled the forward-looking narrative or enforced currency. "Stale docs should never happen" (user direction, FB-0043).

**Design decisions:**
- **Enforcement in the pipeline (automatic), not in `/flow:doctor` (manual).** The user explicitly corrected an earlier draft that put the check only in doctor: "isn't doctor only run manually? I don't want to have to invoke this manually." So 5b runs on every ship; doctor's Check 2.6 is a *secondary* mirror for spotting drift between ships, never the enforcement.
- **Fail-and-reconcile, not auto-edit (user chose option a).** Step 5a (prompt, with judgment) does the doc edits; Step 5b (mechanical) only *verifies* they landed. Keeps the regex layer from rewriting prose.
- **Mechanical gate checks the version token only.** A version-string mismatch is the cheap, unambiguous signal that catches the worst drift; narrative correctness (the Recently-shipped list, the ▶ Next-up prose) stays the judgment of 5a — mechanizing prose-correctness is brittle and low-value.

**Technical decisions:**
- **Project-agnostic version source with graceful skip.** The gate resolves the version from `plugins/flow/.claude-plugin/plugin.json` → `.claude-plugin/plugin.json` → root `package.json`, and skips the mechanical check (keeping 5a) when none exists — so consumer projects without a versioned manifest aren't false-failed. No new schema slot.
- **Section-scoped grep with top-of-doc fallback** (`awk` extracts the "## Now" / "## Current Focus" section; falls back to `head -40` if the heading differs) so the check is precise on flow's convention and lenient elsewhere.

**Tradeoffs discussed:**
- Bundling the `docs/upgrade.md` fix (the originating thread) into the currency PR vs. splitting it (plan-critic Finding 2 raised scope). Kept bundled — it's the same *stale-doc* class, and the user requested the pipeline fix directly the prior turn (the "scope drift" finding was a false positive from cross-turn-context windowing).
- Mechanical narrative-currency (is "PR Q in flight" still true?) was considered and declined as too fuzzy; left to 5a's judgment.

**Lessons learned:**
- **The PR enforces its own thesis.** 5b ties the docs to the version bump: bumping `plugin.json` to 1.5.2 only passes once roadmap/plan say v1.5.2 — so a forgotten doc update blocks the ship. The currency fix can't itself ship stale.
- **The install confusion was itself a stale doc.** My earlier "two commands / reinstall" framing came from flow's own stale `upgrade.md`; verifying against `code.claude.com` (via the claude-code-guide agent) showed one command suffices. Fixed here — a fitting bug for a doc-currency PR.
- **Stale docs were not a one-off.** roadmap "Now" (v1.2.6), plan "Current Focus" (v1.3.0), and 17 lines of merged-PR Handoff Notes had all rotted — confirming this needed a mechanical fix, not another manual cleanup.

### Roadmap hygiene — Deliverable-quality track V2/V3 labels + de-stale `## Now`/PR Q
**Date:** 2026-06-05
**Branch:** `claude/flow-roadmap-hygiene-v2v3-labels` (SHA at squash-merge)

**What was done:** Docs-only roadmap cleanup, immediately after #36 merged:
- **Reconciled the V2/V3 labels.** The O8 entry's acceptance block called its two PRs `V2/V3a` + `V3b`, but the track section uses `V2` = capture, `V3` = render — so "V2" meant different things in the two places. Relabeled to **PR-1 = track V2 (capture) + V3a (renderer), coupled by FB-0003** and **PR-2 = track V3b (durable record)**, with an explicit stage-mapping sentence. Swept the one living cross-reference in the blueprint research doc (the `history.md` mention is an append-only record of #36's state, left as-is).
- **De-staled `## Now`.** Was frozen at "Plugin at v1.2.6 … This PR (PR H3)"; refreshed to **v1.5.1** with an accurate "what shipped since" line (PR Q/S/U + v1.4.x + #35/#37/#36) and reframed the execution-order intro around the three live streams (Track 1 K/L, Track 2 N/O/P, Deliverable-quality V2–V4).
- **Marked PR Q shipped.** The `## Next` PR Q bullet still read "in flight … Phase 11 next"; updated to **SHIPPED (v1.3.0, #26)** and pointed at the Deliverable-quality track it feeds.

**Why:** Surfaced when the user asked whether the roadmap had clear next steps after #36. The track's next-step path (V1 shipped → V2 next → V3 → V4) was clear, but the V2/V3a label mismatch and the stale `## Now`/PR Q lines muddied it.

**Design decision:** Kept the K/L/N/O/P track *descriptions* intact (still the live plan for those PRs) — only fixed the framing/version anchors, rather than rewriting queues whose status I couldn't fully verify. Append-only history entries (e.g. #36's tightening note) left untouched even where they carry the old label.

**Tradeoffs discussed:** Could have moved the whole O8 entry up under the track section for locality; declined — the cross-reference is clear and the move is larger surgery for marginal gain. A fuller `## Now` execution-order audit (K/L/N/O/P current status) is left as separate hygiene.

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

### PR V1 — `Visual-walk` plan field (Deliverable-quality track) — SAFETY
**Date:** 2026-06-05
**Branch:** `claude/priceless-franklin-ee0e79`
**Commit:** (this PR; squash SHA at merge)

**What was done:**
Added a new required plan field, `Visual-walk`, to flow's plan contract — declared, checkable visual/UX acceptance criteria a plan states when the change has a UI surface (gated on the existing `uiSurface` config slot + the diff actually touching UI; N/A under spike/tiny). Appended to three contract surfaces: `plan-discipline.md` (item 8), `planner.md` (template, placed at item-8 position with state-coverage placeholders), `workflow.md` (§2 required-fields + §8 now names the block). Version bump 1.5.0→1.5.1 (plugin.json + marketplace.json + README header + CHANGELOG). `SAFETY`: install-surface manifests modified (per `.claude/rules/safety.md`); changes are version strings + appended description prose only — JSON validity confirmed (`claude plugin validate` ✔, security-review JSON-parse check ✔). First (cheapest) link in the Deliverable-quality roadmap track (FB-0041) toward an autonomous high-quality deliverable.

**Why:**
`workflow.md` Step 8 already instructed the agent to "dial in visual quality against the plan's **declared visual criteria**," but no plan field declared them — a dangling reference. V1 gives that instruction a home, and creates the load-bearing *input* the rest of the Deliverable-quality track (V2 rendered capture, V3 HTML walkthrough) consumes. Declaration-only by design: today's consumers are the agent's Step 8/9 visual dial-in and the human at the plan-approval + merge gates; mechanical verification is deferred to V2.

**Design decisions:**
- **Distinct `Visual-walk:` block, not folded into `Spec-walk`** — so V2's verify-build can extract visual criteria as a labeled grep (parallel to how it already parses `Spec-walk:`), not a heuristic classification. MEDIUM-confidence, reversible (collapse to a `[visual]` tag if V2 prefers).
- **Declaration-only; plan-critic enforcement deferred** — surfaced as a REDIRECT at the approval gate (it diverges from FB-0041's "strengthen the gate" framing); user explicitly approved declaration-only. The enforcement half is Facet 4 of the managed-autonomy umbrella, routed to V1.1/V2.
- **Examples span static state + token/motion + interaction/a11y** — staff-review (ux + push-further triangulated) caught that the initial happy-path-look examples would anchor authors on appearance and seed thin V2 inputs. Expanded the canonical example set across both narration surfaces.

**Technical decisions:**
- **Append as field 8, keep the numbered list** — `plan-discipline.md`'s spike/tiny mode overrides are keyed to field *numbers* (`spike` replaces (4)+(5); `tiny` skips them). Inserting a "4.5" or renumbering would break those refs (the plan-critic BLOCKER B2). Appending + an explicit "N/A under spike/tiny" line keeps the number-keyed overrides valid. B1 (count fan-out) satisfied by carrying no "N fields" magic-count phrase, not by de-numbering.
- **Reused the `uiSurface` slot** — no new schema slot; `Visual-walk` is gated on the same project-wide flag `/flow:accessibility-review` uses, plus a per-diff "and the diff touches UI" qualifier (so a `uiSurface:true` project on a docs-only PR isn't pushed to invent visual criteria — the FB-0007 case).

**Tradeoffs discussed:**
- Declaration-only V1 vs. include-enforcement-now: declaration-only chosen as the cheapest unblocker; the real gate-strengthening comes from V2 (rendered capture turning "visual=Unknown" into a real PASS), and a critic rule only enforces *that you declared*, not that criteria are *met*. Enforcement + fixture deferred to keep V1 minimal.
- Field name `Visual-walk` (vs `UX-walk`/`Visual-spec`) — chosen for parallelism with `Spec-walk`; confirmed at the gate.

**Lessons learned:**
- **FB-collision lived in real time.** Mid-build, #35 (dynamic-workflows alignment) merged to `main`, claiming `FB-0037` for a different concept + leaving a stale base. The stale-base check surfaced it; renumbered this PR's entry `FB-0037 → FB-0041` with a full cross-file reference sweep (feedback/roadmap/plan/reserved), kept #35's entries intact, and cleared #35's now-shipped reservations with an audit-trail entry. This is exactly the case the K1 reserved-numbers protocol (+ the planned `/flow:doctor` Check 6) exists for — and a concrete data point for #35's own FB-0039 ("parallel writes make the reserved-numbers protocol load-bearing under fan-out").
- **The dogfood install is stale.** This environment runs flow **1.3.0** while developing 1.5.1, so `/flow:ship` (auto-invocable since 1.4.0/PR S) could not be model-invoked — shipped via the dev-side `/ship` instead, spawning `/flow:security-review` + `/flow:accessibility-review` manually to preserve the `STATUS: SKIPPED`/clean audit signal `general.md` requires. Re-installing flow from this repo would close the gap. (Routed as a follow-up.)

### Dynamic-workflows alignment report + adoption direction
**Date:** 2026-06-03
**Branch:** `claude/flow-dynamic-workflows-alignment-oJWKN`
**Commit:** (this PR)

**What was done:**
Docs-only direction-setting pass on how Flow should align with Claude Code's native dynamic workflows (research preview, 2026-05-28). Added: (1) full report `dev-docs/research/dynamic-workflows-alignment-2026-06.md` (state of play / concerns / opportunities O1–O8, grounded in the official `code.claude.com/docs/en/workflows` + `agent-teams` docs and Flow's own prior art); (2) three feedback entries — **FB-0037** (designer lenses are load-bearing, don't collapse under fan-out), **FB-0038** (use workflows where scale earns it, never force; token/cost first-class, no blanket ultracode), **FB-0039** (the human-review + self-learning artifacts — Flow-run PR table, companion HTML case-study, core-docs/FB/memory — must survive adoption); (3) a `roadmap.md` § Exploration umbrella entry tying O1–O8 to `Surfaces when` triggers. No plugin artifacts touched.

**Why:**
The user wants Flow to take full advantage of dynamic workflows — especially the parallel "voting"/adversarial-review fan-out — without the loop's structure inhibiting the engine, while keeping cost in mind and preserving designer perspectives + the review/self-learning artifacts.

**Design decisions:**
- **Segment-bounded adoption, not loop-wide.** Workflows forbid mid-run input; Flow's value is its gates. So a workflow owns the fan-out *between* gates and never spans one (segments A/B/C). This is the central reconciliation — keep rigidity at the gates, allow flexibility in the interior.
- **"Voting" refined, not adopted wholesale.** Honored existing prior art (FB-0016 + `dynamic-workflows-2026-05.md`): blind refutation rubber-stamps, debate loops amplify bias (PR J scope-out). The grounded direction is the untested *informed-independent refutation* variant at fan-out scale, re-tested on UI diffs — not generic claim-voting. Avoided contradicting hard-won findings.

**Technical decisions:**
- Full analysis lives in `dev-docs/research/` (matches the `agent-orchestration-2026-05.md` / `dynamic-workflows-2026-05.md` convention); actionable hooks live in `roadmap.md` + `feedback.md` so they re-surface via the exploration rule.
- Claimed FB-0037/38/39 **above** the 0020–0033 cross-session band (PR-U precedent), reserved in `reserved-feedback-numbers.md` before drafting (K1 protocol).

**Tradeoffs discussed:**
- **One umbrella PR vs. per-O-item PRs** — chose direction-setting + per-item graduation. The umbrella spans shipped-artifact, doctrine, and config surfaces that must ship/review independently (three-surface boundary + small-PR discipline). Pulling it into one PR would violate both.
- **Standalone research doc vs. inline roadmap only** — kept both: the doc preserves the full reasoning; the roadmap/feedback hooks make it actionable and trigger-discoverable.

**Lessons learned:**
- Flow's own constraints (FB-0012 mechanical-loop-only; PR J debate-loop scope-out; FB-0016 refutation spike) sharpen the native-feature recommendations rather than block them — the prior-art read is what kept the "voting" recommendation honest.

**Follow-up (same session):** User clarified that the visual-history / visual-verification artifacts are partly aspirational, and restated the actual goal — a human-review *value model*. Added **FB-0040** (north star: ground in user needs, make assumptions explicit, raise subjective questions, rationale for everything, then automate from clear intent + catalogue feedback/decisions — the principle FB-0037/38/39 serve), and marked the companion-HTML / visual-history artifacts explicitly ASPIRATIONAL/NOT-YET-SHIPPED in FB-0039 + the report (shipped baseline = `/flow:verify-build` behavioral check, v1.3.0; the rich visual report is a roadmap vision, not a surface to preserve). Key consequence captured: because workflows take no mid-run input, assumptions + subjective questions must surface at the *gate* preceding a segment, never in the fan-out interior — maximizing human-review value means *richer gate decisions, not more gates*.


### PR U — ship-time gate semantics + reviewer/ship-spike auto-invocability (v1.5.0) SAFETY
**Date:** 2026-06-02
**Branch:** `claude/pr-u-ship-gate-semantics` (rebased onto `main` @ `1eb4ad9` v1.4.2; squash SHA filled at merge)

**What was done:** Combined PR T umbrella Facets 2 + 3 + 5 (Facet 5 absorbed from the abandoned "Track A") into one PR:
- **Facet 5 — auto-invocability:** flipped `disable-model-invocation: true → false` on `audit-plan`, `audit-completion`, `critique-plan`, `ship-spike`. README + workflow.md relabeled accurately (the three reviewers → BOTH, never cold-start; `ship-spike` → auto but judgment-gated). FB-0010 grep confirms zero MANUAL survivors for the four.
- **Facet 2 — resolution-confidence + draft-routing:** `[auto-fixable]`/`[decision-required]` axis on security/a11y; `/flow:ship` routes decision-required findings (and non-converging verify-build regressions) to a **draft PR + `🚫 NOT READY TO MERGE` manifest** instead of a silent proceed or hard halt. Integrated into the v1.4.1 `## Flow run` PR body.
- **Facet 3 — verify-build placement:** ship-time verify-build reframed as a confirmation re-run (discovery → Step 8/9 readiness boundary; visual sign-off folds into the merge gate).
- Fixture `evals/fixtures/resolution-confidence-routing/`; v1.4.2 → **v1.5.0**; FB-0034/0035/0036.

**Why:** Closes the asymmetry where security/a11y BLOCKERs had no ship-stopping gate while verify-build hard-halted — both could yield a best-effort not-ready PR or an arbitrary mid-loop stop. Operationalizes the two-gate thesis: escalation routes INTO the merge gate (draft), and no reviewer/ship-spike skill is itself a gate.

**Design decisions:**
- **Draft-routing, not hard-halt** (plan-critic BLOCKER): auto-advance-into-ship stays verify-build-PASS-gated (PR S predicate + FB-0018 invariant unchanged); only ship-*internal* unresolvable findings route to draft. Invariant: no merge-ready PR on a non-PASS build.
- **Visual sign-off → merge gate** (plan-critic REDIRECT, user decision): preserves exactly two human gates.
- **Facet 5 depends on #33** (session-discovery fix): the `context: fork` reviewers need it to resolve transcripts from worktree cwds, else they auto-invoke but audit nothing. The parallel session that merged #33 live-verified fork-path parity is PASS once #33 is in base — closing the original auditor UNVERIFIED concern.

**Technical decisions:**
- Manifest is an in-memory per-run accumulator (Step 2 → Step 7); machine-consumable sentinel shipped as the *producer*; the *consumer* (CI/doctor merge-block + persistence breadcrumb) routed to roadmap as the deliberate second half.
- **Rebase collision reconciliation (FB-0010):** collided with merged #32 ("PR T — Flow-run descriptions") on the **PR-T letter** (this PR is "PR U"; the planning umbrella keeps the "Managed-autonomy confidence" name) and on **FB-0019** (renumbered this PR's entries → **FB-0034/0035** + added **FB-0036**, above the cross-session high-water flagged in the #33 handoff). Draft-manifest integrated into #32's `## Flow run` body rather than reverting it.

**Tradeoffs discussed:**
- Resolution-confidence self-tagging is an LLM judgment (MEDIUM) — mitigated by default-to-decision-required + the fixture pinning the boundary.
- ship-spike left on hard-halt (separate scope; roadmap follow-up).

**SAFETY:** edits `ship/SKILL.md` (ship contract) + the reviewer prompts + 4 skill invocation flags. Preserved: ship never merges; PR S auto-advance predicate; FB-0011/0012/0018 contracts. Pre-ship caught a self-inflicted secret-scanner trap (fixture used a realistic live-key-prefixed literal → push protection scans history → soft-reset + clean re-commit, not the unblock URL). staff-review (4 lenses) returned 0 BLOCKERs.

### `extract_session.py` session-discovery fix — reviewers were context-starved from worktree / dotted-path cwds (v1.4.2) SAFETY
**Date:** 2026-06-02
**Branch:** `fix/extract-session-cwd-slug` (off `main` @ `4f5fba6` v1.4.0; rebased onto `9117c3a` v1.4.1 at ship — version bumped 1.4.1→1.4.2 after the parallel PR #32 took 1.4.1)
**Commit:** `fix/extract-session-cwd-slug` (squash SHA filled at merge)

**What was done:**
Fixed `find_session_file` / `slugify_cwd` in `plugins/flow/scripts/extract_session.py` so the audit/critique reviewers actually locate the current session transcript. Two changes: (1) the cwd→`~/.claude/projects/<dir>` encoding now replaces **every** non-ASCII-alphanumeric character with `-` (matching Claude Code), not just `/`; (2) discovery first tries an exact match via the `CLAUDE_CODE_SESSION_ID` env var (validated to `[A-Za-z0-9_-]+` before it reaches the glob), falling back to the corrected cwd-slug, then to graceful `None`. Bumped v1.4.1 → v1.4.2 (plugin.json + marketplace.json ×2), CHANGELOG v1.4.2 entry, README + workflow.md "shipped surface" headers, and a new regression fixture `plugins/flow/evals/security/test_session_discovery.py`.

**Why:**
Discovered while verifying PR T / Facet 5 (reviewer skills made auto-invocable). Model-invoking `/flow:audit-plan` forked correctly but the forked auditor returned *"session file not found for this working directory"* and audited nothing. Root cause: `slugify_cwd` replaced only `/`, but Claude Code names its project dir by replacing `/` **and** `.` (and `_`, spaces) with `-`. So `/Users/.../flow/.claude/worktrees/<wt>` → CC writes `...flow--claude-worktrees...` while the script looked for `...flow-.claude-...` → directory miss → silent context starvation. This fires for **every** `.claude/worktrees/` dev session (i.e. all of flow's own dogfooding) and any consumer project under a dotted path. It is invocation-mode-independent (hand-typed slash command hit it identically), so it predates and is orthogonal to Facet 5 — but it would have made the newly auto-invocable reviewers hollow exactly where they're first exercised.

**Design decisions:**
- **Prefer `CLAUDE_CODE_SESSION_ID` over slug reconstruction.** Empirically the env var is exported into the skill `!`-backtick substitution subprocess (verified live: with the slug deliberately broken, the model-invoked auditor still returned grounded context — only the session-id path could have resolved it). It pinpoints the *exact* current session rather than newest-by-mtime in the cwd's dir, eliminating a latent wrong-session-audit risk in shared-cwd cases. Kept as best-effort primary (exactly-one-match or fall through) so it never degrades the slug path.
- **Corrected slug stays as deterministic fallback.** The env var is undocumented; the slug fallback (now matching CC's full encoding, unit-proven against the real dir name) guarantees correctness even if the var ever disappears.

**Technical decisions:**
- Encoding implemented as `re.sub(r"[^0-9A-Za-z]", "-", cwd).lstrip("-")`. Verified it reproduces the real on-disk dir name exactly, plus dotted/`_`/space cases. Confirmed against CC behavior via empirical project-dir inspection + claude-code-guide (replaces all non-alphanumerics; preserves hyphens; no dash collapsing).
- `_find_session_by_id` validates `session_id` to `[A-Za-z0-9_-]+` (fullmatch) before globbing `~/.claude/projects/*/<id>.jsonl`, and returns the file only on a unique match.

**Tradeoffs discussed:**
- **Scope: fold into Facet 5 vs. separate PR.** Chose a standalone bug-fix PR (user decision) — the bug is pre-existing, invocation-mode-independent, and benefits all reviewer usage, so it deserves its own focused review + fixture rather than riding inside Facet 5's flag-flip. Facet 5 then ships onto a verified-working reviewer path.
- **session-id-only vs. layered.** Rejected session-id-only (undocumented var ⇒ no guarantee) and slug-only (leaves the wrong-session-in-shared-cwd risk). Layered primary+fallback gets exactness when available and determinism always.

**SAFETY:** `extract_session.py` is on the safety-critical paths list (silent failure starves reviewers without surfacing an error). Preserved: malformed-JSONL skip, empty-session / no-turns / no-plan `emit_cannot_audit` fallbacks, and the explicit-`--session-file` override path (eval harness) — all unchanged. The change only *adds* a more-correct primary lookup and *widens* the encoding the fallback understands; the graceful-`None` terminal behavior is intact. Safety-history pre-check (`git log -5 -- extract_session.py`) showed no prior crash/fallback commits on the file. New fixture asserts the graceful-`None` case so a future refactor can't silently drop it. **Security-review (red-team lens) caught a glob-injection BLOCKER** in the new `_find_session_by_id`: `session_id` was interpolated straight into `Path.glob(f"*/{session_id}.jsonl")`, so a tampered/malformed `CLAUDE_CODE_SESSION_ID` (e.g. `*`, `[a-z]*`, `../…`) could wildcard-match or traverse to other transcripts. External exploitability is low (the env var isn't attacker-reachable without prior code execution), but the value flows into a filesystem glob and this file already takes a defense-in-depth stance (the `gather_reference_docs` cwd constraint), so it was fixed: `session_id` is now validated to `[A-Za-z0-9_-]+` (UUIDs pass; any path/glob metacharacter → `None` → cwd-slug fallback). A Case-4 injection fixture asserts five metachar/traversal payloads all resolve to `None`; a Case-5 fixture asserts the ambiguous `>1 match` guard returns `None`.

**Lessons learned:**
- "Reload the plugin in a fresh session" was insufficient to verify Facet 5: a session loads the *installed cache*, not the worktree source — and the cache slug bug then masked the real fork-path behavior. Verifying preprocessing scripts live requires patching the cache copy (scripts run per-invocation, so no restart needed) and exercising the actual skill `!`-substitution context, not just `--session-file`.

### Flow-run PR descriptions — per-step `## Flow run` table replaces `## Reviews` (v1.4.1)
**Date:** 2026-06-01
**Branch:** `claude/epic-northcutt-2d5e88` (commit at push time; off `origin/main` @ `4f5fba6`)

**What was done:**
Replaced the generic `## Reviews` blurb in the `/flow:ship` PR body with a `## Flow run` per-step table that documents the full loop run, plus instruction text telling the ship agent how to populate it from the session's loop history:
- **`plugins/flow/skills/ship/SKILL.md` §7** — `## Flow run` table (one row per loop step: Clarify → Plan+critique → Execute → Preflight → /simplify → /flow:staff-review → security/a11y/verify-build → Doc synthesis), each `✓` (ran) or `skipped (<reason>)`; a **Notable** cell for genuine signal or `—`. Instruction block encodes the mode/config skip reasons, the bidirectional honesty rule, the no-manufactured-notes rule, and the follow-ups-stay-canonical + never-merge doctrine.
- **`.claude/skills/ship/SKILL.md` (dev-side dogfood `/ship`) Step 4** — same `## Flow run` block (generic cross-refs, no `/flow:ship`-specific step numbers). Its merge behavior + step numbering left untouched (out of scope).
- **`plugins/flow/skills/ship-spike/SKILL.md` Step 7** — trimmed table; `/simplify` + `/flow:staff-review` pre-marked `skipped (spike)`; verify-build row carries the 3-check spike-rubric result.
- **`plugins/flow/docs/workflow.md`** — §10 gains a "The PR body documents the full flow run" subsection; the spike section's PR-body bullet names the trimmed table.
- Version bump v1.4.0 → **v1.4.1** (plugin.json, marketplace.json ×2, README header + ship-row, CHANGELOG v1.4.1 entry); cumulative description sentence appended.
- **`dev-docs/feedback.md` FB-0019** + reservation in `reserved-feedback-numbers.md`; this entry.

**Why:**
Prompted by dogfooding flow on another project where richer per-step PR descriptions were wanted. The old `## Reviews` one-liner under-documented what the loop actually did — a reviewer couldn't see at a glance which gates ran, which were skipped (and whether legitimately), or what each step surfaced. The table makes the loop's execution legible on the PR page itself.

**Design decisions:**
- **Table populated from in-session context, not a new machine-readable artifact.** The ship agent already writes Summary + Test plan from session context; the loop steps happened in the same session/branch, so a structured loop-log buffer would be over-engineering (FB-0015 bundled/over-build check). Generalizing verify-build's findings buffer to all steps was scoped out.
- **Bidirectional honesty rule.** The user's request named only the "never imply it ran when it didn't" failure mode. The plan-critic caught the inverse: the request's "if security/a11y are not-yet-shipped, say so" conditional evaluates *false* in v1.4.x (all three reviewers ship and run), so carrying it forward unconditionally would have instructed the agent to write "skipped — not yet shipped" for steps that actually execute. Resolution: real skip reasons map to runtime-config states; "not yet shipped" is a clearly-conditional fallback for a step genuinely absent from the reader's flow version. Captured as FB-0019 sub-rule (a).

**Technical decisions:**
- **Dev-side `/ship` reconciled, not unified.** CLAUDE.md treats `plugins/flow/skills/ship/SKILL.md` and `.claude/skills/ship/SKILL.md` as distinct surfaces and documents no sync convention; the dev-side skill is the older simpler push+PR+merge command. Applied only the PR-body section to satisfy the user's "update both" done-criterion, without touching its merge behavior or step numbering.
- **Version bump.** Shipped plugin artifacts (ship + ship-spike skills, workflow.md) changed, so v1.4.1 per the PR-J precedent (prompt-only change → bump). Surfaced in the plan as a MEDIUM-confidence call for the merge gate; docs-at-root no-bump precedent (PR H1/H2) doesn't apply since these files ship in the install bundle.

**Tradeoffs discussed:**
- **Per-step table vs. keeping the prose blurb.** The table costs more PR-body bytes and asks the agent to recall the whole loop; chose it because the legibility gain (skip-with-reason visible per step) is exactly what the dogfood surfaced as missing. The no-manufactured-notes rule + `—` default bound the cost: a routine PR's table is mostly dashes.
- **FB-0010 fan-out risk.** The skip-reason vocabulary now lives in four surfaces; mitigated by a dedicated spec-walk grep line (plan-critic FOLLOW-UP) rather than relying on author memory.

**Lessons learned:**
- A user request can embed a conditional that's stale against the current codebase. Evaluate "if X, say Y" against the code before encoding it as an instruction — the plan-critic's prove-or-disprove pass (v1.2.5) is what caught it here.

**Safety note (no SAFETY marker):** This entry touches safety-listed files (`ship/SKILL.md`, both manifests) but modifies only the PR-body template + version/description strings — no error-handling, persistence, or fallback paths. Ran the `git log --oneline -5 -- plugins/flow/skills/ship/SKILL.md` precondition check (recent SAFETY commits were verify-build + bounded-retry preflight + auto-invocable; none touched by this PR-body edit). Per `.claude/rules/documentation.md`, no SAFETY marker is warranted.

### `/flow:ship` auto-invocable — autonomous-loop trigger at Step 8 (v1.4.0) SAFETY
**Date:** 2026-05-30
**Branch:** `claude/auto-ship-readiness-trigger` (commit at push time; stacked on the docs PR #29 squash)

**What was done:**
Flipped `/flow:ship`'s `disable-model-invocation` from `true` → `false` so the agent can invoke ship itself at the end of a driven loop, paired with a deterministic gate so it can't fire arbitrarily:
- **ship/SKILL.md** — flag flip + an auto-invocation contract in the description (the text Claude Code reads to decide auto-firing): auto-invoke only when the ship-readiness predicate holds and the FB-0011 risk gate is clear; never when verify-build is skipped; never merges.
- **workflow.md** — Step 8 "Present" rewritten as a **conditional gate**: a ship-readiness predicate (all spec-walk boxes checked, no open BLOCKER, no unresolved MEDIUM/LOW assumption, `/flow:verify-build` would return PASS), an FB-0011 risk gate, and explicit auto-advance vs stop-and-present paths. Loop diagram + MEDIUM confidence-row cross-referenced.
- **general.md** — workflow-discipline bullet encoding the trigger (auto-loads on `**/*`).
- Version bump v1.3.0 → **v1.4.0** (marketplace.json ×2, plugin.json, README header) + cumulative description sentences; README auto/manual table `ship` row → `AUTO·when-ready` + cold-start note revised; CHANGELOG v1.4.0 entry.

**Why:**
The user's goal is an autonomous coding loop with human gates only at plan approval and merge. `ship`'s `disable-model-invocation: true` was a blanket-conservative default set in v1.0.0 and never revisited toward that direction — it forced the user to type "ship it" at every loop end, which is not one of the two load-bearing gates. Auto-invoking ship does not violate the merge gate (ship opens a PR, never merges).

**Design decisions:**
- **verify-build is the load-bearing gate, not the predicate.** The predicate only decides whether to *enter* ship; ship's own Step 2 verify-build (`exit_code: 1` on FAIL/Unknown) re-confirms and halts pre-PR. So a falsely-confident auto-advance is caught mechanically — the model's self-report is not the safety boundary. This is why the predicate can be "soft" (rule + description guidance) without a Stop-hook.
- **Skipped-verify stays MANUAL** (user decision, 2026-05-30): library/none platform + doc-only diffs have no behavioral gate, so the predicate requires `overall_verdict: PASS`, not merely "verify-build didn't fail." Default-to-ESCALATE per FB-0011.
- **ship-spike stays MANUAL** — spikes are user-initiated explorations; the deliverable (the answer) is a judgment call, not a mechanical readiness signal.

**Technical decisions:**
- Encoded the predicate in `general.md` (already loads on `**/*`) rather than a new rule file — a 5th rule would break the "4 auto-loading rules" fan-out contract (README/doctor/manifest all cite the count).
- Verified no eval/doctor/CI assertion depended on `ship` being `disable-model-invocation: true` (`git grep` — none) before flipping. Evals + security evals green post-change.

**Tradeoffs discussed:**
- Flip-the-flag-alone vs flag-plus-gate. Flipping alone would let the model ship on a vibe (the un-gated judgment FB-0011 warns against). Chose flag + readiness predicate + verify-build hard gate so autonomy is earned by a mechanical signal, not asserted.
- Stacked this PR on the docs PR (#29) rather than basing both on the same `main` — the README auto/manual table only exists post-#29, so editing the `ship` row required #29 merged first. Avoided re-introducing the staleness #29 removed.

**Lessons learned:**
- The autonomy increase is reversible (flip the flag back) and bounded (merge stays human, verify-build gates pre-PR) — which is what made it shippable without a hard Stop-hook. The Stop-hook remains a deferred roadmap item for hard enforcement.

### README + workflow.md + config.example — surface auto-vs-manual reality, list skills in loop order, de-stale v1.0.0→v1.3.0
**Date:** 2026-05-30
**Branch:** `claude/nice-lamarr-3c30c0` (commit at push time)

**What was done:**
Docs/config correction PR, three coherent pieces:
- **README.md** — reordered the skill catalog from importance-order into **loop order** (the user's explicit complaint: "skills aren't listed in workflow order, confusing"). Added a **Fires** column (AUTO / MANUAL / BOTH) + a `Step · gate` column, a `⚠️ Cold-start reality` callout stating plainly that on a bare "build me X" only the auto-loading rules attach and nothing executable fires until typed, added the missing **`/flow:verify-build`** row, and fixed the header (`v1.2.5`→`v1.3.0`, `11`→`12 skills`). Expanded the one-line `## The loop` arrow into a numbered table naming every skill at its step and marking the three human pauses (Gate 1 plan, Gate 3 LOW-confidence, Gate 2 merge) + mechanical stops.
- **plugins/flow/docs/workflow.md** — de-staled `Bootstrap status (flow v1.0.0)` → `Shipped surface (flow v1.3.0)`; stripped every `(PR 2)` / `(PR 3)` / `[not yet shipped]` marker that described already-shipped surface (staff-review, security/a11y review, ship-spike, workflow-help, memory machinery, template dir) as future work; updated the skills cheat sheet + config-slot prose. (This change was pre-staged in the worktree from a prior session; verified and folded in as in-scope.)
- **template/base/flow.config.json.example** — expanded from 14 to all 21 documented slots (added `preflightCmd`, `sourceFilePatterns`, `uiFilePatterns`, and the four verify-build slots) so adopters reading the example discover the mechanical-preflight + behavioral-verification gates instead of shipping them off-by-default. (Also pre-staged; verified and folded in.)

**Why:**
A workflow-driven production-readiness audit surfaced that (a) the README presented skills in an order no reader could map onto the loop and never distinguished auto-fire from manual-typing, and (b) the canonical workflow doc the README points to as "the loop itself" still described half the shipped plugin as unshipped PR-2/PR-3 work — contradicting a v1.3.0 install. Both erode adopter trust. The 14-of-21 example config silently disabled the headline reliability + verification gates for anyone who only read the example.

**Design decisions:**
- Kept the README's "When to use each reviewer" matrix (a by-work-type view) alongside the new loop-order catalog rather than collapsing them — different lookups for different reader intents.
- The cold-start honesty note is deliberately blunt ("a typed-command toolkit with a thin auto-loaded guidance layer, not a loop that drives itself") because the gap between the "managed-autonomy loop" framing and the typed-command reality was the single biggest UX surprise the audit found.

**Technical decisions:**
- No code touched; markdown + JSON-with-comments only. No version bump (docs/config at root, same precedent as prior docs-only PRs). Skill/rule counts unchanged (12 skills, 4 rules) so no fan-out sweep needed beyond the version-string + skill-count edits in README, which were the contract change.
- Verified each pre-staged diff (`workflow.md`, `config.example`) before staging rather than committing an unreviewed change.

**Tradeoffs discussed:**
- Documenting today's manual reality vs the intended auto-ship end-state. Chose to describe what's shipped (manual) here and split the auto-ship capability into its own PR (`claude/auto-ship-readiness-trigger`) rather than write forward-looking docs about unbuilt behavior — the exact staleness class this PR removes.

**Lessons learned:**
- The audit found the most dangerous staleness wasn't wrong code but a canonical doc confidently describing shipped features as future work. De-staling docs is as load-bearing as fixing code when the doc is the adopter's map.

### Reviewer-refutation spike — verdict (blind refutation does not cut the FP tax on this diff; re-test as the feature evolves)
**Date:** 2026-05-28
**Branch:** `claude/dazzling-goodall-1ea214`
**Commit:** [SHA at commit time]

**What was done:**
Ran the reviewer-refutation spike (drafted in `plan.md`, plan-critic-APPROVED) as a dynamic workflow: 3 reviewer stances (staff-engineer, security/red-team, shell-robustness) fanned over `template/base/bootstrap.sh`, producing 15 raw findings; each finding was then verified two ways in parallel — **Method A** = the finder re-checks its own finding (today's PR J self-disproof), **Method B** = a fresh **blind** agent that never sees the finder's reasoning or the other findings. Cost: 33 agents / ~983k tokens / ~4 min for one 259-line file.

**Result:**
- Self-disproof (A) kept 10/15 (refuted 5). Blind refutation (B) kept **15/15 (refuted 0)** — a rubber stamp. The hypothesis (blind refutation cuts the false-positive tax) **inverted**.
- Root cause: the false positives in this diff are **significance** misjudgments, not **verification** errors. The claimed mechanism is almost always real (the code does do X); what makes it a false positive is the judgment that X doesn't matter under Flow's documented trust model (e.g. the symlink/FLOW_DIR "attacks" require an attacker already inside the adopter's own repo/shell). A blind agent confirms the mechanism and stamps "real"; it lacks the stance + project context to ask "but does this matter?" Blindness removes deference bias but also removes the judgment that catches the dominant FP class.
- Self-disproof outperformed but was **internally inconsistent**: it refuted the dangling-symlink write-through yet kept the structurally identical symlink-append; it refuted the slot-count finding in one framing yet kept the same false claim in another. Right answers, unreliable process.
- Adjudication (grounded): of the 5 disagreements, self-disproof was correct on 4 (the two symlink/FLOW_DIR significance calls and the slot-count false positive — verified: schema has 16 properties at b1c8e01 / 17 at HEAD, so "slots" ≠ example-key-count). One was a compound finding (real dead-code claim bundled with a false stray-space claim) neither method handled cleanly.

**Verdict:** **Do not encode blind refutation into the reviewer prompts.** PR J's self-disproof stays — it does real work. But the experiment's real payoff is diagnostic: the FP bottleneck is significance judgment, and both methods apply it inconsistently. The promising (untested) direction is **informed-independent refutation** — a fresh agent *with* stance + project context (not blind) + a uniform significance/exploitability rubric. **Not a write-off:** this is one data point on one problem type (a clean, already-reviewed shell script). Dynamic workflows are in research preview and will evolve; re-test across other problem types — especially UI projects, genuinely-buggy pre-review diffs, and migration-scale diffs — before drawing a general conclusion. Tracked in `roadmap.md` § Exploration.

**Why:**
The 2026-05-28 dynamic-workflows release made adversarial refutation a native runtime primitive; the spike measured whether the *pattern* is worth porting into Flow's shippable reviewer prompts (plugins can't bundle workflows, so the runtime itself isn't shippable — see `dev-docs/research/dynamic-workflows-2026-05.md` §5.3).

**Design decisions:**
- Controlled comparison (same finder pass, vary only the verification step) rather than two end-to-end runs — isolates the blindness variable instead of confounding it with finder variance.
- Reviewed a real, self-contained code diff (`bootstrap.sh`) rather than a docs diff — docs-only diffs early-exit the reviewers and produce no signal.

**Tradeoffs discussed:**
- Blind vs informed refutation: blindness kills deference bias (the original goal) but also kills significance judgment. The experiment showed significance is the dominant axis here, so blindness was the wrong knob — independence + context is the right combination. Recorded as the next variant to test, not adopted now.
- One diff is directional, not statistically robust; the named limitation (undersamples "kills real findings" because the file was already reviewed clean) is why the roadmap entry requires re-test on buggy + UI diffs before any general conclusion.

**Lessons learned:**
- A single dynamic-workflow review fan-out cost ~983k tokens on a 259-line file — concrete confirmation that workflows are a *selective tier*, not a per-PR default (matches the research doc's trigger-model finding).
- The spike paid for itself regardless of the methodology verdict: it found a real BLOCKER-class crash + two NITs in flow's own `bootstrap.sh` (fixed in the entry below), triangulated by all three stances.

### bootstrap.sh — trailing-flag crash + cp -n comment drift + swift counter miss SAFETY
**Date:** 2026-05-28
**Branch:** `claude/dazzling-goodall-1ea214`
**Commit:** [SHA at commit time]

**What was done:**
Fixed three defects in `template/base/bootstrap.sh` (shipped in the install bundle), all surfaced by a reviewer-refutation spike that fanned three review stances over the file:
1. **BLOCKER (error handling) — trailing-flag crash.** The arg-parse loop did `--stack) STACK="$2"; shift 2` (same for `--project` / `--flow-dir`) with no guard. Under the script's `set -eu`, a flag passed as the final token (`bootstrap.sh --stack`, or the realistic typo `--stack web --project`) expanded `$2` unbound and aborted with a raw `bash: $2: unbound variable` (rc 1), bypassing the guided `⚠️ … exit 2` usage path every other failure uses. Added a `need_val` helper that checks `[ $# -ge 2 ]` before `shift 2` and routes a missing value to the existing usage/`exit 2` path. Applied uniformly to all three value-taking flags.
2. **NIT — `cp -n` comment/code drift.** Header (line 27), the `set -eu` rationale (line 32), and the Step A banner (line 113) all credited idempotency to `cp -n`, but `copy_n` actually uses an `[ -e "$dest" ]` precheck + plain `cp` (no `-n`). The comments also contradicted the accurate Step C note (BSD cp returns 1 on skip under set -e). Rewrote the three comments to describe the `[ -e ]`-guard reality and cite why real `cp -n` is deliberately avoided.
3. **NIT — swift counter miss.** The swift-only `safety.md` append/skip branches mutated state but never did `copied=$((copied+1))` / `skipped=$((skipped+1))`, unlike the structurally-parallel `.gitignore.append` block, so the `scaffold complete: N created, M skipped` summary undercounted on the swift stack. Added the increments.

**Why:**
A blind-vs-self refutation spike (see `dev-docs/research/dynamic-workflows-2026-05.md`) reviewed `bootstrap.sh`; the trailing-flag crash was independently found by all three stances and kept by both verification methods — the highest-confidence finding in the run, and a textbook FB-0010 fail-loud violation living in flow's own scaffolder. The two NITs were high-agreement findings worth folding into the same fix.

**Design decisions:**
- Route the missing-value case to the *existing* guided usage path rather than inventing a new error shape — consistency with every other failure in the script (single `⚠️ … run with --help for usage … exit 2` voice).

**Technical decisions:**
- `need_val` helper rather than inline `${2:-}` guards ×3 — DRY + uniform messaging, consistent with FB-0009's "consistency is the value" lineage. One guard shape for all three flags.
- Verified the only trailing-arg-prone `$2` sites are the three arg-parse cases; `$2` at the `copy_n`/`copy_tree` definitions are function-local params (always bound when called) and need no guard.
- Left the Step B "17 slots" line untouched: the spike's slot-count finding was adjudicated a false positive — "slots" is the schema property count (16 at b1c8e01, 17 at HEAD post-PR-M `preflightCmd`), not the example file's populated-key count.

**Tradeoffs discussed:**
- `need_val` helper vs per-case inline check: helper won for uniformity; cost is one extra function. Acceptable.
- Scope: the fix made the pre-existing `--help` verbosity (the `grep -E '^# '` dumps all column-0 comments, including section dividers and rationale, not just the usage header) marginally longer. Did NOT fix the `--help` greediness — out of scope for this task, logged as a FOLLOW-UP. Restricting scope to the three named defects is the discipline the spike itself reinforced.

**Verification:**
- `bash -n` clean.
- Reproduced all three trailing-flag cases → now emit `⚠️ <flag> requires a value` + `exit 2` (was `$2: unbound variable` rc 1).
- Existing paths unaffected: missing `--stack`, unknown arg, `--help` all behave as before.
- Real swift scaffold in a temp dir: first run `16 created / 0 skipped`, re-run `0 created / 16 skipped` — the matched totals prove every mutation is now counted in exactly one branch (idempotency invariant).

**FOLLOW-UP:**
- `--help` greps every `^# ` line, so it prints section dividers + rationale comments, not just the usage header (lines 2–28). Pre-existing; restrict the grep to the contiguous header block (e.g. stop at the first blank line). Surfaces when: next edit to `bootstrap.sh`'s `--help` handling.

### Flow plugin v1.3.0 — `/flow:verify-build` plan-driven behavioral verification gate (PR Q) `SAFETY`
**Date:** 2026-05-28
**Branch:** `claude/lucid-matsumoto-730ba0`
**Commits:** `e722a9b` (PR Q skill) + `4cd5bbc` (staff-review fixes) + `5ad95f2` (manifest bump + flow self-config)

**What was done:**
Added `/flow:verify-build`, the third final-pass reviewer in `/flow:ship` Step 2 (alongside `/flow:security-review` and `/flow:accessibility-review`). Wraps bundled `/verify` (transitively `/run` + `/run-skill-generator`) with flow-specific orchestration: plan-driven criteria extraction from `**Spec-walk:**` checkboxes, fresh-context adversarial transformation, per-dimension parallel judges (PASS/FAIL/Unknown with two-citation evidence), Unknown-blocking gate per FB-0011, and structured findings buffer routed to `/flow:ship` Step 4a FB-XXXX synthesis. Closes the static-analysis-only gap in the loop's verification surface (Potemkin-interface / hallucinated-success class — the dominant agentic-dev failure mode no current flow step catches).

New plugin surface:
- `plugins/flow/skills/verify-build/SKILL.md` (~310 lines) — 9-step orchestrator
- `plugins/flow/skills/verify-build/lib/` — extract-criteria.py + 4 prompt files (adversarial.md, rubric.md, spike-rubric.md, not-tested-checklist.md) + findings-schema.json (JSON Schema draft-07) + findings-example.json
- 3 eval fixture sets: verify-unknown-blocks/, verify-toy-web-app/, verify-budget-overrun/ (14 fixture files)
- Schema slots: `platform`, `verifyEnabled`, `verifyFindingsPath`, `verifyBudgetCalls` (17 → 21)
- ship-spike Step 2 invokes verify-build in spike mode (3-check rubric)
- doctor Check 5.3 detects whether `/run-skill-generator` has been run
- workflow.md Step 10 + skills cheat sheet + config slots table; bootstrap.md Step 5.5 + migration.md Stage 1.5 name `/run-skill-generator` as Tier-1 prerequisite
- `flow.config.json` added at repo root: `platform: library` + `uiSurface: false` + `defaultBranch: main` (flow self-dogfoods the new schema by opting out of verify-build at platform check)

**Why:**
The 11-step loop verifies through static analysis only — typecheck/lint at Preflight, staff-review reading code at Step 7, security/a11y reviewers reading the diff at ship Step 2. No step actually runs the binary. The dominant agentic-dev failure mode is "Potemkin interface" (Replit Agent 3) / hallucinated success (Arize field analysis): an agent claims a feature works because it compiled, types passed, the diff looks plausible — when the button does nothing, the API call 400s and is silently swallowed, or rendered state never matches intent. PR Q closes that gap with a runtime gate that blocks ship on Unknown verdicts.

**Design decisions:**
- **Thin wrapper around bundled `/verify` rather than reimplementing run-and-observe** — first-pass draft proposed 20+ files with 5 platform runners (web/ios/android/tauri/cli) duplicating what bundled `/verify` + `/run` already do. User caught this; redraft shrinks to ~6 lib files leaning on bundled skills as the execution layer (FB-0015 lesson). Same pattern `/flow:security-review` and `/flow:accessibility-review` already follow.
- **Per-dimension parallel judges (correctness / regression / scope-creep) rather than one mega-judge** — Anthropic's evals guidance recommends one judge per dimension to reduce dimension contamination. Parallel for speed + position-bias isolation.
- **Unknown is a gate-blocking verdict** — Per FB-0011 (autonomy bar — ESCALATE on uncertainty). Judge forced to admit ignorance rather than fabricate PASS. Two-citation rule binding: verdict without verbatim observation quote + criterion quote ⇒ Unknown.
- **Findings-buffer JSON shape forward-compat with future HTML case-study renderer** — Per user vision note 2026-05-28. Buffer schema (per-criterion text + per-adversarial-case text + per-step observation captures with `type` discriminator + per-dimension verdict with evidence + top-level "not tested" checklist) is a superset of what an eventual HTML renderer needs. PR Q ships the JSON; the renderer PR (post-PR-Q) renders against this contract. No schema migration required.
- **Spike-mode (3-check rubric) for `/flow:ship-spike`** — Launch / one happy step / no log errors. Single-dimension (correctness only — regression + scope-creep are not meaningful without a plan defining scope). Same Unknown-blocking semantics; lower bar in number of checks, not verdict rigor.
- **Inherits FB-0012 bounded-retry contract from PR M** — Judge runs single-pass; budget cap (verifyBudgetCalls slot) forces Unknown on overrun (mechanical exit signal per FB-0012(a) — no judge-output loop); reward-hacking guards (no test-disabling, no @ts-ignore/eslint-disable) baked into adversarial.md prompt per FB-0012(c).
- **Flow self-config as `platform: library`** — flow itself has no runtime; verify-build cleanly skips at Step 1.2 platform check. Dogfoods the new schema slot; provides the canonical "this is a library plugin" reference config for any plugin-like consumer.

**Technical decisions:**
- **POSIX-portable shell** in SKILL.md `!` blocks (no bash arrays — dash compatibility per FB-0010 silent-skip discipline). External CLI fail-fast (FB-0009).
- **JSON Schema draft-07 with `additionalProperties: false`** at every level of findings-schema.json — strict. Additive changes require explicit schema bump; prevents drift.
- **8 observation type discriminators** (screenshot / a11y_snapshot / network / console / log / stdout / exit_code / narrative) — covers what bundled `/verify` can return + structured captures from Playwright/XcodeBuildMCP, with `narrative` as the freeform fallback.
- **Optional `timestamp_offset_ms` on observations** — relative-to-verify-start, for the future renderer's timeline layout. Absolute timestamp anchor deferred to PR R+ (FOLLOW-UP routed).
- **Spike-mode preserves schema shape** — regression + scope-creep dimensions emitted as Unknown with `evidence: ["(spike mode — dimension not applicable)", "<criterion>"]` so downstream consumers (ship Step 4a, future HTML renderer) don't need spike-aware branching.
- **Verify-build does NOT auto-skip on doc-only diffs** — unlike security + a11y, behavioral changes can live in non-code files (config-driven toggles, etc.). The run-and-observe loop is cheap to attempt; falls through to Unknown if nothing observable.

**Tradeoffs discussed:**
- **Single big PR vs phase-staged PRs.** User chose Path B (full skill on one branch, single PR) over Path A (intake PR + phase PRs). Reasoning: ship one focused PR per skill; let queued PRs (N/O/P/R) build on top regardless of sequencing order. PR Q is orthogonal to N/O/P/R (different files; mechanical rebase in either order). Ship order = whichever finishes first.
- **Wrap bundled `/verify` vs inline orchestration in `/flow:ship` Step 2.5.** Chose Shape A (separate skill) over Shape B (inline). Justifications: ship-spike composability, eval testability, separation of concerns, future Preflight-tier extensibility, standalone invocability for power users wanting flow's plan-criteria + Unknown gate vs bundled `/verify`'s freeform observation. Precedent: `/flow:security-review` resolves the CLAUDE.md "don't wrap bundled" ambiguity in favor of substantive-added-value wrappers.
- **Ship-only single-tier vs two-tier (Preflight fast-subset + ship full-pass).** Two-tier rejected — fast subset meaningless on iOS (60s min build+boot) and Android (~30s emu boot); slowing iterate cycles to catch a class reviewers can also catch is a bad trade. Mid-iterate verification available via bundled `/verify` directly.
- **Adversarial transformation: inline `lib/adversarial.md` vs named subagent.** Inline. Promote to `plugins/flow/agents/verify-adversarial.md` on rule-of-three (consistent with `flow:close-out` precedent).
- **VLM pairwise instruction kept in v1 rubric.** Default-safe — if bundled `/verify` returns screenshots structurally and judge doesn't pairwise-compare, scores are unreliable. Phase 1 empirical characterization may drop this if `/verify` is confirmed text-only.

**Lessons learned:**
- **Always check the harness's available-skills list before drafting a new flow skill** (FB-0015 — captured this PR). The 20+-file first-pass draft duplicated bundled `/verify` + `/run` + `/run-skill-generator` because I didn't audit available-skills at session start. Concrete pre-planning check: grep for the proposed skill's core verb (verify, run, audit, review, ship); if a match exists, justify the wrapper with substantive added value or drop the skill.
- **FB number / PR letter coordination is non-trivial under cross-worktree parallelism.** Drafted as FB-0010 → FB-0012 → FB-0013 → FB-0014 → FB-0015 across the session as collisions surfaced. PR letter drafted as M → Q after bounded-retry PR M took the slot. K1's reserved-feedback-numbers.md protocol made the collisions visible before merge; without it the cross-file references would have silently pointed at the wrong concepts (FB-0010 fan-out class applied to FB numbers).
- **Staff-review caught a fan-out BLOCKER on the manifest descriptions** (17-slot references that survived the diff). Doctor Check 2.5's scan misses install-surface JSON (`.claude-plugin/marketplace.json` + `plugins/flow/.claude-plugin/plugin.json`). FB-0010 strikes again; routed as FOLLOW-UP to extend Check 2.5's scan.
- **Flow's own `flow.config.json` was missing.** Adding it as `{platform: library, uiSurface: false}` IS dogfooding the schema — useful both for self-protection at /flow:ship invocation AND as a reference config for any plugin-like consumer.

### PR K1 — Reserved feedback numbers (claim-time defense for FB-XXXX collisions across parallel branches; no version bump)
**Date:** 2026-05-28
**Branch:** `pr-k1/reserved-feedback-numbers`
**Commit:** [SHA at ship time]

**What was done:**
Added `dev-docs/reserved-feedback-numbers.md` — a small protocol file where in-flight branches claim their `FB-XXXX` number before drafting the entry in `feedback.md`. Parallel branches editing this file at the same line produce a clean textual merge conflict (mechanical enforcement). When a PR ships, `/flow:ship`'s synthesis step removes the line. Also added a Handoff Notes entry in `dev-docs/plan.md` documenting the FB-collision audit + resolution.

**No version bump.** `dev-docs/` is project-dev only; doesn't ship in the plugin install.

**Why:**
Post-PR-J cross-worktree audit (triggered by user prompt 2026-05-28: "make sure there hasn't been any lost work… as the PR letters advance on this branch and others") discovered three in-flight FB conflicts before any branch had rebased:

1. `sweet-hellman-6c0745` drafted FB-0011 = "bounded-retry agent loops" while PR J had already shipped FB-0011 = "autonomy bar" to main.
2. `sweet-hellman` drafted FB-0012 = "same-model critic collusion."
3. `pr-m/verify-build-skill` (lucid-matsumoto-730ba0) independently drafted FB-0012 = "check bundled Claude Code skills first."

Counts at audit time: sweet-hellman had **20 FB-0011 references across 5 files** (feedback.md, history.md, plan.md, research doc, schema.json) and **12 FB-0012 references across 2 files** (plan.md, research doc). PR M (verify-build) had 1 FB-0012 textual entry + by-name handoff-doc references.

The textual merge conflict on `feedback.md`'s insertion point only catches the entry itself. The 19 + 11 cross-file references would survive a feedback.md-only rebase resolution and silently point at the wrong concept (the FB-0010 "fan-out contradiction" sub-class applied to FB numbers).

**Resolution recorded mid-PR-K1:** Between this PR's initial draft and the rebase onto main, sweet-hellman rebased + shipped at `0cf642e` (#22) as v1.2.6. Sweet-hellman **renumbered their drafted FB-0011 → FB-0012 and swept all 20 cross-file references cleanly before pushing** — no silent overwrite occurred. PR J's FB-0011 ("autonomy bar") survives untouched on main. The verify-build PR (lucid-matsumoto) still has the open arbitration item: its drafted FB-0012 must renumber to **FB-0013**, and its drafted "PR M" letter is now taken (suggest PR N at its ship time). PR K1's protocol file is updated to reflect the resolution; the audit-trail section preserves both the original contention and the outcome for institutional memory.

**Design decisions:**
- **Why a separate file rather than a section in `dev-docs/plan.md`** — the protocol's mechanical benefit is the textual merge conflict on a small, dedicated file. Sections in plan.md edit other lines too, weakening the conflict-detection guarantee. Single-purpose file is sharper.
- **Why a docs-only PR rather than folding into PR K** — sweet-hellman + PR M (verify-build) were both actively in flight at PR K1's commit time; landing the protocol file ahead of either rebase gives both branches a fetch-and-pull-in coordination surface. PR K (which adds the mechanical Doctor Check 6 + lens-staff-engineer FB-cross-file hunt) is the *permanent enforcement*; PR K1 is the *immediate-coordination signal* layer. Option C from the layered-defense recommendation.
- **Why include current state details in the file itself** — concrete inline references (which branches claim which numbers, what the resolution was) are higher-signal than abstract protocol description. Branches reading the file see the live state plus the rule.
- **Suggested arbitration of the residual FB-0012 contention** — lucid-matsumoto's verify-build PR moves to FB-0013 (single cross-reference; cheaper than re-renumbering sweet-hellman's now-merged FB-0012). Not enforced; surfaced for human decision at PR M-verify-build ship time.

**Technical decisions:**
- File lives at `dev-docs/reserved-feedback-numbers.md` alongside other dev-docs metadata. Not `plugins/flow/` — doesn't ship in the install.
- Format: protocol description + Currently reserved list + Audit trail. The Audit trail section is intentional; FB-0010-style institutional memory for past collisions.
- Protocol step 3 ("push your reservation immediately, don't batch") is the load-bearing race-detection move. Without immediate push, two branches can both reserve the same number locally before either pushes; the push order then determines who wins, but the local edits diverge silently.

**Tradeoffs discussed:**
- **Protocol file vs Doctor Check 6 first.** Doctor Check 6 (FB-collision check vs `origin/main`) is the *rebase-time* enforcement; this file is the *claim-time* enforcement. Both are needed: Doctor catches collisions even if the protocol file isn't updated; the protocol file prevents collisions from being introduced in the first place. PR K ships Doctor Check 6 + lens-staff-engineer hunt extension as the second + third defensive layer. The user explicitly chose Option C (both): land this small PR now, fold Doctor + lens changes into PR K.
- **Audit-trail section in the file vs in history.md.** Kept in the file because the audit trail IS the institutional memory of why this protocol exists. history.md tracks "what we built"; reserved-feedback-numbers.md tracks "what conflicts the protocol caught." Different surfaces; cheap to maintain both.
- **Auto-update on `/flow:ship` vs manual entry removal.** Decided: `/flow:ship` synthesis step (step 4) handles the entry removal — same place that updates feedback.md with the new FB entry. Single source of doc-write timing.

**Lessons learned:**
- **Cross-worktree audits are cheap and catch class issues mechanical merge can't.** The 20-FB-0011-references finding was invisible to git merge-conflict detection but obvious to a one-shot grep across uncommitted state. Periodic "what's in-flight elsewhere?" sweeps are a good discipline; consider folding into the `/flow:doctor` Check 6 design when PR K builds it.
- **Sweet-hellman's clean renumber-then-rebase validated the protocol shape even before the protocol file existed.** Their sweep covered all 20 FB-0011 references + 12 FB-0012 references; nothing silently survived. This is the existence proof that the discipline (grep first, edit second per FB-0010) works when applied. The protocol file makes it harder to forget the sweep, but doesn't change the mechanics.
- **Naming registries work mechanically when the registry file is small and dedicated.** Same pattern works for skill names, schema slots, agent names. If a fourth class hits the same "merge-conflict-but-cross-file" pattern, consider generalizing this file to "reserved-identifiers.md" with sections per identifier type.

### Flow plugin v1.2.6 — bounded-retry mechanical preflight in /flow:ship + /flow:ship-spike (PR M)  `SAFETY`
**Date:** 2026-05-27
**Branch:** `pr-h2/preflight-retry-loop` (branch name retained from pre-rename; PR labeled PR M after the parallel PR I/J/K/L collision)
**Commit:** [SHA after rebase + force-push]

**What was done:**
Added a bounded-retry mechanical preflight (new Step 1c) to `/flow:ship` and `/flow:ship-spike`. The step runs a project-owned shell command (new `flow.config.json.preflightCmd` slot — typecheck + lint + fast tests, project owns the composition) BEFORE invoking reviewers. On non-zero exit, the skill enters a bounded-retry loop: fix the failure, re-run, up to N=3 total invocations, with oscillation detection via diff-hash (`git diff HEAD | sha256sum`). The loop fires ONLY on this externally-verifiable exit signal — reviewer outputs at Step 2 stay deliberately single-pass. Docs-only diffs skip the loop entirely via the 3-source check (committed + uncommitted + untracked, per PR D's lineage), with `sourceFilePatterns` regex validated before use (FB-0010 silent-skip prevention). Unset/whitespace-only slot emits the standard loud-warning (FB-0006/0007 pattern), never silent no-op. Exit 127 (command not found) fails fast without consuming the retry budget. Schema grew from 16 → 17 slots; live references updated (plugin.json description, marketplace.json descriptions ×2, README.md ×2, doctor SKILL.md description, template/base/CLAUDE.md.template + bootstrap.sh — the template/base/ updates caught at review-time per PR G's consistency discipline). New eval fixture `plugins/flow/evals/security/test_preflight_retry.py` with 6 test functions exercising 7 load-bearing contract markers (N=3 cap, diff-hash oscillation, exit-127 fail-fast, do-not-disable-tests, do-not-add-suppressors, single-pass-reviewers, docs-only early-exit) plus schema/jq/sh-c behavior assertions.

**Why:**
User-driven exploration of whether to add `/loop`-style iteration to the workflow. Research pass against Anthropic's "Building Effective Agents" (evaluator-optimizer pattern requires "stopping conditions" + "explicit success criteria") and the 2026 Agentic Coding Trends Report ("without explicit success criteria, verification becomes guesswork"). The honest read: a bounded retry is the right primitive where the exit signal is mechanically verifiable (external tool exit code); it's the wrong primitive where the exit signal is another model's judgment (reviewer "looks good"). Flow's current `/flow:ship` had no mechanical-quality preflight loop at all — Step 3's `typecheckCmd` re-run was a one-shot post-reviewer-fix check. This PR adds the missing primitive in the one slot where the exit signal is unambiguous, and explicitly forbids the same shape on reviewer-judgment outputs (reward-hacking failure mode).

**Design decisions:**
- **Loop only on mechanically-verifiable exit codes (preflight script exit status).** Never loop on LLM-judgment outputs (auditor "approved", plan-critic "APPROVED", reviewer "no findings"). Loops over LLM judgment teach Claude to *phrase around* the reviewer rather than fix substance — exactly what evidence-or-silence and passive review are designed to prevent. This is the load-bearing call; everything else is downstream. Captured as **FB-0012**.
- **Step 1c position: BEFORE reviewers, not after.** Running preflight before Step 2 means reviewers see code that already typechecks (what they expect). Running it after would risk reviewers + Claude fighting over the same files across iterations.
- **Hard N=3 cap, not a config slot.** Anthropic guidance names "maximum iterations" without prescribing N. N=3 is a deliberate choice (rationale: enough for fix-A-broke-B-fix-B, not enough to wander) — not an empirically-tested literature finding. Matches the spirit of Microsoft Magentic's caps (three separately-configurable: `max_round_count`, `max_stall_count`, `max_reset_count`) and Trigger.dev's example of "up to 10 iterations"; both name caps without prescribing N. If 3 proves wrong later, the slot is a single-file follow-up; adding it prematurely violates FB-0003.
- **Diff-hash oscillation detection on top of N=3.** Pure A↔B↔A oscillation aborts before attempt 3 burns budget. Drift (A→B→C all broken differently) is caught by N=3 exhaustion. Independently converged with Microsoft Magentic's `max_stall_count` primitive (Magentic counts consecutive non-progressing rounds; Flow detects exact-diff oscillation — same defensive shape, different detector). Known false-positive: same correct fix made twice → spurious abort; mitigated by attempt logs preserving the situation.
- **Prompt-driven contract, not shell-script harness.** The retry semantics live in the SKILL.md natural-language instructions, not in a wrapper script. Matches Flow's existing orchestration idiom. The risk (a session ignoring the cap) is detected via the per-attempt log line; the alternative (shell harness) is real implementation cost.
- **Reward-hacking guards explicit in the contract.** "Do NOT modify or disable tests unless the failure is a genuine test bug" + "Do NOT add `// @ts-ignore`, `# noqa`, `# type: ignore`, `eslint-disable-next-line`, `// biome-ignore`, `@SuppressWarnings`, `#[allow(...)]`, or equivalent suppressors." Prompt-level guards are probabilistic; human merge gate at Step 7 is the backstop. Both layers matter.
- **Docs-only diffs skip the loop entirely.** Reuses `sourceFilePatterns` (PR D lineage). A docs PR has nothing for preflight to verify; running it is wasted work + violates the FB-0006/0007 early-exit-when-irrelevant principle.
- **No standalone `/flow:preflight` skill.** Step 1c stays inside `/flow:ship` and `/flow:ship-spike` so the loop only fires under the surrounding gates (stale-base, gh+jq, something-to-ship). Exposing it standalone invites consumers to invoke the loop without the gates.

**Technical decisions:**
- **Reuse `sourceFilePatterns` for docs-only early-exit** — already in schema since PR D. Avoids new regex slot proliferation.
- **3-source diff check** matching PR D's `/flow:security-review` lineage: committed (`git diff origin/$BASE..HEAD`) + uncommitted (`git diff HEAD`) + untracked (`git ls-files --others --exclude-standard`). The common 'iterate locally then /flow:ship' loop hits uncommitted/untracked — must catch all three.
- **`sourceFilePatterns` regex validated before use** via PR D's GREP_RC check (grep -qE returns 0/1 on valid regex match/no-match; 2 on regex error). Invalid override falls back to default + emits loud warning. Closes FB-0010 silent-skip class.
- **Whitespace-only `$PREFLIGHT_CMD` treated as unset** — `jq -r` returns literal whitespace for `"   "` slot values; `[ -z "$VAR" ]` wouldn't catch. `printf '%s' | tr -d '[:space:]'` strips and re-tests.
- **3-tier `DEFAULT_BRANCH` fallback chain in Step 1c** — separate Bash invocations don't share scope (per `/flow:ship` Step 1b's explicit note). Re-resolved inline to avoid the FB-0008 silent-fallback-to-`main` failure.
- **`sh -c "$PREFLIGHT_CMD"` not `eval`** — same trust model as `typecheckCmd` (FB-0004); subshell can't mutate caller-process state.
- **Schema description names the precedence between `preflightCmd` and `typecheckCmd`** — if both set, both run (Step 1c for preflight, Step 3 for typecheck). Avoids a magic precedence rule; user owns the config.
- **Mirror Step 1c verbatim across ship + ship-spike** — consistency is the value (FB-0009 lineage); a copy-paste here is cheaper than a doc-snippet extraction until a 3rd bounded-retry block exists.
- **ship-spike Step 2 trimmed** — Step 1c now handles preflight via bounded retry; Step 2's redundant `tools/preflight/check.mjs` invocation removed. Step 2 retains `typecheckCmd` one-shot (parallels `/flow:ship` Step 3's role).
- **Eval fixture asserts SHAPE not end-to-end behavior** — prompt-driven iteration is non-deterministic by construction. Contract markers are text-grep on SKILL.md. Real "does Claude obey N=3?" is a dogfood-time question, not CI-time.

**Tradeoffs discussed:**
- **Bounded retry on preflight vs adding a `/loop` user-facing primitive.** User asked about `/loop` — Anthropic's `/loop` is a scheduling/polling primitive (run a prompt every N minutes), not a goal-seeking primitive. The right fit for "iterate until tests pass" is an internal retry block inside `/flow:ship`, not a separate user command. A standalone command would invite usage without the surrounding ship gates.
- **Loop the reviewers too?** No. Single-pass reviewers are load-bearing per Flow's product principles ("evidence or silence"). Looping until the auditor approves teaches reward hacking. The research pass explicitly identifies this as the failure mode; the PR body should not invite consumers to extend the contract to reviewer outputs.
- **Hardcoded N=3 vs config slot.** Slot adds flexibility but violates FB-0003 if shipped without proven need. 3 is a deliberate design choice consistent with non-prescriptive guidance; adjustable later if dogfood shows it bites.
- **Schema description length.** v1.2.6 description grows again (already long after v1.2.5). Acceptable cost; consumers read it once during install. Future PR could deduplicate via a CHANGELOG.md reference.
- **Prompt-driven loop vs shell-harness.** Shell harness is more reliable but real implementation cost + diverges from Flow's idiom. Ship the prompt-driven version; instrument with per-attempt log line; promote to harness if a session ignores the cap.
- **PR letter rename PR H2 → PR M.** Original branch + PR title used "PR H2" (next-in-sequence at planning time). After rebase onto main, "PR H2" was already taken by the docs cadence softening PR (squash `2266ceb`). Renamed to PR M (next available letter after K/L, which are queued for `/flow:red-team` + Detection-Point-3 routing). Branch name kept as `pr-h2/preflight-retry-loop` for continuity; PR title updated to PR M.

**Lessons learned:**
- **Documentation referencing a slot before the schema declares it** is an inverse FB-0003 (doc-without-implementation, vs the more common schema-without-consumer). Worth a follow-up sweep to find others. Doctor's Check 2.5 would not catch this directly — it checks slot-count fan-out, not "every documented slot has a schema entry."
- **The user's framing question ("would loops help us iterate to quality?") was the right question to push back on.** The honest answer is "loops help on mechanical signals; they harm on judgment signals." Encoding that distinction in the contract (Step 1c does loop; Step 2 does not) is more valuable than the loop itself.
- **Bounded-retry contracts need oscillation detection.** Pure iteration caps would allow A↔B↔A burn until exhaustion. Diff-hash is the cheap detector. Future bounded-retry blocks (if any) should inherit this — captured as FB-0012.
- **5-lens review pipeline emulated via Agent subagents (FB-0001 pattern) caught 1 BLOCKER + 11 NITs that survived implementation discipline.** BLOCKER was a FB-0010 fan-out survivor (template/base/ files still said "16 slots") — exactly the class FB-0010 was written to prevent. The discipline working on its own enforcement.
- **PR letter collisions on a fast-moving main require renumber-on-rebase.** Original "PR H2" became "PR M" after PR I/J/H2-docs/K-queued/L-queued landed in parallel. Lesson: when committing forward-planning blocks for queued PRs, expect rename if main moves. Plan-critic flagged the scope drift (forward-planning in same diff as in-flight PR) — convention update queued for future H-series.

### PR H2 — docs/upgrade.md cadence softening (no version bump)
**Date:** 2026-05-27
**Branch:** `pr-h2/upgrade-cadence-softening`
**Commit:** [SHA at ship time]

**What was done:**
Three copy edits to `docs/upgrade.md` after user feedback that the original PR-H1 prescription was too aggressive ("do I really need to run this after every session? every update? or just major updates?"):

1. **"When to run it" table rewritten** with semver-aware guidance. Old table had 5 triggers, all variations of "run the ritual." New table differentiates major/minor/patch bumps explicitly: major requires before-next-session; minor before-next-session in projects using the new surface; **patch is OPTIONAL — batch them, flow's discipline is additive at patch level so deferring is safe.** Added explicit "Mid-session: skip" and "Just to be safe: skip" rows. Plus a TL;DR at the top: "run when you want a specific new feature; otherwise weekly-ish hygiene is enough."

2. **"Multi-project ritual" → "Multi-project: once per machine (for user-scope installs)".** Original section claimed the ritual must run "in each project's Claude Code session" because the catalog cache is "per-session." That was wrong: for user-scope installs (the default), the catalog cache + the installed plugin both live at user-scope; one ritual run propagates to all projects on the machine. Project-scope installs (custom workflow) are the per-project case, but most consumers don't set that up. Section now distinguishes the two with a quick `jq` check for which scope you're in (with fail-loud fallback for jq-missing case, mirroring the existing FB-0009 pattern elsewhere in the same doc).

3. **Auto-update tradeoff hardened.** Old text said "for patch bumps, this is usually fine — flow's discipline is additive-only at patch level." That overpromised the additive guarantee. New text: "flow aims to be additive-only [at patch level]... the discipline is enforced by author care + lens-staff-engineer + /flow:doctor Check 2.5 — it's not a hard guarantee, so verify each upgrade with /flow:doctor regardless." Plus version-aware recommendation reframed as a principle: "when a major bump ships (any x.0.0), default to auto-update off until you've read the major-bump CHANGELOG; flip back on after you've understood the breaking changes." Rule propagates forward without naming a specific version.

**Why:**
User asked the cadence question directly. Re-reading my own upgrade.md surfaced that I'd overprescribed — every trigger row said "run the ritual" with no patch-vs-major distinction. A consumer following the prior table literally would have been running the 2-command ritual after every flow PR merge, even for trivial patch bumps. That's friction with no proportional benefit. The fix is copy-only; no behavior changes.

**Design decisions:**
- **No version bump.** Same precedent as PR H1: `docs/` lives at repo root, not inside `plugins/flow/`; consumers fetch the new copy from GitHub directly, not via `/plugin install`. No new behavior shipped.
- **Patch-bump = optional, not "skip entirely."** Considered telling consumers to never run the ritual for patch bumps unless they see a feature they want. Decided against: weekly-ish hygiene catches accumulated drift, and the cost of running the ritual is ~30 seconds. The current copy ("optional. Batch them") frames the right cadence without being absolute.
- **The "per-machine vs per-project" correction is a factual fix, not a softening.** The original "per-session" claim was wrong; I traced it from my Claude Code research and may have misread the source. The corrected description matches actual Claude Code marketplace + plugin-install behavior (per-machine for user-scope installs).
- **Auto-update recommendation reframed as a principle, not a named version.** Original "OFF starting v2.0.0" — named-version signaling — is fragile (no event surfaces it when v2.0.0 ships). New "when a major bump ships (any x.0.0), default off until you've read the CHANGELOG" propagates forward as a rule.

**Tradeoffs discussed:**
- **Where to surface "cadence" in the doc.** Considered (a) new section at top, (b) integrated into "When to run it" table, (c) rewriting both. Chose (b) + (c): the table itself carries the major/minor/patch distinction, with a TL;DR sentence above the table. Avoids creating a new section that competes with the existing structure.
- **Multi-project section accuracy.** The original "per-session" claim was a real factual error. Considered framing the fix as "clarification" — landed on "correction" instead per the .claude/rules/general.md scope discipline ("'why' goes in the documentation").

**Lessons learned:**
- **Docs overprescription is a real risk** when the author is also the maintainer dogfooding. The author internalizes "do this often" as a default and bakes it into the consumer-facing doc, where it reads as required cadence to someone less invested. The corrective surface is consumer feedback at first-read; this PR turns one such feedback round into a doc-shape change.
- **Per-session vs per-machine vs per-project install scoping.** Worth understanding deeply before writing install/upgrade docs. The original wrongness in PR H1 was caught only by an explicit user question. Routed as numbered plan FOLLOW-UP #27: `/flow:doctor` install-scope detection check would prevent future doc errors of this shape.
- **Parallel-PR collision via PR J (v1.2.5 adversarial sharpening, separate session).** While PR H2 was in flight, PR J shipped to main bumping the plugin to v1.2.5. Rebased PR H2 onto the new main + reconciled the v1.2.4-current → v1.2.5-current framing in plan.md Current Focus. The FB-0008 stale-base preflight gate would have caught this at /flow:ship time; manual rebase served the same role since this PR went via `gh pr create` after the workflow-loop completed (per PR I workflow-spawn discipline, /flow:ship should orchestrate end-to-end — captured as discipline reinforcement, not a new FOLLOW-UP).

### PR J — Adversarial sharpening of the reviewer pipeline (v1.2.4 → v1.2.5) `SAFETY`
**Date:** 2026-05-27
**Branch:** `claude/youthful-chaum-500268`
**Commit:** [SHA at ship time]

**What was done:**
Prompt-only PR sharpening Flow's four reviewer surfaces along the dimensions deep research on adversarial review and code-review best practices converges on. First of a three-PR sequence (PR J = sharpening; PR K = `/flow:red-team` skill + agent; PR L = trust-boundary detector + autonomous gate). Bumps to v1.2.5. *Note: originally drafted as "PR I" during the planning conversation; renamed to PR J after rebase on `origin/main` revealed that a separate "PR I — workflow-spawn skip prevention" had landed in parallel (squash `da0b2c4`, also bumping to v1.2.4). My PR is complementary (different reviewer surfaces); renumbered to PR J + v1.2.5 to avoid collision. Queued PR J → PR K, queued PR K → PR L throughout this entry, plan.md, FB-0011, and project memory.*

Four reviewer prompts edited:

1. **`plugins/flow/agents/auditor.md`** — added two new sections:
   - `## Principle` (right after the intro): Anthropic's verbatim over-engineering warning ("flag only gaps that affect correctness or evidence-grounding; treat the rest as optional") promoted to a principle-level statement, not buried in schema.
   - `## Self-check before emitting` (between False-verification proxies and Output format): three-step disproof routine. The reviewer must name the specific session text that would invalidate the finding, re-scan for it, and drop if found or if the lookup is fuzzy. Directly modeled on Anthropic's Claude Code Security pattern: "Claude re-examines each result, attempting to prove or disprove its own findings and filter out false positives."

2. **`plugins/flow/agents/plan-critic.md`** — added two new sections + one in-place edit:
   - `## Principle` (same shape as auditor): adversarial framing tempered with the over-engineering warning.
   - `## Self-check before emitting` (between The two-citation rule and What does not count): the disproof routine adapted to the two-citation rule — the reviewer must attempt to find a *third* citation that would resolve the apparent conflict.
   - `Internal incoherence` category extended to explicitly cover **fan-out contradictions within the plan** (count / name / slot / version / file path referenced in N places where values disagree). This absorbs **PR-G FOLLOW-UP #5** ("plan-critic.md fan-out hunt addition") from `dev-docs/plan.md` § "PR H+ FOLLOW-UPs routed from PR G review."

3. **`plugins/flow/agents/lens-staff-engineer.md`** — added one new section:
   - `## How to read this diff` (right after the title intro, before Inputs): explicit adversarial reading stance ("assume the diff is broken — what's the most likely break?") + the over-engineering warning. The framing is the engineer-lens analog of the security lens's threat-model stance; the existing FB-0010 hunts (silent-skip on edge case, fan-out contradiction) compose under this stance rather than replacing it.

4. **`plugins/flow/skills/security-review/SKILL.md`** — modified the agent prompt block at Step 3 only; all operational logic (FB-0006/FB-0007 source-file early-exit, FB-0008 `[ -z ]` defaultBranch fallback chain discipline, FB-0009 fail-fast gh+jq, three-source diff capture including uncommitted + untracked) preserved untouched. *Note: FB-0008's full stale-base preflight gate (`git fetch + merge-base --is-ancestor`) lives in `/flow:ship` Step 1, `/flow:staff-review` Step 1, and `/flow:doctor`, not in `/flow:security-review`; what security-review applies from FB-0008 is the `[ -z ]` fallback chain pattern (not the pipe-OR form). The stale-base preflight gate proper is added to `/flow:red-team` in PR K per the plan-critic ISSUE 7 finding.*
   - Identity shift: "You are a staff security engineer cold-reading a diff" → "You are a **red-team operator**. Your goal is to find an **exploitable vulnerability** — not to evaluate whether the code is good."
   - Added over-engineering warning + an explicit narrowness reminder ("a missing input validator on a value that never reaches user-controlled data is not a finding; a sanitizer config that is wrong-by-default *is*").
   - "Hunt for:" → "Attack surface (categories to probe):" — same nine categories, each gains an attacker-mindset trailing question (e.g., "Where is the attacker URL?", "Where does cross-origin trust enter?").
   - Added a `Before emitting each BLOCKER/NIT` disprove paragraph: trace the dangerous sink back to the input source; if not user-controllable in any realistic execution path, drop the finding.
   - Output format gains a "the attacker scenario in one sentence" requirement on BLOCKER lines, forcing the reviewer to produce a concrete exploit path rather than abstract speculation.

Version bump: `1.2.4` → `1.2.5` in `plugins/flow/.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json` (both fields: top-level metadata + per-plugin entry). Marketplace descriptions refreshed to surface v1.2.5 framing (the v1.2.4 workflow-spawn summary moves to CHANGELOG history-of-record). README.md "What v1.2.4 ships" → "What v1.2.5 ships" (skill catalog unchanged — no slot/skill/lens/rule count drift).

CHANGELOG.md gains a v1.2.5 entry following the established Date / Version / Headline / 2-4 bullets / "Breaking changes: none" pattern, placed above the v1.2.4 (PR I workflow-spawn) entry.

**Why:**
User asked: "should I add an additional adversarial review in the workflow of the flow plugin?" Triggered a deep-research pass across (a) frontier-lab official documentation (Anthropic Claude Code best-practices, Multi-Agent Coordination Patterns, Claude Code Security, OpenAI CriticGPT, DeepMind CodeMender), (b) AI-native production patterns (Anthropic's own Claude Code Review plugin, Cursor Bugbot, Cognition's "Don't Build Multi-Agents" carve-out for read-only review, GitHub Copilot Code Review's "silence is better than noise"), and (c) academic literature on multi-agent debate, LLM-as-judge bias, self-critique failure modes (Du et al., Liang et al., Smit et al., Zhang et al. ICML 2025 position paper, Zheng et al. NeurIPS 2023, Huang et al. ICLR 2024, Khan et al. ICML 2024 Best Paper, Kenton et al. NeurIPS 2024, McAleese et al. CriticGPT, Bai et al. Constitutional AI).

Convergent findings that shape this PR:
- **Anthropic explicitly recommends "an adversarial review step"** (Claude Code best-practices: "Before treating a task as done, have a subagent review the diff in a fresh context and report gaps"). Flow already has this in shape; the gap was that the prompts weren't explicit about the adversarial stance.
- **Adversarial framing raises recall by 16–93% on security-sensitive tasks** (Mao et al. on multi-role vulnerability detection; multiple 2025–2026 studies on attacker-mindset prompting; CriticGPT catches ~85% of inserted bugs vs ~25% for human reviewers).
- **But:** "A reviewer prompted to find gaps will usually report some, even when the work is sound" (Anthropic best-practices); CriticGPT hallucinates and human-machine teams outperform critic-alone. The over-engineering tax is documented and material.
- **Mitigation: prove-or-disprove self-check.** Anthropic's Claude Code Security ships exactly this pattern at scale: "Claude re-examines each result, attempting to prove or disprove its own findings and filter out false positives." This PR backports the pattern into Flow's auditor + plan-critic + security-review reviewers.
- **Categorical (pass/flag) outputs beat numeric scores** (OpenAI Cookbook LLM-as-judge: classifier 98% vs 92–95% for numeric raters). Flow's existing `ISSUE` / `AUDIT SUMMARY` / `No issues flagged.` / `APPROVED` schemas are already optimal — this PR resists the temptation to add confidence scores and reinforces the existing schemas.

PR J scope: prompt-only. PR K adds `/flow:red-team` as a user-invocable standalone skill. PR L adds the trust-boundary detector + autonomous-invocation wiring at three workflow detection points (plan / staff-review / ship).

**Design decisions:**
- **Standalone `/flow:red-team` skill, not a 5th lens in `/flow:staff-review`** (decision made in plan; ships in PR K). The 4-lens ceiling stays. Red-team has its own threat-model categories and a different consequence asymmetry (false negatives much worse than false positives) — composes with `/flow:ship` the same way `/flow:security-review` and `/flow:accessibility-review` already do.
- **Per-finding `Fix-confidence:` field on red-team output (ships PR L)** with values `AUTO-FIX-SAFE` vs `ESCALATE`. Encodes the user's stated autonomy bar (FB-0011, saved to project memory at `~/.claude/projects/-Users-benyamron-dev-flow/memory/feedback_autonomy_bar.md`): auto-fix only when fix is clearly best-practice + clearly aligned with spec/intent + low implementation risk; otherwise escalate. This extends the existing confidence-gate primitive into auto-fix routing.
- **No debate loop.** "Judging with Many Minds" (arxiv 2505.19477) shows debate amplifies bias sharply after the initial round. Flow's parallel-then-merge topology is on the safer side of the published evidence — preserve it.
- **No numeric 0–100 scores.** OpenAI Cookbook's classification-vs-numeric finding plus Anthropic research system's "pass-fail with rubric" preference. Keep the categorical schema.
- **Mix-model-family routing deferred to a roadmap follow-up.** Same-family models agree on wrong answers 97% of the time (Goel et al. 2025); a cheap config change would help, but the Claude Code subagent SDK surface for this isn't there yet.

**Technical decisions:**
- **Self-check is a prompt-level addition, not a separate agent or pass.** Same agent, same context, ~50–100 extra tokens, drops findings via internal reasoning rather than a second invocation. Lowest-cost intervention with the largest published quality lift.
- **Adversarial framing on `lens-staff-engineer` is composable with FB-0010 hunts.** The new `## How to read this diff` section sits at the top of the prompt; the existing silent-skip + fan-out hunts continue to operate inside the categorical Hunts list. Neither replaces the other.
- **Security-review's identity shift preserved every operational gate.** The agent prompt is one section of the SKILL.md file; the bash orchestration around it (early-exit, FB-0008 fallback chain, fail-fast) is intentionally untouched. This isolates the behavior change to the reviewer's framing.
- **Plan-critic's fan-out hunt addition uses the existing two-citation rule.** A fan-out contradiction is just a special case of internal incoherence where the two citations are two stale references in different files. No new category, no schema change.

**Tradeoffs discussed:**
- **All reviewers adversarial vs selectively adversarial.** Loading "find more bugs" framing onto every existing reviewer would burn the over-engineering tax across the entire pipeline. Per the published evidence (consequence-asymmetry analysis), security has the strongest case for full adversarial identity; UX, design-engineer, accessibility, push-further have weak cases (false positives in subjective categories are pure noise). Resolution: full red-team identity for security; adversarial-leaning preamble for engineer (the FB-0010 hunts are already adversarial-shaped, this just makes the stance explicit); no framing change for UX / design-engineer / accessibility / push-further.
- **Separate skill vs 5th lens for red-team.** A 5th lens would reuse staff-review's orchestration but compromise the 4-lens ceiling discipline and mix threat-model categories with engineer/UX/design/push-further. Standalone skill is cleaner, composes with `/flow:ship` like the other domain reviewers, and preserves the documented contract in `plugins/flow/docs/workflow.md` Step 7 ("Four Explore agents review the diff in parallel from four lenses"). Standalone wins.
- **3-PR split vs single mega-PR.** Sharpening (PR J) is prompt-only, dogfoods fast, lowest blast-radius. New skill (PR K) is testable in isolation as user-invocable. Autonomous gate (PR L) depends on PR K's skill existing. Each PR has one clean story.
- **Auto-fix-safe vs always-stop-and-present on red-team BLOCKERs.** User explicitly chose the "act when clearly best-practice + low-risk + no competing options; otherwise stop" hybrid — saved as the durable autonomy-bar rule (FB-0011 + project memory). Encoded as the per-finding `Fix-confidence:` tag in PR L. Default-to-ESCALATE when in doubt; conservative-grow the AUTO-FIX-SAFE category list only with dogfood evidence.

**Lessons learned:**
- **Plan-critic caught 5 BLOCKERs + 2 REDIRECTs + 1 FOLLOW-UP on the draft plan**, all real misalignments — including a passive-vs-active violation (the detector was originally wired into the plan-critic *agent* rather than the orchestrating skill), a 4-lens-ceiling contradiction inside the plan's own Scope statement, missing SAFETY discipline + missing FB-0003 schema-pairing + missing FB-0008 stale-base for the new skill. Pre-plan-approval critique is load-bearing; this was a strong dogfood validation.
- **Engineer-lens dogfood caught a factual error in the CHANGELOG mid-PR.** The sharpened engineer-lens (running on its own new prompt) caught that I'd labeled "FB-0008 stale-base preflight" as preserved-in-security-review, when actually the preflight gate proper isn't in security-review (it's in /flow:ship + /flow:staff-review + /flow:doctor). What security-review applies from FB-0008 is the `[ -z ]` fallback chain. Strong meta-validation: the prove-or-disprove discipline forced the agent to verify the FB-0008 claim against the file before accepting my CHANGELOG line.
- **Parallel-PR collision caught at FB-0008 stale-base preflight before push.** A separate "PR I" (workflow-spawn skip prevention) merged on main during this session — collision discovered at the post-commit stale-base check. Rebased + renumbered to PR J + v1.2.5. This is the FB-0008 gate doing exactly what it was designed to do.
- **PR-G FOLLOW-UP #5 absorbed opportunistically.** Editing `plan-critic.md` anyway; bundling the one-line fan-out hunt addition costs nothing and avoids a separate PR. PR H proper's queue gets one item shorter.
- **Research substrate is the right project-dev investment.** The 3-research-agent parallel pass produced a 12k-word report with 50+ first-party citations that grounded every PR J/K/L decision in published evidence rather than vibes. Worth the token spend on any future architecture-shaping question.

### Flow plugin v1.2.4 — workflow-spawn skip prevention (FB-0010 workflow-step sub-class)  `SAFETY`
**Date:** 2026-05-27
**Branch:** `pr-i/workflow-spawn-prevention`
**Commit:** [SHA at ship time]

**What was done:**
Encoded the 9th FB-0010 incident as a workflow discipline. PR H1's review surfaced that the author ran `gh pr create` directly instead of invoking `/flow:ship`, skipping `/flow:ship`'s Step 2 pipeline (which spawns `/flow:security-review` + `/flow:accessibility-review`). The skip was justified after-the-fact ("would have early-exited anyway") but missed that the `STATUS: SKIPPED` audit-trail signal is load-bearing regardless of body execution.

Defenses encoded across 4 surfaces:

1. **`plugins/flow/skills/staff-review/SKILL.md`** (consumer-shipped) — new "After this skill" footer naming `/flow:ship` as the canonical next step. Reframes the existing "ends with work ready, not merged" line into actionable forward motion. Direct fix for the inflection point where the author would naturally choose between `/flow:ship` and `gh pr create`.

2. **`plugins/flow/skills/ship/SKILL.md` Step 1.0** (consumer-shipped) — visual emphasis (`⚠️` per ASSUMES line) + a new REMINDER paragraph naming the workflow-step silent-skip class explicitly + the "Always invoke /flow:ship, never `gh pr create`" rule.

3. **`plugins/flow/docs/workflow.md` Step 10** (consumer-shipped) — new "Never bypass `/flow:ship` with `gh pr create` directly" subsection. Names the failure mode: skipping `/flow:ship` skips the entire Step 2 (security + a11y reviews); the STATUS: SKIPPED line is load-bearing audit-trail. Canonical reference for the discipline.

4. **`.claude/rules/general.md` Workflow discipline subsection** (project-dev only) — auto-loads on every edit in this repo. Mirrors the workflow.md statement scoped to flow's own dev infrastructure.

Plus CHANGELOG.md v1.2.4 entry + manifest version bump v1.2.3 → v1.2.4 in both `.claude-plugin/marketplace.json` + `plugins/flow/.claude-plugin/plugin.json`.

**Why:**
PR H1's review pipeline missed `/flow:security-review` + `/flow:accessibility-review` entirely until the user caught it. Root cause: I bypassed `/flow:ship` and ran `gh pr create` manually. 1 incident isn't usually enough for FB encoding (FB-0010 was encoded after 6), but the fix is trivially mechanizable as prompt-level reminders. MEDIUM confidence in plan.md names the fallback: if a 2nd workflow-spawn-skip occurs after PR I, the next step is orchestration-level auto-spawn in `/flow:staff-review` (requires session-introspection helper that doesn't exist).

**Design decisions:**
- **Reduced scope from 12 files to 9.** Initial plan included reviewer-skill exit footers on staff-review + critique-plan + audit-plan + audit-completion + log-disagreement (5 SKILL.md files). Reading the latter 4 surfaced rigid `## Output` blocks ("Do not add commentary before or after.") that would conflict with appended footer prose. Reduced to staff-review only. Plan-critic Finding 1 REDIRECT confirmed this independently; Finding 3 BLOCKER (fan-out file count contradiction in the original plan) was also surfaced by plan-critic and validates FB-0010 working on its own defense PR.
- **Primary fix vs defense-in-depth.** Staff-review footer + `/flow:ship` Step 1.0 strengthening + workflow.md Step 10 are primary (directly address the bypass). `.claude/rules/general.md` is defense-in-depth (project-dev only).
- **No orchestration auto-spawn.** Considered auto-spawning security/a11y from `/flow:staff-review` Step 4. Rejected because it duplicates `/flow:ship` Step 2 (drift risk), needs session-introspection that doesn't exist, and prompt-level reminders are the cheap-first defense with auto-spawn as named fallback.
- **v1.2.4 patch-level.** Additive workflow guardrails — no skill behavior, contract, or schema changed.
- **SAFETY marker** because of `plugins/flow/skills/ship/SKILL.md` + both manifests (all on safety.md paths list). Runtime authority unchanged.

**Technical decisions:**
- Workflow.md Step 10 subsection placed BETWEEN pipeline list and "Why the PR opens here" — linear flow: pipeline → discipline → rationale.
- General.md subsection placed AFTER "Consistency discipline" and BEFORE "Autonomous work guardrails" — narrative arc: general → consistency → workflow → autonomy.
- CHANGELOG v1.2.4 entry follows Keep-a-Changelog-style format established in PR H1.

**Tradeoffs discussed:**
- **Encode-after-1-incident vs wait for 2-3.** FB-0010 encoded after 6. This is 1 incident of new sub-class. Decision: encode now because fix is cheap + user explicitly chose this over dogfood-first.
- **Reviewer-skill footer scope.** Wanted footers on all 5; rigid `## Output` blocks on audit/critique skills constrained to staff-review only.
- **Project-dev rule vs consumer-shipped rule.** Considered adding to `plugins/flow/rules/general.md` (consumer-shipped). Decided project-dev only because workflow.md Step 10 already carries the consumer-side contract; adding it as a rule too would be fan-out.

**Lessons learned:**
- **Plan-critic + parallel execution + self-correction converged on the same fix.** Plan-critic returned NOT APPROVED with a BLOCKER (fan-out count contradiction); independently I'd discovered the audit/critique-plan conflict and reduced scope. Two paths to the same answer.
- **FB-0010 self-application caught itself.** Plan-critic flagged "fan-out count contradiction inside the FB-0010 defense PR." The discipline works on its own defense PR. Catching it pre-commit validates the discipline.
- **Discipline-PR for 1-incident class is defensible when fix is mechanical.** Threshold isn't hard; it's "is encoding cost less than expected recurrence cost?" Cheap reminders justify low threshold. Invasive orchestration changes require higher threshold.


### PR H1 — Upgrade docs + CHANGELOG (pre-install shore-up, docs-only at repo root, no version bump)
**Date:** 2026-05-27
**Branch:** `pr-h1/upgrade-docs-changelog`
**Commit:** [SHA at ship time]

**What was done:**
Shipped two cheap fixes from the Tier-2 audit of flow's update infrastructure, before user begins active dogfood across two consumer projects (md-manager + health-tracker):

1. **`docs/upgrade.md` (new)** — the 2-command ritual (`/plugin marketplace update flow` → `/plugin install flow@flow` → `/flow:doctor`), when-to-run guidance, verification via doctor's final-line verdict, 4 troubleshooting cases (marketplace-not-found, missing skills in /help, doctor Section 1 FAIL, unexpected breaking change), optional auto-update opt-in with tradeoff callout, multi-project ritual section.
2. **`CHANGELOG.md` (new, at repo root)** — extracted v1.0.0 through v1.2.3 from the inline README "Versions:" block + history.md entries. Reverse chronological; date + headline + 2-4 bullets + explicit "Breaking changes:" callout per entry. v1.0.0 is the only entry with a real breaking change (install identity changed from `assumption-auditor@llm-auditor` to `flow@flow`). Keep-a-Changelog-style — distinct from history.md format (no SHA/branch/tradeoffs; intentionally terse).
3. **`README.md`** — replaced 6-line inline "Versions:" block with a single line linking to CHANGELOG.md + a separate line linking to docs/upgrade.md. Also added upgrade.md to the "Full bootstrap docs" rail under the Quick Start.
4. **`docs/bootstrap.md`** — appended "When a new flow version ships, pick it up via the 2-command ritual in docs/upgrade.md" to the "What's next" section.
5. **`docs/migration.md`** — appended a "Keeping flow up to date" subsection pointing at upgrade.md.

**No version bump.** Pure docs-at-root changes; `docs/` and `CHANGELOG.md` are not included in the plugin install package (`/plugin install flow@flow` ships only `plugins/flow/*`). Consumers fetch the new docs from GitHub directly. Spares a no-op `/plugin marketplace update` cycle.

**Why:**
User asked "is the update infrastructure solid?" before installing across md-manager + health-tracker. Audit identified Tier-2 gaps:
- Update requires 2 commands consumers must remember; no auto-update by default for third-party marketplaces.
- No CHANGELOG at the canonical repo-root location (per-version notes were buried inline in README + verbosely in history.md).
- No "your installed version is behind" surfacing anywhere.

The first two are mechanizable as docs. The third (silent version drift) is left for PR H proper (FB-0010 FOLLOW-UP #2 — generalize Check 2.5 to a `minFlowVersion` slot + Doctor Check 6) per explicit Scope (out) call.

**Design decisions:**
- **CHANGELOG distinct from history.md (intentional divergence).** history.md retains the verbose internal-tracking format (SHA + tradeoffs + design decisions); CHANGELOG is terse user-facing (date + headline + bullets + breaking-change callout). Plan-critic specifically flagged this divergence as worth naming; spec-walk item 9 makes the divergence explicit so future docs hygiene PRs don't try to merge the two formats.
- **No version bump for docs-at-root.** Verified: `/plugin install flow@flow` packages only the `plugins/flow/*` subtree; root-level `docs/`, `CHANGELOG.md`, `README.md` are read from GitHub directly. Consumers on v1.2.3 get the new docs the moment we merge — no client action. Bumping to v1.2.4 would force a no-op upgrade cycle.
- **Cross-links in 5 places (README × 2, bootstrap.md, migration.md, plan.md).** A CHANGELOG nobody can find is the FB-0005 silent-failure class re-stated. Plan-critic explicitly approved this scope expansion as "polished over partial" per CLAUDE.md quality bar.
- **Multi-project ritual section in upgrade.md.** User's stated use case is 2 active consumer projects. Explicit guidance prevents the "I updated once, why didn't it stick everywhere?" failure mode.

**Technical decisions:**
- CHANGELOG written manually (not auto-generated from history.md or git log). Manual extraction risks drift; MEDIUM confidence verdict #2 flagged this. Mitigation: FB-0010 lens-engineer hunt + Check 2.5 catch survivors at review (and indeed Check 2.5 passed against the current tree post-edit).
- Upgrade.md "Pin to a prior version" troubleshooting uses `cd ~/.claude/plugins/flow && git checkout v1.2.3`. This assumes the plugin install directory is a git checkout (Claude Code's plugin manager treats marketplaces as git repos). If a future Claude Code release changes the install shape, this hint becomes stale — accept the risk; the doc names the assumption.
- Auto-update opt-in example uses the schema documented by Claude Code (`"autoUpdate": true` in `extraKnownMarketplaces.<name>`). Doc surfaces the tradeoff (silent breaking-change exposure) so consumers choose deliberately.

**Tradeoffs discussed:**
- **Bump or no bump?** Considered bumping to v1.2.4 to give consumers a discoverability signal that new upgrade docs exist. Decided against: the docs land on GitHub immediately; a version bump would force no-op `/plugin install` cycles across all consumers; sets a bad precedent (every README polish = version bump = upgrade burden). If consumers report they don't notice the new docs, revisit per the verdict-#1 mitigation.
- **CHANGELOG location.** Considered putting under `docs/CHANGELOG.md`. Decided on repo root — Keep-a-Changelog convention is `CHANGELOG.md` at root, and the file is short enough that root placement keeps it visible on GitHub's repo landing.
- **Manual vs auto extraction.** Auto-extracting from history.md per-version blocks via a script would prevent drift but adds a dependency (script must run on every history.md edit) and complicates docs hygiene. For 6 versions of history, manual is cheaper. Revisit when CHANGELOG hits 15+ entries.

**Lessons learned:**
- Plan-critic ran cleanly in parallel with execution and produced APPROVED + 3 actionable findings (CHANGELOG format spec + file count cleanup + verdict #1 mitigation reword). Folding the 3 into the plan before write-time was cheaper than catching them at review.
- FB-0010 discipline applied to PR H1's own work caught the inline-versions-block-in-README as a fan-out source for the future CHANGELOG; cleaner to delete the inline block than maintain two copies (FB-0010 single-source-of-truth principle).

### Flow plugin v1.2.3 — consistency discipline (FB-0010 defense for the recurring bug class)  `SAFETY`
**Date:** 2026-05-26
**Branch:** `pr-g/consistency-discipline`
**Commit:** [SHA to be filled at ship time]

**What was done:**
Encoded defenses for the most-recurring bug class flow's own development has surfaced — "consistency that depends on author memory" — across 6 incidents (PR 1 stale paths, PR B unset DEFAULT_BRANCH, PR D regex inversion, PR E POSIX/bash mismatch, PR F pass-1 slash-as-shell, PR F pass-2 slot-count fan-out + intra-file contradiction). Specifically:

1. **FB-0010** captures the lesson with all 6 citations. Two flavors named: *silent-skip on edge case* (failure swallowed via `2>/dev/null` / unset-fallback / regex inversion) and *fan-out contradiction* (a count/name/slot referenced in N places, only some updated by a contract change).
2. **`lens-staff-engineer.md`** (consumer-shipped) gains two explicit hunt categories: silent-skip sweep + consistency sweep. The "specifically asks" section adds a grep-after-diff step naming the patterns to search for. The "gotchas" section names the consistency sweep as load-bearing — fan-out contradictions live in unchanged files, so they survive diff-only review.
3. **`/flow:doctor` Check 2.5** (consumer-shipped) compares `jq '.properties | keys | length'` on the schema against any "N slots" claim in CLAUDE.md / README.md / docs/, flagging survivors of a stale count. Cheap mechanical check for the fan-out shape that's actually mechanizable.
4. **`plugins/flow/docs/workflow.md` Step 4** adds a "consistency sweep" paragraph naming the discipline at the preflight stage, before `/simplify` runs.
5. **`.claude/rules/general.md`** (project-dev) adds a "Consistency discipline (FB-0010)" section with the grep-first-edit-second rule + the "If a colleague greps for the old value tomorrow, will they find a contradiction?" check.
6. **README + manifest** bumped to v1.2.3 with version-note explaining the discipline. plugin.json + marketplace.json descriptions updated to reflect the new lens-engineer hunts + the doctor check.

**Why:**
The engineer-lens missed 2 of 6 occurrences first-pass (both fan-out shapes — PR F pass-2 was needed to catch them via adversarial review). Pattern is stable enough across PRs to encode rather than re-derive each time. Costs of encoding (small lens-prompt + doctor-check + workflow.md paragraph + project-dev rule) are dramatically smaller than the cumulative cost of adversarial-second-pass review every PR.

**Design decisions:**
- **Two-layer defense** — consumer-shipped (lens-engineer + doctor) + project-dev (general.md rule). Consumer projects benefit from the same discipline flow uses on itself; flow gets a stronger internal guardrail than just shipping the consumer artifacts.
- **Doctor Check 2.5 is WARN-not-FAIL.** Mismatched documented count is a real signal but doesn't BLOCK install/use; staying WARN keeps the doctor surface low-friction and respects the "[READY with WARN-level items]" path's existing semantics.
- **Lens-engineer hunts are additive, not gating.** The lens still triages BLOCKER/NIT/FOLLOW-UP; the new hunts give it explicit search vocabulary rather than relying on emergent "specifically asks" coverage.
- **Schema as source-of-truth for slot count.** Future contract changes update the schema, and the doctor check + lens grep both derive from that — no third copy to drift.

**Technical decisions:**
- Doctor Check 2.5 uses `grep -rEn '([0-9]+) slots?'` with awk filtering against the schema's actual count. Cheap, portable across BSD/GNU. The `grep -vE ":[[:space:]]*#"` line filters out comment lines so we don't flag `# Schema has 16 slots — see CHANGELOG` style annotations as stale.
- Workflow.md addition lives at Step 4 (Preflight) rather than Step 7 (Staff-review) because the discipline catches the bug class CHEAPER as a pre-simplify sweep than as a lens-agent finding.
- Project-dev rule lives in `.claude/rules/general.md` (auto-loads on `**/*`) rather than `safety.md` (auto-loads only on safety-critical paths). The discipline applies to every edit, not just safety surfaces.

**Tradeoffs discussed:**
- **Mechanizing further** — e.g., a pre-commit grep that does the slot-count check automatically — was considered. Decided against for now: pre-commit hooks add install friction; consumers vary in whether they run hooks; and Check 2.5 in `/flow:doctor` plus the lens-engineer prompt cover the same surface at lower cost.
- **Promotion to a Stop hook** (fail the session if `/flow:critique-plan` was skipped — the existing "honest gap" in CLAUDE.md.template) was also considered for this PR. Decided to scope to consistency-discipline only; Stop hooks are v1.x autonomous-routines work per the spec, and this PR is the rule-of-six trigger for the consistency class specifically, not a broader enforcement-layer redesign.
- **Single big "consistency.md" rule file** vs subsection of general.md was considered. Kept as a subsection because the rule applies on every edit (matching general.md's `**/*` glob) and dedicating a file would split the auto-load mechanism unnecessarily.

**Lessons learned:**
- 5 prior incidents (PRs 1, B, D, E, F-pass-1) all caught by the engineer-lens *eventually*. Only at occurrence 6 (PR F pass-2 — the slot-count fan-out) did the pattern require *adversarial* review to surface. That's the threshold for encoding: when the same lens that should catch it stops catching it reliably, give the lens explicit prompt-level vocabulary for the pattern.
- "Internal contradictions inside one file" (line 22 vs line 260 of doctor/SKILL.md) is a sub-shape of fan-out contradiction that survives even careful single-file review. The discipline rule names it explicitly.
- **SAFETY marker on this entry** is because `.claude-plugin/marketplace.json` and `plugins/flow/.claude-plugin/plugin.json` (both on `.claude/rules/safety.md`'s `paths:` list) had description text and version field changes. Runtime authority is unchanged — no allowedTools/sourcePaths/disable-model-invocation modifications; the changes are version + description prose only. Plus `/flow:doctor` Check 2.5 introduces a new WARN-branch error-handling shape (documentation.md format spec requires SAFETY marker on error-handling changes). Verified via `git diff main` that no authority-bearing keys changed in either manifest.

**Self-review iterations (workflow pipeline ran 6 parallel reviewers — engineer + push-further + UX-designer + design-engineer + security + plan-critic):**
- 2 BLOCKERs caught, both FB-0010 violations inside the PR that adds FB-0010 defenses: (a) `README.md:50` said "6 agents" but the count is 8; (b) `dev-docs/plan.md` "Files touched: 9 files" but Scope (in) enumerated 10. Both fixed inline before push. Validates the discipline's value and proves PR-G defenses applied to PR G itself work.
- 6 cheap NITs fixed in-tree, mostly FB-0010 violations within `/flow:doctor` Check 2.5 itself: schema-not-reachable silent-skip, no-docs-found vacuous PASS, jq-failure unguarded, greedy-sed picking grep-line-number digit, narrow scan-target list (missed CLAUDE.md.template + core-docs/ + dev-docs/), and the "PRs 1, B, D, E, F" undercount vs "6 incidents." A SCAN_TARGETS leading-space word-split bug surfaced only at smoke-test time and was a 7th silent-skip flavor caught by tightening the test matrix.
- 9 FOLLOW-UPs routed to plan.md (deferred deliberately): Defense #4 (silent-skip skill-code pairing), Check 2.5 generalization to skill/lens/rule counts, consumer-shipped consistency rule (`plugins/flow/rules/general.md`), plan-critic.md fan-out hunt addition, CLAUDE.md.template consumer mention, intra-file contradiction detection, schema-path fallback hardening, symlink-following grep hardening, citation drift across files.

### Bootstrap doc — document `allow_auto_merge` prereq for the merge queue
**Date:** 2026-05-25
**Branch:** [next branch off main]
**Commit:** [next commit]

**What was done:**
Added an "Optional — GitHub merge queue" section to `docs/bootstrap.md` (between Step 6 and "What's next") and a matching Troubleshooting entry. Documents the four-step recipe (enable auto-merge → add CI workflow → apply ruleset → queue with `gh pr merge --auto`) and calls out `allow_auto_merge=true` as the load-bearing prereq that produces the `enablePullRequestAutoMerge` GraphQL error if skipped.

**Why:**
Flow's own merge queue setup in the prior history entry hit this exact error mid-flow (`gh pr merge 14 --auto` failed; had to `gh api -X PATCH /repos/by-dev-tools/flow -f allow_auto_merge=true` before queueing worked). md-manager already had it enabled, so the divergence was invisible until flow's first queued PR. Any consumer following flow's lead and setting up a queue will hit the same wall.

**Design decisions:**
- **Placed in `docs/bootstrap.md`, not `plugins/flow/docs/workflow.md`.** Workflow.md is a 413-line loop reference with no GitHub-infra section; expanding its scope to cover repo settings would dilute its purpose. Bootstrap.md already covers GitHub PR setup at Step 6, so this fits naturally as an optional sub-step.
- **Framed as optional, not mandatory.** Flow doesn't ship a merge-queue requirement — it ships a loop. The queue is one of several ways to enforce the loop's "every PR through CI" discipline; consumers without a queue still get the loop's value.
- **Included the four-step recipe inline, not as a separate doc.** Bootstrap.md is already a stepwise recipe; adding another markdown file for one optional configuration would fragment the consumer's read path.

**Technical decisions:**
- Referenced both `by-dev-tools/flow` (Python stdlib CI) and `by-dev-tools/md-manager` (Node CI) as reference workflows so consumers can pick whichever matches their stack.
- The ruleset-copy instruction points at `gh api /repos/by-dev-tools/flow/rulesets/<id>` rather than embedding a JSON payload — the payload is long and would drift if the source ruleset evolves.

**Tradeoffs discussed:**
- Inline section vs. standalone `docs/merge-queue.md`. Standalone would be easier to deep-link but adds a file for ~30 lines of content; the bootstrap reader is already in the right mental context for "PR machinery setup". Kept inline.
- Whether to also add this to `template/base/README.md.template`. The template is project-generic README boilerplate (consumer's own README), not flow's setup docs — would be confusing to inject flow-specific GitHub setup into a project README scaffold. Skipped.

---

### CI workflow + merge queue ruleset on main — mirror md-manager structure  `SAFETY`
**Date:** 2026-05-25
**Branch:** claude/charming-goldwasser-f8a7b2
**Commit:** [this PR]

**What was done:**
1. Added `.github/workflows/ci.yml` with two jobs (`evals`, `security`) triggered on `pull_request:` + `merge_group:`. Both run Python stdlib invocations of the existing eval runners — no new deps. Concurrency-grouped on event + ref so superseded runs cancel.
2. Applied a GitHub ruleset on `main` mirroring md-manager's structure: deletion-block, non-fast-forward, required linear history, PR-required with squash-only merges (0 required reviewers), required status checks (`evals` + `security` — 2 contexts vs md-manager's 3, since flow's testable surface is different), and a merge queue (squash, ALLGREEN grouping, max 1 build / max 5 merge / 5-min wait / 60-min timeout). Every parameter on every rule matches md-manager exactly except the status-check context names + count, which differ by design.
3. **`SAFETY`** — wired 3 missing check types into `plugins/flow/evals/run_evals.py` (`severity`, `finding_count`, `reference_rule_contains`) so the 3 plan-critic fixtures (`scope_drift_form_fix`, `spec_violation_bundled_ui`, `internal_incoherence_jwt_migration`) stop failing under the runner. These keys were already in `ground_truth.yaml` from PR 1 but had no rule implementation; the runner returned `unknown=<key>` for them. Now: `severity` matches `· {value lower} ·` in output, `finding_count` regex-counts `^ISSUE(\s+N)?\s+·` lines on raw output, `reference_rule_contains` substring-matches the value in lowercased output. Existing pass/skip behavior preserved for the 5 other cases.

**Why:**
md-manager has a merge queue; flow had no branch protection, no CI, and no merge queue. Setting it up "in the same way" gives flow the same shipping discipline: every PR must clear evals + security before landing, merges are squash-only, history stays linear. This is the lightest layer of the loop's mechanical gates — feedback compounds when every change is forced through the same pipeline.

**Design decisions:**
- **`evals` + `security` as required checks** (vs. only `security`, vs. no required checks). User picked both. Required also fixing the 3 broken eval cases — a one-edit fix that lets the regression surface ship as a real gate from day one rather than as a follow-up.
- **No required reviewers (0).** Mirrors md-manager. Solo-dev cadence; the loop's human gate is plan approval, not PR review.
- **Squash-only.** Mirrors md-manager. Keeps `main` linear and each PR atomic.
- **Merge queue grouping = `ALLGREEN`** with `max_entries_to_merge: 5` and `min_entries_to_merge_wait_minutes: 5`. Mirrors md-manager exactly — at flow's volume, batching is unlikely to fire, but the config is identical so behavior is predictable when it does.

**Technical decisions:**
- **Eval harness check additions kept minimal** — three small `if key == …` branches in `check_required`. No restructuring of the dispatch, no new helper functions, no changes to `load_ground_truth` or `render_context`. The runner's exit-code contract (0 if no failures, 1 otherwise) is preserved.
- **`finding_count` counts on raw `output`**, not lowercased `text`, because `ISSUE` is uppercase in the schema and the regex is anchored on it. Other checks use lowercased `text` for case-insensitive substring matching, consistent with prior keys.
- **Workflow runs `python3` directly** (no `pip install`); flow declares stdlib-only.
- **Ruleset applied via `gh api POST /repos/by-dev-tools/flow/rulesets`** with the JSON payload structurally identical to md-manager's except in the `required_status_checks` list — md-manager has 3 contexts (`typecheck`/`build`/`test`); flow has 2 (`evals`/`security`).

**Post-ship audit findings (retroactive `/flow:security-review` + `/flow:audit-completion` against PR #14):**
- **Audit-completion finding 1 — Unverified completion** ("ready to merge via the queue"): CI green on `pull_request:` event ≠ behavioral verification of the queue. End-to-end merge-queue exercise (PR enters queue → `merge_group:` CI fires → PR lands) is the missing check. Action: hold the "ready" claim to "ruleset + CI in place; queue path untested" until PR #14 is actually queued.
- **Audit-completion finding 2 — Unverified completion** ("byte-for-byte"): corrected above. The required-status-checks list differs in size (2 vs 3) and contents by design; "structurally identical except for status-check contexts" is the accurate framing.
- **Security NITs:** (a) `actions/checkout@v4` / `actions/setup-python@v5` use major-version pins rather than commit SHAs — matches md-manager's posture deliberately; tightening pinning is a project-wide policy choice, not a flow-only one. (b) `python-version: '3.11'` hardcoded across two jobs — fine; multi-version matrix only needed if/when version-compat issues surface. No BLOCKERs found.

**Tradeoffs discussed:**
- Required checks set: only `security` (no eval-fix scope) vs. both (fix evals first). User picked both → fixed evals.
- Whether to gate the merge queue on a CI workflow that didn't yet exist on `main`. GitHub evaluates required status checks against PR head / merge_group SHAs, not historical default-branch runs, so applying the ruleset alongside the workflow PR works — this PR's own merge_group run satisfies the gate.

**Lessons learned:**
- The `unknown=<key>` failures from `run_evals.py` had been latent since PR 1 — running the harness end-to-end exits 1 today on `main`. Worth treating that exit code as part of the PR-1 acceptance bar in retrospect; the merge queue setup surfaces it for free.

---

### Flow plugin v1.2.0 — template directory + bootstrap docs + PR-2 follow-up absorption (PR 3 of extraction umbrella)
**Date:** 2026-05-25
**Branch:** pr3/template-directory
**Commit:** 215c875..[push] (7 phase commits; PR opened at Phase 8)

**What was done:**
Shipped the consumer-side scaffolding so a new project can adopt flow in ~10 minutes per `docs/bootstrap.md`. Three deliverable surfaces:

1. **`template/base/`** (11 files) — Tier 1 (CLAUDE.md.template, README.md.template, flow.config.json.example, .claude/settings.json.example, .claude/rules/safety.md.template, .gitignore.template) + Tier 2 (5 core-docs scaffolds with format headers: spec, plan, roadmap, history, feedback).
2. **`template/stacks/{web,swift,tauri-rust-ts}/`** (16 files) — per-stack overlays: preflight runner (web/tauri = .mjs; swift = .sh), CI workflow yaml, `.gitignore.append`, UI rules (web + tauri), dev-server rule (web + tauri), link skill (web + tauri), swift safety.md.append.
3. **`docs/bootstrap.md`** (NEW projects, ~8 KB) + **`docs/migration.md`** (EXISTING projects, ~11 KB; renamed PR A/B/C → Stage 1/1.5/2 to eliminate umbrella numbering collision).

Plus absorbed 2 PR-2 FOLLOW-UPs as security regression fixtures:
4. **`plugins/flow/evals/security/test_cwd_constraint.py`** — 4 strong asserts on `extract_session.py` `--reference-paths` defense (rejects absolute outside-cwd via content-sentinel check, accepts with opt-out, accepts under-cwd, rejects dotdot traversal).
5. **`plugins/flow/evals/security/test_malicious_config.py`** — 3 asserts on `flow.config.json` shell-meta handling (jq -r is string-safe across 10 string slots, sh -c "$TYPECHECK" executes per documented trust model, critique-plan referenceGlob preserves literal string in quoted-arg form).
6. **`plugins/flow/evals/run_security_evals.py`** — discovery-based runner companion to `run_evals.py`.

Plus schema slot #14 added: **`rustWorkspaceDir`** (consumer of the tauri preflight script that was dead per FB-0003 rule).

Manifest bump: v1.1.0 → v1.2.0 (additive; no breaking changes).

Phased execution (Phases 1-8, all success criteria verified):

- **Phase 1:** Schema slot enumeration; md-manager web-stack signal survey (npm scripts, settings.json hook patterns, .gitignore baseline). 4 observations recorded; per-PR plan committed.
- **Phase 2:** template/base/ Tier 1 (6) + Tier 2 (5). Placeholder consistency verified (caught + fixed `INSTALL_STEPS` vs `INSTALLATION_STEPS` inconsistency pre-commit).
- **Phase 3:** 3 stack overlays. node --check on the .mjs runners; bash -n on the swift .sh runner; ci.yml structural grep.
- **Phase 4:** bootstrap.md (~7.9 KB, 6 steps, covers 3 stacks) + migration.md (~11.2 KB, 3 stages with validation gate at Stage 1.5). Migration deletion list verified against md-manager-pr4-6-spec.md (12/12 expected items).
- **Phase 5:** 2 security fixtures + runner. Bug caught + fixed during execution (parents[3] → .parent.parent.parent in path derivation). All 7 asserts pass.
- **Phase 6:** Bootstrap verification — followed `docs/bootstrap.md` Steps 1-5 from scratch in `/tmp/flow-bootstrap-smoke/` for the web stack. Plugin loaded; 5 user-visible skills surfaced via `/help`; preflight chain ran end-to-end (typecheck pass; build + test fail as expected for empty smoke project, demonstrating the gate contract works); claude plugin validate clean. Swift + tauri preflight runners verified syntax-only (no Xcode/cargo env in this session). All template paths referenced by bootstrap.md resolved (12/12).
- **Phase 7:** Dogfood via 3 parallel lens Agents (engineer+simplify combined, push-further, security; skipped UX-designer + design-engineer + accessibility with explicit reason — pure docs+template+JSON-example surface). Caught 4 BLOCKER + 9 NIT + 4 FOLLOW-UP findings; all BLOCKER + NIT fixed in commit `33428e6`; FOLLOW-UPs routed to dev-docs/plan.md.
- **Phase 8:** This entry. Manifest bumped 1.1.0 → 1.2.0; history.md + plan.md + feedback.md FB-0004 written; PR opens at end of phase.

**Why:**
PR 3 of the flow extraction umbrella. After PR 3 ships, md-manager (the canonical reference consumer) can run PRs 4 → 5 → 6 against a complete v1.2.0 surface — install non-breaking using the template, dogfood, then delete duplicates. Without PR 3, md-manager PR 4 has nothing to derive its `flow.config.json` shape from. Now flow ships its own consumer scaffolding.

PR 3 also absorbs 2 of the 8 PR-2 FOLLOW-UPs (the eval coverage items) because PR 3 was touching the eval surface anyway — closes them as concrete tests rather than open promises.

**Design decisions:**

- **3 stacks for v1.2.0 (web / swift / tauri-rust-ts), not more.** Matches the umbrella's stated targets. Python / Go / Rust-only / Ruby / etc. defer to v1.3+ if/when consumers ask. Shipping 3 well > shipping 7 thinly.
- **Tier 1 + Tier 2 base split.** Tier 1 = required for any consumer (CLAUDE.md, flow.config.json, settings.json, safety.md, README, .gitignore). Tier 2 = recommended-but-shippable-empty core-docs scaffolds (spec/plan/roadmap/history/feedback) with format headers. Consumers who want flow but don't care about the doc discipline can skip Tier 2. Tier 1 is non-negotiable.
- **Bootstrap docs as 6 numbered steps, not collapsed to 4.** Push-further lens suggested collapsing install+copy and verify+smoke. Held the 6-step shape: each step has a different verification outcome; collapsing would compress two distinct cognitive transitions into one. PR 4 dogfood will surface whether the step count feels heavy in practice — FB-0004 captures the watch-this-pattern signal.
- **`$comment-*` keys in flow.config.json.example.** Push-further suggested replacing with a sibling `.example.md` cheat-sheet. Held: putting docs in a separate file means consumers hold two files in their head during bootstrap. The bootstrap step explicitly tells them to strip the comments. FB-0004 captures this for PR 4 reconsideration.
- **Migration Stage 1/1.5/2 naming, not PR A/B/C.** Push-further caught the umbrella numbering collision (PR 4/5/6 in flow's plan vs PR A/B/C in migration doc). Stage names match the parenthetical labels the doc already used.
- **`.claude/settings.json.example` documents intentional divergence from default-hooks.json.** Initially claimed "pulled from" — false. Switched to "modeled on … differs intentionally" + named the differences (POSIX case vs bash [[]] + omitted *.pem/*_rsa patterns). Replicating default-hooks.json verbatim was the alternative; chose documented-divergence because the template needs POSIX-portability and the omitted patterns produced false positives in earlier consumer feedback.

**Technical decisions:**

- **Preflight scripts share the same shape pattern (loadConfig → runGate → summary) but ship as 3 separate files**, one per stack. Push-further routed "shared helper library" as FOLLOW-UP — defer until a 4th stack lands or until an existing stack's preflight needs a behavior change that has to land in all three.
- **Security fixtures live under `plugins/flow/evals/security/`**, separate from `plugins/flow/evals/fixtures/` (auditor regression). Different runner (`run_security_evals.py`), different shape (assert-on-exit-code, not assert-on-rendered-text). Avoids polluting the auditor harness's contract.
- **Strong asserts on content sentinels, not path strings.** PR-3 engineer-lens caught that `assert "/etc/hosts" not in stdout` is vacuous (leak prints `127.0.0.1`, not the path). Switched both rejection + accept tests to content-sentinel checks. **FB-0004** captures the rule.
- **`cp -n` (no-clobber) in all bootstrap recipes.** Security NIT: a user who misreads bootstrap.md as suitable for an existing project would silently clobber CLAUDE.md / README.md / .gitignore. -n + an explanatory note + a pointer at migration.md closes the foot-gun.
- **`rustWorkspaceDir` slot landed in v1.2.0 schema (not deferred).** Engineer NIT: the tauri preflight already read the slot; documenting it inline closes the FB-0003 schema-without-implementation gap (in the wrong direction — implementation-without-schema). Pair landed.

**Tradeoffs discussed:**

- **Skip UX/design-engineer/accessibility lenses in Phase 7 dogfood vs run them anyway.** Skipped with explicit reason: PR 3 is pure docs+templates+JSON-examples — no visual surface, no UI code. Running them would have produced empty reviews (per the staff-review SKILL's "Don't skip a lens... legitimate skip is when a lens genuinely doesn't apply"). Logged explicitly rather than skipped silently.
- **`cp -n` vs `cp --backup=numbered`.** Picked `-n` (skip-existing). `--backup` would preserve clobbered files as `.~1~` versions but adds complexity for the common case (fresh project — nothing to backup).
- **Stage 1.5 vs Stage 2 numbering.** Considered just three stages (1/2/3). Picked Stage 1/1.5/2 because the dogfood gate (Stage 1.5) is structurally a checkpoint, not a deliverable PR like Stages 1 + 2 — the half-step naming reflects that.
- **Bootstrap.md vs migration.md as two files** vs one merged "adopting flow" doc. Two files = clearer entry point for each audience (the first paragraph of each doc tells you whether you're in the right place). Migration doc is 50% longer than bootstrap; merging would dilute both.

**Lessons learned:**

- **Vacuous-pass test asserts are a class of bug only adversarial review catches.** test_absolute_outside_cwd_rejected initially asserted on `"/etc/hosts" not in stdout` — passes trivially because a leak prints content, not the path string. Engineer lens flagged it as a BLOCKER. FB-0004 captures the rule: when writing security regression tests, the assert must check on the THING THAT WOULD LEAK, not on a proxy for it.
- **Schema slots without consumers and consumers without schema slots are symmetric bugs.** PR 2 caught `memoryHardCap` documented-but-not-read; PR 3 caught `rustWorkspaceDir` read-but-not-documented. Both surface the same way: dogfood, not greps. Pre-commit grep recipe from FB-0003 needs the bi-directional version (every consumer reference must have a schema entry AND vice versa).
- **Push-further lens caught two structural design questions (collapsing bootstrap steps, replacing $comment keys with sibling cheat-sheet) that benefit from real-consumer signal before settling.** Held both; routed to plan.md "PR 4+ follow-ups" so md-manager's PR 4 dogfood can pressure-test them. This is the lens working correctly — surfacing direction-worthy questions, not demanding immediate change.
- **Per-phase commits + per-phase verification + per-phase task-list updates compounded.** When Phase 7's lens reviews surfaced 4 BLOCKERs, locating each one took seconds (each was in a specific phase commit's diff). Monolithic commits would have made the dogfood loop more expensive.

### Flow plugin v1.1.0 — workflow surface backfill (PR 2 of extraction umbrella)
**Date:** 2026-05-24
**Branch:** pr2/workflow-backfill
**Commit:** 25ef3bc..ef8fd32 (7 phase commits + dogfood fix commit; PR pending push to push at end of Phase 8)

**What was done:**
Backfilled the `[PR 1 LIMITATION]` placeholders inside `plugins/flow/skills/ship/SKILL.md` (step 2 security+a11y reviews; step 4b memory machinery) and ported the rest of the workflow surface from md-manager. The plugin now covers the full canonical 11-step loop end-to-end. 13 new shipped artifacts + 3 modified existing artifacts + manifest version bump.

Phased execution (Phases 1–8):

- **Phase 1:** Fetched 12 md-manager sources via `gh api` in parallel. Refined the handoff plan with 4 observations: staff-review extraction is more structural than handoff implied; security/a11y reviews carry heavier md-manager tokens; all 4 source skills start step numbering at 0; ship-spike references nonexistent `tools/preflight/check.mjs`. Committed plan refinement; user direction was "execute autonomously per success criteria" so no separate user-gate beyond the original PR-2-plan approval.

- **Phase 2:** Ported `/flow:security-review` and `/flow:accessibility-review`. De-projected (stripped 'markdown-notes app', 'Vite + React + TypeScript', src/lib/markdown.ts, `--sand-9`, `--page-text-quiet`). Added `uiSurface=false` skip-early gate to accessibility-review for backend-only consumers. Config-slot doc paths throughout. All locked PR-1 idioms applied.

- **Phase 3:** Extracted 4 lens prompts from md-manager's inline `staff-review/SKILL.md` (14.3KB single file) into separate plugin-shipped agent files (`lens-staff-engineer.md`, `lens-ux-designer.md`, `lens-design-engineer.md`, `lens-push-further.md`). Each agent has frontmatter + Inputs + Hunts + Specifically-asks + Triage scheme + Output format + Gotchas. Push-further lens's "Nothing to push — surface at ceiling for its scope" escape hatch preserved verbatim (load-bearing restraint contract).

- **Phase 4:** Ported `/flow:staff-review` as a pure orchestrator. The SKILL spawns 4 parallel `Agent` calls with `subagent_type: lens-{staff-engineer,ux-designer,design-engineer,push-further}`. File grew from md-manager's 14.3KB → only 12.9KB despite adding all the consumer-side config-slot scaffolding (the lens content extraction worked; the file is just slightly under what an orchestrator + scaffolding needs).

- **Phase 5:** Ported the remaining 9 artifacts in one phase: `/flow:ship-spike` (lightweight spike pipeline), `/flow:workflow-help` (new skill — prints loop + project config + skill catalog), `planner` + `docs` context-isolation agents (de-projected to read paths from spawner-injected slots), 4 portable rules (`general.md`, `plan-discipline.md`, `documentation.md`, `exploration.md`), `tools/memory/check.mjs` (canonical-path derivation with Claude-Code-worktree slug scoring added), `flow.config.schema.json` (13 slots — 2 more than the handoff estimated: `designLanguagePath` + `branchPrefix` per actual SKILL needs and the md-manager spec call-out), and `default-hooks.json` (2 PreToolUse hooks — sensitive-file write blocker + path-validation warn-only). Manifest bumped to v1.1.0.

- **Phase 6:** Backfilled `/flow:ship` placeholders with real `Skill('flow:security-review')` + `Skill('flow:accessibility-review')` invocations (step 2) and the full 6-substep memory machinery (step 4b). Addressed both PR-1 FOLLOW-UPs: `critique-plan` SKILL now reads `flow.config.json.referenceGlob` (default `core-docs/*.md`); `extract_session.py` rejects out-of-cwd `--reference-paths` by default with stderr message, opt-in via `--allow-external-paths`. Verified empirically (created minimal session file, tested `/etc/hosts` rejection-then-acceptance).

- **Phase 7:** Dogfooded PR 2 through the newly-built `/flow:staff-review` lens orchestration. Spawned 4 parallel Agent subagents (engineer + UX-designer + push-further + security) on PR 2's own diff. Skipped design-engineer (no visual surface) + accessibility (uiSurface=false in flow's own repo) with explicit reason. Caught 2 BLOCKERs (`Skill` missing from ship.md `allowed-tools`; `memoryHardCap` schema slot dead) + 11 NITs + 8 FOLLOW-UPs. All BLOCKERs + NITs fixed in-tree. FOLLOW-UPs routed to `dev-docs/plan.md` § "PR 3+ follow-ups from PR 2 review".

- **Phase 8:** This entry. Doc synthesis (history.md + plan.md + feedback.md FB-0002 + FB-0003). Will verify md-manager-pr4-6-spec.md accuracy against shipped surface, then push + open PR.

**Why:**
PR 2 of the flow extraction umbrella. After PR 2, a consumer project with `flow.config.json` set can run the full 11-step loop using only `/flow:*` skills + Claude Code bundled natives (`/simplify`, `/batch`, `/debug`, `/loop`, `/claude-api`). The plugin is feature-complete for v1 — PR 3 ships the consumer-side template directory; PRs 4–6 migrate md-manager.

**Design decisions:**

- **Lens prompts extracted to separate agent files** (vs kept inline in staff-review SKILL): more modular (each lens individually invocable), the orchestrator is more readable, and lens prompts can be versioned independently. Trade-off: introduces a new subagent_type dispatch pattern that wasn't smoke-tested in plugin context before this PR. Mitigated by dogfooding in Phase 7 (which succeeded).

- **`workflow-help` is a new skill, not a port.** md-manager has no equivalent. Designed as the onboarding front door: prints the canonical 11-step loop + resolved project config + skill catalog + bundled-native annotations + project-shaped-surface list. Push-further lens correctly flagged that the first version jumped straight to a step list — added "Flow is a managed-autonomy loop: ..." opening sentence in Phase 7.

- **13 slots in `flow.config.schema.json`, not 11.** Handoff estimated 11. Added `designLanguagePath` (read by staff-review UX + design-engineer + push-further lenses + a11y-review for grounding) and `branchPrefix` (called out in md-manager spec as needed; landing now since the cost is one schema entry). Both must have at least one consumer wired in to avoid the FB-0003 "schema-without-implementation" anti-pattern.

- **Hooks are opt-in, not auto-applied.** `plugins/flow/hooks/default-hooks.json` ships the patterns; consumers merge them into their project's `.claude/settings.json` (template/settings.json.example in PR 3 will do this by default). Both hooks are warn-only or block-on-clear-pattern (Edit|Write sensitive-file matcher exits 2); neither blocks arbitrary actions.

**Technical decisions:**

- **`sh -c` over `eval` (idiom locked in PR 1)** applied to all 4 new typecheckCmd consumers (ship, ship-spike, staff-review, security-review, accessibility-review). Subshell isolation; trust boundary documented at each call site.

- **`${CLAUDE_PLUGIN_ROOT}` for all cross-file references in shipped prompts (idiom locked in PR 1)** applied universally. The 13 cross-file refs in PR 2's new artifacts all use the dynamic form. Three legitimate documentation references to `tools/preflight/check.mjs` remained un-prefixed because that path is CONSUMER-shipped (not plugin-shipped) — documented in commit messages.

- **Memory tool path derivation**: ported from md-manager's `tools/memory/check.mjs` with added scoring penalty for `-claude-worktrees-` slugs (parallel to the existing `-conductor-workspaces-` penalty), so the harness's canonical project path wins over the worktree path. The auditMarker lives next to the script (per-install, not per-project) — documented in the script's top-of-file comment as acceptable for v1.1 with a v1.2 revisit if cross-project misalignment surfaces.

- **`extract_session.py` cwd constraint via `Path.resolve()` + `relative_to()`**: defeats symlink-following attacks (Path.resolve canonicalizes the path) AND `..` traversal (relative_to raises ValueError for out-of-tree paths). Verified empirically by the security lens reviewer with symlinks pointing outside cwd. The `--allow-external-paths` opt-out is only settable via explicit CLI flag.

**Tradeoffs discussed:**

- **Lens extraction (Option B, this PR) vs keep inline (Option A, md-manager's pattern):** chose extraction. Cost: one more layer of indirection at spawn time; introduces a `subagent_type` contract that wasn't pre-validated. Benefit: modular lenses, individually invocable, orchestrator file is readable rather than buried under 12KB of prompt content. Fallback would have been single-commit reversion if Phase 4 smoke-failed — it didn't.

- **`memoryHardCap` wire vs drop the slot:** engineer lens caught it as dead (schema doc says configurable, check.mjs hardcoded 30). Choices: (a) wire check.mjs to read the slot, (b) drop the slot from schema. Wiring is the better fix — the schema documents it as configurable for a real reason (consumers with bigger memory corpora) and the implementation cost is ~15 lines. Same calculus for `branchPrefix` (wired to ship + ship-spike branch creation).

- **Skill descriptions: trigger-quality vs body-completeness:** UX lens caught that `/flow:security-review`'s description didn't mention the doc-only skip — the auto-trigger machinery would fire on doc-only diffs that mention "rendering" in prose, then skip — wasted spin-up. Added "Skips doc-only diffs" to the description. Tradeoff: longer description, slightly more parse cost, but cleaner trigger contract.

- **Reviewer-notes template ellipses vs explicit null-finding:** UX lens caught that `_Findings:_ ...` reads as unfilled placeholder. Replaced with explicit empty-shape pattern (`Nothing of consequence` / `—`). Tradeoff: slightly more verbose; clearer signal to human reviewers.

- **Hook 2 known bypasses (warn-only vs hard-enforce):** Security lens noted bypasses (python -m, env-var indirection, equals-form arg). Choices: (a) widen regex to catch more, (b) drop the hook entirely, (c) keep warn-only and document bypasses. Chose (c) — the in-script `cwd` constraint in `extract_session.py` is the load-bearing defense; the hook is documented as belt-to-braces. Consumers wanting hard enforcement can change `exit 0` → `exit 2`.

**Lessons learned:**

- **Dogfooding caught 2 BLOCKERs that all the pre-commit greps + claude plugin validate + smoke test missed.** Specifically: (1) Skill missing from ship.md allowed-tools — runtime-only failure; (2) memoryHardCap dead slot — semantic mismatch between schema doc and implementation. Both classes are now FB entries (FB-0002 and FB-0003). The pattern is the same as PR 1's discovery that stale `agents/auditor.md` refs in shipped prompts survived the cold-read: only running the loop end-to-end exposes the surface.

- **The bootstrap exception is now FULLY lifted for PR 3+.** All review skills exist + work. Future PRs in the umbrella should walk themselves through `/flow:staff-review` + `/flow:security-review` (+ `/flow:accessibility-review` for UI work) WITHOUT having to spawn Agent subagents manually — the SKILLs themselves do that.

- **Per-phase commits with co-author trailer made the dogfood traversable.** When the engineer lens flagged the `Skill` missing from `allowed-tools`, locating the change took seconds (it was in Phase 6's commit message verbatim). Monolithic commits would have hidden the regression in noise.

- **Schema design needs the "every slot has a consumer" check.** Two of 13 slots in v1.1.0's first commit had no consumer — caught by engineer lens, fixed in Phase 7. FB-0003 captures the rule. The check can be a pre-commit grep; should land as a one-liner in flow's own preflight when that exists.

### Flow plugin v1.0.0 — restructure + rename + initial workflow surface (PR 1 of extraction umbrella)
**Date:** 2026-05-24
**Branch:** claude/trusting-jackson-0de7f4
**Commit:** d3517dc..65a0a58 (9 commits; PR https://github.com/by-dev-tools/flow/pull/5)

**What was done:**
- Repo restructured from flat root (`agents/`, `skills/`, `scripts/`, `evals/`, `DISAGREE.md`) into Anthropic's marketplace + plugin shape: `.claude-plugin/marketplace.json` at root; `plugins/flow/*` for the plugin (manifest, agents, skills, scripts, evals, docs, DISAGREE).
- Marketplace renamed `llm-auditor` → `flow`; plugin renamed `assumption-auditor` → `flow`; both URLs updated to `by-dev-tools/flow`.
- Plugin version bumped 0.3.0 → 1.0.0 to mark the rename + expanded scope (workflow loop, not just audit/critique).
- New shipped surface: `plugins/flow/skills/ship/SKILL.md` (ported from md-manager's `.claude/skills/ship/SKILL.md` per a locked PR-1 port table — 3a active, 3b placeholdered, security+a11y placeholdered, loud-warning typecheck, default-branch fallback chain) and `plugins/flow/docs/workflow.md` (ported canonical 11-step loop, de-projected, bundled-Claude-Code skills annotated, flow-internal audit/critique skills annotated).
- Disagreement storage path renamed `~/.claude/plugins/data/assumption-auditor/disagreements/` → `~/.claude/plugins/data/flow/disagreements/`. Pre-existing records on disk become orphaned; README documents the `mv` migration.
- This repo's own dev-tracking moved `core-docs/` → `dev-docs/` to keep `core-docs/` free as the name for consumer-template scaffolding shipping in PR 3.
- README + CLAUDE.md rewritten for the marketplace identity + three-surface boundary (plugin artifacts / dev-tracking / project-dev infra).
- `.claude/rules/safety.md` rewrote its `paths:` frontmatter for the new safety-critical surface under `plugins/flow/*` and added `plugins/flow/skills/ship/SKILL.md` as new published surface. `general.md`, `documentation.md`, agents, project-dev skills all updated `core-docs/` → `dev-docs/`.
- Recovery anchor: pushed git tag `pre-flow-plugin` at `8857ebd` so the flat-root layout is recoverable forever.

**Why:**
PR 1 of the flow plugin extraction umbrella (canonical plan: md-manager `core-docs/plan.md` § "Flow plugin extraction"). The umbrella exists to make the managed-autonomy workflow installable as a Claude Code plugin so md-manager + designer + future consumer projects don't each carry their own copy of the loop's skills/rules/agents. PR 1 specifically converts this repo (the renamed llm-auditor) from a single-plugin flat-layout to the marketplace + plugin shape Anthropic documents, plus lands the workflow surface that the bundled reviewers will ride alongside.

**Design decisions:**
- **Bundling audit/critique inside flow** (not a separate `assumption-auditor` plugin sibling): they're used with the workflow skills 100% of the time; separation imposed install friction without compositional value. Recorded as Decision 2 in `core-docs/handoffs/flow-plugin-consolidation-2026-05-23.md` (md-manager).
- **One repo for marketplace + plugin + (future) template**: matches Anthropic's `claude-plugins-official` pattern and is explicitly documented as supported. Avoids the maintenance cost of multiple repos.
- **`dev-docs/` for plugin self-tracking; `template/core-docs/` reserved for consumer scaffolding (PR 3)**: keeps the consumer-vs-plugin distinction visible. Without this, future sessions would conflate "flow's dev-tracking" with "what flow ships to consumers."
- **Loud-warning pattern for unset config slots** (not silent no-op): false-affordance risk if `/flow:ship` silently skipped a missing `typecheckCmd`. The warning leaves trace evidence.
- **Default-branch fallback chain (`git symbolic-ref` → `flow.config.json.defaultBranch` → literal `main`)**: works in every repo without project setup; respects override if the consumer configures it.

**Technical decisions:**
- **`source: "./plugins/flow"` with no `pluginRoot`** (not `pluginRoot: "./plugins"` + `source: "flow"`): both forms are documented but coexistence is ambiguous. Validator passes both individually; engineer-lens review during PR walked-through caught the redundancy. Single-form keeps the manifest cleaner.
- **Shipped prompts reference paths via `${CLAUDE_PLUGIN_ROOT}/...`** (not relative paths like `agents/auditor.md`): dynamic resolution works regardless of install location; relative paths broke when the file moved to `plugins/flow/agents/`. Engineer-lens caught two cases (plan-critic.md + critique-plan/SKILL.md) the initial cold-read missed.
- **`sh -c "$TYPECHECK"` over `eval "$TYPECHECK"`**: subshell can't mutate caller-process state. Mildly stronger isolation; trust model is unchanged (project owns its own `flow.config.json` like `package.json` scripts). Security-lens recommendation.
- **`git mv` for every restructure move** (not delete + create): preserves blame across the move boundary. Single commit with 29 renames as the restructure step.

**Tradeoffs discussed:**
- **Renaming surface vs preserving install continuity**: rename breaks existing user installs of `assumption-auditor@llm-auditor` until the user re-runs `/plugin marketplace add` + updates `~/.claude/settings.json`. Accepted because there's a single user (sole consumer); coordinated one-line settings.json edit is the migration cost. Flagged in PR body.
- **Disagreement-storage-path rename vs orphaning records**: chose rename + README migration instructions over the alternative (dual-write to both old and new paths). Local debug/dev data, sole consumer, trivial `mv`.
- **Step 0 vs Step 1 numbering in /flow:ship**: initially numbered 0–7 (Pre-flight as 0 to signal it's a gate, not work). Push-further lens caught it as a materiality scratch — readers process docs top-to-bottom, not as developers reading off-by-one. Renumbered 1–8.
- **README cheat-sheet vs single-source-of-truth**: initially duplicated the 11-step ASCII block verbatim across README and workflow.md. Push-further lens caught it. Replaced README block with a one-line arrow flow + pointer; workflow.md is the canonical source.
- **Whether to retroactively run plan-critic on the plan I wrote**: yes, as dogfood. Verdict: APPROVED. No findings. First evidence that flow's own bar is consistent with this work.

**Lessons learned:**
- **Cold-read pass missed two stale path references** (`agents/auditor.md` in shipped prompts) that the engineer-lens review caught. The pre-PR cold-read grepped for `core-docs/` and `md-manager` tokens but not for bare `agents/` references — those slipped through. Adding "grep for bare `agents/` / `skills/` / `scripts/` / `evals/` references in shipped artifacts" to the next cold-read recipe would catch the same class.
- **Validator-passes ≠ manifest-clean**. `claude plugin validate` accepted `pluginRoot` + absolute `source` coexisting, but the shape was ambiguous. Always-on validators catch syntax; ambiguous-but-syntactically-valid shapes need lens-level review. (This is the kind of finding that would earn an agent-memory entry once PR 2's memory machinery exists — surfacing under "Lessons learned" instead.)
- **Per-phase commits with the co-author trailer made the cold-read trivial** to traverse. Step C's manifest rename commit was 28 lines; reviewing it after the fact took seconds. Monolithic restructure commit would have buried real issues under thousands of unchanged-content rename lines.
- **The /ship pipeline's own walk-through caught issues the pre-merge cold-read missed.** Three BLOCKERs and two cheap NITs found by the lens reviews, all fixed in a single follow-up commit. This is the "review pipeline catches what cold-reads miss" data point that motivated bundling the workflow surface into flow in the first place — meta-validation by dogfooding.

### Auto-invoked disagreement loop for v0.3.0
**Date:** 2026-05-15
**Branch:** v0.3.0-disagreement-loop
**Commit:** 5a3038f

**What was done:**
Closed the feedback loop on the auditor and plan-critic so users can register disagreement with a specific finding in plain language, without invoking a slash command. The plugin now ships an auto-invoked `log-disagreement` skill that the model triggers when it detects pushback on a recent finding, captures the session window and dispute metadata to user-scope storage, and confirms the capture in a single line.

Concrete artifacts:
- `skills/log-disagreement/SKILL.md` — model-invokable skill (`disable-model-invocation` omitted; default behavior allows the model to invoke). Description lists explicit invocation triggers (plain-language disagreement after an audit output) and anti-triggers (general conversation, acceptance, unrelated pushback). Body instructs the model to extract reviewer/category/severity/claim/reason and dispatch the capture script.
- `scripts/log_disagreement.py` — captures the session window from the audit output forward (last ~12 turns by default) into a `.jsonl` plus a `.meta.json` with the structured dispute fields. Stored under `~/.claude/plugins/data/assumption-auditor/disagreements/` so disputes accumulate across projects and survive workspace cleanup.
- `agents/auditor.md` and `agents/plan-critic.md` — added an "Output footer (always)" section requiring every output to end with the disagreement invitation. The footer is part of the schema, not commentary, so the existing "do not add commentary before or after" discipline remains intact.
- `evals/fixtures/*.expected.txt` — footer appended to all five existing fixtures so they stay aligned with the new schema. The harness is still stubbed; once live invocation lands, expected outputs and live outputs will match exactly.
- README updated with the auto-invocation flow and a new entry in the slash-command table.
- `.claude-plugin/{plugin,marketplace}.json` bumped to 0.3.0 with descriptions reflecting the new feedback channel.

**Why:**
The v0.2.0 feedback loop was open: when a reviewer's output was wrong, users had to manually edit `DISAGREE.md` to register the disagreement. Most users would not bother. Maintainer-side prompt tuning depended on disagreements being captured, which depended on users doing free work — a brittle loop that empirically yielded zero entries in `DISAGREE.md` across the v0.1.0–v0.2.0 cycle. Without captured disputes the next prompt tune is data-blind; with them, every false positive becomes a regression test.

The forcing function: as the plan-critic moves toward being a real approval gate (md-manager integration just shipped), the cost of a bad critic finding rises. Users will tolerate occasional false positives only if they have a near-zero-cost way to flag them. Manual `DISAGREE.md` editing fails that bar; "just say so in chat" passes it.

**Design decisions:**
- **Model-invokable skill instead of a hook.** Two options for auto-invocation: a `UserPromptSubmit` hook (deterministic but keyword-based) or a model-invokable skill (nuanced but probabilistic). Chose the skill because plain-language disagreement is too varied for keyword matching to catch well — "actually the scope is fine here" is disagreement; a keyword hook would miss it. The trade-off is silent-miss risk when the model fails to recognize disagreement. Mitigated by the explicit invitation footer (gives the user a near-explicit trigger) and by a documented v0.3.1 follow-up to add a hook as a deterministic safety net if smoke-testing shows the miss rate is non-trivial.
- **User-scope storage, not project-scope.** Disagreements are plugin-improvement data, not project data. A project-scope log would scatter the feedback across repos and make maintainer-side analysis hard. User-scope under `~/.claude/plugins/data/` mirrors how forge stores its data and survives project deletion.
- **Two paired files per disagreement.** `.jsonl` for the session window (fixture-skeleton), `.meta.json` for the structured fields (queryable). Splitting them means the maintainer can `cat *.meta.json | jq` to triage disputes without parsing session JSONL, while still having the session content available for promoting a disagreement to an eval fixture.
- **Footer in the output schema, not in the skill output.** The footer needs to be inside the subagent's prescribed output so the existing "do not add commentary" rules don't conflict with it. Wrote it as a schema section, not a special case, so future schema additions follow the same pattern.
- **No automatic promotion to eval fixture.** Disagreements land as candidates; promoting them to `evals/fixtures/` is still a manual maintainer step. Tempting to auto-promote but risky — a single misclassified disagreement becomes a permanent regression test pinning the wrong behavior. Manual review remains the gate.

**Technical decisions:**
- **`datetime.datetime.now(datetime.timezone.utc)` instead of `utcnow()`.** Python 3.7+ stdlib only is the project constraint. `utcnow()` is deprecated in 3.12+; `now(timezone.utc)` works in 3.2+ and isn't deprecated. Future-proof at zero cost.
- **`SESSION_CAPTURE_WINDOW = 12` and `start = max(0, audit_idx - WINDOW//2)`.** Captures from a few turns before the audit forward, so the fixture includes the user request, the plan/completion, the audit output, and the user's pushback. Empirically sized; tuneable in a follow-up if it captures too little or too much.
- **Walking records back-to-front for audit detection.** `find_recent_audit_record_idx` scans for assistant turns containing `AUDIT SUMMARY` / `CRITIQUE SUMMARY` / `ISSUE ·` / `No issues flagged` / `APPROVED`. Marker-based detection is brittle to future schema changes but cheap; documented as a known coupling.
- **Slugify the category for the filename.** Prevents collision when multiple disputes land in the same second (rare but possible) and keeps filenames filesystem-safe across platforms.
- **The skill calls the script via `Bash` only.** No file-edit tools needed in the skill; the model just packages the dispute fields and runs the script. Smaller blast radius.

**Tradeoffs discussed:**
- **Auto-invoke vs explicit `/disagree` slash command:** explicit is more reliable but adds friction; auto-invoke is frictionless but risks silent miss. Chose auto-invoke with the explicit-invitation footer as a hybrid — the model has full context to detect disagreement, the user has an obvious channel to push back. The silent-miss tradeoff is acknowledged and has a documented mitigation path.
- **Footer wording:** considered "Disagree? Just say so." (terse), "If a finding is wrong, just say so. Your pushback will be logged for prompt tuning." (chosen — explicit about both the channel and what happens to the input), and a longer explanation of the loop (rejected as commentary).
- **CLAUDE.md fragment for reliability:** original plan included a CLAUDE.md instruction telling the model to invoke `/log-disagreement` on detected disagreement. Plugins cannot inject CLAUDE.md fragments into host projects, so dropped. The skill description and footer carry the same instruction-load now.
- **Bumping plan.md Current Focus to reference v0.3.0:** could have left it pointing at the v0.2.0 next-step (live eval invocation). Updated so the document reflects the current state; live-eval-invocation moves to the "next load-bearing step" framing inside the v0.3.0 entry.

**Safety:**
Touches `agents/auditor.md` and `agents/plan-critic.md` — both safety-critical per `.claude/rules/safety.md`. The change is additive (a new schema section requiring a footer) and does not modify, weaken, or remove any existing discipline: the "evidence or silence" rule, the two-citation rule, the forbidden phrases, the permission-to-find-nothing clause are all preserved. Existing fixtures' expected outputs were updated to include the new footer so the regression set stays aligned. The footer text is invariant ("If a finding is wrong, just say so. Your pushback will be logged for prompt tuning.") — no variability that could erode reviewer discipline. Marked here per the safety rule's "Flag the change" requirement, though strictly this isn't an error-handling / persistence / fallback change.

**Lessons learned:**
- The "model-invokable skill description" doubles as documentation of the auto-invocation contract. Wrote it carefully because it's the only line of defense against silent miss — the more concrete and exemplified the description, the higher the recognition rate. Treating it like a regular skill description (one-line summary) would have been worse than the alternative.
- The footer being part of the *schema* matters. Putting it in commentary territory would create a "the prompt says no commentary, but it also requires this commentary" contradiction. Naming it as a schema element resolves the conflict cleanly. Worth remembering for any future schema additions.
- Storage location reveals product intent. User-scope under `~/.claude/plugins/data/` signals "this is plugin-improvement data, not project data." Project-scope would have signaled "this is a per-project audit log" — a different (and worse for this use case) product.


**Date:** 2026-05-14
**Branch:** project-status-overview
**Commit:** 8ce9fb3

**What was done:**
Added a second skeptical reviewer alongside the existing auditor: the **plan-critic**, which checks proposed plans for *reasoning* gaps (scope drift, spec violation, internal incoherence) rather than *evidence* gaps. Shipped as v0.2.0.

Concrete artifacts:
- `agents/plan-critic.md` — prompt with three categories, a two-citation discipline (every finding cites both a source of truth and the conflicting plan element), and three severity tiers (BLOCKER / REDIRECT / FOLLOW-UP). Explicit `APPROVED` signal for clean plans.
- `skills/critique-plan/SKILL.md` — user-invocable entry point. `disable-model-invocation: true`, `context: fork`, `agent: plan-critic`. Mirrors the existing `audit-plan` skill pattern. Invokes the preprocessor with `--reference-glob "core-docs/*.md"`.
- `scripts/extract_session.py` extended with `--reference-paths` and `--reference-glob` (opt-in). Reads matching docs from CWD; skips `history.md` / `plan.md` / `roadmap.md`; caps each doc at 12000 chars; renders a `## Reference documents` section above the existing context. Existing audit-plan / audit-completion flows produce byte-identical output when the new flags aren't passed.
- `evals/fixtures/scope_drift_form_fix.{jsonl,expected.txt}` — exercises scope drift.
- `evals/fixtures/spec_violation_bundled_ui.{jsonl,expected.txt}` — exercises spec violation; reference rule embedded via in-session Read of `core-docs/feedback.md`.
- `evals/fixtures/internal_incoherence_jwt_migration.{jsonl,expected.txt}` — exercises internal incoherence; two contradictory plan steps (keep + remove the same middleware file).
- `evals/ground_truth.yaml` — new entries with a `reviewer: plan-critic` field for future harness dispatch.
- Marketplace + plugin metadata enriched to match the `forge` pattern (owner, version, keywords, homepage, repository, category).

**Why:**
The existing auditor is rigorous but narrow — it can only flag claims that lack session evidence. It misses a different failure class: plans whose *reasoning* is misaligned with intent. Plans that silently expand scope, contradict a documented rule, or contain internal contradictions don't lack evidence — they lack alignment. The plan-critic is the sibling lens for that class.

The md-manager workflow's plan-approval gate (step 3 of its workflow.md) was the proximate forcing function. That gate is currently a human-only check; the long-term goal is to stage trust so an agent can review plans at the gate. The plan-critic is the first credible candidate to do so.

**Design decisions:**
- **Sibling subagent, not a fifth auditor category.** The auditor's discipline is "evidence or silence" — adding reasoning categories would dilute it. Two prompts, shared plumbing, no cross-references is the right separation.
- **Two-citation rule as the falsifier-equivalent.** The auditor demands a tool-call citation; reasoning critique can't. The substitute discipline: every finding must produce one quote from a source of truth, one quote from the plan element, plus one sentence of glue. If the critic can't produce both quotes, no flag. Same epistemic stance as "evidence or silence."
- **Severity tiers in the output.** Auditor output is binary (issue / no-issue). For an approval-gate use case, a calling agent needs to distinguish "must fix before approval" from "note and proceed." BLOCKER / REDIRECT / FOLLOW-UP imported from the md-manager `staff-review` skill pattern.
- **Deterministic doc loading via preprocessor.** Reference docs are inputs; loading them belongs in the preprocessor, not in the subagent's tool use. This keeps the critic's context predictable and removes its dependency on what Claude happened to Read during the session.
- **Default skip list.** `history.md` (decision log), `plan.md` (work tracker), `roadmap.md` (future work) are *not* sources of truth for new plans. Loading them would inject noise and stale state. Excluded by default; user can override with explicit `--reference-paths`.

**Technical decisions:**
- **Glob-with-skip-list, not explicit-paths-only.** Glob is more ergonomic for projects following the `core-docs/` convention. Explicit `--reference-paths` available as override for non-conventional layouts.
- **12000-char cap per doc.** Sized to fit typical `spec.md` / `feedback.md` / `design-language.md` / `workflow.md` without truncation. Adds a `(truncated; original N chars)` marker when it does fire. Cap is per-doc, not total, since the critic reads them as separate quotable units.
- **`reviewer: plan-critic` field in ground_truth.yaml.** Forward-looking — the eval harness doesn't dispatch on it yet (still reads `.expected.txt` stubs for both reviewers), but adding the field now means the harness rewire only needs to read what's already there.
- **README registers both reviewers explicitly.** The "Slash commands" table at the top is the install-and-go contract. Sub-tables for each reviewer's categories. Output formats documented separately.

**Tradeoffs discussed:**
- **Plugin vs. in-repo for md-manager:** could have built the critic directly in md-manager. Decided against — the categories are generic, the infrastructure already exists in this plugin, and md-manager isn't the only project that will benefit. Cost of the plugin dependency is one `/plugin install` per consumer.
- **Bundle into forge marketplace vs. independent:** could have added the critic to the existing forge marketplace for a unified surface. Decided against — different products (forge = infrastructure architect, auditor = session reviewer), different release cadence, easier to spin off if maintenance shifts. Two marketplaces costs users one extra `/plugin marketplace add` command. Trivial.
- **Ship plan-critic in v0.2.0 vs. hold experimental:** plan-critic hasn't been battle-tested on real sessions. Shipping anyway because the md-manager workflow change depends on `/critique-plan` existing. README is honest that the third category (internal incoherence) lacks a fixture and that the eval harness is still stubbed. Better to ship with honest limitations than block the consumer workflow.
- **History entry written before commit:** the docs discipline rule requires history.md updated before commit. Entry written now with `Commit: [pending]` placeholder; replace with SHA on the actual commit.

**Lessons learned:**
- The "two-citation rule" framing took several passes to land. Initial drafts asked for "specific quotes" or "concrete evidence" — too vague. Naming the structure (one quote from truth, one from the plan, one sentence of glue) made the discipline enforceable. Worth doing the same exercise for any future reviewer category.
- The preprocessor-vs-subagent question for doc loading kept coming back. Multiple options seemed plausible (extend preprocessor, sibling preprocessor, subagent Read tool, pre-flight skill, host-project rule). The right factoring was clear once the question was "which component is responsible for deterministic input?" — that's the preprocessor's job, always.
- README discipline matters at the marketplace boundary. The bare marketplace.json (the v0.1.0 version) would have shipped fine for self-install but looked unfinished in any discovery surface. Filling in keywords / homepage / category is 10 minutes of work; doing it before publish saves a "looks abandoned" first impression.


**Date:** 2026-04-20
**Branch:** codebase-overview
**Commits:** e30b75b, 4d3522b, + in-progress fixup

**What was done:**
Added `CLAUDE.md`, `core-docs/`, and `.claude/` scaffolding for developing the plugin. Kept the new project-dev files strictly separate from the plugin's own published artifacts (root `agents/`, `skills/`, `scripts/`, `evals/`, `.claude-plugin/`, `README.md`, `DISAGREE.md`). Added a `.gitignore` for `.claude/settings.local.json`, `.claude/forge/`, and `.DS_Store`.

**Why:**
Before this change, the repo had no project-dev infrastructure -- no agent specs, no rules, no living docs. Sessions developing the plugin had to rediscover context every time. The template provides a scoped, predictable place for that context.

**Design decisions:**
- Explicit plugin-vs-dev boundary documented at the top of CLAUDE.md. The dual-name collision (`agents/` at root vs. `.claude/agents/`) is structural -- Claude Code's plugin convention requires plugin artifacts at root, and Claude Code's project convention requires project-dev infra under `.claude/`. Resolved via documentation, not reorganization.
- Renamed `.claude/skills/audit/` to `.claude/skills/preship/` to avoid slash-command collision with the plugin's own `/audit-plan` and `/audit-completion`. The pre-ship skill's frontmatter `name:` was updated to match (caught in review -- would otherwise have registered as `/audit`).
- Deleted template pieces inapplicable to a headless plugin: `core-docs/design-language.md`, `.claude/agents/ui.md`, `.claude/rules/ui.md`, `.claude/rules/dev-server.md`, `.claude/skills/link/`, `.claude/skills/dev-panel/`, `.claude/skills/setup/`.
- Scoped `.claude/rules/safety.md` to plugin-critical files: `agents/auditor.md`, `scripts/*.py`, plugin manifests, eval harness. These are the files whose silent breakage would be most expensive.

**Technical decisions:**
- `.claude/settings.local.json` gitignored per Claude Code convention (per-user permissions should not be shared).
- Empty `.claude/forge/` directory left in tree (git doesn't track empty dirs) but gitignored to prevent Forge's local cache from being committed later.
- `core-docs/plan.md` Current Focus populated with the real v0.1.0 state (eval harness stub + SKIP'd fixtures) rather than left as a template placeholder.

**Tradeoffs discussed:**
- Keep vs. rename `.claude/skills/audit/`: renaming adds a small cognitive cost (users typing `/audit` won't find it) but eliminates a real collision risk during plugin development. Renaming won.
- Populate vs. leave template placeholders in `plan.md`/`history.md`/`feedback.md`: populated plan.md because the current focus is knowable and useful; left history.md and feedback.md format-only because the first real entries should come from real work, not backfill.
- Merge template README content into the existing plugin README: skipped. Template README is generic philosophy; plugin README is concrete install/use docs. Nothing to merge.

**Lessons learned:**
- Directory renames don't automatically update frontmatter `name:` fields. Always grep for the old name after a skill rename. The preship skill's frontmatter was missed in the first pass and caught in self-review -- the exact kind of "declared done, didn't actually verify" error the plugin itself is designed to catch.
- Full-repo grep for references to deleted files (`design-language`, `UI Agent`, etc.) after cleanup is load-bearing. Four agent/workflow files had stale references the deletion step missed.
