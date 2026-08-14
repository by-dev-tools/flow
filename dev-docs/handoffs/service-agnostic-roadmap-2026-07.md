# Service-agnostic Flow — Codex + Cursor support from one source tree

**Mode:** feature (large, multi-PR) | **Priority:** medium | **Horizon:** post-v1.22.0, unscheduled
**Branch:** `claude/flow-service-agnostic-96aec1` (research only — no plugin artifacts changed)
**Status:** **PLAN — not started.** Research complete and validated 2026-07-29/30. Nothing implemented.
**Scope:** Claude Code (primary) + OpenAI Codex CLI + Cursor. **No other hosts.**
**Companion:** `dev-docs/research/service-agnostic-2026-07.md` — the field survey (standards landscape, prior art, why other approaches lose). This doc is the *execution* layer and is self-contained; read the survey only for background.

---

## 0. Picking this up cold

You need nothing from the originating conversation. Read in this order:

1. §1 Goal + §2 Scope — what this is and isn't.
2. §3 The three decisions — the architecture, and why.
3. §5 Validated facts — every load-bearing claim with its provenance. **Do not re-derive these; do re-verify anything marked ⚠️.**
4. **§17 first, then §11 Phase 00.** Spike S6 resolved to a **confirmed live bug in the shipped plugin**, independent of this port: the 4 advertised "auto-loading rules" have never loaded for any consumer, and the default hooks don't load either. Fix that before anything else here.
5. §11 Spec-walk — the actual work, as checkboxes.
6. §12 Confidence verdicts — **two assumptions remain LOW, which is an automatic human gate.** Phases 2–3 cannot start until §14's spikes resolve them.

**Prerequisite:** neither `codex` nor `cursor-agent`/`agent` was installed on the originating machine, so every Codex/Cursor claim below is docs- or source-derived, never runtime-verified. Claude Code claims **were** empirically tested against CLI v2.1.141. Install both CLIs before Phase 2.

---

## 1. Goal

Let Flow's workflow run on Codex CLI and Cursor as well as Claude Code, generated from **one source tree** so a change is authored once and never hand-ported. Claude Code remains the primary, most-capable host; the other two get an honestly-degraded tier that declares which gates are mechanical and which are advisory.

## 2. Scope

### In
- One plugin root, three generated host manifests; a generator + CI drift check.
- A `tools/flow` CLI that owns determinism and host dispatch.
- A stamped-context invariant so gates cannot pass without fresh evidence.
- Codex adapter, then Cursor adapter.
- Per-capability declarations surfaced by `/flow:doctor`.
- An owned `/simplify` replacement (5th lens) for hosts lacking it.

### Out
- **Any host beyond these three.** Aider is stalled (v0.86.0, Aug 2025); Roo Code is archived.
- **MCP as a delivery vehicle.** MCP prompts-as-slash-commands don't work on Codex ([#8342](https://github.com/openai/codex/issues/8342), open since 2025-12-19, no maintainer reply); SEP-2640 forbids executable skill content by design.
- **Codex custom prompts** (`~/.codex/prompts/`) — officially deprecated in favour of skills, user-scope only, not repo-shareable.
- **Mobile behavioral verification on non-Claude hosts** (§10).
- **Changing the plugin name.** Not needed (§5.6).
- Any change to the two human gates (plan approval, merge).

---

## 3. The three decisions

**1. One repo, one plugin root, three manifests — all generated but the Claude Code one.** Not three forks, not a runtime abstraction layer. Generated artifacts are committed (all three hosts install from git with **no build step**), and `flow gen --check` in CI is what makes "never hand-edit" true rather than aspirational.

**2. The gate guarantee moves from the host into `tools/flow`.** **Both Codex and Cursor fail hooks OPEN** — on timeout, on any non-zero-but-not-2 exit, on exit-2-with-empty-stderr, and on unparseable JSON stdout. A crashed Flow gate *permits and looks like a pass*. That is FB-0074 at the host layer and no configuration fixes it. So make a verdict **impossible without fresh stamped evidence** (§8).

**3. Codex first, Cursor second — but they are not a ranking.** Codex is stronger on **gate mechanics** (`CLAUDE_PLUGIN_ROOT` set for free, per-turn context injection, constrained decoding, richer subagents). Cursor is stronger on **verification** (bundled zero-setup Browser). Codex goes first because gate mechanics are what Flow *is*. Capability declarations must be **per-capability, not one tier per host**.

---

## 4. Why this exists

Flow is ~13,700 lines of host-neutral content (7,267 markdown doctrine + 6,404 stdlib Python, zero third-party deps) wrapped in a thin Claude-Code-specific layer. The coupling is real but narrow and concentrated:

| Coupling | Count | Disposition |
|---|---|---|
| `${CLAUDE_PLUGIN_ROOT}` refs | 143 | **Free** — Codex sets it (§5.1) |
| `` !`shell` `` substitution sites | 51 | ~11 load-bearing → stamped context (§8); ~40 are `git`/`jq` orientation → CLI calls |
| `Skill("...")` composition calls | 21 | → instructions-as-data (Phase 1c) |
| `Agent`/`subagent_type` spawns | 7 | → per-host spawn vocabulary |
| Skills using `context: fork` + `agent:` | 5 | Both hosts have the primitive |
| Skills using `disable-model-invocation: true` | 2 | Exact on Cursor; sidecar on Codex |
| Bundled-native deps | `/verify` ×34, `/simplify` ×25, `/run` ×18, `/run-skill-generator` ×6 | §10 |

All 17 skills reduce to **three frontmatter shapes**, so the generator is a 3-case transform:

