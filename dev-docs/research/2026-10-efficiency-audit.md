# Token-efficiency audit — is flow spending tokens productively?

**Date:** 2026-10-04
**Status:** resolved — measured, point-in-time. Not maintained afterward; re-measure before citing after a few weeks (the account's rate-limit ceiling, the orchestrator's succession count, and every in-flight workspace below will have moved on).
**Mode:** spike (research). No plugin artifacts changed.
**Trigger:** Ben, 2026-10-04: *"We're hitting limits pretty quickly. If we're using the tokens as productively as possible that's fine — I just want to make progress on the work — but I want to make sure we are being productive and that some process isn't being wasteful."*
**Scope measured:** every `by-dev-tools/flow` Conductor workspace with activity since 2026-09-06 through 2026-10-04 (the orchestrator seat's full lifetime at the time of this audit), ~45 sessions measured directly, ~95 more (the S0 probe suite) counted exactly by name and sampled for cost.

## 0. Bottom line

Measured spend across the program in this window is **≈ $1,900**, and it is concentrated, not
diffuse: **five workspaces account for roughly $1,440 of it (~76%)** — CV1's fix (§3), the
orchestrator seat itself, TrackB's D1 Phase 2 feature work, the plugin-currency/visual-check fix,
and `/flow:audit-coverage`'s recall measurement. The single most *actionable* waste source is not
a token inefficiency at all: the account has **no overage** ("out_of_credits" on every rejection),
and the orchestrator's own session alone recorded **~134 hours of confirmed rate-limit stall**
over 22 days — the thing Ben actually described ("hitting limits," "make progress"). Token spend
*mix* is mostly defensible once you look at what each dollar bought; the velocity loss from a
hard, shared, non-overageable cap is the bigger problem.

## 1. Method — what's measured, sampled, or inferred

**Authoritative source: Claude Code's own `result` events, not my own token arithmetic.** Every
session transcript (fetched via `conductor session message <id> --json`, paginated 100 at a time)
contains periodic `rawPayload.type == "result"` records carrying `total_cost_usd`, `usage`, and a
per-model `modelUsage` breakdown — Anthropic's own list-price cost computation for that session,
not a model I built. I pull the **last** such event per session (cumulative) rather than resumming
every assistant turn myself; cross-checked the two methods on the orchestrator seat and they
diverge (see §3), which is itself a finding, not just a caveat.

**What I could measure and how:**
- Per-session `total_cost_usd`, `modelUsage` (tokens + $ by model), `num_turns`, message
  timestamps (first/last, and gaps) — for any workspace/session, via the Conductor API. This is
  the bulk of this doc's evidence.
- Tool-call shape (which tools ran, how many times, how many characters of result text each
  produced) — by walking `assistant` → `tool_use` and `user` → `tool_result` blocks in the raw
  transcript. Did this for the orchestrator seat only (§3); too expensive to repeat for every
  worker session given the "be economical" instruction, and the orchestrator is the one session
  explicitly named as the likely largest consumer.
- Dispatch routing rationale — by reading each worker's **first** message (the brief the
  orchestrator sends when creating the workspace), which carries a `ROUTING (FB-0091): model X ·
  effort Y · why: ...` line. Sampled 14 of these directly (§4); did not re-fetch all ~40.

**What I could NOT measure, and why:**
- `tools/model-measure/model_measure.py` reads **local** Claude Code transcript files under
  `~/.claude/projects/`. Those exist only for sessions that ran on the sandbox they ran on — I
  have no filesystem access to any other workspace's sandbox. Every number in this doc therefore
  comes from the Conductor API, not that tool. (I did verify the API's `result` events are the
  same underlying data model_measure.py documents using — same `usage` shape, same per-model
  granularity.)
- `.flow/usage.tsv` on the orchestrator seat: never read directly (no filesystem access to that
  sandbox either, and the contract asked me not to create new sessions to go get it). Used the
  dispatch-brief text instead, which carries the same routing decision in prose.
