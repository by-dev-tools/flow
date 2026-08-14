# Flow × service-agnostic — feasibility & architecture report

**Date:** 2026-07-29
**Branch:** `claude/flow-service-agnostic-96aec1`
**Plugin version at time of research:** v1.27.0
**Status:** research / direction-setting. **No plugin artifacts changed by this doc.** Actionable hooks land in `roadmap.md` § Exploration; the staged plan in §8 is a proposal, not an approved scope.

> ⚠️ **PARTIALLY SUPERSEDED.** This is the *field survey*. For every execution decision — layout, tiering, the CLI's location, how context is injected — `dev-docs/handoffs/service-agnostic-roadmap-2026-07.md` is authoritative. Later validation against official docs, `openai/codex` source, and the shipped Claude Code binary overturned several conclusions below; those are marked inline.

Question researched: *can Flow run on Codex, Cursor, and other agents instead of only Claude Code — what are the implications, what approaches exist, and how do context / skills / workflows survive the move?*

Four parallel research streams: Flow's internal coupling map (first-hand, this branch), Codex CLI, Cursor + 12 other harnesses, and portability prior-art/tooling.

---

## 0. One-line synthesis

> **The premise is half out of date. Flow's *doctrine* is already portable — `SKILL.md` is a published spec with ~44 adopters, and Claude Code's `.claude/skills/` and `.claude/agents/` are read by Cursor, Copilot, Amp, OpenCode, and Cline directly. But the *loop machinery* will not standardize: the one governed spec body with authority here (Agent Plugins v1.0.0, TSC from Amazon/Cursor/Microsoft/OpenAI/Vercel) has **formally declared commands, hooks, agents, and rules out of scope** as "too client-specific for a stable portable contract." So the portable artifact set is exactly two things — skills and MCP servers — and everything else must be generated per host. Flow's orchestration currently lives inside prompt markdown; moving it into a `flow` CLI is the whole job. Two real losses: hook-based gates are **fail-open by default** on both non-Claude hosts, and `/simplify` has no substitute anywhere. ⚠️ *A third claimed loss — "Flow doesn't own its behavioral-gate engine" — was later **overturned**: Flow already owns the judging gate, the drive/observe layer is host-provided (bundled on Cursor), and only the launch recipe is genuinely missing. See roadmap §1.1.***

**Direction-of-travel caveat, stated plainly:** the "portable" half of this is vendor convergence, not ratified standards. Every cross-tool win below was produced unilaterally by vendors while the corresponding standards proposal sat unanswered. Design for it; don't assume it's stable.

---

## 1. What Flow actually is, measured

Three separable assets with very different portability profiles. Measured on this branch:

| Asset | Size | Portability |
|---|---|---|
| **Doctrine** — 17 `SKILL.md`, 9 `agents/*.md`, 4 `rules/*.md`, `docs/workflow.md`, 5 judging rubrics | **7,900 lines markdown** | Portable **today**, some of it *unchanged* (§3.1) |
| **Deterministic core** — 26 non-eval `.py`, 1 `.sh`, 1 `.mjs`, `flow.config.schema.json` (32 slots) | **8,015 lines Python**, stdlib only, zero third-party deps | Host-agnostic **already** |
| **Eval harnesses** — 29 files, all enumerated in CI | **7,603 lines Python** | Host-agnostic already |
| **Orchestration glue** | see §2 | **0% portable** |

~15,900 lines of host-neutral content wrapped in a thin Claude-Code-specific layer. The asset:liability ratio is much better than it looks from outside.

**Load-bearing skills:** `ship` (1370 L), `doctor` (677), `verify-build` (446), `ship-spike` (392), `land` (410), `post-merge` (406), `staff-review` (300).
**Thin dispatch skills** (a `!`-backtick call plus "obey your system prompt"): `critique-plan` (79), `log-disagreement` (48), `audit-plan` (30), `audit-completion` (27). Cheapest to port, most dependent on `context: fork`.

---

## 2. The coupling inventory — what actually breaks

Counted on this branch, not estimated:

| Coupling | Count | Notes |
|---|---|---|
| `${CLAUDE_PLUGIN_ROOT}` references | **165** | ~38 distinct paths. Several already carry a `plugins/flow/...` fallback — the seed of a shim. |
| `` !`shell` `` prompt-time substitution sites | **51** | Across 15 of 17 skills. **The sharpest incompatibility** (§5.1). |
| `Skill("...")` composition calls | **21** | Flow's "composition, not reimplementation" idiom. |
| `Agent` / `subagent_type` spawn sites | **7** | staff-review's four lenses, security/a11y `Explore`, verify-build's adversarial fork. |
| Skills using `context: fork` + `agent:` | **5** | All four audit skills + critique-plan. They have **no body logic** — the harness fork *is* the mechanism. |
| Skills using `disable-model-invocation: true` | **3** | `land`, `post-merge` — the human-only gate. |
| Bundled-native dependencies | `/verify` ×42, `/simplify` ×25, `/run` ×18, `/run-skill-generator` ×10 | Flow **does not own** these (§5.2). |
| Hook configs | 3 files | The `SessionStart` hook is the **only unattended entry point** in the whole system. |
| Packaging | 2 manifests | Descriptions are 17KB and 25KB of release-note prose doubling as the changelog surface. |

**Transcript parsing is the deepest single coupling.** `scripts/extract_session.py` (963 L) reimplements Claude Code's project-dir slug encoding (`slugify_cwd`, `:74-89`), globs `~/.claude/projects/*/<session_id>.jsonl`, and parses the Anthropic Messages API content-block shape. It hard-codes Claude Code **tool names as data** (`:347` `("Read","NotebookRead")`, `:350` `"Grep"`, `:354` `"Bash"`, `:575` `("Edit","Write","NotebookEdit","MultiEdit")`).

The failure mode is the dangerous kind: if tool names don't match, `artifact_was_read()` returns `False` for everything, every artifact renders `UNREAD`, and **the auditor mints false "unverified recall" findings**. Silent wrong answer, not a crash. This matters more than it looks because **Codex has no first-class `Read`/`Grep`/`Glob` at all** — file access goes through the shell. Any host adapter needs an eval fixture on this exact path.

**Already-clean seams:**
- `scripts/bounding_logic.py` (50 L) — **zero** harness dependency. An adapter only needs `list[Turn]` + normalized `{name, input, result}` dicts. Cleanest seam in the repo.
- `$CLAUDE_PROJECT_DIR` is only the **second-precedence** root resolver behind `git rev-parse --show-toplevel` — so root anchoring is largely portable already. (And Cursor exports `CLAUDE_PROJECT_DIR` as an alias — see §4.2.)
- `contribution_store.py:44-47` honors `FLOW_CONTRIB_DIR`. `log_disagreement.py:32-35` does **not** — asymmetric, and re-hardcoded in `contribute/SKILL.md:38`.

