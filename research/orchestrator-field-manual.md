# Orchestrator field manual — measurement traps and standing calls

> **Status: LIVING.** Companion to `2026-08-23-flow-cloud-workflow-plan.md` (⭐ canonical).
> That doc is the *design* of the orchestrator seat — §4.8 the job description, §4.9
> succession, §4.10 the skill suite. This doc is the *operational residue*: the specific
> ways measuring this system has produced confident wrong answers, and the standing
> resolve-vs-escalate calls a fresh seat would otherwise re-derive from scratch.
>
> - **Created:** 2026-09-12, at the succession-3 boot.
> - **Why it exists:** every item below was held as a **sandbox-local memory file** by a
>   prior orchestrator seat and passed forward only inside the transient succession brief.
>   That violates §4.9's disposability invariant in the one direction it cannot survive —
>   a sandbox-local file is recoverable from neither GitHub nor the Conductor API — so each
>   rotation re-learned these by being told, or by re-making the mistake. Writing them here
>   is §4.9 wind-down step 2 applied to knowledge rather than to artifacts.
> - **Deletion criterion** (§1 requirement 7): each trap below dies when a mechanical check
>   subsumes it. § 1 traps die when `/flow:orchestrate` performs the sweep itself; § 2 dies
>   when `/flow:gate` implements the §4.8 four-axis classification. Delete the row, not the
>   file, as each lands — an empty § is the signal to delete the file.

## 1. Measurement traps — each produced a confident wrong answer

Every one of these returned a *clean-looking* result. That is the shared signature, and it
is the reason they are grouped rather than filed separately: **a suspiciously tidy result is
the symptom, not the reassurance.** Three separate wrong conclusions in this program shared
it — a zeroed force-push count, a transcript search that matched the orchestrator's own
question and reported PRESENT when the truth was ABSENT, and a substring search that came
back clean while two workers were rate-limited.

| # | Trap | What it looked like | What to do instead |
|---|---|---|---|
| T1 | **`conductor sql` truncates long values** — and as of 2026-09-12 returns HTTP 503 (disabled sometime before that date) | A `substr(transcript, …, 500)` search returned clean while two workers sat rate-limited | Read transcripts in ~100–150 char chunks; never conclude ABSENT from one substring query |
| T2 | **A rate-limited worker never wakes itself and cannot ping you** | `Status: idle` — indistinguishable between "waiting at a gate" and "died hours ago" | Poll the **`Updated` timestamp**, not the status. `conductor session status <id>` exposes it. This is §4.8 rule 6's named known gap |
| T3 | **Never read git state while a git command is still running** | Reading mid-rebase on #138 showed commits apparently dropped | Wait for the command to exit. Nothing was lost; the false conclusion was one step from a destructive force-push |
| T4 | **Keep-both conflict resolution preserves content, not ordering** — and is correct *only* for append-only content | A blanket keep-both on #146 duplicated JSON keys and resurrected three deliberately-deleted files | Distinguish *deleted-by-this-branch* (`git log --diff-filter=D main..branch`) from *added-to-main-after-fork* before resolving |
| T6 | **Composing a message or commit body as a double-quoted shell string executes its backticks and `$(...)`** | A quoted source comment lost a word; a `git commit -m` with backticked command names actually *invoked* one | Use `--message-file` / `git commit -F` with a heredoc-written file. Never put prose you did not author into a shell word |
| T5 | **Ground-truth sweeps that read `origin/main` do not see open branches** | A worker re-derived its FB number from `main` correctly and still collided with three numbers claimed on an open PR branch | Sweep `git ls-remote` / `gh pr list` as well. Observed live at succession-3 boot — the fifth FB collision in this program |

**The shell-composition trap is not a beginner error, and priming does not prevent it.** T6
fired **four times in the single session that created this file**, among agents who had each
just finished reasoning about that exact hazard:

