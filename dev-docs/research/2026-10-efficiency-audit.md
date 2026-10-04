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
and `/flow:audit-coverage`'s recall measurement. Token spend *mix* is mostly defensible once you
look at what each dollar bought (§4) — model routing held up on every dispatch checked, with no
under-routed rework found. The real velocity loss is narrower than "the account has no overage"
alone suggests: the orchestrator's own 134 measured idle-hours following a rate-limit rejection
turn out, on inspection, to be the seat going fully dormant until Ben happens to send any message
— not evidence of specific work sitting blocked (§3). The sharper, directly-confirmed waste is on
the **worker side**: workers that hit the shared account-wide limit, whose 5-hour window clears,
and then sit dark for hours more because nobody has re-pinged them — the orchestrator's own resume
message to one worker states this outright ("you hit the limit around 04:00 UTC; it reset at
04:30 and it is now ~14:30"). Whether to buy more headroom (overage / a higher tier) is Ben's
call, not a recommendation this audit makes — §8 presents it as a decision with the measured cost
next to it.

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

**Rate limiting is real and frequent, but the orchestrator-side gaps are NOT "work blocked by the
limit" — they're the seat going fully dormant until Ben manually nudges it.** (Revised after the
orchestrator's own review of a first draft of this doc, which rightly pushed back on treating all
idle time as limit waste: the seat is idle by design whenever nobody is messaging it — that's the
pre-execution/merge human gate working as intended, not waste.) Every `rate_limit_event` here
carries `overageStatus: "rejected"` / `overageDisabledReason: "out_of_credits"` /
`isUsingOverage: false` — overage is off, so a saturated 5-hour window is a hard wall. I found
**24 actual `status: "rejected"` hits** across the 22 days, and **12 of the 27 gaps of 8+ hours
between consecutive messages begin within 10 minutes of one of those rejections**, summing to
**134.0 hours**. But checking what arrived during each of those 12 gaps (every inbound message,
by sender) shows the same shape **12 times out of 12**: exactly one message arrives, and it lands
at the very end of the gap, from Ben directly (no worker relay), and it is content-free —
*"continue"*, *"Continue"*, *"continue (and make sure the workers that were stopped continue
too)"*. **None of the 12 show a worker report or a Ben decision sitting queued and stuck during
the gap** — there's nothing here that was *waiting* on the limit; the seat just stopped running
entirely and needed Ben to notice and re-send *anything* before it could resume, regardless of
whether the underlying 5-hour window had already cleared by then. That's a real, measured
mechanical-restart lag (the account's own hard stop plus however long until a human happens to
check back in) — but it is not evidence that 134 hours of coordination work was sitting blocked,
and I'm not claiming that. Since the account's rate-limit windows are `unifiedWindows` — one
shared five-hour/seven-day pool across every session on the account — a worker hitting the
ceiling affects the orchestrator's own budget too, and vice versa; this is an account-wide
constraint, not a per-seat one, which is what makes the worker-side finding below the sharper one.

**The clearer waste is on the worker side, and it's directly confirmed in-transcript, not
inferred.** Checked 5 worker sessions active this week (Sep 27 – Oct 4): **10 gaps of 8+ hours**,
clustering into ~3 distinct wall-clock windows where *multiple* worker sessions went dark
simultaneously (confirming the account-wide shared pool). In the clearest instance, the
orchestrator's own resume message to the `currency+visual-fix` worker says it outright: *"You hit
the session limit around 04:00 UTC; it reset at 04:30 and it is now ~14:30"* — the 5-hour window
itself was only blocking for ~30 minutes; **the other ~10 hours is pure coordination lag**, the gap
between the window clearing and the orchestrator noticing and re-pinging the worker. A second
instance an hour later is captured even more explicitly: *"Orchestrator (auto-resume). The account
session limit that stopped you has reset. Resume exactly where..."* This is the pattern the
orchestrator asked me to isolate, and it is the right thing to rank as waste: not the rate-limit
window (bounded, ≤5h by design), but **the time between reset and the next human-or-orchestrator
touch that actually resumes the worker**.

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

**Workspaces, used for something a subagent would have done more cheaply — for SOME of the S0
probe suite, not all of it.** 95 sessions across 8 workspaces, testing whether a rule-skill loads
under different arms/models. I initially recommended running this whole suite as an in-session
subagent fan-out instead; checking the actual setup commands for each arm (per the orchestrator's
correction) shows that recommendation is right for some arms and wrong for others:

