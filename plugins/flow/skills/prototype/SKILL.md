---
name: prototype
description: >
  The prototype phase and human gate 1 (D1 Phase 2, FB-0081/FB-0113/FB-0114).
  For a UI-surface change, the human's FIRST decision point becomes a
  prototype they can look at rather than a plan they have to read. Writes
  the design brief, runs /flow:review-brief over it, produces and
  self-evaluates an HTML prototype, presents it with the click-to-pin
  annotation layer, and captures the human's approval as a checkable
  record. Iterative and cheap by design: no ship pipeline, no evals, no
  doc synthesis. Never approves on the human's behalf, never merges.
  Trigger phrases: "/flow:prototype", "prototype this", "let's prototype
  before planning".
disable-model-invocation: false
allowed-tools: Read, Write, Edit, Bash, Agent, Skill
---

# Task: prototype first, then let the human approve a look — not a description of a look

This is D1's answer to a specific complaint (`dev-docs/roadmap.md` § Designer-signal track): *"I feel like I'm spending too much time approving things … too in the technical weeds for me to really understand. A lot of the messages I come to are too long and I don't really read them and I just end up approving anyway."* An approval that wasn't read is worse than no gate — it launders an unreviewed decision as a reviewed one.

So for a UI-surface change the gate **moves**. It does not multiply.

> **The invariant, and you are the part of the loop that holds it: exactly ONE pre-execution human gate, always.** Prototype approval XOR plan approval. Never both — that is the ceremony this removes. Never neither — that is a gate silently deleted. And a plan always exists before Execute.

**Iteration is the point.** No ship pipeline, no evals, no doc synthesis, no commits, no PR. The six-round annotation-layer rebuild is the reference case. If you find yourself running `/flow:ship`, `/flow:staff-review`, `/simplify`, an eval harness, or writing a history entry, you have left this phase.

## 0. No jq required — and that is deliberate

Most config-reading flow skills fail loud on a missing `jq`, because they read `flow.config.json` through it and a silent degradation to hardcoded defaults would mean acting on the wrong config. **This skill reads no config in shell.** `prototype-gate.py` parses `flow.config.json` with Python's stdlib `json`, so there is no jq dependency to guard — and adding a guard for a tool this skill never invokes would be ceremony that implies a dependency it does not have.

The engine still refuses to guess: an unreadable `flow.config.json` yields `config_state: malformed` and **fails closed to the classic plan gate**, because `uiSurface` and `role` are then unknown and a human gate must not move on a guess. An *absent* config is different and legitimate — flow's documented defaults apply.

## 1. Resolve the repo root and the scratch home

```sh
ROOT=$(git rev-parse --show-toplevel 2>/dev/null)
{ [ -n "$ROOT" ] && [ -d "$ROOT" ]; } || ROOT="${CLAUDE_PROJECT_DIR:-}"
if [ -z "$ROOT" ] || ! cd "$ROOT" 2>/dev/null; then
  echo "[prototype] ROOT-UNRESOLVED — the repo could not be located from cwd $(pwd); flow.config.json was not read, so the pre-execution gate CANNOT be resolved. This is not a clean pass. Re-run from the repo root, or set CLAUDE_PROJECT_DIR."
  exit 0
fi
FLOW_SCRATCH="$ROOT/.flow"
if [ -L "$FLOW_SCRATCH" ]; then
  echo "⚠️ BLOCKER: $FLOW_SCRATCH is a symlink — refusing to write flow scratch through it (CWE-59)." >&2
  exit 1
fi
mkdir -p "$FLOW_SCRATCH"
[ -f "$FLOW_SCRATCH/.gitignore" ] || printf '# Created by flow. Ephemeral scratch; never committed.\n*\n' > "$FLOW_SCRATCH/.gitignore"
SLUG=$(git branch --show-current 2>/dev/null | tr '/' '-' | tr -cd 'A-Za-z0-9._-'); [ -n "$SLUG" ] || SLUG="detached"
PROTO_DIR="$FLOW_SCRATCH/prototypes/$SLUG"
mkdir -p "$PROTO_DIR"
echo "PROTO_DIR=$PROTO_DIR"
python3 ${CLAUDE_PLUGIN_ROOT}/skills/prototype/lib/prototype-gate.py arming --config "$ROOT/flow.config.json"
```

If `ROOT-UNRESOLVED` prints, **stop** and report it.

Read the `arming` verdict. `armed: false` means the project declares **no UI surface** — there is nothing to prototype. Say so plainly and hand back to the classic plan gate. Note that a `role: designer` under `uiSurface: false` is reported as **suppressed**, not silently dropped: tell the human their role setting was overridden and why, so a config contradiction surfaces instead of quietly picking a gate.

## 2. Write the design brief

The brief is the first artifact in this loop, and it is **where the trigger's inputs are declared**. Without it the trigger has nothing to read and fails closed to the classic plan gate.

