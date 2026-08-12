# Flow × Codex × Cursor — implementation roadmap

**Date:** 2026-07-29
**Branch:** `claude/flow-service-agnostic-96aec1`
**Plugin version at time of writing:** v1.22.0
**Scope:** Claude Code (primary) + OpenAI Codex CLI + Cursor. **No other hosts.**
**Status:** proposal. No plugin artifacts changed by this doc. Companion to `dev-docs/research/service-agnostic-2026-07.md` (the field survey); this doc is the *execution* layer.

Every fact below was validated against official vendor docs, and where docs are silent, against `openai/codex@406dc92` source or artifacts on disk. Source-only facts are marked ⚠️ **unstable** and must not become contracts.

---

## 0. The three decisions that determine everything

**1. One repo, three plugin manifests, one shared source tree.** Not three forks, not a runtime abstraction layer. All three hosts have a near-isomorphic plugin format, and Codex's loader already discovers all three manifest paths.

**2. The gate guarantee moves from the host into `tools/flow`.** Today Flow's gates rely on host mechanics (`!`-backtick substitution, hook exit codes). **Both Codex and Cursor fail hooks OPEN** — on timeout, on any non-zero-but-not-2 exit, on exit-2-with-empty-stderr, and on unparseable JSON stdout. So a crashed Flow gate on either host *permits and looks like a pass*. That is FB-0074 at the host layer, and it cannot be fixed by configuration. The fix is to make a verdict **impossible without fresh stamped evidence** — which Flow already does for test plans and skip audits, and which needs generalizing to context.

**3. Codex first, Cursor second — but they are not a ranking.** Codex is stronger on **gate mechanics**: `CLAUDE_PLUGIN_ROOT` set for free, real per-turn context injection, constrained decoding (`--output-schema`), richer subagent config. Cursor is stronger on **verification**: a bundled zero-setup Browser tool that beats anything Codex CLI has (§1.1). Codex goes first because gate mechanics are what Flow *is*; verification is what Flow *checks*. Capability declarations must therefore be **per-capability, not one tier per host**.

---

## 1. What is free, what is generated, what is lost

### Free — works unchanged, no adapter code

| Thing | Why |
|---|---|
| **`${CLAUDE_PLUGIN_ROOT}` — all 143 refs** | Codex **documents** setting `CLAUDE_PLUGIN_ROOT` and `CLAUDE_PLUGIN_DATA` "for compatibility with existing plugin hooks." This single fact removes what looked like the largest mechanical cost in the port. |
| **One `SKILL.md` per skill, serving all three hosts** | Codex's frontmatter struct has no `deny_unknown_fields`; unknown keys are silently dropped (⚠️ source-verified, not documented). Cursor's behavior is undocumented but the spec's `metadata` escape hatch and `allowed-tools` being a *spec* field both point to lenient parsing. |
| **`agents/*.md` reviewer prompts** | Cursor officially reads `.claude/agents/` (project *and* user scope), and documents precedence: `.cursor/` > `.claude/` > `.codex/`. Same 9 files serve Claude Code + Cursor. |
| **All 6,404 lines of stdlib Python, all 26 `lib/` files, `verify-pr-body.sh`** | Zero harness surface. |
| **`gh`-driven logic — 27 calls in `ship`, 8 in `land`, 7 in `staff-review`** | Host-agnostic. |
| **All 21 eval harnesses** | They test the deterministic core. |
| **`flow.config.json` + its 30-slot schema** | Plain JSON Schema. |
| **Subagent depth** | Verified: every Flow spawn is depth 1 (agent prompt files never spawn). Safe under Codex's undocumented `agents.max_depth = 1` default. |
| **Root `CLAUDE.md`** | Cursor CLI reads it as rules; Codex reads it via `project_doc_fallback_filenames`. |

### Generated — one source, N emitted artifacts

