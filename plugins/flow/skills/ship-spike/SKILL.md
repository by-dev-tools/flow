---
name: ship-spike
description: >
  Lightweight terminal pipeline for spike-mode PRs (exploratory work that
  answers a question rather than shipping a feature). Skips /simplify and
  /flow:staff-review (they ran for the full /flow:ship; spikes don't need
  them since the code is disposable). Writes the history.md entry — which
  IS the deliverable for a spike — commits, pushes, and opens a PR labeled
  `spike`. Never merges. Only invoke when the plan declared `mode: spike`.
  Trigger phrases: "ship the spike", "/flow:ship-spike", "wrap up the spike".
disable-model-invocation: false
allowed-tools: Read, Edit, Write, Glob, Grep, Bash, Agent, Skill
---

You are running the flow ship-spike pipeline for a spike-mode PR. **Never merge.**

## Project context (resolved at invocation)

- Project config: !`cat flow.config.json 2>/dev/null || echo "(no flow.config.json — using built-in defaults)"`
- Default branch (PR base): !`git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@' || cat flow.config.json 2>/dev/null | jq -r '.defaultBranch // "main"' 2>/dev/null || echo "main"`
- Current branch: !`git branch --show-current`
- History doc path: !`cat flow.config.json 2>/dev/null | jq -r '.historyPath // "dev-docs/history.md"' 2>/dev/null || echo "dev-docs/history.md"`
- Plan doc path: !`cat flow.config.json 2>/dev/null | jq -r '.planPath // "dev-docs/plan.md"' 2>/dev/null || echo "dev-docs/plan.md"`

## Pre-condition

The plan in the project's plan doc for the current work item must declare `**Mode:** spike`. If it doesn't, stop and tell the user — they want `/flow:ship`, not `/flow:ship-spike`. A spike-mode plan has:
- A research question.
- A disposability statement (deleted / kept behind flag / gates next PR).

If neither field exists, this is a feature plan and the wrong skill.

## 1. Pre-flight

### 1.5. External CLI dependency check (BLOCKING)

Fail-fast on missing `gh` CLI per FB-0009. Same shape as `/flow:ship` Step 1.5.

```sh
# POSIX-portable (NOT bash array — breaks on dash; see /flow:ship Step 1.5).
MISSING=""
command -v gh >/dev/null 2>&1 || MISSING="$MISSING gh"
command -v jq >/dev/null 2>&1 || MISSING="$MISSING jq"
if [ -n "$MISSING" ]; then
  MISSING_TRIMMED=$(echo "$MISSING" | sed 's/^ //')
  echo "⚠️ BLOCKER: /flow:ship-spike requires $MISSING_TRIMMED (missing on PATH)." >&2
  echo "   Install:" >&2
  echo "     macOS:         brew install$MISSING" >&2
  echo "     Debian/Ubuntu: apt install$MISSING" >&2
  echo "     Other:         https://cli.github.com (gh), https://jqlang.org (jq)" >&2
  case " $MISSING_TRIMMED " in *" gh "*) echo "   After install, run: gh auth login" >&2 ;; esac
  exit 1
fi
```

Identical shape to `/flow:ship` Step 1.5 — the consistency itself is the value per FB-0009.

### 1a. Stale-base check (BLOCKING)

Same gate as `/flow:ship` Step 1a — spike branches diff vs the default branch too, and a stale spike base produces phantom-deletion noise that obscures the actual research-question answer. See `dev-docs/feedback.md` FB-0008. See `/flow:ship` Step 1a for the rationale on the `[ -z ]` guards (the `||` pipe form silently fails on empty stdout).

```sh
DEFAULT_BRANCH=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@')
[ -z "$DEFAULT_BRANCH" ] && DEFAULT_BRANCH=$(jq -r '.defaultBranch // "main"' flow.config.json 2>/dev/null)
[ -z "$DEFAULT_BRANCH" ] && DEFAULT_BRANCH=main

git fetch origin --quiet
if ! git merge-base --is-ancestor "origin/${DEFAULT_BRANCH}" HEAD; then
  BEHIND=$(git rev-list --count HEAD..origin/${DEFAULT_BRANCH})
  HEAD_SHORT=$(git rev-parse --short HEAD)
  echo "⚠️ BLOCKER: branch is stale vs origin/${DEFAULT_BRANCH}." >&2
  echo "   Current HEAD: ${HEAD_SHORT}; base is behind by ${BEHIND} commit(s)." >&2
  echo "   Try: git fetch origin && git rebase origin/${DEFAULT_BRANCH}" >&2
  exit 1
fi
```

### 1b. Confirm there is something to ship

In parallel (each bullet is its own Bash invocation — `DEFAULT_BRANCH` from 1a does NOT persist):
- `git status --short`
- `` git log --oneline origin/$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@' || jq -r '.defaultBranch // "main"' flow.config.json 2>/dev/null || echo main)..HEAD ``
- `gh pr list --head $(git branch --show-current) --json number,url 2>/dev/null`

Classify (same shape as `/flow:ship`):
- **PR-OPEN** — at least one PR returned. Note the number for body updates; we'll push new commits to the existing spike PR rather than open a new one.
- **LOCAL-ONLY** — commits ahead and/or dirty tree, no PR yet. The normal spike-ship path.
- **NOTHING-TO-SHIP** — clean tree at default branch. Stop and tell the user.

If on the default branch: create a spike branch first. The conventional prefix is `spike/`; if `flow.config.json.branchPrefix` is set, prepend it (e.g., `claude/` + `spike/` → `claude/spike/<short-name>`).

```sh
PREFIX=$(cat flow.config.json 2>/dev/null | jq -r '.branchPrefix // empty' 2>/dev/null)
git checkout -b "${PREFIX}spike/<short-name>"
```

