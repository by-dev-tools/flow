---
name: audit-skips
description: >
  Audit every /flow:ship and /flow:ship-spike stage skip (and silent self-certified
  short-circuit) for legitimacy. No stage skip is accepted on its own say-so, and
  "the agent did it manually" never substitutes for a stage's real pipeline output.
  For each stage (preflight, /simplify, staff-review, security, a11y, verify-build,
  audit-coverage, and the visual-verification/Present step) it classifies LEGITIMATE
  (skip reason verified against ground truth) or SHOULD-RE-RUN (reason contradicted
  by the diff/config, OR the stage claims it ran but its canonical OUTPUT ARTIFACT
  is absent/stale for HEAD — verdict-without-artifact == skip). Runs in /flow:ship
  Step 2a AFTER the four reviewers report and BEFORE Step 3, and in /flow:ship-spike
  Step 2a — spike mode produces the most skips, so it is the path that most needs
  this gate. On the ship path a SHOULD-RE-RUN that can't be cheaply re-run routes to
  the draft manifest (decision-required); spike PRs have no manifest, so ship-spike
  halts and the user adjudicates. Skeptical, fresh-context, read-only — it never
  fixes. Invocable directly (/flow:audit-skips), or by /flow:ship or /flow:ship-spike.
disable-model-invocation: false
context: fork
agent: skip-auditor
---

# Task: Audit this ship's stage skips for legitimacy

You are a skeptical, read-only auditor. Your one job: decide, **per stage**, whether
a skip (or a "ran" claim) is honest against ground truth. You **never fix** anything
and you **never re-run** a stage — you classify; the caller (`/flow:ship` or
`/flow:ship-spike`) does the routing.

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

On a successful run the block also reports **where it found flow itself** — `plugin_root`,
`plugin_root_arm` (`host-var` | `install-record` | `checkout`), and
`plugin_root_ambiguous`. These are provenance, not verdicts: do not let them change a
stage classification. Quote `plugin_root_arm` in your summary when anything looks off, so
the operator can tell whether the engine came from the host variable, the install record,
or a local checkout — the question that went unanswerable for 35 releases (FB-0141). If
`plugin_root_ambiguous` is `true`, flow matched more than one installed root and this run
picked one arbitrarily; say so.

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
# the WORKTREE root, which is always the tree under review when cwd is inside a repo.
# (NOTE: no backticks anywhere in this block -- it lives inside a single-backtick dynamic-
# context span, so ONE inner backtick truncates the span and everything after it is emitted
# as literal text instead of being executed. FB-0010; the same warning is repeated below.)
ROOT=$(git rev-parse --show-toplevel 2>/dev/null)
{ [ -n "$ROOT" ] && [ -d "$ROOT" ]; } || ROOT="${CLAUDE_PROJECT_DIR:-}"
if [ -z "$ROOT" ] || ! cd "$ROOT" 2>/dev/null; then
  printf '{"root_error": "no git toplevel from this cwd and no CLAUDE_PROJECT_DIR; config and diff were NOT read. Re-run from the repo root, or set CLAUDE_PROJECT_DIR to the repo", "stages": []}\n'
  exit 0
