# Flow cloud workflow — the canonical plan

> **⭐ CANONICAL — this is the up-to-date plan.** Written 2026-08-23. It consolidates and
> supersedes the *design* content of every prior cloud-workflow doc (genealogy in §0);
> where any older doc disagrees with this one, **this one wins**. The 2026-08-22 research
> note remains authoritative for its raw *facts* (this doc cites them rather than
> re-deriving); its §8 design proposal is superseded here.
>
> - **Date:** 2026-08-23
> - **Status:** PLAN — approved direction, staged for execution (§5). Step 1 is queued work;
>   nothing in this doc is built yet except what §0 marks shipped.
> - **Owner:** Ben. **Scope:** org-wide (all 8+ Conductor projects), with flow-plugin changes
>   where the pipeline needs new vocabulary.
> - **Provenance legend used throughout:** ✅ measured/verified live this session ·
>   📄 docs-derived · 🤝 reported by the Trio session (not independently verified here) ·
>   ⚠️ open conflict between sources.

## 0. Doc genealogy — what this consolidates, and the status of each

| Doc | Where | What it contributes | Status after this doc |
|---|---|---|---|
| `research/2026-08-22-conductor-orchestration.md` | flow repo | 24 verified platform facts, measured cost model, model-routing table, sleep/wake probe | **Facts remain authoritative** (cited as `[F#]` below). §8 design + §10 templates **superseded** — the ledger loses its state-tracking role (§4.3), the dispatch brief survives |
| `core-docs/cloud-local-workflow-plan.md` | Trio repo | Tiered cloud/local split, PR-label queue (D6), ambient environment detection (D2), one-pipeline rule (D1), `/verify-queue`, industry evidence | **Direction absorbed; two corrections + one re-sequencing** (§2.3, §4.2). The Trio-local artifacts it specifies (placement rule, `/verify-queue`, greenlight queue) remain valid to build — *after* Step 1 here, and with Appendix B replaced by the flow-native manifest (§4.2). Mark its header: "superseded as architecture by flow `research/2026-08-23-flow-cloud-workflow-plan.md`; local artifacts still to build per its §3, amended" |
| `dev-docs/handoffs/service-agnostic-roadmap-2026-07.md` | flow repo | The `tools/flow` CLI direction; hooks fail-open on non-Claude hosts | Unchanged — referenced, not superseded |
| PHASE0 worker plan (`conductor/phase0-concurrent-work-check-cloud-inert`) | flow repo, in flight | Step 2 concurrent-work sweep fix | Unchanged — it is Step 2 of §5, already at its plan gate |

**Cleanup owed:** the two "superseded" edits above (08-22 note status line — done in the same
change that adds this doc; Trio doc header — owed in the Trio repo, listed §5 step 6).

## 1. What we want — requirements, stated once

These are the definition of done for the whole program. Each carries its rationale; none is
aspirational filler.

1. **One pipeline, environment-keyed placement — never a fork.** A second workflow drifts on
   every flow upgrade *and routes around `/flow:audit-skips`*, flow's native machinery for
   judging skips. A declared, environment-keyed skip flows **through** the audit. (Trio D1,
   sharpened; verified against the audit engine ✅ §2.2.)
2. **A session can never claim verification it could not perform.** Cloud has no Apple
   toolchain; the false-"done" class is the one flow exists to catch (FB-0018, FB-0062,
   FB-0066). Mechanical, not advisory.
