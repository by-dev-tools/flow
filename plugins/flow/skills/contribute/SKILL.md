---
name: contribute
description: |
  Drain the cross-project lesson-contribution queue into a PR against the flow plugin repo. This is the DRAIN end of the lesson-harvest loop (FB-0059): /flow:ship + /flow:ship-spike Step 4c enqueues flow-generalizable lessons (reviewer false-positives, gate misfires, taste calls the human overruled) to user-scope storage as you work in any project; this skill — run FROM the flow checkout — synthesizes them into flow edits, sanitizes out personal-project tokens, applies the verified ones, and opens a PR. Never merges (the human gates the merge).
  Runs UNATTENDED by design (a flow-repo SessionStart hook and/or a local OS job invoke it; see workflow.md). You may also invoke it manually as an override. Trigger phrases: "/flow:contribute", "drain the contribution queue", "contribute lessons back to flow", "harvest lessons into a flow PR".
  Also drains the existing /flow:log-disagreement store (disputed reviewer findings → reviewer-prompt + eval-fixture proposals) — closing a loop those records were always meant for but nothing automated.
allowed-tools: Read, Edit, Write, Glob, Grep, Bash, Agent, Skill
---

# Task: contribute harvested lessons back to flow

You are draining accumulated, generalizable lessons into a PR against the flow plugin repo. The human reviews and merges; you never merge. **Split the output by confidence, do not park it behind a draft (FB-0073):** verified, self-contained changes get *applied* and the PR opens **ready for review**; genuine decisions get *surfaced explicitly* in the body. A draft is neither doing the work nor asking the question — the merge is the human gate, not the draft state. This runs unattended — emit clear one-line status, make no interactive prompts, and **fail safe** (when in doubt, HOLD an item for human attention rather than shipping it into the PR).

## Resolve scripts + config

```sh
# Preflight (BLOCKING) — jq reads every config slot below; gh opens the PR. If either is
# absent, slot reads silently fall back to defaults (contributionThreshold, and a custom
# contributionsQueuePath → split-brain with contribution_store.py's own default). Fail
# loud, same shape as /flow:ship Step 1.5 (FB-0009). Ref jq-absence-handling-2026-06.
MISSING=""
command -v gh >/dev/null 2>&1 || MISSING="$MISSING gh"
command -v jq >/dev/null 2>&1 || MISSING="$MISSING jq"
if [ -n "$MISSING" ]; then
  MISSING_TRIMMED=$(echo "$MISSING" | sed 's/^ //')
  echo "⚠️ BLOCKER: /flow:contribute requires $MISSING_TRIMMED (missing on PATH)." >&2
  echo "   Install: brew install$MISSING (macOS) | apt install$MISSING (Debian/Ubuntu) | https://cli.github.com (gh), https://jqlang.org (jq)" >&2
  case " $MISSING_TRIMMED " in *" gh "*) echo "   After install, run: gh auth login" >&2 ;; esac
  exit 1
fi

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
python3 "$SCRIPTS/contribution_store.py" dedup --lesson-hash "<hash>"
# exit 0 = novel · exit 3 = already queued (drop it) · exit 4 = RECURRENCE of a
# previously-dismissed lesson (do NOT drop — see the re-examine rule below)
```

Also drop **already-encoded** lessons: grep `dev-docs/feedback.md` and the candidate's target artifact for the synthesized rule; on a match, `dismiss` it with reason `already-encoded` and skip.

**An `already-encoded` dismissal must reproduce the symptom, not reason from the fix.** A grep hit — or an argument that the target "already shares the hardened helper / was covered by PR #N" — establishes that *some* fix exists, not that *this* failure mode is gone. Before dismissing, construct the smallest input that would exhibit the reported symptom and confirm it no longer occurs; if you cannot cheaply construct one, HOLD rather than dismiss. (Dogfood: a `Visual-walk` cross-PR grab was dismissed as already-encoded because both walk parsers share `walk_extract.py`'s first-block scoping — that shared scoping was the *cause*, since selection is per-label and the two can land in different PRs' sections. A short repro plan would have caught it; instead it took an independent recurrence from a second project.) A **recurrence of a previously-dismissed lesson is strong evidence the dismissal was wrong** — re-examine it from scratch rather than re-applying the earlier reasoning. `dedup` reports this mechanically as **exit 4** (distinct from exit 3 "already queued"), with the prior dismissal's reason and date on stderr: treat exit 4 as *re-open with the prior reason as the thing to disprove*, never as a drop. Re-dismissing after an exit 4 requires the symptom repro above — a second wrong dismissal should cost more than the first.

