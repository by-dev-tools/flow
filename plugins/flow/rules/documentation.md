---
paths:
  - "**/history.md"
  - "**/feedback.md"
  - "**/plan.md"
  - "**/roadmap.md"
  - "**/spec.md"
---

# Documentation Format Rules (flow plugin)

These rules ensure consistent formatting across the project's narrative docs (history, feedback, plan, roadmap, spec). Path-matches the file names so the rule auto-loads regardless of where the project keeps the docs (`flow.config.json.{history,feedback,plan,roadmap,spec}Path`; defaults `dev-docs/<name>.md`; consumer projects typically `core-docs/<name>.md`).

## history.md format

Every entry must include:
- **Date** (YYYY-MM-DD)
- **Branch** (the branch the work shipped from)
- **Commit / PR reference** when available. `/flow:ship` writes the entry before committing, so this field can be a forward reference ("[this commit]" or "[range pending push]") at write time; `git log` and the PR link recover the SHAs later. Don't block on the SHA — branch + entry content are the load-bearing parts.
- **What was done** in user-facing terms
- **Why** — the problem or goal
- **Design decisions** with reasoning
- **Technical decisions** with reasoning
- **Tradeoffs discussed** — the most valuable part for future reference
- **Lessons learned** (optional but high-value)

Entries that modify error handling, persistence, fallback behavior, or sanitization (markdown rendering, HTML sanitizer config, etc.) must include a `SAFETY` marker in the title or body.

## feedback.md format

Every entry must include:
- **Sequential ID** (FB-XXXX)
- **Date** (YYYY-MM-DD)
- **Source type** (user correction, user preference, user direction, review feedback)
- **What was said** — factual summary, not raw quote
- **Synthesized rule** — the actionable takeaway
- **Applies to** — which areas of the project this affects

## plan.md maintenance

- "Current focus" must reflect reality at all times
- "Handoff Notes" should be populated at the end of each session and cleared when the next session picks them up
- Completed items move to "Recently Completed" (keep last 3–5), then to history.md
- Never delete planned items without documenting why in history.md

## plan.md work-item format

Every entry under "Active Work Items" must include the fields from `${CLAUDE_PLUGIN_ROOT}/rules/plan-discipline.md`:

- **Mode** — `feature` (default), `spike`, or `tiny`
- **Goal** — 1–3 sentences in user terms
- **Scope (in)** / **Scope (out)**
- **Spec-walk checkboxes** — every numbered/bulleted requirement → checkbox bound to a test/verification (skipped in `tiny` mode; replaced with "Research question" in `spike` mode)
- **Confidence verdict per load-bearing assumption** — HIGH/MEDIUM/LOW with `Why:` and `If it flips:` (skipped in `tiny` mode; replaced with "Disposability" in `spike` mode)
- **Risks / open questions**
- **Files touched** — anticipated paths

See `plan-discipline.md` for the full spec and the LOW = automatic-human-gate behavior.

## memory entry format (failure-pattern memory)

Memory entries live at `~/.claude/projects/<canonical-project>/memory/feedback_<short_snake_name>.md`. They are written at `/flow:ship` step 4b only when the 5 guardrails in `${CLAUDE_PLUGIN_ROOT}/docs/workflow.md` § "Continuous improvement" pass. Required fields:

- **Source** — which review surfaced it
- **First seen** — YYYY-MM-DD on branch <name>
- **Source-diversity evidence** — which 2-of-3 sources (recurrence in time / two reviewers / one review + user correction) support this entry
- **Pattern** — the failure mode in 1–3 sentences
- **Why I missed it** — one line on the assumption or shortcut that led to the bug
- **How to catch it next time** — concrete check
- **Promotion target** — what the preflight rule would look like if this graduates
- **Fire log** — append YYYY-MM-DD on each subsequent firing; 2+ entries = promotion candidate (user-approved, not automatic)
