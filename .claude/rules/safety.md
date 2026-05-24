---
paths:
  - "plugins/flow/agents/auditor.md"
  - "plugins/flow/agents/plan-critic.md"
  - "plugins/flow/skills/audit-plan/SKILL.md"
  - "plugins/flow/skills/audit-completion/SKILL.md"
  - "plugins/flow/skills/critique-plan/SKILL.md"
  - "plugins/flow/skills/ship/SKILL.md"
  - "plugins/flow/scripts/extract_session.py"
  - "plugins/flow/scripts/bounding_logic.py"
  - "plugins/flow/scripts/log_disagreement.py"
  - ".claude-plugin/marketplace.json"
  - "plugins/flow/.claude-plugin/plugin.json"
  - "plugins/flow/evals/run_evals.py"
  - "plugins/flow/evals/ground_truth.yaml"
---

# Safety-Critical Code Rules

This file loads automatically when you touch the plugin's published artifacts or its eval harness. These are the files that determine what the plugin does, what its reviewers see, and how we know whether it's right.

Safety-critical surfaces in this plugin:

- **`plugins/flow/agents/auditor.md`** and **`plugins/flow/agents/plan-critic.md`** -- the reviewer system prompts. Changes here directly alter audit/critique behavior. Small wording shifts can flip false-positive rates.
- **`plugins/flow/scripts/extract_session.py`** and **`plugins/flow/scripts/bounding_logic.py`** -- session parsing and context assembly. Silent failure modes here starve the reviewers of evidence without surfacing an error. Already known to skip malformed JSONL lines silently (line ~90); be deliberate about any change to that.
- **`plugins/flow/scripts/log_disagreement.py`** -- writes user-pushback records to user-scope storage. The storage path is load-bearing for the disagreement-capture contract; changes here orphan prior data.
- **`plugins/flow/skills/audit-plan/SKILL.md`**, **`plugins/flow/skills/audit-completion/SKILL.md`**, **`plugins/flow/skills/critique-plan/SKILL.md`** -- slash command dispatch. Shell substitution is used to inject preprocessed context; no size guards today.
- **`plugins/flow/skills/ship/SKILL.md`** -- the workflow ship pipeline. Changes here affect what every project's `/flow:ship` invocation does; placeholder sections for `/flow:security-review` and `/flow:accessibility-review` are intentional until PR 2 backfills them.
- **`.claude-plugin/marketplace.json`** and **`plugins/flow/.claude-plugin/plugin.json`** -- install surface. Breaking these breaks installation for every user.
- **`plugins/flow/evals/run_evals.py`** and **`plugins/flow/evals/ground_truth.yaml`** -- the only regression signal we have. If evals break silently, we lose the ability to detect reviewer behavior drift.

## Before modifying safety-critical code

1. Run `git log --oneline -5 -- <file>` to check for recent deliberate safety decisions.
2. If a recent commit mentions "crash", "data loss", "safety", "integrity", or "fallback" -- read that commit's diff to understand what was deliberately added.
3. Preserve safety behavior through rewrites. If restructuring a function, verify all safety-critical paths from the previous version still exist.

## When committing safety changes

- Flag the change in the commit message with a `SAFETY` marker.
- Flag the change in `dev-docs/history.md` with a `SAFETY` marker.
- Explain what safety behavior was preserved, modified, or added.

## Never silently downgrade error handling

- Don't replace explicit error handling with silent fallbacks (e.g., `fatalError` to silent catch, `throw` to `try?`, error alerts to console logs).
- Don't convert user-facing warnings to debug-only logging.
- Don't remove validation without documenting why it's no longer needed.
