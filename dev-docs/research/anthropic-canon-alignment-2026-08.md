# Anthropic agent-building canon — Flow alignment check (2026-08)

**Date:** 2026-08-14
**Status:** research / direction-setting. Elevates **two** items to top priority in `roadmap.md` § Now — **M** (subagent model routing, already scoped) and **AB** (attention budget & harness-weight audit, **net-new**). No plugin artifacts changed by this doc.
**Companion doc:** `ai-workflow-landscape-2026-07.md` benchmarks flow against *competing frameworks* (gstack / Superpowers / GSD) and the Claude-Code **loops** article. This doc is the *first-party Anthropic canon* layer that one never mapped — specifically the **context-engineering** article, which is the freshest and most load-bearing of the set.

**Provenance / confidence.** `anthropic.com` is **egress-blocked** from the flow CI/dev environment (Cloudflare 403 on the direct route; not-in-allowlist through the agent proxy), and per proxy policy those denials are not retried. The article specifics below were recovered from **WebSearch result summaries** (which quote the articles) plus training knowledge — **not** the full article text. Treat the "the article says X" claims as **high-confidence-but-unverified against source**; re-fetch and confirm quotes if any of them become load-bearing for a shipped change. Flow's *own* state (what it does and doesn't do) is directly verified against the repo.

---

## 0. One-line synthesis

> Flow is strongly aligned with — and on structured note-taking, sub-agent verification, and self-improvement **ahead of** — Anthropic's published agent canon. Two gaps recur across every article and are now top priority: **(1) per-subagent model routing** (everything runs on the inherited session model) and **(2) attention budget** (flow is a token-heavy, surface-heavy harness with no mechanism to prune weight as model capability grows). The second is the sharper, less-tracked one, and flow's own dev-docs are the clearest evidence of the debt.

---

## 1. The canon checked against

Four first-party Anthropic pieces define the current best-practice set:

