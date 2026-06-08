# Roadmap

Where the flow plugin is going over the next few horizons. Active work lives in `plan.md`; this is what's queued + what's being explored.

The plugin extraction umbrella (PRs 1-3 in flow + PRs 4-6 in md-manager) is the load-bearing scope through v1.2.0. Post-extraction v1.x+ work (autonomous routines, JTBD substrate, visual artifacts, design lenses, HTML reports, deploy previews) is documented in md-manager's `core-docs/handoffs/*-design-2026-05-23.md` series — that's the canonical roadmap for post-extraction; mirror entries here only when they become Now/Next.

---

## Now

**Plugin at v1.5.2 on `main`.** Since the v1.2.6 consumer-feedback era (PRs A–M), the loop has filled out: `/flow:verify-build` behavioral gate (PR Q, v1.3.0); auto-invocable `/flow:ship` at the Step 8 readiness predicate (PR S, v1.4.0); the `## Flow run` PR-body table (v1.4.1); reviewer session-discovery fix (v1.4.2); ship-time gate semantics + reviewer/ship-spike auto-invocability (PR U, v1.5.0); the dynamic-workflows alignment direction (#35); the **Deliverable-quality track V1** — the `Visual-walk` plan field (#37, v1.5.1) — plus its visual-verification blueprint + O8 spec (#36, docs); and **doc-currency in the ship pipeline** (PR DC, v1.5.2, this PR — `/flow:ship` now keeps roadmap "Now" + plan "Current Focus" current automatically, with a mechanical gate that blocks a stale-docs ship).

**▶ Next up: V2 — rendered capture + baseline** (Deliverable-quality track § below). **Spike DONE (2026-06-08, this PR — see `history.md` "SV2-spike"):** the `verify-build/lib/rubric.md:68` screenshot question is resolved — bundled `/verify` returns screenshots as image content blocks bound to the *invoking* agent's context with only a narration string in the text channel (no usable file path, even with `save_to_disk`), and verify-build's fresh-context judges read text → visual claims reach them as narration → Unknown. **V2 = branch (B): add an explicit capture-and-persist step** (persist frames to a flow-controlled path, write path refs into `observations[].content` — schema already supports it; keep+rewrite the rubric's VLM/pairwise section around path-referenced frames + a baseline; read text from the a11y tree, not pixels). The load-bearing next step toward the autonomous high-quality deliverable: it turns "visual = Unknown" into a real PASS the Step 8 predicate can trust.

### Execution order — the live forward queue

Three streams are open and interleave at PR boundaries (each PR is reviewed + merged independently): **Track 1** (autonomy-bar enforcement, K/L), **Track 2** (research-driven hardening, N/O/P), and the **Deliverable-quality track** (V2→V3→V4; see its § below). The two legacy tracks below remain queued; the Deliverable-quality track is the one with the most recent explicit user direction.

**Track 1 — autonomy bar enforcement (driven by PR J's FB-0011):**
1. **PR K** — `/flow:red-team` skill: standalone reviewer mirroring security-review structure, FB-0008 stale-base preflight, FB-0006/FB-0007 source-file early-exit, FB-0011 autonomy-bar `Fix-confidence` field (per-finding `AUTO-FIX-SAFE` vs `ESCALATE`).
2. **PR L** — trust-boundary detector (mechanical/regex, stdlib-only) + autonomous-invocation wiring + `/flow:ship` Detection-Point-3 routing applying FB-0011's auto-fix-vs-escalate rule. Depends on PR K's output schema.

**Track 2 — research-driven orchestration hardening (driven by `dev-docs/research/agent-orchestration-2026-05.md`):**
1. **PR N** (bumps to v1.2.7) — documentation grounding (Magentic `max_stall_count` citation in FB-0012, evaluator-optimizer archetype reference in workflow.md) + structured-result STATUS markers for `/flow:ship` Step 2 reviewers (closes PR E+ FOLLOW-UP #1 with field-validated production pattern). Plus generalize doctor Check 2.5 to scan `template/` files (PR M's BLOCKER class validates this — promote to PR N scope or bundle into next doctor-touching PR).
2. **PR O** (bumps to v1.2.8) — test-edit reward-hacking PreToolUse hook: mechanizes Step 1c's no-disable-tests guard via `Edit`/`Write` matcher against test-file glob, emits `ask` decision. Adds `flow.config.json.testFilePatterns` slot (18 slots total) + opt-in hook entry.
3. **PR P** (bumps to v1.2.9 or v1.3.0) — auditor model-diversity eval addressing FB-0013 same-model critic collusion. **Measurement-first:** build comparative eval infrastructure (Step A), swap auditor to Sonnet ONLY if ≥80% finding-overlap + comparable FP rate vs Opus on existing fixtures (Step B). Tier 2/3 (plan-critic, lens agents) stay on Opus per user direction. v1.3.0 if swap ships; v1.2.9 if Step A's eval shows structural mitigation is sufficient.

### Cross-track dependencies

| Item | Depends on | Reason |
|---|---|---|
| PR L | PR K | PR L applies the autonomy-bar routing to PR K's output schema. |
| PR N Phase 2 (STATUS markers) | none from K/L | Independent — modifies different files (security-review/SKILL.md + accessibility-review/SKILL.md + ship/SKILL.md Step 2). |
| PR O | PR N (preferred, not required) | PR O's hook is opt-in via `default-hooks.json`; PR N's STATUS markers extend the reviewer-output contract that PR O's hook surface is adjacent to. Bundling would risk both PRs being large; sequencing keeps them small. |
| PR P | PR N + PR O | PR P's measurement infrastructure benefits from the structured-result contracts PR N adds (easier eval comparison). |
| Carryover doctor Check 2.5 generalization (template/ files) | none — bundle into PR N | Validated by PR M's BLOCKER class. Lowest-cost place to land. |

### Track 1 vs Track 2 — which goes next?

**Superseded by the ▶ Next up pointer in § Now (V2).** *If* you redirect away from the Deliverable-quality track, the lowest-risk pick within these two tracks is **PR N** (docs grounding + STATUS markers; absorbs the doctor Check 2.5 generalization). The two tracks don't block each other at PR boundaries.

The detailed per-PR plans live in `dev-docs/plan.md` § "Active Work Items".

## Deliverable-quality track — toward the autonomous high-quality deliverable

**Goal state (user direction, 2026-06-05; FB-0041):** human + agent collaborate on a plan → agent gets first-gate approval → agent builds and **self-iterates against the plan's success criteria — behavioral *and* visual** — autonomously → when confident the plan is fully addressed and the visuals are good, the agent ships (auto-fixing what it can, draft-routing what it can't), opens a PR with the `## Flow run` table, **and presents an HTML visual walkthrough** of what was built. The human reviews those two deliverables at the merge gate and merges or gives feedback. Over time the feedback loop drives the deliverable toward "ready to merge with little/no human feedback." **No third gate** — the two load-bearing gates (plan approval, merge) are preserved; everything between trends autonomous. Close the quality gap by strengthening the behavioral+visual gate, never by re-inserting the human pre-ship.

**Where we are (2026-06-05 gap audit):** the *spine* ships in v1.5.0 — two-gate structure, Step 8 ship-readiness predicate + auto-advance (PR S), verify-build behavioral gate (PR Q), bounded mechanical auto-fix loops (PR M), `/flow:ship` draft-routing (PR U), the `## Flow run` PR table (PR T), and the two-layer feedback synthesis. The gaps cluster on **visual-verification depth** (the design lens reads the *diff*, not pixels; verify-build's screenshot capture is honestly uncertain per `verify-build/lib/rubric.md:68`, so visual claims often resolve to Unknown), the **HTML walkthrough deliverable** (not built; PR Q's findings-buffer JSON is the forward-compat data layer), and the **consumer-side proactive-error loop** (strong for flow's own dev; thinner consumer-side). This track sequences the four fixes as a dependency chain — each unblocks the next. Interleaves with Track 1 (K/L) + Track 2 (N/O/P) at PR boundaries.

### V1 — Structured visual acceptance criteria (cheapest; the input everything needs)
**Surfaces when:** the plan template / `plan-discipline.md` / `workflow.md` Step 2 required-fields are next touched, OR a consumer reports the agent shipped a UI change with no declared visual bar.

Extend the plan's spec-walk so visual/UX criteria are *declared* the way behavioral ones already are — a `Visual-walk:` (or equivalent) block of checkable visual assertions ("matches token X; empty/loading/error states present; motion ≤ Y ms; honors design-language doc rule Z"). Without declared visual criteria there is nothing to verify or render against — this is the load-bearing input for V2 and V3. Lowest cost (prose/template change + plan-critic awareness of the new field). **Do first.** *(V1's declaration-only field shipped in v1.5.1 — the items below are its deferred follow-ups.)*

**V1 staff-review follow-ups (2026-06-05; deferred by design — captured so V1.1/V2 inherit the named shape, not re-derived):**
- **plan-critic enforcement** — flag a `uiSurface:true` plan that omits `Visual-walk` (Facet 4's gate half) + an eval fixture. Owner: V1.1 or fold into V2. (Surfaced + approved-deferred at V1's plan gate, Confidence #2.)
- **`designLanguagePath` fallback** — `Visual-walk` says "write against the design-language doc," but the slot is Optional; a `uiSurface:true` project may lack one. Add a one-line "if no design-language doc, assert against observed/intended states" clause. Owner: V1.1.
- **Spec-walk vs Visual-walk boundary** — both say "user-perceptible"; the behavioral/visual split is undefined, so authors may duplicate or guess — which undermines V2's separate-extraction premise. Add a one-line boundary rule. Owner: fold into V2 (where extraction becomes testable).
- **`Not checked:` sub-line** — `Visual-walk` declares what WILL be checked but not its negative space (reduced-motion, dark mode, RTL, narrow viewport, high-contrast). A declared "not checked" list is the data source V3's "what we did NOT test" pane renders + the confidence-boundary the merge-gate human needs (FB-0035). Owner: V1.1 or sequence against V3.
- **Worked example** — no end-to-end populated `Visual-walk` block exists yet; naturally lives with the `/flow:plan` skill or V3's renderer. Owner: docs.

### V2 — Rendered capture + baseline (the gate that makes visual autonomy safe)
**Surfaces when:** the V2 feature plan is drafted (the spike precondition is now met — see below), OR a consumer reports visual claims resolving to Unknown on every run.

**Empirical question RESOLVED (SV2-spike, 2026-06-08; `history.md` "SV2-spike"):** bundled `/verify` does **not** hand structured frames to verify-build's judges. A live Chrome-MCP run showed screenshots return as image content blocks bound to the *invoking* agent's context + a narration string in the text channel (no usable file path, even with `save_to_disk: true`); the fresh-context judges read text only → visual claims reach them as narration → Unknown (today's "visual = Unknown → block"). The rubric's VLM/pairwise section is **kept, not removed** — re-grounded on path-referenced frames. (Side-finding: the Chrome-MCP network panel mis-reported a `201` POST as `503`; read text — incl. status — from the a11y tree / explicit assertion, not a single observation channel.)

**V2 = branch (B): add an explicit capture-and-persist step** so verify-build's judges *and* `lens-design-engineer` get actual frames + a baseline for the pairwise VLM comparison the rubric already prefers over absolute scoring: the orchestrator drives the browser-MCP screenshot, persists each frame to a flow-controlled path (assets dir alongside `verifyReportPath`), and writes path refs into the buffer's `observations[].content` (schema already types it as "relative path or base64 data URI" — no migration for capture). Use `a11y_snapshot` observations for label/copy/status, reserving `screenshot` for genuinely visual claims. Converts today's "visual = Unknown → block" into a real PASS/FAIL the Step 8 predicate can consume. **Highest-leverage PR for the autonomy goal** — it's what lets the agent honestly say "visuals are good" without a human babysitting. Depends on V1's declared criteria. Couples capture (producer) + renderer/judge-consumer (consumer) in one PR per FB-0003; must not duplicate #36's durable `visual-history.html` (V3b).

### V3 — HTML visual walkthrough renderer (the deliverable the human opens before merge)
= the existing **"Verify-build HTML case-study report"** item in § Next — this entry now sequences it as **V3 of this track**. PR Q's findings-buffer JSON (`lib/findings-schema.json`) is the forward-compat data layer; build the renderer against it — hero + per-criterion "the question / what we explored / what we learned" + the **screenshots from V2** + per-dimension verdict + a "what we did NOT test" checklist. Complements the `## Flow run` PR table with visual detail. **Sequence after V2** so it renders *verified* visuals, not a pretty page with nothing behind it.

### V4 — Consumer-side proactive-error loop (the compounding flywheel)
**Surfaces when:** the memory→preflight promotion path (`workflow.md` § Continuous improvement) is next touched, OR dogfood shows the agent repeating a visual/UX mistake a prior session already logged.

Strengthen the consumer-side memory→preflight loop so the agent checks its work against past logged visual/UX corrections *before* presenting — driving "most issues fixed before the human reviews" toward the goal state's "little/no feedback." The mechanism exists for flow's own dev; this hardens it consumer-side and compounds with V1–V3 (more structured criteria → more checkable past-error patterns). **Do last** — it needs V1's criteria + V2's gate to have something concrete to check against.

**Smaller / optional (not on the critical path):** a `/flow:plan` skill + mechanical first-gate assertion. Plan-*write* is prose-enforced today (no `/flow:plan` command, no mechanical "all required fields present" check, and even the `planner` agent returns text for the main thread to apply rather than writing the file). Hygiene; low urgency vs. V1–V4.

**Sequencing rationale:** V1 is the input, V2 is the gate that makes autonomy safe, V3 is the deliverable, V4 is the flywheel. V3-before-V2 produces an unverified-but-pretty walkthrough; V4-before-V1 gives the loop nothing structured to check against.

## Next

After the K/L (Track 1) + N/O/P (Track 2) sequences ship, AND in parallel with them (different surface; mechanical rebase):

- **PR Q — SHIPPED (v1.3.0, #26, `aeadcb7`).** `/flow:verify-build` — plan-driven behavioral verification gate at `/flow:ship` Step 2. Wraps bundled `/verify` (and transitively `/run` + `/run-skill-generator`) with flow-specific orchestration — criteria extracted from `**Spec-walk:**` checkboxes, adversarial transformation, per-dimension parallel judges with Unknown-blocking gate, structured findings buffer routed to `/flow:ship` Step 4a. Closed the static-analysis-only gap in the loop's verification surface (Potemkin-interface / hallucinated-success class). FB-0015 (check bundled first) captured the discipline lesson. **Its findings buffer is the data layer the Deliverable-quality track's V2/V3 build on** (see that § + the O8 entry below).

### Make `/flow:ship` Step 2 auto-entry-aware so the verify-build precondition becomes a mechanical assertion (post-PR-S, push-further roadmap-concrete)

**Surfaces when:** `plugins/flow/skills/ship/SKILL.md`'s auto-invocation contract is touched again, OR a consumer reports an auto-ship that opened a PR on a `platform=library|none` / `verifyEnabled=false` project where the Step 8 predicate should have stopped it.

PR S's auto-ship relies on ship Step 2's verify-build (`exit_code:1` on FAIL/Unknown) as the mechanical net, but Step 2 behaves identically whether ship was auto-entered or typed — it can't *assert* the Step 8 predicate's "verify-build PASS / not-skipped" precondition actually held. For code diffs the net is real (Unknown blocks); the thin spot is the genuinely-skipped case (`verifyEnabled=false` / `platform=library|none`), where Step 2 skips verify-build entirely, so a mis-judged auto-advance there would open a PR with no behavioral gate. Direction: write a one-line auto-entry breadcrumb at Step 8 (a `--auto` arg or a `/tmp` flag) and have ship Step 2 hard-fail-to-present when `auto-entered AND verify-build skipped`. Cost ~ one flag write + one conditional + one eval fixture. Out of scope for the PR-S flag-flip (adds a control-flow contract); the right shape once auto-ship has dogfood miles.

### Apply PR U draft-routing to `/flow:ship-spike` (post-PR-U)

**Surfaces when:** `ship-spike/SKILL.md` Step 2 is touched again, OR a spike's verify-build (`--spike`, 3-check) returns Unknown and hard-halts where a draft + manifest would have been the better outcome.

PR U moved `/flow:ship` from a verify-build hard-halt to draft-routing (a non-converging regression → draft PR + `🚫 NOT READY TO MERGE` manifest), but deliberately left `/flow:ship-spike` on its existing hard-halt (`spike-rubric.md`: "Unknown verdicts block ship"; `ship-spike/SKILL.md`: "Unknown ⇒ exit 1 → spike ship halts"). That's a scope-boundary inconsistency, not a correctness bug — spikes are throwaway. But it's arguably *more* right for spikes to draft-route: a spike answering a negative research question ("it doesn't work, here's why") shouldn't be blocked from opening its PR by a failing smoke check, since the deliverable is the history-entry learning, not passing code. Direction: adopt the same draft-manifest routing in ship-spike Step 2; update `spike-rubric.md` + `ship-spike/SKILL.md` + the verify-build description (which currently notes "ship-spike still halts — spike scope"). Cost ~ mirror of PR U's ship Step 2 edit + fixture. Routed from PR U (2026-06-01).

### Machine-consume the `NOT READY TO MERGE` manifest sentinel (post-PR-U, push-further roadmap-concrete)

**Surfaces when:** `ship/SKILL.md`'s manifest block is next touched, OR a draft PR with the sentinel gets merged anyway (the producer/consumer drift the sentinel exists to prevent).

PR U ships the *producer* of a machine-checkable sentinel (`<!-- flow:not-ready-manifest -->` … `<!-- /flow:not-ready-manifest -->`, a paired delimiter designed to be parsed) but no *consumer*. Draft status is mechanical-but-one-click-overridable; the manifest is human-readable-but-advisory; nothing reconciles them if they drift (manifest present but PR marked ready, or empty manifest but still draft), and nothing at the merge gate enforces the sentinel. This is the deliberate second half of PR U's contract — it turns "a not-ready PR can't *look* ready" into "can't *be* merged ready," which is the actual safety property the two-gate thesis wants. Direction: a `/flow:doctor`-style or CI predicate that greps an open PR body for the sentinel and asserts **manifest-present ⟺ PR-is-draft** (loud inconsistency otherwise), plus optionally a branch-protection/merge-queue check that fails while the sentinel is present. Cost ~ one grep predicate + one doctor check + one fixture (mirrors doctor Check 2.5 shape). Sub-items folded in from PR-U staff-review: (a) **persist the manifest** to a `/tmp/flow-not-ready-manifest.json` breadcrumb (mirror `verifyFindingsPath`) so an interrupted ship run between Step 2 and Step 7 can't lose it and re-open a ready PR that should be draft; (b) `/flow:doctor` `gh`-version check for `gh pr ready --undo` availability. Routed from PR U (2026-06-01).

### Extend the resolution-confidence axis to `/flow:staff-review` BLOCKERs (post-PR-U, push-further roadmap-concrete; Later)

**Surfaces when:** staff-review's lens output contract or ship Step 2's manifest source-enum is next touched.

PR U's resolution-confidence axis (`[auto-fixable]`/`[decision-required]`, default-to-escalate) is a reusable reviewer primitive, but it lives only on the two ship-time reviewers (security + a11y). `/flow:staff-review`'s four-lens BLOCKERs have no such tag, so a staff-review BLOCKER the agent can't confidently resolve has nowhere structured to route — it gets best-effort-fixed (the exact failure mode PR U eliminated for security/a11y) or surfaced as prose. Direction: add the axis to all four lens output contracts and wire a staff-review `[decision-required]` BLOCKER into the same draft-manifest routing ship Step 2 accumulates; the manifest entry-prefix enum already anticipates source-tagging (`[<security|a11y|verify-build>]`) — add `staff-review`. Cost ~ four lens-prompt edits + one manifest-enum line + one fixture. Correctly scoped OUT of PR U (Facets 2+3 only); recorded so the next staff-review touch picks up the named shape rather than re-deriving it. Routed from PR U (2026-06-01).

### Verify-build HTML case-study report (= V3 of the Deliverable-quality track; post-PR-Q)

**This is V3 of the "Deliverable-quality track"** (see that § above, #37/FB-0041): V1 = the `Visual-walk` declared-criteria plan field (shipped declaration-only, v1.5.1), V2 = rendered capture, V3 = this HTML walkthrough renderer, V4 = the proactive-error loop. This entry is the concrete V2+V3 spec; it consumes V1's declared criteria and is sequenced after V2 so it renders *verified* visuals.

**Surfaces when:** consumer reports they want a richer pre-merge review artifact than the structured-buffer + PR-body checklist PR Q ships, OR PR Q's findings-buffer JSON schema gains a stable consumer-validated shape.

**Direction:** PR Q's `/flow:verify-build` JSON findings buffer (`lib/findings-schema.json`) is the structured-data layer. The vision (user, 2026-05-28) is a **rendered HTML report** as the final pre-merge artifact — the file the human opens before clicking merge. Concretized into a spec 2026-06-04 against `byamron/health-tracker`'s prior art; full analysis + de-tokenization ledger in [`dev-docs/research/visual-verification-blueprint-2026-06.md`](research/visual-verification-blueprint-2026-06.md). Reference shape: health-tracker's `craft/visual-history.html` (merged #10 — hero + per-decision "question / explored / learned" panes, before/after, real screenshots) for the durable record, and its ephemeral per-feature review companion for the per-run report. Spec below.

**Spec (concrete, post-PR-Q; project-agnostic — zero project tokens, all targets from `flow.config.json`):**

1. **CAPTURE — two additive buffer fields (`schema_version` stays `1.0`; additive ⇒ no migration).** The buffer is already a superset for the *evidence + verdict* layer (typed observations + `timestamp_offset_ms`, adversarial cases, two-citation per-dimension verdicts, `not_tested`). It is a **blank** for two things the report needs:
   - `criteria[].grounding` — `{ type: need|design-language|craft-commitment|open-question, statement, citations[], decision_test? }`. *Rationale carried* — why the surface looks/behaves the way it does. Citations resolve from `specPath` / `designLanguagePath`, never hardcoded doc names.
   - top-level `open_questions[]` — `{ question, rationale, recommended_default, user_need_lens, routing: this-iteration|future-planning }`. **Distinct from `Unknown`** (epistemic). A `this-iteration` question **blocks Step 8 auto-advance** (mirrors an unresolved MEDIUM assumption); `future-planning` routes to the roadmap.
   - Constraint: FB-0003 — don't land the fields until a producer writes them and a consumer reads them in the same PR.

2. **RENDER — the ephemeral human-feedback report (co-equal to the durable record, not an afterthought).** A stdlib-only Python renderer (no new dependency), buffer JSON → one self-contained HTML file at a new `verifyReportPath` slot (default a temp dir, e.g. `/tmp/flow-verify-report.html` — ephemeral, NOT committed). This is **the file the human opens at the merge gate to give feedback** — its job is to surface the real decisions/tradeoffs needing input, not to extract a rubber-stamp (FB-0040). Structure: hero + verdict pills (`metadata`/`overall_verdict`) → legend (PASS/FAIL/Unknown + the four grounding chips) → TOC (per criterion) → per-criterion section (text → grounding callout → evidence/timeline from `observations[]` → adversarial pane → per-dimension verdict cards with the verbatim two-citation evidence) → standalone **"Open questions for you"** block → "what we did NOT test" (`not_tested[]`) → footer. **Coverage requirement:** the report must render the **full declared `Visual-walk` state set** (V1) — every declared state gets an evidence item or an explicit "not captured" line, so "exhaustive" is verifiable. Screenshots base64-inlined but **resized first** (~460–620px, never raw retina PNGs). Needs its own report design-language doc (`plan.md` item 10). **Capture-depth dependency:** exhaustiveness is bounded by what V2 captures into the buffer — the renderer shows what V2 captured, so V2 must exercise the full declared state set (see Sequencing).

3. **DOCUMENT — the durable visual record (`visual-history.html`, FB-0042).** The rendered report is ephemeral; at `/flow:ship` its load-bearing visual decisions distill into a **single curated `visual-history.html`** — the *picture* companion to the existing history core doc (`historyPath`), NOT a new `.md` and NOT a `.md`+`.html` pair (health-tracker #10 has no separate `.md`). Opt-in, **`uiSurface`-gated**; new `visualHistoryPath` slot. It commits **lean screenshot assets** (resized keepers on relative paths in a `visual-history-assets/` dir; CSS/SVG reconstruction is the honest fallback when capture isn't available — *not* schematic-only, *not* base64-embedded). Curated + **decision-centric**, **reverse-chronological** (newest first), anchor-link TOC, **no italic headings** (health-tracker FB-0006). Scaffolded into `template/base/core-docs/`. ship Step 4a's existing FB-candidate derivation extends to answered `this-iteration` questions. Full shape in **FB-0042**.

4. **GATE — folds into the merge gate, no third gate (FB-0035/FB-0034).** Discovery + iteration happen at Present (Step 8/9) before the ship decision; a `this-iteration` "this is wrong" re-enters Execute and re-renders the report; the report is the file opened at the existing merge gate. A non-converging regression at ship's confirmation re-run routes to a draft PR + manifest (FB-0034) — escalation lands *in* a gate, never as a new one.

**Sequencing + acceptance criteria (implementation-ready).** Mapped to the track stages: **V2** (capture) + **V3a** (ephemeral renderer) land as **one PR** — FB-0003 couples the new schema fields to a producer (capture) *and* a consumer (renderer) in the same PR — then **V3b** (durable record) is a second PR. (V1 shipped in v1.5.1; V4 is later.)

**PR-1 — track V2 (capture) + V3a (renderer): capture-depth + the two buffer fields + the ephemeral renderer.** Acceptance:
- [ ] `criteria[].grounding` + top-level `open_questions[]` land in `findings-schema.json` (additive; `schema_version` stays `1.0`) **with a producer writing them and a consumer reading them in the same PR** (FB-0003) — `findings-example.json` updated; an eval fixture asserts the shape.
- [ ] verify-build (via bundled `/verify`/`/run`) **exercises every declared `Visual-walk` state** (V1) and writes an `observations[]` entry per state; a declared state with no observation → `Unknown` + a `not_tested[]` line (no silent gap).
- [ ] `verifyReportPath` slot + stdlib renderer emit the § "RENDER" structure; **coverage assertion**: every declared `Visual-walk` state appears in the report as evidence-or-"not captured".
- [ ] `open_questions[routing=this-iteration]` present ⇒ Step 8 auto-advance blocks (§ GATE); fixture pins it.
- [ ] Landed against a real UI surface first (health-tracker is the available fixture) before the shape is called stable (FB-0016).

**PR-2 — track V3b: the durable record + the distill bridge.** Acceptance:
- [ ] `visualHistoryPath` slot + a `template/base/core-docs/visual-history.html` scaffold (uiSurface-gated; no separate `.md`); `visual-history-assets/` convention documented; renderer/author uses lean asset refs or labelled CSS/SVG reconstruction (FB-0042).
- [ ] `/flow:ship` **distill step**: from that run's ephemeral report, the load-bearing visual decisions (`grounding` that changed the user's read + `this-iteration` questions the human resolved) become **one** curated, reverse-chronological, no-italic-heading entry; then the ephemeral report is discarded.
- [ ] CLAUDE.md sync-table row + the doc-update path wire it as a core living doc; an eval/fixture covers the gated scaffold + the distill output shape.

PR letters TBD (post-PR-Q; PR R taken by the init-skill plan). **FB-0042** governs (3); this entry + the blueprint govern (1)/(2)/(4); **#37/FB-0041** is the umbrella the whole track serves. Full implementation contract — including the two-artifact contract table — in [`dev-docs/research/visual-verification-blueprint-2026-06.md`](research/visual-verification-blueprint-2026-06.md) § 2–§ 4.

**Origin:** user vision note 2026-05-28 (PR Q scoping intake); concretized 2026-06-04 from health-tracker prior art; reconciled 2026-06-05 with flow #37 (the Deliverable-quality track) + merged health-tracker #10 (FB-0042 + the blueprint research doc).

- **27 carryover FOLLOW-UPs** routed from reviews of PR G + H1 + I + J + H2-docs + M. Most are MEDIUM-priority polish or v1.2 hygiene; bundle into a future PR H-proper consolidation after the active queue lands. Highlights: doctor Check 2.5 generalization to `template/` files (validated by PR M's BLOCKER class; folding into PR N is preferred — see Now § Cross-track dependencies); manifest description CHANGELOG.md extraction; `preflightCmd` example in `template/base/flow.config.json.example`; per-attempt log machinery enforcement.
- **Resume umbrella retirement.** md-manager PRs 5 (dogfood) + 6 (delete duplicates + retire umbrella) per `dev-docs/handoffs/md-manager-pr4-6-spec.md`. Flow-side: standing by for PR 5's feedback intake; may surface additional rough edges worth a second follow-up bundle.
- **Carryover PR-2 FOLLOW-UPs not yet absorbed** (items 3-8 in `dev-docs/plan.md` § "PR 3+ follow-ups from PR 2 review"). Most are MEDIUM-priority polish or v1.2 hygiene; pick up opportunistically rather than as a focused PR.

## Later

- **Schema slot bi-directional consumer-pairing check** as a pre-commit recipe (FB-0003 pre-commit grep + FB-0009 follow-up). One-shot script under `tools/` would catch the next schema-without-implementation / implementation-without-schema bug before it ships.
- **End-to-end `/flow:ship` regression coverage.** Currently zero fixtures for the workflow skills; verification is dogfood-only. A small fixture project under `evals/` that exercises one ship pipeline in CI would catch the runtime-permission class (FB-0002) before it ships.
- **CHANGELOG.md extraction from manifest descriptions** — both plugin + marketplace descriptions are at ~1500 chars after each version cumulative sentence; extracting to CHANGELOG.md reference would relieve the bloat. Worth doing before v1.2.7 to stop the trend (engineer + auditor lens convergence on PR M).
- **Doctor Check 2.5 generalization** — currently scans `CLAUDE.md / README.md / docs / core-docs / dev-docs` for stale `N slots` references; PR M's BLOCKER (template/ files missed) validates extending to scan `template/` too. Also worth generalizing beyond slot count to skill count / lens count / rule count. **Version strings: DONE (PR DC)** — version-currency is now enforced automatically at `/flow:ship` Step 5b + mirrored in doctor Check 2.6; only the remaining count generalizations (template/ files, skill/lens/rule counts) stay queued. Bundle the rest into PR N or the next doctor-touching PR.
- **Doc-currency gate: `jq`-absent hardening** (PR DC staff-review FOLLOW-UP) — the Step 5b / Check 2.6 currency gate assumes `jq` is on PATH; if absent (with a manifest present), it false-FAILs with a misleading "no .version" diagnosis. Add a `command -v jq` preflight with a clean install hint (FB-0009 fail-fast shape). Low priority — consistent with existing `jq` reliance (Step 1c, doctor 2.5). **Surfaces when:** the currency-gate shell is next touched, OR a consumer reports a jq-missing false-FAIL.
- **Narrative-currency micro-check: "in-flight" vs merged** (PR DC push-further FOLLOW-UP) — the version-token gate is mechanical; full narrative correctness is (correctly) left to 5a judgment. But ONE narrative assertion is mechanical, not fuzzy: flag any `## Now` line marking a PR/branch "in flight" whose PR is actually merged on the default branch (`gh pr list --state merged`, FB-0009 early-exit shape). The second-worst drift this PR's evidence cited ("PR Q in flight" while shipped). Net-new doctor/ship check. **Surfaces when:** a "PR X in flight" line is next found stale, OR the next doctor-check-touching PR.
- **`## Flow run` skip-vocabulary consistency check** (PR T staff-review FOLLOW-UP) — the skip-reason vocabulary (`skipped (spike)` / `skipped (tiny)` / `uiSurface:false` / `verifyEnabled:false` / `platform library|none`) + the `<✓ / skipped (reason)>` Status-cell shape now live in `/flow:ship` §7, `/flow:ship-spike` §7, and (by reference) the dev-side `.claude/skills/ship`. PR T guards drift with a one-PR spec-walk grep; the durable fix is a `/flow:doctor` check that diffs the skip-reason token set + Status-cell convention across those surfaces. Net-new check; fold into the Check 2.5 generalization above. **Surfaces when:** the `## Flow run` table wording is edited in any ship skill.

---

## § Exploration

Items surfaced by `/flow:staff-review`'s push-further lens, consumer dogfood, or research passes. These don't have a concrete shape yet — they describe a direction worth investigating when relevant code is touched. Each entry includes a **`Surfaces when:`** trigger naming the file paths or area that should re-surface the item, so the auto-loading `exploration` rule can grep this section for trigger matches.

### Cross-run aggregation of `## Flow run` tables — the loop reflecting on itself (PR T, push-further exploration)

**Surfaces when:** `plugins/flow/skills/ship/SKILL.md` §7 (`## Flow run`) is touched again, OR any future loop-telemetry / `/flow:doctor` cross-PR-analysis work begins.

PR T (v1.4.1) makes each ship emit structured per-step self-documentation on its PR — but every table is born and dies with one PR; nothing ever reads them back. The latent value the structure creates: noticing patterns across runs ("`/simplify` has shown `—` on the last 8 PRs — is it earning its step?"; "verify-build skipped 6 runs straight — is `verifyEnabled` mis-set?"). Open question: is there a low-cost way to make the tables aggregatable (e.g. `/flow:doctor` scanning the project's own merged-PR bodies via `gh`) **without** introducing the per-session machine-readable loop-history artifact PR T deliberately declined (FB-0015 over-build check / FB-0019 "in-session context only")? Touches retention/parsing/privacy questions with no clear shape yet. Do NOT pull into a PR until the shape clarifies — the in-session-only decision is correct for current scope.

### Stop-hook enforcement for the Step 8 ship-readiness predicate (post-PR-S, push-further exploration)

**Surfaces when:** `plugins/flow/skills/ship/SKILL.md`'s auto-invocation contract is widened to a currently-skipped platform (per FB-0018's "applies to"), OR a consumer reports an auto-ship that fired when the predicate should have stopped it, OR `plugins/flow/hooks/default-hooks.json` gains a Stop hook for any other reason.

PR S deliberately keeps the Step 8 predicate as *guidance* (rule + skill description), with verify-build as the only mechanical backstop — correct ceiling for a flag-flip PR. A Stop-hook is the lever that would make the predicate genuinely non-bypassable (the model can't talk past a hook), but it's a different surface and out of scope. This entry records that the soft-enforcement model was a deliberate choice, not an oversight, so a future widening session doesn't reinvent the question.

### Rule-of-three: `flow:close-out` skill abstraction for umbrella tracker hygiene

**Surfaces when:** a fourth umbrella close-out PR lands in any consumer (e.g., the eventual designer migration creates the same shape) — currently three instances: md-manager#21 (close-out for flow PR 1+2), md-manager#22 (close-out for flow PR 3), and md-manager#24 (close-out for flow PR 4).

**Direction:** The mechanical 70% of these close-out PRs is now stable across three instances — SHIPPED header format, checkbox-flip diff in `core-docs/plan.md`, sweep-to-Recently-Completed at `/flow:ship` time. The per-PR 30% (which FB-derived confidence verdicts to name, which post-merge action items to surface) is genuinely PR-specific. If a fourth instance lands, that's the rule-of-three trigger to consider whether the variance is principled (worth keeping bespoke) or accidental (worth a `flow:close-out` skill that templates the mechanical parts and prompts for the FB-derived parts). Do not extract yet — three is the cue to flag, not the cue to commit.

**Origin:** md-manager PR #24 push-further lens; consumer feedback report 2026-05-25.

**Out of scope (don't conflate):** This is distinct from `/flow:ship` itself (which closes out a PR's OWN session) and from `/flow:ship-spike` (which closes out a spike). The proposed `flow:close-out` would close out a CROSS-REPO umbrella tracker entry — orthogonal scope.

### Hook-mechanization fan-out for reward-hacking suppressors  *(STRONG signal)*

**Surfaces when:** PR O lands the test-edit PreToolUse hook, OR a second reward-hacking instance is observed in a Step 1c retry attempt log (suppressor insertion or test deletion that the prompt-level guard didn't catch).

**Direction:** PR O ships a PreToolUse hook on `Edit`/`Write` against test-file patterns, emitting `ask`. The same hook shape applies to other reward-hacking patterns the prompt contract already names but doesn't mechanize: `@ts-ignore` / `# type: ignore` / `// biome-ignore` / `# noqa` / `eslint-disable-next-line` / `@SuppressWarnings` / `#[allow(...)]` insertion via Edit operations; deletion of `expect()` / `assert` calls; weakening type signatures. All detectable as PreToolUse hooks on Edit/Write with regex on `new_string` (`old_string` for deletions). If PR O's test-edit hook earns its keep in dogfood, follow with PR O.1 covering suppressor insertion. If PR O shows false-positive friction during regular dev, the fan-out is rejected as a class — keep prompt-level guards + human merge gate.

**Origin:** PR M push-further lens EXPLORATION (STRONG signal per the research synthesis); pairs naturally with PR O's mechanism.

### Flaky-test classification: distinguish "no progress" from "fix-not-applied"  *(MODERATE signal)*

**Surfaces when:** Step 1c bounded retry produces an oscillation abort that turned out to be a flaky test (consumer reports false-positive after their first oscillation BLOCKER), OR a second consumer-PR exhausts N=3 on a test that intermittently passes.

**Direction:** Current Step 1c contract conflates "Claude attempted a fix that didn't help" (oscillation) with "Claude correctly recognized a transient failure and applied no fix" (flake-clear). Magentic's `max_stall_count` distinguishes "no progress" from "wrong progress" via consecutive-non-progressing-rounds counting; Flow's diff-hash conflates them. Mitigation worth tracking: if attempt N+1 produces *identical diff to HEAD* (i.e., no fix applied) AND preflight passes on that attempt, treat as flake-clear and proceed; require this case to be logged explicitly so dogfood can distinguish legitimate flake-clears from missing fixes.

**Origin:** PR M push-further lens EXPLORATION (MODERATE signal); inspired by Magentic stall counter pattern (research §3.2).

### Goose's `load` vs `delegate` execution-mode verb split  *(MODERATE signal)*

**Surfaces when:** Anthropic ships any skill-to-skill or skill-to-subagent orchestration primitive in Claude Code, OR Block's Goose ships the `load`/`delegate` verb proposal ([Goose discussion #6202](https://github.com/block/goose/discussions/6202)).

**Direction:** Goose's proposal: unify recipes / skills / subagents under two execution verbs — `load` injects sources into current context ("Teach me this"); `delegate` executes sources in isolated subagents ("Do this for me"). *"The tool determines the execution mode, not the file format."* This would resolve Flow's emergent `Skill('a'); Skill('b')` pattern — currently undocumented by Anthropic — into a sanctioned primitive. If Anthropic reacts with their own version, Flow should adopt their primitive; if Goose ships theirs first and gains traction in the Claude Code ecosystem, Flow should consider adopting it for `/flow:ship` Step 2's reviewer invocations. Don't preempt; this is the most thoughtful public take on the orchestration question but signal is single-engineering-discussion-strength, not multiple-converged-sources.

**Origin:** Skill-chaining research pass 2026-05-27 (`dev-docs/research/agent-orchestration-2026-05.md` §7.3); PR M push-further lens flagged as forward bet.

### Network/infrastructure failure classification in Step 1c  *(WEAK signal)*

**Surfaces when:** A real Step 1c attempt fails because of network/disk-full (not code), AND the user reports the 3-attempt exhaustion was wasted budget — i.e., they wanted Step 1c to abort early on infrastructure failure rather than treat it as a fixable code failure.

**Direction:** Today Step 1c treats every non-zero non-127 exit as fix-attempt-worthy. A consumer running `npm test` that fails because `ECONNREFUSED` / `ETIMEDOUT` / `ENOSPC` (npm registry unreachable, disk full, etc.) burns the retry budget on attempts Claude can't possibly fix. Mitigation worth tracking: classify stderr matching `ECONNREFUSED|ETIMEDOUT|ENOSPC|EHOSTUNREACH` as `BLOCKER: infrastructure failure, not a code failure — fix the environment and retry` without consuming the retry budget (same fail-fast shape as exit 127). Weak signal because in practice these are rare during a /flow:ship invocation (developers don't usually have network failures mid-PR-shipping); preempting violates FB-0003.

**Origin:** PR M push-further lens EXPLORATION (WEAK signal).

### Markdown-lint preflight slot for docs-only PRs  *(WEAK signal)*

**Surfaces when:** A consumer reports wanting docs-only PRs to still run a mechanical check (markdownlint, vale, alex, cspell) even though Step 1c's docs-only early-exit skips the full preflight.

**Direction:** Step 1c skips preflight entirely on docs-only diffs (no source files per `sourceFilePatterns`). Some consumers ship documentation as a product surface (md-manager, documentation sites) and want mechanical checks at ship time. A `flow.config.json.docsPreflightCmd` slot would solve this without bloating the existing `preflightCmd`. WEAK because no consumer has asked yet; pre-empting violates FB-0003. Roadmap entry exists so we don't re-derive the design when/if the request lands.

**Origin:** PR M push-further lens EXPLORATION (WEAK signal).

### Eval fixture re-categorization (`evals/security/` → `evals/contract/`)  *(deferred design discussion)*

**Surfaces when:** A third contract-shape eval fixture is authored (currently 2: `test_preflight_retry.py` + the planned `test_status_markers.py` for PR N) — rule-of-three trigger for re-categorization.

**Direction:** PR M added `test_preflight_retry.py` under `plugins/flow/evals/security/`, but the file is a contract test (asserting SKILL.md text + schema slot shapes), not a security test (asserting no command injection / no path leak). Mis-categorization compounds — the next contract test will follow the precedent. Either (a) rename `evals/security/` to `evals/` and put contract tests at top level alongside `test_cwd_constraint.py` / `test_malicious_config.py`, OR (b) create `evals/contract/` and move `test_preflight_retry.py` there. Option (b) is cleaner but affects the `run_security_evals.py` runner (which auto-discovers via glob). Defer until the third contract fixture forces the call.

**Origin:** PR M push-further lens NIT (deferred for design discussion). PR N's `test_status_markers.py` will be the rule-of-three trigger.

### Dynamic-workflows adoption: segment-bounded fan-out between gates  *(alignment umbrella — direction-setting, not yet a PR)*

**Surfaces when:** (a) Anthropic moves dynamic workflows past research preview or changes the API/limits (currently: 16 concurrent / 1,000 total agents, no mid-run input, no script-side filesystem, `claude -p`/SDK auto-launch); OR (b) `/flow:staff-review` or `/flow:verify-build` orchestration is next touched; OR (c) a consumer hits review-context bloat on a large diff, or wants migration-scale (per-file) review coverage; OR (d) `ultracode` / `/effort` interaction with the loop is raised.

**The thesis (full report: [`dev-docs/research/dynamic-workflows-alignment-2026-06.md`](research/dynamic-workflows-alignment-2026-06.md)):** dynamic workflows are an *execution substrate*; Flow's doctrine (two human gates, four review lenses, loop-only-on-mechanical-exit, evidence-or-silence) is a set of *constraints on how that substrate is used*. The adoption shape is **segment-bounded: a workflow owns the fan-out BETWEEN two human gates and never spans a gate** (workflows forbid mid-run input — *"for sign-off between stages, run each stage as its own workflow"*). The loop's three workflow-able segments: **A** Clarify→Plan→critique (→ plan-approval gate), **B** Execute→preflight→simplify→staff-review→Present (→ Present gate), **C** ship pipeline (→ merge gate).

**Direction (prioritized; each its own future PR, not a monolith):**
- **O1 — port `/flow:staff-review` + `/flow:verify-build` to saved workflow scripts** (`.claude/workflows/`). Buys clean main context (only the triaged verdict returns), rerunnability, `args` by diff base; moves the deterministic aggregation rule from SKILL.md prose into the script (resolves the markdown↔JS fan-out risk for these two). **Preserve all four lenses as distinct phases (FB-0037).**
- **O2 — scale fan-out per-file/per-criterion** — keep the lenses as the role taxonomy, fan out per changed file, converge in the script. **Only when diff size earns the token cost (FB-0038).**
- **O3 — the real "voting": informed-independent refutation at scale** — NOT generic claim-voting. See the empirical entry below: blind refutation rubber-stamps and debate loops amplify bias; the untested promising variant (fresh agent + context + significance rubric) is what the workflow substrate enables, on UI diffs especially. Respect FB-0012 (single-pass convergence, never iterate-to-approval). Pairs with PR P.
- **O4 — reframe `workflow.md` around the three gate-bounded segments** (the doctrine update that makes O1–O3 safe).
- **O5 — `ultracode` interaction policy** — a workflow may own a segment but must terminate at a gate and surface its result; consider scoping `disableWorkflows` for segment C. Closes the gate-bypass risk; operationalizes FB-0038's no-blanket-ultracode rule.
- **O6 — parallelize the ship triad** (security ∥ a11y ∥ verify-build) once C is a workflow.
- **O7 — K1 reserved-numbers becomes a prerequisite** for any fan-out feedback synthesis (workflows have no file-locking; parallel FB-number writes race) — FB-0039.
- **O8 — preserve the human-review + self-learning artifacts (FB-0039):** Flow-run PR table (enrich with the saved-script path + per-phase token/agent summary), the companion HTML case-study (see the entry above — its natural data source is the verify-build JSON buffer), and the core-docs/FB/memory pipeline (a synthesis agent writes them; the script can't).

**Why not now:** research preview + this repo has no UI-bearing consumer to validate the design-lens fan-out (O2/O3) against. Direction-setting only; each O-item graduates to a lettered PR when its `Surfaces when` trigger fires. Do NOT pull the umbrella into one PR — it spans shipped-artifact, doctrine, and config surfaces that must ship and review independently (three-surface boundary + small-PR discipline).

**Origin:** user direction 2026-06-03 (dynamic-workflows alignment conversation); FB-0037/0038/0039 capture the three load-bearing preservation constraints.

### Dynamic-workflows-based review: re-test refutation across problem types, incl. UI  *(research-driven — re-test as the feature evolves)*

**Surfaces when:** (a) Anthropic ships a new dynamic-workflows version or moves it past research preview (the API/behavior changes), OR (b) Flow gains a UI-bearing consumer project to dogfood on, OR (c) any future reviewer-quality pass is run on a substantively different diff (large migration, genuinely-buggy pre-review diff, UI/a11y-heavy diff).

**Direction:** The 2026-05-28 reviewer-refutation spike (`dev-docs/research/dynamic-workflows-2026-05.md`; history entry "Reviewer-refutation spike — verdict") tested *blind* independent refutation vs PR J's self-disproof on **one** diff (`bootstrap.sh`, a shell script). On that diff, blind refutation refuted 0/15 (a rubber stamp) while self-disproof refuted 5/15 — because the false positives there were **significance** misjudgments (the mechanism is real, but doesn't matter under Flow's trust model), and blindness strips the context needed to judge significance. **This is one data point on one problem type — explicitly not a write-off.** Dynamic workflows are in research preview and will evolve; the result may differ on diffs where the dominant FP class is *verification* error rather than *significance* error.

Re-test specifically on:
- **UI projects** — a11y + design-engineer + visual findings may behave differently under refutation than shell-correctness findings; the significance-vs-verification balance is likely different (a contrast-ratio or focus-trap claim is more mechanically checkable than a "is this attacker-reachable" claim). This is the highest-value re-test and needs a UI-bearing consumer (none in flow's own repo).
- **Genuinely-buggy, pre-review diffs** — the spike reviewed an already-merged/clean file, which undersamples the "does refutation wrongly kill *real* findings" failure mode. Re-run on a diff with known-planted or known-historical bugs.
- **Larger / migration-scale diffs** — where dynamic fan-out (scale finders to diff size) is the actual draw, not just refutation.

The promising variant the spike pointed at (not yet tested): **informed-independent refutation** — a fresh agent *with* stance + project context (not blind) + a uniform significance/exploitability rubric — which would address both the rubber-stamp problem (blind) and the inconsistency problem (self-disproof gave opposite verdicts on the same issue across framings).

**Origin:** Reviewer-refutation spike 2026-05-28 (`dev-docs/research/dynamic-workflows-2026-05.md`); user direction to keep the direction alive and re-test across problem types incl. UI as dynamic workflows evolve, rather than write it off on one data point.
