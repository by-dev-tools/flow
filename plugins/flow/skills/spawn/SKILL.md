---
name: spawn
description: >
  Dispatch one worker: admission-control the item against open branches and PRs,
  route model + effort from the job-shape table and LOG THE WHY, render the
  dispatch brief, create the workspace through the dispatchBackend adapter with
  the brief as its first message, and instruct the new agent's first action as a
  named flow skill. The routing floor is enforced, not suggested — work touching
  sensitivePaths cannot be routed down. Use on "/flow:spawn", "dispatch a
  worker", "spin up a workspace for X". Never merges.
disable-model-invocation: false
allowed-tools: Read, Grep, Glob, Bash, Write
---

# Task: dispatch one worker, and leave an audit trail you can tune against

**This wraps a checklist and a table; the judgment stays yours.** Which item to dispatch, whether it is ready, and what "done" means are your calls. What this pins down is the part that has measurably gone unapplied: a fleet was found running **4 of 4 workers on the top tier — including a parked one doing nothing — with no dispatch logging a `model · effort · why` line at all.** Specified, believed effective, never applied.

**Deletion criterion (FB-0088):** delete when two consecutive routing audits show the `model·effort·why` line is emitted correctly *without* this skill (the practice stuck), or when the backend gains a typed dispatch API that carries the brief contract itself.

## 0. Resolve the backend

```sh
ROOT=$(git rev-parse --show-toplevel 2>/dev/null); { [ -n "$ROOT" ] && [ -d "$ROOT" ]; } || ROOT="${CLAUDE_PROJECT_DIR:-}"
[ -n "$ROOT" ] && cd "$ROOT" || { echo "[spawn] ROOT-UNRESOLVED — nothing ran."; exit 0; }
python3 "${CLAUDE_PLUGIN_ROOT:-plugins/flow}/lib/dispatch_backend.py" check 2>&1 || true
```

If `createWorker` is absent or invalid, **stop and say so**: render the brief anyway, hand it to the human, and state plainly that no workspace was created. A dispatch that silently did not happen is the worst outcome available here.

## 1. Admission control — before anything else

```sh
# Ref-only round trip; no `git fetch` first (its objects would be read by nothing).
git ls-remote --heads origin | sed 's|.*refs/heads/||' | grep -i -- "<item-slug>" || echo "no branch for this item"
gh pr list --state open --json number,title,headRefName --limit 60 2>/dev/null || \
  echo "[spawn] ⚠️ gh unavailable — open-PR check NOT performed; say so."
```

Three checks, all of which have caught real collisions:

