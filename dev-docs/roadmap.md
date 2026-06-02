# Roadmap

Where the flow plugin is going over the next few horizons. Active work lives in `plan.md`; this is what's queued + what's being explored.

The plugin extraction umbrella (PRs 1-3 in flow + PRs 4-6 in md-manager) is the load-bearing scope through v1.2.0. Post-extraction v1.x+ work (autonomous routines, JTBD substrate, visual artifacts, design lenses, HTML reports, deploy previews) is documented in md-manager's `core-docs/handoffs/*-design-2026-05-23.md` series — that's the canonical roadmap for post-extraction; mirror entries here only when they become Now/Next.

---

## Now

**Plugin at v1.2.6 on `main`** (PR M squash `0cf642e`). Consumer-feedback umbrella complete (PRs A-F); FB-0010 consistency-discipline shipped (PR G); upgrade infrastructure shipped (PR H1 + H2-docs); workflow-spawn-skip prevention shipped (PR I, v1.2.4); adversarial sharpening of reviewer pipeline shipped (PR J, v1.2.5); bounded-retry mechanical preflight shipped (PR M, v1.2.6).

**This PR (PR H3)** is the roadmap refresh — docs-only, no version bump, same precedent as PR H1 / H2-docs. After it merges, the next-up sequence below applies.

### Execution order — what's next after PR H3 lands

Two parallel tracks in the active queue. Different scope, different drivers, can interleave at PR boundaries (each PR is reviewed + merged independently). **The recommended next-up PR after H3 lands is determined by which track has explicit user direction.**

