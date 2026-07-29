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
# /flow:ship writes the per-stage report to this temp handoff before invoking the
# skill (ephemeral, like the verify-build findings buffer). Standalone invocation
# without the handoff still emits the context block, with an empty stage set.
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
SKIP-AUDIT SUMMARY
- <stage>: <LEGITIMATE | SHOULD-RE-RUN> — <one-line reason>[ · auto-resolvable: re-run | decision-required]
- ...
RESOLUTION: <all N stage skips LEGITIMATE — proceed | M SHOULD-RE-RUN (A auto-resolvable, D decision-required)>
```

When every stage is LEGITIMATE, the body lists each stage and the `RESOLUTION:` line
reads `all N stage skips LEGITIMATE — proceed`. When ≥1 stage is SHOULD-RE-RUN, the
`RESOLUTION:` line names how many are auto-resolvable (re-run + re-audit once) vs
decision-required (→ draft manifest). Do not explain your process.
