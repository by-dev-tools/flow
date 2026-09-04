# Rescued lesson-contribution queue records (2026-09-04)

**Status:** temporary rescue. **This directory is expected to be deleted** — see § Deletion criterion.

## What these are

Three `status: queued` records from the `/flow:ship-spike` Step 4c lesson-harvest queue (FB-0059),
produced by the spike on branch `conductor/spike-designmd-investigation-vercel-agentic-design-guidance`
(PR #140) and created `2026-09-03T06:42:23Z`. They are the normal input to `/flow:contribute`.

## Why they are in git instead of the queue

`contributionsQueuePath` defaults to `~/.claude/plugins/data/flow/contributions` — **user-scope storage
inside the workspace**. That is correct on a persistent machine and correct-by-design for the
cross-project contract (a lesson harvested in project A must be visible to a `/flow:contribute` run
rooted in the flow checkout). It is wrong on an **ephemeral cloud workspace**, where the whole
filesystem is destroyed at teardown, typically within ~24h. These three records were minutes from
being lost that way.

Committing them puts them in git, which survives teardown by construction. That is also a working
demonstration of the durability fix being proposed — the queue should ride a substrate that already
survives, rather than a store that has to be remembered before archiving a workspace.

The same defect has already been recorded once, in a different subsystem: `dev-docs/history.md`
(AB Step 1, 2026-08-27) notes that the harness-audit marker file is *"gitignored/per-clone, so under
the now-active flow cloud workflow (ephemeral per-PR workspaces) every fresh workspace's first
`--audit-due` reports 'due'"*. Two subsystems, one root cause — user-scope persistence predates
flow's cloud workflow and has not been revisited.

## What was and was not committed, and why

| Artifact | Committed? | Reason |
|---|---|---|
| 3 queue records (`*.json`) | **Yes**, with one surgical redaction | Small, high-value, and the evidence the durability proposal rests on |
| 3 evidence windows (`*.window.jsonl`) | **No** | ~61 KB each of raw session transcript. `sanitize_tokens.py scan` flags them, and they contain **private-repo names and internal doc paths** (`byamron/health-tracker`, `decisions/design-language`). `by-dev-tools/flow` is a **public** repo — that content does not belong here. They are reconstructable from the session transcript if ever needed; each record retains its `lesson_hash` and the original window basename |
| Disagreements store | **N/A** | `~/.claude/plugins/data/flow/disagreements` was never created this session — no `/flow:log-disagreement` fired. Nothing to rescue |

**The one redaction:** `evidence.window_path` held an absolute sandbox home path
(`/home/vercel-sandbox/...`). Replaced with a placeholder; the original basename is preserved in a
sibling field. Nothing else was altered — the lesson text is byte-for-byte as harvested.

### Why these were NOT run through the full `sanitize_tokens.py scrub`

Because scrubbing **corrupts them**. `known_tokens.json` records the origin project slug as `flow`,
so a full scrub rewrites the literal, correct path `plugins/flow/skills/general/SKILL.md` into
`plugins/<project>/skills/general/SKILL.md` and `project_slug: flow` into `project_slug: <project>` —
destroying the actionable target the record exists to carry.

That is a real, separate finding worth its own entry: **the sanitizer's project-token model assumes
the origin project is not flow.** When flow harvests from its own repo, "flow" is not a foreign token
to be scrubbed, it is the literal path — and scrubbing degrades the record instead of protecting it.

Running `scan` on the committed copies still exits 1 with a single survivor, `project-token: flow`.
That survivor is a **false positive in this context**: the destination repo *is* flow, so the token
cannot leak anything. The genuine survivor class (home paths) is gone; verified absent along with
every private-repo token (`health-tracker`, `ripe`, `music-app`, `byamron`, `portfolio`).

## Deletion criterion (FB-0088)

**Delete this entire directory when either of the following is true:**

1. `contributionsQueuePath` points at durable storage (synced, or a git-backed path) **and** these
   three records have been drained normally by `/flow:contribute` — i.e. they have become flow edits,
   FB entries, or recorded dismissals; **or**
2. The records are drained by any other route and the durability fix lands, making an ad-hoc rescue
   directory redundant.

This directory is a workaround for a storage defect, not a new store. It must not accumulate further
records, and no tooling should be taught to read from it — if something starts depending on it, the
durability fix was never made and that is the bug to fix instead.

## The records

| File | Source type | Confidence | Summary |
|---|---|---|---|
| `...scope-a-check-coverage-defect-to-the-full-advert.json` | `decision` | 0.9 | Scope a check-coverage defect to the full advertised guarantee, not the one instance you noticed |
| `...shipship-spike-never-state-whether-a-docs-only-d.json` | `taste` | 0.9 | `ship`/`ship-spike` never state whether a docs-only diff should bump the plugin version |
| `...accessprovenance-caveats-in-research-docs-need-a.json` | `error` | 0.6 | Access/provenance caveats in research docs need a re-check trigger, not just a warning |

All three carry `recurrence_count: 1` — which is itself the finding. In an ephemeral workspace the
count is structurally pinned at 1 forever, so the source-diversity bar stops deferring weak signals
and starts destroying them.