## Step 4 — sanitize (FAIL-CLOSED — runs before anything reaches the PR)

The flow repo is **public** and must stay project-agnostic. Scrub every candidate's lesson text + evidence window before it can land in a commit.

```sh
KNOWN="$QUEUE_ROOT/known_tokens.json"
# scrub (neutralize), then re-scan; a non-zero scan = residual leak.
python3 "$SCRIPTS/sanitize_tokens.py" scrub --tokens-file "$KNOWN" < raw.txt > clean.txt
python3 "$SCRIPTS/sanitize_tokens.py" scan  --tokens-file "$KNOWN" < clean.txt   # exit 1 = still dirty
```

- **scan clean (exit 0)** → mark the entry `sanitization_clean = true`.
- **scan still dirty (exit 1)** → mark `sanitization_clean = false`. This **halves** its confidence and routes it to **HELD (needs-manual-scrub)** — it is listed in the PR body under "Held — needs human attention" and is **never** auto-included in the diff. Do not hand-edit the scan to pass. A residual leak the deterministic scan misses is exactly why the human still reviews the PR.

## Step 5 — score, then split include vs hold

```sh
python3 "$SCRIPTS/contribution_store.py" score "<entry.json>" --write   # writes confidence
```

- **Auto-include** an entry iff `confidence >= $THRESHOLD` AND `sanitization_clean == true`.
- **Hold** everything else (sub-threshold OR needs-manual-scrub) — surfaced in the PR body, carried to the next run, never dropped.

## Step 6 — apply included edits + open/update the rolling PR

For each auto-included entry, apply the edit by `artifact_kind`:

- `fb-entry` → a new `FB-XXXX` in `dev-docs/feedback.md` (claim the number in `dev-docs/reserved-feedback-numbers.md` FIRST, per its protocol).
- `rule-edit` / `new-check` → the named rule / doctor or ship check.
- `reviewer-prompt` → a scoped edit to `auditor.md` / `plan-critic.md` / the staff lens.
- `eval-fixture` / any reviewer-prompt change → **draft a companion eval fixture** under `plugins/flow/evals/fixtures/` (reuse the disagreement `.jsonl` window where available) and **wire its harness into `.github/workflows/ci.yml`** (CI enumerates harnesses explicitly — an unwired harness gives zero protection). Prompt changes are code changes (CLAUDE.md): no reviewer-prompt edit ships without a fixture.

Then commit and open or update a **single rolling PR**, ready for review (FB-0073 — not a draft):

```sh
# Reuse an open contribution PR (append commits) — never spawn duplicates.
OPEN=$(gh pr list --repo "$FLOW_REPO" --state open --label flow-contribution \
  --json number --jq '.[0].number' 2>/dev/null)
# If $OPEN: push to its branch. Else: create a NEW branch + PR labeled flow-contribution.
# NOT --draft: applied edits are verified work awaiting a merge decision, not a parking lot.
# (A genuine BLOCKER still drafts it, via /flow:ship's own draft-manifest rule -- same as any PR.)
gh pr create --repo "$FLOW_REPO" --label flow-contribution \
  --title "flow-contribution: harvested lessons" --body "<body>"
```

PR body must include: the included lessons (with provenance + confidence + sanitization status) and a **"Held — needs human attention"** section listing every held entry and why (sub-threshold / needs-manual-scrub / needs a design call). Hold reasons must be specific enough to act on — "needs a design call" without naming the fork is parking, which is what FB-0073 rejects. **Never merge.** The merge is the human gate; merge = approved, close = rejected, edit-then-merge = edited (Step 1 reads that next run).

After draining, advance nothing in the queue you didn't act on — held items stay queued for next time. **Flip each entry you included in the PR out of the drain so it doesn't re-appear on the next run:**

```sh
python3 "$SCRIPTS/contribution_store.py" set-status --id "<entry-id>" --status proposed
```

(`contribution_store.py list` only emits `status==queued`, so a `proposed` entry won't re-drain; if its PR is later closed-unmerged, Step 1's calibrate routes it to `dismissed.json`.) Entries the human rejects go to `dismiss`; held (sub-threshold / needs-manual-scrub) entries stay `queued`.

## What not to do

- Do not run outside the flow checkout (Step 0 guards this).
- Do not merge or auto-approve. (Opening **ready for review** is correct — FB-0073; only a genuine BLOCKER drafts the PR, on the same rule as any other `/flow:ship` run.)
- Do not include an entry that failed sanitization, or one below threshold, in the diff — hold it.
- Do not edit a sanitizer scan or a confidence score to force an include.
- Do not regenerate a disagreement's captured `.jsonl` window — reuse it as the fixture skeleton.
