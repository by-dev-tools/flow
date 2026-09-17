---
name: gate
description: >
  Classify one gate decision and format it. Plan gate — four axes (stakes,
  reversibility, confidence, taste); all four green and the orchestrator may
  approve, any one red goes to a human, and an undeclared axis counts as red.
  Merge gate — classifies which delegable branch a change falls into and returns
  "human" every time. Runs the ships-or-paperwork test BEFORE escalating, and
  formats what survives with recommendation, confidence, justification and a
  return address. Use on "/flow:gate", "can I approve this plan?", "should this
  escalate?". CLASSIFIES AND FORMATS ONLY — it never merges.
disable-model-invocation: false
allowed-tools: Read, Grep, Glob, Bash, Write
---

# Task: decide what you may decide, and make what's left cheap to answer

Two human gates are the product: plan approval and merge. This skill does not remove either. It makes **who holds each one a function of the decision's properties**, so low-stakes reversible work stops costing human attention while high-stakes, irreversible or taste-laden work still requires it.

**Why this is code and not a paragraph:** a wrong answer here fails *silently*. An axis mis-read as green auto-approves a plan that should have escalated, and nothing downstream reports it — the work just proceeds with one fewer human in the loop than the policy promised. So the combination rule is a truth table with fixtures, and **every undeclared axis counts as red.** There is no input meaning "couldn't tell, proceed anyway".

**What stays yours:** whether a change is genuinely reversible, and whether it is a taste call. Those are judgment, this skill takes them as declared inputs and refuses to guess them. Stakes is computed for you.

**Deletion criterion (FB-0088):** delete when the rollout reaches its final rung and the classification is enforced by the merge machinery itself under a distinct merge identity — a skill that only *recommends* would then be a weaker copy of a live gate. Or the opposite: when two consecutive audits show these classifications never diverge from the human's, which retires the audit log and with it the main job.

## 0. Run the ships-or-paperwork test FIRST

Before classifying anything, ask whether the choice changes **behaviour**, a **consumer surface**, or a **gate verdict** — or only *where something gets written*.

```sh
ROOT=$(git rev-parse --show-toplevel 2>/dev/null); { [ -n "$ROOT" ] && [ -d "$ROOT" ]; } || ROOT="${CLAUDE_PROJECT_DIR:-}"
[ -n "$ROOT" ] && cd "$ROOT" || { echo "[gate] ROOT-UNRESOLVED — nothing ran."; exit 0; }
python3 "${CLAUDE_PLUGIN_ROOT:-plugins/flow}/skills/gate/lib/gate-classify.py" ships-or-paperwork \
  --changes-behavior <yes|no> --changes-consumer-surface <yes|no> --changes-gate-verdict <yes|no>
```

`paperwork` ⇒ **resolve it yourself.** If the diff is identical either way and the question is documentation placement or wording, escalating spends the scarcest resource in the system on a decision with no outcome attached. This was earned: an escalation offering a "declare vs waive" choice turned out to produce a byte-identical diff either way, and the human's reply was to ask what was actually being asked of them.

The asymmetry makes the test safe to get slightly wrong: guessing "paperwork" when it was "ships" produces a call the human can still reverse at the merge gate; guessing "ships" when it was paperwork is a guaranteed waste with no upside. When genuinely unsure, decide, act, and **mention the call in one line**.

Format compliance is not the bar. An escalation can carry options, a recommendation, a confidence and a rationale and still be worthless to receive.

## 1. The plan gate — four axes, all four must be green

```sh
git diff --name-only origin/HEAD...HEAD > .flow/gate-files.txt 2>/dev/null
python3 "${CLAUDE_PLUGIN_ROOT:-plugins/flow}/skills/gate/lib/gate-classify.py" plan \
  --files-file .flow/gate-files.txt \
  --reversible <yes|no> --confidence <high|medium|low> \
  --critique-verdict <approved|redirect|findings> --taste <low|high> \
  [--prototype-attached]
```

