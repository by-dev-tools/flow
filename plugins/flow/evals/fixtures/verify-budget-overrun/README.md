# Fixture: verify-budget-overrun

**Purpose:** Pin the contract that when `/flow:verify-build` Step 5's tool-call count exceeds `flow.config.json.verifyBudgetCalls`, all unjudged verdicts are forced to `Unknown`, the overall verdict aggregates to `Unknown`, and the exit code is `1` (gate blocks). This is the fail-closed behavior per FB-0012(a) — the budget cap is a mechanical exit signal, not a judge-output signal.

**Phase:** PR Q Phase 9. Documentation fixture; harness wiring deferred to consumer dogfood.

## What this fixture demonstrates

The budget cap is what prevents a runaway verify pass from consuming the session's tool-call budget. The cap is `flow.config.json.verifyBudgetCalls` (default 60). When the count of tool calls made by bundled `/verify` during Step 5 reaches this cap:

1. `/flow:verify-build` aborts the verify invocation mid-flight.
2. Any criteria that had NOT yet been observed have their `observations[]` left empty.
3. The judges at Step 6 receive criteria with empty observations.
4. Per `lib/rubric.md` discipline, empty observations → cannot satisfy two-citation rule → Unknown verdict.
5. Aggregation at Step 7 sees Unknown → `overall_verdict: Unknown`, `exit_code: 1`.
6. The findings buffer's `metadata.verify_budget_overrun: true` flag signals to `/flow:ship` Step 4a (and the future HTML renderer) that the Unknown verdicts were forced by budget, not by inconclusive evidence.

This is fail-closed by design: a runaway verify pass that's eating tool calls without producing observations should NOT silently succeed by virtue of the gate timing out. It should block ship, route to ESCALATE per FB-0011, and let the user adjudicate (raise the budget? cap was correct? something wrong with the launch?).

## Files

- `input/config.json` — `flow.config.json` with `verifyBudgetCalls: 10` (low cap to trigger overrun in the simulated scenario).
- `input/criteria.json` — Three criteria; the simulated verify pass exercises the first one then hits the cap.
- `input/observations.txt` — Mock `/verify` stdout: covers criterion 1 fully, hits budget cap before covering criteria 2 and 3.
- `expected/findings-buffer.json` — Final aggregated buffer with `metadata.verify_budget_overrun: true`, overall verdict Unknown, exit code 1.

## How a future smoke run would use this fixture

1. Read `input/config.json` → confirm `verifyBudgetCalls: 10` is the cap.
2. Mock bundled `/verify` to emit `input/observations.txt` and report 10 tool calls used (exactly at cap).
3. Run `/flow:verify-build` against `input/criteria.json` with this config.
4. Compare actual findings-buffer output against `expected/findings-buffer.json`:
   - `metadata.verify_budget_calls_used`: 10
   - `metadata.verify_budget_overrun`: true
   - `overall_verdict`: "Unknown"
   - `exit_code`: 1
   - Criterion 1: aggregated_verdict "PASS" (observed before cap)
   - Criteria 2 and 3: aggregated_verdict "Unknown" with notes citing budget overrun

## What this fixture does NOT cover

- **Below-budget runs that still produce Unknown** for other reasons (those are covered by `verify-unknown-blocks/`).
- **Runs that complete fully under budget** (those are covered by `verify-toy-web-app/`).
- **Spike-mode budget overrun** — spike has only 3 checks; if Phase 6's spike rubric expands to require more than `verifyBudgetCalls` worth of tool calls, that's a misconfiguration, not a budget-cap test. Spike-mode behavior on budget overrun is the same as full-mode: force unjudged to Unknown.

## See also

- `verify-unknown-blocks/` — sibling: Unknown from inconclusive observations
- `verify-toy-web-app/` — sibling: end-to-end PASS happy path
- `plugins/flow/skills/verify-build/lib/findings-schema.json` — schema with `verify_budget_overrun` field
- `plugins/flow/skills/verify-build/SKILL.md` Step 5 — budget-cap semantics
