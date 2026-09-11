### Flow-run PR descriptions — per-step `## Flow run` table replaces `## Reviews` (v1.4.1)
**Date:** 2026-06-01
**Branch:** `claude/epic-northcutt-2d5e88` (commit at push time; off `origin/main` @ `4f5fba6`)

**What was done:**
Replaced the generic `## Reviews` blurb in the `/flow:ship` PR body with a `## Flow run` per-step table that documents the full loop run, plus instruction text telling the ship agent how to populate it from the session's loop history:
- **`plugins/flow/skills/ship/SKILL.md` §7** — `## Flow run` table (one row per loop step: Clarify → Plan+critique → Execute → Preflight → /simplify → /flow:staff-review → security/a11y/verify-build → Doc synthesis), each `✓` (ran) or `skipped (<reason>)`; a **Notable** cell for genuine signal or `—`. Instruction block encodes the mode/config skip reasons, the bidirectional honesty rule, the no-manufactured-notes rule, and the follow-ups-stay-canonical + never-merge doctrine.
- **`.claude/skills/ship/SKILL.md` (dev-side dogfood `/ship`) Step 4** — same `## Flow run` block (generic cross-refs, no `/flow:ship`-specific step numbers). Its merge behavior + step numbering left untouched (out of scope).
- **`plugins/flow/skills/ship-spike/SKILL.md` Step 7** — trimmed table; `/simplify` + `/flow:staff-review` pre-marked `skipped (spike)`; verify-build row carries the 3-check spike-rubric result.
- **`plugins/flow/docs/workflow.md`** — §10 gains a "The PR body documents the full flow run" subsection; the spike section's PR-body bullet names the trimmed table.
- Version bump v1.4.0 → **v1.4.1** (plugin.json, marketplace.json ×2, README header + ship-row, CHANGELOG v1.4.1 entry); cumulative description sentence appended.
- **`dev-docs/feedback.md` FB-0019** + reservation in `reserved-feedback-numbers.md`; this entry.

**Why:**
Prompted by dogfooding flow on another project where richer per-step PR descriptions were wanted. The old `## Reviews` one-liner under-documented what the loop actually did — a reviewer couldn't see at a glance which gates ran, which were skipped (and whether legitimately), or what each step surfaced. The table makes the loop's execution legible on the PR page itself.

**Design decisions:**
- **Table populated from in-session context, not a new machine-readable artifact.** The ship agent already writes Summary + Test plan from session context; the loop steps happened in the same session/branch, so a structured loop-log buffer would be over-engineering (FB-0015 bundled/over-build check). Generalizing verify-build's findings buffer to all steps was scoped out.
- **Bidirectional honesty rule.** The user's request named only the "never imply it ran when it didn't" failure mode. The plan-critic caught the inverse: the request's "if security/a11y are not-yet-shipped, say so" conditional evaluates *false* in v1.4.x (all three reviewers ship and run), so carrying it forward unconditionally would have instructed the agent to write "skipped — not yet shipped" for steps that actually execute. Resolution: real skip reasons map to runtime-config states; "not yet shipped" is a clearly-conditional fallback for a step genuinely absent from the reader's flow version. Captured as FB-0019 sub-rule (a).

**Technical decisions:**
- **Dev-side `/ship` reconciled, not unified.** CLAUDE.md treats `plugins/flow/skills/ship/SKILL.md` and `.claude/skills/ship/SKILL.md` as distinct surfaces and documents no sync convention; the dev-side skill is the older simpler push+PR+merge command. Applied only the PR-body section to satisfy the user's "update both" done-criterion, without touching its merge behavior or step numbering.
- **Version bump.** Shipped plugin artifacts (ship + ship-spike skills, workflow.md) changed, so v1.4.1 per the PR-J precedent (prompt-only change → bump). Surfaced in the plan as a MEDIUM-confidence call for the merge gate; docs-at-root no-bump precedent (PR H1/H2) doesn't apply since these files ship in the install bundle.

**Tradeoffs discussed:**
- **Per-step table vs. keeping the prose blurb.** The table costs more PR-body bytes and asks the agent to recall the whole loop; chose it because the legibility gain (skip-with-reason visible per step) is exactly what the dogfood surfaced as missing. The no-manufactured-notes rule + `—` default bound the cost: a routine PR's table is mostly dashes.
- **FB-0010 fan-out risk.** The skip-reason vocabulary now lives in four surfaces; mitigated by a dedicated spec-walk grep line (plan-critic FOLLOW-UP) rather than relying on author memory.

**Lessons learned:**
- A user request can embed a conditional that's stale against the current codebase. Evaluate "if X, say Y" against the code before encoding it as an instruction — the plan-critic's prove-or-disprove pass (v1.2.5) is what caught it here.

**Safety note (no SAFETY marker):** This entry touches safety-listed files (`ship/SKILL.md`, both manifests) but modifies only the PR-body template + version/description strings — no error-handling, persistence, or fallback paths. Ran the `git log --oneline -5 -- plugins/flow/skills/ship/SKILL.md` precondition check (recent SAFETY commits were verify-build + bounded-retry preflight + auto-invocable; none touched by this PR-body edit). Per `.claude/rules/documentation.md`, no SAFETY marker is warranted.
