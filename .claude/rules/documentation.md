---
paths:
  - "dev-docs/**"
---

# Documentation Format Rules

These rules ensure consistent formatting across dev-docs files.

## history.md format

Every entry must include:
- **Date** (YYYY-MM-DD)
- **Branch and commit SHA** -- not just the branch name
- **What was done** in user-facing terms
- **Why** -- the problem or goal
- **Design decisions** with reasoning
- **Technical decisions** with reasoning
- **Tradeoffs discussed** -- the most valuable part for future reference

Entries that modify error handling, persistence, or fallback behavior must include a `SAFETY` marker.

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
