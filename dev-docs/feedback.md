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

### FB-0016: A negative spike result on a new or fast-evolving capability is one data point, not a verdict to abandon — record a re-test trigger (across un-sampled problem types, incl. UI) instead of writing it off
**Date:** 2026-05-28
**Source:** user direction (stated during the dynamic-workflows reviewer-refutation spike)

**What was said:** The spike returned a negative result — blind independent refutation did not cut the reviewer false-positive tax on one shell-script diff (`bootstrap.sh`). The user directed: write the verdict honestly, but ALSO put it on the roadmap to re-test later with different problem types — "this feature is going to evolve so we don't want to completely write it off yet ... it will be important to test in some other projects with UI as well." Earlier in the same session the user also insisted the experiment run on "something useful and substantive where I will be able to judge the result," and steered the spike's scope to its highest-signal, lowest-cost shape.

**Synthesized rule:** When a spike, eval, or experiment yields a negative or surprising result about a **new or fast-evolving capability** (research-preview features, freshly-shipped primitives, anything still changing under us):

```
(a) Record the result honestly in history.md WITH the named limitation that
    bounds it (one diff / one problem type / already-reviewed-clean target /
    single-model / etc.). A conclusion is only as general as the sample.

(b) Do NOT treat one data point on one problem type as a general verdict to
    abandon the direction. Create a roadmap § Exploration entry with a
    `Surfaces when:` trigger to re-test as the capability matures — and
    enumerate the problem types NOT yet sampled (UI surfaces especially,
    genuinely-buggy / pre-review diffs, larger/migration scale).

(c) Capture the most promising untested variant the experiment pointed at,
    so the re-test starts ahead of where this one ended (here: informed-
    independent refutation + a significance rubric, vs the blind variant).

(d) Scope experiments to substantive, human-judgeable targets up front — a
    trivial or unjudgeable target produces a result you can't trust either way.
```

**Applies to:** spikes + research passes, evaluating new Claude Code / Anthropic capabilities (dynamic workflows, future primitives), roadmap § Exploration hygiene, history.md verdict entries.

**Validation:** First applied to the 2026-05-28 reviewer-refutation spike — verdict recorded in `history.md` ("Reviewer-refutation spike — verdict") with its single-diff limitation named, and re-test direction captured in `roadmap.md` § Exploration ("Dynamic-workflows-based review: re-test refutation across problem types, incl. UI"). See `dev-docs/research/dynamic-workflows-2026-05.md`.

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

### FB-0012: Bounded-retry agent loops must loop only on mechanically-verifiable exit codes, never on LLM-judgment outputs; oscillation detection via diff-hash is mandatory on top of the iteration cap
**Date:** 2026-05-27
**Source:** user direction (synthesized from research pass + design discussion before PR M)

**What was said:** User asked whether `/loop` and goal-iteration primitives belonged in flow's review/quality workflow, and whether iteration could plateau or oscillate. The honest answer surfaced two distinct design rules: (1) loops are productive when the exit signal is an external tool's exit code (typecheck pass, test green, lint clean); loops are *harmful* when the exit signal is another LLM's judgment ("the auditor approved," "the reviewer says it looks good") because they teach the writer to phrase around the reviewer rather than fix substance — exactly the reward-hacking failure mode that passive-review-with-evidence-or-silence is designed to prevent. (2) A bounded iteration cap (N=3) alone is insufficient — a session can oscillate between fix-A-then-fix-B until exhaustion without converging. Diff-hash on top of the cap catches pure A↔B↔A oscillation cheaply.

**Synthesized rule:** Bounded-retry contracts in any flow skill MUST satisfy three conditions to ship:

```
(a) The exit signal must be mechanically verifiable — an external tool's exit
    code, a regex match on stable text, a file-existence check. NEVER the
    output of an LLM-judgment step (reviewer "approved", auditor "clean",
    plan-critic "APPROVED"). If the exit signal is another model's call,
    keep the step single-pass and rely on the human merge gate.

(b) The iteration cap must be paired with an orthogonal abort condition.
    Diff-hash equality (sha256 of `git diff HEAD` against prior attempts)
    is the canonical cheap detector — pure oscillation aborts before the
    cap exhausts. The cap and the orthogonal check are NOT redundant: the
    cap catches *drift* (each attempt different but all broken); the hash
    catches *oscillation* (an attempt repeating a prior diff).

(c) The contract must explicitly forbid reward-hacking fixes: "do not
    modify or disable tests to silence preflight; do not add @ts-ignore /
    # noqa / eslint-disable / @SuppressWarnings or equivalent suppressors."
    Prompt-level guards are probabilistic; the human merge gate is the
    backstop, but the contract should not produce escape hatches by
    default.
```

