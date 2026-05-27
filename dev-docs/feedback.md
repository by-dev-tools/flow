# Feedback Log

User feedback synthesized into actionable guidance. When the user gives feedback -- corrections, preferences, reactions, direction changes -- the relevant insight is captured here so it shapes all future work.

This is not a transcript. Each entry distills feedback into a rule or preference that applies going forward.

---

## How to Write an Entry

```
### FB-XXXX: [Short summary of the feedback]
**Date:** YYYY-MM-DD
**Source:** user correction | user preference | user direction | review feedback

**What was said:** Brief, factual summary of the feedback.

**Synthesized rule:** The actionable takeaway -- what to do differently going forward.

**Applies to:** [areas this affects: ux, code, architecture, workflow, etc.]
```

### Numbering
Increment from the last entry. Use `FB-0001`, `FB-0002`, etc.

### Source types
- **user correction** -- user fixed something you did wrong
- **user preference** -- user expressed a stylistic or process preference
- **user direction** -- user set strategic direction or priorities
- **review feedback** -- issues found during code/design review

---

## Entries

<!-- Add new entries below this line, newest first. -->

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

**Validation:** 6 incidents across 5 merged PRs + 1 in-flight PR (PR F two-pass). Pattern is real and stable enough to encode. Eval signal: the engineer-lens has now caught only 4 of the 6 occurrences first-pass; adversarial second-pass caught the other 2 (both fan-out contradictions, the harder-to-grep flavor). The fix targets close the gap.

### FB-0009: `gh` CLI dependency in shipped skills must fail-fast, not silently 127
**Date:** 2026-05-25
**Source:** review feedback (synthesized from md-manager PR 4 consumer-feedback report 2026-05-25)

**What was said:** md-manager's PR 4 sibling-validation worktree (`~/dev/md-manager-pr4-validate`) lacked `gh` CLI. `/flow:ship` Step 1 (`gh pr list` for PR-OPEN detection) fell back gracefully via the `2>/dev/null` swallow. Step 7 (`gh pr create`) did NOT fall back — exit 127 with no diagnostic. The umbrella owner had to take over and run `gh pr create` from a worktree that had it installed.

**Synthesized rule:** Every flow skill that invokes `gh` (or any other external CLI not guaranteed by Claude Code) must fail-fast at Step 1 with a clean install hint, not at the invocation site with `exit 127`. Pattern: `if ! command -v gh >/dev/null 2>&1; then echo "⚠️ /flow:<skill> requires the gh CLI. Install: brew install gh (macOS) or https://cli.github.com" >&2; exit 1; fi`. Add to `/flow:ship` Step 1, `/flow:staff-review` Step 1 (gh-pr-list optional but used), and `/flow:ship-spike` Step 1 (`gh pr create` mandatory). Document `gh` as an install prerequisite in `docs/bootstrap.md` + `docs/migration.md` Step 1 sections. Same shape would apply to any future `jq`, `git`, or `node` dependency that flow assumes — fail-fast at the workflow entrypoint, not at the invocation site.

**Applies to:** workflow, dependency hygiene, error UX

**Validation:** 1 BLOCKER in md-manager PR 4 sibling worktree; recovery cost was a worktree switch + manual `gh` invocation. Could have been a clean stop with install hint at workflow entry.

### FB-0008: Stale-base preflight is the cheapest gate for the most expensive class of dogfood waste
**Date:** 2026-05-25
**Source:** review feedback (synthesized from md-manager PR 4 consumer-feedback report 2026-05-25)

