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
