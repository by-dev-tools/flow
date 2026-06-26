---
name: contribute
description: |
  Drain the cross-project lesson-contribution queue into a draft PR against the flow plugin repo. This is the DRAIN end of the lesson-harvest loop (FB-0058): /flow:ship Step 4c enqueues flow-generalizable lessons (reviewer false-positives, gate misfires, taste calls the human overruled) to user-scope storage as you work in any project; this skill — run FROM the flow checkout — synthesizes them into proposed flow edits, sanitizes out personal-project tokens, and opens a draft PR. Never merges (human gates the merge in v1).
  Runs UNATTENDED by design (a flow-repo SessionStart hook and/or a local OS job invoke it; see workflow.md). You may also invoke it manually as an override. Trigger phrases: "/flow:contribute", "drain the contribution queue", "contribute lessons back to flow", "harvest lessons into a flow PR".
  Also drains the existing /flow:log-disagreement store (disputed reviewer findings → reviewer-prompt + eval-fixture proposals) — closing a loop those records were always meant for but nothing automated.
allowed-tools: Read, Edit, Write, Glob, Grep, Bash, Agent, Skill
---

# Task: contribute harvested lessons back to flow

You are draining accumulated, generalizable lessons into a **draft** PR against the flow plugin repo. The human reviews and merges; you never merge. This runs unattended — emit clear one-line status, make no interactive prompts, and **fail safe** (when in doubt, HOLD an item for human attention rather than shipping it into the PR).

## Resolve scripts + config

```sh
# Resolve plugin scripts: installed plugin root, else this flow checkout.
if [ -n "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -d "${CLAUDE_PLUGIN_ROOT}/scripts" ]; then
  SCRIPTS="${CLAUDE_PLUGIN_ROOT}/scripts"
elif [ -d "plugins/flow/scripts" ]; then
  SCRIPTS="plugins/flow/scripts"
else
  echo "⚠️ [contribute] cannot locate flow scripts; run from the flow checkout."; exit 0
fi

# Resolve config slots (defaults match the schema).
CFG="flow.config.json"
get() { jq -r ".$1 // empty" "$CFG" 2>/dev/null; }
FLOW_REPO="$(get flowRepoPath)"
THRESHOLD="$(get contributionThreshold)"; [ -z "$THRESHOLD" ] && THRESHOLD="0.6"
QUEUE_ROOT="$(get contributionsQueuePath)"
[ -z "$QUEUE_ROOT" ] && QUEUE_ROOT="$HOME/.claude/plugins/data/flow/contributions"
QUEUE_ROOT="$(echo "$QUEUE_ROOT" | sed "s#^~#$HOME#")"
# Export FLOW_CONTRIB_DIR so every contribution_store.py call below operates on the SAME
# directory the skill reads ($QUEUE_ROOT). Without this, the store falls back to its own
# default and diverges from a configured contributionsQueuePath (split-brain).
export FLOW_CONTRIB_DIR="$QUEUE_ROOT"
DISAGREE_DIR="$HOME/.claude/plugins/data/flow/disagreements"
```

## Step 0 — guards (fail clean, never a partial run)

1. **Run from the flow checkout.** If `flowRepoPath` is set and `$(pwd -P)` is not that path (resolve both), print one line — `run /flow:contribute from the flow checkout at <flowRepoPath>` — and stop. If `flowRepoPath` is unset and the cwd has no `.claude-plugin/marketplace.json`, print a one-line hint to set `flowRepoPath` and stop.
2. **Nothing to do.** If the queue (`$QUEUE_ROOT/queue/*.json` with `status:queued`) is empty AND the disagreements store (`$DISAGREE_DIR/*.meta.json`) is empty, print `[contribute] queue empty — nothing to drain` and stop.

## Step 1 — calibrate from prior PR outcomes (closes the loop unattended)

Before draining new work, learn from what the human did with the last contribution PR. The PR outcome IS the human-gate signal — no interactive prompt needed.

```sh
# Find contribution PRs the human already closed/merged since last run.
gh pr list --repo "$FLOW_REPO" --state all --label flow-contribution --limit 20 \
  --json number,state,mergedAt,title 2>/dev/null
```

For each contribution PR resolved since the last run: `merged` → `approved`; `closed` unmerged → `rejected`; merged-after-edits → `edited`. Record one calibration event per lesson it carried, and route rejected lessons to `dismissed.json` so they never resurface:

```sh
python3 "$SCRIPTS/contribution_store.py" calibrate --lesson-hash "<hash>" \
  --confidence "<score-at-decision>" --decision "approved|edited|rejected" --artifact-kind "<kind>"
# rejected only:
python3 "$SCRIPTS/contribution_store.py" dismiss --lesson-hash "<hash>" \
  --summary "<summary>" --reason "rejected-in-#<pr>" --by "pr-outcome"
```

This is the data a future auto-merge rung trains its threshold on (deferred — v1 always gates merge on the human).

## Step 2 — drain BOTH sources

1. **Contribution queue:**
   ```sh
   python3 "$SCRIPTS/contribution_store.py" list   # pending entries, sorted by confidence
   ```