| Article | Core contribution |
|---|---|
| **Building Effective Agents** | Simplicity first; prefer *workflows* (predefined paths) over autonomous *agents* until the task demands autonomy; patterns (prompt-chaining, routing, parallelization, **orchestrator-workers**, **evaluator-optimizer**); three principles — simplicity, transparency (show planning steps), good agent-computer interface (ACI). |
| **Effective Context Engineering for AI Agents** *(freshest; the landscape doc never mapped it)* | Context is a **finite resource** with diminishing returns ("context rot"); find the **smallest set of high-signal tokens**. Three long-horizon techniques: **compaction**, **structured note-taking** (agentic memory to external files), **sub-agents** (clean context, return condensed summaries). Plus **just-in-time retrieval** (fetch at runtime via lightweight identifiers, don't pre-load). |
| **Effective Harnesses for Long-Running Agents** | Initializer vs coding agent; durable progress file + git for fresh-context reconstruction; incremental one-unit-at-a-time loop (implement → test → note → commit); keep a clean working state; crash-resilience (a fresh harness resumes from the session log). ⚠️ **Correction (post-merge #115):** the *"assumptions expire"* meta-lesson often cited to this article is **not in its text** (full-fetch verified 2026-08-15) — it is a take-home / context-engineering framing; see `anthropic-engineering-blog-verification-2026-08.md`. |
| **Multi-agent research system** | Orchestrator-worker tiering (Opus lead / Sonnet workers); token usage explains most of the performance variance → route deliberately. |

---

## 2. Alignment, by best practice

| Anthropic best practice | Flow status | Evidence in-repo |
|---|---|---|
| **Structured note-taking** — persist progress to external files | ✅ **Ahead of the canon** | `plan.md` (handoff notes), `history.md`, `feedback.md`, `roadmap.md`, agent memory, the PR `## Flow run` table — plus *mechanical* doc-currency gates (ship 5a/5b, `statusDocs`, `statusSurfaceCandidates`) the article doesn't prescribe. |
| **Sub-agents, clean context, condensed returns** | ✅ **Strong** | `staff-review` (4 fresh Explore lenses), `auditor`, `plan-critic`, `verify-build` judges — all fresh-context, structured returns. |
| **Transparency — show planning steps** | ✅ **Strong** | Human-gated plan, spec-walk checkboxes, confidence verdicts, self-documenting `## Flow run` table. |
| **Evaluator-optimizer & orchestrator-workers** | ✅ **Strong** | `verify-build` (generate → adversarial-judge), auditor/plan-critic as evaluators; staff-review/ship as orchestrators; FB-0012 bounded mechanical-fix loop. |
| **Workflow-first over premature autonomy** | ✅ **Aligned by design** | Flow *is* a deterministic workflow with LLM steps + two human gates — exactly what "Building Effective Agents" says to reach for first. |
| **Use scripts for deterministic work** | ✅ **Exemplary** | `extract_session.py`, `check.mjs`, `render-*.py`, `skip-audit-checks.py`, `visual-significance.py`. |
| **Self-improvement / encode failures** | ✅ **Ahead** | feedback→memory→preflight promotion with anti-ossification guardrails the literature lacks. |
| **Crash-resilience / resume from durable state** | ✅ **Aligned** | Durable docs + commit-at-every-phase-boundary let a cold session reconstruct from `plan.md` + git. |
| **Just-in-time retrieval via lightweight identifiers** | 🟢 **Practiced, unnamed** | "Read source-of-truth docs first," grep-first/edit-second, `file:line` refs, read git log before touching safety files. |
| **Compaction / long-session context isolation** | 🟡 **Aware, unscheduled** | Relies on the harness's built-in summarization + the per-PR bound; the GSD comparison in the landscape doc flags long single-thread context rot. The docs *are* the handoff state, but nothing compacts them. |
| **Per-subagent model routing (Opus judgment / Sonnet mechanical)** | 🔴 **Known gap → roadmap M** | Everything inherits the session model. Measurement-first per FB-0083. **Now top priority.** |
| **Attention budget — "smallest set of high-signal tokens"; context is finite** | 🔴 **Net-new; sharpest divergence → roadmap AB** | Flow keeps accreting always-on surface and prunes only reactively. See § 3. **Now top priority.** |

---

## 3. The attention-budget finding (net-new — this is the one nobody was tracking)

Anthropic's context-engineering article treats context as a scarce resource: *find the smallest set of high-signal tokens that maximizes the desired outcome*, because attention degrades as the window fills ("context rot"). Flow's design bias is the opposite pole — it optimizes for **trust and coverage** by adding scaffolding, and it prunes only when a step becomes obvious friction. That bias is defensible for high-stakes, long-lived code (it is flow's moat), but it has produced real, measurable weight, and there is **no mechanism that audits harness weight the way the 5-ship audit audits memory entries.**

This is the same tension named by the *"every harness component assumes the model can't do something; those assumptions expire"* meta-lesson, sharpened by the context-engineering framing. *(Post-merge #115: that meta-lesson is **not** in the effective-harnesses article's text — attribute it to the `cwc-long-running-agents` take-home / the context-engineering framing, not the harnesses article. The attention-budget claims in this section, by contrast, are now **source-verified** against the full text — see `anthropic-engineering-blog-verification-2026-08.md`.)* A gate that compensated for a weakness of an older model is pure token cost once the model no longer needs it, and nothing in flow ever revisits that.

**Dogfood evidence, in flow's own repo (all directly verified):**
- `roadmap.md` § Now is composed of multi-thousand-token single-line append-blobs — each version bump prepends its full release blurb. Reading even ~20 lines of it exceeds a 25k-token read budget. This is the exact "append-only changelog in a UI/context surface" class flow already fixed once for the `/plugin` description (FB-0078) — unfixed here.
- `plan.md` carries **38 Spec-walk blocks** and the active one is selected by position (already filed in § Next as its own concern).
- `workflow.md` (~530 lines of dense narrative), `CLAUDE.md`, and the auto-loading `.claude/rules/*` all load into context every session, and only grow.

**Shape for AB (first cuts — full item in `roadmap.md` § Next "AB"):**
1. A periodic **harness-weight audit**, parallel to the 5-ship memory audit but over *always-loaded surface + gates*: per surface/step, "does this still earn its token cost at the current model capability?" Flag expired-assumption scaffolding for pruning.
2. **Compact the dev-docs** — apply the article's own *compaction* technique to `roadmap.md` § Now and `plan.md`'s active blocks: distill to a high-signal head, push detail to `history.md`. Dogfoods the principle; converges with the existing § Next "38 Spec-walk blocks" item.
3. A stdlib **always-on context-budget report** (token count over `CLAUDE.md` + rules + loaded skill preambles) so growth is *visible* — the note-taking analog of M's per-subagent token attribution.
4. Fold **just-in-time retrieval** and **curated canonical examples over exhaustive lists** into the workflow doctrine as first-class principles.

---

## 4. Why these two are now top priority (user direction, 2026-08-14)

The user reviewed this alignment check and directed that flow **capture the findings durably** and make the two recurring gaps — **model routing** and **attention budget** — **top priority in the roadmap**, to be **picked up by a fresh agent**. Captured as **FB-0084**. The prior active-program sequence (M → #5 → #2 → #4 → #3) is superseded at the head by: **M + AB first.** M keeps its measurement-first constraints (FB-0083: Opus default, Sonnet-only challenger, no Haiku, no swap on faith).

---

## Sources

First-party (egress-blocked — recovered via WebSearch summaries + training knowledge; re-fetch to verify quotes):
- Anthropic — *Effective context engineering for AI agents* (`anthropic.com/engineering/effective-context-engineering-for-ai-agents`)
- Anthropic — *Building Effective AI Agents* (`anthropic.com/engineering/building-effective-agents`)
- Anthropic — *Effective harnesses for long-running agents* (`anthropic.com/engineering/effective-harnesses-for-long-running-agents`)
- `anthropics/cwc-long-running-agents` (GitHub) — Code with Claude 2026 long-running-agents take-home

Companion in-repo: `dev-docs/research/ai-workflow-landscape-2026-07.md` (§ 3 model routing, § 4 loops-article alignment).
