## 2026-08-14 — Capture the long-running-loop design + external validation

**Branch:** `docs/long-running-loops` · **SHA:** merged #107 @ `0c17b638`

**What was done (user-facing).** Durably recorded a multi-session design exploration for making flow run much longer autonomously, as a new research note (`dev-docs/research/2026-08-14-long-running-loops.md`) plus a `roadmap.md` § Exploration entry cross-linked to the Designer-signal (D1) + Deliverable-quality tracks. Three parts: a successive-PR "shift" model (a stateless fresh-session-per-item executor, a durable queue, an integration branch + a `mechanically-verifiable ∧ inert ∧ reversible` merge predicate that lets stepping-stones auto-merge to staging while `main` stays human-gated); a decision-corpus quality substrate (forward priors + corrective feedback, surface-indexed, loaded at build time); and a divergent-variation landscape reframed from precision to coverage.

**Why.** The design lived only in a session transcript plus an ephemeral 12-agent investigation output — the FB-0010 "durable in the repo, not the transcript" risk. It is grounded in an adversarially-validated investigation of health-tracker (phases 0–2, ~20 transcripts, PRs #7–#41) and externally validated against Anthropic's long-running-agent + context-engineering posts.

**Decisions / tradeoffs.**
- **Exploration, not Next.** The load-bearing bet — that the agent can predict which foundational forks to prototype (coverage recall) and classify Tier-0-stance vs Tier-1-taste reliably — is unproven and must be measured on real review rounds before any build. Filed with a `Surfaces when:` trigger; prototype order in § 9 of the note.
- **Coverage, not precision.** The naive "agent predicts the winning variant" framing is refuted by the repo's own history (D1's none-of-the-above 4th option; FB-0013's refusal of an A/B menu). Reframed to landscape-mapping so the design survives the evidence.
- **Honest about extending beyond baseline.** The note flags the divergent-variation coding loop as ahead of Anthropic's published baseline (they call multi-agent coding open research), while the foundation is independently corroborated.
- **Shipped from an isolated worktree** after a concurrent session collided in the shared primary worktree and orphaned the first commit; the two files were recovered from the orphaned commit and re-committed clean off latest main.

**Overlap noted.** The concurrently-merged #106 (`anthropic-canon-alignment-2026-08.md`, FB-0084) independently validated flow against the same Anthropic canon at broader scope; this note is narrower (the long-running-loop *design*) and shares the sources — worth a future cross-link.
