# Long-running, mostly-autonomous flow loops — successive PRs, a decision corpus, and divergent-variation landscapes

**Date:** 2026-08-14
**Status:** research / direction-setting. Forward exploration, **prototype-gated** — not committed work. Feeds a `§ Exploration` entry in `roadmap.md` ("Long-running autonomous loops"). No plugin artifacts changed by this doc.
**Companion docs:** `agent-orchestration-2026-05.md` (the autonomous-coding preconditions this assumes), `dynamic-workflows-alignment-2026-06.md`, `visual-verification-blueprint-2026-06.md`, `ai-workflow-landscape-2026-07.md` (competitive layer). Relates directly to `roadmap.md` § **Designer-signal track / D1** (move the human gate to the artifact) and § **Deliverable-quality track**.
**Provenance / confidence.** Design synthesis from a multi-session design conversation, grounded in a **12-agent investigation of the health-tracker repo** (phase history, ~20 session transcripts, `decisions/`+`workflow/` docs, PRs #7–#41) whose claims were **adversarially validated** by three skeptic agents before synthesis. External validation is from **live web fetch** of current Anthropic engineering posts (cited inline, § 7). Health-tracker evidence is solid (direct artifacts + quotes); the divergent-variation design is **ahead of published baseline** and flagged as such throughout.

---

## 0. One-line synthesis

> flow already ships single-loop autonomy (Step-8 auto-advance between the plan and merge gates). The next horizon is **chaining loops** so flow runs all day, and a **quality substrate underneath** — a decision corpus that grounds autonomous judgment and absorbs every correction. Anthropic's own "Effective harnesses for long-running agents" independently arrives at our core loop architecture (fresh-context increments + durable on-disk state + self-verification); the **divergent-variation landscape** is the one piece Anthropic still calls open research, so it is scoped to *coverage, not precision*, and sequenced last.

---

## 1. The question

The primary user (a designer, four adopting projects) wants flow to run much longer unattended — larger PRs, or successive PRs across a day — so they come home to a larger reviewable surface with *more done*, without losing quality or the human decisions that matter. The design problem is not "run longer"; it is:

> **Preserve the epistemic value of the two load-bearing gates (plan approval, merge) while removing their synchronous, blocking nature.**

Two axes were considered. **Larger single PRs** is a modest lever (~2–3×): flow's per-PR verification budget is fixed, so self-verification quality degrades as one PR's surface grows, and an incoherent grab-bag breaks the spec-walk discipline (one checkbox = one discrete behavior). **Successive PRs** is where "all day" lives, and is the focus below.

---

## 2. Loop architecture — the successive-PR ("shift") model

Mostly *composition* of existing flow primitives, not new machinery. Reused as-is: the Step-8 ship-readiness predicate (the per-item autonomous-advance gate), confidence gates (the park trigger), the FB-0011 risk gate (the escalate trigger), and `/flow:ship`'s draft-PR-on-non-PASS safety net. Genuinely new: the queue+charter, the stateless executor, park-and-continue, cumulative verification, the evening digest, telemetry, and runaway guardrails.

### 2.1 Integration branch + merge predicate

The user runs a staging branch already (`xcode-testing` in trio, the target before a manual merge to main). Adopt it:

- Shift-mode PRs target a configured **integration branch**; the human merge gate moves to **integration → main**. `main` stays human-gated — "Claude never merges to main" is preserved absolutely. `/flow:ship` still never merges; the merge becomes a *separate*, strictly-gated executor step.
- One config slot `integrationBranch`, defaulting to `defaultBranch`. Unset ⇒ merges to main (fine while releases have no consequences — the user's current state). Set to `xcode-testing` once releases matter — a one-slot flip, no code change. The merge predicate is the same discipline either way.
- **Merge predicate — auto-merge a PR iff:** (a) inside an approved plan/charter, (b) mechanically verified (a *positive* verify-build PASS, not "didn't fail"; FB-0018), (c) **inert on merge** (changes nothing user-visible until a later phase activates it — additive field, flag-gated code, behavior-preserving refactor), and (d) **cleanly revertible / low blast radius** (excludes migrations, deletions, one-way doors). Anything failing (b)–(d) stops for the human, *even a "trivial" stepping stone*.

This resolves the "if it merges some, it might as well merge the final" puzzle: the property that licenses a merge is *mechanical-verifiability + inert + reversible*, **not** position in the chain. Stepping stones are mergeable precisely because they are the parts a machine can fully verify and that do nothing until activated; a judgment-laden final integration is gated precisely because it is the part only the human can judge. When the final phase *also* passes the predicate, merging it is correct, not a violation.

**Plan-time discipline this implies:** decompose features so every non-final phase is *additive-and-inert*, concentrating activation + judgment in the final phase. `/flow:critique-plan` could enforce it ("is each non-final phase additive-and-inert? if not, it can't auto-merge").

### 2.2 Stateless executor + queue + park/resume

- The scheduler is **dumb** (bundled `/loop`, or a launchd job — the `/flow:contribute` precedent): "nothing running? pick the next ready item → spawn a fresh `claude -p` session." All intelligence lives in the per-item session; durable state lives in the **queue file + git**, never in conversation context.
- **Fresh session per item is non-negotiable** — it kills the context-collapse failure mode. A crash costs one item's partial work (recoverable from its branch), never the day. Running items carry a **heartbeat**; the scheduler treats `running` + stale heartbeat as crashed → `parked(crashed)`, and a fresh retry re-plans from the branch's last commit (idempotent).
- **Park-and-continue:** an item that trips a park trigger (LOW/MEDIUM JIT plan, FB-0011, unresolvable preflight, budget exceeded) records `parked(reason)`, leaves its branch at the last good commit, and the scheduler moves to the next item with no unmet deps. Dependent items flip to `blocked-by-dep`; independent items keep flowing. A single ambiguous item never idles the whole day.
- **Guardrails** (the general.md cost/permanence class, baked in, not optional): per-item `budget_minutes` kill-switch, a daily PR/token ceiling, a kill-file / `/flow:halt`.

Queue item (a **charter**, not a finished plan):
```
- id: HT-014
  charter: "Add streak-freeze so a missed day doesn't reset the streak"
  confidence_intent: HIGH        # morning verdict — is the INTENT clear?
  scope_in / scope_out
  files_anticipated: [...]        # for overlap detection at dispatch
  depends_on: [HT-013]
  budget_minutes: 45
  status: ready | running | parked(<reason>) | needs-review(PR#) | merged(PR#) | blocked-by-dep
```

### 2.3 Two-tier planning (the plan gate stays load-bearing but batched)

A plan written at 8am for item 5 is stale by 2pm (items 1–4 changed the tree). Resolution:

- **Morning (human, synchronous): approve *charters*** — intent + scope boundaries + a confidence-of-intent verdict. Cheap to batch-approve; you sign *what*, not *how*. This is the front-loaded plan gate.
- **Per item (fresh session, autonomous): write the detailed plan JIT** against current tree state → `/flow:critique-plan` → proceed only if confidence stays HIGH; **MEDIUM/LOW parks** for evening review. The confidence gate does real work at execution time, with current information.

### 2.4 Phase-as-one-loop sizing heuristic (from health-tracker evidence, § 4)

> One loop = **one verifiability-homogeneous slice of a single surface**, scoped to **~5–6 adversarially-verifiable acceptance criteria**, all gateable **in one environment**, with **every foundational decision resolved at the plan gate**. Add ~5–25 pinning tests. **Split** the instant (a) the verification environment changes (cloud-unit → sim → human-grant) or (b) a criterion's test seam doesn't exist yet. **Do not split** for a contested taste call — fold it in and surface it at merge. Cap by criteria-count and environment-homogeneity, never by line budget.

### 2.5 Evening digest

The human-facing deliverable (jargon-free, per the user's copy preference): **shipped/merged** (links, one-line each, total surface), **needs-review** (open PRs on the integration branch), **parked** (item + *why* — the decisions only the human can make), **blocked-by-dep**, **killed**, plus the day's telemetry. You review the accumulated integration branch as one diff, then promote integration→main yourself.

---

## 3. Telemetry (Phase 0 — build first, stands alone)

Post-hoc analyzer over the JSONL transcripts (extends `plugins/flow/scripts/extract_session.py`). **Verified** the transcript exposes per-row `timestamp`, `type`, `tool_use` (name+input), and `message.usage` (`input_tokens`/`output_tokens`/`cache_read_input_tokens`) + model — so **cost-per-loop falls out for free**, not just timing.

- **Exact:** total wall-clock, per-tool latency (pair call→result), tokens, dollars, tool histogram, and the **idle-vs-working split** (gap before the next *user* message = agent waiting on you; gap after a tool_result = agent working).
- **Heuristic (directional):** time-per-step — step boundaries are inferred from skill/slash invocations and the first Edit after a plan, not a clean field.

The idle/working split is the number that justifies the whole project: if a "couple-hour" loop is mostly agent-waiting-on-you, shift mode's value is *deleting the human-wait bottleneck by batching approvals*, not making the agent faster. Phase 0 is the hypothesis test.

---

## 4. The health-tracker investigation (the evidence base)

**Method:** a 12-agent dynamic workflow — 8 parallel discovery readers (phase history, design/feedback docs, variant culture, visual craft, 4 transcript-mining batches), 3 adversarial validators, 1 high-effort synthesizer. ~935k tokens, ~6.5 min.

### 4.1 What the skeptics killed — precision → coverage

The naive design — "the agent predicts the *winning* fork and pre-builds it" — is **refuted** by the user's own history:
- **Foundational decisions are not pre-enumerable.** D1 (heart-cluster) shipped *"None of the three original directions ship"* — a 4th none-of-the-above option after 17 rounds, then revised again to variant C.
- **The user is on record refusing the menu.** On the anchor-color stance call: *"give me a recommendation with a clear rationale that survives adversarial critique"* (FB-0013) — an explicit rejection of a binary A/B on a stance-touching decision.

**The user's reframe dissolves this:** the goal is **coverage, not precision** — map the decision *landscape* so feedback is complete and early, then *reconfigure* from the judgment. The variants are scaffolding for the human's judgment, not a replacement. Under coverage, D1 is a success: the variants surfaced the decision area and gave concrete artifacts to react against, which is what produced the 4th option faster. Metric flips from *precision* (did we build the winner?) to *recall* (did we surface every decision area worth weighing in on?) + *reconfiguration cost*. New failure mode this introduces: **coverage explosion** — controlled only by the foundational docs pruning the decision surface to the forks that matter (§ 5).

### 4.2 Feedback taxonomy — what the user reserves

| Tier | Class | Example | Pre-buildable? |
|---|---|---|---|
| **0** | Stance / "is this the right frame" | D1 4th-option; FB-0013 | **No** → escalate-to-research (competitive scan + principles + self-red-team → one grounded rec) |
| **0** | Scope past the not-building line | *"Two metric areas. Nothing else."* | **No** → hard gate |
| **0** | Voice/copy semantics | *"still showing up in the simulator"* (resting→resting HR) | **No** → codify as lints |
| **0** | Reversibility-class assignment | *"Not locked the way D1–D7 are"* | **No** → discovered mid-flight; human output at plan gate |
| **1** | Single-axis visual taste | serif, selector, hue, value-stacking | **Yes** ← the env-flag seam |
| **1** | Static-composition exploration | rows-as-cards, dividerless | Yes, *if* shared seam |
| **2** | Interaction-feel / motion | *"compare the interactions"* (FB-0024) | **No** → build harness, human drives on-sim |
| **3** | Correctness | data≠Apple Health; light-angle regression | **No** → gates, not forks |

**Two findings that reshape the design:**
- **The highest-value forks are uncapturable unattended.** Interaction-feel and motion/ambient are where the user overrides most (FB-0024) and exactly the axes still-frame screenshots and the current sim harness (tap disabled, computer-use times out, HealthKit grant manual — 2b₂b shipped as a *draft* awaiting a manual grant, PR #29) structurally cannot render. The autonomous variant loop is capped at **static/token/launch-pinnable** forks. (The parked cloud-sim research, `research/2026-08-14-cloud-ios-simulator-limrun.md`, is a possible future unblock.)
- **The dominant reliability threat in an all-day run is not weak taste — it is rule-regression and gate-skipping.** *"we already talked about…"*, *"I already said to stop…"*, *"why doesn't it have a visual history entry"*, *"explain why the indicated skipped steps were skipped"*. FB-0010 silent-skip class. The user even spec'd the fix: *"add a step in flow for when a stage is skipped… another pass by the agent to validate if skipping the stage is legitimate"* (now shipped as `/flow:audit-skips`).

### 4.3 Phase-sizing drivers (validates § 2.4)

Phase 2 sub-divided along a **verification/environment seam** (*"web-OK / Mac-gated"*, PR #23), **not** size: pure logic (2b₁, 2b₂a) is unit-gated anywhere; integration (2b₂b) *"5/5 PASS after the maintainer-granted seeded pass"* (PR #29). 2c split *at the plan gate* because 2c₁'s state *"isn't simulator-drivable until 2c₂ builds the MockBaseline-nil seam"* (PR #37). Contested-taste calls do **not** force a split — PR #14 folded the anchor-color decision into one PR and surfaced it at the Present gate. **Divergent-variations collapse only the taste-driver; they do nothing for environment seams or missing test seams.**

### 4.4 The variant culture (already invented) + prunable-harness discipline

The `HT_*` env-flag seam is the gold pattern: one named axis, 2–3 values, gated `#if DEBUG`, variant is a **parameter on the real production component** (not a parallel artifact). Pick cost ~0: PR #38 chose Radley over Fraunces by *"inverting the existing HT_SERIF flag rather than ripping anything out"*; PR #35 *"promoted [the variant] from the DEBUG harness to a shippable screen."* This is the literal "structures already built to execute quickly upon decision" the user wants.

**Avoiding bloat/dead code (the user's constraint), two tiers matched to intent:**
- **Exploration harness (default for landscape-mapping):** N variants in an isolated DEBUG harness, *not woven into prod*. Prune = delete a harness leaf, zero prod surgery. Promote only the chosen one.
- **Retained prod flag (exception, opt-in, bounded ~1/fork):** a loser kept behind a flag because the user said "keep validating."

Mechanical hygiene that makes cutting deterministic: **fork-id annotations** (`// FORK:row-style:cards`) so a prune is greppable; a **`prune-fork` operation** at the pick (inline winner, delete losers unless opt-in retained); a **"no orphaned forks" preflight** (a decided fork with unpruned losers in prod is a defect — FB-0010 applied to variant cleanup).

---

## 5. The decision corpus (the unifying substrate)

The two needs the user named — richer foundational docs (priors) + efficient feedback capture (adaptation) — are **the same object**: decision-relevant knowledge, indexed by product surface, that grounds the agent's judgment. Forward priors (vision, JTBD/user-needs, locked decisions, rejected directions, reversibility classes) and corrective priors (what went wrong before) are the same kind of thing — a foundational *correction* becomes a forward *rule*. health-tracker already converges `decisions/open-questions.md` + `design-language.md` + `feedback.md` toward this.

Three load-bearing behaviors:
1. **Read-before-fork.** Before building any fork on a surface, load *all* corpus entries tagged to that surface (priors + prior corrections) as hard constraints. Closes the *"still showing up in the simulator"* gap — the rule wasn't unknown, it wasn't *loaded at build time*. Requires the corpus queryable by surface.
2. **Capture-at-correction.** Structured capture *at the moment* (what was wrong, the rule, scope, lint-candidate?), not deferred to ship-time synthesis. `/flow:log-disagreement` fires only on disputes-of-a-reviewer-finding; the trigger must widen to *any* correction.
3. **Compounding via proactive gaps.** At the plan gate, for each foundational fork: can I ground a reversible judgment in the corpus, or is there a genuine gap? Batch **only genuine gaps** as proactive questions ("here's a fork, here's what the docs imply, here's the gap — which way?"). Answers harden into corpus entries → the same question is never asked twice → the agent judges more autonomously over cycles. Same promotion-pipeline shape as flow's memory→preflight, applied to *product judgment*.

**Caution (from Anthropic's context-engineering guidance, § 7):** the corpus must stay high-signal and curated, not sprawl — carry flow's own memory guardrails (the ~30-entry cap + periodic audit) into the corpus design, or it becomes the context-rot it exists to prevent.

---

## 6. The divergent-variation / landscape-charter loop

A *mode* of a charter — a **landscape charter** (map + prototype a decision-heavy surface) vs a **build charter** (execute a settled spec). Two gates preserved:

1. **Plan gate (enriched):** read the corpus for the surface → enumerate foundational forks → **filter hard to Tier-1** (single-axis, shared-seam; Tier-0 routes to escalation-to-research or stop) → ground-or-ask per fork → present the **fork map** (decision areas + doc-grounded lean each + the 2–3 gaps only you can fill + a merge prediction per fork). You approve the map + fill gaps. This is the single planning gate — now fork-aware and gap-filling.
2. **Build (autonomous):** build the landscape in the harness, each fork a fork-id-tagged prunable leaf, grounded in corpus + answers.
3. **Merge gate (enriched):** present the landscape on the finished deliverable, each variant with its doc-grounding rationale. You judge across all areas in one pass. (Interaction/motion forks: ship the switchable harness + a "human-drives-on-sim" handoff — do not fake a contact sheet.)
4. **Reconfigure (autonomous):** apply judgments → collapse chosen leaves to prod, prune the rest → **capture judgments back into the corpus** → re-verify → ship.

**Combinatorial control:** axis budget = 1 per fork (a multi-axis "variant" is a smell rejected at plan time); strategy-pattern shared seam so a variant is a *leaf, not a rebuild*. Per-variant review cost is real (~8–16 captures against the {SE|17 × default|AX5 × ≥2 ambient cells × story state} matrix), so **telemetry/budget govern fork *count*** — the binding constraint is the human's review bandwidth at the merge gate, not the agent's build throughput. Bank un-opted forks as parked roadmap blocks rather than rendering them all.

This is an extension of the **Designer-signal track / D1** ("move the human gate to the artifact"): instead of one prototype, prototype across the decision landscape.

---

## 7. External validation vs Anthropic engineering (fetched 2026-08)

The **foundation** is independently arrived at by Anthropic's own teams; the **frontier** (variants) is where Anthropic still calls the answer open.

| Our design | Anthropic guidance | Verdict |
|---|---|---|
| Fresh session per item, durable state in queue-file + git | Harness uses `claude-progress.txt` + initial git commit + feature-list JSON; each session "begins with no memory of what came before" and is prompted to "get its bearings" | **Strong match** |
| Charter sets up the run; per-item coding loop executes | Explicit **initializer** vs **coding agent**; "only one feature at a time"; leaves "environment in a clean state" | **Strong match** |
| Verify-build / self-verification; guard against Potemkin PASS | Must "self-verify all features," "only mark features as passing after careful testing"; without prompting Claude "fail[ed] to recognize that the feature didn't work end-to-end" | **Validated** |
| Fresh context per unit to avoid collapse | "specialized sub-agents… clean context windows"; "context… a finite resource with diminishing marginal returns" | **Validated** |
| Decision corpus: read-before-act, write-after | Memory tool + "structured note-taking… persisted to memory outside of the context window"; "build up knowledge bases over time" | **Validated in spirit** |
| Promote recurring corrections to lints | "code linting being an excellent form of rules-based feedback" | **Validated directly** |
| Coarse human gates (plan+merge) + agent self-limitation | oversight "doesn't require approving every action but being in a position to intervene"; "Claude Code asks for clarification more than twice as often as humans interrupt it" | **Validated** |
| Merge-predicate: auto-merge only reversible/inert | "reversibility as a key demarcation for when stricter human approval becomes necessary" (0.8% of tool calls irreversible) | **Strong match** |

**Where we extend beyond the published baseline (higher design risk):**
1. **Divergent-variation coding loops.** The multi-agent post validates "pursu[ing] multiple independent directions simultaneously" (90.2% gain), but the harness post explicitly lists multi-agent coding as **open future work** ("still unclear whether a single general-purpose agent performs best… or a multi-agent architecture"). Our variant-landscape is aligned with the research *direction* but ahead of baseline → scoped to coverage-not-precision, sequenced last.
2. **Telemetry + budget governance.** Concept validated by the multi-agent "explicit research budget controlling agent count, tool usage, and reasoning depth"; the harness post covers no budgets/telemetry. Our extension.
3. **Human review gates in the long-running loop.** The harness post "does not mention explicit human review gates" — our integration-branch + merge gate is our addition (supported by the autonomy post's framing, not by the long-running-agent guidance specifically).

---

## 8. Honest limits / open questions

- **Coverage has no mechanical gate.** A missed decision area is invisible until the human spots it late. Partial defense: a decision-coverage audit agent (completeness-critic pattern), seeded from the open-questions register. Best-effort.
- **The Tier-0/Tier-1 classifier is the whole ballgame.** Mis-classifying a composition/stance fork as a taste fork burns a variant sweep on a decision that needs research — and presents a menu the user has refused (FB-0013). Cheapest mechanical signal: "building both options makes the component's *seam* diverge (not just a parameter)" ⇒ it's Tier-0, kick to research.
- **Corpus quality is a prerequisite, not a given.** A fresh project starts thin and bootstraps *through* the proactive-question loop — question-heavy early, few later. Front-load vision/JTBD docs to shorten the cold start.
- **Reconfiguration isn't always per-fork-independent.** Cross-fork judgments ("given cards for rows, the anchor should change too") reintroduce rework. Model forks independent where possible; accept genuine dependencies.
- **Interaction & motion are uncapturable unattended** on the current harness (see § 4.2). Scope the variant loop to static/launch-pinnable forks explicitly; hand interaction forks back to the human on-sim.

---

## 9. Prototype order

1. **Decision corpus + surface-indexed feedback, loaded at build time.** Build first *regardless of the variant idea* — it's the dominant reliability fix (§ 4.2) and stands alone. Prove a captured correction is *enforced at the next build of that surface*.
2. **The grounding/gap pass** — a **coverage** test (replaces the refuted precision test): replay a health-tracker phase, emit the fork map + proactive questions *before* reading the user's actual feedback, measure recall against the areas the user actually contested + whether the questions were the right gaps.
3. **Prunable-harness mechanics** — fork-id tags + `prune-fork` + "no orphaned forks" preflight; prove building 3–4 variants and cutting to 1 leaves mechanically-zero dead code.
4. **Telemetry analyzer (Phase 0)** — independent, cheap; slot in anytime.

If (2) fails, the design degrades from "the agent builds the foundational forks before you ask" to a **render-for-review aid** — still worth shipping, a smaller claim.

---

## Sources

- [Effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)
- [Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
- [Measuring AI agent autonomy in practice](https://www.anthropic.com/research/measuring-agent-autonomy)
- [How we built our multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system)
- [Claude Code best practices](https://www.anthropic.com/engineering/claude-code-best-practices)
- Internal: health-tracker investigation (12-agent workflow, 2026-08); health-tracker PRs #7–#41, `decisions/`, `workflow/feedback.md` (FB-0013/0015/0016/0023/0024/0025), `craft/visual-history.html`; `research/2026-08-14-cloud-ios-simulator-limrun.md`.