3. **The queue is durable git state — PRs + a label — never workspace or ledger state.**
   Workspaces sleep at 1 h idle and die at ~23.8 h [F9, ✅ measured]; PRs don't. A parallel
   ledger can drift from PR reality; a label *is* PR reality. (Trio D6, adopted over the
   08-22 note's ledger — see §4.3 for what survives of the ledger.)
4. **Gates stay human and stay countable.** Flow's two (plan approval, merge) plus exactly
   one new one — **G2 promotion** (draft → ready after a real Mac verify pass) — which the
   environment split genuinely forces. Not a ceremony budget; a cap.
5. **One place to look.** The orchestrator's actual product is attention: dispatches out,
   pre-triaged decisions in, one chat. (The original ask of the 08-22 session.)
6. **Concurrency is capped by the shared five-hour rate window, not by token price.** Every
   worker draws on one subscription budget [F23, ✅ observed `rate_limit_event`:
   `five_hour`, overage `rejected`/`out_of_credits`]; N workers exhaust it ~N× faster and
   the whole fleet stalls *at once*. Admission control reads `resetsAt` before dispatching.
7. **Facts over procedures; every artifact carries a deletion criterion** (FB-0088). A
   harness that scripts judgment becomes a ceiling as models improve; the failure mode is
   never removing the right thing later (FB-0077 precedent).

## 2. Validated claims and corrections

### 2.1 Load-bearing facts (consolidated; provenance on every row)

| # | Claim | Provenance |
|---|---|---|
| C1 | Conductor cloud = Linux, permanently; no macOS cloud option | 📄 Conductor docs; 🤝 Trio empirical (no `swift`/`xcodebuild`/`clang` in sandbox) |
| C2 | The public API + MCP are **cloud-only**; local Mac workspaces are invisible to both | ✅ [F6] — checked across 4 projects; MCP docs state no local execution |
| C3 | **Idle sleep at exactly 3600 s; max lifetime 23.8 h** | ✅ [F9, F21] — env vars + live probe |
| C4 | A queued message **wakes a sleeping workspace; agent replies in ~12 s** | ✅ [F22] — end-to-end probe |
| C5 | Conductor MCP live at `api.conductor.build/mcp`, 20 tools incl. `create_workspace`, reachable **from cloud** | ✅ [F24] — `tools/list` enumerated (went live mid-session 08-23; staged rollout) |
| C6 | flow pre-installs into every cloud workspace from the cloud-computer image, user scope — but **version-pinned by the image** (was 1 commit stale) | ✅ [F10, F11]; 🤝 Trio confirms the install path independently |
| C7 | Session transcripts carry full per-message token usage; cache read:create measured 10:1 on a long session; output ≈ 208 K for one research session | ✅ [F17, §5 of 08-22 note] |
| C8 | One shared five-hour rate window per subscription; overage currently rejected | ✅ [F23] |
| C9 | `git worktree list` returns only itself in cloud → flow Step 2's concurrent sweep is inert there; `git ls-remote` / `gh pr list` work fine | ✅ [F7, F8] — the PHASE0 bug, fix in flight |
| C10 | Industry pattern: every major cloud agent is Linux; the standard is Linux-drafts → PR → macOS CI → human. Duolingo: Linux workers + Swift → 13.6 % of a batch burned on lint-only failures | 🤝 Trio research 2026-08-19 (3 parallel deep-dives). Direction-confirming, not load-bearing here |
| C11 | Xcode Cloud: keep as TestFlight/release gate only; too queue-flaky for per-iteration agent feedback | 🤝 Trio research |
| C12 | Self-hosted GHA macOS runner = $0 GitHub minutes | 🤝 Trio research (GH pricing) — matters only for the deferred Phase-1 runner |

### 2.2 Verified this session against flow's code (the keystone findings)

**The manifest vocabulary is closed and has no environment concept.** ✅
`manifest-triage.py` `KINDS = ('rigor','security','a11y','verify-build','coverage','skip-audit','status-surface','visual-deliverable')` — validated at `add-entry` write time. There is no way to emit "unverifiable on this host" through flow's non-forgeable manifest path today; it would have to be hand-written into the PR body, exactly the hand-authoring FB-0067/FB-0074 closed off.

**The skip auditor actively rejects the Trio plan's skip string.** ✅
`skip-audit-checks.py:257-258`: a verify-build skip is LEGITIMATE only when config says `platform ∈ {library,none}` or `verifyEnabled=false`; otherwise → `SHOULD-RE-RUN — skip claims platform library/none but platform='ios'`. Trio is `platform: ios`, so its Appendix-A canonical skip is **mechanically classified SHOULD-RE-RUN** by the very auditor D1 says the design must flow through. Flow models "no runnable target" as a *config property*; it has no concept of *"runnable in principle, not on this host."* That missing concept is Step 1.

**Both failure paths of shipping from cloud on an ios project were traced.** ✅
Run verify-build → cannot launch → Unknown → draft, but filed as `needs: regression fix` (wrong copy, wasted bounded-retry). Skip it per the Trio rule → flow manifest empty → triage `READY` → ship Step 7 asserts `--want-draft false` while the rule forces draft → **read-back gate fails the ship**. Either way the local rule *fights* the gates instead of composing.

### 2.3 Corrections to prior docs (why the consolidation was needed)

| Prior claim | Correction | Consequence |
|---|---|---|
| Trio: "workspaces sleep after **4 h** idle" | ✅ Measured: **1 h** (`IDLE_TIMEOUT_MS=3600000`; probe slept at exactly 3600 s) | 4× overestimate. Any time-shifted design (wake windows, batch cadence) must assume 1 h. Cache TTL (1 h) == idle timeout: an orchestrator polling at 45–50 min keeps its prefix warm; at 90 min it re-pays cold start |
| Trio D8: upstream a flow `environment` concept **last**, after the local rule proves itself | **Re-sequenced to first** (§5 Step 1) | Without it the rule fights ship's gates (§2.2). The fix is small: one `KIND_COPY` entry + one ground-truth branch in the skip auditor. Keystone, not follow-up |
| 08-22 note §8: committed markdown ledger as the coordination substrate | Demoted (§4.3) — PR + label is the queue | The ledger kept state that PRs already express authoritatively; drift-by-construction removed by using the PR itself |
| 08-22 note: stage-split workers (plan worker → execute worker) | Already deleted by the wake probe [F22] | Recorded here so no future doc resurrects it |

### 2.4 The one open conflict — resolve before building anything Mac-bridge-shaped

**⚠️ `RunLocalCommand`.** Trio session: observed, attended (per-command user prompt), ≤10 min,
undocumented. This session: absent from the workspace toolset, and the MCP docs state cloud
cannot execute locally. Both can be true (feature-flagged, attended-only, or since removed).
**Why it matters:** if it exists attended, an attended cloud session can drive `xcodebuild`
on the Mac directly, and `/verify-queue` becomes a convenience rather than the load-bearing
G2 mechanism. **Resolution cost:** minutes, from the Mac (does the tool appear in a local
workspace's cloud-session toolset; does it fire). Until resolved, design assumes it does
NOT exist (fail-safe direction: the queue works either way; a bridge would only add a path).

## 3. Open questions (rest)

| Question | Why it matters | How to settle |
|---|---|---|
| `RunLocalCommand` (§2.4) | G2 mechanism shape | 5-min Mac check |
| Does Conductor surcharge `-1m` context variants? | Routing table defaults to `-1m` | Ask Conductor / billing |
| Subscription consumption weighting | Whether usage ratios can become absolutes | Not published; track ratios only (usage.tsv) |
| Does the wake-on-message hold for a workspace near its 23.8 h hard stop? | Long-queued G2 bounces might land on a dead workspace | Observe in practice; bounce falls back to PR comment (Trio's design already handles it) |

## 4. The design

### 4.1 One pipeline, three placements, three + one gates

Adopted from Trio (D1–D5), org-wide, with flow-native enforcement:

- **Studio (local, attended):** design, iteration, feel-tuning. The placement rule is inert
  (`CONDUCTOR_IS_LOCAL=1`). Zero added ceremony.
- **Autonomous draft (cloud, parallel):** only **greenlit** plans execute unattended. Cloud
  sessions never run `typecheckCmd`/`/flow:verify-build` where the toolchain is absent,
  never auto-invoke `/flow:ship` (the readiness predicate requires a positive behavioral
  PASS, which cannot exist there — this is flow's existing FB-0018 rule doing the work, not
  a new prohibition), and end every workstream as a **draft PR + manifest + label** or a
  queued plan. Never "shipped".
- **Verify pass (local Mac, batch):** `/verify-queue` sweeps `needs-mac-verify` PRs:
  build iOS+macOS, run tests, run `/flow:verify-build` against the plan's Spec-walk, pass →
  promote to ready (G2) / fail → bounce with a build-log excerpt as PR comment + best-effort
  Conductor wake-message to the originating workspace [C4 makes this cheap: 12 s].
- **Gates:** G1 greenlight (plan approved for autonomous execution — this is flow's existing
  plan-approval gate, routed through the orchestrator), **G2 promotion** (the one genuinely
  new gate), G3 merge (unchanged; `/flow:ship` never merges).

**Platform-conditional, not iOS-only:** for web/library projects the toolchain exists in
cloud, verify-build runs (or self-skips per config), and the placement rule imposes nothing.
The split activates only where `platform` requires a toolchain the host lacks.

### 4.2 Step 1 — the `toolchain` manifest kind (the keystone, and a flow-plugin change)

What flow is missing is one concept: **"verifiable in principle, not on this host."** Three
small edits give the whole program a native, non-forgeable spine:

1. **`manifest-triage.py`:** add `"toolchain"` to `KIND_COPY` — plain-language copy per the
   existing schema (`means`: "This change needs a build toolchain this machine doesn't have,
   so the behavioral checks are queued for a machine that does." · `clears_when`: the verify
   pass runs green on a toolchain host · `needs_you`: nothing in-session — process the queue
   on the Mac · never waivable-to-ready, same as `verify-build`).
2. **`skip-audit-checks.py`:** one new LEGITIMATE branch for verify-build/typecheck skips:
   skip_reason names a missing toolchain **AND** ground truth confirms it
   (`command -v xcodebuild` fails / `CONDUCTOR_IS_LOCAL=0` while `platform` needs Apple
   tooling) → LEGITIMATE; claimed on a host that *has* the toolchain → SHOULD-RE-RUN.
   Symmetric with the existing `platform library` branch at `:257`; keeps rule 3 of
   `general.md` (the check verifies presence-of-reason against ground truth, not absence).
3. **Ship §7a.6 needs no change:** a `toolchain` entry on the manifest → verdict ≠ READY →
   draft PR + rendered manifest block, read-back-verified — the existing machinery produces
   Trio's Appendix-B outcome *through* the non-forgeable path. **Appendix B (hand-authored
   manifest) is retired**; the rendered block replaces it. The `needs-mac-verify` label is
   applied by the placement rule at PR-open (label ≠ manifest: the label is the queue key,
   the manifest is the human-readable state).

Eval fixtures required per the quality bar: a red fixture (ios-platform toolchain-skip on a
toolchain-present host → SHOULD-RE-RUN) and a green one (same skip, toolchain absent →
LEGITIMATE), plus the triage-kind render test. This is exactly the shape of change flow's
existing harnesses pin.

### 4.3 The orchestrator, narrowed to what git cannot express

The 08-22 note's orchestrator survives with half its ledger deleted:

- **Queue/state/blocked-on:** gone — the PR's draft status + `needs-mac-verify` label carry
  them authoritatively (Requirement 3).
- **Survives in the ledger:** model/effort per dispatch + why (feeds `usage.tsv` auditing),
  owned-paths assignment (admission control), triage `Overrides` (drains into feedback.md
  via `/flow:contribute` — the learning loop), and the **serialization note**: `plan.md` /
  `history.md` / `roadmap.md` are shared-by-construction across every flow ship, so ships
  are *serialized*, never ownership-partitioned (learned twice: dispatch #1's correction and
  the PHASE0 worker's own rebase flag).
- **Dispatch:** Conductor MCP tools [C5] with the CLI as fallback; briefs per the 08-22 §10.2
  template (unchanged — it worked first try: PHASE0's worker respected every constraint,
  stopped at its gate, reported on contract ✅).
- **Admission control:** before dispatching, check (a) remote branches + open PRs for the
  item (the PHASE0-fixed sweep), (b) the five-hour window's `resetsAt` (Requirement 6) —
  hold the queue rather than dispatch into a near-exhausted window.
- **Model routing:** the 08-22 §6 table + escalation rule stand. First live data point:
  `sonnet-5-1m`/high produced an approvable plan with a real critique catch on a plugin-doc
  fix — starting one tier down works. Roster-hash + 60-day staleness tripwires stand
  (baseline `34bfa3137014f884`, reviewed 2026-08-22).

### 4.4 What is deliberately NOT built (each with its deletion criterion)

| Not built | Why | Revisit when |
|---|---|---|
| Self-hosted GHA macOS runner (Trio Phase 1) | Ben deferred (attendance/cost); `/verify-queue` manual-first proves the shape | The manual sweep exceeds ~1 sitting/week, or overnight batches start |
| `/flow:orchestrate` skill | Flow is project-agnostic; active roadmap decouples from hosts; Conductor API in plugin artifacts fights that | The pattern proves out AND can be expressed host-agnostically |
| Cost model / token estimator / model-selection classifier | Procedures that decay (FB-0088); `usage.tsv` ratios + the routing table suffice | Never, in this form — ratios promote to table edits by hand |
| Ledger state-tracking | PR+label is strictly better (Requirement 3) | n/a — deleted now |
| `tools/flow` CLI for the Step-2 sweep | Open fork owned by the service-agnostic roadmap; prose fix first (PHASE0 worker's explicit position, endorsed) | The CLI exists for other reasons |
| Cron/scheduler for overnight drafts | No native scheduler [📄 C-API]; external cron is Trio Phase 3 | ≥3 workstreams regularly queued at end-of-day |

### 4.5 Handoff without a docs-only PR class (the land-elimination)

`/flow:land` opens a *second* PR after every merge — doubling PR count and adding a
handoff hop — to flip `main`'s forward docs from `at PR (#N)` → `merged (#N)`, stamp the
history SHA, and clear held FB reservations. It exists because `/flow:ship` reconciles at
*PR-open* time and nothing reconciles at merge. Its load-bearing assumption is stated in
its own header [📄 land/SKILL.md §0]: the roadmap "Now" / plan "Current Focus" are what a
**cold reader — a new contributor, or the autonomous loop, a cold agent on each run —**
reads to decide what to do next. **The orchestrator model breaks that assumption:** the
next workspace is not a cold agent re-reading stale `main`; it is spawned by a coordinator
holding live state and handed a dispatch brief (§4.3, 08-22 §10.2). Land's primary consumer
disappears.

Land conflates two jobs; only one survives, and it needs no PR of its own:

| Land reconciles | In the orchestrator model |
|---|---|
| **Forward pointers** (roadmap "Now", plan "Current Focus", ▶ Next up) | **Superseded** — the dispatch brief carries "what's next" live; stale-between-merges is harmless when a coordinator knows the true frontier. |
| **Durable currency** (history status, cleared FB reservations, CHANGELOG) | **Still needed on `main`, but folded — not a separate PR.** |

The *only* reason durable currency needs an after-merge PR is one vestigial dependency:
**the merge SHA is unknown until merge** [✅ verified — #123's entire diff was stamping
`**SHA:** _(set at ship)_` → `merged #122 @ 8eb0497` + clearing two reservations]. Three
changes collapse land to ~nothing:

1. **Reference merged PRs by `#N`, not SHA, in history.** `#N` is known at ship time; GitHub
   already maps `#N` → its merge commit. Drop the SHA convention and the post-merge stamp
   has nothing left to write — the ordering dependency (must run *after* merge) evaporates.
2. **Clear reservations at ship in the common case.** Land held them only because a
   concurrent sibling branch was live; in the orchestrator model the coordinator *knows*
   whether siblings are live (admission control, §4.3) and tells ship, instead of defaulting
   to hold-then-reconcile-at-merge.
3. **Piggyback any true residual on the next ship.** Anything that genuinely cannot be
   written until after merge is absorbed by the *next* feature PR's Step 5a — zero extra PRs.

**Guardrail — currency still reaches `main` through a *reviewed* PR, never a direct push.**
The tempting shortcut (orchestrator commits currency straight to `main`) would bypass the
merge gate, which is flow's whole thesis (§6). The orchestrator speeds the *handoff to the
next workspace*; it does not get to skip G3. Durable currency rides the ship PR itself, or
the next one.

**Deletion criterion (FB-0088).** `/flow:land` is the artifact; its deletion criterion has
now arrived. It is deleted for any repo driven by an orchestrator once changes 1–3 land.
It is *retained* only for the pure-cold-autonomous-loop consumer with **no** coordinator —
where a cold agent really does re-read `main` to choose its next move, and forward-pointer
currency on `main` is load-bearing. That is a real deployment, so land stays in the plugin,
gated on a slot rather than run by default — the same "encode a fact, not a procedure"
discipline this session shipped.

### 4.6 Post-merge and archive in the orchestrator model — the two-lifetime handoff

Post-merge/archive safety carries a doc-currency requirement: reconcile the forward docs so
the *next* agent doesn't work from a stale `main`. Pre-orchestrator, that reconciliation is
what `/flow:post-merge` → `/flow:land` did — a second PR (the doubling §4.5 removes). The
orchestrator model splits doc-currency into **two lifetimes**, and only the second touches git:

- **Handoff currency — live, immediate, NOT in git.** The next workspace is
  orchestrator-spawned with a dispatch brief (§4.3/§4.5), so it never cold-reads `main`. The
  orchestrator carries the delta and states it in the brief ("#126 fixed the concurrent-work
  bug — work from current main"). A stale forward-doc on `main` therefore cannot mislead the
  next agent, because the next agent is not reading it.
- **Durable currency — eventual, GitHub.** The forward-doc reconciliation (roadmap "Now",
  plan "Current Focus", closing a resolved `§ Exploration` entry) **folds into the next ship's
  Step 5a** — batched into a substantive PR, never a standalone land PR (§4.5, changes 2–3).

**What this does to archive-safety.** Doc-currency stops being an archive *blocker*
(reconcile-via-land-PR-first) and becomes a tracked *follow-up*. A workspace is safe to
archive when:

1. Its PR is **merged**.
2. All **committed** work is in `main` (the branch tree matches for the changed files).
3. Nothing **uncommitted / unaccounted** remains in the sandbox — the workspace self-reports
   `git status` / `stash list` / untracked files. This is the one check only the sandbox can
   answer; the orchestrator asks it via `conductor message create`.
4. Any pending forward-doc reconciliation is **tracked to fold into the next ship AND the
   orchestrator holds correct live state** — NOT "`main` is fully reconciled right now."

Checks 1–2 are verifiable from any workspace via `gh` + git; check 3 requires asking the
sandbox; check 4 is a routing fact the orchestrator owns.

**State — including handoff state — is never a maintained artifact** (this is §4.4's
"ledger state-tracking deleted," generalized). It is *live* — the orchestrator's working
context + PR draft/ready/merged + labels + `conductor workspace list` — and *eventual* —
GitHub, via the next ship. A `status` column in a ledger is the wrong shape for the same
reason a land PR is: both duplicate state that already has an authoritative live source, and
both go stale. [✅ 2026-08-25 dogfood: a dispatch ledger written with a `status` column was
stale within minutes — `conductor workspace list` showed three just-created workspaces
already `deleted` while the ledger still read "dispatched." The live API was right; the
maintained artifact was wrong.]

**The one bound — "eventual" must not become "never."** Between a merge and the next ship,
the live handoff/currency state lives only in the orchestrator's session. If that session ends
before a ship carries it to GitHub, it is lost. So the orchestrator **flushes pending durable
currency to GitHub when the queue drains or at session end** — the next-ship fold is the
normal path; a session-end flush is the backstop. This bound is what keeps "eventual" honest.

**Provenance.** Derived from the 2026-08-25 orchestration dogfood — the first end-to-end
orchestrated loop (dispatch → execute → ship #126 → archive-check) run from a sibling
workspace via the `conductor` CLI. It extends §4.5 (land-elimination) from *ship-time*
forward-pointers to *post-merge/archive*, and reinforces §4.4 (no ledger state-tracking).

### 4.7 Human alongside the orchestrator (a consideration, not a feature)

Most implementation workspaces are orchestrator-driven, so the human works from the
orchestrator seat and doesn't track the others — but every worker stays open in the Conductor
UI, and the human may look in or intervene. This needs **no new machinery**; it rides the
re-sync the orchestrator already owes (§4.4/§4.6):

- **Reading is always safe** — opening a worker's transcript/diff disrupts nothing.
- **Writing goes to the same inbox `conductor message create` uses**, so a human message is
  indistinguishable from an orchestrator one. The only real risks are (a) conflicting
  simultaneous instructions the worker can't disambiguate, and (b) the orchestrator acting on
  a now-stale model.
- **Takeover detection is (b)-by-default and near-free:** because the orchestrator must
  re-read a worker's live state before acting on it anyway, it gets human-takeover detection
  for *one extra comparison* — if the latest inbound message is a `userMessage` it did not
  send, treat that worker as human-driven and back off until handed back. **(a) override:** the
  human says "I've got X" / "back to you on X" to set it explicitly. No takeover-lock, no new
  state — just the existing re-sync plus one check.
- **One hard rule:** don't message a worker that is actively mid-`/flow:ship` unless you mean
  to abort it — the one window a stray message can produce a half-ship. At rest or at a gate
  (plan approval / merge), a human message *is* the intended interaction.

The whole consideration reduces to: the human never *has* to touch a worker, and touching one
never corrupts anything, because state is live and the orchestrator re-syncs before it acts.

## 5. Execution sequence

| # | Step | Where | State |
|---|---|---|---|
| 0 | Resolve `RunLocalCommand` (§2.4) | Mac, 5 min | **open — next human action** |
| 1 | `toolchain` manifest kind + skip-audit branch + fixtures (§4.2) | flow plugin | queued — next dispatch after PHASE0; full flow loop, own PR |
| 1a | `#N`-not-SHA history convention (§4.5) — the tiny, high-leverage prerequisite that removes land's only after-merge dependency | flow plugin (ship/land skills + history format) | queued; **dogfooded first in this change** (currency folded here, no standalone land PR) |
| 1b | Fold durable currency into ship / next-ship; gate `/flow:land` behind a slot for the cold-loop-only consumer (§4.5) | flow plugin | after 1a; validate across a few merges before removing land from the default path |
| 2 | PHASE0: Step-2 sweep fix | flow plugin | **in flight — worker at plan gate, awaiting approval** |
| 3 | Trio-local artifacts: placement rule (emitting via `add-entry --kind toolchain`, not Appendix B) + `needs-mac-verify` label + `/verify-queue` + greenlit-queue section | Trio repo | after Step 1 ships |
| 4 | Orchestrator v1: dispatch skill + narrowed ledger + usage.tsv (§4.3) + post-merge/archive close-out + session-end currency flush (§4.6) | per-repo `.claude/skills/` | after 2–3 real dispatches validate the brief/report loop (1 of 3 done) |
| 5 | Re-read everything against 10 dispatches; cut what wasn't load-bearing | — | standing (FB-0088 discipline) |
| 6 | Doc cleanup: Trio plan header edit (§0); confirm 08-22 note status line | Trio repo / flow repo | with steps 3 / this change |

**Sequencing rationale:** Step 1 before Step 3 because §2.2 shows the local rule cannot
compose with ship's gates until the vocabulary exists — building Trio's artifacts first
would ship a hand-authored manifest and a skip string the auditor rejects. Step 0 is free
and can only *shrink* later steps. Step 4 last because the orchestrator is the piece whose
design most benefits from live dispatch data, and dispatch works today via CLI without it. Steps 1a/1b
are sequenced early and small: 1a is a one-line-per-entry convention change with immediate
payoff (this very change dogfoods it), and it must precede 1b because folding currency into
ship is only safe once nothing depends on an after-merge SHA stamp.

## 6. Relationship to flow's two-gate thesis

Nothing here adds a third *flow* gate. G1 **is** flow's plan-approval gate (relayed through
the orchestrator); G3 **is** the merge gate. G2 exists only where the environment split
does — it is the merge gate's *precondition* made mechanical (a draft PR cannot be merged
ready), not a new approval ceremony. Cloud auto-advance stays off not by new rule but by the
existing readiness predicate: no positive behavioral PASS can exist on a toolchain-less
host, so Step 8 always stops-and-presents there. The design's whole trick is that every new
behavior is an *instance* of machinery flow already has — manifest, skip-audit, draft
routing, read-back — with one added noun.