### 1c. Mechanical preflight (bounded retry — N ≤ 3)

Same contract as `/flow:ship` Step 1c — bounded-retry preflight that loops only on externally-verifiable exit codes (N=3 cap, oscillation detection via diff-hash, docs-only early-exit). **Reviewer outputs in Step 2 stay deliberately single-pass; the loop only fires on the preflight exit code, never on LLM-judgment outputs.** The consistency itself is the value: spike-mode work goes through the same mechanical gate as feature-mode work, even though spike code is disposable. A spike whose preflight is red is answering its research question conditionally on a broken state; flag that explicitly in the history entry rather than burying it.

```sh
# Resolve preflightCmd. Unset/whitespace-only → loud warning, proceed without retry (never silent).
PREFLIGHT_CMD=$(jq -r '.preflightCmd // empty' flow.config.json 2>/dev/null)
# Treat whitespace-only as unset (jq returns the literal whitespace string for "  " slot values).
if [ -z "$(printf '%s' "$PREFLIGHT_CMD" | tr -d '[:space:]')" ]; then
  echo "⚠️ flow.config.json.preflightCmd not set; skipping mechanical preflight. Set this slot to enable bounded-retry typecheck/lint/test on /flow:ship-spike."
  # Continue to Step 2 without running the loop.
else
  # Docs-only early-exit: reuse sourceFilePatterns (PR D lineage).
  DEFAULT_BRANCH=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@')
  [ -z "$DEFAULT_BRANCH" ] && DEFAULT_BRANCH=$(jq -r '.defaultBranch // "main"' flow.config.json 2>/dev/null)
  [ -z "$DEFAULT_BRANCH" ] && DEFAULT_BRANCH=main
  SOURCE_PATTERN=$(jq -r '.sourceFilePatterns // empty' flow.config.json 2>/dev/null)
  [ -z "$SOURCE_PATTERN" ] && SOURCE_PATTERN='\.(ts|tsx|js|jsx|mjs|cjs|py|rs|swift|go|rb|java|kt|sh|bash|tf|tfvars|sql|proto|graphql|gql)$|\.(json|ya?ml|toml)$|(^|/)(Dockerfile|Makefile)(\.|$)'

  # Validate sourceFilePatterns regex BEFORE using it (FB-0010 silent-skip prevention).
  echo "" | grep -qE "$SOURCE_PATTERN" 2>/dev/null
  GREP_RC=$?
  if [ "$GREP_RC" -gt 1 ]; then
    echo "⚠️ [preflight] flow.config.json.sourceFilePatterns is invalid as an extended regex (grep exit $GREP_RC); falling back to default." >&2
    SOURCE_PATTERN='\.(ts|tsx|js|jsx|mjs|cjs|py|rs|swift|go|rb|java|kt|sh|bash|tf|tfvars|sql|proto|graphql|gql)$|\.(json|ya?ml|toml)$|(^|/)(Dockerfile|Makefile)(\.|$)'
  fi

  # Three checks (PR D pattern): committed + uncommitted + untracked.
  SOURCE_FILES_COMMITTED=$(git diff "origin/${DEFAULT_BRANCH}..HEAD" --name-only 2>/dev/null | grep -E "$SOURCE_PATTERN" || true)
  SOURCE_FILES_MODIFIED=$(git diff HEAD --name-only 2>/dev/null | grep -E "$SOURCE_PATTERN" || true)
  SOURCE_FILES_UNTRACKED=$(git ls-files --others --exclude-standard 2>/dev/null | grep -E "$SOURCE_PATTERN" || true)
  if [ -z "$SOURCE_FILES_COMMITTED" ] && [ -z "$SOURCE_FILES_MODIFIED" ] && [ -z "$SOURCE_FILES_UNTRACKED" ]; then
    echo "[preflight] no source files in diff (committed+uncommitted+untracked); skipping mechanical preflight (docs-only spike)."
    # Continue to Step 2 without running the loop.
  fi
  # If PREFLIGHT_CMD is set AND source files exist anywhere, follow the retry contract below.
fi
```

**Retry contract** (followed by the agent executing this skill — iteration discipline is in the prompt, not in shell):

For each attempt `N` in 1..3:

1. Run `sh -c "$PREFLIGHT_CMD"`. Capture exit code and stderr.
2. If **exit 0**: log `[preflight] attempt N of 3: PASSED.` → proceed to Step 2.
3. If **exit 127** (command not found): abort with `BLOCKER: preflightCmd resolved to a command not found on PATH ($PREFLIGHT_CMD). Fix the slot or install the script. Halting before Step 2.` → exit 1. Do NOT count this against the retry budget.
4. If **any other non-zero exit**: log `[preflight] attempt N of 3: FAILED (exit code <N>).` Capture the diff hash via `git diff HEAD | sha256sum | cut -d' ' -f1`. Record for oscillation detection. Proceed to step 5.
5. If `N == 3`: abort with `BLOCKER: preflight failed 3 attempts without convergence. Last error: <stderr>. All attempted fixes preserved in tree; inspect with 'git diff origin/${DEFAULT_BRANCH}..HEAD'. Halting before Step 2.` → exit 1.
6. **Fix the failure.** Read stderr; identify the specific failure. Make the **minimal** fix:
   - Touch only files in the failure's blast radius. Do NOT refactor adjacent code.
   - Do NOT modify or disable tests unless the failure is a genuine test bug — and if so, name the bug explicitly in the attempt log. Disabling a test to make preflight green is reward hacking; for spike mode, this is doubly important because the spike's history entry IS the deliverable — a silently-disabled test corrupts the answer.
   - Do NOT add `// @ts-ignore`, `# noqa`, `# type: ignore`, `eslint-disable-next-line`, `// biome-ignore`, `@SuppressWarnings`, `#[allow(...)]`, or equivalent suppressors.