- **Arms `c2`, `c-old`, and `c-v1`'s follow-up session genuinely needed their own workspace.**
  Their setup messages (verbatim, `claude plugin marketplace add ~/flow-src` then
  `claude plugin install flow@flow`) **reinstall a specific flow plugin snapshot — e.g. the
  pre-v1.51.0 shape, or the probing branch's own copy — at plugin scope**, which is Claude-Code-
  installation-wide state, not session-local. A subagent spawned from a parent session shares that
  parent's plugin registry; it cannot hold its own, different `flow@flow` install at the same
  time, so these arms could not have been subagents without clobbering whatever the parent (or a
  sibling subagent) had installed. The `9c542643` "S0 option c" exploration session (the $130.77
  one, §2/§6) is testing the same live hypothesis and is correctly its own workspace for the same
  reason.
- **Arms `a`, `b`, `d`, and `c`'s own setup (no plugin reinstall step — just scrubbing the repo to
  a neutral consumer project) show no evidence of needing a distinct installed version.** These —
  and the 60 zero-cost `documentation`/`exploration`/`general`-type probes within them — are the
  ones the subagent-fan-out recommendation actually applies to.

Each workspace paid a **setup/bootstrap tax before any probe content ran** — measured at
$0.14–$0.21 for the "Setup Verification" / "SETUP_OK Verification" / "Flow Plugin Consumer Setup"
session that runs first. Small in dollars (~$1.2–1.6 total across all 8 workspaces); the pattern
is still worth flagging for the subset where it applies, because it's the shape that would compound
if probe-style campaigns grow — but **it does not apply uniformly to "the S0 probe suite,"** and
the recommendation below is scoped accordingly.

**Subagents, used correctly: `/flow:staff-review`'s four parallel lenses.** These run as in-session
`Agent` calls, scoped to one diff, sharing the calling session's git state, and dying with it. I
found no evidence any of the four lenses were mis-provisioned as a workspace instead — this is the
one place in the program where "subagent, not workspace" is already the default, and it's the
right default.

**Rule of thumb this data supports — qualified by the plugin-install constraint found in §5:**
workspace when the job needs its own branch/PR/ship pipeline, must outlive the dispatching
session, **or needs its own distinct installed-plugin state** (a Claude Code install is
machine-scope, not session-scope); subagent when the job is read-mostly, single-purpose, finishes
within the calling session's own turn, and doesn't touch that shared install state. Arms `a`,
`b`, `d`, and `c` of the S0 probe suite match the subagent description and were run as workspaces
anyway; arms `c2`, `c-old`, `c-v1`, and the `9c542643` exploration session do not — they
deliberately exercise a different installed plugin version each, which a subagent cannot do
without clobbering a sibling's or the parent's own install.

## 6. Waste patterns, ranked by measured cost

1. **Worker-side rate-limit coordination lag — 10 confirmed 8+-hour gaps across 5 worker sessions
   this week, directly confirmed in-transcript (§3).** Not the rate-limit window itself (bounded,
   ≤5h by design) — the orchestrator's own words to one worker: *"you hit the session limit around
   04:00 UTC; it reset at 04:30 and it is now ~14:30."* The waste is the ~10 hours between reset
   and the next re-ping, repeated across multiple workers in overlapping windows (confirming the
   account-wide shared pool). Ranked first because it's the one rate-limit finding that's
   confirmed as *lost* time rather than merely correlated with a rejection — see item 2 for why
   the orchestrator's own 134 idle-hours do NOT belong in this same bucket.
2. **CV1 rework — $582.18 measured, likely an undercount (§4).** $502.32 in the session explicitly
   described as a retry after "defeated by review," plus $79.86 in a follow-on session; the
   defeated first attempt's own cost is not visible to this audit at all.
3. **Orchestrator's own git/gh/transcript-polling via raw Bash — 865,545 chars of tool output over
   22 days, the single largest tool-result category, against only 5 subagent dispatches in the
   same window (§3).** Not inherently wasteful — coordination needs ground truth — but the volume
   relative to how rarely it delegates suggests some fraction could be a narrower, purpose-built
   query instead of full Bash + eyeball each time.
4. **S0 probe suite's workspace-per-probe pattern, for the subset that didn't need its own
   install — ≈$0.6–0.8 in pure bootstrap tax (arms `a`/`b`/`d`/`c` only; §5).** Small in dollars;
   flagged for the pattern risk if probe-style campaigns scale up, not the amount measured here.
   Explicitly does NOT include arms `c2`/`c-old`/`c-v1`, which needed their own workspace.
5. **Cost-counter resets — 17 downward corrections, ~$99 of "lost" running total in the
   orchestrator seat (§3).** Not wasted spend itself; it means anyone (human or the orchestrator)
   reading Claude Code's own live running-cost number mid-session, right after a compaction, sees
   a number that's silently too low.
