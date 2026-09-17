---
name: orchestrate
description: >
  Boot or re-boot an orchestrator seat that drives other workspaces: read the
  project's plan and rules, re-derive live worker state from the dispatchBackend
  adapter, sweep open branches and open PRs (not just the default branch), find
  workers that have gone SILENT by last-activity rather than status, re-address
  the ping channel to this seat's session id, and load the gate policy — then
  report ready as one scannable decision, not a status dump. The standard first
  action of any orchestrator seat, and mandatory for a successor. Use on
  "/flow:orchestrate", "boot the orchestrator", "take over the seat".
disable-model-invocation: false
allowed-tools: Read, Grep, Glob, Bash, Write, Skill
---

# Task: boot an orchestrator seat, and leave nothing for the next one to rediscover

The orchestrator's product is **attention** — the human's. A seat that relays everything recreates the exact cost it exists to remove, so this skill's output is a decision, not a report.

**This skill wraps a checklist; the judgment stays yours.** It does not decide which worker matters, whether a plan is sound, or what to dispatch next. It makes sure the six things a fresh seat always needs are actually done, in an order where each one's failure is visible.

**Deletion criterion (FB-0088):** delete this skill when the backend exposes a single boot call that re-derives worker state, sweeps open branches and reports last-activity — at which point this is a wrapper over one command and should be deleted, not maintained.

## 0. Resolve the backend adapter (never a silent no-op)

```sh
ROOT=$(git rev-parse --show-toplevel 2>/dev/null)
{ [ -n "$ROOT" ] && [ -d "$ROOT" ]; } || ROOT="${CLAUDE_PROJECT_DIR:-}"
if [ -z "$ROOT" ] || ! cd "$ROOT" 2>/dev/null; then
  echo "[orchestrate] ROOT-UNRESOLVED — could not locate the repo from cwd $(pwd). Nothing below ran."
  exit 0
fi
LIB="${CLAUDE_PLUGIN_ROOT:-plugins/flow}/lib/dispatch_backend.py"
python3 "$LIB" check 2>&1 || true
```

Read the report. `slot_present: false` or any `absent`/`invalid` verb is **not** a reason to stop — the workflow still applies. It changes what you say: every step below whose verb is missing must be reported to the human as **"not performed, do this by hand"**, using the `manual_fallback` text the check prints. Never let a missing verb become a step you silently skipped.

## 1. Read the durable layer — by slot, and only the pointers

Resolve the doc slots through the **shared resolver** — never by reading `flow.config.json` yourself. It is the one thing that knows a slot may point at a directory (`[ -f ]` is false on one) and that an unresolved slot must be loud, not silent:

```sh
R="${CLAUDE_PLUGIN_ROOT}/lib/resolve-doc-slot.sh"; [ -f "$R" ] || { [ -f plugins/flow/.claude-plugin/plugin.json ] && grep -q '"name": *"flow"' plugins/flow/.claude-plugin/plugin.json 2>/dev/null && R=plugins/flow/lib/resolve-doc-slot.sh; }
for SLOT in planPath:dev-docs/plan.md roadmapPath:dev-docs/roadmap.md feedbackPath:dev-docs/feedback.md; do
  [ -f "$R" ] && sh "$R" "${SLOT%%:*}" "${SLOT#*:}" \
    || echo "⚠️ [resolve-doc-slot] not found — ${SLOT%%:*} was NOT resolved, so this seat has NO ${SLOT%%:*} context. Reinstall the flow plugin."
done
```

Then read: the project's canonical plan, `CLAUDE.md`, the feedback corpus, plan "Current Focus", roadmap "Now". **A seat that silently resolved nothing reads exactly like a project with no plan** — which is why the resolver is loud rather than defaulting.

**Read them; do not copy them into your own notes.** Durable design lives in git and is re-readable by any successor; a summary you hold in session context is a snapshot that goes stale and dies with the seat. The whole disposability invariant is that you hold nothing that isn't recoverable from git, the backend, or already delivered to the human.

## 2. Re-derive live worker state — never from a snapshot

Render and run `listWorkers`. Live state is the backend's, not a document's: a dispatch ledger with a `status` column was measured stale **within minutes** — it read "dispatched" for three workspaces the API already reported as deleted. If you catch yourself about to write a status table to disk, don't.

## 3. Ground-truth sweep — open branches and open PRs, not just the default branch

```sh
# `ls-remote` is a ref-only round trip that asks the remote directly — no `git fetch`
# first. A fetch here would download objects for every remote branch and then be read
# by nothing, and it is most expensive on exactly the repo this skill is for: a fleet
# with many live branches.
git ls-remote --heads origin | sed 's|.*refs/heads/||'
gh pr list --state open --json number,title,headRefName,isDraft --limit 60 2>/dev/null || \
  echo "[orchestrate] ⚠️ gh unavailable — open-PR state NOT swept; say so rather than assuming zero."
```

A sweep that reads only the default branch **does not see open branches**, and that gap has produced repeated version/feedback-number collisions: a worker re-derived its number from the default branch correctly and still collided with three numbers claimed on an open branch. Whatever contested resource this project serializes (version numbers, feedback IDs, doc slots), sweep both.

