---
name: verify-build
description: >
  Plan-driven behavioral verification gate at /flow:ship Step 2. Wraps
  bundled /verify (and transitively /run + /run-skill-generator) with
  flow-specific orchestration: extracts acceptance criteria from the
  current PR plan's Spec-walk checkboxes, adversarially transforms each
  criterion into "what would break this" cases the implementer didn't
  author, drives bundled /verify against the criteria list, judges
  observations per-dimension with an Unknown-aware rubric, and blocks
  ship on Unknown or FAIL. Catches the Potemkin-interface /
  hallucinated-success class no static reviewer catches. Use during
  /flow:ship's final-pass review; invokable directly via /flow:verify-build
  for mid-iterate behavioral checks (though bundled /verify is the
  preferred ad-hoc tool for that — see workflow.md). Composes with
  /flow:red-team (static adversarial code review, PR K) at different
  layers — both fire from /flow:ship Step 2.
allowed-tools: Read, Glob, Grep, Bash, Skill, Agent
---

# Behavior verification (verify-build)

Cold-runs the built artifact against the plan's Spec-walk acceptance criteria and judges observations against intent, returning a PASS / FAIL / Unknown verdict (exit 1 on FAIL/Unknown). Two callers consume that verdict differently: at the **Step 8/9 readiness boundary** it's the *discovery* gate (the readiness predicate requires a positive PASS to auto-advance — FB-0018); inside **`/flow:ship` Step 2** it's a *confirmation* re-run — a non-converging FAIL/Unknown regression routes to a draft PR + manifest rather than hard-halting (`/flow:ship-spike` still halts — spike scope). Invocable directly when the user wants flow's plan-criteria verdict vs bundled `/verify`'s freeform observation.

## When to invoke

- `/flow:ship` invokes this automatically as one of the three final-pass reviewers (security + accessibility + verify-build).
- The user asks: "verify the build", "verify against the plan", "/flow:verify-build", "does this actually work end-to-end".
- A feature touched behavior the static reviewers (security, accessibility, staff-review) can't catch — e.g. "button now triggers correct API call", "form validates per spec", "state transitions match plan".

Skip if `flow.config.json.verifyEnabled` is `false` (project-wide opt-out) or `flow.config.json.platform` resolves to `library` / `none` (no runnable target).

## Project context (resolved at invocation)

- Project config: !`cat flow.config.json 2>/dev/null || echo "(no flow.config.json — using built-in defaults)"`
- Default branch: !`git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@' || cat flow.config.json 2>/dev/null | jq -r '.defaultBranch // "main"' 2>/dev/null || echo "main"`
- Plan doc: !`PLAN=$(cat flow.config.json 2>/dev/null | jq -r '.planPath // empty'); [ -z "$PLAN" ] && PLAN="dev-docs/plan.md"; [ -f "$PLAN" ] && echo "$PLAN" || echo "(no plan doc at $PLAN)"`
- Verify enabled: !`cat flow.config.json 2>/dev/null | jq -r '.verifyEnabled // true'`
- Project run skill: !`ls -d .claude/skills/run-*/ 2>/dev/null | head -1 || echo "(none — heuristic launch only)"`

## Bundled-skill integration contract

`/flow:verify-build` is a thin orchestrator. The execution layer is bundled Claude Code skills, NOT reimplemented in flow:

| Layer | Owner | Behavior |
|---|---|---|
| Launch recipe (per-project) | `.claude/skills/run-<name>/` (scaffolded by bundled `/run-skill-generator`) | Project-specific build + launch invocation. Committed to repo. |
| Launch dispatch | bundled `/run` | Reads recipe if present; falls back to heuristic by project type (CLI / server / TUI / browser-driven / library / Electron). |
| Run + observe loop | bundled `/verify` | Invokes `/run` + drives the running app + reports observations. Output is freeform stdout per Anthropic's published docs. |
| **Plan-driven gate** | **`/flow:verify-build` (this skill)** | Extracts criteria from plan, adversarializes, judges, gates ship. |

### Documented contract for bundled `/verify` (as of 2026-05-28)

