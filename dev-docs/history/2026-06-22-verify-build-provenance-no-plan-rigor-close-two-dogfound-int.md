### Verify-build provenance + no-plan rigor — close two dogfound integrity holes (v1.10.0) — SAFETY
**Date:** 2026-06-22
**Branch:** `claude/quirky-jones-9932cd` (PR pending; squash SHA at merge)
**Commit:** [range on branch; squash SHA filled at merge]

**What was done:**
Closed two source-level integrity gaps in flow's own skills, both surfaced by a real `/flow:ship` run on production SwiftUI code in a consumer project (FB-0056).
- **Provenance (forgery defense).** Added a per-criterion `provenance` enum to the verify-build findings schema (`adversarial-judged | spike-rubric | hand-authored`) + `metadata.no_plan_fallback`, with the load-bearing contract that **absent/unrecognized ⇒ `hand-authored`** (untrusting default). `render-test-plan.py` and `render-report.py` now render a hand-authored PASS as a distinct `[~]` state (Markdown) / hollow-ring dot + `self-reported` chip + warning banner (HTML) and DROP the "machine verdict, not self-report" claim — a buffer the implementer wrote by hand can never render as machine-judged. Stamping prose added to `verify-build/SKILL.md` Step 7/8 + `spike-rubric.md`.
- **Spike vs no-plan split + rigor gate.** `verify-build` Step 2 now treats an *explicit* `/flow:ship-spike` as the only path to spike's 3-check rubric; a *missing/Spec-walk-less plan* is the **no-plan fallback** — source-touching → the full judged path over diff-derived criteria (provenance `adversarial-judged`, `no_plan_fallback=true` → ship draft-routes it); docs-only → smoke rubric. New stdlib `ship/lib/rigor-marker.py` (commit-invariant source fingerprint): `staff-review` writes a marker after its fixes land; `ship` Step 1.0a reads it for source-touching diffs → `[decision-required]` draft entry if missing/stale. Ship Step 2 routes `no_plan_fallback` likewise.
- **Evals + CI.** New `run_report_render_evals.py` (render-report.py had zero coverage) + `run_rigor_marker_evals.py` (incl. a seeded-git commit-invariance test) + a hand-authored fixture in `run_render_evals.py`; **wired all of them — plus the orphaned `run_visual_history_evals.py` — into `.github/workflows/ci.yml`** (staff-review BLOCKER). `workflow.md` + `design-language.md` updated; `gh` projectCards resilience + "second-source the provenance stamp" routed to roadmap § Next.

**Why:**
The dogfood run shipped a hand-authored verify-build buffer that rendered as "machine verdict, not self-report," and a no-plan production diff that got spike-grade verification + a ready PR — defeating verify-build's core value prop (the implementer can't show green without a real adversarial PASS) and the loop's review-rigor assumption. Root cause: when the judged path can't run, the loop silently degraded to a self-reported / reduced-rigor path that still rendered as machine-judged and merge-ready.

**Design decisions:**
- **Untrusting default (absent ⇒ hand-authored)** so omission can never mint a machine `[x]`; the residual *commission* seam (an author writing the trusted value) is a documented honest-limitation + a roadmap follow-up, not a silent over-claim — the schema text says so explicitly ("cooperative-agent contract, not cryptographic").
- **Keep no-plan judged** (user choice): a production diff lacking a plan artifact still earns a real fresh-context-judge verdict, not a 3-check smoke test — so a green stays trustworthy even absent a plan, while still routing to draft so the human declares criteria or waives.
- **Self-reported HTML treatment** demotes the verdict dot to a hollow ring (not just a chip) so the skim surfaces (heading/TOC/Overall pill) don't read solid green; the chip uses the banner's brick accent, NOT the FAIL verdict red, to avoid a verdict-color collision (design-engineer finding).

**Technical decisions:**
- **No new config slot for the marker** — it's a within-loop internal handoff a consumer never relocates (unlike `verifyFindingsPath`); a slot would fan the "24 slots" contract across marketplace/plugin/doctor/schema for no benefit. Fixed conventional `/tmp` path, branch-slugged.
- **Commit-invariant fingerprint** — `git diff origin/<base>` vs the working tree (not `..HEAD`), so committing staff-review's fixes between staff-review and ship doesn't false-trip the gate; centralized in one stdlib helper consumed by both writer and reader (FB-0054b).
- **Additive schema** (no `schema_version` bump) — `provenance`/`no_plan_fallback` optional; pre-fix buffers still validate; the example validates against the updated schema.

**Tradeoffs discussed:**
- **Marker mechanism vs manifest-only attestation** — chose the mechanical marker (FB-0047 enforce-don't-attest) over trusting the agent's loop-history; the marker is real evidence the gate keys on.
- **One PR vs split** — kept Gap A + Gap B together (they share the provenance infra + the no-plan/hand-authored root cause); the env-adjacent `gh` projectCards item was scoped OUT to the roadmap.
- **Provenance per-criterion vs top-level** — per-criterion (the judging site), with renderers deriving the buffer-level "any self-reported" predicate; avoids a redundant top-level field that could desync.

**Lessons learned:**
- A contract change to a non-forgeable renderer is an FB-0010 fan-out: every existing fixture had to be stamped (an un-stamped fixture correctly flipped to `[~]`), and every producer's prose updated, in the same PR.
- A new eval harness not wired into `ci.yml` gives **zero** standing protection — caught by staff-review; the orphaned `run_visual_history_evals.py` was a prior instance (now also wired). Memory entry written.
- Subagent spawning hit a transient session limit mid-loop; `/simplify` was done inline (quality review of readable code), staff-review + security ran once spawning recovered.