Write it to the canonical path — `.flow/prototypes/<branch-slug>/brief.md`, which `$PROTO_DIR/brief.md` resolves to — or use the path passed as `$ARGUMENTS`. Brief and prototype share one scratch home so a single path resolves both, and `trigger` reads the brief from exactly there. Shape, per `${CLAUDE_PLUGIN_ROOT}/docs/workflow.md` § "D1 design-brief template":

```markdown
**Mode:** feature · **Surface:** visual

1. **Problem** — …
2. **Whose moment** — …
3. **Constraints** — …
4. **Intended scope** — …
5. **Deliberately excluded** — …
6. **Where this pushes past the literal request** — …
```

- **`Mode`** scopes *this phase only* and is **not inherited by the technical plan**, which declares its own. In a brief, `Mode: tiny` means *"this surface does not earn a prototype"* — a copy change, a spacing or token correction, a single-state tweak. It does not relax any classic-path consequence of `tiny`.
- **`Surface`** is `visual` or `non-visual`. `role: designer` implies `visual` when the line is absent. This is declared rather than inferred **on purpose**: before anything is built there is no diff, so nothing can be measured, and a per-run judgment call would be exactly the un-pinnable input this design rejects.
- **~80 words total** across the six fields (readable in about 20 seconds). If the brief runs materially longer, emit a `[WARN]` and offer to tighten it — **never block on it**. The cap exists so the brief gets read; a long brief is worth flagging, not worth stopping a gate over.

## 3. Resolve the trigger

```sh
python3 ${CLAUDE_PLUGIN_ROOT}/skills/prototype/lib/prototype-gate.py trigger \
  --brief "$PROTO_DIR/brief.md" --config "$ROOT/flow.config.json"
```

| `path` | What you do |
|---|---|
| `prototype-first` | continue to Step 4 |
| `collapsed` | **stop prototyping.** `Mode: tiny` — the surface does not earn a prototype. No review passes, no prototype. Hand back: the pre-execution gate is **plan approval**, unchanged |
| `classic` | **stop.** Hand back to the classic plan gate, unchanged |

Report the resolved `path`, `pre_execution_gate` and the `reasons[]` that produced them **in your hand-off message**. A mis-declared `Surface` is the one failure mode this design cannot prevent — surfacing the resolved values is what makes it visible to the human before they commit, rather than after.

## 4. Review the brief before building anything

```
Skill("flow:review-brief") with the brief path as its argument
```

Pass the path explicitly. Without an argument `/flow:review-brief` falls back to scanning the session transcript for a plan-shaped turn — which is the ambiguous state this phase exists to remove.

Resolve every `decision-required` finding **with the human** before prototyping. A brief that solves the wrong problem costs a discarded prototype; a question costs a moment.

## 5. Prototype — iteratively

Build an HTML prototype at `$PROTO_DIR/prototype.html`. Self-contained, no build step, openable via `file://`.

**HTML for the first build on every platform, web and mobile alike** — a human decision (FB-0113), taken deliberately and broader than the web-only option. The cost it accepts is that infeasibility now surfaces *after* a look has been approved, which is exactly why Step 6 is not optional.

Iterate freely. This is the cheap artifact; changing it is the point.

## 6. The feasibility read — asserted, not advisory

Write `$PROTO_DIR/feasibility.md`. **Required unless `platform` is exactly `web`** — including when `platform` is **unset**, which is the default an iOS consumer most commonly ships and therefore the case a hand-kept list of native platforms would silently miss.

It lives in a sibling file, not inside the HTML: an HTML-comment-embedded block is invisible to the human looking at the rendered page — precisely the reader it exists to warn.

**When the prototype IS the delivery medium** (browser-rendered UI — `platform: web`, or `library`/`none`/`cli`/`tauri` on a project whose surface is a webview), one line is the whole read:

```markdown
**Feasibility** — Delivery medium: browser (the prototype is the artifact, not a proxy). No native translation required.
```

**When it is a proxy** (`ios`, `android`, or anything you do not declare otherwise), the full read — and `ios`/`android` **cannot** take the one-line exit:

```markdown
**Feasibility** — this is an HTML proxy of an ios surface; type rendering, motion and system chrome will differ.

- <affordance> — native-standard | native-custom | expensive | infeasible — <reason naming the platform mechanism>
```

Every row needs a verdict from that closed set. `contract` returns each non-`native-standard` row in `must_surface[]`, and **those rows lead your gate-1 message**: a look the human cannot afford must not be approved before its price is stated.

```sh
python3 ${CLAUDE_PLUGIN_ROOT}/skills/prototype/lib/prototype-gate.py contract \
  --dir "$PROTO_DIR" --config "$ROOT/flow.config.json"
```

`approve` re-runs this and **refuses** on a failure, so a native prototype with no feasibility read cannot reach gate 1 at all. That is what "asserted, not advisory" buys.

## 7. Self-check before spending the human's attention

Spawn both in **one tool message**, fresh context, against the rendered prototype:

| Reviewer | `subagent_type` | Looks for |
|---|---|---|
| Design engineer | `flow:lens-design-engineer` | geometry, spacing rhythm, palette fidelity, motion quality, token use vs hardcoded values |
| UX designer | `flow:lens-ux-designer` | empty/loading/error states, keyboard reachability, focus, contrast, copy |

