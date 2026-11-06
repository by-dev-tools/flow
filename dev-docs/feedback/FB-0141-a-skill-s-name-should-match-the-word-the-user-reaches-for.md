### FB-0141 — A skill's name should match the word the user reaches for, not the word that described it at ship time

**Date:** 2026-11-01

**Source type:** user direction, relayed.

**What was said:** Ben asked (in `byamron/portfolio`, a different repo) whether flow had a
post-merge or retro skill. The relaying agent reported his own words, paraphrased: he reaches for
`/flow:post-merge` as "the workspace retro," and "post-merge" didn't come to mind when he went
looking for it by name. Request: rename `/flow:post-merge` to `/flow:retro`.

**Synthesized rule:** A skill's shipped name is a user-facing API, and "accurately describes what
it does" is not the same bar as "is the word the user actually reaches for." `post-merge` was
coined to describe *when* the skill runs (timing); `retro` is what the skill *is* to the person
invoking it (a workspace retrospective) — and the second is the one that actually gets typed.
When a user reports reaching for a different word than a skill's name, that is itself the
signal to rename, independent of whether the existing name is technically accurate.

**Applies to:** skill naming across the plugin generally — not just this one instance. Concretely
this PR renamed `plugins/flow/skills/post-merge/` → `plugins/flow/skills/retro/` and every live
reference to it (frontmatter `name`, `workflow-help`, `docs/workflow.md`, `/flow:land`'s caller
text, `doctor`'s skill-composition example, `run_land_evals.py` / `run_merge_status_evals.py` /
`run_skill_composition_evals.py`'s live assertions, the `postMergeWaitSeconds` slot's description
text, the canonical `research/2026-08-23-flow-cloud-workflow-plan.md`, and the open — not yet
shipped — backlog items in `dev-docs/roadmap.md` § Next/Later that reference the skill by path).
Historical records (`changelog/`, `dev-docs/history/`, other `dev-docs/feedback/` entries, and the
"Shipped"/"Prior" narrative inside `dev-docs/plan.md`/`dev-docs/roadmap.md` § Now) were
deliberately left naming `post-merge` — they describe what was true *at the time those PRs
shipped*, under the name the skill had then, and rewriting them would misrepresent history rather
than correct it. Confirmed before renaming: Claude Code has no author-definable skill-alias
mechanism (verified against the official docs, 2026-11-01) — "built-in aliases exist only for
bundled skills and commands... you can't define your own" — so this is a straight rename with no
deprecated-alias period, not a two-step migration.

**Also worth naming once, briefly:** this request reached flow by relay — an agent working in
`byamron/portfolio` forwarded it on Ben's behalf because that workspace's local lesson-contribution
queue was about to be archived with it, and `/flow:contribute` only drains a queue that still
exists on disk. A relay through a second agent is a real fallback, but it is strictly worse than
the queue surviving: it costs a human's attention to broker what would otherwise have been a
silent, automatic drain. Filed as a fact, not a fix — the queue's survival-vs-archive tradeoff
is `flow.config.json.contributionsQueuePath`'s existing design tradeoff (user-scope storage, which
is right on a persistent machine and wrong on an ephemeral one), already named in
`plugins/flow/skills/ship/SKILL.md` Step 4c.iv's flush mechanism for the PR-body case. Whether an
equivalent survive-the-archive mechanism is worth building for the *queue* itself (not just a
ship's own lessons) is a separate, unscoped question — not decided here.
