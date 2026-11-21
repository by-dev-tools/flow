---
name: retro
description: >
  The workspace retro (FB-0072): the "merged — anything left, or safe to
  archive?" skill. Run it AFTER PRs merge — one PR, a list of them
  (`/flow:retro 151 153 154`), or with no argument EVERY PR merged into the default
  branch since the last retro. It runs the whole close-out once for the group:
  (1) confirms each PR is actually merged with a MERGE-QUEUE-SAFE gate (a queued PR
  that hasn't landed yet is "not merged YET", not a failure); (2) reconciles the
  forward docs by calling /flow:land ONCE for the whole group, which opens a single
  `docs: land #N …` PR; (3) synthesizes the merge-gate feedback window /flow:ship
  structurally can't see (your review→iterate→merge comments) into user-scope agent
  memory + the /flow:contribute queue; (4) safe-deletes each merged branch (remote
  only when its tip still equals what the PR merged; never a branch checked out in
  another worktree); (5) prints a ✅ safe to archive / 🚫 not safe verdict listing
  every PR. Never merges. Trigger phrases: "retro", "run the retro", "close out
  what merged", "merged — safe to archive?", "workspace retro", "/flow:retro".
  AUTO-INVOCATION: you MAY invoke this yourself when the user asks for a retro or
  close-out in words, or when the user tells you PRs have merged — or you have just
  helped land a batch and the merge is evident in the conversation or from `gh`.
  Pass the PR numbers when the conversation names them; with none, the default is
  "everything merged since the last retro". NEVER invoke it mid-loop to get ahead of
  a merge, at the end of /flow:ship (that PR is OPEN, not merged), or because you
  expect a PR to merge soon: the question is "did a merge already happen", never "is
  one about to". Its §2 gate refuses any PR that is not merged and it never merges
  anything — that gate, not the frontmatter, is the safety.
disable-model-invocation: false
allowed-tools: Read, Edit, Write, Glob, Grep, Bash, Skill
---

You are running the flow **post-merge close-out** for PRs that have already merged (or
that a human just queued to merge). It handles one PR or a **group of them in a single
run**. You **never merge anything**. This is the one command that answers the question
asked after essentially every merge — "merged — anything left to do here, or is it safe to
archive?" — and does the close-out work that question implies.

**Why this exists.** `/flow:ship` synthesizes feedback from the window that *closes
when the PR opens* — but your richest design-taste feedback lands *after*: you review
the PR + walkthrough at the merge gate, comment, the agent iterates, you merge. That
merge-gate window is structurally outside ship's synthesis, and there's no next ship
on the branch to catch it (FB-0072). `/flow:retro` captures it. It also folds in
the doc-currency reconciliation (`/flow:land`), the stale-branch cleanup, and the
archive-safety check you'd otherwise do by hand.

**Why it takes a group.** A batch of merged PRs is one event, not N. Run once per PR, the
close-out costs a prompt and a `docs: land` PR per merge, and those PRs all edit the same
roadmap/plan lines. So the steps split by what they actually are: **shared work runs once
per group** (the doc-currency PR, the feedback synthesis, the verdict) and **per-PR work runs
per PR** (the merge check and the branch cleanup).

**Composition, not combination (from #79; settled by FB-0077).** This skill delegates the
doc-currency step to `/flow:land` rather than reimplementing reconciliation. `/flow:land`
stays a narrow, independently-invocable skill (you can still run it alone after a GitHub-web
merge with no local workspace); `/flow:retro` is the orchestrator that does the feedback
+ cleanup + verdict around it. **The delegation is a real `Skill("flow:land")` call** — see §3.

That call took two tries to get right, and the history is the point. #79 specified it, but
`/flow:land` carried `disable-model-invocation: true`, so the call was rejected at runtime and
§3 degraded to its fallback on **every** run. FB-0074 caught that and added
`doctor/lib/skill-composition-lint.py`, which fails on any skill calling a model-disabled
target — the right detector. But it then satisfied its own lint the wrong way, by deleting the
call and rewriting §3 as "hand it to the human." That conceded the composition instead of
fixing it, and reduced this skill to a reminder to run another command. FB-0077 cleared the
flag on `/flow:land` instead: the flag was redundant with `/flow:land`'s own §1a gate (it
refuses any PR that is not already merged, and Claude cannot merge). The lint still runs
and still passes — now because the composition is legal, not because the call was removed.

**Why this skill is model-invocable too (v1.69.0).** FB-0077 kept `disable-model-invocation:
true` here as "the human gate above `/flow:land`". In practice it only blocked the person it
was meant to serve: a user who said "run the retro" in chat got a refused `Skill("flow:retro")`
and had to type the slash command themselves, once per PR. The flag was never the guard.
The guard is the same one that made `/flow:land`'s flag redundant — **§2 refuses every PR
that is not merged, `/flow:land` §1a re-checks it, and nothing here can merge.** What a
mistaken invocation can reach is a `docs: land` PR, memory entries, and the deletion of branches
that §5 has proven are what the PR merged. All of it is reversible, none of it ships code. The
risk the flag was standing in for — firing mid-loop, before a merge — is a *when* question the
frontmatter could not answer anyway, so the AUTO-INVOCATION clause above states it in prose
and `run_skill_composition_evals.py` pins that clause alongside the flag.

## Project context (resolved at invocation)

- Project config: !`cat flow.config.json 2>/dev/null || echo "(no flow.config.json — using built-in defaults)"`
- Default branch: !`git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@' || cat flow.config.json 2>/dev/null | jq -r '.defaultBranch // "main"' 2>/dev/null || echo "main"`
- Current branch: !`git branch --show-current`
- Post-merge wait cap: !`cat flow.config.json 2>/dev/null | jq -r '.postMergeWaitSeconds // 150' 2>/dev/null || echo 150`

## Argument

`/flow:retro [<PR#> …]` — zero or more PR numbers (`151` or `#151`; space- or
comma-separated — a PR URL is refused, since it could name another repo).

- **One or more numbers** — exactly that group. Use this when the conversation names the PRs.
- **None** — **do not ask.** The group is every PR merged into the default branch since the
  last retro (§1b: a per-repo watermark; the first run in a repo looks back 7 days, capped at
  20 PRs). A bare `/flow:retro` after a batch of merges is the whole point of this skill — a
  confirmation prompt here is the per-PR chore it exists to remove. §1b prints the resolved
  group before anything runs, so a wrong set is visible, and every step after it is
  idempotent and non-destructive.

If a number can't be parsed, stop and say which token; never guess.

## 1. Pre-flight — external CLI check (BLOCKING)

Per FB-0009, fail fast at the entrypoint with a clean hint rather than a mid-run `exit 127`.

```sh
MISSING=""
command -v gh >/dev/null 2>&1 || MISSING="$MISSING gh"
command -v jq >/dev/null 2>&1 || MISSING="$MISSING jq"
command -v git >/dev/null 2>&1 || MISSING="$MISSING git"
if [ -n "$MISSING" ]; then
  MISSING_TRIMMED=$(echo "$MISSING" | sed 's/^ //')
  echo "⚠️ BLOCKER: /flow:retro requires $MISSING_TRIMMED (missing on PATH)." >&2
  echo "   Install: macOS 'brew install$MISSING' · Debian/Ubuntu 'apt install$MISSING' · gh: https://cli.github.com" >&2
  case " $MISSING_TRIMMED " in *" gh "*) echo "   After install: gh auth login" >&2 ;; esac
  exit 1
fi
```

**Shell note for every block below.** Bash blocks do not share variables, so each one
re-declares its inputs as literals (`NUMS=`). Iteration is `while read` over a newline list, never
`for N in $LIST`: zsh does not word-split an unquoted variable, so that form silently runs
once with the whole list as one "number".

## 1b. Resolve the group

An explicit argument is normalized by the helper (which refuses anything that is not a PR
number); an empty one selects the default group from the per-repo watermark. Write the argument
as bare digits — the helper exists so that a stray token fails here, not inside `gh`.

```sh
if [ -n "${CLAUDE_PLUGIN_ROOT:-}" ]; then H="${CLAUDE_PLUGIN_ROOT}/skills/retro/lib/merge-status.py"; else H="plugins/flow/skills/retro/lib/merge-status.py"; fi
[ -f "$H" ] || { echo "⚠️ BLOCKER: retro helper not found at $H — reinstall the flow plugin." >&2; exit 1; }
ARGS=''    # the PR numbers typed or passed, bare digits, e.g. ARGS="151 153 154"; leave EMPTY when none were given
DEFAULT_BRANCH=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@')
[ -z "$DEFAULT_BRANCH" ] && DEFAULT_BRANCH=$(jq -r '.defaultBranch // "main"' flow.config.json 2>/dev/null)
[ -z "$DEFAULT_BRANCH" ] && DEFAULT_BRANCH=main
if [ -n "$ARGS" ]; then
  NUMS=$(python3 "$H" parse-prs "$ARGS") || { echo "🚫 BLOCKER: could not read '$ARGS' as PR numbers — nothing was changed." >&2; exit 1; }
  echo "[retro] group (explicit): $(printf '%s' "$NUMS" | tr '\n' ' ')"
else
  REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner 2>/dev/null)
  [ -n "$REPO" ] || { echo "🚫 BLOCKER: gh could not resolve this repo, so there is no way to find 'merged since the last retro'. Pass PR numbers, or fix 'gh auth status'." >&2; exit 1; }
  # The watermark sits beside the harvest marker (same user-scope directory, same slot — no new config).
  QUEUE_ROOT="$(jq -r '.contributionsQueuePath // empty' flow.config.json 2>/dev/null | sed "s#^~#$HOME#")"
  [ -n "$QUEUE_ROOT" ] && export FLOW_CONTRIB_DIR="$QUEUE_ROOT"
  MARKER="$(jq -r '.lastHarvestedPath // empty' flow.config.json 2>/dev/null | sed "s#^~#$HOME#")"
  [ -z "$MARKER" ] && MARKER="${FLOW_CONTRIB_DIR:-$HOME/.claude/plugins/data/flow/contributions}/last_harvested.json"
  WM="$(dirname "$MARKER")/last_retro.json"
  LISTJSON=$(gh pr list --state merged --base "$DEFAULT_BRANCH" --limit 100 --json number,title,mergedAt,headRefName,isCrossRepository 2>/dev/null)
  # `gh pr list` orders by CREATION, so a long-lived PR merged recently can sit outside a full
  # page. Say so rather than let the watermark advance silently past it.
  [ "$(printf '%s' "$LISTJSON" | jq 'length' 2>/dev/null)" = "100" ] && echo "⚠️ [retro] 100 merged PRs came back (the page limit) — an older-created PR merged recently may be missing from the default group. Pass its number explicitly if so." >&2
  [ -n "$LISTJSON" ] || { echo "🚫 BLOCKER: 'gh pr list' returned nothing (auth/network?) — cannot tell what merged. Nothing was changed." >&2; exit 1; }
  NUMS=$(printf '%s' "$LISTJSON" | python3 "$H" select --watermark-file "$WM" --repo "$REPO") || { echo "🚫 BLOCKER: could not select the default group." >&2; exit 1; }
  if [ -z "$NUMS" ]; then
    echo "[retro] nothing has merged into $DEFAULT_BRANCH since the last retro — nothing to close out."
    exit 0
  fi
  echo "[retro] group (everything merged since the last retro): $(printf '%s' "$NUMS" | tr '\n' ' ')"
fi
```

Carry the printed list forward as `NUMS` — it is the group for every later step — and carry
whether it was **explicit** or **default**: only a default run moves the watermark (§6b).

## 2. Merge-detect — the MERGE-QUEUE-SAFE gate (BLOCKING on terminal, patient on transient)

The load-bearing gate, per PR. It is **three-state**, not two — reserving fail-loud for a PR
that will *never* merge, and treating a still-`OPEN` PR as *not merged yet* (poll), so a merge
queue's 1–2 min delay never produces a false failure (FB-0072). The classification + poll
policy live in the deterministic helper; the loop's I/O (fetch + sleep) is here.

For a group the poll is **shared**: each round classifies every still-pending PR, merged ones
drop out, and the one `postMergeWaitSeconds` cap bounds the whole wait — N queued PRs do not
cost N × the cap. A closed-unmerged or still-queued PR does **not** abort the group: it is
named, left out of every later step, and reported in the verdict. Only if *nothing* in the group
merged does the run stop.

```sh
if [ -n "${CLAUDE_PLUGIN_ROOT:-}" ]; then H="${CLAUDE_PLUGIN_ROOT}/skills/retro/lib/merge-status.py"; else H="plugins/flow/skills/retro/lib/merge-status.py"; fi
[ -f "$H" ] || { echo "⚠️ BLOCKER: retro helper not found at $H — reinstall the flow plugin." >&2; exit 1; }
NUMS='<the group from §1b, space-separated>'
CAP=$(jq -r '.postMergeWaitSeconds // 150' flow.config.json 2>/dev/null); [ -z "$CAP" ] && CAP=150
INTERVAL=20                                 # seconds between polls
ELAPSED=0
MERGED=""; CLOSED=""
PENDING=$(printf '%s' "$NUMS" | tr -s ' ,\n' '\n')
while : ; do
  STILL=""
  while read -r N; do
    [ -n "$N" ] || continue
    BLOB=$(gh pr view "$N" --json state,mergedAt,autoMergeRequest 2>/dev/null)
    STATE=$(printf '%s' "$BLOB" | python3 "$H" classify)   # merged | closed | open
    case "$STATE" in
      merged) MERGED="$MERGED $N"; echo "[retro] PR #$N is merged." ;;
      closed) CLOSED="$CLOSED $N"; echo "🚫 [retro] PR #$N is CLOSED without merging — left out of this close-out." >&2 ;;
      open)   STILL="$STILL $N" ;;
      *)
        # classify always prints one of the three words above, so this only fires if the helper
        # itself is broken (a bad edit / wrong Python). A FAILED `gh pr view` (unauthed/network)
        # yields an empty blob → classify 'open' → polled, absorbed as "not merged yet" (the
        # queue-safety default) — NOT this branch. Fail loud, don't guess.
        echo "🚫 BLOCKER: unexpected classification from the merge-status helper ('${STATE}') for #$N — the helper may be broken. Nothing was changed." >&2
        exit 1 ;;
    esac
  done <<EOF
$PENDING
EOF
  PENDING=$(printf '%s' "$STILL" | tr -s ' ' '\n')
  [ -n "$(printf '%s' "$PENDING" | tr -d '[:space:]')" ] || break
  VERDICT=$(python3 "$H" poll-verdict --state open --elapsed "$ELAPSED" --cap "$CAP")
  case "$VERDICT" in
    wait)
      echo "[retro] still open (queued/auto-merge?): $(printf '%s' "$PENDING" | tr '\n' ' ')— polling up to ${CAP}s; re-checking in ${INTERVAL}s…"
      sleep "$INTERVAL" ; ELAPSED=$((ELAPSED + INTERVAL)) ;;
    giveup-graceful) break ;;
    *) echo "🚫 BLOCKER: unexpected verdict from the merge-status helper ('${VERDICT}') — the helper may be broken. Nothing was changed." >&2; exit 1 ;;
  esac
done
STILL_OPEN=$(printf '%s' "$PENDING" | tr '\n' ' ')
echo "[retro] merged:${MERGED:- (none)}   closed-unmerged:${CLOSED:- (none)}   still open: ${STILL_OPEN:-(none)}"
if [ -z "$MERGED" ]; then
  if [ -n "$CLOSED" ]; then
    echo "🚫 BLOCKER: nothing in the group merged, and${CLOSED} closed without merging — nothing to close out." >&2
    echo "   (If you meant to merge, reopen + re-merge, then re-run '/flow:retro'.)" >&2
    exit 1
  fi
  echo "🕒 Still open after ${ELAPSED}s: ${STILL_OPEN}. If a merge queue is holding them they may just need more time —" >&2
  echo "   re-run '/flow:retro' once they land. (Nothing was changed; this is not a failure.)" >&2
  exit 0                                    # graceful, distinct from the terminal exit 1
fi
```

Carry **`MERGED`** forward as the working group for §3–§6. `CLOSED` and `STILL_OPEN` are not
close-out inputs; they go straight to the §6 verdict as PRs that are **not** closed out. A group
of one PR behaves exactly as the single-PR skill always did: closed → BLOCKER, still-open →
graceful exit.

`autoMergeRequest` in the fetched blob is a *confidence* signal that a merge is intended —
you can trust the poll on a queue repo. A non-queue repo merges instantly, so `classify`
returns `merged` on the first pass and the loop never sleeps. `postMergeWaitSeconds: 0`
makes an OPEN PR give up immediately (fail-fast) instead of polling.

## 3. Doc-currency — call `/flow:land` ONCE for the group (composition; FB-0077)

Now that the merges are confirmed, the forward docs need reconciling: flipping each item to
"merged (#N)" across roadmap / plan / history, checking CHANGELOG currency, and opening a small
`docs: land …` PR. That is exactly `/flow:land`'s job, and it takes the **whole list in one call**,
producing **one** PR for the group. **Call it — do not reimplement it here**, do not call it once
per PR, and do not degrade it into a note asking the human to run it themselves. This step is
the reason `/flow:retro` is an orchestrator.

First, find which PRs already have a landing PR (idempotent re-run, or the human ran `/flow:land`
by hand). Match on the **title naming that number** — a group's PR names all of them — and only
land the rest. A *closed-unmerged* landing PR does not count (an abandoned docs PR must not
satisfy doc-currency forever); an open or merged one does:

```sh
NUMS='<MERGED from §2, space-separated>'
TODO=""
if [ -n "${CLAUDE_PLUGIN_ROOT:-}" ]; then H="${CLAUDE_PLUGIN_ROOT}/skills/retro/lib/merge-status.py"; else H="plugins/flow/skills/retro/lib/merge-status.py"; fi
[ -f "$H" ] || { echo "⚠️ BLOCKER: retro helper not found at $H — reinstall the flow plugin." >&2; exit 1; }
DEFAULT_BRANCH=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@'); [ -z "$DEFAULT_BRANCH" ] && DEFAULT_BRANCH=$(jq -r '.defaultBranch // "main"' flow.config.json 2>/dev/null); [ -z "$DEFAULT_BRANCH" ] && DEFAULT_BRANCH=main
# `landing-prs` owns the definition of "a PR /flow:land could have opened": same repo (not a fork), based
# on the default branch, on a `land-<N>` head, titled `docs: land #…`, not closed. A title alone is writable
# by anyone who can open a PR — naming #151 in one would otherwise mark #151 "already landed", skip the real
# reconciliation, and advance the watermark past it. Its output is PROJECTED (`#N STATE url covers: #a #b`):
# titles are written by whoever opened the PR and are never printed into this run.
LANDING=$(gh pr list --search "docs: land in:title" --state all --limit 100 --json number,state,url,title,headRefName,baseRefName,isCrossRepository 2>/dev/null | python3 "$H" landing-prs --default-branch "$DEFAULT_BRANCH")
while read -r N; do
  [ -n "$N" ] || continue
  HIT=$(printf '%s\n' "$LANDING" | grep -E "covers:.*#${N}( |$)" | head -1 | cut -d' ' -f3)
  if [ -n "$HIT" ]; then echo "[retro] #$N already has a landing PR: $HIT — doc-currency satisfied."; else TODO="$TODO $N"; fi
done <<EOF
$(printf '%s' "$NUMS" | tr -s ' ,\n' '\n')
EOF
echo "[retro] to land:${TODO:- (none)}"
```

If `TODO` is empty, skip the call. Otherwise invoke it **once, passing every number in `TODO` as
the skill's argument** — the same thing the human types as `/flow:land <PR#> <PR#> …`:

```
Skill("flow:land")   # argument: the TODO numbers from above, space-separated — never invoke this bare
```

The argument is load-bearing. Started without a number, `/flow:land` falls into its own Argument
fallback: it guesses the most recent merged PR and then *stops to confirm with the human* —
putting a prompt back into the orchestration this step exists to remove, and risking a land
against the wrong PR.

`/flow:land` re-verifies **every** merge itself (§1a) and refuses a dirty tree (§1b) before editing
anything, so a mistaken number or a mid-loop invocation fails loudly there rather than
corrupting the forward docs or disturbing uncommitted work.

**It also leaves you on its own `<prefix>land-…` branch — it never switches back.** That is why
§5 resolves each merged branch from `gh`, not from `git branch --show-current`.

**Handling the result:**

- **Succeeded** — record the `docs: land …` PR URL. It is still the human's to merge, so §6
  names it as the one remaining action, not a completed step.
- **Errored** — surface the error verbatim, record `doc-currency: NOT reconciled —
  run '/flow:land <the TODO numbers>'`, and **continue** to §4 and §5; they are independent of
  doc reconciliation. §6 treats it as a **🚫 not safe to archive** input, because the forward docs
  still point at unmerged work.
- **Rejected at runtime** (the call comes back refused rather than erroring inside the skill) —
  that means `/flow:land`'s `disable-model-invocation` flag has been re-set to `true`,
  reintroducing the exact FB-0074/FB-0077 defect. Say so explicitly rather than quietly falling
  back: name the flag as the cause and carry the outstanding items as in the errored case. That is
  a flow bug, not a repo problem — it should have been caught by CI.

`/flow:land` remains a narrow, independently-invocable skill — the human can still run it
alone after a GitHub-web merge with no local workspace. Calling it here does not consume
that; it just stops this close-out from asking the human to do what it can do itself.

## 4. Merge-gate feedback synthesis (the delta window) — ONCE, USER-SCOPE STORES ONLY (v1)

Capture the feedback from the window ship couldn't see — your merge-gate review → iterate
→ merge comments on **this group's branches** since the last ship. It runs **once for the
whole group**, not per PR: the window is the session's transcript, which does not divide by PR,
and synthesizing it N times would only re-find the same lessons N times. **v1 writes only
user-scope stores** (agent memory + the `/flow:contribute` queue), reusing the exact machinery
`/flow:ship` Step 4b/4c already uses. It does **NOT** write the repo `feedbackPath` doc
(`dev-docs/feedback/`) — that would mean committing an `FB-XXXX` to a just-merged branch;
deferred to v1b (the transcript-timestamp watermark + an FB-inbox). **Content-match dedup** makes
an overlapping window safe: a lesson ship already captured re-matches its existing entry and
appends a fire-log date instead of duplicating (no watermark needed for v1).

Scope note (honest v1 limitation): this synthesizes best-effort from the **current session**
since the last ship on this branch. Robust multi-session / Conductor-worktree window
resolution is deferred to v1b. A group merged in a session that did not witness the review
conversations (an orchestrator closing out PRs its workers shipped) will usually pre-scan to
"no signal" — that is the honest answer, not an error.

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
then advance the watermark. If it doesn't trip, print `[retro] no merge-gate feedback
signal — synthesis skipped` and advance the watermark anyway:

```sh
python3 "$S/harvest_lesson.py" mark --marker-file "$MARKER"
```

(That watermark is the **transcript** window — a different thing from the §1b/§6b PR watermark,
which lives in a sibling file. The two never share a key.)

Emit one honest line either way (never silent): `[retro] merge-gate synthesis: M memory
entr(ies), F queued contribution(s)` or the skipped line.

## 5. Stale-branch cleanup — per PR (gated on the §2 merge confirmation)

For each PR in `MERGED`, decide with the helper and then act on its verdict. The helper
**decides and never deletes**; this block executes only what it approved. Use the **safe** delete
(`git branch -d`, which refuses if the branch isn't fully merged) — **never** the force delete.

Three facts shape this step, each learned from a real batch:

- **A squash-merged branch always makes `git branch -d` refuse.** The merged content is on the
  default branch under a *different* commit, so git cannot see the branch as merged — in a batch
  of squash-merges, `-d` refuses *every* local branch. That refusal is **not** evidence of
  unmerged work (§2 already proved the PR merged), and it is not licence to force-delete.
  Report each such branch as **left behind**, with whether its tip equals what the PR merged, and
  let the human delete it. Never `-D`.
- **The remote head may only be deleted if it is still what the PR merged.** The helper compares
  the remote tip to the PR's `headRefOid` from `gh pr view`. Equal → delete. Different → someone
  pushed after the merge; those commits were never reviewed, so the branch stays (`moved`).
  A fork PR's head ref names a branch on the contributor's repo — deleting the same name on `origin`
  would destroy an unrelated upstream branch — so a fork is never deleted from here.
- **A branch checked out in another worktree is somebody's live workspace.** `worktree:<path>`
  verdicts are skipped and *named*, never touched. In a batch this is the common case: the
  orchestrator's own worktrees are exactly where the merged branches are still checked out.

**Resolve each branch from the PR, NOT from `git branch --show-current` (FB-0077).** §3 really
calls `/flow:land`, which checks out its own `<prefix>land-…` branch and does not switch back —
so by now `--show-current` returns **land's** branch. Deleting that would delete the head branch
of the `docs: land` PR §3 just opened, which makes GitHub **close that PR**. The helper takes the
name from `gh`'s `headRefName`.

A merged PR's branch can also be the **base of another open PR** (a stacked PR whose parent just
landed — see workflow.md § "Stacked PRs"). Deleting the head would retarget or close the child, so
the block leaves it and names the dependent.

```sh
if [ -n "${CLAUDE_PLUGIN_ROOT:-}" ]; then H="${CLAUDE_PLUGIN_ROOT}/skills/retro/lib/merge-status.py"; else H="plugins/flow/skills/retro/lib/merge-status.py"; fi
[ -f "$H" ] || { echo "⚠️ BLOCKER: retro helper not found at $H — reinstall the flow plugin." >&2; exit 1; }
NUMS='<MERGED from §2, space-separated>'
DEFAULT_BRANCH=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@')
[ -z "$DEFAULT_BRANCH" ] && DEFAULT_BRANCH=$(jq -r '.defaultBranch // "main"' flow.config.json 2>/dev/null)
[ -z "$DEFAULT_BRANCH" ] && DEFAULT_BRANCH=main
# `gh` resolves a PR number in ITS repo; the delete below goes to `origin`. In a fork/upstream layout
# those can differ, so only delete when origin is the repo gh resolved (exact owner/name, case-insensitive).
GH_REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner 2>/dev/null)
ORIGIN_URL=$(git remote get-url origin 2>/dev/null)
REPO_MATCH=no
# Exact owner/name from the origin URL (ssh or https), NOT a substring: `me/repo` must not match `me/repo-fork`.
ORIGIN_SLUG=$(printf '%s' "$ORIGIN_URL" | sed -E 's#^.*[:/]([^/:]+/[^/]+)$#\1#; s#\.git$##' | tr 'A-Z' 'a-z')
[ -n "$GH_REPO" ] && [ "$ORIGIN_SLUG" = "$(printf '%s' "$GH_REPO" | tr 'A-Z' 'a-z')" ] && REPO_MATCH=yes
git fetch origin --quiet 2>/dev/null || echo "⚠️ [retro] 'git fetch origin' failed — remote tips below may be stale; deletes are verified against the live remote anyway." >&2
while read -r N; do
  [ -n "$N" ] || continue
  BLOB=$(gh pr view "$N" --json headRefName,headRefOid,isCrossRepository 2>/dev/null)
  if [ -z "$BLOB" ]; then
    echo "⚠️ [retro] #$N: gh could not read the PR — branch cleanup skipped for it (re-run once gh is reachable)." >&2
    continue
  fi
  PLAN=$(printf '%s' "$BLOB" | python3 "$H" branch-plan --default-branch "$DEFAULT_BRANCH")
  BR=$(printf '%s' "$BLOB" | jq -r '.headRefName // empty')
  RPLAN=$(printf '%s' "$PLAN" | jq -r '.remote')
  LPLAN=$(printf '%s' "$PLAN" | jq -r '.local')
  TIPOK=$(printf '%s' "$PLAN" | jq -r '.tip_matches')
  DETAIL=$(printf '%s' "$PLAN" | jq -r '.detail')

  # A merged parent's branch can be the base of an open child PR — leave it, name the child.
  if [ -n "$BR" ]; then
    # Fail CLOSED: a gh error (rate limit, network) must not read as "no dependents" — that is the
    # exact case this guard exists for, and it would delete the base out from under a stacked child.
    if ! DEPS=$(gh pr list --state open --base "$BR" --json number --jq '[.[].number] | map("#" + tostring) | join(" ")' 2>/dev/null); then
      echo "⚠️ [retro] #$N: could not check whether open PRs are based on '$BR' (gh failed) — branch left in place." >&2
      continue
    fi
    if [ -n "$DEPS" ]; then
      echo "⚠️ [retro] #$N: '$BR' is the base of open PR(s) $DEPS — branch left in place so they are not retargeted/closed under you." >&2
      continue
    fi
  fi

  case "$RPLAN" in
    delete)
      # Second line of defence behind the helper's long-lived-name list: ask GitHub. Fail CLOSED — an
      # unanswered question is not "unprotected".
      PROT=$(gh api "repos/{owner}/{repo}/branches/$BR" --jq '.protected' 2>/dev/null)
      OID=$(printf '%s' "$BLOB" | jq -r '.headRefOid // empty')
      if [ "$PROT" != "false" ]; then
        echo "⚠️ [retro] #$N: remote $BR left in place — GitHub did not confirm it is unprotected (protected=${PROT:-unknown})." >&2
      elif [ "$REPO_MATCH" != "yes" ]; then
        echo "⚠️ [retro] #$N: remote $BR left in place — 'origin' does not match the repo gh resolved PR #$N in." >&2
      else
        # Fully-qualified ref + a lease on the exact tip the PR merged: a push that landed between
        # the check and now makes this fail instead of discarding commits nobody reviewed.
        git push origin --force-with-lease="refs/heads/$BR:$OID" ":refs/heads/$BR" 2>/dev/null \
          && echo "[retro] #$N: deleted remote branch $BR (was ${OID%${OID#???????}}; restorable from that SHA)." \
          || echo "[retro] #$N: could not delete remote $BR (moved, protected, or no permission); left in place." >&2
      fi ;;
    gone)         echo "[retro] #$N: remote branch $BR already gone (auto-deleted on merge?)." ;;
    moved)        echo "⚠️ [retro] #$N: remote $BR left in place — $DETAIL (pushed after the merge)." >&2 ;;
    skip-fork)    echo "[retro] #$N: fork PR — its head branch lives on the contributor's repo; nothing to clean up on origin." ;;
    skip-default) echo "[retro] #$N: head is the default branch — nothing to delete." ;;
    skip-long-lived) echo "[retro] #$N: head '$BR' looks like a long-lived branch (release/develop/…) — never deleted from here." ;;
    *)            echo "⚠️ [retro] #$N: remote branch left in place (${RPLAN}${DETAIL:+: $DETAIL})." >&2 ;;
  esac

  case "$LPLAN" in
    delete|current)
      if [ "$LPLAN" = "current" ]; then
        # Checked out in THIS worktree: try to step off first. In a linked worktree the default
        # branch is usually checked out in the primary one, so this can fail — then it is left.
        if ! git checkout "$DEFAULT_BRANCH" >/dev/null 2>&1; then
          echo "⚠️ [retro] #$N: local $BR is checked out here and '$DEFAULT_BRANCH' is not available to switch to (another worktree, or a dirty tree) — left in place." >&2
          continue
        fi
      fi
      # Safe delete only. `-d` refuses a squash-merged branch even though §2 proved the PR merged.
      if git branch -d -- "$BR" >/dev/null 2>&1; then
        echo "[retro] #$N: deleted local branch $BR."
      else
        echo "⚠️ [retro] #$N: local $BR LEFT BEHIND — 'git branch -d' refuses (a squash/rebase merge isn't visible to git as merged). Local tip equals the merged head: ${TIPOK}. Delete it by hand once you've checked it; this skill never force-deletes." >&2
      fi ;;
    absent)      echo "[retro] #$N: no local branch $BR." ;;
    worktree:*)  echo "⚠️ [retro] #$N: local $BR is checked out in another worktree (${LPLAN#worktree:}) — skipped. Archive or remove that worktree, then delete the branch." >&2 ;;
    skip-*)      : ;;
    *)           echo "⚠️ [retro] #$N: local branch left in place (${LPLAN}${DETAIL:+: $DETAIL})." >&2 ;;
  esac