## 4. Sweep for SILENT workers — by last activity, never by status

> **If you are a successor, do step 5 first.** Until the ping channel is re-addressed every
> worker is silent *by construction* — they have all been pinging an address that died with
> the previous seat — so this sweep tells you nothing and will read every live worker as a
> phantom stall. The steps cannot simply swap (re-address needs step 2's worker list), which
> is why the interlock is stated rather than implied. The spec puts re-address first for
> exactly this reason.

Workers ping you when they finish or stall, so you react rather than poll. **But the failure this protocol most needs to report is the one it cannot:** a rate-limited worker has no turn in which to send anything. Its status reads `idle`, which is indistinguishable between "waiting at a gate", "done and forgot", and "died hours ago".

So for each live worker, render `workerStatus` and read the **last-activity timestamp**. Flag anything quiet for materially longer than its work should take. Do not treat silence as progress, and do not let the ping protocol's existence be mistaken for coverage.

## 5. Re-address the ping channel — the successor's true first action (see step 4's note)

Every live worker is pinging a session id. On a succession that id is the **outgoing** seat's, it died with the seat, and the failure is invisible from both ends: pings go nowhere and you read the resulting silence as "nothing needs me."

Render `selfSession` to get your own id, then send **one message per worker** via `sendMessage` carrying it. Write each message with the Write tool to a scratch file and pass the path — never compose it as a quoted shell argument.

**One message per worker, not one batched message with per-worker sections.** A batched message got the wrong instruction read by the wrong worker, and the misroute is undetectable from both ends: the wrong recipient silently absorbs an instruction that was never theirs, and the intended worker has nothing to notice the absence of. One observed instance surfaced a fortnight late, and only because a worker volunteered it while reporting something else.

If `selfSession` is missing, **ask the human for the id** — do not skip the re-address.

## 6. Load the gate policy

Do **not** re-derive the four-axis rule in prose — `/flow:gate` implements it, and re-deriving is exactly what that engine exists to replace. Invoke it per decision: `Skill("flow:gate")`. Confirm `sensitivePaths` resolves:

```sh
# `--files-file /dev/null`, NOT `--print-defaults`: the latter returns before the
# config is ever read, so it proves the file is executable and nothing about THIS
# project's slot — a present-but-malformed `sensitivePaths`, the one case the
# predicate warns loudly about, would still print "available". And the `|| echo`
# branch is load-bearing: a bare `&& echo` prints nothing on failure, which is the
# silent-skip shape rather than a check.
# Parsed with python3 rather than jq deliberately: python3 is already a hard
# dependency of every lib this suite calls, and adding jq would oblige this skill
# to carry the repo's BLOCKING jq guard for one cosmetic line.
python3 "${CLAUDE_PLUGIN_ROOT:-plugins/flow}/lib/sensitive_paths.py" --files-file /dev/null \
  | python3 -c 'import json,sys; print("[orchestrate] sensitivePaths resolved from:", json.load(sys.stdin)["pattern_source"])' \
  || echo "⚠️ [orchestrate] the sensitivePaths predicate is NOT available — the gate's stakes axis cannot be computed this session. Reinstall the flow plugin."
```

Report `pattern_source` in the ready line. `default` on a project that *believes* it configured the slot is the interesting case, and it is invisible unless you say it.

## 7. Report ready — one decision, plus a one-line lay of the land

Apply the communication rules to **this output**, which is the first thing the human reads from you:

1. **Decide within scope; don't relay.** Anything inside the gate's green quadrant, you call. Escalate only what a red axis forces.
2. **Classify ships-or-paperwork before escalating anything.** If the choice produces an identical diff either way and the question is documentation placement or wording, it is your call — escalating it spends the human's attention on a null result. Run it — in full, because the flags are what it classifies on:

```sh
python3 "${CLAUDE_PLUGIN_ROOT:-plugins/flow}/skills/gate/lib/gate-classify.py" ships-or-paperwork \
  --changes-behavior <yes|no> --changes-consumer-surface <yes|no> --changes-gate-verdict <yes|no>
```

An unstated axis counts as `yes`, so a bare call classifies `behavioral` and you escalate something you could have decided — fail-safe, but it spends the attention this test exists to save. The test is cheap; run it every time, with the flags.
3. **One decision at a time.** Surface the single most pressing item, plus **one line** naming the other live threads and their state. Never a flat dump of unrelated asks; never silence about parallel threads either.
4. **Progressive disclosure.** Lead with what is needed. Default to scannable-in-seconds; let the human pull detail by asking.
5. **Every escalation carries recommendation + confidence + justification** and a return address, so the answer can be relayed back from this seat. The human should never have to ask for the confidence or the why, and should never have to open a worker workspace to unblock it.

Then state explicitly, in one line each: how many workers are live, how many are **silent** (step 4), anything the sweep in step 3 contradicts, and any backend verb that was missing so a step went unperformed.

**Large text blocks read worse than you assume.** A verbose orchestrator is the failure mode, not the thorough one.
