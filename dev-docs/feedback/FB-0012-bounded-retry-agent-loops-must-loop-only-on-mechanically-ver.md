### FB-0012: Bounded-retry agent loops must loop only on mechanically-verifiable exit codes, never on LLM-judgment outputs; oscillation detection via diff-hash is mandatory on top of the iteration cap
**Date:** 2026-05-27
**Source:** user direction (synthesized from research pass + design discussion before PR M)

**What was said:** User asked whether `/loop` and goal-iteration primitives belonged in flow's review/quality workflow, and whether iteration could plateau or oscillate. The honest answer surfaced two distinct design rules: (1) loops are productive when the exit signal is an external tool's exit code (typecheck pass, test green, lint clean); loops are *harmful* when the exit signal is another LLM's judgment ("the auditor approved," "the reviewer says it looks good") because they teach the writer to phrase around the reviewer rather than fix substance — exactly the reward-hacking failure mode that passive-review-with-evidence-or-silence is designed to prevent. (2) A bounded iteration cap (N=3) alone is insufficient — a session can oscillate between fix-A-then-fix-B until exhaustion without converging. Diff-hash on top of the cap catches pure A↔B↔A oscillation cheaply.

**Synthesized rule:** Bounded-retry contracts in any flow skill MUST satisfy three conditions to ship:

```
(a) The exit signal must be mechanically verifiable — an external tool's exit
    code, a regex match on stable text, a file-existence check. NEVER the
    output of an LLM-judgment step (reviewer "approved", auditor "clean",
    plan-critic "APPROVED"). If the exit signal is another model's call,
    keep the step single-pass and rely on the human merge gate.

(b) The iteration cap must be paired with an orthogonal abort condition.
    Diff-hash equality (sha256 of `git diff HEAD` against prior attempts)
    is the canonical cheap detector — pure oscillation aborts before the
    cap exhausts. The cap and the orthogonal check are NOT redundant: the
    cap catches *drift* (each attempt different but all broken); the hash
    catches *oscillation* (an attempt repeating a prior diff).

(c) The contract must explicitly forbid reward-hacking fixes: "do not
    modify or disable tests to silence preflight; do not add @ts-ignore /
    # noqa / eslint-disable / @SuppressWarnings or equivalent suppressors."
    Prompt-level guards are probabilistic; the human merge gate is the
    backstop, but the contract should not produce escape hatches by
    default.
```

When designing the next bounded-retry block (if any), inherit these three conditions from `/flow:ship` Step 1c as the canonical contract. Do NOT copy-paste the prose if a second block lands — extract to `plugins/flow/docs/retry-contract.md` and reference (preempts the loud-warning-copy-dedup shape from PR-2 FOLLOW-UPs).

**Applies to:** workflow design, agent-loop contracts, /flow:ship + /flow:ship-spike Step 1c, any future bounded-retry primitive

**Validation:** Encoded as the load-bearing design call of PR M (v1.2.6). Independently converged with Microsoft Magentic's `max_stall_count` primitive (Magentic counts consecutive non-progressing rounds; Flow detects exact-diff oscillation — same defensive shape, different detector). Research sources: Anthropic's "Building Effective Agents" (evaluator-optimizer pattern requires "stopping conditions ... to maintain control" + "explicit success criteria"); 2026 Agentic Coding Trends Report ("without explicit success criteria, verification becomes guesswork"); Claude Code's own scheduled-task docs ("be explicit about what success looks like ... the task runs autonomously, so it can't ask clarifying questions"). The "loop only on mechanical signals" call is the cure for the reward-hacking failure mode that loops-over-LLM-judgment invite — same shape as why flow's reviewers are passive ("evidence or silence") rather than active. See `dev-docs/research/agent-orchestration-2026-05.md` for the full industry survey supporting this rule.