fi
# jq reads planPath below and parses the stamp JSON; if it is absent, config is never read
# and the gate cannot run. Route it like root_error — the gate did NOT run, not a clean pass
# (jq-absence-handling-2026-06).
command -v jq >/dev/null 2>&1 || { printf '{"jq_error": "jq is not on PATH; flow.config.json and the plan were NOT read, so the skip-legitimacy gate did NOT run. Install jq (https://jqlang.org) and re-run", "stages": []}\n'; exit 0; }
# /flow:ship (Step 2a.1) and /flow:ship-spike (Step 2a.1) write the per-stage report to this
# handoff before invoking the skill
# (ephemeral, like the verify-build findings buffer); a standalone invocation without it
# still emits the context block, with an empty stage set. Resolved AFTER the cd above, so
# a relative FLOW_SKIP_AUDIT_STAGES override resolves against the repo root rather than
# whatever cwd the fork inherited (which the cd just left).
# ...and the handoff itself must be REPO-LOCAL, not /tmp (FB-0082). The root anchor above
# fixes which tree we read; it does not make a /tmp file visible. A forked skill cannot see
# a /tmp file the parent shell wrote at all -- reproduced as a same-file A/B (full report
# from the parent, "no stage report" from the fork) -- so through v1.22.0 this gate still
# no-opped on every ship even with the anchor. Repo-local is visible to both AND per-worktree
# by construction, which also ends the cross-project clobbering of the global /tmp namespace.
# Relative default resolves against $ROOT because of the cd above.
STAGES="${FLOW_SKIP_AUDIT_STAGES:-.flow/skip-audit-stages.json}"
# Flow plugin root -- THREE arms (FB-0141 has the measurements, the ~35-site class, and
# the review history; this block keeps only what a maintainer needs in place).
# SECURITY: arm 3 is cwd-relative. READ THE SECURITY NOTE BELOW BEFORE PORTING THIS.
#
# Arm 1 was $CLAUDE_PLUGIN_ROOT; arm 2 was a bare, UNGATED plugins/flow/... --
# flow-repo-relative, so in a consumer project it cannot exist. On any run where the host
# variable was absent every helper below was unreachable, and the gate reported "cannot
# verify the stamp" on every single invocation. Neither arm may be assumed: CPR is set in
# SOME forked context blocks and unset in others, measured in one session, and WHY is not
# established -- so every arm must stand on its own.
#
# WHAT ARM 2 IS, AND IS NOT. The host's own install record: the only LIVE source of the
# root, and version-bearing, which is why a cache glob is wrong (a host can hold several
# cached versions, so a glob can run one version's engine against another's handoff). It
# does NOT name "the version in use". ship/lib/plugin-provenance.py::read_running measured
# that: an update rewrites the record immediately yet needs a restart to apply, so a
# session that began before the update keeps running the OLD tree while the record
# advertises the new one (observed: record 1.41.0, session executing 1.29.0). Arm 2 fires
# exactly when CPR is unset, so a cached old skill body CAN resolve to a newer tree. PATH
# is the reliable signal per that module, and it is not available to this bootstrap.
#
# SECURITY -- the honest version, not the flattering one. Both greps below are CONTENT
# checks. They detect a mis-install; they are NOT an attacker boundary, because no file
# inside a tree can authenticate that tree against whoever wrote it.
#   Arm 2 is still not an attacker primitive: forging it means writing into the user's own
#   config dir, where settings.json hooks already live, so anyone who can has easier
#   options. That location -- not the grep -- is what makes it safer than a cwd guess.
#   Arm 3 IS cwd-relative, and this block runs after a cd into the repo under review. An
#   untrusted repo shipping plugins/flow/.claude-plugin/plugin.json with the right name
#   plus its own two scripts gets its Python executed. That exposure is INHERITED: the arm
#   it replaces had no gate at all and was reached whenever CPR missed. This change
#   strictly NARROWS it (arm 2 shadows arm 3 on any normal install, and a name check now
#   exists where there was none) and does NOT close it. An arm-2 miss falls through to
#   arm 3, not to a refusal. Open decision on the PR; see FB-0141 § "A content check is
#   not an identity check" before porting this to another skill.
#
# (No backticks: this is a single-backtick dynamic-context span. One inner backtick
# truncated this exact block once already -- FB-0010.)
FPR=""; FPR_ARM="none"; FPR_AMBIGUOUS=false
if [ -n "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -f "${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json" ]; then
  FPR="$CLAUDE_PLUGIN_ROOT"; FPR_ARM="host-var"
fi
if [ -z "$FPR" ]; then
  # jq is guaranteed here -- the command -v jq gate above exits before this point.
  # The loop lives INSIDE the command substitution: a "while read" on the right of a
  # pipe runs in a subshell, so an assignment there would not survive the pipeline.
  # read -r, not "for C in $(...)", so an install path containing a space survives.
  IPJ="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/plugins/installed_plugins.json"
  IPJ_STATE=absent
  if [ -f "$IPJ" ]; then
    # Probe parseability SEPARATELY from the query. The query ends 2>/dev/null, so an
    # unparseable record yielded no candidates and NO signal, and arm 3 (cwd-relative)
    # was then reached silently -- a bare 2>/dev/null with no [WARN] branch, which
    # general.md item 1 forbids. Worse, the refusal below would have reported "no flow@
    # entry points at an installed flow", asserting a search result for what was really a
    # parse failure: the same say-what-you-detected rule this block closes on.
    if jq empty "$IPJ" >/dev/null 2>&1; then
      IPJ_STATE=ok
    else
      IPJ_STATE=unparseable
      echo "⚠️ [audit-skips] the install record at $IPJ is present but could not be parsed, so flow's installed location could not be read from it. Falling back to the local checkout if there is one. Fix: reinstall the flow plugin, or set CLAUDE_PLUGIN_ROOT to the installed flow directory." >&2
    fi
  fi
  if [ "$IPJ_STATE" = ok ]; then
    CANDS=$(jq -r '(.plugins // {}) | to_entries[] | select(.key | startswith("flow@")) | .value[]? | .installPath? // empty' "$IPJ" 2>/dev/null       | while IFS= read -r C; do
          if [ -n "$C" ] && [ -f "$C/.claude-plugin/plugin.json" ] && grep -q '"name": *"flow"' "$C/.claude-plugin/plugin.json" 2>/dev/null; then
            printf '%s\n' "$C"
          fi
        done)
    FPR=$(printf '%s' "$CANDS" | head -1)
    [ -n "$FPR" ] && FPR_ARM="install-record"
    # First-match-wins is the only sane default, but it must not be SILENT. A dual
    # user+project install puts two entries under one key, and presenting an arbitrary
    # pick as the answer is the thing plugin-provenance.py reports entry_count to avoid.
    if [ "$(printf '%s\n' "$CANDS" | grep -c .)" -gt 1 ]; then
      # Name EVERY candidate, not just the winner: "set CLAUDE_PLUGIN_ROOT to the one
      # you mean" is unusable advice if the message printed only one of them.
      echo "⚠️ [audit-skips] flow looks installed more than once, so this run picked one arbitrarily. Using: $FPR. Also matched: $(printf '%s\n' "$CANDS" | grep -v "^$FPR$" | tr '\n' ' ')" >&2
      echo "   If the verdicts look wrong, set CLAUDE_PLUGIN_ROOT to the installed flow directory you mean, then re-run." >&2
      FPR_AMBIGUOUS=true
    fi
  fi
fi
if [ -z "$FPR" ] && [ -f plugins/flow/.claude-plugin/plugin.json ] && grep -q '"name": *"flow"' plugins/flow/.claude-plugin/plugin.json 2>/dev/null; then
  # Arm 3: the flow checkout itself. Dogfooding only -- a consumer project never has
  # this. Content-gated, not authenticated; see the SECURITY note above.
  FPR="plugins/flow"; FPR_ARM="checkout"
fi
# Both helpers resolve off the SAME root. They were two independent copies of the
# two-arm shape, so both were dead together on an unset CPR -- meaning the skill was
# wholly unusable against an install, not merely unable to check the stamp. One root
# also removes the state where the stamp is checked by the install and the verdicts are
# computed by the checkout.
H="$FPR/skills/audit-skips/lib/skip-audit-checks.py"
# When NO arm resolved, say THAT. An empty $FPR would otherwise compose
# "/scripts/flow_scratch.py" and the operator is told a helper is missing from a path
# that was never a real location -- the same unreadable garbage /flow:audit-coverage
# calls out in its INVENTORY-UNAVAILABLE branch. The remedy for an unresolved root
# (reinstall / point CLAUDE_PLUGIN_ROOT at the install) is not the remedy for a helper
# missing from a root that DID resolve, so the two must not share one message.
FPR_NOTE=""
if [ -z "$FPR" ]; then
  # Branch on whether the record EXISTS. $IPJ is assigned unconditionally but only READ
  # under [ -f "$IPJ" ], so a flat "no flow@ entry in <path>" asserts a search that never
  # happened and sends the operator to inspect a file that is not there. This block's own
  # rule: say what the gate detected, not what it hoped to prevent.
  case "${IPJ_STATE:-absent}" in
    ok)          FPR_WHERE="no flow@ entry in $IPJ points at an installed flow" ;;
    unparseable) FPR_WHERE="the install record at $IPJ could not be parsed" ;;
    *)           FPR_WHERE="there is no install record at ${IPJ:-the usual location}" ;;
  esac
  # Ends on a REMEDY, like its two siblings in this block (root_error ends "Re-run from
  # the repo root, or set CLAUDE_PROJECT_DIR"; jq_error ends "Install jq ... and re-run").
  # The remedy was known -- it was sitting in the comment above instead of in the message.
  FPR_NOTE="flow could not find its own installation, so the handoff stamp was not checked. Looked at: CLAUDE_PLUGIN_ROOT, the install record, and ./plugins/flow ($FPR_WHERE). Fix: reinstall the flow plugin, or set CLAUDE_PLUGIN_ROOT to the installed flow directory, then re-run"
