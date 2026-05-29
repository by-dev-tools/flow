# Fixture: verify-unknown-blocks

**Purpose:** Demonstrate that when any per-dimension judge returns `Unknown` for any criterion, `/flow:verify-build` aggregates to exit 1 (gate blocks) per FB-0011 (autonomy bar — ESCALATE on uncertainty).

**Phase:** PR Q Phase 4. Harness wiring deferred to PR Q Phase 9 (smoke + harness phase) since the existing eval harness (`run_evals.py`) is auditor/plan-critic-specific; verify-build judges use a different subagent shape and need a parallel test path.

## What this fixture contains

- `input/criteria.json` — A small input criteria list (3 criteria) including adversarial cases, modeling what `extract-criteria.py` would produce.
- `input/observations.txt` — A mock `/verify` stdout transcript covering 2 of 3 criteria (the third is deliberately not exercised — the Unknown trigger).
- `judges/correctness.json` — Expected output from the correctness judge against this input.
- `judges/regression.json` — Expected output from the regression judge.
- `judges/scope-creep.json` — Expected output from the scope-creep judge.
- `expected-aggregate.json` — The aggregated verdict that `/flow:verify-build` Step 7 should produce from the three judge outputs. Demonstrates `Unknown ⇒ exit 1`.

## Expected behavior (the contract this fixture pins)

1. Each judge runs independently against the observations.
2. Two of three judges return PASS / FAIL for the two exercised criteria.
3. For the third criterion (not exercised in observations), all three judges return `Unknown` per the rubric's "default to Unknown when two-citation rule cannot be satisfied" rule.
4. The aggregator at Step 7 sees at least one Unknown verdict and sets the overall verdict to `Unknown`.
5. Exit code is 1 (gate blocks). Findings buffer at `flow.config.json.verifyFindingsPath` contains the Unknown verdicts with their evidence + notes routed for `/flow:ship` Step 4a synthesis.

## How this fixture should be used by Phase 9

When the smoke harness lands in Phase 9 (`evals/fixtures/verify-toy-web-app/`), Phase 9 also adds a harness for verify-build judges. That harness:

1. Reads `input/criteria.json` and `input/observations.txt` from this fixture.
2. Invokes each judge with the appropriate dimension (mocked or real, depending on harness depth).
3. Compares actual judge outputs against `judges/*.json` (substring match per `run_evals.py` precedent).
4. Runs the aggregation logic (extracted from SKILL.md Step 7 into a Python helper at Phase 9) against the actual judge outputs.
5. Asserts the aggregated result matches `expected-aggregate.json`: verdict = `Unknown`, exit code = 1.

## Why this fixture exists in Phase 4 (not deferred to Phase 9)

The judge rubric (Phase 4's deliverable) is the load-bearing surface — the verdict definitions, the two-citation rule, the Unknown-default behavior. Pinning the expected behavior with a concrete fixture *now* keeps Phase 9's harness wiring honest: the harness must implement what this fixture documents, not what's convenient at Phase 9 time.

This is the same shape PR M used for its bounded-retry contract: write the contract first (FB-0012), let subsequent phases mechanically enforce it.
