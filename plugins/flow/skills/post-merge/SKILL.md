---
name: post-merge
description: >
  The "merged — anything left, or safe to archive?" skill (FB-0072). Human-invoked
  AFTER you merge a PR, it runs the whole post-merge close-out in one command:
  (1) confirms the PR is actually merged with a MERGE-QUEUE-SAFE gate (a queued PR
  that hasn't landed yet is "not merged YET", not a failure); (2) reconciles the
  forward docs by CALLING /flow:land (composition, not a reimplementation);
  (3) synthesizes the merge-gate feedback window /flow:ship structurally can't see
  (your review→iterate→merge comments) into user-scope agent memory + the
  /flow:contribute queue; (4) safe-deletes the merged branch; (5) prints a
  ✅ safe to archive / 🚫 not safe verdict. Never merges. Trigger: "/flow:post-merge
  <PR#>", "post-merge #N", "merged — safe to archive?".
disable-model-invocation: true
allowed-tools: Read, Edit, Write, Glob, Grep, Bash, Skill
---

You are running the flow **post-merge close-out** for a PR a human has already
merged (or just queued to merge). You **never merge anything**. This is the one
command that answers the question you ask on essentially every PR — "merged —
anything left to do here, or is it safe to archive?" — and does the close-out work
that question implies.

**Why this exists.** `/flow:ship` synthesizes feedback from the window that *closes
when the PR opens* — but your richest design-taste feedback lands *after*: you review
the PR + walkthrough at the merge gate, comment, the agent iterates, you merge. That
merge-gate window is structurally outside ship's synthesis, and there's no next ship
on the branch to catch it (FB-0072). `/flow:post-merge` captures it. It also folds in
the doc-currency reconciliation (`/flow:land`), the stale-branch cleanup, and the
archive-safety check you'd otherwise do by hand. `disable-model-invocation: true`: a
human runs this after merging — it must never auto-fire mid-loop.

**Composition, not combination (from #79).** This skill **calls** `/flow:land` for the
doc-currency step rather than reimplementing reconciliation. `/flow:land` stays a
narrow, independently-invocable skill (you can still run it alone after a GitHub-web
merge with no local workspace); `/flow:post-merge` is the orchestrator that also does
the feedback + cleanup + verdict around it.

## Project context (resolved at invocation)

- Project config: !`cat flow.config.json 2>/dev/null || echo "(no flow.config.json — using built-in defaults)"`
- Default branch: !`git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@' || cat flow.config.json 2>/dev/null | jq -r '.defaultBranch // "main"' 2>/dev/null || echo "main"`
- Current branch: !`git branch --show-current`
- Post-merge wait cap: !`cat flow.config.json 2>/dev/null | jq -r '.postMergeWaitSeconds // 150' 2>/dev/null || echo 150`

## Argument

`/flow:post-merge <PR#>` — the PR you just merged (or queued). If omitted, resolve the
open/most-recent PR for the current branch (`gh pr list --head "$(git branch --show-current)"`)
and **confirm the number with the user before any cleanup** — cleaning up the wrong
branch loses work. If you can't resolve a number, stop and ask; never guess.

## 1. Pre-flight — external CLI check (BLOCKING)

Per FB-0009, fail fast at the entrypoint with a clean hint rather than a mid-run `exit 127`.

```sh
MISSING=""
command -v gh >/dev/null 2>&1 || MISSING="$MISSING gh"
command -v jq >/dev/null 2>&1 || MISSING="$MISSING jq"
command -v git >/dev/null 2>&1 || MISSING="$MISSING git"
if [ -n "$MISSING" ]; then
  MISSING_TRIMMED=$(echo "$MISSING" | sed 's/^ //')
  echo "⚠️ BLOCKER: /flow:post-merge requires $MISSING_TRIMMED (missing on PATH)." >&2
  echo "   Install: macOS 'brew install$MISSING' · Debian/Ubuntu 'apt install$MISSING' · gh: https://cli.github.com" >&2
  case " $MISSING_TRIMMED " in *" gh "*) echo "   After install: gh auth login" >&2 ;; esac
  exit 1
fi
```

## 2. Merge-detect — the MERGE-QUEUE-SAFE gate (BLOCKING on terminal, patient on transient)

The load-bearing gate. It is **three-state**, not two — reserving fail-loud for a PR that
will *never* merge, and treating a still-`OPEN` PR as *not merged yet* (poll), so a merge
queue's 1–2 min delay never produces a false failure (FB-0072). The classification +
poll policy live in the deterministic helper; the loop's I/O (fetch + sleep) is here.

```sh
if [ -n "${CLAUDE_PLUGIN_ROOT:-}" ]; then H="${CLAUDE_PLUGIN_ROOT}/skills/post-merge/lib/merge-status.py"; else H="plugins/flow/skills/post-merge/lib/merge-status.py"; fi
[ -f "$H" ] || { echo "⚠️ BLOCKER: post-merge helper not found at $H — reinstall the flow plugin." >&2; exit 1; }
N="<PR#>"                                   # from the Argument step
CAP=$(jq -r '.postMergeWaitSeconds // 150' flow.config.json 2>/dev/null); [ -z "$CAP" ] && CAP=150
INTERVAL=20                                 # seconds between polls
ELAPSED=0
while : ; do
  BLOB=$(gh pr view "$N" --json state,mergedAt,autoMergeRequest 2>/dev/null)
  STATE=$(printf '%s' "$BLOB" | python3 "$H" classify)   # merged | closed | open
  VERDICT=$(python3 "$H" poll-verdict --state "$STATE" --elapsed "$ELAPSED" --cap "$CAP")
  case "$VERDICT" in
    proceed)
      echo "[post-merge] PR #$N is merged — proceeding." ; break ;;
    terminal)
      echo "🚫 BLOCKER: PR #$N is CLOSED without merging — nothing to close out here." >&2
      echo "   Not running doc reconciliation / branch cleanup on an unmerged PR. (If you meant to" >&2
      echo "   merge, reopen + re-merge the PR, then re-run '/flow:post-merge $N'.)" >&2
      exit 1 ;;
    wait)
      echo "[post-merge] PR #$N still open (queued/auto-merge?) — polling up to ${CAP}s; re-checking in ${INTERVAL}s…"
      sleep "$INTERVAL" ; ELAPSED=$((ELAPSED + INTERVAL)) ;;
    giveup-graceful)
      echo "🕒 PR #$N is still open after ${ELAPSED}s. If it's in a merge queue it may just need more time —" >&2
      echo "   re-run '/flow:post-merge $N' once it lands. (Nothing was changed; this is not a failure.)" >&2
      exit 0 ;;                             # graceful, distinct from the terminal exit 1
    *)
      # Defensive default: classify/poll-verdict always print one of the four words above, so this
      # only fires if the helper itself is broken (a bad edit / wrong Python). A FAILED `gh pr view`
      # (unauthed/network) yields an empty blob → classify 'open' → 'wait'/'giveup', absorbed as
      # "not merged yet" (safe; the queue-safety default) — NOT this branch. Distinguishing a broken
      # gh from a genuinely-open PR is a v1b follow-up (roadmap § Next). Fail loud, don't busy-loop.
      echo "🚫 BLOCKER: unexpected verdict from the merge-status helper ('${VERDICT}') — the helper may be broken." >&2
      echo "   Nothing was changed. Check the helper + 'gh pr view $N', then re-run." >&2
      exit 1 ;;
  esac
done
```

`autoMergeRequest` in the fetched blob is a *confidence* signal that a merge is intended —
you can trust the poll on a queue repo. A non-queue repo merges instantly, so `classify`
returns `merged` on the first pass and the loop never sleeps. `postMergeWaitSeconds: 0`
makes an OPEN PR give up immediately (fail-fast) instead of polling.

## 3. Doc-currency — call `/flow:land` (composition)

Now that the merge is confirmed, reconcile the forward docs by **invoking `/flow:land`** —
do NOT reimplement its reconciliation. `/flow:land` flips the item to "merged (#N)" across
roadmap / plan / history, clears reserved numbers, checks CHANGELOG currency, and opens
its own small `docs: land #N` PR. Because §2 already confirmed `merged`, `/flow:land`'s own
two-state merge gate (its §1a) is satisfied on its first check — no queue interaction.

```
Skill("flow:land")   # pass the PR number as its argument: /flow:land <PR#>
```

If `/flow:land` reports it already landed this PR (idempotent re-run), that's fine —
continue. If it errors, surface the error but continue to the feedback + cleanup steps
(they're independent of doc reconciliation); note the land failure in the final hand-off
so the human can re-run `/flow:land <PR#>` alone.

## 4. Merge-gate feedback synthesis (the delta window) — USER-SCOPE STORES ONLY (v1)

Capture the feedback from the window ship couldn't see — your merge-gate review → iterate
→ merge comments on THIS branch since the last ship. **v1 writes only user-scope stores**
(agent memory + the `/flow:contribute` queue), reusing the exact machinery `/flow:ship`
Step 4b/4c already uses. It does **NOT** write the repo `feedbackPath` doc (`dev-docs/feedback.md`)
— that would mean committing an `FB-XXXX` to a just-merged branch; deferred to v1b (the
transcript-timestamp watermark + an FB-inbox). **Content-match dedup** makes an overlapping
window safe: a lesson ship already captured re-matches its existing entry and appends a
fire-log date instead of duplicating (no watermark needed for v1).

Scope note (honest v1 limitation): this synthesizes best-effort from the **current session**
since the last ship on this branch. Robust multi-session / Conductor-worktree window
resolution is deferred to v1b.

**4a — agent failure-pattern memory** (mirror `/flow:ship` Step 4b): run the corpus health
check, apply the source-diversity bar, and write/refresh entries under
`~/.claude/projects/<canonical>/memory/`, matching before writing (dedup, not duplicate):

```sh
node "${CLAUDE_PLUGIN_ROOT}/tools/memory/check.mjs" 2>/dev/null || true
```

**4b — flow-generalizable lesson harvest** (mirror `/flow:ship` Step 4c): the same pre-scan
→ enqueue → mark path into the cross-project `/flow:contribute` queue. The pre-scan makes a
window with no merge-gate signal ~free.

```sh
if [ -n "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -d "${CLAUDE_PLUGIN_ROOT}/scripts" ]; then S="${CLAUDE_PLUGIN_ROOT}/scripts"; else S="plugins/flow/scripts"; fi
QUEUE_ROOT="$(jq -r '.contributionsQueuePath // empty' flow.config.json 2>/dev/null | sed "s#^~#$HOME#")"
[ -n "$QUEUE_ROOT" ] && export FLOW_CONTRIB_DIR="$QUEUE_ROOT"
MARKER="$(jq -r '.lastHarvestedPath // empty' flow.config.json 2>/dev/null | sed "s#^~#$HOME#")"
[ -z "$MARKER" ] && MARKER="${FLOW_CONTRIB_DIR:-$HOME/.claude/plugins/data/flow/contributions}/last_harvested.json"
python3 "$S/harvest_lesson.py" prescan --marker-file "$MARKER"   # exit 0 = signal; 1 = none
```

If the pre-scan trips, analyze + enqueue the merge-gate lessons exactly as `/flow:ship`
Step 4c does (noise filter → destination test → source type → `harvest_lesson.py enqueue`),
then advance the watermark. If it doesn't trip, print `[post-merge] no merge-gate feedback
signal — synthesis skipped` and advance the watermark anyway:

```sh
python3 "$S/harvest_lesson.py" mark --marker-file "$MARKER"
```

Emit one honest line either way (never silent): `[post-merge] merge-gate synthesis: M memory
entr(ies), F queued contribution(s)` or the skipped line.

## 5. Stale-branch cleanup (gated on the §2 merge confirmation)

Only after §2 confirmed `merged`: switch off the merged branch and delete it. Use the **safe**
delete (`git branch -d`, which refuses if the branch isn't fully merged) — **never** the force
delete. Remote-delete is graceful: many repos auto-delete the head branch on merge, so it may
already be gone.

```sh
DEFAULT_BRANCH=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@')
[ -z "$DEFAULT_BRANCH" ] && DEFAULT_BRANCH=$(jq -r '.defaultBranch // "main"' flow.config.json 2>/dev/null)
[ -z "$DEFAULT_BRANCH" ] && DEFAULT_BRANCH=main
MERGED_BRANCH=$(git branch --show-current)
WORKTREE_PATH=$(git rev-parse --show-toplevel 2>/dev/null)
CO_ERR=$(mktemp "${TMPDIR:-/tmp}/flow-pm-co.XXXXXX")   # per-run (concurrent runs won't cross-contaminate)
if [ -z "$MERGED_BRANCH" ] || [ "$MERGED_BRANCH" = "$DEFAULT_BRANCH" ]; then
  echo "[post-merge] on $DEFAULT_BRANCH (or detached) — no feature branch to delete here."
  rm -f "$CO_ERR"
else
  git fetch origin --quiet
  # Try to switch OFF the merged branch first. This can fail two common ways — and we must
  # NOT then run `git branch -d` on the still-current branch (git refuses to delete the branch
  # you're on, and would report it as "not merged", the WRONG reason). Capture the result:
  #  - flow's usual setup is a LINKED WORKTREE; the default branch is often checked out in the
  #    primary worktree, so `git checkout <default>` here fails "already checked out at …".
  #  - a dirty tree that would be overwritten also blocks the checkout.
  if git checkout "$DEFAULT_BRANCH" 2>"$CO_ERR"; then
    git pull --ff-only origin "$DEFAULT_BRANCH" 2>/dev/null || true
    # Safe delete — `-d` refuses if the branch isn't fully merged, a last backstop even though
    # §2 confirmed the PR merged. NEVER `-D`.
    if git branch -d "$MERGED_BRANCH" 2>/dev/null; then
      echo "[post-merge] deleted local branch $MERGED_BRANCH."
    else
      echo "⚠️ [post-merge] 'git branch -d $MERGED_BRANCH' refused (not fully merged into $DEFAULT_BRANCH locally)." >&2
      echo "   Left it in place — inspect before deleting. Do NOT force-delete blindly." >&2
    fi
  else
    echo "⚠️ [post-merge] could not switch off $MERGED_BRANCH ($(head -1 "$CO_ERR" 2>/dev/null))." >&2
    echo "   This is usually a linked worktree (the default branch is checked out elsewhere) or a dirty tree." >&2
    echo "   To clean up, from another checkout: 'git worktree remove ${WORKTREE_PATH:-<this-worktree-path>}' then 'git branch -d $MERGED_BRANCH'," >&2
    echo "   or commit/stash the dirty tree and re-run. Skipping local branch delete (never delete the branch you're on)." >&2
  fi
  rm -f "$CO_ERR"
  # Remote delete is independent of the local checkout — attempt it either way (graceful:
  # many repos auto-delete the head branch on merge, so it may already be gone).
  if git ls-remote --exit-code --heads origin "$MERGED_BRANCH" >/dev/null 2>&1; then
    git push origin --delete "$MERGED_BRANCH" 2>/dev/null && echo "[post-merge] deleted remote branch $MERGED_BRANCH." \
      || echo "[post-merge] could not delete remote $MERGED_BRANCH (may lack permission); harmless." >&2
  else
    echo "[post-merge] remote branch $MERGED_BRANCH already gone (auto-deleted on merge?)."
  fi
fi
```

Note this often runs inside a **linked git worktree** — if the default branch is checked out in
the primary worktree, the `git checkout <default>` above fails and the block takes the "could not
switch off" path (which is why §6's verdict must reflect whether the branch was actually deleted,
not assume it).

## 6. Archive-safety verdict — the answer to "safe to archive?"

The verdict is the whole point of the skill, so it must be honest about the **entire** close-out,
not just git state. **Do NOT print a blanket success string** — §3 (`/flow:land`) and §5 (cleanup)
both have non-fatal failure paths that fall through to here (the linked-worktree cleanup case
especially — flow's *usual* setup), so a fixed "✅ … branch cleaned" can directly contradict a
warning printed seconds earlier. Assemble the verdict from THREE inputs you have in hand:

1. **Git-state (deterministic, from the helper)** — any uncommitted / unpushed / stray-untracked
   work archiving would lose. It names each reason and never deletes anything:
   ```sh
   if [ -n "${CLAUDE_PLUGIN_ROOT:-}" ]; then H="${CLAUDE_PLUGIN_ROOT}/skills/post-merge/lib/merge-status.py"; else H="plugins/flow/skills/post-merge/lib/merge-status.py"; fi
   [ -f "$H" ] || { echo "⚠️ BLOCKER: post-merge helper not found at $H — reinstall the flow plugin." >&2; exit 1; }
   python3 "$H" archive-check    # prints `safe` (exit 0) or `not-safe: <reason(s)>` (exit 1)
   ```
2. **Branch cleanup (from §5, which you just ran)** — did §5 actually delete the local branch, or
   leave it (the linked-worktree / dirty-tree path)? A left branch means cleanup is still owed.
3. **The open `docs: land #N` PR (from §3)** — `/flow:land` opens a `docs: land #N` PR the human
   still merges; archiving with it open loses the doc-currency land just produced. Check it, and
   also recall whether `/flow:land` itself errored in §3 (then docs were NOT reconciled):
   ```sh
   gh pr list --search "docs: land #$N in:title" --state open --json number,url 2>/dev/null
   ```

**Assemble:** print `✅ safe to archive` ONLY when ALL hold — git-state `safe`, §5 deleted the
local branch, `/flow:land` succeeded, and its `docs: land` PR is either merged or you name it as
the human's one remaining merge. Otherwise print `🚫 not fully closed out —` and the SPECIFIC
leftover(s): the git-state reason(s); `local branch <name> left in place — see §5's worktree steps`;
`/flow:land failed — run '/flow:land <PR#>'`; and/or `docs: land PR #M still open — your merge`.
**Never claim a step happened that didn't** — the ✅ line is the single most-read output; it must
not lie on the path the design highlights.

## 7. Hand off

Summarize in one block, each line reflecting what ACTUALLY happened this run: the merge
confirmation, the `/flow:land` result (+ its `docs: land #N` PR URL, or a note to run it manually
if it failed), the feedback-synthesis line, the branch-cleanup result (deleted / left-with-reason),
and the assembled archive-safety verdict from §6. If the verdict is 🚫, name exactly what to do to
make it ✅. **Do not merge anything** — `/flow:land`'s docs PR is the human's to merge.

## Gotchas

- **Merge queue = wait, not fail.** The single most important behavior: a queued-but-unlanded
  PR is `open` → poll, never `terminal`. Only a `CLOSED`-unmerged PR fails loud.
- **Composition:** call `/flow:land`; do not reimplement doc reconciliation here (FB-0010 fan-out
  + the compose-not-combine decision). Land stays independently invocable + auto-fireable.
- **`git branch -d`, never `-D`.** The safe delete is a backstop even after the merge check.
- **v1 writes user-scope only.** No `feedbackPath` repo-doc write; content-match dedup makes an
  overlapping window safe without a watermark (both the watermark + repo-doc FB-inbox are v1b).
- **Idempotent.** A re-run after a partial close-out is safe: `/flow:land` no-ops if already
  landed, dedup absorbs re-synthesis, and the branch delete is skipped if already gone.

## Config slots used

| Slot | Default | Used in |
|---|---|---|
| `flow.config.json.postMergeWaitSeconds` | `150` (`0` = fail-fast) | §2 merge-detect poll cap |
| `flow.config.json.defaultBranch` | `git symbolic-ref` → `main` | §5 cleanup target |
| `flow.config.json.contributionsQueuePath` | `~/.claude/plugins/data/flow/contributions` | §4b harvest enqueue |
| `flow.config.json.lastHarvestedPath` | `…/contributions/last_harvested.json` | §4b harvest watermark |
