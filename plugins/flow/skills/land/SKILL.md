---
name: land
description: >
  Post-merge doc-currency reconciliation. Human-invoked AFTER you merge a PR
  (Claude can't merge, so this can't live inside /flow:ship). It flips the
  merged PR's item to "merged (#N)" across roadmap / plan / history and moves it
  to "Recently shipped", then opens a small `docs: land #N` PR — never merges.
  Also re-runs the visual-history distill if a visual pass was blocked at ship
  and has since completed, clears any feedback-ID reservations the PR claimed,
  and checks CHANGELOG currency. Closes the "at PR → merged never reconciles"
  gap. Trigger: "/flow:land <PR#>", "land #N", "reconcile docs after merging
  #N".
disable-model-invocation: true
allowed-tools: Read, Edit, Write, Glob, Grep, Bash
---

You are running the flow **post-merge** doc-currency reconciliation for a PR that
a human has already merged. **You never merge anything** — you open a small
reconciliation PR the human merges.

This skill exists because `/flow:ship` reconciles forward docs at **PR-open** time
(Step 5a), but nothing flips the item to "merged (#N)" once the human merges — so
`main` sits stale until someone hand-writes a "docs: post-merge currency" PR
(FLOW-1, a recurring manual patch). `/flow:land <PR#>` is the one command that
replaces that hand-edit. `disable-model-invocation: true`: a human runs this after
merging — it must never auto-fire mid-loop.

## Project context (resolved at invocation)

- Project config: !`cat flow.config.json 2>/dev/null || echo "(no flow.config.json — using built-in defaults)"`
- Default branch: !`git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@' || cat flow.config.json 2>/dev/null | jq -r '.defaultBranch // "main"' 2>/dev/null || echo "main"`
- Current branch: !`git branch --show-current`
- Roadmap / plan / history paths: !`cat flow.config.json 2>/dev/null | jq -r '"roadmap=" + (.roadmapPath // "dev-docs/roadmap.md") + " plan=" + (.planPath // "dev-docs/plan.md") + " history=" + (.historyPath // "dev-docs/history.md")' 2>/dev/null || echo "roadmap=dev-docs/roadmap.md plan=dev-docs/plan.md history=dev-docs/history.md"`

## Argument

`/flow:land <PR#>` — the merged PR number. If the user omits it, try the most
recent merged PR for the current branch's lineage, but **confirm the number with
the user before editing anything** — landing the wrong PR corrupts the forward
docs. If you can't resolve a number, stop and ask; never guess silently.

## 1. Pre-flight

### 1.5. External CLI dependency check (BLOCKING)

`gh` + `jq` are mandatory (PR-state lookup + slot reads). Same fail-fast shape as
`/flow:ship` Step 1.5 (FB-0009) — the consistency is the value:

```sh
MISSING=""
command -v gh >/dev/null 2>&1 || MISSING="$MISSING gh"
command -v jq >/dev/null 2>&1 || MISSING="$MISSING jq"
if [ -n "$MISSING" ]; then
  MISSING_TRIMMED=$(echo "$MISSING" | sed 's/^ //')
  echo "⚠️ BLOCKER: /flow:land requires $MISSING_TRIMMED (missing on PATH)." >&2
  echo "   Install: brew install$MISSING | apt install$MISSING | https://cli.github.com (gh), https://jqlang.org (jq)" >&2
  case " $MISSING_TRIMMED " in *" gh "*) echo "   After install, run: gh auth login" >&2 ;; esac
  exit 1
fi
```

### 1a. Verify the PR is actually MERGED (BLOCKING — the load-bearing gate)

`/flow:land` reconciles docs to the *merged* reality. Running it on an open or
closed-unmerged PR would write a lie. Verify first; fail loudly, edit nothing:

