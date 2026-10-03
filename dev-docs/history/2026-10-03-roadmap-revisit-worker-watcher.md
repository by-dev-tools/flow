## 2026-10-03 — Roadmap: revisit the worker watcher after the stopping point (orchestrator seat, docs-only)

**Branch:** `orchestrator/watcher-revisit-evidence` · **Feedback:** FB-0130

**What:** one addition under the existing § Next entry "Workers killed by the account session limit read
identical to workers that finished": a **▶ REVISIT AFTER THE STOPPING POINT** block recording Ben's
2026-10-03 direction, the stall evidence since 2026-09-29, what the seat built and why it is not the
answer, three measurement traps it hit, what is ruled out, and the surviving options.

**Why now, and why in git:** Ben chose not to build further watcher machinery during the program but
asked for the revisit to be recorded *in the repo* so an orchestrator rotation cannot lose it (FB-0130).
The seat's first answer had put it in sandbox-local scratch, which its own policy entry classifies as
not surviving teardown.

**Decisions and tradeoffs:**
- **Extend the existing entry rather than open a new one.** The gap is the same gap; a second entry
  would split the evidence and invite the two to drift (FB-0010 fan-out).
- **Record the three traps verbatim** (self-matching `pgrep`, a silent 4,000-message pagination cap, a
  non-forced `git fetch` that silently kept a pre-rebase PR head). Each produced a confident wrong answer
  in this seat; whoever builds the real watcher should not have to rediscover them.
- **Name the out-of-workspace options with their costs, decide none.** A scheduled GitHub Action needs a
  Conductor token as a repo secret (a security decision); a Claude Code cloud routine costs a session per
  tick and its reach to Conductor is unverified. Both are Ben's call, after the stopping point.

**Ship note:** this PR's own skip audit flagged `visual-verification` as SHOULD-RE-RUN on a docs-only
roadmap edit, because `dev-docs/plan.md` still carries a merged PR's `**Visual-walk:** N/A` line and the
visual-significance predicate treats any Visual-walk block as forcing significance. That is the trap
already recorded in roadmap § Next ("A `**Visual-walk:** N/A` block forces `visual_significant` TRUE"),
now observed firing on a PR that does not touch the plan at all. Routed to the manifest as a waiver
question rather than overridden.
