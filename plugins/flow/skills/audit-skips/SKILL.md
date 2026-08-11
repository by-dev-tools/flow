---
name: audit-skips
description: >
  Audit every /flow:ship stage skip (and silent self-certified short-circuit) for
  legitimacy. No stage skip is accepted on its own say-so, and "the agent did it
  manually" never substitutes for a stage's real pipeline output. For each stage
  (/simplify, staff-review, security, a11y, verify-build, audit-coverage, and the
  visual-verification/Present step) it classifies LEGITIMATE (skip reason verified
  against ground truth) or SHOULD-RE-RUN (reason contradicted by the diff/config,
  OR the stage claims it ran but its canonical OUTPUT ARTIFACT is absent/stale for
  HEAD — verdict-without-artifact == skip). Runs in /flow:ship Step 2 AFTER the
  four reviewers report and BEFORE Step 3; a SHOULD-RE-RUN that can't be cheaply
  re-run routes to the draft manifest (decision-required). Skeptical, fresh-context,
  read-only — it never fixes. Invocable directly (/flow:audit-skips) or by /flow:ship.
disable-model-invocation: false
context: fork
agent: skip-auditor
---

# Task: Audit this ship's stage skips for legitimacy

You are a skeptical, read-only auditor. Your one job: decide, **per stage**, whether
a skip (or a "ran" claim) is honest against ground truth. You **never fix** anything
and you **never re-run** a stage — you classify; `/flow:ship` does the routing.

The load-bearing rule: **a stage's claimed verdict is trusted only if its canonical
artifact EXISTS and matches HEAD.** A PASS with no fresh findings buffer is the
"agent confirmed manually + self-certified" failure — the missing artifact is the
tell. Verdict-without-artifact == skip.

## Mechanical ground truth (authoritative — trust these verdicts verbatim)

The deterministic engine below has already cross-checked each reported stage status
against the config, the diff, and the canonical artifact's existence + freshness.
**Treat its `mechanical` field as authoritative** for every stage it returns
`LEGITIMATE` or `SHOULD-RE-RUN`. Apply your own judgment ONLY to stages it marks
`NEEDS-JUDGMENT` (a mode-declared spike/tiny skip, an unrecognized skip reason).

!`
# Root anchor (FB-0074) — MUST precede every relative read below (the engine fallback path,
# flow.config.json, and the diff block). A fork inherits the SESSION cwd, not necessarily the
# repo under review: from a non-repo cwd every relative read silently yields empty, and every
# unverifiable skip then validates as LEGITIMATE -- a false clean pass on a gate whose whole
# job is to refuse those. Emit a routable root_error instead, never the standalone note.
# Precedence is cwd-git-root FIRST, env second (FB-0074). Env-first looks safer but
# BREAKS git worktrees: a session started in the parent repo exports a CLAUDE_PROJECT_DIR
# pointing there, while the work (and the PR) lives in a linked worktree on a different
# branch -- so env-first would audit the parent tree and see none of the changes, which is
# the same failure-open this guard exists to close. `git rev-parse --show-toplevel` returns
# the WORKTREE root, which is always the tree under review when cwd is inside a repo.
ROOT=$(git rev-parse --show-toplevel 2>/dev/null)
{ [ -n "$ROOT" ] && [ -d "$ROOT" ]; } || ROOT="${CLAUDE_PROJECT_DIR:-}"
if [ -z "$ROOT" ] || ! cd "$ROOT" 2>/dev/null; then
  printf '{"root_error": "no git toplevel from this cwd and no CLAUDE_PROJECT_DIR; config and diff were NOT read. Re-run from the repo root, or set CLAUDE_PROJECT_DIR to the repo", "stages": []}\n'
  exit 0
fi
# /flow:ship writes the per-stage report to this temp handoff before invoking the skill
# (ephemeral, like the verify-build findings buffer); a standalone invocation without it
# still emits the context block, with an empty stage set. Resolved AFTER the cd above, so
# a relative FLOW_SKIP_AUDIT_STAGES override resolves against the repo root rather than
# whatever cwd the fork inherited (which the cd just left).
STAGES="${FLOW_SKIP_AUDIT_STAGES:-/tmp/flow-skip-audit-stages.json}"
if [ -n "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -f "${CLAUDE_PLUGIN_ROOT}/skills/audit-skips/lib/skip-audit-checks.py" ]; then
  H="${CLAUDE_PLUGIN_ROOT}/skills/audit-skips/lib/skip-audit-checks.py"
else
  H="plugins/flow/skills/audit-skips/lib/skip-audit-checks.py"
fi
PLAN=$(jq -r '.planPath // empty' flow.config.json 2>/dev/null); [ -z "$PLAN" ] && PLAN="dev-docs/plan.md"
if [ -f "$STAGES" ]; then
  PLAN_ARG=""; [ -f "$PLAN" ] && PLAN_ARG="--plan $PLAN"
  # Capture stderr (do NOT 2>/dev/null it away) so an engine failure on a PRESENT handoff is
  # diagnosable. Distinguish that failure from the absent-handoff no-op below via a dedicated
  # engine_error field: a present-but-unreadable handoff is NOT "nothing to audit" -- the
  # skip-legitimacy gate did not run, and collapsing it to the standalone message is the silent
  # no-op this branch exists to prevent. (No backticks in this block -- it runs inside a
  # single-backtick dynamic-context span; an inner backtick would truncate it. FB-0010.)
  ENGINE_ERR=$(mktemp)
  if OUT=$(python3 "$H" --report "$STAGES" --config flow.config.json $PLAN_ARG 2>"$ENGINE_ERR"); then
    printf '%s\n' "$OUT"
  else
    # Both interpolations go through jq -Rs . (sound JSON-string escaping). The || branches only
    # fire if jq is missing (it's a declared pipeline prerequisite) and emit a SAFE CONSTANT
    # string, never a raw-interpolated value -- so the output stays valid JSON even then.
    printf '{"engine_error": %s, "handoff": %s, "stages": []}\n' \
      "$(jq -Rs . < "$ENGINE_ERR" 2>/dev/null || printf '"skip-audit-checks.py failed (jq unavailable)"')" \
      "$(printf '%s' "$STAGES" | jq -Rs . 2>/dev/null || printf '"(handoff path; jq unavailable)"')"
  fi
  rm -f "$ENGINE_ERR"
else
  echo '{"note":"no stages handoff at '"$STAGES"' — /flow:ship writes it at Step 2. Standalone run: nothing to audit.","stages":[]}'
fi
`

