## 2026-07-08 — AI-workflow competitive benchmark + five-item program reconciliation

**Branch:** `claude/cool-ardinghelli-43c165` · **SHA:** merged #102 @ `3fac2a2`

**What was done (user-facing).** Captured a competitive benchmark of flow against the current AI-coding-workflow landscape (gstack, Superpowers, GSD, Spec Kit, BMAD; the Claude-Code loops article; the reflection & visual-feedback literature). The durable report already landed on `main` via the pre-archive preservation commit (#100) at `dev-docs/research/ai-workflow-landscape-2026-07.md`; this PR does the two follow-on doc actions: reconciles the five-item program the benchmark produced against the current roadmap in `roadmap.md` § Next, and drafts the net-new model-measurement harness (M) as a QUEUED PR plan in `plan.md`.

**Why.** The benchmark surfaced that flow is best-in-set on trust/verification but behind on per-subagent model routing (three independent sources — gstack, Anthropic's multi-agent pattern, the loops article — all point at it), under-instrumented on reflection, and ahead-but-unreliable on visual feedback. A parallel archive process preserved the research plus an "Active program" handoff (`dev-docs/handoffs/active-program-2026-07-08.md`) marked "preserved, not applied — re-integrating is a judgment call." This PR is that judgment-applied re-integration against v1.27.0.

**Design decisions.**
- **Reconcile, don't re-paste.** Most of the program had already landed or shipped: #2 = Designer-signal track D3 (FB-0046), #4 = D1 + the shipped pin-to-anything annotation work (#75 / #84), #5 = Facet 4 + FB-0044. Only **M** (model-measurement harness) and **#3** (memory-effectiveness instrumentation) are genuinely net-new, so only those two became live roadmap § Next entries. The stale M→#5→#2→#4→#3 forward-queue re-prioritization from the handoff was deliberately NOT re-imposed — v1.27.0's Designer-signal track supersedes it.
- **Model routing is measurement-first (FB-0083).** M ships the *measurement* (token attribution + offline Opus-vs-Sonnet A/B + randomized sampler), never a swap. Opus stays default, Sonnet is the only challenger, no Haiku; the standing "plan-critic + lenses stay on Opus" direction (FB-0013) is preserved.
- **The M plan is QUEUED, not active.** Its Spec-walk sits below this PR's active block so the first-block readers (`extract-criteria` / `extract-visual-states`) never mistake it for the active plan.

**Technical decisions.** Docs-only diff (roadmap.md + plan.md + feedback.md + history.md prose; the research doc was already committed by #100). The four ship reviewers self-skip (security: doc-only; a11y: no UI files in diff; verify-build: platform library; audit-coverage: no behavior). The Test plan renders the honest no-behavioral-gate fallback (platform library).

**Tradeoffs.** Bundling the reconciliation + M plan into one small docs PR keeps direction-setting in a single reviewable unit, at the cost of touching two hot forward-looking docs (roadmap + plan) — accepted because the edits are additive § Next entries + a plan Current-Focus pointer, not restructures.

**Lessons learned.** A parallel archive/preservation process can commit session artifacts to `main` *before* the session's own PR opens — check `git log` / `git diff` against origin before assuming uncommitted work is unique (the research doc was already upstream, byte-identical). "Preserved, not applied" handoffs are a deliberate shape: they record direction without forcing a mechanical paste, leaving reconciliation as a judgment call for a later session.
