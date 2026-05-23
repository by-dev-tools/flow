# Product Specification

## Vision

A passive, skeptical auditor that runs inside Claude Code between "plan" and "execute" (or "done" and "trust"), surfacing claims the session never actually verified -- so users catch over-confident reasoning before it compounds into broken work.

## Long-term direction

The plugin's design is shaped by a longer-term goal: enabling AI agents to make decisions and approvals that humans can trust. Each piece contributes to that arc:

- **The reviewers** identify the gaps that would erode trust if missed (unverified claims, plan misalignment).
- **The two-citation discipline** keeps findings verifiable, not interpretive — a reviewer's claim can be falsified by inspecting its two quotes.
- **The disagreement loop** captures human pushback as input to prompt tuning, so the reviewers' calibration improves with use.
- **A planned verification sibling** (separate plugin, see plan.md) would close the loop further by executing the verification checks the auditor suggests — moving from "AI surfaces a concern" to "AI confirms or refutes the concern."

Today the plugin informs human decisions; the user stays the approval authority. The long-term arc shifts load from human-as-final-approver toward agent-as-final-approver, one trust step at a time. No piece of that shift is rushed — each requires evidence that the previous step is reliable.

## Usage guidance

| Work type | Suggested reviewers | Rationale |
|---|---|---|
| Bug fix | `/audit-plan`, `/audit-completion` | diagnosis + completion categories dominate |
| New feature | `/audit-plan`, `/critique-plan`, `/audit-completion` | assumption + scope + completion all matter |
| Refactor | all three | surface-area assumptions, scope discipline, build ≠ behavior |
| Throwaway prototype | none required | no trust context to protect |

Features benefit from this plugin *more* than bug fixes. The "Unverified diagnosis" category is bug-flavored and quiet on features; the other three categories are most-active on feature/refactor work where there is no original symptom to manually verify against.

## Problem

Claude produces confident plans and completion claims that are load-bearing but unverified. Common failure modes:

- Diagnosing a root cause from recall, then acting on it without running a tool that would confirm or falsify it.
- Declaring work "done" because `build` or `typecheck` passed -- proxies that don't prove the user-visible behavior was fixed.
- Building plans on premises not stated by the user and not grounded in the session context.
- Referencing prior work ("we already tried X") without re-reading the artifact to check the claim is still true.

Users typically catch these errors after acting on them, which is the expensive moment. An auditor that reads the transcript and names the gap -- before execution, before trust -- catches them cheaply.

## Solution

Two slash commands the user invokes manually:

- `/audit-plan` -- run after Claude produces a plan, before execution.
- `/audit-completion` -- run after Claude declares work done/fixed/ready, before trusting the claim.

Each command runs a Python preprocessor (`scripts/extract_session.py`) that loads the session JSONL, bounds the relevant window, extracts and summarizes tool calls, and identifies artifact paths Claude referenced. The preprocessor output is injected into a forked auditor subagent (`agents/auditor.md`) that applies a fixed audit schema and produces a plain-text report: either a single `ISSUE` block, an `AUDIT SUMMARY` with multiple issues, or `No issues flagged.`

The auditor itself is prompt-driven. No custom code runs in the subagent context.

## Features

| Feature | Description | Status |
|---------|-------------|--------|
| `/audit-plan` slash command | Dispatches preprocessor + auditor for a pre-execution plan review | shipped (v0.1.0) |
| `/audit-completion` slash command | Dispatches preprocessor + auditor for a post-completion claim review | shipped (v0.1.0) |
| Session preprocessing (`extract_session.py`) | Loads JSONL, normalizes turns, bounds window, summarizes tool calls, detects artifact paths | shipped (v0.1.0) |
| Bounding logic (`bounding_logic.py`) | Finds most recent substantive user message to anchor the audit window | shipped (v0.1.0) |
| Auditor system prompt (`auditor.md`) | 132-line prompt defining categories, falsifiers, false-verification proxies, output schema | shipped (v0.1.0) |
| Offline eval harness (`evals/run_evals.py`) | YAML-driven regression tests against pre-recorded expected outputs | shipped (v0.1.0) |
| `DISAGREE.md` feedback log | Append-only log of user-disputed audit outputs; feeds prompt-tuning | shipped (empty) |
| `/critique-plan` slash command | Dispatches preprocessor + plan-critic for scope / spec / coherence review of a proposed plan | shipped (v0.2.0) |
| Plan-critic system prompt (`plan-critic.md`) | Three categories (scope drift, spec violation, internal incoherence) with two-citation discipline and severity tiers | shipped (v0.2.0) |
| Reference-doc loading (`--reference-paths` / `--reference-glob`) | Preprocessor injects source-of-truth `.md` files into context so plan-critic can quote rules deterministically | shipped (v0.2.0) |
| `log-disagreement` auto-invoked skill | Model-invokable skill that captures user pushback on a finding to user-scope storage; no slash command required | shipped (v0.3.0) |
| Reviewer output footer | Auditor and plan-critic outputs end with an invitation to push back, anchoring the auto-invocation contract | shipped (v0.3.0) |
| Live auditor integration in evals | Replace `.expected.txt` stub with real auditor invocation | planned |
| Ground-truth fixtures for real cases | Three canonical cases (trio_navigation_stack_cycle_3, portfolio_blank_screen, trio_morphing_recall) still SKIP'd pending fixture capture | planned |
| Structured output schema | Move auditor output from free text to a parseable format so eval checks don't rely on substring match | planned |

## Audit Categories

Exactly four categories are recognized. Additions require a fixture and a `history.md` decision entry.

| Category | Fires on |
|----------|----------|
| Unverified diagnosis | Confident root-cause claim acted on with no tool invocation supporting it |
| Unverified completion | "Done / fixed / ready" claim backed only by build / typecheck / startup (false-verification proxies) |
| Unverified assumption | Plan premise not in the user request and not in session context, load-bearing enough to change the plan |
| Unverified recall | Reference to prior work without a fresh read of the named artifact |

## Tech Stack

- **Distribution:** Claude Code plugin installed via `/plugin install <path-or-marketplace-url>`
- **Preprocessing language:** Python 3.7+, stdlib only (`json`, `argparse`, `pathlib`, `dataclasses`, `re`, `subprocess`)
- **Prompt language:** Markdown with YAML frontmatter (Claude Code convention)
- **Subagent model:** whatever the user's Claude Code session resolves to; the plugin does not pin a model
- **Input:** session transcript files at `~/.claude/projects/<cwd-slug>/*.jsonl`
- **Output:** plain text to the Claude Code conversation
- **Persistence:** none. State lives in the user's session files and the repo's `DISAGREE.md`.

## Cost Structure

No per-use cost beyond the user's existing Claude Code token usage. The plugin delegates to a subagent in the same session; there are no external API calls, no hosting, no third-party services.

## Current Status

- **Stage:** v0.1.0 prototype -- functional, honest about limitations, not yet battle-tested on real sessions
- **Last updated:** 2026-04-20

### Known limitations (see `README.md` for the canonical list)

- Artifact regex misses files with no extension or unusual paths
- Tool-call history truncates at 50 calls
- Bounding logic occasionally grabs the wrong user turn on short follow-ups
- Plan/completion mode detection is heuristic
- SwiftUI proxy handling is hardcoded; other frameworks need explicit additions
- Eval harness reads pre-recorded `.expected.txt` files (`run_evals.py:195`) instead of invoking the auditor live; regression-only, not correctness
- Three canonical cases in `evals/ground_truth.yaml` are marked SKIP pending fixture capture
- No structured schema for LLM output; eval checks use substring matching and will drift if the auditor's formatting changes