```sh
N="<PR#>"   # the argument
STATE_JSON=$(gh pr view "$N" --json state,mergedAt,title,headRefName,mergeCommit,url 2>/dev/null)
if [ -z "$STATE_JSON" ]; then
  echo "⚠️ BLOCKER: gh could not read PR #$N (wrong number, wrong repo, or no auth). Nothing changed." >&2
  exit 1
fi
STATE=$(printf '%s' "$STATE_JSON" | jq -r '.state')
MERGED_AT=$(printf '%s' "$STATE_JSON" | jq -r '.mergedAt // empty')
if [ "$STATE" != "MERGED" ] || [ -z "$MERGED_AT" ]; then
  echo "⚠️ BLOCKER: PR #$N is '$STATE' (mergedAt=${MERGED_AT:-none}) — /flow:land runs AFTER a human merges." >&2
  echo "   If it really is merged, check you passed the right number. Nothing changed." >&2
  exit 1
fi
echo "[land] PR #$N is MERGED ($MERGED_AT). Title: $(printf '%s' "$STATE_JSON" | jq -r '.title')"
echo "[land] branch=$(printf '%s' "$STATE_JSON" | jq -r '.headRefName')  mergeCommit=$(printf '%s' "$STATE_JSON" | jq -r '.mergeCommit.oid // "unknown" | .[0:9]')"
```

Carry `title`, `headRefName`, and the short `mergeCommit` forward — Step 2 matches
on the PR number AND the branch name.

### 1b. Sync `main` so the reconciliation lands on top of the merge

```sh
git fetch origin --quiet
```

Create the reconciliation branch from the up-to-date default branch (Step 6 commits
here; Claude never pushes to `main` directly):

```sh
BASE=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@')
[ -z "$BASE" ] && BASE=$(jq -r '.defaultBranch // "main"' flow.config.json 2>/dev/null); [ -z "$BASE" ] && BASE=main
PREFIX=$(jq -r '.branchPrefix // empty' flow.config.json 2>/dev/null)
BR="${PREFIX}land-${N}"
# Idempotent: a re-run after a partial land reuses the existing branch (checkout -b
# would die "branch already exists", breaking the idempotency contract below).
if git show-ref --verify --quiet "refs/heads/${BR}"; then
  echo "[land] re-run: reusing existing branch ${BR}."
  git checkout "${BR}" && git rebase "origin/${BASE}"
else
  git checkout -b "${BR}" "origin/${BASE}"
fi
```

## 2. Discover the active-slot item (gh + doc-scan)

Find what this PR was tracked as in the forward docs, so you flip the right line.
Search `roadmapPath` "Now" and `planPath` "Current Focus" / "Active Work Items" for
a reference to **`#N`** or the **branch name** (`headRefName`):