Give each the **absolute path** to `$PROTO_DIR/prototype.html`, the design-language doc path, and the workspace identity (`repo=… branch=… head=…`). Iterate on what they find, then present.

**This is not a verdict, and the distinction matters.** FB-0066 forbids an implementer *self-certifying* shipped visual work from frames it read itself. Nothing here is certified: the verdict at gate 1 is the **human's**. This pass exists to raise the floor before spending their attention. Run it once on the candidate you intend to present — not once per edit.

*Optional strengthening where a browser is available:* capture a frame and run it through `${CLAUDE_PLUGIN_ROOT}/skills/verify-build/lib/frame-integrity-checklist.md`. Deliberately **not** required — that checklist is written for captured frames and demands a per-edge description; applying it to source HTML is a different activity.

## 8. Present — human gate 1

```sh
python3 ${CLAUDE_PLUGIN_ROOT}/skills/prototype/lib/prototype-gate.py present --file "$PROTO_DIR/prototype.html"
```

This injects the existing click-to-pin annotation layer and **authors no markup of its own**. All flow-authored chrome goes in your chat message instead — which is also why the message has to carry it:

1. **The `file://` path**, so they can open it.
2. **The feasibility summary**, leading, whenever `must_surface[]` is non-empty. Name each expensive/infeasible affordance and its cost.
3. **What approval commits them to** — this look is what the technical plan gets written against.
4. **How to send feedback** — pin comments on the page, press "Copy notes", paste back. Each iteration round re-enters Step 5.

**You may not approve on their behalf, under any circumstances.** There is no inference from silence, no "looks good so proceeding", no treating a stylistic remark as sign-off.

## 9. Capture the approval

Only after the human states approval. Write their **verbatim** words to a file with the `Write` tool, then:

```sh
python3 ${CLAUDE_PLUGIN_ROOT}/skills/prototype/lib/prototype-gate.py approve \
  --dir "$PROTO_DIR" --quote-file "$PROTO_DIR/approval-quote.txt" --config "$ROOT/flow.config.json"
```

The quote arrives **only as a file path**. There is deliberately no `--quote` string flag: untrusted text does not belong on a command line (FB-0108), and this is the first new interface since that rule landed.

Then **commit the two lines `approve` prints into the plan doc** (`flow.config.json.planPath`):

```markdown
**Pre-execution gate:** prototype
**Prototype approved:** `<sha256>` · "<verbatim quote>" · repo=… branch=… head=…
```

`.flow/` is gitignored, so `approval.json` does not survive the workspace. **These committed lines are the durable half**, and `gate-execute` reads them and nothing else. Skipping this step leaves the guard armed on state that can vanish — which is how a lost workspace turns into no human gate at all.

## 10. Hand off

Write the technical plan against the approved prototype, then:

```sh
python3 ${CLAUDE_PLUGIN_ROOT}/skills/prototype/lib/prototype-gate.py gate-execute --plan "$PLAN_PATH"
```

**Do not proceed to Execute on `ok: false`.** It means the plan declares a prototype gate but carries no approval digest, or resolves no active Spec-walk block — in both cases nothing has been approved and nothing exists to build against. That is the condition FB-0080 named.

**There is no second human gate here.** The human already gated, at the prototype. The plan is machine-reviewed:

- `/flow:critique-plan` — scope drift, spec violation, incoherence.
- `/flow:audit-plan` — unverified assumptions and recall.
- `/flow:audit-coverage` **in prototype-source mode, once that mode ships** — completeness.

**Be honest about which of those is live.** Until the source mode exists, this review is a **form and coherence check and explicitly not a completeness check** — the §9.3 spike measured this exact reviewer set catching 1 of 12 real coverage gaps, and the completeness backstop is the existing `/flow:audit-coverage` running post-execution against a real diff at `/flow:ship` Step 2. A gap is caught **late, not never**. Say that plainly rather than implying the plan was fully checked.

Phase 3 (auto-writing the plan and machine-gating it) is **not built**; it is gated on §9.3. Do not imply otherwise.

## Gotchas

- **Never run the ship pipeline from this phase.** No `/flow:ship`, no `/flow:ship-spike`, no `/flow:staff-review`, no `/simplify`, no eval harness, no history or feedback entry. Iteration is the point, and each of those turns a cheap artifact into an expensive one.
- **Never approve on the human's behalf.** The one rule with no exception.
- **A `collapsed` or `classic` verdict is a success, not a failure.** Proportionality is a first-class constraint: three review passes and a prototype cost more than a small change is worth. Hand back cleanly.
- **Don't skip the brief because the change "seems obviously visual."** The brief is where `Mode` and `Surface` are declared; skipping it leaves the trigger with nothing to read, and it fails closed to the classic plan gate.
- **Don't edit the prototype after approval without re-approving.** `verify` detects it by sha256, and the record stops describing what the human actually saw.