- **Already in flight?** A branch or open PR for the item means you are about to dispatch a duplicate.
- **Rate window near exhausted?** Under one subscription every worker draws on **one** budget: N workers exhaust it ~N× faster and the *whole fleet then stalls at once*. Hold the queue rather than dispatch into a near-empty window; 3–4 concurrent workers is the useful maximum.
- **Serialization, not partition.** Docs every ship touches — plan, history, roadmap — are **shared by construction**, so ships through them are *serialized*, never ownership-partitioned. Name the ship-slot holder in the brief. (Learned twice, from two workers' rebase collisions.)

## 2. Route `model · effort`, and log the why

**Effort is a bigger lever than model tier.** Tier sets price *per token*; effort sets *how many tokens*. A strong model at low effort routinely costs less than a weak model at high effort, because a weak model flails and **flailing in an agentic loop is billed**. So the first question is not "can this be cheaper?" but "what does this job actually need?"

This is **right-sizing, not rationing.** Two failure modes, and the second is worse:

- **Over-spending** — everything on the top tier by default rather than by decision.
- **Under-dispatching** — holding back a legitimate parallel worker to conserve budget. That trades throughput, the scarce thing, for tokens, the cheap thing. **Never decline a worker that has real work for budget reasons; right-size it instead.**

| Job shape | Model | Effort |
|---|---|---|
| Orchestrator — triage, relay, dispatch | mid-tier, long-context | low–medium |
| Feature work, full loop | top-tier, long-context | high |
| One-way door / architecture / **gate machinery** | top-tier (or the reasoning-heaviest available) | xhigh–max |
| Bug fix with a known repro + failing test | upper-mid tier | medium |
| Docs, changelog, doc-currency | mid-tier | low |
| Mechanical sweep — low-stakes repos only | small/fast tier | low |
| Spike / research | upper-mid tier | medium–high |
| Adversarial second opinion | a *different vendor's* frontier model | high |

> **Tiers, never model ids — a host-agnosticism decision, not shorthand.** A literal roster is a host-specific token and would fail the same bar that keeps the backend behind a config slot; it also rots quietly and then routes *everything* wrong. Resolve tiers to your host's ids **at dispatch time**.
>
> **Refresh criterion (FB-0088):** re-derive the tier→id mapping whenever your host's roster changes (a hash of its model list is the cheap tripwire) **and** on a 60-day backstop regardless, since pricing and effort guidance move without the roster changing. Remediation stays manual: a policy that auto-updates from scraped docs rots quietly and then routes everything wrong.

**Escalation rule — start one tier down, let evidence promote, re-dispatch rather than grind.** The loop already emits the promotion signals: a LOW-confidence assumption, a plan critique that returns REDIRECT, a verification that returns Unknown, or two loops on one failure. **A stuck cheap worker burns more than a fresh strong one, and a fresh context is worth more than a persuaded one.** Promotion is a *re-dispatch*, never a mid-session switch — changing model or effort mid-conversation breaks the prompt cache and forces a full re-prefill.

Fast mode is nearly always wrong for a worker: more speed at more cost, and nobody is watching an unattended worker.

### The one hard floor — enforced, not remembered

```sh
# Same scratch preamble as every other .flow writer — the mkdir (the shell's own
# redirect fails without it) and the CWE-59 symlink refusal. Both sites in this
# skill get it; fixing one of two identical redirects is the fan-out class.
[ -L .flow ] && { echo "⚠️ BLOCKER: .flow is a symlink — refusing to write scratch through it." >&2; exit 1; }
mkdir -p .flow
printf '%s\n' <each glob this worker will own> > .flow/spawn-globs.txt
python3 "${CLAUDE_PLUGIN_ROOT:-plugins/flow}/lib/sensitive_paths.py" --globs-file .flow/spawn-globs.txt
```

Note `--globs-file`, not `--files-file`: you hold *owned globs*, the gate holds a *changed-file list*, and one predicate asked two different questions has two correct answers. So spawn's input is **normalised** (globs expanded against tracked files) rather than the predicate overloaded. A glob matching nothing today is reported loudly — "matches nothing yet" is not "nothing sensitive here".

`sensitive: true` ⇒ **top tier, high effort, no exceptions.** A wrong answer in gate machinery fails *silently* — a mis-classifying gate passes bad work — which is the one error class where a cheaper model's savings are not worth having. This is the same predicate the plan gate uses for its stakes axis, deliberately.

Then do **both** of these — the brief line is what the worker sees, the record is what you tune against:

1. Write the routing line **into the brief itself**.
2. Append one record per dispatch:

```sh
[ -L .flow ] && { echo "⚠️ BLOCKER: .flow is a symlink — refusing to write scratch through it." >&2; exit 1; }
mkdir -p .flow
[ -s .flow/usage.tsv ] || printf 'date\titem\tmodel\teffort\twhy\towns\toutcome\n' > .flow/usage.tsv
printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$(date -u +%Y-%m-%d)" "<item>" "<model>" "<effort>" \
  "<one clause>" "<owned globs>" "pending" >> .flow/usage.tsv
```

**The `outcome` column is what makes this an audit rather than a log** (`landed` / `re-dispatched` / `abandoned`, filled in when the item resolves): a choice that saves 40% per turn and gets re-dispatched a third of the time is a loss. Compare **ratios between choices**, never absolutes.

This is not a ledger of live *state* — that is deleted by design, because state has an authoritative live source and a maintained copy goes stale. A decision already made does not. The file is session scratch, so `/flow:handoff` step 2 externalizes it; otherwise every rotation silently resets the trail.

**Deletion criterion (FB-0088):** delete when tiers are chosen by measurement rather than judgment, or when the host reports per-session model/effort directly.

## 3. Render the brief — and keep it under ~30 lines

Past ~30 lines, something in it belongs in the repo instead. Everything about *how to work* already lives in the project's `CLAUDE.md`, this plugin, and the auto-loading rules; restating it here is duplicated state that drifts.

Write it with the **Write tool** to `.flow/brief-<item>.md`. Never compose it as a shell string.

```markdown
# <item-id> — <title>

## Outcome
<2–4 sentences. What is true when this is done. Not how.>

## Done means
- [ ] <observable criterion>

## Routing
model · effort · why: <tier/id> · <effort> · <one clause>

## You own
write: <globs>
do not touch: <globs>          # another worker holds these
ship slot: <held by you | held by <worker>; rebase when it lands>

## Context you can't get from the repo
- <fact>                        # omit the section entirely when there are none

## Contract
- Mode: feature. Run the full loop.
- STOP at the plan gate: write the plan, push the branch, report, end your turn.
- Surface every decision with a recommendation, a confidence (high/medium/low), and the
  justification. Never make me ask for the confidence or the why.
- Claim any contested number (version, feedback id) MECHANICALLY by pushing the file, not in prose.
  Re-sweep the default branch AND open branches at every rebase; if either is at or above your
  claim, take the next free value and re-sweep immediately, without asking.
- Ping me at <session-id> on completion, on a blocking question, and on a stall. Compose the
  message into a file and send it with the backend's message-file form — never as a quoted
  shell argument.
- FIRST, before anything else: confirm `<the named skill>` actually resolves in YOUR environment
  (e.g. `claude plugin details`, or attempt it and read the error). A spawned workspace only has
  the skills INSTALLED there, and an installed plugin can be several releases behind this repo —
  a skill added by an unmerged PR is not registered at all. If it does not resolve, ping me
  immediately with "SKILL-ABSENT <name>"; do NOT improvise a substitute and do NOT proceed
  silently. Then: run <the named skill>.
- Never create workspaces or sessions. Never merge.
```

## 4. Create the workspace — brief as the first message

```sh
python3 "${CLAUDE_PLUGIN_ROOT:-plugins/flow}/lib/dispatch_backend.py" \
  render createWorker --set name=<worker-name> --set messageFile=.flow/brief-<item>.md
```

Run the rendered command. The renderer refuses unsafe values rather than escaping them; if it refuses, fix the value — do not hand-edit the command.

## 5. Instruct, don't remote-invoke

**You cannot reach into another workspace's process.** "A gets B to run X" works exactly one way: A creates B, and B's **first message instructs B** to run a named skill, which B then invokes in its own process. That is why this suite ships in the plugin (so B *has* the skills) and is agent-invocable (so B *can* run them with no human in the loop).

So the brief's contract names the skill B should run first. Be specific — a named skill, not "get started".

**And have B assert it exists first.** B resolves that skill from its *installed* plugin tree — not this checkout, and possibly several releases behind it; a skill added by an unmerged PR is installed nowhere. Without the assertion B receives an instruction naming a command that does not exist, and the failure is silent at both ends: B improvises, you read the ping as progress. Hence the contract's first line is a precondition with a named failure ping.

## 6. Report the dispatch — one line

Name the worker, the item, and the routing line with its why. If any backend verb was missing and a step went unperformed, say which. Apply the same communication rules as the rest of the seat: one decision at a time, recommendation + confidence + justification on anything you need answered, and classify ships-or-paperwork before escalating at all.