fi
PLAN=$(jq -r '.planPath // empty' flow.config.json 2>/dev/null); [ -z "$PLAN" ] && PLAN="dev-docs/plan.md"
# Stamp gate (FB-0082). A handoff must PROVE it belongs to this repo+branch+HEAD before
# it is audited. Namespacing alone is not enough: two worktrees of one repo share a repo
# path, and a handoff left by an earlier branch in THIS worktree is still readable. A
# mismatch is refused loudly rather than read-and-hope -- and is kept DISTINCT from the
# absent case, because collapsing the two is exactly how a foreign buffer reads as
# "nothing to do". An UNSTAMPED handoff is refused too (fail closed -- FB-0062).
SCRATCH_PY="$FPR/scripts/flow_scratch.py"
STAMP_STATUS=""; STAMP_REASON=""
if [ -f "$STAGES" ]; then
  if [ ! -f "$SCRATCH_PY" ]; then
    # The gate CANNOT fail open. If the checker is unreachable we cannot prove the
    # handoff is ours, and "cannot prove" must never read as "verified" -- that is
    # the exact failure this whole branch exists to remove.
    STAMP_STATUS="unverifiable"
    # Two genuinely DIFFERENT sentences, not one interpolation. Appending the
    # handoff-provenance tail to the unresolved-root case composed a ~470-character
    # sentence with two colons whose lede was the wrong story: nothing about "flow cannot
    # locate itself" concerns whether the handoff belongs to this workspace, and the
    # caller nests this inside "COULD NOT VERIFY the handoff stamp (<path>): ...".
    # (/simplify had collapsed these into one line; its objection was that the two arms
    # were the same sentence twice with drifted wording. They no longer are.)
    if [ -n "$FPR_NOTE" ]; then
      STAMP_REASON="$FPR_NOTE"
    else
      STAMP_REASON="stamp checker not reachable at $SCRATCH_PY -- cannot prove this handoff belongs to this workspace"
    fi
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
if [ -f "$STAGES" ] && [ "$STAMP_STATUS" = "unverifiable" ]; then
  # DISTINCT from stamp_error: we could not CHECK the stamp (missing checker, no python3
  # or jq), which is an install/toolchain problem. Collapsing it into stamp_error would
  # print "does not belong to this workspace" -- a false statement -- and send the agent
  # to a remedy (re-run 2a.1) that cannot fix a missing interpreter. Distinguishing
  # "cannot prove" from "disproved" is the same discipline as absent-vs-stale.
  printf '{"stamp_unverifiable": %s, "handoff": %s, "stages": []}\n' \
    "$(printf '%s' "$STAMP_REASON" | jq -Rs . 2>/dev/null || printf '"stamp checker unreachable"')" \
    "$(printf '%s' "$STAGES" | jq -Rs . 2>/dev/null || printf '"(handoff path; jq unavailable)"')"
