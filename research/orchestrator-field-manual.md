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
| T5 | **Ground-truth sweeps that read `origin/main` do not see open branches** | A worker re-derived its FB number from `main` correctly and still collided with three numbers claimed on an open PR branch | Sweep `git ls-remote` / `gh pr list` as well. Observed live at succession-3 boot — the fifth FB collision in this program |

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

## 3. Presentation rules the human has stated directly

- **Always hyperlink PR numbers** — `[#149](https://github.com/by-dev-tools/flow/pull/149)`,
  inline *and inside tables*, no exceptions. Stated as not optional. The lapse recurs
  specifically inside status tables, which is exactly where the cost is highest.
- **One message per worker.** A batched message with per-worker sections got the wrong
  instruction read by the wrong worker.
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
