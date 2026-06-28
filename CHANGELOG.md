# Changelog

All notable changes to flow are recorded here. Reverse chronological (newest first).

This is the **consumer-facing changelog** — read this before upgrading. For per-PR design decisions + tradeoffs, see [`dev-docs/history.md`](dev-docs/history.md) (verbose, internal-tracking).

Format: each entry has a date, version, headline, 2-4 bullets, and an explicit "Breaking changes:" callout (currently always "none").

To upgrade: see [`docs/upgrade.md`](docs/upgrade.md).

---

## v1.11.1 — 2026-06-27

**`/flow:ship-spike` re-ship now gets the same `gh` Projects-classic resilience as `/flow:ship` + `/flow:staff-review`. SAFETY (PR-body write fallback).**

- **Fan-out fix.** v1.10.1 added a canonical `gh`-resilience fallback (REST body PATCH + draft-toggle mutations) for the Projects-classic `projectCards` GraphQL deprecation and wired it into `/flow:ship` Step 7 + `/flow:staff-review` Step 7 — but **`/flow:ship-spike`'s PR-OPEN re-ship path was missed** (the third PR-write site). On affected repos a spike re-ship's body update would still fail silently. `/flow:ship-spike` Step 7 now references the canonical fallback, and the stale `/flow:staff-review` §1.5 note is de-staled (FB-0010 fan-out completion, FB-0060).
- Docs-only; no renderer or gate behavior changes. Breaking changes: none.

## v1.11.0 — 2026-06-25

**Flow now learns from its own use and contributes the lessons back. `/flow:ship` Step 4c harvests *flow-generalizable* lessons (a reviewer false-positive, a gate misfire, a taste call you overruled) behind a ~free pre-scan; the new `/flow:contribute` skill drains them into a DRAFT PR back to the flow plugin. Runs itself; you only gate the merge. SAFETY (new ship step + session-parsing helpers + install-surface manifests).**

- **Harvest (automatic, in `/flow:ship` Step 4c).** A deterministic pre-scan makes clean PRs cost zero tokens. When the transcript carries a correction / symptom / overrule / endorsed-reviewer signal, the analyzer routes each finding PROJECT-LOCAL (existing 4a/4b surfaces) vs FLOW-GENERALIZABLE vs BOTH, drops noise/low-confidence, and enqueues the generalizable ones to a user-scope cross-project queue. Routing/noise are best-effort LLM judgment; only the confidence score + pre-scan are mechanical.
- **`/flow:contribute` (the drain).** Run from your flow checkout (`flowRepoPath`), it drains the queue **and** the previously-manual `/flow:log-disagreement` store, sanitizes out personal-project tokens (fail-closed — a residual leak is held for you, never shipped), scores, and opens a single rolling **draft** PR with the high-confidence clean lessons (everything else held + listed). Never merges; calibrates from each PR's merge/close/edit outcome.
- **Self-triggering.** A flow-repo `SessionStart` hook fires the drain whenever you open the flow checkout with a non-empty queue (primary); an optional local OS job covers the rest. No cloud routine (the queue + checkout are local).
- **4 new slots → 28 total:** `flowRepoPath`, `contributionsQueuePath`, `lastHarvestedPath`, `contributionThreshold`. New scripts (`contribution_store.py`, `harvest_lesson.py`, `sanitize_tokens.py`) + `run_contribution_evals.py` wired into CI. Auto-merge of high-confidence contributions is designed-for but **deferred** (v1 always gates the merge on you). FB-0059.
- Breaking changes: none.

## v1.10.2 — 2026-06-26

**Fixes a jq boolean-slot footgun that silently inverted `verifyEnabled: false` / `uiSurface: false` opt-outs. SAFETY (skip-gate / fallback behavior).**