| Source | Emits | Notes |
|---|---|---|
| `SKILL.md` frontmatter | `agents/openai.yaml` sidecar per skill | Only for the 5 skills needing `disable-model-invocation`. Codex **ignores** that key — the real control is `policy.allow_implicit_invocation: false`. Set `policy.products: [CODEX]`. ⚠️ Sidecar `interface` is **snake_case**; plugin-manifest `interface` is **camelCase**. |
| `agents/*.md` | `agents-codex/*.toml` | Codex requires TOML with `name`, `description`, `developer_instructions`. Map `tools: Read, Grep` → `sandbox_mode = "read-only"`. |
| `rules/*.md` (`paths:`) | `rules-cursor/*.mdc` (`globs:` + `alwaysApply: false`) | **`.md` in `.cursor/rules/` is silently ignored — extension must be `.mdc`.` No `.claude/rules/` compat path exists on Cursor. |
| `hooks/default-hooks.json` | `hooks/codex-hooks.json`, `hooks/cursor-hooks.json` | Cursor cannot use the Claude-format file (see §3). |
| `.claude-plugin/plugin.json` | `.codex-plugin/plugin.json`, `.cursor-plugin/plugin.json` | Cursor requires only `name`; Codex requires only `name`. |

### Lost — declare it, don't paper over it

| Loss | Host | Consequence |
|---|---|---|
| **Behavioral verify gate** (`/verify` ×34, `/run` ×18, `/run-skill-generator` ×6) | **web: neither — see §1.1** · **iOS/Android/Tauri: both** | Much smaller than the reference count implies. See §1.1. |
| **`/simplify`** (×25 in `workflow.md`, enforced by `audit-skips`) | Codex + Cursor | **Neither host substitutes it** — both ship diff-scoped reviewers pointed at *defects*, not quality. Own it as a 5th lens, layered on native diff scoping. |
| **Per-turn deterministic context injection** | **Cursor only** | `UserPromptSubmit` → `beforeSubmitPrompt`, whose entire output is `continue` + `user_message`. **No context field.** Only `sessionStart` (fire-and-forget, non-blocking) and `postToolUse` have `additional_context`. Codex is fine — `UserPromptSubmit` supports `hookSpecificOutput.additionalContext`, default ~2500 tokens, tunable via `additionalContextLimit`. |
| **Schema-enforced subagent output** | **Cursor only** | Codex has real constrained decoding: `codex exec --output-schema` becomes Responses API `text.format={type:"json_schema",strict:true}` (⚠️ source-verified). Cursor's `--output-format json` returns a free-text `result` blob, and emits **no well-formed JSON at all on failure**. |
| **Subagents inside a plugin bundle** | Codex | No `agents` field in the manifest (⚠️ source-verified absent). The 9 `.toml` files must install out-of-band to `~/.codex/agents/`. Biggest packaging asymmetry. |
| **`sandbox_mode` as a hard guarantee** | Codex | *"Codex reapplies the parent turn's live runtime overrides… including `--yolo`, even if the selected custom agent file sets different defaults."* A read-only auditor is not enforced under `--yolo`. |
| **Hook fail-closed** | Both | See §3. |

### 1.1 The bundled-skill question, answered — and a correction

An earlier draft of this doc said "Flow doesn't own its behavioral gate; accept degradation." **That over-stated the loss.** `/verify` is not one capability, it is three, and Flow already owns the expensive one.

| Layer | Who owns it today | Portable? |
|---|---|---|
| **Launch** — the per-project recipe + dispatch (`/run`, `/run-skill-generator`) | Claude Code natives | **Replace with a `flow.config.json` `launchCmd` slot.** More deterministic than a generated skill, and an improvement on Claude Code too. Neither Codex CLI nor Cursor has a launch-recipe concept to leverage. |
| **Drive + observe** — navigate, click, screenshot, read state | Platform MCPs, which **Flow already drives itself** (`verify-build:278`: *"Capture the frame via the platform's screenshot MCP"*) | **Yes.** MCP servers are host-agnostic and all three hosts are MCP clients. |
| **The plan-driven judging gate** — criteria extraction, adversarial transformation, per-dimension rubric, Unknown-blocking | **Flow, entirely** (`verify-build` 425 lines + `render-report.py` 532 + rubrics) | Already portable |

So the real gap is the launch layer plus an orchestration prompt — not an engine.

**Per-host reality for the drive/observe layer:**

- **Cursor — NATIVE, and best-in-class for web.** A **bundled** Browser tool (extension-hosted MCP, *zero user setup*): navigate, click, type, scroll, screenshot, **console output**, **network traffic**, plus dev-server port awareness (*"detect running development servers and use the correct ports instead of starting duplicate servers"*). Plus a context-filtering **Browser subagent**. One gap: **no accessibility-tree read**, which Flow's §5a a11y-gated capture protocol depends on — verify before relying on it.
- **Codex CLI — build on MCP.** No built-in browser (*"Browser isn't available in Codex CLI"* — ChatGPT desktop app only). But Codex's own docs recommend **Playwright MCP** and **Chrome DevTools MCP** by name.
- **iOS / Android / Tauri — Claude Code only in practice.** Neither host has a mobile automation story. XcodeBuildMCP is *just an MCP server*, so it should work on both — but that is untested and must not be assumed.

**Correction to §2's tier assignment:** Cursor is **not** weaker than Codex on verification. For web surfaces it is the strongest of the three. Codex remains the better first target for the *other* reasons in §0.3 (`CLAUDE_PLUGIN_ROOT`, real per-turn context injection, constrained decoding, richer subagents).

**What neither host gives you:**

- **`/simplify` — no substitute anywhere.** Codex's `/review` is explicitly the wrong lens (*"focusing on behavior changes and missing tests"*) and explicitly **does not apply fixes** (*"reports prioritized findings without changing your working tree"*). Cursor's Agent Review / Bugbot is closer — it names *"code quality problems"* and Autofix applies — but it is defect-and-security weighted, not reuse/altitude. **Build the owned lens, layer it on native scoping**: `codex review --uncommitted|--base` for Codex, `agent -p --force` for Cursor.
  ⚠️ Codex trap: the custom `PROMPT` argument **conflicts with** `--base`/`--commit`/`--uncommitted`, so you cannot combine a custom lens with explicit scoping in one invocation.
- **`/run-skill-generator` — nothing to leverage on either host.** Confirms the `launchCmd` slot decision.

⚠️ **Correction to an earlier assumption:** Codex's `auto_review.policy` is **not** code review — it is the *sandbox-approval* reviewer (*"a reviewer swap, not a permission grant"*). Only `review_model` + `/review` + `codex review` are the review surface.

⚠️ **Enterprise gating:** Cursor's browser and Codex's Computer Use are both admin-disableable. Any substitute above can be switched off by someone else's policy — a capability probe, not an assumption.

⚠️ **Cursor's built-in skill set is moving weekly** — the on-disk snapshot here (13 skills) is ~3 months behind the documented 19. Re-verify before depending on any of it.

---

## 2. Host capability matrix — the honest version

| Primitive | Claude Code | Codex | Cursor |
|---|---|---|---|
| `SKILL.md`, one file | ✅ | ✅ ignores extra keys ⚠️ | ⚠️ undocumented |
| Human-only skill | `disable-model-invocation` | `policy.allow_implicit_invocation: false` | `disable-model-invocation` ✅ exact |
| Fresh-context fork | `context: fork` + `agent:` | `.codex/agents/*.toml` + `spawn_agent` | `.cursor/agents/*.md`, reads `.claude/agents/` |
| Read-only reviewer | `tools:` allowlist | `sandbox_mode` (⚠️ not enforced under `--yolo`) | `readonly: true` ✅ |
| Per-turn context injection | ✅ `additionalContext` | ✅ `additionalContext` (~2500 tok) | ❌ **none** |
| Session-start injection | ✅ | ✅ | ⚠️ fire-and-forget, non-blocking |
| Hook blocks on failure | exit 2 | exit 2 + **stderr required** | exit 2, or `failClosed: true` |
| **Hook fails OPEN on timeout** | — | ⚠️ **yes** | **yes (documented)** |
| Constrained output | — | ✅ `--output-schema` | ❌ none |
| Plugin bundles subagents | ✅ | ❌ | ✅ |
| `${CLAUDE_PLUGIN_ROOT}` | ✅ | ✅ **documented alias** | ❌ |
| Drive/observe for **web** | ✅ `/verify` | 🟡 Playwright / Chrome DevTools MCP | ✅ **bundled Browser** (no a11y tree) |
| Drive/observe for **iOS/Android** | ✅ | ❌ untested via MCP | ❌ untested via MCP |
| Launch recipe | ✅ `/run` + generator | ❌ (desktop-app-only Actions) | ❌ | 
| Diff-scoped reviewer to build on | ✅ | 🟡 `codex review` (no apply) | 🟡 Agent Review + Bugbot Autofix |
| Transcript parseable | ✅ | ⚠️ `.jsonl`/`.jsonl.zst`, schema disclaimed | ⚠️ claims "Claude Code-compatible JSONL" (headless only) |

**Tier assignment (revised per §1.1):** Claude Code = **Full**. Codex = **High** — loses `/simplify` and the launch recipe; verification is buildable on Playwright MCP. Cursor = **High for web / Medium otherwise** — it has the *best* drive-observe layer of the three (bundled, zero-setup), but loses per-turn context injection and constrained output, which are the gate-integrity primitives.

The tiers are no longer a single ranking: **Codex is stronger on gate mechanics, Cursor is stronger on verification.** `capabilities/*.json` must therefore be per-capability, not one tier label per host.

---

## 3. The two hazards that must be designed around, not configured around

### 3.1 Both hosts fail hooks OPEN

Codex (⚠️ source-verified, undocumented — identical logic across all 7 event handlers): `Failed` status leaves `should_stop = false` for timeout, any non-zero-non-2 exit, exit-2-with-empty-stderr, and unparseable JSON stdout. A Python hook with a `SyntaxError` (exit 1) or a missing interpreter (127) **does not block**.

Cursor (documented): *"Other exit codes: Hook failed, action proceeds (fail-open)"*, and `failClosed` defaults to `false` where *"hook failures (crash, timeout, invalid JSON) allow the action through."* The default `timeout` value is **not published**.

**Rules for the generator:**
1. Every generated hook exits **exactly 0 or exactly 2**, and **always writes to stderr on 2** (Codex discards an exit-2 with empty stderr and fails open).
2. Set `failClosed: true` and an **explicit** `timeout` on every Cursor hook.
3. Never rely on "hook errored ⇒ blocked." Treat hooks as *enrichment*, and put the gate in the artifact invariant (§4).

### 3.2 Codex hook trust is hash-keyed — regeneration silently disables gates

⚠️ Source-verified: trust persists in `config.toml` as `[hooks.state]`, keyed `"<source-path>:<event>:<group_index>:<handler_index>"`, value `trusted_hash = "sha256:…"`. Docs confirm the behavior: *"Codex records trust against the hook's current hash, so new or changed hooks are marked for review and skipped until trusted"* — and explicitly for plugins: *"Installing or enabling a plugin doesn't automatically trust its hooks."*

**Combined with fail-open, a Flow upgrade silently drops every gate on Codex.** This is the single nastiest failure mode in the port.

**Mitigation, and it constrains the design:** hooks must dispatch through **one stable entrypoint per event** — e.g. `command: "$CLAUDE_PLUGIN_ROOT/tools/flow hook pre-tool-use"` — whose *string never changes across releases*. Version the logic inside `tools/flow`, never in the `command` field. Keep handler order fixed. And `/flow:doctor` must assert on Codex that every declared hook is currently **trusted**, not merely present.

---

## 4. The load-bearing invariant: stamped context

This replaces the "move the 51 substitution sites to hooks" plan, which cannot work on Cursor.

The 51 sites are not uniform:
- **~11 script-backed sites** (the 5 audit/critique forks + `ship` + `verify-build`) feed deterministic Python. **These are the gates.**
- **~40 inline sites** are `git`/`jq`/`cat` orientation (branch name, config slots). If the model runs these itself, the cost is convenience, not soundness.

**Invariant to add:** `flow context <mode>` writes its output to a file stamped with `branch`, `head_sha_short`, and a content digest. Every consumer refuses to produce a verdict when the stamp is absent or stale, emitting the existing `[decision-required]` routing instead.

This is not new machinery — it is generalizing what already exists:
- `ship/lib/render-test-plan.py:138` — *"an un-stamped buffer reads as un-judged"* (the load-bearing untrusting default)
- `audit-skips/lib/skip-audit-checks.py:178-179` — `fresh` computed from `branch` + `head_sha_short` match
- `audit-skips/SKILL.md:10` — *"verdict-without-artifact == skip"*

**Why this is the right answer:** the guarantee stops depending on host mechanics Flow doesn't control and starts depending on Flow's own engine, which is identical on all three hosts. Injection becomes a per-host *optimization*: Claude Code and Codex hooks inject mechanically; Cursor's skill body asks the model to run it, and non-compliance is **detected** rather than silent. It also closes the roadmap § Exploration item on stamping the resolved repo root into the skip-audit handoff — same mechanism, same PR family.

---

## 5. Target layout

### 5.0 Not three plugins — one plugin, three manifests

**There is exactly one source tree and one plugin root.** Generated artifacts are committed build output (all three hosts install from a git repo with **no build step**, so they must be in the repo), and are never hand-edited. `flow gen --check` in CI is what makes that true rather than aspirational.

**Plugin root stays `plugins/flow/`** — the existing `.claude-plugin/marketplace.json` already points there (`"source": "./plugins/flow"`), and all three host manifests live side by side inside it.

The mechanism that lets three hosts read one tree without colliding is documented manifest behavior: **naming a component path in the manifest replaces folder auto-discovery for that component.** So each host's manifest points at the variant it can parse, and ignores the others.

```
flow/                                        ← repo root
├── .claude-plugin/marketplace.json          SOURCE   Claude Code entry; ALSO read by Codex (documented)
├── .cursor-plugin/marketplace.json          GEN      Cursor marketplace entry
│
└── plugins/flow/                            ← THE plugin root, all hosts
    │
    ├── .claude-plugin/plugin.json           SOURCE   ─┐
    ├── .codex-plugin/plugin.json            GEN       │ 3 manifests, 1 root
    ├── .cursor-plugin/plugin.json           GEN      ─┘
    │
    ├── skills/<name>/
    │   ├── SKILL.md                         SOURCE   ★ ONE file → all 3 hosts
    │   ├── agents/openai.yaml               GEN        Codex sidecar (only the 5 that need it)
    │   └── lib/**                           SOURCE     shared verbatim (26 files)
    │
    ├── agents/*.md                          SOURCE   ★ Claude Code + Cursor read as-is (9)
    ├── agents-codex/*.toml                  GEN        Codex; installed out-of-band (9)
    │
    ├── rules/*.md            (paths:)       SOURCE     Claude Code (4)
    ├── rules-cursor/*.mdc    (globs:)       GEN        Cursor — .mdc MANDATORY (4)
    │
    ├── hooks/
    │   ├── default-hooks.json               SOURCE   ★ Claude Code + Codex share this format
    │   ├── codex-hooks.json                 GEN        stable-entrypoint dispatch (§3.2)
    │   └── cursor-hooks.json                GEN        native camelCase events, failClosed
    │
    ├── tools/flow                            SOURCE   NEW — determinism + host dispatch
    │                                                  ⚠️ NOT bin/ — that PATH-injects (§5.4)
    ├── tools/memory/**                       SOURCE   existing
    ├── adapters/{codex,cursor}/gen.py        SOURCE   NEW — the generators
    ├── capabilities/*.json                   SOURCE   NEW — per-host tier declarations
    │
    ├── scripts/**  schema/**  docs/**        SOURCE   shared verbatim, untouched
    └── evals/**                              SOURCE   98 files; + per-adapter fixtures
```

★ = the three places where one file genuinely serves multiple hosts with no transformation.

### 5.1 What each manifest declares

Discovery semantics differ **per field per host**. This table is the contract; §5.2 lists what breaks if you get it wrong.

| | Claude Code | Codex | Cursor |
|---|---|---|---|
| `skills` | **ADDS to** default `skills/` | **ADDS to** default `./skills` ⚠️ *(undocumented — [PR #28790](https://github.com/openai/codex/pull/28790))* | **REPLACES** — must set `"./skills/"` |
| `agents` | **REPLACES** default `agents/` | **field does not exist** — cannot bundle subagents | **REPLACES** — must set `"./agents/"` |
| `rules` | not a documented component (§5.7) | n/a | **REPLACES** — **must set `"./rules-cursor/"`** |
| `hooks` | own merge rules; default `hooks/hooks.json` | **REPLACES**; default `hooks/hooks.json` | **REPLACES**; default `hooks/hooks.json` |
| `mcpServers` | own merge rules | **no auto-discovery at all** — `.mcp.json` imported only if declared | auto-detects `mcp.json` |
| Human-only skill | `disable-model-invocation` | `agents/openai.yaml` → `policy.allow_implicit_invocation: false` | `disable-model-invocation` (exact) |

**Two asymmetries that matter most:**

- **Codex's `skills` is ADDITIVE, so `./skills` is *always* loaded** no matter what the manifest says. You cannot scope skills per-host by path. Any per-host gating must happen inside `SKILL.md` frontmatter or the `agents/openai.yaml` sidecar.
- **All three hosts auto-discover the same `hooks/hooks.json` path** — but Codex wants Claude-style PascalCase events and Cursor wants native camelCase. **Never place a file at `hooks/hooks.json`.** Per-host filenames + explicit manifest pointers are mandatory (§5.2).

### 5.2 The four silent-no-op defects — and the CI assertions that catch them

Every one of these fails **silently**, which is this repo's documented worst bug class (FB-0010 silent-skip). Each gets a mechanical assertion in `flow gen --check`.

| # | Defect | Assertion |
|---|---|---|
| 1 | `hooks/default-hooks.json`, `codex-hooks.json`, `cursor-hooks.json` match **no host's auto-discovery default**, so hooks load for nobody unless every manifest declares its own path. | Every manifest declares `hooks`, **and** the declared path resolves, **and** `hooks/hooks.json` does **NOT** exist (it would be auto-read by both Codex and Cursor in the wrong format). |
| 2 | Cursor auto-discovers `rules/` and **accepts `.md`** — so Flow's Claude-format rules (`paths:` frontmatter) would load into Cursor **unscoped**, since Cursor expects `globs:`. | `.cursor-plugin/plugin.json` sets `"rules": "./rules-cursor/"`. Assert present; assert every file in `rules-cursor/` is `.mdc` with `globs`/`alwaysApply`. |
| 3 | `agents-codex/*.toml` is **inert on every host** — no loader reads it. The out-of-band install to `~/.codex/agents/` is entirely undocumented territory, and a plugin hook **cannot** do it silently (plugin hooks are untrusted until the user reviews them). | `flow install --host codex` places them; `/flow:doctor --host codex` asserts they landed. Without this the 5 fork-based audit skills run **inline**, which looks identical to working. |
| 4 | Three manifests drift. **This is not hypothetical** — `firebase/agent-skills` ships all three and its `license` has already diverged (MIT in the Claude manifest, Apache-2.0 in the other two). | Cross-manifest field-agreement check on `name`, `version`, `license`, `repository`. |

**Why Flow can adopt this layout safely where Firebase didn't:** Firebase hand-maintains three manifests, so drift is inevitable. Flow **generates two from one**, so the failure mode is structurally impossible. That is the entire argument for generation over hand-maintenance, and it is the reason this layout is defensible here.

### 5.3 Honest status of the layout

**Neither vendor documents, recommends, or provides an example of a single-repo multi-host plugin layout.** Stated plainly because it matters:

- Cursor's plugin docs never mention another host.
- Codex's two cross-host affordances are both framed as *legacy*: the officially-supported `$REPO_ROOT/.claude-plugin/marketplace.json` ("legacy-compatible"), and the submission portal's `claude_format_normalized`, which **converts** `.claude-plugin/plugin.json` into `.codex-plugin/plugin.json`. Conversion-on-upload is the opposite of endorsing keeping both.
- **OpenAI ships its own plugin as three separate repos** — `openai-developers-for-claude`, `openai-developers-for-cursor`, plus the directory listing — with different internal layouts.

Against that: **36 repos were verified shipping 2+ host manifests at one plugin root**, 34 with all three, including Firebase, DataDog, Slack, Microsoft, Meta, Kraken, Resend, and GitGuardian. It is a real de-facto convention among credible publishers.

**Verdict: adopt it, with the §5.2 assertions.** The pattern works, is source-verified deterministic on Codex, and is empirically verified non-breaking on Claude Code (§5.4). The residual risk is that it is undocumented on both non-Claude hosts and could change without a changelog obligation — which the drift/resolve assertions turn into a loud CI failure rather than a silent regression.

⚠️ **Correction to an earlier claim in the companion research doc:** Codex does **not** overlay-merge `.claude-plugin/plugin.json` with `.codex-plugin/plugin.json`. Manifest discovery is **first-match-wins** over `[".codex-plugin", ".claude-plugin", ".cursor-plugin"]` and then breaks. The overlay that does exist is `MarketplacePluginManifestFallback` — a marketplace-entry↔manifest bridge, a different mechanism.

### 5.4 Claude Code regression safety — empirically verified

Tested against CLI **v2.1.141** on this plugin: adding `.codex-plugin/`, `.cursor-plugin/`, `agents-codex/*.toml`, `rules-cursor/*.mdc`, `capabilities/*.json`, and a nested `skills/ship/agents/openai.yaml` produced an **identical component inventory** (17 skills / 9 agents) and `claude plugin validate` passed. Discovery is fixed-name, `.claude-plugin` is matched exactly with no `.*-plugin` glob, and agent discovery is plugin-root-anchored so a nested `agents/` inside a skill is off every scan path. The plugin root already ships 5 unrecognized directories (108 files) today.

**Two hard constraints found:**

1. **`bin/` is a documented Claude Code component** — *"Executables added to the Bash tool's `PATH`… invokable as bare commands."* Putting the CLI under `bin/` would inject a bare `flow` onto every consumer's PATH and **collide with Facebook's Flow type-checker** in exactly the `web` and `tauri-rust-ts` stacks Flow ships. **Put it at `tools/flow` instead.** Also avoid the other reserved names: `commands/`, `workflows/`, `output-styles/`, `themes/`, `monitors/`, `settings.json`, `.mcp.json`, `.lsp.json`, `hooks/hooks.json`.
2. **Keep `plugin.json` metadata-only.** Unknown top-level keys are documented-safe and load fine at runtime, but **fail `claude plugin validate` on v2.1.141** — reddening CI while user installs stay fine. All multi-host config goes in sibling files.

**The real regression gate for CI** (only Claude Code has a validator — Codex and Cursor have none):

```bash
claude plugin validate ./plugins/flow
claude plugin validate .
claude --plugin-dir ./plugins/flow plugin details flow@inline   # assert 17 skills / 9 agents
```

### 5.5 Shared vs generated, counted

| Class | Files | Share |
|---|---|---|
| **Source, shared by all hosts** | ~165 (43 skills + 9 agents + 4 rules + 1 hooks + 6 scripts + 4 schema/docs/tools + 98 evals) | **~88%** |
| **Generated per host** | ~22 (2 manifests + ~5 sidecars + 9 TOML + 4 `.mdc` + 2 hook files) | ~12% |

The 12% is machine-written and CI-verified. **You maintain the 88%.**

### 5.6 The maintenance loop

```
edit source  →  flow gen  →  commit source + generated together
                                        ↓
                          CI: flow gen --check  (fails if drifted)
```

Three rules make it hold:
1. Every generated file carries a `DO NOT EDIT — generated by flow gen` header.
2. `flow gen --check` re-runs the generator into a temp dir and diffs. Any hand-edit fails the build.
3. **The generator fails loudly when a source declares a semantic with no mapping for a target host** — e.g. adding `context: fork` to a new skill errors until the Codex TOML and Cursor agent mappings exist. Silent omission is what produces three divergent plugins; a hard failure is what prevents it.

### 5.7 Where per-host divergence is *allowed* to live

Exactly two places, both small and both declarative:

- `adapters/{codex,cursor}/gen.py` — the transformation rules.
- `capabilities/{claude-code,codex,cursor}.json` — which gates are mechanical vs advisory on that host, consumed by `/flow:doctor`.

Nothing else may branch on host. If a skill body needs an `if codex:` clause, that is a signal the logic belongs in `tools/flow` behind a capability check, not in prose.

### 5.8 Do NOT dual-publish skills

Do not place the same skill in both `.claude/skills/` and `.agents/skills/` of one project. Cursor reads both, Codex reads `.agents/`, and **neither dedupes by name** — Codex docs, verbatim: *"If two skills share the same `name`, Codex doesn't merge them; both can appear in skill selectors."* Plugin packaging sidesteps this entirely because each host loads its own manifest. For loose user-scope installs target `~/.agents/skills/` only, never `~/.codex/skills/` (⚠️ deprecated root that also hosts the `.system` cache Codex rewrites on upgrade).

**Do NOT dual-publish the same skill into `.claude/skills/` and `.agents/skills/` in one project.** Cursor reads both, Codex reads `.agents/`, and **neither does name-based dedupe** — Codex docs: *"If two skills share the same `name`, Codex doesn't merge them; both can appear in skill selectors."* You'd get duplicate entries. Plugin packaging avoids this entirely because each host loads its own manifest. (This corrects the dual-publish advice in the companion research doc.)

**Install targets:** user skills → `~/.agents/skills/`, never `~/.codex/skills/` (⚠️ source-verified deprecated, and it hosts the `.system` cache Codex rewrites on upgrade — confirmed on this machine: `~/.codex/skills/.system/.codex-system-skills.marker`).

---

## 6. Phases

### Phase 0 — Harden on Claude Code only (3–4 PRs, zero host work)

Everything here is independently valuable and ships whether or not a port happens.

| PR | Content | Acceptance |
|---|---|---|
| **0a** | **Stamped-context invariant** (§4). `flow context <mode>` writes stamped artifacts; the 11 script-backed consumers assert stamp freshness and route `[decision-required]` on absent/stale. | New eval fixture: stale stamp ⇒ `[decision-required]`, never a clean verdict. Wired into `ci.yml`. |
| **0b** | **Renderer fail-loud audit.** `render-test-plan.py`, `render-report.py`, `skip-audit-checks.py` must fail loudly on schema mismatch, never degrade. Prerequisite for hosts without constrained decoding. | Fixture per renderer: malformed model JSON ⇒ non-zero exit + named error, not a partial render. |
| **0c** | **Env overrides + schema slots.** `FLOW_DISAGREEMENT_DIR` (chip already queued); add `host` + `capabilityTier` slots; land the already-known-missing `changelogPath`. Re-derive the "30 slots" fan-out count across `workflow.md` / `plugin.json` / `marketplace.json` / doctor. | `git grep -n '30 slots'` returns zero contradictions. |
| **0d** | **`extract_session.py` adapter seam.** Split discovery+parse (`:74-208`) behind an interface; keep `:222-673` + `bounding_logic.py` neutral. Tool-name tables (`:347`, `:350`, `:354`, `:575`) become a per-host map. | Eval for the **false-`UNREAD`** failure mode: an unrecognized tool name must fail loudly, not silently make every artifact `UNREAD` and mint false "unverified recall" findings. |

### Phase 1 — `tools/flow` + the generator + drift enforcement (2–3 PRs)

| PR | Content | Acceptance |
|---|---|---|
| **1a** | **`tools/flow` CLI** wrapping existing `lib/*.py`: `flow context`, `flow gate`, `flow render`, `flow audit`, `flow hook <event>`, `flow doctor`. Claude Code artifacts now call the CLI instead of inlining shell. | All 21 existing evals still green; ~40 inline substitution sites reduced to CLI calls. |
| **1b** | **The generator + drift lint.** `adapters/*/gen.py` emits every generated artifact in §5. A `flow gen --check` mode fails if any emitted artifact differs from what the source would produce. | New `evals/run_adapter_gen_evals.py`, **enumerated in `ci.yml`**. CI fails on any hand-edited generated file. Every generated file carries a `DO NOT EDIT — generated by flow gen` header. |
| **1c** | **Instructions-as-data.** `flow gate ship --step 2` returns JSON describing what must happen next, including `{action: "spawn_fork", prompt_file, schema}`. Adapters translate the spawn vocabulary. | `ship` and `verify-build` orchestration expressed as data; one Claude Code translator consumes it. |

**◆ Decision gate.** Proceed only if Phase 1 landed clean and dogfooded on ≥2 real Flow PRs. If the CLI refactor doesn't hold under Flow's own gates, stop — the port was never the constraint.

### Phase 2 — Codex adapter (3 PRs)

| PR | Content | Acceptance |
|---|---|---|
| **2a** | `.codex-plugin/plugin.json`, `agents/openai.yaml` sidecars, `agents-codex/*.toml`, `hooks/codex-hooks.json`. Hooks dispatch through the **stable** `tools/flow hook <event>` entrypoint (§3.2). | `codex plugin marketplace add by-dev-tools/flow --ref vX` installs; `/skills` lists all 17. |
| **2b** | Codex transcript adapter: `~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl` **and `.jsonl.zst`**; prefer `transcript_path` from hooks over globbing; prefer `codex exec --json`'s documented event stream and `last_assistant_message` over parsing rollouts (schema is explicitly disclaimed as unstable). Tool map: `Read\|Grep\|Glob → Bash`, `Write\|Edit → apply_patch`, `Task → spawn_agent`. | Fixtures for both plain and zstd rollouts, plus an unknown-tool-name case. Note: hook *matcher* aliases ≠ payload `tool_name` — payload always reports `apply_patch`. |
| **2c** | Capability declaration: tier **High**, `verifyEnabled` forced false with a loud reason, `/flow:doctor --host codex` asserting hooks are **trusted** (not just present), skill-catalog budget check (2% of context or 8,000 chars — 17 skills *will* get squeezed, so front-load trigger words in descriptions). Adopt `codex exec --output-schema` to harden the 3 renderers' inputs. | Doctor prints mechanical-vs-advisory per gate. A skipped verify gate blocks ship auto-invocation exactly as `platform: library` does today. |

### Phase 3 — Cursor adapter (2 PRs)

| PR | Content | Acceptance |
|---|---|---|
| **3a** | `.cursor-plugin/plugin.json`, `rules-cursor/*.mdc` (`.mdc` mandatory — `.md` is silently ignored), `hooks/cursor-hooks.json` using **native** events. Do **not** ship a shared `.claude/settings.json` hooks path: `tool_input.file_path` is undocumented and probably absent (Cursor's file tools use `path`/`fileText`), `Edit` collapses into `Write`, `Glob`/`WebFetch`/`WebSearch` have no equivalent, and `tool_input` flips between object and JSON-string across events. Use `beforeShellExecution` (`.command`) and `beforeReadFile`/`afterFileEdit` (`.file_path`) — top-level and documented. `failClosed: true` + explicit `timeout` everywhere. | Local install via `~/.cursor/plugins/local/flow` symlink; skills and agents resolve. |
| **3b** | Tier **Medium**: no per-turn injection (skill bodies invoke `flow context` and the §4 stamp catches non-compliance), no constrained output (text contract + Python parser is the enforcement point), verify disabled. Document the **account-level** prerequisite: *"Include third-party Plugins, Skills, and other configs"* must be enabled — it cannot be set from the repo, so doctor must verify it took effect. | Doctor names every advisory gate. An advisory gate never renders byte-identically to a mechanical one. |

---

## 7. How this stays maintainable

The maintainability property comes from five mechanical rules, not discipline:

1. **One source per artifact, enumerated in §5.** Generated files carry a `DO NOT EDIT` header.
2. **`flow gen --check` in CI.** Editing a source without regenerating fails the build. This is the FB-0010 fan-out defense applied to the adapter layer — grep-first becomes generate-first.
3. **One `SKILL.md` per skill, three hosts.** Extra frontmatter is ignored, not honored — so any Claude-Code-only *semantic* (`context: fork`, `disable-model-invocation`) must have a generated counterpart, and the generator fails loudly if a source declares one with no mapping for a target host.
4. **Capability is data, not prose — and PER-CAPABILITY, not one tier per host.** §1.1 showed the hosts don't rank linearly (Codex is stronger on gate mechanics, Cursor on verification), so `capabilities/*.json` declares each capability separately (`contextInjection`, `constrainedOutput`, `driveObserveWeb`, `driveObserveMobile`, `freshContextFork`, `hookFailClosed`). `/flow:doctor` renders it, and adding a gate forces declaring which capability it needs.
5. **Per-host eval fixtures, enumerated in `ci.yml`.** CI enumerates rather than globs, so every new harness must be wired explicitly.

**The rule that keeps it honest:** never let an advisory gate render byte-identically to a mechanical one. That is the FB-0074 lesson, and at three hosts it's the whole ballgame.

---

## 8. Open items to verify empirically (cheap, and they gate real work)

| # | Question | Cost | Gates |
|---|---|---|---|
| 1 | Do Cursor and Codex actually tolerate Flow's extra SKILL.md frontmatter without erroring? Codex is source-verified lenient; Cursor is undocumented. | 5 min | Whether one `SKILL.md` works or each host needs its own |
| 2 | Does Cursor's headless transcript really write *"Claude Code-compatible JSONL"* (its April 2026 changelog claim), and is it thick enough for `extract_session.py`? | 30 min | Size of PR 3a |
| 3 | Does Claude Code enforce `allowed-tools` for the `Skill` tool? | 15 min | Severity of the queued `ship-spike:176` chip |
| 4 | Codex `agents.max_concurrent_threads_per_session` real default (⚠️ source says 6 for v1, 4 for v2; undocumented). | 10 min | staff-review's 4-lens fan-out |
| 5 | Does Flow's doctrine fit Codex's 32 KiB `AGENTS.md` cap? The marketplace description alone is 17 KB. | 10 min | Whether `AGENTS.md` can carry orientation |

Do #1 first. It's five minutes and it decides the shape of the generator.

---

## 9. Explicitly out of scope

- Any host other than Claude Code, Codex, Cursor.
- MCP as a delivery vehicle. MCP prompts as slash commands **do not work on Codex** ([#8342](https://github.com/openai/codex/issues/8342), open since 2025-12-19, no maintainer reply), and SEP-2640 forbids executable skill content by design.
- Codex custom prompts (`~/.codex/prompts/`) — **officially deprecated** in favor of skills, user-scope only, not repo-shareable.
- Relying on `.claude-plugin/plugin.json` being discovered by Codex. It is (⚠️ source-only, `DISCOVERABLE_PLUGIN_MANIFEST_PATHS`), but emit `.codex-plugin/plugin.json` explicitly. The `.claude-plugin/marketplace.json` path **is** documented and can be relied on.
- Building a Flow-owned behavioral-verify engine. That is a separate, larger decision (§10).

---

## 10. The one decision this plan does not make

**This decision got cheaper.** §1.1 established that Flow already owns the judging gate, and that the drive/observe layer is host-provided (bundled on Cursor, Playwright MCP on Codex). So the choice is no longer "build an engine or give up":

- **Web surfaces — own it.** The work is a `launchCmd` slot plus an orchestration prompt over MCP primitives Flow *already drives itself*. Medium, not large. Cursor's bundled Browser makes this genuinely cheap there; Codex needs Playwright MCP declared as a dependency.
- **iOS / Android / Tauri — accept degradation.** Neither host has a mobile automation story. XcodeBuildMCP is just an MCP server and *should* work on both, but that is untested; treat it as a spike, not a plan. Until proven, `ship` on those platforms requires an explicit human "ship it" on non-Claude hosts, exactly as `platform: library` does today.

Recommendation: **split the decision by platform rather than by host.** Do the web path in Phase 2/3 — it is affordable and it is where Cursor is strongest. Leave mobile degraded and *declared*. Phase 0's stamped-context work is what makes the degradation visible rather than silent, which remains the property that actually matters.

**Before committing to the web path, run one spike:** confirm Cursor's Browser can return an accessibility tree. Flow's §5a protocol is a11y-gated (*snapshot the tree, assert the state, then screenshot*), and the tool's documented surface is DOM + screenshot only. If there is no a11y read, either §5a's gate weakens on Cursor or the protocol needs a DOM-based variant — and that is a design decision, not an implementation detail.
