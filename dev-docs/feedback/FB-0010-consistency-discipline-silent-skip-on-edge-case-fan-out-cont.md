### FB-0010: Consistency discipline — silent-skip on edge case + fan-out contradiction are the two flavors that survive single-pass review
**Date:** 2026-05-26
**Source:** review feedback (synthesized retrospectively after 6 occurrences across PRs 1, B, D, E, F-pass-1, F-pass-2)

**What was said:** Across the consumer-feedback PR sequence (A → F), the same bug class kept surfacing in adversarial review — always *after* the engineer-lens or simplify pass that should have caught it. The class has two distinct shapes that share one root cause:

1. **Silent-skip on edge case.** Code that fails on an edge case without surfacing the failure. The path silently degrades instead of erroring loud. Examples:
   - PR 1: stale `core-docs/` paths in `/flow:critique-plan` defaulted empty, gave the plan-critic zero reference docs, never warned.
   - PR B: `DEFAULT_BRANCH=` unset triggered downstream `origin/..HEAD` parsing as a literal string, failed silently in the stale-base check.
   - PR D: regex inversion in the per-diff early-exit always matched, so every diff falsely tripped the "no source files" gate.
   - PR E: POSIX `[ ]` test with a bash-only `${arr[@]}` expansion would have produced empty stdin to `grep` and silently taken the false-OK branch in non-bash shells.
   - PR F pass-1: `/flow:doctor` Checks 1.1/1.2/3.2 invoked `/plugin marketplace list` and `/help` inside `Bash` blocks — shell can't resolve slash commands, would have returned empty stdin and INVERTED every check.

2. **Fan-out contradiction.** A contract value (a count, a name, a slot) referenced in N places, where a contract change only updated some of them. The remaining stale references contradict the new ground truth. Examples:
   - PR F pass-2: PR D added 2 schema slots (sourceFilePatterns + uiFilePatterns), bringing the total from 14 → 16. PR F left 5 places still saying "14 slots" (README ×2, CLAUDE.md.template, doctor/SKILL.md, bootstrap.sh).
   - PR F pass-2: `/flow:doctor` SKILL.md said "exits 0 only when all checks pass" at line 22, but line 260 said "not an exit code, since skill bodies are agent prompts not processes." Internal contradiction inside one file — same PR fixed the bottom but not the top.
   - PR F pass-2: README workflow-surface header said "10 user-visible skills" but the table had 11 rows (the new `/flow:doctor` row from this PR).

**Common root cause:** *consistency that depends on author memory*. Both shapes survive engineer-lens review when the reviewer is reading the diff (which looks self-consistent) without grepping the codebase for related references. Both shapes survive `claude plugin validate` because the manifest is syntactically clean. Both shapes survive `/simplify` because the per-file shape is fine.

**Synthesized rule:** Treat consistency across files as a first-class review concern, not an emergent property. Four concrete defenses:

1. **In review prompts (consumer-shipped).** `lens-staff-engineer` should explicitly grep for stale references after any contract change. Pattern: "the diff claims contract X (e.g., 'N slots', 'flag --foo deprecated', 'now reads from config.bar'); grep the codebase for residual references to the OLD form and flag survivors." Make this explicit in the lens prompt rather than implicit in "specifically asks."

2. **In mechanical checks (consumer-shipped).** `/flow:doctor` should compare derived counts against documented counts when both are cheap to introspect — e.g., schema slot count vs the integer in any `flow.config.schema.json` reference. A WARN beats a wait-for-adversarial-review.

3. **In project-dev rules.** A `Consistency discipline` section in `.claude/rules/general.md` reminds future sessions: when changing a count, name, or slot, **grep first, edit second.** Specifically: `git grep -nE '<old-value>' -- '<file-types>'` before staging, and treat every survivor as a fix that ships with the contract change, not a follow-up.

4. **In skill code (consumer-shipped).** Silent-skip class — pair every `2>/dev/null || true` / `// empty` / `|| echo ""` with an explicit positive assertion that the value is non-empty before the consumer uses it. If unset is acceptable, branch explicitly with a `[WARN]` / `[SKIP]` log line; if unset is fatal, exit with a clean message at the entrypoint (FB-0009 fail-fast pattern generalized).

**Applies to:** workflow, review prompts, doctor checks, project-dev discipline, all shipped skills

**Validation:** **9 incidents across 8 merged PRs** (as of PR I, v1.2.4 — kept current; if you find a 10th, update this line plus the incident count in `plan.md` + `CHANGELOG.md` + manifest descriptions in lockstep, or you've just demonstrated FB-0010 working on its own entry again). Pattern is real and stable enough to encode + extend.

**Sub-classes** (named retroactively after PR I's review surfaced that the original two-flavor framing under-covered the workflow-discipline shape):

1. **Code-edge silent-skip** (8 prior incidents, PRs 1, B, D, E, F-pass-1, F-pass-2, G, H1) — code that fails on an edge case without surfacing the failure. Examples cited in "What was said" above plus: PR G's `SCAN_TARGETS` shell-word-split bug (gawk-only `match()` in /flow:doctor Check 2.5 first draft, caught by smoke-test); PR H1's zsh-vs-bash word-splitting silent-skip in Check 2.5 (caught by engineer-lens cold-bash, fixed in commit 7826928).

2. **Workflow-step judgment-skip** (1 incident, PR H1 → defended by PR I) — author makes a deliberate decision to skip a discipline-required action, justified after-the-fact ("would have been a no-op anyway"), missing that the discipline produces signal (here: `STATUS: SKIPPED` log lines in the session transcript) regardless of whether the body runs. **Distinct from silent-skip:** the author didn't fail to notice the skip; they chose it. Different defense shape: prompt-level reminders + workflow.md discipline statements + project-dev rules, not louder error handling. PR I's defense.

3. **Fan-out contradiction** (sub-class of code-edge silent-skip when the value referenced in N files is a count/name/version — see "What was said" point 2 above). Caught itself recursively inside PR G + PR H1 + PR I (4 times across the FB-0010 defense PRs themselves). Each self-catch is a mini-confirmation that the discipline works on the discipline-PRs.

Eval signal: the engineer-lens catches the silent-skip flavor reliably first-pass; the fan-out + workflow-step-judgment flavors required adversarial-second-pass review in 4 of 9 incidents. Reminder: when changing this count, run `git grep -nE '([0-9]+) incident'` across the codebase before staging.