elif [ -f "$STAGES" ] && [ "$STAMP_STATUS" = "invalid" ]; then
  # Present but CORRUPT — not foreign. Reuse the engine_error shape: "present but could
  # not be processed" is exactly its semantics and its remedy already fits. Emitting
  # stamp_error here would tell the operator the handoff belongs to another workspace,
  # which is false, and send them to the wrong fix.
  printf '{"engine_error": %s, "handoff": %s, "stages": []}\n' \
    "$(printf '%s' "$STAMP_REASON" | jq -Rs . 2>/dev/null || printf '"handoff is unreadable"')" \
    "$(printf '%s' "$STAGES" | jq -Rs . 2>/dev/null || printf '"(handoff path; jq unavailable)"')"
elif [ -f "$STAGES" ] && [ "$STAMP_STATUS" != "ok" ] && [ -n "$STAMP_STATUS" ]; then
  # Present but NOT ours. Never audit it, never call it a clean standalone no-op.
  printf '{"stamp_error": %s, "handoff": %s, "stages": []}\n' \
    "$(printf '%s' "$STAMP_REASON" | jq -Rs . 2>/dev/null || printf '"handoff stamp did not match this workspace"')" \
    "$(printf '%s' "$STAGES" | jq -Rs . 2>/dev/null || printf '"(handoff path; jq unavailable)"')"
