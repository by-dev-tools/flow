# Orchestrator-driven Conductor workspaces — feasibility, constraints, cost

> **Scope note:** This is an exploratory research note, **not** part of the flow
> plugin. It concerns how one human drives many Conductor cloud workspaces across
> *all* of their projects, and lives under `research/` so it stays greppable
> without touching any plugin surface (`plugins/flow/`), flow's own dev-tracking
> (`dev-docs/`), or project-dev infra (`.claude/`). Nothing here ships with the
> plugin.
>
> - **Date:** 2026-08-22
> - **Status:** ⚠️ **PARTIALLY SUPERSEDED (2026-08-23).** The §2 *facts* remain authoritative
>   and are cited as `[F#]` elsewhere. The §8 design proposal and §10.1 ledger template are
>   superseded by **`research/2026-08-23-flow-cloud-workflow-plan.md`** (the canonical plan) —
>   notably the ledger loses state-tracking to a PR+label queue, and the dispatch mechanism is
>   the now-live Conductor MCP. The §10.2 dispatch-brief template survives unchanged.
> - **Trigger:** "Can I interact with one orchestrator workspace per repo that spawns
>   and directs the others, so I stop context-switching across a dozen workspaces?"
> - **Vantage point:** every claim below marked ✅ was tested from inside a Conductor
>   **cloud** workspace (`flow` project, 2026-08-20/22). Claims from a Mac client are
>   untested — noted where it matters.

## 0. One-line synthesis

> The orchestrator pattern works and Conductor already assumes it — `workspace create`
> defaults to the current workspace's project from inside a workspace. The binding
> constraints are not capability but **lifetime** (1h idle / 23.8h max) and **reach**
> (cloud-only; no agent path to the Mac). Both push the same direction: the orchestrator
> is a *respawnable role backed by a committed ledger*, not a long-lived chat. Cost is
> dominated by output tokens and by how badly you fragment prompt-cache prefixes.

## 1. What was asked

Can one "orchestrator" workspace per repo spawn and direct sibling workspaces via the
Conductor API, inside the existing cloud org, with spawned workspaces following the flow
workflow — and does that align with Anthropic's orchestration guidance?

## 2. Verified facts

| # | Fact | Evidence |
|---|---|---|
| 1 | Conductor CLI at `/conductor/bin/conductor` wraps `https://api.conductor.build/v0` | `conductor --help`, `CONDUCTOR_API_URL` |
| 2 | Cloud workspace carries `CONDUCTOR_API_KEY` == `CONDUCTOR_API_TOKEN`, both **org-scoped** personal key | `auth whoami` → user+org; `project list` → all 8 projects |
| 3 | `workspace create` defaults to the current workspace's project when run inside one | `workspace create --help` |
| 4 | Spawn controls: `--agent claude\|codex\|cursor`, `--model`, `--effort`, `--fast-mode`, `--branch`, `--env`, `--message` | `workspace create --help` |
| 5 | Drive/observe: `session status`, `session message --after`, `message create`, `session cancel`, `workspace archive` | `conductor --help` |
| 6 | **The API is cloud-only.** Local Mac workspaces are invisible | `project workspace` → rows for `flow`/`portfolio` (cloud), **zero** for `md-manager`/`health-tracker` (local) |
| 7 | `git ls-remote`, `git fetch`, `gh pr list` all work from a cloud workspace | ran live; 40+ branches, PR #120 |
| 8 | `git worktree list` returns **only itself** in cloud — flow's Step 2 concurrent-work check is inert there | ran live |
| 9 | **Idle timeout 1h; max lifetime 23.8h** | `CONDUCTOR_INTERNAL_IDLE_TIMEOUT_MS=3600000`, `MAX_LIFETIME_MS=85800000` |
| 10 | flow is pre-installed at **user scope** from the cloud-computer image, not per workspace | `installedAt 2026-08-19T04:51` vs workspace `createdAt 2026-08-20T21:40` |
| 11 | That install can go **stale** — no per-workspace refresh | `known_marketplaces.lastUpdated 2026-08-19`; installed `1.29.0@cf783ac`, 1 commit behind `origin/main` |
| 12 | No `RunLocalCommand` tool in this workspace; cloud agents cannot execute on the Mac | ToolSearch → no match; MCP docs state it explicitly |
| 13 | "Sync to a local directory" is **one-way cloud→Mac, human-enabled**; local changes may be overwritten | cloud-workspace docs |
| 14 | Conductor MCP (0.82.0, 2026-08-20) documents 20 orchestration tools at `https://api.conductor.build/mcp` | `/docs/api/mcp` |
| 15 | That endpoint went live **mid-research** — staged rollout, not a doc error | `POST /mcp` → `404` at 2026-08-22 23:55Z; **`200` + all 20 tools at 2026-08-23 00:47Z**, from a *cloud* workspace |
| 16 | In-workspace MCP gained `GetDiffComments` alongside `DiffComment`/`GetWorkspaceDiff`/`GetTerminalOutput`/`AskUserQuestion` | appeared live in the session tool list |
| 17 | Session transcripts carry full per-message usage (`input`/`output`/`cache_creation`/`cache_read`, model, tier, speed) | parsed `~/.claude/projects/<slug>/<id>.jsonl` |
| 18 | `conductor sql` reads a sparse transcripts view — 7 sessions org-wide; no local sessions | ran live |
| 19 | Flow **fails safe** on a no-simulator host: MANDATORY-capture gate → `not_tested[]` → `Unknown`, never a silent PASS | `verify-build/SKILL.md` |
| 20 | Cross-session messaging cannot bridge workspaces — separate containers, separate filesystems | Claude Code docs |
| 21 | A workspace sleeps at **exactly 3600s** idle, matching `IDLE_TIMEOUT_MS` | probe 2026-08-22/23: idle 23:23:10 → `sleeping` 00:23:44 |
| 22 | **`message create` against a sleeping workspace is accepted (`state: queued`), wakes it, and the agent replies — 12s end-to-end.** `sleeping` → `ready` | probe: queued 00:23:44, `AWAKE` 00:23:56 |
| 24 | **The orchestration MCP is reachable from a cloud workspace** — no Mac client required. `tools/list` returns exactly the 20 documented tools (`create_workspace`, `send_message`, `run_sql`, …); stateless (no `mcp-session-id` issued) | live `initialize` + `tools/list`, 2026-08-23 00:47Z |
| 23 | Transcripts carry `rate_limit_event` — `rateLimitType: "five_hour"`, `status`, `resetsAt`, `overageStatus`. On this account overage is `rejected` / `out_of_credits` | probe session message list |