1. [#148](https://github.com/by-dev-tools/flow/pull/148)'s heredoc delimiter collision — a
   **refuted design**, and the reason the add-entry fast follow exists at all.
2. An orchestrator message quoting a source comment: backticks substituted, a word silently
   vanished — **silent data loss**.
3. A worker's `git commit -m` with backticked command names: substituted and *run*, invoking
   the plugin-update command that session had just agreed to defer — **unintended execution**.
   Harmless only because the substitution stripped its argument.
4. That same worker's message **reporting instance 3** — mangled by instance 3's own bug.

Note the escalation across the first three: refuted design → silent data loss → unintended
execution. Then note the fourth, which is the whole argument in one event: **the report of the
failure was destroyed by the failure it was reporting.** A hazard that corrupts its own incident
report cannot be managed by attention, because attention is exactly what it consumes and then
eats.

Note also what all four share — every author was maximally primed. This is the strongest
available argument that the fix belongs in the *interface* rather than in author discipline, and
it is first-hand rather than theoretical. **Standing rule for this seat: compose every worker
message and commit body via a file (`--message-file`, `git commit -F`), never as a quoted shell
argument.**

**Capability claims expire.** A ⚠️/OPEN marker plus a stated resolution cost is an
instruction to run the test, not a conclusion to inherit. A prior seat told the human that
cloud workspaces could not use `RunLocalCommand`, by reading §2.4's *working assumption* as a
*finding*; the capability exists and the test took minutes. `.claude/rules/documentation.md`
§ "Recorded rejections" already says this — it applies to the plan's own provenance markers too.

## 2. Standing calls — resolve silently vs escalate

Canonical §4.8 gives the four-axis gate policy and the seven communication rules. These are
the recurring cases that policy does not name explicitly, settled once here.

**Resolve silently, do not ask** (§4.8 rule 1 + rule 7):

- **Version-number and FB-number collisions between concurrent workers.** Assign
  deterministically — the branch pushed first and closest to merge keeps its claim; the other
  re-sweeps. Issue the **self-healing rule** with the assignment: *at every rebase, re-read
  `origin/main` **and** open branches; if either is at or above your claim, take the next free
  value and re-sweep immediately, without asking.*
- **Stale or conflicting PRs after a merge.** Message each affected worker to rebase
  immediately; do not wait to be asked.
- **Stalled workers**, and everything about how work is sequenced between them.

**Escalate** — merges, and high-stakes / high-taste / one-way-door / gate-machinery calls.
Note that escalating still means deciding *in the orchestrator seat* (§4.8 rule 5): the
approval authority is the human's, the interaction surface stays the orchestrator.

## 2a. Live finding — the demote qualifier has no producer (2026-09-13)

`walk_extract.py` selects the **first non-demoted Spec-walk heading**, where demoted means the
heading carries `(shipped)` / `(merged …)` / `(demoted)`. Four consumers read that qualifier —
`walk_extract`, `extract-criteria`, `extract-visual-states`, `visual-significance`.

**Nothing in flow writes it.** `/flow:land` flips *status-line* references to `merged (#N)` and
moves items to "Recently shipped"; its `SKILL.md` contains zero occurrences of `demote` or
`Spec-walk`. `ship`'s only `demote` is manifest-entry classification (`auto` → `ask`),
unrelated. So the qualifier is hand-written or not at all — a **fifth FB-0085-class instance**
(read by four consumers, produced by none), and it is the root cause of the laundered-PASS
hazard below.

Measured on `origin/main` 2026-09-13 (corrected figures — an earlier orchestrator count of
"35 of 60 PR blocks" was wrong on both the unit and the heading type):

| | count |
|---|---|
| `## PR —` blocks | 31 |
| **Spec-walk headings** | **59** |
| Spec-walk headings demoted | **3** |
| **active** (what the parser chooses among) | **56** |

The winner on `main` is the **merged** vacuous-criterion block ([#148](https://github.com/by-dev-tools/flow/pull/148)).
So a plan block appended below it inherits a shipped PR's checkboxes, and
`/flow:verify-build` + `/flow:audit-coverage` grade the new diff against already-passed criteria
and report green.

**Two traps inside this one.** First, demoting the `## PR —` heading buys nothing — the parser
reads the *Spec-walk* line; on `main`, 7 PR headings carry a merged/shipped qualifier and 3 of
those still have an unqualified Spec-walk block beneath. The place authors naturally update is
not the place the parser reads. Second, **running `/flow:land` does not fix this** and would
make it look fixed — the confidence-inverting shape again. Land is still worth running for its
actual job (status lines, roadmap, CHANGELOG currency); it is simply not this fix.

The strongest remedy on offer is the one the *consumer* project already built:
[health-tracker#116](https://github.com/byamron/health-tracker/pull/116)'s `assert-block`, which
refuses to verify unless the selected block is the current PR's — failing loudly instead of
depending on an author remembering to demote.

**Deletion criterion:** delete this section when a producer writes the qualifier, or when an
`assert-block` equivalent ships in flow and the selection can no longer be silently wrong.

## 3. Presentation rules the human has stated directly

- **Always hyperlink PR numbers** — `[#149](https://github.com/by-dev-tools/flow/pull/149)`,
  inline *and inside tables*, no exceptions. Stated as not optional. The lapse recurs
  specifically inside status tables, which is exactly where the cost is highest.
- **One message per worker.** A batched message with per-worker sections got the wrong
  instruction read by the wrong worker.

  **The misroute is undetectable from both ends, and the delay is unbounded.** The wrong
  recipient silently absorbs an instruction that was never theirs; the intended worker simply
  never receives one and has nothing to notice the absence of. Observed: a succession-2
  "vacuous-criterion approved to execute" instruction landed in the *Notion* workspace and
  surfaced only at the succession-3 boot — a fortnight later, and only because that worker
  volunteered it while reporting something else. It cost nothing **by luck**: the correct
  worker held its own copy and shipped the work as
  [#148](https://github.com/by-dev-tools/flow/pull/148). Treat the one-message-per-worker rule
  as load-bearing rather than tidy, and when a worker reports an instruction that is not its
  own, always resolve where the *intended* recipient ended up — do not assume a duplicate.
- **Large text blocks read worse than an agent assumes.** Stated directly: a verbose
  orchestrator recreates the exact attention cost the seat exists to remove (§1 requirement 5).

## 4. Program facts a fresh seat asks for in its first hour

- **Measured throughput: ~1.25 PRs/day** (20 merged 2026-08-26 → 2026-09-10).
- **The binding constraint is the shared five-hour rate window plus the human merge gate —
  not agent throughput.** 3–4 concurrent workers is the useful maximum; beyond that the fleet
  stalls together (§1 requirement 6, [F23]).
- **Notion surface constraint:** the token is a GitHub Actions repo secret `NOTION_TOKEN` and
  is **never** pasted into chat or into any file. The repo's secret-blocking hook is
  filename-based only (`*.env*`, `*credentials*`, `*secret*`) and will not catch a token
  sitting in an ordinary `.md` or `.py`.

## 5. README currency — a standing debt with a per-feature release condition

`README.md` is the user-facing marketplace/install/use doc and it has **not** been reconciled
against the 2026-08 cloud-workflow program. Ben's standing direction (2026-08-27): **draft the
changes now, implement each one only when its feature has actually landed and the claim is true.**
Shipping a README that describes unbuilt behaviour is precisely the class Phase 00 exists to fix, so
a batched end-of-program rewrite is the wrong shape — fold each correction into the ship that makes
it true (canonical §4.5/§4.6: no standalone docs-only land PR).

**One claim on `main` is false right now**, and it is the reason this section exists rather than a
roadmap line. Verified verbatim at `a156228`, 2026-09-13:

```
README.md:86: - **4 auto-loading rules** that attach by file path — workflow discipline, plan requirements, doc format, exploration triggers.
```

The AGENTS.md spike's E1 measured that `paths:` on a `SKILL.md` **never activates**. Those four
rules have therefore not loaded for any consumer since v1.33.0, while the README has advertised them
the whole time. Do **not** fix the line on its own: **S0 decides the wording.** If S0 makes the rules
load, the claim becomes true and needs no edit; if it cannot, the claim needs correcting. Editing now
means guessing which, and rewriting twice. This is the FB-0085 class surfacing in user-facing copy —
shipped, advertised, never loading.

**Owed updates, each gated on its feature landing:**

- **`toolchain` manifest kind** (shipped [#132](https://github.com/by-dev-tools/flow/pull/132),
  v1.32.0) — the loop/gate description never mentions that a change can be honestly "verifiable in
  principle, but not on this host," which drafts the PR rather than green-ticking it. **Landed; safe
  to write now.** This is the only one currently unblocked.
- **`README.md:86` / the four rules** — blocked on S0, as above.
- **Orchestrator skill suite** (§4.10 — `/flow:orchestrate`, `/flow:spawn`, `/flow:handoff`,
  `/flow:gate`) — decided, not built. The skill list needs these **only once they ship**.
- **D1 prototype-first gate** — changes where the first human gate sits for designer-role projects.
  The README describes the current plan-approval gate; revisit after D1 Phases 1–2.

**Correction to an earlier version of this debt:** a previous seat carried "17 skills / 9 agents /
33 slots" as owed countable claims requiring an FB-0010 fan-out sweep. Measured 2026-09-13:
`README.md` and `.claude-plugin/marketplace.json` on `main` carry **no** such countable claims, and
the real counts are **22 skills / 10 agents**. **That item is closed — do not re-open it.** Recorded
here because an inherited to-do that turns out not to exist costs a future seat the same
investigation twice.

**Deletion criterion (FB-0088):** delete this section when every gated item above has either shipped
its README edit or been dropped with a reason — i.e. when the README makes no claim about the
cloud-workflow program that is not true on `main`.

## 6. Model routing at dispatch — the procedure, not just the table

**The table already exists** (`research/2026-08-22-conductor-orchestration.md` §6, carried
forward by canonical §4.3) and **FB-0091** already says the orchestrator routes itself as
deliberately as it routes workers. What did not exist is a seat that *runs* the procedure.
Measured 2026-09-14: **4 of 4 live workers were `opus-5-1m`** — including a parked one doing
nothing — and no dispatch in this program logged a `model·effort·why`. Specified, believed
effective, never applied: the FB-0085 shape, one level up from code.

### The framing, which is right-sizing and NOT rationing

Ben's direction, 2026-09-14, and it inverts the emphasis a cost-anxious seat naturally takes:

> *"In practice I don't think we should need to worry much about running into usage limits (we
> shouldn't sacrifice legitimate parallel workers just to stretch out usage) and using the right
> model for the job should help us make that reality. But we also shouldn't be afraid to use a
> powerful model when necessary and valuable."*

So the goal is **to stop the five-hour window being the binding constraint**, not to run fewer
workers under it. Two failure modes, and the second is the one this seat has been committing:

- **Over-spending** — everything on the top tier, which is where we are.
- **Under-dispatching** — holding back a legitimate parallel worker to conserve budget. That is
  the *wrong* economy: it trades throughput, the scarce thing, for tokens, the cheap thing.
  Never decline a worker that has real work for budget reasons; right-size it instead.

### The lever that matters most

**Effort is a bigger lever than model tier.** Tier sets price *per token*; effort sets *how many
tokens*. A strong model at low effort routinely costs less than a weak model at high effort,
because a weak model flails and **flailing in an agentic loop is billed**. So the first question
at dispatch is not "can this be cheaper?" but "what does this job actually need?"

| Job | Model | Effort |
|---|---|---|
| Orchestrator — triage, relay, dispatch | `sonnet-4-6-1m` | low–medium |
| Feature work, full flow loop | `opus-5-1m` | high |
| One-way door / architecture / **gate machinery** | `opus-5-1m` or `fable-5` | xhigh–max |
| Bug fix with a known repro + failing test | `sonnet-5-1m` | medium |
| Docs, changelog, doc-currency | `sonnet-4-6-1m` | low |
| Mechanical sweep — **non-flow only** | `haiku-4-5` | low |
| Spike / research | `sonnet-5-1m` | medium–high |

**Escalation rule — start one tier down, let evidence promote, re-dispatch rather than grind.**
Flow already emits the promotion signals: a LOW-confidence assumption, a `/flow:critique-plan`
REDIRECT, a `/flow:verify-build` Unknown, or two loops on one failure. **A stuck cheap worker
burns more than a fresh strong one, and a fresh context is worth more than a persuaded one.**
Promotion is a re-dispatch, never a mid-session switch — changing model or effort mid-conversation
breaks the prompt cache and forces a full re-prefill.

**Fast mode is nearly always wrong for a worker:** ~2.5× output speed at ~2× price, and nobody is
watching an unattended worker.

### The one hard floor

**Gate machinery does not get routed down.** `ship` / `manifest-triage` / `skip-audit` /
`verify-build` / `pr-coherence`, and the consumer-side G2 equivalents, stay top-tier at high
effort. A wrong answer there fails *silently* — a mis-classifying gate passes bad work — which is
the one error class where a cheaper model's savings are not worth having. This is the same
`sensitivePaths` set §4.8 uses for the plan gate, deliberately.

### What the orchestrator must do at dispatch

1. Pick `model · effort` from the table.
2. **Log the `why` in one line, in the dispatch brief itself.** FB-0091's requirement. Without
   it there is no audit trail to tune against, which is why the table has gone unapplied.
3. Re-check at promotion: if a signal fires, re-dispatch a *fresh* worker one tier up rather
   than arguing with the stuck one.

**Worked application — the three phases approved 2026-09-14.** None of them is Opus work, and
saying so concretely is the point:

| Phase | Job shape | Route | Why |
|---|---|---|---|
| 1 — `harness_audit.py:157` | bug fix, known repro, exact line | `sonnet-5-1m` · medium | `tools/`, not shipped; the bug is located and the fix is one list entry |
| 2 — orchestrator discipline | docs only | `sonnet-4-6-1m` · low | prose into two existing docs, no code |
| 3 — `doctor` shell extraction | refactor + eval rewrite | `sonnet-5-1m` · medium–high | mechanical, but it touches a shipped skill and two eval suites, so not the bottom tier |

Contrast the current fleet, all correctly top-tier under this same table: add-entry (rewrites
`manifest-triage`), version-honesty (edits `ship/**`), Trio (`/verify-queue`, the G2 gate) — all
gate machinery, all `opus-5-1m`. **The problem was never that those three are Opus. It is that
everything else was too, by default rather than by decision.**

**Deletion criterion:** delete this section when `/flow:spawn` (§4.10) applies the table and emits
the `model·effort·why` line itself — at which point the procedure is executable rather than
remembered, which is the whole point of §4.10.

## 7. Presenting multiple open PRs — always state the queue order and why

**Ben's standing direction, 2026-09-16:** whenever more than one PR is open, say explicitly whether
they can be queued **at the same time**, or whether one will conflict so the others must be queued
**later, after preparation**. Do not leave him to infer it from a list.

This is not bookkeeping. Queuing two PRs that collide costs a merge-conflict resolution done under
time pressure by whoever notices second — and `plan.md` conflicts are the class most likely to be
resolved by a blind union, which produces two contradictory status blocks and a Spec-walk extractor
that selects the wrong PR's criteria. The cheap moment to catch it is before the queue, not after.

**How to determine it — measure, never predict from file names:**

```sh
A=$(gh pr view <n> --json files --jq '[.files[].path]|sort|.[]')
B=$(gh pr view <m> --json files --jq '[.files[].path]|sort|.[]')
comm -12 <(echo "$A") <(echo "$B")            # the ONLY possible conflict sites
git merge-tree $(git merge-base $HA $HB) $HA $HB | grep -c '^<<<<<<<'   # 0 = clean
```

Disjoint file sets are a *guarantee* of no textual conflict, not an estimate. Overlap is not a
guarantee of conflict — two PRs can add entries to different sections of one file and merge fine —
so when they overlap, run the `merge-tree` simulation rather than assuming the worst.

**Report it in one of three shapes, explicitly:**

- **"Queue both now — disjoint file sets, merge simulation clean."**
- **"Queue #A now; #B needs a rebase after it lands — they collide in `<file>`."** Name the file and
  say who will do the rebase.
- **"Queue #A only; #B is not ready for a reason unrelated to conflicts"** (red CI, an open decision).

**The structural reason this keeps coming up in this repo:** the append-only docs were fragmented to
one file per entry ([#146](https://github.com/by-dev-tools/flow/pull/146)), which removed the dominant
conflict source — two PRs writing a history entry no longer touch the same file. What remains is
`plan.md` and `roadmap.md`, both deliberately edited **in place**. So the practical rule of thumb,
which the measurement should still confirm rather than replace: **two docs PRs usually merge clean;
two PRs that both carry a plan block usually collide in `plan.md`.**

**Deletion criterion:** delete this section when `/flow:orchestrate` computes and prints the queue
order itself.