elif [ -f "$STAGES" ]; then
  PLAN_ARG=""; { [ -f "$PLAN" ] && PLAN_ARG="--plan $PLAN"; } || echo "⚠️ [audit-skips] no plan doc at $PLAN — running WITHOUT plan context. This is NOT the same as \"the plan declares no criteria\": check flow.config.json.planPath." >&2
  # Capture stderr (do NOT 2>/dev/null it away) so an engine failure on a PRESENT handoff is
  # diagnosable. Distinguish that failure from the absent-handoff no-op below via a dedicated
  # engine_error field: a present-but-unreadable handoff is NOT "nothing to audit" -- the
  # skip-legitimacy gate did not run, and collapsing it to the standalone message is the silent
  # no-op this branch exists to prevent. (No backticks in this block -- it runs inside a
  # single-backtick dynamic-context span; an inner backtick would truncate it. FB-0010.)
  ENGINE_ERR=$(mktemp)
  # No pre-check on $H. Arm 1 now gates on the MANIFEST rather than on this specific
  # helper, so a root carrying a manifest but a missing engine is newly ACCEPTED here
  # instead of falling through -- deliberately (silently reaching past a resolved root
  # into a different tree is how a working-tree engine ends up grading an installed
  # release's handoff). That state needs no extra branch: python3 exits non-zero, its
  # stderr names the full path, and the failure arm below already routes it as
  # engine_error, which already blocks. Pinned by the engine-absent eval case.
  if OUT=$(python3 "$H" --report "$STAGES" --config flow.config.json $PLAN_ARG 2>"$ENGINE_ERR"); then
    # PROVENANCE ON THE SUCCESS PATH. Every other diagnostic in this block is a JSON key
    # on stdout -- the channel the reader demonstrably sees -- and until now the success
    # path said nothing about WHICH root produced the verdicts. On the one gate whose
    # failure mode was 35 releases of invisible wrongness, that is the obvious thing left
    # undone: a verdict that looks wrong gave the operator no way to tell whether the
    # engine came from the host variable, the install record, or ./plugins/flow.
    #
    # It also stops relying on stderr for the ambiguity signal. Whether a forked
    # context block's stderr reaches the model at all is UNMEASURED here (filed in the
    # roadmap); the >&2 warning above stays, but the fact now also travels on the channel
    # that is proven. Leaning on an unmeasured channel is the shape of the bug this whole
    # change exists to fix. (And no backticks in that sentence -- writing it with them
    # truncated this span and broke the block, exactly as the header warns. FB-0010.)
    #
    # Additive keys only, and failure-tolerant: if jq cannot re-emit the object, print the
    # engine's output unchanged rather than losing the audit to a diagnostic.
    printf '%s\n' "$OUT" | jq --arg r "$FPR" --arg a "$FPR_ARM" --argjson amb "$FPR_AMBIGUOUS" \
      '. + {plugin_root: $r, plugin_root_arm: $a, plugin_root_ambiguous: $amb}' 2>/dev/null \
      || printf '%s\n' "$OUT"
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
  echo '{"note":"no stages handoff at '"$STAGES"' — /flow:ship and /flow:ship-spike write it at Step 2a. Standalone run: nothing to audit.","stages":[]}'
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
# jq scopes the diff below (defaultBranch); if absent it silently defaults. Route like ROOT-UNRESOLVED.
command -v jq >/dev/null 2>&1 || { echo "[audit-skips] JQ-MISSING — jq is not on PATH; flow.config.json (defaultBranch) was NOT read, so the diff was NOT reliably scoped. This is not a clean pass. Install jq (https://jqlang.org) and re-run."; exit 0; }
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
    SHOULD-RE-RUN. **`context.plan_mode` in the block above is your evidence** — it
    carries the plan path, `declared_mode` (`spike` / `tiny` / `other` / `null`), and
    how many `**Mode:**` lines exist. It reports a CLASSIFICATION, never a line copied
    out of the plan: the plan doc is repo-controlled and this field lands in your
    prompt, so quoting it verbatim would let whoever wrote the plan address you
    directly. `occurrences: 0` means the mode was never declared: the claim is
    unbacked, so the reviews were owed. `ambiguous: true` means the plan holds more
    than one `**Mode:**` line (normal — plan docs accumulate one per PR block), so
    `declared_mode` is the *convention's* answer ("active PR at the top"), not a
    proven one; when it disagrees with what the diff plainly shows you, say so and
    resolve toward SHOULD-RE-RUN rather than adopting a retained block's mode. This
    field is evidence, never a verdict — the engine deliberately does not decide the
    row for you, because a first-match read of a 50-block plan can be confidently
    wrong in the failure-open direction.
  - Spike/tiny is an accepted reason for **`/simplify` and `staff-review` only**.
    For every other stage — security, accessibility, audit-coverage, verify-build,
    preflight — the engine already returns SHOULD-RE-RUN without consulting you.
    Don't soften it. Disposability is about code quality on code that gets deleted;
    it does not reach a permanent commit's secrets, an accessibility pattern a
    prototype gets a human's approval for, or whether the thing ever ran.
  - An unrecognized skip reason that the diff/config plainly contradicts →
    SHOULD-RE-RUN; one you cannot refute → LEGITIMATE (default to trusting a skip
    you have no evidence against — do not manufacture findings).
