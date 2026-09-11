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