**What was said:** md-manager PR 4 (PR #23) forked at `b8b0e0b` while `origin/main` had advanced to `eb8e7b9` by the time Phase 4.3 ran `/flow:staff-review`. Three of four lenses converged on "stale-base producing phantom-deletion diff" as the headline BLOCKER. Fix was a single rebase; **discovery cost was 4 lens spawns + minutes of triage**. md-manager's retro `/critique-plan` post-merge also flagged "base is current with main" as the missing load-bearing assumption from the per-PR plan — captured as md-manager's FB-0033.

**Synthesized rule:** Every flow skill that consumes a diff vs the default branch must include a stale-base check at the workflow entrypoint, before any expensive operation (especially lens-agent spawn). Pattern for `/flow:ship` Step 1, `/flow:staff-review` Step 1, `/flow:ship-spike` Step 1:

```sh
# Resolve default branch via PR-1's 3-tier fallback chain
DEFAULT_BRANCH=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@' \
  || cat flow.config.json 2>/dev/null | jq -r '.defaultBranch // "main"' \
  || echo "main")

git fetch origin --quiet
if ! git merge-base --is-ancestor "origin/${DEFAULT_BRANCH}" HEAD; then
  echo "⚠️ BLOCKER: branch is stale vs origin/${DEFAULT_BRANCH}. Rebase or merge before /flow:<skill>." >&2
  echo "       (current HEAD: $(git rev-parse --short HEAD); base needs $(git rev-list --count HEAD..origin/${DEFAULT_BRANCH}) commits)" >&2
  exit 1
fi
```

Class lesson: when a recurring expensive review-loop pattern is reducible to a mechanical check, write the mechanical check. The 4-lens-spawn-then-converge dynamic that caught PR 23's stale base is exactly what the loop's review surface is for — but a free upstream check that prevents the burn is strictly cheaper.

**Applies to:** workflow, preflight discipline, cost-of-review

**Validation:** 1 BLOCKER in md-manager PR 4. Reinforced cross-repo: md-manager's own retro `/critique-plan` reached the same conclusion independently and captured it as md-manager FB-0033 ("don't skip /critique-plan or /simplify even on docs-only diffs"). The class is real.

### FB-0007: Per-diff non-UI early-exit in /flow:accessibility-review (uiSurface=true projects shipping docs-only)
**Date:** 2026-05-25
**Source:** review feedback (synthesized from md-manager PR 4 consumer-feedback report 2026-05-25)

**What was said:** md-manager's `flow.config.json` declares `uiSurface: true` (correct — the project has UI). md-manager PR #23 was docs+config only; no UI files in the diff. `/flow:accessibility-review` still triggered full agent spawn against the diff, returned "nothing to review," and the spawn cost was wasted. The `uiSurface: false` early-exit gate flow ships protects backend/CLI/library consumers but doesn't protect UI-surface projects shipping docs-only PRs.

**Synthesized rule:** `/flow:accessibility-review` Step 1 should pair the existing `uiSurface=false` project-wide gate with a per-diff non-UI detection. Pattern (`${DEFAULT_BRANCH}` resolved via PR-1's 3-tier fallback chain — see FB-0008 snippet):

```sh
# Existing: project-wide early-exit
UI_SURFACE=$(cat flow.config.json 2>/dev/null | jq -r '.uiSurface // true')
if [ "$UI_SURFACE" = "false" ]; then echo "[a11y-review] uiSurface=false; skipping."; exit 0; fi

# NEW: per-diff early-exit
UI_FILES_IN_DIFF=$(git diff "origin/${DEFAULT_BRANCH}..HEAD" --name-only | grep -E '\.(tsx|jsx|vue|svelte|css|scss|html)$|^(src|app|packages/ui)/' || true)
if [ -z "$UI_FILES_IN_DIFF" ]; then echo "[a11y-review] no UI files in diff; skipping."; exit 0; fi
```

The UI-file regex is necessarily heuristic; consider a `flow.config.json.uiFilePatterns` slot for projects that want to override (e.g., monorepos with non-standard layouts). Pair this PR with FB-0006 — same fix shape, same detection scaffolding, one PR.

**Applies to:** workflow, /flow:accessibility-review, cost-of-review

**Validation:** 1 wasted spawn in md-manager PR 4. Every consumer with `uiSurface: true` will hit this on every docs-only PR.

### FB-0006: Per-diff doc-only early-exit in /flow:security-review (currently only prose, not structured)
**Date:** 2026-05-25
**Source:** review feedback (synthesized from md-manager PR 4 consumer-feedback report 2026-05-25)

**What was said:** md-manager PR #23 was docs+config only. `/flow:security-review`'s body says "skip if doc-only" in prose but has no structured early-exit gate — the orchestrator (or human) has to detect doc-only manually. By contrast, `/flow:accessibility-review` has a project-wide `uiSurface=false` gate (but lacks per-diff coverage; see FB-0007).

**Synthesized rule:** `/flow:security-review` Step 1 should add per-diff source-file detection paralleling FB-0007's a11y fix. Pattern (`${DEFAULT_BRANCH}` resolved via PR-1's 3-tier fallback chain — see FB-0008 snippet):

```sh
SOURCE_FILES_IN_DIFF=$(git diff "origin/${DEFAULT_BRANCH}..HEAD" --name-only | grep -E '\.(ts|tsx|js|jsx|py|rs|swift|go|rb|java|sh|mjs)$|\.json$|\.yaml$|\.yml$' || true)
if [ -z "$SOURCE_FILES_IN_DIFF" ]; then echo "[security-review] no source/config files in diff; skipping."; exit 0; fi
```

The source-file regex is necessarily heuristic; consider a `flow.config.json.sourceFilePatterns` slot for projects that want to override. Pair this PR with FB-0007 — same fix shape, same detection scaffolding, one PR.

**Applies to:** workflow, /flow:security-review, cost-of-review

**Validation:** 1 forced manual-skip-decision in md-manager PR 4. Every doc-only PR in any consumer triggers the same friction.

### FB-0005: Marketplace-key-mismatch is a silent-failure UX bug; install docs must verify by name
**Date:** 2026-05-25
**Source:** review feedback (synthesized from md-manager PR 4 consumer-feedback report 2026-05-25)

**What was said:** md-manager's user-scope `~/.claude/settings.json` had `extraKnownMarketplaces.llm-auditor` pointing at `https://github.com/by-dev-tools/flow.git` (stale key from before flow's PR 1 marketplace rename). Project-scope had `"enabledPlugins": { "flow@flow": true }`. Flow's `marketplace.json` declares `name: "flow"`. Result: `/help` silently omitted all `/flow:*` skills. No error, no warning, no diagnostic. Root cause: `enabledPlugins.<plugin>@<marketplace>` resolves by matching the marketplace's `name` field, NOT the user-scope settings key. A stale-keyed entry pointing at the right URL is invisible to the resolver.