- Exact $ totals for the ~95 S0 probe sessions: counted exact session names (cheap, no token
  cost) and sampled 13 of them directly for cost; extrapolated the rest by type, since "documentation"/
  "exploration"/"general"-type probes measured **exactly $0** on every one of 5 direct checks
  (no real model call happened — `num_turns: 1`, all-zero `usage`) while "plan-discipline"-type
  probes measured $0.07–$1.03 depending on model. I did not re-verify all 60 zero-cost ones
  individually; if even a few are secretly non-zero the total below is a slight undercount, not an
  overcount.
- Three sessions are still **actively running** as this audit was written (my own `audit` session,
  a concurrent `graphs` research session in a sibling workspace, and `mobile-opts-1.56.0`, which
  grew from $154.79 to $168.98 between two measurements taken ~15 minutes apart during this audit).
  Every total below is a snapshot, not a final figure, and is biased **low**.
- Two sessions (`414039bd`, `d17ce7ff`, both prior orchestrator-seat incarnations) returned zero
  messages and zero result events — likely created but never used (cost ≈ $0), not a measurement
  gap I could close further without guessing.

## 2. Headline numbers

| Workspace / session | Cost (measured) | Span | Note |
|---|---|---|---|
| CV1 — audit-coverage can't see `.md` (2 sessions) | **$582.18** | Sep 21 – Oct 4 (12+ days) | $502.32 first/escalated attempt ("defeated by review," routed to `xhigh`) + $79.86 fresh follow-on session |
| Orchestrator seat (`77d5e766`) | **$185–$284** | Sep 12 – Oct 4 (22 days) | Range because Claude Code's own cumulative counter isn't monotonic across compactions — see §3 |
| Track B — D1 Phase 2 | **$277.29** (corrected; $201.88 as last-read) | Sep 16 – Sep 30 | 4 counter-reset corrections inside one session |
| Fix: plugin currency deadlock + visual-walk | **$182.95** | Oct 3 – Oct 4 | The visual-check fix named in this task's own ship-slot contract |
| `/flow:audit-coverage` recall measurement | **$135.80** | Sep 26 (one day) | `tools/coverage-recall/` |
| Mobile options 1–3 (main session) | **≥ $168.98**, still growing | Oct 3 – Oct 4 | Snapshot; grew visibly during this audit |
| S0 — rule-skills never load, option c | **$130.77** | Sep 27 – Sep 30 | One of the 8 "S0 probe" workspaces, but NOT a probe — a full exploration session |
| Closeout (plan doc, field manual, contribute drain) | $42.69 | Sep 26 – 30 | |
| Touch (mobile option 4, main) | $23.97 | Oct 3 – 4 | |
| Mobile workflow research | $22.67 | Oct 3 – 4 | |
| Track A — orchestrator skill suite | $11.38 | Sep 16 – 20 | |
| D1(a) — audit-coverage source mode | $8.85 | Sep 20 – 21 | |
| Ship fence-injection | $7.68 | Sep 16 – 20 | |
| Notion read-only surface | $6.76 | Sep 6 – 12 | |
| S0 probe suite (95 sessions, 8 workspaces, excl. the $130.77 one above) | ≈ $8.56 | Sep 27 – 30 | 60 of 95 sessions cost **exactly $0** (synthetic, no model call); the rest average $0.15–$1.03 each |
| Everything else measured individually (bootstraps, currency-fix probes, Spike 9.3, Ship field manual, HTML orchestration dashboard) | ≈ $10.5 combined | — | |

**Total measured ≈ $1,900** over the window, with the three caveats in §1 (in-progress sessions,
orchestrator range, S0 zero-cost assumption) all pushing the true figure **upward**, not down.

**Concentration:** the top 5 rows above sum to **≈$1,440 — about 76% of everything measured.**
This is not a "death by a thousand cuts" profile; it's a small number of expensive workstreams
plus a long tail of cheap ones.

## 3. The orchestrator seat

Measured directly: 56 pages / 5,526 transcript records, Sep 12 – Oct 4 (22 days), 899 main-thread
assistant turns + 57 subagent-attributed turns.