When designing the next bounded-retry block (if any), inherit these three conditions from `/flow:ship` Step 1c as the canonical contract. Do NOT copy-paste the prose if a second block lands — extract to `plugins/flow/docs/retry-contract.md` and reference (preempts the loud-warning-copy-dedup shape from PR-2 FOLLOW-UPs).

**Applies to:** workflow design, agent-loop contracts, /flow:ship + /flow:ship-spike Step 1c, any future bounded-retry primitive

**Validation:** Encoded as the load-bearing design call of PR M (v1.2.6). Independently converged with Microsoft Magentic's `max_stall_count` primitive (Magentic counts consecutive non-progressing rounds; Flow detects exact-diff oscillation — same defensive shape, different detector). Research sources: Anthropic's "Building Effective Agents" (evaluator-optimizer pattern requires "stopping conditions ... to maintain control" + "explicit success criteria"); 2026 Agentic Coding Trends Report ("without explicit success criteria, verification becomes guesswork"); Claude Code's own scheduled-task docs ("be explicit about what success looks like ... the task runs autonomously, so it can't ask clarifying questions"). The "loop only on mechanical signals" call is the cure for the reward-hacking failure mode that loops-over-LLM-judgment invite — same shape as why flow's reviewers are passive ("evidence or silence") rather than active. See `dev-docs/research/agent-orchestration-2026-05.md` for the full industry survey supporting this rule.

### FB-0011: Autonomy bar — act when clearly best-practice + low-risk + no competing options; otherwise stop and present
**Date:** 2026-05-27
**Source:** user direction (stated during PR J planning conversation, in response to the REDIRECT question about red-team BLOCKER auto-fix vs stop-and-present)

**What was said:** Asked whether `/flow:ship` should auto-apply red-team BLOCKER fixes in-tree (faster, more autonomous) vs stop and present them for explicit user approval (slower, safer for one-way-door choices), the user gave a nuanced hybrid: *"If there is a solution that is clearly aligned with best practices as well as the spec/intent of the project and there is little risk in implementing it, then that should be done automatically. If the path forward is unclear, there are still significant risks, or there are competing options that are significantly different that both have merit, or there are one-way door decisions that need to be made, then the implementation should stop and wait for human review."*

**Synthesized rule:** In the Flow workflow's autonomy direction, an agent may act autonomously ONLY when ALL three hold: (1) the action is clearly aligned with best practices, (2) clearly aligned with the project's spec/intent (cite the rule/doc), (3) implementation risk is low (mechanical fix, single-file, recoverable). Stop and present to the user when ANY hold: the path forward is unclear; significant risks remain; competing options of comparable merit exist; or the decision is one-way-door.

This extends the existing **confidence-gate doctrine** ([[user-confidence-gates]] in workflow.md § "Confidence gates" — HIGH proceeds, MEDIUM surfaces at step 8, LOW auto-blocks) into auto-fix routing. The connection is direct: LOW-confidence assumptions can't proceed without explicit user resolution; analogously, a finding whose fix would constitute a LOW-confidence change can't auto-apply without explicit user resolution.

**Encoded as:**
- Per-finding `Fix-confidence:` field on `/flow:red-team` output schema (ships PR K) with values `AUTO-FIX-SAFE` (all three "act" conditions hold) vs `ESCALATE` (any "stop" condition holds). Default to `ESCALATE` when in doubt — false positives on stop-and-present cost the user a moment of attention; false positives on auto-fix could corrupt safety-critical code.
- `/flow:ship` Detection-Point-3 routing (ships PR L): `AUTO-FIX-SAFE` findings auto-apply in-tree, re-run preflight + red-team, ship if clean (cap at 4 iterations per the research diminishing-returns curve). `ESCALATE` findings stop the ship and surface to the user with full two-citation evidence + suggested fix.
- Conservative AUTO-FIX-SAFE category list (starts narrow; grows only with dogfood evidence). Initial examples: committed secret → delete + add to .gitignore; outbound HTTP→HTTPS upgrade; missing input validation that follows an existing in-repo pattern verbatim.
- Project-memory entry at `~/.claude/projects/-Users-benyamron-dev-flow/memory/feedback_autonomy_bar.md` (cross-session reminder; this FB entry is the consumer-shipped canonical version).

**Applies to:** workflow, autonomous gates, /flow:red-team (PR K), future Execute-stage gates, future /flow:staff-review BLOCKER triage, /flow:ship orchestration

**Validation:** Stated explicitly by the user 2026-05-27 during PR J planning; saved to project memory same day; encoded into PR J's plan as the PR-L Detection-Point-3 routing rule. PR L ships the mechanical enforcement. (Originally planned as PR-K Detection-Point-3 routing; renumbered to PR L after the parallel PR I collision required a PR J → PR K → PR L cascade.)

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
