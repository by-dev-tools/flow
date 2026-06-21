# Plan

## Current Focus

**Plugin at v1.8.1 (V3b shipped + VALIDATED — the durable `visual-history.html` record + the `/flow:ship` Step 5c distill bridge; the FB-0016 iOS cold-run confirmed it works and caught the v1.8.1 asset-path fix).** The managed-autonomy spine is shipped (two-gate loop, `/flow:verify-build` behavioral gate, autonomous ship-readiness trigger, draft-routing, `## Flow run` PR table). The **"enforce that the work was done correctly" pair is complete on `main` (v1.6.0)**: **PR TP** (#46, v1.5.3) renders the PR Test plan non-forgeably from the verify-build buffer; **PR-2** (#47, v1.6.0) adds `/flow:audit-coverage` (under-declaration → draft). **Deliverable-quality track V2 (rendered capture) + V3a (ephemeral HTML walkthrough)** shipped in **PR #45 (v1.6.1)** — a11y-gated capture-and-persist per `Visual-walk` state (iOS via XcodeBuildMCP), the stdlib HTML renderer, additive `grounding` + `open_questions` schema fields, `verifyReportPath` slot. **v1.7.0** layered the **two-way annotation delta** onto #45's renderer (click-to-pin overlay; located pins + "Copy notes"); **v1.7.1** was a plain-language copy pass on the report (#50, FB-0052); and **v1.8.0** (this PR) shipped **V3b** — the durable `visual-history.html` record + the `/flow:ship` Step 5c distill bridge (a `visualHistoryPath` slot, the stdlib `insert-visual-history.py` + `visual-history-skeleton.html`, the gated distill step, the Step 4a open-question→FB extension; created-on-first-write, FB-0053 reversing FB-0042(e)'s mechanism). **The V1→V3 chain is now complete; only V4 remains** (`roadmap.md` § Now).

**▶ Next up: V4** (consumer-side proactive-error loop). **V2.1 hardening SHIPPED (2026-06-21, this branch)** — both cold-gate follow-ups below are closed: `extract-visual-states.py` (deterministic state-set) + §5a decoupled from Spec-walk (no more silent visual-summary skip) + robust heading match + active-block scoping via shared `walk_extract.py`; see the PR block immediately below + history.md "V2.1 hardening" + FB-0055. V2 + V3a + V3b shipped (v1.6.1 / v1.7.0 / v1.8.0); only **V4** remains. The V3b durable-record **entry shape is now VALIDATED** — the FB-0016 health-tracker iOS cold-run (2026-06-16) confirmed §5c fires, the curated entry is editorially sound, and screenshots load; it caught the v1.8.1 `assets/`-path-doubling fix + two routed follow-ups (Spec-walk-block aggregation below; the `resolved` open-question schema flag in `roadmap.md` § Next).

## Handoff Notes

- **Current state is in "Current Focus" above** (v1.7.0; Deliverable-quality track, ▶ V2.1 hardening + V3b next). Shipped-PR detail lives in `history.md`. These notes are pruned at each ship by the doc-currency reconciliation step (`/flow:ship` Step 5a) once the dogfood install is ≥ v1.5.2.
- **Recently shipped (2026-06-15) — the two-way annotation layer (v1.7.0):** `render-report.py` injects `annotation-layer.html` (click-to-pin overlay) before `</body>` when ≥1 captured frame is present, completing V3a as a two-way human-feedback surface; frameless reports stay read-only; unreadable layer warns + renders read-only. **Re-scoped to the additive delta** after the stale-base gate caught **#45** pre-empting ~70% of a standalone `/flow:walkthrough` version — see `history.md` "Two-way annotation layer" + **FB-0051**. Layer-implementation gotchas worth remembering: defer image sizing to the renderer's `.obs img` CSS (don't override width — it clobbers #45's `max-width:600px` cap); pin alignment is a JS measured-host-width sync, not a CSS shrink-wrap (an `inline-block`+%-width image collapses the box to ~0px). Validate any injected-overlay CSS in a real browser.
- **▶ V2.1 / V3b handoff (for a fresh session/agent):** V2 + V3a (incl. two-way annotation) are shipped. Remaining: **V2.1 hardening** (the two cold-gate follow-ups below — `extract-visual-states.py` parser + Spec-walk-heading routing fragility) and **V3b** (durable `visual-history.html` record + the distill bridge; coordinate with **#36**'s merged blueprint/FB-0042, don't duplicate it). Read `roadmap.md` § Deliverable-quality track V2/V3/V4 for sequencing.
- **New direction captured (2026-06-09, docs-only PR):** FB-0044 (low-confidence ⇒ iterate-not-stop; quality-gap→iterate vs preference-fork→escalate), FB-0045 (craft-iteration is a permitted judgment-loop under four guards — refines FB-0012), FB-0046 (experience + push-further-on-quality as first-class plan-gate lenses). Roadmap: "Agentic-iteration doctrine" (Deliverable-quality track, after V2) + "Plan-gate quality lenses" (§ Next, V-track-independent). These shape how the autonomous loop iterates toward the deliverable — read before drafting V2.
- **Managed-autonomy umbrella — remaining facets:** Facet 1 (doctor/init unify + CLAUDE.md sentinel) + Facet 4 (plan-declared comprehensive success criteria enforced by plan-critic — the V1.1 `Visual-walk` enforcement half). Both planned, not started.
- **In-flight parallel branch:** #36 — visual-history durable record (V3-flavored HTML companion; FB-0042).
- **Recently shipped (2026-06-11) — the "enforce that the work was done correctly" pair is DONE:** **PR TP** (#46, v1.5.3) renders the PR `## Test plan` non-forgeably from the verify-build buffer (declared criteria *verified*; FB-0047); **PR-2** (#47, v1.6.0) adds `/flow:audit-coverage` (the declared set is *complete* — under-declaration → draft; FB-0048). Detail in `history.md`. **Residual follow-up:** the vacuous-criterion check (over-broad declaration — verify-build's axis) is filed in `roadmap.md` § Next; not started.
- **Open hygiene:** user-scope `~/.claude/settings.json` still has a stale `extraKnownMarketplaces.llm-auditor` key (cosmetic — points at `flow.git` under the pre-rename name); remove when convenient. Md-manager PR 5 (dogfood) still pending in a separate worktree.
- **Op tip:** `gh pr edit` errors on this repo (projects-classic GraphQL deprecation) — use `gh api -X PATCH .../pulls/N -f body=...` to set a PR body.

## PR V2.1 — Visual-capture routing fix + `extract-visual-states.py` parser (Deliverable-quality track — SHIPPED 2026-06-21)

**Restated request:** "Resume the roadmap here" → the user picked V2.1 hardening and directed "do the most robust fix in line with our intent" on the Spec-walk routing fork. Close the two cold-gate routing follow-ups from the health-tracker cold-runs: the silent visual-summary skip + the non-deterministic capture state-set.

**Mode:** feature (medium). **Status:** SHIPPED on `claude/pr-visual-summaries-workflow-wrvj3a`; version assignment deferred to ship time (v1.9.0 held by in-flight #54). Detail in `history.md` "V2.1 hardening"; governed by FB-0055.

**What shipped:**
1. **`lib/walk_extract.py`** (new, shared) — heading-match + first-(active-)block scoping + checkbox collection; one source of truth for both parsers (FB-0010 fan-out defense).
2. **`lib/extract-visual-states.py`** (new) — deterministic 1:1 parse of the `Visual-walk` block (assertion + optional `[category:]`), so cold agents start from the same enumerated input.
3. **`lib/extract-criteria.py`** (refactored onto the shared helper) — robust heading match (canonical / qualified / markdown), active-block scoping, loud multi-block warning, additive `block_count` (backward-compatible).
4. **`verify-build/SKILL.md`** — §2 (spike no longer skips §5a), §3 (first-block + robust-heading note), §5a (activation decoupled from Spec-walk; parser-driven state-set).
5. **`rules/plan-discipline.md`** — "active PR plan goes at the top" convention (retires the author-memory "qualify retained headings" convention).
6. **`evals/run_walk_extract_evals.py`** (new, 47 checks, wired into CI) + the toy fixture's reference JSON updated for `block_count`.

**Spec-walk:**
- [x] §5a visual capture runs independently of Spec-walk extraction — a malformed `**Spec-walk:**` heading no longer silently skips the HTML visual summary. (verify: `test_visual_decoupled` — Visual-walk found alongside an h3 Spec-walk; SKILL.md §5a/§2 decoupled.)
- [x] `extract-visual-states.py` emits a deterministic 1:1 assertion list with optional category. (verify: `test_visual_category_parse`.)
- [x] Both parsers match canonical / `(qualified)` / markdown / italic-tail headings AND scope to the first (active) block with a loud multi-block warning. (verify: `test_heading_forms`, `test_first_block_only`; smoke on real plan.md → 25 blocks, extracts first, warns.)
- [x] `extract-criteria.py` stays backward-compatible (`criteria`/`source_heading`/`warnings` keys unchanged; `block_count` additive). (verify: `test_cli_backward_compat_keys`; `run_evals.py` audit-coverage fixtures green.)
- [x] Graceful degradation: no block → empty + warning + exit 0; malformed checkbox → warn, keep good; missing file → exit 1. (verify: `test_empty_and_warns`, `test_missing_file_exits_1`.)
- [x] Shared logic factored into `walk_extract.py` (no duplicated regex across the two parsers). (verify: both CLIs import it.)
- [x] `run_walk_extract_evals.py` wired into CI; 47/47 green.
- [x] Docs: history (SAFETY), feedback (FB-0055), roadmap (V2.1 marked shipped), plan (this block + cold-gate items marked done), reserved-numbers (FB-0055 claimed).
- [ ] **Deferred to ship time:** version bump + CHANGELOG + manifests/README (v1.9.0 collides with #54; maintainer assigns at merge). `/flow:critique-plan` + `/flow:staff-review` + `/flow:ship` pipeline (no PR requested yet).

**Confidence verdicts:**
- **HIGH** — decoupling fixes the silent-skip: §5a's predicate no longer references Spec-walk. Verified by the decoupling eval + the SKILL.md rewrite.
- **HIGH** — robust-match + active-block scoping are co-dependent and landed together (loosening alone would re-aggregate retained blocks). Verified by the multi-block eval on real plan.md.
- **MEDIUM** — first-block-in-document-order is a heuristic for "active block." Mitigated by the loud multi-block warning + the documented top-placement convention; residual is an author placing the active block second (warned, not silent).

---

## PR V3b — Durable `visual-history.html` record + distill bridge (Deliverable-quality track — ACTIVE, planning)

**Restated request:** "Move forward with V3b" (user, 2026-06-16) — build the **durable visual record** half of V3: a single curated `visual-history.html` (the *picture* companion to `historyPath`), grown over a project's life, plus the **distill bridge** at `/flow:ship` that converts each run's ephemeral verify-build report into one curated entry. Governed by **FB-0042**; spec = `roadmap.md` § Next "PR-2 — track V3b" + blueprint § 4 contract table. Also folds in the **roadmap/plan doc-currency fix** (the `## Now` header still reads "v1.7.0"; `main` is v1.7.1).

**Mode:** feature (medium) | **Priority: high** (closes the Deliverable-quality track's V3; the "nothing reads the per-run report back" gap).

**Why this PR exists:** V3a made the per-run report a two-way human-feedback surface, but it is **ephemeral** — regenerated each iteration, discarded after merge. Without a durable target, the *decision-making* in each report dies (the roadmap's "Cross-run aggregation" gap). FB-0042 settles the two-tier model: ephemeral report **feeds** a durable, curated, committed record via a distill step at ship. This PR builds the durable end + the bridge.

**The two-artifact contract (blueprint § 4 — do not conflate):**
| | Ephemeral report (SHIPPED v1.6.1/1.7.0) | Durable record (THIS PR) |
|---|---|---|
| Slot / path | `verifyReportPath` (temp, **not committed**) | `visualHistoryPath` → `visual-history.html` (**committed**) |
| Lifecycle | per run, regenerated, discarded | append-only, grows over project life |
| Scope | exhaustive (every observation) | **curated** — only decisions that changed the user's read |
| Produced by | `render-report.py` from the buffer | **distilled at `/flow:ship`** — agent-authored, mechanically inserted |
| Screenshots | base64-inlined | **lean asset refs** in `visual-history-assets/`; CSS/SVG fallback |

**Distill source = the findings buffer (not HTML re-parse).** The load-bearing visual decisions live as structured fields in `verifyFindingsPath` (the same buffer Step 4a already reads): `criteria[].grounding` entries (the rationale that changed the user's read) + resolved `open_questions[routing=this-iteration]`. The distill step reads those + copies the relevant persisted frames from the report's `assets/` dir into the consumer's committed `visual-history-assets/` dir. No HTML scraping. *(Reconciliation with the spec wording: blueprint § 4 + roadmap.md:166 say "distilled from the ephemeral report" — that report is itself rendered from this same buffer, so "the buffer" and "the report's load-bearing decisions" are the same `grounding`/`open_questions` data; reading structured JSON rather than re-parsing rendered HTML is the more robust path and matches how Step 4a already consumes the buffer. Not a contract change.)*

**Decisions locked at this gate (pending your approval of the 3 forks below):**
- **Authoring = agent-curated content, helper-inserted structure** (Fork 1 → A). A small stdlib helper (`skills/ship/lib/insert-visual-history.py`) takes an authored entry block + asset refs and (a) seeds the file from the lib skeleton on first write, (b) **prepends** the entry (reverse-chron), (c) regenerates the anchor-link TOC, (d) asserts no-italic-headings. Curation (which decisions are load-bearing) stays the agent's judgment; structure is mechanical (defends the FB-0010 "consistency depends on author memory" class). Mirrors the existing `render-test-plan.py` / `render-report.py` lib family.
- **Create-on-first-write, not bootstrap-scaffolded** (Fork 2 → A). The skeleton lives at `skills/ship/lib/visual-history-skeleton.html` (a lib asset). The distill step creates `visualHistoryPath` from it on the first qualifying ship when `uiSurface=true`. **No empty doc** for non-UI consumers (FB-0007), no `uiSurface` logic bolted into `bootstrap.sh` (which runs *before* config exists). Honors FB-0042(e)'s *intent* (uiSurface-gated, opt-in) while correcting its literal "scaffold into template/base/core-docs" mechanism — flagged for approval. **If approved, the reversal must land same-PR in the spec sources** (critique Finding 1, FB-0010 fan-out): update `roadmap.md:165` acceptance ("scaffold" → "created-on-first-write by the ship distill step") + FB-0042(e) wording, else a future grep hits a permanent contradiction. A new FB entry records the mechanism reversal (reserve the number first).
- **Validation = evals now; live health-tracker cold-run tracked as follow-up** (Fork 3 → A). Flow's own repo is `uiSurface:false`/`platform:library` → its own ship **correctly self-skips** the distill step. Per the realistic-demos rule, **no fabricated visual-history.html for flow's own non-visual repo.** Correctness is pinned by an eval fixture over a synthetic buffer (legitimate test data, not a user-facing demo); the FB-0016 live validation runs on the health-tracker iOS fixture as a tracked follow-up (exactly as #45's iOS cold run was).
- **Version bump → v1.8.0** (minor — new slot + new ship capability).

**Scope (in):**
1. **Schema slot.** Add `visualHistoryPath` (default e.g. `core-docs/visual-history.html` / flow's own would be `dev-docs/` but flow never writes it) to `flow.config.schema.json`, right after `verifyReportPath`. Description: companion to `historyPath`; uiSurface-gated; created-on-first-write by the ship distill step. **FB-0010 slot-count fan-out 22→23** across: `marketplace.json`, `plugin.json`, `README.md` (×2), `docs/workflow.md`, `doctor/SKILL.md` (Check 2.5 + the "all 22 slots" line), `template/base/CLAUDE.md.template`, `template/base/bootstrap.sh`.
2. **Skeleton lib asset** `skills/ship/lib/visual-history-skeleton.html` — neutral-theme, self-contained, empty-of-entries: `<h1>`, intro paragraph (what this doc is), an empty TOC `<nav>`, an entries container, reverse-chron + no-italic-heading conventions baked into structure. Zero project/brand tokens.
3. **Insert helper** `skills/ship/lib/insert-visual-history.py` (stdlib-only): args = target path, authored entry HTML (stdin or file), optional asset paths to register. Behavior: seed-from-skeleton-if-absent → prepend entry into the entries container → regenerate TOC from entry `<h2 id=...>` anchors → assert no `<em>`/`*...*` in headings (warn+strip or fail). Graceful on malformed target (warn, never crash). Pinned by an eval.
4. **`/flow:ship` distill step** (new **§ 5c**, after 5b, before Commit). Gated: run only when `uiSurface=true` AND verify-build ran at Step 2 AND the buffer has ≥1 load-bearing `grounding`/resolved `open_question`. Reads the buffer; the agent authors ONE curated, decision-centric entry (PR#/date/branch metadata, grounding = user-need + decision-test or design-language/craft rationale, a key before/after, questions carried forward); copies the cited frames into `visual-history-assets/`; calls the insert helper; stages the `.html` + assets. Skip path emits an explicit one-line reason (`no UI surface` / `no load-bearing visual decisions this run` / `verify-build skipped`), never a silent no-op. **Distill-then-discard:** the ephemeral report stays ephemeral.
5. **Step 4a extension** (small): also derive a candidate FB-XXXX from an `open_questions[this-iteration]` the human answered with a *correction* (canonical user-correction FB source) — blueprint § 4. Source-diversity bar still applies.
6. **Eval fixture** (`evals/`, stdlib): (a) insert helper seeds-from-skeleton, prepends reverse-chron, regenerates TOC, strips/flags italic headings; (b) distill output shape over a synthetic buffer; (c) gating — `uiSurface:false` ⇒ no file created; no-load-bearing-decision ⇒ skip. No new dependency.
7. **Doc-currency fix (folded in):** correct `roadmap.md` § Now header (`v1.7.0` → `v1.7.1`) + `plan.md` Current Focus (`v1.7.0` → `v1.7.1`). The Step 5a reconciliation will then carry both to **v1.8.0** at ship.
8. **Version bump 1.7.1 → 1.8.0** (both manifests + README + CHANGELOG).
9. **Docs:** `history.md` (**SAFETY** — new persistence path / commits assets / create-on-first-write fallback), `plan.md` (this block; swept at ship), `roadmap.md` (mark V3b shipped; V4 remains; the § Now currency fix; **+ the line-165 acceptance reversal** if Fork 2 approved), `feedback.md` (**one new FB** recording the FB-0042(e) mechanism reversal: bootstrap-scaffold → created-on-first-write — reserve the number first; otherwise FB-0042 governs). CLAUDE.md sync-table row for the new core living doc (per FB-0042 acceptance).

**Scope (out):** V4 consumer-side proactive-error loop → later. The live health-tracker cold-run validation → tracked follow-up (this PR ships capability + evals). Generalizing the record beyond visual scope to ADR-style decision history → explicitly out (FB-0042: visual-scoped). Auto-rendering entries from the buffer with no curation → out (FB-0042: curated, not a PR dump). Cross-run aggregation/analytics of the record → out (roadmap § Exploration).

**Spec-walk:**
- [x] `visualHistoryPath` slot in `flow.config.schema.json` (after `verifyReportPath`); slot-count 22→23 reconciled across all 8 fan-out surfaces (no surviving current-state "22"; CHANGELOG/plan historical retained). `claude plugin validate .` clean; schema has 23 properties.
- [x] `visual-history-skeleton.html` lib asset — self-contained, neutral theme (matches `render-report.py`), zero brand/project tokens, empty TOC + entries container, `<section aria-label>` landmark, `:focus-visible`, AA-contrast (pinned by eval).
- [x] `insert-visual-history.py` — seeds-from-skeleton, prepends (reverse-chron), regenerates TOC, strips italic headings, atomic write (temp + `os.replace`), alt-missing nudge, graceful on malformed target (no partial write).
- [x] `/flow:ship` § 5c distill step — gated (uiSurface + verify-build-ran + load-bearing-decision hard-skip), agent-authored entry, asset copy into `visual-history-assets/`, insert-helper call, explicit skip reasons; grounding-type enum aligned to the 4-type schema set.
- [x] Step 4a derives a candidate FB from a human-corrected `this-iteration` open question.
- [x] Eval fixture (`run_visual_history_evals.py`, 31 checks): insert mechanics + distill shape + gating contract + WCAG contrast assertions. Green.
- [x] Doc-currency fix: roadmap § Now + plan Current Focus brought fully accurate to v1.8.0 (full narrative refresh per user direction, not just the version token).
- [x] Version bumped 1.7.1→1.8.0 (both manifests + README + CHANGELOG); no stale `1.7.1` survivors that should change.
- [x] CLAUDE.md (template) sync-table row added for `visual-history.html` as a core living doc.
- [ ] FB-0016 live validation on health-tracker (iOS) — **tracked follow-up**, NOT a blocker for this capability PR; entry shape marked provisional-pending-UI-dogfood in §5c + docs.
- [x] `claude plugin validate .` clean.
- [x] Ran `/flow:critique-plan` before approval (3 findings, all folded in — Fork 2 same-PR spec reversal, distill-source reconciliation note, currency-scope confirmed).
- [x] Ran `/flow:staff-review` after implementation (4 lenses, **no BLOCKERs**; cheap NITs fixed inline — contrast ×4, grounding-enum drift, atomic write, hard-skip reminder, a11y landmark/focus, alt nudge, contrast eval; FOLLOW-UPs + exploration routed to `roadmap.md`). `/simplify`: n/a (prose + one stdlib helper already minimal).

**Confidence verdicts per load-bearing assumption:**
- **HIGH** — the buffer carries the distill source (`grounding` + `open_questions` shipped in v1.6.1; verified in `findings-schema.json`).
- **HIGH** — flow's own ship self-skips cleanly (`uiSurface:false` confirmed in flow.config.json); no fabricated demo.
- **MEDIUM** — Fork 2 deviates from FB-0042's literal "scaffold into template/base/core-docs" (create-on-first-write instead). Intent-preserving, but a documented FB reversal — wants your sign-off.
- **MEDIUM** — the exact authored-entry shape (how much before/after, how grounding renders) isn't pinned until the health-tracker dogfood; the eval pins *structure*, not editorial quality. Acceptable for a capability PR per FB-0016 (shape provisional until UI-validated).

---

## PR V2 + V3a — Rendered capture + ephemeral HTML walkthrough (Deliverable-quality track — ACTIVE, planning)

**Restated request:** Build the **V2 (rendered capture + baseline)** + **V3a (ephemeral HTML walkthrough renderer)** link of the Deliverable-quality track, so `/flow:verify-build` turns visual claims from Unknown into a real PASS/FAIL the Step 8 predicate can trust, and produces the HTML walkthrough the human opens at the merge gate. User direction 2026-06-09: "move forward on the roadmap, I want that V2 and V3 functionality."

**Mode:** feature (large) | **Priority: high** (load-bearing for FB-0041 autonomous deliverable; the precondition that makes craft-iteration honest per FB-0045).

**Decisions locked (Gate-1 2026-06-09; CORRECTED 2026-06-11 — iOS-first, not web):**
- **STRUCTURAL CORRECTION:** the earlier "web-first against health-tracker" framing was wrong — health-tracker is an **iOS/SwiftUI app** (`HealthTracker.xcodeproj`), and the renderer's HTML is only an *output format*, never the capture platform. The flow roadmap mislabeled health-tracker as a "web fixture" and SV2 characterized capture on a throwaway web toy + Chrome MCP, seeding the error. **Capture target = iOS via XcodeBuildMCP** (`xcodebuildmcp@2.6.2`, configured in health-tracker's `.mcp.json`). Schema fields / renderer / gate / rubric stay platform-agnostic; the screenshot-drive seam is iOS, not Chrome. (Roadmap web-first framing to be corrected in scope item 12 — FB-0010 fan-out.)
- **Validation surface: health-tracker (iOS, local at `/Users/benyamron/dev/health-tracker`), via XcodeBuildMCP.** User chose (2026-06-11) to make XcodeBuildMCP reachable to this session so I drive capture + validation directly. The web-toy path is dropped (it only characterized the wrong platform).
- **Structural setup (Phase B prerequisite):** (1) XcodeBuildMCP reachable to this session — local `.mcp.json` + session restart; (2) `platform: ios` set in health-tracker's `flow.config.json` (currently unset); (3) local flow worktree linked into health-tracker for the full `/flow:verify-build` e2e run. Phase 0 + capture-mechanism validation can run by driving XcodeBuildMCP directly (no plugin link needed); only the final end-to-end dogfood needs the link.
- **Scope: PR-1 = V2 capture + V3a ephemeral renderer** (FB-0003-coupled). **V3b durable `visual-history.html` + distill bridge = PR-2** (coordinate with #36's merged blueprint/FB-0042). Android/mobile-mcp = later fast-follow.

**Goal:** A `/flow:verify-build` run on a UI surface captures a frame + an a11y snapshot per declared `Visual-walk` state, persists them, writes referenced `observations[]` + the two new buffer fields, judges visual claims pairwise-vs-baseline (not absolute), and a stdlib Python renderer emits one self-contained **ephemeral** HTML report (the merge-gate artifact). An unanswered `this-iteration` open question blocks Step 8 auto-advance.

**Why this PR exists:** SV2 proved visual claims reach the fresh-context judges as *narration* → resolve to Unknown → block (today). FB-0041's autonomous deliverable needs a real visual PASS; FB-0045 needs the judge to see *real artifacts* (not narration) for craft-iteration to be honest. V2 is that link; V3a is the human-feedback artifact (blueprint §3).

**⚠ KEY TECHNICAL RISK — DOWNGRADED by the iOS pivot.** The frame-persist problem SV2 found ("no file even with `save_to_disk`") was a **Chrome-MCP artifact**, not general. **XcodeBuildMCP screenshots write a PNG to disk and return the path natively** (`simctl io … screenshot`) — exactly the SV2 iOS re-test note ("iOS may surface paths differently → cheaper"). So the dominant risk likely resolves at Phase 0. **Phase 0 (first execution step): characterize XcodeBuildMCP's screenshot-return contract** against health-tracker's simulator — confirm a readable file path comes back (expected). Ladder if it doesn't: (a) XcodeBuildMCP native path (expected to work); (b) bundled-`/run`-driven screenshot-to-path; (c) **fallback** resize-then-base64 into `observations[].content` (schema + renderer support it; resize-before-encode). The ladder **is** the bounded iterate FB-0044 prescribes; the rest of the PR is gated on it yielding *addressable frame data*. All-fail → **feasibility-falsified scoped stop-and-re-plan** (not a draft-route — nothing partial to ship; the doctrine's sanctioned stop for a falsified approach, distinct from a mid-loop quality stop — resolves the `/flow:critique-plan` coherence finding). No longer the gating risk it was under the web framing.

**Scope (in):**
1. **Schema (additive; `schema_version` stays `1.0`).** Add `criteria[].grounding` (`{type: need|design-language|craft-commitment|open-question, statement, citations[], decision_test?}`) + top-level `open_questions[]` (`{question, rationale, recommended_default, user_need_lens, routing: this-iteration|future-planning}`). Update `findings-schema.json` + `findings-example.json` + an eval fixture (FB-0003: producer writes them, renderer + Step-8 gate read them, same PR).
2. **Capture-and-persist** (verify-build SKILL.md Steps 5/8), driven by the declared `Visual-walk` state set: per state, a `screenshot` observation (persisted per Phase 0) + an `a11y_snapshot` observation (label/copy/status from the a11y tree, NOT pixels — SV2 bonus finding). A declared state with no observation → `Unknown` + a `not_tested[]` line (no silent gap). Flow owns capture+persist; bundled `/verify` only narrates.
3. **Baseline + rubric rewrite** (`rubric.md:59-68`): re-ground the VLM section on referenced frames + a baseline; pairwise (A vs baseline) over absolute scoring; text from the a11y tree. Define baseline lifecycle: first run (no baseline) seeds it → visual-layout claim is `Unknown` until baselined (acceptable); later runs compare. Keep the section, don't remove it (SV2 branch B).
4. **`verifyReportPath` slot + assets-dir convention**: new config slot (default temp, e.g. `/tmp/flow-verify-report.html`) + an assets dir alongside it for persisted frames. Update `flow.config.schema.json` + the slot tables (verify-build SKILL.md, workflow.md, ship SKILL.md if it reads it). Loud-warning on unset where load-bearing.
5. **Stdlib Python renderer (V3a)**: buffer JSON → one self-contained ephemeral HTML file, blueprint §3 structure (hero + verdict pills → legend → TOC → per-criterion [text → grounding callout → evidence/timeline → adversarial pane → per-dimension verdict cards] → standalone "Open questions for you" → "what we did NOT test" → footer). **Coverage assertion**: every declared `Visual-walk` state appears as evidence-or-"not captured". Screenshots resized (~460–620px) + base64-inlined. Neutral default theme, zero brand tokens. No new dependency.
6. **Report design-language doc** (`dev-docs/design-language.md` for the *report itself* — typography, PASS/FAIL/Unknown semantic colors, timeline conventions). Also flips flow's own `flow.config.json.uiSurface`? NO — flow stays a library; this DL doc governs the renderer's output, not a flow UI surface.
7. **Renderer invocation**: verify-build renders the report after the buffer write (new Step ~9) + outputs `verifyReportPath`; ship Step 2's confirmation re-run re-renders.
8. **Step-8 gate**: `open_questions[routing=this-iteration]` present ⇒ blocks Step 8 auto-advance (mirrors an unresolved MEDIUM assumption). Update `workflow.md` Step 8 + the readiness predicate; eval fixture pins it.
9. **Eval fixtures (stdlib, no deps)**: (a) schema-shape (grounding + open_questions valid; example validates); (b) renderer coverage (every declared state rendered as evidence-or-not-captured); (c) open-questions-blocks-Step-8.
10. **Validation (FB-0016)**: run `/flow:verify-build` against local health-tracker with a `Visual-walk`-bearing plan; confirm real frames persisted + a real report rendered + visual criteria resolve PASS/FAIL (not all-Unknown). Shape not called stable until this passes on the real surface.
11. **Version bump 1.5.2 → 1.6.0** (new capability): both manifests + README + CHANGELOG.
12. **Docs**: history.md (**SAFETY** — verify-build gate + schema + frame persistence-to-disk), plan.md (this block; swept at ship), roadmap.md (mark V2/V3a built; V3b + iOS-seam remain), feedback.md (likely no new FB — references FB-0041/0042/0045; add one only if a durable rule emerges, reserve the number first).

**Scope (out):** V3b durable `visual-history.html` + distill bridge → **PR-2**. iOS/XcodeBuildMCP capture seam → **fast-follow PR**. Real-device testing → out (simulator/headless only). plan-critic enforcement of `Visual-walk` presence (Facet 4 / V1.1) → separate. Android/mobile-mcp → out.

**Spec-walk:**
- [x] **Phase 0 — RESOLVED (2026-06-11, live).** XcodeBuildMCP `screenshot(returnFormat:"path")` returns a **native file path** to an **already-optimized** frame (368×800 JPEG, 24KB — no capture-side resize needed on iOS); `snapshot_ui` returns the a11y tree (semantic targets + text) — the SV2 text source. Branch (a) confirmed; base64 fallback moot. Full chain proven: built+ran HealthTracker on the iPhone 17 sim (~21s), captured a real frame, persisted it (file copy), rendered → 41KB self-contained HTML with the real frame base64-inlined + a11y text + grounding + a this-iteration question. The Chrome-MCP "no path" problem does NOT apply to iOS.
- [ ] `criteria[].grounding` + `open_questions[]` in `findings-schema.json` (additive; `schema_version` still `"1.0"`); `findings-example.json` updated; schema-shape eval validates both. (verify: run the eval)
- [ ] Capture driven by declared `Visual-walk` states: per state a persisted screenshot obs + an a11y_snapshot obs; uncaptured state → Unknown + not_tested line. (verify: health-tracker run buffer has one obs-pair per declared state)
- [ ] Rubric VLM section rewritten around referenced frames + baseline pairwise; absolute scoring discouraged; text from a11y tree; no "may be removed" marker survives. (verify: read `rubric.md`)
- [ ] `verifyReportPath` slot + assets dir in `flow.config.schema.json` + slot tables; loud-warning on unset. (verify: grep slot across surfaces)
- [ ] Stdlib renderer emits the §3 structure to a self-contained HTML file; coverage assertion present; screenshots resized + base64-inlined. (verify: render the example buffer; open the HTML)
- [ ] Report design-language doc exists (neutral theme, zero brand tokens). (verify: read; grep brand tokens → none)
- [ ] `open_questions[this-iteration]` blocks Step 8 auto-advance; `workflow.md` Step 8 + predicate updated; fixture pins it. (verify: run the gate fixture)
- [x] Validated on health-tracker (iOS simulator via XcodeBuildMCP): **FB-0016 DONE — cold skill-driven `/flow:verify-build` run, GREEN (round 2, 2026-06-11).** A fresh agent followed `§5a`/`§10` literally against the real app: 6/6 captures a11y-gated (snapshot→assert→screenshot), drive ladder reached each state (unreachable → honest `not_tested`), the baseline second-run resolved a visual criterion to **PASS** (and the VLM-pairwise correctly ignored a non-deterministic status-bar clock where byte-`cmp` would have false-FAILed). Round 1 caught 3 real `§5a` prose gaps (fixed in `839c986` + FB-0050); round 2 confirmed the fixes with no new gaps. The one residual (assertion-vs-enumerated-state-list derivation) is the already-routed V2.1 parser follow-up, not a blocker.
- [ ] Version bumped 1.5.2→1.6.0 (both manifests + README + CHANGELOG); no stale `1.5.2` survivors that should change. (verify: `git grep '"version"'`)
- [ ] `claude plugin validate .` clean.
- [ ] Run `/flow:critique-plan` before approval.
- [ ] Run `/simplify` + `/flow:staff-review` after implementation.

**Confidence verdicts per load-bearing assumption:**
- **Assumption:** XcodeBuildMCP returns an addressable screenshot path on iOS (so persist is trivial). **Confidence: HIGH.** **Why:** `simctl io … screenshot` writes a PNG and returns its path — native iOS behavior, and the exact case SV2 flagged as "cheaper" than web. **If it flips** (no path): base64-into-buffer fallback (schema + renderer support it). *(Phase 0 confirms before the rest proceeds; web's Chrome-MCP no-path problem does not apply here.)*
- **Assumption:** the two schema fields are additive (no migration). **Confidence: HIGH.** **Why:** blueprint §2 + the schema's own additive rule; existing consumers ignore unknown fields.
- **Assumption:** web-first validates the platform-agnostic shape sufficiently for FB-0016. **Confidence: HIGH.** **Why:** schema/renderer/gate/rubric are platform-independent; only the capture-drive seam is platform-specific (explicitly fast-followed).
- **Assumption:** pairwise-vs-baseline is judgeable from the frames we persist. **Confidence: MEDIUM.** **Why:** depends on frame fidelity + baseline availability; first run has no baseline (→ visual-layout Unknown until seeded, acceptable). **If it flips:** lean on a11y-tree assertions for text, keep visual-layout claims Unknown until baselined.

**Risks / open questions:**
- **Frame-persist mechanism (the big one)** — Phase 0 gates via the a→b→c iterate-ladder; all-three-fail = feasibility-falsified → scoped stop-and-re-plan (not a draft-route; nothing partial to ship).
- **Renderer scope creep** — keep stdlib, one file, neutral theme; resist theming features.
- **Base64 weight** if fallback (c) — resize-before-encode; never paste base64 into the working context (blueprint).
- **Baseline storage/versioning** — where the baseline lives across runs (assets dir; first-run seeds). Keep minimal in PR-1; durable baseline lineage is V3b-adjacent.
- **Large PR** — Phase 0 + schema + capture + rubric + renderer + gate + evals + validation; the natural fault line if it bloats is Phase 0 as a precursor spike (offered at the gate).

**Files touched (anticipated):** `plugins/flow/skills/verify-build/SKILL.md`, `.../lib/rubric.md`, `.../lib/findings-schema.json`, `.../lib/findings-example.json`, `.../lib/not-tested-checklist.md` (maybe), a new `.../lib/render-report.py`, `plugins/flow/schema/flow.config.schema.json`, `plugins/flow/docs/workflow.md`, `plugins/flow/skills/ship/SKILL.md` (if it reads `verifyReportPath`), `dev-docs/design-language.md` (new — report DL), `plugins/flow/evals/fixtures/*` (3), `plugins/flow/.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `README.md`, `CHANGELOG.md`, `dev-docs/{history.md,plan.md,roadmap.md}`.

---

**Staff-review FOLLOW-UPs (2026-06-11, four lenses; BLOCKER + cheap NITs fixed inline — deferred items captured here, not lost):**
- **Renderer: hero criterion tally** (UX) — show "N PASS / N FAIL / N Unknown" in the hero so the human can triage where to spend attention. Small schema-read addition; pairs with the open-questions ordering. Owner: renderer, next iteration.
- **Open-questions answer affordance** (push-further, roadmap-concrete) — the report collects questions but the answer happens off-surface; render a copy-ready answer stub per question (the `this-iteration` → Execute vs resolved grammar the Step-8 gate already implies). ~1 renderer fn + an answer-grammar contract. Owner: renderer + Step-8 gate.
- **Dark-mode token table in `design-language.md`** (design-eng) — the renderer ships ~7 dark hexes with no source-of-truth table; the NITs fixed this round (routing tag, meta-row labels not inverting) existed *because* there's no dark-token table forcing coverage. Add the table + audit the CSS against it. Owner: DL doc, next report-polish pass.
- **`platform_hint` vs `not-tested-checklist` coverage** (staff-eng) — enum has tauri/cli/android but the checklist + capture model web/ios; widen when V2 fast-follows Android. Owner: Android/mobile-mcp fast-follow.
- **Report a11y at 200% zoom / 320px** (UX) — layout should reflow (flex-wrap + auto-fit grid) but unverified; `/flow:accessibility-review` skips it (flow is `uiSurface:false`, but the *report* is a UI artifact). Owner: a dedicated report-a11y pass.
- **Step-8 `open_questions[this-iteration]` behavioral test** (staff-eng) — the eval greps the gate *language*, not the predicate's behavior (no executable predicate exists yet; FB-0018-adjacent). The plan/eval should say "pins the documented contract," not "pins the behavior." Owner: whoever mechanizes the Step-8 predicate.
- **Surface-elevation scale** (design-eng, § Exploration) — `#fafafa` callout tint + routing fills are ad-hoc; a named page→card→inset elevation scale in the DL would prevent future ad-hoc tints when V3b lands.

**Cold-gate FOLLOW-UPs (2026-06-11, from the flow-true `/flow:verify-build` run on health-tracker — substantive §5a prose gaps fixed inline). ✅ BOTH SHIPPED 2026-06-21 in the V2.1 hardening PR (`claude/pr-visual-summaries-workflow-wrvj3a`); see history.md "V2.1 hardening" + FB-0055. Retained below for provenance:**
- **✅ SHIPPED — `extract-visual-states.py` parser + a structured `Visual-walk` state-set syntax.** §5a's state-set derivation is prompt-driven (no parser, unlike Spec-walk's `extract-criteria.py`); two cold agents enumerate states differently. V1 declares `Visual-walk` *assertions*, not an enumerable *state* list — §5a now derives states from the assertions in-prompt + degrades gracefully (capture primary state, rest `not_tested`), but a parser + a declared state-set syntax would make it deterministic. Owner: a V2.1 hardening PR. **Surfaces when:** a consumer reports two runs capturing different state sets, OR `plan-discipline.md`'s `Visual-walk` field is next touched.
- **✅ SHIPPED — §5a routing fragility: a malformed `**Spec-walk:**` heading → 0 criteria → spike fallback → §5a silently skipped.** Resolved both facets: (a) loosened the heading match (canonical / qualified-parenthetical / markdown `### Spec-walk` / `**Visual-walk** *(…)*:`) AND (b) scoped extraction to the active (first) block — co-dependent, so both landed together — AND decoupled §5a from Spec-walk entirely (it gates on `uiSurface` + a `Visual-walk` block via `extract-visual-states.py`, independent of spike/criteria). The interim "retained blocks MUST qualify their heading" convention is retired for "active PR plan goes at the top." On the health-tracker plan (non-canonical `**Spec-walk (each → …):**` heading) the V2 capture path is never reached even though a `Visual-walk` block exists — the new code is gated behind clean criteria extraction. §5a now documents this activation precondition, but the real fix is to either (a) loosen `extract-criteria.py`'s heading match, or (b) let `Visual-walk` capture run independently of Spec-walk extraction. Owner: same V2.1 hardening. **Surfaces when:** `extract-criteria.py` or the spike-fallback trigger is next touched, OR a consumer reports visual capture silently skipped on a UI plan.
  - **CONFIRMED + extended by the V3b FB-0016 cold-run (2026-06-16):** the fragility bit immediately on a real run, in two ways. (1) An h3 `### Spec-walk` heading is ignored (the parser keys on the canonical `**Spec-walk:**`) → it silently grabbed a *retained sibling block* (PR 1c's shipped Spec-walk) instead. (2) Once the active heading was fixed, the parser **aggregated every matching `**Spec-walk:**` block in the file** → it pulled the active block AND PR 1c's (12 stray criteria) until 1c's heading was qualified to self-exclude (`**Spec-walk (PR 1c — shipped):**`, matching how 1a/1b already do it). So the fix has two facets: the heading-match (a) above, **and** "scope extraction to the *active* block, or require retained blocks to qualify their heading." Cheapest interim: document the "retained Spec-walk blocks MUST qualify their heading so they self-exclude" convention loudly in `plan-discipline.md` + the plan template; the durable fix is to scope `extract-criteria.py` to the active block. **The same `**Spec-walk:**`-aggregation behavior is also what the §5c distill depends on indirectly** (no decided grounding ⇒ no entry), so a mis-extracted criteria set can cascade into a wrong/empty visual-history entry.
## PR-2 — Coverage audit: close under-declaration (`/flow:audit-coverage`, FB-0048) — SHIPPED v1.6.0 (see history.md "PR-2")

**Status:** SHIPPED v1.6.0 (this PR; FB-0048 written, reservation cleared). The "enforce" pair (PR TP + PR-2) is complete. Residual: vacuous-criterion check (roadmap § Next). Loop: critique (1 redirect + 2 follow-ups) + audit (clean) → Gate-1 → execute → /simplify → /flow:staff-review (dogfood caught a zsh-word-split BLOCKER) → /flow:ship (security-review fixed a path-traversal BLOCKER). Detail in `history.md`. Original planning record below for provenance.

**Restated request:** PR TP made *declared* verification unforgeable; the residual hole is **under-declaration** — an agent changes behavior X but never declares a Spec-walk criterion for X, so verify-build never tests it, the rendered Test plan is honestly all-green for what was declared, and X ships unverified. Close it: make under-declaration **visible and blocking** at the merge gate. This is the load-bearing other half of "enforce that the work was done correctly" (FB-0047/FB-0048).

**Core thesis:** A new adversarial **coverage audit** compares the *workspace diff* against the *declared Spec-walk criteria* and flags behavior-changing hunks no criterion covers. Each gap → `[decision-required]` → the existing **draft manifest** (PR U) → PR is mechanically NOT-READY until the gap is closed (declare the criterion + verify-build verifies it) or the human waives it. Same enforcement shape as a security/a11y decision-required blocker; routes *into* the merge gate, never a silent proceed, never a hard mid-loop halt (FB-0012: no LLM-judgment hard gate / no iteration on judge output).

**Design decisions (grounded):**
- **Reuse the `auditor` agent + add ONE category** ("Undeclared change"), used only in a new `coverage` mode — not a new agent. The auditor already uses mode-selected category subsets (audit-plan → assumption+recall; audit-completion → diagnosis+completion+recall). Avoids duplicating the ~80 lines of safety-critical disprove/output discipline (FB-0010 fan-out).
- **New `/flow:audit-coverage` skill** (`context: fork`, `agent: auditor`, model-invocable) with a NEW context-assembly path: source-file diff vs default branch + `extract-criteria.py` declared criteria (reused from PR Q). The auditor's current input is the session transcript (`extract_session.py`); coverage needs diff+criteria — different evidence base, same discipline.
- **Surface → draft, not hard-gate** (verdict D). **No auto-fix** (agent adding the missing criterion itself = grading own homework). Resolution = declare + verify, or human waive, through the gate.

**Spec-walk:**
- [ ] 1. New **"Undeclared change"** category in `auditor.md` (disprove: "name the declared criterion that would cover this hunk; re-scan; if found, drop"; fields `Hunk:` + `Why uncovered:`). SAFETY.
- [ ] 2. `/flow:audit-coverage` SKILL assembles diff + declared criteria, instructs coverage-mode (only the new category). SAFETY.
- [ ] 3. Genuine under-declaration → `ISSUE · Undeclared change` citing the hunk (eval fixture).
- [ ] 4. Fully-covered diff → `No issues flagged.` (low-FP eval fixture).
- [ ] 5. Refactor/docs-only diff → skip or no-flag (skip-path + eval).
- [ ] 6. Wired into **ship Step 2** alongside security/a11y/verify-build; gap → `[decision-required]` → draft manifest; consolidated reviews line includes `coverage=[ran|skipped]`. SAFETY.
- [ ] 7. `workflow.md`: coverage discovery at Step 8 + confirmation at ship Step 2 (mirrors verify-build).
- [ ] 8. **FB-0010 fan-out swept** (new skill): README "12→13 user-visible skills" + table row; `workflow.md` "Shipped surface" list (§ line ~15) **AND** "Skills cheat sheet" table (§ line ~443); `workflow-help` skill list; marketplace + plugin descriptions; ship Step 2 reviewer list. *(absorbed critique FOLLOW-UP: include both workflow.md skill-catalog sites, not just the discovery narrative.)*
- [ ] 9. Honest-limitation docs: coverage is LLM-judgment, **best-effort — raises the bar, not a deterministic completeness guarantee** (false negatives possible). README + workflow.
- [ ] 10. Eval fixtures (the feasibility validation, folded in).

**Non-goals:** (1) not a deterministic completeness guarantee; (2) not surfacing gaps in PR-TP's rendered Test plan (they live in the draft manifest); (3) no auto-fix; (4) no change to verify-build / render / the readiness predicate's existing conditions (additive finding source).

**Confidence verdicts:**
- **A — adversarial coverage-judge gives useful signal at acceptable false-positive rate:** **MEDIUM** (the feasibility crux). Mitigation: disprove discipline + evidence-or-silence + permission-to-find-nothing control FP; draft-routing (not hard-block) bounds a false positive's cost; **eval crit 3+4 are the go/no-go** — if it can't catch genuine under-declaration AND stay silent on a covered diff, the approach is wrong → stop + report (fall back to a SPIKE/history deliverable), don't ship a draft-spamming nuisance. *Surface at the gate.*
- **B — reuse auditor + new category > new agent:** HIGH. **C — coverage needs diff+criteria not the session:** HIGH (verified). **D — surface-to-draft not hard-gate:** HIGH (FB-0012-consistent).
- **E — CORRECTED (was: "platform:library doesn't skip → this PR self-verifies"):** Coverage does run on library, BUT flow's own *behavior* lives in markdown (`auditor.md`, the SKILLs, `workflow.md`) which the source-filter correctly excludes as docs — so coverage on flow's own PR-2 diff sees only the `.json` manifests (metadata, no behavior) → clean/skip. Same shape as verify-build skipping on `platform:library`: flow ships a reviewer it can't fully dogfood on itself because flow isn't a typical app. **The catch-path is validated by (a) the offline `coverage_undeclared` fixture and (b) a live prompt run this session — the updated auditor prompt correctly flagged an undeclared rate-limit behavior AND stayed silent (`No issues flagged.`) on a fully-covered diff (verdict A go/no-go = GO).** New + updated skill/agent load from the installed 1.5.1 cache, so the exact skill plumbing isn't Skill-tool-invocable until merged (same constraint as PR-TP).
- **A — feasibility (coverage judge signal/FP):** MEDIUM→**validated GO this session** (catch + no-false-positive both passed on the two fixtures via a live auditor-prompt run); pinned offline by the 3 ground_truth cases.

**Version base re-derive at ship** from `origin/main` (currently 1.5.3 → 1.6.0); don't hardcode (absorbed critique FOLLOW-UP, FB-0010 version fan-out class).

**Mode:** full feature PR. **SAFETY:** `auditor.md`, the audit skills, ship Step 2. **FB-0048.**

---

## PR TP — Render the PR `## Test plan` from the verify-build findings buffer (SHIPPED v1.5.3 — see history.md "PR TP")

**Status:** SHIPPED v1.5.3 (this PR; FB-0047 written). Render half complete; **under-declaration coverage = PR-2 (FB-0048), queued.** Loop: plan → critique+audit (4 findings absorbed) → Gate-1 (staged) → execute → /simplify → /flow:staff-review (1 BLOCKER + cheap NITs fixed) → /flow:ship (security-review fixed a markdown-injection BLOCKER; a11y + verify-build self-skipped). 12-case eval harness (`evals/run_render_evals.py`) pins crit 1–5 + the staff/security fixes. Detail in `history.md`. Original planning record below for provenance.

**Source:** user direction 2026-06-11 — a near-autonomous loop should complete as much testing/validation as possible *before* the human sees the PR; the human confirms it was done + green, then quick-merges; and the workflow must **enforce** that, not let the agent self-attest. → claim **FB-0047** at ship.

**Restated request:** Empty `- [ ]` Test-plan boxes are the wrong merge-gate signal: either unforgeably-empty (no info) or, if the agent hand-checks them, forgeable self-report — the Potemkin class `/flow:verify-build` exists to kill. The human needs to *see* that every required behavioral check ran and passed, with evidence, so review collapses to "confirm + merge."

**Mode:** full feature PR. **SAFETY** — `ship/SKILL.md` is safety-critical (`.claude/rules/safety.md`); preserve every existing buffer-read/skip path through the edit; `SAFETY` marker in commit + history.

**Core thesis:** Make the PR `## Test plan` a **non-forgeable projection of the verify-build findings buffer**, not hand-authored markdown. Checkbox state = the buffer's machine `aggregated_verdict`; each line cites the buffer's two-quote evidence; `not_tested[]` renders verbatim as the explicit human-residue; the no-behavioral-surface path renders an honest "manual verification required (reason)" and keeps the PR in the human-decides lane. The ship agent cannot show a criterion green unless an adversarial fresh-context judge already returned PASS for it.

**What already exists (this *surfaces* existing enforcement — except the staleness check, which is net-new — audit ISSUE 2):**
- The buffer + `findings-schema.json`: per-criterion `aggregated_verdict` + 2-quote evidence, `not_tested[]`, `metadata` (branch, `head_sha_short`, `spike_mode`).
- `ship/SKILL.md:291` Step 4a already reads the buffer **but only for `aggregated_verdict ∈ {FAIL, Unknown}`** (FB-candidate synthesis). PASS criteria, the evidence, and `not_tested[]` never reach the PR body. We extend the read to *all* criteria and route the result to the body.
- Hard enforcement is already upstream: verify-build exits 1 on any FAIL/Unknown; readiness predicate requires a positive PASS (FB-0018); ship-internal regression → draft (FB-0034/0035). **This PR does not weaken, duplicate, or replace any of it.** Caveat (audit ISSUE 2): the crit-4 stale-buffer check (SHA/branch match) is *net-new* logic — Step 4a today guards only ran/skipped + present/missing, never freshness.

**Key design decision — deterministic script vs agent-prose render:** **script** (`plugins/flow/skills/ship/lib/render-test-plan.py`, stdlib-only) reads the buffer JSON → emits the `## Test plan` markdown block; the ship agent pastes stdout verbatim. Rationale: the user's requirement is *enforcement*, so the section must be a pure function of the machine buffer (agent can't selectively check boxes) + golden-testable; matches flow's Python-for-mechanism pattern (`extract-criteria.py`). This is the enforcement teeth (verdict B).

**Spec-walk:**
- [ ] **1. All criteria render** (PASS *and* FAIL/Unknown), one line each, citing the per-dimension evidence quote. *Pin:* fixture buffer (2 PASS + 1 Unknown) → rendered markdown contains all 3. Note (audit ISSUE 1): today's `## Test plan` is a *single* `- [ ] <how to verify>` line (`ship/SKILL.md:444-445`) — this is a structural **expansion** to N criteria-lines + not_tested + fallback, not a re-render of existing boxes.
- [ ] **2. Verdict drives checkbox, unforgeably:** `PASS → [x]`; `FAIL`/`Unknown → [ ]` + verdict + `notes` reason inline; state read from the buffer field, never agent-decided. *Pin:* fixture.
- [ ] **3. `not_tested[]` renders into the PR body** as a verbatim "What we did NOT test" block (today it hits only verify-build stdout). *Pin:* fixture.
- [ ] **4. Skip / no-buffer / stale-buffer path is honest:** verify-build skipped, OR no buffer, OR buffer `head_sha_short`/`branch` ≠ current HEAD/branch → `- [ ] <how to verify> — ⚠️ no behavioral gate ran (<reason>); manual verification required`; never render a stale buffer as current. *Pin:* fixture mismatched-SHA → stale message, not criteria. **(net-new logic — audit ISSUE 2.)**
- [ ] **5. Spike-mode buffer renders correctly:** `metadata.spike_mode: true` → render only `correctness`; don't render placeholder Unknown `regression`/`scope-creep` as real gaps (`verify-build/SKILL.md:165`). *Pin:* spike fixture.
- [ ] **6. FB-0010 fan-out sweep:** every "Test plan" description (ship Step 7 template + narration, `workflow.md` § PR-body, `ship-spike`, any `.claude/skills/ship`) updated to the rendered model + fallback. *Pin:* `git grep -n "Test plan"`.
- [ ] **7. Honest-limitation docs** (README/workflow "Bootstrap status"): attestation reflects behavioral/**text** verification only, not visual (until V2); under-declaration not closed here. **The "behavioral/text" claim describes the consumer path — see self-ship reconciliation below.** *Pin:* read sections.
- [ ] **8. Eval fixture(s) + golden output** under `plugins/flow/evals/fixtures/` (quality bar: no new behavior without a fixture). *Pin:* eval run.

**Non-goals (scope fence):**
1. **Not** the V3 HTML case-study renderer (`roadmap.md:75`/`:122`) — standalone HTML + screenshots, sequenced after V2. This PR renders *PR-body markdown* from verdict+evidence+not_tested text, available today, no V2 dependency (verdict C).
2. **Not** closing under-declaration → **PR-2** (FB-0048).
3. **Not** a new `human-required` criterion state (human-eyes criteria surface as Unknown → correctly block/draft).
4. **No change** to the readiness predicate, draft-routing, exit-code gate, or verify-build.

**This PR's own ship (critique ISSUE 2 reconciliation):** flow is `platform: library` → verify-build self-skips on flow's own ship (verdict F, confirmed `verify-build/SKILL.md` skip-path). So this PR's *own* `## Test plan` renders the crit-4 **fallback** ("no behavioral gate ran — platform library; manual verification required"). The crit-7 "behavioral/text verification only" honesty claim describes the **consumer** path, not flow's self-ship. **Verification of this PR = the eval fixtures + golden outputs (verdict F), NOT a dogfood behavioral run** — expected, not a coverage gap.

**Confidence verdicts (load-bearing):**
- **A — buffer present at ship Step 7 when verify-build ran:** HIGH. Step 8 writes it; Step 4a already depends on it. *If flips:* the no-buffer fallback (crit. 4) handles absence — non-fatal.
- **B — deterministic script is the right enforcement shape:** HIGH. Enforcement-not-attestation + golden-testable + matches flow's pattern. *If flips* (lighter agent-prose preferred): move format into Step 7 prose — smaller diff, weaker enforcement; reversible.
- **C — distinct from V3 HTML renderer:** HIGH, verified `roadmap.md:74-75,:122-148` (different output/inputs/sequencing). *If flips:* this markdown renderer becomes the reusable core V3 later wraps — additive.
- **D — under-declaration deferrable to PR-2:** **resolved at Gate-1 → staged** (was MEDIUM; user chose stage 2026-06-11). PR-1 makes *declared* verification unforgeable + visible; PR-2 closes the under-declaration hole. PR-1 ships first; PR-2 committed, not optional.
- **E — script under `ship/lib/`:** MEDIUM/LOW. Buffer is verify-build's contract (argues `verify-build/lib/`) but consumer is ship. *If flips:* trivial move.
- **F — flow can't dogfood-behaviorally-verify this** (`platform: library`): HIGH, verified. Fixtures carry the verification; this PR's ship shows `verify-build skipped (platform library)` — expected.

**PR-2 — close under-declaration (queued; FB-0048):** wire `/flow:audit-completion`'s unverified-completion category into the readiness chain as an adversarial coverage check — every behavior-changing requirement must map to a declared Spec-walk criterion, else block. The second half of "enforce that the work was done correctly." Fresh plan → Gate-1 cycle after PR-1 ships.

**Adversarial review (plan-time, 2026-06-11):**
- `/flow:critique-plan` → 2: (1) **scope drift** — plan delivers projection, not completeness-enforcement; under-declaration is the load-bearing half. *Resolved:* staged scope (user Gate-1 decision). (2) **incoherence** — crit-7 "behavioral/text" vs verdict-F "no behavioral gate on this PR." *Resolved:* self-ship reconciliation above.
- `/flow:audit-plan` → 2 LOW (every load-bearing factual premise else CONFIRMED against artifacts): (1) **recall precision** — today's Test plan is a single line, not a multi-box checklist → absorbed into crit. 1 as an expansion. (2) **honesty** — stale-buffer check is net-new, not a projection of an upstream guard → "what already exists" framing corrected.

**Files (anticipated):** `plugins/flow/skills/ship/lib/render-test-plan.py` (NEW, stdlib), `plugins/flow/skills/ship/SKILL.md` (SAFETY — Step 4a/7), `plugins/flow/docs/workflow.md` (§ PR-body), `plugins/flow/skills/ship-spike/SKILL.md` (if it carries a Test plan), `README.md` + workflow "Bootstrap status", `plugins/flow/evals/fixtures/**` (golden), `.claude/skills/ship*` (fan-out sweep), `plugins/flow/.claude-plugin/plugin.json` + `.claude-plugin/marketplace.json` (version bump), dev-docs cascade (history/plan/roadmap/feedback/reserved).

**Ship:** `/flow:ship` (verify-build will self-skip — platform library; security/a11y self-skip or run per diff; the gate's audit-trail `SKIPPED` signal is load-bearing). GATE 2 (merge) preserved.

---

## SV2-spike — Does bundled `/verify` return screenshots structurally, or only narrate them? (Deliverable-quality track V2 prerequisite)

**Restated request:** Before scoping V2 (rendered capture + baseline), resolve the open empirical question flagged at `verify-build/lib/rubric.md:68` + `verify-build/SKILL.md:56-64`: does bundled `/verify` return screenshots **structurally** (image data a downstream consumer — verify-build's per-dimension judge and the future HTML renderer — can use as pixels or as path-referenced files), or does it only **narrate** observations in freeform prose? The whole shape of V2 depends on the answer. Run cheaply as a spike; the history.md entry is the deliverable; don't over-build.

**Mode:** `spike` | **Priority: high** (unblocks the V2 feature PR — the load-bearing next link in the Deliverable-quality track; turns "visual = Unknown → blocks" into a real PASS the Step 8 predicate can trust).

**Research question (the one the spike must answer):**
1. **Primary:** Does bundled `/verify` return screenshots *structurally* or *narrate* them?
2. **Decision sub-question (the one that actually forks V2):** Do any structured frames `/verify` captures *reach a fresh-context judge subagent* (verify-build Step 6), or do they stay only in the invoking context? The judges are spawned fresh and read `/verify`'s **text**; the schema already path-references screenshots (`observations[].content` = relative path). So even "structured at the MCP layer" may still be "narration to the judge" — and that distinction, not the raw capability, decides V2.

**Why it forks V2:**
- **Branch (A) — structured *and reaches the judge*:** V2 wires the existing frames into a baseline + the pairwise-VLM comparison `rubric.md` already prefers over absolute scoring. Smaller PR.
- **Branch (B) — narration-only to the judge:** V2 must add an explicit **capture-and-persist-to-disk** step (path-referenced per the schema), reusing `/run`'s browser-MCP screenshot tools, supplying the baseline; the rubric's pairwise-VLM section is rewritten around path-referenced frames rather than removed; absolute-scoring stays discouraged.

**Method — primary (live):**
1. Stand up a runnable toy web app in a **disposable scratch dir** (`.context/scratch/` or `/tmp`), NOT the committed fixture (its README says "not meant to be executed"; `server.mjs` serves no static files and `vite` isn't installed). A pure-node, zero-dep static server serving `index.html` + the existing `POST /api/submit` → 201 handler (reuse the fixture's `index.html` + `main.js` + server logic).
2. Invoke bundled `Skill("verify")` in **this session** against that app + the toy plan's two Spec-walk criteria. Observe the returned artifact: (a) prose-only, or image content blocks? (b) does `/verify` write any screenshot files to disk on its own, and where?
3. **Probe the Skill→judge boundary:** spawn a fresh-context `Agent` (the `rubric.md` judge shape) and check whether it can see any frame `/verify` produced **without being handed a path**. Confirms/refutes structured propagation across the subagent boundary.
4. Record which screenshot-capable MCP `/verify`/`/run` actually used (Chrome / Preview / computer-use) and that tool's return contract (image block vs. file path).

**Method — fallback (documentary, if no browser MCP is connected or the live run exceeds a small budget):** characterize from `/verify`'s Anthropic-documented freeform-stdout contract (already partially captured in `SKILL.md:52-64`) + the screenshot-MCP return contracts + the fresh-context-subagent boundary. Record the conclusion **with its named limitation** (no live confirmation) per FB-0016, and a re-test trigger.

**Hypothesis (to confirm/refute — NOT assumed):** leans **branch (B)-with-nuance** — structured frames exist at the MCP layer but don't auto-propagate to fresh-context judges (which read text); the schema already path-references screenshots; so V2 adds a capture-and-persist step reusing `/run`'s screenshot tools + supplies the baseline; the pairwise-VLM section survives (rewritten around path-referenced frames). The live run exists to confirm or overturn this, not to rubber-stamp it.

**Disposability:** the scratch app is uncommitted (`.context/scratch/` or `/tmp`); the `/verify` run is read-only against a toy. The **only durable artifacts** are `dev-docs/history.md` (the spike deliverable: the answer + the V2 shape recommendation + its limitation) and a one-line `roadmap.md` ▶ Next-up refinement recording the resolved answer so V2's feature plan inherits it. **No `plugins/flow/*` edits, no schema change, no version bump.** Resolving the `rubric.md:68` / `SKILL.md:64` markers (annotate / rewrite / remove the VLM section) is **V2 feature-PR work** — it's part of real implementation and touches shipped safety-critical artifacts — explicitly OUT of spike scope.

**Coordination (#36 / FB-0042):** #36 owns the **durable** record (`visual-history.html`). This spike characterizes capture only — no renderer, no durable-record work. The V2 feature PR that follows = **capture + ephemeral render (V3a)**, coupled per FB-0003 (new schema field needs a producer AND a consumer in the same PR); it must not duplicate #36's durable record.

**Confidence verdicts per load-bearing assumption:**
- **Assumption:** a single live `/verify` invocation against a web toy is sufficient to characterize output shape for the V2 decision. **Confidence:** MEDIUM. **Why:** one run on one platform (web) answers the web branch, which is V2's immediate target; but it's one data point (FB-0016). iOS/Android capture shape is out of V2's near-term scope, so web-only is acceptable. **If it flips:** name the limitation + add a re-test trigger for other platforms.
- **Assumption:** the judge boundary holds — a fresh-context `Agent` can't see a sibling skill's image blocks without a path. **Confidence:** HIGH (architectural: subagents receive only their prompt). **If it flips** (images DO propagate): V2 shifts toward the simpler branch (A).
- **Assumption:** keeping `rubric.md` / `SKILL.md` edits OUT of the spike is correct scope. **Confidence:** HIGH. **Why:** the spike deliverable is the history entry; the marker itself ties removal to "first real verify-build run" as part of V2 implementation; touching shipped safety-critical artifacts for a research finding over-builds the spike + forces a version bump. **If it flips** (user wants the breadcrumb now): add one-line "RESOLVED (spike, see history): <answer>" annotations to both markers — low-risk, no behavior change. *Surface at the gate.*

**Risks / open questions:**
- **Browser MCP may not be connected** (Chrome extension) → live run blocked. Mitigation: documentary fallback + named limitation. Can confirm MCP availability first if the user prefers.
- **`/verify`→`/run` heuristic launch may fail on the toy** (no `run-*` recipe). Mitigation: the scratch app is a trivial zero-dep node server I can start myself and point `/verify` at; if `/run` insists on its own launch path, I observe that too — it's data about `/verify`'s behavior either way.
- **Cost / permanence:** local-only, zero paid services, scratch dir — low on all three. No deletion/overwrite of committed files.
- **FB:** the spike likely needs **no new FB-XXXX** (a research finding routes to `history.md`, not a behavioral rule). If a durable rule emerges, reserve a number in `reserved-feedback-numbers.md` FIRST (next free ≈ **FB-0044**; FB-0042 still in-flight on #36) and push the reservation early per the collision protocol.

**Files (anticipated):** `dev-docs/history.md` (spike deliverable), `dev-docs/roadmap.md` (▶ Next-up one-line refinement), `dev-docs/plan.md` (this block + handoff). Scratch app: uncommitted. **NO `plugins/flow/*` edits.**

**Spike-ship:** via `/flow:ship-spike` (labeled `spike`; never merges). GATE 2 (merge) preserved.

**Spike-walk (mechanical checks before ship):**
- [x] Research question 1 + 2 answered with evidence. (LIVE Chrome-MCP run: screenshots = image blocks to the invoking context + a narration string in text; `save_to_disk:true` surfaced no path + no file on disk; judges are fresh-context Agents reading text → narration-only → Unknown. See `history.md` "SV2-spike".)
- [x] V2 branch (A vs B) named, with the concrete capture shape. (**Branch B** — explicit capture-and-persist; path refs into `observations[].content`; keep+rewrite the rubric VLM section around path-referenced frames + baseline; a11y tree for text.)
- [x] `history.md` SAFETY-free spike entry written. (No shipped-artifact / error-handling / persistence change → no SAFETY marker.)
- [x] `roadmap.md` ▶ Next-up + V2 § refined with the resolved answer so V2's feature plan inherits it.
- [x] Scratch app left uncommitted; `git status` shows no `plugins/flow/*` or app files staged. (Only `.context/scratch/` — gitignored; verified.)
- [x] **(critique-plan REDIRECT resolution)** Doc-currency gate is a non-issue: verified `/flow:ship-spike` does **not** run the `/flow:ship` Step 5a/5b currency machinery (its Step 5 only sweeps to Recently Completed), AND no version bump leaves `plugin.json` = `1.5.2` with `roadmap.md:11` + `plan.md:5` already `**Plugin at v1.5.2**`. The ▶ Next-up edit touches only the bullet, never the `**Plugin at vX.Y.Z**` headline line → token stays current either way.
- [x] Run `/flow:critique-plan` before approval. (done: 1 REDIRECT — ship-spike doc-currency-gate coherence; resolved in-plan as above. 0 BLOCKER. No scope drift, #36 boundary + FB-collision protocol confirmed clean.)

**Outcome:** answered (branch B). Deliverable = `history.md` "SV2-spike" entry + roadmap refinement. No new `FB-XXXX` needed (research finding). Next: draft the **V2 feature plan** (capture + ephemeral render, FB-0003-coupled; coordinate with #36's V3b).

---

## PR DC — Doc-currency in the ship pipeline (MERGED #39, v1.5.2 — see history.md)

**Restated request:** We should proactively improve the workflow so stale docs never happen. Make the ship pipeline *itself* keep `roadmap.md` "Now" and `plan.md` "Current Focus" current on every ship — and back it with a mechanical currency check that fires **automatically in the pipeline**, NOT one we have to remember to run via `/flow:doctor`.

**Mode:** feature (small-medium) | **Priority: high** (foundation: keeps the roadmap/plan honest for every autonomous run + the cold-agent legibility the goal state needs)

**Why this PR exists (live evidence):** Right now `roadmap.md` "Now" says **"Plugin at v1.2.6"** and `plan.md` "Current Focus" says **"Plugin at v1.3.0"** — the real version is **v1.5.1** (V1 just merged; #36 in flight). Both source docs drifted because `/flow:ship` Step 5 writes a *history* entry + routes follow-ups, but nothing reconciles the forward-looking "Now"/"Current Focus" narrative or sweeps completed items. A cold agent (or the autonomous loop, which IS a cold agent each run) reading "Now" would start the wrong thing. This is the FB-0010 fan-out class applied to direction.

**Design — flow doctrine: prompt discipline + an AUTOMATIC mechanical backstop (NOT manual doctor).** The user explicitly corrected an earlier draft that put the check only in `/flow:doctor`: doctor is manual, so it can't be the enforcement. Enforcement lives in the ship pipeline (automatic every ship); doctor gets a *secondary* copy only because it fits its consistency punch-list.

**`/flow:critique-plan` resolution (2 REDIRECT findings):**
- **F1 — upgrade.md "disputed fact."** The single-command claim is *verified*, not assumed: `claude-code-guide` confirmed against `code.claude.com` (discover-plugins + plugin-marketplaces docs) that `/plugin marketplace update <name>` refreshes the catalog AND updates installed plugins in one step (it is not catalog-only), and that `autoUpdate: true` does both automatically at session start. The user was already given this answer in conversation. **Adjustment:** the upgrade.md edit leads with the **autoUpdate** path (the real answer to "why reinstall?") and states current behavior accurately, rather than just deleting the install command — and the edit documents *both* facts (one command suffices; autoUpdate automates it) so a reader isn't left guessing. Spec-walk updated accordingly.
- **F2 — "scope drift: user didn't request the currency pipeline."** Assessed as a **false positive** (the critic windowed on the latest message). The prior turn's explicit direction was *"make sure the pipeline accounts for keeping the plan and roadmap fully up to date as part of the pipeline; this stale docs issue should never happen,"* followed by approval to draft. The currency machinery (A + B + B′) IS the requested scope; the upgrade.md fix is bundled because it's the same *stale-doc* class. Surfaced at the approval gate for confirmation; will `/flow:log-disagreement` if the user concurs it's a false positive (the cross-turn-context miss is useful critic-tuning signal).

**Scope (in):**
- **A — Ship-time reconciliation (prompt).** `plugins/flow/skills/ship/SKILL.md` Step 5 (doc updates) gains explicit sub-steps, runs every ship:
  1. Update `roadmap.md` "Now": set the version line from `plugin.json` (source of truth), move the just-shipped item into a "Recently shipped" line, refresh a **▶ Next up** pointer.
  2. Sweep completed `plan.md` "Active Work Items" → "Recently Completed" (keep last 3–5 per the documentation rule), and refresh "Current Focus" to the real version/state.
  3. Clear shipped FB reservations from `reserved-feedback-numbers.md` (closes the dev-side `/ship` non-auto-clear gap the audit trail repeatedly documents).
- **B — Automatic currency gate (mechanical), the backstop.** A ship **preflight assertion** (stdlib/grep, mirrors Step 1c shape): parse the version token in `roadmap.md` "Now" + `plan.md` "Current Focus" and assert it equals `plugin.json` `.version`. On drift → loud failure that the agent must reconcile (via A) before commit. Fires automatically inside `/flow:ship` — no human invocation. Define a **stable marker format** for the version line so the parse isn't brittle (e.g. an HTML-comment sentinel `<!-- flow:current-version -->` around the version, or a fixed `Plugin at vX.Y.Z` regex contract documented in the skill).
- **B′ — Doctor secondary surface.** `plugins/flow/skills/doctor/SKILL.md` gets the same version-currency check as a punch-list item (it fits; **promotes the already-queued** roadmap § Later "Check 2.5 generalization → version strings"). Explicitly marked secondary: "also enforced automatically at ship; doctor is the manual health-check copy, not the enforcement."
- **Dev-side mirror.** `.claude/skills/ship/SKILL.md` (this repo's dogfood ship) gets the same Step-A reconciliation + Step-B currency check, so flow's own ships stay current (this is the surface that produced the stale docs).
- **Narrate the discipline.** `plugins/flow/docs/workflow.md` Step 10 names doc-currency as part of ship (currency is automatic-at-ship, not manual-doctor).
- **Fix the stale `docs/upgrade.md`** (the bug that started this thread): the "2-command ritual" + "install-alone is the most-common silent-failure mode" framing is stale. Verified current behavior (claude-code-guide vs `code.claude.com` discover-plugins + plugin-marketplaces docs): `/plugin marketplace update <name>` updates installed plugins in one step (catalog + version, NOT catalog-only), and `autoUpdate: true` does it automatically at session start. Reframe to **lead with autoUpdate** (the real answer to "why reinstall?"), then document the single `/plugin marketplace update` command as the manual fallback — keeping both facts explicit rather than just deleting the install line. Fix the autoUpdate config example (flat `"url"` → the real nested `source` + `autoUpdate`-sibling shape, matching the working `settings.json`).
- **Dogfood once (apply A in this very PR):** refresh `roadmap.md` "Now" (→ v1.5.1, Recently-shipped = PR Q/S/T/U + V1, ▶ Next up = **V2 rendered-capture, spike-first**; note #36 visual-history in flight); fix the stale "PR H3"/"Track-N next-up" framing; mark PR Q done (it's shipped, shown "in flight"). Sweep `plan.md` "Current Focus" + PR V1 (merged) → Recently Completed. Clear the shipped **FB-0041** reservation (V1's, never auto-cleared).
- **Version bump** `1.5.1 → 1.5.2` (shipped artifacts changed: ship/doctor/workflow): both manifests + README header + CHANGELOG.
- `dev-docs/{history.md (SAFETY — manifest + ship-pipeline change), feedback.md (**FB-0043**), plan.md (this block; reserved cleared at ship)}`.

**Scope (out):**
- **Fully-mechanical "narrative currency"** (is the Recently-shipped list / ▶ Next-up prose *correct*?) — too fuzzy to mechanize; stays prompt-level (A). The mechanical gate (B) checks the **version token only** — the cheapest signal that catches the worst drift.
- **Cross-run `## Flow run` aggregation / loop telemetry** — separate roadmap § Exploration item; not this.
- **A Stop-hook** enforcing currency — the ship preflight gate is automatic enough; no hook (consistent with the soft-enforcement posture).
- **Reordering the Deliverable-quality track vs #36's in-flight visual-history work** — the dogfood refresh reflects reality (V1 done, #36 in flight, V2 recommended); it does not re-sequence #36.

**Spec-walk:**
- [ ] Ship Step 5 has the 3 reconciliation sub-steps (roadmap Now / plan sweep / FB-reservation clear), each independently checkable. (verify: read Step 5)
- [ ] Ship has an automatic preflight currency gate asserting roadmap+plan version == `plugin.json`; documents the stable version-marker format; loud-fails on drift. (verify: read the gate; grep for the marker)
- [ ] `.claude/skills/ship/SKILL.md` carries the same reconciliation + currency check. (verify: read)
- [ ] `doctor/SKILL.md` has the version-currency check, explicitly marked secondary-to-ship; the queued "Check 2.5 → version strings" roadmap item is marked promoted/done. (verify: read doctor + roadmap)
- [ ] `workflow.md` Step 10 names the doc-currency discipline. (verify: read)
- [ ] `docs/upgrade.md`: leads with autoUpdate; documents `/plugin marketplace update` as the one-command manual path (updates installed plugins, not catalog-only); stale "install alone is the silent-failure mode" framing removed; autoUpdate example uses the nested `source`+`autoUpdate` shape. (verify: read + grep "install flow@flow" → no survivor as a required step)
- [ ] Dogfood applied: roadmap "Now" = v1.5.2 at ship, Recently-shipped + ▶ Next-up present, no "v1.2.6"/"PR H3"/"PR N next-up" survivors; plan Current Focus current; PR V1 + this PR in Recently Completed; FB-0041 reservation cleared. (verify: `git grep -nE 'v1\.2\.6|PR H3'` on roadmap → none)
- [ ] Version bumped 1.5.1→1.5.2 (both manifests + README + CHANGELOG); no `1.5.1` version-field survivors. (verify: `git grep '"version"'`)
- [ ] `claude plugin validate .` clean.
- [x] Run `/flow:critique-plan` before approval. (done: 2 REDIRECTs — F1 upgrade.md grounding reframed; F2 "scope drift" assessed false-positive, both surfaced at the gate; user approved option (a) fail-and-reconcile.)
- [x] Run `/flow:staff-review` after implementation. (done: engineer + push-further; ux light, design-engineer N/A. 0 BLOCKER. **Triangulated fix:** the 5b gate could false-pass on its own Recently-shipped enumeration → anchored the assertion to the `**Plugin at vX**` headline line (ship 5b + doctor 2.6); verified the stale-headline case now FAILS. NIT: added the empty-`$VER` guard to Check 2.6. 2 FOLLOW-UPs → roadmap § Later (jq-absent hardening; in-flight-vs-merged micro-check).)
- [ ] Ship (dev-side `/ship` while the install is < 1.4.0, or `/flow:ship` once re-installed) — the currency gate must pass on THIS PR (it dogfoods its own check; verified PASS).

**Confidence verdict per load-bearing assumption:**
- **Assumption:** The mechanical gate should check the **version token only**, leaving narrative currency to the prompt step. **Confidence:** HIGH. **Why:** a version-string mismatch is the cheap, unambiguous signal that catches the worst drift (the literal "v1.2.6 vs v1.5.1" bug); mechanizing prose-correctness is brittle and low-value. **If it flips:** add targeted narrative assertions (e.g. "no PR shown 'in flight' that's merged") as follow-ups.
- **Assumption:** Enforcement belongs at ship (automatic), with doctor as a secondary copy — not the reverse. **Confidence:** HIGH. **Why:** explicit user direction ("doctor is manual; I don't want to invoke this manually"). **If it flips:** n/a — this is a stated requirement, not a guess.
- **Assumption:** The gate should **fail-and-require-reconcile** (the agent fixes via Step A), not auto-edit silently. **Confidence:** MEDIUM. **Why:** Step A (prompt) does the edit with judgment; the gate just verifies it happened — keeps the mechanical layer simple and avoids a regex auto-rewriting prose. **If it flips:** you'd prefer the gate auto-bump the version line itself → small addition, but risks clobbering intentional wording. *Surface at the gate.*

**Risks / open questions:**
- **Brittle version parse.** Needs a stable marker. Mitigation: define + document the sentinel/format in the skill; the gate fails loudly (not silently) if it can't find it (FB-0009 fail-fast posture).
- **Collision with #36** (in flight, touches roadmap/feedback/reserved). Expected; handled by the reserved-numbers + stale-base protocol at ship (we just rehearsed this with #35/#37).
- **Dogfood double-edit:** this PR both *adds* the reconciliation step AND *applies* it once. Risk of the applied refresh drifting from what the new step prescribes — mitigated by running the new gate on this PR (it self-checks).

**Files touched (anticipated):** `plugins/flow/skills/ship/SKILL.md`, `.claude/skills/ship/SKILL.md`, `plugins/flow/skills/doctor/SKILL.md`, `plugins/flow/docs/workflow.md`, `docs/upgrade.md`, `dev-docs/roadmap.md`, `dev-docs/plan.md`, `plugins/flow/.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `README.md`, `CHANGELOG.md`, `dev-docs/history.md`, `dev-docs/feedback.md`, `dev-docs/reserved-feedback-numbers.md`.

---

## PR V1 — Structured visual acceptance criteria (MERGED #37, v1.5.1; Deliverable-quality track — see history.md)

**Restated request:** Give the plan a place to *declare* visual/UX success criteria the way it already declares behavioral ones (Spec-walk), so the agent can self-iterate against a visual bar and the human can see that bar at the approval gate. First (cheapest) link in the Deliverable-quality track (roadmap.md § "Deliverable-quality track"; FB-0041). It is the load-bearing *input* for V2 (rendered capture) and V3 (HTML walkthrough).

**Relationship to managed-autonomy Facet 4** (Handoff Notes, line ~30 — "plan-declared comprehensive success criteria enforced by plan-critic"): V1 is the **visual slice** of Facet 4, **declaration-only**. Facet 4's *plan-critic enforcement* half is deliberately deferred here (see Confidence verdict #2). V1 ships the field; a later increment (V1.1 or folded into V2/Facet 4) adds the critic rule. Naming them together so the two don't fan out into conflicting designs.

**Mode:** feature (small) | **Priority: high** (unblocks V2/V3; user-directed goal-state track)

**Goal:** Add a `Visual-walk:` block to flow's plan contract — a list of checkable visual/UX assertions a plan declares when the change has a UI surface. Purely *declarative* in V1: the field's consumers are the human (plan-approval + merge gates) and the agent's existing Step 8/9 visual dial-in. No mechanical verification of the criteria yet — that's V2.

**Why this PR exists / what it closes:** `workflow.md` Step 8 already instructs the agent to "dial in visual quality against the plan's **declared visual criteria**" (line ~214), but no plan field declares them — a dangling reference. V1 gives that instruction a home. Pairs with the existing `uiSurface` config slot (same gate `/flow:accessibility-review` uses): `Visual-walk` is required when `uiSurface=true` and the diff has UI, skipped otherwise — so non-UI projects/changes are unaffected.

**Design decision — distinct `Visual-walk:` block vs. folding visual checkboxes into `Spec-walk`:** distinct block. Rationale: V2's verify-build needs to *extract visual criteria separately* (different judge dimension, different capture path) the way it already parses `**Spec-walk:**`. A separately-addressable block makes V2/V3 extraction a labeled grep, not a heuristic classification of which spec-walk lines are "visual." Cost is one more template field; benefit is a clean machine-readable boundary for the rest of the track.

**BLOCKER fixes from `/flow:critique-plan` (resolved in-plan before the gate):**
- **B1 — field-count fan-out (FB-0010).** Adding an 8th required field would strand any "7 fields" count reference. Resolution: (a) **append `Visual-walk` as a new field (item 8), not insert "4.5"** — appending avoids renumbering; (b) **no magic count phrase** — the contract surfaces enumerate fields but never assert a total count, so a future Nth field can't strand a "N fields" phrase. *(Note: the list stays numbered, NOT de-numbered — B2 below depends on the `(4)`/`(5)` numbers staying valid; B1 is satisfied by removing count *phrases*, not the enumeration.)*; (c) **sweep the count** — `git grep -nE '(seven|[0-9]+)[ -]+(required )?(plan )?fields?'` fixed the two survivors in `dev-docs/plan.md` + `dev-docs/roadmap.md` (now number-agnostic); the shipped contract surfaces carry no count phrase.
- **B2 — spike/tiny mode interaction.** `plan-discipline.md` keys mode overrides to field *numbers* (`spike` replaces (4)+(5); `tiny` skips (4)+(5)). Resolution: `Visual-walk` is **appended (not wedged mid-list), and is N/A under `spike`/`tiny`** — stated explicitly the same way (4)/(5) are skipped — so the existing number-keyed overrides stay valid and untouched.

**Scope (in):**
- `plugins/flow/rules/plan-discipline.md` — **append** required field `Visual-walk` to the "Required plan fields" list (UI changes only; gated on `uiSurface`), with the "each assertion names a user-perceptible visual state + how it's checked" shape, mirroring the Spec-walk discipline; reference `designLanguagePath` as the source-of-truth. **Add a mode-interaction line:** `Visual-walk` is N/A under `spike`/`tiny` (alongside the existing (4)/(5) override sentence). **Keep the list numbered** (B2 needs the `(4)`/`(5)` mode refs valid); satisfy B1 by carrying no "N fields" count *phrase*, NOT by de-numbering.
- `plugins/flow/agents/planner.md` — add the `Visual-walk:` block to the canonical plan template (UI-only, with a one-line "omit for non-UI / spike / tiny" note).
- `plugins/flow/docs/workflow.md` §2 *Required fields* — narrate the new field + the spike/tiny N/A; carry no count *phrase* consistently with plan-discipline.md (B1; §2 is a bullet list, not numbered); **update §8 (line ~214) so "declared visual criteria" names the `Visual-walk` block** (closes the dangling reference — FB-0010 fan-out: the term must point at a real field).
- Version bump `1.5.0 → 1.5.1` (shipped artifacts changed: rules/ + agents/ + docs/): `plugins/flow/.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json` (both fields), README `## What v1.5.0 ships` header, `CHANGELOG.md` v1.5.1 entry.
- `dev-docs/{history.md, plan.md}` — decision-log entry + mark this item; `reserved-feedback-numbers.md` FB-0041 line cleared at ship (per protocol).

**Scope (out) — deliberately deferred to keep V1 the cheap unblocker:**
- **Any mechanical verification of visual criteria** (rendered capture, screenshot/baseline, VLM judging, verify-build extraction) → **V2**.
- **HTML walkthrough rendering** → **V3**.
- **The plan-critic enforcement half of Facet 4** (flag UI plan missing `Visual-walk`) → V1.1 / V2 (see Confidence #2).
- **A PreToolUse/Stop hook enforcing the field's presence** → not in the track; the field is contract-enforced like the plan's other required fields (prose + plan-critic), not hook-enforced.
- **`/flow:plan` authoring skill** → the optional/off-critical-path item noted in the track, separate PR.

**Spec-walk:**
- [x] `plan-discipline.md` lists `Visual-walk` as a required field for UI changes, gated on `uiSurface`, with the per-assertion shape (user-perceptible state + check method) + `designLanguagePath` reference. (verified: item 8 added at plan-discipline.md:33)
- [x] `planner.md` template includes the `Visual-walk:` block with the UI-only / omit-for-non-UI note. (verified: planner.md:56 + mode notes at :68/:70)
- [x] `workflow.md` §2 narrates the field AND §8's "declared visual criteria" phrase is updated to name the `Visual-walk` block — no dangling reference survives. (verified: workflow.md:118 §2 + :215 §8 names the block)
- [x] Field is consistently UI-gated across all three surfaces (no surface implies it's required for backend-only changes). (verified: `git grep -n 'Visual-walk'` — every mention carries the uiSurface/UI-only qualifier)
- [x] **(B2)** `Visual-walk`'s spike/tiny interaction is stated explicitly in `plan-discipline.md` + `planner.md` + `workflow.md` §2 (N/A under spike/tiny), and the existing number-keyed `(4)`/`(5)` mode-override sentence is left valid/untouched. (verified: append-not-insert; mode sentences updated in all three surfaces)
- [x] **(B1)** Field-count fan-out swept: contract surfaces (plan-discipline.md, workflow.md) carry no "N fields" magic-count phrase (enumeration kept so B2's `(4)`/`(5)` mode refs stay valid), and `git grep -nE '(seven|[0-9]+)[ -]+(required )?(plan )?fields?'` returns no stale survivors in shipped artifacts (only plan.md's own B1 explanation). (verified: grep clean on plugins/)
- [x] Version bumped 1.5.0→1.5.1 in both manifests (metadata + per-plugin) + README header + CHANGELOG entry; no `1.5.0` version-field survivors. (verified: all 3 version fields = 1.5.1; metadata-version fan-out caught + fixed at preflight)
- [x] `claude plugin validate .` clean. (verified: ✔ Validation passed)
- [x] Run `/flow:critique-plan` on this plan before approval (advisory; resolve BLOCKER/REDIRECT in-plan). (done: 2 BLOCKERs fixed in-plan; REDIRECT + FOLLOW-UP surfaced at the gate; user approved declaration-only + `Visual-walk` name)
- [x] Run `/flow:staff-review` after implementation. (done: 3 lenses — engineer/ux/push-further; design-engineer N/A no visual surface. 0 BLOCKER; 5 NITs fixed inline — expanded examples to cover interaction/loading/a11y states across both contract surfaces, moved planner template block to item-8 position for cross-surface consistency, propagated the per-diff UI qualifier to all 3 surfaces, fixed stale "de-number" Scope-in wording, removed a stray blank line; 5 FOLLOW-UPs routed to roadmap § Deliverable-quality V1.)
- [x] Ship to open the PR. (Shipped via the dev-side `/ship` because the dogfood install is flow 1.3.0 — predates the 1.4.0 auto-ship flag, so `/flow:ship` couldn't be model-invoked. Gates run manually for the audit trail: security-review CLEAN (.json manifests in diff → ran, no findings); a11y-review SKIPPED (uiSurface:false); verify-build SKIPPED (platform=library). history.md V1 entry written. Never merged — merge stays the human gate.)

**Confidence verdict per load-bearing assumption:**

- **Assumption:** A distinct `Visual-walk:` block (vs. folding visual checkboxes into `Spec-walk`) is the right shape, because V2 will extract visual criteria separately. **Confidence:** MEDIUM. **Why:** V2 isn't built, so the extraction need is projected, not observed; but it directly mirrors how verify-build already parses `**Spec-walk:**` separately. **If it flips:** if V2 ends up wanting them folded, collapse the block into spec-walk with a `[visual]` tag — a single-surface rename, reversible. *Surfaced for the approval gate.*
- **Assumption:** V1 should NOT touch `plan-critic.md` (no new "flag UI plan missing Visual-walk" rule), keeping it a pure template/contract change with no eval fixture required. **Confidence:** MEDIUM. **Why:** adding a critic rule triggers the quality bar's "no new rule without a fixture" requirement, enlarging V1; deferring keeps it the cheap unblocker, and the human still sees a missing visual bar at the approval gate. **If it flips:** you want the critic to mechanically flag UI plans with no `Visual-walk` (= Facet 4's enforcement half) → add a one-line `Internal incoherence` clause + one fixture in a fast follow (V1.1) or fold into V2. *This is the main decision I want your call on at the gate.*
- **Assumption:** A version bump (1.5.1) is warranted because shipped plugin artifacts (rules/agents/docs) change. **Confidence:** HIGH. **Why:** consistent with PR J/T precedent (prompt/docs artifacts that ship in the install bundle → bump). **If it flips:** you prefer no bump → revert manifest/README/CHANGELOG edits; single reversible sweep.

**Risks / open questions:**
- **Field could become decorative** if nothing consumes it before V2 ships. Mitigation: it has two live consumers on day one (human at both gates; the Step 8/9 dial-in instruction that currently references criteria with no home). The risk is real only if V2 stalls indefinitely — acceptable for the cheapest link.
- **Naming:** `Visual-walk` parallels `Spec-walk` cleanly; open to `UX-walk` / `Visual-spec` if you prefer. Cosmetic, set now to avoid a later rename fan-out.

**Files touched (anticipated):** `plugins/flow/rules/plan-discipline.md`, `plugins/flow/agents/planner.md`, `plugins/flow/docs/workflow.md`, `plugins/flow/.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `README.md`, `CHANGELOG.md`, `dev-docs/history.md`, `dev-docs/plan.md`, `dev-docs/reserved-feedback-numbers.md`.

---

## PR T — Flow-run PR descriptions (MERGED #32, v1.4.1)

**Mode:** feature (small), prompt/docs change to shipped artifacts | **Priority: medium (dogfood-driven UX)**
**Branch:** `claude/epic-northcutt-2d5e88` (off `origin/main` @ `4f5fba6`)
**Goal:** Make `/flow:ship` (and `/flow:ship-spike`) write PR descriptions that document the **full flow-loop run** — every step that ran, which steps were skipped and *why* (mode-dependent: spike/tiny; no UI surface; not-yet-shipped), and any significant decision or finding each step produced. A routine step shows `—`; the agent is explicitly told not to manufacture filler. Replaces the generic `## Reviews` blurb in the PR body with a per-step `## Flow run` table.

**Why this PR exists:** Prompted by dogfooding flow on another project where richer per-step PR descriptions were wanted. The current PR body (`## Reviews` one-liner) under-documents what the loop actually did — a reviewer can't see at a glance which gates ran, which were skipped (and whether the skip was legitimate), or what each step surfaced. A per-step table makes the loop's execution legible on the PR page itself, while keeping follow-ups canonical in the roadmap/plan docs.

**Scope (in):**
- `plugins/flow/skills/ship/SKILL.md` §7 — replace the `## Reviews` body block with a `## Flow run` per-step table + an instruction paragraph telling the ship agent how to populate it from THIS session's loop history (✓ ran / `skipped (<reason>)`; mode-dependent skips encoded; Notable = genuine signal or `—`; no manufactured notes).
- `.claude/skills/ship/SKILL.md` (flow's dogfood dev-side `/ship`) Step 4 — apply the same `## Flow run` body change for consistency. **Note:** this is NOT literally a copy of `/flow:ship` (CLAUDE.md treats them as distinct surfaces and documents no sync convention; the dev-side `/ship` is the older, simpler push+PR+merge skill). Only the PR-body section is reconciled; its merge behavior and step numbering are left as-is (out of scope).
- `plugins/flow/skills/ship-spike/SKILL.md` Step 7 — add a **trimmed** `## Flow run` table reflecting spike's fewer steps (/simplify + /flow:staff-review pre-marked `skipped (spike)`).
- `plugins/flow/docs/workflow.md` §10 (+ spike section) — narrate the new PR-body shape so the doc stays consistent.
- Version bump `1.4.0 → 1.4.1` (shipped plugin artifacts changed): `plugins/flow/.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json` (metadata + per-plugin), README `## What v1.4.0 ships` header, new `CHANGELOG.md` v1.4.1 entry. Cumulative description sentence appended.
- `dev-docs/{history.md,feedback.md,plan.md}` — decision-log entry, **FB-0019** (the dogfood-driven preference), this block.

**Scope (out):**
- Changing the dev-side `/ship`'s merge behavior or aligning it to `/flow:ship` (separate hygiene concern; this PR only touches its PR-body section).
- Adding a machine-readable loop-history artifact the agent reads from (the agent populates the table from in-session context, same as it already writes Summary/Test plan). A structured findings buffer exists only for verify-build; generalizing it is out of scope.
- Any change to which steps run / gate semantics. This PR is descriptive only.

**Spec-walk:**
- [x] `/flow:ship` §7 has a `## Flow run` table replacing `## Reviews`; Summary + Test plan retained. (verify: read §7)
- [x] Instruction text encodes all mode/config skip rules: spike (skips /simplify + staff-review), tiny (skips spec-walk + /simplify + staff-review), a11y skip on `uiSurface:false` or non-UI diff, security skip on doc-only, verify-build skip on `verifyEnabled:false`/`platform library|none`. (verify: grep §7 for each)
- [x] **Plan-critic REDIRECT resolved:** the "not-yet-shipped" wording is NOT the primary skip reason for security/a11y/verify-build — in v1.4.x all three ship and run (`ship/SKILL.md:215-217`), so their real skip reasons are the runtime-config states above. "not yet shipped" appears ONLY as a clearly-conditional generic fallback for a step genuinely absent from the *reader's installed flow version*. Writing "skipped — not yet shipped" for a step that actually ran would be the inverse of the user's honesty intent. (verify: read §7 — the not-yet-shipped clause is conditional, not applied to v1.4.x reviewers)
- [x] Instruction explicitly says Notable = genuine signal only, routine → `—`, and "do not manufacture notes". (verify: read)
- [x] Instruction preserves doctrine: follow-ups canonical in roadmap/plan; PR never merged by Claude. (verify: read)
- [x] `.claude/skills/ship/SKILL.md` Step 4 carries the `## Flow run` convention. **REVISED after staff-review BLOCKER:** the dev-side `/ship` is a distinct 6-step push+PR+**merge** command that orchestrates none of the loop's review steps — embedding the full table there produced a structurally-un-fillable artifact (the FB-0019 sub-rule (a) failure mode). Resolution: replaced the embedded table with a *conditional reference* to `/flow:ship` §7 ("if this PR came out of a driven loop, add a `## Flow run` table — see §7") + a note that the table documents the session's loop, not this skill's steps. Honors CLAUDE.md's distinct-surfaces convention (the user's "reconcile per CLAUDE.md" escape hatch). (verify: read .claude/skills/ship/SKILL.md Step 4)
- [x] `/flow:ship-spike` Step 7 has the trimmed `## Flow run` table with /simplify + staff-review pre-marked `skipped (spike)`. (verify: read)
- [x] `plugins/flow/docs/workflow.md` §10 + spike section narrate the `## Flow run` PR shape. (verify: read)
- [x] Version bumped to 1.4.1 in both manifests (3 version fields) + README header + CHANGELOG v1.4.1 entry; no `1.4.0`→`1.4.1` fan-out survivors that should have changed. (verify: `git grep -nE '1\.4\.0'` — surviving hits are historical references only)
- [x] **FB-0010 skip-vocabulary fan-out (plan-critic FOLLOW-UP):** after the simplify trim + staff-review BLOCKER fix, the authoritative skip-reason vocabulary lives in only TWO copies — `ship/SKILL.md` §7 and `ship-spike/SKILL.md` §7 (workflow.md §10 was trimmed to a pointer; the dev-side `/ship` now references §7 rather than copying). Ran the grep sweep — strings consistent across both authoritative copies. Durable `/flow:doctor` check routed to roadmap § Later. (verify: `git grep` sweep — done)
- [x] **Staff-review (4 lenses) ran:** 1 BLOCKER (dev-side un-fillable table — FIXED, see above), 1 NIT triangulated by engineer+UX+design-engineer (`✓ · skipped` Status cell read as "both" — FIXED: switched to `<✓ / skipped (reason)>` placeholder matching the Notable column + glyph-binding lead-in), 3 FOLLOW-UPs (worked filled example — DONE inline in workflow.md §10; doctor skip-vocab check → roadmap Later; cross-run aggregation → roadmap § Exploration). Push-further verdict: "surface at ceiling for its scope" + one exploration entry.
- [x] `claude plugin validate .` clean.
- [x] FB-0019 claimed in `reserved-feedback-numbers.md` before drafting; entry written; `dev-docs/history.md` entry written.

**Confidence verdicts:**
- **Assumption:** The ship agent has THIS session's full loop history in context at ship time, so it can populate the table without a new machine-readable artifact. **Confidence:** HIGH. **Why:** the agent already writes Summary + Test plan from in-session context; the loop steps happened in the same session/branch. **If it flips:** the table degrades to best-effort (some `—` where signal existed) — non-fatal, never wrong, just less rich; a structured loop-log artifact becomes a follow-up.
- **Assumption:** A version bump (1.4.1) is warranted because shipped plugin artifacts (ship/ship-spike skills + workflow.md) changed. **Confidence:** MEDIUM. **Why:** consistent with PR J precedent (prompt-only change → version bump); the alternative (no bump, like docs-at-root PRs H1/H2) doesn't apply since these files ship in the install bundle. **If it flips:** user prefers no bump → revert the manifest/CHANGELOG/README edits; single sweep, reversible. Surfaced here for the merge gate.

**Files touched (anticipated):** `plugins/flow/skills/ship/SKILL.md`, `.claude/skills/ship/SKILL.md`, `plugins/flow/skills/ship-spike/SKILL.md`, `plugins/flow/docs/workflow.md`, `plugins/flow/.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `README.md`, `CHANGELOG.md`, `dev-docs/reserved-feedback-numbers.md`, `dev-docs/feedback.md`, `dev-docs/history.md`, `dev-docs/plan.md`.

---

## PR S — Autonomous ship-readiness trigger (MERGED #30, v1.4.0)

**Mode:** feature | **Priority: high** (load-bearing for the autonomous-loop direction)
**Branch:** `claude/auto-ship-readiness-trigger` (off `origin/main` @ `efd31c4`)
**Goal:** Let the agent invoke `/flow:ship` on its own when a change is mechanically confirmed ready and low-risk, so the loop runs unattended between the two human gates (plan approval, merge) instead of requiring the user to type "ship it" at Step 8 Present. Ship still never merges — the merge gate is untouched.

**Why this PR exists:** The two load-bearing gates are plan + merge (`workflow.md`; `dynamic-workflows-2026-05.md:100` "a human at both ends"). `ship` carries `disable-model-invocation: true` set in PR 1 (v1.0.0) as a blanket conservative default and never revisited toward the stated autonomy direction (FB-0011 memory: "direction is 'toward' full autonomy ... staged is correct"). Auto-invoking `ship` does NOT violate the merge gate (ship opens a PR, never merges). The mechanical readiness signal already exists: `/flow:verify-build` emits `overall_verdict` + `exit_code` (Unknown ⇒ exit 1 ⇒ ESCALATE per FB-0011), and `ship` Step 2 already halts the pipeline on `exit_code: 1`. What's missing is the *trigger* that decides "ready + low-risk → fire ship" vs "escalate → pause at Present." This is the "explicit success criteria + mechanical stopping condition" the research (`agent-orchestration-2026-05.md`) names as the precondition for autonomous coding.

**Scope (in):**
- **Readiness predicate** (deterministic, evaluated at end of Step 7/8): all spec-walk checkboxes checked; no open BLOCKERs from `/simplify` + `/flow:staff-review`; no unresolved MEDIUM/LOW-confidence load-bearing assumptions; preflight green.
- **Risk gate** applying FB-0011 1:1: auto-advance only when aligned-with-spec + low-risk; **ESCALATE to Present** on any of {unclear path, significant risk, competing comparable options, one-way-door}.
- **Loop wiring:** Step 8 "Present" becomes *conditional* — auto-advance into `/flow:ship` when predicate + risk gate pass; else pause and present (current behavior).
- Flip `disable-model-invocation: true → false` on `ship`, **paired** with the trigger discipline (a portable rule encoding the predicate) so the model can't fire ship arbitrarily. Decide same for `ship-spike`.
- Ship's existing mechanical gates remain the safety net (stale-base, Step 1c bounded-retry preflight, Step 2 verify-build Unknown/FAIL-blocking). A falsely-confident auto-advance is caught by verify-build `exit_code: 1` → halt → present, pre-PR.
- Doc/contract updates: `workflow.md` Step 8 rewrite + Confidence-gates cross-ref; README auto/manual table (`ship` row MANUAL → conditional-AUTO); FB-0010 fan-out sweep on the `ship` invocation contract.

**Scope (out):**
- PR K `/flow:red-team` + trust-boundary detector + AUTO-FIX-SAFE routing for security findings — the *other* autonomous gate; stays PR L, independent.
- Any change to the plan gate or merge gate (both stay hard human gates).
- Hard Stop-hook enforcing the predicate (enforcement stays "soft"; hook deferred per `plan.md` v1.x autonomous-routines line).
- **Auto-ship when `verify-build` is skipped** (`verifyEnabled=false`, `platform=library|none`, or doc-only diff): **stays MANUAL in v1** (user decision 2026-05-29). No behavioral gate ⇒ default-to-ESCALATE per FB-0011. Auto-ship kicks in only on a real behavioral PASS.

**Spec-walk:**
- [ ] Readiness predicate documented in `workflow.md` Step 8, each condition independently checkable. (verify: read rewritten step)
- [ ] Risk gate maps 1:1 to FB-0011's four ESCALATE triggers. (verify: cross-check `feedback.md` FB-0011 + `feedback_autonomy_bar.md`)
- [ ] Skipped-verify-build path explicitly stays MANUAL. (verify: predicate requires `overall_verdict: PASS`, not merely "verify-build didn't fail")
- [ ] `ship` frontmatter `disable-model-invocation: false`; ship appears in the model's invocable skill set. (verify: grep + skill-list)
- [ ] A portable rule encodes the predicate + escalation so it's enforced as guidance. (verify: rule file present + auto-load glob)
- [ ] README auto/manual table + `workflow.md` consistent on the `ship` invocation contract (no survivors of "ship = MANUAL"). (verify: `git grep` sweep)
- [ ] Dogfood: low-risk change auto-ships without "ship it" typed; risky change (injected MEDIUM assumption) escalates to Present; verify-build Unknown halts pre-PR even after auto-advance.

**Confidence verdicts:**
- **Assumption:** The readiness predicate need not be perfect because verify-build is the load-bearing gate; the predicate only decides whether to *enter* ship, which re-confirms. **Confidence:** HIGH. **Why:** verify-build already provides the hard mechanical gate. **If it flips:** if predicate quality were the gate this would be unsafe — but it isn't (ship Step 2 catches it).
- **Assumption:** Flipping the flag + soft rule guidance suffices without a Stop-hook. **Confidence:** MEDIUM — flagged at Step 8 Present per the loop. **Why:** consistent with current soft-enforcement posture; model could over-eagerly advance. **If it flips:** add the deferred Stop-hook as a follow-up; doesn't change this PR's shape.

**Risks / open questions:**
- **One-way-door:** flipping `disable-model-invocation` is a real autonomy increase. Mitigated by verify-build hard gate + merge staying human; reversible (flip back).
- **Reward-hacking the predicate** (model marks checkboxes done without real work — the Potemkin class). Architecture leans on verify-build's adversarial behavioral check, not self-report.

**Files touched (anticipated):**
- `plugins/flow/skills/ship/SKILL.md` (frontmatter flag; readiness preamble)
- `plugins/flow/skills/ship-spike/SKILL.md` (decision pending in-PR)
- `plugins/flow/docs/workflow.md` (Step 8 rewrite + Confidence-gates cross-ref)
- `plugins/flow/rules/*.md` (new readiness-predicate rule)
- `README.md` (auto/manual table: `ship` row)
- `.claude-plugin/marketplace.json` + `plugins/flow/.claude-plugin/plugin.json` (version bump — confirm at ship)
- `dev-docs/{plan.md,history.md,feedback.md}` at ship time

**Staff-review FOLLOW-UPs (PR S, 2026-05-30 — captured, not fixed in-PR):**
- **Stale `Co-Authored-By: Claude Opus 4.7` in `plugins/flow/skills/ship/SKILL.md` commit template** (~line 342). Pre-existing; newly relevant because the auto-ship path will stamp it on unattended commits. One-line hygiene fix, next ship-pipeline touch.
- **No dogfood / eval coverage for the auto-advance / escalate / verify-build-Unknown-halt behaviors.** Evals confirm nothing *broke*, not that the new escalate path *works*. The verify-build hard gate makes the predicate non-load-bearing for safety, so this is a confidence item, not a blocker. Owner: testing, next iteration.
- **Invocation-mode label fragments across surfaces** (`AUTO·when-ready` / "auto-invocable" / "conditional gate" / "auto-advance"). Core predicate/gate vocabulary is consistent; only the mode *noun* drifts. Pin one canonical term with a glossary line in `workflow.md`, docs hygiene pass.
- Two push-further items routed to `roadmap.md` (Next: ship Step 2 auto-entry assertion; § Exploration: Stop-hook enforcement).

## SPIKE (DONE 2026-05-28) — Does blind independent refutation cut the reviewer false-positive tax?

**Status: COMPLETE.** Ran as a dynamic workflow over `template/base/bootstrap.sh` (3 stances → 15 findings → self-disproof vs blind-refute verification). **Verdict: do NOT encode blind refutation** — it rubber-stamped 15/15 while self-disproof refuted 5/15, because the FP bottleneck is *significance* judgment (which blindness strips), not *verification*. PR J's self-disproof stays. Full verdict + adjudication in `history.md` ("Reviewer-refutation spike — verdict").

**Not a write-off — re-test as the feature evolves.** One data point on one problem type (clean shell script). Tracked in `roadmap.md` § Exploration ("Dynamic-workflows-based review: re-test refutation across problem types, incl. UI") — re-run on UI projects, genuinely-buggy pre-review diffs, and migration-scale diffs before any general conclusion; and test the untested **informed-independent refutation** variant (fresh agent *with* context + a significance rubric).

**Byproduct:** found + fixed a real BLOCKER-class crash + 2 NITs in `bootstrap.sh` (see history entry below).

---

## PR H2 — upgrade.md cadence softening (MERGED, docs-only)

**Mode:** feature (small), docs-only at repo root | **Priority: highest (active consumer feedback)**
**Goal:** Fix the over-prescription in `docs/upgrade.md` that user-tested as too aggressive. Three copy-only edits, no behavior change, no version bump.

**Scope (in):**
- `docs/upgrade.md` — three sections rewritten:
  1. "When to run it" table — patch bumps marked optional + batchable; major/minor distinction explicit; "mid-session/just to be safe" rows added as explicit skip rows; TL;DR sentence on top with auto-update pointer.
  2. "Multi-project ritual" → "Multi-project: once per machine (for user-scope installs)" — corrects PR H1's factual error about per-session cache; distinguishes user-scope vs project-scope install behavior; adds `jq` check (with FB-0009 fail-loud fallback) for which scope you're in.
  3. Auto-update tradeoff section — softens "discipline is additive-only at patch level" (overpromise) to "aims to be additive-only... enforced by author care + lens-staff-engineer + /flow:doctor Check 2.5 — not a hard guarantee." Reframes version-aware recommendation as a principle ("when a major bump ships, default off until you've read the CHANGELOG") rather than naming a specific version.
- `dev-docs/history.md` — decision-log entry.
- `dev-docs/plan.md` — this block + Current Focus refresh.

**Scope (out):**
- Version bump (consistent with PR H1 — docs-at-root don't ship in the install bundle).
- New install-scope detection in `/flow:doctor` (routed to numbered FOLLOW-UP #27 — combined-lens explicitly promoted this from unnumbered candidate after catching FB-0010 fan-out at history.md routing).
- Backfilling the `per-session` error in any place it might also appear (PR H1's commit message + plan.md PR H1 block — those are historical; only the live consumer-facing doc needs correcting).

**Spec-walk:**
- [x] "When to run it" table has 7 rows with explicit major/minor/patch differentiation + mid-session "skip" rows.
- [x] TL;DR sentence appears before the table with auto-update pointer.
- [x] Multi-project section names the per-machine-for-user-scope reality.
- [x] Auto-update section softens the "additive-only" promise + uses principle framing rather than named-version.
- [x] `claude plugin validate` clean.
- [x] No version bump in either manifest; no CHANGELOG entry (docs-only, no plugin behavior changed).
- [x] No fan-out: search for "per-session" in `docs/upgrade.md` → no survivors.
- [x] Review pipeline: combined lens + security + a11y all spawned (per PR I's workflow-spawn discipline). Plan-critic deferred — small enough scope, combined into the lens pass.

**Files touched:** 3 — `docs/upgrade.md`, `dev-docs/history.md`, `dev-docs/plan.md`.

---

## PR J — Adversarial sharpening of the reviewer pipeline (merged, v1.2.4 → v1.2.5, squash `2e8ab3c`)

**Mode:** feature (prompt-only) | **Priority: high (research-grounded reviewer quality lift)**
**Goal:** Sharpen Flow's four reviewer surfaces along the dimensions deep research on adversarial review converges on, while encoding Anthropic's verbatim over-engineering warning to bound the false-positive tax. First of a three-PR sequence; PR K adds the `/flow:red-team` skill; PR L adds the autonomous gate.

**Scope (in):**
- `plugins/flow/agents/auditor.md` — new `## Principle` section (Anthropic's "flag only gaps that affect correctness or evidence-grounding" warning at principle level) + new `## Self-check before emitting` section (three-step disproof routine: name the specific session text that would invalidate the finding → re-scan for it → drop if found or fuzzy). Modeled directly on Anthropic's Claude Code Security "prove or disprove" pattern.
- `plugins/flow/agents/plan-critic.md` — same `## Principle` section adapted to the plan-vs-intent stance + new `## Self-check before emitting` (three-citation challenge variant — find a third citation that would resolve the apparent conflict). Also extends the `Internal incoherence` category to explicitly cover **fan-out contradictions within the plan** (count/name/slot/version referenced in N places where values disagree) — absorbs **PR-G FOLLOW-UP #5**.
- `plugins/flow/agents/lens-staff-engineer.md` — new `## How to read this diff` section (adversarial reading stance: "assume the diff is broken — what's the most likely break?") + the over-engineering warning. Composes with the existing FB-0010 silent-skip + fan-out hunts.
- `plugins/flow/skills/security-review/SKILL.md` — agent prompt at Step 3 shifts to **fully red-team identity** ("you are a red-team operator; your goal is to find an exploitable vulnerability"). "Hunt for:" → "Attack surface (categories to probe):" with each category gaining an attacker-mindset trailing question. New `Before emitting each BLOCKER/NIT` paragraph: trace the dangerous sink back to the input source; drop if not user-controllable in any realistic execution path. Output format gains "the attacker scenario in one sentence" on BLOCKER lines. **All operational logic preserved**: FB-0006/FB-0007 source-file early-exit, FB-0008 `[ -z ]` defaultBranch fallback chain discipline, FB-0009 fail-fast gh+jq, three-source diff capture.
- Version bump `1.2.4` → `1.2.5` in `plugins/flow/.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json` (both fields: metadata + per-plugin). Descriptions refreshed; v1.2.4 workflow-spawn-skip summary moves to CHANGELOG history-of-record.
- `README.md` — "What v1.2.4 ships" → "What v1.2.5 ships". Skill catalog, agent count (8), rules count (4), slot count (16) all unchanged — no fan-out drift.
- `CHANGELOG.md` — new v1.2.5 entry placed above v1.2.4 entry, following Date / Version / Headline / 2-4 bullets / Breaking changes: none pattern.
- `dev-docs/feedback.md` — new **FB-0011** (autonomy bar — the durable consumer-facing rule the user stated mid-PR).
- `dev-docs/history.md` — `SAFETY`-marked entry (safety-critical files modified per `.claude/rules/safety.md`: auditor.md, plan-critic.md, security-review/SKILL.md).
- `dev-docs/plan.md` — this block + Current Focus refresh + Handoff Notes refresh + PR I block retitled to "merged."

**Scope (out):**
- **`/flow:red-team` skill + agent** — deferred to PR K.
- **Trust-boundary detector + autonomous-invocation wiring** — deferred to PR L.
- **`flow.config.json.trustBoundaryPatterns` schema slot** — deferred to PR L (lands paired with the detector per FB-0003 schema-pairing discipline).
- **Model-family routing across reviewers** — Claude Code subagent SDK substrate not there yet; roadmap follow-up.
- **Debate loop / cross-critique** — explicitly out per "Judging with Many Minds" (arxiv 2505.19477) bias-amplification finding. Parallel-then-merge stays.
- **Numeric 0-100 confidence scores** — explicitly out per OpenAI Cookbook (classifier 98% vs numeric 92-95%). Categorical schema preserved.
- **`dev-docs/spec.md` broadening** — queued hygiene PR; out of scope here.

**Spec-walk:**
- [x] `git log --oneline -5` precondition check ran on each safety-critical file (auditor.md, plan-critic.md, lens-staff-engineer.md, security-review/SKILL.md). No recent commits mention crash/safety/integrity/fallback; clean to edit.
- [x] `auditor.md` — `## Principle` and `## Self-check before emitting` sections added; categories untouched; footer + forbidden-phrases untouched; output schema unchanged.
- [x] `plan-critic.md` — `## Principle` and `## Self-check before emitting` added; `Internal incoherence` extended with fan-out clause; two-citation rule preserved (the fan-out clause uses it).
- [x] `lens-staff-engineer.md` — `## How to read this diff` added immediately after title intro; FB-0010 hunts intact; output format unchanged.
- [x] `security-review/SKILL.md` Step 3 — agent prompt switches to red-team identity; over-engineering warning added; attack-surface categories preserve all nine entries with added attacker questions; disprove paragraph added; BLOCKER line format gains attacker-scenario requirement. Steps 1, 2, 4, 5 untouched.
- [x] `plugins/flow/.claude-plugin/plugin.json` version 1.2.4 → 1.2.5; description refreshed.
- [x] `.claude-plugin/marketplace.json` metadata.version 1.2.4 → 1.2.5 (both metadata + per-plugin); both descriptions refreshed.
- [x] `README.md` "What v1.2.4 ships" → "What v1.2.5 ships".
- [x] `CHANGELOG.md` v1.2.5 entry added above v1.2.4 with date / headline / 5 bullets / Breaking changes: none.
- [x] `dev-docs/feedback.md` FB-0011 entry written.
- [x] `dev-docs/history.md` `SAFETY`-marked entry added; engineer-lens-dogfood NIT (FB-0008 mislabel) corrected; rebase + renumbering documented.
- [x] `dev-docs/plan.md` — this block + Current Focus refresh + Handoff Notes refresh.
- [x] Preflight: `claude plugin validate .` clean (sanity — no manifest schema changes, just version + description string edits).
- [x] Engineer-lens dogfood (parallel Agent invocation of the freshly-sharpened lens prompt against this PR's diff): 0 BLOCKER + 1 NIT (FB-0008 mislabel — fixed inline) + 1 FOLLOW-UP (phrasing precision — fixed inline). Meta-validation: the sharpened lens caught a real factual error in its own PR.
- [x] Existing eval fixtures pass: 5 passed / 0 failed / 3 skipped (pre-existing scaffold cases). No regression from the prompt edits.
- [x] FB-0008 stale-base preflight ran before push — caught the parallel PR I collision; rebased + renumbered cleanly.
- [ ] Self-fan-out grep post-rebase: no `v1.2.4` or `PR I` survivors in PR J's own content (CHANGELOG/history/plan v1.2.4 references are now ONLY about the merged PR I).
- [ ] `/flow:security-review` + `/flow:accessibility-review` final-pass: both will early-exit on this prompt-only diff (no source files beyond the 2 JSON manifests; no UI). Audit-trail STATUS: SKIPPED is the load-bearing artifact (per PR I discipline).
- [ ] Commit + push + `gh pr create` via the documented `/flow:ship` discipline (NOT direct `gh pr create` — PR I discipline applies here too).

**Confidence verdicts:**

**Assumption:** Prompt-only edits to reviewer system prompts are sufficient to operationalize the published research findings (adversarial framing, prove-or-disprove, over-engineering bound). No new agents, no new orchestration, no schema changes required.
**Confidence:** HIGH
**Why:** Anthropic's own Claude Code Security and Code Review plugin both encode this pattern at the prompt level, not in orchestration. The "evidence or silence" rule that Flow's reviewers already enforce composes naturally with the prove-or-disprove self-check. PR K adds new orchestration; PR J deliberately stays prompt-only to isolate the behavior change.
**If it flips:** Eval fixtures regress (existing borderline cases that were flagged on weak evidence now drop incorrectly). Tune the prove-or-disprove instructions or carve specific exclusions per category. Single-file fix per reviewer.

**Assumption:** Bundling PR-G FOLLOW-UP #5 (plan-critic fan-out hunt) into PR J doesn't expand scope meaningfully because plan-critic.md is already being edited for the prove-or-disprove section.
**Confidence:** HIGH
**Why:** One-line addition inside the existing `Internal incoherence` category description. No new category, no schema change. The two-citation rule applies unchanged. PR H proper's queue gets one item shorter.
**If it flips:** PR-G review caught more from FOLLOW-UP #5 than expected; carve out a separate PR. Low likelihood — the FOLLOW-UP entry itself says "one-line bullet under Internal incoherence."

**Files touched:** 10 — `plugins/flow/agents/auditor.md`, `plugins/flow/agents/plan-critic.md`, `plugins/flow/agents/lens-staff-engineer.md`, `plugins/flow/skills/security-review/SKILL.md`, `plugins/flow/.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `README.md`, `CHANGELOG.md`, `dev-docs/feedback.md`, `dev-docs/history.md`, `dev-docs/plan.md` (this file).

---

## PR I — Workflow-spawn prevention (merged, v1.2.3 → v1.2.4, squash `da0b2c4`)
## PR I — Workflow-spawn prevention (merged, v1.2.3 → v1.2.4, squash `da0b2c4`)

**Mode:** feature (small) | **Priority: highest (pre-dogfood mechanical defense)**
**Goal:** Encode workflow-step discipline so future loops don't silent-skip the ship pipeline. User explicitly requested PR I after PR H1's review surfaced the issue + the "1 incident isn't usually enough threshold but the fix is trivially mechanizable" tradeoff was made explicit.

**Root cause analysis:** PR H1's actual skip wasn't "forgot to add `/flow:security-review` to the pipeline" — it was "bypassed `/flow:ship` entirely and ran `gh pr create` manually." `/flow:ship` already spawns security + a11y in Step 2. So the defense isn't "add more spawns to staff-review"; it's "make it harder to skip `/flow:ship` without noticing."

**Scope (in):** ← reduced from initial 12-file scope after observing audit/critique SKILL.md files end with rigid `## Output` blocks ("Do not add commentary before or after"). Adding "After this skill" footers there would conflict with the subagent output contract. Reduced scope keeps the footer addition tight to staff-review (the human-facing orchestration skill that's the natural pre-ship inflection point) + relies on workflow.md + `/flow:ship` Step 1.0 surface for the rest. Plan-critic Finding 1 REDIRECT confirmed this reduction.

- `plugins/flow/skills/staff-review/SKILL.md` — append "After this skill" footer naming `/flow:ship` (which spawns security + a11y automatically) as the canonical next step. Reframe the existing "ends with work ready, not merged" line into actionable forward motion. **Primary fix for the root cause.**
- `plugins/flow/skills/ship/SKILL.md` Step 1.0 — strengthen the assumption-surface block. Add `⚠️` per ASSUMES line + a new REMINDER paragraph naming the workflow-step silent-skip class explicitly + the "Always invoke /flow:ship, never `gh pr create`" rule. **Primary fix for the root cause.**
- `plugins/flow/docs/workflow.md` Step 10 — add an explicit "Never bypass `/flow:ship` with `gh pr create` directly" discipline. Names the failure mode: skipping `/flow:ship` skips the entire Step 2 (security + a11y reviews). **Primary fix.**
- `.claude/rules/general.md` (project-dev only — flow's own dev infra) — new "Workflow discipline" subsection: always invoke `/flow:ship` from this repo's `.claude/skills/ship`; never `gh pr create` directly. **Defense-in-depth for this repo's own development.**
- `CHANGELOG.md` — new v1.2.4 entry.
- `.claude-plugin/marketplace.json` + `plugins/flow/.claude-plugin/plugin.json` — v1.2.3 → v1.2.4 + description refresh.
- `dev-docs/history.md` — entry with SAFETY marker (manifest + ship/SKILL.md edits — both on safety paths list).
- `dev-docs/plan.md` — this block + mark FOLLOW-UP #20 done.

Plan-critic Finding 7 framing FOLLOW-UP: reviewer-footer is reframed above as "Primary fix"; staff-review IS the canonical inflection point where the workflow author chooses next-step, so the footer addresses the root cause directly. Workflow.md Step 10 + general.md are belt-and-suspenders.

**Scope (out):**
- Auto-spawn missing reviewers from `/flow:staff-review` (would need session-introspection helper; deferred per existing FOLLOW-UP).
- Pre-commit hooks (rejected: install friction; consistent with PR G decision).
- `/flow:upgrade` skill (FOLLOW-UP #15 — separate scope).
- README.md update (the existing version-log line just links to CHANGELOG.md per PR H1; no per-version inline entry needed).

**Spec-walk:**
- [ ] All 5 reviewer skills (`staff-review`, `critique-plan`, `audit-plan`, `audit-completion`, `log-disagreement`) have a uniform "After this skill" footer naming next step.
- [ ] `workflow.md` Step 10 has the explicit "never `gh pr create` directly" discipline.
- [ ] `/flow:ship` Step 1.0 assumption surface is visually louder (`⚠️` per line).
- [ ] `.claude/rules/general.md` has the new Workflow discipline subsection.
- [ ] CHANGELOG.md has a v1.2.4 entry; date matches the merge date; "Breaking changes: none" callout present.
- [ ] Both manifests bumped + descriptions refreshed.
- [ ] `claude plugin validate` clean.
- [ ] `/flow:doctor` Check 2.5 still emits expected output (12 historical-narrative WARN — unchanged on the current dev-docs/).
- [ ] Self-fan-out grep: no v1.2.3 references in v1.2.4-bumped descriptions; skill/agent/lens counts unchanged.
- [ ] **`/flow:security-review` + `/flow:accessibility-review` ARE spawned during this PR's review pipeline** (the meta-discipline — eat my own dog food). Per-diff gates will early-exit cleanly (no source/UI files in PR I diff — markdown + skill body edits only).
- [ ] `dev-docs/history.md` entry written with SAFETY marker.

**Confidence verdicts:**

**Assumption:** Per-skill exit reminders + workflow.md strictening will catch the workflow-spawn-skip class going forward without needing orchestration-level auto-spawn.
**Confidence:** MEDIUM
**Why:** Prompt-level reminders improve LLM behavior probabilistically. The exit-reminder is concrete enough that the next loop is likely to notice + act on it. Adversarial review + the FB-0010 lens hunt remain the backstop. If a 2nd workflow-spawn-skip incident occurs after PR I lands, that's the signal for orchestration-level auto-spawn (the harder fix).
**If it flips:** Promote to auto-spawn in `/flow:staff-review` Step N. Cost: session-introspection helper. Horizon: PR if/when triggered.

**Files touched:** 10 — `plugins/flow/skills/staff-review/SKILL.md`, `plugins/flow/skills/ship/SKILL.md`, `plugins/flow/docs/workflow.md`, `.claude/rules/general.md`, `CHANGELOG.md`, `README.md` (header rename only — `## What v1.2.3 ships` → `## What v1.2.4 ships`; caught by FB-0010 grep-first-edit-second pre-commit sweep), `.claude-plugin/marketplace.json`, `plugins/flow/.claude-plugin/plugin.json`, `dev-docs/history.md`, `dev-docs/plan.md`.

---

## PR H1 — Upgrade docs + CHANGELOG (MERGED, docs)

**Mode:** feature (small), docs-only | **Priority: highest (pre-install shore-up)**
**Goal:** Make the update workflow discoverable + auditable before consumer install. Two cheap fixes from the "is the update infrastructure solid?" Tier-2 audit — the rituals that prevent silent version drift between 2 active consumer projects.

**Scope (in):**
- New file: `docs/upgrade.md` — the 2-command update ritual (`/plugin marketplace update flow` → `/plugin install flow@flow` → `/flow:doctor`), when-to-run guidance, verification steps, troubleshooting (FB-0005 silent-failure mode, marketplace-key-mismatch, `/flow:doctor` Section 1 failures), optional auto-update opt-in with breaking-change warning.
- New file: `CHANGELOG.md` at repo root — extracted version-by-version from current README + history.md. Reverse chronological, one-liner per version + 2-3 bullets, breaking-change callouts (none yet). Replaces the inline "Versions:" block at the bottom of README.
- `README.md` — replace inline "Versions:" block with link to `CHANGELOG.md`; add cross-link to `docs/upgrade.md` in install + bootstrap sections so consumers can find it after first install.
- `docs/bootstrap.md` — add a "Keeping flow up to date" pointer to `docs/upgrade.md` at the end (after first PR walkthrough).
- `docs/migration.md` — same pointer (existing-project consumers also need to know).
- `dev-docs/history.md` — decision-log entry.
- `dev-docs/plan.md` — this block + Current Focus refresh.

**Scope (out):**
- **Version bump** — pure docs-at-root change; doesn't ship in plugin install (manifests unchanged); consumers reading on GitHub get the new docs without a re-install. Spares users a no-op upgrade ritual.
- **`minFlowVersion` slot + `/flow:doctor` Check 6** — deferred to PR H proper; mechanical defense for silent version drift, but ships best paired with the slot-count generalization (PR-G FOLLOW-UP #2).
- **Post-merge GitHub Actions reminder** — deferred; cheap when needed but assumes a feedback mechanism we don't have yet.
- **CHANGELOG auto-generation from history.md** — manual extraction this time; if drift becomes a maintenance burden, add a script later.

**Spec-walk:**
- [ ] `docs/upgrade.md` exists with: what-it-is, when-to-run, 2-command ritual, verification, troubleshooting (≥3 cases), auto-update note.
- [ ] `CHANGELOG.md` exists at repo root with v1.0.0 through v1.2.3 entries; reverse chronological; each entry has date + headline + 2-4 bullets + "breaking changes: none" or explicit list.
- [ ] `README.md` — inline "Versions:" block removed; replaced with one-line link to CHANGELOG.md; install section cross-references upgrade.md.
- [ ] `docs/bootstrap.md` + `docs/migration.md` — both have a one-line pointer to `docs/upgrade.md`.
- [ ] `claude plugin validate .` clean (no manifest changes; sanity).
- [ ] `/flow:doctor` Check 2.5 emits expected output: against flow's own tree, WARN with ~12 historical-narrative survivors in `dev-docs/history.md` + `dev-docs/feedback.md` + `dev-docs/handoffs/*` (intentional — those are accurate prose about past schema states, not stale current claims). Against a clean consumer project, PASS. Validated in both bash + zsh + sh (POSIX `set -- ; for; "$@"` pattern; an earlier `$SCAN_TARGETS` string-join silently no-op'd under zsh — yet another FB-0010 silent-skip caught at pre-commit).
- [ ] No version bump in either manifest; no v1.2.4 references anywhere.
- [ ] Self-fan-out grep: no contradictions introduced (CHANGELOG vs README vs history.md version notes match).
- [ ] `dev-docs/history.md` entry written (no SAFETY marker — no manifest/error-handling changes; verified against `.claude/rules/safety.md` `paths:` list — none of PR H1's 7 files match).
- [ ] CHANGELOG entries follow Keep-a-Changelog-style (Date + headline + bullets + "Breaking changes:" callout, no SHA/branch/tradeoffs blocks) — distinct from `dev-docs/history.md` format spec; the two intentionally diverge (CHANGELOG is consumer-facing terse, history.md is internal-tracking verbose).

**Confidence verdicts:**

**Assumption:** Pure docs-at-root changes don't need a version bump because they don't ship in the plugin install (consumers fetch them from GitHub, not via `/plugin install`).
**Confidence:** HIGH
**Why:** `docs/` is not packaged into the plugin binary — only `plugins/flow/*` ships. Consumers on v1.2.3 read the new docs from GitHub the moment we merge; no client-side action required. Spares a no-op `/plugin marketplace update`.
**If it flips:** A consumer reports they didn't NOTICE the new docs (they're delivered either way via GitHub, but the consumer's habit is to ignore unbumped versions). Bump to v1.2.4 then as a discoverability signal (not a delivery mechanism — the docs were already there). Single-file edit.

**Assumption:** CHANGELOG.md manual extraction matches the inline README version notes + history.md decisions without drift.
**Confidence:** MEDIUM
**Why:** Manual extraction from two sources risks scribal mismatch; FB-0010 specifically warns against this. Mitigation: I'll grep both sources after writing CHANGELOG and reconcile; the FB-0010 lens-engineer hunt + Check 2.5 will catch survivors at review.
**If it flips:** Lens-engineer flags fan-out between CHANGELOG and README. Fix inline before merge.

**Files touched:** 7 — `docs/upgrade.md` (new), `CHANGELOG.md` (new), `README.md`, `docs/bootstrap.md`, `docs/migration.md`, `dev-docs/history.md`, `dev-docs/plan.md`.

---

## PR M — Bounded-retry mechanical preflight in /flow:ship + ship-spike (MERGED #22, v1.2.6)

**Mode:** feature (small-medium) | **Priority: medium**
**Goal:** Add a bounded-retry mechanical preflight (new Step 1c) to `/flow:ship` and `/flow:ship-spike`. Runs the project's preflight command (a config slot the project owns); on non-zero exit, fixes and retries up to N=3 with oscillation detection via diff-hash. Loops ONLY on externally-verifiable exit codes (the preflight script's exit status) — never on reviewer judgment. Encodes the research-pass principle: the only "goal" we trust as a loop exit is a tool's exit code, not another model's approval.

**Why this PR exists:** User-driven exploration of whether to add `/loop`-style iteration to the workflow. Anthropic's "Building Effective Agents" names the evaluator-optimizer pattern with mandatory "stopping conditions (such as a maximum number of iterations)"; the 2026 Agentic Coding Trends Report names "explicit success criteria" as the precondition for verification. Flow's current ship pipeline runs typecheck ONCE at Step 3 after reviewer fixes — there's no mechanical-quality preflight loop. This PR adds it, in the one slot where the exit signal is unambiguous (external tool exit code), and explicitly forbids the same shape on reviewer-judgment outputs.

**Scope (in):**
- New slot: `flow.config.json.preflightCmd` (shell command; project-owned at same trust level as `typecheckCmd`). FB-0003 pair-slot-with-consumer satisfied (consumer is the new Step 1c).
- `plugins/flow/skills/ship/SKILL.md` — new Step 1c between 1b and 2: bounded-retry preflight with N=3 cap, diff-hash oscillation detection, docs-only early-exit (reusing `sourceFilePatterns` from the schema), loud-warning if unset, fail-fast if `preflightCmd` resolves to a missing file.
- `plugins/flow/skills/ship-spike/SKILL.md` — same Step 1c block, mirrored verbatim (consistency IS the value per FB-0009 lineage). Existing Step 2 `typecheckCmd` block stays as-is for projects that haven't set `preflightCmd`; schema description documents precedence (both set = both run).
- `plugins/flow/schema/flow.config.schema.json` — add `preflightCmd`; update `typecheckCmd` description to name the precedence relative to `preflightCmd`.
- `docs/bootstrap.md` — add `preflightCmd` example alongside `typecheckCmd` in the config-population section. One-line note on N=3 retry semantics.
- `plugins/flow/evals/security/test_preflight_retry.py` — assert-on-shape tests paralleling `test_cwd_constraint.py` / `test_malicious_config.py`. 5 cases: (a) unset slot → loud-warning text present + no retry attempted; (b) `preflightCmd` with shell metas → opaque-string pass-through (no command execution); (c) SKILL.md text grep — verify N=3 cap, oscillation language, fail-fast-on-missing-file branch all present; (d) SKILL.md text grep — verify "do NOT modify tests to make them pass" rule present; (e) schema validates against the slot.
- `plugins/flow/.claude-plugin/plugin.json` + `.claude-plugin/marketplace.json` — v1.2.5 → v1.2.6. Update description to mention bounded-retry preflight (1 sentence).
- `dev-docs/history.md` — decision-log entry with the research-pass citations + the loop-only-on-mechanical-exit principle.
- `dev-docs/feedback.md` — **FB-0012** capturing the design rule: "bounded-retry contracts in agent loops require oscillation detection by diff-hash; pure iteration cap is insufficient because LLM fix-loops can drift without repeating." Self-feedback from this PR's research pass.

**Scope (out):**
- Looping the reviewers (security, accessibility, staff-review). Single-pass is load-bearing — looping LLM-judgment outputs is reward-hackable. The PR body documents this as the rejected shape.
- A standalone `/flow:preflight` user-facing skill. The loop only fires inside `/flow:ship` / `/flow:ship-spike` so it stays under the surrounding gates (stale-base, gh+jq, something-to-ship).
- Shell-script harness around the retry. SKILL.md is the orchestration; Claude follows the cap in natural language. If a session ignores the cap, the per-attempt log line ("Preflight attempt N of 3") makes the off-contract behavior visible.
- A `flow.config.json.preflightMaxAttempts` slot. N=3 is hardcoded for now (FB-0003 — don't ship slots without consumers; if 3 proves wrong, add the slot then).
- Generalizing the retry contract to a reusable doc snippet (`plugins/flow/docs/retry-contract.md`). Defer until a second bounded-retry block exists; copy-paste once is fine.

**Spec-walk:**
- [ ] `flow.config.schema.json` has `preflightCmd` slot with description, examples, precedence note. `typecheckCmd` description updated.
- [ ] `/flow:ship` Step 1c exists between 1b and 2. Contract names: N=3 cap, diff-hash oscillation abort, docs-only early-exit via `sourceFilePatterns`, fail-fast on missing-script, loud-warning on unset.
- [ ] `/flow:ship-spike` Step 1c exists (verbatim block).
- [ ] `docs/bootstrap.md` documents `preflightCmd`.
- [ ] `plugins/flow/evals/security/test_preflight_retry.py` 5 cases pass locally.
- [ ] Both manifests at v1.2.6; descriptions mention bounded-retry preflight.
- [ ] `claude plugin validate .` clean.
- [ ] FB-0002 pre-commit grep clean (no new tool invocations missing from `allowed-tools`).
- [ ] FB-0003 grep clean: `preflightCmd` appears in ≥4 surfaces (SKILL.md ×2, schema, fixture, bootstrap.md, history.md).
- [ ] FB-0010 consistency check clean: any "16 slots" mention in docs/CLAUDE.md needs to become "17 slots" to match the new schema cardinality.
- [ ] `dev-docs/history.md` + `dev-docs/feedback.md` updated.
- [ ] Self-test: stage a docs-only diff; verify Step 1c early-exits without invoking `preflightCmd`. Stage a source diff with a failing test fixture; verify the bounded-retry contract is followed (Claude session reads the contract and respects N=3 even if not actually fixing).

**Confidence verdicts:**

**Assumption:** N=3 is the right hardcoded cap.
**Confidence:** MEDIUM-HIGH
**Why:** Anthropic guidance names "maximum iterations" without prescribing N. 3 is a deliberate design call — enough for fix-A-broke-B-fix-B, not enough to wander. Consistent with Magentic's separately-configurable caps + Trigger.dev's example "up to 10 iterations" — both frame iteration limits as design choices, not empirically-tested constants. Higher caps consume budget on cases that should fail loud.
**If it flips:** Add `preflightMaxAttempts` slot. Single-file change; contract shape unchanged.

**Assumption:** Diff-hash oscillation detection catches the real failure mode without unacceptable false positives.
**Confidence:** MEDIUM
**Why:** Pure oscillation (A↔B↔A) is exactly what hashing catches. Drift (A→B→C, each broken) it doesn't catch — N=3 catches drift by exhaustion. False-positive shape: Claude makes the same correct fix twice because the second failure was a different issue. Both diffs hash identically → spurious oscillation abort. Mitigation: attempt logs preserve the situation; user can see and decide.
**If it flips:** Add per-attempt failure-signature comparison (same error + same diff = oscillation; different error + same diff = retry-without-progress, also abort).

**Assumption:** Prompt-driven looping (Claude follows N=3 in natural language) is reliable enough to ship without shell-harness fallback.
**Confidence:** MEDIUM
**Why:** Flow already orchestrates 11-step workflows through prompt semantics — `/flow:ship` has 9 numbered steps held across many sessions. The cap is no harder to follow. Risk: a session that ignores the cap and keeps fixing. Mitigation: per-attempt log line makes off-contract behavior visible.
**If it flips:** Wrap retry in a shell script under `plugins/flow/tools/preflight-retry.sh`; SKILL.md invokes that. Defer until v1 ships and we see the failure mode.

**Assumption:** Step 1c belongs BEFORE reviewers (Step 2), not after.
**Confidence:** HIGH
**Why:** Running preflight before reviewers means reviewers see code that already typechecks — what they expect. Running it after risks reviewers + Claude fighting over the same file across iterations, which is exactly the reward-hacking failure mode the research pass identified.
**If it flips:** Step 3's existing one-shot typecheck would need to absorb the retry behavior. Real restructure; defer.

**Risks:**
- **Reward hacking via test modification.** Claude's "fix" could be to xfail or delete a failing test. Mitigated in the prompt contract ("Make the minimal fix. Do NOT modify or disable tests unless the failure is a genuine test bug — and if so, name the bug explicitly in the attempt log"). Backstop: human merge gate at Step 7 still applies.
- **Preflight speed.** A 5-minute test suite × 3 = 15 minutes worst case. Bootstrap doc recommends pointing `preflightCmd` at a fast subset (typecheck + lint), with CI handling the full suite.
- **Cross-pollination with PR D's per-diff early-exit.** Step 1c reuses `sourceFilePatterns` (already in schema since PR D); docs-only diffs skip the loop entirely. No additional regex needed.
- **Eval fixture is text-grep based, not runtime-execution.** Real Claude runs are non-deterministic; the fixture asserts the SKILL.md contract is _written_, not _executed end-to-end_. Same pattern as `test_cwd_constraint.py` / `test_malicious_config.py`. Sufficient for FB-0003 (slot has a consumer at land time); not sufficient for "does Claude actually obey the cap." That's a dogfood-time question, not a CI-time question.
- **Manifest description length.** v1.2.5 description is already long; adding a sentence for v1.2.6 pushes it further. Acceptable cost; consumers read it once.

**Files touched:**
- `plugins/flow/schema/flow.config.schema.json` (new slot + description update)
- `plugins/flow/skills/ship/SKILL.md` (new Step 1c)
- `plugins/flow/skills/ship-spike/SKILL.md` (new Step 1c + Step 2 cleanup)
- `docs/bootstrap.md` (preflightCmd example)
- `plugins/flow/evals/security/test_preflight_retry.py` (new file)
- `.claude-plugin/marketplace.json` (v1.2.6 + description)
- `plugins/flow/.claude-plugin/plugin.json` (v1.2.6 + description)
- `dev-docs/history.md` (decision-log entry)
- `dev-docs/feedback.md` (FB-0012)
- `dev-docs/plan.md` (this block + Current Focus refresh)
- `template/base/CLAUDE.md.template`, `template/base/bootstrap.sh`, `plugins/flow/skills/doctor/SKILL.md`, `README.md` ×2 ("16 slots" → "17 slots" FB-0010 sweep)

### Review pipeline findings (5 parallel lenses)

Spawned via Agent subagents emulating the planned skills per FB-0001 (plugin not installed in dev environment). Lenses: staff-engineer, push-further, plan-critic, security, auditor.

**Findings:** 1 BLOCKER + 11 NITs + 11 FOLLOW-UPs + 6 EXPLORATIONs. BLOCKER and NITs fixed in-tree; FOLLOW-UPs routed below; EXPLORATIONs added to `dev-docs/roadmap.md` § Exploration.

**BLOCKER (plan-critic; FIXED inline):**
- `template/base/CLAUDE.md.template` and `template/base/bootstrap.sh` still said "16 slots" after the FB-0010 sweep claimed completion. Exactly the fan-out class FB-0010 was written to defend. Fixed. Validates PR H+ FOLLOW-UP #2 (generalize doctor Check 2.5 to scan `template/` files too).

**NITs fixed inline:**
- (engineer) Whitespace-only `$PREFLIGHT_CMD` not treated as unset — added `printf '%s' | tr -d '[:space:]'` check in both Step 1c blocks.
- (engineer + security converged) `sourceFilePatterns` regex not validated before use — copied PR D's GREP_RC validation pattern. Closes FB-0010 silent-skip class.
- (engineer) Step 1c only checked committed diff — expanded to 3-source check (committed + uncommitted + untracked) matching PR D's `/flow:security-review` lineage.
- (engineer) ship-spike Step 2 preflight now overlaps Step 1c — trimmed Step 2 to one-shot typecheck only (parallels `/flow:ship` Step 3's role).
- (push-further) Suppressor list missing common patterns — added `# type: ignore`, `// biome-ignore`, `#[allow(...)]` to both Step 1c retry contracts.
- (push-further) Eval `do-not-disable-tests` regex brittle ("Never disable tests" would fail it) — broadened to accept do not / don't / never / must not + modify/disable/stub/skip/silence + tests. Suppressor regex expanded to cover all 7 patterns.
- (auditor ISSUE 1) "Empirically 3 is the elbow" overstated as literature finding — reframed as "deliberate design call consistent with non-prescriptive guidance" in history.md + plan.md Confidence verdict.
- (auditor ISSUE 2) "6 contract assertions" miscount — clarified to "6 test functions exercising 7 load-bearing contract markers" in history.md. FB-0010 fan-out drift caught.

**FOLLOW-UPs routed:**

1. **(push-further FOLLOW-UP)** STATUS marker for Step 1c itself (`STATUS: PREFLIGHT_PASSED`/`SKIPPED`/`FAILED`/`ABORTED`). Natural extension of PR N's STATUS-marker work on the two reviewers. Horizon: bundle into PR N if scope permits, else PR O.
2. **(push-further FOLLOW-UP)** Roll-forward story on abort — when Step 1c aborts after 3 attempts, the partial fixes are left in tree with no signposting. Add structured abort summary (per-attempt one-line stderr + diff-hash + files-touched) dumped to `.context/preflight-attempts-<timestamp>.log`. Horizon: post-PR-H4, only if dogfood produces an actual oscillation abort. Don't preempt FB-0003.
3. **(push-further FOLLOW-UP)** `preflightMaxAttempts` slot defensibility — track in roadmap.md "config-slot pressure" section; defensible trigger is ≥2 real-project reports where N=3 misfires (slow integration tests where attempt 3 is plausibly close; flaky tests where a different cap would clear). Until then hardcoded is correct.
4. **(plan-critic FOLLOW-UP)** `template/base/flow.config.json.example` doesn't include `preflightCmd` example or `$comment-preflightCmd` doc key. Consumers running bootstrap won't see the new slot at install time. Cosmetic for current dogfood; promote to BLOCKER if next consumer dogfood doesn't surface it. Horizon: PR N or H4.
5. **(plan-critic FOLLOW-UP)** Forward-planning H3/H4/H5 blocks ended up in PR M's diff (scope creep beyond stated Scope (in)). Not BLOCKING — they live only in plan.md, no plugin artifact changes — but tighter PR atomicity for future H-series. Convention update: forward-planning lives in its own commit on the next ship.
6. **(plan-critic FOLLOW-UP)** Confidence verdict on "Prompt-driven looping (Claude follows N=3 reliably)" is MEDIUM but the eval is text-grep only — i.e., contract-compliance is CI-untestable until dogfood. By the project's LOW-confidence-as-gate convention this is closer to LOW. The "If it flips" mitigation is sound; just call out "CI-untestable until dogfood" framing in the next plan iteration.
7. **(plan-critic REDIRECT, validated)** Generalize doctor Check 2.5 to scan `template/` files (the BLOCKER above survives because Check 2.5 didn't see template/base/). Pairs naturally with PR G FOLLOW-UP #2 ("generalize Check 2.5 beyond slot count to also check template files"). Promote priority: this PR's BLOCKER is the second incident; tighten the check. Horizon: PR N or H4.
8. **(security FOLLOW-UP)** PR O already covers test-edit reward-hacking hook — no separate routing needed.
9. **(engineer FOLLOW-UP)** Per-attempt log machinery is prose-only — no enforcement that the agent surfaces attempt logs to the user. A session could silently swallow the log and only surface the final BLOCKER. Horizon: first dogfood-time evidence of contract drift.
10. **(engineer FOLLOW-UP)** SIGINT mid-retry is undefined in the contract. Working tree left in indeterminate state; no log line records partial fix. Horizon: real consumer hits this.
11. **(engineer FOLLOW-UP)** Initial-state-revert triggers oscillation abort (defensible but a quiet false-positive). Document as expected limitation. Horizon: first user puzzle-report.
12. **(engineer + auditor FOLLOW-UP)** Manifest description bloat — both descriptions are ~1500 chars after the v1.2.6 sentence. Extract a CHANGELOG.md and reference from descriptions. Horizon: before v1.2.7 ships.

**EXPLORATIONs (added to `dev-docs/roadmap.md` § Exploration if not already there):**

- **Flaky-test failure mode** (push-further, MODERATE signal) — tests that pass 80% / fail 20% produce non-oscillating diff-hashes that exhaust N=3 wastefully. Magentic-style classification rule worth tracking: "if attempt N+1 produces identical diff to HEAD AND preflight passes, treat as flake-clear."
- **Network/disk-full infrastructure failures** (push-further, WEAK signal) — `ECONNREFUSED|ETIMEDOUT|ENOSPC` in stderr could classify as infrastructure failure (abort without consuming retries) instead of fix-attempt.
- **Goose `load` vs `delegate` execution-mode split** (push-further, MODERATE signal) — single thoughtful proposal at Block ([Goose #6202](https://github.com/block/goose/discussions/6202)); track for Anthropic reaction or Goose shipping.
- **Markdown-lint preflight for docs-only PRs** (push-further, WEAK signal) — separate `docsPreflightCmd` slot. No consumer demand yet; preempting violates FB-0003.
- **PR O hook-mechanization fan-out** (push-further, STRONG signal) — same shape applies beyond test-files: `@ts-ignore` / `# type: ignore` insertion, `eslint-disable-next-line` / `# noqa` insertion, deletion of test assertions or `expect()` calls. All detectable as PreToolUse hooks on Edit/Write with regex on `new_string`. Add to PR O scope expansion or PR O.1.
- **Eval fixture mis-categorized under `evals/security/`** (push-further NIT, deferred for design discussion) — `test_preflight_retry.py` is a contract test, not security test. Either rename to `evals/contract/` or update parent runner's directory comment. Deferred because moving the file affects multiple references (run_security_evals.py auto-discovers via glob; renaming requires runner update). Worth doing soon before more contract tests follow the precedent.

---

## PR N — Research-driven orchestration hardening (queued; bumps to v1.2.7)

**Mode:** feature (small-medium) | **Priority: medium**
**Branch:** `pr-h3/research-driven-hardening` (off `main` after PR M merges)
**Goal:** Apply the validated high-leverage findings from `dev-docs/research/agent-orchestration-2026-05.md`. Two-phase scope: documentation grounding (Magentic citation + evaluator-optimizer archetype reference) + structured-result contracts for `/flow:ship`'s skill-to-skill chain (closes PR E+ FOLLOW-UP #1 with field-validated production pattern).

**Why this PR exists:** The comprehensive industry research surfaced two well-evidenced moves: (a) Anthropic's *evaluator-optimizer* archetype is the canonical name for Step 1c's pattern, and Microsoft Magentic's `max_stall_count` is the closest production analog to Flow's diff-hash detector — citing both grounds Flow's design in the field's published taxonomy; (b) the production-validated convention across MindStudio, LangGraph supervisors, Magentic managers, and shanraisshan's best-practice repo is **structured-result contracts on every step** — *"multi-step workflows break at the first unexpected state when there's no shared state object and no per-step success/error field"* ([MindStudio](https://www.mindstudio.ai/blog/what-is-orchestrator-skill-claude-code)). Flow's `/flow:ship` Step 2 currently can't programmatically distinguish ran-clean from skipped from found-issues for security + a11y reviews — PR D shipped `STATUS: SKIPPED` for the early-exit path; the symmetric markers were deferred and now warrant promotion from "v1.3+ enhancement" to current best-practice gap.

**Scope (in):**

*Phase 1 — Documentation grounding:*
- `dev-docs/feedback.md` FB-0012 update: append Magentic `max_stall_count` citation block as independent-convergence evidence.
- `dev-docs/feedback.md` **new FB-0013**: same-model critic+generator collusion as tracked design limitation. Frame honestly: *"Flow already mitigates this structurally (context isolation via extract_session.py, adversarial framing, strict output schemas, held-out eval fixtures, pushback capture). PR P will measure whether the structural mitigations are sufficient via comparative eval before any model swap."* Don't promise the swap — promise the measurement.
- `plugins/flow/docs/workflow.md` Step 4: insert evaluator-optimizer reference after the existing preflight paragraph, citing Building Effective Agents.
- `plugins/flow/skills/ship/SKILL.md` Step 1c preamble: one-line citation block (Anthropic + ADK + Magentic).
- `plugins/flow/skills/ship-spike/SKILL.md` Step 1c preamble: same citation block (consistency).

*Phase 2 — Structured-result contracts (scope: only the skill-to-skill chain in `/flow:ship` Step 2):*
- `plugins/flow/skills/security-review/SKILL.md` final-line output: emit exactly one of three STATUS markers — `STATUS: SKIPPED — <reason>` (already present per PR D), `STATUS: CLEAN — <N> source files reviewed, no findings`, `STATUS: FINDINGS — <n> BLOCKERs, <n> NITs, <n> FOLLOW-UPs`.
- `plugins/flow/skills/accessibility-review/SKILL.md` final-line output: same three-status shape, scoped to UI files.
- `plugins/flow/skills/ship/SKILL.md` Step 2: update post-reviewer consolidation line to parse `STATUS:` markers and emit structured summary. Back-compat: if a reviewer emits no STATUS line, treat as "ran, status unknown" + print a `[WARN]` line (never silent no-op per FB-0006/0007 lineage).
- New eval fixture `plugins/flow/evals/security/test_status_markers.py` paralleling existing fixture shape: text-grep assertions that both reviewer SKILL.md files contain all three STATUS templates.

*Phase 3 — Manifest + history + plan:*
- `.claude-plugin/marketplace.json` + `plugins/flow/.claude-plugin/plugin.json` → v1.2.7. Cumulative description sentence.
- `dev-docs/history.md` SAFETY entry (modifies `ship/SKILL.md`).
- `dev-docs/plan.md` updates.

**Scope (out):**
- Extending STATUS markers to `/flow:staff-review`'s 4 lens agents. Different orchestration shape (`Agent()` not `Skill()`); already has BLOCKER/NIT/FOLLOW-UP structure; modifying 4 lens prompts is broader scope. Track as roadmap candidate; revisit after dogfood signals the gap.
- Extending STATUS markers to `/flow:critique-plan` / `/flow:audit-plan` / `/flow:audit-completion`. Standalone (not chained from another skill); already single-output schema (APPROVED / structured CRITIQUE). No orchestration gap here.
- Test-edit reward-hacking hook (moved to PR O — lower-leverage than Phase 2's contract fix).
- Auditor model-diversity swap (moved to PR P — requires measurement infrastructure first).

**Spec-walk:**

*Phase 1:*
- [ ] FB-0012 has Magentic citation paragraph with link to docs.
- [ ] FB-0013 captures same-model critic collusion with honest framing ("structural mitigations may be sufficient; PR P will measure").
- [ ] `workflow.md` Step 4 names evaluator-optimizer + cites Building Effective Agents.
- [ ] `/flow:ship` Step 1c preamble cites Anthropic + ADK + Magentic.
- [ ] `/flow:ship-spike` Step 1c preamble identical (consistency).

*Phase 2:*
- [ ] `flow:security-review` SKILL.md template includes all three STATUS markers in its documented output shape.
- [ ] `flow:accessibility-review` SKILL.md template includes all three STATUS markers.
- [ ] `/flow:ship` Step 2 parses STATUS lines and emits structured consolidation.
- [ ] `/flow:ship` Step 2 has graceful fallback for missing STATUS line (prints `[WARN]`; never silent).
- [ ] `test_status_markers.py` 4 cases pass (STATUS templates present in both reviewers; fallback message present in ship Step 2; back-compat with PR D's `STATUS: SKIPPED`).
- [ ] `claude plugin validate .` clean.

*Phase 3:*
- [ ] Both manifests at v1.2.7; descriptions name Phase 1 + Phase 2 changes.
- [ ] FB-0010 fan-out check: schema slot count unchanged (still 17); no doc-count drift.
- [ ] `dev-docs/history.md` SAFETY entry.
- [ ] `dev-docs/plan.md` reflects PR N ship state.

**Confidence verdicts:**

**Assumption:** Three STATUS values (SKIPPED / CLEAN / FINDINGS) are sufficient for the two reviewers.
**Confidence:** MEDIUM-HIGH
**Why:** These three cover the documented paths (PR D's early-exit + two substantive outcomes). An ERROR case (reviewer crashes mid-execution) is conceivable but unobserved in dogfood. Don't ship vaporware (FB-0003).
**If it flips:** Add ERROR / INDETERMINATE in a follow-up PR when a real case demands it. Schema change is one-line.

**Assumption:** Citing Magentic + evaluator-optimizer in the contract preamble materially improves consumer trust in Flow's design.
**Confidence:** HIGH
**Why:** Engineering teams routinely scrutinize unattributed design choices; grounding the contract in peer-reviewed (Anthropic) + production-validated (Magentic ships exactly this primitive) lineage answers "why this number / why this rule" without prompting the question.

**Assumption:** Capturing FB-0013 without immediate mitigation is honest documentation, not abdication.
**Confidence:** HIGH
**Why:** Same pattern as FB-0012 — documenting a design limitation before having the fix is consistent with "evidence or silence" discipline. The honest framing ("structural mitigations may be sufficient; PR P will measure") is more truthful than "we will fix this."

**Risks:**
- **Reviewer skills are safety-critical** per `.claude/rules/safety.md`. Phase 2 modifies both review SKILLs + ship SKILL.md. SAFETY marker in commit + history entry mandatory.
- **PR D's existing `STATUS: SKIPPED` shape** must be preserved unchanged for back-compat. Phase 2 EXTENDS, doesn't replace.
- **`/flow:ship` Step 2 parsing** must fail-gracefully on missing STATUS line — print `[WARN]`, never silent (FB-0006/0007 lineage).
- **Manifest description length** grows again. Acceptable cost; future PR could deduplicate via CHANGELOG.md.

**Files touched:**
- `dev-docs/feedback.md` (FB-0012 update + new FB-0013)
- `plugins/flow/docs/workflow.md` (Step 4 evaluator-optimizer reference)
- `plugins/flow/skills/ship/SKILL.md` (Step 1c preamble + Step 2 STATUS parsing)
- `plugins/flow/skills/ship-spike/SKILL.md` (Step 1c preamble)
- `plugins/flow/skills/security-review/SKILL.md` (STATUS markers in output template)
- `plugins/flow/skills/accessibility-review/SKILL.md` (STATUS markers in output template)
- `plugins/flow/evals/security/test_status_markers.py` (new file)
- `.claude-plugin/marketplace.json` + `plugins/flow/.claude-plugin/plugin.json` (v1.2.7)
- `dev-docs/history.md` + `dev-docs/plan.md`

---

## PR O — Test-edit reward-hacking hook (queued; bumps to v1.2.8)

**Mode:** feature (small-medium) | **Priority: medium**
**Branch:** `pr-h4/test-edit-guard` (off `main` after PR N merges)
**Goal:** Mechanize the no-disable-tests reward-hacking guard from `/flow:ship` Step 1c via a PreToolUse hook. Prompt-level guards in the SKILL.md are probabilistic; a hook on `Edit`/`Write` against test-file patterns is the production-validated tool-level interrupt analogous to OpenAI's `needsApproval` and Anthropic hooks' `ask` decision.

**Why this PR exists:** PR M shipped prompt-level reward-hacking guards in Step 1c (*"do not modify or disable tests... do not add `@ts-ignore`/`# noqa`/`eslint-disable-next-line`"*). These rely on Claude's semantic compliance with the contract. The field's stronger pattern is mechanical interrupts at the tool-call layer — emit `ask` when Claude tries to edit a test file during preflight retry, requiring user confirmation. Lower-leverage than PR N's structured-result contracts (the orchestration gap is more widely-cited in the field) but still real value for the test-disabling specific failure mode.

**Scope (in):**
- New `flow.config.json.testFilePatterns` slot in schema (mirrors `sourceFilePatterns` / `uiFilePatterns` shape). Defaults cover common test naming: `**/*test*.{ts,tsx,js,jsx,py,rs,go,rb}`, `**/__tests__/**`, `**/*_test.go`, `**/test_*.py`, `**/*.test.{ts,tsx,js,jsx}`, `**/*.spec.{ts,tsx,js,jsx}`. Invalid-regex fallback emits loud warning (caught via grep -E exit-2 detection).
- New entry in `plugins/flow/hooks/default-hooks.json`: PreToolUse hook matching `Edit` and `Write` tool calls against test-file glob; emits `ask` decision with prompt: *"This edit modifies a test file. If you're fixing a code bug, switch to fixing the code instead. If you're fixing a genuine test bug, confirm with reason."*
- Hook is **opt-in** per the documented `default-hooks.json` baseline convention; consumers who don't want it leave it disabled.
- Schema grows 17 → 18 slots. FB-0010 fan-out sweep: README ×2, doctor SKILL.md, plugin.json + marketplace.json descriptions.
- New eval fixture `plugins/flow/evals/security/test_test_edit_guard.py`. Cases: (a) hook config validates against the hooks schema; (b) test-file pattern match logic correct on common naming conventions; (c) non-test-file edits not flagged; (d) malicious `testFilePatterns` regex doesn't execute (parallels `test_malicious_config.py`).
- New FB entry capturing the rule: *"reward-hacking guards in prompt contracts must be paired with mechanical interrupts where the tool surface allows; PreToolUse hook on test-file edits is the canonical pattern for the no-disable-tests rule."*
- Manifest bump v1.2.7 → v1.2.8 + cumulative description sentence.

**Scope (out):**
- Generalizing the hook to other reward-hacking patterns (`@ts-ignore` additions, `eslint-disable-next-line` insertions). These are content-pattern checks not file-path checks — different hook shape, defer until PR O dogfood shows test-file guard alone is insufficient.
- Making the hook always-on (not opt-in). Consumer choice via `default-hooks.json` is the established pattern.
- Scoping the hook to "only during Step 1c" — hooks fire on every tool call, not scoped to specific skill steps. The hook applies to all `Edit`/`Write` on test files; consumers can disable if friction outweighs benefit.

**Confidence verdicts:**

**Assumption:** The default `testFilePatterns` covers the majority of real-world test layouts without false positives during regular development.
**Confidence:** MEDIUM
**Why:** Defaults cover ~95% of TypeScript / Python / Rust / Go / Ruby test conventions. Edge cases exist (integration tests outside `__tests__/`, custom naming, monorepos with non-standard layouts). Slot lets consumers override; `ask` decision (not `deny`) lets the user dismiss false-positives.
**If it flips:** False positives cause friction during dev. Mitigation: hook is opt-in; consumers can disable in `default-hooks.json`. Worst case: dogfood proves the defaults wrong and we tune them.

**Assumption:** `ask` decision (user confirms) is the right gate strength, not `deny` (block outright).
**Confidence:** HIGH
**Why:** Genuine test bugs exist; blocking outright would create more friction than reward hacking it prevents. `ask` is the Magentic plan-signoff intuition — human in the loop only when it matters.

**Files touched:**
- `plugins/flow/schema/flow.config.schema.json` (new `testFilePatterns` slot)
- `plugins/flow/hooks/default-hooks.json` (new PreToolUse hook)
- `plugins/flow/evals/security/test_test_edit_guard.py` (new file)
- Live "17 slots" → "18 slots" updates (FB-0010 sweep)
- `.claude-plugin/marketplace.json` + `plugins/flow/.claude-plugin/plugin.json` (v1.2.8)
- `dev-docs/feedback.md` (new FB entry on hook-mechanization pattern)
- `dev-docs/history.md` (SAFETY entry — modifies hook surface)
- `dev-docs/plan.md`

---

## PR P — Auditor model-diversity evaluation (queued; bumps to v1.2.9 or v1.3.0 depending on outcome)

**Mode:** feature (medium — eval infrastructure + possible swap) | **Priority: low-medium**
**Branch:** `pr-h5/auditor-model-eval` (off `main` after PR O merges)
**Goal:** Address FB-0013 (same-model critic collusion) via a **measurement-first** approach. Build comparative eval infrastructure to measure whether downgrading the `auditor` from Opus to Sonnet preserves finding quality. Ship the model swap ONLY IF the eval clears a quantitative bar; otherwise close FB-0013 as "structural mitigations sufficient; model diversity not warranted."

**Why this PR exists:** The skill-chaining research surfaced critic-generator collusion as a documented failure mode in same-model setups. Flow's structural mitigations (context isolation via `extract_session.py`, adversarial framing in `auditor.md`, strict output schemas, held-out eval fixtures, pushback capture via `log-disagreement`) likely address most of the risk — but this is a hypothesis, not a measurement. Running the auditor on Sonnet vs Opus against the same fixture set will give us data. Opus is materially better at subjective judgment and creative synthesis; routing critique-heavy roles to Sonnet sacrifices real capability. The swap is defensible only if data shows comparable finding quality.

**Two-step structure:**

*Step A — Build comparative eval infrastructure:*
- Extend `plugins/flow/evals/run_evals.py` (or new `evals/run_model_comparison.py`) to invoke auditor against each `evals/fixtures/*.jsonl` once with `model: opus` and once with `model: sonnet`. Capture findings for each.
- Compute overlap metrics: finding-count delta, false-positive rate (compare to `ground_truth.yaml`), finding relevance overlap.
- Document the **≥80% finding-overlap with comparable FP rate** bar as the swap gate.

*Step B — Decide based on data:*
- Run the comparison on all fixtures.
- **If Sonnet clears the bar:** swap auditor to `model: sonnet` in `plugins/flow/agents/auditor.md` frontmatter. Update FB-0013 to "structural + diversity mitigation in place." Bump to v1.3.0 (model swap is a behavior change worth signaling).
- **If Sonnet doesn't clear the bar:** keep auditor on Opus. Update FB-0013 to "structural mitigations sufficient; model diversity not warranted per measured FP/overlap." Bump to v1.2.9 (eval infrastructure only).

**Scope (in):**
- Comparative eval infrastructure (the model-comparison runner). This is the load-bearing deliverable regardless of swap decision.
- Sonnet-vs-Opus run on `auditor` against the existing 5 fixtures + the eval's ground_truth.yaml.
- Decision documented in FB-0013 update + `dev-docs/history.md`.
- If swap: only `auditor` model frontmatter changes. NOT `plan-critic`, lens agents, or any other role — Tier 1 only.

**Scope (out):**
- **Tier 2/3 model swaps** (plan-critic, lens agents). These require their own eval pass with the same ≥80% bar before any swap. Track as roadmap candidates; do not bundle.
- **Cross-vendor diversity** (Claude + non-Anthropic model). Out of scope for a Claude Code plugin.
- **Dynamic model routing** (different model per call based on complexity heuristics). Premature optimization; ship static-frontmatter swap first if at all.
- **Removing FB-0013 from feedback.md.** Even if swap ships, the FB entry stays — it captures the design limitation and the evidence-based mitigation that addressed it.

**Confidence verdicts:**

**Assumption:** Comparative eval infrastructure is the right shape (run auditor twice, compare findings, score against ground truth).
**Confidence:** HIGH
**Why:** Matches the existing eval harness shape; reuses fixture machinery; standard A/B testing pattern.

**Assumption:** ≥80% finding-overlap + comparable FP rate is the right swap gate.
**Confidence:** MEDIUM
**Why:** 80% is a defensible threshold (substantial agreement, not perfection) but specific number is somewhat arbitrary. If Sonnet hits 75% on 5 fixtures, the call is harder. Document the threshold; revisit if dogfood signals it's wrong.
**If it flips:** Adjust threshold based on what the data shows. Threshold choice is itself a tradeoff — stricter bar means fewer swaps + more capability preservation; looser bar means more cost savings + more diversity.

**Assumption:** The 5 existing fixtures cover the range of auditor scenarios well enough to make a swap decision.
**Confidence:** MEDIUM
**Why:** 5 fixtures is small. The decision should note this — *"swap decision based on 5 fixtures; revisit if Sonnet auditor produces user-reported regressions in dogfood."*

**Risks:**
- **Confirmation bias in eval design.** Designing the eval to favor an expected outcome. Mitigation: define the threshold + comparison metrics BEFORE running the comparison; document them in PR plan; user reviews before swap is committed.
- **Sonnet might miss nuanced findings that don't surface in current fixtures.** Real risk — the fixtures were authored against Opus's finding patterns. A new fixture authored specifically to stress-test the auditor on Sonnet-known-weakness patterns (subtle evidence-chain reasoning) would strengthen the eval. Consider adding one as part of Step A.
- **Model alias resolution.** `model: sonnet` in the sub-agent frontmatter resolves to whatever Sonnet is current at invocation time. This is good for forward-compat but means the eval data ages — a future Sonnet might behave differently. Acceptable: the eval can be re-run when concerned.

**Files touched (Step A — always):**
- `plugins/flow/evals/run_model_comparison.py` OR extension to `run_evals.py` (new comparative runner)
- New fixture targeting subtle reasoning (optional but recommended)
- `dev-docs/feedback.md` FB-0013 update with measurement methodology
- `dev-docs/history.md` (data-driven decision entry)
- `.claude-plugin/marketplace.json` + `plugins/flow/.claude-plugin/plugin.json` (v1.2.9 if no swap, v1.3.0 if swap)

**Files touched (Step B — only if swap ships):**
- `plugins/flow/agents/auditor.md` (add `model: sonnet` frontmatter)

---

## PR R — `/flow:init` skill (planning; queued; provisional letter)

**Mode:** feature (medium)
**Priority:** TBD pending ship-vs-defer decision. Originally noted in [`README.md`](../README.md) "Known limitations" as `/flow:init` deferred to bootstrap.sh + manual placeholder fill; line 891 of this file ("`/flow:init` auto-bootstrap skill — v2.0+ per post-extraction roadmap") confirms intentional deferral. **Question on the table:** advance now or hold the v2.0+ schedule. Plan is fully scoped so the call is informed.
**Source:** 2026-05-27 → 2026-05-28 conversation in worktree `thirsty-napier-5a3ff4`. User direction: "it should identify what's missing, what exists but may need to be adapted/optimized for flow, and propose additions. existing documentation/files should never be deleted - any changes need to be explicitly approved by the human." Planning thread ran plan-critic 5 passes (11 substantive findings + 5 edit-discipline findings, all resolved before this section was written). FB claim: **FB-0014** (reserved in `dev-docs/reserved-feedback-numbers.md`).
**Letter note:** "R" chosen to clear past lucid-matsumoto's pending re-letter (likely Q) and sweet-hellman's queued N/O/P. Finalize at ship time; if queue clears differently, renumber at rebase via the FB-0010 grep-first-edit-second discipline.

**Goal:** Provide a single skill that lets any project adopt flow in one in-session command. The skill (1) detects repo state, (2) inventories what's missing vs what exists-but-needs-adapting, (3) proposes a complete additive change set, and (4) applies only the items the user explicitly approves. **No file is ever deleted; no file is ever overwritten without explicit per-file approval.**

**Scope (in):**

Three-phase skill structure, gated by approval:

- **Phase A — INVENTORY (read-only).** Delegate detection to `/flow:doctor`'s check matrix (single source of truth; init does not duplicate the 17-slot logic — note: now 17 slots per v1.2.6, not 16 as planning thread assumed). Add repo-classification checks doctor doesn't: stack signal (`package.json` web vs `src-tauri/` tauri-rust-ts; `Cargo.toml`-only flagged unsupported; `*.xcodeproj`/`Package.swift` swift; ambiguous → ask), docs convention (`core-docs/` vs `dev-docs/` vs `docs/` vs none — propose `core-docs/` for new, preserve existing), prior `.claude/` content (CLAUDE.md exists? `.claude/rules/safety.md` exists? local `/staff-review` or other workflow skill conflicts with `/flow:*`?). Classify the repo into one of four states: FRESH / PARTIAL-FLOW / EXISTING-OWN-WORKFLOW / ALREADY-READY. Print inventory table with `[MISSING]` / `[PRESENT]` / `[PRESENT — adapt-candidate]` / `[CONFLICT — local skill X overlaps /flow:Y]`.
- **Phase B — PROPOSAL (writes nothing).** For each `[MISSING]`: show file path + first ~15 lines + source template path. For each `[adapt-candidate]`: show unified diff of the proposed additive section (e.g., appending a "Workflow" section to existing CLAUDE.md; appending paths to existing safety.md frontmatter). **Never a rewrite — only additive Edit-tool sections.** For each `[CONFLICT]`: emit warning, no proposed change. For each placeholder slot: print inferred value + source. Present proposal as a numbered list; user approves with `apply all` / `apply 1,3,5` / `apply 1-7` / `skip 4` / `cancel`. Ambiguous input re-prompts rather than guessing.
- **Phase C — EXECUTE (only approved items).** Every write uses `cp -n` semantics OR additive Edit; refuses to overwrite. After writes: run `/flow:doctor`, print its output, emit final-line verdict `[INIT COMPLETE]` / `[INIT COMPLETE — N items declined; re-run /flow:init or fix manually]` / `[INIT INCOMPLETE — see doctor output]`.

Prerequisite work (Phase 1 of execution, if it ships):

- **Move `template/` → `plugins/flow/template/`** so templates ship inside the user-scope plugin install (`/flow:init` reads from `${CLAUDE_PLUGIN_ROOT}/template/...` without requiring a local checkout). `git mv` preserves history. Update path references in: (a) `plugins/flow/template/base/bootstrap.sh` itself — implement **smart-fallback** so `$FLOW_DIR/template/base/` is tried first then `$FLOW_DIR/plugins/flow/template/base/`, preserving the documented `--flow-dir = path to a local flow checkout` CLI semantic; (b) `plugins/flow/skills/doctor/SKILL.md` — replace **5 hardcoded `template/base/` references at lines 113, 114, 168, 250, 251** (verified 2026-05-28 against post-PR-M HEAD via `grep -n 'template/base' plugins/flow/skills/doctor/SKILL.md`; original planning thread cited 113/114/168/183/184 against a stale base before PRs A-M shipped) with `${CLAUDE_PLUGIN_ROOT}/template/base/...` or with `/flow:init` invocation hint; (c) `README.md`; (d) `docs/bootstrap.md`; (e) `docs/migration.md`. Clean break at old root path (no deprecation stub).

Init consumes `/flow:doctor`'s text output via two regex layers: (a) status lines `^\[(PASS|FAIL|WARN|SKIP)\] <label>` — all four statuses including `SKIP`, which doctor emits when a check's prerequisites haven't passed; (b) continuation lines `^( {2,})(\S.*)$` with `Fix:` as a recognized sub-shape but not the only shape (doctor emits multi-line hints like `Fix: brew install gh` + `Then: gh auth login`). Plus final-line verdict (`[READY]` / `[READY with WARN-level items]` / `[NOT READY]`). Status mapping: `PASS` → not in inventory; `FAIL` → `[MISSING]`; `WARN` → `[PRESENT — adapt-candidate]`; `SKIP` → `[DEFERRED]`. New eval fixture at `plugins/flow/evals/fixtures/doctor-format-stability/` asserts doctor's output line shape is stable across all 4 statuses + multi-line continuation. **No `--json` flag on doctor** — cross-skill scope expansion outside the user envelope, per planning-thread plan-critic ISSUE 1 resolution.

Documentation + version updates (if it ships):

- `plugins/flow/.claude-plugin/plugin.json` + `.claude-plugin/marketplace.json`: bump to next available version (likely v1.3.0 if it lands as the v1.3 milestone, or a v1.2.x patch if absorbed earlier).
- `README.md`: remove `/flow:init` from "Known limitations"; promote to "Quick start" front door.
- `plugins/flow/docs/workflow.md`: add `/flow:init` to onboarding surface.
- `docs/bootstrap.md`: restructure to show `/flow:init` first, `bootstrap.sh` as appendix.
- `docs/migration.md`: Stage 1 references `/flow:init` (handles "install non-breaking" with merge prompts).
- `dev-docs/feedback.md`: add FB-0014 ("Init skill must default to additive + per-item human approval; never overwrite or delete existing files").
- `plugins/flow/evals/init_unit/`: Python unit tests for `init_helpers.py` (matches `evals/security/test_cwd_constraint.py` subprocess-invocation pattern, NOT import-based — corrected during planning).

**Scope (out):**

- Auto-applying without approval. Even for FRESH repos with no conflicts, init always presents the proposal and waits.
- Modifying or removing local workflow skills. Init flags conflicts; never resolves them. `docs/migration.md` Stage 2 is the user's call.
- Auto-installing the plugin. Init assumes `/plugin marketplace add` + `/plugin install` already ran; if doctor's Section 1 fails, init exits early with a fix-it hint.
- Cross-repo concerns. Init operates on `pwd`; doesn't touch `~/.claude/settings.json` or other repos.
- A `/flow:doctor --json` flag (left as a separate decision; can be filed as a follow-up if text parsing proves brittle in dogfood).

**Spec-walk:**

- [ ] `plugins/flow/skills/init/SKILL.md` exists with three phases (INVENTORY / PROPOSAL / EXECUTE) clearly delimited.
- [ ] Init delegates to `/flow:doctor` for the check matrix; no duplicated check logic.
- [ ] Init parses doctor's text via documented contract: status `^\[(PASS|FAIL|WARN|SKIP)\] <label>` + general indented continuation; SKIP maps to `[DEFERRED]` in inventory.
- [ ] Eval fixture at `plugins/flow/evals/fixtures/doctor-format-stability/` asserts doctor's output format stability across all 4 statuses + multi-line continuation.
- [ ] Repo classification yields exactly one of FRESH / PARTIAL-FLOW / EXISTING-OWN-WORKFLOW / ALREADY-READY.
- [ ] PARTIAL-FLOW vs EXISTING-OWN-WORKFLOW disambiguator documented in init/SKILL.md: presence of `flow.config.json` → PARTIAL-FLOW; project-local `.claude/skills/` without it → EXISTING-OWN-WORKFLOW; ambiguous → user-redirect.
- [ ] Phase B output ends with the literal approval prompt; Phase C writes nothing until approval received.
- [ ] Every write is gated by approval AND a precondition check (file doesn't exist, or change is additive via Edit not rewrite).
- [ ] init/SKILL.md includes a table-form approval grammar spec covering: empty input, single number, comma-list, range, `apply all`, `skip <list>`, mixed apply+skip, out-of-range, negative/zero, duplicates, reversed ranges, open-ended ranges, whitespace tolerance, `cancel`.
- [ ] `template/` moved to `plugins/flow/template/`; root deleted; bootstrap.sh smart-fallback implemented; doctor SKILL.md 5 references at lines 113/114/168/250/251 updated; 3 root docs updated; grep gate clean.
- [ ] Eval fixtures for 4 repo states under `plugins/flow/evals/init_unit/fixtures/{fresh,partial-flow,existing-own-workflow,already-ready}/` with checksum-before/after asserts proving no deletes + no overwrites.
- [ ] FB-0014 added to `dev-docs/feedback.md` synthesizing the "additive + per-item approval, never destructive" rule; reservation removed from `reserved-feedback-numbers.md` during /flow:ship synthesis step.
- [ ] `claude plugin validate .` clean.
- [ ] README "Known limitations" no longer lists `/flow:init`; v2.0+ Backlog entry at plan.md:891 removed since it ships earlier than originally roadmapped.

**Spec-walk additions: health-tracker dogfood inputs (2026-05-28).** Signals derived from health-tracker's flow setup handoff. Health-tracker is a native iOS / SwiftUI app with XcodeGen-managed project + non-default doc convention; it adopted flow without renaming its existing docs. Initially added 6 items from the handoff; **audited 2026-05-28 against the live schema** (`plugins/flow/schema/flow.config.schema.json`) and against the "generalizable + valuable at this stage" bar — 3 kept, 1 simplified, 1 dropped, 1 reshaped. Audit notes inline below each item.

- [ ] **Swift stack detection signals extended.** `init_helpers.py` classifier recognizes `project.yml` (XcodeGen) and `Project.swift` (Tuist) in addition to `*.xcodeproj` + `Package.swift` as swift-stack indicators. Rationale: XcodeGen projects gitignore `.xcodeproj` and treat `project.yml` as source-of-truth; missing this signal would misclassify XcodeGen + Tuist projects (both industry-standard iOS tooling). **Audit verdict: KEEP** — structural fact, near-zero cost.
- [ ] **`uiSurface: false` default for swift stack.** When stack is detected as swift (any of the 4 signals above), the inferred-slot proposal for `uiSurface` is `false`, not `true`. Documented rationale in the proposal: schema default is `true` (verified 2026-05-28 against `plugins/flow/schema/flow.config.schema.json`), so without this override every swift consumer hits noisy `/flow:accessibility-review` early-exits — flow's HTML/ARIA heuristics don't apply to SwiftUI/UIKit. (Future v1.3+: a SwiftUI-aware a11y review skill would flip this default; not in PR R scope.) **Audit verdict: KEEP** — schema-confirmed value; cost-of-no-override is real.
- [ ] **Slot-mapping for existing docs (additive principle for slot configuration).** When init's Phase A detects existing docs at non-default paths (e.g., `HISTORY.md` at repo root, `<project>-spec.md` at root, `docs/roadmap.md`, `design-language.md` at root), Phase B proposes mapping `flow.config.json` slots to those existing paths rather than creating new files under `core-docs/`. This is the additive-only principle applied to slot configuration — not just file content. Without it, init would create duplicate-purpose files at default paths while existing docs remain orphaned (the case health-tracker would have hit). Proposal output example: "I see `HISTORY.md` at root; propose `historyPath: HISTORY.md` instead of creating `core-docs/history.md`. Approve or skip." **Audit verdict: KEEP** — structural correctness; closes a real "never destructive" gap at the slot layer.
- [ ] **Existing `.claude/rules/safety.md` preserved.** Any existing `safety.md` is classified as `[PRESENT]`; init never proposes replacing it. If user wants flow's standard safety conventions appended, that happens via the general additive-Edit rule that already governs all adapt-candidate edits — no separate detection logic needed. **Audit verdict: SIMPLIFIED** from the originally-drafted "[PRESENT — adapt-candidate] with template-marker detection" — that mechanical detection was over-specified for N=1 evidence; the simpler "exists → leave alone unless user explicitly asks for additions" rule covers the same intent.
- [ ] ~~**`branchPrefix` slot inferred from git branch list.**~~ **DROPPED.** Original draft proposed inferring `branchPrefix` from a `git branch --list` prefix-pattern scan. Schema verification (2026-05-28) showed the slot's default is `""` (opt-in by design — `flow doesn't add a prefix unless this is set`); cost of leaving unset is zero behavior change. Inferring it is overengineering for marginal value. If a real consumer reports friction, file as a separate FB.
- [ ] **Composed `preflightCmd` for source-of-truth-file stacks only.** When Phase A detects a source-of-truth project file (`project.yml` for XcodeGen; `Project.swift` for Tuist), Phase B proposes a composed `preflightCmd` with the appropriate pre-build step: `xcodegen generate && xcodebuild -scheme <X> -destination <Y> test` or `tuist generate && xcodebuild ...`. For all other stacks (including plain SPM swift, web, tauri-rust-ts), follow the schema's documented `examples` field (single-command or stack-native multi-step like `npm run typecheck && npm run lint && npm test -- --bail`) rather than inventing composed forms. **Audit verdict: RESHAPED** from the originally-drafted "composed multi-step for all stacks" — that overgeneralized from N=1 (XcodeGen needs the composed form; SPM-only swift doesn't); narrowed to only those stacks where source-of-truth file presence makes the pre-build step load-bearing.

**Confidence verdicts:** (Carried verbatim from 5-pass critic-resolved planning thread; line numbers updated to reflect post-PR-M doctor SKILL.md.)

**Assumption:** `/flow:doctor`'s existing text output is regular enough that init can parse it reliably via line-shape regex, given an eval fixture that locks the format.
**Confidence:** HIGH
**Why:** Doctor emits ~17 checks plus a final verdict line, all in a consistent `[STATUS] label` + optional indented continuation shape. The eval fixture asserting format stability is load-bearing — any future doctor edit that changes line shape fails the test and forces coordinated update.
**If it flips:** doctor's format proves brittle in init dogfood. File `/flow:doctor --json` as separate user-approved follow-up PR.

**Assumption:** "Additive only" via Edit tool suffices for all adapt-candidate cases.
**Confidence:** HIGH
**Why:** Realistic adapts (append Workflow section to CLAUDE.md; append paths to safety.md frontmatter; append lines to .gitignore) don't require destructive edits.
**If it flips:** Specific case becomes `[CONFLICT]`; surfaced with manual-merge instructions.

**Assumption:** Explicit disambiguator (`flow.config.json` presence → PARTIAL-FLOW; project-local `.claude/skills/` without it → EXISTING-OWN-WORKFLOW) is sufficient for binary-signal cases; ambiguous cases escalate to user-redirect.
**Confidence:** HIGH for disambiguated; MEDIUM for ambiguous edge cases (caught at Present-step per workflow.md MEDIUM contract).
**Why:** `flow.config.json` presence is binary. Edge cases get explicit user resolution, not silent heuristic guess.

**Assumption:** Stack auto-detection from `package.json` / `Cargo.toml` / `*.xcodeproj` covers common cases.
**Confidence:** HIGH
**Why:** Three supported stacks each have unique fingerprints. Multi-stack monorepos → ask user.

**Risks:**

- `template/` move + path updates touch ~10 files. Mitigation: single atomic Phase 1 commit; grep gates; `claude plugin validate .` clean before proceeding.
- Init couples with `/flow:doctor`'s text format. Mitigation: format-stability eval fixture.
- Approval-batching UX is tricky. Mitigation: numbered proposals; `apply` trigger word forces deliberateness; ambiguous input re-prompts.
- **NEW risk caught during 2026-05-28 rebase:** Plan content was authored against base before PRs A-M shipped. Foundational assumptions (slot count, line numbers, current "letter availability") all required correction at the rebase. Mitigation already applied (line numbers fixed to 250/251; slot count noted as 17 not 16; letter R chosen past current claims). Any further rebase before execution must repeat this verification.
- **NEW risk:** Section 4 of doctor SKILL.md may have additional `template/base/` references the grep didn't catch (Section 4 was added during PRs A-M and wasn't in the original planning sample). Mitigation: re-grep at Phase 1 execution.

**Phased execution (each phase = one commit unless trivially small):**

- **Phase 1 — Prerequisite: `template/` move (clean break).** `git mv template/ plugins/flow/template/` + path updates in 5 files: bootstrap.sh (smart-fallback), doctor SKILL.md (5 references at 113/114/168/250/251, **verify exhaustive via grep before edit** per FB-0010 discipline), README.md, docs/bootstrap.md, docs/migration.md. Single commit.
- **Phase 2 — `SKILL.md` Phase A (INVENTORY) + Python helpers.** Write `plugins/flow/skills/init/SKILL.md` Phase A body + `plugins/flow/scripts/init_helpers.py` (library + thin argparse CLI). Smoke against FRESH and ALREADY-READY repo states.
- **Phase 3 — Phase B (PROPOSAL) + approval-parse logic + grammar table.** Smoke `apply all` / `apply 1,3,5` / `skip 4` / `cancel` + edge cases per grammar table.
- **Phase 4 — Phase C (EXECUTE) with no-overwrite enforcement.** Smoke against EXISTING-OWN-WORKFLOW state; assert no existing file modified outside approved additive edits.
- **Phase 5 — Eval fixtures + Python unit tests.** `plugins/flow/evals/init_unit/test_init_helpers.py` invokes `init_helpers.py` via `subprocess.run` (matches existing security-test pattern). Fixtures under `plugins/flow/evals/init_unit/fixtures/{fresh,partial-flow,existing-own-workflow,already-ready}/`. Plus `plugins/flow/evals/fixtures/doctor-format-stability/` regression fixture.
- **Phase 6 — Docs + manifest bump.** README, bootstrap.md, migration.md, workflow.md updated to lead with `/flow:init`. Version bump per current cycle.
- **Phase 7 — Dogfood via `/flow:staff-review` + `/flow:security-review`** on PR's own diff. 4 parallel lenses canonical pattern.
- **Phase 7.5 — Present MEDIUM-confidence verdicts to user** (per workflow.md MEDIUM contract). Specifically the EXISTING-OWN-WORKFLOW heuristic edge cases.
- **Phase 8 — `/flow:ship` + open PR.** PR body documents Phase 7.5 resolutions.

**Files touched (anticipated):**

- New: `plugins/flow/skills/init/SKILL.md`
- New: `plugins/flow/scripts/init_helpers.py` — Python helpers with library + argparse CLI (matches `extract_session.py` shape)
- Moved: `template/` → `plugins/flow/template/` (~10 files via `git mv`); root deleted
- Modified post-move: `plugins/flow/template/base/bootstrap.sh` (smart-fallback `--flow-dir`), `plugins/flow/skills/doctor/SKILL.md` (5 hardcoded `template/base/` references at lines 113/114/168/250/251 — verified post-PR-M HEAD), `README.md`, `docs/bootstrap.md`, `docs/migration.md`
- Modified: `plugins/flow/.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json` (version bump TBD by ship cycle)
- Modified: `plugins/flow/docs/workflow.md` (add `/flow:init` to onboarding)
- Modified: `dev-docs/{plan,history,feedback}.md` (synthesis at ship time)
- Modified: `dev-docs/reserved-feedback-numbers.md` (remove FB-0014 reservation at ship time per protocol)
- Modified: `README.md` (remove from Known Limitations; promote to Quick start)
- New: `plugins/flow/evals/init_unit/test_init_helpers.py`
- New: `plugins/flow/evals/init_unit/fixtures/{fresh,partial-flow,existing-own-workflow,already-ready}/`
- New: `plugins/flow/evals/fixtures/doctor-format-stability/`

---

## PR U — Ship-time gate semantics: resolution-confidence + draft-routing + verify-build placement (implements umbrella Facets 2 + 3 + 5)

**STATUS (2026-06-03): MERGED — PR #31 (v1.5.0, squash `ef75472`).** Staff-review clean (0 BLOCKERs, two passes); security-review trivially-safe; a11y + verify-build self-skipped (uiSurface:false / platform:library). Rebased onto v1.4.2 + de-stacked; Facet 5 (reviewer/ship-spike auto-invocability) absorbed from the old "Track A". FB-0034 + FB-0035 + FB-0036 written + reservations cleared. Realizes umbrella Facets 2 + 3 + 5.

**Mode:** feature (medium–large) | **Priority:** high | **Horizon:** v1.5.0 | **SAFETY** (ship pipeline + reviewer prompts)
**Source:** managed-autonomy umbrella Facets 2 + 3 + 5 (critique-clean 2026-05-30). Shipped as one PR because they share `ship/SKILL.md` + the PR S predicate reconciliation, and Facet 5 (auto-invocability) was absorbed at rebase. FB written: **FB-0034** (Facet 2, resolution-confidence/draft-routing) + **FB-0035** (Facet 3, verify-build placement) + **FB-0036** (Facet 5, reviewer/ship-spike model-invocable).
**Branch (at execution):** new branch off `main` (currently stacked on `claude/infallible-mclaren-c2bd23`'s committed work; rebase onto `main` before execution).

**Goal:** Make every ship-time gate finding resolve to exactly one of {auto-fix in-tree, draft-PR + manifest} — never a silent proceed, never a hard mid-loop halt — and move verify-build's *discovery* role to the readiness boundary so ship only *confirms*. Net effect: the loop reaches a PR autonomously, and "not ready" is always mechanically visible (draft status) at the merge gate.

**Scope (in):**

*Facet 2 — resolution-confidence + draft routing:*
- **Resolution-confidence axis** added to `security-review` + `accessibility-review` output contracts: each BLOCKER tagged `auto-fixable` (single clear fix, mechanically verifiable) or `decision-required` (multiple valid fixes / out-of-repo action / un-auto-fixable like dep-reputation). Default-to-`decision-required` when unsure (FB-0011 ESCALATE-by-default).
- **`ship/SKILL.md` routing:** auto-fixable → fix in-tree + continue (today's path). decision-required (from any of the three reviewers) → do not best-effort; collect into a draft manifest.
- **Draft-PR + manifest:** when any unresolved decision-required finding exists at PR-open time, `gh pr create --draft` with a `🚫 NOT READY TO MERGE` block pinned at the top of the body — per-blocker: what's unresolved, what it needs (secret rotation / design decision / dep vetting), candidate resolutions. (Absorbs PR Q FOLLOW-UP #18 — BLOCKED-state visibility.)

*Facet 3 — verify-build placement:*
- **`workflow.md`:** verify-build *discovery* loop documented at the Present/Iterate boundary (steps 8–9); ship Step 2 verify-build reframed as a **confirmation re-run** (regression check), not discovery. Visual sign-off folds into the merge gate (agent dials in pre-PR vs plan criteria; human verifies via PR preview).
- **`ship/SKILL.md` Step 2:** verify-build = confirmation. On FAIL/Unknown after a readiness PASS = regression → FB-0012 bounded mechanical fix; if unresolvable → draft routing (NOT hard-halt). 

*Shared — PR S predicate reconciliation (the critique BLOCKER fix):*
- Auto-advance-INTO-ship (PR S predicate) **unchanged**: still requires readiness verify-build `PASS`. Only ship-internal handling changes (hard-halt → draft). Edit the PR S predicate wording in `ship/SKILL.md` + `workflow.md` Step 8 to state this explicitly so the two don't read as contradictory. Assert the invariant: **no merge-ready PR is producible on a non-PASS build.**

**Scope (out):**
- Facets 1 + 4 of the umbrella (separate PRs; Facet 5 is included here, absorbed at rebase).
- The "did source change since readiness verify → skip rebuild" optimization slot — **candidate, deferred** to a follow-up unless it's trivial; note it, don't build it here.
- New `flow.config.json` slots beyond what's strictly required (avoid schema churn; if the skip-rebuild slot lands, it's one additive slot).
- Auto-fixing decision-required findings (by definition out of scope — they route to draft).
- `uiSurface`-no-preview-skill screenshot fallback (noted as open sub-item in Facet 3; separate small follow-up).

**Spec-walk:**
- [ ] `security-review` + `accessibility-review` SKILL.md output contracts add the `auto-fixable | decision-required` tag on BLOCKERs, default-to-decision-required. (verify: read both contracts + a fixture)
- [ ] `ship/SKILL.md` routes decision-required findings (from all 3 reviewers) to a draft manifest; auto-fixable still fixed in-tree. (verify: read Step 2–7 flow)
- [ ] Draft-PR path: `gh pr create --draft` + pinned `🚫 NOT READY TO MERGE` manifest with per-blocker need + candidate resolutions. (verify: read Step 7 + a fixture PR body)
- [ ] verify-build reframed: discovery at steps 8–9 in `workflow.md`; ship Step 2 = confirmation re-run; regression → bounded-fix-or-draft. (verify: read workflow.md + ship Step 2)
- [ ] PR S predicate reconciliation explicit in `ship/SKILL.md` + `workflow.md` Step 8: auto-advance still requires readiness PASS; invariant "no merge-ready PR on a non-PASS build" stated. (verify: read predicate + grep for contradiction)
- [ ] FB-0010 fan-out sweep: every place that says verify-build "hard-stops"/"halts ship" updated to the confirmation+draft model (grep `hard-stop|halt|exit_code: 1|STOP`). (verify: git grep)
- [ ] Eval fixture(s): a decision-required finding produces a draft PR + manifest; an auto-fixable finding does not; a ship-internal verify-build regression after readiness PASS routes to draft not hard-halt.
- [ ] `claude plugin validate .` clean; version bump v1.4.x → v1.5.0 (marketplace.json ×2 + plugin.json).
- [ ] `/flow:staff-review` (4 lenses) on the diff; `/flow:ship`.

**Confidence verdicts:**
- **Assumption:** the draft-PR-manifest model is strictly safer than the current hard-halt (no merge-ready PR on a non-PASS build; human sees structured state at merge). **Confidence:** HIGH. **Why:** draft status is mechanical + the merge gate is unchanged. **If it flips:** if drafts are routinely ignored/merged-anyway in practice, add a CI check that blocks merge while the manifest block is present (follow-up).
- **Assumption:** reviewers can reliably self-tag auto-fixable vs decision-required. **Confidence:** MEDIUM. **Why:** it's a judgment the reviewer LLM makes; mis-tagging auto-fixable→decision-required just over-escalates (safe), but decision-required→auto-fixable could best-effort a fix that shouldn't be auto-made. **If it flips:** default-to-decision-required + require an explicit mechanical-verification step before any auto-fix is trusted; eval fixture pins the boundary.

**Risks:**
- **SAFETY ship-contract change touching 4 deployed skills.** Mitigation: per-PR `/flow:critique-plan` (this), `/flow:staff-review`, eval fixtures before merge; SAFETY markers.
- **FB-0010 fan-out** (verify-build "hard-stop" language lives in ship + workflow + README + verify-build SKILL + PR Q docs). Mitigation: explicit grep sweep Spec-walk line.
- **Contradicting merged PR S.** Mitigation: the predicate-reconciliation Spec-walk line + an assertion test that auto-advance still requires PASS.

**Files touched (anticipated):** `plugins/flow/skills/{ship,security-review,accessibility-review,verify-build}/SKILL.md` (SAFETY), `plugins/flow/docs/workflow.md`, `README.md`, `plugins/flow/evals/fixtures/**` (new), `.claude-plugin/marketplace.json` + `plugins/flow/.claude-plugin/plugin.json` (v1.5.0), dev-docs cascade (history/plan/feedback/reserved-feedback).

**Phased execution:** (1) reviewer output-contract tags + fixtures; (2) ship routing + draft-PR/manifest; (3) verify-build placement + PR S predicate reconciliation in ship/workflow; (4) fan-out sweep + README + version; (5) staff-review + ship.

---

## Managed-autonomy confidence (umbrella; planning) — PR-letter dropped (merged #32 took "PR T")

**Mode:** feature (large — spans 1 skill merge, 1 shipped-skill amendment, 1 agent + 1 rule, and the ship contract) | **Priority:** high (load-bearing for the plugin's core thesis) | **Horizon:** v1.4.x → v1.5
**Source:** 2026-05-30 conversation in worktree `infallible-mclaren-c2bd23`. User JTBD framing: *"as a user running a repo, I want to install this plugin, run a command, and get the repo set up to follow the workflow. Once set up, I want confidence it's going to work and run sequentially… it shouldn't stop arbitrarily unless it's for a good reason that we outlined in the workflow."* Five design decisions surfaced across the thread; this umbrella captures them with reasoning so the set can go through `/flow:critique-plan` + `/flow:audit-plan` before any code moves. **Not yet critiqued — planning only. Builds on the merged PR S (auto-ship-readiness trigger, v1.4.0) — PR S delivered ship auto-invocation; this umbrella extends and generalizes that work.**
**FB claims:** **FB-0034** (umbrella thesis), **FB-0035** (verify-build placement), **FB-TBD (Facet 1, unshipped — claim fresh at ship)** (doctor/init unification), **FB-0036** (all-skills model-invocable / Facet 5). The gate-principle ("human gates are plan + merge") is already shipped as **FB-0018** by PR S — this umbrella cites it, does not restate it. Reserved in `dev-docs/reserved-feedback-numbers.md`.
**Letter note:** "T" — "S" is claimed by the merged auto-ship-readiness PR (#30). Finalize at ship time; the five facets may ship as separate lettered PRs (T1…T5) if they advance at different rates — they're independently shippable.

**Unifying thesis (the durable rule, → FB-0034):** An autonomous agent can only make a *principled* proceed-vs-stop decision if every stage has an explicit, comprehensive success criterion to check against. Vague criteria force the agent into one of two failure modes — stalling with no clear done-signal, or proceeding on best-effort it can't verify. The plugin's job is to engineer the environment so Claude proceeds confidently wherever its declared criteria are met, and stops **only** at the two human gates: **final plan approval** and **PR merge**. Everything between them runs autonomously; **all flow skills are model-invocable and no skill is itself a gate** (Facet 5). **Escalation is not a failure of autonomy — it is the thing that makes the autonomy trustworthy.** This is the evaluator-optimizer principle (FB-0012 already applies it to the preflight loop: iterate only on mechanical exit signals, never on LLM judgment) generalized to every gate in the loop.

**Gate model — exactly two human gates; escalations route INTO them, never add a third (→ FB-0034, → FB-0036):** This matches CLAUDE.md's stated model — *"two load-bearing human gates (plan approval, merge), a third automatic gate on LOW-confidence assumptions."* The automatic escalation paths do not create new human stops; they route their unresolved state into one of the two existing gates:
- **LOW-confidence assumptions** surface *at the plan-approval gate* (presented in the plan for the human to resolve when approving).
- **A decision-required reviewer blocker the agent can't resolve confidently** (Facet 2) routes *into the merge gate* — the agent finishes the loop autonomously and opens the PR as a **draft + 🚫 manifest**, so the unresolved state lands in the human's merge review rather than halting the loop mid-flight to ask. The merge gate was already there; the manifest just makes "not ready" loud at it.

This is why making the reviewer/audit/ship skills model-invocable (Facet 5) is coherent with "don't stop arbitrarily": forcing a human to hand-type `/flow:critique-plan` or `/flow:ship` was an *artificial* stop that is neither of the two real gates.

**Scope (in) — five facets:**

### Facet 1 — Unify `/flow:doctor` + `/flow:init` into one detect→propose→fix entrypoint (→ FB-TBD (Facet 1, unshipped — claim fresh at ship)). **Amends PR R.**

PR R currently plans init as a *separate* skill that delegates to doctor's check matrix. This facet reframes that: **"first-time setup" is not a distinct state — a fresh repo is just one where every check fails; a drifted repo is one where one check fails.** Same machine, idempotent convergence (the `brew doctor` / `terraform plan→apply` pattern).
- **One check matrix** (already doctor's, the single source of truth). `doctor` (default) = run matrix, report read-only, print fix commands (today's behavior). `doctor --fix` (≡ PR R's PROPOSAL + EXECUTE phases together — it must propose before it applies) = run matrix, propose + apply a fix for each failure, approval-gated, idempotent.
- The PR R three-phase structure (INVENTORY / PROPOSAL / EXECUTE) survives intact — this facet decides it's a **mode of doctor**, not a sibling skill, collapsing three user-facing entry points (bootstrap.sh, doctor, init) to one mental model: *"run doctor; it tells you what's wrong and offers to fix it."*
- **Preserve safety profiles, not skills:** read-only default stays risk-free to run anywhere; `--fix` carries PR R's never-overwrite / never-delete / per-item-approval contract (FB-0014); `bootstrap.sh` stays as the non-interactive CI path.
- **Versioned CLAUDE.md workflow-section sentinel.** Add a check + fix for "is the flow workflow codified in CLAUDE.md," gated on a mechanical marker (`<!-- flow:workflow-section vX.Y -->` … `<!-- /flow:workflow-section -->`), giving three clean outcomes: **absent** → propose insert; **present + current** → pass; **present + stale version** → propose update (diff shown). This closes the drift gap surfaced this session: bootstrap writes the section once and nothing re-proposes it if it's edited, deleted, or goes stale. Drift-aware, idempotent, survives hand-edits.
- **Open question for critique:** does the merged shape obsolete PR R's standalone letter, or does PR R ship the `--fix` mode and this facet only adds the sentinel check? Resolve before execution; reconcile with PR R's reserved FB-0014.

### Facet 2 — Ship-time resolution-confidence gate + draft-PR-with-manifest (→ FB-0034 instance). **Net-new; SAFETY (ship contract).**

Closes the asymmetry found this session: `/flow:verify-build` has an explicit ship-stopping gate (`exit 1` → STOP, FB-0011 Unknown-blocks), but `/flow:security-review` and `/flow:accessibility-review` have **none** — ship Step 2 assumes every BLOCKER they raise is auto-fixable, then flows straight to PR open. That assumption breaks for: decision-required blockers (multiple valid fixes), out-of-repo blockers (committed secret needs *rotation*, a human action), and explicitly un-auto-fixable blockers (dep-reputation risk, which security-review itself routes to "human review" yet categorizes BLOCKER). Result: a best-effort PR that isn't ready, with the unresolved state buried in PR-body prose.
- **Second axis on every reviewer BLOCKER: resolution-confidence**, orthogonal to severity. *auto-fixable* (single clear fix, mechanically verifiable after) → fix in-tree, continue (today's happy path). *decision-required / out-of-repo* → **do not best-effort-resolve.**
- **Route the unresolved blocker into the merge gate, do NOT halt the loop mid-flight (per the two-gate model above).** The agent finishes the loop autonomously and opens the PR as a **draft** (`gh pr create --draft`) carrying a structured `🚫 NOT READY TO MERGE` manifest pinned at the top of the body (per-blocker: what's unresolved + what it needs — secret rotation / design decision / dep vetting + candidate resolutions). The human encounters it at the merge gate they were going to hit anyway — no new gate, no arbitrary mid-loop stop. Draft status is the mechanical signal the merge gate can trust; the manifest is the human-readable one. A not-ready PR can never *look* ready.
- **Symmetric gate semantics across all three ship-time reviewers.** Security + a11y currently have *no* ship-stopping behavior; verify-build currently *hard-stops* ship (no PR). This facet harmonizes both extremes onto the draft-PR-routing middle: any ship-time gate finding the agent can't auto-resolve → draft + manifest, never a silent proceed and never a hard halt. **This supersedes verify-build's current ship-INTERNAL hard-stop (shipped PR Q, `/flow:ship` Step 2 gate-blocking) — it's a behavior change to a shipped skill; reconcile with PR Q.**
- **Predicate reconciliation with merged PR S (resolves plan-critic BLOCKER, 2026-05-30).** Two decision points were conflated; they are distinct and must stay so:
  - **(1) Auto-advance-INTO-ship gate** (PR S readiness predicate) — **UNCHANGED.** Entering ship autonomously still requires the readiness verify-build to be `PASS` (evaluated at the step-8 readiness boundary per Facet 3). If readiness verify-build is FAIL/Unknown, the loop does NOT auto-advance — it pauses/presents. FB-0018's invariant ("auto-ship kicks in only on a real behavioral PASS") is therefore preserved; FB-0018 cannot be self-certified, so the gate stays mechanical.
  - **(2) Ship-INTERNAL handling of an unresolvable finding** — this is what changes from hard-halt → draft-routing. Because auto-advance only happened on a readiness PASS, a ship-internal verify-build FAIL means a *regression between readiness and ship* (exactly the case Facet 3's confirmation re-run exists to catch). The agent attempts the FB-0012 bounded mechanical fix; if it still can't resolve, it routes to **draft PR + manifest** rather than hard-halting.
  - **Why the safety property survives:** the draft path never produces a *merge-ready* PR on a failing build — a draft is mechanically NOT-READY and the human sees the manifest at the merge gate. So "no auto-ship on a non-PASS" holds; we only swap a mid-loop hard-halt for a clearly-marked draft, which is *stronger* (the human gets structured state at the gate they were hitting anyway, instead of a silent mid-loop stop). **This reconciliation is owned scope, not a defer — see Spec-walk.**
- Touches `plugins/flow/skills/{ship,security-review,accessibility-review}/SKILL.md` (SAFETY per `.claude/rules/safety.md`).

### Facet 3 — verify-build = readiness-boundary discovery; ship runs confirmation only (→ FB-0035). **Amends shipped PR Q; SAFETY (ship contract).**

Category error in current placement: verify-build is a **discovery** mechanism (run the app, observe, iterate on visual/behavioral gaps) parked inside `/flow:ship` Step 2, a **packaging** step. When discovery lives in packaging, the human's "ship it" triggers first-time run-and-observe, and any iteration happens *inside* the ship pipeline — manufacturing the not-ready PR of Facet 2 from a different direction. The "ship it" approval should *mean* "I've seen it work," not "go find out if it works."
- **Move the verify-build discovery loop to the Present/Iterate boundary (loop steps 8–9)** — the definition-of-done gate. Visual review + behavioral observation + iteration happen here, *before* the loop auto-advances into ship.
- **Visual sign-off folds into the MERGE gate (resolves plan-critic REDIRECT, user decision 2026-05-30).** Step 8 visual iteration is the *agent* dialing in visual quality to its best judgment against the plan-declared visual criteria (Facet 4) — NOT a human pause. Because "looks right" is a judgment the agent cannot self-certify as DONE (FB-0018), the **authoritative human visual sign-off lands at the merge gate**, via the PR preview: ship Step 8 already invokes the project's dev-server/preview skill *if one exists* (flow bundles none — it's deliberately project-shaped) and includes the URL so the human verifies in-browser before merging. **Open sub-item:** for `uiSurface` projects with no preview skill, decide the fallback (e.g., attach screenshots from the verify-build run to the PR) so the merge-gate visual sign-off isn't blind. So "dialed in before ship" = the agent's best visual pass pre-PR; the human's authoritative look happens at the (already-existing) merge gate — **no third human gate, two gates preserved.** If the agent's visual confidence is low (can't tell if it meets the criteria), that's a Facet-2 resolution-confidence escalation → draft PR + manifest, same routing as any other unresolvable finding.
- **Keep a verify-build *confirmation* re-run inside ship, reframed as a regression check:** "the diff about to become a PR still runs and still meets the criteria already signed off." Failing *here* = genuine designed-stop (something regressed between readiness and ship — bad rebase, a doc/config edit that broke a path). Should never surface *new* iteration work; if it does, the readiness gate was skipped.
- **General rule:** anything that can produce iteration runs before the readiness decision; anything inside ship is a pass/fail confirmation, never a loop. (Consistent with FB-0012 — ship-internal gates don't loop.)
- **Cost caveat:** the ship-time re-run can be gated on "did source change since the readiness verify passed?" (HEAD unchanged + readiness verify green → trust, don't rebuild). Candidate new slot.
- Touches `plugins/flow/skills/{ship,verify-build}/SKILL.md` + `plugins/flow/docs/workflow.md` (steps 8–10 reframing). Reconcile with PR Q's shipped Step 2 placement + its open FOLLOW-UP #18 (BLOCKED-state visibility) which Facet 2's manifest partly absorbs.

### Facet 4 — Plan-declared comprehensive per-stage success criteria, enforced by plan-critic (→ FB-0034 core). **Net-new.**

The spine. Declare success criteria **once, in the plan, at loop step 2**, and consume them at each gate — don't scatter criteria across skills (verify-build already does this: it pulls "plan-driven criteria" from Spec-walk checkboxes; generalize that pattern to every gate).
- Each criterion tagged **mechanical** (exit code: typecheck/test/lint/build) or **judgment** (visual quality, copy, empty-state correctness). Mechanical → the loop iterates on it (FB-0012). Judgment → checked by a reviewer/rubric; an unmet one with low resolution-confidence becomes the Facet 2 escalation gate, never silent best-effort.
- **Comprehensiveness becomes a plan-critic responsibility:** its remit grows to include *"are these acceptance criteria comprehensive — do they cover correctness, behavior, visual, security, a11y, AND scope, or are there unstated success conditions?"* That's where "super comprehensive" is enforced — at planning time, before code moves.
- Give every loop step a named exit criterion (sketch): Clarify → no unsurfaced LOW-confidence assumption; Plan → required fields + declared acceptance criteria + critique passed; Execute → implements declared scope, no drift beyond `files_touched`; Preflight → exit 0; staff-review → 4 lenses ran w/ findings or explicit N/A; Present/Iterate → verify-build criteria met + agent's best visual pass vs plan-declared criteria (authoritative human visual sign-off deferred to the merge gate, per Facet 3); Ship → all gates *confirm* (not discover), no unresolved decision-required blocker.
- Touches `plugins/flow/agents/plan-critic.md` (SAFETY — reviewer prompt), `plugins/flow/rules/plan-discipline.md` (required acceptance-criteria field), `plugins/flow/docs/workflow.md`.

### Facet 5 — All flow skills model-invocable; exactly two human gates (→ FB-0036). **Partially APPLIED this session; SAFETY (ship + reviewer skills).**

User direction (2026-05-30): *"all skills should be auto invocable — the only human gates are final plan review and PR merge (so the skills/stages shouldn't handle these specifically, but they should be able to get up to that point autonomously)."* Forcing a human to hand-type `/flow:critique-plan`, `/flow:audit-plan`, `/flow:audit-completion`, or `/flow:ship` was an artificial stop that is neither of the two real gates — it blocks the loop from running autonomously up to them.
- **EDIT APPLIED this session (uncommitted; NOT live in-session):** flipped `disable-model-invocation: true → false` on **four** skills — `audit-plan`, `audit-completion`, `critique-plan` (each `context: fork` + reviewer `agent:`), and `ship-spike`. **`ship` was already flipped by the merged PR S (#30); this session does NOT re-touch it** (reconciled at rebase — took main's `ship/SKILL.md` with its readiness-predicate preamble). `ship-spike` is the one place this session overrides PR S, which left it MANUAL — flipped per user direction (spike is human-chosen at the plan gate; ship-spike never merges, so per "safety lives at the merge gate" auto-invoking it crosses nothing; caveat below). The other flow skills were already model-invocable. Reconciled the one fan-out survivor: `dev-docs/spec.md:42` ("Two slash commands the user invokes manually" → auto-invocable framing).
- **ship-spike caveat (judgment-gated, no mechanical predicate):** PR S's `ship` auto-advance is gated on a mechanical readiness predicate (verify-build would PASS). A spike has no equivalent — its "done?" signal is "did I answer the research question?", a judgment. So auto-advancing into `ship-spike` necessarily fires on judgment, not a mechanical gate. Acceptable *because* spike code is disposable, the spike PR never merges, and it's human-reviewed — but it should NOT grow a fake mechanical predicate to look symmetric with `ship`.
- **TECHNICAL FINDING (smoke-tested this session):** `disable-model-invocation` is read at **plugin/session load time, not per-call.** After the frontmatter edit, `Skill("flow:audit-plan")` still errored `cannot be used with Skill tool due to disable-model-invocation`. So the edit takes effect only on the **next** session / plugin reload — it is NOT active in the session that made it. Consequence: (a) any future change to a skill's invocation flag must be verified in a *fresh* session, never assumed live mid-session; (b) the fork-path behavioral check below cannot run until reload.
- **UNVERIFIED (auditor ISSUE, accepted):** that model-invoking a `context: fork` reviewer skill delivers the *same* preprocessed context to the forked subagent as the old hand-typed path did. This is a runtime-mechanics claim no repo file establishes, and it could not be smoke-tested in-session (see finding above). **Before Facet 5 ships:** in a fresh session, model-invoke one fork reviewer against a known fixture and confirm the forked subagent receives identical preprocessed context to the `disable-model-invocation: true` path. Until then, treat the audit/critique auto-invocation as edit-complete but behavior-unverified.
- **No skill *is* a gate.** `ship`/`ship-spike` already stop *at* the merge gate by never merging ("Do not merge. Do not approve. Do not run `gh pr merge`." — ship Step 8); making them model-invocable lets the loop reach the PR-open step autonomously without crossing the merge gate. The audit/critique skills are review passes, not gates.
- **Remaining (now DONE in PR U):** README "What's installed?" / slash-command table + `plugins/flow/docs/workflow.md` describe the reviewer/ship-spike auto-invocability explicitly (PR S already documented `ship`'s auto/manual row + the auto/manual map; extend it to the now-flipped reviewers + ship-spike). `/flow:doctor` could grow a check asserting no flow skill regressed to `disable-model-invocation: true` except by deliberate decision. CLAUDE.md product-principle line already states the two-human-gate model — keep in sync.
- **Resolved (user, 2026-05-30):** `ship` should NOT carry a safety property via non-model-invocation, and no `autoShip` slot is warranted. The safety boundary is the **merge gate** (and adjacent merge-time infrastructure), not the auto-invocation flag — `ship` opens a PR but never merges, so auto-invoking it crosses nothing irreversible. Ship-time safety lives in the gates ship runs (security/a11y/verify-build) and at merge, not in whether a human hand-typed the command. Drop the `autoShip` idea.

**Scope (out):**
- 100% deterministic workflow. Explicitly a non-goal (user direction this session): the aim is *principled* proceed-vs-stop, not mechanical determinism everywhere.
- Hard Stop hooks enforcing step-skips (e.g., a Stop hook failing if `/flow:critique-plan` was skipped). Still deferred to the v1.x autonomous-routines work per `template/base/CLAUDE.md.template`; this umbrella is about gate *semantics + criteria*, not hook enforcement.
- New auto-fix categories for the resolution-confidence gate beyond the conservative FB-0011 default-to-ESCALATE list. AUTO-FIX-SAFE grows only with dogfood evidence.

**Spec-walk (planning-level; each facet gets a full Spec-walk when it splits into a shippable PR):**
- [ ] Facet 1: `--fix` mode decided as a doctor mode vs PR R sibling-skill; CLAUDE.md sentinel check added with absent/current/stale outcomes; FB-0014 reconciled.
- [ ] Facet 2: resolution-confidence axis defined in security-review + a11y-review output contract; symmetric ship-stop semantics; draft-PR + manifest implemented; reconciled with PR Q FOLLOW-UP #18.
- [ ] Facet 2 ↔ PR S predicate reconciliation (plan-critic BLOCKER): auto-advance-into-ship still requires readiness verify-build PASS (PR S predicate unchanged + FB-0018 invariant intact); only ship-internal unresolvable findings route to draft. Edit owns the PR S predicate wording (and ship Step 8 / workflow.md) so removing the internal hard-halt does not weaken the auto-advance gate. (verify: read reconciled predicate; confirm no merge-ready PR is producible on a non-PASS build)
- [ ] Facet 3: verify-build discovery relocated to workflow steps 8–9; ship-time run reframed as confirmation; "did source change" skip slot evaluated; PR Q Step 2 placement reconciled.
- [ ] Facet 4: plan-critic remit extended to criteria-comprehensiveness; plan-discipline.md requires an acceptance-criteria field; per-step exit criteria documented in workflow.md.
- [~] Facet 5: four skills' frontmatter flipped to `disable-model-invocation: false` this session (audit-plan, audit-completion, critique-plan, ship-spike); `ship` was already flipped by merged PR S; spec.md:42 fan-out reconciled. **Edit done this session (uncommitted); NOT live until reload — flag is load-time, not per-call.** NOT done: fork-path behavioral parity check (must run in a fresh session, per auditor ISSUE); README/workflow.md reviewer + ship-spike auto/manual doc; optional doctor regression check.
- [x] Whole umbrella runs `/flow:critique-plan` + `/flow:audit-plan` (2026-05-30, on the reconciled 5-facet version). plan-critic: 2 findings (BLOCKER — PR S predicate vs Facet 2 draft-routing; REDIRECT — visual sign-off placement), both resolved in-plan. auditor: no issues, 8 recall/assumption claims verified. Umbrella is critique-clean; **per-facet execution may now begin** (each facet still gets its own full Spec-walk + review when it splits into a shippable PR).

**Confidence verdicts:**

**Assumption:** The five facets are coherent facets of one thesis (principled proceed-vs-stop) and benefit from being planned together even if shipped separately.
**Confidence:** HIGH
**Why:** Each facet independently traces to the same JTBD and the same evaluator-optimizer principle already encoded in FB-0012; planning them apart would risk contradictory gate semantics.
**If it flips:** split into five standalone plan entries; the thesis still lives in FB-0034.

**Assumption:** Reframing verify-build's placement (Facet 3) does not require reverting any of shipped PR Q's mechanism — only *where in the loop* the discovery vs confirmation runs.
**Confidence:** MEDIUM
**Why:** PR Q's skill is placement-agnostic in principle (it's invokable standalone for mid-iterate checks per its own description), but ship Step 2 wiring + workflow.md + FOLLOW-UP #18 are coupled to the current placement. Needs verification against the shipped skill before execution.
**If it flips:** Facet 3 carries a larger ship.md/workflow.md diff than anticipated; treat as its own lettered PR with full staff-review.

**Assumption:** Extending plan-critic's remit (Facet 4) to judge criteria-comprehensiveness won't materially raise its false-positive rate.
**Confidence:** MEDIUM
**Why:** plan-critic is a safety-critical reviewer prompt (small wording shifts flip FP rates per `.claude/rules/safety.md`); a "are these criteria comprehensive?" mandate could make it flag thin-but-adequate plans. Needs an eval fixture first.
**If it flips:** scope Facet 4 to plan-discipline.md (the required field) only, and leave plan-critic judgment for a later eval-backed PR.

**Risks:**
- **Ship-contract fan-out (FB-0010).** Facets 2 + 3 both edit `ship/SKILL.md`; the resolution-confidence + draft-PR + confirmation-only changes must land coherently. Mitigation: if shipped separately, sequence Facet 2 then Facet 3, grep-first-edit-second on every ship-step reference.
- **Reconciling with two existing PRs.** Facet 1 amends queued PR R; Facet 3 amends shipped PR Q. Mitigation: each facet's Spec-walk has an explicit "reconcile with PR R/Q" checkbox; don't execute until reconciliation is recorded.
- **Safety-critical surface.** Three of four facets touch SAFETY surfaces (ship pipeline ×2, plan-critic prompt). Mitigation: full `/flow:critique-plan` + `/flow:audit-plan` on the umbrella, eval fixture before any plan-critic wording change, `SAFETY` markers in commits + history.

---

## PR Q — `/flow:verify-build` skill: plan-driven behavioral verification gate (MERGED #26, v1.3.0)

**Mode:** feature (medium — full skill + 5 lib assets + 3 fixture sets + workflow + doctor + schema integration) | **Priority: high** | **Horizon:** v1.3.0
**Branch:** `claude/lucid-matsumoto-730ba0` during execution; renamed to `pr-q/verify-build-skill` at ship time.
**Canonical plan:** [`dev-docs/handoffs/pr-q-verify-build-plan.md`](handoffs/pr-q-verify-build-plan.md) — full Mode/Goal/Scope/Spec-walk/Confidence verdicts/Risks/Phases/Files-touched.

**Goal (one-liner):** Add `/flow:verify-build` as a thin wrapper around bundled `/verify` (transitively `/run` + `/run-skill-generator`) that adds plan-driven criteria extraction (from `**Spec-walk:**` checkboxes), adversarial criteria transformation, per-dimension parallel judges with Unknown-blocking gate, and structured findings buffer routed to `/flow:ship` Step 4a. Closes the static-analysis-only gap in the loop's verification surface (Potemkin-interface / hallucinated-success class — the dominant agentic-dev failure mode no current flow step catches).

**Sequencing — orthogonal, not queued:** PRs N (orchestration hardening), O (test-edit hook), P (auditor model-diversity), R (init-skill) target different surfaces. PR Q targets `/flow:ship` Step 2 final-pass review surface. Different files in the diff; no real content dependency. Rebases onto main as N/O/P/R land. Ship order = whichever finishes first. Inherited locked pattern: PR M's FB-0012 bounded-retry contract — verify-build's judge runs single-pass; any future retry primitive inherits PR M Step 1c's `(a)` mechanical exit signal + `(b)` N=3 + diff-hash + `(c)` no test-disabling guards.

**Status (2026-05-28):** **All 11 phases complete; PR open / ready to merge.** Phases 1–9 landed the skill + lib/ + fixtures + integration. Phase 10 (staff-review dogfood) returned 1 BLOCKER + 19 NITs + 13 FOLLOW-UPs; BLOCKER + 11 cheap NITs fixed in-tree; 18 FOLLOW-UPs routed below. Phase 11 bumped manifest v1.2.6 → v1.3.0 + added flow.config.json self-config (platform: library + uiSurface: false). Final schema slot count: 17 → 21 (added platform via staff-review NIT, on top of the 3 planned verifyEnabled/verifyFindingsPath/verifyBudgetCalls). FB number resolved as **FB-0015** (cascaded from drafted FB-0010 → FB-0012 → FB-0013 → FB-0014 → FB-0015 as collisions surfaced).

**Locked patterns inherited:** FB-0008 (stale-base preflight), FB-0009 (fail-fast on missing CLIs), FB-0010 (consistency discipline; silent-skip + fan-out defenses applied), FB-0011 (autonomy bar; Unknown ⇒ ESCALATE), FB-0012 (bounded-retry contract from PR M — mechanical exit signal + N=3 + reward-hacking guards), FB-0015 (check bundled first — applied to thin-wrapper shape).

**Letter / FB history (for traceability):** drafted as "PR M" in conversation (2026-05-27→28 morning); collided with bounded-retry PR M (`0cf642e`). Renumbered to PR Q after K1's protocol audit (per PR R's reserved-feedback-numbers entry which acknowledged Q as my slot). FB number cascaded: original FB-0010 → FB-0012 (PR G collision) → FB-0013 (PR M collision; PR P reserved) → FB-0014 (PR R claimed) → **FB-0015** at this rebase.

**Files touched:** new under `plugins/flow/skills/verify-build/` (SKILL.md + lib/{extract-criteria.py, adversarial.md, rubric.md, spike-rubric.md, not-tested-checklist.md, findings-schema.json, findings-example.json}); new under `plugins/flow/evals/fixtures/` (verify-unknown-blocks/, verify-toy-web-app/, verify-budget-overrun/ — 14 fixture files total); modified `plugins/flow/skills/{ship,ship-spike,doctor}/SKILL.md` (SAFETY), `plugins/flow/docs/workflow.md`, `plugins/flow/schema/flow.config.schema.json` (4 new slots: `platform`, `verifyEnabled`, `verifyFindingsPath`, `verifyBudgetCalls`; total 17 → 21), `docs/{bootstrap,migration}.md`, README.md + `template/base/{CLAUDE.md.template,bootstrap.sh}` + manifest descriptions (slot count fan-out); plus dev-docs cascade (feedback, plan, roadmap, reserved-feedback-numbers, handoffs/pr-q-verify-build-plan.md).

### PR Q+ FOLLOW-UPs from staff-review (2026-05-28; 4 parallel lenses)

1. **Doctor Check 2.5 scan misses install-surface JSON** (engineer lens FOLLOW-UP) — Check 2.5's slot-count fan-out scan scans CLAUDE.md / README.md / docs / core-docs / dev-docs but NOT `.claude-plugin/marketplace.json` or `plugins/flow/.claude-plugin/plugin.json`. PR Q's BLOCKER was a fan-out survivor in exactly those install-surface descriptions. Generalize Check 2.5's grep to include `.claude-plugin/` and `plugins/flow/.claude-plugin/`. Horizon: next doctor-touching PR (or PR N if it generalizes the scan anyway).

2. **Spike-mode pre-check vs Python parser asymmetric match rules** (engineer lens FOLLOW-UP) — SKILL.md Step 2 uses `grep -q '\*\*Spec-walk'` (looser, line-substring match); Step 3's Python regex requires line-anchored `^\s*\*\*Spec-walk:?\*\*:?\s*$` (stricter). A plan with `**Spec-walk:** see below:` passes Step 2 (not spike) but Step 3 yields zero criteria. Tighten Step 2 grep to anchor on `^[[:space:]]*\*\*Spec-walk` AND optionally trailing `:?\*\*` to mirror Python. Horizon: before first real-run dogfood; cheap one-line tighten.

3. **metadata.platform_hint enum couples to bundled /run autodetect output labels** (engineer lens FOLLOW-UP) — If bundled `/run` ever changes its autodetect labels (cli/server/tui/electron/browser-driven/library), verify-build silently mis-classifies in the findings buffer. Add a smoke fixture asserting current `/run` labels at first dogfood run + a graceful fallback to `"unknown"` if a new label appears. Horizon: Phase 1 empirical /verify characterization (already on roadmap; fold in).

4. **Workflow.md cheat-sheet row for verify-build is twice the width of siblings** (UX lens FOLLOW-UP) — Trim "Plan-driven behavioral verification: extract criteria from `**Spec-walk:**` checkboxes, adversarial transform, judge bundled `/verify`'s observations per dimension, block ship on Unknown" → "Plan-driven behavioral verification: runs the built artifact, judges per-dimension, blocks ship on Unknown." Horizon: next workflow.md polish PR.

5. **README.md `What's installed?` block did NOT mention verify-build** (UX lens FOLLOW-UP) — Only the slot count moved. Add a one-line bullet for `/flow:verify-build` alongside the other named skills. Horizon: PR Q ship time addendum OR first README touch.

6. **`verifyBudgetCalls` unit is ambiguous at user-facing layer** (UX lens FOLLOW-UP) — Schema description names "MCP tool calls" implicitly but the ship line and SKILL.md don't disambiguate (HTTP calls? Model calls? Verify-side tool calls?). Sweep the user-facing references to say "verify-side MCP tool calls." Horizon: docs cadence PR.

7. **Empty-state messaging for "verify ran, all PASS, zero criteria extracted"** (UX lens FOLLOW-UP) — A plan with `**Spec-walk:**` heading but zero checkboxes silently produces PASS-via-vacuous-truth. Add a Step 3 sentinel: zero criteria + not in spike mode → emit Unknown with "no criteria to verify; check plan's Spec-walk block." Horizon: Phase-1 empirical follow-up; defer to first dogfood that exposes the empty case.

8. **findings-schema.json strict-validator compatibility** (design-engineer lens FOLLOW-UP) — `additionalProperties: false` at top level + a `definitions` block may trip strict ajv-class validators that don't special-case the `definitions` keyword. The right test is "does ajv accept findings-example.json against findings-schema.json?" Defer to whichever PR wires the first real schema-validation harness.

9. **Toy-app fixture HTML doesn't match its plan** (design-engineer lens FOLLOW-UP) — Plan/plan.md has a criterion about "form validation rejects empty required fields" but app/index.html has no form (one button only). Either expand the HTML to have the form, or trim the second criterion. Horizon: first real dogfood that uses the toy fixture in an executable harness.

10. **No design-language.md for the future HTML renderer PR** (design-engineer lens FOLLOW-UP) — When the verify-build HTML case-study renderer PR lands, it will need a `dev-docs/design-language.md` covering report typography scale, semantic colors for PASS/FAIL/Unknown, timeline-rendering conventions. Horizon: blocks the future HTML renderer at staff-review time; create the design-language doc as part of that PR's intake.

11. **`verifyDimensions` slot** (push-further roadmap-concrete) — Let consumers exclude scope-creep judging for refactor-class PRs (where scope IS "do not change behavior" by definition). Add a 4th verify slot with default `["correctness","regression","scope-creep"]`; Step 6 spawns judges only for the configured subset. Horizon: post-PR-Q after observing one refactor PR's verify behavior; ~30 LOC in SKILL.md Step 6 + a new slot + fixture variants.

12. **Absolute timestamp anchor in findings-buffer metadata** (push-further future-exploration) — `timestamp_offset_ms` is relative; no absolute anchor in metadata. Renderer cannot say "this verify pass happened on 2026-05-28T14:32Z" or compare across runs. **Surfaces when:** HTML renderer work begins OR a second consumer of the findings buffer is added (CI dashboard, verify-history timeline). Direction: add `metadata.verify_started_at_iso8601` (additive; schema_version stays 1.0). Don't add preemptively in PR Q.

13. **Voice/tense inconsistency across lib/*.md prompts** (UX lens FOLLOW-UP) — `rubric.md` and `spike-rubric.md` mix second-person-to-judge with third-person-passive. `not-tested-checklist.md` is third-person-descriptive. Pin second-person throughout judge prompts; third-person in docs/checklists. Horizon: next lib/-touching PR (probably the calibration fixture PR mentioned above).

14. **Bootstrap Step 5.5 inverts cause-and-consequence** (UX lens FOLLOW-UP) — First sentence explains wrapper plumbing before naming the action. Reorder: open with "Run `/run-skill-generator` once per project" then drop the wrapper explanation into "Why this matters." Horizon: next bootstrap.md touch.

15. **Skill description is 13 lines vs project's 5-6 line norm** (UX lens FOLLOW-UP) — Trim to ~6 lines; move composability + adversarial-transformation detail to body. Horizon: docs cadence PR.

16. **Doctor 5.3 third-line "opt-out" anti-pattern** (UX lens FOLLOW-UP) — Currently teaches "you can set verifyEnabled=false to make this go away." Rewrite as a condition: "Only set verifyEnabled=false if your project has no runnable target — a pure library or docs-only repo." Horizon: next doctor touch.

17. **Web "not tested" checklist conflates three categories** (UX lens FOLLOW-UP) — Mix of environment / unexercised-flows / breadth axes. Group into three sub-labels so the agent can scan independently. Horizon: docs cadence PR.

18. **Consolidated review-results line buries the BLOCKED state inside `ran (...)` parens** (UX lens FOLLOW-UP) — When verify-build returns Unknown/FAIL and blocks ship, the alarm is hidden behind `verify-build=ran (overall_verdict:Unknown, gate BLOCKED)`. Promote BLOCKED to a top-level state visible at the level of `ran|skipped`. Horizon: ship.md Step 2 line format revision; small wording change with real signal value.

---

## PR G — Consistency discipline (FB-0010, SHIPPED — squash `0c3386b`)

**Mode:** feature (small) | **Priority: highest**
**Goal:** Defend against the most-recurring bug class (FB-0010, 6 incidents): silent-skip on edge case + fan-out contradiction. Encode as explicit lens prompts + a mechanical doctor check + a workflow.md preflight note + a project-dev rule.

**Scope (in):**
- `dev-docs/feedback.md` — FB-0010 entry with all 6 PR citations and the two-flavor synthesis.
- `plugins/flow/agents/lens-staff-engineer.md` — silent-skip + fan-out hunts added to Hunts; consistency-sweep + silent-skip-sweep added to Specifically Asks; Gotchas reinforced.
- `plugins/flow/skills/doctor/SKILL.md` — Check 2.5 comparing `jq '.properties | keys | length'` on the schema against "N slots" claims in CLAUDE.md/README.md/docs/.
- `plugins/flow/docs/workflow.md` Step 4 — "consistency sweep" paragraph (FB-0010 reference).
- `.claude/rules/general.md` — Consistency discipline subsection (project-dev rule, auto-loads on every edit).
- `README.md` — v1.2.5 version note.
- `.claude-plugin/marketplace.json` + `plugins/flow/.claude-plugin/plugin.json` — v1.2.2 → v1.2.5, descriptions refreshed.
- `dev-docs/history.md` — decision-log entry.
- `dev-docs/plan.md` — this block + Current Focus refresh.

**Scope (out):**
- Pre-commit hooks (rejected: install friction outweighs benefit at this scale).
- Stop hook for skipped `/flow:critique-plan` (deferred to v1.x autonomous-routines work).
- Auto-fix for stale slot counts (doctor flags WARN; fix is author judgment).
- New eval fixtures (deferred until pattern proven by next consumer dogfood).

**Spec-walk:**
- [ ] FB-0010 entry exists with the two-flavor synthesis + all 6 PR citations.
- [ ] `lens-staff-engineer.md` Hunts list, Specifically Asks, and Gotchas all reference the new patterns explicitly.
- [ ] `/flow:doctor` Check 2.5 added; smoke against current flow repo emits PASS (all "16 slots" mentions match schema).
- [ ] `workflow.md` Step 4 mentions the consistency sweep.
- [ ] `.claude/rules/general.md` has the new subsection BEFORE "Autonomous work guardrails".
- [ ] README v1.2.5 line added.
- [ ] Both manifests bumped + descriptions refreshed; `claude plugin validate .` clean.
- [ ] `dev-docs/history.md` entry written.
- [ ] Self-test: grep for any remaining "14 slots" / "15 slots" / etc. across the tree returns nothing; no v1.2.2-only version strings in any new file.

**Confidence verdicts:**

**Assumption:** The lens-staff-engineer prompt addition will improve catch rate on the next consistency-class incident.
**Confidence:** MEDIUM
**Why:** Prompt-level vocabulary additions improve LLM behavior probabilistically. The shape is concrete enough (grep, then flag survivors) that the lens has a clear action to take. Adversarial review still serves as backstop.
**If it flips:** Promote to mechanical pre-commit check (rejected for v1.2.5 but reachable in v1.3+).

**Assumption:** Doctor Check 2.5's awk-filtered grep won't produce false positives on the current flow tree.
**Confidence:** HIGH
**Why:** Schema's slot count is THE source-of-truth and is single-pull-via-jq; any documented mismatch is genuinely stale. Verified via spec-walk smoke step.
**If it flips:** Tighten regex or add a doctor-skip glob slot. Single-file fix.

**Files touched:** 10 files (see Scope (in) — `.claude-plugin/marketplace.json` + `plugins/flow/.claude-plugin/plugin.json` count as 2 distinct edits even though the bullet groups them).

### PR H+ FOLLOW-UPs routed from PR G review pipeline (6 parallel lenses)

PR G's review (engineer + push-further + UX-designer + design-engineer + security + plan-critic) caught 2 BLOCKERs + 6 NITs (all fixed in-tree) + these 9 FOLLOW-UPs:

1. **FB-0010 Defense #4 — silent-skip skill-code pairing across existing shipped skills.** PR G covers defenses #1-3 (lens prompt + doctor check + project-dev rule); defense #4 (skill code: "pair every `2>/dev/null || true` / `// empty` / `|| ""` with explicit positive assertion or `[WARN]` branch") was not applied to existing skill bodies. Scope-deferred because the pattern requires a sweep of all 11 shipped skills + 5 scripts + 1 tool; bigger than PR G's small-feature charter. Owner: domain agent. Horizon: PR H (consumer-feedback round 2 after the new-project dogfood).

2. **Generalize Check 2.5 beyond slot count.** FB-0010 names 4 fan-out targets (counts, names, slots, version strings); Check 2.5 mechanizes only slot count. Symmetric pairs worth mechanizing: skill count (`ls plugins/flow/skills/ | wc -l` vs documented "N user-visible skills"), lens count (`ls plugins/flow/agents/lens-*.md` vs "four-lens"), rule count (`ls plugins/flow/rules/*.md` vs "four portable rules"). Each is ~5 lines of `ls | wc -l` + grep. Defer to v1.2.6 alongside next consumer dogfood. Owner: domain agent. Horizon: PR H.

3. **Consumer-shipped consistency rule (`plugins/flow/rules/general.md`).** PR G added the rule to project-dev `.claude/rules/general.md` only. The shipped portable rule (`plugins/flow/rules/general.md`) has no equivalent — consumers don't inherit the discipline at the rule-level. Lens-engineer catches it at staff-review time; a rule would catch it during execution. Cheap to land. Owner: docs agent. Horizon: PR H or v1.2.6.

4. **CLAUDE.md.template consumer-facing mention.** Consumers reading `template/base/CLAUDE.md.template` have no pointer to the consistency discipline (only `plugins/flow/docs/workflow.md` Step 4 surfaces it consumer-side). A one-line bullet would let consumers self-discover. Pairs naturally with #3. Horizon: PR H.

5. **`plugins/flow/agents/plan-critic.md` fan-out hunt addition.** Plan-critic's "Internal incoherence" category covers "plan steps that contradict each other" but lacks explicit fan-out vocabulary the way `lens-staff-engineer` now has. A plan listing "16 slots" in one section and "14 slots" in another is the in-plan analog of the same bug class. One-line bullet under Internal incoherence: "count/name/slot/version referenced multiple times in the plan — values must agree." Horizon: PR H.

6. **Schema-path fallback hardening in Check 2.5 (security).** When `CLAUDE_PLUGIN_ROOT` is unset, Check 2.5 falls back to `plugins/flow/schema/flow.config.schema.json` (project-relative). A malicious project shipping a same-named file under that path would have doctor report against the WRONG source-of-truth. No RCE, but "fails closed in wrong direction." Fix: require an explicit sentinel like `[ -f .claude-plugin/marketplace.json ]` before trusting the fallback path. Horizon: PR H or v1.2.6.

7. **Symlink-following grep hardening in Check 2.5 (security).** `grep -rEn` follows symlinks on BSD/macOS by default. A `docs/` symlinked to `/etc` would surface `/etc/*.md` "N slots" lines to doctor output (information disclosure, no exec). Defensive fix: `find … -type f -name '*.md' -print0 | xargs -0 grep …`. Horizon: PR H.

8. **Intra-file contradiction detection.** The PR F pass-2 doctor SKILL.md line 22 vs line 260 contradiction was a within-file fan-out shape. The lens-engineer's new hunt language is framed across-files; within-file is unmechanized. Worth a within-file consistency-sweep mode for the lens (or a new doctor check) once a 2nd within-file incident lands. Horizon: surfaces-when a second within-file incident lands.

9. **"PRs 1, B, D, E, F (×2)" citation drift across files.** The 6-incidents-across-5-PRs phrasing now varies across README, marketplace.json description, plugin.json description, FB-0010 entry, history.md, plan.md. Worth defining canonical phrasing in FB-0010 and reference-by-FB elsewhere ("see FB-0010 for the incident list"). This is itself a fan-out shape — ironic but real. Horizon: PR H.

10. **Re-open pre-commit-hook question if a 7th FB-0010 incident lands.** PR G explicitly rejected pre-commit hooks on install-friction grounds. The rejection is defensible only if the prompt-level + check-level defenses suffice. The 7th incident is the experimental signal. Trigger: any future PR that ships a stale count/name/slot/version that survives both `lens-staff-engineer` and Check 2.5. Horizon: triggered-by-occurrence; route to v1.3 if/when.

11. **Workflow.md Step 4 placement of non-mechanical disciplines.** Step 4's lead sentence says "Mechanical gates that MUST be green." Both the existing "Failure-pattern memory" paragraph and PR G's new "Consistency sweep" paragraph are non-mechanical disciplines living inside the "mechanical gates" step. Design-engineer flagged the structural drift but the in-tree fix (sub-heading or move-to-Step-6) was deferred to avoid scope creep in PR G. Horizon: next workflow.md-touching PR.

12. **"Consumer-shipped" vs "project-dev" terminology standardization.** FB entries use parenthetical labels; history.md uses "Two-layer defense" framing. Worth a style-guide note for future FB entries that span both surfaces. Horizon: dev-docs hygiene PR.

13. **Release tagging + version-pinning recipe** (caught during PR H1 pre-lens self-check). PR H1's first draft of `docs/upgrade.md` included a "Pin to a prior version" recipe using `git checkout v1.2.5` — but flow doesn't tag releases at the git-tag level (only `pre-flow-plugin` tag exists). And `~/.claude/plugins/flow/` isn't a known stable path across Claude Code install shapes. Recipe was removed from upgrade.md as false-affordance per CLAUDE.md "no false affordances" rule; recipe re-introduction requires (a) backfill-tagging v1.0.0..v1.2.5 against historical merge SHAs (one-time), (b) auto-tag-on-merge for future PRs (GitHub Actions step on main push or release-please-style automation), (c) verify the actual Claude Code plugin install dir convention. Owner: docs+infra. Horizon: PR H proper or v1.2.6 if a consumer hits a regression they need to roll back from.

14. **CHANGELOG drift trigger** (PR H1 push-further-lens NIT). Manual CHANGELOG maintenance assumed by PR H1 has no mechanical trigger. Add `/flow:ship` spec-walk item: "if version bumped in this PR, CHANGELOG.md has a new entry for the bumped version." Either as a `/flow:ship` Step N check, or as a pre-commit grep in the project's preflight. Until then, the first forgotten CHANGELOG update IS the test of discipline. Horizon: PR H proper or any `/flow:ship`-touching PR.

15. **`/flow:upgrade` skill** (PR H1 push-further-lens FOLLOW-UP). Wraps the 2-command ritual + runs `/flow:doctor` + diffs CHANGELOG-since-last-installed-version. ~40 lines of bash; 1-2 hour build. Real ambition rightly deferred from PR H1 (which is docs-only); land alongside `minFlowVersion` slot + Doctor Check 6 (FOLLOW-UP #2). Horizon: PR H proper or v1.2.6.

16. **CLAUDE.md "Product Principles" should anchor the patch-additive discipline** (PR H1 push-further-lens BLOCKER-lite, addressed in-tree by softening CHANGELOG + upgrade.md prose). The discipline ("patch bumps aim to be additive") now lives in CHANGELOG + upgrade.md but is not in CLAUDE.md, plugin.json description, or any process gate. Worth promoting to CLAUDE.md "Product Principles" as a stated discipline (not contract). Horizon: next CLAUDE.md-touching PR.

17. **Historical-narrative immunity for Check 2.5** (PR H1 engineer-lens FOLLOW-UP). Check 2.5 currently flags every "N slots" mention where N != schema-actual, including legitimate historical prose like "schema bumped from 13 to 16" in `dev-docs/history.md`. The current flow tree emits WARN with 12 such survivors — all intentional narrative. Fix shape: either (a) add a `dev-docs/handoffs/` + `dev-docs/history.md` exclude-list to Check 2.5 (cheap, blunt), (b) skip lines containing context-words like `was`, `bringing`, `estimated`, `→`, `from N` (heuristic), or (c) require a sentinel `<!-- historical -->` HTML comment to mark intentional historical-narrative lines (explicit, more work for authors). Land alongside the Check 2.5 generalization to skill/lens/rule counts (FOLLOW-UP #2) so consumers don't get spurious WARNs on their own historical narrative. Horizon: PR H proper or v1.2.6.

18. **`docs/README.md` index** (PR H1 UX/design-engineer FOLLOW-UP). With `docs/` now holding 4 substantive files (bootstrap, migration, first-pr, upgrade) plus CHANGELOG.md at root, the implicit user journey isn't obvious from the directory listing. A ~20-line decision-tree index ("new project → bootstrap; existing → migration; already installed → upgrade; first PR → first-pr") would be a 5-minute fix compounding across consumer projects. Horizon: PR H proper.

19. **CHANGELOG framing softening** (PR H1 UX/design-engineer NIT). History.md describes CHANGELOG as "Keep-a-Changelog-style" but it lacks K-a-C's `[Unreleased]`, `Added/Changed/Fixed/Removed/Security` subhead categories, and the keepachangelog.com footer link. Honesty fix: change framing in history.md + (eventually) CHANGELOG header from "Keep-a-Changelog-style" to "flow's own consumer-changelog format (date + headline + bullets + breaking-change callout)." Cheap; ride next history.md-touching PR.

21. **`PreToolUse` hook on `Bash` matching `gh pr create`** (PR I push-further-lens FOLLOW-UP F2). Currently PR I ships 3 prompt-level reminders to use `/flow:ship` instead of `gh pr create`. Three of the four defenses (Step 1.0 surface, staff-review footer, workflow.md Step 10) only render if the author opens `/flow:ship` or `/flow:staff-review` — the author who skips both still skips silently. A PreToolUse hook in `.claude/settings.json` matching `gh pr create` could print "use /flow:ship; remove this hook from .claude/settings.json if intentional." ~10 lines of settings.json + 1 doc paragraph. Higher signal-to-friction than another prompt reminder. Horizon: triggered by 2nd workflow-spawn-skip incident OR ride next `.claude/settings.json`-touching PR.

22. **Consumer-shipped workflow rule (`plugins/flow/rules/workflow.md`)** (PR I push-further-lens FOLLOW-UP F3). PR I adds the workflow discipline to `.claude/rules/general.md` (project-dev only). Push-further correctly noted my "fan-out avoidance" reasoning was backwards — rules auto-load on every edit, workflow.md auto-loads on zero edits; the rule is the load-bearing surface and the doc is the reference. Consumer projects need the same defense. Cheap to add — copy the `.claude/rules/general.md` Workflow discipline subsection into a new `plugins/flow/rules/workflow.md` with `paths: ['**/*']` frontmatter. Horizon: PR H proper or v1.2.7.

23. **Encode-after-1-incident threshold as a written rule** (PR I push-further-lens FOLLOW-UP F1). PR I's history.md "Lessons learned" names the principle: *"threshold isn't hard; it's 'is encoding cost less than expected recurrence cost?'"* Should be promoted out of one PR's history entry into `.claude/rules/general.md` (or `dev-docs/feedback.md` as a meta-rule). Otherwise the next 1-incident "but the fix is cheap" judgment call has no precedent to lean on. Cheap; ride next feedback-touching PR.

24. **Make STATUS: SKIPPED actually load-bearing** (PR I push-further-lens FOLLOW-UP B1's path-2 deferral). PR I softened the language ("explicit log line in the session transcript" — true) from "load-bearing audit trail" (false; nothing programmatically consumes the STATUS lines). The real fix: either append STATUS lines to a per-PR record under `~/.claude/plugins/data/flow/` OR add a `/flow:doctor` Check that scans the most recent session transcripts for the STATUS lines. Real scope; defer until the discipline surface needs the upgrade. Horizon: when audit-trail consumption becomes a concrete need.

25. **`.claude/rules/documentation.md` plan.md-maintenance rule vs PR-I practice** (PR I UX/design-engineer NIT #3). The rule says "Completed items move to 'Recently Completed'" but PR I marked FOLLOW-UP #20 in-place with `✅ SHIPPED in PR I (v1.2.6)` prefix because the numbered list is referenced from history.md ("FOLLOW-UP #20"); moving items would break the cross-refs. Resolution: update the documentation rule to explicitly permit in-place `✅ SHIPPED in PR X` marking for numbered traceability lists (numbered FOLLOW-UPs, FB-XXXX entries). Cheap; ride next `.claude/rules/documentation.md`-touching PR.

26. **/flow:ship Step 1.0 surface is now ~25 lines** (PR I engineer-lens FOLLOW-UP F2). Originally 3 ASSUMES lines. PR I adds 7 lines of REMINDER prose. 2.3x expansion. If the user ignored 3 lines, will they read 25? Signal-to-watch at next dogfood. Not fix-now; capture for next /flow:ship-touching PR's plan.

27. **`/flow:doctor` install-scope detection** (PR M combined-lens FOLLOW-UP; engineer-lens NIT #3 promoted to numbered entry to close the FB-0010 fan-out it surfaced — history.md PR M entry routed an unnumbered FOLLOW-UP, which IS the FB-0010 shape the project defends against; numbering closes the contradiction). Add a `/flow:doctor` check that detects at runtime whether flow is user-scope-enabled (`~/.claude/settings.json`'s `enabledPlugins."flow@flow"`) or project-scope-enabled (`./.claude/settings.json`'s same key). Reports scope + the cross-machine-vs-cross-project upgrade behavior implications. Would prevent recurrence of the per-session-vs-per-machine factual error PR M corrects. Cheap: ~15 lines in doctor SKILL.md Section 1; pairs naturally with Check 1.2 (plugin enabled). Owner: domain. Horizon: PR H proper or v1.2.7.

20. ✅ **`/flow:security-review` + `/flow:accessibility-review` workflow-spawn discipline** — **SHIPPED in PR I (v1.2.6).** PR H1's workflow loop spawned plan-critic + 4 staff-review lenses but DID NOT spawn `/flow:security-review` + `/flow:accessibility-review`. Skipped by author judgment ("they'd early-exit on docs-only anyway"). User caught: "were the ship reviews run?" — they hadn't been. **This is itself the FB-0010 silent-skip class applied to workflow discipline (not code).** The 9th FB-0010 incident, and a new sub-class (workflow-step-skip vs code-edge-skip). Per workflow.md Step 10 (the "Never bypass `/flow:ship`" subsection added by PR I — formerly framed under Step 6 in pre-PR-I plan prose) + FB-0008/FB-0033, the discipline is to ALWAYS spawn the reviewers — they produce a `STATUS: SKIPPED` log line in the session transcript as evidence the discipline ran, NOT silent-skip the spawn itself. Make-good: ran both retroactively (security: STATUS SKIPPED no source/config in diff; a11y: STATUS SKIPPED no UI in diff). Defense: `/flow:ship` Step 1.0 already prints the workflow-step assumption surface (which lists security/a11y). Strengthen that surface to either (a) auto-spawn the reviewers if missing or (b) require an explicit author confirmation that they ran. Owner: domain. Horizon: PR H proper or next `/flow:ship`-touching PR. Promote at next /flow:ship feedback synthesis since this is now a 3rd-time-recurring discipline shape: PR F-pass-1 (gawk-only awk = portability silent-skip), PR H1 zsh-vs-bash (word-splitting silent-skip), PR H1 workflow-spawn-skip (judgment silent-skip).

---

## PR E+ follow-ups from PR D review

PR D's lens dogfood (staff-engineer + security combined) caught 2 BLOCKERs + 2 NITs (all fixed in-tree) + 2 FOLLOW-UPs routed here:

1. **Structured exit-status marker for `/flow:*review` early-exit vs clean-run.** PR D's early-exit uses `exit 0` + a `STATUS: SKIPPED — ...` stdout line as a soft marker. When `/flow:ship` Step 2 invokes the reviewers via `Skill('flow:security-review')`, the orchestrator can't programmatically distinguish "skipped — no source files" from "ran, no findings." Both are exit 0. A structured final-line marker (`STATUS: SKIPPED` / `STATUS: CLEAN` / `STATUS: FINDINGS`) would let `/flow:ship` audit-trail what actually ran. PR D adds the `STATUS: SKIPPED` line in the early-exit path; symmetric `STATUS: CLEAN` / `STATUS: FINDINGS` for the substantive paths is the v1.3+ enhancement. Owner: domain agent. Horizon: PR E or post-extraction.

2. **Pattern-injection RCE confirmed safe (informational, no action).** PR D security lens explicitly verified that `grep -E "$PATTERN"` from a flow.config.json-sourced regex does NOT have command-injection surface — `grep` treats the arg as a POSIX ERE, not a shell expression; shell metas land as regex metachars or grep fails outright. Per FB-0004 trust model (flow.config.json = project-owned, package.json-tier trust), this is the correct posture. Captured here as audit-trail evidence; no code change.

---

## PR D+ follow-ups from PR C review

PR C's lens dogfood (staff-engineer + push-further combined) caught 1 BLOCKER + 2 NITs (all fixed in-tree) + 1 FOLLOW-UP routed here:

1. **Surface-AFTER variant of `/flow:ship` Step 1.0 workflow-step assumption block.** PR C ships the surface-BEFORE form (informational pre-flight; zero new infrastructure, prints what's ASSUMED to have run). The richer signal — what ACTUALLY ran — would come from a post-ship "Workflow steps actually executed this session" summary derived from session-transcript scan. Higher-signal than surface-before but requires session-introspection helper that doesn't exist yet. Ship the cheap form (PR C); add this as a v1.3+ enhancement when a session-introspection helper lands. Owner: domain agent. Horizon: post-extraction v1.3.

### Additional FOLLOW-UPs from PR C **full-review re-pass** (4-parallel lens spawn matching the canonical /flow:staff-review pattern)

Per user direction, ran the canonical 4-parallel pattern (engineer + push-further + security + plan-critic + audit-completion) instead of the combined-lens shortcut used in the initial PR C review. Caught 1 BLOCKER + 1 NIT + 2 MEDIUM (audit) — all fixed inline — plus 4 new FOLLOW-UPs:

2. **Single-principle "skips compound" preamble in workflow.md** (push-further roadmap-concrete). PR C adds "even on docs-only ones" qualifier at Step 2 AND Step 6 — both restate the same FB-0008/FB-0033 lesson. A single principle near the top (e.g., a "Discipline" preamble after the 11-step list) cited from Step 2 + 6 would be tighter and prevent the next docs-only qualifier (security, a11y, ship-spike) from spawning a third copy. Horizon: next workflow.md-touching PR.

3. **Cross-repo provenance one-liner inside /flow:ship Step 1.0 emitted block** (push-further roadmap-concrete). Current block cites "FB-0033-style discipline" only in the prose AROUND the verbatim emit. Surfacing "(dogfood-driven: md-manager FB-0033 + flow FB-0008)" inside the printed block would let consumers know this is real burned-cost lesson, not arbitrary nagging. Reduces "why is this here" friction. Horizon: same as #2.

4. **Stacked-PR plan-noting convention** (plan-critic INTERNAL-INCOHERENCE FOLLOW-UP). When PRs chain off each other for review (B branched off A; C off B; D off C; E off D), the per-PR plan's "Files touched" list will appear to mismatch the actual PR diff (which contains stacked content from earlier PRs in the chain). Future stacked-PR plans should note "this is the C slice of a stacked A+B+C PR" so reviewers can map the file list correctly. Horizon: convention update in workflow.md or plan-template; trigger on next stacked-PR sequence.

5. **`/plugin marketplace list` output-shape eval test** (audit-completion MEDIUM #2). The `^flow` anchor in PR C's verify recipe depends on marketplace-list outputting names at column 0 with no leading bullet/indent/glyph. Today's behavior matches; a Claude Code version change could break it silently. Add a regression fixture under `plugins/flow/evals/security/test_marketplace_list_format.py` paralleling the existing fixture shape — assert that `claude --print "/plugin marketplace list" 2>&1 | head -5` returns names at column 0 (or the test fails with a clear "output format changed; update bootstrap.md grep recipe" message). Cheap; one-shot. Bootstrap.md now documents this assumption inline so consumers can adjust without grepping the eval. Horizon: PR D or E.

---

## PR C+ follow-ups from PR B review

PR B's Phase 7 dogfood (staff-engineer + simplify + security combined lens against the stale-base preflight implementation) caught 2 BLOCKERs + 2 NITs (all fixed in-tree) + 1 FOLLOW-UP routed here:

1. **Eval fixture for the stale-base gate.** Test cases: (a) current branch passes silently; (b) stale branch blocks with expected stderr + exit 1; (c) no `refs/remotes/origin/HEAD` configured + no `flow.config.json` → resolves to literal `main`; (d) `flow.config.json.defaultBranch = "trunk"` + no remote HEAD → resolves to `"trunk"`. Both empirical-smoke cases (c) + (d) were verified manually during PR B Phase 9 iteration, but no regression fixture protects them. Would have caught both BLOCKERs PR B's lens flagged (empty-DEFAULT_BRANCH degenerate; cross-shell variable scope). Owner: testing agent. Horizon: PR C or D. Place under `plugins/flow/evals/security/test_stale_base_check.py` paralleling the existing `test_cwd_constraint.py` + `test_malicious_config.py` shape (assert-on-exit-code + assert-on-stderr).

---

## PR 4+ follow-ups from PR 3 review

PR 3's Phase 7 dogfood (3 parallel lens agents — engineer+simplify combined + push-further + security; skipped UX-designer + design-engineer + accessibility with reason: doc/template surface, no UI) caught 4 BLOCKERs + 9 NITs + 4 FOLLOW-UPs. BLOCKERs + NITs fixed in-tree. FOLLOW-UPs routed here:

1. **Preflight script library across 3 stacks** (engineer FOLLOW-UP). web/check.mjs and tauri/check.mjs share ~80% structure (`loadConfig`, `runGate`, GATES summary, exit-code handling). A shared helper module would let stack-specific gates be the diff. Defer to a "preflight library" PR if/when a 4th stack lands; today the divergence is borderline. Owner: domain agent. Horizon: when adding stack #4 (rust-only, python, go) OR when an existing stack's preflight needs a behavior change that has to land in all three.

2. **`$comment-*` keys in flow.config.json.example are janitorial overhead** (push-further inline-cheap, deferred for design discussion). Replacing them with a sibling `flow.config.example.md` cheat-sheet was suggested. Counter-argument: putting docs in a separate file means the consumer holds two files in their head during bootstrap. Hold the existing pattern until PR 4 dogfood confirms or refutes the friction. If md-manager's PR 4 agent flags it, redesign in v1.3.

3. **Collapse bootstrap's 6 steps to 4** (push-further inline-cheap, deferred for design discussion). Merging install+copy and verify+smoke-PR was suggested. Today the 6-step shape mirrors what an adopter actually does (each step has a different verification). PR 4 dogfood will surface whether the step count feels heavy in practice.

4. **Ship `template/bootstrap.sh` shim** (push-further inline-cheap, deferred for design discussion). One-command bootstrap (`./bootstrap.sh --stack web` does Steps 2+3 in one invocation) was suggested. Real value, but the cp ladder doubles as documentation of WHAT the script would do. v2.0+ roadmap already lists `/flow:init` skill as the canonical answer; ship the shim ALONGSIDE that work to avoid two scaffolding paths competing.

5. **Swift preflight unquoted `$WORKSPACE_OR_PROJECT` word-split** (security NIT). `WS=$(ls *.xcworkspace | head -n1)` then used unquoted via shellcheck-disable so xcodebuild gets two args. Filename with space breaks; filename with shell metas could in theory exec. Repo-owner-controlled, so not a real attack surface. Fix: use bash array `WS_ARGS=(-workspace "$WS")` then `xcodebuild "${WS_ARGS[@]}"`. Horizon: PR 4 or when first swift consumer touches the file.

---

## PR 3+ follow-ups from PR 2 review

PR 2's Phase 7 dogfood (4 parallel lens agents + security review on PR 2's own diff) caught 2 BLOCKERs + 11 cheap NITs (all fixed in-tree) + 8 FOLLOW-UPs (routed here):

1. **Eval coverage for cwd-constraint rejection path** (security lens). `extract_session.py`'s `allow_external_paths=False` default needs a regression fixture covering (a) symlink resolution under cwd, (b) `..` glob expansion, (c) absolute `--reference-paths` rejection, (d) `--allow-external-paths` opt-out. The constraint is a 30-line block in a 600-line file; future refactor could regress it silently. Owner: testing agent. Horizon: next reviewer-touching PR (could land in PR 3 or as a quick follow-up flow PR). Add fixtures under `plugins/flow/evals/fixtures/cwd-constraint/`.

2. **Eval fixture for malicious-flow.config.json injection probe** (security lens). The `jq -r` + quoted-args pattern in skill `!<cmd>` blocks is correct today, but no fixture asserts that `flow.config.json` with shell metas in `referenceGlob`, `defaultBranch`, `typecheckCmd` is handled without command execution. One-line test would prevent silent regression. Horizon: PR 3.

3. **Memory tool `validateMemoryDir` should `realpath` before prefix check** (security lens). Currently `Path.resolve()` collapses `..` but doesn't follow symlinks. Limited threat surface today (script only LISTS filenames; doesn't read contents). Revisit when `check.mjs` ever starts reading entry contents. Recommended fix when revisited: `realpathSync` before `startsWith(projectsRoot + '/')` check.

4. **Single-source slot documentation** (push-further roadmap-concrete). Slot semantics duplicated across `flow.config.schema.json` (description fields), `workflow-help/SKILL.md` (slot table), `plugins/flow/docs/workflow.md` (slot table), and per-skill "Config slots used" tables. Will drift the first time a slot's behavior changes and someone updates 3 of 4. Pick schema as canonical; generate the others at release time, OR replace prose tables with a one-line pointer. Horizon: v1.2.

5. **Loud-warning copy deduplication** (UX lens FOLLOW-UP). The `⚠️ flow.config.json.<slot> not set; ...` string appears verbatim in 5 skills. If wording evolves (e.g., add schema link), it's 5 edits. Extract to a single doc snippet referenced by `${CLAUDE_PLUGIN_ROOT}/docs/...`. Horizon: v1.2.

6. **workflow-help vs README cheat-sheet duplication** (UX lens FOLLOW-UP — recurring; PR 1 review flagged the same shape for README+workflow.md). Workflow-help SKILL output overlaps the README cheat-sheet. Confirm side-by-side; decide canonical surface (probably README points at `/flow:workflow-help`, since the latter substitutes resolved project context). Horizon: next docs-touching PR.

7. **workflow-help craft asymmetry vs flow's own preached doctrine** (push-further EXPLORATION). The plugin asks consumers to hold themselves to "uncommon care" but its own front door (`/flow:workflow-help`) is "comprehensive reference." Could be a one-line aphorism per step, a "what flow gives you / what flow asks of you" contract, or similar. Surfaces when: anyone edits `plugins/flow/skills/workflow-help/SKILL.md` or `plugins/flow/docs/workflow.md`.

8. **Fallback message tone for missing project docs** (UX lens EXPLORATION). All 5 review skills emit `(no spec doc at $SPEC)` etc. when a doc is missing. Reads like shell output. Friendlier shape might be `Spec doc: not configured — set flow.config.json.specPath to enable spec-grounded review`. Surfaces when: a consumer reports the messages feel cryptic, OR when adding a new review skill (rule the tone in then).

## Per-stack memory-tool foreign-cwd verification

Routed for **PR 4 dogfood** (md-manager extraction umbrella): the `check.mjs` `deriveMemoryDir()` falls back to `~/.claude/projects/<slug-of-cwd>` when no project-name match exists under `~/.claude/projects/`. For consumers using flow at user-scope from a cwd that doesn't match any existing slug, this creates a separate memory dir per worktree — which the harness won't auto-load. Already documented in pr2-flow-plan.md's confidence verdict; surface as a real follow-up entry once md-manager PR 5 dogfoods.

## PR 2 follow-ups from PR 1 review

The walk-through-the-loop review on PR 1 surfaced two findings that are out-of-scope for PR 1 but in-scope for PR 2. Quoted here verbatim so PR 2's planner doesn't have to re-derive them:

1. **Consumer-vs-flow path divergence in critique-plan default.** `plugins/flow/skills/critique-plan/SKILL.md:13` hardcodes `--reference-glob "core-docs/*.md"`. When flow runs `/flow:critique-plan` on itself (which uses `dev-docs/` not `core-docs/`), the plan-critic sees zero reference docs. The fix is a `flow.config.json.referenceGlob` slot that the SKILL reads at invocation, with the documented default chain (consumer projects: `core-docs/*.md`; flow's own repo: `dev-docs/*.md`). PR 2's `flow.config.schema.json` work picks this up. Cost: ~10 min once the config-slot machinery exists.

2. **`extract_session.py --reference-paths` accepts arbitrary host paths.** Currently, `gather_reference_docs` reads any absolute path the caller passes; output is injected verbatim into the auditor subagent's context. In the current invocation chain, the caller is the `critique-plan` SKILL with a hardcoded glob, so consumer input never reaches it. But if a future skill or recipe ever forwards user-controlled paths, an attacker could exfil file contents (e.g., `~/.ssh/config`) into the subagent's prompt and out via tool output. Constrain to `cwd` (reject resolved paths outside `Path.cwd()`) unless an explicit override flag says otherwise. Document the trust model in the script docstring. Pairs naturally with PR 2's path-validation rule baseline (`plugins/flow/hooks/default-hooks.json`).

## Active Work Items

### Consumer-feedback follow-ups (PRs A-E, sequential) — driven by md-manager PR 4 report 2026-05-25

5 small focused PRs absorbing md-manager's first-real-consumer dogfood findings. FB-0005 through FB-0009 + 1 EXPLORATION (rule-of-three close-out skill) captured in PR A's intake. Each PR runs the workflow loop (plan → execute → preflight → /flow:staff-review or lens emulation → /flow:ship pipeline → open PR; user merges).

**Canonical priority sequence + one-liner per PR:** see [`dev-docs/roadmap.md`](roadmap.md) § Now. The per-PR plans below carry the detailed scope, spec-walk, and confidence verdicts; roadmap.md is the single source of truth for "what's the order + what's next."

#### PR A — Consumer feedback intake (docs-only; in flight on `pr-a/consumer-feedback-intake`)

**Mode:** feature (small)
**Goal:** Capture md-manager's PR 4 consumer-feedback report as canonical flow `dev-docs/` artifacts before any implementation work begins. Closes the cross-repo signal loop (consumer flagged → captured → addressable).

**Scope (in):**
- Create `dev-docs/roadmap.md` with format header + Now / Next / Later / § Exploration sections. Flow has been deferring this since v1.0.0; right moment to land it (matches the consumer-template convention flow ships in PR 3).
- Add 5 FB entries to `dev-docs/feedback.md` (FB-0005 through FB-0009) covering the 5 rough edges from the consumer report. Each entry: source, what-was-said, synthesized rule, applies-to, validation.
- Add 1 EXPLORATION entry to `dev-docs/roadmap.md` § Exploration covering the rule-of-three `flow:close-out` skill abstraction observation (don't extract yet — wait for a fourth instance).
- Update plan.md: Current Focus advances to "PRs A-E sequenced"; Handoff Notes refreshed for post-PR-3 state; PR A-E Active Work Item block added.

**Scope (out):** Any code changes to plugin artifacts (PR B+ does that). The Workflow discipline lesson from md-manager FB-0033 (workflow.md should reinforce "don't skip even on docs-only") routes to PR C, not PR A.

**Spec-walk:**
- [ ] `dev-docs/roadmap.md` exists with the 4-section structure (Now / Next / Later / § Exploration) + the rule-of-three EXPLORATION entry.
- [ ] `dev-docs/feedback.md` has 5 new entries (FB-0005 through FB-0009) per the documentation rule schema; each cites the consumer report as source.
- [ ] `dev-docs/plan.md` Current Focus + Handoff Notes reflect the new state; PR A-E block added under Active Work Items.
- [ ] No edits to `plugins/flow/*`, `template/*`, `docs/*`, `evals/*` (verify via `git diff --name-only origin/main..HEAD` returning only `dev-docs/` paths).
- [ ] `claude plugin validate .` exits clean (sanity).

**Confidence verdicts:**

**Assumption:** Creating `dev-docs/roadmap.md` now (rather than deferring to a "roadmap initialization" PR) is the right moment because PR A has a real EXPLORATION entry to land + flow has been deferring this since v1.0.0 with no cost.
**Confidence:** HIGH
**Why:** Empty roadmap.md would be busy-work; one with a real entry is canonical reference material.
**If it flips:** EXPLORATION moves to `dev-docs/plan.md` "Backlog" section instead. Single-file revert.

**Assumption:** FB-0005 through FB-0009 numbering doesn't collide with any in-flight session writing to feedback.md.
**Confidence:** HIGH
**Why:** Single-author repo; no in-flight concurrent FB-writing session.
**If it flips:** Renumber at commit time; non-architectural.

**Risks:** none material — purely additive docs.

**Files touched:** `dev-docs/roadmap.md` (new), `dev-docs/feedback.md` (5 entries added), `dev-docs/plan.md` (Current Focus + Handoff Notes + new Active Work Item block).

#### PR B — Stale-base preflight in `/flow:ship` Step 1 (queued)

**Mode:** feature (small) | **Priority: highest**
**Goal:** Add a mechanical preflight check that prevents the stale-base BLOCKER class md-manager PR 4 burned 4 lens spawns surfacing. FB-0008 captures the rule + pattern.

**Scope (in):** `plugins/flow/skills/ship/SKILL.md` Step 1 — add `git fetch origin --quiet` + `git merge-base --is-ancestor` check; exit 1 with clear stderr message if branch is behind. Mirror same check into `/flow:ship-spike` Step 1 and `/flow:staff-review` Step 1 (both also diff-vs-default-branch consumers).

**Scope (out):** Auto-rebasing on detection. Stale-base detection is the gate; the fix is the user's call.

**Spec-walk:**
- [ ] All 3 skills (`ship`, `ship-spike`, `staff-review`) have the stale-base check at Step 1, before any expensive operation.
- [ ] Check uses `flow.config.json.defaultBranch` with 3-tier fallback chain (matches PR 1 locked idiom).
- [ ] `git fetch origin --quiet` precedes the check (otherwise it tests against a stale local view).
- [ ] Error message names the gap (`(current HEAD: X; base needs N commits)`) so the user knows what's needed.
- [ ] `claude plugin validate .` clean.
- [ ] Smoke test: forge a stale branch in `/tmp/`; verify `/flow:ship` exits 1 with the expected message.

**Confidence verdicts:**

**Assumption:** Forced-update / shallow-clone consumers won't hit false positives from the `merge-base --is-ancestor` check.
**Confidence:** HIGH
**Why:** `git fetch origin` brings the remote ref current; `is-ancestor` is the standard idiom. Shallow clones fail-soft (no ancestry info = treats as ancestor).
**If it flips:** Add `--depth=1` aware fallback (`git rev-parse origin/<branch> 2>/dev/null` first). Surface at smoke time.

**Files touched:** `plugins/flow/skills/{ship,ship-spike,staff-review}/SKILL.md`.

#### PR C — Marketplace install verification + `/flow:ship` assumption surfacing (queued)

**Mode:** feature (small) | **Priority: high**
**Goal:** Two related fixes pairs into one PR. Address FB-0005 (marketplace-key-mismatch install docs gap) by adding a verification step to `docs/bootstrap.md` + `docs/migration.md`. Address the workflow discipline lesson (md-manager FB-0033 cross-project applicability) by making `/flow:ship` print which workflow steps it assumes have already run.

**Scope (in):**
- `docs/bootstrap.md` Step 1 + `docs/migration.md` Stage 1: add `/plugin marketplace list | grep '^flow'` verification step after install, with fallback instruction to re-run `/plugin marketplace add by-dev-tools/flow` if absent. Document the rename-causes-stale-key class of issue.
- `plugins/flow/skills/ship/SKILL.md` Step 1: print "ASSUMES: /critique-plan ran during plan; /simplify ran post-commit; /flow:staff-review ran with substantive output or explicit N/A per lens. Skips become visible at the next ship." Single-line; doesn't gate, just surfaces.
- `plugins/flow/docs/workflow.md` Step 6 + Step 2 sub-step: add "even for docs-only diffs" qualifier per workflow discipline (a) recommendation from the consumer report.

**Scope (out):** A `flow:doctor` skill (deferred; workflow discipline (b)). The doc fix + assumption-surfacing is enough behavior change to test the discipline; doctor is v1.2+ if discipline doesn't change.

**Spec-walk:**
- [ ] `docs/bootstrap.md` + `docs/migration.md` have the marketplace-name verification step at install-time.
- [ ] `plugins/flow/skills/ship/SKILL.md` Step 1 prints the workflow-step assumption list.
- [ ] `plugins/flow/docs/workflow.md` Step 6 + Step 2 have the "even for docs-only" qualifier.
- [ ] `claude plugin validate .` clean.

**Files touched:** `docs/bootstrap.md`, `docs/migration.md`, `plugins/flow/skills/ship/SKILL.md`, `plugins/flow/docs/workflow.md`.

#### PR D — Per-diff non-UI early-exit (paired in `/flow:security-review` + `/flow:accessibility-review`) (queued)

**Mode:** feature (medium) | **Priority: medium**
**Goal:** Pair FB-0006 + FB-0007. Both reviewers should detect "no relevant files in diff" at Step 1 and early-exit cleanly, saving spawn cost on docs-only PRs.

**Scope (in):**
- `plugins/flow/skills/security-review/SKILL.md` Step 1: add per-diff source-file detection (`git diff <base>..HEAD --name-only | grep -E ...`). If empty, emit "[security-review] no source/config files in diff; skipping." and exit 0.
- `plugins/flow/skills/accessibility-review/SKILL.md` Step 1: add per-diff UI-file detection, AND in addition to the existing `uiSurface=false` project-wide gate. Same shape as security-review.
- `plugins/flow/schema/flow.config.schema.json`: add two optional slots (`sourceFilePatterns`, `uiFilePatterns`) for projects with non-standard file layouts (e.g., monorepos). Defaults documented inline.
- `plugins/flow/.claude-plugin/plugin.json` + `.claude-plugin/marketplace.json`: bump metadata.version + plugin version to v1.2.1 (additive patch — no breaking changes). Update description text to reflect the new slot count (14 → 16) + the per-diff early-exit behavior.

**Scope (out):** Restructuring the reviewers to take diff-paths as inputs (today they read from disk; the early-exit checks the path list but the reviewer itself still works as-is).

**Spec-walk:**
- [ ] Both reviewers' Step 1 has per-diff detection wired.
- [ ] Schema has 2 new slots with defaults + examples; consumers exist (the reviewer skills read them).
- [ ] No false-positive on a real source-touching PR (smoke: stage a single `src/foo.ts` edit; verify both reviewers proceed without early-exit).
- [ ] Manifest version + slot count reflected (note: doesn't necessarily bump major.minor; this is a 1.2.x patch since it's additive).
- [ ] `claude plugin validate .` clean.

**Files touched:** `plugins/flow/skills/{security-review,accessibility-review}/SKILL.md`, `plugins/flow/schema/flow.config.schema.json`, `.claude-plugin/marketplace.json`, `plugins/flow/.claude-plugin/plugin.json`.

#### PR E — `gh` CLI fail-fast check (queued)

**Mode:** feature (small) | **Priority: low**
**Goal:** FB-0009. Add `command -v gh` check at `/flow:ship` Step 1, `/flow:staff-review` Step 1, `/flow:ship-spike` Step 1. Emit install hint + exit 1 if absent rather than exit 127 at invocation site.

**Scope (in):**
- 3 SKILL.md edits adding the `command -v gh` check.
- `docs/bootstrap.md` Step 1 + `docs/migration.md` Stage 1: document `gh` as a prerequisite alongside `claude` + `node` + `jq`.

**Spec-walk:**
- [ ] All 3 skills' Step 1 has the gh-CLI check.
- [ ] Install hint message includes both macOS (`brew install gh`) and the generic URL.
- [ ] Both bootstrap + migration docs name `gh` in the prereq list.
- [ ] `claude plugin validate .` clean.

**Files touched:** `plugins/flow/skills/{ship,staff-review,ship-spike}/SKILL.md`, `docs/bootstrap.md`, `docs/migration.md`.

---

### PR 3 — Template directory + bootstrap docs + absorb PR-2 follow-ups (SHIPPED — awaiting merge)

**Mode:** feature
**Branch:** `pr3/template-directory` (off `main` after PR 2 squash `3409103`)
**Goal:** Ship the consumer-side scaffolding so a new project can adopt flow in ~10 minutes per `docs/bootstrap.md`. Cover the three stacks documented in the umbrella plan (web / swift / tauri-rust-ts). Provide `docs/migration.md` for existing projects (md-manager being the upcoming case in PRs 4-6). Absorb PR 2's two follow-up eval fixtures (cwd-constraint + malicious-config injection) since PR 3 is touching the eval surface anyway. Manifest bump v1.1.0 → v1.2.0.

**Scope (in):**
- `template/base/` — Tier 1 (required: CLAUDE.md.template, flow.config.json.example, .claude/settings.json.example, .claude/rules/safety.md.template, README.md.template, .gitignore.template) + Tier 2 (recommended-but-shippable-empty: core-docs/{spec,plan,roadmap,history,feedback}.md scaffolds with format headers).
- `template/stacks/web/` — Vite/React/TS stack: `tools/preflight/check.mjs` (npm typecheck + build + test), `.claude/skills/link/SKILL.md` (vite dev server), `.claude/rules/{ui,dev-server}.md`, `.github/workflows/ci.yml` (Node CI), `.gitignore.append` (web-stack entries).
- `template/stacks/swift/` — `tools/preflight/check.sh` (xcodebuild + xcodebuild test + swift-format lint), `.claude/rules/safety.md.append` (.xcodeproj/.xcworkspace edits), `.github/workflows/ci.yml` (macOS runner + Xcode action), `.gitignore.append` (DerivedData, xcuserdata).
- `template/stacks/tauri-rust-ts/` — `tools/preflight/check.mjs` (npm typecheck + build + cargo fmt --check + cargo clippy -D warnings + cargo test), `.claude/skills/link/SKILL.md` (tauri dev), `.claude/rules/ui.md`, `.github/workflows/ci.yml` (Node + Cargo), `.gitignore.append` (target/, src-tauri/target).
- `docs/bootstrap.md` — step-by-step adoption for a NEW project (per stack: which template/base files to copy, which stack overlay to merge, how to fill placeholders, how to install plugin, how to validate `flow.config.json`).
- `docs/migration.md` — adoption for an EXISTING project with `.claude/` content (md-manager case): the additive-then-replace pattern, what to keep project-shaped (safety.md, ui.md, link/, project skills) vs delete (workflow skills, generic rules, planner+docs, memory tool).
- PR-2 FOLLOW-UPs absorbed:
  - `plugins/flow/evals/fixtures/cwd-constraint/` — fixtures covering symlink-into-cwd (accepted), `..` glob expansion (rejected), absolute `--reference-paths` (rejected with explicit stderr), `--allow-external-paths` opt-out (accepted). Wire into `evals/run_evals.py` or add a separate `evals/run_security_evals.py` if the existing harness shape doesn't fit security-class tests.
  - `plugins/flow/evals/fixtures/malicious-config/` — fixture: `flow.config.json` with shell metas in `referenceGlob`, `defaultBranch`, `typecheckCmd`. Asserts no command execution; values land as opaque strings into their consumer skills.
- Manifest bump in both `.claude-plugin/marketplace.json` (metadata.version + plugin version) and `plugins/flow/.claude-plugin/plugin.json`: 1.1.0 → 1.2.0. Description updated to mention "template directory + bootstrap docs."

**Scope (out):**
- md-manager-side changes (PRs 4-6).
- Other PR-2 FOLLOW-UPs not tagged for PR 3 (items 3-8 in the FOLLOW-UPs section above stay deferred).
- `/flow:init` auto-bootstrap skill (v2.0+ per post-extraction roadmap).
- v1.x+ post-extraction features.

**Locked patterns from PR 1 + PR 2 (still binding):**
- Templates use `{{PLACEHOLDER}}` syntax for fill-in slots (CLAUDE.md.template, README.md.template, safety.md.template).
- All shell command examples in template files use `sh -c "$VAR"`, never `eval "$VAR"`.
- Per-stack preflight scripts print loud `⚠️` warnings for any unset config slot, never silently no-op.
- Default-branch resolution in template-shipped scripts uses the 3-tier fallback chain.
- Cross-file refs in template SKILL.md files (only `link/` ships in templates) use `${CLAUDE_PLUGIN_ROOT}` ONLY for plugin-shipped paths; consumer-side relative paths are fine.
- No md-manager-specific tokens in template artifacts.

**Phased execution (each ends with one commit; per-phase verifiable success criteria):**

- **Phase 1 — Plan + consumer-model read.** Read schema (13 slots, defaults). Survey md-manager (the reference web consumer) for actual npm scripts, settings.json shape, .gitignore. Done. **Success:** schema slots enumerated; web-stack defaults validated against md-manager actuals.
- **Phase 2 — `template/base/` (Tier 1 + Tier 2).** 8 files. **Success:** all 8 files exist; placeholders use `{{NAME}}` syntax consistently; flow.config.json.example parses with jq; settings.json.example parses; no md-manager tokens.
- **Phase 3 — 3 stack overlays.** ~15 files total. **Success:** each stack has at least preflight + CI workflow + .gitignore.append; preflight scripts have node --check / shellcheck clean (where applicable); CI yamls parse with yq/python-yaml.
- **Phase 4 — `docs/bootstrap.md` + `docs/migration.md`.** **Success:** bootstrap covers all 3 stacks; migration explicitly names the keep-vs-delete file lists matching the md-manager spec; both docs reference template paths that exist.
- **Phase 5 — Absorb 2 PR-2 FOLLOW-UPs.** **Success:** cwd-constraint fixture rejects out-of-cwd path with non-zero exit + explicit message; malicious-config fixture asserts shell-meta values pass through as strings; both wired into the eval harness.
- **Phase 6 — Bootstrap verification.** In `/tmp/`, follow `docs/bootstrap.md` for the web stack from scratch. Optional smoke for swift + tauri (full bootstrap may need a real Mac/Rust env). **Success:** web bootstrap produces a working project with `claude --plugin-dir <flow> --print "/flow:workflow-help"` returning the expected output; `claude plugin validate` clean against the bootstrapped project.
- **Phase 7 — Dogfood PR 3 via `/flow:staff-review` + `/flow:security-review`.** Skills exist on main now (PR 2 shipped them). Spawn lens agents via Agent tool with `subagent_type: lens-*`. Triage; apply BLOCKER + cheap NIT inline; route FOLLOW-UPs. **Success:** at least 3 of 4 lenses ran (a11y likely skipped via uiSurface=false); all BLOCKERs fixed; FOLLOW-UPs routed.
- **Phase 8 — `/flow:ship` + manifest bump + open PR.** Run the pipeline; bump to v1.2.0; verify md-manager spec accuracy (no changes expected — PR 3 is consumer-side); push; open PR; never merge. **Success:** PR open against main; MERGEABLE; PR body documents 8 phases; md-manager spec re-verified.

**Confidence verdicts:**

- **Three stack overlays are sufficient for v1.2.0 coverage.** HIGH. Web + swift + tauri match the umbrella's stated targets. Other stacks (python, go, rust-only) defer to v1.3+.
- **`docs/bootstrap.md` is testable from scratch in `/tmp/` for the web stack.** HIGH. Node + npm are universally available.
- **Swift + tauri bootstrap verification may be smoke-only** (no full Xcode/Rust env in this session). MEDIUM. Mitigation: document the assumption in the bootstrap docs; consumer reports become PR 3+ FOLLOW-UPs.
- **PR-2 FOLLOW-UP eval fixtures slot cleanly into the existing harness.** MEDIUM. The existing `evals/run_evals.py` runs against jsonl session fixtures for the auditor; security-class tests (assert-no-shell-execution) need a different shape. Likely add a separate `evals/run_security_evals.py` (or skip the harness wiring and ship as standalone Python smoke tests under `evals/fixtures/cwd-constraint/test.py`). Decide at Phase 5.
- **Manifest bump to v1.2.0 is additive (no breaking changes).** HIGH. Templates are consumer-pulled, not plugin-pushed.

**Risks:**
- Stack-overlay scope creep — keep each overlay to ~5 files, defer "everything a stack might need" to consumer fork.
- Migration doc accuracy depends on md-manager's actual state at PR 4 time — keep it general where possible, point at md-manager-pr4-6-spec.md for specifics.
- Bootstrap verification in `/tmp/` requires `claude` CLI access from the shell — confirmed available (used in PR 1 + PR 2 smoke tests).

**Files touched (anticipated):**
- New under `template/base/`: 8 files (Tier 1 + Tier 2)
- New under `template/stacks/web/`: 5 files
- New under `template/stacks/swift/`: 4 files
- New under `template/stacks/tauri-rust-ts/`: 5 files
- New under `docs/`: `bootstrap.md`, `migration.md`
- New under `plugins/flow/evals/fixtures/`: 2 fixture dirs (cwd-constraint, malicious-config)
- Modified: `.claude-plugin/marketplace.json`, `plugins/flow/.claude-plugin/plugin.json` (v1.2.0); `dev-docs/{history,plan,feedback}.md` (Phase 8 synthesis); possibly `plugins/flow/evals/run_evals.py` or new `evals/run_security_evals.py`.

### PR 2 — Workflow surface backfill (SHIPPED — awaiting merge)

**Mode:** feature
**Branch:** `pr2/workflow-backfill` (off `docs/pr2-handoffs`)
**Canonical plan:** [`dev-docs/handoffs/pr2-flow-plan.md`](handoffs/pr2-flow-plan.md). 8 phases, per-phase verifiable success criteria, 6 confidence verdicts, 6 risks, ~24 files. User direction: execute autonomously, self-grade against success criteria, follow the workflow being implemented at each stage.

**Phase 1 status (complete):** all 12 md-manager sources fetched to `/tmp/pr2-sources/` (sizes match estimates ±2%). Source-read observations refining the handoff plan:
- Staff-review extraction (Phase 3-4): md-manager uses `subagent_type: Explore` with inline prompts; PR 2 changes to `subagent_type: lens-*` with extracted agent files. Structural change confirmed MEDIUM. Fallback documented.
- Security/a11y reviews: heavier md-manager-specific token references than handoff anticipated (`--sand-9`, `--page-text-quiet`, "markdown-notes app"). De-projection effort scaled accordingly.
- All 4 skills start step numbering at 0 (same off-by-one PR 1's `/flow:ship` had). Apply PR-1 NIT fix (start at 1) across all ports.
- `ship-spike` references non-existent `tools/preflight/check.mjs` — port keeps as a config-slot opportunity (consumer-side preflight is project-specific per consolidation doc Decision 1).

Execution proceeds through Phases 2-8 per the handoff.

### PR 1 — Flow plugin restructure + initial workflow surface (SHIPPED — awaiting merge)

Status: all spec-walk checkboxes complete; PR opened at [by-dev-tools/flow#5](https://github.com/by-dev-tools/flow/pull/5); walk-through-the-loop review pass surfaced 3 BLOCKERs + 2 cheap NITs, all fixed in follow-up commit `65a0a58`; plan-critic retroactive verdict APPROVED; recovery anchor at git tag `pre-flow-plugin`. Full history entry in `dev-docs/history.md`. Original plan spec-walk preserved below for reference.

---

**Mode:** feature

**Goal:** Move existing root-level plugin content into `plugins/flow/*`, rename `llm-auditor` / `assumption-auditor` identifiers to `flow` (both marketplace name and plugin name), bump to v1.0.0, add `/flow:ship` skill (ported from md-manager via the locked /ship port table — 3a/3b split, loud-warning pattern, default-branch discovery, config-slot doc paths) and `plugins/flow/docs/workflow.md` (canonical 11-step loop, de-projected), rename this repo's `core-docs/` to `dev-docs/` to match the consumer-vs-plugin convention. The result is an installable v1.0.0 `flow` plugin whose marketplace shape matches Anthropic's pattern and whose own dev-tracking is cleanly separated from the plugin artifacts it ships.

**Scope (in):**
- Create recovery tag `pre-flow-plugin` against current HEAD (`8857ebd`) and push it. Brief calls this the recovery anchor; it doesn't exist yet.
- Restructure plugin artifacts via `git mv` (preserve history):
  - `agents/{auditor,plan-critic}.md` → `plugins/flow/agents/`
  - `skills/{audit-plan,audit-completion,critique-plan,log-disagreement}/SKILL.md` → `plugins/flow/skills/`
  - `scripts/{extract_session,bounding_logic,log_disagreement}.py` → `plugins/flow/scripts/`
  - `evals/{ground_truth.yaml,run_evals.py,fixtures/}` → `plugins/flow/evals/`
  - `DISAGREE.md` → `plugins/flow/DISAGREE.md`
- Rename `.claude-plugin/marketplace.json`: marketplace `name` `llm-auditor` → `flow`; plugin `name` `assumption-auditor` → `flow`; plugin `source` `./` → `plugins/flow`; add `metadata.pluginRoot: "./plugins"`; update `homepage`/`repository` URLs to `https://github.com/by-dev-tools/flow`; bump marketplace `metadata.version` and plugin `version` to `1.0.0`; expand `description` to reflect the workflow scope.
- Rename `.claude-plugin/plugin.json`: `name` `assumption-auditor` → `flow`, `version` `0.3.0` → `1.0.0`, `homepage`/`repository` URLs to by-dev-tools/flow, updated `description` covering the audit/critique + workflow surface.
- Move `.claude-plugin/plugin.json` to `plugins/flow/.claude-plugin/plugin.json` (Anthropic pattern: marketplace at repo root, plugin manifest inside its own directory).
- Update `plugins/flow/scripts/log_disagreement.py` disagreement-storage path: `~/.claude/plugins/data/assumption-auditor/disagreements/` → `~/.claude/plugins/data/flow/disagreements/`. Note: pre-existing user data at the old path becomes orphaned (acceptable — it's local dev/debug data; called out in PR body and README).
- Add `plugins/flow/skills/ship/SKILL.md` — port from md-manager `.claude/skills/ship/SKILL.md` (fetched via `gh api repos/by-dev-tools/md-manager/contents/...`) per the locked PR-1 /ship port table:
  - Steps 0, 2, 4–5: port as-is.
  - Step 1 (`/security-review`, `/accessibility-review`): `[PR 1 LIMITATION]` placeholder block; skills land in PR 2.
  - Step 3a (user-feedback → `feedback.md`): port active — pure markdown, no tooling dep.
  - Step 3b (memory machinery via `tools/memory/check.mjs`): `[PR 1 LIMITATION]` placeholder; memory tooling lands in PR 2.
  - Step 6 (`gh pr create --base main`): replace hardcoded `main` with default-branch discovery (`git symbolic-ref` → `flow.config.json.defaultBranch` slot → literal `main` fallback).
  - Step 7 (`/link`): replace with generic "if your project has a dev-server skill, invoke it now" note.
  - `npm run typecheck` references: config-slot via `flow.config.json.typecheckCmd`; **loud warning** if unset (`⚠️ flow.config.json.typecheckCmd not set; skipping preflight re-run. Set this slot to enable typecheck on /ship.`) — never silent no-op.
  - Doc paths (`core-docs/history.md`, etc.): config-slot via `flow.config.json.historyPath` / `planPath` / `roadmapPath` / `feedbackPath` / `specPath` with sensible defaults.
  - De-project: strip md-manager-specific tokens (`src/store.tsx`, `--sand-*`, `Geist`, `Mini`, `pattaya`, etc.).
- Add `plugins/flow/docs/workflow.md` — port from md-manager `core-docs/workflow.md` (already fetched at `/tmp/md-workflow.md`):
  - Strip md-manager-specific examples (designer cargo gates, md-manager preflight lists, etc.).
  - Annotate `/simplify`, `/batch`, `/debug`, `/loop`, `/claude-api` as **"(bundled with Claude Code)"** wherever referenced — they are Anthropic-native, not flow-provided.
  - Annotate `/critique-plan`, `/audit-plan`, `/audit-completion` as **flow-internal** (not an external assumption-auditor plugin anymore — they're bundled into flow).
  - Add a "Project config slots" section narratively documenting `flow.config.json` (paths, defaultBranch, typecheckCmd, etc.). JSON Schema lands PR 2.
  - Add a "Bootstrap status" / "v1.0.0 scope" section: only `/flow:ship` + the four audit/critique skills + 2 agents (`auditor`, `plan-critic`) shipped; full workflow surface comes in PR 2.
- Rename `core-docs/` → `dev-docs/` (flow's own dev-tracking; per Decision 4 + the consumer-vs-plugin convention). Move all files: `plan.md` (this plan + prior content preserved), `history.md`, `feedback.md`, `spec.md`, `workflow.md`. Note: this is a `git mv` rename, not a content rewrite.
- Update `CLAUDE.md` (project-dev concern, not plugin-shipped) for the new layout: plugin artifacts at `plugins/flow/*` (not root); project-dev knowledge at `dev-docs/` (not `core-docs/`); identity is "flow" (not "assumption-auditor"); call out the `template/core-docs/` (consumer-side) vs `dev-docs/` (plugin-side) distinction explicitly so future sessions don't conflate them.
- Update `.claude/rules/safety.md`: rewrite path references for the new layout. Safety-critical paths become `plugins/flow/agents/auditor.md`, `plugins/flow/scripts/extract_session.py`, `plugins/flow/scripts/bounding_logic.py`, `plugins/flow/skills/audit-plan/SKILL.md`, `plugins/flow/skills/audit-completion/SKILL.md`, `plugins/flow/.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `plugins/flow/evals/run_evals.py`, `plugins/flow/evals/ground_truth.yaml`. (Plus add `plugins/flow/skills/ship/SKILL.md` to the safety-critical list — it's new published surface.)
- Update `.claude/rules/general.md`, `.claude/agents/*.md`, `.claude/skills/*/SKILL.md` (project-dev infra): any references to `core-docs/...` get updated to `dev-docs/...`.
- Rewrite root `README.md` for the marketplace-shaped identity: what the marketplace is (`flow`), how to install (`/plugin marketplace add by-dev-tools/flow && /plugin install flow@flow`), pointer to `plugins/flow/docs/workflow.md` for what the plugin does, v1.0.0 status (audit/critique + `/flow:ship` shipped; rest of workflow surface lands PR 2; template directory lands PR 3), History section referencing the `pre-flow-plugin` tag for archeology and noting the rename from `llm-auditor`. The pre-rename assumption-auditor README content is preserved at the tag — not lost.
- Manual cold-read of full diff with security + simplification + project-agnostic lenses (the plugin's own `/flow:simplify` doesn't exist — `/simplify` is bundled-native, can be used; flow's `/flow:staff-review` doesn't exist yet — bootstrap exception per the brief).
- Per-phase commits with `Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>` trailer.
- Open PR against `main`; user merges.

**Scope (out):**
- Workflow skills `/flow:staff-review`, `/flow:security-review`, `/flow:accessibility-review`, `/flow:ship-spike`, `/flow:workflow-help` — PR 2.
- Agents `planner`, `docs`, the four staff-review lens agents (`staff-engineer`, `ux-designer`, `design-engineer`, `push-further`), optional `uncommon-care` — PR 2.
- Rules `general.md`, `plan-discipline.md`, `documentation.md`, `exploration.md` (the project-dev ones at `.claude/rules/*` that would become plugin-shipped portable rules) — PR 2.
- `tools/memory/check.mjs` — PR 2.
- `plugins/flow/schema/flow.config.schema.json` — PR 2.
- `plugins/flow/hooks/*` — PR 2.
- `template/` directory (web / swift / tauri-rust-ts overlays + `template/base/`) — PR 3.
- Backfilling `/flow:ship`'s PR-1-limitation placeholders — PR 2.
- Any md-manager-side changes (config layer, dogfood, deletion of duplicates) — PRs 4–6.
- Updating `~/.claude/settings.json` (`assumption-auditor@llm-auditor` → `flow@flow`) — user-side one-liner after merge; flagged in PR body.
- v1.x+ post-extraction features (autonomous routines, JTBD substrate, visual artifacts, design lenses) — out of the extraction umbrella entirely.

**Spec-walk checkboxes** (each binds to a verification step):

- [ ] `pre-flow-plugin` tag exists on `origin` and points at the pre-PR-1 HEAD (`git ls-remote --tags origin | grep pre-flow-plugin` matches `8857ebd`).
- [ ] All plugin artifacts live under `plugins/flow/` (verify: no `agents/`, `skills/`, `scripts/`, `evals/`, `DISAGREE.md` at repo root; all six moved).
- [ ] `.claude-plugin/marketplace.json` parses with `jq .` and declares marketplace `name: "flow"` + plugin `name: "flow"` + plugin `source: "plugins/flow"` (or equivalent `pluginRoot`-relative form).
- [ ] `plugins/flow/.claude-plugin/plugin.json` parses with `jq .` and declares `name: "flow"`, `version: "1.0.0"`, by-dev-tools/flow URLs.
- [ ] `plugins/flow/skills/ship/SKILL.md` exists, contains the explicit `[PR 1 LIMITATION]` placeholder for `/security-review` + `/accessibility-review`, contains the loud-warning string for unset `typecheckCmd`, has no md-manager-specific tokens (`grep -i "md-manager\|sand-\|space-\|geist\|mini\|pattaya"` returns empty).
- [ ] `plugins/flow/docs/workflow.md` exists, annotates `/simplify` (and `/batch`, `/debug`, `/loop`, `/claude-api`) as "(bundled with Claude Code)" wherever referenced, annotates `/critique-plan`+`/audit-plan`+`/audit-completion` as flow-internal, documents `flow.config.json` slots narratively, lists v1.0.0 scope and PR-2 backfill plan.
- [ ] `dev-docs/{plan,history,feedback,spec,workflow}.md` exist (all five files moved from `core-docs/`); `core-docs/` directory no longer exists.
- [ ] `plugins/flow/scripts/log_disagreement.py` writes to `~/.claude/plugins/data/flow/disagreements/` (grep for the new path; old `assumption-auditor` string absent).
- [ ] `.claude/rules/safety.md` lists the new `plugins/flow/*` paths; old root paths absent.
- [ ] `.claude/rules/general.md`, `.claude/agents/*.md`, `.claude/skills/*/SKILL.md` reference `dev-docs/` (not `core-docs/`); grep for `core-docs/` in `.claude/` returns empty.
- [ ] Root `README.md` describes the `flow` marketplace identity, includes install command, History section, and `pre-flow-plugin` tag reference.
- [ ] `CLAUDE.md` describes the new `plugins/flow/*` layout, `dev-docs/` convention, and the consumer-vs-plugin distinction (`template/core-docs/` vs `dev-docs/`).
- [ ] `grep -rn "llm-auditor\|assumption-auditor" .claude-plugin/ plugins/ README.md CLAUDE.md` returns only intentional history-tag references (in README "History" section and any commit-message archeology lines).
- [ ] `claude plugin validate .` exits clean.
- [ ] Local smoke test: `mkdir /tmp/flow-smoke && cd /tmp/flow-smoke && git init && claude` → `/plugin marketplace add <local-or-branch-ref>` → `/plugin install flow@flow` succeeds → `/help` lists `flow:ship`, `flow:audit-plan`, `flow:audit-completion`, `flow:critique-plan`, `flow:log-disagreement` (5 user-visible skills). If installing from the open branch fails because Claude Code can't read unmerged refs, document the failure and note "re-run smoke after merge" — don't block PR open on it.
- [ ] Manual cold-read pass complete: security (no command-injection in `` !`<cmd>` ``, no leaked paths, no secrets), simplification (no duplicated content between SKILL.md files, no dead text from md-manager source), project-agnostic (grep diff for `md-manager`, `pattaya`, `sand-`, `--space-`, `Geist`, `Mini`).

**Confidence verdicts (per load-bearing assumption):**

**Assumption:** Restructuring root content into `plugins/flow/*` via `git mv` preserves all behavior because skill files reference `${CLAUDE_PLUGIN_ROOT}/scripts/...` (dynamic) and `.claude-plugin/marketplace.json`'s plugin `source` slot is the only thing telling Claude Code where the plugin lives.
**Confidence:** HIGH
**Why:** Verified the three skill files (`critique-plan`, `audit-plan`, `audit-completion`, `log-disagreement`) all use `${CLAUDE_PLUGIN_ROOT}/scripts/...`. CLAUDE_PLUGIN_ROOT resolves dynamically to the installed plugin's path. The marketplace `source` field is the only static path reference and updates as part of this PR.
**If it flips:** A skill file has a hardcoded path that breaks after move. Smoke test (Step verify) catches it; fix the reference; the move stands. Single-file correction, not architectural.

**Assumption:** Renaming the marketplace from `llm-auditor` to `flow` and plugin from `assumption-auditor` to `flow` doesn't break any existing user installs in a way we have to handle gracefully. Pre-PR-1 installs will simply stop receiving updates until users re-run `/plugin marketplace add by-dev-tools/flow && /plugin install flow@flow`.
**Confidence:** HIGH
**Why:** Anthropic plugins are identified by `marketplace-name@plugin-name`; renaming both ends produces a new identity that the user must opt into. No silent breakage — the old key continues to point at a marketplace key that no longer exists, so the user sees an obvious "update failed" prompt. User is currently the sole consumer; coordinated migration is a one-line settings.json edit.
**If it flips:** Some Claude Code internal caches the old identity in a way that breaks the user's session on next launch. Mitigation: PR body documents the one-line settings.json edit + explicit `/plugin marketplace remove llm-auditor` if needed. The user already has a settings.json backup from PR 0 at `~/.claude/settings.json.bak.20260523-144832`.

**Assumption:** md-manager's `.claude/skills/ship/SKILL.md` (the port source for `/flow:ship`) ports per the locked PR-1 table at ~19% replacement rate (the consolidation doc's metric from the prior closed PR-1 attempt). Specifically: 3a stays active, 3b becomes a placeholder, security+a11y review invocations become placeholders, `typecheckCmd` becomes a loud-warning config slot, doc paths become config slots, default-branch becomes a fallback chain.
**Confidence:** MEDIUM
**Why:** The 19% metric came from a prior agent's port attempt against the SAME source file in a DIFFERENT host repo. The locked port table is stable. But: (a) md-manager's `/ship` source may have evolved since that estimate (I haven't read it yet — fetch + read happens during execution), and (b) edge cases in the port (e.g., new pipeline steps added to `/ship` in md-manager since the estimate) could push the replacement rate higher.
**If it flips:** If replacement exceeds ~30% (the prior re-plan trigger threshold), surface a mid-execution re-plan to the user rather than silently absorb scope. The mitigation pattern is exactly what the prior PR-1 attempt did with the `/simplify`-is-bundled discovery — proposal + approval, not silent expansion. Adds one round-trip; no architectural change.

**Assumption:** The `core-docs/` → `dev-docs/` rename doesn't break any rules/agents/skills under `.claude/` that read from `core-docs/` paths, because we update all references atomically in the same commit as the rename.
**Confidence:** MEDIUM
**Why:** The grep shows `.claude/rules/general.md`, `.claude/agents/*.md`, and `.claude/skills/*/SKILL.md` reference `core-docs/` paths. Atomic update is straightforward in principle, but path references can hide in non-obvious places (e.g., `paths:` frontmatter for rule auto-load, glob patterns in skills' `!` shell-substitution blocks). The risk is a missed reference that silently fails (a rule that no longer auto-loads, a skill whose context-injection cat-fails).
**If it flips:** A project-dev rule or agent stops working correctly in mid-PR. Discovery happens when the agent next tries to invoke that rule/agent during PR 1 execution itself, and the failure mode is visible (rule doesn't load, agent reports cat-error). Mitigation: pre-rename grep + post-rename verification grep + smoke-invoke each updated agent/skill at least once before push. Single-commit reversion is trivial if needed.

**Assumption:** `pre-flow-plugin` tag created against current HEAD (`8857ebd`) is sufficient as the recovery anchor — i.e., users (the user) can run `git checkout pre-flow-plugin` on the merged main branch and see the pre-restructure state.
**Confidence:** HIGH
**Why:** Standard git tag operation; `git push origin pre-flow-plugin` persists the tag remotely. The brief explicitly names this as the recovery mechanism.
**If it flips:** Tag push fails (auth / branch-protection issue). Trivial to retry; surface to user if it persists.

**Assumption:** Moving `.claude-plugin/plugin.json` from repo root to `plugins/flow/.claude-plugin/plugin.json` is the correct Anthropic-pattern shape — i.e., marketplace.json lives at repo root, plugin.json lives inside the plugin's own subdirectory.
**Confidence:** HIGH
**Why:** Verified against `code.claude.com/docs/en/plugin-marketplaces` in the prior consolidation session: marketplace.json at root + `plugins/<name>/.claude-plugin/plugin.json` inside is the explicit pattern. The current flat layout (both manifests at root) was acceptable when there was only ever going to be one plugin; the marketplace pattern formalizes the separation.
**If it flips:** `claude plugin validate .` rejects the new layout. Surface, fix path, re-validate. Single fix, no architectural impact.

**Risks / open questions:**
- **`log_disagreement.py` storage path orphan.** Renaming `~/.claude/plugins/data/assumption-auditor/disagreements/` → `~/.claude/plugins/data/flow/disagreements/` orphans any pre-existing disagreement records on the user's machine. Acceptable: it's local debug/dev data; the user has been the sole consumer; called out in README + PR body so the user can `mv` the old dir manually if they want continuity.
- **`/ship` port may surface unknown coupling.** If the md-manager source has evolved since the prior port-attempt's 19% estimate (e.g., new memory machinery references, new review skills baked in), the port could spill scope. Mitigation per the prior PR-1 pattern: surface re-plan rather than silently absorb. Re-plan trigger threshold is >30% replacement.
- **`/plugin marketplace add` from an unmerged branch.** The brief notes `/tmp/flow-smoke` may not be able to install from an open branch ref. If so, document and proceed; smoke can be re-run post-merge. Don't block PR open on this.
- **The `pre-flow-plugin` tag doesn't exist yet.** Verified empty via `git tag --list` and `gh api repos/by-dev-tools/flow/git/refs/tags` (404). The plan creates it as Step A. If for some reason tag creation fails (auth, branch-protection on tag namespaces), surface to user — the restructure is destructive enough that a recovery anchor is non-negotiable.
- **Marketplace `source` field shape.** The current marketplace.json declares `"source": "./"` because there's only one plugin and it lives at root. After restructure, `source` becomes `"plugins/flow"` (or `metadata.pluginRoot: "./plugins"` + `"source": "flow"` per the consolidation doc's docs-verified pattern). I'll use the `pluginRoot` form per Anthropic's example — cleaner if more plugins ever ship.
- **`spec.md` legacy content.** The current `core-docs/spec.md` describes the assumption-auditor product (audit categories, plugin scope, etc.). After rename to `dev-docs/spec.md`, this content describes flow's *audit-side* legacy product, but flow's broader workflow-plugin identity now exceeds what that spec covers. PR 1 preserves spec.md verbatim under the rename (do not rewrite scope in PR 1 — that's a separate dev-docs hygiene PR if needed). Flag in handoff notes that dev-docs/spec.md will need broadening in a follow-up.

**Files touched (anticipated):**

**Moves (`git mv` — history preserved):**
- `agents/auditor.md` → `plugins/flow/agents/auditor.md`
- `agents/plan-critic.md` → `plugins/flow/agents/plan-critic.md`
- `skills/audit-plan/SKILL.md` → `plugins/flow/skills/audit-plan/SKILL.md`
- `skills/audit-completion/SKILL.md` → `plugins/flow/skills/audit-completion/SKILL.md`
- `skills/critique-plan/SKILL.md` → `plugins/flow/skills/critique-plan/SKILL.md`
- `skills/log-disagreement/SKILL.md` → `plugins/flow/skills/log-disagreement/SKILL.md`
- `scripts/extract_session.py` → `plugins/flow/scripts/extract_session.py`
- `scripts/bounding_logic.py` → `plugins/flow/scripts/bounding_logic.py`
- `scripts/log_disagreement.py` → `plugins/flow/scripts/log_disagreement.py`
- `evals/run_evals.py` → `plugins/flow/evals/run_evals.py`
- `evals/ground_truth.yaml` → `plugins/flow/evals/ground_truth.yaml`
- `evals/fixtures/` → `plugins/flow/evals/fixtures/`
- `DISAGREE.md` → `plugins/flow/DISAGREE.md`
- `.claude-plugin/plugin.json` → `plugins/flow/.claude-plugin/plugin.json`
- `core-docs/plan.md` → `dev-docs/plan.md`
- `core-docs/history.md` → `dev-docs/history.md`
- `core-docs/feedback.md` → `dev-docs/feedback.md`
- `core-docs/spec.md` → `dev-docs/spec.md`
- `core-docs/workflow.md` → `dev-docs/workflow.md`

**Modified (post-move):**
- `.claude-plugin/marketplace.json` (rename names, URLs, source, pluginRoot, version, description)
- `plugins/flow/.claude-plugin/plugin.json` (rename, version bump, URLs, description)
- `plugins/flow/scripts/log_disagreement.py` (storage path rename)
- `README.md` (rewrite for marketplace identity)
- `CLAUDE.md` (update layout references)
- `.claude/rules/safety.md` (update safety-critical path list)
- `.claude/rules/general.md` (`core-docs/` → `dev-docs/`)
- `.claude/agents/{planner,domain,testing,docs}.md` (`core-docs/` → `dev-docs/`)
- `.claude/skills/{ship,preship}/SKILL.md` (`core-docs/` → `dev-docs/`)

**New:**
- `plugins/flow/skills/ship/SKILL.md` (port from md-manager)
- `plugins/flow/docs/workflow.md` (port from md-manager)

**Tag:**
- `pre-flow-plugin` at `8857ebd` (pushed to origin)

**Execution sequence** (each step → its own commit unless trivially small):

1. **Step A — Recovery tag.** `git tag pre-flow-plugin 8857ebd && git push origin pre-flow-plugin`. Verify via `git ls-remote --tags origin`.
2. **Step B — Restructure (move).** `git mv` all 19 file/dir paths above into `plugins/flow/*` and `dev-docs/*`. Move `.claude-plugin/plugin.json` into `plugins/flow/.claude-plugin/plugin.json`. Single commit: "Restructure: hoist plugin artifacts into plugins/flow/; rename core-docs/ → dev-docs/".
3. **Step C — Manifest rename.** Update `.claude-plugin/marketplace.json` and `plugins/flow/.claude-plugin/plugin.json` for `flow` identity + v1.0.0 + by-dev-tools URLs + descriptions. Validate with `jq .` + `claude plugin validate .`. Commit: "Rename marketplace + plugin to flow; bump to 1.0.0".
4. **Step D — log_disagreement storage path.** Edit `plugins/flow/scripts/log_disagreement.py` for the `assumption-auditor` → `flow` storage-dir rename. Commit: "Rename disagreement storage path: assumption-auditor → flow".
5. **Step E — Reference updates under `.claude/`.** Grep + edit all `.claude/rules/`, `.claude/agents/`, `.claude/skills/` references for `core-docs/` → `dev-docs/` and old root paths → `plugins/flow/*`. Commit: "Update project-dev infra path references for restructure".
6. **Step F — Port `/flow:ship`.** Fetch md-manager's `.claude/skills/ship/SKILL.md` via `gh api`. Read it. If replacement rate looks >30%, surface re-plan before writing. Otherwise port per the locked PR-1 table → `plugins/flow/skills/ship/SKILL.md`. Commit: "Add /flow:ship skill (ported from md-manager; PR 2 backfills placeholders)".
7. **Step G — Port `workflow.md`.** Port `/tmp/md-workflow.md` → `plugins/flow/docs/workflow.md` per the de-projection rules above. Commit: "Add canonical workflow.md (de-projected; v1.0.0 scope notes)".
8. **Step H — Rewrite README + CLAUDE.md.** Marketplace identity in README; new layout in CLAUDE.md. Commit: "Rewrite README + CLAUDE.md for flow marketplace identity".
9. **Step I — Manual cold-read pass.** Run greps for md-manager-specific tokens; check for command-injection in `` !`<cmd>` ``; verify no secrets / hardcoded user paths. Apply fixes inline. Commit only if fixes: "Manual review pass: <findings>".
10. **Step J — Verification.** `claude plugin validate .` clean; `jq .` parses both manifests; smoke test in `/tmp/flow-smoke` per the spec-walk checklist. Capture any smoke-test friction in `dev-docs/feedback.md` to surface in PR 2.
11. **Step K — Push + open PR.** `git push -u origin claude/trusting-jackson-0de7f4`; `gh pr create --base main --title "PR 1: Restructure into plugins/flow/; rename to flow@1.0.0; add /flow:ship + workflow.md" --body "..."`. Output PR URL. **Do not merge.**

---

## Recently Completed

_Last few shipped; full detail in `dev-docs/history.md`. (Merged PR blocks above are kept as historical records — a deeper archive-prune is a tracked follow-up.)_

- **SV2-spike handoff clarity** (docs PR, 2026-06-08) — wired the spike's resolved capture-and-persist mechanism into the roadmap PR-1 acceptance checkbox + added a ▶ V2 handoff pointer to Handoff Notes, so a fresh-session agent inherits the answer from the checklist it acts on (FB-0010 fan-out across the spike→feature seam).
- **SV2-spike — `/verify` screenshot-structure question** (spike PR, 2026-06-08) — **proceed.** Resolved `rubric.md:68`: bundled `/verify` is narration-only to verify-build's fresh-context judges (frames stay image-blocks in the orchestrator's context; no path even with `save_to_disk`). **V2 = branch (B)**, an explicit capture-and-persist step. Deliverable = `history.md` "SV2-spike".
- **PR DC — doc-currency in the ship pipeline** (#39, v1.5.2, 2026-06-05) — `/flow:ship` Step 5a reconciliation + 5b mechanical gate; a stale-docs ship is now blocked automatically.
- **V1 — `Visual-walk` plan field** (#37, v1.5.1, 2026-06-05) — declared visual/UX acceptance criteria; first link of the Deliverable-quality track.
- **PR U — ship-time gate semantics** (#31, v1.5.0) — resolution-confidence + draft-routing + verify-build placement.
- **PR S — autonomous ship-readiness trigger** (#30, v1.4.0).
- **PR Q — `/flow:verify-build` behavioral gate** (#26, v1.3.0).

## Backlog

(Items below predate the flow extraction; preserved for continuity. Most fold into PR 2 or post-extraction roadmap.)

- Verification skill (sibling plugin) — see prior plan content at `pre-flow-plugin` tag for full context. Reassess after extraction settles.
- Wire `evals/run_evals.py` to live auditor subagent invocation (remove `.expected.txt` stub) — flow-internal eval improvement, post-extraction.
- Capture fixtures for `trio_navigation_stack_cycle_3`, `portfolio_blank_screen`, `trio_morphing_recall`.
- Structured output schema for auditor (replace substring matching in eval checks).
- Expand artifact regex beyond the hardcoded 28-extension list in `plugins/flow/scripts/extract_session.py` (post-restructure path).
- Raise or remove the 50-call tool-history cap in `plugins/flow/scripts/extract_session.py`.
- Generalize hardcoded SwiftUI proxy handling to other frameworks.
- Broaden `dev-docs/spec.md` beyond the audit-only scope to cover flow's full workflow-plugin identity (follow-up hygiene PR after extraction).
