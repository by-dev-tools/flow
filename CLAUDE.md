# CLAUDE.md -- Flow

## What This Is

A Claude Code plugin distributing the **managed-autonomy workflow**: an 11-step loop with two load-bearing human gates (plan approval, merge), a third automatic gate on LOW-confidence assumptions, and a feedback pipeline that compounds quality across sessions. Bundled into the same plugin are the skeptical reviewers (`auditor`, `plan-critic`) that audit sessions for unverified claims and critique plans for scope/spec/coherence misalignment — they're used together with the workflow skills 100% of the time, so separation only adds install friction.

**Core thesis:** the most expensive errors in a session compound when (a) plans aren't critiqued before approval, (b) claims aren't audited before trust, and (c) the loop has no mechanical gates between intent and ship. Flow's contribution is a packaged loop + a passive skeptical layer, both project-agnostic, that any repo can adopt in ~10 minutes once PR 3 ships the template directory.

**Lineage:** this repo was previously published as `byamron/llm-auditor` (marketplace) hosting the `assumption-auditor` plugin. Renamed in place to `by-dev-tools/flow` on 2026-05-23; restructured into the Anthropic marketplace + plugin shape in v1.0.0 (PR 1 of the flow extraction umbrella). Pre-v1.0.0 content is recoverable via `git checkout pre-flow-plugin`.

## Repository Layout -- Read This First

This repo contains **three distinct surfaces**. Don't confuse them.

### 1. Marketplace + plugin artifacts (what ships to users)

These files are published when the plugin is installed.

| Path | Purpose |
|------|---------|
| `.claude-plugin/marketplace.json` | Marketplace declaration (one plugin: `flow`) |
| `plugins/flow/.claude-plugin/plugin.json` | Plugin manifest |
| `plugins/flow/agents/auditor.md` | Auditor subagent system prompt |
| `plugins/flow/agents/plan-critic.md` | Plan-critic subagent system prompt |
| `plugins/flow/skills/audit-plan/SKILL.md` | `/flow:audit-plan` slash command |
| `plugins/flow/skills/audit-completion/SKILL.md` | `/flow:audit-completion` slash command |
| `plugins/flow/skills/critique-plan/SKILL.md` | `/flow:critique-plan` slash command |
| `plugins/flow/skills/log-disagreement/SKILL.md` | Auto-invoked disagreement-capture skill |
| `plugins/flow/skills/ship/SKILL.md` | `/flow:ship` final-pass pipeline (PR-2-placeholdered for security + a11y + memory) |
| `plugins/flow/scripts/extract_session.py` | Session preprocessing for the reviewers |
| `plugins/flow/scripts/bounding_logic.py` | User-message windowing |
| `plugins/flow/scripts/log_disagreement.py` | Writes pushback records to user-scope storage |
| `plugins/flow/docs/workflow.md` | Canonical 11-step loop reference (long-form) |
| `plugins/flow/evals/` | Regression fixtures + harness for the reviewers |
| `plugins/flow/DISAGREE.md` | Free-form feedback log for the reviewer side |
| `README.md` | User-facing marketplace + install + use docs |
| `LICENSE` | MIT |

### 2. Plugin's own dev-tracking (not shipped)

Flow tracks its own development in `dev-docs/` (NOT `core-docs/` — that name is reserved for consumer-project scaffolding the template directory ships in PR 3).

| Path | Purpose |
|------|---------|
| `dev-docs/plan.md` | Current focus + active work items + handoff notes |
| `dev-docs/history.md` | Per-PR decision log: what + why + tradeoffs + SHA |
| `dev-docs/feedback.md` | Synthesized user corrections (FB-XXXX) |
| `dev-docs/spec.md` | Plugin scope + features + categories (legacy: audit-only scope; broadening to full flow identity is a queued hygiene PR) |
| `dev-docs/workflow.md` | Flow-internal dev workflow (different from the consumer-facing `plugins/flow/docs/workflow.md`) |

### 3. Project-dev infrastructure (how we build the plugin; also not shipped)

These files help Claude sessions develop and maintain this repo. Not part of the plugin.

| Path | Purpose |
|------|---------|
| `CLAUDE.md` | This file -- always loaded |
| `.claude/agents/` | Project-dev agents (planner, domain, testing, docs) for building flow |
| `.claude/skills/` | Project-dev workflows (`/ship`, `/preship`) for shipping flow PRs |
| `.claude/rules/` | Auto-loading scoped rules (safety, general, documentation) |
| `.claude/settings.json` | Hooks (secret blocking) |
| `.context/` | Per-session scratch |

