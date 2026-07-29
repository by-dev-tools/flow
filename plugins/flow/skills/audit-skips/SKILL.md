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
# the same failure-open this guard exists to close. A git rev-parse --show-toplevel returns
# (NOTE: no backticks anywhere in this block -- it lives inside a single-backtick dynamic-
# context span, so ONE inner backtick truncates the span and everything after it is emitted
# as literal text instead of being executed. FB-0010; the same warning is repeated below.)
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
# ...and the handoff itself must be REPO-LOCAL, not /tmp (FB-0075). The root anchor above
# fixes which tree we read; it does not make a /tmp file visible. A forked skill cannot see
# a /tmp file the parent shell wrote at all -- reproduced as a same-file A/B (full report
# from the parent, "no stage report" from the fork) -- so through v1.22.0 this gate still
# no-opped on every ship even with the anchor. Repo-local is visible to both AND per-worktree
# by construction, which also ends the cross-project clobbering of the global /tmp namespace.
# Relative default resolves against $ROOT because of the cd above.
STAGES="${FLOW_SKIP_AUDIT_STAGES:-.flow/skip-audit-stages.json}"
if [ -n "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -f "${CLAUDE_PLUGIN_ROOT}/skills/audit-skips/lib/skip-audit-checks.py" ]; then
  H="${CLAUDE_PLUGIN_ROOT}/skills/audit-skips/lib/skip-audit-checks.py"
else
  H="plugins/flow/skills/audit-skips/lib/skip-audit-checks.py"
fi
PLAN=$(jq -r '.planPath // empty' flow.config.json 2>/dev/null); [ -z "$PLAN" ] && PLAN="dev-docs/plan.md"
# Stamp gate (FB-0075). A handoff must PROVE it belongs to this repo+branch+HEAD before
# it is audited. Namespacing alone is not enough: two worktrees of one repo share a repo
# path, and a handoff left by an earlier branch in THIS worktree is still readable. A
# mismatch is refused loudly rather than read-and-hope -- and is kept DISTINCT from the
# absent case, because collapsing the two is exactly how a foreign buffer reads as
# "nothing to do". An UNSTAMPED handoff is refused too (fail closed -- FB-0062).
if [ -n "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -f "${CLAUDE_PLUGIN_ROOT}/scripts/flow_scratch.py" ]; then
  SCRATCH_PY="${CLAUDE_PLUGIN_ROOT}/scripts/flow_scratch.py"
else
  SCRATCH_PY="plugins/flow/scripts/flow_scratch.py"
fi
STAMP_STATUS=""; STAMP_REASON=""
if [ -f "$STAGES" ]; then
  if [ ! -f "$SCRATCH_PY" ]; then
    # The gate CANNOT fail open. If the checker is unreachable we cannot prove the
    # handoff is ours, and "cannot prove" must never read as "verified" -- that is
    # the exact failure this whole branch exists to remove.
    STAMP_STATUS="unverifiable"
    STAMP_REASON="stamp checker not reachable at $SCRATCH_PY -- cannot prove this handoff belongs to this workspace"
  else
    STAMP_JSON=$(python3 "$SCRATCH_PY" check "$STAGES" 2>/dev/null)
    STAMP_STATUS=$(printf '%s' "$STAMP_JSON" | jq -r '.status // empty' 2>/dev/null)
    STAMP_REASON=$(printf '%s' "$STAMP_JSON" | jq -r '.reason // empty' 2>/dev/null)
    # An empty status means python3/jq failed, not that the stamp passed.
    if [ -z "$STAMP_STATUS" ]; then
      STAMP_STATUS="unverifiable"
      STAMP_REASON="stamp check produced no verdict (python3 or jq unavailable) -- cannot prove this handoff belongs to this workspace"
    fi
  fi
fi
if [ -f "$STAGES" ] && [ "$STAMP_STATUS" != "ok" ] && [ -n "$STAMP_STATUS" ]; then
  # Present but NOT ours. Never audit it, never call it a clean standalone no-op.
  printf '{"stamp_error": %s, "handoff": %s, "stages": []}\n' \
    "$(printf '%s' "$STAMP_REASON" | jq -Rs . 2>/dev/null || printf '"handoff stamp did not match this workspace"')" \
    "$(printf '%s' "$STAGES" | jq -Rs . 2>/dev/null || printf '"(handoff path; jq unavailable)"')"
elif [ -f "$STAGES" ]; then
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
  /flow:ship Step 2).` and stop. This is the clean no-op — and since FB-0075 it is once again
  a *trustworthy* one: the handoff is written to a **repo-local** `.flow/` path both the parent
  and this fork can see, so an absent handoff now really does mean none was written. It did not
  mean that before FB-0075, when the handoff lived in `/tmp` and was structurally invisible to a
  forked skill — this note fired on **every** ship from v1.13.0 to v1.22.0, and the whole gate
  no-opped silently behind it. If you ever see this note on a run launched from `/flow:ship`
  Step 2a (which always writes a handoff), the transport is broken again: treat it as a
  `stamp_error`, not a pass, and say so.
- If the mechanical block carries **`"root_error"`** (FB-0074 — the skill could not locate the
  repo under review from its inherited cwd), do **NOT** treat it as "nothing to audit". Nothing
  was read: `flow.config.json` resolved empty, every `git` call returned empty, and *every*
  unverifiable skip would otherwise validate as LEGITIMATE — a false clean pass produced by
  looking at the wrong place, which is strictly worse than an engine crash because it emits a
  confident verdict. Output a loud diagnostic and stop:
  `⚠️ SKIP-AUDIT ROOT-UNRESOLVED (<root_error>). The skip-legitimacy gate did NOT run — this
  is not a clean pass.` Route it exactly like `engine_error` below: from `/flow:ship` Step 2a
  it becomes a `[decision-required]` draft-manifest entry, never a silent proceed.
- If the mechanical block carries **`"stamp_error"`** (a handoff WAS present but its
  `flow_stamp` does not match this repo/branch/HEAD, or it carries none at all), do **NOT**
  audit it and do **NOT** report a clean standalone no-op — you are looking at another
  workspace's handoff, or a stale one from an earlier branch. Output a loud diagnostic and stop:
  `⚠️ SKIP-AUDIT REFUSED a handoff that does not belong to this workspace (<handoff>):
  <stamp_error>. The skip-legitimacy gate did NOT run — this is not a clean pass.` From
  `/flow:ship` Step 2a this routes to the draft manifest as `[decision-required]`
  (`[skip-audit] handoff failed its stamp check — re-run ship Step 2a.1 or human-waive`).
- If the mechanical block carries **`"engine_error"`** (the handoff file WAS present but
  `skip-audit-checks.py` failed on it — the engine exits non-zero on a malformed/unreadable
  report rather than collapsing to `stages:[]`), do **NOT** treat it as "nothing to audit" —
  the gate did not execute. Output a loud diagnostic and stop:
  `⚠️ SKIP-AUDIT ENGINE FAILED on a present handoff (<handoff>): <engine_error>. The
  skip-legitimacy gate did NOT run — this is not a clean pass.` When invoked from `/flow:ship`
  Step 2a this routes to the draft manifest as `[decision-required]` (`[skip-audit] engine
  failed on a present handoff — fix the engine input or human-waive`), never a silent proceed.
- A present, VALID handoff with genuinely zero skipped stages (`{"stages": []}` from a real
  report — no `note`, `engine_error` or `stamp_error`, engine exit 0) is an honest empty audit: nothing
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
