### FB-0070: A "contribution" / lightweight PR is NOT exempt from the full `/flow:ship` pipeline — size or "it's just a proposal the human gates" is not a reason to shortcut review stages
**Date:** 2026-07-06
**Source:** user correction (this session: I opened a `flow-contribution` PR via a hand-rolled `gh pr create` draft and skipped the ship pipeline, reasoning it was a small docs-only proposal)

**What was said:** "Why wouldn't you run the full pipeline for a contribution feature? Run everything so the quality stays high." The user rejected the size/kind-based shortcut outright.

**Synthesized rule:** The quality bar is size- and kind-independent. Run the full `/flow:ship` pipeline for **every** PR — docs-only, lightweight, and `flow-contribution` proposals included — and let each stage self-skip on its OWN documented predicate (doc-only, `uiSurface:false`, `platform:library`) rather than pre-deciding a whole-pipeline skip. "It's just a proposal the human gates at merge" is not a reason to skip review: the stages are cheap on a small diff (they early-exit), and the `STATUS: SKIPPED` audit trail is itself load-bearing. This is the concrete recurrence of the existing workflow-discipline rule ("always invoke `/flow:ship`, never `gh pr create`") applied to the contribution case, and of FB-0033 ("don't skip `/critique-plan` or `/simplify` even on docs-only"). Also captured agent-side as the `feedback_full_pipeline_every_pr` memory.

**Applies to:** `.claude/rules/general.md` § Workflow discipline; `/flow:ship` auto-invocation discipline; `/flow:contribute` (a contribution is still shipped through the full pipeline); FB-0033 (don't-skip-on-docs-only sibling), FB-0010 (workflow-step silent-skip class).