| Axis | Green means | Why it is on the list |
|---|---|---|
| **Stakes** | the diff touches no `sensitivePaths` entry | a wrong version there fails *silently*, is *exploitable*, or is a *one-way door* |
| **Reversible** | a plain `git revert` fully undoes it — no migration, no external side effect | a two-way door is cheap to get wrong |
| **Confidence** | the plan's own verdict is HIGH **and** the plan critique returned APPROVED with no open MEDIUM/LOW assumption | reuses existing signal; introduces none |
| **Taste** | a correct answer exists and is checkable by tests or critique | not a visual / UX / product call |

**Carve-out, always human:** a plan gate with a **prototype attached**. The prototype *is* the high-taste artifact, so the other four axes do not get to override it.

This is an extension of the existing autonomy bar and of "a positive PASS, not the absence of failure" — a policy over the gates the loop already has, not new machinery.

## 2. The merge gate — classified, but human every time

A merge writes to the default branch, so it keys on something stricter than stakes: **explicit verifiability.**

```sh
python3 "${CLAUDE_PLUGIN_ROOT:-plugins/flow}/skills/gate/lib/gate-classify.py" merge \
  --diff-class <docs-only|code> --verify-verdict <pass|fail|unknown|skipped> \
  --confidence <extremely-high|high|medium|low> --plan-axes-green <yes|no>
```

Three branches: **docs-only** (no behavior to get wrong); **code with a real end-to-end verification** — a behavioral PASS, extremely-high confidence, and still inside the plan-gate green quadrant (the green run *is* the proof); and **anything else** — verification skipped or Unknown, or any red axis — which has no behavioral proof.

**The verdict is `human` for all three, and there is no setting that changes it.** Delegated merges are the *second* rung of a rollout whose first rung is exactly this: classify every call and log it, so the widening is earned by an audit trail rather than asserted. The rung after that also requires a distinct merge identity, so that who merged is recorded natively and tamper-evidently. Until that identity exists, an agent merging would do so under the human's own credential and destroy the only provenance the policy asks for.

So this step's output is the **classification and the recommendation**, which is what the human is being handed — not a decision this skill is withholding.

## 3. Log the classification

Every call — approved or escalated — writes its `audit_line` into the current PR block in the project's plan doc (`planPath`). That is the audit trail the rollout is earned with.

**In the plan doc, not a new store.** State that is duplicated into a maintained ledger goes stale: a dispatch ledger with a status column was measured wrong within minutes of being written. The plan doc is already reviewed, already in git, and already the place decisions are recorded.

## 4. Format what escalates — and give the answer somewhere to go

```sh
python3 "${CLAUDE_PLUGIN_ROOT:-plugins/flow}/skills/gate/lib/gate-classify.py" format \
  --decision-file .flow/gate-decision.json
```

Write the JSON with the **Write tool** (`title`, `recommendation`, `confidence`, `justification`, `originating_session`, `other_threads[]`), never as a shell string — the justification is prose about code and routinely contains backticks.

The renderer refuses to format an escalation that is missing the recommendation / confidence / justification triple, and refuses one with **no `originating_session`**. That second refusal is the one people skip: the seat is the single human-facing decision surface **in both directions**. An escalation is not finished when it is presented — it is finished when the human's answer has been **relayed back** to the worker that raised it, from this seat, via the backend's message verb. A human should never have to open N worker workspaces to keep N workstreams moving; that is the attention cost the seat exists to remove, and routing approvals through worker chats reintroduces it in full.

When the human answers, relay it back yourself — that is the return leg, and it is a command, not an intention:

```sh
# Write the answer to a file first; it is prose about code and carries backticks.
python3 "${CLAUDE_PLUGIN_ROOT:-plugins/flow}/skills/spawn/lib/dispatch-backend.py" \
  render sendMessage --set session=<originating_session> --set messageFile=.flow/gate-answer.md
```

Then run the rendered command. If `sendMessage` is unconfigured the renderer says so loudly — deliver the answer by hand and say that you did, rather than letting the decision stop here.

The approval authority stays with the human. The *interaction surface* stays here.

## 5. One decision at a time

Surface the single most pressing item, plus **one line** naming the other live threads and their state. Never a flat dump of unrelated asks demanding simultaneous attention; never silence about parallel threads either. Lead with the decision; let the human pull detail by asking.

## What this skill will not do

It does not merge, and it contains no code path that could. It does not approve on the human's behalf when any axis is red. It does not invent the reversibility or taste axes when you have not declared them — it marks them unknown, which escalates.
