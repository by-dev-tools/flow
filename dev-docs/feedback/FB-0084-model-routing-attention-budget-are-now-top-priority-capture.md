### FB-0084: Model routing + attention budget are now top priority — capture the alignment findings and hand off to a fresh agent
**Date:** 2026-08-14
**Source:** user direction

**What was said:** After an alignment check of flow against Anthropic's first-party agent canon (building-effective-agents, context-engineering, long-running-harnesses), the user asked to (a) make sure all the important findings are captured in docs, and (b) make it **top priority in the roadmap** to address the two recurring gaps — **subagent model routing** and **attention budget** — with a **new agent to pick up** on them.

**Synthesized rule:** The two token-economy gaps are the current top of the queue, superseding the prior active-program head (M → #5 → #2 → #4 → #3). **M** (per-subagent model routing) keeps all FB-0083 measurement-first constraints. **AB** (attention budget & harness-weight audit) is net-new: flow accretes always-on surface with no mechanism to prune expired-assumption scaffolding — Anthropic's "smallest set of high-signal tokens" + the harnesses "assumptions expire" meta-lesson. Findings are durably captured in `dev-docs/research/anthropic-canon-alignment-2026-08.md`; both items are marked ▶ TOP PRIORITY in `roadmap.md` § Now/§ Next; the plan.md Current Focus + Handoff Notes point a fresh agent at them. When new gates/steps/surfaces are proposed, weigh their token cost, not just their coverage value.

**Applies to:** workflow, architecture, roadmap items M + AB, model selection, dev-docs hygiene