- **Input:** invocable as `Skill('verify')`; accepts no documented structured input parameters — agents pass instructions in conversational form.
- **Output (DOCUMENTED):** freeform stdout text describing what was launched, what was observed, what behavior matched/didn't match intent. **No structured JSON schema. No documented PASS/FAIL contract.**
- **Output (UNKNOWN — empirical verification deferred to first real verify-build run):**
  - Whether screenshots are included structurally in the response, or only narrated.
  - Whether `/verify` emits a parseable success/failure marker at end of output.
  - Whether `/verify` accepts criteria-list input (e.g. "verify these specific behaviors: ...") or only ad-hoc descriptions.
  - Exit-code semantics if invoked outside of `Skill()` (e.g. via direct CLI).
- **Delegation:** `/verify` invokes `/run` internally. `/run` defers to `.claude/skills/run-<name>/` if present; otherwise falls back to heuristic launch by project type. Per Anthropic docs, heuristic launch is "unreliable for projects that need anything beyond a standard launch: a database, an env file, a graphical session, a multi-step build."
- **Project-skill requirement:** Step 1 of this skill emits a loud warning if no `.claude/skills/run-*/` exists, naming `/run-skill-generator` as the one-line fix. Does NOT block — heuristic launch may still work for simple projects.

**Empirical verification TODO (Phase 1 follow-up):** at first real `/flow:verify-build` run against a known-good toy project (`evals/fixtures/verify-toy-web-app/`), capture actual `/verify` output shape and update this section with the empirical contract. If screenshots are NOT returned structurally, remove the pairwise-comparison instruction from `lib/rubric.md` (Decision 4 resolution).

## 1. Pre-flight

### 1.0. External-CLI / MCP dependency check (BLOCKING)

Per FB-0009: fail fast at workflow entrypoint if mandatory tools are missing, with clean install hint. Does NOT block on missing `/run-skill-generator` recipe (warning only — see Step 1.1).

```sh
# POSIX-portable: space-delimited string (NOT bash array — dash compat).
MISSING=""
command -v jq >/dev/null 2>&1 || MISSING="$MISSING jq"
command -v git >/dev/null 2>&1 || MISSING="$MISSING git"
if [ -n "$MISSING" ]; then
  MISSING_TRIMMED=$(echo "$MISSING" | sed 's/^ //')
  echo "⚠️ BLOCKER: /flow:verify-build requires $MISSING_TRIMMED (missing on PATH)." >&2
  echo "   Install:" >&2
  echo "     macOS:         brew install$MISSING" >&2
  echo "     Debian/Ubuntu: apt install$MISSING" >&2
  exit 1
fi
```

Per-platform MCPs (Playwright MCP for web, XcodeBuildMCP for iOS, mobile-mcp for Android) are NOT checked here — bundled `/run` and `/verify` discover and use whatever MCPs are available. If a required MCP is missing for the detected platform, `/verify` will report inability to launch and judge will return Unknown → ESCALATE per FB-0011.

### 1.1. Project run skill detection (WARN-only)

Per the plan-critic BLOCKER absorbed during PR Q scoping: bundled `/run` and `/verify` work best with a per-project recipe scaffolded by `/run-skill-generator`. Without it, heuristic launch may fail on projects needing env files, DBs, multi-step builds, or non-standard scheme/package selection.

```sh
RUN_SKILLS=$(ls -d .claude/skills/run-*/ 2>/dev/null)
if [ -z "$RUN_SKILLS" ]; then
  echo "⚠️ WARN: no .claude/skills/run-*/ found." >&2
  echo "   /flow:verify-build relies on bundled /run + /verify, which work best" >&2
  echo "   with a project-specific launch recipe. Run /run-skill-generator once" >&2
  echo "   (Anthropic bundled skill) to teach /run + /verify how to launch your" >&2
  echo "   project. Continuing with heuristic launch — may fail on complex projects." >&2
fi
```

### 1.2. Skip-path checks

Resolve `flow.config.json.verifyEnabled` and `flow.config.json.platform`:

```sh
VERIFY_ENABLED=$(jq -r '.verifyEnabled // true' flow.config.json 2>/dev/null)
PLATFORM=$(jq -r '.platform // empty' flow.config.json 2>/dev/null)

if [ "$VERIFY_ENABLED" = "false" ]; then
  echo "[verify-build] disabled via flow.config.json.verifyEnabled=false; skipping."
  exit 0
fi

case "$PLATFORM" in
  library|none)
    echo "[verify-build] platform=$PLATFORM has no runnable target; skipping."
    exit 0
    ;;
esac
```

