---
name: review-brief
description: >
  Pre-prototype review of a design brief (D1 Phase 1, FB-0081 step 3): one
  extraction of the brief + reference docs, fanned to auditor + plan-critic
  + the experience/ambition lens in a single tool message, returning one
  triaged verdict. BLOCKER / decision-required findings route to a human
  question, never a document to read; a clean pass proceeds to the
  prototype phase. Pass a brief-file path argument
  (/flow:review-brief path/to/brief.md) to review a queued brief document;
  without one, reviews the session's most recent design-brief-shaped plan.
disable-model-invocation: false
allowed-tools: Read, Bash, Agent
---

# Task: Review this design brief before anything gets built

D1's loop (`dev-docs/handoffs/d1-prototype-first-gate.md`, FB-0081) moves a UI change's first human gate from the plan to the prototype — but before any prototype work starts, the brief that motivates it gets one review pass. This skill is that pass: `auditor` (assumptions invented rather than asked), `plan-critic` (scope drift, spec violation, incoherence vs. the reference docs — including *absent elements the user explicitly requested*), and `lens-experience` (is this the right problem, is the ambition high enough) all `Read` the **same extracted scratch file**, spawned together, and you return one triaged verdict.

**This is not gate machinery.** There is no draft-PR manifest at this stage — no PR exists yet. A `decision-required` finding becomes an answerable question in your reply, not a routed artifact.

**Not a `context: fork` skill.** Unlike `/flow:critique-plan` (which forks straight into `plan-critic`), this skill fans out to *three* parallel `Agent` calls from the live conversation — a single-agent fork is structurally incompatible with that. That means its config reads follow the **blocking**, not fork-routed, jq-absence shape (jq-absence-handling-2026-06): a real `command -v jq` check that exits non-zero, run explicitly via the `Bash` tool as Step 0 below — not an auto-injected `!`-context span, which can't abort a non-forked skill's turn.

## 0. External CLI dependency check (BLOCKING for jq)

