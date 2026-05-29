# Fixture: verify-toy-web-app

**Purpose:** End-to-end smoke fixture for `/flow:verify-build`. Documents the file structure + plan shape + expected outputs that a minimal "happy-path" verify run should produce against a toy web project. Pin the smoke contract; actual execution deferred to consumer dogfood at PR Q ship time (Phase 10) + ongoing post-merge.

**Phase:** PR Q Phase 9. This fixture is documentation + contract; not a self-contained runnable test (the verify-build skill needs bundled `/verify` + `/run` + an MCP, none of which the eval harness mocks).

## What this fixture demonstrates

The minimum viable case for verify-build to produce a clean PASS:

1. A project with a parseable plan containing `**Spec-walk:**` checkboxes.
2. A `.claude/skills/run-*/` recipe (scaffolded by `/run-skill-generator` — we describe what one would look like for a Vite app).
3. A simple, observable feature (a single button click that triggers a network request + UI update).
4. `/flow:verify-build` ran end-to-end: extract criteria → adversarial transform → bundled `/verify` → per-dimension judges → aggregate → buffer write.
5. All three dimensions PASS for both criteria → `overall_verdict: PASS` → `exit_code: 0` → ship pipeline continues.

## Directory layout

```
verify-toy-web-app/
├── README.md                          (this file)
├── app/
│   ├── package.json                   (Vite + minimal deps)
│   ├── index.html                     (one button: "Submit")
│   ├── src/main.js                    (button handler: POST /api/submit; show toast)
│   └── server.mjs                     (tiny Node server: POST /api/submit returns 201)
├── plan/
│   ├── flow.config.json               (planPath + verifyEnabled config)
│   └── plan.md                        (per-PR plan with 2 Spec-walk criteria)
└── expected/
    ├── extract-criteria.json          (output of lib/extract-criteria.py against plan/plan.md)
    ├── adversarial-cases.json         (output of lib/adversarial.md against criteria)
    ├── verify-stdout.txt              (mock bundled /verify transcript)
    ├── judge-correctness.json
    ├── judge-regression.json
    ├── judge-scope-creep.json
    └── findings-buffer.json           (the final aggregated buffer, all-PASS happy path)
```

## How a future smoke run would use this fixture

When Phase 9 (or post-PR-Q dogfood) wires a real harness, the harness would:

1. Spin up `app/` as a real running server (or use Playwright to drive it).
2. Run `/flow:verify-build` against `plan/` (with `flow.config.json.planPath = plan/plan.md`).
3. Capture each stage's actual output.
4. Compare actual vs `expected/*.json` (substring match per `run_evals.py` precedent).
5. Assert `findings-buffer.json` matches the contract: `overall_verdict: PASS`, `exit_code: 0`, all six dimension-criterion cells PASS.

## What we DON'T pin in this fixture

- **Exact bundled `/verify` stdout** — that's freeform per Anthropic docs; the harness should match on semantically-relevant substrings, not exact prose.
- **Adversarial case wording** — different judge runs may produce different adversarial cases; the contract is "1-2 distinct cases per criterion that satisfy the four properties," not "these exact cases."
- **Per-dimension judge prose in `notes`** — same reason; semantic match only.
- **Timestamps in the findings buffer** — `timestamp_offset_ms` will vary per run; harness ignores it for comparison.

## What we DO pin

- **Spec-walk extraction** — `extract-criteria.json` is deterministic; the parser is pure.
- **Verdict structure** — every criterion entry has all three dimensions; every dimension has `verdict` + exactly-2 `evidence` + `notes`.
- **Aggregation contract** — all PASS at criterion level → `aggregated_verdict: PASS`; all PASS overall → `overall_verdict: PASS, exit_code: 0`.
- **Not-tested checklist shape** — web-platform checklist from `lib/not-tested-checklist.md`; specific items may flip to `tested: true` if the run actually exercised them.

## Why this is documentation, not a runnable test

The verify-build skill orchestrates bundled `/verify`, which spawns bundled `/run`, which delegates to a per-project run skill or heuristic launch. None of these are mockable in the existing eval harness; mocking them would either:

1. Pin the wrong contract (test the mock, not the real integration), or
2. Add substantial new harness machinery for low marginal value.

The right validation is consumer dogfood: install flow at v1.3.0 in a real project, run `/flow:ship` with verify-build enabled, observe whether the contract holds in practice. PR Q's Phase 11 ship process exercises this in the smallest possible scope (flow's own dev-docs cascade — though flow itself is `platform: library` and skips verify-build, so the dogfood is "verify-build is correctly skipped on library projects"). Real consumer dogfood lands when md-manager or health-tracker installs v1.3.0.

## See also

- `verify-unknown-blocks/` — sibling fixture demonstrating the Unknown ⇒ exit 1 contract
- `verify-budget-overrun/` — sibling fixture demonstrating budget cap → Unknown → exit 1 contract
- `plugins/flow/skills/verify-build/lib/findings-schema.json` — the JSON Schema this fixture's `findings-buffer.json` validates against
- `plugins/flow/skills/verify-build/lib/findings-example.json` — canonical example matching the schema
