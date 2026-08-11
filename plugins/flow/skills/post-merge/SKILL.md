---
name: post-merge
description: >
  The "merged — anything left, or safe to archive?" skill (FB-0072). Human-invoked
  AFTER you merge a PR, it runs the whole post-merge close-out in one command:
  (1) confirms the PR is actually merged with a MERGE-QUEUE-SAFE gate (a queued PR
  that hasn't landed yet is "not merged YET", not a failure); (2) reconciles the
  forward docs by calling /flow:land, which opens its own `docs: land #N` PR;
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

**Composition, not combination (from #79; settled by FB-0077).** This skill delegates the
doc-currency step to `/flow:land` rather than reimplementing reconciliation. `/flow:land`
stays a narrow, independently-invocable skill (you can still run it alone after a GitHub-web
merge with no local workspace); `/flow:post-merge` is the orchestrator that does the feedback
+ cleanup + verdict around it. **The delegation is a real `Skill("flow:land")` call** — see §3.

That call took two tries to get right, and the history is the point. #79 specified it, but
`/flow:land` carried `disable-model-invocation: true`, so the call was rejected at runtime and
§3 degraded to its fallback on **every** run. FB-0074 caught that and added
`doctor/lib/skill-composition-lint.py`, which fails on any skill calling a model-disabled
target — the right detector. But it then satisfied its own lint the wrong way, by deleting the
call and rewriting §3 as "hand it to the human." That conceded the composition instead of
fixing it, and reduced this skill to a reminder to run another command. FB-0077 cleared the
flag on `/flow:land` instead: the flag was redundant with `/flow:land`'s own §1a gate (it
refuses any PR that is not already merged, and Claude cannot merge), while this skill's own
`disable-model-invocation: true` keeps a human gate above the whole path. The lint still runs
and still passes — now because the composition is legal, not because the call was removed.

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

## 3. Doc-currency — call `/flow:land` (composition; FB-0077)

Now that the merge is confirmed, the forward docs need reconciling: flipping the item to
"merged (#N)" across roadmap / plan / history, clearing reserved numbers, checking CHANGELOG
currency, and opening a small `docs: land #N` PR. That is exactly `/flow:land`'s job. **Call
it — do not reimplement it here**, and do not degrade it into a note asking the human to run
it themselves. This step is the reason `/flow:post-merge` is an orchestrator.

First, check whether it already ran (idempotent re-run, or the human ran it by hand before
invoking this skill). If an open or merged `docs: land #N` PR exists, treat doc-currency as
satisfied, say so, and skip the call:

```sh
gh pr list --search "docs: land #$N in:title" --state all --json number,state,url 2>/dev/null
```

Otherwise invoke it, **passing the PR number as the skill's argument** — the same thing the
human types as `/flow:land <PR#>`:

```
Skill("flow:land")   # argument: $N from §2 — never invoke this bare
```

The argument is load-bearing. Started without a number, `/flow:land` falls into its own Argument
fallback: it guesses the most recent merged PR and then *stops to confirm with the human* —
putting a prompt back into the orchestration this step exists to remove, and risking a land
against the wrong PR.

`/flow:land` re-verifies the merge itself (§1a) and refuses a dirty tree (§1b) before editing
anything, so a mistaken number or a mid-loop invocation fails loudly there rather than
corrupting the forward docs or disturbing uncommitted work.

**It also leaves you on its own `<prefix>land-N` branch — it never switches back.** That is why
§5 resolves the merged branch from `gh`, not from `git branch --show-current`.

**Handling the result:**

- **Succeeded** — record the `docs: land #N` PR URL. It is still the human's to merge, so §6
  names it as the one remaining action, not a completed step.
- **Errored** — surface the error verbatim, record `doc-currency: NOT reconciled —
  run '/flow:land <PR#>'`, and **continue** to §4 and §5; they are independent of doc
  reconciliation. §6 treats it as a **🚫 not safe to archive** input, because the forward docs
  still point at unmerged work.
- **Rejected at runtime** (the call comes back refused rather than erroring inside the skill) —
  that means `/flow:land`'s `disable-model-invocation` flag has been re-set to `true`,
  reintroducing the exact FB-0074/FB-0077 defect. Say so explicitly rather than quietly falling
  back: name the flag as the cause and carry the outstanding item as in the errored case. That is a
  flow bug, not a repo problem — it should have been caught by CI.

`/flow:land` remains a narrow, independently-invocable skill — the human can still run it
alone after a GitHub-web merge with no local workspace. Calling it here does not consume
that; it just stops this close-out from asking the human to do what it can do itself.

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

**Resolve the target branch from the PR, NOT from `git branch --show-current` (FB-0077).**
§3 now really calls `/flow:land`, and `/flow:land` checks out its own `<prefix>land-N` branch
and does not switch back — so by the time this step runs, `--show-current` returns **land's**
branch, not the merged feature branch. Deleting that would delete the head branch of the
`docs: land #N` PR §3 just opened, which makes GitHub **close that PR**, while the branch
this step exists to clean up survives untouched — and §5 would report success either way.
Take the name from `gh` instead; it is the same value §2 already fetched:

```sh
DEFAULT_BRANCH=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@')
[ -z "$DEFAULT_BRANCH" ] && DEFAULT_BRANCH=$(jq -r '.defaultBranch // "main"' flow.config.json 2>/dev/null)
[ -z "$DEFAULT_BRANCH" ] && DEFAULT_BRANCH=main
# Authoritative: the merged PR's own head ref, NOT `git branch --show-current` (§3 left us
# on land's branch). One `gh` call fetches both fields we need.
#
# SAFETY — bail out on a FORK PR. For a cross-repository PR, `headRefName` is the branch name
# **inside the contributor's fork**, carrying no owner namespace: a PR opened from a fork's
# `develop` reports exactly `develop`. Deleting that name on `origin` would destroy the
# upstream branch of the same name, and GitHub auto-closes any open PR whose head it was. The
# `ls-remote` check further down does not save us — it *confirms* the collision and proceeds.
# Skipping is also just correct: a fork PR's head branch lives on someone else's repo, so
# there is nothing here for this step to clean up.
PRJSON=$(gh pr view "$N" --json headRefName,isCrossRepository 2>/dev/null)
MERGED_BRANCH=$(printf '%s' "$PRJSON" | jq -r '.headRefName // empty' 2>/dev/null)
IS_FORK=$(printf '%s' "$PRJSON" | jq -r '.isCrossRepository // empty' 2>/dev/null)

if [ "$IS_FORK" = "true" ]; then
  echo "[post-merge] PR #$N came from a fork — its head branch ('$MERGED_BRANCH') lives on the"
  echo "   contributor's repo, not origin. Nothing to clean up here; skipping branch deletion."
  MERGED_BRANCH=""
elif [ -z "$MERGED_BRANCH" ]; then
  # gh could not answer. Fall back to the current branch ONLY when it is not land's — after
  # §3 that is the wrong target, and a wrong target here deletes the wrong branch.
  CUR=$(git branch --show-current)
  case "$CUR" in
    *land-"$N")
      echo "⚠️ [post-merge] gh could not resolve PR #$N's head branch, and the current branch" >&2
      echo "   ($CUR) is /flow:land's, not the merged one. Skipping cleanup rather than deleting" >&2
      echo "   the wrong branch — clean up by hand, or re-run once gh is reachable." >&2
      MERGED_BRANCH="" ;;
    *) MERGED_BRANCH="$CUR" ;;
  esac
fi
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
    if git branch -d -- "$MERGED_BRANCH" 2>/dev/null; then
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
  if git ls-remote --exit-code --heads origin -- "$MERGED_BRANCH" >/dev/null 2>&1; then
    git push origin --delete -- "$MERGED_BRANCH" 2>/dev/null && echo "[post-merge] deleted remote branch $MERGED_BRANCH." \
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
3. **Doc-currency (from §3)** — branch on what §3 actually did this run, then confirm it against
   the repo rather than trusting the call's own report:
   ```sh
   gh pr list --search "docs: land #$N in:title" --state all --json number,url,state 2>/dev/null
   ```
   §3 succeeded (or found an existing PR) ⇒ that `docs: land #N` PR is the human's **one
   remaining merge** — name it with its URL. Merged already ⇒ doc-currency is fully satisfied.
   §3 errored or was rejected, and no such PR exists ⇒ docs were **never reconciled** and
   `/flow:land <PR#>` is still owed. A §3 that reported success with no PR to show for it is a
   contradiction — report the contradiction, don't pick the flattering side.

**Assemble:** print `✅ safe to archive` ONLY when ALL hold — git-state `safe`, §5 deleted the
local branch, and the `docs: land #N` PR exists and is merged (or you name it as the human's one
remaining merge). Otherwise print `🚫 not fully closed out —` and the SPECIFIC leftover(s): the
git-state reason(s); `local branch <name> left in place — see §5's worktree steps`;
`doc-currency NOT reconciled — run '/flow:land <PR#>'`; and/or `docs: land PR #M still open —
your merge`.
**Never claim a step happened that didn't** — the ✅ line is the single most-read output; it must
not lie on the path the design highlights.

## 7. Hand off

**Lead with the verdict.** The reader's question at this moment is one question — "am I done?" —
so answer it on the first line, before any detail: `✅ #N closed out — nothing left.` or
`🚫 #N — 1 left: merge docs PR #M <url>`. The 🚫 list names **actions the human must take**, not
steps that ran.

Then the detail block, each line reflecting what ACTUALLY happened this run: the merge
confirmation, the doc-currency result (the `docs: land #N` PR URL when §3 opened or found one;
`run /flow:land <PR#>` as an explicit next action when §3 errored or was rejected — never imply
either happened when it didn't), the feedback-synthesis line, the branch-cleanup result (deleted
/ left-with-reason), and the §6 verdict's reasoning. **Do not merge anything** — `/flow:land`'s
docs PR is the human's to merge.

## Gotchas

- **Merge queue = wait, not fail.** The single most important behavior: a queued-but-unlanded
  PR is `open` → poll, never `terminal`. Only a `CLOSED`-unmerged PR fails loud.
- **Composition is a real `Skill()` call (FB-0077).** Delegate doc reconciliation to
  `/flow:land`; never reimplement it here (FB-0010 fan-out + the compose-not-combine decision),
  and never downgrade it to "ask the human to run it" — that is what made this skill a reminder
  instead of an orchestrator. `/flow:land` is model-invocable *because* its own §1a merged-PR
  gate is the real guard; `doctor/lib/skill-composition-lint.py` keeps the call legal, and
  `run_skill_composition_evals.py` fails if the flag comes back.
- **`git branch -d`, never `-D`.** The safe delete is a backstop even after the merge check.
- **v1 writes user-scope only.** No `feedbackPath` repo-doc write; content-match dedup makes an
  overlapping window safe without a watermark (both the watermark + repo-doc FB-inbox are v1b).
- **Idempotent.** A re-run after a partial close-out is safe: §3 detects an existing `docs: land`
  PR instead of re-asking for one, dedup absorbs re-synthesis, and the branch delete is skipped
  if already gone.

## Config slots used

| Slot | Default | Used in |
|---|---|---|
| `flow.config.json.postMergeWaitSeconds` | `150` (`0` = fail-fast) | §2 merge-detect poll cap |
| `flow.config.json.defaultBranch` | `git symbolic-ref` → `main` | §5 cleanup target |
| `flow.config.json.contributionsQueuePath` | `~/.claude/plugins/data/flow/contributions` | §4b harvest enqueue |
| `flow.config.json.lastHarvestedPath` | `…/contributions/last_harvested.json` | §4b harvest watermark |