| Shape | Count | Skills |
|---|---|---|
| `allowed-tools` only | 7 | accessibility-review, contribute, log-disagreement, security-review, staff-review, verify-build, workflow-help |
| `allowed-tools` + `disable-model-invocation` | 5 | ship, ship-spike, doctor, land, post-merge |
| `agent` + `context: fork` + `disable-model-invocation` | 5 | audit-plan, audit-completion, audit-coverage, audit-skips, critique-plan |

---

## 5. Validated facts

Provenance: **[DOC]** official vendor docs · **[SRC]** `openai/codex@406dc92` source · **[TEST]** empirically run · ⚠️ = undocumented, may change without notice.

### 5.1 Free — works unchanged

| Fact | Provenance |
|---|---|
| Codex sets `CLAUDE_PLUGIN_ROOT` **and** `CLAUDE_PLUGIN_DATA` "for compatibility with existing plugin hooks" — all 143 refs work | **[DOC]** |
| Codex silently ignores unknown `SKILL.md` frontmatter (`RawPluginManifest`/`SkillFrontmatter` have no `deny_unknown_fields`) → one SKILL.md serves all hosts | **[SRC]** ⚠️ |
| Cursor officially reads `.claude/agents/` (project + user); precedence `.cursor/` > `.claude/` > `.codex/` | **[DOC]** |
| Cursor officially reads `.claude/skills/` and `.codex/skills/` for compatibility | **[DOC]** |
| `$REPO_ROOT/.claude-plugin/marketplace.json` is supported by Codex ("legacy-compatible") | **[DOC]** |
| All 6,404 lines of stdlib Python, 26 `lib/` files, `verify-pr-body.sh`, 21 eval harnesses, `flow.config.json` + schema | — |
| `gh`-driven logic (27 calls in ship, 8 in land, 7 in staff-review) | — |
| Every Flow subagent spawn is **depth 1** (agent prompt files never spawn) → safe under Codex `agents.max_depth = 1` | **[TEST]** grep |

### 5.2 Codex specifics