## Workspace diff — what was actually built (corroboration only)

!`
# Root anchor (FB-0074) — see the mechanical block above.
ROOT=$(git rev-parse --show-toplevel 2>/dev/null)
{ [ -n "$ROOT" ] && [ -d "$ROOT" ]; } || ROOT="${CLAUDE_PROJECT_DIR:-}"
if [ -z "$ROOT" ] || ! cd "$ROOT" 2>/dev/null; then
  echo "[audit-skips] ROOT-UNRESOLVED — the repo under review could not be located from cwd $(pwd); no diff was read. Re-run from the repo root, or set CLAUDE_PROJECT_DIR to the repo."
  exit 0
fi
# Newline-strip the path before echoing: this block's stdout IS prompt context,
# so a directory name containing a newline could inject a fake verdict line.
printf '[audit-skips] repo root: %s\n' "$(printf '%s' "$ROOT" | tr -d '\n\r')"
BASE=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@')
[ -z "$BASE" ] && BASE=$(jq -r '.defaultBranch // "main"' flow.config.json 2>/dev/null)
[ -z "$BASE" ] && BASE=main
{ git diff "origin/$BASE..HEAD" --name-status 2>/dev/null; git diff HEAD --name-status 2>/dev/null; git ls-files --others --exclude-standard 2>/dev/null | sed 's/^/?\t/'; } | sort -u | head -200
`

## What to check

- The mechanical block above is the **source of truth**. Echo its `LEGITIMATE` /
  `SHOULD-RE-RUN` verdicts faithfully — do **not** soften a `SHOULD-RE-RUN` into
  "probably fine," and do **not** invent a `SHOULD-RE-RUN` the engine didn't find.
- For each stage the engine marked **`NEEDS-JUDGMENT`**, decide LEGITIMATE vs
  SHOULD-RE-RUN yourself, using the diff above + the plan's declared mode:
  - A `/simplify` / `staff-review` skip tagged spike/tiny is **LEGITIMATE** only if
    the plan actually declares that mode; otherwise the reviews were owed →
    SHOULD-RE-RUN.
  - An unrecognized skip reason that the diff/config plainly contradicts →
    SHOULD-RE-RUN; one you cannot refute → LEGITIMATE (default to trusting a skip
    you have no evidence against — do not manufacture findings).
- If the mechanical block is `{"note": ..., "stages": []}` (the handoff file was **absent** —
  a standalone run), output exactly `SKIP-AUDIT: no stage report to audit (run from
  /flow:ship Step 2).` and stop. This is the clean no-op — **unless** this skill was **forked**
  and the parent DID write a handoff to a `/tmp` path the fork's filesystem can't see (so
  `[ -f "$STAGES" ]` reads false even though a handoff exists): then this "absent" note is a
  false no-op, not a clean pass. When run from `/flow:ship` a handoff is always written at 2a.1,
  so a `note` there means the fork couldn't see it — set `FLOW_SKIP_AUDIT_STAGES` to a shared
  path, or route it like an `engine_error` below. (The systemic fork-handoff-transport fix is
  tracked in `roadmap.md` § Exploration.)
