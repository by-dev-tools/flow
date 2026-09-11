### FB-0015: Check bundled Claude Code skills before drafting any new flow skill
**Date:** 2026-05-28
**Source:** user correction (surfaced during PR Q `/flow:verify-build` planning)

**Note on numbering:** Cascaded through multiple collisions: drafted as FB-0010 → FB-0012 → FB-0013 → FB-0014, finally FB-0015. FB-0013 reserved by PR P (same-model critic collusion); FB-0014 claimed by PR R (init-skill additive-defaults). Each renumber was a polite deferral to existing plan-documented reservations. K1's claim-time protocol (reserved-feedback-numbers.md) is what made the collisions visible before merge; PR Q's slot is now claimed.

**What was said:** During PR Q (`/flow:verify-build`) planning, drafted a 20+-file skill spanning 5 platform runners (web/ios/android/tauri/cli), a `platform-detect.sh` lib, a `verify-judge.md` subagent, and per-platform schema slots. User asked whether this overlapped with the bundled `/verify` skill. It did, substantially: bundled `/verify` already does "run app + observe behavior," bundled `/run` already does platform detection across CLI/server/TUI/Electron/browser-driven/library buckets, and bundled `/run-skill-generator` scaffolds per-project launch recipes that `/run` and `/verify` automatically defer to. All three are listed in the harness available-skills section at every session start. CLAUDE.md explicitly forbids parroting bundled skills ("Never wrap a bundled Claude Code skill"). The first-pass draft violated this rule and would have shipped ~15 files of execution-layer duplication.

**Synthesized rule:** Before drafting any new `/flow:*` skill, audit the harness available-skills list for bundled skills that already cover the same surface. For each overlapping skill, identify what flow-specific value the new skill adds beyond the bundled one (config-slot integration, gate-shaped contract, feedback routing, in-flow context). If the delta is genuinely orchestration-only, the new skill becomes a thin wrapper (~5–6 files, 150-line SKILL.md) that delegates execution to the bundled skill — same pattern `/flow:security-review` and `/flow:accessibility-review` already follow. If the delta is null, drop the skill and reference the bundled one directly from `workflow.md` (the `/simplify`, `/batch`, `/debug`, `/loop`, `/claude-api` precedent).

Concrete pre-planning check: search the system-reminder "available-skills" section at session start; grep for the proposed skill's core verb (verify, run, audit, review, ship, plan, build, test); if a match exists, justify the wrapper with substantive added value or drop the skill.

This is a class lesson: the harness gives this information for free at every session start, and missing it is purely a discipline failure. Pair with FB-0010's pre-edit grep discipline — same "look before you write" shape, different layer (consistency across files vs duplication of capability).

**Applies to:** workflow, skill design, plan discipline, scope discipline

**Validation:** PR Q first-pass draft (then numbered PR M) proposed `lib/{web,ios,android,tauri,cli}-runner.md` + `lib/platform-detect.sh` + `agents/verify-judge.md` — all of which duplicate work bundled `/run` + `/verify` + `/run-skill-generator` already do. Caught at adversarial-review time by user question; redraft shrinks PR Q from 20+ files to ~6 by leaning on bundled skills as the execution layer.