Note: when `platform` is unset, bundled `/run` will autodetect — no flow-side autodetect needed.

## 2. Spike-mode branch

Detect spike mode and short-circuit criteria extraction. Three triggers — any one enables spike mode:

**Spike mode fires on any of three triggers:**

1. **Caller signal.** `/flow:ship-spike` invokes this skill with the contextual instruction that spike mode applies (the agent reading both SKILL.md files treats the parent ship-spike context as the trigger; no shell-level `--spike` flag is parsed). When the calling skill is `/flow:ship-spike`, treat `SPIKE=true`.
2. **Missing plan.** `flow.config.json.planPath` doesn't resolve to an existing file.
3. **No Spec-walk block.** Plan file exists but lacks a `**Spec-walk:**` heading.

Triggers 2 and 3 are detected mechanically:

```sh
SPIKE=false
PLAN_PATH=$(jq -r '.planPath // empty' flow.config.json 2>/dev/null)
[ -z "$PLAN_PATH" ] && PLAN_PATH="dev-docs/plan.md"

if [ ! -f "$PLAN_PATH" ]; then
  SPIKE=true
  SPIKE_REASON="no plan at $PLAN_PATH"
elif ! grep -q '\*\*Spec-walk' "$PLAN_PATH"; then
  SPIKE=true
  SPIKE_REASON="plan at $PLAN_PATH has no **Spec-walk:** block"
fi

# Trigger 1 (caller signal) is set by prose above when invoked from /flow:ship-spike;
# detection there is contextual, not shell-positional.

if [ "$SPIKE" = "true" ]; then
  echo "[verify-build] spike mode active: ${SPIKE_REASON:-invoked by /flow:ship-spike}"
fi
```