- If the mechanical block carries **`"root_error"`** (FB-0074 — the skill could not locate the
  repo under review from its inherited cwd), do **NOT** treat it as "nothing to audit". Nothing
  was read: `flow.config.json` resolved empty, every `git` call returned empty, and *every*
  unverifiable skip would otherwise validate as LEGITIMATE — a false clean pass produced by
  looking at the wrong place, which is strictly worse than an engine crash because it emits a
  confident verdict. Output a loud diagnostic and stop:
  `⚠️ SKIP-AUDIT ROOT-UNRESOLVED (<root_error>). The skip-legitimacy gate did NOT run — this
  is not a clean pass.` Route it exactly like `engine_error` below: from `/flow:ship` Step 2a
  it becomes a `[decision-required]` draft-manifest entry, never a silent proceed.
- If the mechanical block carries **`"engine_error"`** (the handoff file WAS present but
  `skip-audit-checks.py` failed on it — the engine exits non-zero on a malformed/unreadable
  report rather than collapsing to `stages:[]`), do **NOT** treat it as "nothing to audit" —
  the gate did not execute. Output a loud diagnostic and stop:
  `⚠️ SKIP-AUDIT ENGINE FAILED on a present handoff (<handoff>): <engine_error>. The
  skip-legitimacy gate did NOT run — this is not a clean pass.` When invoked from `/flow:ship`
  Step 2a this routes to the draft manifest as `[decision-required]` (`[skip-audit] engine
  failed on a present handoff — fix the engine input or human-waive`), never a silent proceed.
- A present, VALID handoff with genuinely zero skipped stages (`{"stages": []}` from a real
  report — neither `note` nor `engine_error`, engine exit 0) is an honest empty audit: nothing
  was skipped, so there is nothing to re-run. Proceed with `SKIP-AUDIT: all stage skips
  legitimate (0 skips)`. Do not treat the empty stage set as anomalous — only the `note`
  (absent) and `engine_error` (present-but-failed) shapes above are special.
- **`auto_resolvable`** on a SHOULD-RE-RUN means `/flow:ship` can cheaply re-invoke
  the stage now and re-audit once. `auto_resolvable: false` (e.g. a missing
  visual-history entry, a visual-deliverable gap) means it must route to the draft
  manifest as `[decision-required]` — name it so.

**Known asymmetry (intentional, not a gap).** The "verdict-without-artifact == skip"
rule only fires for stages that emit a canonical per-HEAD artifact — verify-build (the
findings buffer) and staff-review (the rigor marker). `security` / `accessibility` /
`audit-coverage` emit **no** machine artifact, so a bare "ran" claim from them has
nothing to cross-check and is trusted as `LEGITIMATE`. Giving every reviewer a freshness
breadcrumb so its "ran" claim becomes mechanically checkable is a tracked roadmap § Next
exploration — until then, this asymmetry is by design, not a silent hole.

A result where every stage is LEGITIMATE is the correct, common outcome on a clean
PR. Do not invent findings to appear thorough.

## Output

Produce EXACTLY this shape (no prose before or after):

```
[⚠️ PATTERN-WARNING: <warning>]        ← only when context.pattern_warnings is non-empty
SKIP-AUDIT SUMMARY
- <stage>: <LEGITIMATE | SHOULD-RE-RUN> — <one-line reason>[ · auto-resolvable: re-run | decision-required]
- ...
RESOLUTION: <all N stage skips LEGITIMATE — proceed | M SHOULD-RE-RUN (A auto-resolvable, D decision-required)>
```

**`PATTERN-WARNING` (FB-0079).** If `context.pattern_warnings` is non-empty, emit one
`⚠️ PATTERN-WARNING: <warning>` line per entry ABOVE the summary. The engine resolves each
reviewer's file pattern through `visualFilePatterns`/`a11yFilePatterns` → `uiFilePatterns` →
built-in default; an unusable pattern degrades to the default and records the warning there.
Unlike `root_error`/`engine_error`, this is a **degraded measurement, not an absent one** — the
verdicts below are still produced and still meaningful, but they were measured with the built-in
pattern rather than the project's own. Say so rather than reporting a confident verdict whose
ruler silently changed. This is the one exception to "no prose before or after".

When every stage is LEGITIMATE, the body lists each stage and the `RESOLUTION:` line
reads `all N stage skips LEGITIMATE — proceed`. When ≥1 stage is SHOULD-RE-RUN, the
`RESOLUTION:` line names how many are auto-resolvable (re-run + re-audit once) vs
decision-required (→ draft manifest). Do not explain your process.