6. **Orchestrator-seat mechanical-restart lag — 134.0 measured hours following a rate-limit
   rejection, deliberately ranked last and separated from item 1 above (§3).** Checking what
   arrived during each of the 12 qualifying gaps shows, 12 times out of 12, exactly one message —
   Ben's own content-free "continue," landing at the very end. There is no evidence any of the 12
   had a worker report or decision sitting queued and blocked; this looks like the seat going
   fully dormant until any human touch restarts it, not specific work being held up. Listed for
   completeness (it's a real, measured number) but NOT folded into item 1's total, because the
   evidence for "this was limit-caused waste" is much weaker here than for the worker-side case.

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

1. **This one is Ben's call, not a recommendation flow can act on unilaterally: raise or remove
   the account's rate-limit ceiling (overage, a higher tier, or both).** It's a cost decision
   against a measured stall cost, not an obvious win — presenting both sides rather than
   recommending a direction. **Measured cost of the status quo:** confirmed worker-side
   coordination lag of ~10 hours per shared-limit event, 10 such events this week alone across 5
   sessions checked (§3, §6 item 1) — this is the number that would shrink with more headroom,
   not the orchestrator's own 134 idle-hours (§3/§6 item 6), which the evidence doesn't support
   attributing to the limit itself. **Cost of raising it:** real $, scaling with usage, uncapped
   until a new ceiling is chosen. **How you'd know it worked:** fewer confirmed worker-side
   coordination-lag events in the next audit window, independent of whether the orchestrator's own
   134-idle-hour number changes at all (it shouldn't, if that number really is "waiting for Ben"
   rather than limit-caused).
2. **Add an explicit utilization-aware throttle to the orchestrator's own dispatch loop**
   ("don't open a new worker above N% of the shared window," or "re-ping any worker whose window
   has reset within M minutes of the reset, not whenever someone happens to check"). Unlike #1,
   this is a flow-side process change, not a spend decision. **Expected saving:** directly targets
   the confirmed worker-side coordination lag (§6 item 1) without raising the ceiling at all.
   **Cost:** pure discipline — the orchestrator (or a lightweight watcher) has to actually poll
   reset times and act on them. **How you'd know:** the gap between a worker's window reset and
   its next re-ping shrinks from ~10 hours toward the reset latency itself.
3. **Run probe-style campaigns as in-session subagent fan-outs instead of one Conductor workspace
   per probe — scoped to arms that don't need a distinct installed plugin version** (§5). Checking
   the actual setup commands shows this applies to arms `a`/`b`/`d`/`c` of the S0 suite (no
   plugin-scope reinstall) but NOT to `c2`/`c-old`/`c-v1`, which explicitly install a different
   `flow@flow` snapshot each — state a subagent can't hold independently of its parent's own
   install. **Expected saving:** ~$0.6–0.8 plus setup latency per campaign at today's scale for the
   qualifying arms only — small now, but scales with campaign size. **Cost:** a subagent's output
   is harder to resume or inspect independently after the session ends than a durable workspace's
   is; also requires correctly classifying which arms need their own install before choosing the
   primitive, which this audit had to discover by reading setup commands rather than assume.
   **How you'd know:** the next probe-style campaign's non-install-dependent arms run as ~1
   workspace, not N — while arms that genuinely need a distinct plugin install keep their own.
4. **When a dispatch brief cites "defeated by review" or similar as grounds for an effort
   escalation, require it to name the defeated attempt's session/workspace id and (if known) its
   cost — not just assert that it happened.** **Expected saving:** none directly; this is an
   auditability fix, not a cost fix — right now CV1's true rework cost cannot be fully measured
   because the first attempt isn't traceable. **Cost:** one more field in the dispatch-brief
   convention. **How you'd know:** the next escalation-after-failure case has a working link from
   the retry brief back to the original session.
5. **Treat the orchestrator's own git-log/diff/gh-pr/transcript-polling Bash usage (865K chars,
   the largest tool-output category, §3) as a candidate for a narrower purpose-built query** —
   the same shape of thing this audit's own scripts do (one targeted API call + aggregation,
   instead of a raw command plus eyeballing the output). **Expected saving:** not sized here —
   genuinely don't know what fraction of 205 git calls / 103 `gh` calls / 62 transcript-polls is
   necessary ground-truth-checking vs. habit, and sizing that needs a follow-up measurement, not a
   guess. **Cost:** building and maintaining one more internal tool. **How you'd know:** Bash's
   share of the orchestrator's own tool-result characters drops in the next window.
6. **Flag the non-monotonic running-cost counter (§3, 17 resets / ~$99 "lost") as platform
   feedback, not a flow action.** This is Claude Code product behavior, not something this repo
   can fix. **Expected saving:** none to flow directly; the value is that nobody (human or
   orchestrator) is misled by a live total that silently drops after a compaction. **Cost:**
   nothing on flow's side beyond writing this down. **How you'd know:** not flow's to verify.