**Synthesized rule:** Flow's `docs/bootstrap.md` (NEW projects) and `docs/migration.md` (EXISTING projects with prior `.claude/` content) Step 1 must include an explicit marketplace-name verification step:

```sh
# After /plugin marketplace add by-dev-tools/flow:
/plugin marketplace list | grep '^flow'   # must return a line; if absent, registration failed
```

If absent, instruct: `/plugin marketplace add by-dev-tools/flow` (re-adds with the correct name, regardless of whether a stale-keyed entry already exists pointing at the same URL). Optionally consider a `flow:doctor` skill or `template/base/scripts/verify-install.sh` that does the mechanical check + emits a clean diagnostic. Worth considering filing an upstream Claude Code issue — silent-failure on `enabledPlugins`-without-matching-marketplace is a UX bug regardless of plugin.

**Applies to:** install ergonomics, /docs/bootstrap.md, /docs/migration.md, dependency hygiene

**Validation:** 1 BLOCKER in md-manager PR 4 — the consumer hit it during Stage 1 install. Every future consumer with a stale `extraKnownMarketplaces` entry (or any name-mismatch shape) will hit the same silent-omission failure.

### FB-0004: Security regression tests must assert on what would leak, not on a proxy for it
**Date:** 2026-05-25
**Source:** review feedback (PR 3 engineer-lens dogfood)

**What was said:** PR 3 Phase 7's engineer lens caught that `test_absolute_outside_cwd_rejected` asserted `"/etc/hosts" not in result.stdout` — passes trivially because a content leak prints `127.0.0.1` (the host file's content), not the path string. A regression that drops the cwd check but doesn't print the path would pass the test silently. The dotdot-traversal test in the same file got it right: `"127.0.0.1" not in stdout and "::1" not in stdout`. Both rejection + accept tests were strengthened in the same Phase 7 fix commit to use content sentinels.

**Synthesized rule:** When writing a security regression test, identify what a real leak/breach would actually output, then assert on THAT. A real leak of `/etc/hosts` prints loopback addresses, not the path. A real leak of `~/.ssh/id_rsa` prints `-----BEGIN OPENSSH PRIVATE KEY-----`. A real shell injection prints `pwned` or creates a marker file. The path string is a proxy and proxies have escape hatches. When in doubt: write a deliberately-broken implementation locally, run the test, verify it FAILS. If the test passes with a known-broken implementation, the assert is vacuous.

**Applies to:** security regression testing, workflow

**Validation:** 1 BLOCKER caught in PR 3 Phase 7. Original assert: `"/etc/hosts" not in result.stdout or "outside" in combined.lower() or "external" in combined.lower()` — three disjuncts, any of which trivially satisfies. Replaced with `"127.0.0.1" not in result.stdout and "::1" not in result.stdout` — content-only, no escape hatch.

### FB-0003: Schema-without-implementation is a class of bug only dogfood catches
**Date:** 2026-05-24
**Source:** review feedback (PR 2 engineer-lens dogfood)

**What was said:** The Phase-7 engineer-lens review on PR 2 flagged that `memoryHardCap` was documented in `flow.config.schema.json` as configurable but `tools/memory/check.mjs` hardcoded `HARD_CAP = 30` and never read the config — a "false affordance" in the engineer lens's words. Same pattern with `branchPrefix`: documented in schema, no consumer in any skill. Both shipped through Phase 5's pre-commit greps cleanly because no static check correlates "slot documented in schema" against "slot read by something."

