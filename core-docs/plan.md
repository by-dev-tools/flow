# Plan

## Current Focus

v0.1.0 plugin scaffold is shipped. Next load-bearing step is replacing the eval harness stub (`evals/run_evals.py:195` reads pre-recorded `.expected.txt` files) with live auditor invocation, then capturing fixtures for the three SKIP'd canonical cases in `evals/ground_truth.yaml`.

## Handoff Notes

None.

## Active Work Items

_None active. Add items here when the next piece of work is scoped._

---

## Recently Completed

- **Project-dev scaffolding** (2026-04-20) -- CLAUDE.md, core-docs, .claude/ infra added with plugin-vs-dev boundary documented.

## Backlog

- Wire `evals/run_evals.py` to live auditor subagent invocation (remove `.expected.txt` stub)
- Capture fixtures for `trio_navigation_stack_cycle_3`, `portfolio_blank_screen`, `trio_morphing_recall`
- Structured output schema for auditor (replace substring matching in eval checks)
- Expand artifact regex beyond the hardcoded 28-extension list in `scripts/extract_session.py`
- Raise or remove the 50-call tool-history cap in `scripts/extract_session.py`
- Generalize hardcoded SwiftUI proxy handling to other frameworks