**Track 1 — autonomy bar enforcement (driven by PR J's FB-0011):**
1. **PR K** — `/flow:red-team` skill: standalone reviewer mirroring security-review structure, FB-0008 stale-base preflight, FB-0006/FB-0007 source-file early-exit, FB-0011 autonomy-bar `Fix-confidence` field (per-finding `AUTO-FIX-SAFE` vs `ESCALATE`).
2. **PR L** — trust-boundary detector (mechanical/regex, stdlib-only) + autonomous-invocation wiring + `/flow:ship` Detection-Point-3 routing applying FB-0011's auto-fix-vs-escalate rule. Depends on PR K's output schema.

**Track 2 — research-driven orchestration hardening (driven by `dev-docs/research/agent-orchestration-2026-05.md`):**
1. **PR N** (bumps to v1.2.7) — documentation grounding (Magentic `max_stall_count` citation in FB-0012, evaluator-optimizer archetype reference in workflow.md) + structured-result STATUS markers for `/flow:ship` Step 2 reviewers (closes PR E+ FOLLOW-UP #1 with field-validated production pattern). Plus generalize doctor Check 2.5 to scan `template/` files (PR M's BLOCKER class validates this — promote to PR N scope or bundle into next doctor-touching PR).
2. **PR O** (bumps to v1.2.8) — test-edit reward-hacking PreToolUse hook: mechanizes Step 1c's no-disable-tests guard via `Edit`/`Write` matcher against test-file glob, emits `ask` decision. Adds `flow.config.json.testFilePatterns` slot (18 slots total) + opt-in hook entry.
3. **PR P** (bumps to v1.2.9 or v1.3.0) — auditor model-diversity eval addressing FB-0013 same-model critic collusion. **Measurement-first:** build comparative eval infrastructure (Step A), swap auditor to Sonnet ONLY if ≥80% finding-overlap + comparable FP rate vs Opus on existing fixtures (Step B). Tier 2/3 (plan-critic, lens agents) stay on Opus per user direction. v1.3.0 if swap ships; v1.2.9 if Step A's eval shows structural mitigation is sufficient.

### Cross-track dependencies

| Item | Depends on | Reason |
|---|---|---|
| PR L | PR K | PR L applies the autonomy-bar routing to PR K's output schema. |
| PR N Phase 2 (STATUS markers) | none from K/L | Independent — modifies different files (security-review/SKILL.md + accessibility-review/SKILL.md + ship/SKILL.md Step 2). |
| PR O | PR N (preferred, not required) | PR O's hook is opt-in via `default-hooks.json`; PR N's STATUS markers extend the reviewer-output contract that PR O's hook surface is adjacent to. Bundling would risk both PRs being large; sequencing keeps them small. |
| PR P | PR N + PR O | PR P's measurement infrastructure benefits from the structured-result contracts PR N adds (easier eval comparison). |
| Carryover doctor Check 2.5 generalization (template/ files) | none — bundle into PR N | Validated by PR M's BLOCKER class. Lowest-cost place to land. |

### Track 1 vs Track 2 — which goes next?

**Recommendation:** PR N is the lowest-risk next-up (docs grounding + STATUS markers; closes acknowledged FOLLOW-UP #1 with field-validated pattern; absorbs doctor Check 2.5 generalization). If PR K is further along in user planning (the FB-0011 entry suggests K's design is in flight), K could go first — but the two tracks don't block each other at PR boundaries.

The detailed per-PR plans live in `dev-docs/plan.md` § "Active Work Items".

## Next

After the K/L (Track 1) + N/O/P (Track 2) sequences ship, AND in parallel with them (different surface; mechanical rebase):

- **PR Q** (in flight on `claude/lucid-matsumoto-730ba0` — orthogonal to all of K/L/N/O/P/R; not queued behind any of them) — `/flow:verify-build` skill: plan-driven behavioral verification gate at `/flow:ship` Step 2. Wraps bundled `/verify` (and transitively `/run` + `/run-skill-generator`) with flow-specific orchestration — criteria extracted from `**Spec-walk:**` checkboxes, adversarial transformation, per-dimension parallel judges with Unknown-blocking gate, structured findings buffer routed to `/flow:ship` Step 4a. Closes the static-analysis-only gap in the loop's verification surface (Potemkin-interface / hallucinated-success class). Inherits PR M's FB-0012 bounded-retry contract for any future retry primitive. Per-PR plan: [`dev-docs/handoffs/pr-q-verify-build-plan.md`](handoffs/pr-q-verify-build-plan.md). **Phases 1–9 complete (full skill + lib + fixtures + ship + ship-spike + doctor + workflow + bootstrap + migration + schema); Phase 10 staff-review dogfood in progress; Phase 11 ship + manifest v1.3.0 next.** Different files than K/L/N/O/P/R; rebases cleanly in either order. FB-0015 (check bundled first) captures the discipline lesson.

### Make `/flow:ship` Step 2 auto-entry-aware so the verify-build precondition becomes a mechanical assertion (post-PR-S, push-further roadmap-concrete)

**Surfaces when:** `plugins/flow/skills/ship/SKILL.md`'s auto-invocation contract is touched again, OR a consumer reports an auto-ship that opened a PR on a `platform=library|none` / `verifyEnabled=false` project where the Step 8 predicate should have stopped it.

PR S's auto-ship relies on ship Step 2's verify-build (`exit_code:1` on FAIL/Unknown) as the mechanical net, but Step 2 behaves identically whether ship was auto-entered or typed — it can't *assert* the Step 8 predicate's "verify-build PASS / not-skipped" precondition actually held. For code diffs the net is real (Unknown blocks); the thin spot is the genuinely-skipped case (`verifyEnabled=false` / `platform=library|none`), where Step 2 skips verify-build entirely, so a mis-judged auto-advance there would open a PR with no behavioral gate. Direction: write a one-line auto-entry breadcrumb at Step 8 (a `--auto` arg or a `/tmp` flag) and have ship Step 2 hard-fail-to-present when `auto-entered AND verify-build skipped`. Cost ~ one flag write + one conditional + one eval fixture. Out of scope for the PR-S flag-flip (adds a control-flow contract); the right shape once auto-ship has dogfood miles.

### Verify-build HTML case-study report (PR R successor candidate, post-PR-Q)

**Surfaces when:** consumer reports they want a richer pre-merge review artifact than the structured-buffer + PR-body checklist PR Q ships, OR PR Q's findings-buffer JSON schema gains a stable consumer-validated shape.

**Direction:** PR Q's `/flow:verify-build` JSON findings buffer (per `lib/findings-schema.json`) is the structured-data layer. The vision (user, 2026-05-28) is a **rendered HTML case-study report** as the final pre-merge artifact — the file the user opens before clicking merge. Reference shape: `/Users/benyamron/dev/health-tracker/.claude/worktrees/nervous-meitner-0f88be/case-study.html` — a polished narrative page with hero + lede + TOC + numbered sections + per-section "the question / what we explored / what we learned" panes. Per-section content for verify-build: the criterion (from `**Spec-walk:**`), the adversarial cases generated, the screenshots / a11y-tree observations captured at each step, the per-dimension judge verdict (PASS / FAIL / Unknown with two-citation evidence), final "what we did NOT test" checklist. Closes the workflow loop at the human gate (Step 10 → merge) with full evidence.

**Forward-compat lever in PR Q (already done):** PR Q's findings-buffer JSON shape is designed as a superset of what an HTML renderer needs — per-criterion + per-adversarial-case + per-step observations with `type` discriminator + per-dimension verdict with evidence + top-level "not tested" checklist. PR Q does NOT render HTML; this future PR does, against the JSON contract PR Q establishes.

**Origin:** user vision note 2026-05-28, shared while finishing PR Q scoping intake. Not assigned a PR letter yet (PR R is taken by the init-skill plan); will be PR S+ once PR Q ships.

- **27 carryover FOLLOW-UPs** routed from reviews of PR G + H1 + I + J + H2-docs + M. Most are MEDIUM-priority polish or v1.2 hygiene; bundle into a future PR H-proper consolidation after the active queue lands. Highlights: doctor Check 2.5 generalization to `template/` files (validated by PR M's BLOCKER class; folding into PR N is preferred — see Now § Cross-track dependencies); manifest description CHANGELOG.md extraction; `preflightCmd` example in `template/base/flow.config.json.example`; per-attempt log machinery enforcement.
- **Resume umbrella retirement.** md-manager PRs 5 (dogfood) + 6 (delete duplicates + retire umbrella) per `dev-docs/handoffs/md-manager-pr4-6-spec.md`. Flow-side: standing by for PR 5's feedback intake; may surface additional rough edges worth a second follow-up bundle.
- **Carryover PR-2 FOLLOW-UPs not yet absorbed** (items 3-8 in `dev-docs/plan.md` § "PR 3+ follow-ups from PR 2 review"). Most are MEDIUM-priority polish or v1.2 hygiene; pick up opportunistically rather than as a focused PR.

## Later

- **Schema slot bi-directional consumer-pairing check** as a pre-commit recipe (FB-0003 pre-commit grep + FB-0009 follow-up). One-shot script under `tools/` would catch the next schema-without-implementation / implementation-without-schema bug before it ships.
- **End-to-end `/flow:ship` regression coverage.** Currently zero fixtures for the workflow skills; verification is dogfood-only. A small fixture project under `evals/` that exercises one ship pipeline in CI would catch the runtime-permission class (FB-0002) before it ships.
- **CHANGELOG.md extraction from manifest descriptions** — both plugin + marketplace descriptions are at ~1500 chars after each version cumulative sentence; extracting to CHANGELOG.md reference would relieve the bloat. Worth doing before v1.2.7 to stop the trend (engineer + auditor lens convergence on PR M).
- **Doctor Check 2.5 generalization** — currently scans `CLAUDE.md / README.md / docs / core-docs / dev-docs` for stale `N slots` references; PR M's BLOCKER (template/ files missed) validates extending to scan `template/` too. Also worth generalizing beyond slot count to skill count / lens count / rule count / version strings (per PR G FOLLOW-UP #2). Bundle into PR N or the next doctor-touching PR.
- **`## Flow run` skip-vocabulary consistency check** (PR T staff-review FOLLOW-UP) — the skip-reason vocabulary (`skipped (spike)` / `skipped (tiny)` / `uiSurface:false` / `verifyEnabled:false` / `platform library|none`) + the `<✓ / skipped (reason)>` Status-cell shape now live in `/flow:ship` §7, `/flow:ship-spike` §7, and (by reference) the dev-side `.claude/skills/ship`. PR T guards drift with a one-PR spec-walk grep; the durable fix is a `/flow:doctor` check that diffs the skip-reason token set + Status-cell convention across those surfaces. Net-new check; fold into the Check 2.5 generalization above. **Surfaces when:** the `## Flow run` table wording is edited in any ship skill.

---

## § Exploration

Items surfaced by `/flow:staff-review`'s push-further lens, consumer dogfood, or research passes. These don't have a concrete shape yet — they describe a direction worth investigating when relevant code is touched. Each entry includes a **`Surfaces when:`** trigger naming the file paths or area that should re-surface the item, so the auto-loading `exploration` rule can grep this section for trigger matches.

### Cross-run aggregation of `## Flow run` tables — the loop reflecting on itself (PR T, push-further exploration)

**Surfaces when:** `plugins/flow/skills/ship/SKILL.md` §7 (`## Flow run`) is touched again, OR any future loop-telemetry / `/flow:doctor` cross-PR-analysis work begins.

PR T (v1.4.1) makes each ship emit structured per-step self-documentation on its PR — but every table is born and dies with one PR; nothing ever reads them back. The latent value the structure creates: noticing patterns across runs ("`/simplify` has shown `—` on the last 8 PRs — is it earning its step?"; "verify-build skipped 6 runs straight — is `verifyEnabled` mis-set?"). Open question: is there a low-cost way to make the tables aggregatable (e.g. `/flow:doctor` scanning the project's own merged-PR bodies via `gh`) **without** introducing the per-session machine-readable loop-history artifact PR T deliberately declined (FB-0015 over-build check / FB-0019 "in-session context only")? Touches retention/parsing/privacy questions with no clear shape yet. Do NOT pull into a PR until the shape clarifies — the in-session-only decision is correct for current scope.

### Stop-hook enforcement for the Step 8 ship-readiness predicate (post-PR-S, push-further exploration)

**Surfaces when:** `plugins/flow/skills/ship/SKILL.md`'s auto-invocation contract is widened to a currently-skipped platform (per FB-0018's "applies to"), OR a consumer reports an auto-ship that fired when the predicate should have stopped it, OR `plugins/flow/hooks/default-hooks.json` gains a Stop hook for any other reason.

PR S deliberately keeps the Step 8 predicate as *guidance* (rule + skill description), with verify-build as the only mechanical backstop — correct ceiling for a flag-flip PR. A Stop-hook is the lever that would make the predicate genuinely non-bypassable (the model can't talk past a hook), but it's a different surface and out of scope. This entry records that the soft-enforcement model was a deliberate choice, not an oversight, so a future widening session doesn't reinvent the question.

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

### Dynamic-workflows-based review: re-test refutation across problem types, incl. UI  *(research-driven — re-test as the feature evolves)*

**Surfaces when:** (a) Anthropic ships a new dynamic-workflows version or moves it past research preview (the API/behavior changes), OR (b) Flow gains a UI-bearing consumer project to dogfood on, OR (c) any future reviewer-quality pass is run on a substantively different diff (large migration, genuinely-buggy pre-review diff, UI/a11y-heavy diff).

**Direction:** The 2026-05-28 reviewer-refutation spike (`dev-docs/research/dynamic-workflows-2026-05.md`; history entry "Reviewer-refutation spike — verdict") tested *blind* independent refutation vs PR J's self-disproof on **one** diff (`bootstrap.sh`, a shell script). On that diff, blind refutation refuted 0/15 (a rubber stamp) while self-disproof refuted 5/15 — because the false positives there were **significance** misjudgments (the mechanism is real, but doesn't matter under Flow's trust model), and blindness strips the context needed to judge significance. **This is one data point on one problem type — explicitly not a write-off.** Dynamic workflows are in research preview and will evolve; the result may differ on diffs where the dominant FP class is *verification* error rather than *significance* error.

Re-test specifically on:
- **UI projects** — a11y + design-engineer + visual findings may behave differently under refutation than shell-correctness findings; the significance-vs-verification balance is likely different (a contrast-ratio or focus-trap claim is more mechanically checkable than a "is this attacker-reachable" claim). This is the highest-value re-test and needs a UI-bearing consumer (none in flow's own repo).
- **Genuinely-buggy, pre-review diffs** — the spike reviewed an already-merged/clean file, which undersamples the "does refutation wrongly kill *real* findings" failure mode. Re-run on a diff with known-planted or known-historical bugs.
- **Larger / migration-scale diffs** — where dynamic fan-out (scale finders to diff size) is the actual draw, not just refutation.

The promising variant the spike pointed at (not yet tested): **informed-independent refutation** — a fresh agent *with* stance + project context (not blind) + a uniform significance/exploitability rubric — which would address both the rubber-stamp problem (blind) and the inconsistency problem (self-disproof gave opposite verdicts on the same issue across framings).

**Origin:** Reviewer-refutation spike 2026-05-28 (`dev-docs/research/dynamic-workflows-2026-05.md`); user direction to keep the direction alive and re-test across problem types incl. UI as dynamic workflows evolve, rather than write it off on one data point.