**Notably absent (good news):** zero use of `TodoWrite`, plan mode, permission modes, background tasks, `WebFetch`/`WebSearch`. And **no model name or tier is pinned anywhere** — no `model:` key in any skill or agent frontmatter. The only `claude-*` strings are commit trailers.

---

## 3. The field, as of 2026-07

### 3.1 The finding that reframes everything: `.claude/` is the de-facto standard

Flow's format isn't a liability. Competitors read it directly.

| Flow artifact | Read natively by | Fidelity |
|---|---|---|
| `.claude/skills/` + `SKILL.md` | **Cursor, GitHub Copilot, Amp, OpenCode, Cline** (plus Claude Code) | **Real** — same file, same parse |
| `.claude/agents/` (subagent definitions) | **Cursor, GitHub Copilot** | **Real** |
| `.claude/rules/` | **GitHub Copilot** (via `chat.instructionsFilesLocations`) | Real |
| `.claude/settings.json` hooks | **Cursor, GitHub Copilot** — published event mappings | ⚠️ **Compat shim, not contract compatibility** — see below |
| `CLAUDE.md` | **Cursor CLI, Copilot, Zed, OpenCode, Amp** (fallback), Codex (via `project_doc_fallback_filenames`) | Real |

**The hooks claim needs qualifying — this is where I initially overstated it.** Cursor does ship a [third-party hooks](https://cursor.com/docs/reference/third-party-hooks) page that reads Claude Code hooks from `.claude/settings.json`, and its env-var table documents `CLAUDE_PROJECT_DIR` verbatim as *"Alias for project dir (Claude compatibility)"*. Copilot goes further and is deliberately bilingual: camelCase event names get camelCase fields, PascalCase names get **snake_case** fields, *"as used in Claude Code plugins."* Codex's Rust hook engine struct is literally named **`ClaudeHooksEngine`**.

But underneath, the contracts diverge in ways that break scripts:

- **Casing:** Cursor `preToolUse` vs Claude Code `PreToolUse`. Native config files are not portable.
- **stdin schema differs materially:** Cursor sends `conversation_id`, `generation_id`, `workspace_roots`, `user_email` and has **no `session_id` and no `cwd`**. Claude Code sends `session_id`, `cwd`, `tool_name`, `tool_input`, `tool_use_id`. **A hook script reading `.cwd` breaks on Cursor.**
- **Decision shape:** Cursor flat `permission: allow|deny|ask`; Claude Code nested `hookSpecificOutput.permissionDecision`.
- **Event model and scale:** Claude Code has **29 events** and is tool-centric with a `matcher`; Cursor has ~21 and is operation-centric (`beforeShellExecution`, `beforeReadFile`, Tab hooks). Gemini renames (`BeforeTool` ≠ `PreToolUse`); Zed's proposal uses snake_case. **Four incompatible casing conventions across five tools; Copilot alone speaks two.**

This matters concretely for Flow: `plugins/flow/hooks/default-hooks.json` reads `.tool_input.file_path` and `.tool_input.command`. Whether Cursor's shim populates those under a Claude-cased event is **unverified** (§10.3) and is the single fact that decides how cheap Move 1 is.

**Two corrections to claims I made in the first draft**, both verified against vendor docs:

1. **Claude Code does not read `AGENTS.md`.** Verbatim from [code.claude.com/docs/en/memory](https://code.claude.com/docs/en/memory): *"Claude Code reads `CLAUDE.md`, not `AGENTS.md`."* The documented bridges are an `@AGENTS.md` import inside `CLAUDE.md`, or `ln -s AGENTS.md CLAUDE.md`. (Demand signal: [claude-code#6235](https://github.com/anthropics/claude-code/issues/6235), open since 2025-08-21, **4,472 👍**.) So the symlink recommendation stands — but as a bridge, not as native support.
2. **Claude Code does not read `.agents/skills/`** — zero occurrences of `.agents` in its skills docs; only `.claude/skills/` and `~/.claude/skills/`. Tracked at [claude-code#16345](https://github.com/anthropics/claude-code/issues/16345). **So dual-publishing is genuinely dual** — the `.agents/` copy serves everyone else, the `.claude/` copy serves Claude Code. Not a symlink-and-done.

**Two standards are real and multi-vendor:**

- **Agent Skills** — published [specification](https://agentskills.io/specification), repo [agentskills/agentskills](https://github.com/agentskills/agentskills) (23.6k stars, actively maintained). *"Originally developed by Anthropic, released as an open standard."* ~44 adopting products. Six frontmatter fields, **two required**: `name` (≤64 chars, must match parent dir) and `description` (≤1024); optional `license`, `compatibility`, `metadata`, `allowed-tools` (**Experimental**). Progressive disclosure in three tiers. Has a validator (`skills-ref`) — which AGENTS.md lacks. ⚠️ **But it is unversioned** (no releases, no version string, no RFC-2119 boilerplate), **it does not standardize discovery directories** (explicitly: *"it only defines what goes inside them"*), and **Claude Code contradicts it** — Claude Code says *"All fields are optional… `name` defaults to the directory name"* and adds ~15 non-spec fields. Claude Code's precedence also **inverts the ecosystem norm**: enterprise > personal > project, where the spec's implementation guide states the universal convention is project-overrides-user. Secondary sources claiming AAIF stewardship of Agent Skills are **unsupported by primary sources**.
- **AGENTS.md** — governance real, maintenance inert. Contributed to the **Agentic AI Foundation** (Linux Foundation, formed 2025-12-09; platinum members include AWS, Anthropic, Google, Microsoft, OpenAI). Repo is now `agentsmd/agents.md`. But: **there is no specification document** — no `spec/`, no schema, no `CONTRIBUTING.md`, no validator. The entire normative surface is a landing-page FAQ, whose answer to *"Are there required fields?"* is *"No."* **Last commit 2026-03-12 — 4 commits in 6 months, and `author_association` is `NONE` for all of the last 100 issue comments (zero maintainer participation).** Its own "define a spec" issue ([#211](https://github.com/agentsmd/agents.md/issues/211)) sits open and unanswered. It standardizes a filename and one precedence sentence: *"The closest AGENTS.md to the edited file wins."*
  Two traps: **"supports AGENTS.md" ≠ "AGENTS.md is authoritative"** (Zed ranks it 7th of 9 behind `.rules`/`.cursorrules`; Augment ranks `CLAUDE.md` above it; Warp prefers `WARP.md`), and **nested AGENTS.md is not universal** despite being the headline rule (Roo and Jules are root-only; VS Code's nesting is experimental). Of the 23 tools on the adoption list, 19 verify, 3 don't (**Aider, Phoenix, Semgrep** — no vendor doc found), and 1 is **contradicted** (Claude Code). The "60k projects" figure is an unaudited file count, stale since March.

**`.agents/skills/` is the emerging vendor-neutral directory** — read by Cursor, Codex (where it is the *only* official path), Gemini CLI, Amp, OpenCode, Zed (exclusively), Copilot, Roo. **`.claude/skills/` is a de-facto second** — Cursor, Copilot, Amp, OpenCode, Cline. Publishing to both reaches essentially everything.

Flow already half-anticipates this: `statusSurfaceCandidates` defaults to `["CLAUDE.md", "AGENTS.md", "README.md", "GEMINI.md", ".cursorrules", ".github/copilot-instructions.md"]`. Flow *reads* multi-host projects today; it just doesn't *run* on them.

### 3.2 Commands are being absorbed into skills — everywhere

This is a strong, one-directional trend and it settles a design question for Flow:

- Claude Code: *"Custom commands have been merged into skills."*
- Cursor: ships a `/migrate-to-skills` built-in that converts commands → skills with `disable-model-invocation: true`, *"which preserves their explicit invocation behavior."* The `cursor.com/docs/commands` page now 404s and `docs/context/commands` renders the **Skills** page.
- Amp: **deleted** custom commands outright (2026-01-29), because they *"were two ways of doing the same thing."*
- Codex: custom prompts officially **deprecated** — *"Use skills for reusable instructions."*

Commands are also the least portable artifact: 9 tools, 9 mutually unintelligible argument syntaxes (`$ARGUMENTS` / `${input:name}` / `{{args}}` / `$1–$9` + named `KEY=value` / explicitly none). **Conclusion: Flow should express every user-facing entry point as a skill with `disable-model-invocation`, not as a command.** That is both the portable choice and where every vendor is heading.

### 3.3 The authoritative answer on what will never standardize

**This is the most decision-relevant find in the report.** The **Agent Plugins Specification v1.0.0 (Working Draft)** at [agent-plugins.org/specification](https://agent-plugins.org/specification) uses RFC 2119/8174 language, defines a `plugin.json` manifest, and defines exactly **two** portable component types — **Skills** and **MCP servers**. Verbatim:

> "Other proposed component types — such as **commands, hooks, agents, rules**, and LSP servers — remain **too client-specific for a stable portable contract** and are outside the v1 format until their formats converge."

Its TSC is *"core maintainers from Amazon, Cursor, Microsoft, OpenAI, and Vercel."* That is the clearest available signal that Flow's subagents, hooks, and slash commands will not be standardized on any timeline worth planning around.

**Implication for Flow, stated bluntly:** the portable artifact set is skills + MCP servers. Everything else in Flow — the `context: fork` audit forks, the hooks that would replace shell substitution, the `Skill()` composition graph — is permanently adapter territory. That's not a reason to abandon the port; it's the reason to put orchestration in a CLI and generate the rest (§6), rather than waiting for a standard that the people who would write it have said they won't.

*(Caveat: a separate site, open-plugins.com, describes a v1.0.0 that **includes** `commands/` and `hooks/`. The two contradict each other; agent-plugins.org has the named TSC, so I treat it as authoritative. Worth re-checking.)*

**Why the convergence that does exist happened:** vendors, not standards bodies. `.agents/skills/` shipped in a dozen products while its proposal sat unanswered 11 months. Cursor and Copilot implemented Claude Code's hook contract unilaterally. Commands converged **by being deleted** into skills. And the market's verdict on all of it is that six-plus maintained converters exist (`rulesync`, `ruler`, `mcpx-cli`, `dotagents`, `ai-rules-sync`, `universal-agents`) — tellingly, `rulesync` and `ruler` each **invented their own neutral directory** rather than adopting `.agents/`.

### 3.4 What is *not* standardized

| Layer | Portable? | Reality |
|---|---|---|
| Instruction file | ✅ Mature | AGENTS.md; near-universal ingestion |
| Skills (instruction half) | ✅ Mature | Real spec, ~45 adopters, `.agents/skills/` + `.claude/skills/` |
| Skills (script/executable half) | ❌ | Forbidden over MCP by spec; each host gates differently |
| Hooks | 🟡 De-facto | No spec, but Claude Code's names+location are read by Cursor, Copilot, Codex, Cline. **Fail-open/fail-closed semantics diverge dangerously** (§5.1) |
| Subagents | 🟡 Partial | No spec; disjoint field sets and two serialization formats. **But Cursor and Copilot both read `.claude/agents/`** |
| Slash commands | ❌ | Not portable. Write skills instead (§3.2) |
| Plugin bundles | ❌ Explicitly deferred | MCP WG ruled it out of scope |
| MCP config | 🟡 | Protocol standard; config file is not — 8 different top-level keys |

### 3.5 MCP is a distribution channel for doctrine, not a portability layer

MCP spec revision **`2026-07-28`** — published the day before this research. **It is a rewrite, not a bump:** sessions removed, the `initialize` handshake **gone** (MCP is now stateless, version in `_meta`), a new mandatory `server/discover` RPC, MRTR replacing server-initiated requests, SSE resumability and `ping` removed, OAuth DCR deprecated. A formal 12-month deprecation window now exists (SEP-2596).

- **Roots, Sampling, and Logging are DEPRECATED.** Elicitation is the only surviving undeprecated client feature. **Do not build on them.**
- **The MCP config file is not standardized** — 8 distinct filenames and 6 distinct top-level keys across 13 tools (`mcpServers` in 7, but also `servers`, `context_servers`, `amp.mcpServers`, `mcp`, `[mcp_servers.x]` TOML, `extensions:` YAML). [SEP-2633](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2633) proposes a standard `mcp.json` and records maintainer consensus from the March 2026 MCP Dev Summit — but it's an open draft with **no published schema yet**. Bet on the shape; don't bet on it having landed.
- **MCP prompts as slash commands do not work on Codex.** [openai/codex#8342](https://github.com/openai/codex/issues/8342) open since 2025-12-19, no assignee, no maintainer reply. Cursor's docs claim prompt support but never claim slash-invocability, with live bug reports. **MCP cannot be the delivery vehicle for `/flow:*`.**
- **[SEP-2640 Skills Extension](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2640)** (In Review) would serve skills as `skill://` resources — but its security model is explicit: *"Skills are data, not directives."* Hosts **MUST NOT** honor mechanisms in skill content causing local code execution without explicit opt-in; **scripts and hooks in skill frontmatter must be ignored or gated.** So MCP can carry Flow's doctrine and never its machinery.
- The [Skills Over MCP WG charter](https://modelcontextprotocol.io/community/working-groups/skills-over-mcp) puts **plugin/bundle packaging explicitly out of scope**.

### 3.6 Prior art — generation wins, abstraction doesn't

| Project | Stars | Approach |
|---|---|---|
| [github/spec-kit](https://github.com/github/spec-kit) | 124.5k | `specify init --integration <agent>` generates per-agent artifacts from a neutral source; **or** installs Agent Skills instead. **The template to copy.** |
| [dyoshikawa/rulesync](https://github.com/dyoshikawa/rulesync) | 1.3k | Codegen from `.rulesync/`, plus reverse `import` and tool→tool `convert`. **Widest scope: 9 categories** — rules, ignore, MCP, commands, subagents, skills, hooks, permissions, checks — across 40+ tools |
| [intellectronica/ruler](https://github.com/intellectronica/ruler) | 2.8k | Codegen, `ruler.toml`. Cleanest mental model; rules + MCP only |
| [ruvnet/ruflo](https://github.com/ruvnet/claude-flow) | 66.5k | Meta-harness. **The rename from `claude-flow` is the tell** |
| [Conductor](https://www.conductor.build/) | closed | Wraps host *processes* in worktrees. Nothing for config portability |
| [SuperClaude](https://github.com/SuperClaude-Org/SuperClaude_Framework) | 23.6k | **Claude-only.** Cautionary |

**Nobody has a portable subagent runtime. Nobody ports Claude Code *plugins* as bundles.** Every project that works either generates per-host artifacts from a neutral source, or wraps the host process. `vibe-rules` (530 stars) is **abandoned** — no commits since 2025-08-21. `aicm`/`ai-config-manager` is a 3-star backup tool; don't cite it.

[ACP](https://agentclientprotocol.com/) (Zed + JetBrains, 3.8k stars) standardizes the *editor↔agent session* interface and even advertises available slash commands — but explicitly does **not** cover agent configuration.

---

## 4. Per-host capability mapping

### 4.1 Codex CLI — near-isomorphic

At v0.146.0 (2026-07-29). Docs moved to `learn.chatgpt.com`; the in-repo `docs/*.md` are now one-line stubs, so **GitHub is no longer authoritative**.

| Flow mechanism | Codex equivalent | Fidelity |
|---|---|---|
| `SKILL.md` | **`.agents/skills/`** (cwd, parents, repo root), `~/.agents/skills`, `/etc/codex/skills` | **Same format** |
| `disable-model-invocation: true` | sidecar `agents/openai.yaml` → `policy.allow_implicit_invocation: false` | **Near-exact** |
| `context: fork` + `agent:` | `.codex/agents/*.toml` — `name`, `description`, `developer_instructions`, **plus any `config.toml` key** (`model`, `sandbox_mode`, per-agent MCP). Own context window; **cannot escalate** parent sandbox | **Good — arguably richer** |
| `Agent` spawn | `spawn_agent` / `wait_agent` / `send_message` / `list_agents` / `close_agent` ⚠️ *source-derived, not official docs* | Good |
| Hooks | `~/.codex/hooks.json` or `.codex/hooks.json`; **11 events** incl. `SessionStart`, `UserPromptSubmit`, `PreToolUse`, `SubagentStop`. Claude's PascalCase names verbatim, same stdin-JSON, same exit codes, same `additionalContext` | **~Superset for `command` type.** `prompt`/`agent` handler types are parsed and **silently skipped** |
| `.claude-plugin/plugin.json` | `.codex-plugin/plugin.json` — bundles skills + MCP + hooks + agents + prompts | **Near-isomorphic** |
| Session transcript | `~/.codex/sessions/YYYY/MM/DD/rollout-<ts>-<uuid>.jsonl`; hooks provide `transcript_path` | Adaptable — **schema undocumented** |
| `CLAUDE.md` | `AGENTS.md` chain (git root → cwd, **32 KiB cap**); `project_doc_fallback_filenames` can include `"CLAUDE.md"`; each level checks `AGENTS.override.md` first | Good |
| `/flow:x` commands | ⚠️ custom prompts **deprecated**, user-scope only, no project scope | **Use skills** |

Two Codex capabilities Flow could exploit: **`codex exec --output-schema <file>`** (constrained decoding — would harden Flow's model-authored JSON, §5.4) and Starlark `.rules` execution policy.

⚠️ **Verify before building:** multi-agent is mid-migration v1→v2 with conflicting flags and depth defaults; no official built-in tool-name reference exists (get names from a `PreToolUse` hook that logs `tool_name`); **`.codex/skills/` appears on no official OpenAI page** despite being widely cited — the official path is `.agents/skills`.

### 4.2 Cursor — high tier, not degraded (this was the biggest surprise)

Cursor 3.x (3.0 shipped 2026-04-02; 3.11 on 2026-07-10). Docs moved to `cursor.com/docs`.

| Flow mechanism | Cursor equivalent | Fidelity |
|---|---|---|
| `SKILL.md` | `.cursor/skills/`, `.agents/skills/`, **`.claude/skills/`**, `.codex/skills/` + user equivalents | **Same format** |
| `disable-model-invocation` | **same field name, same semantics** | **Exact** |
| Flow's `rules/*.md` `paths:` frontmatter | Cursor skills support a **`paths:`** glob field | **Exact** — Flow's rules can become skills |
| `context: fork` + `agent:` | `.cursor/agents/*.md`, **`.claude/agents/`**, `.codex/agents/` — `name`, `description`, `model`, `readonly`, `is_background`. Own context, no conversation history, resumable by ID. **Nesting allowed but depth-limited** | **Good** |
| `subagent_type: Explore` | Built-in **Explore** subagent (parallel codebase search), plus Bash and Browser | **Exact analogue** |
| Hooks | `.cursor/hooks.json` — **21 events**, the richest surveyed. Plus **native reading of `.claude/settings.json` hooks** with published event mapping and `CLAUDE_PROJECT_DIR` alias | **Good — but see §5.1** |
| Packaging | `.cursor-plugin/plugin.json` — bundles rules, skills, agents, commands, MCP, hooks. Marketplace + private team marketplaces | **Near-isomorphic** |
| Session transcript | JSONL at `~/.cursor/projects/<slug>/agent-transcripts/`; hooks provide `transcript_path` + `CURSOR_TRANSCRIPT_PATH` | Adaptable |
| `CLAUDE.md` | Cursor **CLI** explicitly reads `AGENTS.md` *and* `CLAUDE.md` as rules; IDE-side docs name only AGENTS.md ⚠️ unconfirmed for the editor | Good on CLI |
| Rules `paths:` | `.cursor/rules/*.mdc` — `description` / `globs` / `alwaysApply`. ⚠️ **plain `.md` in that dir is silently ignored** | Lossy — prefer skills |

Cursor also has a `@cursor/sdk` that honors `.cursor/mcp.json`, `.cursor/agents/*.md`, and `.cursor/hooks.json`, and a CLI (`agent`) with `-p/--print`, `--output-format json`, `--resume`, `--worktree`. **Cloud agents run command-based hooks but not prompt-based ones**, and skip `sessionStart`/`sessionEnd`.

`.cursorrules` is **removed from the docs entirely** — legacy, undocumented, don't design around it.

### 4.3 GitHub Copilot — also high tier

Copilot converged on the open/Anthropic shapes more aggressively than anyone: reads `AGENTS.md`, `CLAUDE.md`, `SKILL.md`, `.claude/skills/`, `.claude/agents/`, `.claude/rules/`, and `.claude/settings.json` hooks. Subagents are `.agent.md` with the richest schema surveyed (including `handoffs`, which has no Claude Code counterpart) and a `runSubagent` tool. Hooks accept Claude PascalCase aliases across 14 events with `command` / `http` / `prompt` types.

Two cautions: instruction-file precedence is **explicitly undefined** (*"does not define a general precedence order"* — files combine, not override), and MCP config has **three incompatible shapes** with different top-level keys (`servers` vs `mcpServers` vs UI-only).

### 4.4 Everything else

- **Gemini CLI** — `GEMINI.md` (AGENTS.md is **opt-in only**; the default-support request was closed *"not planned"*), TOML commands with `!{shell}` injection, subagents in `.gemini/agents/`, 11 hook events with **divergent names** (`BeforeTool`, not `PreToolUse`), skills at `.agents/skills/`. Extensions are the packaging layer.
- **OpenCode** — the one host besides Claude Code with **`` !`shell` `` substitution in commands**, plus `$ARGUMENTS`/`$1..$n`/`@file`. Reads `.claude/skills/`. Strongest OSS hook story (JS plugins, ~30 events, blocks by throwing).
- **Amp** — AGENTS.md native, reads `.claude/skills/`. Custom agents are **TypeScript**, not markdown. `tool.call` can `allow`/`reject`/`modify`/`synthesize` — the most expressive blocking contract surveyed.
- **Zed** — skills at `.agents/skills/` **only** (not `.claude/`), definition-less subagents via `spawn_agent`, **no agent hooks** at all, no custom commands.
- **Cline** — `.clinerules/`, reads `.claude/skills/`, 6 hook events, definition-less subagents (experimental), macOS/Linux only.
- **Aider — do not target.** Last tagged release **v0.86.0, 2025-08-09** (~12 months). No skills, no MCP (PRs closed unmerged), no AGENTS.md auto-load, no custom commands, no blocking hooks. Maintenance-mode.
- **Roo Code — dead.** Archived 2026-05-15. Note that both agents.md and agentskills.io **still list it** — those listings are stale, which is a good reminder to cross-check every adoption claim against vendor docs.
- **Windsurf → Devin Desktop** (Cognition); `docs.windsurf.com` redirects to `docs.devin.ai`. Infers rule activation mode from AGENTS.md file *location*.

---

## 5. The things that genuinely don't port

### 5.1 Hook-based gates are FAIL-OPEN by default on two of three hosts

**This is the most important finding in the whole report, and it is squarely an FB-0074-class hazard.**

The portable replacement for Flow's 51 `` !`shell` `` substitution sites is hooks: `UserPromptSubmit` / `SessionStart` returning `additionalContext` injects preprocessed context deterministically, host-provided, and cannot be skipped by a non-compliant model. That mechanism exists on Claude Code, Codex, Cursor, and Copilot. It is a genuine upgrade over shell substitution — more portable *and* more robust.

But the failure semantics diverge in exactly the direction that matters:

| Host | Blocking contract |
|---|---|
| Claude Code | exit 2 blocks |
| Codex | exit 2 blocks (Claude-compatible) |
| **Cursor** | exit 2 = deny, but **other non-zero codes are fail-open by default** — a gate needs explicit `failClosed: true` |
| **Copilot** | *"Timeouts are fail-open for every event, including `preToolUse`"* — **a hung gate silently permits** |

So a Flow hook that crashes, times out, or exits 1 on Cursor or Copilot **permits the action and looks identical to a pass**. That is precisely the class v1.27.0 spent three fixes on: *a gate that reports success without doing its job.* Any adapter emitting hooks **must** set `failClosed: true` on Cursor, and must treat Copilot hooks as advisory rather than mechanical, and `/flow:doctor` must say so.

### 5.2 Flow doesn't own its behavioral gate

`verify-build` is a **wrapper**. `SKILL.md:41-66` is a formal "Bundled-skill integration contract": launch recipe from `/run-skill-generator`, dispatch from `/run`, run-and-observe from `/verify`; Flow supplies only the plan-driven gate. `/simplify` is a required pipeline step with a mechanical marker, referenced 25× in `workflow.md` and enforced by `audit-skips`.

On any other host **there is no engine behind Flow's strongest gate.** Options:

1. **Implement a Flow-owned verify engine.** Large — a screenshot/drive/observe harness per platform. This is the actual reason Flow is Claude-Code-shaped.
2. **Degrade the gate and say so.** Cheaper, honest, and **already precedented in Flow's own code**: `ship/SKILL.md:20-22` refuses to auto-invoke when verify-build skips and demands an explicit human "ship it". A host without a verify engine is the same condition as `platform: library`. Reuse the existing path.
3. Pretend. Not an option — §7.

`/simplify` is easier: it's a quality pass Flow could own as a fifth lens agent.

### 5.3 Fresh-context audit forks — better than expected

Five skills have **no body logic**; `context: fork` + `agent: auditor` *is* the implementation, and their whole epistemic value is that the auditor never saw the reasoning it audits.

This ports better than anticipated: **Cursor and Copilot both read `.claude/agents/` directly**, Codex has richer TOML agent files, and `codex exec` / `agent -p` / `copilot --agent` are viable fresh-process fallbacks anywhere (with `--output-schema` on Codex for the contract). Zed and Cline have subagents but **no definition files** — there, the reviewer prompt has nowhere to live and "skeptical fresh-context review" silently becomes "same context, asked nicely," which looks identical in the output.

### 5.4 Strict-schema instruction-following

Flow's determinism rests on subagents emitting exact schemas that **deterministic Python then parses**: `render-test-plan.py` (561 L), `render-report.py` (532 L), `skip-audit-checks.py` (502 L) all consume model-authored JSON per `findings-schema.json`. Rubrics require case-sensitive `PASS`/`FAIL`/`Unknown`; `lens-push-further` requires a verbatim sentence.

No tool enforces any of this — the model complies. Flow has never had to think about it because it only ran on Claude. Mitigations: constrained decoding where offered (`codex exec --output-schema`), and making every renderer **fail loud on schema mismatch rather than degrade**. Worth auditing regardless of any port.

---

## 6. Recommended architecture

Two moves, and the first is far cheaper than the framing "port Flow to other services" suggests.

### Move 1 — publish to the neutral directories (small, high leverage)

Because `.claude/` and `.agents/` are already read cross-vendor, a large fraction of Flow's doctrine reaches Cursor, Copilot, Codex, Amp, OpenCode, and Zed with **no translation at all** — just placement.

- ~~**Skills → dual-publish** to `.agents/skills/` and `.claude/skills/`.~~ **SUPERSEDED — see `dev-docs/handoffs/service-agnostic-roadmap-2026-07.md` §5.** Dual-publishing the same skill into two directories of one project produces **duplicate entries**, because Cursor reads both `.claude/skills/` and `.agents/skills/`, Codex reads `.agents/`, and **neither does name-based dedupe**. Codex docs, verbatim: *"If two skills share the same `name`, Codex doesn't merge them; both can appear in skill selectors."* The correct answer is **per-host plugin packaging** (`.claude-plugin/` + `.codex-plugin/` + `.cursor-plugin/` manifests in one repo over one shared `skills/` tree), which sidesteps discovery-directory collisions entirely. For loose user-scope installs, target `~/.agents/skills/` only — and never `~/.codex/skills/`, which is a deprecated root that also hosts the `.system` cache Codex rewrites on upgrade.
- **Agents → keep `.claude/agents/`** — Cursor and Copilot read it natively. This is the cheapest win in the whole report: Flow's 9 reviewer prompts reach three hosts unchanged.
- **Hooks → generate per host.** The `.claude/settings.json` shim on Cursor/Copilot is real but **not contract-compatible** (§3.1) — different casing, different stdin schema, no `cwd` on Cursor. Set `failClosed: true` on Cursor (§5.1).
- **Instructions → `AGENTS.md` as source of truth, bridged to `CLAUDE.md`** via `@AGENTS.md` import or `ln -s` — Claude Code does not read AGENTS.md natively. Watch the 32 KiB Codex cap.
- **Entry points → skills with `disable-model-invocation`**, never commands (§3.2). Note Claude Code's own docs: *"Custom commands have been merged into skills"*, and a skill wins on clash.
- **Keep only the two portable frontmatter fields neutral** — `name` and `description` are all the spec requires and all that's universal. Everything else (`allowed-tools`, `context: fork`, `agent:`, `paths:`) is per-adapter.

### Move 2 — orchestration into a CLI, then generate per host

Do **not** build a runtime abstraction layer. Every project that tried is dead or Claude-only; the two that work (spec-kit at 124k stars, rulesync across 40+ tools) both **generate per-host artifacts from a neutral source**.

```
flow-core/                      # the asset — host-agnostic
  doctrine/                     # was agents/, docs/, rules/, rubrics — pure markdown
  lib/                          # was scripts/ + skills/*/lib/ — unchanged, stdlib Python
  tools/flow                    # NEW: the CLI. NOT bin/ — that PATH-injects on Claude Code
  flow.config.schema.json       # + host slot, + capability tier
adapters/
  claude-code/                  # .claude-plugin/, context:fork skills, hooks
  codex/                        # .codex-plugin/, .agents/skills/, .codex/agents/*.toml, hooks.json
  cursor/                       # .cursor-plugin/, skills w/ paths:, .cursor/hooks.json (failClosed)
  generic/                      # AGENTS.md + .agents/skills/ — degraded, works everywhere
```

**The idea that makes this work: the CLI emits instructions as data.**

Today orchestration lives *inside prompt markdown* — 51 substitution sites, 21 `Skill()` calls, 7 `subagent_type` spawns. That's what makes it unportable. If `flow gate ship --step 2` instead returns a JSON plan of what must happen next (including "spawn a fresh-context reviewer with this prompt and this schema"), then:

- Per-host surface collapses from **79 embedded orchestration sites** to one CLI plus thin generated wrappers.
- Each adapter translates one vocabulary: *spawn a fork* → `Agent(subagent_type:…)` / `spawn_agent` / `runSubagent` / `codex exec`.
- The 23 eval harnesses keep working — they test the CLI, which is where the logic now lives.
- **It is testable inside Claude Code before betting on a second host.**

### How the three things the question asked about survive

| Asset | Preservation mechanism |
|---|---|
| **Context** (the docs) | Already portable — `core-docs/*.md` are plain markdown, paths already come from `flow.config.json`. Make `AGENTS.md` the source of truth. Watch the **32 KiB Codex cap** (§10.6). |
| **Skills** (the doctrine) | Already portable, and partly *unchanged* — `SKILL.md` is a published spec; `.agents/skills/` + `.claude/skills/` reach ~everything. Host-specific fields move to the adapter's generator. |
| **Workflows** (the loop) | Does **not** survive as markdown. It survives by moving into `tools/flow` as instructions-as-data, with per-host spawn/hook translation in the adapters. |

---

## 7. Capability tiers — the constraint that keeps this honest

Flow's core thesis is *mechanical gates between intent and ship*. A Flow whose gates are advisory but which prints the same output would be worse than no Flow — it would launder unverified work through a trusted-looking pipeline. FB-0074 at product scale.

So each adapter declares a tier, and `/flow:doctor` must print **which gates are mechanical and which are advisory on this host**:

| Tier | Hosts | Mechanical | Advisory |
|---|---|---|---|
| **Full** | Claude Code | all gates | — |
| **High** | Codex | plan/merge gates, fresh-context audits, hook-injected context, skip audit | behavioral verify — ⚠️ *revised: buildable on Playwright MCP, see roadmap §1.1* |
| **High−** | Cursor | plan/merge gates, fresh-context audits — **only with `failClosed: true`**; hook stdin does NOT carry `tool_input` (resolved: see roadmap §5.3) | per-turn context injection (impossible). ⚠️ *revised: Cursor has the BEST web verification of the three — bundled Browser, roadmap §1.1* |
| **Medium** | Copilot | plan/merge gates, fresh-context audits | **hooks (fail-open on timeout)**, verify |
| **Degraded** | Zed, Cline, Gemini | plan/merge gates (prose) | audits (no agent definition files), context, verify |
| **Doctrine-only** | generic AGENTS.md hosts | — | everything |

Enforcement should reuse machinery Flow already has: `verifyEnabled: false` + `platform: library|none` already causes `ship` to refuse auto-invocation and demand an explicit human "ship it" (`ship/SKILL.md:20-22`). A host without a verify engine is the same condition. `reviewLenses: []` already degrades staff-review cleanly.

**Corollary:** never let an advisory gate render byte-identically to a mechanical one. That is exactly the bug v1.27.0 fixed three instances of.

---

## 8. Staged plan, with a real decision gate

### Stage 0 — do regardless of any port (cheap, independently valuable)

1. `AGENTS.md` as source of truth; generate/symlink `CLAUDE.md`.
2. Env override for the hardcoded `~/.claude` disagreements path (`log_disagreement.py:32-35`), de-duplicating the copy in `contribute/SKILL.md:38`. *Chip queued.*
3. `host` slot + capability tier in the schema (slot 33 — note `changelogPath` is already read-but-undeclared per roadmap § Exploration, so fix both and re-derive the "32 slots" fan-out count).
4. Split `extract_session.py` at its existing seam: discovery+parse (`:74-208`) behind an adapter interface; keep `:222-673` + `bounding_logic.py` neutral. **~70% becomes reusable.** Add an eval for the false-`UNREAD` failure mode specifically.
5. Audit the three renderers for fail-loud-on-schema-mismatch (§5.4).
6. ~~Dual-publish skills.~~ **SUPERSEDED** — causes duplicate skill entries; use per-host plugin manifests instead (see the roadmap doc §5).
7. **Verify the Cursor hook stdin schema** (§10.3) before assuming any hook portability. **RESOLVED against official docs, and the answer is no:** `tool_input.file_path` is undocumented and the evidence says absent (Cursor's file tools use `path`/`fileText`), `Edit` collapses into `Write`, `Glob`/`WebFetch`/`WebSearch` have no equivalent, and `tool_input` flips between object and JSON-string across events. A shared `.claude/settings.json` hooks file cannot carry Flow's gates on Cursor — generate native `.cursor/hooks.json`.

**Also superseded by the roadmap doc:** the §5.1 recommendation to move the 51 substitution sites onto `UserPromptSubmit` hooks. That works on Claude Code and Codex but **not on Cursor**, where `beforeSubmitPrompt` has no context-injection field at all. The portable replacement is the **stamped-context invariant** (roadmap §4) — make a verdict impossible without fresh stamped evidence, so injection becomes a per-host optimization rather than the guarantee.

### Stage 1 — the load-bearing refactor (Claude Code only)

Build `tools/flow` wrapping the existing `lib/*.py`. ⚠️ **The hook-injection half of this is superseded** — `UserPromptSubmit` cannot inject context on Cursor. Use the **stamped-context invariant** instead (roadmap §4/§8): make a verdict impossible without fresh stamped evidence, so injection is a per-host optimization rather than the guarantee.

**This is where the value is, and it's verifiable without a second host.** If Stage 1 doesn't hold up under Flow's own evals and dogfood, stop — the port was never the problem.

### ◆ Decision gate

Only proceed if Stage 1 landed clean **and** there's a real second-host user. Do not port speculatively.

### Stage 2 — Codex or Cursor adapter

Both are now viable seconds. **Codex** if you want the richer subagent/hook fidelity and constrained decoding; **Cursor** if you want the cheapest path, since it reads `.claude/skills/`, `.claude/agents/`, and `.claude/settings.json` natively — much of Flow would work before an adapter exists. Accept verify-build degradation, declared per §7. Set `failClosed: true` on Cursor.

### Stage 3 — Copilot / generic

Copilot is close behind. Zed, Cline, Gemini get the degraded tier. **Skip Aider and Roo Code entirely** (stalled / archived).

---

## 9. What I would not do

- **Don't ship slash commands over MCP prompts.** Dead on Codex ([#8342](https://github.com/openai/codex/issues/8342), 7 months, no maintainer reply).
- **Don't ship `/flow:*` as commands at all.** Every vendor is absorbing commands into skills (§3.2), and command argument syntax is the least portable thing in the ecosystem.
- **Don't build on MCP sampling or roots.** Deprecated 2026-07-28.
- **Don't expect MCP to carry the Python engines.** SEP-2640 forbids it by design.
- **Don't write a runtime abstraction layer.** Generate artifacts.
- **Don't port `doctor` Sections 1 and 3** (~140 L of Claude Code install introspection) or `skill-composition-lint.py` (205 L, lints a Claude-Code-only frontmatter rule). Rewrite per adapter; ~zero salvage.
- **Don't trust adoption lists.** agents.md and agentskills.io both still list **archived Roo Code**; agents.md lists **Aider**, whose docs show no AGENTS.md ingestion, and **Gemini CLI**, where it's opt-in only. Cross-check every claim against vendor docs. Don't use `vercel-labs/skills` as a support matrix — it doesn't distinguish native from shimmed and contradicts vendor docs.
- **Don't rely on Codex's `/import`.** It's mechanical — Claude Code tool names survive verbatim.
- **Don't do this before the queue is drained.** 9 queued lesson-contributions and § Exploration entries (fork-handoff transport, `/tmp` collisions, `${CLAUDE_PLUGIN_ROOT}` resolution lint) all touch the exact seams a port would move. Landing those first makes the port smaller.

---

## 10. Open questions — verify empirically before building

1. Does Claude Code enforce `allowed-tools` for the `Skill` tool? Decides the severity of the `ship-spike:176` / `:12` mismatch. *(Chip queued.)*
2. Does the Cursor **editor** (not just the CLI) read `CLAUDE.md`? Docs conflict; third-party guides say no.
3. **Does Cursor's `.claude/settings.json` hook shim populate `tool_input.file_path` / `tool_input.command`?** Cursor's native stdin schema has **no `cwd` and no `session_id`**, and Flow's `default-hooks.json` reads `.tool_input.*` in both hooks. If the shim doesn't fill those, Flow's hooks are no-ops on Cursor — and because Cursor is **fail-open on non-2 exit codes**, a no-op hook looks exactly like a pass. **Highest-priority empirical check in this report.**
4. Do Cursor/Copilot's reads of `.claude/skills/` and `.claude/agents/` handle Flow's *non-standard* frontmatter (`context: fork`, `agent:`) gracefully, or does an unknown key break the parse? Claude Code itself treats all skill fields as optional and adds ~15 non-spec ones, so tolerance is likely but unproven. **Determines whether Move 1 is nearly free or needs a generator.**
5. Codex multi-agent v1 vs v2 flags and depth defaults — conflicting across all sources. Weakest area of the research.
6. Does `AGENTS.md`'s 32 KiB Codex cap fit Flow's doctrine? Flow's marketplace description alone is 17 KB. Silent truncation is the most-reported AGENTS.md production problem.
7. Codex built-in tool names — no official reference. Get them from a `PreToolUse` hook logging `tool_name`.
8. Codex rollout JSONL record schema — undocumented. Budget for size: [#24948](https://github.com/openai/codex/issues/24948) documents a 732 MB session file.
9. Cursor command argument interpolation — **no syntax documented anywhere**, including in Cursor's own shipped skills. Absent, or undocumented?
10. Which `plugin.json` does Agent Plugins v1 actually specify — agent-plugins.org (Skills + MCP only) or open-plugins.com (also commands + hooks)? The two contradict; this decides whether a portable bundle format is worth targeting at all.

---

## 11. One risk not in the brief: skill-distribution security

If a portable Flow ever ships through a skills registry rather than a git checkout, note that the Agent Skills spec has **no signing, no provenance, and no permission model** — `allowed-tools` is experimental and advisory. Snyk's "ToxicSkills" audit (2026-02-05) scanned 3,984 published skills: **36% had at least one security flaw, 13.4% critical, 76 confirmed malicious, and 91% of those used prompt injection.**

Flow is unusually exposed here because its skills legitimately execute bundled Python and shell. That's exactly the shape a consumer can't distinguish from a malicious one, and it's why SEP-2640 forbids executable skill content over MCP (§3.5). Keep distribution via a git checkout the consumer inspects, and keep the `sanitize_tokens.py` fail-closed scrub in the contribution path. Don't publish Flow to a public skills registry without a provenance story.

---

## Sources

**Standards:** [agentskills.io](https://agentskills.io/) · [Agent Skills specification](https://agentskills.io/specification) · [client-implementation guide](https://agentskills.io/client-implementation/adding-skills-support) · [agentskills/agentskills](https://github.com/agentskills/agentskills) · **[Agent Plugins Specification v1.0.0](https://agent-plugins.org/specification)** · [agent-plugins.org](https://agent-plugins.org) · [agents.md](https://agents.md/) · [agentsmd/agents.md](https://github.com/agentsmd/agents.md) · [#211 define a spec](https://github.com/agentsmd/agents.md/issues/211) · [#38 shared commands API](https://github.com/agentsmd/agents.md/issues/38) · [AAIF formation](https://www.linuxfoundation.org/press/linux-foundation-announces-the-formation-of-the-agentic-ai-foundation) · [aaif.io/projects](https://aaif.io/projects/) · [MCP spec 2026-07-28](https://modelcontextprotocol.io/specification/2026-07-28/) · [MCP versioning](https://modelcontextprotocol.io/specification/versioning) · [MCP 2026-07-28 changelog](https://modelcontextprotocol.io/specification/2026-07-28/changelog) · [SEP-2633 mcp.json](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2633) · [Skills Over MCP WG](https://modelcontextprotocol.io/community/working-groups/skills-over-mcp) · [SEP-2640](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2640) · [ACP](https://agentclientprotocol.com/) · [Snyk ToxicSkills](https://snyk.io/blog/toxicskills-malicious-ai-agent-skills-clawhub/)

**Claude Code (for the contradicted claims):** [memory / AGENTS.md](https://code.claude.com/docs/en/memory) · [skills](https://code.claude.com/docs/en/skills) · [hooks](https://code.claude.com/docs/en/hooks) · [#6235 AGENTS.md support](https://github.com/anthropics/claude-code/issues/6235) · [#16345 .agents/skills](https://github.com/anthropics/claude-code/issues/16345)

**Codex:** [AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md) · [Subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents) · [Build skills](https://learn.chatgpt.com/docs/build-skills) · [Build plugins](https://learn.chatgpt.com/docs/build-plugins) · [Hooks](https://learn.chatgpt.com/docs/hooks) · [Custom prompts (deprecated)](https://learn.chatgpt.com/docs/custom-prompts) · [Config reference](https://learn.chatgpt.com/docs/config-file/config-reference) · [Non-interactive mode](https://learn.chatgpt.com/docs/non-interactive-mode) · [codex_mcp_interface.md](https://github.com/openai/codex/blob/main/codex-rs/docs/codex_mcp_interface.md) · [DeepWiki hooks](https://deepwiki.com/openai/codex/3.11-hooks-system) · [#8342](https://github.com/openai/codex/issues/8342) · [#24948](https://github.com/openai/codex/issues/24948)

**Cursor:** [rules](https://cursor.com/docs/rules) · [skills](https://cursor.com/docs/skills) · [subagents](https://cursor.com/docs/subagents.md) · [hooks](https://cursor.com/docs/hooks.md) · [third-party hooks](https://cursor.com/docs/reference/third-party-hooks) · [plugins](https://cursor.com/docs/plugins.md) · [mcp](https://cursor.com/docs/mcp.md) · [CLI](https://cursor.com/docs/cli/using) · [changelog 1.6](https://cursor.com/changelog/1-6) · [changelog 2.5](https://cursor.com/changelog/2-5)

**Copilot:** [hooks-reference](https://docs.github.com/en/copilot/reference/hooks-reference) · [subagents](https://code.visualstudio.com/docs/copilot/agents/subagents) · [about-agent-skills](https://docs.github.com/en/copilot/concepts/agents/about-agent-skills) · [custom-instructions-support](https://docs.github.com/en/copilot/reference/custom-instructions-support) · [prompt-files](https://code.visualstudio.com/docs/agent-customization/prompt-files) · [AGENTS.md in code review](https://github.blog/changelog/2026-06-18-copilot-code-review-agents-md-support-and-ui-improvements/)

**Others:** [Gemini CLI](https://geminicli.com/docs/cli/gemini-md/) · [OpenCode](https://opencode.ai/docs/rules/) · [Cline](https://docs.cline.bot/customization/cline-rules) · [Zed](https://zed.dev/docs/ai/instructions) · [Amp](https://ampcode.com/manual) · [Amp: slashing custom commands](https://ampcode.com/news/slashing-custom-commands) · [Aider conventions](https://aider.chat/docs/usage/conventions.html) · [Devin/Windsurf AGENTS.md](https://docs.devin.ai/desktop/cascade/agents-md) · [Junie skills](https://junie.jetbrains.com/docs/agent-skills.html) · [Claude Code hooks](https://code.claude.com/docs/en/hooks) · [Claude Code MCP](https://code.claude.com/docs/en/mcp)

**Prior art:** [spec-kit](https://github.com/github/spec-kit) · [rulesync](https://github.com/dyoshikawa/rulesync) · [ruler](https://github.com/intellectronica/ruler) · [ruflo](https://github.com/ruvnet/claude-flow) · [skillport](https://github.com/gotalab/skillport) · [Conductor](https://www.conductor.build/)