**Two cost numbers disagree, and the gap is itself diagnostic.** Claude Code's own cumulative
`total_cost_usd` reads **$184.69** at the last `result` event. But that counter is not
monotonic — I found **17 downward corrections** across the session's 185 `result` events (e.g.
$20.99 → $5.08 on Sep 13; $14.18 → $8.29 on Sep 22; $112.23 → $107.69 on Sep 29), each coinciding
with either a succession (a new orchestrator incarnation taking the seat — this is explicitly
"succession 3" per the workspace name) or a compaction. Adding back every detected drop (the
standard way to recover a true cumulative total from a counter that resets) gives **$283.79**. A
second, independent cross-check — manually summing every individual assistant turn's `usage`
across the whole transcript, which can't suffer the same reset problem — gives **402M cache-read
tokens** for the main thread alone, roughly double what the last `modelUsage` reading (211M)
implies. Both signals point the same direction: **the displayed running cost under-reports a
long, compacted session**, and $185 is a floor, not the answer. I'm reporting $185–$284 rather than
picking one number.

**Tool mix: the orchestrator does its own work; it rarely delegates.** Across 899 main-thread
turns it issued **782 Bash calls, 43 Grep, 23 Read, 12 WebFetch, 11 Skill, 7 Write — and only 5
Agent (subagent) calls** in 22 days. Bash alone produced 865,545 characters of tool-result text
(vs. 143,210 from Read, 32,536 from Grep) — by far the largest single source of context growth.
Bucketing those 782 Bash commands by what they actually did:

| Bucket | Calls | Result chars |
|---|---|---|
| git log / diff / show / status | 205 | 308,081 |
| other (untyped miscellany) | 307 | 200,036 |
| transcript polling (`session message`, `message get`) | 62 | 105,385 |
| cat / head / tail / sed -n | 22 | 100,675 |
| `gh pr` / `gh issue` / `gh api` | 103 | 96,959 |
| `conductor workspace`/`session` list/get/status | 50 | 35,017 |
| grep / rg / find | 6 | 14,191 |
| watcher / sleep | 25 | 4,906 |

Git-state polling is the single biggest bucket, bigger than transcript-polling. This matches the
coordination role (checking what landed, what's open, whether a worker's claimed state is real)
rather than looking like runaway waste — but the volume, relative to 5 total subagent dispatches
in 22 days, says the orchestrator is choosing "go look myself" over "ask something cheaper to look
and report back" nearly every time.

**Rate limiting is real, frequent, and has no safety valve.** Every `rate_limit_event` in this
session carries `overageStatus: "rejected"` / `overageDisabledReason: "out_of_credits"` /
`isUsingOverage: false` — overage is off, so a saturated 5-hour window is a hard wall, not a
throttle. I found **24 actual `status: "rejected"` hits** (not just `allowed_warning` near-limit
readings) across the 22 days. Cross-referencing against the 27 gaps of 8+ hours between consecutive
transcript messages: **12 of those 27 long gaps begin within 10 minutes of a confirmed rejection.**
Summing just those 12 gives **≈134 hours of rate-limit-attributable stall** in the orchestrator's
own session alone, out of 22 days (528 hours) elapsed — roughly a quarter of the window. (The other
15 long gaps are most likely ordinary overnight/offline periods; I'm not attributing those to rate
limiting.) Since the account's rate-limit windows are explicitly `unifiedWindows` — one shared
five-hour and seven-day pool across every session on the account — a worker hitting the ceiling
blocks the orchestrator too, and vice versa; this is an account-wide constraint, not a per-seat one.

**Model mix:** `claude-opus-5[1m]` (pre-succession) cost $102.99 of the $184.69 last reading;
`claude-opus-5-5[1m]` (post-succession) cost $81.47; `claude-haiku-4-5` cost $0.22. The succession
(new orchestrator incarnation) coincided with a model generation upgrade, roughly splitting the
seat's lifetime cost down the middle between the two.