2. **Disagreements store** (loop-closure): each `$DISAGREE_DIR/*.meta.json` is a disputed reviewer finding the maintainer never processed. Convert each into a candidate `reviewer-prompt` contribution — the disputed claim + the user's reason become the lesson; the paired `<stem>.jsonl` window (if present) is **reused verbatim** as the eval-fixture skeleton (do not regenerate it). The target artifact is the reviewer prompt named by the `reviewer` field (`auditor` → `plugins/flow/agents/auditor.md`; `plan-critic` → `plugins/flow/agents/plan-critic.md`).

## Step 3 — dedup

For every candidate, compute its `lesson_hash` and drop duplicates:

```sh
python3 "$SCRIPTS/contribution_store.py" dedup --lesson-hash "<hash>"   # exit 3 = duplicate
```

Also drop **already-encoded** lessons: grep `dev-docs/feedback.md` and the candidate's target artifact for the synthesized rule; on a match, `dismiss` it with reason `already-encoded` and skip.

## Step 4 — sanitize (FAIL-CLOSED — runs before anything reaches the PR)

The flow repo is **public** and must stay project-agnostic. Scrub every candidate's lesson text + evidence window before it can land in a commit.

```sh
KNOWN="$QUEUE_ROOT/known_tokens.json"
# scrub (neutralize), then re-scan; a non-zero scan = residual leak.
python3 "$SCRIPTS/sanitize_tokens.py" scrub --tokens-file "$KNOWN" < raw.txt > clean.txt
python3 "$SCRIPTS/sanitize_tokens.py" scan  --tokens-file "$KNOWN" < clean.txt   # exit 1 = still dirty
```

- **scan clean (exit 0)** → mark the entry `sanitization_clean = true`.
- **scan still dirty (exit 1)** → mark `sanitization_clean = false`. This **halves** its confidence and routes it to **HELD (needs-manual-scrub)** — it is listed in the PR body under "Held — needs human attention" and is **never** auto-included in the diff. Do not hand-edit the scan to pass. A residual leak the deterministic scan misses is exactly why the human still reviews the draft.

## Step 5 — score, then split include vs hold

```sh
python3 "$SCRIPTS/contribution_store.py" score "<entry.json>" --write   # writes confidence
```

- **Auto-include** an entry iff `confidence >= $THRESHOLD` AND `sanitization_clean == true`.
- **Hold** everything else (sub-threshold OR needs-manual-scrub) — surfaced in the PR body, carried to the next run, never dropped.

## Step 6 — apply included edits + open/update the draft PR

For each auto-included entry, apply the edit by `artifact_kind`:

- `fb-entry` → a new `FB-XXXX` in `dev-docs/feedback.md` (claim the number in `dev-docs/reserved-feedback-numbers.md` FIRST, per its protocol).
- `rule-edit` / `new-check` → the named rule / doctor or ship check.
- `reviewer-prompt` → a scoped edit to `auditor.md` / `plan-critic.md` / the staff lens.
- `eval-fixture` / any reviewer-prompt change → **draft a companion eval fixture** under `plugins/flow/evals/fixtures/` (reuse the disagreement `.jsonl` window where available) and **wire its harness into `.github/workflows/ci.yml`** (CI enumerates harnesses explicitly — an unwired harness gives zero protection). Prompt changes are code changes (CLAUDE.md): no reviewer-prompt edit ships without a fixture.

Then commit and open or update a **single rolling draft PR**:

```sh
# Reuse an open contribution PR (append commits) — never spawn duplicates.
OPEN=$(gh pr list --repo "$FLOW_REPO" --state open --label flow-contribution \
  --json number --jq '.[0].number' 2>/dev/null)
# If $OPEN: push to its branch. Else: create a NEW branch + draft PR labeled flow-contribution.
gh pr create --repo "$FLOW_REPO" --draft --label flow-contribution \
  --title "flow-contribution: harvested lessons" --body "<body>"
```

PR body must include: the included lessons (with provenance + confidence + sanitization status) and a **"Held — needs human attention"** section listing every held entry and why (sub-threshold / needs-manual-scrub). **Never merge.** The draft PR is the human gate; merge = approved, close = rejected, edit-then-merge = edited (Step 1 reads that next run).

After draining, advance nothing in the queue you didn't act on — held items stay queued for next time. **Flip each entry you included in the PR out of the drain so it doesn't re-appear on the next run:**

```sh
python3 "$SCRIPTS/contribution_store.py" set-status --id "<entry-id>" --status proposed
```

(`contribution_store.py list` only emits `status==queued`, so a `proposed` entry won't re-drain; if its PR is later closed-unmerged, Step 1's calibrate routes it to `dismissed.json`.) Entries the human rejects go to `dismiss`; held (sub-threshold / needs-manual-scrub) entries stay `queued`.

## What not to do

- Do not run outside the flow checkout (Step 0 guards this).
- Do not merge, mark ready-for-review, or auto-approve — v1 is draft-only.
- Do not include an entry that failed sanitization, or one below threshold, in the diff — hold it.
- Do not edit a sanitizer scan or a confidence score to force an include.
- Do not regenerate a disagreement's captured `.jsonl` window — reuse it as the fixture skeleton.