7. Compute the new diff hash. Compare against ALL prior hashes from this Step 1c run. If it matches ANY prior hash: abort with `BLOCKER: oscillation detected (attempt N+1 produced the same diff as attempt M). The fix is reverting a prior fix — a different approach is required. Last error: <stderr>. Halting before Step 2.` → exit 1.
8. Increment `N`. Return to step 1.

If Step 1c fails for a spike: the spike answered its research question conditional on a broken state. Either fix the broken state OR document the conditional explicitly in the history entry at Step 3 (`What we learned: <answer> — caveat: this assumes <broken thing> is resolved upstream`). Do NOT bypass Step 1c by deleting tests; that corrupts the spike's value.

## 2. Skip the CRAFT reviews; run the safety-net reviewers + verify-build

`/simplify` and `/flow:staff-review` do not run for spikes. Reviewing throwaway code for craft is theater.

> **What "disposable" does and does not excuse (FB-0100).** The disposability rationale above is about code *quality* on code that gets deleted, and it reaches exactly those two stages. Read no further into it. It does **not** excuse skipping `/flow:security-review` — the code is disposable, the **commit is not**, and a key hardcoded to move fast in a spike stays in git history long after the spike is deleted. It does **not** excuse skipping `/flow:accessibility-review` — flow is deliberately moving the human gate *onto prototypes* (a written plan cannot convey feel, so the human approves a prototype instead), which means an a11y flaw in an approved prototype does not die with the throwaway code: it propagates into the real PR as an endorsed **pattern**. And it says nothing at all about `/flow:audit-skips`, which is read-only and cheap. Both reviewers self-skip on a doc-only / non-UI diff, so the common spike pays one fork each that immediately exits — bounded cost, real upside. Step 1c above already enforces the bounded-retry mechanical preflight; this step is a one-shot typecheck confirmation that mirrors `/flow:ship` Step 3's role (re-check after any review-applied fixes, even though spike skips reviews):

```sh
# Configured typecheck via flow.config.json.typecheckCmd (one-shot; Step 1c already
# ran the full preflight loop with retry). If preflightCmd already includes typecheck,
# this is redundant but safe. If they're configured to overlap, the user owns that
# choice — see schema description's precedence note.
TYPECHECK=$(cat flow.config.json 2>/dev/null | jq -r '.typecheckCmd // empty')
if [ -n "$TYPECHECK" ]; then
  sh -c "$TYPECHECK"
else
  echo "⚠️ flow.config.json.typecheckCmd not set; skipping typecheck. Set this slot to enable typecheck on /flow:ship-spike."
fi
```

Step 1c (above) is the load-bearing preflight gate for spikes; a spike that survives Step 1c's bounded retry and this Step 2 one-shot typecheck has passed mechanical checks. If a spike's mechanical checks would fail in a way that invalidates the research answer, document that conditionally in Step 3's history entry rather than disabling the checks.

### 2.1. The two safety-net reviewers

Invoke both. Each cold-reads the diff and **self-skips** with a clean early-exit message when it has nothing to look at, so there is no spike-mode special case to maintain and no self-declared skip for the Step 2a audit to have to take on faith:

```
Skill("flow:security-review")
Skill("flow:accessibility-review")
```

- `/flow:security-review` self-skips on a doc-only or trivially-safe diff.
- `/flow:accessibility-review` self-skips on `flow.config.json.uiSurface: false` or a diff with no UI in it.

Route findings the same way `/flow:ship` Step 2 does, minus the manifest (spike PRs have none): fix `[auto-fixable]` BLOCKERs and cheap NITs in-tree; a `[decision-required]` BLOCKER is **not** best-effort'd — pause and hand the choice to the user (§2a.3's decision-required path), and record whatever they decide in the Step 3 history entry. FOLLOW-UPs go to the roadmap at Step 5.

**`/flow:audit-coverage` is NOT invoked in spike mode**, and that is a considered exclusion rather than an oversight. Its premise is *"is the declared criteria set complete?"* — and a spike declares a research question, not a `**Spec-walk:**` block, while spike-mode verify-build runs a fixed 3-check rubric instead of plan-derived criteria. There is no declared set for it to find incomplete. Report it in the Step 2a handoff as `skipped` / `no Spec-walk`; that claim is **mechanically verified against the plan file** by the audit engine, which is a stronger guarantee than the reviewer's own self-skip would give. It is also self-correcting: if the spike's plan *does* carry an active Spec-walk block, the engine returns `SHOULD-RE-RUN · auto-resolvable` and you invoke `Skill("flow:audit-coverage")` then.

### 2.2. Behavioral check