When you see `agents/` and `skills/` under `plugins/flow/`, those are **plugin artifacts** (what consumers get when they install flow). When you see `.claude/agents/` and `.claude/skills/`, those are **project-dev** roles for building flow itself. The two never mix. Same for `dev-docs/` (plugin's own self-tracking) vs the future `template/core-docs/` (PR 3 — the scaffolding consumer projects copy when adopting flow).

## Tech Stack

- **Platform:** Claude Code plugin marketplace (one plugin per repo today: `flow`)
- **Language:** Python 3.7+ (stdlib only, no external deps) for preprocessing; Markdown for prompts, skills, and the workflow doc
- **AI:** delegates to Claude Code subagents defined in `plugins/flow/agents/*.md`; no direct API calls
- **Persistence:** none in the plugin runtime; reviewer pushback writes to `~/.claude/plugins/data/flow/disagreements/`; consumer-side memory entries (PR 2) live at `~/.claude/projects/<canonical>/memory/`

## Product Principles

- **Passive over active.** The auditor and plan-critic read; they do not re-run tools. Verification is the user's call.
- **Evidence or silence.** If a claim can't be challenged with specific evidence from the session, don't flag it. "No issues flagged" / "APPROVED" is a valid output.
- **Fixed output format.** Every reviewer pass returns the same structured shape so users and regression tests can parse it reliably.
- **Narrow scope beats wide scope.** Four auditor categories + three plan-critic categories — not more.
- **The loop is the product.** Bundling workflow skills (`/flow:ship` and the rest landing in PR 2) with the reviewers means the loop ships once and the human gate stays where it should — at plan approval and merge.
- **Project-agnostic by default.** Every doc path, command, and default branch comes from `flow.config.json` slots with documented defaults. Never silently no-op on a missing slot: print a loud `⚠️` warning so consumers know.
- **Feedback loop is load-bearing.** `DISAGREE.md` + auto-captured disagreements under `~/.claude/plugins/data/flow/disagreements/` are the source of prompt-tuning work and new eval cases.

## Core Documents (dev-side)

All living project knowledge lives in `dev-docs/`. Read before acting; update before shipping.

| Document | Path | Purpose |
|----------|------|---------|
| Plan | `dev-docs/plan.md` | Current focus, active work items, handoff notes |
| History | `dev-docs/history.md` | Per-PR decision log |
| Feedback | `dev-docs/feedback.md` | Synthesized user corrections (FB-XXXX) |
| Spec | `dev-docs/spec.md` | Plugin scope (audit-side today; broadening queued) |
| Workflow | `dev-docs/workflow.md` | Flow-internal dev workflow |

The **consumer-facing** workflow doc — the one that ships with the plugin — is `plugins/flow/docs/workflow.md`. Don't conflate them.

## Agent Workflow (dev-side)

Project-dev agents live in `.claude/agents/`. Invoke via `claude --agent <name>` or by name in conversation. Use `/clear` between phases.

| Agent | Role | When to use |
|-------|------|-------------|
| `planner` | Scope features, write goals, update plan.md | Starting or refining work |
| `domain` | Python scripts, prompt changes, eval logic | Any code or prompt change |
| `testing` | Evals, fixtures, regression cases | After domain changes |
| `docs` | history.md, plan.md, commit | Shipping completed work |

Dev-side slash commands: `/ship` (project-dev push + PR), `/preship` (standards review before shipping flow itself). Don't confuse these with the plugin's own `/flow:ship`, `/flow:audit-plan`, etc. — those are user-facing commands published by this plugin.

## How to Work

1. **Read before writing.** Check `dev-docs/plan.md` for current focus and `dev-docs/feedback.md` for past corrections.
2. **Respect the three-surface boundary.** Changes to plugin artifacts (`plugins/flow/*`, `.claude-plugin/marketplace.json`, `README.md`) change user-visible behavior. Changes under `dev-docs/` are dev-tracking only. Changes under `.claude/` are project-dev infra. Never mix.
3. **Prompt changes are code changes.** The reviewer prompts at `plugins/flow/agents/{auditor,plan-critic}.md` and the new `plugins/flow/skills/ship/SKILL.md` are deployed surface. Treat edits like edits to a deployed service: write an eval fixture first (where applicable), update `dev-docs/history.md`, tune deliberately.
4. **Follow the rules.** `.claude/rules/` auto-loads safety and documentation discipline when you touch matching files.
5. **Never wrap a bundled Claude Code skill.** `/simplify`, `/batch`, `/debug`, `/loop`, `/claude-api` are native. If a future flow skill would parrot one, drop it and reference the native one instead.

## Quality Bar

Code and prompts don't ship unless they meet these standards simultaneously:

- **Correct:** auditor outputs match the `ISSUE` / `AUDIT SUMMARY` / `No issues flagged.` schema in `plugins/flow/agents/auditor.md`; plan-critic outputs match the `CRITIQUE SUMMARY` / `APPROVED` schema in `plan-critic.md`. Evals pass.
- **Evidence-backed:** no new category, rule, or heuristic without a fixture in `plugins/flow/evals/fixtures/` demonstrating it.
- **Graceful on malformed input:** every preprocessing path handles missing session files, empty transcripts, and malformed JSONL without crashing. Skills that read `flow.config.json` degrade to documented defaults or print a loud warning — never silently no-op.
- **Lean:** Python stdlib only. No new dependencies without explicit discussion.
- **Project-agnostic:** plugin artifacts must contain no project-specific tokens (no `md-manager`, `pattaya`, `sand-`, `--space-`, `Geist`, `Mini`, etc.). Project-shaped knowledge comes from `flow.config.json`, not hardcoded paths.
- **Honest limitations:** known gaps are listed in `README.md` and `plugins/flow/docs/workflow.md` "Bootstrap status" section. Don't ship a change that invalidates either list without updating it.
