### FB-0011: Autonomy bar — act when clearly best-practice + low-risk + no competing options; otherwise stop and present
**Date:** 2026-05-27
**Source:** user direction (stated during PR J planning conversation, in response to the REDIRECT question about red-team BLOCKER auto-fix vs stop-and-present)

**What was said:** Asked whether `/flow:ship` should auto-apply red-team BLOCKER fixes in-tree (faster, more autonomous) vs stop and present them for explicit user approval (slower, safer for one-way-door choices), the user gave a nuanced hybrid: *"If there is a solution that is clearly aligned with best practices as well as the spec/intent of the project and there is little risk in implementing it, then that should be done automatically. If the path forward is unclear, there are still significant risks, or there are competing options that are significantly different that both have merit, or there are one-way door decisions that need to be made, then the implementation should stop and wait for human review."*

**Synthesized rule:** In the Flow workflow's autonomy direction, an agent may act autonomously ONLY when ALL three hold: (1) the action is clearly aligned with best practices, (2) clearly aligned with the project's spec/intent (cite the rule/doc), (3) implementation risk is low (mechanical fix, single-file, recoverable). Stop and present to the user when ANY hold: the path forward is unclear; significant risks remain; competing options of comparable merit exist; or the decision is one-way-door.

This extends the existing **confidence-gate doctrine** ([[user-confidence-gates]] in workflow.md § "Confidence gates" — HIGH proceeds, MEDIUM surfaces at step 8, LOW auto-blocks) into auto-fix routing. The connection is direct: LOW-confidence assumptions can't proceed without explicit user resolution; analogously, a finding whose fix would constitute a LOW-confidence change can't auto-apply without explicit user resolution.

**Encoded as:**
- Per-finding `Fix-confidence:` field on `/flow:red-team` output schema (ships PR K) with values `AUTO-FIX-SAFE` (all three "act" conditions hold) vs `ESCALATE` (any "stop" condition holds). Default to `ESCALATE` when in doubt — false positives on stop-and-present cost the user a moment of attention; false positives on auto-fix could corrupt safety-critical code.
- `/flow:ship` Detection-Point-3 routing (ships PR L): `AUTO-FIX-SAFE` findings auto-apply in-tree, re-run preflight + red-team, ship if clean (cap at 4 iterations per the research diminishing-returns curve). `ESCALATE` findings stop the ship and surface to the user with full two-citation evidence + suggested fix.
- Conservative AUTO-FIX-SAFE category list (starts narrow; grows only with dogfood evidence). Initial examples: committed secret → delete + add to .gitignore; outbound HTTP→HTTPS upgrade; missing input validation that follows an existing in-repo pattern verbatim.
- Project-memory entry at `~/.claude/projects/-Users-benyamron-dev-flow/memory/feedback_autonomy_bar.md` (cross-session reminder; this FB entry is the consumer-shipped canonical version).

**Applies to:** workflow, autonomous gates, /flow:red-team (PR K), future Execute-stage gates, future /flow:staff-review BLOCKER triage, /flow:ship orchestration

**Validation:** Stated explicitly by the user 2026-05-27 during PR J planning; saved to project memory same day; encoded into PR J's plan as the PR-L Detection-Point-3 routing rule. PR L ships the mechanical enforcement. (Originally planned as PR-K Detection-Point-3 routing; renumbered to PR L after the parallel PR I collision required a PR J → PR K → PR L cascade.)
