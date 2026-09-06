### FB-0003: Schema-without-implementation is a class of bug only dogfood catches
**Date:** 2026-05-24
**Source:** review feedback (PR 2 engineer-lens dogfood)

**What was said:** The Phase-7 engineer-lens review on PR 2 flagged that `memoryHardCap` was documented in `flow.config.schema.json` as configurable but `tools/memory/check.mjs` hardcoded `HARD_CAP = 30` and never read the config — a "false affordance" in the engineer lens's words. Same pattern with `branchPrefix`: documented in schema, no consumer in any skill. Both shipped through Phase 5's pre-commit greps cleanly because no static check correlates "slot documented in schema" against "slot read by something."

**Synthesized rule:** Every config slot landed in `flow.config.schema.json` must be paired with at least one consumer SKILL/agent/tool that reads it AT LANDING TIME — not "documented now, wired later." If a slot is genuinely future-only, mark it `"deprecated": "v1.x — not yet implemented"` in the schema description so consumers know. Treat schema-without-implementation as a contract lie equivalent to the loud-warning-vs-silent-no-op risk from PR 1. Pre-commit check: `for slot in $(jq -r '.properties | keys[]' schema/flow.config.schema.json); do if ! grep -q "$slot" plugins/flow/{skills,agents,tools,scripts}/; then echo "WARN: $slot documented but no consumer"; fi; done`.

**Applies to:** workflow, schema design, config-slot contracts

**Validation:** 2 of 13 slots in PR 2's schema (memoryHardCap, branchPrefix) had no consumer at first commit; engineer-lens caught both. Both wired in Phase 7 fix commit. The remaining 11 slots had at least one consumer.
