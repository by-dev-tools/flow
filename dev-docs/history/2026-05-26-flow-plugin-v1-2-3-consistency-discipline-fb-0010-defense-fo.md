### Flow plugin v1.2.3 — consistency discipline (FB-0010 defense for the recurring bug class)  `SAFETY`
**Date:** 2026-05-26
**Branch:** `pr-g/consistency-discipline`
**Commit:** [SHA to be filled at ship time]

**What was done:**
Encoded defenses for the most-recurring bug class flow's own development has surfaced — "consistency that depends on author memory" — across 6 incidents (PR 1 stale paths, PR B unset DEFAULT_BRANCH, PR D regex inversion, PR E POSIX/bash mismatch, PR F pass-1 slash-as-shell, PR F pass-2 slot-count fan-out + intra-file contradiction). Specifically:

1. **FB-0010** captures the lesson with all 6 citations. Two flavors named: *silent-skip on edge case* (failure swallowed via `2>/dev/null` / unset-fallback / regex inversion) and *fan-out contradiction* (a count/name/slot referenced in N places, only some updated by a contract change).
2. **`lens-staff-engineer.md`** (consumer-shipped) gains two explicit hunt categories: silent-skip sweep + consistency sweep. The "specifically asks" section adds a grep-after-diff step naming the patterns to search for. The "gotchas" section names the consistency sweep as load-bearing — fan-out contradictions live in unchanged files, so they survive diff-only review.
3. **`/flow:doctor` Check 2.5** (consumer-shipped) compares `jq '.properties | keys | length'` on the schema against any "N slots" claim in CLAUDE.md / README.md / docs/, flagging survivors of a stale count. Cheap mechanical check for the fan-out shape that's actually mechanizable.
4. **`plugins/flow/docs/workflow.md` Step 4** adds a "consistency sweep" paragraph naming the discipline at the preflight stage, before `/simplify` runs.
5. **`.claude/rules/general.md`** (project-dev) adds a "Consistency discipline (FB-0010)" section with the grep-first-edit-second rule + the "If a colleague greps for the old value tomorrow, will they find a contradiction?" check.
6. **README + manifest** bumped to v1.2.3 with version-note explaining the discipline. plugin.json + marketplace.json descriptions updated to reflect the new lens-engineer hunts + the doctor check.

**Why:**
The engineer-lens missed 2 of 6 occurrences first-pass (both fan-out shapes — PR F pass-2 was needed to catch them via adversarial review). Pattern is stable enough across PRs to encode rather than re-derive each time. Costs of encoding (small lens-prompt + doctor-check + workflow.md paragraph + project-dev rule) are dramatically smaller than the cumulative cost of adversarial-second-pass review every PR.

**Design decisions:**
- **Two-layer defense** — consumer-shipped (lens-engineer + doctor) + project-dev (general.md rule). Consumer projects benefit from the same discipline flow uses on itself; flow gets a stronger internal guardrail than just shipping the consumer artifacts.
- **Doctor Check 2.5 is WARN-not-FAIL.** Mismatched documented count is a real signal but doesn't BLOCK install/use; staying WARN keeps the doctor surface low-friction and respects the "[READY with WARN-level items]" path's existing semantics.
- **Lens-engineer hunts are additive, not gating.** The lens still triages BLOCKER/NIT/FOLLOW-UP; the new hunts give it explicit search vocabulary rather than relying on emergent "specifically asks" coverage.
- **Schema as source-of-truth for slot count.** Future contract changes update the schema, and the doctor check + lens grep both derive from that — no third copy to drift.

**Technical decisions:**
- Doctor Check 2.5 uses `grep -rEn '([0-9]+) slots?'` with awk filtering against the schema's actual count. Cheap, portable across BSD/GNU. The `grep -vE ":[[:space:]]*#"` line filters out comment lines so we don't flag `# Schema has 16 slots — see CHANGELOG` style annotations as stale.
- Workflow.md addition lives at Step 4 (Preflight) rather than Step 7 (Staff-review) because the discipline catches the bug class CHEAPER as a pre-simplify sweep than as a lens-agent finding.
- Project-dev rule lives in `.claude/rules/general.md` (auto-loads on `**/*`) rather than `safety.md` (auto-loads only on safety-critical paths). The discipline applies to every edit, not just safety surfaces.