- `jq -r '.X // true'` treats boolean `false` (not just `null`) as "empty", so `false // true` → `true` — an explicit opt-out resolved to *enabled*. The load-bearing case: a project with `verifyEnabled: false` had `/flow:verify-build`'s Step 1.2 skip-gate fail to fire, running the behavioral gate despite the opt-out.
- Fixed all **four** affected sites with `jq -r 'if .X == false then "false" else "true" end'` (absent/null → default-on; explicit `false` honored): `doctor` Check 5.3, `verify-build` Step 1.2 skip-gate + the preprocessed display line, and `ship` §5c's `uiSurface` visual-history gate (the 4th instance, which regressed in v1.8.0 — caught while bringing the fix current).
- **FB-0058** names the durable discipline: never read a boolean slot with `// <default>`; grep skills for `.<slot> //` when adding a boolean slot or a new read. (Originally drafted as FB-0047 on PR #44; renumbered on merge to avoid colliding with main's shipped FB-0047.)
- Surfaced by a consumer dogfood (valletta iOS flow-migration, `verifyEnabled: false`).
- Breaking changes: none.

## v1.10.1 — 2026-06-24

**Docs-only follow-up to v1.10.0: `gh` Projects-classic PR-write resilience. SAFETY (PR-write fallback behavior in the ship pipeline).**

- `/flow:ship` Step 7 + `/flow:staff-review` Step 7 now document a fallback for the `gh` Projects-classic GraphQL deprecation: on classic-projects repos with affected `gh` versions, `gh pr edit` / `gh pr ready` / `gh pr view --json` fail with `GraphQL: Projects (classic) … projectCards`. The fallback sets the PR body via REST (`gh api -X PATCH .../pulls/N -F body=@file`) and toggles draft state via the `markPullRequestReadyForReview` / `convertPullRequestToDraft` GraphQL mutations (which don't query `projectCards`).
- The secondary item from the same FB-0056 dogfood report that produced v1.10.0; no behavior change to renderers or gates.
- Breaking changes: none.

## v1.10.0 — 2026-06-23

**Two dogfood-discovered integrity gaps in `/flow:verify-build` + `/flow:ship` are closed (#57). SAFETY (verify/ship verdict + gating behavior).**

- **Provenance / anti-forgery.** A per-criterion `metadata`/criterion `provenance` field (`adversarial-judged` | `spike-rubric` | `hand-authored`; **absent ⇒ hand-authored**) lets the renderers tell a judged buffer from a self-reported one. A hand-authored buffer renders a distinct `[~]` self-report state + banner in the PR Test plan and HTML report, never a forgeable machine `[x]`.
- **Spike ≠ no-plan.** Spike's reduced rigor now requires an explicit `/flow:ship-spike`; a no-plan source-touching diff runs the full judged path over diff-derived criteria + draft-routes (`no_plan_fallback`); docs-only → smoke.
- **Rigor gate.** A new commit-invariant `lib/rigor-marker.py`: `/flow:staff-review` writes it, `/flow:ship` Step 1.0a reads it for source-touching diffs → draft if missing/stale.
- New report-render + rigor-marker eval harnesses + a hand-authored fixture, wired into CI (with the previously-orphaned visual-history harness). FB-0056.
- Breaking changes: none.

## v1.9.1 — 2026-06-21

**`/flow:verify-build`'s rendered visual summary is no longer silently dropped when a plan's `**Spec-walk:**` heading is non-canonical. The visual-capture step (§5a) now gates on its own condition, independent of behavioral-criteria extraction, and a new parser makes the capture state-set deterministic. Deliverable-quality track V2.1. SAFETY (verify-build routing/fallback behavior).**

- **Silent-skip fix.** §5a (visual capture → the HTML walkthrough) was gated behind successful `**Spec-walk:**` extraction, so a non-canonical heading → 0 criteria → spike fallback → §5a skipped with no warning, dropping the visual summary even when a `Visual-walk` block was declared. §5a now activates on `uiSurface:true` + a `Visual-walk` block present (via the new parser), decoupled from Spec-walk and spike mode.
- **New `extract-visual-states.py`** — deterministic 1:1 parse of the `Visual-walk` block (one capture-target per declared assertion + optional `[category:]`), so two runs no longer enumerate the capture state-set differently.
- **Robust heading match + active-block scoping (both parsers).** Recognizes canonical `**Spec-walk:**`, qualified `**Spec-walk (…):**`, markdown `### Spec-walk`, and the `**Visual-walk** *(…)*:` form; extracts only the first (active) block with a loud multi-block warning. Convention: author the active PR's plan at the top — retained blocks are ignored and need no heading qualification (retires the prior author-memory convention). Shared logic in `lib/walk_extract.py`; `extract-criteria.py` stays backward-compatible (additive `block_count`). Pinned by `evals/run_walk_extract_evals.py` (FB-0055).
- Breaking changes: none.

## v1.9.0 — 2026-06-19

**Doc-currency reconciliation now covers project-declared status surfaces, not just the built-in plan/roadmap pair. A new `statusDocs` slot lets a project name forward-looking status docs (e.g. a `CLAUDE.md` / `README` status line a cold agent reads) that `/flow:ship` reconciles every ship — and the mechanical gate fires with NO version manifest, closing the dogfood hole where a sub-PR left a phase status stale. SAFETY (new ship-time BLOCKER path).**

- **New `statusDocs` slot (24 slots total)** — an array (default `[]`) of `{ "path": "CLAUDE.md", "marker": "flow:status" }` entries. Flow reconciles **only** the region between the HTML-comment fences `<!-- {marker} -->` … `<!-- /{marker} -->` — a narrow, mechanical update, never a restructure (so projects that gate broad `CLAUDE.md` edits behind a human stay safe). `marker` defaults to `flow:status`. Empty/absent ⇒ identical behavior to today.
- **`/flow:ship` Step 5a** reconciles each declared region to the just-shipped reality (after the built-in plan "Current Focus" + roadmap "Now"). A declared-but-unfenced surface is a loud `⚠️` warning, never a silent skip.
- **`/flow:ship` Step 5b** gains a **version-manifest-INDEPENDENT** marker-coverage gate: if the ship moved forward-looking status (plan "## Current Focus" or roadmap "## Now" changed vs the base) but a declared region was left untouched — or a declared marker is missing — the ship **BLOCKS**. The existing version-token assertion is preserved for versioned projects; this adds real enforcement for projects with no `plugin.json`/`package.json`.
- **`/flow:doctor` Check 2.7** verifies every declared `statusDocs` path exists and is fenced, so misconfiguration surfaces at setup instead of at the next ship's BLOCKER.
- **`lib/status-docs.py` (stdlib) + `evals/run_status_docs_evals.py`.** A shared pure-text helper (parse entries, extract region/section, check fences) consumed by Step 5b + doctor — one implementation, not three copies of awk (FB-0010). Wired into CI.
- **Backward compatible (FB-0054):** projects that don't declare `statusDocs` see no behavior change on any step; flow's own repo declares none, so this PR's own ship exercises the empty-skip path.
- Breaking changes: none.

## v1.8.1 — 2026-06-16

**Fixes a dogfound image-load bug in V3b's `/flow:ship` Step 5c distill, caught by the first real cold-run on a UI surface. SAFETY (asset-persistence path correctness).**

- **Asset-path doubling fix.** §5c set `ASSETS_SRC="$(dirname REPORT)/assets"` and copied `"$ASSETS_SRC/<content>"`, but each frame's `observations[].content` already begins `assets/…` (the §5a convention) → the source path doubled to `.../assets/assets/<frame>`, so the copy missed and the durable record's `<img>` refs pointed at missing files. §5c now resolves frame sources against the **report dir** (`$REPORT_DIR/<content>`) and copies by **basename**, aligning §5a's and §5c's "relative to what" wording. A new `run_visual_history_evals.py` guard pins it (no `ASSETS_SRC`, uses `$REPORT_DIR` + `basename`, keeps the explicit `assets/assets` trap note).
- **Resolved-this-iteration open-question routing clarified.** §5c now distinguishes a `this-iteration` question the human *answered with a decision* (a distill source) from a genuinely-forward `future-planning` question (route to roadmap), and warns against relabeling a still-open blocker as `future-planning` just to clear the Step 8 gate. The proper schema `resolved` flag is roadmapped (§ Next).
- **Validated:** the FB-0016 health-tracker (iOS) cold-run confirmed §5c fires, the curated entry is editorially sound, and screenshots load — and surfaced this bug + two roadmap follow-ups (Spec-walk-block aggregation; the `resolved` open-question flag).
- Breaking changes: none.

## v1.8.0 — 2026-06-16

**The durable visual record (`visual-history.html`) + the distill bridge — Deliverable-quality track V3b. The ephemeral per-run verify-build report now *feeds* a committed, curated record of the visual decisions that changed how the product looks; nothing is read back from `/tmp` and lost. SAFETY (new committed-asset persistence path + create-on-first-write fallback).**

- **New `visualHistoryPath` slot (23 slots total)** — the path to a single, curated, reverse-chronological `visual-history.html`, the *picture* companion to the history doc. Default `core-docs/visual-history.html`; `uiSurface`-gated.
- **`/flow:ship` Step 5c — the distill bridge.** On UI projects, after a verify-build run, the load-bearing visual decisions in that run's findings buffer (the `grounding` entries that changed the user's read + any resolved this-iteration `open_questions`) are distilled into **one** curated entry; the ephemeral report stays ephemeral (distill-then-discard). Heavily gated — self-skips with an explicit reason on `uiSurface:false`, a skipped verify-build, or a run with no load-bearing visual decision (the record is curated, **not** a per-PR dump).
- **`lib/insert-visual-history.py` (stdlib) + `lib/visual-history-skeleton.html`.** The agent curates *which* decision is load-bearing and authors its content; the helper enforces *structure* — seeds the file from the bundled skeleton on first write (no `bootstrap.sh` scaffold, so non-UI projects never get an empty doc), prepends the entry (reverse-chronological), regenerates the anchor-link TOC, and strips heading emphasis (no italic headings). Lean committed asset refs in `visual-history-assets/`; an inline CSS/SVG reconstruction is the honest, labelled fallback when capture isn't available. Malformed target / invalid entry → loud fail, no partial write.
- **`/flow:ship` Step 4a** now also derives a candidate `FB-XXXX` from a this-iteration `open_question` the human answered with a correction (the canonical user-correction FB source).
- **Mechanism note (FB-0053, reverses FB-0042(e)):** created-on-first-write, not a bootstrap scaffold — `bootstrap.sh` runs before `flow.config.json` exists, so it can't gate on `uiSurface`; create-on-first-write keeps the doc out of non-UI repos. Pinned by `evals/run_visual_history_evals.py`.
- **Validation:** the entry shape is **provisional** pending a UI-surface cold-run (flow's own repo is `uiSurface:false`, so its ship always self-skips this step). The first real curated entry comes from the tracked health-tracker (iOS) follow-up.
- Breaking changes: none.

## v1.7.1 — 2026-06-15

**Plain-language copy pass on the `/flow:verify-build` HTML report so a human reading it to make the merge decision understands it at a glance (from FB-0052). Copy-only — no behavior, schema, or logic change.**

- Plainer lede; the legend header `How a verdict / a choice earns its place` → **"Legend"** + a one-line gloss explaining the grounding tags.
- Dropped the redundant jargon `verify exit code: N` pill (the `Overall` pill already encodes pass/fail); `N verify calls` → `N verification steps`.
- Observation labels humanized: `a11y_snapshot` → "Accessibility tree"; `timestamp_offset_ms` shown as **"1.2s in"** instead of `+1200ms`.
- Did **not** rename the grounding vocabulary (need / design-language / craft-commitment / open-question — the established FB-0040 tags); glossed it. Renderer's graceful-degradation + security guards untouched.
- Breaking changes: none.

## v1.7.0 — 2026-06-15

**The `/flow:verify-build` ephemeral HTML report is now a TWO-WAY review surface — the human leaves *located* feedback at the merge gate instead of prose the agent must guess at. Completes V3a (the renderer shipped read-only in v1.6.0). SAFETY (changes the rendered report's output + injection behavior).**

- **Click-to-pin annotation overlay (`verify-build/lib/annotation-layer.html`):** a self-contained, dependency-free vanilla-JS layer that `render-report.py` injects before `</body>` **when the buffer carries at least one captured frame**. The reviewer clicks a screenshot to drop a numbered pin, types a note, and clicks **Copy notes** to get a structured, per-screen, reading-order block (`#3 · <criterion> at x=46% y=31%: …`) to paste back — so a `[this iteration]`-class visual flag re-enters Execute with exact coordinates, mirroring an `open_questions[this-iteration]`.
- **Graceful + scoped:** a frameless (text-only / pre-capture) report stays read-only — no toolbar when there's nothing to annotate; an unreadable layer file renders read-only with a warning, never a crash. Pins persist in `localStorage` (keyed per branch via the report title), harmonize with the report's light/dark palette, and are keyboard-operable.
- **No new slot, no new skill, no new dependency:** the layer rides on the existing `verifyReportPath` report and `render-report.py` (stdlib-only). Captured frames gain a `class="annot-shot"` hook; #45's raster-data-URI allowlist + path-traversal guards are untouched (security-reviewed clean).
- **Honest limitation:** pins bind to the screenshot region in the report's DOM, not the live app's view tree — no CSS-selector / component resolution in the running product.
- Breaking changes: none.

## v1.6.1 — 2026-06-11

**Rendered visual capture + an ephemeral HTML walkthrough for `/flow:verify-build` — visual claims become real PASS/FAIL the autonomy loop can trust, and the human opens a real report at the merge gate (Deliverable-quality track V2/V3a). SAFETY (verify-build gate + findings schema + frame persistence).**

- **Capture-and-persist (SKILL §5a), a11y-gated:** for each declared `Visual-walk` state, flow drives the platform's screenshot MCP itself (XcodeBuildMCP on iOS returns a native frame path; bundled `/verify` only narrates frames to the fresh-context judges — SV2), **in order: snapshot the a11y tree → assert the intended state → screenshot** (never screenshot-then-assume), with a named drive ladder (UI-automation → launch/env hook → can't-reach ⇒ `Unknown` + `not_tested`). Persists a path-referenced `screenshot` + an `a11y_snapshot` (text/status from the a11y tree, not pixels).
- **Two additive findings-buffer fields** (`schema_version` stays `1.0`): `criteria[].grounding` (need / design-language / craft-commitment / open-question) + top-level `open_questions[]` (subjective human calls, distinct from epistemic `Unknown`).
- **Rubric re-grounded:** visual claims judged **pairwise-vs-baseline** (no baseline ⇒ Unknown; first run seeds it), text from the a11y tree.
- **Stdlib HTML renderer (`lib/render-report.py`):** buffer → one self-contained ephemeral report (`verifyReportPath` slot) with grounding callouts, per-dimension verdict cards, a standalone "Open questions for you" block, and a coverage checklist. Raster-data-URI allowlist (security hardening).
- **Loop gate:** an `open_questions[routing=this-iteration]` entry blocks Step 8 auto-advance.
- New `verifyReportPath` slot (22 slots). **Validated by a cold skill-driven `/flow:verify-build` run on a real iOS surface** — round 1 caught 3 `§5a` prose gaps (fixed + FB-0050), round 2 green (FB-0049).
- **Breaking changes:** none.

---

## v1.6.0 — 2026-06-11

**New `/flow:audit-coverage` reviewer closes the under-declaration hole: it flags behavior changes in the diff that no declared `**Spec-walk:**` criterion covers — a behavior verify-build never tested, so the v1.5.3 Test plan would be honestly all-green while the change ships unverified. SAFETY (auditor agent + ship pipeline).**

- **`/flow:audit-coverage` — coverage auditor (13th user-visible skill):** compares the workspace diff against the plan's declared `**Spec-walk:**` criteria and flags each **user-perceptible behavior change no criterion covers**. The complement to verify-build: verify-build checks the declared criteria *pass*; audit-coverage checks the declared set is *complete*. Reuses the `auditor` agent via a new **"Undeclared change"** category (coverage mode) + the existing `extract-criteria.py` parser — no new agent, no duplicated discipline.
- **Routes to the draft manifest, never a hard halt:** each gap is a `[decision-required]` finding → the PR opens as a **draft** until the criterion is declared + verified (re-run verify-build) or the human waives it at the merge gate. The agent must **not** auto-add the missing criterion (grading its own homework). Wired in as the fourth `/flow:ship` Step 2 final-pass reviewer and at the Step 8 readiness boundary.
- **Runs on all platforms** (under-declaration isn't platform-specific — unlike verify-build it does **not** skip on `platform: library|none`); self-skips on doc/test/refactor-only diffs or a plan with no `**Spec-walk:**` block.
- **Honest limitation:** best-effort LLM judgment — it raises the completeness bar, it does **not** deterministically guarantee it (a subtle undeclared behavior can still slip past as a false negative). Not a substitute for the human read at the merge gate. Signal + low-false-positive behavior pinned by `evals/` fixtures (catches a genuine under-declaration; stays silent on a fully-covered diff).

**Breaking changes:** none. Additive — a new reviewer + one new auditor category (coverage mode only); the existing four auditor categories and all other skills are unchanged.

---

## v1.5.3 — 2026-06-11

**The PR `## Test plan` is now rendered from the verify-build findings buffer — a non-forgeable record of behavioral verification, not a hand-authored checklist. The human verifies testing was done and merges, instead of re-verifying. SAFETY (ship pipeline).**

- **`/flow:ship` Step 7 renders `## Test plan` via `skills/ship/lib/render-test-plan.py`:** one checkbox per `**Spec-walk:**` criterion whose state IS the buffer's machine `aggregated_verdict` — `PASS → [x]` (with the adversarial fresh-context judge's evidence quote), `FAIL`/`Unknown → [ ]` (with the judge's reason). The agent can no longer hand-check a box: a green box means a real judge returned PASS. Closes the gap where the Test plan was empty `- [ ]` placeholders disconnected from the verification that actually ran.
- **`not_tested[]` checklist now surfaces in the PR body** (previously only on verify-build's stdout), so the explicit "what we did NOT test" gaps reach the merge gate.
- **Honest fallback, never a forged or stale render:** when verify-build skipped (`verifyEnabled=false`, `platform=library|none`), produced no buffer, or the buffer is stale (its branch/sha ≠ current HEAD) or malformed, the section renders `⚠️ No behavioral gate ran (<reason>); manual verification required` with an unchecked manual line. A `platform: library` repo — including flow's own — always takes this fallback (expected, not a gap).
- **Scope:** attests **behavioral/text** verification only (not visual — that's the Deliverable-quality track's V2), and only over criteria the plan **declared**. A behavior changed without a declared Spec-walk criterion is not yet gated — closing that under-declaration hole (wire `/flow:audit-completion` coverage into the readiness chain) is a queued follow-up. Renderer behavior pinned by `evals/run_render_evals.py`.

**Breaking changes:** none. Additive — Summary + Flow-run table unchanged; the `## Test plan` is now script-rendered rather than hand-authored, and degrades to the manual fallback wherever no buffer exists (i.e. every pre-v1.5.3 case).

---

## v1.5.2 — 2026-06-05

**Makes doc-currency automatic: every `/flow:ship` reconciles the forward-looking roadmap + plan, and a mechanical gate blocks any ship that would leave them stale. Also corrects the upgrade docs. SAFETY (ship pipeline + manifests).**

- **`/flow:ship` Step 5a — doc-currency reconciliation (every ship):** refresh roadmap "Now" (current version, Recently-shipped, ▶ Next-up pointer), sweep shipped plan items → Recently Completed, and clear shipped `FB-XXXX` reservations.
- **`/flow:ship` Step 5b — automatic currency gate:** mechanically asserts the manifest version appears in roadmap "Now" + plan "Current Focus"; blocks the ship and requires reconciliation on drift. Enforced **in the pipeline**, not via the manual `/flow:doctor`.
- **`/flow:doctor` Check 2.6 (secondary):** a manual mirror of the gate for spotting drift between ships — explicitly not the enforcement.
- **`docs/upgrade.md` corrected:** `/plugin marketplace update <name>` updates the installed plugin in one step (not catalog-only); the doc now leads with `autoUpdate` (the no-command path) and fixes the stale "2-command ritual" + the autoUpdate config-example shape.
- Dogfooded: this release fixes the live staleness (roadmap "Now" had read "v1.2.6"; plan "Current Focus" "v1.3.0"), and the new gate self-verifies on this very PR.
- **Breaking changes:** none.

## v1.5.1 — 2026-06-05

**Adds a `Visual-walk` plan field — declared visual/UX acceptance criteria for UI changes. First (cheapest) link in the Deliverable-quality roadmap track toward an autonomous high-quality deliverable.**

- **New plan field `Visual-walk`** (UI changes only; gated on the existing `uiSurface` config slot; N/A under spike/tiny). A plan declares checkable visual/UX assertions — e.g. "empty state renders the zero-data illustration"; "primary button uses the accent token, not a hardcoded hex"; "enter motion ≤ 200ms" — written against the design-language doc (`designLanguagePath`), parallel to the existing `Spec-walk`.
- **Closes a dangling reference:** `workflow.md` Step 8 already told the agent to "dial in visual quality against the plan's declared visual criteria," but no plan field declared them. `Visual-walk` is now that home; Step 8 names the field.
- **Declaration-only.** The criteria are not yet mechanically verified — today's consumers are the agent's Step 8/9 visual dial-in and the human at the plan-approval + merge gates. Rendered capture + verification land in a later roadmap link (V2).
- Touches plan contract surfaces only (`plan-discipline.md`, `planner.md`, `workflow.md`); no new skill, no new schema slot (reuses `uiSurface`). Skill count (12) and slot count (21) unchanged.
- **Breaking changes:** none.

## v1.5.0 — 2026-06-02

**Ship-time gate semantics: unresolved blockers route to a draft PR + NOT-READY manifest, never a silent proceed or a hard mid-loop halt. SAFETY.**

- **Resolution-confidence axis** on `/flow:security-review` + `/flow:accessibility-review`: every BLOCKER is tagged `[auto-fixable]` (one clear, mechanically-verifiable fix) or `[decision-required]` (multiple valid fixes / out-of-repo action like rotating a leaked secret / un-auto-fixable). Default to `[decision-required]` when unsure (FB-0011 ESCALATE-by-default).
- **`/flow:ship` routing:** `[auto-fixable]` BLOCKERs are fixed in-tree; `[decision-required]` BLOCKERs are added to a **draft manifest**. If the manifest is non-empty, the PR opens as a **draft** with a `🚫 NOT READY TO MERGE` block pinned at the top — so an unresolved blocker reaches you at the merge gate instead of halting the loop or producing a merge-ready-looking PR. The manifest integrates with the `## Flow run` PR body (v1.4.1).
- **`/flow:verify-build` at ship is now a confirmation re-run, not discovery.** Behavioral + visual dialing-in happens at the Step 8/9 readiness boundary; ship re-runs verify-build to catch a regression. A non-converging FAIL/Unknown (after the FB-0012 bounded mechanical fix) routes to the draft manifest rather than hard-halting. Visual sign-off folds into the merge gate.
- **Reviewer + ship-spike skills are now model-invocable** (`disable-model-invocation: false` on `/flow:audit-plan`, `/flow:audit-completion`, `/flow:critique-plan`, `/flow:ship-spike`) — the only two human gates are plan approval + PR merge; no skill is itself a gate. The `context: fork` reviewers rely on the v1.4.2 session-discovery fix to resolve transcripts from worktree cwds. Docs (README + workflow.md) updated to label them accurately (BOTH, never cold-start; ship-spike judgment-gated).
- **The v1.4.0 auto-advance predicate is unchanged** — auto-advancing *into* ship still requires a verify-build PASS (FB-0018 invariant). Only ship-*internal* failure handling changed. **Invariant: no merge-ready PR is ever produced on a non-PASS build.**
- `/flow:ship-spike` keeps its verify-build hard-halt (separate scope; follow-up tracks adopting draft-routing there).
- **Breaking changes:** none. New schema slots: none.

## v1.4.2 — 2026-06-02

**Reviewers no longer silently run context-starved from worktree / dotted-path sessions (`extract_session.py` session-discovery fix). SAFETY.**

- `find_session_file` (the session-transcript locator behind `/flow:audit-plan`, `/flow:audit-completion`, `/flow:critique-plan`) reconstructed the `~/.claude/projects/<dir>` name by replacing only `/` with `-`. Claude Code replaces **every** non-alphanumeric character (so `.`, `_`, spaces too). Any working directory containing a `.` — e.g. every `.claude/worktrees/...` session — mismatched, and the reviewers reported "session file not found" and audited nothing. Encoding now mirrors Claude Code exactly.
- Discovery now **prefers an exact match via `CLAUDE_CODE_SESSION_ID`** (which Claude Code exports into spawned subprocesses, including a skill's `!`-backtick substitution), independent of cwd encoding; the corrected cwd-slug is the deterministic fallback, and an unresolved lookup still returns `None` gracefully (no crash). The session-id is validated to `[A-Za-z0-9_-]+` before it reaches the filesystem glob, so a tampered/malformed value can't wildcard-match or traverse to other transcripts.
- New regression fixture `plugins/flow/evals/security/test_session_discovery.py` covers the encoding (dotted / `_` / space paths), the session-id primary, the slug fallback, the graceful-`None` case, glob-injection payloads, and the ambiguous-id guard.

**Breaking changes:** none. Pure correctness fix to session preprocessing; reviewer output schemas, slot counts, and all other surfaces unchanged. Consumers running from a normal (dot-free) project root were unaffected; the fix additionally hardens worktree / dotted-path usage.

## v1.4.1 — 2026-06-01

**PR descriptions now document the full flow-loop run — a per-step `## Flow run` table replaces the generic `## Reviews` blurb.**

- `/flow:ship` §7 PR body gains a `## Flow run` table: one row per loop step (Clarify → Plan+critique → Execute → Preflight → /simplify → /flow:staff-review → security/a11y/verify-build → Doc synthesis), each marked `✓` (ran) or `skipped (<reason>)`, with a **Notable** cell for genuine signal (a plan-critic catch, a load-bearing decision, a fixed BLOCKER, a real review finding) or `—` when routine. The ship agent fills it from the session's loop history and is **instructed not to manufacture notes**.
- Skip reasons are mode- and config-dependent and always named: spike skips `/simplify` + `/flow:staff-review`; tiny also skips the spec-walk; `/flow:accessibility-review` skips on `uiSurface:false` or a non-UI diff; `/flow:security-review` on a doc-only diff; `/flow:verify-build` on `verifyEnabled:false` or `platform` `library`/`none`. (`skipped — not yet shipped` is reserved for a step genuinely absent from the running flow version — never written for a step that actually ran.)
- `/flow:ship-spike` writes a trimmed version of the same table (fewer rows; `/simplify` + `/flow:staff-review` pre-marked `skipped (spike)`).
- `plugins/flow/docs/workflow.md` §10 + the spike section narrate the new PR-body shape; the dogfood dev-side `/ship` mirrors it. Follow-ups remain canonical in the roadmap/plan docs — the table only points at them; the PR is still never merged.

**Breaking changes:** none. Additive — Summary + Test plan are unchanged; only the trailing review blurb is replaced by the richer table.

## v1.4.0 — 2026-05-30

**`/flow:ship` is now auto-invocable — the autonomous-loop trigger (human gates stay at plan + merge).**

- `/flow:ship` frontmatter `disable-model-invocation` flipped `true → false`. The agent auto-advances from Step 8 into the ship pipeline when the **ship-readiness predicate** holds — every spec-walk checkbox checked, no open BLOCKER from `/simplify` or `/flow:staff-review`, no unresolved MEDIUM/LOW-confidence assumption, and `/flow:verify-build` would return PASS (not merely "didn't fail") — AND the FB-0011 risk gate is clear (no unclear path / significant risk / competing comparable options / one-way-door). Otherwise it stops and presents.
- `plugins/flow/docs/workflow.md` Step 8 rewritten as a **conditional gate**; `plugins/flow/rules/general.md` adds a workflow-discipline bullet encoding the trigger.
- **Stays manual:** when `/flow:verify-build` is skipped (`platform` `library`/`none`, or a doc-only diff) there is no behavioral gate, so those still require an explicit "ship it"; `/flow:ship-spike` keeps `disable-model-invocation: true` (spikes are user-initiated by nature).
- The two load-bearing human gates — **plan approval (Step 2)** and **merge (Step 11)** — are untouched. Ship still never merges.

**Breaking changes:** none. Additive — typing `/flow:ship` / saying "ship it" works exactly as before; the new path is autonomous advance only once a driven loop reaches Step 8 with a green predicate. It never starts from a cold request. Reviewer/skill output schemas unchanged.

> **Note:** v1.2.6 (bounded-retry mechanical preflight) and v1.3.0 (`/flow:verify-build`) shipped without CHANGELOG entries — backfill tracked as a follow-up.

## v1.2.5 — 2026-05-27

**Adversarial sharpening of the reviewer pipeline (PR J; research-grounded — see Anthropic's "adversarial review step" best-practice + CriticGPT recall results).**

- `auditor` agent gains a **Self-check before emitting** step: each finding must survive an attempted disproof — name the specific session text that would invalidate the finding, re-scan for it, drop if found or if the lookup is fuzzy. Mitigates the documented "reviewer prompted to find gaps will report some even when work is sound" failure mode.
- `plan-critic` agent gains the same self-check adapted to the two-citation rule: each finding must survive an attempted third citation that would resolve the apparent conflict. Plan-critic's `Internal incoherence` category now also explicitly covers **fan-out contradictions within the plan** (count/name/slot/version referenced in N places where values disagree) — PR-G FOLLOW-UP #5 absorbed.
- `lens-staff-engineer` agent gains an explicit **adversarial reading** preamble ("assume the diff is broken — what's the most likely break?"). This is the engineer-lens analog of the security lens's threat-model stance; the published research convergence is that explicit "find the break" framing materially raises recall on real defects.
- `/flow:security-review` agent prompt shifts to **fully red-team identity** ("you are a red-team operator; your goal is to find an exploitable vulnerability — not to evaluate whether the code is good"). Adds a trace-input-source-back disprove step: if the dangerous sink can't be reached via a concrete attacker scenario, drop the finding. Operational logic (FB-0006/FB-0007 source-file early-exit, FB-0008 `[ -z ]` defaultBranch fallback chain discipline, FB-0009 fail-fast gh+jq, three-source diff capture) unchanged.
- All four edited prompts adopt Anthropic's verbatim *"flag only gaps that affect correctness or the stated requirements, and treat the rest as optional"* warning at the top of each prompt, before any category logic — the explicit countermeasure to the over-engineering tax adversarial framing brings.

**Breaking changes:** none. Prompt-only PR; existing eval fixtures remain green. Reviewer output schema unchanged. The change is additive: clean diffs continue to produce `No issues flagged.` / `APPROVED`; the sharper recall surfaces on diffs that genuinely warrant it.

## v1.2.4 — 2026-05-27

**Workflow-spawn skip prevention (FB-0010 workflow-step sub-class).**

- `/flow:staff-review` now ends with an explicit "After this skill" footer naming `/flow:ship` as the canonical next step. Reframes the existing "ends with work ready, not merged" line into actionable forward motion.
- `/flow:ship` Step 1.0 workflow-step assumption surface gains `⚠️` visual emphasis per ASSUMES line + a REMINDER paragraph explicitly naming the "never bypass `/flow:ship` with `gh pr create`" rule.
- `plugins/flow/docs/workflow.md` Step 10 adds a "Never bypass `/flow:ship`" subsection. Names the failure mode: skipping `/flow:ship` skips the entire Step 2 (security + a11y reviews) of the pipeline, and the `STATUS: SKIPPED` audit-trail signal is load-bearing even on docs-only PRs.
- Defends against the 9th FB-0010 incident, surfaced during PR H1 when the author skipped spawning `/flow:security-review` + `/flow:accessibility-review` and ran `gh pr create` directly. 1 incident isn't usually enough for FB encoding, but the fix is trivially mechanizable (prompt-level reminders + workflow.md discipline statement).

**Breaking changes:** none. Additive workflow guardrails — no skill behavior or contract changed.

## v1.2.3 — 2026-05-27

**Consistency discipline (FB-0010 defense for the recurring bug class.)**

- `lens-staff-engineer` agent now explicitly hunts two flavors of "consistency that depends on author memory": silent-skip on edge case (failures swallowed via `2>/dev/null` / unset-fallback / regex inversion) + fan-out contradiction (count/name/slot referenced in N places, only some updated).
- `/flow:doctor` gains **Check 2.5** comparing the schema's actual slot count (`jq '.properties | keys | length'`) against any documented "N slots" claim in `CLAUDE.md` / `README.md` / `docs/` / `core-docs/` / `dev-docs/`. Flags WARN on mismatch.
- `plugins/flow/docs/workflow.md` Step 4 adds a "Consistency sweep" paragraph naming the discipline at preflight, before `/simplify` runs.
- Defends against the most-recurring bug class flow's own development has surfaced — 6 incidents across PRs 1, B, D, E, F (pass 1), F (pass 2).

**Breaking changes:** none. Additive prompt + new doctor check + new workflow.md paragraph.

## v1.2.2 — 2026-05-26

**Consumer dogfood-readiness.**

- New skill: `/flow:doctor` — PASS/FAIL/WARN punch-list verifying flow is correctly installed + project is correctly configured. Use after `bootstrap.sh` or any time something feels off.
- New scaffolder: `template/base/bootstrap.sh` — one-command project setup (`bash bootstrap.sh --stack web|swift|tauri-rust-ts`). Idempotent; re-running on a populated project skips existing files.
- New walkthrough: `docs/first-pr.md` — step-by-step concrete guide for your first PR through the loop.
- Refreshed `README.md` + `template/base/CLAUDE.md.template` — explains the 3-layer enforcement mechanism (auto-loading rules + skill triggers + `/flow:ship` Step 1.0 surface).

**Breaking changes:** none.

## v1.2.1 — 2026-05-25

**Consumer-feedback follow-ups (5 fixes from md-manager's first real-consumer dogfood report).**

- **Stale-base preflight** in `/flow:ship`, `/flow:ship-spike`, `/flow:staff-review` Step 1 — prevents the "fork from old base → phantom-deletion diff" class of waste before any expensive review runs.
- **Marketplace install verification** docs (`docs/bootstrap.md` + `docs/migration.md`) — adds `/plugin marketplace list | grep '^flow'` step to catch the silent-omission failure when a stale `extraKnownMarketplaces` key points at flow's URL under a non-canonical name (FB-0005).
- **`/flow:ship` Step 1.0 workflow-step assumption surface** — prints which workflow steps `/flow:ship` ASSUMES already ran (critique-plan, simplify, staff-review). Skips become visible at ship time.
- **Per-diff non-UI early-exit** in `/flow:security-review` + `/flow:accessibility-review` — checks the diff for source/UI files; skips with `STATUS: SKIPPED` if none present. Saves spawn cost on docs-only PRs even for `uiSurface: true` projects.
- **`gh` + `jq` CLI fail-fast** — `/flow:ship` + `/flow:ship-spike` Step 1 check `command -v gh` / `command -v jq` and exit 1 with install hint if missing, rather than exit 127 at the invocation site. `/flow:staff-review` adds warn-only check (gh is optional there).

**Breaking changes:** none. All additive guardrails.

## v1.2.0 — 2026-05-25

**Consumer scaffolding (template directory + bootstrap/migration docs).**

- New `template/base/` — Tier 1 (CLAUDE.md.template, flow.config.json.example, .claude/settings.json.example, .claude/rules/safety.md.template, README.md.template, .gitignore.template) + Tier 2 (5 core-docs scaffolds: spec, plan, roadmap, history, feedback with format headers).
- New `template/stacks/{web,swift,tauri-rust-ts}/` — per-stack overlays: preflight runner, CI workflow, `.gitignore.append`, UI/dev-server rules (web + tauri), link skill (web + tauri).
- New `docs/bootstrap.md` — step-by-step adoption walkthrough for new projects, all 3 stacks covered.
- New `docs/migration.md` — 3-stage migration pattern for existing projects with prior `.claude/` content (install non-breaking → dogfood validate → delete duplicates).
- New security regression fixtures: `plugins/flow/evals/security/test_cwd_constraint.py` + `test_malicious_config.py` — protects against path traversal + shell-meta injection through `flow.config.json` values.
- Schema's first published slot set (current count lives in `plugins/flow/schema/flow.config.schema.json` — the single source of truth).

**Breaking changes:** none. Templates are consumer-pulled, not plugin-pushed.

## v1.1.0 — 2026-05-24

**Full workflow surface backfill.**

- 5 new shipped skills: `/flow:staff-review` (4 parallel lenses), `/flow:security-review`, `/flow:accessibility-review`, `/flow:ship-spike` (spike-mode lightweight pipeline), `/flow:workflow-help` (11-step loop + resolved config slots).
- 6 new shipped agents: `planner` + `docs` (context-isolation helpers), plus 4 staff-review lens agents (`lens-staff-engineer`, `lens-ux-designer`, `lens-design-engineer`, `lens-push-further`).
- 4 portable auto-loading rules: `general.md` (workflow discipline on every edit), `plan-discipline.md` (required plan fields + LOW=gate), `documentation.md` (history/feedback/plan format rules), `exploration.md` (§ Exploration triggers).
- New memory tool: `plugins/flow/tools/memory/check.mjs` — failure-pattern corpus cap + audit-due check.
- New `plugins/flow/schema/flow.config.schema.json` — JSON Schema for `flow.config.json`. The schema is the single source of truth for slot count + names; the README + `/flow:doctor` Check 2.5 derive from it.
- New default hooks at `plugins/flow/hooks/default-hooks.json` — opt-in PreToolUse hooks (sensitive-file write blocker + path-validation warn).
- `/flow:ship` PR-1 limitations backfilled (`/flow:security-review` + `/flow:accessibility-review` now wire in; memory machinery now active).

**Breaking changes:** none. PR-1 placeholder behavior replaced with real implementations.

## v1.0.0 — 2026-05-24

**Marketplace restructure + rename from `byamron/llm-auditor` → `by-dev-tools/flow`.**

- Repository renamed in place + restructured into Anthropic marketplace + plugin shape: marketplace at `.claude-plugin/marketplace.json` (one plugin: `flow`); plugin manifest at `plugins/flow/.claude-plugin/plugin.json`.
- 5 shipped skills: `/flow:ship` (port from md-manager's `/ship`), `/flow:audit-plan`, `/flow:audit-completion`, `/flow:critique-plan`, `/flow:log-disagreement` (the last 4 ported from the prior `assumption-auditor` plugin).
- 2 shipped agents: `auditor`, `plan-critic`.
- New canonical loop reference: `plugins/flow/docs/workflow.md` — the 11-step managed-autonomy loop.
- Pre-v1.0.0 content recoverable via `git checkout pre-flow-plugin`.

**Breaking changes:** install identity changed. Old `assumption-auditor@llm-auditor` users must re-add via `/plugin marketplace add by-dev-tools/flow && /plugin install flow@flow`. GitHub maintains a `byamron/llm-auditor` → `by-dev-tools/flow` redirect, so old clones still pull from the same place. The old user-scope `extraKnownMarketplaces.llm-auditor` key continues to resolve at the URL level but is invisible to the resolver (`enabledPlugins.<plugin>@<marketplace>` matches the marketplace's `name` field, NOT the user-scope settings key) — see FB-0005 and `docs/migration.md` for the install verification step that catches this.

---

## Notes on versioning

- Flow follows **semver as a discipline, not a contract**. Patch bumps (`1.2.x`) aim to be additive; minor bumps (`1.y.0`) add user-visible surface; major bumps (`x.0.0`) are reserved for breaking changes (none have happened). The discipline is enforced by `lens-staff-engineer` review + `/flow:doctor` Check 2.5 + author care — there is no mechanical gate today that BLOCKS a breaking change from landing in a patch bump. Always verify upgrades with `/flow:doctor`; treat any patch-level regression as a bug worth filing.
- The plugin manifest version (`plugins/flow/.claude-plugin/plugin.json`) and marketplace metadata version (`.claude-plugin/marketplace.json`) are kept in sync.
- **Docs-only changes at the repo root** (e.g., this CHANGELOG itself, `docs/upgrade.md`) ship without a version bump — they don't change plugin behavior and consumers fetch them from GitHub directly, not via `/plugin install`.