done <<EOF
$(printf '%s' "$NUMS" | tr -s ' ,\n' '\n')
EOF
```

Note this often runs inside a **linked git worktree** — if the default branch is checked out in
the primary worktree, a `current` verdict cannot be acted on and takes the "left in place" path
(which is why §6's verdict must reflect what was actually deleted, not assume it).

## 6. Archive-safety verdict — the answer to "safe to archive?"

The verdict is the whole point of the skill, so it must be honest about the **entire** close-out,
not just git state, and it covers **every PR in the group** — including the ones §2 left out.
**Do NOT print a blanket success string** — §3 (`/flow:land`) and §5 (cleanup) both have
non-fatal failure paths that fall through to here (squash-merged branches that `-d` refuses
especially — in a batch that is *most* of them), so a fixed "✅ … branches cleaned" can directly
contradict a warning printed seconds earlier. Assemble the verdict from FOUR inputs you have in hand:

1. **Git-state (deterministic, from the helper)** — any uncommitted / unpushed / stray-untracked
   work archiving *this worktree* would lose. It names each reason and never deletes anything:
   ```sh
   if [ -n "${CLAUDE_PLUGIN_ROOT:-}" ]; then H="${CLAUDE_PLUGIN_ROOT}/skills/retro/lib/merge-status.py"; else H="plugins/flow/skills/retro/lib/merge-status.py"; fi
   [ -f "$H" ] || { echo "⚠️ BLOCKER: retro helper not found at $H — reinstall the flow plugin." >&2; exit 1; }
   python3 "$H" archive-check    # prints `safe` (exit 0) or `not-safe: <reason(s)>` (exit 1)
   ```
2. **Branch cleanup (from §5, which you just ran)** — per PR, did §5 delete the local and remote
   branches, or leave them (squash-merge refusal, another worktree, moved remote, open dependent)?
   A left branch means cleanup is still owed, and *which* branch and *why* is the actionable part.
3. **Doc-currency (from §3)** — branch on what §3 actually did this run, then confirm it against
   the repo rather than trusting the call's own report:
   ```sh
   if [ -n "${CLAUDE_PLUGIN_ROOT:-}" ]; then H="${CLAUDE_PLUGIN_ROOT}/skills/retro/lib/merge-status.py"; else H="plugins/flow/skills/retro/lib/merge-status.py"; fi
   DEFAULT_BRANCH=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@'); [ -z "$DEFAULT_BRANCH" ] && DEFAULT_BRANCH=main
   gh pr list --search "docs: land in:title" --state all --json number,url,state,title,headRefName,baseRefName,isCrossRepository 2>/dev/null \
     | python3 "$H" landing-prs --default-branch "$DEFAULT_BRANCH"
   ```
   Same helper subcommand as §3 (one definition of "landing PR"), and its output is **projected**: PR
   titles are written by whoever opened the PR, so they are never printed raw into this run — only the
   numbers they name. (A closed landing PR is not listed: it does not count as doc-currency.)
   For each merged PR: a landing PR whose title names it exists ⇒ that PR is the human's **one
   remaining merge** — name it with its URL (a group usually has exactly one). Merged already ⇒
   doc-currency is fully satisfied for it. §3 errored or was rejected, and no such PR names it ⇒
   docs were **never reconciled** for it and `/flow:land <PR#>` is still owed. A §3 that reported
   success with no PR to show for it is a contradiction — report the contradiction, don't pick the
   flattering side.