**Synthesized rule:** Every config slot landed in `flow.config.schema.json` must be paired with at least one consumer SKILL/agent/tool that reads it AT LANDING TIME — not "documented now, wired later." If a slot is genuinely future-only, mark it `"deprecated": "v1.x — not yet implemented"` in the schema description so consumers know. Treat schema-without-implementation as a contract lie equivalent to the loud-warning-vs-silent-no-op risk from PR 1. Pre-commit check: `for slot in $(jq -r '.properties | keys[]' schema/flow.config.schema.json); do if ! grep -q "$slot" plugins/flow/{skills,agents,tools,scripts}/; then echo "WARN: $slot documented but no consumer"; fi; done`.

**Applies to:** workflow, schema design, config-slot contracts

**Validation:** 2 of 13 slots in PR 2's schema (memoryHardCap, branchPrefix) had no consumer at first commit; engineer-lens caught both. Both wired in Phase 7 fix commit. The remaining 11 slots had at least one consumer.

### FB-0002: Validator-pass doesn't mean runtime-safe; the dispatcher is its own contract
**Date:** 2026-05-24
**Source:** review feedback (PR 2 engineer-lens dogfood)

**What was said:** Phase 7 caught that `/flow:ship`'s Phase-6 backfill invoked `Skill("flow:security-review")` and `Skill("flow:accessibility-review")` but the SKILL.md's `allowed-tools` frontmatter didn't list `Skill`. `claude plugin validate .` passed (the manifest is syntactically clean); the cwd-constraint test passed; the smoke install passed. The bug would have surfaced only at runtime when the dispatcher denied the tool call. This is a class of bug the validator can't catch and pre-commit greps would miss.

**Synthesized rule:** When a SKILL invokes a tool (`Skill`, `Agent`, `Bash`, `Edit`, `Write`, `Read`, `Glob`, `Grep`, `TaskCreate`, `TaskUpdate`, etc.), explicitly verify that tool is in the SKILL's `allowed-tools` frontmatter. The frontmatter is the dispatcher's contract; `claude plugin validate` validates manifest syntax, not tool-allowlist correctness. Recommended pre-commit grep:
```sh
for skill in plugins/flow/skills/*/SKILL.md; do
  ALLOWED=$(awk '/^allowed-tools:/{print; exit}' "$skill")
  for tool in Skill Agent Bash Edit Write Read Glob Grep TaskCreate TaskUpdate; do
    if grep -qE "\\b${tool}\\(" "$skill" && ! echo "$ALLOWED" | grep -qE "\\b${tool}\\b"; then
      echo "WARN: $skill invokes $tool but allowed-tools omits it"
    fi
  done
done
```

**Applies to:** workflow, plugin skill development, pre-commit checks

**Validation:** 1 BLOCKER caught in PR 2's Phase 7 dogfood (Skill missing from ship.md). PR 1 had no Skill invocations so this class was latent until PR 2.

### FB-0001: Dogfood the workflow even when not all skills exist yet
**Date:** 2026-05-24
**Source:** user direction

**What was said:** After PR 1 was opened, the user said: "even though all the skills may not be officially built out yet, follow the prompts from the skills in workflow.md to review the PR, taking it through all the stages of the intended workflow that we are implementing."

**Synthesized rule:** When a PR builds the workflow infrastructure itself, dogfood every loop step that *can* be run (manually or by emulating the planned skill's prompt via Agent subagents). Don't skip a step because the named skill doesn't exist yet — the loop's value is the *steps*, not the skill packaging. Concrete pattern: spawn 3-4 parallel review-lens Agents (engineer, push-further, security, plan-critic emulation) with the equivalent of the planned SKILL.md prompts; triage findings via the same BLOCKER / NIT / FOLLOW-UP scheme; apply BLOCKER + cheap NIT inline; route FOLLOW-UPs to plan.md; write the history.md entry; push the fix commit so the PR auto-updates.

Don't pre-empt this rule with "no skill, no review" — that defeats the point of building flow at all. Bootstrap exception (manual cold-read) is the *fallback* when even manual review isn't feasible, not the *default* when a manual review would be cheap.

**Applies to:** workflow, code review, agent self-feedback discipline

**Validation:** the walk-through-the-loop pass on PR 1 caught 3 BLOCKERs the pre-merge cold-read missed (manifest redundancy, two stale `agents/auditor.md` references in shipped prompts, `eval` vs `sh -c`). All three would have been consumer-visible bugs if shipped.
