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
