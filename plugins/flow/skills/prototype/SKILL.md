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

State the resolved gate in **one line** ("This is going to prototype approval, not plan approval — because …"), and keep the raw `reasons[]` available if they ask. A mis-declared `Surface` is the one failure mode this design cannot prevent, so the resolved value must be visible before they commit — but a four-sentence engine dump competes with the gate-1 budget below for the same scarce attention, and loses to it.

## 4. Review the brief before building anything

```
Skill("flow:review-brief") with the brief path as its argument
```

Pass the path explicitly. Without an argument `/flow:review-brief` falls back to scanning the session transcript for a plan-shaped turn — which is the ambiguous state this phase exists to remove.

Resolve every `decision-required` finding **with the human** before prototyping. A brief that solves the wrong problem costs a discarded prototype; a question costs a moment.

## 5. Prototype — iteratively

**Read `flow.config.json.designLanguagePath` before you write any markup.** Build against its tokens, hue tiers, radii and type scale. Step 7 hands that same doc to two reviewers who grade the result by it — using it as a rubric but not as a build input guarantees at least one rework round on every run, spending exactly the attention this phase exists to conserve. If the project has no such doc, **say so in the hand-off**: the prototype is then ungrounded and the human's eye is the only standard, which they should know before they look.

Build an HTML prototype at `$PROTO_DIR/prototype.html`. Self-contained, no build step, openable via `file://`.

- **Show the states the surface actually has** — empty, loading, error, focus — not only the happy path. Step 7's UX lens grades them, and a prototype that only shows the good case hides the decisions most worth a designer's opinion.
- **Frame a mobile prototype at a realistic viewport.** FB-0113 makes HTML the first build medium for mobile too, so a desktop-width page can pass the feasibility read as an honest proxy while being a poor one. The feasibility read covers native *translation*; it does not cover viewport *fidelity*.

**HTML for the first build on every platform, web and mobile alike** — a human decision (FB-0113), taken deliberately and broader than the web-only option. The cost it accepts is that infeasibility now surfaces *after* a look has been approved, which is exactly why Step 6 is not optional.

Iterate freely. This is the cheap artifact; changing it is the point.

## 6. The feasibility read — asserted, not advisory

Write `$PROTO_DIR/feasibility.md`. **Required unless `platform` is exactly `web`** — including when `platform` is **unset**, which is the default an iOS consumer most commonly ships and therefore the case a hand-kept list of native platforms would silently miss.

It lives in a sibling file, not inside the HTML: an HTML-comment-embedded block is invisible to the human looking at the rendered page — precisely the reader it exists to warn.

**When the prototype IS the delivery medium**, one line is the whole read. Eligible platforms are an **allowlist** — `web`, `library`, `none`, `cli`, `tauri` — so a platform value nobody has considered yet (a future `react-native`, `flutter`, `macos`, `electron`) **cannot** declare its way out of the guard; it is treated as a proxy until someone deliberately adds it here:

```markdown
**Feasibility** — Delivery medium: browser (the prototype is the artifact, not a proxy). No native translation required.
```

**When it is a proxy** (`ios`, `android`, or anything you do not declare otherwise), the full read — and `ios`/`android` **cannot** take the one-line exit:

```markdown
**Feasibility** — this is an HTML proxy of an ios surface; type rendering, motion and system chrome will differ.

- <affordance> — native-standard | native-custom | expensive | infeasible — <reason naming the platform mechanism>
```

`ios` and `android` are outside the allowlist above, so they always need the full read. Every row needs a verdict from that closed set. `contract` returns each non-`native-standard` row in `must_surface[]`, and **those rows lead your gate-1 message**: a look the human cannot afford must not be approved before its price is stated.

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

Give each the **absolute path** to `$PROTO_DIR/prototype.html`, the design-language doc path, **`$PROTO_DIR/brief.md`**, and the workspace identity (`repo=… branch=… head=…`). The brief matters: it holds *Constraints* and *Deliberately excluded*, and without it the UX lens will flag states the brief deliberately scoped out — the same noise the "prototype under iteration" calibration exists to suppress, arriving through a different door. Iterate on what they find, then present.

**This is not a verdict, and the distinction matters.** FB-0066 forbids an implementer *self-certifying* shipped visual work from frames it read itself. Nothing here is certified: the verdict at gate 1 is the **human's**. This pass exists to raise the floor before spending their attention. Run it once on the candidate you intend to present — not once per edit.

*Optional strengthening where a browser is available:* capture a frame and run it through `${CLAUDE_PLUGIN_ROOT}/skills/verify-build/lib/frame-integrity-checklist.md`. Deliberately **not** required — that checklist is written for captured frames and demands a per-edge description; applying it to source HTML is a different activity.

## 8. Present — human gate 1

```sh
python3 ${CLAUDE_PLUGIN_ROOT}/skills/prototype/lib/prototype-gate.py present --file "$PROTO_DIR/prototype.html"
```

This writes **`prototype.presented.html`** — the prototype plus the existing click-to-pin annotation layer, and **no markup of flow's own**. It does **not** modify `prototype.html`: the source stays byte-identical, because that is the file `approve` hashes and therefore the thing the human is approving. Give the human the *presented* path to open. All flow-authored chrome goes in your chat message instead — which is also why the message has to carry it:

