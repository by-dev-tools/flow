# Roadmap

Where the flow plugin is going over the next few horizons. Active work lives in `plan.md`; this is what's queued + what's being explored.

The plugin extraction umbrella (PRs 1-3 in flow + PRs 4-6 in md-manager) is the load-bearing scope through v1.2.0. Post-extraction v1.x+ work (autonomous routines, JTBD substrate, visual artifacts, design lenses, HTML reports, deploy previews) is documented in md-manager's `core-docs/handoffs/*-design-2026-05-23.md` series — that's the canonical roadmap for post-extraction; mirror entries here only when they become Now/Next.

---

## Now

**Plugin at v1.2.5 on `main`** (PR J squash `2e8ab3c`). Consumer-feedback umbrella complete (PRs A-F); FB-0010 consistency-discipline shipped (PR G); upgrade infrastructure shipped (PR H1 + H2-docs); workflow-spawn-skip prevention shipped (PR I); adversarial sharpening of reviewer pipeline shipped (PR J).

Active queue — see `dev-docs/plan.md` § "Active Work Items" for full per-PR plans:

- **PR M** (open at [#22](https://github.com/by-dev-tools/flow/pull/22) — merge queued; bumps v1.2.5 → v1.2.6) — bounded-retry mechanical preflight at Step 1c of /flow:ship + /flow:ship-spike. Loops only on externally-verifiable preflight exit code (FB-0012). Independent of K/L scope; can land in any order. Grounded in `dev-docs/research/agent-orchestration-2026-05.md`.
- **PR K** (queued behind PR J) — `/flow:red-team` skill: standalone reviewer mirroring security-review structure, FB-0008 stale-base preflight, FB-0006/FB-0007 source-file early-exit, FB-0011 autonomy-bar `Fix-confidence` field.
- **PR L** (queued behind PR K) — trust-boundary detector (mechanical/regex, stdlib-only) + autonomous-invocation wiring + per-finding `AUTO-FIX-SAFE`/`ESCALATE` routing per FB-0011 autonomy bar. Detection-Point-3 routing for /flow:ship.
- **PR N** (queued behind PR M; bumps to v1.2.7) — research-driven orchestration hardening: documentation grounding (Magentic `max_stall_count` citation in FB-0012, evaluator-optimizer archetype reference in workflow.md) + structured-result STATUS markers for `/flow:ship` Step 2 reviewers (closes PR E+ FOLLOW-UP #1 with field-validated pattern).
- **PR O** (queued behind PR N; bumps to v1.2.8) — test-edit reward-hacking PreToolUse hook: mechanizes Step 1c's no-disable-tests guard via `Edit`/`Write` matcher against test-file glob, emits `ask` decision.
- **PR P** (queued behind PR O; bumps to v1.2.9 or v1.3.0) — auditor model-diversity eval addressing FB-0013 same-model critic collusion. Measurement-first: build comparative eval infrastructure, swap auditor to Sonnet ONLY if ≥80% finding-overlap + comparable FP rate vs Opus on existing fixtures. Tier 2/3 (plan-critic, lens agents) stay on Opus.

## Next

After the M/N/O/P sequence + K/L ship:

- **27 carryover FOLLOW-UPs** routed from reviews of PR G + H1 + I + J + H2-docs + M. Most are MEDIUM-priority polish or v1.2 hygiene; bundle into a future PR H-proper consolidation after the active queue lands. Highlights: doctor Check 2.5 generalization to `template/` files (validated by PR M's BLOCKER class); manifest description CHANGELOG.md extraction; `preflightCmd` example in `template/base/flow.config.json.example`; per-attempt log machinery enforcement.
- **Resume umbrella retirement.** md-manager PRs 5 (dogfood) + 6 (delete duplicates + retire umbrella) per `dev-docs/handoffs/md-manager-pr4-6-spec.md`. Flow-side: standing by for PR 5's feedback intake; may surface additional rough edges worth a second follow-up bundle.
- **Carryover PR-2 FOLLOW-UPs not yet absorbed** (items 3-8 in `dev-docs/plan.md` § "PR 3+ follow-ups from PR 2 review"). Most are MEDIUM-priority polish or v1.2 hygiene; pick up opportunistically rather than as a focused PR.

## Later

- **Schema slot bi-directional consumer-pairing check** as a pre-commit recipe (FB-0003 pre-commit grep + FB-0009 follow-up). One-shot script under `tools/` would catch the next schema-without-implementation / implementation-without-schema bug before it ships.
- **End-to-end `/flow:ship` regression coverage.** Currently zero fixtures for the workflow skills; verification is dogfood-only. A small fixture project under `evals/` that exercises one ship pipeline in CI would catch the runtime-permission class (FB-0002) before it ships.
- **CHANGELOG.md extraction from manifest descriptions** — both plugin + marketplace descriptions are at ~1500 chars after each version cumulative sentence; extracting to CHANGELOG.md reference would relieve the bloat. Worth doing before v1.2.7 to stop the trend (engineer + auditor lens convergence on PR M).
- **Doctor Check 2.5 generalization** — currently scans `CLAUDE.md / README.md / docs / core-docs / dev-docs` for stale `N slots` references; PR M's BLOCKER (template/ files missed) validates extending to scan `template/` too. Also worth generalizing beyond slot count to skill count / lens count / rule count / version strings (per PR G FOLLOW-UP #2). Bundle into PR N or the next doctor-touching PR.

---

## § Exploration

Items surfaced by `/flow:staff-review`'s push-further lens, consumer dogfood, or research passes. These don't have a concrete shape yet — they describe a direction worth investigating when relevant code is touched. Each entry includes a **`Surfaces when:`** trigger naming the file paths or area that should re-surface the item, so the auto-loading `exploration` rule can grep this section for trigger matches.

### Rule-of-three: `flow:close-out` skill abstraction for umbrella tracker hygiene

**Surfaces when:** a fourth umbrella close-out PR lands in any consumer (e.g., the eventual designer migration creates the same shape) — currently three instances: md-manager#21 (close-out for flow PR 1+2), md-manager#22 (close-out for flow PR 3), and md-manager#24 (close-out for flow PR 4).

**Direction:** The mechanical 70% of these close-out PRs is now stable across three instances — SHIPPED header format, checkbox-flip diff in `core-docs/plan.md`, sweep-to-Recently-Completed at `/flow:ship` time. The per-PR 30% (which FB-derived confidence verdicts to name, which post-merge action items to surface) is genuinely PR-specific. If a fourth instance lands, that's the rule-of-three trigger to consider whether the variance is principled (worth keeping bespoke) or accidental (worth a `flow:close-out` skill that templates the mechanical parts and prompts for the FB-derived parts). Do not extract yet — three is the cue to flag, not the cue to commit.

**Origin:** md-manager PR #24 push-further lens; consumer feedback report 2026-05-25.

**Out of scope (don't conflate):** This is distinct from `/flow:ship` itself (which closes out a PR's OWN session) and from `/flow:ship-spike` (which closes out a spike). The proposed `flow:close-out` would close out a CROSS-REPO umbrella tracker entry — orthogonal scope.

### Hook-mechanization fan-out for reward-hacking suppressors  *(STRONG signal)*

**Surfaces when:** PR O lands the test-edit PreToolUse hook, OR a second reward-hacking instance is observed in a Step 1c retry attempt log (suppressor insertion or test deletion that the prompt-level guard didn't catch).

**Direction:** PR O ships a PreToolUse hook on `Edit`/`Write` against test-file patterns, emitting `ask`. The same hook shape applies to other reward-hacking patterns the prompt contract already names but doesn't mechanize: `@ts-ignore` / `# type: ignore` / `// biome-ignore` / `# noqa` / `eslint-disable-next-line` / `@SuppressWarnings` / `#[allow(...)]` insertion via Edit operations; deletion of `expect()` / `assert` calls; weakening type signatures. All detectable as PreToolUse hooks on Edit/Write with regex on `new_string` (`old_string` for deletions). If PR O's test-edit hook earns its keep in dogfood, follow with PR O.1 covering suppressor insertion. If PR O shows false-positive friction during regular dev, the fan-out is rejected as a class — keep prompt-level guards + human merge gate.

**Origin:** PR M push-further lens EXPLORATION (STRONG signal per the research synthesis); pairs naturally with PR O's mechanism.

### Flaky-test classification: distinguish "no progress" from "fix-not-applied"  *(MODERATE signal)*

**Surfaces when:** Step 1c bounded retry produces an oscillation abort that turned out to be a flaky test (consumer reports false-positive after their first oscillation BLOCKER), OR a second consumer-PR exhausts N=3 on a test that intermittently passes.

**Direction:** Current Step 1c contract conflates "Claude attempted a fix that didn't help" (oscillation) with "Claude correctly recognized a transient failure and applied no fix" (flake-clear). Magentic's `max_stall_count` distinguishes "no progress" from "wrong progress" via consecutive-non-progressing-rounds counting; Flow's diff-hash conflates them. Mitigation worth tracking: if attempt N+1 produces *identical diff to HEAD* (i.e., no fix applied) AND preflight passes on that attempt, treat as flake-clear and proceed; require this case to be logged explicitly so dogfood can distinguish legitimate flake-clears from missing fixes.

**Origin:** PR M push-further lens EXPLORATION (MODERATE signal); inspired by Magentic stall counter pattern (research §3.2).

### Goose's `load` vs `delegate` execution-mode verb split  *(MODERATE signal)*

**Surfaces when:** Anthropic ships any skill-to-skill or skill-to-subagent orchestration primitive in Claude Code, OR Block's Goose ships the `load`/`delegate` verb proposal ([Goose discussion #6202](https://github.com/block/goose/discussions/6202)).

**Direction:** Goose's proposal: unify recipes / skills / subagents under two execution verbs — `load` injects sources into current context ("Teach me this"); `delegate` executes sources in isolated subagents ("Do this for me"). *"The tool determines the execution mode, not the file format."* This would resolve Flow's emergent `Skill('a'); Skill('b')` pattern — currently undocumented by Anthropic — into a sanctioned primitive. If Anthropic reacts with their own version, Flow should adopt their primitive; if Goose ships theirs first and gains traction in the Claude Code ecosystem, Flow should consider adopting it for `/flow:ship` Step 2's reviewer invocations. Don't preempt; this is the most thoughtful public take on the orchestration question but signal is single-engineering-discussion-strength, not multiple-converged-sources.

**Origin:** Skill-chaining research pass 2026-05-27 (`dev-docs/research/agent-orchestration-2026-05.md` §7.3); PR M push-further lens flagged as forward bet.

### Network/infrastructure failure classification in Step 1c  *(WEAK signal)*

**Surfaces when:** A real Step 1c attempt fails because of network/disk-full (not code), AND the user reports the 3-attempt exhaustion was wasted budget — i.e., they wanted Step 1c to abort early on infrastructure failure rather than treat it as a fixable code failure.

**Direction:** Today Step 1c treats every non-zero non-127 exit as fix-attempt-worthy. A consumer running `npm test` that fails because `ECONNREFUSED` / `ETIMEDOUT` / `ENOSPC` (npm registry unreachable, disk full, etc.) burns the retry budget on attempts Claude can't possibly fix. Mitigation worth tracking: classify stderr matching `ECONNREFUSED|ETIMEDOUT|ENOSPC|EHOSTUNREACH` as `BLOCKER: infrastructure failure, not a code failure — fix the environment and retry` without consuming the retry budget (same fail-fast shape as exit 127). Weak signal because in practice these are rare during a /flow:ship invocation (developers don't usually have network failures mid-PR-shipping); preempting violates FB-0003.

**Origin:** PR M push-further lens EXPLORATION (WEAK signal).

### Markdown-lint preflight slot for docs-only PRs  *(WEAK signal)*

**Surfaces when:** A consumer reports wanting docs-only PRs to still run a mechanical check (markdownlint, vale, alex, cspell) even though Step 1c's docs-only early-exit skips the full preflight.

**Direction:** Step 1c skips preflight entirely on docs-only diffs (no source files per `sourceFilePatterns`). Some consumers ship documentation as a product surface (md-manager, documentation sites) and want mechanical checks at ship time. A `flow.config.json.docsPreflightCmd` slot would solve this without bloating the existing `preflightCmd`. WEAK because no consumer has asked yet; pre-empting violates FB-0003. Roadmap entry exists so we don't re-derive the design when/if the request lands.

**Origin:** PR M push-further lens EXPLORATION (WEAK signal).

### Eval fixture re-categorization (`evals/security/` → `evals/contract/`)  *(deferred design discussion)*

**Surfaces when:** A third contract-shape eval fixture is authored (currently 2: `test_preflight_retry.py` + the planned `test_status_markers.py` for PR N) — rule-of-three trigger for re-categorization.

**Direction:** PR M added `test_preflight_retry.py` under `plugins/flow/evals/security/`, but the file is a contract test (asserting SKILL.md text + schema slot shapes), not a security test (asserting no command injection / no path leak). Mis-categorization compounds — the next contract test will follow the precedent. Either (a) rename `evals/security/` to `evals/` and put contract tests at top level alongside `test_cwd_constraint.py` / `test_malicious_config.py`, OR (b) create `evals/contract/` and move `test_preflight_retry.py` there. Option (b) is cleaner but affects the `run_security_evals.py` runner (which auto-discovers via glob). Defer until the third contract fixture forces the call.

**Origin:** PR M push-further lens NIT (deferred for design discussion). PR N's `test_status_markers.py` will be the rule-of-three trigger.
