### Dynamic-workflows alignment report + adoption direction
**Date:** 2026-06-03
**Branch:** `claude/flow-dynamic-workflows-alignment-oJWKN`
**Commit:** (this PR)

**What was done:**
Docs-only direction-setting pass on how Flow should align with Claude Code's native dynamic workflows (research preview, 2026-05-28). Added: (1) full report `dev-docs/research/dynamic-workflows-alignment-2026-06.md` (state of play / concerns / opportunities O1–O8, grounded in the official `code.claude.com/docs/en/workflows` + `agent-teams` docs and Flow's own prior art); (2) three feedback entries — **FB-0037** (designer lenses are load-bearing, don't collapse under fan-out), **FB-0038** (use workflows where scale earns it, never force; token/cost first-class, no blanket ultracode), **FB-0039** (the human-review + self-learning artifacts — Flow-run PR table, companion HTML case-study, core-docs/FB/memory — must survive adoption); (3) a `roadmap.md` § Exploration umbrella entry tying O1–O8 to `Surfaces when` triggers. No plugin artifacts touched.

**Why:**
The user wants Flow to take full advantage of dynamic workflows — especially the parallel "voting"/adversarial-review fan-out — without the loop's structure inhibiting the engine, while keeping cost in mind and preserving designer perspectives + the review/self-learning artifacts.

**Design decisions:**
- **Segment-bounded adoption, not loop-wide.** Workflows forbid mid-run input; Flow's value is its gates. So a workflow owns the fan-out *between* gates and never spans one (segments A/B/C). This is the central reconciliation — keep rigidity at the gates, allow flexibility in the interior.
- **"Voting" refined, not adopted wholesale.** Honored existing prior art (FB-0016 + `dynamic-workflows-2026-05.md`): blind refutation rubber-stamps, debate loops amplify bias (PR J scope-out). The grounded direction is the untested *informed-independent refutation* variant at fan-out scale, re-tested on UI diffs — not generic claim-voting. Avoided contradicting hard-won findings.

**Technical decisions:**
- Full analysis lives in `dev-docs/research/` (matches the `agent-orchestration-2026-05.md` / `dynamic-workflows-2026-05.md` convention); actionable hooks live in `roadmap.md` + `feedback.md` so they re-surface via the exploration rule.
- Claimed FB-0037/38/39 **above** the 0020–0033 cross-session band (PR-U precedent), reserved in `reserved-feedback-numbers.md` before drafting (K1 protocol).

**Tradeoffs discussed:**
- **One umbrella PR vs. per-O-item PRs** — chose direction-setting + per-item graduation. The umbrella spans shipped-artifact, doctrine, and config surfaces that must ship/review independently (three-surface boundary + small-PR discipline). Pulling it into one PR would violate both.
- **Standalone research doc vs. inline roadmap only** — kept both: the doc preserves the full reasoning; the roadmap/feedback hooks make it actionable and trigger-discoverable.

**Lessons learned:**
- Flow's own constraints (FB-0012 mechanical-loop-only; PR J debate-loop scope-out; FB-0016 refutation spike) sharpen the native-feature recommendations rather than block them — the prior-art read is what kept the "voting" recommendation honest.

**Follow-up (same session):** User clarified that the visual-history / visual-verification artifacts are partly aspirational, and restated the actual goal — a human-review *value model*. Added **FB-0040** (north star: ground in user needs, make assumptions explicit, raise subjective questions, rationale for everything, then automate from clear intent + catalogue feedback/decisions — the principle FB-0037/38/39 serve), and marked the companion-HTML / visual-history artifacts explicitly ASPIRATIONAL/NOT-YET-SHIPPED in FB-0039 + the report (shipped baseline = `/flow:verify-build` behavioral check, v1.3.0; the rich visual report is a roadmap vision, not a surface to preserve). Key consequence captured: because workflows take no mid-run input, assumptions + subjective questions must surface at the *gate* preceding a segment, never in the fan-out interior — maximizing human-review value means *richer gate decisions, not more gates*.