4. **PRs not closed out (from §2)** — each `CLOSED` or still-open PR is a `🚫` item by itself: it
   was left out of every step above. Likewise, if §1b's selection said `N more merged PR(s) beyond the
   cap`, the group is not complete: that is a `🚫` item (`N more merged PRs waiting — re-run`), never a ✅.

**Assemble:** print `✅ safe to archive` ONLY when ALL hold — git-state `safe`; §5 left no local
branch behind for a PR in `MERGED`; every merged PR has a landing PR that is merged (or that you
name as the human's one remaining merge); and §2 left nothing out. Otherwise print
`🚫 not fully closed out —` and the SPECIFIC leftover(s), each naming its PR: the git-state
reason(s); `local branch <name> (#N) left in place — <why>`; `doc-currency NOT reconciled for #N —
run '/flow:land N'`; `docs: land PR #M still open — your merge`; `#N still open / closed unmerged`.
**Never claim a step happened that didn't** — the ✅ line is the single most-read output; it must
not lie on the path the design highlights.

### 6b. Advance the retro watermark (default-group runs only)

Move the per-repo watermark past this group so the next bare `/flow:retro` starts after it —
**only** when this run's group was the **default** one (not an explicit list) **and** every PR in
`MERGED` is doc-currency-satisfied **and** §2 left nothing out **and** §1b did not warn that the page of merged PRs was full (a full page can omit an older-created PR, and advancing would drop it for good). Advancing past a PR whose docs were
never reconciled would drop it from the next default group; not advancing costs only a harmless,
idempotent re-pick. An explicit-list run never moves it: a hand-picked subset says nothing about
the PRs it skipped. Skip this block otherwise.

```sh
if [ -n "${CLAUDE_PLUGIN_ROOT:-}" ]; then H="${CLAUDE_PLUGIN_ROOT}/skills/retro/lib/merge-status.py"; else H="plugins/flow/skills/retro/lib/merge-status.py"; fi
NUMS='<MERGED from §2, space-separated>'
REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner 2>/dev/null)
QUEUE_ROOT="$(jq -r '.contributionsQueuePath // empty' flow.config.json 2>/dev/null | sed "s#^~#$HOME#")"
[ -n "$QUEUE_ROOT" ] && export FLOW_CONTRIB_DIR="$QUEUE_ROOT"
MARKER="$(jq -r '.lastHarvestedPath // empty' flow.config.json 2>/dev/null | sed "s#^~#$HOME#")"
[ -z "$MARKER" ] && MARKER="${FLOW_CONTRIB_DIR:-$HOME/.claude/plugins/data/flow/contributions}/last_harvested.json"
WM="$(dirname "$MARKER")/last_retro.json"
CLOSED_JSON=$(while read -r N; do [ -n "$N" ] && gh pr view "$N" --json number,mergedAt 2>/dev/null; done <<EOF
$(printf '%s' "$NUMS" | tr -s ' ,\n' '\n')
EOF
)
[ -n "$REPO" ] && printf '%s' "$CLOSED_JSON" | jq -s '.' | python3 "$H" advance --watermark-file "$WM" --repo "$REPO"
```

## 7. Hand off

**Lead with the verdict.** The reader's question at this moment is one question — "am I done?" —
so answer it on the first line, before any detail: `✅ #151 #153 #154 closed out — nothing left.`
or `🚫 9 merged — 2 things left: merge docs PR #M <url>; 3 local branches left behind`. The 🚫
list names **actions the human must take**, not steps that ran.

Then the detail block — **one line per PR** where the answer differs by PR (merge status, branch
outcome), **one line** where the step ran once for the group (the doc-currency PR URL, the
feedback-synthesis line, the git-state reasoning), each reflecting what ACTUALLY happened this run.
`run /flow:land <PR#>` is an explicit next action when §3 errored or was rejected — never imply
either happened when it didn't. **Do not merge anything** — `/flow:land`'s docs PR is the
human's to merge.

## Gotchas

- **Merge queue = wait, not fail.** The single most important behavior: a queued-but-unlanded
  PR is `open` → poll, never `terminal`. Only a `CLOSED`-unmerged PR fails loud — and in a group it
  fails *that PR*, not the run.
- **One run, one group.** Never loop the whole skill per PR. The doc-currency PR, the synthesis and
  the verdict are group-level; running them per PR is the chore this skill was changed to remove, and
  N `docs: land` PRs edit the same lines and conflict with each other.
- **Composition is a real `Skill()` call (FB-0077).** Delegate doc reconciliation to
  `/flow:land`; never reimplement it here (FB-0010 fan-out + the compose-not-combine decision),
  and never downgrade it to "ask the human to run it" — that is what made this skill a reminder
  instead of an orchestrator. `/flow:land` is model-invocable *because* its own §1a merged-PR
  gate is the real guard; `doctor/lib/skill-composition-lint.py` keeps the call legal, and
  `run_skill_composition_evals.py` fails if the flag comes back.
- **This skill is model-invocable; the AUTO-INVOCATION clause is the only thing saying when.**
  The merge gate bounds *what* it can touch (merged PRs only), but nothing mechanical stops a
  premature call — only the clause does. Do not fire it at the end of `/flow:ship` (the PR is open)
  or in anticipation of a merge. If it was invoked early, §2 will report the PR `still open` and
  change nothing; say so and stop.
- **`git branch -d`, never `-D` — and expect `-d` to refuse after a squash merge.** The safe delete
  is a backstop even after the merge check. Left-behind local branches are reported, not forced.
- **A remote head is deleted only if its tip equals the PR's `headRefOid`.** "The PR merged" is not
  enough: commits pushed after the merge were never reviewed.
- **Skip and name, don't fight, a branch checked out elsewhere.** Another worktree's checkout is
  not this skill's to disturb.
- **v1 writes user-scope only.** No `feedbackPath` repo-doc write; content-match dedup makes an
  overlapping window safe without a transcript watermark (both the transcript watermark + repo-doc
  FB-inbox are v1b).
- **Idempotent.** A re-run after a partial close-out is safe: §3 detects an existing `docs: land`
  PR for each number instead of re-asking for one, dedup absorbs re-synthesis, and a branch delete
  is skipped if already gone.

## Config slots used

| Slot | Default | Used in |
|---|---|---|
| `flow.config.json.postMergeWaitSeconds` | `150` (`0` = fail-fast) | §2 merge-detect poll cap (one cap for the whole group) |
| `flow.config.json.defaultBranch` | `git symbolic-ref` → `main` | §1b default group, §5 cleanup target |
| `flow.config.json.contributionsQueuePath` | `~/.claude/plugins/data/flow/contributions` | §1b/§4b/§6b directory for the markers |
| `flow.config.json.lastHarvestedPath` | `…/contributions/last_harvested.json` | §4b harvest watermark; §1b/§6b put `last_retro.json` beside it |