**Tradeoffs discussed:**
- **Mechanizing further** — e.g., a pre-commit grep that does the slot-count check automatically — was considered. Decided against for now: pre-commit hooks add install friction; consumers vary in whether they run hooks; and Check 2.5 in `/flow:doctor` plus the lens-engineer prompt cover the same surface at lower cost.
- **Promotion to a Stop hook** (fail the session if `/flow:critique-plan` was skipped — the existing "honest gap" in CLAUDE.md.template) was also considered for this PR. Decided to scope to consistency-discipline only; Stop hooks are v1.x autonomous-routines work per the spec, and this PR is the rule-of-six trigger for the consistency class specifically, not a broader enforcement-layer redesign.
- **Single big "consistency.md" rule file** vs subsection of general.md was considered. Kept as a subsection because the rule applies on every edit (matching general.md's `**/*` glob) and dedicating a file would split the auto-load mechanism unnecessarily.

**Lessons learned:**
- 5 prior incidents (PRs 1, B, D, E, F-pass-1) all caught by the engineer-lens *eventually*. Only at occurrence 6 (PR F pass-2 — the slot-count fan-out) did the pattern require *adversarial* review to surface. That's the threshold for encoding: when the same lens that should catch it stops catching it reliably, give the lens explicit prompt-level vocabulary for the pattern.
- "Internal contradictions inside one file" (line 22 vs line 260 of doctor/SKILL.md) is a sub-shape of fan-out contradiction that survives even careful single-file review. The discipline rule names it explicitly.
- **SAFETY marker on this entry** is because `.claude-plugin/marketplace.json` and `plugins/flow/.claude-plugin/plugin.json` (both on `.claude/rules/safety.md`'s `paths:` list) had description text and version field changes. Runtime authority is unchanged — no allowedTools/sourcePaths/disable-model-invocation modifications; the changes are version + description prose only. Plus `/flow:doctor` Check 2.5 introduces a new WARN-branch error-handling shape (documentation.md format spec requires SAFETY marker on error-handling changes). Verified via `git diff main` that no authority-bearing keys changed in either manifest.

**Self-review iterations (workflow pipeline ran 6 parallel reviewers — engineer + push-further + UX-designer + design-engineer + security + plan-critic):**
- 2 BLOCKERs caught, both FB-0010 violations inside the PR that adds FB-0010 defenses: (a) `README.md:50` said "6 agents" but the count is 8; (b) `dev-docs/plan.md` "Files touched: 9 files" but Scope (in) enumerated 10. Both fixed inline before push. Validates the discipline's value and proves PR-G defenses applied to PR G itself work.
- 6 cheap NITs fixed in-tree, mostly FB-0010 violations within `/flow:doctor` Check 2.5 itself: schema-not-reachable silent-skip, no-docs-found vacuous PASS, jq-failure unguarded, greedy-sed picking grep-line-number digit, narrow scan-target list (missed CLAUDE.md.template + core-docs/ + dev-docs/), and the "PRs 1, B, D, E, F" undercount vs "6 incidents." A SCAN_TARGETS leading-space word-split bug surfaced only at smoke-test time and was a 7th silent-skip flavor caught by tightening the test matrix.
- 9 FOLLOW-UPs routed to plan.md (deferred deliberately): Defense #4 (silent-skip skill-code pairing), Check 2.5 generalization to skill/lens/rule counts, consumer-shipped consistency rule (`plugins/flow/rules/general.md`), plan-critic.md fan-out hunt addition, CLAUDE.md.template consumer mention, intra-file contradiction detection, schema-path fallback hardening, symlink-following grep hardening, citation drift across files.