This block is self-contained — re-resolve `N` and the branch name inline (the
skill's Bash blocks do NOT share variables across invocations):

```sh
N="<PR#>"
HEADREF=$(gh pr view "$N" --json headRefName --jq '.headRefName' 2>/dev/null)
ROADMAP=$(jq -r '.roadmapPath // "dev-docs/roadmap.md"' flow.config.json 2>/dev/null); [ -z "$ROADMAP" ] && ROADMAP=dev-docs/roadmap.md
PLAN=$(jq -r '.planPath // "dev-docs/plan.md"' flow.config.json 2>/dev/null); [ -z "$PLAN" ] && PLAN=dev-docs/plan.md
HISTORY=$(jq -r '.historyPath // "dev-docs/history.md"' flow.config.json 2>/dev/null); [ -z "$HISTORY" ] && HISTORY=dev-docs/history.md
# Build the pattern WITHOUT an empty alternative: an unset $HEADREF must not turn
# `#N\b|$HEADREF` into `#N\b|` (the trailing `|` matches EVERY line, which would
# make the no-match WARN below unreachable — the FB-0010 silent-skip class).
PAT="#${N}\b"; [ -n "$HEADREF" ] && PAT="${PAT}|${HEADREF}"
MATCHES=$(grep -nE "$PAT" "$ROADMAP" "$PLAN" "$HISTORY" 2>/dev/null)
if [ -n "$MATCHES" ]; then
  printf '%s\n' "$MATCHES"
else
  echo "[land] WARN: no active-slot reference to #$N or branch '${HEADREF:-?}' in $ROADMAP / $PLAN / $HISTORY — reconciling CHANGELOG + version currency only; flip the item by hand if it lives under a non-standard heading." >&2
fi
```

- **Match found** (`$MATCHES` non-empty) → those lines are your reconciliation
  targets (Step 3).
- **No match** → the loud `[land] WARN` above fired. Continue (Steps 4–7) with the
  CHANGELOG + version reconciliation, and flip the narrative item by hand. **Never
  a silent no-op** — the WARN tells the human the narrative flip didn't happen
  (FB-0010 silent-skip defense).

## 3. Reconcile the forward docs (narrative — your judgment)

This is prose reconciliation, the same shape as `/flow:ship` Step 5a (free-form
text, no mechanical marker — so you read each matched line and rewrite it sensibly,
the agent owns the wording):

- **`$ROADMAP` "Now":** flip the item's status from its at-PR phrasing — `at PR
  (#N, ready)`, `in flight`, `(#N) (ready)`, etc. — to **`merged (#N)`**, and move
  it into the **"Recently shipped"** line (trim the oldest if the list exceeds ~5).
  Refresh the **▶ Next up** pointer if this PR was it.
- **`$PLAN`:** move the item from "Active Work Items" / "Current Focus" → "Recently
  Completed" (keep the last 3–5); clear any "Handoff Notes" that referenced #N.
- **`$HISTORY`:** if this PR's entry recorded a placeholder/branch commit ref (e.g.
  `[pending]` or `<branch> (final SHA in the PR)`), update it to `merged #N @
  <mergeCommit short>`.

Do **not** rewrite narrative you can't ground in the merge — only the status of the
item this PR shipped.

## 4. CHANGELOG currency check

The merged version should already carry a `## v<version>` entry (written at ship).
Assert it; a missing entry is the FLOW-1 currency gap (it shipped uncaught once):

```sh
CHANGELOG=$(jq -r '.changelogPath // "CHANGELOG.md"' flow.config.json 2>/dev/null); [ -z "$CHANGELOG" ] && CHANGELOG=CHANGELOG.md
# Resolve the shipped version from the manifest the merge updated.
VSRC=""; for c in plugins/flow/.claude-plugin/plugin.json .claude-plugin/plugin.json package.json; do [ -f "$c" ] && { VSRC="$c"; break; }; done
VER=$(jq -r '.version // empty' "$VSRC" 2>/dev/null)
if [ -n "$VER" ] && [ -f "$CHANGELOG" ]; then
  python3 "${CLAUDE_PLUGIN_ROOT}/skills/land/lib/land-helpers.py" changelog-check "$CHANGELOG" --version "$VER" || \
    echo "[land] (add the missing changelog entry in this reconciliation PR, then re-run if needed)"
fi
```

The helper exits 0 (present), 1 (absent → WARN, you add the entry here), or 2
(no CHANGELOG → N/A). On a WARN, write the missing entry in this reconciliation PR.

## 5. Late visual-history distill (FLOW-5b) — only when a blocked pass has since completed

§5c of `/flow:ship` distills the durable `visual-history.html` entry from the
verify-build buffer. If the visual pass was **blocked at ship** (a permission
sheet, an unavailable simulator) and **completed only after merge**, §5c
self-skipped and the entry was never written. `/flow:land` is where it gets a
second chance. Run the SAME gate `/flow:ship` §5c uses:

```sh
UIS=$(jq -r '.uiSurface // true' flow.config.json 2>/dev/null)
VHPATH=$(jq -r '.visualHistoryPath // "core-docs/visual-history.html"' flow.config.json 2>/dev/null); [ -z "$VHPATH" ] && VHPATH="core-docs/visual-history.html"
FINDINGS=$(jq -r '.verifyFindingsPath // "/tmp/flow-verify-findings.json"' flow.config.json 2>/dev/null); [ -z "$FINDINGS" ] && FINDINGS="/tmp/flow-verify-findings.json"
if [ "$UIS" != "true" ]; then
  echo "[land] visual-history: skipped (uiSurface:false) — non-UI project."
elif [ ! -f "$FINDINGS" ]; then
  echo "[land] visual-history: skipped (no verify-build buffer at $FINDINGS) — no completed visual pass to distill."
else
  echo "[land] visual-history: gate open — inspect the buffer for a load-bearing visual decision NOT already in $VHPATH."
fi
```

If the gate opened: follow `/flow:ship` **§5c steps 1–5 verbatim** (read the buffer,
decide whether a load-bearing `grounding` (`need`/`design-language`/`craft-commitment`)
is present, author ONE curated entry, insert via
`python3 "${CLAUDE_PLUGIN_ROOT}/skills/ship/lib/insert-visual-history.py" --target "$VHPATH"`, stage the assets). Do
**not** re-implement the distill — reuse that one code path so there is a single
distill implementation. **Skip if the decision is already in `$VHPATH`** (don't
double-log an entry §5c already wrote at ship).

## 6. Clear the PR's reserved FB/VH numbers

`/flow:ship` clears a shipped PR's `FB-XXXX` reservation at Step 5a, but a PR that
merged without that step (or whose numbers were reserved late) can leave stale
lines. Clear each FB/VH id this PR introduced, from the reservations file if the
project keeps one:

```sh
RESV="dev-docs/reserved-feedback-numbers.md"   # project-specific; skip if absent
for ID in <FB-XXXX this PR claimed> <VH-XXXX if any>; do
  [ -f "$RESV" ] && python3 "${CLAUDE_PLUGIN_ROOT}/skills/land/lib/land-helpers.py" clear-reservation "$RESV" --id "$ID"
done
```

The helper is idempotent: clearing an absent id is a clean no-op (a re-run of
`/flow:land` never fails on an already-cleared number).

## 7. Commit + open the reconciliation PR

Stage the doc changes (+ any visual-history assets from Step 5). Commit `why`, not
`what`; `SAFETY` in the subject only if Step 5 touched the durable record:

```
docs: land #<N> — post-merge currency

Reconcile forward docs to the merged reality of #<N>: <item> → merged (#<N>),
moved to Recently shipped; <CHANGELOG / visual-history / reservations notes>.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
```

Push and open the PR. **Update its body via the REST form** (never `gh pr edit
--body` — the Projects-classic `projectCards` deprecation makes that silently
exit 1; FB-0057). For a NEW PR, `gh pr create --body-file` is unaffected:

```sh
gh pr create --base "$BASE" --title "docs: land #${N} — post-merge currency" --body-file <bodyfile>
```

Body: a one-paragraph summary of what was reconciled + a checklist of the steps that
ran vs skipped-with-reason (mirror the `/flow:ship` honesty bar). End with the
`🤖 Generated with [Claude Code]` line.

## 8. Hand off

Output the reconciliation PR URL + a one-line summary (`landed #N: <item> → merged;
<n> docs reconciled`). **Do not merge.** The human merges the small currency PR.

## Gotchas

- **The merged-state gate is load-bearing.** Never edit a doc before Step 1a
  confirms `state == MERGED`. Landing an open PR writes a lie into `main`.
- **No-match is a WARN, not a stop.** If discovery (Step 2) finds no active-slot
  line, still do the CHANGELOG + version + reservation reconciliation, and tell the
  human to flip the narrative item by hand. Silent no-op is the FB-0010 failure.
- **Reuse §5c — don't fork the distill.** The late visual-history entry must come
  from `insert-visual-history.py` via the §5c steps, so there is one record format.
- **Never `gh pr edit --body`.** Use the REST `gh api -X PATCH` form for any body
  *update* (FB-0057); `gh pr create --body-file` for the initial open is fine.
- **Idempotent by design.** Re-running `/flow:land #N` after a partial run must not
  error: already-flipped lines stay flipped, already-cleared numbers are no-ops, an
  already-distilled visual decision is skipped.

## Config slots used

| Slot | Default | Used in |
|---|---|---|
| `flow.config.json.defaultBranch` | `git symbolic-ref` → `main` | Step 1b (PR base), Step 7 |
| `flow.config.json.branchPrefix` | unset (no prefix) | Step 1b (reconciliation branch) |
| `flow.config.json.roadmapPath` | `dev-docs/roadmap.md` | Steps 2, 3 |
| `flow.config.json.planPath` | `dev-docs/plan.md` | Steps 2, 3 |
| `flow.config.json.historyPath` | `dev-docs/history.md` | Steps 2, 3 |
| `flow.config.json.changelogPath` | `CHANGELOG.md` | Step 4 |
| `flow.config.json.uiSurface` | `true` | Step 5 (§5c gate) |
| `flow.config.json.visualHistoryPath` | `core-docs/visual-history.html` | Step 5 (late distill) |
| `flow.config.json.verifyFindingsPath` | `/tmp/flow-verify-findings.json` | Step 5 (distill source) |