When `SPIKE=true`:
- Skip Step 3 (extract-criteria) and Step 4 (adversarial transformation).
- Use the fixed 3-check rubric at `${CLAUDE_PLUGIN_ROOT}/skills/verify-build/lib/spike-rubric.md` as the verification script for Step 5's `Skill('verify')` invocation. The rubric's three checks (Launch / One happy step / No log errors) become the "criteria" passed through.
- At Step 6, spawn ONLY the `correctness` judge (regression + scope-creep are not meaningful without a plan). The judge uses `lib/spike-rubric.md` as its system prompt instead of `lib/rubric.md`.
- At Step 7, treat the single correctness verdict per check as the per-criterion `aggregated_verdict` directly. Same Unknown ⇒ exit 1 contract.
- At Step 8, the findings buffer includes `metadata.spike_mode: true`; per-criterion `verdicts.regression` and `verdicts.scope-creep` are emitted as `Unknown` with the canonical placeholder shape — `evidence: ["(spike mode — dimension not applicable)", "<verbatim criterion text>"]` (preserves the schema's exactly-2 evidence requirement) and `notes: "spike mode — dimension not applicable"` — to keep the schema shape stable for downstream consumers (Step 4a, HTML renderer).

Spike mode applies the same evidence + Unknown discipline as full mode — Unknown ⇒ ESCALATE per FB-0011 ⇒ exit 1. The lower bar is in the *number* of checks (3 fixed vs N plan-derived), not in the verdict discipline.

**Why three triggers, not just `--spike`:** Trigger 1 is the explicit user choice (`/flow:ship-spike` invokes verify-build with `--spike`). Triggers 2 and 3 are the graceful-fallback path so that a project running `/flow:verify-build` directly with a missing or malformed plan gets a useful smoke check instead of a hard failure. The fallback is documented in `lib/spike-rubric.md` § "When spike mode fires."

## 3. Extract criteria from plan

Parse the current PR's `**Spec-walk:**` block:

```sh
PLAN=$(jq -r '.planPath // empty' flow.config.json 2>/dev/null)
[ -z "$PLAN" ] && PLAN="dev-docs/plan.md"

if [ ! -f "$PLAN" ]; then
  echo "[verify-build] no plan at $PLAN — falling back to spike mode."
  exec "$0" --spike  # PLACEHOLDER — actual re-entry shape TBD in Phase 2
fi

python3 "${CLAUDE_PLUGIN_ROOT}/skills/verify-build/lib/extract-criteria.py" "$PLAN"
```

`extract-criteria.py` emits one criterion per `- [ ]` checkbox under `**Spec-walk:**`. If no Spec-walk block found, emits warning + falls back to spike mode.

## 4. Adversarial transformation

For each criterion, spawn a Agent subagent (fresh-context) with the prompt at `${CLAUDE_PLUGIN_ROOT}/skills/verify-build/lib/adversarial.md` to generate 1–2 "what would break this" cases. The adversarial subagent runs in a fresh context — the implementing agent doesn't grade its own homework.

Output: augmented criteria list = original criteria + 1–2 adversarial cases per original.

## 5. Invoke bundled `/verify`

Pass the augmented criteria list to bundled `/verify` as the verification script:

```
Skill("verify")
```

Bundled `/verify` calls `/run` internally for launch, drives the running app per the criteria list, and reports observations. Flow does NOT reimplement any of this.

**Budget cap:** track tool-call count via `flow.config.json.verifyBudgetCalls` (default 60). If exceeded, abort the verify invocation and emit `Unknown` for all unjudged dimensions → ESCALATE per FB-0011.

## 5a. Capture-and-persist visual frames (V2)

**Activation (all must hold, else §5a is N/A — say so explicitly):** (a) **not** spike mode (spike skips Steps 3–4, so it never reaches §5a); (b) the plan's `**Spec-walk:**` criteria extracted cleanly — a malformed Spec-walk heading yields 0 criteria → spike fallback → §5a silently skipped, so a plan with a `Visual-walk` block but a non-canonical Spec-walk heading captures nothing (a known routing fragility; see roadmap follow-up); (c) the plan declares a `Visual-walk` block on a `uiSurface:true` project. Non-UI / no `Visual-walk` → skip; visual capture is N/A.

**Deriving the capture state-set.** The `Visual-walk` block (V1) is a list of checkable visual *assertions* ("empty state renders", "primary button uses the accent token", "enter motion ≤200ms"), **not** an enumerated state list. §5a captures one frame per distinct *app state* those assertions name or imply (empty / loading / error / interaction / a11y / happy-path), deduplicated. This derivation is **prompt-driven** — there is no `extract-visual-states.py` parser yet (a routed follow-up) — so **list the state-set you derived** in the run, and treat any state you cannot tie to a declared assertion as out of scope. If the block is only an inline `(Visual-walk)` parenthetical with no enumerable states, capture the **primary/launch state only** and mark the rest `not_tested` — never invent a rich state-set from prose the plan didn't declare.

Bundled `/verify` **narrates** screenshots to the orchestrator — it does NOT hand structured frames to the fresh-context judges (SV2-spike). So **flow owns capture-and-persist.** For each derived state, **in this exact order**:

1. **Reach the state — the drive ladder.** Try in order: (a) the platform's **UI-automation** tool (tap/gesture/type — XcodeBuildMCP `tap`/`type_text`, Playwright click, etc.) *if the MCP config exposes one*; (b) a documented **launch-arg / env hook** the app provides for state injection (e.g. a debug/mock toggle); (c) **if neither can reach the state, STOP — mark it `Unknown` + a `not_tested[]` line and move on.** Do NOT screenshot whatever happens to be on screen. Many MCP configs expose only `screenshot` + the a11y tree and *no* drive primitive — then only the launch state is reachable and every other state is honestly `Unknown`. Naming a drive prerequisite is the consumer's job, not §5a's to assume.
2. **Assert the state via the a11y tree BEFORE the screenshot (load-bearing).** Call the a11y-snapshot tool (`snapshot_ui` / equivalent) and **confirm it shows the intended state** (expected labels/markers). Only on a match do you proceed to capture. **Never screenshot-then-assume** — an un-gated capture silently persists wrong-state frames (this is flow's own "read state from the a11y tree, not pixels" SV2 principle applied to *capture ordering*; a cold run that skipped this persisted a drifted frame that the pairwise judge then correctly FAILed). If the a11y snapshot doesn't show the intended state, treat it as not-reached (→ 1c).
3. **Capture the frame** via the platform's screenshot MCP — browser MCP for `web`, **XcodeBuildMCP `screenshot`** for `ios`, mobile-mcp for `android`; never hardcode a platform. Most native simulator/device tools return a **file path** (XcodeBuildMCP returns a path to a pre-optimized frame) — copy it into the assets dir; if a tool returns only image data, write the bytes yourself. Resize to ~460–620px if the tool didn't (the renderer does not resize); never paste base64 frame data into the working context.
4. **Persist + reference.** Persist to `<dirname(verifyReportPath)>/assets/<state-slug>.<ext>`. Write the `screenshot` observation's `content` as the path **relative to the report directory** — i.e. `assets/<state-slug>.<ext>` — because Step 10 invokes the renderer with `--assets-dir <dirname(verifyReportPath)>`, so it resolves `content` against the report dir. (Do NOT make `content` relative to the assets dir itself — `assets/x.png` is relative to the report dir, the assets dir's *parent*.) Also write the `a11y_snapshot` observation from step 2 (labels / copy / status — text, incl. network status, is unreliable from pixels).

**A derived state with no captured frame** (un-reachable per step 1, or a11y-assertion failed per step 2) → `Unknown` (Step 7) + a `not_tested[]` line. Never a silent gap; the renderer makes it visible (Step 10).

**Baseline (for the pairwise rubric, Step 6).** A state's baseline lives at `<state-slug>.baseline.<ext>` in the assets dir (a distinct name from the current `<state-slug>.<ext>` — keep current / baseline frames separable, never one ambiguous flat name). If a baseline exists (from an earlier accepted run), pass it to the judges alongside the new frame for pairwise comparison (`rubric.md` § VLM). **First run = no baseline:** seed it (copy `<state-slug>.<ext>` → `<state-slug>.baseline.<ext>`); visual-*layout* claims resolve `Unknown` until a baseline exists (acceptable — text/state claims still resolve from the a11y tree). Absolute single-frame scoring stays discouraged.

**Budget.** In a capture-owning run, count flow's own capture/drive/a11y tool-calls toward `metadata.verify_budget_calls_used` (bundled `/verify` is no longer the only caller); the cap still forces `Unknown` on overrun.

## 6. Per-dimension parallel judging

Spawn N parallel Agent subagent (fresh-context)s — one per dimension — each with the rubric prompt at `${CLAUDE_PLUGIN_ROOT}/skills/verify-build/lib/rubric.md`. Default dimensions:

- **correctness** — does each criterion's observed behavior match intent?
- **regression** — did anything else break that wasn't a criterion?
- **scope-creep** — did the implementation do more than the plan said?

Each judge returns `PASS | FAIL | Unknown` per criterion + two-citation evidence (the observation + the plan-criterion / regression-source / scope-source). Parallel for speed + position-bias isolation.

## 7. Aggregate verdict

```
Any dimension returns FAIL for any criterion    ⇒ exit 1 (gate blocks)
Any dimension returns Unknown for any criterion ⇒ exit 1 (FB-0011: ESCALATE on uncertainty)
All dimensions PASS for all criteria            ⇒ exit 0
```

Per FB-0011 (autonomy bar): Unknown is gate-blocking, not advisory. The judge is forced to admit ignorance; the user adjudicates.

## 8. Emit findings buffer

Write structured JSON to `flow.config.json.verifyFindingsPath` (default `/tmp/flow-verify-findings.json`) per the schema at `${CLAUDE_PLUGIN_ROOT}/skills/verify-build/lib/findings-schema.json`. A canonical example is at `${CLAUDE_PLUGIN_ROOT}/skills/verify-build/lib/findings-example.json` (mixed-verdict shape: one criterion PASS, one criterion Unknown — exactly the case Phase 9's smoke harness will assert against).

The schema pins these properties (binding — consumers depend on them):

- **`schema_version`**: `"1.0"` (bumps only on breaking changes; additive changes do not bump).
- **`metadata`**: branch, head SHA short, plugin version, platform hint (`web`/`ios`/`android`/`tauri`/`cli`/`library`/`none`/`unknown`), verify budget used + overrun flag, spike mode flag.
- **`overall_verdict`**: `"PASS"` / `"FAIL"` / `"Unknown"` — aggregated per Step 7.
- **`exit_code`**: `0` (PASS) or `1` (FAIL or Unknown). Pins the gate-blocking contract.
- **`criteria[]`**: per-criterion entries with `text`, `adversarial_cases`, `observations[]` (each with `type` discriminator: `screenshot` | `a11y_snapshot` | `network` | `console` | `log` | `stdout` | `exit_code` | `narrative`), `verdicts.{correctness,regression,scope-creep}` (each with verdict + exactly-2 evidence quotes + notes), and per-criterion `aggregated_verdict`.
- **`not_tested[]`**: closed-form per-platform checklist from `lib/not-tested-checklist.md` with `item` text, `tested` boolean, optional `rationale`.
- **`criteria[].grounding`** *(optional; V2)*: why the surface looks/behaves as it does — `{type: need|design-language|craft-commitment|open-question, statement, citations[], decision_test?}`. Citations resolve from `flow.config.json.{specPath,designLanguagePath}` or the plan's Spec-walk — **never hardcoded doc names**. Captured for criteria with a visual/UX dimension; the renderer (Step 10) shows it as the rationale callout. Operationalizes FB-0040 (rationale carried).
- **`open_questions[]`** *(optional, top-level; V2)*: subjective human-facing calls — `{question, rationale, recommended_default, user_need_lens, routing: this-iteration|future-planning}`. **DISTINCT from `Unknown`** (epistemic). An `open_questions` entry with `routing: this-iteration` is the mechanical signal that **blocks Step 8 auto-advance** in the loop (mirrors an unresolved MEDIUM assumption — see `docs/workflow.md` Step 8); `future-planning` routes to the roadmap. The renderer surfaces these as the standalone "Open questions for you" block.

**Renderer (V3a):** this buffer is the input to `lib/render-report.py`, which emits the ephemeral HTML walkthrough at `flow.config.json.verifyReportPath` (Step 10). The shape is a superset of what the renderer needs — `timestamp_offset_ms` orders the evidence timeline; the `type` discriminator lets each observation lay out distinctly; `grounding` + `open_questions` (V2) fill the rationale + human-question layers. The durable visual record (`visual-history.html`) is a separate, curated artifact (V3b, a later PR).

### How `/flow:ship` Step 4a reads this buffer (Phase 7 integration; stub here)

When `/flow:ship` Step 2 invokes `Skill("flow:verify-build")` and verify-build exits, the buffer at `flow.config.json.verifyFindingsPath` is the structured handoff to `/flow:ship` Step 4a (synthesize session feedback). Step 4a:

1. Reads the buffer (defaulting to `/tmp/flow-verify-findings.json` if `verifyFindingsPath` unset).
2. For each criterion with `aggregated_verdict ∈ {FAIL, Unknown}`, derives a candidate FB-XXXX entry. The candidate's "What was said" field cites the criterion text + the per-dimension evidence quotes; the "Synthesized rule" field is left for the human-merge gate to author (Step 4a does not invent prose for FB entries).
3. Routes candidates per the source-diversity bar from `${CLAUDE_PLUGIN_ROOT}/docs/workflow.md` § "Continuous improvement" (2-of-3 evidence: recurrence in time / two reviewers / one review + user correction). Verify-build findings count as one review source; pair with another source before promoting to a written FB entry.

The actual `/flow:ship` Step 4a code edit is Phase 7 work. This section documents the contract Phase 7 implements.

### Findings-buffer lifecycle

- Verify-build creates the buffer fresh at Step 8 (overwrites any prior buffer at the path).
- `/flow:ship` Step 4a reads the buffer immediately after its `Skill("flow:verify-build")` call returns.
- After `/flow:ship` completes (PR opened or noop), the buffer is left in place for inspection. Cleanup is the consumer's responsibility (defaults to `/tmp/` so it gets wiped on reboot).
- Concurrent verify-build runs against the same buffer path WILL clobber each other. If a future workflow runs verify-build in parallel (unlikely but possible), each run should override `verifyFindingsPath` to a unique path via the slot. Single-run-per-ship is the v1 contract.

## 9. Render "what we did NOT test" checklist

Per-platform fixed checklist from `${CLAUDE_PLUGIN_ROOT}/skills/verify-build/lib/not-tested-checklist.md`. Closed-form (✗ / ✓ per item); agent flips ✗ → ✓ only where it actually tested. Emitted to stdout for the PR-body author.

Example (web):
```
What we did NOT test:
  [✗] Real device (used Playwright headless)
  [✗] Real network (used dev server)
  [✗] Authenticated 2FA flow
  [✗] Push notifications
  [✗] Payment flows
  [✗] >1 viewport size
  [✗] >1 locale
```

## 10. Render the ephemeral HTML walkthrough (V3a)

After the buffer is written (Step 8), render it to a single self-contained HTML file — the artifact the human opens at the merge gate:

```sh
REPORT=$(jq -r '.verifyReportPath // "/tmp/flow-verify-report.html"' flow.config.json 2>/dev/null)
[ -z "$REPORT" ] && REPORT="/tmp/flow-verify-report.html"
FINDINGS=$(jq -r '.verifyFindingsPath // "/tmp/flow-verify-findings.json"' flow.config.json 2>/dev/null)
[ -z "$FINDINGS" ] && FINDINGS="/tmp/flow-verify-findings.json"
python3 "${CLAUDE_PLUGIN_ROOT}/skills/verify-build/lib/render-report.py" "$FINDINGS" --out "$REPORT" --assets-dir "$(dirname "$REPORT")"
```

The explicit `--assets-dir <report dir>` matches §5a's persist path (`<dirname(verifyReportPath)>/assets/`), so a `screenshot` `content` of `assets/<slug>.<ext>` resolves whether or not the buffer and report share a directory.

`render-report.py` is **stdlib-only** (no new dependency) and reads relative `screenshot` observation paths from the assets dir alongside `verifyReportPath`. It base64-inlines frames (so the HTML is self-contained), surfaces the `grounding` rationale callouts, the per-dimension verdict cards with verbatim two-citation evidence, the standalone **"Open questions for you"** block, and the "what we did NOT test" checklist.

**Coverage is established by capture (§5a), not by the renderer.** The renderer is *honest-by-passthrough* — it renders exactly what the buffer carries (every `observations[]` item + the full `not_tested[]` checklist) and does not itself know the declared `Visual-walk` state set. Exhaustiveness therefore depends on §5a writing a `not_tested[]` line for every state it could not capture: with that, every declared state surfaces in the report as either an evidence item or an explicit "not captured" line. A state that §5a silently dropped (no observation AND no `not_tested[]` line) would simply not appear — so §5a's per-state `not_tested[]` write (step 4 above) is the load-bearing coverage guarantee, and the report makes it *visible*, not *enforced*.

**Ephemeral, not committed.** `verifyReportPath` defaults to a temp path; the report is regenerated every iteration and discarded after merge. The durable, curated visual record (`visual-history.html`) is a separate artifact distilled at `/flow:ship` (V3b — a later PR). Output the report path so the caller (Present step / `/flow:ship`) can open it.

## Gotchas

- **Bundled `/verify` output is freeform.** No structured PASS/FAIL contract. Flow's judge has to parse Claude's response narratively — calibration matters (FB-0011: ESCALATE on uncertainty).
- **Simulator ≠ device.** Same disclaimer XcodeBuildMCP carries; mirrored in the "not tested" stamp.
- **Adversarial transformation must spawn in fresh context.** Otherwise the implementing agent grades its own homework. Use the Agent tool with a fresh-context subagent_type — do not let the spawned agent inherit the implementer's conversation state.
- **Budget cap is fail-closed.** Over-budget ⇒ Unknown ⇒ block (FB-0009 fail-fast generalized to runtime cost).

## Config slots used

| Slot | Default | Used by |
|---|---|---|
| `flow.config.json.verifyEnabled` | `true` | Step 1.2 (skip-path) |
| `flow.config.json.platform` | unset → bundled `/run` autodetect | Step 1.2 (skip-path for library/none) |
| `flow.config.json.planPath` | `dev-docs/plan.md` | Step 3 (criteria extraction) |
| `flow.config.json.verifyFindingsPath` | `/tmp/flow-verify-findings.json` | Step 8 (buffer write) |
| `flow.config.json.verifyReportPath` | `/tmp/flow-verify-report.html` | Step 5a (assets dir alongside it), Step 10 (HTML render) |
| `flow.config.json.verifyBudgetCalls` | `60` | Step 5 (budget cap) |
| `flow.config.json.feedbackPath` | `dev-docs/feedback.md` | Read by `/flow:ship` Step 4a (not by verify-build directly) |