## 3. Still open

| Question | Why it matters | How to settle |
|---|---|---|
| Does Conductor surcharge the `-1m` context variants? | Routing table defaults to `-1m` everywhere | ask Conductor / check billing |
| How does a Claude **subscription** weight consumption? | Determines whether §5's ratios can ever become absolute numbers | not published; track ratios only |

> **Methodology trap, learned the hard way.** The first probe would have returned a **false
> negative**. `conductor session message <id> --limit N` returns the **oldest** N (offset 0,
> `hasMore: true`), so a naive poll never sees the reply; and `--after <justQueuedMessageId>`
> returns `404 Cursor message not found` because a queued message is not yet a transcript cursor.
> Grepping that window for the expected answer silently reports "no response" forever — the
> FB-0010 silent-skip class exactly. Page to the end, or use `--after` with an
> already-*processed* message id.

## 4. Hard constraints

1. **Lifetime.** 1h idle, 23.8h max. No workspace is long-lived. The orchestrator must be
   reconstructible cold from committed state.
2. **Reach.** Cloud-only. Local Mac workspaces are invisible to the API, and no agent path
   to the Mac exists in either direction.
3. **iOS.** No Xcode on Linux. A cloud worker cannot close flow's behavioral gate for Swift.
   Options: GitHub Actions macOS runner (most cloud-native, evidence produced by a machine
   that isn't the implementer — which FB-0066 wants anyway), a self-hosted Mac + `agent-device`
   MCP, or Limrun. See `research/2026-08-14-cloud-ios-simulator-limrun.md`.
4. **Context.** `haiku-4-5` is 200K; every other roster model is 1M. Flow's loop is
   context-heavy, so Haiku is **disqualified** from any full flow loop — not merely discouraged.
5. **Human gates.** Plan approval and merge stay human. The orchestrator routes; it never approves.

## 5. Cost model (measured, not estimated)

From the research session itself — 131 turns, `claude-opus-5`:

| Metric | Value |
|---|---|
| Output tokens | 207,785 |
| Fresh input | 702 |
| Cache creation | 1,676,760 |
| Cache read | 16,786,385 |
| Effective input units (1× fresh + 1.25× write + 0.10× read) | 3,775,290 vs 18,463,847 raw — **~80% eliminated** |

Three consequences:

- **Output is the number to track.** It bills at 5× input at every tier. Fleet consumption
  ≈ output tokens × workers × tier multiplier.
- **Cache read:create ran 10:1, and that ratio is a property of session length.** Every new
  worker re-pays cold-start cache creation for CLAUDE.md + skills + repo context (~20K observed
  on an early turn, billed at 1.25×). Fragmenting into many short sessions has a real cost
  invisible in the per-token table — and it is a direct argument against the stage-split design.
- **Cadence cliff at 1 hour.** This session used the 1h cache TTL (`ephemeral_1h_input_tokens`),
  which is exactly Conductor's idle timeout. Wake the orchestrator at 45–50 min, not 90.

**The ceiling is not cost — it is the shared five-hour window.** Under a Claude subscription every
worker draws on **one** rate-limit budget (fact 23). N parallel workers do not merely cost N×; they
exhaust that window ~N× faster, and when it goes the *entire fleet stalls at once* — with no overage
headroom on this account (`overageStatus: rejected`, `out_of_credits`). This caps useful parallelism
independently of token price, and it is the strongest argument for 3 concurrent workers rather than 8.
Track `resetsAt` from `rate_limit_event`; treat a near-exhausted window as a reason to hold the queue
rather than dispatch into it.

## 6. Model routing

Anthropic pricing (first-party, from a reference cached 2026-06-24 — **re-verify**):
Fable 5 $10/$50 · Opus 5 & 4.8/4.7 $5/$25 · Sonnet 5 $3/$15 (intro $2/$10 **through 2026-08-31**)
· Sonnet 4.6 $3/$15 · Haiku 4.5 $1/$5 (200K).

**Effort is the bigger lever than model tier.** Model tier sets price *per token*; effort sets
*how many tokens*. Lower effort yields fewer, more-consolidated tool calls and less preamble.
A strong model at low effort often costs less than a weak model at high effort — a weak model
flails, and flailing in an agentic loop is billed. Conductor defaults to `sonnet-4-6` / `high`.

| Job | Model | Effort |
|---|---|---|
| Orchestrator — triage, relay, ledger | `sonnet-4-6-1m` | low–medium |
| Feature work, full flow loop | `opus-5-1m` | high |
| One-way-door / architecture / gate machinery | `opus-5-1m` or `fable-5` | xhigh–max |
| Bug fix with known repro + failing test | `sonnet-5-1m` | medium |
| Docs, changelog, doc-currency | `sonnet-4-6-1m` | low |
| Mechanical sweep — **non-flow only** | `haiku-4-5` | low |
| Spike / research | `sonnet-5-1m` | medium–high |
| Adversarial second opinion | `codex gpt-5.5` | high |

**Escalation rule — start one tier down, let evidence promote, re-dispatch rather than grind.**
Flow already emits the signals: a LOW-confidence assumption, a `/flow:critique-plan` REDIRECT,
a `/flow:verify-build` Unknown, or two loops on the same failure. A stuck cheap worker burns
more than a fresh strong one, and a fresh context is worth more than a persuaded one.

**Fast mode is nearly always wrong for workers** — 2.5× output speed at 2× price, and nobody
is watching an unattended worker.

## 7. Staleness safeguard

Two tripwires, no scheduler, no scraper:

- **Roster hash.** `conductor model --json | sha256sum` — free and deterministic. Flips when a
  model is added or retired, a default changes, or effort levels change. **Baseline
  2026-08-22: `34bfa3137014f884`.**
- **Date backstop.** Pricing and effort guidance move without touching the roster, so the policy
  carries `reviewed: YYYY-MM-DD` and alerts past 60 days. Not hypothetical: the model reference
  behind §6 is stamped `cached: 2026-06-24`, already ~2 months old.

Runs in the orchestrator's cold-start (which already reconciles against `git ls-remote` / `gh pr list`).
Fires a message telling a human to re-run `/claude-api` and review §6. **The remediation is
deliberately human** — a routing policy that auto-updates from scraped docs rots quietly and then
routes everything wrong. That is FB-0077's shape one layer up.

## 8. Proposed v1

- **Dispatch mechanism:** the **Conductor MCP** (fact 24) — typed tools, reachable from the cloud
  workspace itself. The `conductor` CLI remains a working fallback; both hit the same `/v0` API.
- **Orchestrator:** cloud workspace, one per repo, respawnable, backed by a committed ledger
  on an `orchestrator` branch that never merges. Push after every state change — that push *is*
  the durability story.
- **Workers:** cloud, **one per item, waiting at its gates** — settled by facts 21–22. A worker that
  sleeps while awaiting plan approval is woken by the approval message itself in ~12s, so the
  plan/execute **stage-split is dropped**: it would have doubled workspaces per item and re-paid
  cold-start cache creation (§5) to solve a problem that does not exist.
- **Triage:** no new policy. FB-0011's escalation triggers and Step 8's ship-readiness predicate
  already encode decide-vs-escalate; the orchestrator applies them one level up.
- **Iterate loop:** Conductor diff comments (`DiffComment` / `GetDiffComments`) rather than prose
  relay — file-anchored, persistent, and costs the orchestrator zero context.
- **Learning:** the orchestrator's `Overrides` section drains into `dev-docs/feedback.md` via the
  existing `/flow:contribute` path. No second mechanism.
- **Guardrail:** workers denied `create_workspace` — mechanically, via a permission deny rule.
  Cloud workspaces ship the MCP pre-installed, so recursive spawning is one model-invocable call away.

## 9. Deliberately not built

No cost model. No token estimator. No model-selection classifier. No wrapper scripts around the
CLI. No state machine, daemon, or poller. No CI adapter until iOS actually enters the fleet.
No `/flow:orchestrate` skill — flow is project-agnostic by default and has an *active* roadmap to
decouple from a single host; baking Conductor's API into plugin artifacts pushes against that.

**v1 ships zero new code:** one markdown ledger, one brief template, both below.

**Bloat tripwires.** Brief past ~30 lines → something belongs in the repo or in flow. Ledger needs
a parser → it is over-structured. You write a rule a current model already follows → delete it.
Every ~10 dispatches, re-read the whole system and cut what was not load-bearing.

## 10. Templates

### 10.1 Ledger — `orchestrator/ledger.md`

```markdown
# Orchestrator ledger — <repo>

**Cold start:** this file is the only state. You need nothing from any prior conversation.
Read it, then reconcile against reality before acting — `git ls-remote --heads origin`,
`gh pr list`, `conductor project workspace <id>`. A workspace that died mid-update leaves
this file confidently wrong.

**Updated:** <ISO8601>   **Routing reviewed:** <date>   **Roster hash:** <sha256[:16]>

## In flight
### <item-id> — <title>
- state: planning | awaiting-plan-approval | executing | awaiting-review | at-PR | merged
- workspace: <deeplink>  · session: <id>
- branch: <name>
- owns: <paths>
- model: <id> · effort: <level>    # why: <one clause>
- blocked-on: <human | nothing | worker>
- last: <one line + time>
- next: <the single next action>

## Queue
## Recently landed
## Overrides
<!-- Triage calls the human reversed. Drain to dev-docs/feedback.md once a pattern forms. -->
```

### 10.2 Dispatch brief — body of `--message`

```markdown
# <item-id> — <title>

## Outcome
<2–4 sentences. What is true when this is done. Not how.>

## Done means
- [ ] <observable criterion>

## You own
write: <globs>
do not touch: <globs>          # another worker holds these

## Context you can't get from the repo
- <fact>                        # omit the section entirely when there are none

## Contract
- Mode: feature. Run the flow loop.
- STOP at the plan gate: write the plan, push the branch, report, end your turn.
- Report: conductor message create --session $FLOW_ORCHESTRATOR_SESSION \
    --message "<item-id> | <state> | <one line> | <what you need> | out=<output_tokens>"
- Never create workspaces or sessions. Never merge.
```

The contract is four lines on purpose. Everything else about how to work already lives in
CLAUDE.md, the flow plugin, and `.claude/rules/` — restating it here is duplicated state that
drifts, which is the FB-0010 fan-out class.

### 10.3 Usage audit — `orchestrator/usage.tsv`

```
date  item-id  model  effort  turns  output  cache_create  cache_read  fresh_in  outcome
```

`outcome` (`landed` / `re-dispatched` / `abandoned`) is what makes this an audit rather than a log:
it answers whether a cheaper routing choice actually finished the work. A choice that saves 40%
per turn and gets re-dispatched a third of the time is a loss. Compare **ratios between routing
choices**, never absolutes — subscription weighting is not published.

## 11. Recommendation

Build the coordination layer; defer central dispatch until it is earned.

**Phase 0 — worth doing regardless.** Replace flow's `git worktree list` concurrent-work check
(§2 fact 8) with a host-agnostic sweep: `git ls-remote --heads origin` + `gh pr list` +
`conductor project workspace`. Remote branches are strictly better evidence than local worktrees —
they are the shared state conflicts actually occur in, and they are visible from every host.
This is a real flow bug, it is ~10 lines, and it routes through `/flow:contribute`.

**Then:** settle §3, write the ledger, dispatch one real item, and re-read this document after
ten dispatches.

**When the orchestrator earns its cost:** ≥3 independent workstreams in flight, work spanning
repos, or you are away from the desk. **When it does not:** single-feature deep work, iOS/Swift,
tightly coupled changes on shared files, or any one-way door — there, the relay only adds distance
between you and the call.