- If the mechanical block is `{"note": ..., "stages": []}` (the handoff file was **absent** —
  a standalone run), output exactly `SKIP-AUDIT: no stage report to audit (run from
  /flow:ship or /flow:ship-spike Step 2a).` and stop. This is the clean no-op — and since FB-0082 it is once again
  a *trustworthy* one: the handoff is written to a **repo-local** `.flow/` path both the parent
  and this fork can see, so an absent handoff now really does mean none was written. It did not
  mean that before FB-0082, when the handoff lived in `/tmp` and was structurally invisible to a
  forked skill — this note fired on **every** ship from v1.13.0 to v1.22.0, and the whole gate
  no-opped silently behind it. If you ever see this note on a run launched from `/flow:ship` or
  `/flow:ship-spike` Step 2a (both of which always write a handoff), the transport is broken again: treat it as a
  `stamp_error`, not a pass, and say so.
- If the mechanical block carries **`"root_error"`** (FB-0074 — the skill could not locate the
  repo under review from its inherited cwd), do **NOT** treat it as "nothing to audit". Nothing
  was read: `flow.config.json` resolved empty, every `git` call returned empty, and *every*
  unverifiable skip would otherwise validate as LEGITIMATE — a false clean pass produced by
  looking at the wrong place, which is strictly worse than an engine crash because it emits a
  confident verdict. Output a loud diagnostic and stop:
  `⚠️ SKIP-AUDIT ROOT-UNRESOLVED (<root_error>). The skip-legitimacy gate did NOT run — this
  is not a clean pass.` Route it exactly like `engine_error` below: from `/flow:ship` Step 2a
  it becomes a `[decision-required]` draft-manifest entry; from `/flow:ship-spike` Step 2a.3 —
  which has no manifest — it halts for the user to adjudicate. Never a silent proceed.
- If the mechanical block carries **`"jq_error"`** (jq-absence-handling-2026-06 — `jq` was not
  on PATH, so `flow.config.json` and the plan were never read and the gate could not run), treat
  it identically to `root_error`: nothing was read, so an all-LEGITIMATE verdict would be a false
  clean pass. Output a loud diagnostic and stop:
  `⚠️ SKIP-AUDIT JQ-MISSING (<jq_error>). The skip-legitimacy gate did NOT run — this is not a
  clean pass. Install jq and re-run.` Routes to `[decision-required]` like `root_error` (though
  `/flow:ship` blocks earlier at Step 1.5 when jq is missing, so this is reached mainly on direct invocation).
- If the mechanical block carries **`"stamp_error"`** (a handoff WAS present but its
  `flow_stamp` does not match this repo/branch/HEAD, or it carries none at all), do **NOT**
  audit it and do **NOT** report a clean standalone no-op — you are looking at another
  workspace's handoff, or a stale one from an earlier branch. Output a loud diagnostic and stop:
  `⚠️ SKIP-AUDIT REFUSED a handoff that does not belong to this workspace (<handoff>):
  <stamp_error>. The skip-legitimacy gate did NOT run — this is not a clean pass.` From
  `/flow:ship` Step 2a this routes to the draft manifest as `[decision-required]`
  (`[skip-audit] handoff failed its stamp check — needs: re-run ship Step 2a.1 | human-waive — confidence: auto-resolvable — candidate resolutions: rewrite the handoff from this workspace`).
