# Feedback Log

User feedback synthesized into actionable guidance. When the user gives feedback -- corrections, preferences, reactions, direction changes -- the relevant insight is captured here so it shapes all future work.

This is not a transcript. Each entry distills feedback into a rule or preference that applies going forward.

---

## How to Write an Entry

```
### FB-XXXX: [Short summary of the feedback]
**Date:** YYYY-MM-DD
**Source:** user correction | user preference | user direction | review feedback

**What was said:** Brief, factual summary of the feedback.

**Synthesized rule:** The actionable takeaway -- what to do differently going forward.

**Applies to:** [areas this affects: ux, code, architecture, workflow, etc.]
```

### Numbering
Increment from the last entry. Use `FB-0001`, `FB-0002`, etc.

### Source types
- **user correction** -- user fixed something you did wrong
- **user preference** -- user expressed a stylistic or process preference
- **user direction** -- user set strategic direction or priorities
- **review feedback** -- issues found during code/design review

---

## Entries

<!-- Add new entries below this line, newest first. -->

### FB-0057: PR-body writes must use the REST PATCH endpoint with read-back, never `gh pr edit --body`; and triage dogfood feedback against current HEAD before fixing

**Date:** 2026-06-24
**Source:** review feedback (a health-tracker iOS consumer ran flow's full `/flow:ship` loop on v1.8.0 and reported six "FLOW-N" gaps; this is PR 1 of a 3-PR response)

**What was said:** Six gaps, highest-value first: (1) no post-merge doc-currency step — a merged PR's status never flips to `merged (#N)`; (2) `gh pr edit --body` silently fails on the Projects-classic GraphQL deprecation (`repository.pullRequest.projectCards`), so the PR body never updates; (3) `/flow:audit-coverage` crashes on its own zsh-eval'd snippet; (4) `extract-criteria.py` only matched a bold `**Spec-walk:**` heading and silently grabbed a different PR's criteria; (5a) `visualHistoryPath` can't adopt a hand-curated/markerless `visual-history.html`; (5b) §5c can't fire when the visual pass is blocked-at-ship but completes later; (6) VH-number collision with no reservation parity with FB. Triaging against current `main` (v1.10.0): **(3)** does not reproduce (reran the Phase-0 block under `zsh -c` and `zsh eval` → clean exit; fixed by PR #47's `while IFS= read`/`tr '\n' ' '` rewrite). **(4)** is closed (logic moved to `walk_extract.py`: matches `#{1,6}` headings + bold, active-block scoping, loud `empty_warning` — FB-0055). **(6)** is N/A for flow: `insert-visual-history.py` derives auto-deduped *slugs*, not `VH-####` numbers; the collision was the consumer's own hand-curated numbering scheme. **(1)/(5a)/(5b)** are genuinely open and already roadmap-flagged (lines 13, 88) — routed to PRs 2 (`/flow:land` post-merge step, closes 1+5b) and 3 (markerless visual-history adoption, 5a). This PR fixes **(2)**.

**Synthesized rule:** Two:

1. **Any flow skill that updates an EXISTING PR's body must use `gh api -X PATCH repos/{owner}/{repo}/pulls/<n> -F body=@file` (REST), never `gh pr edit --body`.** `gh pr edit` resolves `repository.pullRequest.projectCards` through the deprecated Projects-classic GraphQL path and exits 1 *without updating the body* on many repos — a silent failure (FB-0010) at an outward-facing surface, where the stale PR description then misrepresents what shipped. REST has no `projectCards` dependency. Pair the write with a temp-file body (sidesteps quoting + arg-length limits), a read-back assertion on a sentinel string, and a `[WARN]` on BOTH the non-zero exit and the missing-content case; never suppress stderr. (`gh pr create --body[-file]` at creation time is unaffected — the `projectCards` path is specific to `edit`; that's why `/flow:ship`'s LOCAL-ONLY create branch was never exposed, only the PR-OPEN body-*update* sites: `staff-review`, `ship`, and `ship-spike`.) The read-back catches an empty-body write but not a *stale* one (on a re-ship the sentinel header is already present) — the durable form is a per-write freshness token, routed to the roadmap.

2. **Triage consumer/dogfood feedback against current HEAD before fixing — a gap reported on version X may already be closed on `main`.** Half of these six were already-fixed (3, 4) or N/A (6); fixing from the report rather than the code would have re-touched closed surfaces and chased a numbering scheme flow doesn't use. Verify-then-fix: reproduce the claim against current code (run the snippet, grep the matcher, read the helper) before writing a line.

**Applies to:** `staff-review/SKILL.md` Step 7 + the §82 gh-safety note, `ship/SKILL.md` Step 7 PR-OPEN, `ship-spike/SKILL.md` Step 7 re-ship branch (a third site the original fix missed — caught by the staff-review fan-out lens, FB-0010); the FLOW-1/5a/5b roadmap follow-ups (post-merge `/flow:land` + markerless visual-history adoption), routed as separate PRs.

### FB-0056: A "this was verified" signal must be mechanically enforced with an untrusting default; and reduced rigor must require an EXPLICIT declaration, never be the silent fallback when the rigorous path can't run