`jq` scopes `referenceGlob` (Step 1's reference-doc set). Run this via the `Bash` tool before anything else:

```sh
MISSING=""
command -v jq >/dev/null 2>&1 || MISSING="$MISSING jq"
if [ -n "$MISSING" ]; then
  MISSING_TRIMMED=$(echo "$MISSING" | sed 's/^ //')
  echo "⚠️ BLOCKER: /flow:review-brief requires $MISSING_TRIMMED (missing on PATH) — jq scopes the reference-doc glob; degrading to a hardcoded default would review the brief against the wrong reference set and silently mis-scope spec violations." >&2
  echo "   Install: brew install$MISSING (macOS) | apt install$MISSING (Debian/Ubuntu) | https://jqlang.org (jq)" >&2
  exit 1
fi
```

(This carries the same `MISSING=""` accumulator shape `/flow:ship`/`/flow:staff-review` use for their multi-tool checks, even though this skill only ever checks one tool — kept for consistency with the canonical BLOCKING policy shape `run_jq_guard_evals.py` mechanically extracts and executes, not for its own sake.)

If this exits non-zero, stop — report the message to the user and do not proceed to Step 1. Do not degrade to a hardcoded `referenceGlob` default; that is exactly the silent-wrong-config failure mode this check exists to prevent.

## 1. Extract the brief + reference docs, stamp it to repo-local scratch — one extraction, reused verbatim by every reviewer

Invoked with an argument (`/flow:review-brief <path>`), this reviews that brief **document** — it renders under the heading `## Plan under review (from file: <path>)` (the extractor's plan-file mode is deliberately generic; a design brief is reviewed the same way a queued plan document is). Without an argument, the extractor looks for the session's most recent plan-shaped assistant turn — D1's Step 2 (writing the brief) is not wired into the live loop yet (that's Phase 2), so this path is best-effort until then; a brief that doesn't start with a recognizable plan heading may not be found, and the output below will say so rather than silently reviewing the wrong thing.

Run this via the `Bash` tool (same ROOT-anchor rationale as `critique-plan/SKILL.md`: a spec/design-language violation cannot be flagged without quoting the reference doc it violates, and this skill has no reliable inherited cwd). It also writes the extracted context to **repo-local `.flow/` scratch**, stamped with workspace identity — the same idiom `/flow:staff-review` uses for its diff file (FB-0082), for the same reason: three reviewers reading one file, not one copy-pasted into three prompts, is what makes "all three reviewed the same artifact" verifiable rather than merely asserted, and the stamp lets a reviewer detect a stale or foreign scratch file instead of silently reviewing the wrong brief.

```sh
ROOT=$(git rev-parse --show-toplevel 2>/dev/null)
{ [ -n "$ROOT" ] && [ -d "$ROOT" ]; } || ROOT="${CLAUDE_PROJECT_DIR:-}"
if [ -z "$ROOT" ] || ! cd "$ROOT" 2>/dev/null; then
  echo "[review-brief] ROOT-UNRESOLVED — the repo under review could not be located from cwd $(pwd); no reference documents were loaded, so spec violations CANNOT be judged. This is not a clean pass. Re-run from the repo root, or set CLAUDE_PROJECT_DIR to the repo."
  exit 0
fi
REFGLOB=$(cat flow.config.json 2>/dev/null | jq -r '.referenceGlob // empty' 2>/dev/null); [ -z "$REFGLOB" ] && REFGLOB="core-docs/*.md"
# Repo-local scratch (FB-0082) — same idiom as staff-review/SKILL.md, kept in sync with
# scripts/flow_scratch.py; pinned by evals/run_scratch_isolation_evals.py.
FLOW_SCRATCH="$ROOT/.flow"
if [ -L "$FLOW_SCRATCH" ]; then
  echo "⚠️ BLOCKER: $FLOW_SCRATCH is a symlink — refusing to write flow scratch through it (CWE-59)." >&2
  exit 1
fi
mkdir -p "$FLOW_SCRATCH"
[ -f "$FLOW_SCRATCH/.gitignore" ] || printf '# Created by flow. Ephemeral scratch; never committed.\n*\n' > "$FLOW_SCRATCH/.gitignore"
FLOW_BR=$(git branch --show-current 2>/dev/null); FLOW_HEAD=$(git rev-parse --short HEAD 2>/dev/null)
{
  printf '# flow-review-context repo=%s branch=%s head=%s\n' "$ROOT" "$FLOW_BR" "$FLOW_HEAD"
  if [ -n "$ARGUMENTS" ]; then python3 ${CLAUDE_PLUGIN_ROOT}/scripts/extract_session.py --mode plan --plan-file "$ARGUMENTS" --reference-glob "$REFGLOB"; else python3 ${CLAUDE_PLUGIN_ROOT}/scripts/extract_session.py --mode plan --reference-glob "$REFGLOB"; fi
} > "$FLOW_SCRATCH/review-brief-context.txt"
echo "Context written to $FLOW_SCRATCH/review-brief-context.txt (repo=$ROOT branch=$FLOW_BR head=$FLOW_HEAD)"
```

If this prints `ROOT-UNRESOLVED`, **stop** — report the message and do not proceed to Step 2; no reference documents were loaded and no scratch file was written, so a review from here would judge nothing. Otherwise, note the printed `repo=`/`branch=`/`head=` values — you'll pass them to each reviewer below as **Workspace identity**.

## 2. Fan out — three reviewers, one tool message

Spawn all three in a **single tool message** with the `Agent` tool. Each gets the **absolute path** to `$FLOW_SCRATCH/review-brief-context.txt` from Step 1 and the **Workspace identity** line (`repo=… branch=… head=…`) printed there — never a literal `/tmp` guess. Each reviewer is instructed to `Read` that path and, if the file's own header disagrees with the Workspace identity it was given, **stop and say so** rather than reviewing a stale or foreign brief (FB-0082):

| Reviewer | `subagent_type` | Checks |
|---|---|---|
| Auditor | `flow:auditor` | Unverified assumption, unverified recall (plan-audit categories only — see `audit-plan/SKILL.md` for the same scoping) |
| Plan-critic | `flow:plan-critic` | Scope drift (incl. absent elements the user explicitly requested), spec violation vs. the loaded reference docs, internal incoherence |
| Experience lens | `flow:lens-experience` | Right problem / ambition ceiling / experience gaps, plus push-further-on-quality with its anti-scope-creep guard |

Each `Agent` call's prompt: "Task: [audit / critique / lens-review] this design brief. [reviewer-specific scoping from the table above.] Read `<absolute path to review-brief-context.txt>` — that is the brief plus any reference docs. Workspace identity: repo=… branch=… head=… — if the file's own header disagrees, stop and say so instead of reviewing it."

## 3. Triage

Map every reviewer's output onto one of two outcomes — there is no `[auto-fixable]` tier at this stage (nothing is mechanically fixable pre-prototype; the artifact is prose, not code):

- **decision-required** — any of: an auditor `ISSUE` (any category); a plan-critic `ISSUE` at `BLOCKER` or `REDIRECT`; a lens-experience Lens-A finding at `BLOCKER` or `REDIRECT`.
- **captured, non-blocking** — plan-critic `FOLLOW-UP`; any lens-experience Lens-B (push-further) finding, regardless of bucket (push-further is generative by design and never blocks — see `lens-push-further`'s own restraint-first framing, which this lens inherits).

Default to **decision-required** when a finding's tier is ambiguous — over-escalating costs the human a moment's attention; silently proceeding on a brief that solves the wrong problem costs a discarded prototype.

## 4. Resolve

- **All three reviewers clean** (`No issues flagged.` / `APPROVED` / `Ambition bar met.` + `Nothing to push...`): say so plainly and state `Brief cleared pre-prototype review — proceed to the prototype phase.` (D1 Phase 2 is not yet built in this repo; note that explicitly rather than implying a next skill exists.)
- **Any decision-required finding(s):** render as a **numbered, answerable question list** — never as "see the findings above" or a document to go read (FB-0075's shape; mirrors how `/flow:ship` Step 8 hands off open decisions). One question per finding, each with: the reviewer + category, a one-line restatement of the conflict, and what a yes/no or short answer would resolve. Do not proceed to a proceed-recommendation while any decision-required item is open.
- **Non-blocking findings** (FOLLOW-UP / push-further): list them separately, clearly labeled as non-blocking, so they aren't lost — but they never gate the "proceed" verdict.

## Output format

```
BRIEF REVIEW
Auditor: [No issues flagged. | N issues]
Plan-critic: [APPROVED | N findings]
Experience lens: [Ambition bar met. + Nothing to push... | N findings]

[if any decision-required:]
DECISIONS NEEDED (answer to proceed)
1. [reviewer/category] — [conflict, one line] — [what would resolve it]
2. ...

[if any non-blocking:]
NON-BLOCKING (captured, not gating)
- [reviewer/category] — [one line]

VERDICT: [proceed to the prototype phase — not yet built, D1 Phase 2 | blocked on N decision(s) above]
```

## Gotchas

- **Don't paraphrase a reviewer's finding when triaging it.** Quote enough of the original `ISSUE`/finding that the human can tell the question is grounded in something specific, not your summary of it.
- **A brief with zero findings across all three is a legitimate, common outcome** for a well-scoped small change — don't manufacture a decision to look thorough.
- **This skill never fixes the brief itself.** It reviews and triages; revising the brief in response to a decision is a separate turn, same as how `/flow:critique-plan` never edits the plan it critiques.
- **Don't invoke the prototype phase.** It doesn't exist yet in this repo (D1 Phase 2). Say so plainly rather than gesturing at a next step that isn't shipped.
