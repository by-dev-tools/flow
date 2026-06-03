# Flow × Dynamic Workflows — alignment report

**Date:** 2026-06-03
**Branch:** `claude/flow-dynamic-workflows-alignment-oJWKN`
**Status:** research / direction-setting. Actionable hooks land in `roadmap.md` § Exploration ("Dynamic-workflows adoption: segment-bounded fan-out between gates") + `feedback.md` FB-0037 / FB-0038 / FB-0039. No plugin artifacts changed by this doc.

Companion to the empirical thread already on record: `dev-docs/research/dynamic-workflows-2026-05.md` (the reviewer-refutation spike) + FB-0016 (don't write off a new capability on one data point) + FB-0012 (loop only on mechanical exit codes). This doc is the *architecture-alignment* layer; that one is the *reviewer-quality experiment* layer. Read both.

---

## 0. One-line synthesis

> **Dynamic workflows are an execution substrate; Flow's doctrine is a set of constraints on how that substrate is used. The right adoption is segment-bounded: a workflow owns the fan-out *between* two human gates and never spans a gate.**

Flow predates the feature (research preview, 2026-05-28, Claude Code ≥ v2.1.154) and already implements workflow-*shaped* patterns — parallel adversarial review, mechanical convergence, repeatable `/commands` — on the older subagent primitive. The alignment is strong; the three native wins Flow currently leaves on the table are **context isolation, fan-out scale, and orchestration-as-saved-script.** The one real collision is philosophical and resolvable: Flow's defining feature is *mid-loop human gates*, and workflows forbid mid-run human input.

---

## 1. What native dynamic workflows are (source of truth: code.claude.com/docs/en/workflows)

A workflow is a **JavaScript orchestration script Claude writes**, executed by a background runtime in an isolated environment.

- **The script holds the plan.** Unlike subagents / skills / agent-teams (where *Claude* decides turn-by-turn what to spawn), the script owns the loop, the branching, and the intermediate results. **Claude's context receives only the final answer.**
- **Intermediate results live in script variables**, not the context window — the headline context-economy win.
- **Scale:** up to 16 concurrent agents, 1,000 total per run.
- **Signature quality pattern:** *"independent agents adversarially review each other's findings before they're reported, or draft a plan from several angles and weigh them."* Bundled `/deep-research` **"votes on each claim"** and filters claims that don't survive cross-checking.
- **No mid-run user input by design.** *"For sign-off between stages, run each stage as its own workflow."* Only agent permission prompts can pause a run.
- **The script can't touch the filesystem/shell** — agents do all reads/writes/commands; the script only coordinates.
- **Repeatable two ways:** save the script as a `/command` (`.claude/workflows/` shared, or `~/.claude/workflows/` personal); parameterize with a global `args`.
- **Plan-approval prompt before launch** (per permission mode). In `claude -p` / Agent SDK / bypass: no prompt, runs immediately. Subagents always run `acceptEdits`, inherit the tool allowlist.
- **`ultracode`** (`/effort ultracode`, or the keyword in a prompt) = `xhigh` reasoning + automatic workflow orchestration: Claude auto-decides when a task warrants a workflow. Disable via `/config`, `disableWorkflows`, or `CLAUDE_CODE_DISABLE_WORKFLOWS=1`.
- **Cost:** a run spawns many agents → meaningfully more tokens than the same task in conversation. Docs advise running on a small slice first; agent caps bound runaway cost.

Distinct from **agent teams** (experimental, `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS`): teams are peer Claude sessions with a shared task list, mailbox, **file-locking on task claims**, and direct teammate messaging. Workflows do *not* give file-locking — relevant to §4.4 below.

---

## 2. What Flow is (codebase map, 2026-06-03)

An 11-step managed-autonomy loop with **two load-bearing human gates** (plan approval @ Step 2, merge @ Step 11) + an automatic LOW-confidence gate, dogfooded by this repo. Its parallelism today:

| Flow mechanism | What it does | Built on |
|---|---|---|
| `/flow:staff-review` (Step 7) | 4 independent lenses — **staff-engineer, ux-designer, design-engineer, push-further** | in-session **subagents**, parallel; findings → **main context** |
| `/flow:verify-build` (in ship Step 2) | 3 dimension judges (correctness / regression / scope-creep) + per-criterion adversarial transformation | in-session **subagents**, parallel; findings → main context, then JSON buffer |
| `auditor` / `plan-critic` (plan gate) | skeptical review, evidence-or-silence | single fresh-context subagent each |
| `/flow:ship` (Step 10) | security → a11y → verify-build → feedback synth → docs → PR | **sequential** sub-skill orchestration in turn-by-turn context |
| convergence | "any FAIL or Unknown → fail" | **deterministic rule, expressed in markdown prose** |

Design instincts that make Flow *unusually ready* for workflows:
- **Mechanical predicates, not vibes** (preflight exit codes, diff-hash oscillation detection, the Step-8 auto-advance predicate, the verdict aggregation rule). That is exactly "the script holds the loop and branching."
- **Fresh-context, single-role agent prompts** (`auditor.md`, `lens-*.md`) = ideal workflow worker definitions.
- **Repeatable `/commands`** already exist; workflows add the orchestration-as-script axis.
- **Cost-consciousness already baked in:** per-diff skip-paths (FB-0006/0007), stale-base preflight (FB-0008), `verifyBudgetCalls` cap.

What Flow does **not** do today: hold orchestration in a script (it's all in Claude's context), scale fan-out (fixed 4 lenses / 3 judges regardless of diff size), or vote (independent findings + deterministic aggregation + human tiebreak).

---

## 3. Current state of play — how they relate

✅ **Strong philosophical alignment** (mechanical convergence, narrow worker prompts, repeatable commands).
⚠️ **Orchestration lives in Claude's context, not a script.** Every lens finding and judge verdict dumps into the main window — exactly the context-bloat workflows eliminate, and it scales badly on large diffs.
⚠️ **Fan-out is fixed and small** — the opposite of the 16-concurrent / 1,000-total scaling that makes workflows worth it for migrations and codebase-wide audits.
⚠️ **No actual voting** — and Flow's own prior art (§5) says naive voting is *worse*, not better, on Flow's dominant false-positive class. This sharpens, rather than kills, the "voting" goal.

---

## 4. Concerns & considerations

### 4.1 The gate collision (most important)
Flow's thesis — *"more human gates than pure autonomous, fewer than fully manual"* — depends on **mid-loop human checkpoints**. Workflows **prohibit mid-run input**. Therefore: **you cannot wrap the whole loop in one workflow** without destroying plan-approval, LOW-confidence, and merge gates. This is not a limitation to fight — it's the signal to **segment**. Any segment that could hit a LOW-confidence assumption must **terminate and surface the assumption as its result**, never proceed on a guess.

### 4.2 `ultracode` can silently swallow a gate
If a user sets `/effort ultracode` in this repo, Claude may route a substantive task into a headless workflow that runs to completion — **bypassing plan approval and merge**, the exact failure mode `.claude/rules/general.md`'s *"Never bypass `/flow:ship`"* prevents, now at the engine level. Flow has **no guidance on the ultracode interaction** today. (This is also why FB-0038's "don't force a workflow" matters: blanket ultracode is both a cost and a gate risk.)

