# D1 Phase 2 — the prototype phase, human gate 1, and the loop re-order (v1.46.0)

**Date:** 2026-09-20 · **Branch:** `conductor/track-b-d1-phase-2-prototype-gate` · **FB:** FB-0113, FB-0114 · **Implements:** `dev-docs/handoffs/d1-prototype-first-gate.md` § Phase 2 (FB-0081)

## What shipped

For a UI-surface change the human's **first** decision point is now a **prototype** they can look at, not a plan they have to read. `/flow:prototype` writes the design brief, runs `/flow:review-brief` over it, builds and self-evaluates an HTML prototype, presents it with the existing click-to-pin annotation layer, and captures approval as a checkable record. Deterministic engine: `plugins/flow/skills/prototype/lib/prototype-gate.py` (`arming` / `trigger` / `contract` / `approve` / `verify` / `gate-execute` / `present`).

**The gate MOVES; it does not multiply.** The invariant the engine returns on every path: *exactly one pre-execution human gate — prototype approval XOR plan approval, never both, never neither* — plus *a plan always exists before Execute*.

## Why these decisions, and what they cost

**The loop is not renumbered.** "Re-order Steps 1–2" lands **inside Step 2**, which keeps its number and forks. Renumbering would have been the largest fan-out this repo has shipped: "Step 8" is a named contract in a dozen files. Steps 1, 4–7, 10–11 are byte-unchanged; 3, 8, 9 change in prose only.

**"A plan always exists" was pulled forward out of Phase 3.** The handoff filed it under Phase 3 alongside the auto-writer it checks. Leaving it there was wrong: this PR is what *removes* the human plan gate from the D1 path, and Phase 3 is gated on a spike, so the interim would have had neither a human gate on the plan nor an assertion that one exists — FB-0080's exact condition, reintroduced by the PR that exists to close it.

**`gate-execute` reads committed state only, and getting there took three tries.** v1: armed on "an approval record exists" — a file in gitignored `.flow/`, so deleting it turned the guard green (general.md item 3). v2: made the *digest* durable but left the *arming condition* on a live `trigger` call — which reads the brief, also in `.flow/` — so wiping the workspace still dropped it to `ok: true` vacuously, and the fixture meant to prove otherwise was unsatisfiable as written. v3: approval commits **two** lines to the plan doc (`**Pre-execution gate:**` + `**Prototype approved:**`), and the guard reads those plus the active Spec-walk block. All three states now derive from git alone.

**The feasibility read is the complement of `web`, not a list of native platforms** (FB-0113). An enumeration `{ios, android, tauri}` fails open on `platform` **unset** — the documented default, and the config an iOS consumer most commonly ships. Its *content* scales with the medium rather than the enum value: a browser-delivered surface satisfies it with one line, a proxied one needs per-affordance verdicts. **flow's own repo forced that distinction** — `platform: library` + `uiSurface: true`, shipping real browser UI — where a bare `platform == "web"` exemption would have made gate 1 unreachable in this very repository.

**`present` authors zero markup.** The obvious design rendered flow-authored chrome into the page; that would have made `prototype-gate.py` a second browser-UI emitter alongside `render-report.py` — which is inside `uiFilePatterns` precisely because it emits browser UI — and shipping it outside that pattern would have permanently excluded it from flow's own visual and a11y gates. All gate-1 chrome goes in the chat hand-off instead, pinned by a byte-diff fixture.

**No jq guard, deliberately.** Every other config-reading skill fails loud on missing `jq`. This one reads no config in shell — the engine parses `flow.config.json` with stdlib `json` — so a guard would imply a dependency it does not have. What makes the absence safe is the paired positive: an unreadable config yields `config_state: malformed` and **fails closed to the classic plan gate**, because `uiSurface`/`role` are then unknown and a human gate must not move on a guess.

**`mode: tiny` needed a scoping statement to be reachable at all** (FB-0114). Under the shipped definition — a 1–3-line bug fix, "rarely the right call" — D1's only proportionality collapse was undeclarable on design work, which would have rebuilt the ceremony D1 removes. A brief's `Mode` now scopes the pre-prototype phase only and is not inherited by the plan. The shipped definition is untouched at all five defining sites, pinned both ways.

## What was cut, and why

- **`lens-experience`'s accessibility/timing question → roadmap.** Cut at the plan gate. The test the gate applied is better than the one proposed: not *"was it assigned to Phase 2?"* but *"does this PR make the statement false?"* The doctor check and the brief word cap stay in because this PR falsifies them; a new Lens-A question is a feature addition.
- **No 35th config slot.** A published slot is `sensitivePaths` and consumers inherit it permanently; deferring is the reversible direction. Prototype artifacts stay in ephemeral `.flow/` — what mattered (the gate record) is committed.
- **Phase 3 is not built.** No auto-writer, no machine gate. Gated on §9.3.

## The interim state, stated honestly

Until `/flow:audit-coverage` gains its prototype-**source** input mode (approved, built in parallel), the post-gate-1 plan review is a **form-and-coherence check and explicitly not a completeness check**. The §9.3 spike measured this exact reviewer set catching 1 of 12 real coverage gaps. The backstop is the existing `/flow:audit-coverage` against a real diff at `/flow:ship` Step 2 — a gap is caught **late, not never**. Both rows are written into `workflow.md` so no shipped sentence describes a check that may not exist yet.

The spike measured an *auto*-written plan while this interim uses an *agent*-written one. That distinction is real in general and does not apply here: the spike auto-wrote its plan *in character as the D1 Step-6 agent*. Same agent, same context, same moment. The finding transfers.

## Verification

`plugins/flow/evals/run_prototype_gate_evals.py` — 206 checks, wired into CI (36 harnesses, join-check green). Full local suite green on exit codes. Notable: the trigger matrix asserts **both** `path` and `pre_execution_gate` per row, because `collapsed` and `classic` both emit gate `plan` and a gate-only assertion would leave the proportionality collapse pinned by nothing.

Both corpus sweeps run against a **seeded known positive** before their zero-results are trusted, and key on `git grep`'s **exit code** rather than a count of its output (general.md item 4 + corollary, which landed on main mid-flight and caught two of this PR's own fixtures).

## Process note

Nine reviewer rounds before the gate (7 × `/flow:critique-plan`, 2 × `/flow:audit-plan`), 27 findings, all accepted, none disputed. Three were BLOCKERs that would have shipped real holes. The review loop had no declared termination criterion until round 7 flagged that as drift; the rule is now **stop at the first round returning no BLOCKER**.

Every `/flow:critique-plan` pass ran **document-blind** — `referenceGlob` resolves zero documents through the installed 1.29.0 plugin (FB-0107) — so the **Spec violation** category never ran on this plan. Recorded because a limitation nobody writes down becomes a clean bill of health.