**Date:** 2026-06-22
**Source:** user direction (a dogfood finding routed from a consumer iOS project, run through flow's full loop)

**What was said:** A real `/flow:ship` run on production SwiftUI code surfaced two source-level integrity holes in flow's own skills. (A) `render-test-plan.py` stamped every Test plan "checkbox state is the machine verdict from an adversarial fresh-context judge, not self-report" — but the findings buffer can be **hand-authored** by the implementing agent (no `**Spec-walk:**` block, or `extract-criteria.py` misfires), and the schema recorded no signal of *how* a verdict was produced, so the renderer stamped self-reported buffers as non-forgeable. (B) `verify-build` Step 2 fired **spike mode** (3 generic smoke checks) on a *missing plan*, and `ship` Step 1.0's "/simplify + /flow:staff-review ran" assumption "did not gate" — so a production, source-touching diff with no written plan got spike-grade verification + skippable reviews + a still-ready PR. The user chose the robust fixes: mechanical marker for the rigor gate, keep the no-plan path *judged*, one PR, roadmap the env-adjacent `gh` item.

**Synthesized rule:** Two durable disciplines, both instances of "enforcement > attestation" (FB-0047) applied to a new surface:

1. **A machine-trust signal needs a provenance field with an UNTRUSTING DEFAULT.** When a renderer/consumer claims "this green is a machine verdict, not self-report," that claim must be backed by a field recording *how* the verdict was produced (`provenance: adversarial-judged | spike-rubric | hand-authored`), set by the **judging step, never the implementer**, and **absent/unrecognized must read as un-judged** (`hand-authored`). A self-reported PASS renders a distinct state (`[~]` + a visible banner), never the machine `[x]`. The *omission* direction is then airtight; the residual *commission* seam (an author writing the trusted value) is a named honest-limitation + a roadmap follow-up ("second-source the stamp" against judge evidence) — don't claim cryptographic enforcement when it's a cooperative-agent contract.

2. **Reduced rigor must be EXPLICITLY declared, never a silent fallback.** "Disposable spike" and "production code that merely lacks a plan artifact" have opposite risk profiles — collapsing both to the low-rigor path because a plan is *absent* is the FB-0010 silent-skip class applied to the verification bar itself. Split them: spike's lower bar requires an explicit signal (`/flow:ship-spike`); a *missing plan on a source-touching diff* runs the **full judged path over diff-derived criteria** (so a green stays a real PASS) and routes to the draft manifest (declare criteria + re-verify, or human-waive). And the loop's "assumed a review ran" steps must *gate* on **mechanical evidence** (a commit-invariant marker written by the reviewer), not a printed assumption — for source-touching diffs, missing/stale evidence → draft, not a ready PR.

**Build-time lessons (carry forward):** (a) a contract change to a non-forgeable renderer is an FB-0010 fan-out — update every producer's stamping prose + every existing fixture + the inverse-direction eval in the *same* PR (an un-stamped fixture correctly flipped to `[~]` and had to be stamped). (b) A new eval harness that isn't wired into `ci.yml` provides **zero** standing protection — the "pinned by evals" claim is hollow until CI runs it (staff-review BLOCKER; the orphaned `run_visual_history_evals.py` was a prior instance of the same gap). (c) Share the mechanical primitive (the source-fingerprint logic) via one stdlib helper consumed by both the writer (staff-review) and reader (ship), don't duplicate the shell — FB-0054(b); and make the fingerprint **commit-invariant** (`git diff origin/<base>` vs the working tree, not `..HEAD`) so committing the reviewer's fixes doesn't false-trip the gate.

**Applies to:** `findings-schema.json` (`provenance`, `no_plan_fallback`), `render-test-plan.py` + `render-report.py` (provenance-aware rendering), `verify-build/SKILL.md` Step 2 (spike vs no-plan split + judged no-plan path), `ship/SKILL.md` Step 1.0a + Step 2 (rigor gate + no_plan_fallback routing), `staff-review/SKILL.md` (marker write), `rigor-marker.py`, the eval harnesses + `ci.yml`, FB-0047 (enforce-don't-attest), FB-0010 (fan-out / silent-skip), FB-0054(b) (share the primitive).

### FB-0055: Prefer the durable structural fix over an author-memory convention; decouple an independent capture path from a sibling extraction's success

**Date:** 2026-06-21
**Source:** user direction

**What was said:** Choosing how far to go on the Spec-walk routing fix, the user declined the lighter "warn + document the qualify-your-retained-headings convention" option and asked: "is option 2 what we ultimately want? do the most robust fix in line with our intent." I.e. fix the root structure, not paper over it with a convention that depends on authors remembering to qualify headings.

**Synthesized rule:**
1. **Robust over interim.** When a parser tolerates non-canonical input, prefer the structural fix (here: scope extraction to the active/first block) over a convention that relies on author memory to avoid breakage — the latter is the FB-0010 "consistency depends on author memory" smell. The interim "retained Spec-walk blocks MUST qualify their heading so they self-exclude" convention is now retired: the active PR's plan goes at the top, retained blocks are ignored, no qualification needed.
2. **Watch for co-dependent changes.** Loosening the heading match and scoping-to-first-block had to land *together*: under the old strict regex, retained blocks self-excluded *because* their qualified headings failed to match; loosening the match alone would have re-aggregated every stale block. When relaxing a matcher, check what previously depended on its strictness.
3. **Decouple independent pipelines.** An independent capture path (visual, §5a) must never be gated behind a sibling extraction's success (behavioral Spec-walk). The two declare separate blocks; coupling them let a behavioral-extraction failure silently drop the visual deliverable. Each gate gets its own predicate.

**Applies to:** workflow, code, architecture — `verify-build` lib parsers, §5a routing, plan-discipline conventions, and the general "robust-vs-convention" + "decouple independent gates" disciplines.

### FB-0054: Doc-currency must cover *project-declared* status surfaces, not just the hardcoded plan/roadmap pair — and the enforcement gate must fire WITHOUT a version manifest

- **Date:** 2026-06-19
- **Source type:** user direction (a dogfood finding routed from a consumer iOS project, run through flow's full loop)
- **What was said:** Dogfooding flow on a consumer iOS app, two sub-PRs into a phase its `CLAUDE.md` + `README.md` still read "Phase 2 — HealthKit is next" while Phase 2's first two sub-PRs had merged. `CLAUDE.md` auto-loads into every session, so a cold agent reads stale orientation and picks the wrong next action. The forward-looking docs `/flow:ship` *does* reconcile (`planPath` "Current Focus" + `roadmapPath` "Now") were correct — the drift lived in status surfaces flow had no way to know about. Root cause: Step 5a reconciled a *hardcoded* doc set; Step 5b asserted only a **version token** and **silently N/A'd** on projects with no `plugin.json`/`package.json`; and there was no slot by which a consumer could declare "these files also carry forward-looking status." Flow can't hardcode `CLAUDE.md` (flow's own repo has none; not every consumer uses one) — the only correct fix is a project-declarable mechanism.
- **Synthesized rule:** Forward-looking doc-currency (FB-0043's "stale direction should never happen") extends beyond the built-in plan/roadmap pair to **any status surface a project declares** via `flow.config.json.statusDocs` (array of `{path, marker}`, default `[]` → no behavior change for non-adopters). `/flow:ship` reconciles **only** the region between the HTML-comment fences `<!-- {marker} -->` … `<!-- /{marker} -->` — a narrow, mechanical edit, **never** a restructure (respects projects whose own rules gate broad `CLAUDE.md` edits behind a human; gives the gate a concrete target). Step 5a rewrites each region to just-shipped reality; **Step 5b adds a version-manifest-INDEPENDENT marker-coverage gate** that BLOCKS when the ship moved plan/roadmap status forward (the plan "## Current Focus" or roadmap "## Now" section changed vs base) but a declared region was left untouched — so non-versioned projects finally get real mechanical enforcement, not just the version-string check. `/flow:doctor` Check 2.7 verifies setup. Three durable sub-lessons from building it:
  - **(a) A gate that no-ops on a whole project class isn't a gate.** The old 5b silently emitted `N/A` on manifest-less projects — exactly the FB-0010 silent-skip class applied to enforcement itself. A coverage/currency gate must fire on the failing population (here: non-versioned projects), or it's theater for them.
  - **(b) Share the mechanical primitive; don't triplicate awk.** The marker-region logic is consumed by 5a, 5b, and doctor — extracted to one stdlib helper (`skills/ship/lib/status-docs.py`, with a `section` subcommand that also absorbs the version gate's inline `sect()` awk), pinned by an eval. Three inline copies would be the FB-0010 "consistency depends on author memory" fan-out the feature itself exists to prevent.
  - **(c) Name the false-positive case at the point of failure.** The "did the region change?" inequality over-fires when plan/roadmap status moved for a non-status reason; the BLOCKER copy must tell the operator the legitimate over-fire exists AND steer them away from the cosmetic-edit release valve (a hollow whitespace touch defeats the signal) — surfaced by the push-further lens. The normalize-region hardening (reject whitespace-only "reconciliation") is the roadmapped follow-up that closes that valve.
- **Applies to:** `flow.config.json.statusDocs` slot, `/flow:ship` Step 5a/5b, `/flow:doctor` Check 2.7, `skills/ship/lib/status-docs.py`, `docs/workflow.md` doc-currency section, FB-0043 (in-pipeline currency enforcement), FB-0010 (silent-skip + fan-out classes).

### FB-0053: The durable visual record is CREATED ON FIRST WRITE by the ship distill step, not bootstrap-scaffolded — reverses FB-0042(e)'s scaffold *mechanism* while preserving its intent

- **Date:** 2026-06-16
- **Source type:** user direction (approved fork at the V3b plan gate)
- **What was said:** FB-0042(e) and the roadmap acceptance (line 165) literally said "scaffold `visual-history.html` into `template/base/core-docs/` (uiSurface-gated)." Building V3b surfaced that the mechanism can't work as written: `bootstrap.sh` *creates* `flow.config.json` and copies `template/base/core-docs/*.md` — it runs *before* config is meaningful and globs only `.md`, so it can neither read `uiSurface` to gate nor pick up an `.html`. An unconditional copy would seed an **empty** `visual-history.html` into every consumer, including non-UI ones (violating FB-0007 "non-UI consumers don't get an empty doc"). Asked at the plan gate, the user approved reversing the mechanism to create-on-first-write, with the spec sources updated same-PR.
- **Synthesized rule:** The durable visual record is **created on first write** by `/flow:ship`'s Step 5c distill step — it seeds from a bundled lib skeleton (`skills/ship/lib/visual-history-skeleton.html`) into `visualHistoryPath` the first time a UI project ships a load-bearing visual decision — **not** scaffolded by `bootstrap.sh`. This preserves FB-0042(e)'s *intent* (uiSurface-gated, opt-in, no empty doc for non-UI consumers) by moving the gate to where `uiSurface` is actually known (ship time), instead of the one place it can't be (bootstrap, pre-config). General lesson: when a spec mandates scaffolding at install/bootstrap time but the gate depends on config that doesn't exist yet, prefer create-on-first-write at the first qualifying pipeline step — and when you reverse a governing FB's *mechanism*, update that FB + every cross-reference in the SAME PR (FB-0010 fan-out), recording the reversal as a new FB rather than silently editing the old one.
- **Applies to:** `flow.config.json` `visualHistoryPath` slot, `/flow:ship` Step 5c, `skills/ship/lib/insert-visual-history.py` + `visual-history-skeleton.html`, `bootstrap.sh` (what it must NOT do), FB-0042(e), the roadmap V3b acceptance.

### FB-0052: A human-facing artifact must be understandable on its own — plain-language copy, and a *realistic* demo (never synthetic placeholders, and never force a domain-specific demo onto a repo that has no instances of that domain)

- **Date:** 2026-06-15
- **Source type:** user correction
- **What was said:** To let the user exercise the new two-way verify-build report, the agent generated a demo on a non-visual repo (flow itself, `platform:library`) using synthetic colored-rectangle "screenshots." The user: *"this isn't really a visual PR, the html file is incredibly vague and I have no idea what I'm looking at … even still, the copy isn't clear or really understandable."* Two distinct misses: (a) demoing a screenshot-annotation feature on a repo with no real screenshots — fake frames obscure the mechanism instead of showing it; (b) the report's own chrome copy was jargon (`verify exit code: 0`, `18 verify calls`, `+1200ms`, `a11y_snapshot`, "How a verdict / a choice earns its place") — a reviewer shouldn't have to decode it.
- **Synthesized rule:** (1) When showing a feature to the user, use a *realistic* example, not synthetic placeholder content; and do **not** force a demo of a domain-specific feature (a visual-review tool) onto a project that has no instances of that domain (a non-visual library) — it confuses more than it demonstrates. If there's nothing real to point at, say so instead of fabricating one. (2) Human-facing output copy (the report a person reads to make the merge decision) must be plain-language and self-explanatory at a glance (the FB-0040 thesis) — keep internal jargon (exit codes, tool-call counts, raw ms offsets, enum-y type names, cryptic section headers) out of the chrome; gloss any tag/label the reader can't infer.
- **Applies to:** `/flow:verify-build` report (`render-report.py`) + any human-facing rendered artifact; agent ↔ user demos/walkthroughs; the FB-0040 "thinking, not approving" review thesis.

### FB-0051: When the stale-base gate reveals a parallel branch shipped most of the feature you're building, re-scope to the genuinely-additive delta — never ship a duplicate/competing renderer, skill, or slot
**Date:** 2026-06-15
**Source:** user direction + review feedback (the `/flow:ship` stale-base gate)

**What was said:** A full PR built this session (a standalone `/flow:walkthrough` skill + its own annotation layer + a new `verifyReportPath` slot + slot/skill-count fan-out + ship Step-6b wiring) was ~70% pre-empted by **PR #45** ("V2/V3a") merging to main mid-session — #45 independently shipped the V2/V3a rendered-capture renderer (`render-report.py`, read-only), the `verifyReportPath` slot (same name), the `grounding`/`open_questions` buffer fields, and the Step-8 gate. The `/flow:ship` stale-base gate surfaced the collision; the user directed re-scoping to **only the genuinely-additive delta** (the two-way click-to-pin annotation layer, layered onto #45's renderer) rather than shipping the duplicate. This is the 6th+ parallel-work collision the reserved-feedback-numbers log records — recurrence-backed, not a one-off.

**Synthesized rule:** When the stale-base gate (or a rebase) reveals a parallel branch has shipped most of a roadmapped feature you are building, **STOP and re-scope to the genuinely-additive delta** — reset to main, discard what already shipped (even if it was built + staff-reviewed this session), and contribute only the net-new part layered onto the merged work. Do **NOT** ship a duplicate / competing renderer, skill, or slot: it conflicts at merge, duplicates capability, and violates the anti-duplication bar (FB-0010 fan-out / FB-0015 "check what exists first"). The cheapest insurance against wasted parallel work is to check the roadmap item's status + open branches **before** building; the stale-base gate is the backstop that catches it at ship — treat its signal as a re-scope trigger, not an obstacle to route around.

**Applies to:** `/flow:ship` stale-base gate, roadmap-driven feature work, the reserved-feedback-numbers collision protocol, FB-0010 (fan-out / duplication class), FB-0015 (check existing surfaces before drafting).

### FB-0050: Visual capture for verification must be a11y-state-GATED — snapshot the a11y tree and assert the intended state BEFORE the screenshot, never screenshot-then-assume; and a "drive to each state" step must name a drive ladder, never assume drivability the MCP may not expose
**Date:** 2026-06-11
**Source:** review feedback (a cold `/flow:verify-build` behavioral-gate run that tripped the defect)

**What was said:** The flow-true behavioral gate for V2 (a cold, author-bias-free `/flow:verify-build` run against a real iOS app) caught a real defect that static tests + the author's hand-driving missed. SKILL §5a told the agent to "capture a frame" and to "write a `screenshot` observation AND an `a11y_snapshot` observation" as **two independent captures**, never ordering them. The agent screenshotted a state without first asserting it via the a11y tree; the frame had silently drifted to a different state; the fresh-context pairwise judge **correctly returned FAIL** and cited the exact pixel difference. Re-capturing a11y-gated (snapshot → assert state → screenshot) then resolved to PASS. The same run surfaced that §5a's "drive the app to each state" assumes a UI-drive primitive the MCP config may not expose (this XcodeBuildMCP config had only screenshot + a11y, no tap/type).

**Synthesized rule:**
1. **Capture must be a11y-state-gated, in order: snapshot the a11y tree → assert the intended state is present → THEN screenshot.** Never screenshot-then-assume — an un-gated capture persists wrong-state frames that look plausible. This is the SV2 "trust the a11y tree, not the pixels" principle applied to *capture ordering*, not just text-reading. A state that cannot be a11y-asserted is `Unknown` + `not_tested`, never a captured guess.
2. **A "drive the app to each state" step must name a drive ladder** (platform UI-automation tool → a documented launch-arg/env state hook → can't-reach ⇒ `Unknown`) and must never assume drivability a given MCP config provides. Many configs expose capture + a11y but no drive primitive; then only the launch state is reachable and the rest are honestly `Unknown`.
3. **General:** the cold-run lesson reinforces FB-0049 — a verification tool's prose is only proven when a fresh agent follows it literally against a real surface; "two independent captures" read fine to the author and broke on contact.

**Applies to:** `/flow:verify-build` §5a capture, any screenshot-based verification, the SV2 a11y-trust principle, FB-0016, FB-0049.

### FB-0049: A verification/quality tool is not validated until it RUNS against a real surface — static contract tests + hand-driven mechanism checks are Potemkin self-validation; and never conflate output-format with capture-platform
**Date:** 2026-06-11
**Source:** user direction (a pointed question that corrected an in-progress shortcut)

**What was said:** Finishing V2 (the verify-build rendered-capture + HTML-walkthrough feature), Claude proposed shipping PR-1 on the strength of (a) passing static contract eval fixtures (greps that the SKILL prose + schema are present) and (b) Claude hand-driving the screenshot MCP + the renderer itself to prove the mechanism. The user asked: *"which one is more true to the intention of the flow workflow?"* — surfacing that neither proves the **skill drives the mechanism**, only that the parts work. Earlier in the same session the user also corrected a conflation: the renderer's HTML is an **output format**, not the **capture platform** (the app is iOS, captured via XcodeBuildMCP; "web-first" was a render-vs-capture muddle).

**Synthesized rule:**
1. **A verification or quality tool is not validated until it RUNS against a real surface — skill-driven, ideally cold (author-bias-free).** Passing static contract tests + hand-driving the underlying mechanism proves the *parts* work, not that the *tool drives them*. That gap IS the Potemkin / hallucinated-success class verify-build exists to catch — and shipping verify-build's own PR on static+hand-driven evidence would fail it by its own standard. This sharpens FB-0016 ("real surface") and FB-0012 ("static ≠ behavioral"): for a verification tool, "real surface" means *the skill executing end-to-end*, not the mechanism poked by hand.
2. **If the behavioral gate is genuinely unavailable in this session** (session-bound, e.g. the cold run needs a consumer-project context), the flow-true move is a **DRAFT PR with the behavioral gate in the NOT-READY manifest** (FB-0034) — never a merge-ready PR, and never "ship now, validate later" (which defers discovery past the Step-8 gate the loop forbids).
3. **Distinguish output-format from capture-platform.** "Renders to HTML/web" describes the artifact's output, not what's being captured/verified. Don't let an output format leak into platform assumptions.

**Applies to:** `/flow:verify-build` + any verification/quality tooling, the Step-8 readiness predicate, FB-0016 (real-surface validation), FB-0034 (draft-routing), FB-0012 (static ≠ behavioral), dogfooding flow on itself.


### FB-0048: Under-declaration is the load-bearing half of "enforce that the work was done correctly" — a coverage audit flags diff behavior no declared criterion covers, routed to draft; best-effort, not a deterministic guarantee
**Date:** 2026-06-11
**Source:** user direction (continuation of FB-0047; "proceed with PR 2")

**What was said:** After FB-0047's Test-plan render shipped (v1.5.3), the user directed PR-2 to close the staged second half: under-declaration. The render makes *declared* verification unforgeable, but a behavior the agent changed without declaring a Spec-walk criterion is never tested — the Test plan is honestly all-green while the change ships unverified. The user's standing autonomy bar held: "as long as the plan has passed audit and critique gates, you should proceed."

**Synthesized rule:** Enforcing "the work was done correctly" has two halves — *declared criteria are verified* (verify-build → rendered Test plan, FB-0047) AND *the declared set is complete* (no undeclared behavior). The completeness half is inherently LLM-judgment (you can't deterministically enumerate "what behaviors did this diff change"), so it is a **reviewer routed to draft**, not a mechanical hard gate (FB-0012: never hard-gate / iterate on LLM judgment). `/flow:audit-coverage` (v1.6.0) compares the source diff against the declared `**Spec-walk:**` criteria and flags behavior no criterion covers → `[decision-required]` → draft manifest → resolve by declaring + verifying, or human-waive. Reuse over rebuild: a new "Undeclared change" category on the existing `auditor` agent (the mode-selected-subset pattern), `extract-criteria.py` for declared criteria, the existing draft-routing. **Honest limit:** best-effort — it raises the completeness bar, it does not deterministically guarantee it (false negatives possible), and it does not catch *vacuous* criteria (criterion-quality is verify-build's axis — roadmap follow-up). State the limit where it's read (README + the reviewer output), so a clean `coverage=ran` isn't over-trusted. General lesson reinforced: **dogfood the actual mechanism** — the coverage bash looked correct but a live smoke test caught that zsh doesn't word-split `$FILES`, so `git diff -- $FILES` silently saw an empty diff; a static review would have shipped a no-op reviewer.

**Applies to:** workflow, ship pipeline, `audit-coverage`, `auditor.md`, autonomy bar, FB-0010 (dogfood-the-mechanism + fan-out for a new skill)

### FB-0047: A near-autonomous loop must *enforce* that testing was done before the human, not self-attest it — the PR Test plan is a non-forgeable projection of machine verdicts, never a hand-checked box
**Date:** 2026-06-11
**Source:** user direction

**What was said:** The user asked why the `## Test plan` checkboxes in flow PRs arrive unchecked, and pushed past the first proposal (have the agent check boxes it verified): for the "human quickly verifies testing was done, then merges" workflow to work, the workflow must *enforce* that the work was actually done correctly — an agent self-checking a box is the Potemkin/self-report class `/flow:verify-build` exists to kill. As much testing/validation as possible should complete *before* the human sees the PR; the human's job collapses to confirm-and-merge. The user also set the autonomy bar for this work explicitly: "as long as the plan has passed audit and critique gates, you should proceed" (full implementation + ship without further check-ins, once both gates were clean).

**Synthesized rule:** A human-facing "it was tested" signal must be a mechanical function of machine evidence, never agent narration. The PR `## Test plan` is rendered (by `skills/ship/lib/render-test-plan.py`, ship Step 7) from the `/flow:verify-build` findings buffer: checkbox state = the per-criterion `aggregated_verdict` (PASS→`[x]`; FAIL/Unknown→`[ ]` + the judge's reason), with evidence + a one-line headline verdict so the human confirms-and-merges. Reserve `[ ]`/`[x]` exclusively for machine verdicts (the `not_tested` residue renders as plain bullets, never checkboxes). When no current buffer exists (verify-build skipped / no buffer / stale buffer whose branch+sha ≠ HEAD / malformed), render an honest "no behavioral gate ran — manual verification required" fallback; **never** a forged green or a stale render. General principle: enforcement > attestation; surface a green only when an adversarial fresh-context judge produced it. Two honest limits to carry: the attestation is **behavioral/text only** (not visual — Deliverable-quality V2) and covers only **declared** Spec-walk criteria (closing under-declaration is the staged PR-2, FB-0048). When rendering machine-extracted strings of unknown provenance into a human-facing artifact (Markdown/HTML), escape the metacharacters — buffer text can carry content an app-under-test emitted and the judge narrated (security + design-engineer review, two reviewers, same session).

**Applies to:** workflow, ship pipeline, `render-test-plan.py`, verify-build buffer consumers, autonomy bar, security (output escaping)
**Date:** 2026-06-09
**Source:** user direction (incl. a correction of a prior dismissal)

**What was said:** On a proposed staff-review-of-the-plan, the user gave two steers. (1) **Push-further at the plan stage must not grow scope/functionality** — frame it as "could the *quality* be higher," not "could we add more"; in most cases raise the craft bar, not the feature set. (2) The user **disagreed** that a UX-designer lens adds no value before pixels exist: "the value is not in pixels but in experience, which is the most important thing… Maybe it's more of a product designer (or even design-minded product manager) than a strict UX designer, but experience is the most important thing here and should be a quality gate for plans." This corrects an earlier (wrong) framing that dismissed a plan-stage experience lens as needing pixels to be useful.

**Synthesized rule:** The plan gate's two existing reviewers (auditor, plan-critic) are **conformance** checks — *is the plan honest and aligned?* Add a **quality/ambition layer** of two lenses that run alongside them (skippable only when they genuinely don't apply, e.g. a backend-only plan, the same way diff-stage lenses skip):
- **Experience lens (product-designer / design-minded PM).** Is this the *right experience*, and is its ambition high enough? The journey, the edge states, the friction, how it should *feel*, whether the plan solves the experience problem or just satisfies the literal request. This is pre-pixels and is the **highest-value plan-stage question** — experience is the most important thing.
- **Push-further (quality, not scope).** Could the *craft/quality of the declared scope* be higher? Inherits the existing push-further lens's "uncommon care" framing (limited scope to an extraordinarily high bar; "nothing to push" is a valid, often-correct output), with a **loud anti-scope-creep guard** because the plan stage is where "push further" is most tempted to add features: raise the bar of the declared scope; propose new functionality only when it is load-bearing for the stated goal.

These set the success-criteria + craft bar the autonomous iteration loop (FB-0044) converges toward — a weak plan ceilings the deliverable. (A staff-engineer "is the approach sound before we build it" lens is a defensible secondary; held unless requested.) Best substrate is a workflow that fans the plan reviewers out and returns one triaged verdict — exactly the canonical "draft/judge a plan from several angles" workflow use case (dynamic-workflows O1 applied to the plan gate / segment A).

**Applies to:** plan gate (auditor + plan-critic surface), `plan-critic.md`, `plan-discipline.md`, `planner.md`, Visual-walk / declared success criteria, FB-0037 (designer perspectives load-bearing), dynamic-workflows O1, Deliverable-quality track.

### FB-0046: Experience and craft-ambition are first-class plan-gate quality gates — a product-designer / experience lens + a push-further-on-quality (not scope) lens, alongside the auditor + plan-critic
**Date:** 2026-06-09
**Source:** user direction (incl. a correction of a prior dismissal)

**What was said:** On a proposed staff-review-of-the-plan, the user gave two steers. (1) **Push-further at the plan stage must not grow scope/functionality** — frame it as "could the *quality* be higher," not "could we add more"; in most cases raise the craft bar, not the feature set. (2) The user **disagreed** that a UX-designer lens adds no value before pixels exist: "the value is not in pixels but in experience, which is the most important thing… Maybe it's more of a product designer (or even design-minded product manager) than a strict UX designer, but experience is the most important thing here and should be a quality gate for plans." This corrects an earlier (wrong) framing that dismissed a plan-stage experience lens as needing pixels to be useful.

**Synthesized rule:** The plan gate's two existing reviewers (auditor, plan-critic) are **conformance** checks — *is the plan honest and aligned?* Add a **quality/ambition layer** of two lenses that run alongside them (skippable only when they genuinely don't apply, e.g. a backend-only plan, the same way diff-stage lenses skip):
- **Experience lens (product-designer / design-minded PM).** Is this the *right experience*, and is its ambition high enough? The journey, the edge states, the friction, how it should *feel*, whether the plan solves the experience problem or just satisfies the literal request. This is pre-pixels and is the **highest-value plan-stage question** — experience is the most important thing.
- **Push-further (quality, not scope).** Could the *craft/quality of the declared scope* be higher? Inherits the existing push-further lens's "uncommon care" framing (limited scope to an extraordinarily high bar; "nothing to push" is a valid, often-correct output), with a **loud anti-scope-creep guard** because the plan stage is where "push further" is most tempted to add features: raise the bar of the declared scope; propose new functionality only when it is load-bearing for the stated goal.

These set the success-criteria + craft bar the autonomous iteration loop (FB-0044) converges toward — a weak plan ceilings the deliverable. (A staff-engineer "is the approach sound before we build it" lens is a defensible secondary; held unless requested.) Best substrate is a workflow that fans the plan reviewers out and returns one triaged verdict — exactly the canonical "draft/judge a plan from several angles" workflow use case (dynamic-workflows O1 applied to the plan gate / segment A).

**Applies to:** plan gate (auditor + plan-critic surface), `plan-critic.md`, `plan-discipline.md`, `planner.md`, Visual-walk / declared success criteria, FB-0037 (designer perspectives load-bearing), dynamic-workflows O1, Deliverable-quality track.

### FB-0045: Craft-iteration is a permitted judgment-loop *under four guards* — refining FB-0012's correctness-only prohibition on iterating to a reviewer's approval
**Date:** 2026-06-09
**Source:** user direction (doctrine reconciliation)

**What was said:** The iterate-don't-stop direction (FB-0044) requires the agent to loop against a craft/experience bar — which is *judgment*. FB-0012 ("bounded-retry loops may loop only on mechanically-verifiable exit codes, never LLM-judgment outputs") could be over-read to forbid exactly the agentic craft iteration the autonomy goal (FB-0041) depends on. The two are reconcilable: FB-0012's prohibition targets iterating to a reviewer's *approval for correctness*, where a false pass hides a bug and a transcript-only judge is gameable. Craft-iteration is a different risk profile.

**Synthesized rule:** Iterating against *judgment* is **permitted for craft/quality** (distinct from FB-0012's prohibition on iterating to a *correctness* reviewer's approval) **if and only if all four guards hold**: (1) the judge is **independent** — fresh context, ungameable by persuasion; (2) it evaluates against **declared criteria** (the plan's Spec-walk / Visual-walk / craft bar), not open-ended taste; (3) it sees **real artifacts** (V2's captured frames, the a11y tree, tool output), never the worker's narration — this is the guard V2 unlocks and the one most often missing today; (4) the loop is **budget-bounded** with the **human merge gate** as the final backstop. Absent any guard, fall back to FB-0012 (loop only on a mechanical exit code). In practice the control-flow driver keys on the **verify-build verdict** — itself an exit-code summary of guarded judgment — so the iteration stays FB-0012-shaped at the loop layer even though craft quality is judged underneath. This also governs any future workflow "voting" (O3) and the verify-build judges themselves, not just the iterate loop.

**Applies to:** workflow (Execute/Present iteration), `verify-build` judges, FB-0012, FB-0044, FB-0041, dynamic-workflows O3 ("voting"), Deliverable-quality track (V2 is guard #3's precondition).

### FB-0044: Low confidence during Execute is a signal to *iterate*, not to stop — the agent iterates against the plan's success criteria + craft bar until the design is genuinely good, then ships; only a genuine *preference fork* escalates
**Date:** 2026-06-09
**Source:** user direction

**What was said:** When the agent executes and isn't fully confident, it must NOT just stop. The user wants consistent agentic iteration to make the design genuinely good *before* opening the PR — grounded in strong success criteria + a craft bar established in the plan ("agentic iteration is critical here, based on the strong success criteria and craft bar that need to be established in the plan"). This refines (and corrects) an earlier framing that an uncertain agent should ship a draft early: design uncertainty is something the agent should iterate *through*, not hand off prematurely.

**Synthesized rule:** When the agent is not fully confident at Execute/Present, the **default is to iterate** against the plan's declared success criteria + craft/experience bar — never a premature stop, never a premature draft. Split FB-0011's escalation on a clean line:
- **Quality gap** ("not good *enough* yet") → **iterate.** The agent closes this itself; iteration is the dominant behavior, and its ceiling is set by how strong the plan's criteria + craft bar are.
- **Preference fork** ("not sure which *way* you want it" — a one-way-door, or two comparable directions only the human's taste resolves) → **escalate.** No amount of craft resolves a preference; only the human does.

Reserve **stop-before-PR** for genuine one-way-door decisions where even a draft would prejudice the human's choice; otherwise escalation routes INTO a draft PR + NOT-READY manifest (FB-0034), so the human always enters at the PR, never mid-loop. **Safety precondition:** craft-iteration loops on *judgment*, which is honest — not reward-hacked (cf. FB-0012's prohibition on iterating to a *correctness* reviewer's approval) — only when the judge sees **real captured artifacts (V2)**, not the worker's narration, against **declared criteria**, under a **bounded budget**, with the **human merge gate** as the final backstop. So safe autonomous craft-iteration is **V2-gated**; the loop driver should key on the verify-build verdict (a Stop-hook or `/goal` anchored to a mechanically-demonstrable PASS), never on open-ended taste.

**Applies to:** workflow (Step 8/9 loop), autonomy bar (FB-0011), Deliverable-quality track (V2 is the precondition; FB-0041 the umbrella), draft-routing (FB-0034).

### FB-0043: Doc-currency must be automatic *in the ship pipeline*, never reliant on manual `/flow:doctor` — proactively keep roadmap + plan current every ship; stale docs should never happen
**Date:** 2026-06-05
**Source:** user direction (workflow-improvement conversation)

**What was said:** "We should be proactively improving our workflow all the time — make the pipeline account for keeping the plan and roadmap fully up to date as part of the pipeline; this stale-docs issue should never happen." Then, on a draft that put the mechanical check in `/flow:doctor`: "is the doctor addition secondary, or will we rely on it? isn't doctor only run manually? I don't want to have to invoke this manually — it should be handled automatically; but if it fits in that skill anyway then we can keep it."

**Synthesized rule:** Forward-looking docs (roadmap "Now", plan "Current Focus") are part of the ship contract, not optional hygiene — a cold reader (incl. the autonomous loop, which is a cold agent each run) relies on them to know what to do next, so stale direction is the FB-0010 fan-out class applied to *what to work on*. Enforcement must be **automatic and in-pipeline** (a `/flow:ship` gate that fires every ship), never dependent on a human remembering to run a manual skill. A manual skill (`/flow:doctor`) may carry a *secondary* mirror if it fits naturally, but is explicitly NOT the enforcement. And: proactively harden the pipeline itself as part of doing the work — when a process gap surfaces (e.g. the dev-side `/ship` forgetting to clear shipped FB reservations), fix the pipeline so it can't recur, don't just patch the instance.

**Applies to:** `/flow:ship` Step 5 (5a reconciliation + 5b gate), dev-side `/ship`, `/flow:doctor` (Check 2.6, secondary), `workflow.md`, the doc-currency discipline; the meta-principle of proactively hardening the pipeline.

### FB-0042: The durable visual record is a single curated `visual-history.html` — the picture companion to the existing history core doc; lean committed screenshot assets (CSS/SVG reconstruction as the honest fallback), reverse-chronological, decision-centric, no italic headings
**Date:** 2026-06-04 (reconciled 2026-06-05 against merged health-tracker #10 + flow #37)
**Source:** user direction (reversed a "skip it" recommendation; then reconciled to the merged reference implementation)

**What was said:** The user directed adding a durable visual record as a Flow core doc (reversing the blueprint's § 4 "skip it"), then — reviewing #36 alongside flow #37 and the **merged** health-tracker **PR #10** — asked to ensure the best aspects of each land with no drift. #10 is the reference implementation of the durable record + the two-artifact model; this entry is aligned to what #10 actually shipped, not the earlier `.md`+`.html` / "schematic-only" sketch.

**Synthesized rule:** Flow's consumer scaffolding gains an opt-in durable visual record, serving the FB-0040 + FB-0041 (#37) north stars as the **V3 distillation target** of the Deliverable-quality track. Five disciplines, taken from #10's merged shape:

```
(a) Two CO-EQUAL artifacts, never conflated. The per-run verify-build report
    (O8 / the Deliverable-quality track's V3 renderer) is EPHEMERAL — the
    human-FEEDBACK surface: exhaustive evidence across the full declared
    Visual-walk state set PLUS the "open questions for you" (the decisions/
    tradeoffs needing human input), opened at the merge gate, then discarded.
    The visual record is DURABLE — the curated visual subset (only decisions
    that changed the user's read of a surface), committed, grown over the
    project's life. The ephemeral report is not an afterthought; it FEEDS the
    record: at /flow:ship the load-bearing visual decisions (the grounding that
    changed the user's read + the this-iteration questions the human resolved)
    are distilled into one entry, then the report is thrown away. Both must be
    built — the ephemeral renderer AND the durable record AND the distill bridge
    (see the contract table in the blueprint § 4).

(b) A SINGLE curated `visual-history.html`, the PICTURE companion to the
    EXISTING history core doc (flow.config.json.historyPath). NOT a new
    `visual-history.md`, NOT a `.md`+`.html` pair — the written timeline is
    already history.md; this is its visual sibling. (Corrects the earlier
    sketch: #10 has no separate `.md`; it `git mv`'d case-study.html →
    visual-history.html as the one durable visual record.)

(c) Lean COMMITTED screenshot assets, NOT schematic/screenshot-free. Real
    captures preferred — resized keeper images (~≤720px) on relative paths in
    a `visual-history-assets/` dir, write-once + curated (churny galleries
    stay in the ephemeral report). A faithful CSS/SVG reconstruction is the
    HONEST fallback when capture isn't available (e.g. a no-simulator Linux/
    web container), labelled as such, using real values. NOT base64-embedded
    (that's the ephemeral report's mechanism; the durable record references
    assets so git stays healthy). (Corrects the earlier "schematic, zero PNGs"
    rule — #10 commits lean JPEGs; the underlying intent was repo-health, which
    lean assets serve better than schematic-only.)

(d) Curated + decision-centric, reverse-chronological, no italic headings.
    Newest entry at the top (reviewable without scrolling); an interactive
    anchor-link TOC. Each entry is a prominent DECISION (not a PR dump),
    carrying PR#/date/branch metadata, grounding (the user need + decision
    test, or the design-language / craft-commitment rationale), a key
    before/after, and questions carried forward. NO italics in headings
    (health-tracker FB-0006 — applies to authored artifacts, not just app UI).

(e) uiSurface-gated, opt-in. Created only for uiSurface=true projects —
    non-UI consumers (FB-0007) don't get an empty doc. Visual-scoped, not
    generalized to ADR-style decision-history.
    [MECHANISM UPDATED by FB-0053, v1.8.0]: the original "scaffold into
    template/base/core-docs via bootstrap" wording was reversed to
    CREATED-ON-FIRST-WRITE by the /flow:ship Step 5c distill step (seeded
    from a lib skeleton). bootstrap.sh runs before flow.config.json exists,
    so it can't gate on uiSurface; create-on-first-write moves the gate to
    where uiSurface is known. Intent (uiSurface-gated, no empty doc)
    unchanged.
```

Citations resolve from `specPath` / `designLanguagePath` slots — never hardcoded project doc names (project-agnostic quality bar). New slot: `visualHistoryPath` (the `.html` companion to `historyPath`). The grounding + "open questions" disciplines this record distills are the same ones #10 keeps as prose in its `visual-walkthroughs.md` and that #36's blueprint encodes as the verify-build buffer's `grounding` + `open_questions` fields.

**Relationship to the other in-flight work:**
- **#37 (FB-0041)** is the umbrella — the autonomous-deliverable north star whose chain is V1 `Visual-walk` plan field → V2 rendered capture → V3 HTML walkthrough → V4 proactive-error loop. FB-0042 is the *durable-record* half of V3 (the ephemeral renderer is the other half). FB-0042 was renumbered from a colliding FB-0041 to sit above #37's.
- **#10 (merged, health-tracker)** is the reference implementation this entry mirrors. flow's version is the project-agnostic generalization.

**Encoding constraints:**
- FB-0003 (schema-without-implementation): don't land `visualHistoryPath` / the template file until a producer writes the record and `/flow:ship`'s distill step reads it — same PR.
- FB-0016 (re-test new capability on UI before generalizing): land it against a real UI surface (health-tracker is the available fixture) before declaring the entry shape stable.

**Applies to:** `template/base/core-docs/`, `flow.config.json` slots (`visualHistoryPath`), `/flow:ship` distill step, the roadmap "Deliverable-quality track" V3 + the O8 entry, the future renderer PR, the two-gate model (durable record written at ship; FB-0035 visual sign-off folds into merge).

**Origin:** the visual-verification blueprint (`dev-docs/research/visual-verification-blueprint-2026-06.md`). Reversal of § 4's "skip it" recorded 2026-06-04; reconciled to #10's merged shape + #37's track 2026-06-05.

### FB-0041: The goal state is an autonomous high-quality deliverable — agent self-iterates against behavioral *and* visual success criteria, then presents a PR + HTML walkthrough; human gives little/no low-level feedback over time
**Date:** 2026-06-05
**Source:** user direction (goal-state / roadmap conversation)

**What was said:** Articulated the target the managed-autonomy loop is converging toward: human + agent collaborate on a plan → agent gets first-gate approval → agent builds and self-iterates autonomously against the plan's success criteria (functional AND visual) → when confident the plan is fully addressed and the visuals are good, the agent runs the ship flow, auto-fixes issues that surface, and opens a PR with a clear human-readable description + the `## Flow run` per-step table → **and presents, alongside the PR, an HTML file that is a concise visual walkthrough of what was built** (highlighting changed visuals/interactions/features, complementing the PR with more detail + visuals). Human reviews those deliverables at the merge gate and merges or gives feedback (mostly visual/UX). The feedback loop (agents during review + humans, **human precedence on disagreement**) should let the agent proactively check its work against past logged errors so most issues are fixed *before* the human reviews — trending over time toward "ready to merge with little/no feedback." Explicit preference: **no third gate before ship** — the agent self-iterates and polishes low-level issues itself so the human only sees high-quality output.

**Synthesized rule:** Treat the autonomous high-quality deliverable as the north star for the loop. Investment priority is the chain that makes it safe to keep the human out of the pre-ship loop: (1) structured *visual* acceptance criteria in the plan, (2) rendered capture + baseline so visual confidence is a real PASS not an Unknown, (3) the HTML walkthrough deliverable, (4) the consumer-side proactive-error loop. Preserve exactly two human gates (plan approval, merge); never add a third pre-ship gate — close the quality gap by strengthening the behavioral+visual gate, not by re-inserting the human. Human feedback outranks agent feedback on disagreement.

**Applies to:** workflow, architecture, ux, roadmap (the Deliverable-quality track in `roadmap.md`), verify-build, staff-review (design-engineer lens), `/flow:ship`.

### FB-0040: Human-review value model (north star) — surface intent / assumptions / subjective questions / rationale FOR the human; automate implementation from clear intent; catalogue feedback + decisions to improve the process
**Date:** 2026-06-03
**Source:** user direction (dynamic-workflows alignment conversation — stated as the goal the other constraints serve)

**What was said:** "we're working towards maximizing the value of human review (grounding decisions in user needs, making assumptions clear, raising subjective questions for the human to give input on, and having rationale for everything, then automating the implementation based on clear intent and cataloguing feedback and decisions for future reference to improve the process)."

**Synthesized rule:** This is the **north star** that FB-0037 (designer lenses), FB-0038 (cost-aware workflow use), and FB-0039 (preserve review/learning artifacts) all serve — and the lens through which every dynamic-workflows adoption decision should be judged. Human review is most valuable when spent on **intent, assumptions, subjective judgment, and rationale** — not on mechanical implementation. So the loop's job is to:

```
(a) Ground decisions in user needs (cite the need/spec/intent).
(b) Make assumptions explicit and confidence-rated (existing: confidence
    verdicts; LOW auto-gates, MEDIUM surfaces at Present).
(c) Raise SUBJECTIVE questions for human input — the things a machine
    shouldn't unilaterally decide (taste, priority, one-way doors). Use
    AskUserQuestion-style surfacing at a gate, not a guess.
(d) Carry rationale for everything (existing: history.md "why" + tradeoffs,
    plan confidence verdicts, two-citation reviewer evidence).
(e) THEN automate implementation from clear intent (the autonomous interior
    between gates).
(f) Catalogue feedback + decisions for future reference to improve the
    process (existing: feedback.md FB-entities, memory pipeline, history.md).
```

**Load-bearing consequence for dynamic workflows:** because a workflow takes **no mid-run input**, every assumption and subjective question a segment depends on must be surfaced and resolved **at the gate that precedes it** — never deferred into the fan-out interior (which can't pause to ask) and never silently guessed. This is the operational tie between this value model and the segment-bounded adoption shape (O4/O5): gates are where (a)–(d) happen; the workflow interior is where (e) happens; (f) is the workflow's durable output (FB-0039). Maximizing human-review value is therefore NOT "more gates" — it's making the two existing gates carry richer, better-grounded, assumption-explicit, subjectively-informed decisions.

**Applies to:** the whole managed-autonomy loop, dynamic-workflows adoption (esp. O4 segment doctrine + O5 ultracode policy), confidence-gate doctrine, plan/Present gates, AskUserQuestion usage, history.md + feedback.md + memory cataloguing, FB-0037/0038/0039 (this is their shared root)

### FB-0039: The human-review + self-learning artifacts are load-bearing outputs that must survive dynamic-workflows adoption — Flow-run PR table, companion HTML case-study, and the core-docs + FB-entity + memory pipeline
**Date:** 2026-06-03
**Source:** user direction (dynamic-workflows alignment conversation)

**What was said:** "the format of human review and self learning from feedback (pr structure and companion html files showing visual changes, as well as flow's core docs system and feedback entities) is very important, and I want to preserve that as we adopt dynamic workflows."

**Synthesized rule:** When porting any Flow stage to a native dynamic workflow, the *artifacts* the stage produces are part of its contract, not incidental output. Three must survive untouched (or be strengthened):

```
(a) The per-step `## Flow run` PR table (FB-0019) — the loop's execution made
    legible on the PR page. A workflow can ENRICH it (fold in the saved-script
    path + per-phase agent/token summary from /workflows) but never replace it
    with a turn-by-turn transcript or a bare "ran a workflow" line.
(b) Companion HTML case-study reports + visual history showing visual/
    behavioral changes — the rendered page a human opens before the merge gate.
    ASPIRATIONAL, NOT YET SHIPPED: this is a roadmap VISION ("Verify-build HTML
    case-study report", PR-R-successor candidate), not a baseline to build on.
    What IS shipped: /flow:verify-build (PR Q, v1.3.0) — behavioral verification
    that captures some screenshot / a11y-tree observation; its JSON findings
    buffer is the intended data source for the future HTML report. Visual
    sign-off folds into the merge gate (FB-0035), never a third human gate.
    Treat the rich visual artifacts as a target the workflow direction should
    enable, not as an existing surface to preserve.
(c) The core-docs (history/plan/roadmap/spec) + FB-entities + memory self-
    learning pipeline. A workflow script CANNOT write files directly (script ≠
    filesystem); a synthesis agent must. Under fan-out, multiple agents writing
    feedback race on FB numbers — so PR K1's reserved-numbers protocol becomes
    LOAD-BEARING, not optional, the moment feedback synthesis fans out.
```

The general principle: dynamic workflows isolate intermediate results in script variables and return only a final answer — which is a context win, but means the durable human-facing + self-learning surfaces must be explicitly produced as the workflow's outputs, or they silently disappear.

**Applies to:** dynamic-workflows adoption, `/flow:ship` PR-body + feedback synthesis, verify-build HTML report, core-docs discipline, FB-collision protocol (K1), memory pipeline

### FB-0038: Adopt dynamic workflows to their fullest where fan-out scale earns it — but never force a workflow when a single subagent pass suffices; token/cost is a first-class constraint
**Date:** 2026-06-03
**Source:** user direction (dynamic-workflows alignment conversation)

**What was said:** "I want the flow process to be able to use dynamic workflows to the fullest extent, but I don't necessarily want to force it off [if] it's not necessary. I want to keep token efficiency and cost in mind."

**Synthesized rule:** A dynamic workflow spawns many agents and costs meaningfully more tokens than the same task in conversation. Treat "should this be a workflow?" as a **workflow-worthiness predicate**, analogous to the Step-8 ship-readiness predicate — not a default. A workflow earns its cost when fan-out scale adds real value (large/migration-scale diffs, codebase-wide audits, per-file or per-criterion coverage, cross-checked research). For a small diff or a focused task, a single subagent pass (the current primitive) is the cheaper, correct choice. Two durable sub-rules:

```
(a) No blanket ultracode. Do not set /effort ultracode as a standing default
    for this repo's work — it turns every substantive task into a workflow,
    multiplying cost AND risking the gate-bypass in FB-TBD/ultracode policy.
    Reach for a workflow per-task when scale warrants it.
(b) Keep the existing cost gates. Flow's per-diff skip-paths (FB-0006/0007),
    stale-base preflight (FB-0008), and verifyBudgetCalls cap are the cost-
    consciousness model; a workflow port inherits them, it doesn't discard them.
    Gauge spend on a small slice before a large run (docs guidance).
```

**Applies to:** dynamic-workflows adoption strategy, ultracode policy, `/flow:staff-review` + `/flow:verify-build` ports, cost-of-review discipline, FB-0006/0007/0008 lineage

### FB-0037: Designer perspectives are load-bearing in the loop — the ux-designer / design-engineer / push-further lenses must survive dynamic-workflows adoption, not collapse into a generic reviewer
**Date:** 2026-06-03
**Source:** user direction (dynamic-workflows alignment conversation)

**What was said:** "flow's structure intentionally centers designer perspectives, which I want to preserve even as we fully adopt workflows."

**Synthesized rule:** Flow's review surface deliberately carries three design-oriented lenses (`lens-ux-designer`, `lens-design-engineer`, `lens-push-further`) alongside the engineering lens, plus the `designLanguagePath` doc they read from. When `/flow:staff-review` (or any review stage) is ported to a native dynamic workflow, these remain **distinct, named phases** — the workflow fans out *more* coverage per lens (e.g. per-file), it does not merge the four lenses into one general-purpose reviewer to save agents. The `reviewLenses` config slot is the opt-out mechanism (with a documented reason in the plan), not a default-collapse. Design and UX review catch a different class of issue than engineering review; the four-lens triangulation is the value, and it is exactly what fan-out should amplify, never flatten.

**Applies to:** `/flow:staff-review` workflow port, `lens-*` agent definitions, `designLanguagePath`, `reviewLenses` slot, dynamic-workflows adoption

### FB-0036: All flow reviewer skills + ship-spike are model-invocable; the only two human gates are plan approval and PR merge — no skill is itself a gate
**Date:** 2026-06-01
**Source:** user direction (managed-autonomy confidence conversation)

**What was said:** "all skills should be auto invocable — the only human gates are final plan review and PR merge (so the skills/stages shouldn't handle these specifically, but they should be able to get up to that point autonomously)."

**Synthesized rule:** Flip `disable-model-invocation: false` on `audit-plan`, `audit-completion`, `critique-plan`, and `ship-spike` (`/flow:ship` already done in PR S / FB-0018). Reviewers are review *passes*; `ship-spike` opens a PR but never merges — none is a gate, so forcing a human to hand-type them was an artificial stop. Three durable sub-rules:

```
(a) Docs must stay in LOCKSTEP with the flag (FB-0010 fan-out): after any
    flip, zero "MANUAL"/"user-invocable"/"hand-typed" survivors for these
    four in README/workflow.md. The flag and the label are one contract.
(b) Model-invocable ≠ cold-start. The three reviewers fire WITHIN a driven
    loop (at the plan/present gates), not on a cold "build me X". Preserve
    that cold-start-honesty in the docs — label them BOTH (auto + typeable),
    not a bare AUTO that implies they self-start.
(c) ship-spike auto-advance is JUDGMENT-gated, not predicate-gated. Unlike
    /flow:ship (which auto-advances on a mechanical verify-build PASS), a
    spike's "done?" is a judgment. That's acceptable (spike code is
    disposable, never merges, human-reviewed) — do NOT invent a fake
    mechanical predicate to make it look symmetric with ship.
```

**Load-bearing dependency:** the three `context: fork` reviewers only work if `extract_session.py` can find the session transcript from a worktree (dotted-path) cwd — broken until #33 (v1.4.2) fixed slugify + added a `CLAUDE_CODE_SESSION_ID` primary. Without #33 in the base they auto-invoke but audit nothing. (Fork-path parity verified PASS once #33 is present.)

**Applies to:** the four skills' frontmatter, README + workflow.md invocation labels, FB-0010 fan-out discipline, the two-gate model, FB-0018 reconciliation

### FB-0035: verify-build discovery belongs at the readiness boundary; ship-time verify-build is a confirmation re-run (refines FB-0018(b))
**Date:** 2026-06-01
**Source:** user direction (managed-autonomy confidence conversation)

**What was said:** "do we want verify-build before ship? if any iterating needs to be done based on visual review, that should probably be treated as something to dial in before we decide it's ready to ship." The "ship it" decision should mean "I've seen it work," not "go find out if it works."

**Synthesized rule:** Behavioral + visual *discovery* runs at the Step 8/9 readiness boundary, before the ship decision (the auto-advance predicate already requires a verify-build PASS there). At `/flow:ship` Step 2, verify-build is a **confirmation re-run** — a non-converging FAIL/Unknown means a *regression since readiness* → FB-0012 bounded mechanical fix, else route to the draft manifest (FB-0034). This **refines FB-0018(b)**: ship's gate no longer "halts pre-PR on FAIL/Unknown" — it routes to a draft pre-PR, preserving (and strengthening) the invariant *no merge-ready PR on a non-PASS build*. **Visual sign-off folds into the merge gate** (agent dials in pre-PR against plan-declared visual criteria; the authoritative human look is the PR preview) — never a third human gate. General rule: anything that can produce *iteration* runs before the ship decision; anything inside ship is a pass/fail *confirmation*, never a loop.

**Applies to:** `/flow:verify-build`, `/flow:ship` Step 2, `workflow.md` Step 8/10, FB-0018 reconciliation, UI-project visual workflow

### FB-0034: Ship-time blockers resolve to {auto-fix in-tree | draft-PR + NOT-READY manifest} by resolution-confidence — escalation routes INTO the merge gate, never a silent proceed or a hard mid-loop halt
**Date:** 2026-06-01
**Source:** user direction (managed-autonomy confidence conversation)

**What was said:** JTBD — the loop should run autonomously and "shouldn't stop arbitrarily unless it's for a good reason that we outlined in the workflow." On the risk: "are there cases (like security issues discovered in ship flow) where there is reasonable uncertainty about which way to proceed, that could result in a best-effort open PR that isn't ready to merge?" — yes; and an unresolved blocker should surface *at* a designed gate, not halt the loop or ship a not-ready-looking PR.

**Synthesized rule:** Every ship-time reviewer BLOCKER carries a **resolution-confidence** tag orthogonal to severity: `[auto-fixable]` (one clear, mechanically-verifiable fix) or `[decision-required]` (multiple valid fixes / out-of-repo action / un-auto-fixable). **Default to `[decision-required]` when unsure** (FB-0011 ESCALATE-by-default). `/flow:ship` routes auto-fixable → fix in-tree; decision-required (and non-converging verify-build regressions) → a **draft PR + pinned `🚫 NOT READY TO MERGE` manifest**. Three outcomes only — auto-fix, draft-route, or follow-up — **never a silent proceed and never a hard mid-loop halt.** The draft is the mechanical NOT-READY signal the human merge gate trusts; the manifest is the human-readable one. The escalation routes *into* an existing gate (merge), not a new one — this is the operational form of the two-gate thesis (the only human gates are plan approval + merge; automatic escalations route into them).

**Applies to:** `/flow:security-review`, `/flow:accessibility-review`, `/flow:verify-build`, `/flow:ship` Step 2/7, future reviewers, autonomous-gate design, the two-gate model

### FB-0019: PR descriptions should document the full per-step flow-loop run, not a generic Reviews line — and the per-step honesty rule cuts both ways (never imply a step ran that didn't; never imply one was skipped that ran)
**Date:** 2026-06-01
**Source:** user direction (stated while dogfooding flow on another project)

**What was said:** Dogfooding flow on another project, the user wanted richer PR descriptions: the PR body should document the full flow-loop run — every step that ran, which steps were skipped and *why* (spike/tiny mode, no UI surface, etc.), and any significant decision or change each step produced. A step with nothing notable shows "—" with no manufactured filler. The user's request included a conditional ("if security/a11y are not-yet-shipped in this flow version, say so") that, on inspection, evaluates false in v1.4.x — those reviewers ship and run; the plan-critic caught that carrying the clause forward unconditionally would instruct the agent to write "skipped — not yet shipped" for steps that actually execute.

**Synthesized rule:** A flow PR body documents the loop's *execution*, not just its reviews. The canonical shape (`/flow:ship` §7) is a `## Flow run` table — one row per loop step, each marked `✓` (ran) or `skipped (<reason>)` with the reason always named, and a **Notable** cell carrying genuine signal or `—`. Three durable sub-rules:

```
(a) Honesty cuts both ways. Never imply a step ran when it didn't (the
    original failure mode), AND never imply a step was skipped when it ran
    (the inverse). "skipped — not yet shipped" is reserved for a step
    genuinely absent from the running flow version; it is NOT a synonym for
    a runtime-config skip (doc-only / uiSurface:false / verifyEnabled:false
    / platform library|none) and must never be written for a step that
    executed. When a user request carries a conditional ("if X is true,
    say Y"), evaluate the condition against the current codebase before
    encoding it as an unconditional instruction.

(b) No manufactured notes. A routine step gets "—". An invented
    "improved error handling" line is worse than an honest blank — it
    erodes the signal the table exists to carry.

(c) The table points at follow-ups; it does not home them. Deferred
    follow-ups stay canonical in the roadmap/plan docs (existing doctrine);
    the table's closing line only references that they exist. The PR is
    still never merged by Claude.
```

The skip-reason vocabulary is duplicated across four surfaces (`ship/SKILL.md` §7, the dogfood `.claude/skills/ship/SKILL.md`, `ship-spike/SKILL.md`, `workflow.md` §10) — treat it as an FB-0010 fan-out contract: grep the skip strings across all four after any wording change.

**Applies to:** `/flow:ship` + `/flow:ship-spike` PR body, workflow.md ship narration, PR-description quality, FB-0010 fan-out discipline

**Validation:** Encoded in PR T (v1.4.1). The plan-critic's REDIRECT on the "not-yet-shipped" conditional (sub-rule (a)) is the concrete catch that motivated making the honesty rule bidirectional rather than one-directional.

### FB-0018: `/flow:ship` should auto-invoke when ready — the autonomous loop's human gates are plan + merge, not "ship it"; but auto-ship requires a behavioral PASS, not just absence-of-failure
**Date:** 2026-05-30
**Source:** user direction (stated while reviewing why /flow:ship was manual-only)

**What was said:** "don't we want ship to be auto invocable? that's necessary to get to an autonomous coding loop ... the human gates are supposed to be plan and merge right?" On the follow-up scoping question — for projects where `/flow:verify-build` is skipped (library/none platform, doc-only diff) and there is no behavioral gate — the user chose **keep auto-ship MANUAL** there (default-to-ESCALATE), reserving auto-advance for cases with a real behavioral PASS.

**Synthesized rule:** The Flow loop's two load-bearing human gates are **plan approval (Step 2)** and **merge (Step 11)** — nothing else should require a human keystroke by default. `/flow:ship` is therefore auto-invocable: the agent auto-advances from Step 8 when the ship-readiness predicate holds (spec-walk complete, no open BLOCKER, no unresolved MEDIUM/LOW assumption, `/flow:verify-build` returns **PASS** — not merely "didn't fail") and the FB-0011 risk gate is clear. Two hard constraints when extending any auto-ship behavior:

```
(a) The readiness signal must be a positive behavioral PASS, not absence-of-
    failure. If verify-build is skipped (no runnable target), there is no gate
    → stay MANUAL. Never treat "nothing failed" as "ready."
(b) verify-build (mechanical, Step 2) — not the model's self-assessment of the
    predicate — is the load-bearing boundary. The predicate decides whether to
    ENTER ship; ship's own gate re-confirms and halts pre-PR on FAIL/Unknown.
```

This is FB-0011 (autonomy bar) applied to the ship-invocation decision: act autonomously only on a clear, low-risk, mechanically-confirmed signal; otherwise stop and present.

**Applies to:** `/flow:ship` invocation, workflow.md Step 8, autonomous-gate design, future widening of auto-ship scope (e.g. when adding behavioral gates for currently-skipped platforms)

### FB-0017: Document the skill catalog in loop order and mark auto-fire vs manual-typing + gate locations — a non-expert can't map an importance-ordered list onto the workflow
**Date:** 2026-05-30
**Source:** user direction (stated while reviewing flow's own README for production-readiness)

**What was said:** Reviewing how ready flow is for other projects, the user asked for "a full overview of the expected user experience when they open a Claude session with this plugin installed and try to build something, assuming they aren't an expert in the plugin and don't manually invoke skills" — what fires automatically, what they must call themselves, what advances step-to-step, where the pauses are — and directed: "make sure this is clearly indicated in the readme. right now, the skills aren't listed in workflow order, which is confusing."

**Synthesized rule:** When documenting flow's (or any flow-using project's) skill surface for adopters, the catalog must:

```
(a) List skills in LOOP ORDER (the sequence the user moves through), not
    alphabetical or perceived-importance order.
(b) Mark each skill's invocation: AUTO (self-fires) / MANUAL (you type it;
    disable-model-invocation:true) / BOTH (typed or called by ship/triggered
    on a diff). State plainly which high-value skills are MANUAL.
(c) Mark the human pauses (plan gate, merge gate, LOW-confidence gate) and
    mechanical stops at their steps.
(d) Include a blunt cold-start note: on a bare "build me X" with no commands,
    only the auto-loading rules attach — nothing executable fires until typed.
```

The gap to avoid: framing flow as a "managed-autonomy loop" while the docs leave a non-expert unable to tell what runs on its own vs what they must invoke. Honesty about the typed-command reality beats aspirational framing.

**Applies to:** README / consumer-facing docs, workflow.md, onboarding, `/flow:workflow-help` output

### FB-0016: A negative spike result on a new or fast-evolving capability is one data point, not a verdict to abandon — record a re-test trigger (across un-sampled problem types, incl. UI) instead of writing it off
**Date:** 2026-05-28
**Source:** user direction (stated during the dynamic-workflows reviewer-refutation spike)

**What was said:** The spike returned a negative result — blind independent refutation did not cut the reviewer false-positive tax on one shell-script diff (`bootstrap.sh`). The user directed: write the verdict honestly, but ALSO put it on the roadmap to re-test later with different problem types — "this feature is going to evolve so we don't want to completely write it off yet ... it will be important to test in some other projects with UI as well." Earlier in the same session the user also insisted the experiment run on "something useful and substantive where I will be able to judge the result," and steered the spike's scope to its highest-signal, lowest-cost shape.

**Synthesized rule:** When a spike, eval, or experiment yields a negative or surprising result about a **new or fast-evolving capability** (research-preview features, freshly-shipped primitives, anything still changing under us):

```
(a) Record the result honestly in history.md WITH the named limitation that
    bounds it (one diff / one problem type / already-reviewed-clean target /
    single-model / etc.). A conclusion is only as general as the sample.

(b) Do NOT treat one data point on one problem type as a general verdict to
    abandon the direction. Create a roadmap § Exploration entry with a
    `Surfaces when:` trigger to re-test as the capability matures — and
    enumerate the problem types NOT yet sampled (UI surfaces especially,
    genuinely-buggy / pre-review diffs, larger/migration scale).

(c) Capture the most promising untested variant the experiment pointed at,
    so the re-test starts ahead of where this one ended (here: informed-
    independent refutation + a significance rubric, vs the blind variant).

(d) Scope experiments to substantive, human-judgeable targets up front — a
    trivial or unjudgeable target produces a result you can't trust either way.
```

**Applies to:** spikes + research passes, evaluating new Claude Code / Anthropic capabilities (dynamic workflows, future primitives), roadmap § Exploration hygiene, history.md verdict entries.

**Validation:** First applied to the 2026-05-28 reviewer-refutation spike — verdict recorded in `history.md` ("Reviewer-refutation spike — verdict") with its single-diff limitation named, and re-test direction captured in `roadmap.md` § Exploration ("Dynamic-workflows-based review: re-test refutation across problem types, incl. UI"). See `dev-docs/research/dynamic-workflows-2026-05.md`.

### FB-0015: Check bundled Claude Code skills before drafting any new flow skill
**Date:** 2026-05-28
**Source:** user correction (surfaced during PR Q `/flow:verify-build` planning)

**Note on numbering:** Cascaded through multiple collisions: drafted as FB-0010 → FB-0012 → FB-0013 → FB-0014, finally FB-0015. FB-0013 reserved by PR P (same-model critic collusion); FB-0014 claimed by PR R (init-skill additive-defaults). Each renumber was a polite deferral to existing plan-documented reservations. K1's claim-time protocol (reserved-feedback-numbers.md) is what made the collisions visible before merge; PR Q's slot is now claimed.

**What was said:** During PR Q (`/flow:verify-build`) planning, drafted a 20+-file skill spanning 5 platform runners (web/ios/android/tauri/cli), a `platform-detect.sh` lib, a `verify-judge.md` subagent, and per-platform schema slots. User asked whether this overlapped with the bundled `/verify` skill. It did, substantially: bundled `/verify` already does "run app + observe behavior," bundled `/run` already does platform detection across CLI/server/TUI/Electron/browser-driven/library buckets, and bundled `/run-skill-generator` scaffolds per-project launch recipes that `/run` and `/verify` automatically defer to. All three are listed in the harness available-skills section at every session start. CLAUDE.md explicitly forbids parroting bundled skills ("Never wrap a bundled Claude Code skill"). The first-pass draft violated this rule and would have shipped ~15 files of execution-layer duplication.

**Synthesized rule:** Before drafting any new `/flow:*` skill, audit the harness available-skills list for bundled skills that already cover the same surface. For each overlapping skill, identify what flow-specific value the new skill adds beyond the bundled one (config-slot integration, gate-shaped contract, feedback routing, in-flow context). If the delta is genuinely orchestration-only, the new skill becomes a thin wrapper (~5–6 files, 150-line SKILL.md) that delegates execution to the bundled skill — same pattern `/flow:security-review` and `/flow:accessibility-review` already follow. If the delta is null, drop the skill and reference the bundled one directly from `workflow.md` (the `/simplify`, `/batch`, `/debug`, `/loop`, `/claude-api` precedent).

Concrete pre-planning check: search the system-reminder "available-skills" section at session start; grep for the proposed skill's core verb (verify, run, audit, review, ship, plan, build, test); if a match exists, justify the wrapper with substantive added value or drop the skill.

This is a class lesson: the harness gives this information for free at every session start, and missing it is purely a discipline failure. Pair with FB-0010's pre-edit grep discipline — same "look before you write" shape, different layer (consistency across files vs duplication of capability).

**Applies to:** workflow, skill design, plan discipline, scope discipline

**Validation:** PR Q first-pass draft (then numbered PR M) proposed `lib/{web,ios,android,tauri,cli}-runner.md` + `lib/platform-detect.sh` + `agents/verify-judge.md` — all of which duplicate work bundled `/run` + `/verify` + `/run-skill-generator` already do. Caught at adversarial-review time by user question; redraft shrinks PR Q from 20+ files to ~6 by leaning on bundled skills as the execution layer.

### FB-0012: Bounded-retry agent loops must loop only on mechanically-verifiable exit codes, never on LLM-judgment outputs; oscillation detection via diff-hash is mandatory on top of the iteration cap
**Date:** 2026-05-27
**Source:** user direction (synthesized from research pass + design discussion before PR M)

**What was said:** User asked whether `/loop` and goal-iteration primitives belonged in flow's review/quality workflow, and whether iteration could plateau or oscillate. The honest answer surfaced two distinct design rules: (1) loops are productive when the exit signal is an external tool's exit code (typecheck pass, test green, lint clean); loops are *harmful* when the exit signal is another LLM's judgment ("the auditor approved," "the reviewer says it looks good") because they teach the writer to phrase around the reviewer rather than fix substance — exactly the reward-hacking failure mode that passive-review-with-evidence-or-silence is designed to prevent. (2) A bounded iteration cap (N=3) alone is insufficient — a session can oscillate between fix-A-then-fix-B until exhaustion without converging. Diff-hash on top of the cap catches pure A↔B↔A oscillation cheaply.

**Synthesized rule:** Bounded-retry contracts in any flow skill MUST satisfy three conditions to ship:

```
(a) The exit signal must be mechanically verifiable — an external tool's exit
    code, a regex match on stable text, a file-existence check. NEVER the
    output of an LLM-judgment step (reviewer "approved", auditor "clean",
    plan-critic "APPROVED"). If the exit signal is another model's call,
    keep the step single-pass and rely on the human merge gate.

(b) The iteration cap must be paired with an orthogonal abort condition.
    Diff-hash equality (sha256 of `git diff HEAD` against prior attempts)
    is the canonical cheap detector — pure oscillation aborts before the
    cap exhausts. The cap and the orthogonal check are NOT redundant: the
    cap catches *drift* (each attempt different but all broken); the hash
    catches *oscillation* (an attempt repeating a prior diff).

(c) The contract must explicitly forbid reward-hacking fixes: "do not
    modify or disable tests to silence preflight; do not add @ts-ignore /
    # noqa / eslint-disable / @SuppressWarnings or equivalent suppressors."
    Prompt-level guards are probabilistic; the human merge gate is the
    backstop, but the contract should not produce escape hatches by
    default.
```

When designing the next bounded-retry block (if any), inherit these three conditions from `/flow:ship` Step 1c as the canonical contract. Do NOT copy-paste the prose if a second block lands — extract to `plugins/flow/docs/retry-contract.md` and reference (preempts the loud-warning-copy-dedup shape from PR-2 FOLLOW-UPs).

**Applies to:** workflow design, agent-loop contracts, /flow:ship + /flow:ship-spike Step 1c, any future bounded-retry primitive

**Validation:** Encoded as the load-bearing design call of PR M (v1.2.6). Independently converged with Microsoft Magentic's `max_stall_count` primitive (Magentic counts consecutive non-progressing rounds; Flow detects exact-diff oscillation — same defensive shape, different detector). Research sources: Anthropic's "Building Effective Agents" (evaluator-optimizer pattern requires "stopping conditions ... to maintain control" + "explicit success criteria"); 2026 Agentic Coding Trends Report ("without explicit success criteria, verification becomes guesswork"); Claude Code's own scheduled-task docs ("be explicit about what success looks like ... the task runs autonomously, so it can't ask clarifying questions"). The "loop only on mechanical signals" call is the cure for the reward-hacking failure mode that loops-over-LLM-judgment invite — same shape as why flow's reviewers are passive ("evidence or silence") rather than active. See `dev-docs/research/agent-orchestration-2026-05.md` for the full industry survey supporting this rule.

### FB-0011: Autonomy bar — act when clearly best-practice + low-risk + no competing options; otherwise stop and present
**Date:** 2026-05-27
**Source:** user direction (stated during PR J planning conversation, in response to the REDIRECT question about red-team BLOCKER auto-fix vs stop-and-present)

**What was said:** Asked whether `/flow:ship` should auto-apply red-team BLOCKER fixes in-tree (faster, more autonomous) vs stop and present them for explicit user approval (slower, safer for one-way-door choices), the user gave a nuanced hybrid: *"If there is a solution that is clearly aligned with best practices as well as the spec/intent of the project and there is little risk in implementing it, then that should be done automatically. If the path forward is unclear, there are still significant risks, or there are competing options that are significantly different that both have merit, or there are one-way door decisions that need to be made, then the implementation should stop and wait for human review."*

**Synthesized rule:** In the Flow workflow's autonomy direction, an agent may act autonomously ONLY when ALL three hold: (1) the action is clearly aligned with best practices, (2) clearly aligned with the project's spec/intent (cite the rule/doc), (3) implementation risk is low (mechanical fix, single-file, recoverable). Stop and present to the user when ANY hold: the path forward is unclear; significant risks remain; competing options of comparable merit exist; or the decision is one-way-door.

This extends the existing **confidence-gate doctrine** ([[user-confidence-gates]] in workflow.md § "Confidence gates" — HIGH proceeds, MEDIUM surfaces at step 8, LOW auto-blocks) into auto-fix routing. The connection is direct: LOW-confidence assumptions can't proceed without explicit user resolution; analogously, a finding whose fix would constitute a LOW-confidence change can't auto-apply without explicit user resolution.

**Encoded as:**
- Per-finding `Fix-confidence:` field on `/flow:red-team` output schema (ships PR K) with values `AUTO-FIX-SAFE` (all three "act" conditions hold) vs `ESCALATE` (any "stop" condition holds). Default to `ESCALATE` when in doubt — false positives on stop-and-present cost the user a moment of attention; false positives on auto-fix could corrupt safety-critical code.
- `/flow:ship` Detection-Point-3 routing (ships PR L): `AUTO-FIX-SAFE` findings auto-apply in-tree, re-run preflight + red-team, ship if clean (cap at 4 iterations per the research diminishing-returns curve). `ESCALATE` findings stop the ship and surface to the user with full two-citation evidence + suggested fix.
- Conservative AUTO-FIX-SAFE category list (starts narrow; grows only with dogfood evidence). Initial examples: committed secret → delete + add to .gitignore; outbound HTTP→HTTPS upgrade; missing input validation that follows an existing in-repo pattern verbatim.
- Project-memory entry at `~/.claude/projects/-Users-benyamron-dev-flow/memory/feedback_autonomy_bar.md` (cross-session reminder; this FB entry is the consumer-shipped canonical version).

**Applies to:** workflow, autonomous gates, /flow:red-team (PR K), future Execute-stage gates, future /flow:staff-review BLOCKER triage, /flow:ship orchestration

**Validation:** Stated explicitly by the user 2026-05-27 during PR J planning; saved to project memory same day; encoded into PR J's plan as the PR-L Detection-Point-3 routing rule. PR L ships the mechanical enforcement. (Originally planned as PR-K Detection-Point-3 routing; renumbered to PR L after the parallel PR I collision required a PR J → PR K → PR L cascade.)

### FB-0010: Consistency discipline — silent-skip on edge case + fan-out contradiction are the two flavors that survive single-pass review
**Date:** 2026-05-26
**Source:** review feedback (synthesized retrospectively after 6 occurrences across PRs 1, B, D, E, F-pass-1, F-pass-2)

**What was said:** Across the consumer-feedback PR sequence (A → F), the same bug class kept surfacing in adversarial review — always *after* the engineer-lens or simplify pass that should have caught it. The class has two distinct shapes that share one root cause:

1. **Silent-skip on edge case.** Code that fails on an edge case without surfacing the failure. The path silently degrades instead of erroring loud. Examples:
   - PR 1: stale `core-docs/` paths in `/flow:critique-plan` defaulted empty, gave the plan-critic zero reference docs, never warned.
   - PR B: `DEFAULT_BRANCH=` unset triggered downstream `origin/..HEAD` parsing as a literal string, failed silently in the stale-base check.
   - PR D: regex inversion in the per-diff early-exit always matched, so every diff falsely tripped the "no source files" gate.
   - PR E: POSIX `[ ]` test with a bash-only `${arr[@]}` expansion would have produced empty stdin to `grep` and silently taken the false-OK branch in non-bash shells.
   - PR F pass-1: `/flow:doctor` Checks 1.1/1.2/3.2 invoked `/plugin marketplace list` and `/help` inside `Bash` blocks — shell can't resolve slash commands, would have returned empty stdin and INVERTED every check.

2. **Fan-out contradiction.** A contract value (a count, a name, a slot) referenced in N places, where a contract change only updated some of them. The remaining stale references contradict the new ground truth. Examples:
   - PR F pass-2: PR D added 2 schema slots (sourceFilePatterns + uiFilePatterns), bringing the total from 14 → 16. PR F left 5 places still saying "14 slots" (README ×2, CLAUDE.md.template, doctor/SKILL.md, bootstrap.sh).
   - PR F pass-2: `/flow:doctor` SKILL.md said "exits 0 only when all checks pass" at line 22, but line 260 said "not an exit code, since skill bodies are agent prompts not processes." Internal contradiction inside one file — same PR fixed the bottom but not the top.
   - PR F pass-2: README workflow-surface header said "10 user-visible skills" but the table had 11 rows (the new `/flow:doctor` row from this PR).

**Common root cause:** *consistency that depends on author memory*. Both shapes survive engineer-lens review when the reviewer is reading the diff (which looks self-consistent) without grepping the codebase for related references. Both shapes survive `claude plugin validate` because the manifest is syntactically clean. Both shapes survive `/simplify` because the per-file shape is fine.

**Synthesized rule:** Treat consistency across files as a first-class review concern, not an emergent property. Four concrete defenses:

1. **In review prompts (consumer-shipped).** `lens-staff-engineer` should explicitly grep for stale references after any contract change. Pattern: "the diff claims contract X (e.g., 'N slots', 'flag --foo deprecated', 'now reads from config.bar'); grep the codebase for residual references to the OLD form and flag survivors." Make this explicit in the lens prompt rather than implicit in "specifically asks."

2. **In mechanical checks (consumer-shipped).** `/flow:doctor` should compare derived counts against documented counts when both are cheap to introspect — e.g., schema slot count vs the integer in any `flow.config.schema.json` reference. A WARN beats a wait-for-adversarial-review.

3. **In project-dev rules.** A `Consistency discipline` section in `.claude/rules/general.md` reminds future sessions: when changing a count, name, or slot, **grep first, edit second.** Specifically: `git grep -nE '<old-value>' -- '<file-types>'` before staging, and treat every survivor as a fix that ships with the contract change, not a follow-up.

4. **In skill code (consumer-shipped).** Silent-skip class — pair every `2>/dev/null || true` / `// empty` / `|| echo ""` with an explicit positive assertion that the value is non-empty before the consumer uses it. If unset is acceptable, branch explicitly with a `[WARN]` / `[SKIP]` log line; if unset is fatal, exit with a clean message at the entrypoint (FB-0009 fail-fast pattern generalized).

**Applies to:** workflow, review prompts, doctor checks, project-dev discipline, all shipped skills

**Validation:** **9 incidents across 8 merged PRs** (as of PR I, v1.2.4 — kept current; if you find a 10th, update this line plus the incident count in `plan.md` + `CHANGELOG.md` + manifest descriptions in lockstep, or you've just demonstrated FB-0010 working on its own entry again). Pattern is real and stable enough to encode + extend.

**Sub-classes** (named retroactively after PR I's review surfaced that the original two-flavor framing under-covered the workflow-discipline shape):

1. **Code-edge silent-skip** (8 prior incidents, PRs 1, B, D, E, F-pass-1, F-pass-2, G, H1) — code that fails on an edge case without surfacing the failure. Examples cited in "What was said" above plus: PR G's `SCAN_TARGETS` shell-word-split bug (gawk-only `match()` in /flow:doctor Check 2.5 first draft, caught by smoke-test); PR H1's zsh-vs-bash word-splitting silent-skip in Check 2.5 (caught by engineer-lens cold-bash, fixed in commit 7826928).

2. **Workflow-step judgment-skip** (1 incident, PR H1 → defended by PR I) — author makes a deliberate decision to skip a discipline-required action, justified after-the-fact ("would have been a no-op anyway"), missing that the discipline produces signal (here: `STATUS: SKIPPED` log lines in the session transcript) regardless of whether the body runs. **Distinct from silent-skip:** the author didn't fail to notice the skip; they chose it. Different defense shape: prompt-level reminders + workflow.md discipline statements + project-dev rules, not louder error handling. PR I's defense.

3. **Fan-out contradiction** (sub-class of code-edge silent-skip when the value referenced in N files is a count/name/version — see "What was said" point 2 above). Caught itself recursively inside PR G + PR H1 + PR I (4 times across the FB-0010 defense PRs themselves). Each self-catch is a mini-confirmation that the discipline works on the discipline-PRs.

Eval signal: the engineer-lens catches the silent-skip flavor reliably first-pass; the fan-out + workflow-step-judgment flavors required adversarial-second-pass review in 4 of 9 incidents. Reminder: when changing this count, run `git grep -nE '([0-9]+) incident'` across the codebase before staging.

### FB-0009: `gh` CLI dependency in shipped skills must fail-fast, not silently 127
**Date:** 2026-05-25
**Source:** review feedback (synthesized from md-manager PR 4 consumer-feedback report 2026-05-25)

**What was said:** md-manager's PR 4 sibling-validation worktree (`~/dev/md-manager-pr4-validate`) lacked `gh` CLI. `/flow:ship` Step 1 (`gh pr list` for PR-OPEN detection) fell back gracefully via the `2>/dev/null` swallow. Step 7 (`gh pr create`) did NOT fall back — exit 127 with no diagnostic. The umbrella owner had to take over and run `gh pr create` from a worktree that had it installed.

**Synthesized rule:** Every flow skill that invokes `gh` (or any other external CLI not guaranteed by Claude Code) must fail-fast at Step 1 with a clean install hint, not at the invocation site with `exit 127`. Pattern: `if ! command -v gh >/dev/null 2>&1; then echo "⚠️ /flow:<skill> requires the gh CLI. Install: brew install gh (macOS) or https://cli.github.com" >&2; exit 1; fi`. Add to `/flow:ship` Step 1, `/flow:staff-review` Step 1 (gh-pr-list optional but used), and `/flow:ship-spike` Step 1 (`gh pr create` mandatory). Document `gh` as an install prerequisite in `docs/bootstrap.md` + `docs/migration.md` Step 1 sections. Same shape would apply to any future `jq`, `git`, or `node` dependency that flow assumes — fail-fast at the workflow entrypoint, not at the invocation site.

**Applies to:** workflow, dependency hygiene, error UX

**Validation:** 1 BLOCKER in md-manager PR 4 sibling worktree; recovery cost was a worktree switch + manual `gh` invocation. Could have been a clean stop with install hint at workflow entry.

### FB-0008: Stale-base preflight is the cheapest gate for the most expensive class of dogfood waste
**Date:** 2026-05-25
**Source:** review feedback (synthesized from md-manager PR 4 consumer-feedback report 2026-05-25)

**What was said:** md-manager PR 4 (PR #23) forked at `b8b0e0b` while `origin/main` had advanced to `eb8e7b9` by the time Phase 4.3 ran `/flow:staff-review`. Three of four lenses converged on "stale-base producing phantom-deletion diff" as the headline BLOCKER. Fix was a single rebase; **discovery cost was 4 lens spawns + minutes of triage**. md-manager's retro `/critique-plan` post-merge also flagged "base is current with main" as the missing load-bearing assumption from the per-PR plan — captured as md-manager's FB-0033.

**Synthesized rule:** Every flow skill that consumes a diff vs the default branch must include a stale-base check at the workflow entrypoint, before any expensive operation (especially lens-agent spawn). Pattern for `/flow:ship` Step 1, `/flow:staff-review` Step 1, `/flow:ship-spike` Step 1:

```sh
# Resolve default branch via PR-1's 3-tier fallback chain
DEFAULT_BRANCH=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@' \
  || cat flow.config.json 2>/dev/null | jq -r '.defaultBranch // "main"' \
  || echo "main")

git fetch origin --quiet
if ! git merge-base --is-ancestor "origin/${DEFAULT_BRANCH}" HEAD; then
  echo "⚠️ BLOCKER: branch is stale vs origin/${DEFAULT_BRANCH}. Rebase or merge before /flow:<skill>." >&2
  echo "       (current HEAD: $(git rev-parse --short HEAD); base needs $(git rev-list --count HEAD..origin/${DEFAULT_BRANCH}) commits)" >&2
  exit 1
fi
```

Class lesson: when a recurring expensive review-loop pattern is reducible to a mechanical check, write the mechanical check. The 4-lens-spawn-then-converge dynamic that caught PR 23's stale base is exactly what the loop's review surface is for — but a free upstream check that prevents the burn is strictly cheaper.

**Applies to:** workflow, preflight discipline, cost-of-review

**Validation:** 1 BLOCKER in md-manager PR 4. Reinforced cross-repo: md-manager's own retro `/critique-plan` reached the same conclusion independently and captured it as md-manager FB-0033 ("don't skip /critique-plan or /simplify even on docs-only diffs"). The class is real.

### FB-0007: Per-diff non-UI early-exit in /flow:accessibility-review (uiSurface=true projects shipping docs-only)
**Date:** 2026-05-25
**Source:** review feedback (synthesized from md-manager PR 4 consumer-feedback report 2026-05-25)

**What was said:** md-manager's `flow.config.json` declares `uiSurface: true` (correct — the project has UI). md-manager PR #23 was docs+config only; no UI files in the diff. `/flow:accessibility-review` still triggered full agent spawn against the diff, returned "nothing to review," and the spawn cost was wasted. The `uiSurface: false` early-exit gate flow ships protects backend/CLI/library consumers but doesn't protect UI-surface projects shipping docs-only PRs.

**Synthesized rule:** `/flow:accessibility-review` Step 1 should pair the existing `uiSurface=false` project-wide gate with a per-diff non-UI detection. Pattern (`${DEFAULT_BRANCH}` resolved via PR-1's 3-tier fallback chain — see FB-0008 snippet):

```sh
# Existing: project-wide early-exit
UI_SURFACE=$(cat flow.config.json 2>/dev/null | jq -r '.uiSurface // true')
if [ "$UI_SURFACE" = "false" ]; then echo "[a11y-review] uiSurface=false; skipping."; exit 0; fi

# NEW: per-diff early-exit
UI_FILES_IN_DIFF=$(git diff "origin/${DEFAULT_BRANCH}..HEAD" --name-only | grep -E '\.(tsx|jsx|vue|svelte|css|scss|html)$|^(src|app|packages/ui)/' || true)
if [ -z "$UI_FILES_IN_DIFF" ]; then echo "[a11y-review] no UI files in diff; skipping."; exit 0; fi
```

The UI-file regex is necessarily heuristic; consider a `flow.config.json.uiFilePatterns` slot for projects that want to override (e.g., monorepos with non-standard layouts). Pair this PR with FB-0006 — same fix shape, same detection scaffolding, one PR.

**Applies to:** workflow, /flow:accessibility-review, cost-of-review

**Validation:** 1 wasted spawn in md-manager PR 4. Every consumer with `uiSurface: true` will hit this on every docs-only PR.

### FB-0006: Per-diff doc-only early-exit in /flow:security-review (currently only prose, not structured)
**Date:** 2026-05-25
**Source:** review feedback (synthesized from md-manager PR 4 consumer-feedback report 2026-05-25)

**What was said:** md-manager PR #23 was docs+config only. `/flow:security-review`'s body says "skip if doc-only" in prose but has no structured early-exit gate — the orchestrator (or human) has to detect doc-only manually. By contrast, `/flow:accessibility-review` has a project-wide `uiSurface=false` gate (but lacks per-diff coverage; see FB-0007).

**Synthesized rule:** `/flow:security-review` Step 1 should add per-diff source-file detection paralleling FB-0007's a11y fix. Pattern (`${DEFAULT_BRANCH}` resolved via PR-1's 3-tier fallback chain — see FB-0008 snippet):

```sh
SOURCE_FILES_IN_DIFF=$(git diff "origin/${DEFAULT_BRANCH}..HEAD" --name-only | grep -E '\.(ts|tsx|js|jsx|py|rs|swift|go|rb|java|sh|mjs)$|\.json$|\.yaml$|\.yml$' || true)
if [ -z "$SOURCE_FILES_IN_DIFF" ]; then echo "[security-review] no source/config files in diff; skipping."; exit 0; fi
```

The source-file regex is necessarily heuristic; consider a `flow.config.json.sourceFilePatterns` slot for projects that want to override. Pair this PR with FB-0007 — same fix shape, same detection scaffolding, one PR.

**Applies to:** workflow, /flow:security-review, cost-of-review

**Validation:** 1 forced manual-skip-decision in md-manager PR 4. Every doc-only PR in any consumer triggers the same friction.

### FB-0005: Marketplace-key-mismatch is a silent-failure UX bug; install docs must verify by name
**Date:** 2026-05-25
**Source:** review feedback (synthesized from md-manager PR 4 consumer-feedback report 2026-05-25)

**What was said:** md-manager's user-scope `~/.claude/settings.json` had `extraKnownMarketplaces.llm-auditor` pointing at `https://github.com/by-dev-tools/flow.git` (stale key from before flow's PR 1 marketplace rename). Project-scope had `"enabledPlugins": { "flow@flow": true }`. Flow's `marketplace.json` declares `name: "flow"`. Result: `/help` silently omitted all `/flow:*` skills. No error, no warning, no diagnostic. Root cause: `enabledPlugins.<plugin>@<marketplace>` resolves by matching the marketplace's `name` field, NOT the user-scope settings key. A stale-keyed entry pointing at the right URL is invisible to the resolver.

**Synthesized rule:** Flow's `docs/bootstrap.md` (NEW projects) and `docs/migration.md` (EXISTING projects with prior `.claude/` content) Step 1 must include an explicit marketplace-name verification step:

```sh
# After /plugin marketplace add by-dev-tools/flow:
/plugin marketplace list | grep '^flow'   # must return a line; if absent, registration failed
```

If absent, instruct: `/plugin marketplace add by-dev-tools/flow` (re-adds with the correct name, regardless of whether a stale-keyed entry already exists pointing at the same URL). Optionally consider a `flow:doctor` skill or `template/base/scripts/verify-install.sh` that does the mechanical check + emits a clean diagnostic. Worth considering filing an upstream Claude Code issue — silent-failure on `enabledPlugins`-without-matching-marketplace is a UX bug regardless of plugin.

**Applies to:** install ergonomics, /docs/bootstrap.md, /docs/migration.md, dependency hygiene

**Validation:** 1 BLOCKER in md-manager PR 4 — the consumer hit it during Stage 1 install. Every future consumer with a stale `extraKnownMarketplaces` entry (or any name-mismatch shape) will hit the same silent-omission failure.

### FB-0004: Security regression tests must assert on what would leak, not on a proxy for it
**Date:** 2026-05-25
**Source:** review feedback (PR 3 engineer-lens dogfood)

**What was said:** PR 3 Phase 7's engineer lens caught that `test_absolute_outside_cwd_rejected` asserted `"/etc/hosts" not in result.stdout` — passes trivially because a content leak prints `127.0.0.1` (the host file's content), not the path string. A regression that drops the cwd check but doesn't print the path would pass the test silently. The dotdot-traversal test in the same file got it right: `"127.0.0.1" not in stdout and "::1" not in stdout`. Both rejection + accept tests were strengthened in the same Phase 7 fix commit to use content sentinels.

**Synthesized rule:** When writing a security regression test, identify what a real leak/breach would actually output, then assert on THAT. A real leak of `/etc/hosts` prints loopback addresses, not the path. A real leak of `~/.ssh/id_rsa` prints `-----BEGIN OPENSSH PRIVATE KEY-----`. A real shell injection prints `pwned` or creates a marker file. The path string is a proxy and proxies have escape hatches. When in doubt: write a deliberately-broken implementation locally, run the test, verify it FAILS. If the test passes with a known-broken implementation, the assert is vacuous.

**Applies to:** security regression testing, workflow

**Validation:** 1 BLOCKER caught in PR 3 Phase 7. Original assert: `"/etc/hosts" not in result.stdout or "outside" in combined.lower() or "external" in combined.lower()` — three disjuncts, any of which trivially satisfies. Replaced with `"127.0.0.1" not in result.stdout and "::1" not in result.stdout` — content-only, no escape hatch.

### FB-0003: Schema-without-implementation is a class of bug only dogfood catches
**Date:** 2026-05-24
**Source:** review feedback (PR 2 engineer-lens dogfood)

**What was said:** The Phase-7 engineer-lens review on PR 2 flagged that `memoryHardCap` was documented in `flow.config.schema.json` as configurable but `tools/memory/check.mjs` hardcoded `HARD_CAP = 30` and never read the config — a "false affordance" in the engineer lens's words. Same pattern with `branchPrefix`: documented in schema, no consumer in any skill. Both shipped through Phase 5's pre-commit greps cleanly because no static check correlates "slot documented in schema" against "slot read by something."

**Synthesized rule:** Every config slot landed in `flow.config.schema.json` must be paired with at least one consumer SKILL/agent/tool that reads it AT LANDING TIME — not "documented now, wired later." If a slot is genuinely future-only, mark it `"deprecated": "v1.x — not yet implemented"` in the schema description so consumers know. Treat schema-without-implementation as a contract lie equivalent to the loud-warning-vs-silent-no-op risk from PR 1. Pre-commit check: `for slot in $(jq -r '.properties | keys[]' schema/flow.config.schema.json); do if ! grep -q "$slot" plugins/flow/{skills,agents,tools,scripts}/; then echo "WARN: $slot documented but no consumer"; fi; done`.

**Applies to:** workflow, schema design, config-slot contracts

**Validation:** 2 of 13 slots in PR 2's schema (memoryHardCap, branchPrefix) had no consumer at first commit; engineer-lens caught both. Both wired in Phase 7 fix commit. The remaining 11 slots had at least one consumer.

### FB-0002: Validator-pass doesn't mean runtime-safe; the dispatcher is its own contract
**Date:** 2026-05-24
**Source:** review feedback (PR 2 engineer-lens dogfood)

**What was said:** Phase 7 caught that `/flow:ship`'s Phase-6 backfill invoked `Skill("flow:security-review")` and `Skill("flow:accessibility-review")` but the SKILL.md's `allowed-tools` frontmatter didn't list `Skill`. `claude plugin validate .` passed (the manifest is syntactically clean); the cwd-constraint test passed; the smoke install passed. The bug would have surfaced only at runtime when the dispatcher denied the tool call. This is a class of bug the validator can't catch and pre-commit greps would miss.

**Synthesized rule:** When a SKILL invokes a tool (`Skill`, `Agent`, `Bash`, `Edit`, `Write`, `Read`, `Glob`, `Grep`, `TaskCreate`, `TaskUpdate`, etc.), explicitly verify that tool is in the SKILL's `allowed-tools` frontmatter. The frontmatter is the dispatcher's contract; `claude plugin validate` validates manifest syntax, not tool-allowlist correctness. Recommended pre-commit grep:
```sh
for skill in plugins/flow/skills/*/SKILL.md; do
  ALLOWED=$(awk '/^allowed-tools:/{print; exit}' "$skill")
  for tool in Skill Agent Bash Edit Write Read Glob Grep TaskCreate TaskUpdate; do
    if grep -qE "\\b${tool}\\(" "$skill" && ! echo "$ALLOWED" | grep -qE "\\b${tool}\\b"; then
      echo "WARN: $skill invokes $tool but allowed-tools omits it"
    fi
  done
done
```

**Applies to:** workflow, plugin skill development, pre-commit checks

**Validation:** 1 BLOCKER caught in PR 2's Phase 7 dogfood (Skill missing from ship.md). PR 1 had no Skill invocations so this class was latent until PR 2.

### FB-0001: Dogfood the workflow even when not all skills exist yet
**Date:** 2026-05-24
**Source:** user direction

**What was said:** After PR 1 was opened, the user said: "even though all the skills may not be officially built out yet, follow the prompts from the skills in workflow.md to review the PR, taking it through all the stages of the intended workflow that we are implementing."

**Synthesized rule:** When a PR builds the workflow infrastructure itself, dogfood every loop step that *can* be run (manually or by emulating the planned skill's prompt via Agent subagents). Don't skip a step because the named skill doesn't exist yet — the loop's value is the *steps*, not the skill packaging. Concrete pattern: spawn 3-4 parallel review-lens Agents (engineer, push-further, security, plan-critic emulation) with the equivalent of the planned SKILL.md prompts; triage findings via the same BLOCKER / NIT / FOLLOW-UP scheme; apply BLOCKER + cheap NIT inline; route FOLLOW-UPs to plan.md; write the history.md entry; push the fix commit so the PR auto-updates.

Don't pre-empt this rule with "no skill, no review" — that defeats the point of building flow at all. Bootstrap exception (manual cold-read) is the *fallback* when even manual review isn't feasible, not the *default* when a manual review would be cheap.

**Applies to:** workflow, code review, agent self-feedback discipline

**Validation:** the walk-through-the-loop pass on PR 1 caught 3 BLOCKERs the pre-merge cold-read missed (manifest redundancy, two stale `agents/auditor.md` references in shipped prompts, `eval` vs `sh -c`). All three would have been consumer-visible bugs if shipped.