### 4.3 Markdown contract ↔ JS script drift
Flow's aggregation logic lives in `SKILL.md` *prose*. Porting to a workflow means re-expressing it as JS — the **same rule in two places**, i.e. the FB-0010 fan-out-contradiction class. Any port ships with a grep-first contract sweep.

### 4.4 Parallel writes race on shared files
Workflow agents do all writes, with **no file-locking** (that's an agent-*teams* feature). If feedback synthesis ever fans out, **FB-XXXX number assignment races** — precisely what PR K1's reserved-numbers protocol exists to catch. **Workflow-izing `/flow:ship`'s feedback step makes K1 a prerequisite, not a nicety** (see FB-0039).

### 4.5 Every fan-out agent reloads `CLAUDE.md`
At 16 concurrent reviewers, each reloads the full three-surface doctrine — token cost + a risk that workers try to "follow the loop" instead of being one lens. Mitigated by Flow's already-narrow agent prompts; the discipline is to keep workflow workers on tight role prompts and resist leaking loop doctrine into them.

### 4.6 FB-0012 is a hard constraint on any workflow loop
Bounded-retry loops may loop **only on mechanically-verifiable exit codes, never on LLM-judgment outputs.** A workflow that iterated "until the auditor approves" would reintroduce the reward-hacking failure mode Flow's passive-review doctrine exists to prevent. In workflow terms: the script's *convergence* must be a deterministic aggregation (any-FAIL → FAIL), and any *iteration* must key on a tool exit code, never a reviewer verdict.

### 4.7 Does Flow's rigidity inhibit the engine? (the user's worry)
Partly — and fixably. Flow's **agent prompts won't inhibit** anything (they're ideal workers). Flow's **interior rigidity** does: "always exactly 4 lenses," "ship sub-skills always sequential," "always these 11 steps." Workflows' power is *Claude writing the orchestration the task warrants*. Reconciliation: **keep rigidity at the gates, allow flexibility in the interior.** Today Flow is rigid throughout; the throughout-rigidity is the thing most at odds with the engine.

---

## 5. The "voting" goal, grounded in Flow's prior art

The user wants "agents voting." Native `/deep-research` votes on claims and filters non-survivors. But Flow has already run the experiment (`dynamic-workflows-2026-05.md`, FB-0016) and the result is nuanced — and **must be respected, not contradicted**:

- **Blind independent refutation → rubber stamp** (refuted 0/15 on `bootstrap.sh`). Flow's dominant false-positive class is **significance** misjudgment (the issue is real but doesn't matter under the trust model), and blindness strips the context needed to judge significance.
- **Self-disproof** (single agent, prove-or-disprove) → works (PR J, refuted 5/15). Shipped.
- **Debate loop / cross-critique** → explicitly ruled out (PR J scope-out, citing *Judging with Many Minds*, arXiv 2505.19477, bias amplification).
- **Untested, promising:** **informed-independent refutation** — a fresh agent *with* stance + project context + a uniform significance/exploitability rubric.

So the honest synthesis: **native claim-voting helps where the FP class is *verification* error (mechanically checkable claims), not *significance* error.** Flow's existing roadmap entry already names the highest-value re-test: **UI diffs**, where a11y/design claims (contrast ratio, focus trap) are far more mechanically checkable than "is this attacker-reachable." Dynamic workflows give Flow the **substrate to run the untested informed-independent-refutation variant at fan-out scale** — that is the right home for "voting," not a generic adoption of claim-voting across all reviewers.

---

## 6. Opportunities (prioritized; aligned with FB-0037/38/39)

### O1 — Ship `/flow:staff-review` and `/flow:verify-build` as native workflow scripts 🥇
The canonical workflow use case (independent agents, adversarial review, deterministic convergence). Saving them to `.claude/workflows/` buys clean main context (only the triaged verdict returns), rerunnability, and `args`-parameterization by diff base. The aggregation rule moves from prose into the script where it belongs (resolves 4.3 for these two). **Preserve all four lenses as distinct phases — designer lenses do not collapse into a generic reviewer (FB-0037).**

### O2 — Scale the fan-out per-file / per-criterion 🥈
Keep the 4 lenses as the *role taxonomy*; fan out one reviewer per changed file (or per criterion) and converge in the script. Turns "4 perspectives on everything" into "deep coverage on everything" for the large-diff/migration tasks workflows target — **only when the diff size earns the token cost (FB-0038); a 3-file diff stays a single subagent pass.**

### O3 — Test informed-independent refutation at scale (the real "voting" 🥉)
Not generic claim-voting. Use the workflow substrate to run the untested variant from §5 on **UI diffs** (the existing roadmap re-test). Respect FB-0012 (single-pass convergence, no iterate-to-approval) and the debate-loop scope-out. Natural pairing with PR P's auditor model-diversity work.

### O4 — Reframe the loop as three gate-bounded workflow segments
Document in `workflow.md`: **A** (Clarify → Plan → critique → *plan-approval gate*), **B** (Execute → preflight → simplify → staff-review → *Present gate*), **C** (ship pipeline → *merge gate*). Each segment is workflow-able; **a workflow never spans a gate.** Core doctrine update enabling adoption without losing the gates.

### O5 — `ultracode` interaction policy
Extend the *"Never bypass `/flow:ship`"* contract: a workflow may own a *segment* but **must terminate at a gate boundary** and surface its result for human sign-off. Consider scoping `disableWorkflows` for the ship segment or a "don't ultracode across a gate" rule. Closes 4.2; operationalizes FB-0038.

### O6 — Parallelize the ship triad
security ∥ a11y ∥ verify-build are independent and run sequentially today → a natural parallel phase once C is a workflow. Latency win, no semantic change.

### O7 — Reserved feedback numbers (K1) as a workflow prerequisite
If feedback synthesis ever fans out, claim-time FB reservation is required (4.4). Re-rank K1 ahead of any ship-workflow work (FB-0039).

### O8 — Preserve & strengthen the human-review + self-learning artifacts (FB-0039)
- **Flow-run PR table (FB-0019):** fold the workflow's saved-script path + per-phase agent/token summary (from `/workflows`) into the table — strengthens the audit trail with the native artifact.
- **Companion HTML case-study report:** already on the roadmap ("Verify-build HTML case-study report", post-PR-Q) — the rendered page a human opens before clicking merge, carrying per-criterion question/explored/learned + screenshots + per-dimension verdicts. This is *exactly* the visual-change review surface to preserve; a workflow's JSON findings buffer is its natural data source. Visual sign-off folds into the merge gate (FB-0035), never a third gate.
- **Core-docs + FB-entities + memory:** the compounding self-learning pipeline. Workflows can't write these directly (script ≠ filesystem) — a synthesis agent must, and under fan-out the FB-number race (O7) is live.

---

## 7. Bottom line for human-guided autonomous coding

Don't make the whole loop a workflow — its value is its gates, and the engine forbids gates mid-run. Instead: **the human owns the gates (plan approval, the Present decision, merge); the workflow engine owns the fan-out and convergence between them.** Designer perspectives stay first-class phases inside that fan-out (FB-0037). Workflows are adopted where scale earns the tokens, not by default (FB-0038). The PR/HTML/core-docs/feedback artifacts that make review legible and learning compounding are preserved as the workflow's *outputs* (FB-0039). That division is the most powerful expression of human-guided autonomous coding available — and Flow is one doctrine update (O4) plus two skill-ports (O1) away from it.

**Sources:** code.claude.com/docs/en/workflows · code.claude.com/docs/en/agent-teams · claude.com/blog/introducing-dynamic-workflows-in-claude-code · infoq.com/news/2026/06/dynamic-workflows-claude-code · internal: `dynamic-workflows-2026-05.md`, `agent-orchestration-2026-05.md`, FB-0012, FB-0016.