**Budget: ~100 words.** This is the one message the human is guaranteed to read, and the complaint this whole phase answers is *"the messages I come to are too long and I don't really read them and I just end up approving anyway."* A gate that relocates the reading burden instead of removing it has not fixed anything. Link first, costs next, everything else on request. Note the asymmetry this corrects: the brief — which only reviewer agents read — carries a hard ~80-word cap, so applying no budget here would have disciplined the artifact the robots read and exempted the one the human reads.

1. **The `file://` path** to the file `present` names in `presented` — so they can open it. Mention that the small floating comment dock is **flow's**, not part of the design.
2. **The feasibility summary**, leading, whenever `must_surface[]` is non-empty. Name each expensive/infeasible affordance and its cost.
3. **What approval commits them to** — this look is what the technical plan gets written against.
4. **How to send feedback** — click an element to pin a comment, press **"Copy all"**, paste back. Quote that label exactly; it is what the toolbar says. Each iteration round re-enters Step 5.

**If `present` returned `injected: false`, say so and change the ask.** The overlay could not be loaded, so the page is view-only: tell them it takes no pins and ask for feedback in chat instead. Silently repeating "pin comments on the page" sends them clicking at a page that cannot respond, at the one moment their attention was budgeted for.

**You may not approve on their behalf, under any circumstances.** There is no inference from silence, no "looks good so proceeding", no treating a stylistic remark as sign-off.

## 9. Capture the approval

Only after the human states approval. Write their **verbatim** words to a file with the `Write` tool, then:

```sh
python3 ${CLAUDE_PLUGIN_ROOT}/skills/prototype/lib/prototype-gate.py approve \
  --dir "$PROTO_DIR" --quote-file "$PROTO_DIR/approval-quote.txt" --config "$ROOT/flow.config.json"
```

The quote arrives **only as a file path**. There is deliberately no `--quote` string flag: untrusted text does not belong on a command line (FB-0108), and this is the first new interface since that rule landed.

`approve` prints **both** committed lines; paste them into the plan doc (`flow.config.json.planPath`) verbatim, **above the active `**Spec-walk:**` block** — `gate-execute` requires both, and it reads them only from the header region above that heading. That scoping is what stops a *retained* (merged) PR's approval digest lower in the same file from satisfying this PR's gate — a real bypass in a plan doc that keeps shipped blocks, which is the convention this repo and most flow consumers use:

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
- `/flow:audit-coverage` **in prototype-source mode, once that mode ships** — completeness, **best-effort**. Four live runs of this judgment have found 10, 5, 0-of-5 and 2-of-5 of the gaps present, at full precision throughout; the 0-of-5 was in its long-standing **diff** mode, so the variance is a property of the judgment, not of the new input path. It raises the bar; it does not guarantee completeness. **And behaviour added after the plan is written — during `/simplify` and staff-review — is exactly the behaviour least likely to be declared**, so a gap can reach Execute undeclared even when the pass runs clean.

**Be honest about which of those is live, and about what the live one is worth.** Until the source mode exists, this review is a **form and coherence check and explicitly not a completeness check** — the §9.3 spike measured this exact reviewer set catching 1 of 12 real coverage gaps. Once it ships, completeness is *raised*, not *assured*. Either way the backstop is the existing `/flow:audit-coverage` running post-execution against a real diff at `/flow:ship` Step 2, so a gap is caught **late, not never**. Say that plainly rather than implying the plan was fully checked — and note that the one guarantee here that is **not** judgment is `gate-execute`'s: a plan *exists*. That is mechanical, and with completeness only partly checked it carries more of the weight than it looks like it does.

Phase 3 (auto-writing the plan and machine-gating it) is **not built**; it is gated on §9.3. Do not imply otherwise.

## Gotchas

- **Never run the ship pipeline from this phase.** No `/flow:ship`, no `/flow:ship-spike`, no `/flow:staff-review`, no `/simplify`, no eval harness, no history or feedback entry. Iteration is the point, and each of those turns a cheap artifact into an expensive one.
- **Never approve on the human's behalf.** The one rule with no exception.
- **A `collapsed` or `classic` verdict is a success, not a failure.** Proportionality is a first-class constraint: three review passes and a prototype cost more than a small change is worth. Hand back cleanly.
- **Don't skip the brief because the change "seems obviously visual."** The brief is where `Mode` and `Surface` are declared; skipping it leaves the trigger with nothing to read, and it fails closed to the classic plan gate.
- **Don't edit the prototype after approval without re-approving.** `verify` detects it by sha256, and the record stops describing what the human actually saw. (Re-running `present` is safe — it writes a separate file and leaves the source alone.)
- **The committed digest evidences an approval; it does not prove one.** `gate-execute` asserts the plan doc carries a well-formed `**Prototype approved:**` line — a sha-shaped token and a non-empty verbatim quote — plus an active Spec-walk. It cannot re-verify the sha, because the artifact it hashes lives in gitignored `.flow/`. So it is a real check against *the line being absent, empty, or hand-waved*, and not a cryptographic proof that a human looked. Say that honestly rather than implying more.