- If the mechanical block carries **`"stamp_unverifiable"`** (a handoff was present but the
  stamp checker itself could not run — **flow's own installation could not be located**,
  `flow_scratch.py` missing, or no `python3`/`jq`), this
  is an **install/toolchain** problem, NOT a foreign handoff. Do not claim the handoff belongs
  to someone else, and do not tell the operator to re-run ship Step 2a.1 — rewriting the
  handoff cannot fix a missing interpreter. Output:
  `⚠️ SKIP-AUDIT COULD NOT VERIFY the handoff stamp (<handoff>): <stamp_unverifiable>. The
  skip-legitimacy gate did NOT run — this is not a clean pass. Reinstall the flow plugin or
  install python3/jq, then re-run.` Routes to the draft manifest as `[decision-required]`.
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
`audit-coverage` / `preflight` emit **no** machine artifact, so a bare "ran" claim from
them has nothing to cross-check and is trusted as `LEGITIMATE` — all four render the SAME
qualifier (`ran (no machine artifact to cross-check)`), so the summary never shows one
epistemic state in two voices. Giving every reviewer a freshness breadcrumb so its "ran"
claim becomes mechanically checkable is a tracked roadmap § Next item — promoted out of
§ Exploration at v1.38.0, because spike mode made two of these four mandatory and routes
their claim to a clean pass with no draft manifest behind it. Until then, this asymmetry
is by design and stated, not a silent hole.

A result where every stage is LEGITIMATE is the correct, common outcome on a clean
PR. Do not invent findings to appear thorough.

## Output

Produce EXACTLY this shape (no prose before or after):

```
[⚠️ PATTERN-WARNING: <warning>]        ← only when context.pattern_warnings is non-empty
SKIP-AUDIT SUMMARY
- <stage>: <LEGITIMATE | SHOULD-RE-RUN> — <one-line reason>[ · auto-resolvable: re-run | decision-required][ · manifest: <kind>]
- ...
RESOLUTION: <all N stage skips LEGITIMATE — proceed | all N LEGITIMATE, K owe the manifest (<kind>) — add + draft | M SHOULD-RE-RUN (A auto-resolvable, D decision-required)>
```

**`PATTERN-WARNING` (FB-0079).** If `context.pattern_warnings` is non-empty, emit one
`⚠️ PATTERN-WARNING: <warning>` line per entry ABOVE the summary. The engine resolves each
reviewer's file pattern through `visualFilePatterns`/`a11yFilePatterns` → `uiFilePatterns` →
built-in default; an unusable pattern degrades to the default and records the warning there.
Unlike `root_error`/`engine_error`, this is a **degraded measurement, not an absent one** — the
verdicts below are still produced and still meaningful, but they were measured with the built-in
pattern rather than the project's own. Say so rather than reporting a confident verdict whose
ruler silently changed. This is the one exception to "no prose before or after".

**`manifest: <kind>` (the toolchain case).** When a stage's mechanical block carries a
non-null `manifest_kind`, append ` · manifest: <kind>` to that stage's line and use the
`K owe the manifest` form of `RESOLUTION:`. This is the one case where LEGITIMATE does
**not** mean "proceed": the skip was honest — the engine verified against this host that
the toolchain the platform needs really is absent — but the check still never ran, so the
PR owes a draft-manifest entry (`/flow:ship` Step 2a.3 adds it via `manifest-triage.py
add-entry`, and the PR opens as a draft). Echo the field exactly as the engine emitted it;
never invent one and never drop one. Dropping it is not a cosmetic omission — it is how a
change with no behavioral gate reaches a **ready** PR.

When every stage is LEGITIMATE and none carries a `manifest:` field, the body lists each
stage and the `RESOLUTION:` line reads `all N stage skips LEGITIMATE — proceed`. When ≥1 stage is SHOULD-RE-RUN, the
`RESOLUTION:` line names how many are auto-resolvable (re-run + re-audit once) vs
decision-required (→ draft manifest). Do not explain your process.
