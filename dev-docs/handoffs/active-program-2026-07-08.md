# ▶ Active program — user-directed sequence (2026-07-08)

**Status:** PRESERVED, NOT APPLIED. This section was written into `dev-docs/roadmap.md` on an
uncommitted worktree and never reached `main` — it is absent from the roadmap today. Recovered
verbatim here before that workspace was archived. **Re-integrating it into the live roadmap is a
judgment call, not a mechanical paste:** the roadmap has moved from v1.19.0 to v1.27.0 since,
and at least two items below have been partly overtaken.

**Why it is worth keeping.** It is the only record of a *user-directed* build order (M → #5 → #2
→ #4 → #3) and the reasoning behind it. Its companion report — `dev-docs/research/ai-workflow-landscape-2026-07.md`,
preserved in this same commit — was written to justify exactly this sequence, and cites it by path.

**Known overlaps as of v1.27.0**, so a future reader does not re-derive them:
- **#2 (plan-gate ambition lens, FB-0046)** is now **D3** in `roadmap.md` § Designer-signal track
  (FB-0081), where it was promoted from optional to load-bearing under the prototype-first gate.
- **#4 (visual report reframe — design-critique surface, pin-to-anything commenting)** was
  substantially delivered by the v1.24.0 annotation-layer redesign (#84): commenting became a
  persistent mode and pins anchor to any DOM element, not just images. Its remaining asks —
  fires on every PR, reliable delivery, auto-open in preview — are not shipped.
- **M, #5, #3** appear untouched.

The section, verbatim:

---

### ▶ Active program — user-directed sequence (2026-07-08)

Re-prioritizes the forward queue below (Track 1/Track 2 + Deliverable-quality V4) behind a five-item program set by the AI-workflow benchmarking pass (gstack / Superpowers / GSD comparison + the Claude-Code loops article + the reflection & visual-feedback landscape; full report at `dev-docs/research/ai-workflow-landscape-2026-07.md`). Build order — **M → #5 → #2 → #4 → #3**:

- **M — Model-measurement harness (foundational, independent, build early).** NOT a model swap. Per user direction (conservative: **Opus stays default, Sonnet is the only challenger, no Haiku yet**), build the ability to *measure* a delegated model vs a baseline before routing anything: **(a)** per-subagent **token attribution** from the session transcript (extends `extract_session.py`; `/usage` + `/workflows` already surface the raw numbers); **(b)** an **offline A/B eval** that runs the reviewer fixtures through Opus vs Sonnet and reports finding-overlap + FP-rate + token cost (generalizes **PR P** Step A into a reusable harness); **(c)** a **randomized/shadow sampler** that logs `(agent, model, tokens, output)` per real invocation so paired/aggregate samples accumulate over normal use. Routing decisions wait on this data — no agent moves to a cheaper model on faith. Supersedes the benchmarking rec's "flip agents to cheaper models" framing.

- **#5 — Goals + required success criteria.** Make verifiable success criteria a **required** plan field (today spec-walk is the behavioral half — generalize + require, so every plan is loop-runnable by default). Wire two `/goal` cycles: the **plan cycle** (iterate the plan to a clear-criteria bar *before* the approval gate) and the **execution cycle** (iterate implementation until every criterion + verify-build is PASS). Extends **FB-0044/FB-0045** (already names `/goal` as the execution-loop driver). `/loop` reserved for recurring/external work (e.g. `/flow:contribute`), never within-task iteration. *(Goal = stop-condition on the work; loop = time/event trigger.)*

- **#2 — Plan-gate ambition lens + staff-review uncommon-care.** Implement **FB-0046**'s plan-time **experience/ambition lens** (product ambition → captured to *this* roadmap, so ambition is banked without bloating the current plan) alongside auditor + plan-critic. Keep `lens-push-further` as the **execution** uncommon-care lens in staff-review; sharpen it toward the standalone `/uncommon-care` skill's bar. **Load-bearing (user):** verify the roadmap-capture plumbing *actually fires* — an eval asserting a `roadmap-concrete` finding deterministically lands in `roadmapPath`, not just the PR body.

- **#4 — Visual report reframe (product/visual-change-centric).** Reframe the ephemeral pre-merge HTML from a build/verify-verdict report into a **design-critique surface**: what changed in product/UX terms *first* (features/screens changed, before/after visuals, decisions to critique), with the build-steps demoted to a collapsed summary. Requirements: fires on **every** PR; reliable delivery + easy to find vs the PR; auto-opens in Claude-desktop preview; images/screenshots load reliably; **pin-to-anything** commenting (elements/text, not just images — beyond today's image-only pins); works on **plain local HTML** demos (the Agentation differentiator — no React required). Dogfooded in **health-tracker + trio** (both `uiSurface:true`, used daily), not this repo (`uiSurface:false`). Builds on V3a/V3b; absorbs the "Reviewer reachability for the ephemeral report" § Exploration entry (the `/tmp`-path "doesn't send / hard to find" bug).

- **#3 — Memory instrumentation.** Fire-counts per memory entry (increment on cite), relevance-ranked injection, dead-entry detection at audit time — make reflection *measurable* instead of author-curated. Compounds once #5/#2/#4 generate signal. Distinct from **V4** (check-work-against-past-errors); this measures *which memories help*.

The older **Track 1 (K/L)** + **Track 2 (N/O/P)** queues below remain valid but sit behind this program unless a consumer regression re-prioritizes them. Detailed per-PR plans land in `plan.md` § "Active Work Items" as each item starts (#5 first).

---