## 4. Model routing — was the tier/effort right for the job?

Dispatch briefs name their own reasoning (`ROUTING (FB-0091): model X · effort Y · why: ...`),
which makes this auditable without guessing intent. Six representative examples, verbatim:

- **CV1 (xhigh, opus) — escalation after failure, explicitly justified:** *"the first attempt at
  this fix was already defeated by review; that is the evidence this deserves xhigh, not an
  assumption."* This is the single most expensive dispatch in the window ($502 in the session I
  can see). The brief is honest that it's a retry, but **the defeated first attempt's own cost is
  invisible to this audit** — it isn't a separate workspace I can find, so either it happened
  inside this same long session before the brief text was written (in which case $502 already
  includes the waste) or it happened somewhere I have no visibility into (in which case true CV1
  rework cost is higher than measured). Either way: the escalation decision itself reads as
  correctly calibrated — "architecture, one-way-door, already failed once" is exactly the profile
  `xhigh` exists for.
- **Track A — orchestrator skill suite (opus/high):** justified on blast radius, not surface
  difficulty — *"a wrong version there auto-approves plans that should escalate, which fails
  silently... Not routed down despite the 'just author some skills' surface appearance."* Correct
  call: $11.38 for four shipped gate-policy skills is cheap insurance against a silent-failure
  class this repo has been burned by repeatedly (see CLAUDE.md's Consistency-discipline section).
- **`/flow:audit-coverage` source-mode / coverage-recall (opus/high, both):** both justified as
  "gate machinery... fails silently... not routed down." Both cost real money ($8.85 and $135.80)
  but both are editing a reviewer that gates every future `/flow:ship` — proportionate.
- **Mobile research (sonnet/high) — a deliberate *downshift*, and the stated reason is capacity
  management, not quality:** *"It's reversible, and the program's one critical-path worker needs
  the account's capacity."* This is the clearest evidence the orchestrator is already informally
  rationing the shared rate-limit pool via model choice — a real practice, but one that exists only
  in prose inside individual dispatch briefs, not as a written rule anywhere.
- **Spike 9.3 — auto-plan quality (sonnet/high):** *"judgment-heavy reading and one bounded
  experiment, no shipped artifact... if it turns out to need real design work, say so and I will
  re-dispatch one tier up rather than have you grind."* $1.49 total — correctly cheap, and the
  brief pre-commits to an escalation path instead of just hoping sonnet is enough.
- **Closeout (sonnet/medium):** explicitly *not* bumped to high because "nothing here is gate
  machinery and nothing needs designing," despite running two full ship pipelines. $42.69 — the
  medium-effort bump (one tier above the routing table's docs-only default) tracks the actual work
  (two pipelines + a rebase) rather than the content type.

**Net read:** I found no case of a dispatch that was *under*-routed and then needed costly rework
because of it — every "this was expensive" case I found was an explicit, justified escalation
(CV1) or a routing choice that priced in blast radius correctly from the start (Track A, both
audit-coverage dispatches). The routing discipline documented in FB-0091 appears to be genuinely
followed, with reasons that hold up, not rubber-stamped. The one gap: **routing decisions that cite
a prior failure (CV1's "defeated by review") don't name *which* prior attempt or its cost** — so
"was the escalation itself worth it" is not currently answerable from the brief alone. See
recommendation #3.

## 5. Workspaces vs. subagents

The orchestrator's own ratio (782 Bash calls vs. 5 Agent calls, §3) already shows it defaults to
doing things itself rather than delegating within its own session. The workspace-vs-subagent
question is really about a different axis: when does a job get its **own Conductor workspace**
(durable, its own sandbox, its own branch, survives the orchestrator restarting, consumes its own
slice of the shared rate-limit pool) vs. staying an **in-session subagent** (cheap, shares the
caller's context and git state, dies when the caller's turn ends)?

**Workspaces, used correctly:** Track A, Track B, CV1, the mobile options, the currency fix — each
needed its own branch, its own `/flow:ship` pipeline, and independence from the orchestrator's own
lifecycle (some ran for days while the orchestrator seat itself succeeded twice). This is the
right primitive for that shape of work, and nothing in the data suggests over-provisioning here.

**Workspaces, used for something a subagent would have done more cheaply: the S0 probe suite.**
95 sessions across 8 workspaces, testing whether a rule-skill loads under different arms/models.
Each workspace paid a **setup/bootstrap tax before any probe content ran** — directly measured at
$0.14–$0.21 per workspace for the "Setup Verification" / "Flow Plugin Installation" / "SETUP_OK
Verification" session that always runs first. That's only ~$1.2–1.6 total, small in dollars. But
**60 of the 95 probe sessions made literally zero model calls** (`documentation`/`exploration`/
`general` probe types: `num_turns: 1`, all-zero `usage`, measured $0 on all 5 direct checks) — the
*workspace* existed, was created, listed, and will eventually need archiving, for a probe that
never talked to a model at all. A single in-session subagent fan-out (one driving session, up to
95 `Agent`/`Task` calls) would have shared one sandbox, paid the bootstrap tax exactly once, and
produced the same 95 results. The dollar cost here is genuinely small; the **pattern** is the
thing worth flagging, because it's the same pattern that would compound if probe-style campaigns
(testing N variants × M conditions) become a recurring technique rather than a one-off — each
additional workspace is fixed overhead a subagent fan-out wouldn't carry.

**Subagents, used correctly: `/flow:staff-review`'s four parallel lenses.** These run as in-session
`Agent` calls, scoped to one diff, sharing the calling session's git state, and dying with it. I
found no evidence any of the four lenses were mis-provisioned as a workspace instead — this is the
one place in the program where "subagent, not workspace" is already the default, and it's the
right default.

**Rule of thumb this data supports:** workspace when the job needs its own branch/PR/ship pipeline
or must outlive the dispatching session; subagent when the job is read-mostly, single-purpose, and
finishes within the calling session's own turn. The S0 probes match the subagent description
exactly and were run as workspaces anyway.

## 6. Waste patterns, ranked by measured cost

1. **Rate-limit stalls — ~134 confirmed hours, orchestrator seat alone (§3).** Not a token-spend
   number; a velocity number, which is exactly what Ben flagged. Ranked first because it is the
   most directly measured, most repeated, and most on-point to the stated concern. Every hit is a
   hard wall (`out_of_credits`, no overage), not a slowdown.
2. **CV1 rework — $582.18 measured, likely an undercount (§4).** $502.32 in the session explicitly
   described as a retry after "defeated by review," plus $79.86 in a follow-on session; the
   defeated first attempt's own cost is not visible to this audit at all.
3. **S0 probe suite's workspace-per-probe pattern — ≈$1.2–1.6 in pure bootstrap tax, small in
   dollars, wrong primitive (§5).** Flagged for the pattern risk if probe-style campaigns scale up,
   not for the dollar amount measured here.
4. **Orchestrator's own git/gh/transcript-polling via raw Bash — 865,545 chars of tool output over
   22 days, the single largest tool-result category, against only 5 subagent dispatches in the
   same window (§3).** Not inherently wasteful — coordination needs ground truth — but the volume
   relative to how rarely it delegates suggests some fraction could be a narrower, purpose-built
   query instead of full Bash + eyeball each time.
5. **Cost-counter resets — 17 downward corrections, ~$99 of "lost" running total in the
   orchestrator seat (§3).** Not wasted spend itself; it means anyone (human or the orchestrator)
   reading Claude Code's own live running-cost number mid-session, right after a compaction, sees
   a number that's silently too low.

**Not found, despite looking:** review rounds that found nothing costing anything material (the
few `APPROVED` / `No issues flagged.` outcomes I sampled were from reviewers that are supposed to
output exactly that on a clean pass — that's the design, not waste); evidence of under-routed
dispatches causing expensive rework (§4); stale-plugin-caused re-dispatches in this window (flow
was current — v1.57.0 — at audit start, and `claude plugin list` showed no 1.29.0-style staleness
to react to).

## 7. Context management

The orchestrator runs on a 1M-token context window (`opus-5-1m` / `opus-5-5-1m`). Average
cache-read per main-thread turn is roughly 200,000–445,000 tokens depending on which of the two
measurement methods in §3 you trust — consistent with operating near the top of a 1M window for
most of its 899 turns, which is cheap per-token (cache reads are heavily discounted) but still adds
up at this frequency. Compaction is evidenced indirectly through the 17 cost-counter resets (§3);
I did not find a direct "compaction happened" marker in the transcript schema to count separately.

**Dispatch briefs are not generic boilerplate.** Spot-checked 6 of them (§4) — each names a
specific file, path, or behavior-class reason, not a restated copy of CLAUDE.md or the routing
table. No evidence of brief bloat in this sample; if brief-restating-the-repo is happening
elsewhere, it isn't in the 6 I read.

## 8. Ranked recommendations

Deciding nothing; building nothing. Each names an expected saving, what it costs, and how you'd
know it worked.

1. **Raise or remove the account's rate-limit ceiling (overage, a higher tier, or both), or add an
   explicit utilization-aware throttle to the orchestrator's own dispatch loop** ("don't open a new
   worker above N% of the shared window"). **Expected saving:** recovers a meaningful share of the
   ~134 measured stall-hours — the single biggest lever on "make progress," which is the thing Ben
   actually asked about. **Cost:** real $ if it's overage/a higher tier; pure discipline (and some
   dispatches waiting longer) if it's a throttle instead. **How you'd know:** fewer
   `status: "rejected"` events paired with an 8+-hour gap in the next audit window.
2. **Run probe-style campaigns (N variants × M conditions, single bounded turn each, no own
   branch/PR) as in-session subagent fan-outs instead of one Conductor workspace per probe.**
   **Expected saving:** ~$1.50 plus setup latency per 8-workspace campaign at today's scale — small
   now, but it scales linearly with campaign size while a subagent fan-out wouldn't; also removes
   8 workspace-lifecycle actions (create/list/archive) from the orchestrator's own plate, which is
   the same kind of overhead item #4 below is about. **Cost:** a subagent's output is harder to
   resume or inspect independently after the session ends than a durable workspace's is. **How
   you'd know:** the next probe-style campaign's total workspace count is ~1, not ~8.
3. **When a dispatch brief cites "defeated by review" or similar as grounds for an effort
   escalation, require it to name the defeated attempt's session/workspace id and (if known) its
   cost — not just assert that it happened.** **Expected saving:** none directly; this is an
   auditability fix, not a cost fix — right now CV1's true rework cost cannot be fully measured
   because the first attempt isn't traceable. **Cost:** one more field in the dispatch-brief
   convention. **How you'd know:** the next escalation-after-failure case has a working link from
   the retry brief back to the original session.
4. **Treat the orchestrator's own git-log/diff/gh-pr/transcript-polling Bash usage (865K chars,
   the largest tool-output category, §3) as a candidate for a narrower purpose-built query** —
   the same shape of thing this audit's own scripts do (one targeted API call + aggregation,
   instead of a raw command plus eyeballing the output). **Expected saving:** not sized here —
   genuinely don't know what fraction of 205 git calls / 103 `gh` calls / 62 transcript-polls is
   necessary ground-truth-checking vs. habit, and sizing that needs a follow-up measurement, not a
   guess. **Cost:** building and maintaining one more internal tool. **How you'd know:** Bash's
   share of the orchestrator's own tool-result characters drops in the next window.
5. **Flag the non-monotonic running-cost counter (§3, 17 resets / ~$99 "lost") as platform
   feedback, not a flow action.** This is Claude Code product behavior, not something this repo
   can fix. **Expected saving:** none to flow directly; the value is that nobody (human or
   orchestrator) is misled by a live total that silently drops after a compaction. **Cost:**
   nothing on flow's side beyond writing this down. **How you'd know:** not flow's to verify.