**Then invoke `/flow:verify-build` in spike mode** for a minimal behavioral check (does the spike's experimental code actually launch + execute its headline action without log errors). This is the same 3-check spike rubric documented at `${CLAUDE_PLUGIN_ROOT}/skills/verify-build/lib/spike-rubric.md`. Invoke and tell the skill that you're calling from `/flow:ship-spike` so it treats Trigger 1 (caller signal) as satisfied:

```
Skill("flow:verify-build")
# Contextual hint to verify-build: this invocation is from /flow:ship-spike;
# enter spike mode per Step 2 Trigger 1. (The skill also auto-detects spike
# mode via Triggers 2 and 3 if no plan or no Spec-walk block exists.)
```

> **Visual/interaction spikes.** If this spike is a visual or interaction prototype, make sure its plan declares a **`Visual-walk`** block (the states to capture) — verify-build §5a activates only on `uiSurface:true` **AND** a `Visual-walk` block, so a spike plan with just a spike/Spec-walk body (no `Visual-walk`) gives §5a no declared states to capture — the visual walkthrough you wanted isn't produced. With the block present, §5a captures frames + renders the ephemeral HTML walkthrough at `verifyReportPath`. And **invoke `/flow:verify-build`** as above — don't shortcut the behavioral check by driving the sim / `simctl` directly, which skips the Step-10 render. (Non-visual spikes need no `Visual-walk` block and stay fast — no capture.)

Skip behavior matches `/flow:verify-build` standalone: skip if `flow.config.json.verifyEnabled=false`, `platform=library|none`, or the platform's toolchain is absent from this host.

> **A `toolchain absent` skip is NOT a pass in spike mode — pause for the same adjudication the `Unknown` gate demanded.** Step 2a below now audits it (through v1.37.0 spike mode invoked **no** skip-legitimacy audit at all — see FB-0100), but a spike PR is still explicitly not gated by the NOT-READY manifest (see the PR sections below), so the mechanism that turns a validated-but-unverifiable skip into a *draft* on the `/flow:ship` path does not exist here. The audit names the gap; only this pause acts on it. Before this skip condition existed, a toolchain-less host ran verify-build, failed to launch, judged `Unknown`, and hit the Unknown-blocking gate — the user adjudicated. Letting the new self-skip exit 0 silently would convert that halt into a clean pass, which is strictly *less* gated than before on exactly the hosts the cloud workflow targets. So: treat it like the blocked gate. Tell the user the behavioral check could not run on this machine and why, and let them either re-run on a machine that has the toolchain or record the un-verified state as the spike's finding in the Step 3 history entry — the same two options the `Unknown` gate offers. Never proceed silently. Spike mode applies a lower verification bar (3 fixed checks vs N plan-derived) but the same Unknown-blocking gate — Unknown ⇒ exit 1 → spike ship halts. The lower bar is deliberate: spike code is throwaway, but "did this experiment actually launch and do the thing" is a load-bearing check the typecheck alone cannot answer.

If verify-build runs in spike mode and the gate blocks, the user adjudicates: either fix the headline-action behavior + re-run, OR document the failure in Step 3's history entry as the spike's actual finding ("the experiment confirmed that approach X does not work because Y") and proceed past the gate via re-invocation with `--skip-verify` (documented but not implemented in v1). The history entry IS the deliverable for a spike — a failed verify-build is a valid spike result if captured honestly.

## 2a. Skip-legitimacy audit (`/flow:audit-skips`) — runs AFTER Step 2, BEFORE Step 3

**Spike mode is the path that produces the most skips, so it is the path that most needs this gate.** Through v1.37.0 it was the one path that never ran it: `/flow:ship` invoked five reviewers, `/flow:ship-spike` invoked one, and nothing audited the rest. PR #140 shipped with five stages skipped — preflight, `/simplify`, staff-review, verify-build, memory — and no record that any of those skips was checked against anything. That is the same failure class as FB-0082 (this gate inert for eight versions), FB-0085 (rules that never loaded) and FB-0077 (a composition satisfied by deleting the call site): **a gate that does not fire where it is most needed.** See FB-0100.

The same rule applies here as at `/flow:ship` Step 2a: no stage skip is accepted on its own say-so, and "the agent did it manually" never substitutes for a stage's real pipeline output.

### 2a.1. Write the stage handoff

**Identical in shape to `/flow:ship` Step 2a.1 — the consistency itself is the value**, exactly as with Steps 1.5 and 1a. Only the stage rows differ (spike-appropriate statuses, plus a `preflight` row). Every guard below is load-bearing and none is decorative; see ship's Step 2a.1 for the incident behind each. The two copies are pinned against drift by `contract-ship-spike-handoff-*` in `evals/run_scratch_isolation_evals.py`, so this duplication does not depend on author memory (FB-0010).

```sh
# NOTE: this fence is deliberately NOT indented. A heredoc terminator must sit at
# column 0 — an indented `EOF` is treated as CONTENT, so the redirect swallows the
# rest of the script and the handoff is written as invalid JSON. That failure is
# invisible until something reads the file (FB-0082). Keep column 0.
FLOW_ROOT=$(git rev-parse --show-toplevel 2>/dev/null)
if [ -z "$FLOW_ROOT" ]; then
  # exit, don't warn-and-continue: with FLOW_ROOT empty the next line becomes
  # `mkdir -p /.flow` (read-only filesystem) and the raw errors bury this message.
  # A handoff a fork cannot read is not a degraded gate, it is no gate.
  echo "⚠️ BLOCKER: not inside a git repository, so no handoff can be written where a forked skill can read it. The skip-legitimacy gate CANNOT run — do NOT record it as legitimate. Re-run /flow:ship-spike from inside the repo worktree." >&2
  exit 1
fi
# No `${TMPDIR:-/tmp}/flow-detached` fallback here BY DESIGN: a fork cannot see /tmp
# at all, so a detached run must fail loudly rather than write a handoff nothing will
# ever read. (Same deliberate omission as ship Step 2a.1.)
FLOW_SCRATCH="$FLOW_ROOT/.flow"
# SECURITY (CWE-59): refuse to write scratch through a symlink. `.flow` is an ordinary
# repo path with none of git's .git/.gitmodules special-casing, so an untrusted clone can
# ship `.flow` as a symlink; `mkdir -p` on an existing symlink-to-dir exits 0 and FOLLOWS
# it, so every write below would land in an attacker-chosen directory outside the repo.
if [ -L "$FLOW_SCRATCH" ]; then
  echo "⚠️ BLOCKER: $FLOW_SCRATCH is a symlink — refusing to write flow scratch through it, because writes would land outside the repo (CWE-59). Replace it with a real directory." >&2
  exit 1
fi
mkdir -p "$FLOW_SCRATCH" || { echo "⚠️ BLOCKER: cannot create $FLOW_SCRATCH — the skip-legitimacy gate cannot run." >&2; exit 1; }
[ -f "$FLOW_SCRATCH/.gitignore" ] || printf '# Created by flow. Ephemeral scratch; never committed.\n*\n' > "$FLOW_SCRATCH/.gitignore"
STAGES="$FLOW_SCRATCH/skip-audit-stages.json"
FLOW_BR=$(git branch --show-current 2>/dev/null); FLOW_HEAD=$(git rev-parse --short HEAD 2>/dev/null)

# Build the stamp with `jq -n --arg` rather than interpolating into the heredoc: a branch
# name may legally contain a double quote, which would close the JSON string early.
STAMP=$(jq -nc --arg repo "$FLOW_ROOT" --arg branch "$FLOW_BR" --arg head "$FLOW_HEAD" \
  '{repo:$repo, branch:$branch, head:$head}')
# Quoted terminator: the stage rows are literal, and the stamp is spliced in by jq below.
cat > "$STAGES" <<'EOF'
{"stages": [
  {"name": "preflight",           "status": "<ran|skipped>", "skip_reason": "<preflightCmd not set|doc-only|null>"},
  {"name": "simplify",            "status": "skipped",       "skip_reason": "spike"},
  {"name": "staff-review",        "status": "skipped",       "skip_reason": "spike"},
  {"name": "security",            "status": "<ran|skipped>", "skip_reason": "<doc-only|null>"},
  {"name": "accessibility",       "status": "<ran|skipped>", "skip_reason": "<uiSurface:false|no UI in diff|null>"},
  {"name": "verify-build",        "status": "<ran|skipped>", "verdict": "<PASS|FAIL|Unknown|null>", "skip_reason": "<platform library|verifyEnabled:false|toolchain absent: <binaries> not on PATH|null>"},
  {"name": "audit-coverage",      "status": "skipped",       "skip_reason": "no Spec-walk"},
  {"name": "visual-verification", "status": "<ran|skipped>", "skip_reason": "<null>"}
]}
EOF
# Splice the soundly-escaped stamp in (jq rewrites the file from its own parse, so this
# doubles as a syntax check on the rows above).
TMP_STAGES="$STAGES.tmp"
jq --argjson stamp "$STAMP" '{flow_stamp:$stamp} + .' "$STAGES" > "$TMP_STAGES" && mv "$TMP_STAGES" "$STAGES" \
  || { echo "⚠️ BLOCKER: could not stamp the handoff at $STAGES — the skip-legitimacy gate cannot run." >&2; rm -f "$TMP_STAGES"; exit 1; }

# Read-back the write (FB-0067: never trust a write's own exit status).
jq . "$STAGES" >/dev/null 2>&1 || { echo "⚠️ BLOCKER: the handoff at $STAGES is not valid JSON — the skip-legitimacy gate cannot run. Check that the heredoc terminator is at column 0." >&2; exit 1; }
```

Fill every `<…>` from what actually happened this run — do **NOT** leave placeholders. `verify-build`'s `verdict` is its `overall_verdict`; `visual-verification` is the Present-step visual sign-off (ran iff you captured + reviewed frames this run); `preflight` is Step 1c.

**The two pre-filled rows are the only mode-declared skips spike mode gets.** `simplify` and `staff-review` are literal `"spike"` because that skip *is* the mode, and the engine routes it to `NEEDS-JUDGMENT` for the auditor to confirm against the plan's declared mode — which your Pre-condition already required. **Do not write `"spike"` as the skip reason for `security`, `accessibility` or `audit-coverage`.** The engine rejects it outright (`SHOULD-RE-RUN`), because a mode-declared blanket skip is unauditable by construction: mode is a plan declaration, so the gate would be accepting the very claim it exists to contest. Those three skip for diff/config/plan reasons the engine can check, or they run.

### 2a.2. Invoke the audit

```
Skill("flow:audit-skips")
```

Fresh-context, read-only — it classifies, it never fixes. It returns a `SKIP-AUDIT SUMMARY` with one line per stage, backed by the deterministic `lib/skip-audit-checks.py`; trust the mechanical verdicts verbatim.

### 2a.3. Resolve — spike mode has no draft manifest, so an unresolved finding PAUSES

`/flow:ship` routes unresolved findings to the NOT-READY draft manifest. A spike PR is explicitly not gated by that manifest (see the PR sections below), so spike mode uses the mechanism it already has for exactly this situation: **the same halt-and-adjudicate the toolchain-absent verify-build skip uses in Step 2.** The user decides; you never decide for them, and you never proceed silently.

- **All `LEGITIMATE`, none carrying a `manifest:` field** → print `skip-audit: all N stage skips legitimate` and continue to Step 3. The qualifier is load-bearing — an unqualified "all legitimate → proceed" is how a validated-but-*unverifiable* skip slips through.
- **`SHOULD-RE-RUN · auto-resolvable`** → re-run that stage **now** (`Skill("flow:security-review")` / `Skill("flow:accessibility-review")` / `Skill("flow:audit-coverage")` / `Skill("flow:verify-build")`, or re-run `preflightCmd`), rewrite the handoff row, and re-invoke `Skill("flow:audit-skips")` **ONCE**. One cycle only — never iterate on LLM judgment, which is reward-hackable (same discipline as `/flow:ship`).
- **`SHOULD-RE-RUN · decision-required`** → **halt and hand the user the choice**, in the same two-option shape the Step 2 toolchain gate uses: fix the gap and re-run, **or** record the un-audited state as part of the spike's finding. Whatever they choose goes verbatim into the Step 3 history entry and the `## Flow run` table.
- **`LEGITIMATE · manifest: <kind>`** (today: a validated `toolchain` absence) → **not a clean pass.** The skip was honest *and* the check still never ran. There is no manifest here to carry it, so it becomes the same halt: tell the user the behavioral check could not run on this machine and why, and let them re-run on an equipped machine or record the un-verified state as the spike's finding.
- **Any error shape — `root_error` / `ROOT UNRESOLVED`, `jq_error`, `engine_error`, `stamp_error`, `stamp_unverifiable`, or `SKIP-AUDIT: no stage report to audit` on a run where you DID write a handoff at 2a.1** → the gate **did not run**. Never record it as legitimate; never treat it as "nothing to audit". For `stamp_error` only, rewrite the handoff at 2a.1 and re-invoke **once** — a second refusal means the transport is broken. For every other shape, halt and adjudicate as above, naming which shape fired and what it means. An unanchored fork validates every unverifiable skip as LEGITIMATE, so a confident "all legitimate" from a broken run is exactly the output you must not trust.

Then record the result in the Step 3 history entry and in the PR's `## Flow run` table (`/flow:audit-skips` row).

A docs-only spike — the common case — rules clean here without noise: those skips ARE legitimate and the diff/config/plan back them. The audit validates the skip; it does not ban skipping.

## 3. Write the history entry — the entry IS the deliverable

The point of a spike is the learning, not the code. The history doc entry (path from `flow.config.json.historyPath`; default `dev-docs/history.md`) is the canonical artifact. Add an entry (newest first) with:

```markdown
### Spike: <one-line title>
**Date:** YYYY-MM-DD
**Branch:** <name>
**Mode:** spike

**Research question:** <the specific question the spike answers>

**What was built:** <smallest thing that answered the question; one paragraph max>

**What we learned:** <the answer, with any caveats>

**Recommendation:** proceed | pivot | abandon
- If proceed: what the next (real) PR looks like, in 1–3 sentences.
- If pivot: what the better question is, and what to try next.
- If abandon: why this direction is closed; what would re-open it.

**Disposability:** <code is being deleted / kept behind flag / gates next PR>
```

A spike's history entry is shorter than a feature's. Don't pad it with technical decisions or tradeoffs unless the spike itself surfaced them.

## 4. Capture agent self-feedback (if applicable)

Spikes often surface failure-pattern memory entries because the agent is operating with less guard-rail. **All 5 guardrails from `/flow:ship` step 4b apply equally to spike mode** — don't relax them just because the surrounding pipeline is lighter. See `${CLAUDE_PLUGIN_ROOT}/skills/ship/SKILL.md` § 4b for the full text (corpus health check, source-diversity bar, contradiction-with-feedback check, write format, fire-log update, audit-if-due).

Run the same sub-steps in order:
- 4b.i — `node ${CLAUDE_PLUGIN_ROOT}/tools/memory/check.mjs` (corpus health)
- 4b.ii — Apply the source-diversity bar (recurrence-likely + not mechanically checkable + 2-of-3 evidence)
- 4b.iii — Resolve contradictions with the project's feedback doc (path from `flow.config.json.feedbackPath`; user wins)
- 4b.iv — Write the entry if guardrails pass
- 4b.v — Update fire log on existing entries; flag promotion candidates to the project's roadmap
- 4b.vi — `node ${CLAUDE_PLUGIN_ROOT}/tools/memory/check.mjs --audit-due`; if exit 1, run `... --dead` and feed its output to the audit Explore agent

The bar is identical. Spike mode is **lighter on review** (skips /simplify + /flow:staff-review) but **not lighter on learning capture** — if anything, spikes are higher-yield for memory entries because the exploration surfaces failure modes feature work doesn't.

Do NOT synthesize user feedback to the feedback doc for spikes — the conversation density is different (less direction, more exploration). Spike-derived user preferences should wait until the follow-up feature PR confirms them.

### 4c. Harvest flow-generalizable lessons → contribution queue (FB-0059)

Step 4 (above) routes lessons to **this project's** surfaces (memory). Step 4c routes the *other* destination: lessons about **flow itself** (the workflow, the reviewers, the gates, transferable taste) that should become a PR back to the flow plugin. **This mirrors `/flow:ship` § 4c — same scripts, slots, and shell blocks; the consistency itself is the value** (the prose adapts for spike context, see 4c.ii). Spikes are *higher-yield* for this harvest than feature work: the agent runs with less guardrail, so gate misfires, reviewer false-positives, and taste calls the human overruled surface more often. This step is **always-run** (not gated on spike-ness — the value is workflow-type-independent); it's cheap because it reuses the same session evidence Step 4 already surfaced and only enqueues to user-scope storage that `/flow:contribute` later drains — no cross-repo action here. (Unlike the project feedback doc — which Step 4 deliberately skips for spikes because a spike's user-direction is too sparse to distill as immediate local truth — enqueuing here is safe regardless: nothing reaches flow until the human `/flow:contribute` draft-PR gate, and the queue's recurrence-counting backstops any single-source spike signal.)

**Determinism boundary:** the routing + noise judgment below are *best-effort LLM work* (like the auditor/critic), backstopped by the human at the `/flow:contribute` draft-PR gate — NOT a deterministic contract. Only the `confidence` score and the prescan gate are mechanical.

```sh
# Resolve scripts (installed plugin root, else this checkout) + the storage slots.
if [ -n "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -d "${CLAUDE_PLUGIN_ROOT}/scripts" ]; then S="${CLAUDE_PLUGIN_ROOT}/scripts"; else S="plugins/flow/scripts"; fi
# Honor contributionsQueuePath by EXPORTING FLOW_CONTRIB_DIR — the scripts read that env
# var (else the user-scope default). Without this export the slot is a no-op (the queue
# always lands in the default dir, diverging from a configured path).
QUEUE_ROOT="$(jq -r '.contributionsQueuePath // empty' flow.config.json 2>/dev/null | sed "s#^~#$HOME#")"
[ -n "$QUEUE_ROOT" ] && export FLOW_CONTRIB_DIR="$QUEUE_ROOT"
MARKER="$(jq -r '.lastHarvestedPath // empty' flow.config.json 2>/dev/null | sed "s#^~#$HOME#")"
[ -z "$MARKER" ] && MARKER="${FLOW_CONTRIB_DIR:-$HOME/.claude/plugins/data/flow/contributions}/last_harvested.json"
```

**Step 4c.i — Pre-scan cost gate (run FIRST; makes clean spikes ~free).**

```sh
python3 "$S/harvest_lesson.py" prescan --marker-file "$MARKER"   # exit 0 = signal; exit 1 = none
```

If the pre-scan exits 1 (no correction / symptom / human-overrule / endorsed-reviewer signal in the transcript since the last harvest), **STOP Step 4c here** — do not spend tokens on the analysis. Print `[analyze] pre-scan: no candidate signal — skipped` and continue to Step 5. Also skip 4c entirely on a docs-only/trivial diff (reuse the Step 1c source-file detection). Only run the analysis below when the pre-scan trips.

**Step 4c.ii — Analyze + route (only if the pre-scan tripped).**

Over the correction / overrule / preference signals present in your session context since the last harvest (the 4c.i pre-scan already confirmed at least one is there) — spike Step 4 is memory-only, so (unlike `/flow:ship`) there is no earlier 4a user-feedback candidate list to reuse; draw from session context directly and do NOT re-read the transcript — apply, in order:

1. **Noise filter (drop first).** Drop generic "just how coding works" patterns and vague observations with no actionable rule. Apply flow's single-source protection (FB-0010/FB-0056): a lone weak signal with no recurrence does not promote. Count what you drop.
2. **Destination test (per surviving finding).** *Rewrite the lesson with every project-specific noun removed. If it still states an actionable rule about how flow should review/gate/plan → **FLOW-GENERALIZABLE**. If it collapses to project trivia → **PROJECT-LOCAL** (already handled by Step 4 — no further action). If it does both → **BOTH**.*
3. **Source type** (feeds the confidence weight): a symptom/bug the human corrected → `error`/`correction`; **no symptom but the human overruled an agent proposal or stated a preference → `decision`/`taste`** (the highest-value harvest — the point of this feature). Endorsed reviewer finding → `feedback`.

For each FLOW-GENERALIZABLE / BOTH finding, enqueue it (the script captures the dialogue evidence window, records the origin project token, and dedups/recurrence-counts automatically):

```sh
python3 "$S/harvest_lesson.py" enqueue --marker-file "$MARKER" \
  --pr "<this PR url or branch>" --branch "$(git rev-parse --abbrev-ref HEAD)" \
  --source-type "taste|decision|correction|error|feedback" \
  --artifact-kind "rule-edit|reviewer-prompt|eval-fixture|new-check|fb-entry" \
  --summary "<one line>" --rule "<the synthesized, project-agnostic rule>" \
  --target-hint "<flow file/section it would touch>" \
  --evidence-strength "direct-quote|paraphrase|inferred"
```

**Step 4c.iii — Advance the watermark + report (always, even on the skip path).**

```sh
python3 "$S/harvest_lesson.py" mark --marker-file "$MARKER"
```

Print one line — `[analyze] N findings: P project-local, F flow-generalizable, D dropped (noise/low-confidence)` (or the pre-scan skip line). Never silent.

**Flow-repo nudge.** If `pwd` is the flow checkout (`flow.config.json.flowRepoPath`) and the queue is non-empty, also print `[contribute] N queued contribution(s) — run /flow:contribute to open the PR`.

## 5. Update the project's plan doc

Move the spike from "Active Work Items" to "Recently Completed" with a one-line summary including the recommendation (proceed / pivot / abandon).

If the recommendation is "proceed," **add the next-PR scope to "Active Work Items" or the project's roadmap doc** so the learning doesn't decay between sessions.

## 6. Commit

Stage code + doc updates. Commit with subject prefixed `spike:`:

```
spike: <one-line answer to the research question>

<optional body>

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```

## 7. Push and open PR

**PR-OPEN (re-ship into an existing spike PR):** push the new commits to the existing PR. If you update its body and `gh pr edit`/`gh pr ready` fails with a `GraphQL: Projects (classic) … projectCards` error (classic-projects repos on affected `gh` versions), use the **canonical `gh`-resilience fallback** — see `/flow:ship` Step 7 § "gh resilience" (REST `gh api -X PATCH …/pulls/N -F body=@file` for the body; `markPullRequestReadyForReview` / `convertPullRequestToDraft` mutations for draft state). Don't route around `gh pr` pre-emptively — only on the explicit `projectCards` error. **After any body/draft write, read-back-verify (FB-0067):** source `${CLAUDE_PLUGIN_ROOT}/skills/ship/lib/verify-pr-body.sh` and call `flow_verify_pr_write "$N" --expect "<a substring you just wrote>"` (run the write as its own checked statement first — never pipe it into a filter). A spike PR is not gated by the NOT-READY manifest, but the read-back still catches a silent write that never landed.

**LOCAL-ONLY (new spike PR):** push with `-u` if needed. PR base from the resolved default branch:

```sh
BASE=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@' || cat flow.config.json 2>/dev/null | jq -r '.defaultBranch // "main"' 2>/dev/null || echo "main")
gh pr create --base "$BASE" --label spike --title "spike: <answer>" --body "$(cat <<'EOF'
## Summary
**Scope:** spike (exploratory — code is disposable)

<1 plain-language, non-technical sentence: what this spike explored and what it
concluded, understandable at a glance without opening the diff; no internal
codenames or jargon. Additive opener — the Research question / Answer /
Recommendation detail below is kept in full, not replaced.>

## Research question
<the question>

## Answer
<short answer>

## Recommendation
proceed | pivot | abandon — <one-line reasoning>

## Disposability
<what happens to the code: deleted, flagged, gates next PR>

## Flow run
Spike mode runs a trimmed loop. Each step — ran or skipped — with any signal it
produced; `—` when routine. Resolve every `<...>` placeholder before publishing.
(Full per-step guidance: `/flow:ship` §7.)

| Step | Status | Notable |
|---|---|---|
| Clarify | ✓ | — |
| Plan (research question) | ✓ | <approach / —> |
| Execute | ✓ | <smallest thing that answered the question / —> |
| Preflight | ✓ | green / <what ran> |
| /simplify | skipped (spike) | — |
| /flow:staff-review | skipped (spike) | — |
| /flow:security-review | <✓ / skipped (reason)> | <findings / —> |
| /flow:accessibility-review | <✓ / skipped (reason)> | <findings / —> |
| /flow:verify-build | <✓ / skipped (reason)> | <3-check spike-rubric result / —> |
| /flow:audit-coverage | skipped (no Spec-walk) | — |
| /flow:audit-skips | ✓ | <all N stage skips legitimate / N should-re-run + what the user decided> |

## Full writeup
See the history doc entry "Spike: <title>".

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

**After the create, read-back-verify (FB-0067):** same rule as the PR-OPEN path above — `gh pr create` can still land a truncated or unintended body. Note the PR number `gh pr create` returns, then source `${CLAUDE_PLUGIN_ROOT}/skills/ship/lib/verify-pr-body.sh` and call `flow_verify_pr_write "$N" --expect "<a stable substring from the body just written>"` before handing off. A spike PR isn't gated by the NOT-READY manifest, so no `--want-draft`/`--forbid` assertion is needed here — the read-back exists purely to confirm the create wasn't silently truncated.

`/simplify` and `/flow:staff-review` are pre-marked `skipped (spike)` — spike mode
always skips them (workflow.md § Spike mode), and they are the *only* two rows that
may be pre-marked, because they are the only two the disposability rationale reaches.
`/flow:audit-coverage` is pre-marked `skipped (no Spec-walk)` for the structural reason
in Step 2.1 — if the spike's plan *does* carry an active Spec-walk block, the Step 2a
audit will have made you run it, so fill the row from what happened. Fill
`/flow:security-review` and `/flow:accessibility-review` from their Step 2.1 invocations
(each self-skips with its own reason). Fill `/flow:verify-build` from the
Step 2.2 spike-mode invocation: `✓` with the 3-check rubric result if it ran, or
`skipped (verifyEnabled:false)` / `skipped (platform library|none)` / `skipped (toolchain absent)` if it didn't.
`/flow:audit-skips` **always ran** — it audits the others' skips, so it never skips
itself; if it could not run, that is a halt at Step 2a.3, not a row you fill in with an
excuse. **Notable** is genuine signal only — don't manufacture notes for a spike.

The PR title MUST start with `spike:` and the PR MUST have the `spike` label. Both are spike-mode-abuse guards: a feature accidentally shipped through `/flow:ship-spike` should be visually obvious and easy to reject.

## 8. Hand off

Output the PR URL and the recommendation (proceed / pivot / abandon). The user merges or closes.

**Do not merge. Do not approve.** The user handles merging.

## Gotchas

- **Spike PRs that grew into features.** If during execution you realize the work is no longer answering a question but building a feature, **stop and rewrite the plan as `mode: feature`**. Do not try to ship a feature through this skill — the heavy reviews exist for a reason. The user can redirect.
- **Spike code that's being kept** (behind a flag, gating next PR): the disposability statement matters. "Kept behind a flag" means the next PR has to either polish it or remove it — file a roadmap entry naming which.
- **Don't write to the feedback doc.** That's `/flow:ship` (feature mode). Spikes are too sparse on user direction to distill reliably.

## Config slots used

| Slot | Default | Used in |
|---|---|---|
| `flow.config.json.defaultBranch` | `git symbolic-ref` → `main` | Step 1 (pre-flight), Step 1c (docs-only diff base), Step 7 (PR base) |
| `flow.config.json.preflightCmd` | unset → loud warning | Step 1c (bounded-retry mechanical preflight, N≤3) |
| `flow.config.json.sourceFilePatterns` | covers common source/config extensions | Step 1c (docs-only early-exit) |
| `flow.config.json.typecheckCmd` | unset → loud warning | Step 2 (post-1c one-shot typecheck) |
| `flow.config.json.uiSurface` | `true` | Step 2.1 (`/flow:accessibility-review` self-skip) + Step 2a (audit of that skip) |
| `flow.config.json.planPath` | `dev-docs/plan.md` | Step 2a (the audit checks the `audit-coverage` `no Spec-walk` claim against the plan, and reads its declared **Mode** as evidence for the spike rows) |
| `flow.config.json.historyPath` | `dev-docs/history.md` | Step 3 (spike entry — THE deliverable) |
| `flow.config.json.planPath` | `dev-docs/plan.md` | Step 5 (move to Recently Completed) |
| `flow.config.json.feedbackPath` | `dev-docs/feedback.md` | Step 4 (contradiction check; not written to) |
| `flow.config.json.roadmapPath` | `dev-docs/roadmap.md` | Step 5 (next-PR scope if proceed) |
| `flow.config.json.lastHarvestedPath` | `~/.claude/plugins/data/flow/contributions/last_harvested.json` | Step 4c (lesson-harvest watermark; only new transcript since last harvest is analyzed) |
| `flow.config.json.contributionsQueuePath` | `~/.claude/plugins/data/flow/contributions` | Step 4c (enqueue target) + `/flow:contribute` (drain source) |
| `flow.config.json.flowRepoPath` | unset → `/flow:contribute` disabled | Step 4c (flow-repo nudge) + `/flow:contribute` (run-from guard + PR target) |
