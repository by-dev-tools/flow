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
