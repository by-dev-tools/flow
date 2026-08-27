---
paths:
  - "dev-docs/**"
---

# Documentation Format Rules

These rules ensure consistent formatting across dev-docs files.

**Relationship to `plugins/flow/skills/documentation/SKILL.md` (FB-0085 / Phase 00 / 00c):** that file is the plugin's shipped, project-agnostic counterpart; this one is scoped to this repo's own `dev-docs/` paths. The history.md/feedback.md field lists below were synced to the plugin's more evolved wording in this pass (it had since gained fields this file never backported). Keep the two in sync going forward, or note here why this occurrence is deliberately different.

## history.md format

Every entry must include:
- **Date** (YYYY-MM-DD)
- **Branch** (the branch the work shipped from)
- **Commit / PR reference** when available. `/flow:ship` writes the entry before committing, so this field can be a forward reference ("[this commit]" or "[range pending push]") at write time; `git log` and the PR link recover the SHAs later. Don't block on the SHA -- branch + entry content are the load-bearing parts.
- **What was done** in user-facing terms
- **Why** -- the problem or goal
- **Design decisions** with reasoning
- **Technical decisions** with reasoning
- **Tradeoffs discussed** -- the most valuable part for future reference
- **Lessons learned** (optional but high-value)

Entries that modify error handling, persistence, fallback behavior, or sanitization (markdown rendering, HTML sanitizer config, etc.) must include a `SAFETY` marker in the title or body.

## Recorded rejections

When any narrative entry (history, roadmap, plan) records that an alternative was rejected -- "we did not do X because Y", "chose A over B because..." -- Y must be a *measured* result, or the entry must state plainly that X is unevaluated and name the cheap experiment that would settle it. An unverified prediction may not, on its own, carry a rejection: a future reader inherits "X is closed" as settled fact and never re-opens it. A hedge word ("plausibly", "likely", "probably") does not discharge this -- it flags the claim as exactly the unmeasured kind that must not close an alternative by itself.

## feedback.md format

Every entry must include:
- **Sequential ID** (FB-XXXX)
- **Date** (YYYY-MM-DD)
- **Source type** (user correction, user preference, user direction, review feedback)
- **What was said** -- factual summary, not raw quote
- **Synthesized rule** -- the actionable takeaway
- **Applies to** -- which areas of the project this affects

## plan.md maintenance

- "Current focus" must reflect reality at all times
- "Handoff Notes" should be populated at the end of each session and cleared when the next session picks them up
- Completed items move to "Recently Completed" (keep last 3-5), then to history.md
- Never delete planned items without documenting why in history.md