| Fact | Provenance |
|---|---|
| Skills load from `.agents/skills` (cwd→repo root), `$HOME/.agents/skills`, `/etc/codex/skills` | **[DOC]** |
| `~/.codex/skills/` is a **deprecated** user root, and hosts the `.system` cache Codex rewrites on upgrade — **never install there** | **[SRC]** ⚠️ + **[TEST]** (`.codex-system-skills.marker` on disk) |
| No name-based dedupe: *"If two skills share the same `name`, Codex doesn't merge them; both can appear in skill selectors"* | **[DOC]** |
| Manifest discovery is **first-match-wins** over `[.codex-plugin, .claude-plugin, .cursor-plugin]`, then `break`. **There is no overlay merge** | **[SRC]** ⚠️ |
| `skills` manifest field is **ADDITIVE** — `./skills` is always loaded regardless | **[SRC]** ⚠️ ([PR #28790](https://github.com/openai/codex/pull/28790)) |
| `hooks` field **REPLACES**; default is exactly `hooks/hooks.json` | **[DOC]** |
| Plugins **cannot bundle subagents** — no `agents` manifest field exists | **[DOC]** + **[SRC]** |
| Subagents are `~/.codex/agents/*.toml` or `.codex/agents/*.toml`; require `name`, `description`, `developer_instructions`; accept any `config.toml` key | **[DOC]** |
| Sidecar path is exactly `<skill-dir>/agents/openai.yaml`; `policy.allow_implicit_invocation: false` is the `disable-model-invocation` analogue | **[DOC]** |
| Hooks fail OPEN on timeout, non-zero-non-2, exit-2-with-empty-stderr, unparseable JSON | **[SRC]** ⚠️ |
| Hook trust is hash-keyed `path:event:group:handler` → any command-string change silently un-trusts and disables | **[DOC]** + **[SRC]** |
| `UserPromptSubmit` + `SessionStart` inject via `hookSpecificOutput.additionalContext`, default ~2500 tokens, tunable | **[DOC]** |
| `codex exec --output-schema` is real constrained decoding (Responses API `text.format`, `strict:true`) | **[SRC]** ⚠️ |
| Sessions at `~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl`, **also `.jsonl.zst`**; schema explicitly disclaimed as unstable | **[SRC]** ⚠️ |
| **No `Read`/`Grep`/`Glob`/`Write`/`Edit`/`Task` tools.** Canonical `tool_name`s: `Bash`, `apply_patch`, `update_plan`, `spawn_agent`. Hook matcher aliases ≠ payload `tool_name` | **[DOC]** + **[SRC]** |
| `auto_review.policy` is the **sandbox-approval** reviewer, NOT code review | **[DOC]** |

### 5.3 Cursor specifics

| Fact | Provenance |
|---|---|
| Skills load from `.agents/skills/`, `.cursor/skills/`, `.claude/skills/`, `.codex/skills/` + user equivalents. **Precedence not documented** | **[DOC]** |
| Frontmatter: `name`, `description` required; `paths`, `disable-model-invocation`, `metadata` optional. `user-invocable` exists in the changelog but not `skills.md` ⚠️ | **[DOC]** |
| Subagents `.cursor/agents/`, `.claude/agents/`, `.codex/agents/`; fields `name`, `description`, `model`, `readonly`, `is_background` — all optional | **[DOC]** |
| Built-in subagents: Explore, Bash, Browser. Nesting allowed to depth 2 | **[DOC]** |
| All manifest fields **REPLACE** folder discovery: *"The default folder is not also scanned"* | **[DOC]** |
| Plugin `rules/` discovery accepts `.md` — but the standalone rules system silently ignores `.md`; **must be `.mdc`** | **[DOC]** (internally inconsistent — use `.mdc`) |
| Reads Claude-format hooks from `.claude/settings.json`, **but requires an account-level flag** ("Include third-party Plugins, Skills, and other configs") that cannot be set from the repo | **[DOC]** |
| `tool_input.command` documented for Shell; **`tool_input.file_path` is NOT documented** and evidence says absent (Cursor's file tools use `path`/`fileText`). `Edit`→`Write`; `Glob`/`WebFetch`/`WebSearch` have no equivalent; `tool_input` flips object↔JSON-string across events | **[DOC]** |
| `failClosed` defaults **false**; default `timeout` value unpublished; timeout counts as failure → fail-open | **[DOC]** |
| **`beforeSubmitPrompt` cannot inject context** — output is only `continue` + `user_message`. Only `sessionStart` (fire-and-forget, non-blocking) and `postToolUse` have `additional_context` | **[DOC]** |
| **No constrained-output mode**; on failure "no well-formed JSON object is emitted" | **[DOC]** |
| Bundled **Browser** tool (extension-hosted MCP, zero setup): navigate, click, type, scroll, screenshot, console, network, dev-server port awareness. **No documented a11y-tree read** | **[DOC]** |
| CLI binary is `agent` (not `cursor-agent`); reads `AGENTS.md` **and** `CLAUDE.md` at project root | **[DOC]** |
| Transcripts: `transcript_path`/`CURSOR_TRANSCRIPT_PATH` is the only supported locator; changelog claims headless writes "Claude Code-compatible JSONL" ⚠️ | **[DOC]** |
| Local install: `~/.cursor/plugins/local/<name>`, symlink officially endorsed | **[DOC]** |

### 5.4 Claude Code regression safety — **[TEST]** on CLI v2.1.141

Adding `.codex-plugin/`, `.cursor-plugin/`, `agents-codex/*.toml`, `rules-cursor/*.mdc`, `capabilities/*.json` and a nested `skills/ship/agents/openai.yaml` produced an **identical component inventory** (17 skills / 9 agents) and `claude plugin validate` passed. Discovery is fixed-name; `.claude-plugin` is matched exactly with no `.*-plugin` glob; agent discovery is plugin-root-anchored. The plugin root **already ships 5 unrecognized directories** (`docs/`, `evals/`, `schema/`, `scripts/`, `tools/` — 108 files) with no ignore file.

Two hard constraints:
1. **`bin/` is a documented Claude Code component** — *"Executables added to the Bash tool's `PATH`… invokable as bare commands."* Use `tools/flow`. Also avoid `commands/`, `workflows/`, `output-styles/`, `themes/`, `monitors/`, `settings.json`, `.mcp.json`, `.lsp.json`, `hooks/hooks.json`.
2. **Keep `plugin.json` metadata-only.** Unknown top-level keys are documented-safe and load fine at runtime but **fail `claude plugin validate` on v2.1.141**.

Claude Code's `skills` field **ADDS to** default discovery; `commands`/`agents`/`workflows` **REPLACE**.

### 5.5 The layout is undocumented on both non-Claude hosts

**Neither vendor documents, recommends, or exemplifies a single-repo multi-host layout.** OpenAI ships its own plugin as **three separate repos** (`openai-developers-for-claude`, `openai-developers-for-cursor`, plus the directory listing). Codex's portal *converts* `.claude-plugin/plugin.json` → `.codex-plugin/plugin.json` (`claude_format_normalized`) — conversion is the opposite of endorsing coexistence.

Against that: **36 repos verified shipping 2+ host manifests at one plugin root** (34 with all three), including Firebase, DataDog, Slack, Microsoft, Meta, Kraken, Resend, GitGuardian.

**`firebase/agent-skills` has already drifted** — `license` says MIT in the Claude manifest, Apache-2.0 in the other two. That is FB-0010 fan-out contradiction, live, in exactly this layout. **Flow avoids it structurally by generating two manifests from one** — which is the entire argument for generation over hand-maintenance.

### 5.6 The `flow` name is safe; only `bin/` was the hazard

Plugin name `flow`, `flow@flow`, `/flow:*`, and `flow.config.json` have zero shell exposure (Facebook Flow uses `.flowconfig`; Flow blockchain uses `flow.json`). **No rename needed.** The collision existed only via `bin/` PATH injection (§5.4), where `flow` would have collided with Facebook Flow's `flow check` and the Flow blockchain CLI in exactly the `web`/`tauri-rust-ts` stacks Flow ships — ambiguous in both directions (prepend shadows theirs; append makes ours unreachable).

---

## 6. Host capability matrix

| Primitive | Claude Code | Codex | Cursor |
|---|---|---|---|
| One `SKILL.md` | ✅ | ✅ ignores extra keys ⚠️ | ⚠️ undocumented (**spike S1**) |
| Human-only skill | `disable-model-invocation` | `policy.allow_implicit_invocation` | `disable-model-invocation` ✅ exact |
| Fresh-context fork | `context: fork` + `agent:` | `.codex/agents/*.toml` + `spawn_agent` | reads `.claude/agents/` |
| Read-only reviewer | `tools:` allowlist | `sandbox_mode` ⚠️ not enforced under `--yolo` | `readonly: true` ✅ |
| Per-turn context injection | ✅ | ✅ ~2500 tok | ❌ **none** |
| Hook blocks on failure | exit 2 | exit 2 + **stderr required** | exit 2, or `failClosed: true` |
| **Hook fails OPEN on timeout** | — | ⚠️ yes | yes (documented) |
| Constrained output | — | ✅ `--output-schema` | ❌ none |
| Plugin bundles subagents | ✅ | ❌ | ✅ |
| `${CLAUDE_PLUGIN_ROOT}` | ✅ | ✅ documented alias | ❌ |
| Drive/observe **web** | ✅ `/verify` | 🟡 Playwright / Chrome DevTools MCP | ✅ **bundled Browser** (no a11y tree) |
| Drive/observe **mobile** | ✅ | ❌ untested via MCP | ❌ untested via MCP |
| Launch recipe | ✅ `/run` + generator | ❌ (desktop-app-only Actions) | ❌ |
| Diff reviewer to build on | ✅ | 🟡 `codex review` (no apply) | 🟡 Agent Review + Bugbot Autofix |
| Validate/lint command | ✅ `claude plugin validate` | ❌ none | ❌ none |

**Codex is stronger on gate mechanics; Cursor is stronger on verification.** Hence per-capability declarations, not one tier per host.

---

## 7. The two hazards

### 7.1 Both hosts fail hooks OPEN

Only `exit 2` blocks (and on Codex, only with non-empty stderr). Generator rules:
1. Every generated hook exits **exactly 0 or exactly 2**, always writing stderr on 2.
2. `failClosed: true` + an **explicit** `timeout` on every Cursor hook.
3. Never rely on "hook errored ⇒ blocked." Hooks are *enrichment*; the gate lives in §8.

### 7.2 Codex hook trust is hash-keyed — regeneration silently disables gates

Trust is keyed on the handler definition. Any command-string change or handler reorder un-trusts the hook, and Codex **skips untrusted hooks** — combined with fail-open, a Flow upgrade silently drops every gate.

**Mitigation (constrains the design):** dispatch through **one stable entrypoint per event** — `command: "$CLAUDE_PLUGIN_ROOT/tools/flow hook pre-tool-use"` — whose string never changes across releases. Version the logic inside `tools/flow`. Keep handler order fixed. `/flow:doctor` must assert hooks are **trusted**, not merely present.

---

## 8. The load-bearing invariant: stamped context

Hook-based context injection **cannot work on Cursor** (§5.3). The portable replacement is already Flow's own doctrine.

The 51 substitution sites are not uniform: **~11 script-backed** (the 5 audit/critique forks + `ship` + `verify-build`) feed deterministic Python — these are the gates. **~40 inline** are `git`/`jq`/`cat` orientation; if the model runs those itself the cost is convenience, not soundness.

**Invariant:** `flow context <mode>` writes its output stamped with `branch`, `head_sha_short`, and a content digest. Every consumer refuses to produce a verdict when the stamp is absent or stale, emitting the existing `[decision-required]` routing.

This generalizes existing machinery:
- `ship/lib/render-test-plan.py:138` — *"an un-stamped buffer reads as un-judged"*
- `audit-skips/lib/skip-audit-checks.py:178-179` — `fresh` from `branch` + `head_sha_short`
- `audit-skips/SKILL.md:10` — *"verdict-without-artifact == skip"*

The guarantee stops depending on host mechanics and starts depending on Flow's engine, which is identical on all three hosts. Injection becomes a per-host optimization. It also closes the roadmap § Exploration item on stamping the repo root into the skip-audit handoff — same mechanism, same PR family.

---

## 9. Target layout

Plugin root stays `plugins/flow/` (marketplace already points there). Each host's manifest names the variant it can parse.

```
flow/
├── .claude-plugin/marketplace.json          SOURCE   also read by Codex (documented)
├── .cursor-plugin/marketplace.json          GEN
│
└── plugins/flow/                            ← THE plugin root, all three hosts
    ├── .claude-plugin/plugin.json           SOURCE   metadata-only — never add keys (§5.4)
    ├── .codex-plugin/plugin.json            GEN
    ├── .cursor-plugin/plugin.json           GEN
    │
    ├── skills/<name>/SKILL.md               SOURCE   ★ one file → all 3 hosts
    ├── skills/<name>/agents/openai.yaml     GEN      Codex sidecar (5 skills only)
    ├── skills/<name>/lib/**                 SOURCE   shared verbatim (26 files)
    │
    ├── agents/*.md                          SOURCE   ★ Claude Code + Cursor read as-is (9)
    ├── agents-codex/*.toml                  GEN      installed out-of-band (9)
    │
    ├── rules/*.md            (paths:)       SOURCE   (4) — but see §14 spike S6
    ├── rules-cursor/*.mdc    (globs:)       GEN      .mdc MANDATORY
    │
    ├── hooks/default-hooks.json             SOURCE   ★ Claude Code + Codex format
    ├── hooks/codex-hooks.json               GEN
    ├── hooks/cursor-hooks.json              GEN      native camelCase, failClosed
    │
    ├── tools/flow                           SOURCE   NEW — ⚠️ NOT bin/ (§5.4)
    ├── tools/memory/**                      SOURCE   existing
    ├── adapters/{codex,cursor}/gen.py       SOURCE   NEW
    ├── capabilities/*.json                  SOURCE   NEW
    │
    └── scripts/ schema/ docs/ evals/        SOURCE   shared, untouched
```

★ = one file serving multiple hosts with zero transformation.

**Split:** ~165 source files (~88%) / ~22 generated (~12%).

### 9.1 Manifest field matrix

| | Claude Code | Codex | Cursor |
|---|---|---|---|
| `skills` | ADDS to `skills/` | **ADDS** to `./skills` ⚠️ | **REPLACES** — set `"./skills/"` |
| `agents` | REPLACES | **field doesn't exist** | REPLACES — set `"./agents/"` |
| `rules` | not a component (§14 S6) | n/a | REPLACES — **must set `"./rules-cursor/"`** |
| `hooks` | own merge rules | REPLACES; default `hooks/hooks.json` | REPLACES; default `hooks/hooks.json` |

**Codex's `skills` is additive → `./skills` always loads.** Per-host skill gating must happen in frontmatter or the sidecar, never by path.

### 9.2 Four silent-no-op defects → CI assertions

| # | Defect | Assertion in `flow gen --check` |
|---|---|---|
| 1 | No hook filename matches any host's auto-discovery default → hooks load for nobody | Every manifest declares `hooks`; the path resolves; **`hooks/hooks.json` does NOT exist** (both Codex and Cursor would auto-read it in the wrong format) |
| 2 | Cursor auto-discovers `rules/` and accepts `.md` → Flow's `paths:` rules load **unscoped** | `.cursor-plugin/plugin.json` sets `"rules": "./rules-cursor/"`; every file there is `.mdc` with `globs`/`alwaysApply` |
| 3 | `agents-codex/*.toml` is inert everywhere; no loader reads it | `flow install --host codex` places them; `/flow:doctor --host codex` asserts they landed. **Without this the 5 fork skills run inline, which looks identical to working** |
| 4 | Three manifests drift (Firebase precedent, §5.5) | Cross-manifest agreement on `name`, `version`, `license`, `repository` |

### 9.3 Do NOT dual-publish skills

Never place one skill in both `.claude/skills/` and `.agents/skills/` of a project — Cursor reads both, Codex reads `.agents/`, and **neither dedupes by name**. Plugin packaging sidesteps this. For loose user-scope installs target `~/.agents/skills/` only.

---

## 10. The bundled skills — `/verify`, `/simplify`, `/run`, `/run-skill-generator`

`/verify` is **three** capabilities, and Flow already owns the expensive one:

| Layer | Owner today | Disposition |
|---|---|---|
| Launch recipe (`/run`, `/run-skill-generator`) | Claude Code natives | **New `flow.config.json` `launchCmd` slot.** More deterministic than a generated skill; an improvement on Claude Code too. Nothing to leverage on either host. |
| Drive + observe | Platform MCPs — **Flow already drives these itself** (`verify-build:278`) | Portable; MCP is host-agnostic |
| Plan-driven judging gate | **Flow, entirely** (425 + 532 lines + rubrics) | Already portable |

**`/simplify` has no substitute on either host.** Flow never *calls* it — zero `Skill("simplify")` sites; it's prose, and Flow *audits whether it ran* via `rigor-marker.py`, which fingerprints **source content, not provenance**. So it is a *slot with an evidence check*, not a call:
- Claude Code → native `/simplify`, unchanged.
- Codex/Cursor → owned 5th lens (`lens-simplify`, ~60 lines), layered on native diff scoping (`codex review --uncommitted|--base`; `agent -p --force` to apply).
- ⚠️ Codex trap: custom `PROMPT` **conflicts with** `--base`/`--commit`/`--uncommitted`.

`rigor-marker.py`, `audit-skips`, and the ship gate all keep working unchanged.

**This requires amending CLAUDE.md.** [CLAUDE.md:125](../../CLAUDE.md) says "Never wrap a bundled Claude Code skill." Scope it to: *never wrap a bundled skill **on Claude Code**; where a host lacks the native, ship an owned equivalent dispatched by capability — never a wrapper that shadows the native.*

**Verification, split by platform not host:** web is affordable (Cursor bundled Browser; Codex Playwright MCP). **Mobile stays degraded and declared** — neither host has an automation story; XcodeBuildMCP *should* work as an MCP server but that is untested (spike S5).

⚠️ Both Cursor's Browser and Codex's Computer Use are **admin-disableable**. Probe, never assume.

---

## 11. Spec-walk

### Phase 00 — PREREQUISITE: two shipped features that never load (§17)

**Not part of the port. Ship this first, standalone.** Both are advertised in `README.md`, the marketplace description, and `/flow:doctor`, and both are mechanically absent for every consumer.

- [ ] **00a — Convert the 4 rules to path-activated skills.** `rules/` is not a Claude Code plugin component; the four rules have never loaded for anyone. Convert each to a skill under `plugins/flow/skills/` carrying the same `paths:` globs plus `user-invocable: false`. Claude Code's SKILL.md **does** support `paths:` (docs + binary-confirmed Zod schema), and the docs point at exactly this: *"To ship instructions that load into Claude's context, put them in a skill."* *Verify:* a session touching `plan.md` loads the plan-discipline content; `claude plugin details` skill count rises from 17 to 21.
- [ ] **00b — Fix the hooks filename.** `hooks/default-hooks.json` matches no documented default (`hooks/hooks.json`) and `plugin.json` declares no `hooks` field — hence `Hooks (0)`. Rename, or declare `"hooks": "./hooks/default-hooks.json"`. **Decide deliberately whether hooks should be opt-in**: if the current opt-in posture is intentional, the *docs* are wrong, not the code. *Verify:* `claude plugin details` reports the intended hook count and the marketplace description matches.
- [ ] **00c — Reconcile the drifted project-scope copies.** `.claude/rules/{general,documentation}.md` differ from their plugin counterparts by 101 and 74 diff lines. These masked the bug during dogfooding. *Verify:* one source of truth; no near-duplicate pairs remain.
- [ ] **00d — Fix the consumer path.** `template/base/bootstrap.sh:150` copies **only** `safety.md.template`; `general`, `plan-discipline`, `documentation`, `exploration` are copied by nothing and loaded by nothing. *Verify:* a freshly bootstrapped project has all intended rules active by a mechanism that is actually read.
- [ ] **00e — Correct every claim.** `README.md:86` "4 auto-loading rules", the `plugin.json`/`marketplace.json` "four portable rules", `/flow:doctor` Section 3's "auto-load via flow@flow", and `docs/automation-boundaries.md:17` "only the auto-loading rules attach". *Verify:* `git grep -n 'auto-loading rules'` shows no claim the code doesn't back.
- [ ] **00f — Add the missing gate.** A doctor check that asserts each advertised component is actually *reported by the loader*, not merely present on disk. *Verify:* deleting a skill dir reds the check.

### Phase 0 — Harden on Claude Code (no host work; ships regardless)

- [ ] **0a — Stamped-context invariant.** `flow context <mode>` writes stamped artifacts; the 11 script-backed consumers assert freshness. *Verify:* new eval — stale stamp ⇒ `[decision-required]`, never a clean verdict; wired into `ci.yml`.
- [ ] **0b — Renderer fail-loud audit.** `render-test-plan.py`, `render-report.py`, `skip-audit-checks.py` fail loudly on schema mismatch, never degrade. *Verify:* fixture per renderer — malformed model JSON ⇒ non-zero exit + named error, not a partial render.
- [ ] **0c — Env overrides + schema slots.** `FLOW_DISAGREEMENT_DIR`; new `host`, `capabilityTier`, `launchCmd` slots; land the read-but-undeclared `changelogPath`. *Verify:* `git grep -nE '3[0-9] slots'` returns zero contradictions across `workflow.md`/`plugin.json`/`marketplace.json`/doctor.
- [ ] **0d — `extract_session.py` adapter seam.** Split discovery+parse (`:74-208`) behind an interface; keep `:222-673` + `bounding_logic.py` neutral; tool-name tables (`:347`,`:350`,`:354`,`:575`) become a per-host map. *Verify:* eval for the **false-`UNREAD`** mode — an unrecognized tool name fails loudly instead of silently marking every artifact UNREAD and minting false "unverified recall" findings.
- [ ] **0e — CI regression gate.** Add `claude plugin validate ./plugins/flow`, `claude plugin validate .`, and an inventory assertion (`claude --plugin-dir ./plugins/flow plugin details flow@inline` ⇒ 17 skills / 9 agents). *Verify:* deliberately break a skill frontmatter; CI reds.

### Phase 1 — `tools/flow` + generator + drift enforcement

- [ ] **1a — The CLI.** `tools/flow` wrapping existing `lib/*.py`: `context`, `gate`, `render`, `audit`, `hook <event>`, `doctor`, `gen`, `install`. *Verify:* all 21 existing evals green; ~40 inline substitution sites become CLI calls.
- [ ] **1b — Generator + drift lint.** `adapters/*/gen.py` emits every §9 artifact; `flow gen --check` regenerates into a temp dir and diffs. Every generated file carries `DO NOT EDIT — generated by flow gen`. *Verify:* new `evals/run_adapter_gen_evals.py` **enumerated in `ci.yml`**; hand-edit a generated file ⇒ CI reds.
- [ ] **1c — Instructions-as-data.** `flow gate ship --step 2` returns JSON including `{action:"spawn_fork", prompt_file, schema}`. *Verify:* ship + verify-build orchestration expressed as data; one Claude Code translator consumes it; existing behavior unchanged.
- [ ] **1d — Generator completeness guard.** Generator **errors** when a source declares a semantic with no mapping for a target host. *Verify:* add `context: fork` to a scratch skill with no Codex mapping ⇒ `flow gen` exits non-zero.

**◆ Decision gate.** Proceed only if Phase 1 landed clean and dogfooded on ≥2 real Flow PRs, **and** spikes S1–S4 (§14) have resolved.

### Phase 2 — Codex adapter

- [ ] **2a — Packaging.** `.codex-plugin/plugin.json`, `agents/openai.yaml` sidecars, `agents-codex/*.toml`, `hooks/codex-hooks.json` dispatching through the **stable** `tools/flow hook <event>` entrypoint. *Verify:* `codex plugin marketplace add … && codex plugin add` installs; `/skills` lists all 17.
- [ ] **2b — Transcript adapter.** `~/.codex/sessions/**` plain **and `.jsonl.zst`**; prefer `transcript_path` from hooks and `codex exec --json` over rollout parsing. Tool map `Read|Grep|Glob → Bash`, `Write|Edit → apply_patch`, `Task → spawn_agent`. *Verify:* fixtures for plain + zstd + unknown-tool-name.
- [ ] **2c — Capability declaration.** `capabilities/codex.json`; `/flow:doctor --host codex` asserts hooks are **trusted**, agents landed in `~/.codex/agents/`, and the skill catalog fits the 2%/8,000-char budget. Adopt `--output-schema` for the 3 renderers' inputs. *Verify:* doctor prints mechanical-vs-advisory per gate; a skipped verify gate blocks ship auto-invocation exactly as `platform: library` does.

### Phase 3 — Cursor adapter

- [ ] **3a — Packaging.** `.cursor-plugin/plugin.json` + `.cursor-plugin/marketplace.json`, `rules-cursor/*.mdc`, `hooks/cursor-hooks.json` using **native** events (`beforeShellExecution` → `.command`; `beforeReadFile`/`afterFileEdit` → `.file_path`), `failClosed: true` + explicit `timeout` everywhere. *Verify:* symlink install to `~/.cursor/plugins/local/flow`; skills + agents resolve.
- [ ] **3b — Capability declaration + verify path.** `capabilities/cursor.json`; wire the bundled Browser as the web drive/observe provider; document the account-level "Include third-party Plugins, Skills, and other configs" prerequisite and have doctor verify it took. *Verify:* doctor names every advisory gate; **an advisory gate never renders byte-identically to a mechanical one.**

### Phase 4 — Owned `/simplify` + launch slot

- [ ] **4a — `lens-simplify` agent** + capability dispatch (native on Claude Code, owned elsewhere). *Verify:* `rigor-marker.py` accepts the owned lens's marker unchanged.
- [ ] **4b — `launchCmd` slot** replacing `/run` + `/run-skill-generator`. *Verify:* verify-build launches from config on all three hosts.
- [ ] **4c — CLAUDE.md rule amendment** (§10). *Verify:* `git grep -n 'Never wrap a bundled'` shows the scoped form only.

---

## 12. Confidence verdicts

**Assumption:** Adding sibling dirs and manifests to `plugins/flow/` does not break the live Claude Code plugin.
**Confidence:** **HIGH**
**Why:** Empirically tested on CLI v2.1.141 — identical inventory (17/9), `claude plugin validate` passed; discovery is fixed-name; the plugin root already ships 5 unrecognized dirs.
**If it flips:** Generate complete host trees into `dist/codex/` + `dist/cursor/` instead, leaving `plugins/flow/` byte-identical. Costs duplication of generated content only.

**Assumption:** One `SKILL.md` with Claude-Code-only frontmatter loads cleanly on Codex and Cursor.
**Confidence:** **LOW** *(Codex alone would be HIGH; Cursor is undocumented)*
**Why:** Codex is source-verified lenient (no `deny_unknown_fields`). Cursor's behavior is documented **nowhere**, and the risk isn't a parse error — it's **silent semantic loss**: `context: fork` ignored means a skill that must fork runs inline and looks like it worked.
**If it flips:** Generate per-host `SKILL.md` variants; the generator gains a frontmatter-projection stage. Adds ~17 generated files, no architectural change. **Gate: spike S1.**

**Assumption:** Flow's gates can be made mechanical on Codex and Cursor.
**Confidence:** **LOW**
**Why:** Both hosts fail hooks open in undocumented ways; Cursor cannot inject per-turn context at all; Codex's hash-keyed hook trust silently disables gates on upgrade. The stamped-context invariant (§8) is the proposed answer but is **unproven** on either host.
**If it flips:** Non-Claude hosts become advisory-only for gate enforcement — the loop still runs, but `ship` always requires an explicit human "ship it" there. That is a materially smaller product. **Gate: spikes S2 + S3.**

**Assumption:** Cursor's bundled Browser can serve Flow's §5a a11y-gated capture protocol.
**Confidence:** **MEDIUM**
**Why:** Documented surface covers navigate/click/screenshot/console/network but has **no documented a11y-tree read**, which §5a requires (*snapshot tree → assert state → screenshot*).
**If it flips:** §5a needs a DOM-based variant for Cursor, or web verification there degrades to screenshot-only. Design decision, not implementation. **Gate: spike S4.**

**Assumption:** The single-repo three-manifest layout stays viable.
**Confidence:** **MEDIUM**
**Why:** Undocumented on both non-Claude hosts and unverifiable on Cursor (closed source). Codex's precedence is source-verified but could reorder in any release with no changelog obligation. Offset by 36 credible repos using it, and by generation making drift structurally impossible.
**If it flips:** Split into per-host plugin roots under `dist/` — the generator already produces every artifact, so this is a re-target, not a rewrite.

**Assumption:** Flow's 4 portable rules currently auto-load for Claude Code consumers.
**Confidence:** ~~LOW~~ → **RESOLVED 2026-08-12: they do NOT load. Confirmed broken.** See §17.
**Why:** Docs + binary decompilation of CLI v2.1.141 both confirm `rules/` is not a plugin component and no loader call site joins a plugin root.
**If it flips:** n/a — resolved. This became **Phase 00**, a prerequisite bug fix ahead of all porting work.

---

## 13. Risks

1. **Silent gate degradation** — the whole plan's failure mode. Mitigated by §8 + §9.2 + the §7 rules, and by never letting an advisory gate render like a mechanical one.
2. **Undocumented behavior changing** — 12 load-bearing facts are ⚠️ source- or inference-derived. Mitigated by CI assertions that fail loudly, and by keeping them out of contracts.
3. **Scope inflation** — Phases 2–4 are optional. Phase 0 + 1 must stand alone in value.
4. **No validator on 2 of 3 hosts** — Codex and Cursor have no `plugin validate`. Flow's own `flow gen --check` is the only mechanical gate there.
5. **Cursor's surface moves weekly** — the on-disk snapshot used here (13 built-in skills) is ~3 months behind the documented 19. Re-verify §5.3 before Phase 3.
6. **Queue debt** — 41 queued lesson-contributions and § Exploration entries (fork-handoff transport, `/tmp` collisions, `${CLAUDE_PLUGIN_ROOT}` resolution lint) touch the exact seams this work moves. Drain first; the port gets smaller.

---

## 14. Open spikes — these gate the phases

None can be resolved without the CLIs installed. **Install `codex` and `agent` first.**

| # | Question | Cost | Gates |
|---|---|---|---|
| **S1** | Do Cursor + Codex load a `SKILL.md` carrying `context: fork`, `agent:`, `allowed-tools`, `disable-model-invocation` without error — and is the *semantic* loss detectable? | 30 min | Generator shape; **LOW→HIGH** |
| **S2** | Does Cursor's `.claude/settings.json` hook shim populate `tool_input.file_path`/`.command`? (Native stdin has no `cwd`/`session_id`.) | 1 h | Phase 3a; **LOW→** |
| **S3** | Does the stamped-context invariant actually block a stale verdict on Codex and Cursor end-to-end? | 2 h | Phase 2/3 tier; **LOW→** |
| **S4** | Can Cursor's Browser return an accessibility tree? | 1 h | §5a protocol; **MEDIUM→** |
| **S5** | Does XcodeBuildMCP work as an MCP server under Codex/Cursor? | 2 h | Whether mobile verification degrades |
| **S6** | **Do plugin-shipped `rules/` auto-load on Claude Code at all?** | 1 h | **Pre-existing bug — do this FIRST** |
| S7 | Does Claude Code enforce `allowed-tools` for the `Skill` tool? (`ship-spike:176` vs `:12` — chip queued) | 15 min | Severity of a separate bug |
| S8 | Codex `agents.max_concurrent_threads_per_session` real default (⚠️ src says 6 v1 / 4 v2) | 15 min | staff-review's 4-lens fan-out |
| S9 | Does Flow's doctrine fit Codex's 32 KiB `AGENTS.md` cap? (marketplace description alone is 17 KB) | 15 min | Whether AGENTS.md carries orientation |
| S10 | Cursor headless transcript — really "Claude Code-compatible JSONL"? | 30 min | Size of Phase 3 transcript work |

---

## 15. Files touched (anticipated)

**New:** `plugins/flow/tools/flow`, `plugins/flow/adapters/{codex,cursor}/gen.py`, `plugins/flow/capabilities/{claude-code,codex,cursor}.json`, `plugins/flow/agents/lens-simplify.md`, `plugins/flow/evals/run_adapter_gen_evals.py`, `plugins/flow/evals/run_stamped_context_evals.py`.

**Generated (new, committed):** `plugins/flow/.{codex,cursor}-plugin/plugin.json`, `.cursor-plugin/marketplace.json`, `plugins/flow/skills/*/agents/openai.yaml` (×5), `plugins/flow/agents-codex/*.toml` (×9), `plugins/flow/rules-cursor/*.mdc` (×4), `plugins/flow/hooks/{codex,cursor}-hooks.json`.

**Modified:** `plugins/flow/scripts/{extract_session,log_disagreement}.py`, `plugins/flow/schema/flow.config.schema.json`, `plugins/flow/skills/{ship,verify-build,doctor,audit-skips,critique-plan,audit-plan,audit-completion,audit-coverage}/SKILL.md`, `plugins/flow/skills/ship/lib/{render-test-plan,rigor-marker}.py`, `plugins/flow/skills/verify-build/lib/render-report.py`, `plugins/flow/skills/audit-skips/lib/skip-audit-checks.py`, `plugins/flow/docs/workflow.md`, `.github/workflows/ci.yml`, `CLAUDE.md`, `README.md`.

**Docs cascade:** `dev-docs/{plan,history,roadmap,feedback,spec}.md`.

---

## 16. Validation against the quality bar

- **Correct** — no reviewer output schema changes; all 21 existing evals must stay green.
- **Evidence-backed** — every new behavior gets a fixture; 4 new eval harnesses, each explicitly enumerated in `ci.yml` (CI enumerates, never globs).
- **Graceful on malformed input** — Phase 0b makes renderers fail loud; Phase 0d makes an unknown tool name fail loud instead of minting false findings.
- **Lean** — stdlib only. No new dependencies.
- **Project-agnostic** — no host-specific tokens outside `adapters/` and `capabilities/`.
- **Honest limitations** — §6, §10, and §12's two LOW verdicts must be reflected in `README.md` and `docs/workflow.md` "Bootstrap status" before Phase 2 ships.

---

## 17. Resolved spike S6 — two shipped features that never load

**Resolved 2026-08-12. Verdict: CONFIRMED BROKEN.** Independent of the port; fix first (Phase 00).

### Finding A — the 4 portable rules have never loaded for anyone

`rules/` is not a Claude Code plugin component:

- **[DOC]** The Component-path-fields table lists 13 fields; `rules` is not among them. The File-locations table has 13 rows; there is no Rules row. The standard-layout warning enumerates valid root dirs (`commands/`, `agents/`, `skills/`, `workflows/`, `output-styles/`, `themes/`, `monitors/`, `hooks/`) — `rules/` is absent.
- **[DOC]** Stated directly: *"Plugins contribute context through skills, agents, and hooks rather than CLAUDE.md. To ship instructions that load into Claude's context, put them in a skill."*
- **[TEST]** Decompiling CLI v2.1.141: all 8 `rulesDir` occurrences resolve to exactly four sources — managed, user (`~/.claude/rules`), project (`.claude/rules`, walking ancestors), and env-gated additional dirs. **No call site joins a plugin root.** The lazy path-scoped loader (the only one handling `paths:` frontmatter) is likewise only ever handed a project path. The plugin manifest's Zod schema has no `rules` key.
- `paths:` frontmatter **is** real — but only at project/user scope.

**Why it looked fine:** this repo has its own project-scope `.claude/rules/` with near-duplicates that have **drifted** — **[TEST]** `general.md` differs by 101 diff lines, `documentation.md` by 74. Every dogfooding session loaded those *project* rules; the plugin copies contributed nothing.

**Consumer blast radius is worse.** **[TEST]** `template/base/bootstrap.sh:150` copies only `safety.md.template`. `general`, `plan-discipline`, `documentation`, `exploration` are copied by nothing and loaded by nothing — **a bootstrapped consumer has zero of the four advertised rules active.** So `docs/automation-boundaries.md:17`'s claim that on a cold start *"only the auto-loading rules attach"* describes a cold start with **no enforcement layer at all**.

### Finding B — default hooks never load either

**[TEST]** `plugin.json` top-level keys are `author, description, homepage, keywords, license, name, repository, version` — **no `hooks` field** — and the file is named `hooks/default-hooks.json` where the documented auto-discovery default is exactly `hooks/hooks.json`. Hence `claude plugin details` → `Hooks (0)`.

The plugin's own `default-hooks.json` header says hooks are *"NOT auto-applied — consumers opt-in"*, so the posture may be intentional; the marketplace description advertising "default hooks" is then the thing that's wrong. **Decide which, then make code and docs agree.**

### The fix

**[DOC]** SKILL.md supports `paths:` — *"Glob patterns that limit when this skill is activated… Uses the same format as path-specific rules"* — binary-confirmed in the skill Zod schema. Convert each rule to a skill with the same `paths:` list plus `user-invocable: false`. Semantics shift slightly (a rule is *injected* as context; a skill body *loads* when Claude touches a matching file), but it is the mechanism the docs explicitly point at and the only one that ships path-activated guidance from a plugin.

### Why this belongs in this doc

It is the same failure class the port is designed around — **a component advertised as load-bearing that is mechanically absent, and whose absence is indistinguishable from working.** FB-0074, at product scale, in the shipped plugin. Phase 00f adds the missing gate: assert each advertised component is *reported by the loader*, not merely present on disk.
